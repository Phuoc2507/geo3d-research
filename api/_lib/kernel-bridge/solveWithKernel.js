// api/_lib/kernel-bridge/solveWithKernel.js
// Đường ống "kernel mode": đề → (LLM Translator) → Plan JSON → engine.run() → hình + đáp số.
// Import engine từ bản đã build (esbuild) để chạy được trong route .js thuần.
import { runAny, RunPlanSchema, AnalysisPlanSchema, entityTableToGeometryData } from '../kernel-dist/index.mjs';
import { callVilao } from '../vilao.js';
import { TRANSLATOR_PROMPT } from './translatorPrompt.js';
import { answersAgree } from '../answerCompare.js';
import { classifyTier, tierFromThrow } from './classifyTier.js';
import { isProvePlan, validateProvePlan, solveProofPlan } from './solveProof.js';

// Gỡ hàng rào ```json nếu model lỡ thêm dù đã dặn.
function extractJson(raw) {
  return String(raw).trim().replace(/^```(?:json)?/i, '').replace(/```$/i, '').trim();
}

// Model hay viết LaTeX ('\\sqrt', '\\pi') TRONG chuỗi JSON với MỘT gạch chéo ⇒ escape không hợp lệ
// ⇒ JSON.parse ném dù nội dung hoàn toàn đúng. Vá HÌNH THỨC: nhân đôi gạch chéo lẻ (không đứng trước
// một ký tự escape hợp lệ) rồi thử lại. Không đổi nghĩa dữ liệu — chỉ cứu lỗi cú pháp thuần hình thức.
export function parseJsonLoose(text) {
  try { return JSON.parse(text); } catch (e) {
    const patched = String(text).replace(/\\(?!["\\/bfnrtu])/g, '\\\\');
    return JSON.parse(patched); // vẫn hỏng ⇒ ném như cũ
  }
}

// Chuẩn hoá plan TẤT ĐỊNH trước khi validate — sửa vài khác biệt HÌNH THỨC mà model hay mắc
// (cùng ý nghĩa, khác cách viết), KHÔNG đoán/không bịa dữ kiện. Áp cho MỌI model → giảm "lỗi dịch"
// mà không phải nuôi prompt riêng từng model. Chỉ NỚI cho qua các biến thể tương đương; plan sai
// thật vẫn hỏng (queries tham chiếu thực thể không có ⇒ engine ném như cũ).
function normalizePlan(json) {
  if (!json || typeof json !== 'object' || 'analyze' in json) return json; // chỉ RunPlan
  // 1) Bài công thức (nón/trụ/cầu/chóp cụt…) không cần dựng hình → model hay để ops rỗng/thiếu.
  //    Schema đòi ops ≥ 1 (plan vàng nhét 1 điểm giả). Ta tự nhét điểm giả nếu thiếu.
  //    QUAN TRỌNG: tên điểm PHẢI khớp PointNameStrict = /^[A-Z]\d*'?$/ (chữ HOA + số). Trước đây
  //    nhét '__O' (gạch dưới) ⇒ chính điểm giả này FAIL schema ⇒ MỌI bài công thức ops-rỗng rớt
  //    schema lượt đầu. Dùng 'O0' (hợp lệ, gần như không trùng tên điểm nào của đề).
  if (!Array.isArray(json.ops) || json.ops.length === 0) {
    json.ops = [{ op: 'oxyz_point', name: 'O0', at: [0, 0, 0] }];
  }
  if (typeof json.solidName !== 'string' || !json.solidName) json.solidName = 'figure';
  // 2) point_dir.base phải là TOẠ ĐỘ [x,y,z]; model hay ghi TÊN điểm đã dựng → thay bằng toạ độ của nó.
  const ptAt = {};
  for (const op of json.ops) if (op && op.op === 'oxyz_point' && op.name && Array.isArray(op.at)) ptAt[op.name] = op.at;
  for (const op of json.ops) {
    const by = op && op.by;
    if (by && by.form === 'point_dir' && typeof by.base === 'string' && ptAt[by.base]) by.base = ptAt[by.base];
  }
  return json;
}

// Đề tiếng Việt → Plan JSON hợp lệ (đã validate bằng schema của engine).
// Model dịch có thể đổi qua env VILAO_TRANSLATOR_MODEL; mặc định gemini-flash (nhanh/rẻ).
const TRANSLATOR_MODEL = process.env.VILAO_TRANSLATOR_MODEL || 'ts/gemini-3.1-flash-lite';

// Timeout MẶC ĐỊNH cho bước dịch. Đo thực tế: 5–10s/đề (cả gemini lẫn claude). Đặt 25s = thừa đệm.
// KHÔNG dùng mặc định 180s của callVilao: khi engine là bước THỬ TRƯỚC rồi mới rơi về luồng cũ,
// một lần LLM treo sẽ bắt người dùng chờ 3 phút trước khi luồng cũ mới bắt đầu.
const TRANSLATE_TIMEOUT_MS = Number(process.env.VILAO_TRANSLATOR_TIMEOUT_MS) || 25000;

export async function planFromProblem(problem, options = {}) {
  // `options.systemPrompt` cho phép caller (vd bộ tối ưu prompt tiến hoá) thử một prompt ỨNG VIÊN
  // khác mà KHÔNG đụng đường sản xuất. Mặc định giữ nguyên TRANSLATOR_PROMPT ⇒ hành vi cũ không đổi.
  const systemPrompt = options.systemPrompt || TRANSLATOR_PROMPT;
  // VÒNG LẶP SỬA LỖI (engine-guided repair): khi lần dịch trước cho plan HỎNG, caller đưa lại
  // `options.repairHint` (lỗi cụ thể + plan hỏng). Ghép vào đề để LLM PHÂN TÍCH lỗi & dịch lại đúng.
  // Không có hint ⇒ userText === problem ⇒ hành vi cũ không đổi.
  const userText = options.repairHint ? (problem + '\n\n' + options.repairHint) : problem;
  // NGÂN SÁCH TOKEN cho lượt dịch. Các mô hình đời mới có "suy nghĩ" (thinking) tính CHUNG vào
  // max_tokens: với trần 4096, phần suy nghĩ ăn gần hết ngân sách nên plan JSON bị CẮT GIỮA CHỪNG
  // ⇒ "Translator returned non-JSON output" (đo được trên đề thật: ~8/116 câu). Vì vậy các provider
  // có thinking (vertex/gemini) dùng trần rộng hơn; provider cũ giữ 4096 (đường sản xuất không đổi).
  // Trần chỉ là GIỚI HẠN — chi phí vẫn tính theo token thực sinh ra.
  const thinkingProvider = options.provider === 'vertex' || options.provider === 'gemini';
  const maxTokens = options.maxTokens ?? (thinkingProvider ? 16384 : 4096);
  // Chọn nhà cung cấp LLM cho khâu DỊCH. Mặc định Vilao (đường sản xuất không đổi).
  // options.provider === 'gemini' → dùng Gemini chính hãng (cho eval so sánh đa mô hình, chạy trên máy).
  let raw;
  if (options.provider === 'vertex') {
    const { callVertex } = await import('../vertex.js');
    raw = await callVertex(systemPrompt, userText, {
      model: options.model || process.env.VERTEX_MODEL || null,
      maxTokens,
      timeoutMs: options.timeoutMs ?? TRANSLATE_TIMEOUT_MS,
      json: true,
      // temperature chỉ truyền khi caller đặt (vd eval đặt 0 cho tất định); undefined ⇒ prod không đổi.
      temperature: options.temperature,
    });
  } else if (options.provider === 'openai') {
    const { callOpenAICompat } = await import('../openaiCompat.js');
    raw = await callOpenAICompat(systemPrompt, userText, {
      model: options.model || process.env.OAI_MODEL || null,
      maxTokens,
      timeoutMs: options.timeoutMs ?? TRANSLATE_TIMEOUT_MS,
      apiKey: options.apiKey || null,
      json: true,
      reasoningEffort: options.reasoningEffort || null, // dò thử giới hạn thinking qua gateway (scripts/eval/do-bo-dich.mjs)
    });
  } else if (options.provider === 'gemini') {
    const { callGemini } = await import('../gemini.js');
    raw = await callGemini(systemPrompt, userText, {
      model: options.model || process.env.GEMINI_TRANSLATOR_MODEL || null,
      maxTokens,
      timeoutMs: options.timeoutMs ?? TRANSLATE_TIMEOUT_MS,
      apiKey: options.apiKey || null,
      json: true,
    });
  } else {
    raw = await callVilao(systemPrompt, userText, {
      model: options.model || TRANSLATOR_MODEL,
      maxTokens,
      timeoutMs: options.timeoutMs ?? TRANSLATE_TIMEOUT_MS,
      apiKey: options.apiKey || null,
    });
  }
  let json;
  try {
    json = parseJsonLoose(extractJson(raw));
  } catch {
    throw Object.assign(new Error('Translator returned non-JSON output'), { raw });
  }
  // Bộ dịch TỰ KHƯỚC TỪ khi đề thiếu số liệu / ngoài danh mục (chống "phục vụ sai"). Ném ⇒ route
  // rơi về luồng LLM cũ, thay vì để engine trả đáp tự tin cho một bài không nên trả.
  if (json && typeof json === 'object' && json.abstain === true) {
    // Khước từ CÓ CHỦ Ý (thiếu số liệu/ngoài danh mục): đánh dấu `abstained` để vòng lặp KHÔNG sửa
    // (đây là từ chối hợp lệ, không phải plan hỏng).
    throw Object.assign(new Error('translator abstained: ' + (json.abstain_reason || 'thiếu số liệu / ngoài danh mục')), { abstained: true });
  }
  // Plan CHỨNG MINH (mode:'prove'): validate riêng, trả thẳng — solvePlan sẽ định tuyến sang proveGeneral.
  if (isProvePlan(json)) {
    return validateProvePlan(json);
  }
  // Sửa các khác biệt hình thức tất định (ops rỗng, base là tên điểm…) trước khi validate.
  json = normalizePlan(json);
  // Plan có khối `analyze` (bài tham số/tối ưu/hàm số) dùng schema analysis; còn lại là plan hình học thuần.
  const schema = json && typeof json === 'object' && 'analyze' in json ? AnalysisPlanSchema : RunPlanSchema;
  const parsed = schema.safeParse(json);
  if (!parsed.success) {
    // Đính lỗi schema CHI TIẾT (tối đa 3 vấn đề, kèm đường dẫn field) + plan hỏng ⇒ vòng lặp đưa lại
    // cho LLM tự sửa. Zod issues cho biết field nào sai ⇒ hint hữu ích hơn nhiều "invalid".
    const issues = parsed.error.issues.slice(0, 3).map((i) => `${(i.path || []).join('.') || '(gốc)'}: ${i.message}`).join(' | ');
    throw Object.assign(new Error('Translator plan failed schema: ' + (issues || 'invalid')), { raw, plan: json });
  }
  // "scaleSymbol" (thang CHỮ): bài ĐO TUYỆT ĐỐI trên hình RẮN-tới-đồng-dạng, kích thước cho bằng một
  // chữ duy nhất (vd cạnh 'a'). Engine toạ-độ-hoá tại a=1 rồi solvePlan ghép ×a^k vào đáp. Schema
  // KHÔNG khai trường này nên safeParse loại bỏ ⇒ giữ lại từ json gốc. Chỉ nhận MỘT chữ cái.
  if (typeof json.scaleSymbol === 'string' && /^[a-zA-Z]$/.test(json.scaleSymbol)) {
    parsed.data.scaleSymbol = json.scaleSymbol;
  }
  return parsed.data;
}

// Soạn lời nhắc SỬA LỖI đưa lại cho LLM: lỗi engine phản hồi + plan hỏng lần trước.
function repairHintText(err, badPlan) {
  return [
    '════ SỬA LỖI (engine phản hồi) ════',
    'Plan bạn tạo LẦN TRƯỚC bị lỗi khi chạy engine:',
    '  » ' + err,
    'Plan lỗi đó:',
    badPlan,
    'Hãy PHÂN TÍCH nguyên nhân rồi tạo LẠI plan JSON HỢP LỆ: đúng schema, dựng đủ điểm/mặt, đặt query',
    'đúng đại lượng đề hỏi (thể tích/diện tích/khoảng cách/góc/toạ độ/mặt cầu…).',
    'CHỈ khi đề THỰC SỰ thiếu dữ kiện mới trả {"abstain":true,"abstain_reason":"..."}.',
  ].join('\n');
}

// VÒNG LẶP SỬA LỖI (engine-guided repair) — cảm hứng AlphaGeometry. Dịch → chạy engine → nếu HỎNG
// (sai schema / non-JSON / engine không ra đáp) thì đưa LỖI CỤ THỂ + plan hỏng lại cho LLM để nó
// phân tích & dịch lại, thử tối đa `maxRepairs` lần. Khước từ CÓ CHỦ Ý (abstained) thì DỪNG, không sửa.
// Trả { plan, result, repairs } khi ra đáp; NÉM lỗi cuối (mang .abstained nếu là từ chối) khi cạn lượt.
export async function planWithRepair(problem, options = {}, maxRepairs = 2) {
  let hint = null, lastErr = 'unknown';
  for (let attempt = 0; attempt <= maxRepairs; attempt++) {
    let plan;
    try {
      plan = await planFromProblem(problem, hint ? { ...options, repairHint: hint } : options);
    } catch (e) {
      if (e && e.abstained) throw e;                       // từ chối hợp lệ ⇒ không sửa
      lastErr = String(e && e.message || e);
      const bad = e && e.plan ? JSON.stringify(e.plan) : (e && e.raw ? String(e.raw).slice(0, 1200) : '(không đọc được)');
      hint = repairHintText(lastErr, bad);
      continue;                                            // dịch lại với hint
    }
    let result;
    try {
      result = solvePlan(plan);
    } catch (e) {
      lastErr = 'engine ném khi lắp ráp: ' + String(e && e.message || e);
      hint = repairHintText(lastErr, JSON.stringify(plan));
      continue;
    }
    if (result && result.ok && Array.isArray(result.answers) && result.answers.length) {
      return { plan, result, repairs: attempt };           // ✓ ra đáp
    }
    // Engine chạy nhưng KHÔNG ra đáp (vi phạm/không giải được) ⇒ thử sửa tiếp.
    lastErr = String((result && (result.errors?.[0]?.message || result.violations?.[0])) || 'engine không ra đáp');
    hint = repairHintText(lastErr, JSON.stringify(plan));
  }
  throw new Error(`repair exhausted (${maxRepairs} lần): ${lastErr}`); // cạn lượt ⇒ caller xử như TỪ CHỐI
}

// Chạy một Plan qua engine → gói kết quả để frontend dùng.
// Đáp số exact của engine mang BigInt (num/den của phân số chính xác). JSON.stringify NÉM khi gặp
// BigInt ⇒ res.json() của route sẽ chết. Chuyển BigInt → chuỗi để mọi consumer serialize được.
// (Giá trị exact vẫn đọc được ở .text dạng '√2'; đây chỉ là làm cho JSON an toàn.)
function jsonSafe(v) {
  if (typeof v === 'bigint') return v.toString();
  if (Array.isArray(v)) return v.map(jsonSafe);
  if (v && typeof v === 'object') {
    const out = {};
    for (const [k, val] of Object.entries(v)) out[k] = jsonSafe(val);
    return out;
  }
  return v;
}

// Chú thích THANG CHỮ cho đáp đo tuyệt đối trên hình xác-định-tới-đồng-dạng (vd cạnh 'a').
// Engine tính tại a=1 ⇒ đáp exact chính xác bằng (số thuần)·a^k. Ghép ×a^k vào .text để KHÔNG
// hiển thị số trần gây hiểu nhầm là số tuyệt đối. k: khoảng-cách/độ-dài=1, diện-tích=2, thể-tích=3.
// GÓC và TỈ SỐ bất biến theo cỡ (k=0) ⇒ KHÔNG có trong bảng ⇒ giữ nguyên, không ghép.
// sphere_metric CHỈ trả ĐỘ DÀI (bán kính/đường kính/toạ-độ-z đỉnh–đáy — xem query.ts `what`),
// nên thang chữ nhân ×a¹ giống distance. Trước đây thiếu ⇒ engine RỚT chữ 'a' ở bài mặt cầu thang chữ
// (vd bán kính mặt cầu ngoại tiếp = 25a/8 bị trả thành 25/8). Diện tích/thể tích mặt cầu KHÔNG đi
// qua đây (chúng là kind 'area'/'volume', đã có sẵn số mũ 2/3).
// slant (đường sinh nón/nón cụt) và point_coord (toạ độ 1 điểm) là ĐỘ DÀI ⇒ thang chữ ×a¹ như distance.
// Trước đây thiếu ⇒ bài thang chữ hỏi đường sinh/toạ độ bị RỚT chữ 'a' (vd đường sinh = 3a bị trả 3).
// 'ratio' KHÔNG có ở đây vì tỉ số VÔ HƯỚNG (bất biến theo cỡ) — đúng, không được nhân thang.
const SCALE_EXP = { distance: 1, length: 1, slant: 1, point_coord: 1, area: 2, volume: 3, sphere_metric: 1 };
function scaleText(text, sym, k) {
  const t = String(text).trim();
  const s = k === 1 ? sym : `${sym}${k === 2 ? '²' : k === 3 ? '³' : '^' + k}`;
  if (t === '1') return s;                          // a·1 → a
  if (/^\d+(?:\.\d+)?$/.test(t)) return `${t}${s}`; // 2 → 2a ; 13 → 13a
  return `${s}·${t}`;                               // √3/3 → a·√3/3
}
export function applyScaleSymbol(answers, sym) {
  if (!sym || !Array.isArray(answers)) return answers;
  return answers.map((a) => {
    const k = SCALE_EXP[a && a.kind];
    if (!k || a.text == null) return a;
    const t = String(a.text).trim();
    if (t === '' || t === '0' || a.approx === 0) return a; // đáp 0 (vd thẳng hàng ⇒ area 0): không ghép
    // approx là giá trị tại a=1, sẽ gây hiểu nhầm nếu hiện dạng thập phân trần ⇒ bỏ khỏi `approx`.
    // Nhưng GIỮ nó ở `approxAtScale`: đó là số ĐO ĐƯỢC TRÊN HÌNH đang vẽ (thang a=1) — dữ liệu
    // hợp lệ của Mức 2, UI hiện kèm nhãn "ở hình này" (gated bởi pref showIllustrationValues).
    return {
      ...a,
      text: scaleText(a.text, sym, k),
      approx: null,
      approxAtScale: typeof a.approx === 'number' && Number.isFinite(a.approx) ? a.approx : null,
      scaleSymbol: sym,
      scaleExp: k,
    };
  });
}

export function solvePlan(plan) {
  // Plan chứng minh đi đường riêng (proveGeneral) — tách hẳn khỏi đường số, không đụng hành vi cũ.
  if (isProvePlan(plan)) return solveProofPlan(plan);
  const result = runAny(plan);
  // Nhánh analysis: runAnalysis trả { parameter, answer } và KHÔNG có entities ⇒ chưa dựng được hình.
  if (!('entities' in result)) {
    // Nhánh analysis: runAnalysis nay trả THÊM hình dựng tại nghiệm (optimize/solve có op hình học)
    // ⇒ route vẽ hiện được cả hình lẫn đáp số. Gắn `kind` để calculation_log của route định dạng gọn.
    //
    // THANG CHỮ Ở NHÁNH NÀY: trước đây nhánh analysis thoát ra TRƯỚC bước ghép ×a^k, nên bài
    // "V = 36a³, B = 4a² ⇒ h = ?" trả về "9" thay vì "9a" — một đáp SAI mà vẫn mang dấu đã kiểm.
    // Nay: có answerKind ⇒ ghép đúng số mũ; KHÔNG có ⇒ không đoán, đánh dấu đáp chưa chứng nhận
    // để hệ TỪ CHỐI (thà im còn hơn trả số thiếu chữ).
    const rawAnswers = result.ok ? [{ kind: plan.analyze && plan.answerKind ? plan.answerKind : 'kết quả', ...result.answer }] : [];
    let aAnswers = applyScaleSymbol(rawAnswers, plan.scaleSymbol);
    if (plan.scaleSymbol && !plan.answerKind) {
      aAnswers = aAnswers.map((a) => ({ ...a, approximate: true, unscaled: true }));
    }
    return jsonSafe({
      ok: result.ok,
      representative: Array.isArray(aAnswers) && aAnswers.some((a) => a && a.scaleSymbol),
      geometry: result.geometry ?? null,
      parameter: result.parameter,
      answers: aAnswers,
      violations: result.violations,
      errors: result.errors,
    });
  }
  const answers = applyScaleSymbol(result.answers, plan.scaleSymbol); // ghép ×a^k nếu là bài THANG CHỮ
  // MỨC 2 — "minh hoạ đại diện". Bài THANG CHỮ chỉ xác định TỚI ĐỒNG DẠNG: engine buộc phải chọn
  // MỘT thang cụ thể (a=1) để dựng được hình. Đáp CHỮ (vd 'a·√3/3') vẫn đúng TỔNG QUÁT, nhưng mọi
  // số ĐO TRÊN HÌNH đang vẽ chỉ đúng ở đúng thang đó ⇒ không được khẳng định như số tuyệt đối.
  // Cờ này là thứ classifyTier đọc để trả level 2 (trước nay chưa ai đặt ⇒ nhánh Mức 2 nằm chết).
  const representative = Array.isArray(answers) && answers.some((a) => a && a.scaleSymbol);
  return jsonSafe({
    ok: result.ok,
    representative,
    geometry: entityTableToGeometryData(result.entities, plan.solidName || 'figure'),
    answers,
    violations: result.violations,
    errors: result.errors,
    trace: result.trace,
  });
}

export async function solveProblem(problem, options = {}) {
  // Khước từ dịch (abstain / non-JSON / sai schema) TRẢ object Mức-3 có tier, thay vì để exception
  // nổ. Route caller vẫn rơi về LLM fallback — nay có `tier` để render lời giải thích trung thực.
  let plan;
  try {
    plan = await planFromProblem(problem, options);
  } catch (e) {
    return {
      plan: null, ok: false, geometry: null, answers: [], violations: [],
      errors: [{ message: e && e.message ? e.message : 'lỗi dịch' }],
      tier: tierFromThrow(e),
    };
  }

  const result = { plan, ...solvePlan(plan) };
  result.tier = classifyTier(result); // MỘT nguồn sự thật; draw/solve thừa hưởng object này.

  // A1 — ĐỐI CHIẾU 2 ĐƯỜNG: dịch đề LẦN 2 độc lập rồi so đáp số. Lệch ⇒ hạ "chưa kiểm chứng"
  // (chống "đã kiểm chứng nhưng sai" do AI dịch sai nhất quán). Chỉ chạy khi engine ĐÃ giải (L1)
  // nên chỉ tốn thêm 1 lượt DỊCH (rẻ) đúng ở chỗ cần chắc chắn. Tắt bằng env KERNEL_CROSSCHECK='off'.
  // Bài CHỨNG MINH không có `approx` để so ⇒ bỏ qua (tránh tốn thêm một lượt dịch vô ích).
  if (String(process.env.KERNEL_CROSSCHECK || 'on').trim() !== 'off' && result.ok && result.answers?.length && !result.proof) {
    try {
      const r2 = solvePlan(await planFromProblem(problem, options));
      const a1text = result.answers[0]?.text;
      const a2num = r2.answers?.[0]?.approx;
      const agree = a2num != null && Number.isFinite(a2num) ? answersAgree(a1text, a2num, 1e-3) : null;
      if (agree === false) {
        const disagreed = {
          ...result, ok: false, crossCheck: 'disagree',
          errors: [...(result.errors || []), { message: `cross-check lệch: "${a1text}" vs "${r2.answers?.[0]?.text}"` }],
        };
        disagreed.tier = classifyTier(disagreed); // ok flip false ⇒ tier phải tính lại (không stale).
        return disagreed;
      }
      result.crossCheck = agree === true ? 'agree' : 'unverified';
    } catch { /* lỗi khi đối chiếu ⇒ giữ kết quả gốc, không chặn */ }
  }
  return result;
}
