import https from 'https';
import { ensureVertexAccessToken } from './vertexAuth.js';
import { getActiveKeyPool } from './llmKeyStore.js';
import { redactSecrets } from './urlGuard.js';

// ── Provider registry ───────────────────────────────────────────────────────
// Cả tầng LLM dùng chung format OpenAI (/chat/completions). Đổi provider CHÍNH chỉ bằng MỘT biến môi
// trường LLM_PROVIDER (không phải sửa code): 'gemini' = Google chính hãng (mặc định) hoặc 'vilao' = dự
// phòng. Mỗi provider tự khai endpoint + biến chứa API key + tên model (chữ / ảnh), override được qua env.
//   • Gemini: endpoint OpenAI-compat — nuốt response_format json_object + image_url data-URL + Bearer auth,
//     nên payload hiện tại chạy nguyên si. (Lưu ý: prompt-caching KHÔNG có trên shim này, chỉ có ở SDK gốc.)
const PROVIDERS = {
  gemini: {
    chatUrl:  'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
    apiKeyEnv: 'GEMINI_API_KEY',
    // Alias '-latest' (tự trỏ tới bản Flash GA hiện hành) — bền hơn ID phiên bản cứng, tránh 404
    // "no longer available to new users" khi Google ngừng một phiên bản (vd gemini-2.5-flash).
    // Flash-Lite: rẻ nhất + gần như không "thinking" ⇒ nhanh (bản Flash đầy đủ bật suy luận nên hay
    // timeout với tác vụ xuất JSON dài). Alias '-latest' tự trỏ bản Lite GA hiện hành. Đổi qua
    // gemini-flash-latest nếu cần Flash "xịn" hơn (đắt + chậm hơn).
    // gemini-flash-latest = bản Flash đầy đủ hiện hành (đang là 3.7 Flash, $0.75/$3.75) — chất lượng
    // tốt hơn Flash-Lite. Flash bật "thinking" động nên chậm ⇒ ta GIỚI HẠN suy luận bằng
    // GEMINI_REASONING_EFFORT (mặc định 'low') ở phần dựng request bên dưới ⇒ nhanh mà vẫn tốt.
    textModel:   process.env.GEMINI_MODEL        || 'gemini-flash-latest',
    visionModel: process.env.GEMINI_VISION_MODEL || process.env.GEMINI_MODEL || 'gemini-flash-latest',
  },
  vilao: {
    chatUrl:  'https://api.vilao.ai/v1/chat/completions',
    apiKeyEnv: 'VILAO_API_KEY',
    textModel:   process.env.VILAO_MODEL || 'ts/gemini-3.1-flash-lite',
    visionModel: process.env.VILAO_MODEL || 'ts/gemini-3.1-flash-lite',
  },
};

// Nhớ KIỂU AUTH đã dùng được cho từng host gateway (in-memory, theo tiến trình).
//   'bearer' = header "Authorization: Bearer <key>" (vilao, gemini, đa số).
//   'raw'    = header "Authorization: <key>" (một số gateway như api.xah.io nhận key TRẦN).
// Nhờ đó lần đầu tự dò (Bearer → nếu 401/403 thì thử key trần), các lần sau đi thẳng kiểu đúng,
// để hai loại khoá (vilao + custom) cùng chạy trong pool mà không tốn lượt thử thừa.
const AUTH_SCHEME_BY_HOST = new Map();

// Host của các nhà cung cấp CHUẨN vốn dùng "Bearer" — KHÔNG dò key trần cho chúng (tránh tốn 1 lượt
// thử thừa khi khoá 401 vì hỏng thật, và giữ nguyên thứ tự fallback khoá). Chỉ gateway LẠ (vd
// api.xah.io) mới được thử đổi sang key trần.
function isBearerOnlyHost(host) {
  const h = String(host || '').toLowerCase();
  return h === 'api.vilao.ai'
    || h === 'generativelanguage.googleapis.com'
    || h.endsWith('aiplatform.googleapis.com');
}

