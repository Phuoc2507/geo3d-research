// Lắp SolveResult: đáp SỐ từ engine (khi giải được → verified thật); LỜI từ LLM.
export function engineSolved(eng) {
  return !!(eng && eng.ok && eng.answers && eng.answers[0]
    && typeof eng.answers[0].approx === 'number' && Number.isFinite(eng.answers[0].approx)
    && (eng.violations?.length ?? 0) === 0);
}

// Kết quả CHỨNG MINH QUAN HỆ đã QUYẾT (proveGeneral): answers[0].kind='prove' + verdict 'true'/'false'.
// Không có `approx` số ⇒ engineSolved() trả false, nên phải nhận diện riêng. Nhận dạng qua answers[0]
// (không dựa vào eng.proof) vì ở nhánh tái dùng geometry.engineSolve chỉ còn { ok, answers, violations, tier }.
export function proofDecided(eng) {
  const a = eng && eng.ok && Array.isArray(eng.answers) ? eng.answers[0] : null;
  return !!(a && a.kind === 'prove' && (a.verdict === 'true' || a.verdict === 'false')
    && typeof a.text === 'string' && a.text
    && (eng.violations?.length ?? 0) === 0);
}

// Chuỗi đáp engine đưa vào prompt LLM (để lời giải DẪN TỚI đúng kết luận), null nếu engine chưa quyết.
export function engineAnswerText(eng) {
  if (engineSolved(eng)) return eng.answers[0].text;
  if (proofDecided(eng)) return eng.answers[0].text;
  return null;
}

// Chỉ giữ construct hợp lệ: có id(string) + rule.type(string). Toạ độ do frontend tự tính
// từ hình, nên ở đây chỉ cần lọc rác, không cần validate sâu từng loại rule.
function sanitizeConstruct(arr) {
  if (!Array.isArray(arr)) return [];
  return arr
    .filter(c => c && typeof c.id === 'string' && c.rule && typeof c.rule.type === 'string')
    .map(c => ({ id: c.id, label: typeof c.label === 'string' ? c.label : c.id, rule: c.rule }));
}

function normalizeSteps(steps) {
  return (Array.isArray(steps) ? steps : []).map((s, i) => ({
    id: s.id || `s${i + 1}`,
    title: s.title || `Bước ${i + 1}`,
    explanation: s.explanation || '',
    formula: s.formula || null,
    highlight: Array.isArray(s.highlight) ? s.highlight : [],
    construct: sanitizeConstruct(s.construct),
  }));
}

export function assembleSolveResult(eng, llm) {
  const steps = normalizeSteps(llm?.steps);
  if (engineSolved(eng)) {
    const a = eng.answers[0];
    return { steps, final_answer: a.text, answer_value: a.approx, verified: true, verify_error: null };
  }
  if (proofDecided(eng)) {
    // Chứng minh đã quyết (đúng HOẶC bác bỏ có phản ví dụ): đáp là verdict chữ, KHÔNG có số để chấm.
    // Trước đây rơi xuống nhánh dưới ⇒ verified:false + đáp LLM, trong khi tier vẫn Mức 1 (mâu thuẫn).
    return { steps, final_answer: eng.answers[0].text, answer_value: null, verified: true, verify_error: null };
  }
  return {
    steps,
    final_answer: typeof llm?.final_answer === 'string' ? llm.final_answer : '',
    answer_value: typeof llm?.answer_value === 'number' ? llm.answer_value : null,
    verified: false,
    verify_error: 'Engine chưa giải được dạng này — lời giải từ AI, CHƯA kiểm chứng tất định.',
  };
}
