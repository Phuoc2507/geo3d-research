// So MỘT ca golden với kết quả engine (solvePlan/solveProblem). THUẦN, không I/O.
// Trả { id, verdict, detail }. verdict: 'pass' | 'regress-status' | 'regress-answer' | 'error'.
// So đáp bằng SỐ (answerCompare) — √2 khớp 1.4142…, KHÔNG so chuỗi thô.
import { answersAgree, toNumeric } from '../answerCompare.js';

// Chuẩn hoá chuỗi để so đáp phi-số (nhãn/phương trình/đáp "thang chữ" a³·√2/12):
// gộp khoảng trắng, bỏ dấu, thường hoá, chuẩn hoá dấu trừ unicode; đồng thời gỡ khác biệt
// HÌNH THỨC của đáp ký hiệu — số mũ trên (²³…) ↔ ^n, và dấu nhân ·/*/× — để `a√3`, `a·√3`,
// `a^3√2/12`, `a³·√2/12` được coi là một. KHÔNG dùng cho đáp số (đã có answersAgree lo).
const SUP = { '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4', '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9' };
function normText(s) {
  return String(s == null ? '' : s)
    .replace(/[−–—]/g, '-')
    .replace(/[⁰¹²³⁴⁵⁶⁷⁸⁹]/g, (c) => SUP[c])   // số mũ trên → chữ số thường (a³ → a3)
    .replace(/\^/g, '')                          // a^3 → a3  (khớp a³ → a3)
    .replace(/[·*×]/g, '')                       // gỡ dấu nhân hiển thị (a·√3 → a√3)
    .replace(/\s+/g, '')
    .toLowerCase();
}

// So ký hiệu MẠNH HƠN normText: HIỂU PHÉP NHÂN ĐỔI CHỖ. Tách mỗi hạng tử thành các "nguyên tử nhân"
// (số, π, √n, biến^mũ) rồi SẮP để `28πa²/3` == `a²·28π/3`. CHỈ THÊM khớp (dùng sau khi normText trượt),
// KHÔNG bao giờ gỡ khớp cũ — nên không thể biến đáp sai thành "khớp": phải trùng ĐÚNG bộ nguyên tử ở
// tử và mẫu (vd `a√5/3` ≠ `a√5/5` vì mẫu khác; `25a/8` ≠ `25/8` vì thiếu `a`).
function mulAtoms(group) {
  const out = [];
  let i = 0;
  while (i < group.length) {
    const c = group[i];
    if (c === '·' || c === '*' || c === '×') { i++; continue; }
    if (/[0-9.]/.test(c)) { let n = ''; while (i < group.length && /[0-9.]/.test(group[i])) n += group[i++]; const v = parseFloat(n); if (v !== 1) out.push('#' + v); continue; }
    if (c === 'π') { out.push('pi'); i++; continue; }
    if (c === '√') { let r = ''; i++; while (i < group.length && /[0-9]/.test(group[i])) r += group[i++]; out.push('r' + r); continue; }
    if (/[a-z]/.test(c)) { i++; let e = ''; while (i < group.length && /[0-9]/.test(group[i])) e += group[i++]; out.push(c + '^' + (e || '1')); continue; }
    i++; // ký tự lạ: bỏ
  }
  return out.sort();
}
function canonTerm(term) {
  let sign = '+', t = term;
  if (t[0] === '-') { sign = '-'; t = t.slice(1); } else if (t[0] === '+') t = t.slice(1);
  const parts = t.split('/');
  const num = mulAtoms(parts[0] || '');
  const den = parts.length > 1 ? mulAtoms(parts.slice(1).join('/')) : [];
  return sign + num.join('*') + '/' + den.join('*');
}
export function canonSym(s) {
  const x = String(s == null ? '' : s)
    .replace(/[−–—]/g, '-')
    .replace(/[⁰¹²³⁴⁵⁶⁷⁸⁹]/g, (c) => SUP[c])
    .replace(/\^/g, '')
    .replace(/[°\s]/g, '')
    .toLowerCase();
  const terms = [];
  let cur = '';
  for (let i = 0; i < x.length; i++) {
    const ch = x[i];
    if ((ch === '+' || ch === '-') && i > 0) { terms.push(cur); cur = ch; } else cur += ch;
  }
  if (cur) terms.push(cur);
  return terms.map(canonTerm).sort().join('|');
}

export function compareCase(golden, result) {
  const id = golden.id;
  if (result && result.__throw) {
    return { id, verdict: 'error', detail: 'engine văng lỗi: ' + result.__throw };
  }
  const expect = golden.expect || {};
  const wantOk = expect.ok !== false; // mặc định kỳ vọng ok:true
  const gotOk = !!(result && result.ok);
  const answers = (result && result.answers) || [];

  if (!wantOk) {
    // Ca kỳ vọng HỎNG (hiếm ở v1): nay đậu ⇒ đổi hành vi (đánh regress-answer để lộ ra); nay hỏng ⇒ pass.
    return gotOk
      ? { id, verdict: 'regress-answer', detail: 'kỳ vọng ok:false nhưng nay ok:true' }
      : { id, verdict: 'pass', detail: 'ok:false như kỳ vọng' };
  }
  if (!gotOk || answers.length === 0) {
    return { id, verdict: 'regress-status', detail: `kỳ vọng ok:true nhưng nay ok=${gotOk}, số đáp=${answers.length}` };
  }
  const want = expect.answers || [];
  if (want.length !== answers.length) {
    return { id, verdict: 'regress-answer', detail: `số/thứ tự đáp khác: kỳ vọng ${want.length}, nay ${answers.length}` };
  }
  for (let i = 0; i < want.length; i++) {
    // Nhãn CHỮ của đáp: query relative_position trả nhãn ở trường `.relation` (KHÔNG có `.text`).
    // Đọc `.text ?? .relation` để cả đáp-số (text) lẫn đáp-nhãn (relation) đều so được.
    const gotText = answers[i]?.text ?? answers[i]?.relation;
    const wantText = want[i]?.text ?? want[i]?.relation;
    const wantNum = toNumeric(wantText);
    let agree = answersAgree(gotText, wantNum);
    // Đáp KHÔNG phải số (nhãn vị trí tương đối "chéo nhau", phương trình "2x−y+z−3=0"…):
    // answersAgree trả null ⇒ fallback so CHUỖI CHUẨN HOÁ (khi cả hai bên đều không parse ra số).
    if (agree !== true && wantNum === null && toNumeric(gotText) === null) {
      agree = normText(gotText) === normText(wantText) || canonSym(gotText) === canonSym(wantText);
    }
    if (agree !== true) {
      return { id, verdict: 'regress-answer', detail: `đáp #${i + 1} lệch: kỳ vọng "${wantText}" nay "${gotText}"` };
    }
  }
  return { id, verdict: 'pass', detail: `${want.length} đáp khớp` };
}