// Vertex AI (endpoint OpenAI-compat của Google Cloud). KHÁC 'gemini' (AI Studio) ở 2 điểm:
//   • URL mang PROJECT + LOCATION (region) → tính TƯƠI mỗi lần để nhận biến đặt lúc chạy (không cứng ở
//     import). location 'global' dùng host 'aiplatform.googleapis.com'; region khác → '<loc>-aiplatform…'.
//   • Auth = OAuth ACCESS TOKEN (sống ~60') đặt ở VERTEX_ACCESS_TOKEN — KHÔNG phải API key tĩnh; bên
//     ngoài (bộ nạp token) tự làm mới trước khi hết hạn rồi ghi lại biến này (callVilao đọc TƯƠI mỗi lượt).
//   • Tên model trên Vertex cần tiền tố nhà phát hành: 'google/gemini-2.5-flash' (đổi qua VERTEX_MODEL).
export function vertexProvider() {
  const project = process.env.VERTEX_PROJECT || '';
  const loc = (process.env.VERTEX_LOCATION || 'global').trim();
  const host = loc === 'global' ? 'aiplatform.googleapis.com' : `${loc}-aiplatform.googleapis.com`;
  const model = process.env.VERTEX_MODEL || 'google/gemini-2.5-flash';
  return {
    chatUrl: `https://${host}/v1beta1/projects/${project}/locations/${loc}/endpoints/openapi/chat/completions`,
    apiKeyEnv: 'VERTEX_ACCESS_TOKEN',
    textModel: model,
    visionModel: process.env.VERTEX_VISION_MODEL || model,
  };
}

// Provider ĐANG hoạt động (mặc định 'vilao'). Giá trị lạ ⇒ về vilao. Đặt LLM_PROVIDER=gemini (AI Studio
// chính hãng) hoặc LLM_PROVIDER=vertex (Vertex AI, tính tiền qua Google Cloud) — code đã sẵn, chỉ đổi biến.
export function activeProvider() {
  const key = (process.env.LLM_PROVIDER || 'vilao').toLowerCase();
  if (key === 'vertex') return vertexProvider();
  return PROVIDERS[key] || PROVIDERS.vilao;
}

// Giữ để tương thích: đường "khoá tường minh" (test key Vilao, override advance) vẫn dùng model nền Vilao.
const VILAO_MODEL = PROVIDERS.vilao.textModel;

function httpsRequest(url, options, bodyData, timeoutMs) {
  return new Promise((resolve, reject) => {
    let hardTimer = null;
    const clearHardTimer = () => { if (hardTimer) { clearTimeout(hardTimer); hardTimer = null; } };

    const req = https.request(url, options, (res) => {
      // Dọn đồng hồ khi phản hồi đã ĐỌC XONG (hoặc đứt) — không để đồng hồ hủy nhầm request đã hoàn tất.
      res.on('end', clearHardTimer);
      res.on('close', clearHardTimer);
      resolve(res);
    });

    req.on('error', (err) => {
      clearHardTimer();
      reject(err);
    });

    if (timeoutMs) {
      // Đồng hồ CỨNG tính từ lúc gửi: hủy nếu vượt timeoutMs KỂ CẢ khi provider "nhỏ giọt" dữ liệu.
      // req.setTimeout chỉ bắt socket RẢNH nên khi server trả token chậm dần có thể treo 100s+ (đo thực:
      // 1 lượt tách đề chạy 124s dù timeoutMs=25s) → vượt maxDuration 60s của Vercel → hàm bị ngắt thô.
      hardTimer = setTimeout(() => { req.destroy(new Error('Request timed out')); }, timeoutMs);
      req.setTimeout(timeoutMs, () => { req.destroy(new Error('Request timed out')); });
    }

    if (bodyData) {
      req.write(bodyData);
    }
    req.end();
  });
}

