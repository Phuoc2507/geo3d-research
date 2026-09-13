// So MỘT ca golden với kết quả engine (solvePlan/solveProblem). THUẦN, không I/O.
// Trả { id, verdict, detail }. verdict: 'pass' | 'regress-status' | 'regress-answer' | 'error'.
// So đáp bằng SỐ (answerCompare) — √2 khớp 1.4142…, KHÔNG so chuỗi thô.
import { answersAgree, toNumeric } from '../answerCompare.js';

/**
 * Đọc chuỗi kỳ vọng dạng điểm "point (x,y,z)" (hoặc chỉ "(x,y,z)") thành [x,y,z] số.
 * Trả null nếu không phải điểm 3 thành phần số (√2 cũng đọc được qua toNumeric).
 */
function parsePointText(text) {
  if (typeof text !== 'string') return null;
  const m = text.match(/\(([^)]*)\)/);
  if (!m) return null;
  const parts = m[1].split(',').map((s) => s.trim());
  if (parts.length !== 3) return null;
  const nums = parts.map(toNumeric);
  return nums.every((n) => typeof n === 'number' && Number.isFinite(n)) ? nums : null;
}

// Đọc toạ độ dạng Scalar của engine ({approx, exact}) về số, làm gọn nhiễu float.
function coordText(sc) {
  const v = typeof sc === 'object' && sc !== null ? sc.approx : sc;
  if (typeof v !== 'number' || !Number.isFinite(v)) return '?';
  return String(Number(v.toFixed(6)));
}

/**
 * Chuỗi đại diện của MỘT đáp, để so được cả những đáp KHÔNG phải số.
 *
 * Không phải đáp nào cũng có `.text`: `relative_position` trả `{relation}` và
 * `intersection` trả `{result, point}`. Trước đây hai dạng này luôn cho text
 * undefined ⇒ mọi golden viết cho chúng đều rớt, tức là hai loại truy vấn ĐÃ SHIP
 * không thể được canh hồi quy.
 */
export function answerText(a) {
  if (!a || typeof a !== 'object') return '';
  if (typeof a.text === 'string' && a.text.trim()) return a.text.trim();
  if (typeof a.relation === 'string' && a.relation.trim()) return a.relation.trim();
  if (a.kind === 'intersection') {
    const parts = [];
    if (a.result) parts.push(String(a.result));
    const p = a.point?.p;
    if (p) parts.push(`(${coordText(p.x)},${coordText(p.y)},${coordText(p.z)})`);
    return parts.join(' ');
  }
  return '';
}

/** So hai chuỗi đáp bỏ qua hoa/thường và khoảng trắng thừa. */
function sameText(a, b) {
  const norm = (t) => String(t ?? '').toLowerCase().replace(/\s+/g, ' ').trim();
  return norm(a) !== '' && norm(a) === norm(b);
}

// Chuẩn hoá MẠNH HƠN sameText cho đáp KÝ HIỆU ("thang chữ" a³·√2/12): gỡ khác biệt HÌNH THỨC —
// số mũ trên (²³…) ↔ ^n, dấu nhân ·/*/× — để `a√3`, `a·√3`, `a^3√2/12`, `a³·√2/12` được coi là một.
// KHÔNG dùng cho đáp số (đã có answersAgree lo).
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

// So đáp KHÔNG PHẢI SỐ: chuỗi chuẩn hoá nhẹ (nhãn "rời nhau", "point (1,2,0)"), rồi mới tới hai
// tầng ký hiệu mạnh hơn. Chuỗi RỖNG không bao giờ được coi là khớp (kể cả khi kỳ vọng cũng rỗng).
function sameSymbolic(got, want) {
  if (sameText(got, want)) return true;
  const g = normText(got);
  if (g === '') return false;
  return g === normText(want) || canonSym(got) === canonSym(want);
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

  // GỘP điểm: "tìm giao điểm" được translator trả HỢP LỆ theo hai khuôn — MỘT truy vấn
  // `intersection` (đáp "point (x,y,z)") HOẶC BA `point_coord` x/y/z rời. Golden viết theo
  // khuôn một KHÔNG được đánh trượt oan khuôn hai. Khi kỳ vọng đúng một điểm và engine trả
  // đúng ba toạ độ số (theo thứ tự x,y,z), so theo TỪNG THÀNH PHẦN. Guard want.length===1
  // giữ cho không gộp nhầm các ca kỳ vọng nhiều đáp.
  if (want.length === 1 && answers.length === 3) {
    const pt = parsePointText(want[0]?.text);
    if (pt) {
      const nums = answers.map((a) =>
        a && typeof a.approx === 'number' ? a.approx : toNumeric(answerText(a)),
      );
      if (nums.every((n) => typeof n === 'number' && Number.isFinite(n))) {
        const bad = pt.findIndex((w, i) => answersAgree(String(nums[i]), w) !== true);
        return bad === -1
          ? { id, verdict: 'pass', detail: 'khớp 1 điểm (gộp 3 toạ độ rời)' }
          : { id, verdict: 'regress-answer', detail: `điểm lệch ở toạ độ #${bad + 1}: kỳ vọng ${pt[bad]} nay ${nums[bad]}` };
      }
    }
  }

  if (want.length !== answers.length) {
    return { id, verdict: 'regress-answer', detail: `số/thứ tự đáp khác: kỳ vọng ${want.length}, nay ${answers.length}` };
  }
  for (let i = 0; i < want.length; i++) {
    const got = answerText(answers[i]);
    const wantText = want[i]?.text;
    // Ưu tiên so SỐ (√2 khớp 1.4142…). Kỳ vọng không đọc được thành số — vd
    // 'rời nhau', 'point (1,2,0)' — thì so chuỗi đã chuẩn hoá.
    const wantNum = toNumeric(wantText);
    const agree = wantNum === null ? sameSymbolic(got, wantText) : answersAgree(got, wantNum);
    if (agree !== true) {
      return { id, verdict: 'regress-answer', detail: `đáp #${i + 1} lệch: kỳ vọng "${wantText}" nay "${got}"` };
    }
  }
  return { id, verdict: 'pass', detail: `${want.length} đáp khớp` };
}
