// scripts/eval/methods.mjs
// Hai "phương pháp" để so sánh trên cùng một tập đề. Mỗi phương pháp trả kết quả CHUẨN HOÁ:
//   { status: 'answer' | 'abstain' | 'error', answers: [{kind?,text}], ms, note? }
//
//  • 'system'     — HỆ NEURO-SYMBOLIC của đề tài: LLM dịch → engine tính + tự kiểm. Từ chối an toàn
//                   khi thiếu dữ kiện (abstain) thay vì bịa.
//  • 'llm-direct' — BASELINE: để LLM GIẢI THẲNG và tự đưa đáp số (không engine, không tự kiểm).
//
// Cờ mock=true cho phép chạy OFFLINE để kiểm thử harness (không gọi LLM, không tốn tiền):
//  system-mock dùng plan golden có sẵn; llm-direct-mock giả lập tất định (một phần đúng, một phần
//  "confidently wrong", một phần từ chối) để bảng chỉ số có ý nghĩa.
import crypto from 'node:crypto';
import { solvePlan } from '../../api/_lib/kernel-bridge/solveWithKernel.js';

const DIRECT_PROMPT =
  'Bạn là trợ giảng giải toán HÌNH HỌC KHÔNG GIAN. Hãy GIẢI bài và chỉ trả về JSON:\n' +
  '{"answers":["<đáp số gọn, vd 64/3 hoặc 2√2/3 hoặc số>"]}  (một phần tử cho mỗi câu hỏi, đúng thứ tự);\n' +
  'hoặc {"abstain":true} nếu đề THIẾU dữ kiện để ra đáp số. Không kèm lời giải, không rào ```.';

const hnum = (s) => parseInt(crypto.createHash('sha1').update(String(s)).digest('hex').slice(0, 8), 16);
const extractJson = (raw) => String(raw).trim().replace(/^```(?:json)?/i, '').replace(/```$/i, '').trim();
const { parseJsonLoose } = await import('../../api/_lib/kernel-bridge/solveWithKernel.js');

// CỔNG "CHỈ ĐÁP EXACT": hệ chỉ được xuất đáp CHÍNH XÁC (căn/π/hữu tỉ đã chứng nhận). Khi engine rơi về
// SỐ THẬP PHÂN (approximate=true) nghĩa là số học exact KHÔNG chứng nhận được ⇒ không đáng tin ⇒ HỆ TỪ
// CHỐI (an toàn) thay vì xuất số thập phân không kiểm chứng (đúng triết lý "thà im còn hơn sai").
const allExact = (answers) => Array.isArray(answers) && answers.length > 0 && answers.every((a) => a && a.approximate !== true);

// Hai bộ đáp có ĐỒNG THUẬN không: cùng số đáp, và từng cặp khớp theo VĂN BẢN chuẩn hoá (hai lượt
// cùng đi qua một engine nên đáp exact được render cùng dạng) HOẶC khớp theo GIÁ TRỊ SỐ trong dung sai.
const sameAnswers = (A, B) => {
  if (!Array.isArray(A) || !Array.isArray(B) || A.length !== B.length || A.length === 0) return false;
  const norm = (t) => String(t == null ? '' : t).replace(/\s+/g, '').toLowerCase();
  return A.every((a, i) => {
    const b = B[i];
    if (!a || !b) return false;
    if (norm(a.text) === norm(b.text)) return true;
    const x = typeof a.approx === 'number' ? a.approx : null;
    const y = typeof b.approx === 'number' ? b.approx : null;
    return x !== null && y !== null && Number.isFinite(x) && Number.isFinite(y)
      && Math.abs(x - y) <= 1e-6 * Math.max(1, Math.abs(x));
  });
};

