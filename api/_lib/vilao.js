import https from 'https';
import { ensureVertexAccessToken } from './vertexAuth.js';

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
    textModel:   process.env.VILAO_MODEL || 'ram/gemini-3.5-flash-low',
    visionModel: process.env.VILAO_MODEL || 'ram/gemini-3.5-flash-low',
  },
};

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

export function resolveApiKey(options = {}, envKey = process.env.VILAO_API_KEY) {
  const key = options.apiKey || envKey;
  if (!key) throw new Error('Vilao API key is not set (opts.apiKey or VILAO_API_KEY)');
  return key;
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
  } = options;

  // Chọn endpoint + khoá + model theo NGỮ CẢNH:
  //  • CÓ options.apiKey (admin test khoá Vilao, hoặc override ADVANCE/DETAILED): đi ĐÚNG endpoint Vilao
  //    với khoá + model được truyền — giữ nguyên hành vi cũ của các tính năng đó.
  //  • KHÔNG có: dùng provider ĐANG hoạt động (mặc định Gemini chính hãng) — endpoint + khoá env + model
  //    của provider. Tên model format Vilao mà caller truyền (translator…) BỎ QUA, vì mỗi provider đặt tên
  //    khác nhau và cả app chỉ có MỘT model logic ("flash rẻ"); đổi model theo provider qua GEMINI_MODEL /
  //    GEMINI_VISION_MODEL (hoặc VILAO_MODEL). `aiModel`/`useReasoning` không còn đổi model (giữ tham số cho
  //    tương thích; `useReasoning` vẫn chỉ tác động cờ JSON mode bên dưới).
  let chatUrl, currentApiKey, modelToUse;
  if (apiKey) {
    const prov = provider ? PROVIDERS[provider] : null;
    chatUrl = baseUrl || prov?.chatUrl || PROVIDERS.vilao.chatUrl;   // mặc định Vilao (giữ hành vi cũ)
    currentApiKey = apiKey;
    modelToUse = model || prov?.textModel || VILAO_MODEL;
  } else {
    const prov = activeProvider();
    chatUrl = prov.chatUrl;
    if (chatUrl.includes('aiplatform.googleapis.com')) {
      // Vertex: token OAuth sống ~60' — mint/refresh từ khoá SA (VERTEX_SA_KEY_JSON) theo tiến trình.
      currentApiKey = await ensureVertexAccessToken();
    } else {
      currentApiKey = process.env[prov.apiKeyEnv];
    }
    if (!currentApiKey) {
      throw new Error(`Thiếu API key cho provider '${process.env.LLM_PROVIDER || 'vilao'}' (đặt ${prov.apiKeyEnv})`);
    }
    modelToUse = imageBase64 ? prov.visionModel : prov.textModel;
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

  const bodyObj = {
    model: modelToUse,
    messages: messages,
    max_tokens: maxTokens,
  };

  // Ép JSON mode khi có ảnh (kể cả useReasoning): output ảnh luôn là JSON, và nếu tắt JSON mode
  // thì phần transcription đề bài (free-text nhiều dòng) dễ chứa ký tự chưa escape làm hỏng cả JSON.
  // useReasoning ở đây chỉ đổi cờ này chứ không đổi model, nên bật lại an toàn.
  if ((!useReasoning || imageBase64) && modelToUse !== 'ox/o1-mini') {
    bodyObj.response_format = { type: 'json_object' };
  }

  // GIỚI HẠN suy luận cho Gemini: Flash bật "thinking" động (ngốn tới ~24K token nghĩ ⇒ chậm/timeout).
  // reasoning_effort: 'low'~1K, 'medium'~8K, 'high'~24K, 'none' tắt hẳn. Mặc định 'low' cho nhanh mà vẫn
  // đủ suy luận cho hình học; đổi qua GEMINI_REASONING_EFFORT ('none' rẻ/nhanh nhất, 'high' kỹ hơn).
  // CHỈ áp cho endpoint Gemini — provider khác (Vilao) không hiểu tham số này. 'default' = để model tự quyết.
  const geminiEffort = (process.env.GEMINI_REASONING_EFFORT ?? 'low').trim();
  if (chatUrl.includes('generativelanguage.googleapis.com') && geminiEffort && geminiEffort !== 'default') {
    bodyObj.reasoning_effort = geminiEffort;
  }
  // Vertex (aiplatform) OpenAI-compat cũng nhận reasoning_effort cho Gemini 2.5+, NHƯNG mặc định TẮT
  // (chỉ gửi khi VERTEX_REASONING_EFFORT được đặt) để tránh rủi ro endpoint từ chối tham số khi chưa xác
  // nhận. Đặt VERTEX_REASONING_EFFORT=low để khớp 'flash-low' của Vilao khi so sánh.
  const vertexEffort = (process.env.VERTEX_REASONING_EFFORT || '').trim();
  if (chatUrl.includes('aiplatform.googleapis.com') && vertexEffort && vertexEffort !== 'default') {
    bodyObj.reasoning_effort = vertexEffort;
  }

  let attempt = 0;

  while (attempt < maxAttempts) {
    try {
      const bodyData = JSON.stringify(bodyObj);
      const requestOptions = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': "Bearer " + currentApiKey,
          'Content-Length': Buffer.byteLength(bodyData)
        }
      };

      const response = await httpsRequest(chatUrl, requestOptions, bodyData, timeoutMs);

      if (response.statusCode < 200 || response.statusCode >= 300) {
        let errorText = '';
        response.on('data', chunk => errorText += chunk);
        await new Promise(r => response.on('end', r));

        console.error('Vilao error:', response.statusCode, errorText);

        if ([502, 503, 504].includes(response.statusCode) && attempt < maxAttempts - 1) {
          console.warn("Vilao " + response.statusCode + ", retry attempt " + attempt);
          await sleepMs(500 * attempt);
          attempt++;
          continue;
        }

        throw new Error("Vilao API error: " + response.statusCode + " " + errorText);
      }

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
        data = JSON.parse(dataText);
      } catch (e) {
        throw new Error("Failed to parse Vilao response: " + dataText.substring(0, 100));
      }

      if (isEmptyVilaoContent(data)) {
        // Content rỗng/thiếu = lỗi TẠM ⇒ retry giống 5xx (đừng fail thẳng thành "Lỗi vẽ hình").
        // maxAttempts=1 (caller đã hedge) ⇒ 0<0 sai ⇒ ném ngay, để hedge/caller lo — không chồng retry.
        if (attempt < maxAttempts - 1) {
          console.warn("Vilao empty content, retry attempt " + attempt);
          await sleepMs(500 * attempt);
          attempt++;
          continue;
        }
        throw new Error('Vilao returned empty content');
      }
      if (returnRaw) {
        return { content: data.choices[0].message.content, usage: data.usage || null, model: modelToUse };
      }
      return data.choices[0].message.content;

    } catch (err) {
      if (isNetworkError(err) && attempt < maxAttempts - 1) {
        console.warn("Vilao network error: " + err.message + ", retry attempt " + attempt);
        await sleepMs(1000 * attempt);
        attempt++;
        continue;
      }
      throw err;
    }
  }

  throw new Error('Vilao failed after maximum retries');
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