export function isNetworkError(error) {
  if (!error) return false;
  const msg = (error.message || '').toLowerCase();
  const code = (error.code || '').toString().toUpperCase();
  // Soi cả .code: khi đồng hồ cứng hủy GIỮA stream, for-await ném Error('aborted') code ECONNRESET —
  // message KHÔNG chứa 'timed out'. Chỉ soi message thì bỏ sót lỗi timeout-giữa-stream (case hay gặp nhất).
  if (['ECONNRESET', 'ECONNREFUSED', 'ETIMEDOUT', 'ECONNABORTED', 'EPIPE'].includes(code)) return true;
  return msg.includes('timeout')
    || msg.includes('timed out')   // đồng hồ CỨNG ném Error('Request timed out') — 'timed out'≠'timeout'!
    || msg.includes('aborted')
    || msg.includes('econnreset')
    || msg.includes('connection reset')
    || msg.includes('network')
    || msg.includes('econnrefused')
    || msg.includes('fetch failed');
}

async function sleepMs(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Response Vilao KHÔNG có content dùng được? (thiếu choices, thiếu message, hoặc content rỗng/khoảng-trắng).
// gemini-flash thỉnh thoảng trả content="" dù finish_reason=stop và KHÔNG lỗi mạng → đây là lỗi
// TẠM (retry thường ra ngay ở lượt sau), nên callVilao coi nó như 5xx: thử lại trong vòng lặp thay vì
// fail thẳng (trước đây 1 lượt rỗng = toast "Lỗi vẽ hình / Vilao returned empty content"). Tách hàm
// thuần để test không cần mạng.
export function isEmptyVilaoContent(data) {
  if (!data || !Array.isArray(data.choices) || data.choices.length === 0) return true;
  const content = data.choices[0]?.message?.content;
  return typeof content !== 'string' || content.trim() === '';
}

// Vilao có endpoint trả JSON ĐƠN (model 'ram/*') HOẶC SSE STREAMING (model 'ts/*': mỗi dòng
// 'data: {chat.completion.chunk...}'). Chuẩn hoá cả hai về { choices:[{message:{content}}], usage }
// để phần dưới xử lý như nhau. Ném khi không parse được gì (caller bắt → "Failed to parse").
export function parseVilaoBody(dataText) {
  const trimmed = (dataText || '').trim();
  if (!trimmed) throw new Error('empty body');

  // 1) JSON đơn (non-streaming) — thử trước. KHÔNG bắt đầu bằng 'data:' ⇒ chắc chắn không phải SSE.
  if (!trimmed.startsWith('data:')) {
    return JSON.parse(trimmed);
  }

  // 2) SSE streaming: gộp content của TỪNG chunk (delta.content, hoặc message.content ở chunk cuối).
  let content = '';
  let usage = null;
  let finish = null;
  let sawChunk = false;
  for (const rawLine of trimmed.split('\n')) {
    const line = rawLine.trim();
    if (!line.startsWith('data:')) continue;
    const payload = line.slice(5).trim();
    if (!payload || payload === '[DONE]') continue;
    let chunk;
    try { chunk = JSON.parse(payload); } catch { continue; }
    sawChunk = true;
    const choice = chunk.choices && chunk.choices[0];
    if (choice) {
      const piece = (choice.delta && typeof choice.delta.content === 'string')
        ? choice.delta.content
        : (choice.message && typeof choice.message.content === 'string' ? choice.message.content : '');
      content += piece;
      if (choice.finish_reason) finish = choice.finish_reason;
    }
    if (chunk.usage) usage = chunk.usage;
  }
  // Có tiền tố 'data:' nhưng không chunk nào parse được ⇒ coi như hỏng, để caller ném "Failed to parse".
  if (!sawChunk) return JSON.parse(trimmed);
  return { choices: [{ message: { content }, finish_reason: finish }], usage };
}

export function resolveApiKey(options = {}, envKey = process.env.VILAO_API_KEY) {
  const key = options.apiKey || envKey;
  if (!key) throw new Error('Vilao API key is not set (opts.apiKey or VILAO_API_KEY)');
  return key;
}

/**
 * Khoá của provider theo THỨ TỰ ưu tiên: khoá CHÍNH (<apiKeyEnv>) rồi các khoá DỰ PHÒNG (<apiKeyEnv>_BACKUP).
 * Khi khoá chính hỏng vì LỖI KHOÁ (401/403 bị thu hồi/sai, 429 hết quota), callVilao tự chuyển khoá tiếp.
 * MỖI biến có thể chứa NHIỀU khoá ngăn bằng dấu phẩy / xuống dòng / khoảng trắng (nhiều key dự phòng chỉ
 * cần 1 biến): VILAO_API_KEY_BACKUP="sk-b1, sk-b2, sk-b3". Lọc rỗng + khử trùng, đọc TƯƠI mỗi lần.
 */
export function resolveApiKeyCandidates(apiKeyEnv, env = process.env) {
  const split = (v) => (v || '').split(/[\s,]+/).map((s) => s.trim()).filter(Boolean);
  const list = [...split(env[apiKeyEnv]), ...split(env[`${apiKeyEnv}_BACKUP`])];
  return [...new Set(list)];   // Set giữ THỨ TỰ chèn: chính trước, dự phòng sau
}

/**
 * Lỗi này có phải "lỗi KHOÁ" (đáng chuyển sang khoá dự phòng) không? — 401/403 (khoá sai/bị thu hồi),
 * 429 (hết quota / rate limit). KHÔNG tính timeout / mạng / 5xx: khoá khác trên CÙNG endpoint không cứu
 * được, và thử thêm dễ vượt trần thời gian của Vercel. statusCode gắn sẵn ở lỗi API; soi thêm message dự phòng.
 */
export function isKeyError(err) {
  if (!err) return false;
  const code = Number(err.statusCode);
  if (code === 401 || code === 403 || code === 429) return true;
  const msg = (err.message || '').toLowerCase();
  if (/\b(401|403|429)\b/.test(msg)) return true;
  return /unauthorized|forbidden|invalid api key|quota|rate limit|insufficient_quota|exceeded your/.test(msg);
}

export async function callVilao(systemPrompt, userPrompt, options = {}) {
  const {
    maxTokens = 4096,
    timeoutMs = 180000,
    imageBase64 = null,
    aiModel = 'low',
    useReasoning = false,
    onStream = null,
    model = null,
    apiKey = null,
    provider = null,   // (chỉ khi có apiKey) 'gemini'|'vilao' — chọn endpoint cho khoá tường minh (tab Test API Key).
    baseUrl = null,    // (chỉ khi có apiKey) đè thẳng URL /chat/completions; ưu tiên cao hơn provider.
    maxAttempts = 2,   // số lần thử tối đa (kể cả retry nội bộ khi lỗi mạng/timeout). Đặt 1 khi caller
                       // đã tự hedge (chạy song song) để khỏi chồng retry gây phí token.
    returnRaw = false, // true → trả { content, usage, model } (cho tab Test API Key: cần token). Mặc định giữ nguyên (trả content).
    reasoningEffort = null, // ÉP mức suy luận PER-CALL ('none'|'low'|'medium'|'high') — ưu tiên hơn env
                            // dùng chung. Cho bước dịch Lý/Hóa ép 'low' (dịch máy móc, chống timeout) mà
                            // KHÔNG đổi reasoning của luồng Toán (Toán không truyền ⇒ giữ hành vi env).
  } = options;

  // Chọn endpoint + khoá + model theo NGỮ CẢNH:
  //  • CÓ options.apiKey (admin test khoá Vilao, hoặc override ADVANCE/DETAILED): đi ĐÚNG endpoint Vilao
  //    với khoá + model được truyền — giữ nguyên hành vi cũ của các tính năng đó.
  //  • KHÔNG có: dùng provider ĐANG hoạt động (mặc định Gemini chính hãng) — endpoint + khoá env + model
  //    của provider. Tên model format Vilao mà caller truyền (translator…) BỎ QUA, vì mỗi provider đặt tên
  //    khác nhau và cả app chỉ có MỘT model logic ("flash rẻ"); đổi model theo provider qua GEMINI_MODEL /
  //    GEMINI_VISION_MODEL (hoặc VILAO_MODEL). `aiModel`/`useReasoning` không còn đổi model (giữ tham số cho
  //    tương thích; `useReasoning` vẫn chỉ tác động cờ JSON mode bên dưới).
  // candidates: danh sách ỨNG VIÊN thử theo THỨ TỰ, mỗi ứng viên MANG endpoint (url) + model RIÊNG →
  // khoá dự phòng có thể là NHÀ CUNG CẤP KHÁC + MODEL KHÁC. Ứng viên không khai url/model ⇒ dùng mặc định
  // của provider đang chạy. defaultUrl/defaultModel = endpoint+model mặc định.
  let defaultUrl, defaultModel, candidates;
  if (apiKey) {
    // Khoá tường minh (tab test / override): 1 ứng viên, không dự phòng.
    const prov = provider ? PROVIDERS[provider] : null;
    defaultUrl = baseUrl || prov?.chatUrl || PROVIDERS.vilao.chatUrl;
    defaultModel = model || prov?.textModel || VILAO_MODEL;
    candidates = [{ apiKey, url: defaultUrl, model: defaultModel }];
  } else {
    const prov = activeProvider();
    defaultUrl = prov.chatUrl;
    defaultModel = imageBase64 ? prov.visionModel : prov.textModel;
    if (defaultUrl.includes('aiplatform.googleapis.com')) {
      // Vertex: token OAuth (mint/refresh từ VERTEX_SA_KEY_JSON) — 1 ứng viên, không pool.
      candidates = [{ apiKey: await ensureVertexAccessToken(), url: defaultUrl, model: defaultModel }];
    } else {
      // Pool đổi-lúc-chạy (bảng llm_api_keys) ƯU TIÊN, rồi khoá env làm LƯỚI AN TOÀN cuối. getActiveKeyPool
      // KHÔNG BAO GIỜ throw (chưa cấu hình DB / lỗi ⇒ []) → Supabase trục trặc vẫn chạy bằng env.
      const dbPool = await getActiveKeyPool(prov.apiKeyEnv);                    // [{apiKey, url, model}]
      const envKeys = resolveApiKeyCandidates(prov.apiKeyEnv).map((k) => ({ apiKey: k, url: null, model: null }));
      const seen = new Set();
      candidates = [];
      for (const c of [...dbPool, ...envKeys]) {
        const ak = String(c.apiKey || '').trim();
        if (!ak || seen.has(ak)) continue;                                     // khử trùng theo giá trị khoá
        seen.add(ak);
        candidates.push({ apiKey: ak, url: c.url || defaultUrl, model: c.model || defaultModel });
      }
    }
    if (!candidates.length) {
      throw new Error(`Thiếu API key cho provider '${process.env.LLM_PROVIDER || 'vilao'}' (đặt ${prov.apiKeyEnv})`);
    }
  }

  const messages = [];
  if (systemPrompt) {
    messages.push({ role: 'system', content: systemPrompt });
  }

  if (imageBase64) {
    const dataUrl = imageBase64.startsWith('data:') 
      ? imageBase64 
      : "data:image/jpeg;base64," + imageBase64;
    messages.push({
      role: 'user',
      content: [
        { type: 'text', text: userPrompt },
        { type: 'image_url', image_url: { url: dataUrl } }
      ]
    });
  } else {
    messages.push({ role: 'user', content: userPrompt });
  }

  // Dựng body cho MỘT ứng viên (model + url riêng): JSON mode + reasoning_effort tuỳ endpoint.
  function buildBody(mdl, url) {
    const body = {
      model: mdl,
      messages: messages,
      max_tokens: maxTokens,
      // stream:false tường minh — model 'ts/*' Vilao mặc định SSE; parseVilaoBody vẫn gộp SSE (lưới an toàn).
      stream: false,
    };
    // Ép JSON mode khi có ảnh (transcription free-text dễ làm hỏng JSON nếu tắt).
    if ((!useReasoning || imageBase64) && mdl !== 'ox/o1-mini') {
      body.response_format = { type: 'json_object' };
    }
    // reasoning_effort CHỈ cho endpoint Google (Gemini AI Studio / Vertex). reasoningEffort per-call > env.
    const callEffort = (reasoningEffort || '').trim();
    const geminiEffort = callEffort || (process.env.GEMINI_REASONING_EFFORT ?? 'low').trim();
    if (url.includes('generativelanguage.googleapis.com') && geminiEffort && geminiEffort !== 'default') {
      body.reasoning_effort = geminiEffort;
    }
    const vertexEffort = callEffort || (process.env.VERTEX_REASONING_EFFORT || '').trim();
    if (url.includes('aiplatform.googleapis.com') && vertexEffort && vertexEffort !== 'default') {
      body.reasoning_effort = vertexEffort;
    }
    // Gateway OpenAI-compat TRUNG GIAN (khoá trong bảng llm_api_keys, vd api.xah.io) chuyển tiếp tới model
    // có "thinking": không giới hạn suy luận ⇒ bước DỊCH (system prompt ~60k ký tự) hay quá 25s ⇒
    // "Request timed out" ⇒ Mức 3 dù model mạnh (log problem_reports 10–14/9: 6/6 lỗi dịch là timeout
    // ~50s). OPT-IN qua env LLM_REASONING_EFFORT_HOSTS="api.xah.io,host2" (+ LLM_REASONING_EFFORT, mặc định
    // 'low'; reasoningEffort per-call vẫn ưu tiên). KHÔNG đặt env ⇒ body y như cũ. Chỉ gửi cho host được
    // liệt kê vì gateway lạ có thể từ chối tham số không biết.
    if (!('reasoning_effort' in body)) {
      const extraHosts = String(process.env.LLM_REASONING_EFFORT_HOSTS || '')
        .split(',').map((h) => h.trim().toLowerCase()).filter(Boolean);
      if (extraHosts.length) {
        let host = '';
        try { host = new URL(url).host.toLowerCase(); } catch { /* url lạ → bỏ qua */ }
        const extraEffort = callEffort || (process.env.LLM_REASONING_EFFORT || 'low').trim();
        if (host && extraHosts.includes(host) && extraEffort && extraEffort !== 'default') {
          body.reasoning_effort = extraEffort;
        }
      }
    }
    return body;
  }

  // Gửi 1 request bằng MỘT ứng viên (endpoint+model+khoá riêng), kèm retry nội bộ (network/5xx/empty).
  async function sendWithKey(cand, candTimeout) {
    const bodyObj = buildBody(cand.model, cand.url);
    // Kiểu auth cho host này: dùng lại kiểu đã biết chạy, mặc định 'bearer'. Sẽ tự đổi sang 'raw'
    // (key trần) nếu gateway từ chối Bearer bằng 401/403 (vd api.xah.io).
    let candHost = '';
    try { candHost = new URL(cand.url).host; } catch { /* url lạ → bỏ qua cache */ }
    let authScheme = (candHost && AUTH_SCHEME_BY_HOST.get(candHost)) || 'bearer';
    let triedRaw = authScheme === 'raw';
    let attempt = 0;
    while (attempt < maxAttempts) {
      try {
        const bodyData = JSON.stringify(bodyObj);
        const requestOptions = {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': authScheme === 'raw' ? cand.apiKey : ("Bearer " + cand.apiKey),
            'Content-Length': Buffer.byteLength(bodyData)
          }
        };

        const response = await httpsRequest(cand.url, requestOptions, bodyData, candTimeout);

        if (response.statusCode < 200 || response.statusCode >= 300) {
          let errorText = '';
          response.on('data', chunk => errorText += chunk);
          await new Promise(r => response.on('end', r));

          // Body lỗi của nhà cung cấp thường vọng lại chính khoá vừa gửi (vd 401 "Incorrect API key:
          // sk-..."). Che TRƯỚC khi ghi log Vercel và trước khi ghép vào message lỗi (message này
          // đi tiếp ra tận trình duyệt admin ở tab Test API Key), và cắt ngắn cho khỏi ngập log.
          const safeErrText = redactSecrets(errorText).slice(0, 500);
          console.error('Vilao error:', response.statusCode, safeErrText);

          // Gateway từ chối "Bearer" (401/403) → thử lại NGAY bằng key TRẦN đúng 1 lần (không tăng
          // attempt: đây là ĐỔI KIỂU AUTH, không phải retry vì flaky). Chạy được thì nhớ ở dưới.
          if ((response.statusCode === 401 || response.statusCode === 403) && authScheme === 'bearer' && !triedRaw && candHost && !isBearerOnlyHost(candHost)) {
            authScheme = 'raw';
            triedRaw = true;
            console.warn('Auth "Bearer" bị từ chối, thử key trần cho host:', candHost || '(?)');
            continue;
          }

          if ([502, 503, 504].includes(response.statusCode) && attempt < maxAttempts - 1) {
            console.warn("Vilao " + response.statusCode + ", retry attempt " + attempt);
            await sleepMs(500 * attempt);
            attempt++;
            continue;
          }

          const apiErr = new Error("Vilao API error: " + response.statusCode + " " + safeErrText);
          apiErr.statusCode = response.statusCode;   // để isKeyError phân biệt lỗi khoá (401/403/429)
          throw apiErr;
        }

        // Status 2xx = kiểu auth này ĐƯỢC chấp nhận → nhớ cho host để lần sau đi thẳng.
        if (candHost) AUTH_SCHEME_BY_HOST.set(candHost, authScheme);

        let dataText = '';
        for await (const chunk of response) {
          const text = chunk.toString();
          dataText += text;
          if (onStream) {
            onStream(text);
          }
        }

        let data;
        try {
          data = parseVilaoBody(dataText);
        } catch (e) {
          throw new Error("Failed to parse Vilao response: " + redactSecrets(dataText.substring(0, 100)));
        }

        if (isEmptyVilaoContent(data)) {
          // Content rỗng/thiếu = lỗi TẠM ⇒ retry giống 5xx (đừng fail thẳng thành "Lỗi vẽ hình").
          if (attempt < maxAttempts - 1) {
            console.warn("Vilao empty content, retry attempt " + attempt);
            await sleepMs(500 * attempt);
            attempt++;
            continue;
          }
          throw new Error('Vilao returned empty content');
        }
        if (returnRaw) {
          return { content: data.choices[0].message.content, usage: data.usage || null, model: cand.model };
        }
        return data.choices[0].message.content;

      } catch (err) {
        if (isNetworkError(err) && attempt < maxAttempts - 1) {
          console.warn("Vilao network error: " + redactSecrets(err.message) + ", retry attempt " + attempt);
          await sleepMs(1000 * attempt);
          attempt++;
          continue;
        }
        throw err;
      }
    }
    throw new Error('Vilao failed after maximum retries');
  }

  // Thử lần lượt các ứng viên. Chọn ứng viên KẾ theo LOẠI lỗi:
  //   • lỗi KHOÁ (401/403/429): thử NGAY khoá kế (có thể chỉ mình khoá đó hỏng — kể cả cùng endpoint+model).
  //   • timeout/mạng/5xx: nhảy sang ứng viên có ĐÍCH KHÁC (khác endpoint HOẶC khác model) — cùng nhà cung
  //     cấp nhưng khác model (vd mn/ag/gemini-3.6-flash-high ↔ anxs/gemini-3.7-flash-high) vẫn đáng thử vì
  //     model kia có thể đang khoẻ. Bỏ qua ứng viên TRÙNG HỆT đích (cùng endpoint + model → vô ích).
  // Ngân sách CẢ vòng ≤ ~52s (chừa lằn maxDuration 60s của Vercel) để không bao giờ 504 vì thử quá nhiều.
  const targetSig = (c) => `${c.url}|${c.model}`;   // "đích" = endpoint + model
  const OVERALL_CAP_MS = Math.min(52000, Math.max(timeoutMs, (timeoutMs || 0) + 22000));
  const MIN_ATTEMPT_MS = 6000;
  const startAll = Date.now();
  let lastError = null;
  let ki = 0;
  while (ki >= 0 && ki < candidates.length) {
    const cand = candidates[ki];
    const remaining = OVERALL_CAP_MS - (Date.now() - startAll);
    if (ki > 0 && remaining < MIN_ATTEMPT_MS) break;                 // hết ngân sách cho ứng viên sau
    const candTimeout = ki === 0 ? timeoutMs : Math.min(timeoutMs, remaining);
    try {
      return await sendWithKey(cand, candTimeout);
    } catch (err) {
      lastError = err;
      const nextKi = isKeyError(err)
        ? ki + 1                                                     // lỗi khoá → khoá kế (bất kể đích)
        : candidates.findIndex((c, idx) => idx > ki && targetSig(c) !== targetSig(cand));  // khác đích
      if (nextKi < 0 || nextKi >= candidates.length) throw err;
      console.warn(`[llm] ứng viên #${ki + 1} lỗi (${redactSecrets(err?.message || String(err))}) → thử #${nextKi + 1}${isKeyError(err) ? ' (lỗi khoá)' : ' (đổi endpoint/model)'}`);
      ki = nextKi;
    }
  }
  throw lastError || new Error('Vilao failed after maximum retries');
}