export function makeMethod(name, { apiKey = null, model = null, timeoutMs = 25000, mock = false, provider = 'vilao', temperature = undefined, verifyTemperature = 0.4 } = {}) {
  // ---- HỆ NEURO-SYMBOLIC ----
  if (name === 'system') {
    return async function system(item) {
      const t0 = Date.now();
      // BƯỚC 1 — DỊCH đề → plan. Thất bại ở đây KHÔNG phải "sự cố" mà là HỆ TỪ CHỐI AN TOÀN:
      //  • translator tự khước từ (thiếu số liệu/ngoài danh mục), hoặc plan SAI SCHEMA ⇒ 'abstain'
      //    (hệ thà im còn hơn trả đáp cho bài chưa dựng chắc được).
      //  • chỉ non-JSON / mạng / timeout / rate-limit mới là 'error' HẠ TẦNG (không tính cho hệ).
      let plan;
      try {
        if (mock) plan = item.plan; // offline: dùng plan golden (bỏ qua khâu LLM dịch)
        else {
          const { planFromProblem } = await import('../../api/_lib/kernel-bridge/solveWithKernel.js');
          plan = await planFromProblem(item.text, { apiKey, model, timeoutMs, provider, temperature });
        }
      } catch (e) {
        const msg = String(e && e.message || e);
        const infra = /non-JSON|timeout|ETIMEDOUT|ECONNRESET|ENOTFOUND|EAI_AGAIN|fetch failed|network|\b(429|5\d\d)\b/i.test(msg);
        return { status: infra ? 'error' : 'abstain', answers: [], ms: Date.now() - t0, note: msg };
      }
      // BƯỚC 2 — CHẠY engine. Engine NÉM khi lắp ráp plan (dựng hình suy biến, tham chiếu hỏng…):
      //  đó cũng là hệ TỪ CHỐI, tuyệt đối không đoán bừa ⇒ 'abstain', không để rơi vào 'error'.
      let result;
      try {
        result = solvePlan(plan);
      } catch (e) {
        return { status: 'abstain', answers: [], ms: Date.now() - t0, note: 'engine ném khi lắp ráp: ' + String(e && e.message || e) };
      }
      if (!result.ok) return { status: 'abstain', answers: [], ms: Date.now() - t0, note: 'engine từ chối (violation/unsolved)' };
      if (!allExact(result.answers)) return { status: 'abstain', answers: [], ms: Date.now() - t0, note: 'đáp xấp xỉ (không exact) ⇒ từ chối' };
      return { status: 'answer', answers: (result.answers || []).map((a) => ({ kind: a.kind, text: a.text })), ms: Date.now() - t0 };
    };
  }

  // ---- HỆ NEURO-SYMBOLIC + VÒNG LẶP SỬA LỖI (engine-guided repair, cảm hứng AlphaGeometry) ----
  //   plan hỏng → đưa lỗi engine + plan hỏng lại cho LLM sửa → thử lại (tối đa 2 lần). Từ chối
  //   có chủ ý / cạn lượt sửa = 'abstain' (an toàn); chỉ mạng/timeout mới 'error'.
  if (name === 'system-repair') {
    return async function systemRepair(item) {
      const t0 = Date.now();
      if (mock) { // offline: không có LLM để sửa ⇒ chạy plan golden một lượt như 'system'
        try { const r = solvePlan(item.plan); return r.ok ? { status: 'answer', answers: (r.answers || []).map((a) => ({ kind: a.kind, text: a.text })), ms: Date.now() - t0 } : { status: 'abstain', answers: [], ms: Date.now() - t0 }; }
        catch (e) { return { status: 'abstain', answers: [], ms: Date.now() - t0, note: String(e && e.message || e) }; }
      }
      try {
        const { planWithRepair } = await import('../../api/_lib/kernel-bridge/solveWithKernel.js');
        const { result, repairs } = await planWithRepair(item.text, { apiKey, model, timeoutMs, provider, temperature }, 2);
        if (!allExact(result.answers)) return { status: 'abstain', answers: [], ms: Date.now() - t0, note: 'đáp xấp xỉ (không exact) ⇒ từ chối' };
        return { status: 'answer', answers: (result.answers || []).map((a) => ({ kind: a.kind, text: a.text })), ms: Date.now() - t0, note: 'repairs=' + repairs };
      } catch (e) {
        const msg = String(e && e.message || e);
        const infra = /non-JSON|timeout|ETIMEDOUT|ECONNRESET|ENOTFOUND|EAI_AGAIN|fetch failed|network|\b(429|5\d\d)\b/i.test(msg);
        return { status: infra ? 'error' : 'abstain', answers: [], ms: Date.now() - t0, note: msg };
      }
    };
  }

  // ---- HỆ + VÒNG LẶP SỬA LỖI **CÓ KIỂM CHỨNG** (repair-verified) ----
  //  Vấn đề của repair trần: ép LLM sửa tới khi engine chạy được ⇒ có khi nó dựng một mô hình
  //  KHÁC đề mà vẫn hợp lệ ⇒ engine tính đúng cho đề SAI ⇒ "đáp sai có dấu kiểm chứng".
  //  Cách chặn: dịch ĐỘC LẬP LẦN HAI rồi CHỈ xuất đáp khi hai lần ĐỒNG THUẬN.
  //  QUAN TRỌNG: lần hai phải là MẪU ĐỘC LẬP — nếu để temperature=0 như lần một thì plan sinh ra
  //  y hệt, "xác minh" trở nên vô nghĩa. Vì vậy lần hai dùng temperature > 0 (mặc định 0.4).
  if (name === 'system-repair-verified') {
    return async function systemRepairVerified(item) {
      const t0 = Date.now();
      const ab = (note) => ({ status: 'abstain', answers: [], ms: Date.now() - t0, note });
      if (mock) {
        try { const r = solvePlan(item.plan); return r.ok && allExact(r.answers)
          ? { status: 'answer', answers: (r.answers || []).map((a) => ({ kind: a.kind, text: a.text })), ms: Date.now() - t0 }
          : ab('mock: engine không ra đáp exact'); }
        catch (e) { return ab(String(e && e.message || e)); }
      }
      const base = { apiKey, model, timeoutMs, provider };
      let main, verify;
      try {
        const { planWithRepair } = await import('../../api/_lib/kernel-bridge/solveWithKernel.js');
        main = await planWithRepair(item.text, { ...base, temperature }, 2);
      } catch (e) {
        const msg = String(e && e.message || e);
        const infra = /non-JSON|timeout|ETIMEDOUT|ECONNRESET|ENOTFOUND|EAI_AGAIN|fetch failed|network|\b(429|5\d\d)\b/i.test(msg);
        return infra ? { status: 'error', answers: [], ms: Date.now() - t0, note: msg } : ab(msg);
      }
      if (!allExact(main.result.answers)) return ab('đáp xấp xỉ (không exact) ⇒ từ chối');
      // LƯỢT XÁC MINH — dịch lại độc lập (nhiệt độ khác) + cũng được sửa lỗi để độ phủ tương đương.
      try {
        const { planWithRepair } = await import('../../api/_lib/kernel-bridge/solveWithKernel.js');
        verify = await planWithRepair(item.text, { ...base, temperature: verifyTemperature }, 2);
      } catch { return ab('lượt xác minh không dựng được plan ⇒ chưa đủ đồng thuận'); }
      if (!allExact(verify.result.answers)) return ab('lượt xác minh không ra đáp exact ⇒ chưa đủ đồng thuận');
      if (!sameAnswers(main.result.answers, verify.result.answers))
        return ab('hai lượt dịch độc lập KHÔNG đồng thuận ⇒ từ chối (chặn "đáp sai có dấu kiểm chứng")');
      return { status: 'answer', answers: (main.result.answers || []).map((a) => ({ kind: a.kind, text: a.text })),
        ms: Date.now() - t0, note: 'repairs=' + main.repairs + ' · đã đồng thuận 2 lượt' };
    };
  }

  // ---- BASELINE: LLM GIẢI THẲNG ----
  if (name === 'llm-direct') {
    return async function llmDirect(item) {
      const t0 = Date.now();
      if (mock) {
        // Giả lập tất định: ~1/2 đúng, ~1/4 sai tự tin, ~1/4 từ chối — để bảng chỉ số có ý nghĩa.
        const h = hnum(item.text) % 4;
        const want = (item.expect?.answers || []).map((a) => ({ text: a.text }));
        if (h === 0 || h === 1) return { status: 'answer', answers: want, ms: Date.now() - t0 };
        if (h === 2) return { status: 'answer', answers: want.map((a) => ({ text: '999' })), ms: Date.now() - t0 }; // sai tự tin
        return { status: 'abstain', answers: [], ms: Date.now() - t0 };
      }
      try {
        // Chọn nhà cung cấp cùng chữ ký (sys, user, opts)→text: 'vertex' (Gemini qua Google Cloud, credit
        // $300), 'gemini' (AI Studio, key tĩnh), hoặc mặc định Vilao.
        const call = provider === 'vertex'
          ? (await import('../../api/_lib/vertex.js')).callVertex
          : provider === 'gemini'
          ? (await import('../../api/_lib/gemini.js')).callGemini
          : provider === 'openai'
          ? (await import('../../api/_lib/openaiCompat.js')).callOpenAICompat
          : (await import('../../api/_lib/vilao.js')).callVilao;
        // Ngân sách token: mô hình đời mới tính phần "suy nghĩ" CHUNG vào max_tokens; trần 1024 làm
        // đáp JSON bị cắt giữa chừng ⇒ non-JSON. Nới trần để BASELINE được đo ở điều kiện công bằng
        // với hệ (trần chỉ là giới hạn, chi phí vẫn theo token thực sinh).
        const directMaxTokens = provider === 'vertex' || provider === 'gemini' ? 8192 : 1024;
        const raw = await call(DIRECT_PROMPT, item.text, { model, maxTokens: directMaxTokens, timeoutMs, apiKey, temperature });
        let j;
        // Dùng CÙNG bộ phân tích khoan dung như phía hệ: model hay viết '\\sqrt', '\\pi' với một gạch
        // chéo trong chuỗi JSON ⇒ escape không hợp lệ. Nếu chấm những ca đó là 'lỗi' thì BASELINE bị
        // phạt oan vì lỗi hình thức (đo được: 13/116 câu, đa số đáp ĐÚNG). Đối xử đối xứng mới công bằng.
        try { j = parseJsonLoose(extractJson(raw)); } catch { return { status: 'error', answers: [], ms: Date.now() - t0, note: 'non-JSON' }; }
        if (j && j.abstain === true) return { status: 'abstain', answers: [], ms: Date.now() - t0 };
        const arr = Array.isArray(j?.answers) ? j.answers : (j?.answer != null ? [j.answer] : null);
        if (!arr) return { status: 'error', answers: [], ms: Date.now() - t0, note: 'thiếu answers' };
        return { status: 'answer', answers: arr.map((t) => ({ text: String(t) })), ms: Date.now() - t0 };
      } catch (e) {
        return { status: 'error', answers: [], ms: Date.now() - t0, note: String(e && e.message || e) };
      }
    };
  }

  throw new Error('phương pháp không hỗ trợ: ' + name);
}