// HEDGE TRỄ: chạy fn() một lần; nếu sau delayMs vẫn chưa xong thì bắn THÊM 1 lượt song song,
// lấy KẾT QUẢ hợp lệ VỀ TRƯỚC (Promise.any). Trị "spike" độ trễ ngẫu nhiên của model: đa số
// lượt ~5s xong trước delayMs → KHÔNG tốn thêm; chỉ khi spike mới gọi lượt 2 (spike độc lập
// từng lượt nên lượt 2 gần như luôn nhanh) ⇒ đuôi độ trễ bị cắt mà không phải chờ hết timeout.
// Chỉ ném khi CẢ HAI lượt đều hỏng.
export async function hedge(fn, { delayMs = 6000 } = {}) {
  const swallow = (p) => { p.catch(() => {}); return p; };   // chặn unhandledRejection của lượt thua
  const first = swallow(fn());
  const HEDGE = Symbol('hedge');
  const timer = new Promise((res) => setTimeout(() => res(HEDGE), delayMs));

  // Đợi: first xong (ok/lỗi) HOẶC chạm mốc delayMs.
  const winner = await Promise.race([
    first.then((v) => ({ ok: true, v }), (e) => ({ ok: false, e })),
    timer,
  ]);

  if (winner !== HEDGE) {
    if (winner.ok) return winner.v;         // first xong sớm, thành công
    return await swallow(fn());             // first lỗi sớm → thử lại ngay (1 lượt)
  }

  // first còn chậm (spike) → bắn lượt 2 song song, lấy cái nào THÀNH CÔNG trước.
  const second = swallow(fn());
  return await Promise.any([first, second]);   // reject (AggregateError) chỉ khi cả hai đều hỏng
}
