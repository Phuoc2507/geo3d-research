// api/_lib/kernel/scalar.ts

// Giá trị chính xác = (num/den)·√radicand, với radicand nguyên dương square-free.
// radicand === 1 ⇒ số hữu tỷ thuần. den luôn > 0. Phân số luôn rút gọn.
export type Exact = { num: bigint; den: bigint; radicand: number };

// Trần cho radicand (một `number`). Vượt trần: (1) tích/căn có thể vượt 2^53 → làm tròn
// double sai → giá trị exact sai; (2) extractSquare O(√radicand) ghim CPU. Trên trần này,
// các phép trả `null` (rời trường an toàn) và rơi về float. 1e12 thừa cỡ bài phổ thông
// (radicand thực tế là √2, √3, √13…) mà √(1e12)=1e6 vòng vẫn nhanh.
export const MAX_SAFE_RADICAND = 1e12;

function bgcd(a: bigint, b: bigint): bigint {
  a = a < 0n ? -a : a;
  b = b < 0n ? -b : b;
  while (b) {
    [a, b] = [b, a % b];
  }
  return a || 1n;
}

// Tách thừa số chính phương: r = factor² · rad, rad square-free. Trả { rad, factor }.
function extractSquare(r: number): { rad: number; factor: bigint } {
  if (!Number.isInteger(r) || r < 1) {
    throw new Error(`radicand must be a positive integer, got ${r}`);
  }
  let rad = r;
  let factor = 1n;
  for (let f = 2; f * f <= rad; f++) {
    while (rad % (f * f) === 0) {
      rad /= f * f;
      factor *= BigInt(f);
    }
  }
  return { rad, factor };
}

export function makeExact(num: bigint, den: bigint, radicand: number = 1): Exact {
  if (den === 0n) throw new Error('Exact denominator cannot be zero');
  if (num === 0n) return { num: 0n, den: 1n, radicand: 1 };
  if (den < 0n) {
    num = -num;
    den = -den;
  }
  const { rad, factor } = extractSquare(radicand);
  num *= factor;
  const g = bgcd(num, den);
  return { num: num / g, den: den / g, radicand: rad };
}

export function exactToApprox(e: Exact): number {
  return (Number(e.num) / Number(e.den)) * Math.sqrt(e.radicand);
}

export function displayExact(e: Exact): string {
  const sign = e.num < 0n ? '-' : '';
  const n = e.num < 0n ? -e.num : e.num;
  if (e.radicand === 1) {
    return e.den === 1n ? `${sign}${n}` : `${sign}${n}/${e.den}`;
  }
  const radStr = `√${e.radicand}`;
  const numer = n === 1n ? radStr : `${n}${radStr}`;
  return e.den === 1n ? `${sign}${numer}` : `${sign}${numer}/${e.den}`;
}

export function negExact(a: Exact): Exact {
  return { num: -a.num, den: a.den, radicand: a.radicand };
}

// a + b — chỉ đóng khi cùng radicand (hoặc một trong hai bằng 0). Ngược lại ⇒ null.
export function addExact(a: Exact, b: Exact): Exact | null {
  if (a.num === 0n) return b;
  if (b.num === 0n) return a;
  if (a.radicand !== b.radicand) return null;
  // a.num/a.den + b.num/b.den, chung radicand
  const num = a.num * b.den + b.num * a.den;
  const den = a.den * b.den;
  return makeExact(num, den, a.radicand);
}

export function subExact(a: Exact, b: Exact): Exact | null {
  return addExact(a, negExact(b));
}

// (a.num/a.den·√ra)·(b.num/b.den·√rb) = (a.num·b.num)/(a.den·b.den)·√(ra·rb)
export function mulExact(a: Exact, b: Exact): Exact | null {
  const radicand = a.radicand * b.radicand;
  if (radicand > MAX_SAFE_RADICAND) return null; // rời trường an toàn ⇒ để caller rơi về float
  return makeExact(a.num * b.num, a.den * b.den, radicand);
}

// a / b = (a.num·b.den)/(a.den·b.num) · √ra/√rb = ... · √(ra·rb)/rb
export function divExact(a: Exact, b: Exact): Exact | null {
  if (b.num === 0n) throw new Error('Exact division by zero');
  const radicand = a.radicand * b.radicand;
  if (radicand > MAX_SAFE_RADICAND) return null;
  const num = a.num * b.den;
  const den = a.den * b.num * BigInt(b.radicand);
  return makeExact(num, den, radicand);
}

// √(num/den) khi là hữu tỷ không âm; = √(num·den)/den. Ngoài ra ⇒ null.
export function sqrtExact(a: Exact): Exact | null {
  if (a.radicand !== 1) return null; // √ của một căn: ngoài trường
  if (a.num < 0n) return null;
  if (a.num === 0n) return makeExact(0n, 1n, 1);
  const radicand = Number(a.num * a.den);
  if (!Number.isSafeInteger(radicand) || radicand > MAX_SAFE_RADICAND) return null;
  return makeExact(1n, a.den, radicand);
}

// Số lai: approx (float) luôn có; exact khi tính được trong trường hữu tỷ + MỘT căn;
// sum khi tính được trong trường TỔNG NHIỀU CĂN (lớp rộng hơn, xem cuối tệp).
// Bất biến: nếu sum có đúng 1 số hạng thì exact cũng được điền (tương thích code cũ).
export type Scalar = { approx: number; exact: Exact | null; sum?: ExactSum | null };

export function num(n: number): Scalar {
  return { approx: n, exact: null, sum: null };
}

export function fromExact(e: Exact): Scalar {
  return { approx: exactToApprox(e), exact: e, sum: sumFromExact(e) };
}

// Gói kết quả: ưu tiên giữ exact cũ; nếu thiếu mà sum lại về được 1 số hạng thì điền exact
// từ sum (cải thiện thuần tuý, vẫn là một căn đúng). Không bao giờ điền exact từ tổng ≥2 căn.
function pack(approx: number, exact: Exact | null, sum: ExactSum | null): Scalar {
  const ex = exact ?? (sum ? exactFromSum(sum) : null);
  return { approx, exact: ex, sum };
}
const S = (a: Scalar): ExactSum | null => (a.sum !== undefined ? a.sum : (a.exact ? sumFromExact(a.exact) : null));

// Hằng tiện dụng: số nguyên/hữu tỷ chính xác.
export function rat(n: bigint, d: bigint = 1n): Scalar {
  return fromExact(makeExact(n, d, 1));
}

export function add(a: Scalar, b: Scalar): Scalar {
  const exact = a.exact && b.exact ? addExact(a.exact, b.exact) : null;
  const sa = S(a), sb = S(b);
  return pack(a.approx + b.approx, exact, sa && sb ? addSum(sa, sb) : null);
}

export function sub(a: Scalar, b: Scalar): Scalar {
  const exact = a.exact && b.exact ? subExact(a.exact, b.exact) : null;
  const sa = S(a), sb = S(b);
  return pack(a.approx - b.approx, exact, sa && sb ? subSum(sa, sb) : null);
}

export function mul(a: Scalar, b: Scalar): Scalar {
  const exact = a.exact && b.exact ? mulExact(a.exact, b.exact) : null;
  const sa = S(a), sb = S(b);
  return pack(a.approx * b.approx, exact, sa && sb ? mulSum(sa, sb) : null);
}

export function div(a: Scalar, b: Scalar): Scalar {
  const exact = a.exact && b.exact && b.exact.num !== 0n ? divExact(a.exact, b.exact) : null;
  const sa = S(a), sb = S(b);
  const sum = sa && sb && !isZeroSum(sb) ? divSum(sa, sb) : null;
  return pack(a.approx / b.approx, exact, sum);
}

export function neg(a: Scalar): Scalar {
  const sa = S(a);
  return pack(-a.approx, a.exact ? negExact(a.exact) : null, sa ? negSum(sa) : null);
}

export function sqrt(a: Scalar): Scalar {
  const exact = a.exact ? sqrtExact(a.exact) : null;
  const sa = S(a);
  return pack(Math.sqrt(a.approx), exact, sa ? sqrtSum(sa) : null);
}

export function displayScalar(s: Scalar): string {
  if (s.sum && s.sum.terms.length > 1) return displaySum(s.sum);      // tổng nhiều căn
  if (s.exact) return displayExact(s.exact);
  if (s.sum) return displaySum(s.sum);                                 // 0 hoặc 1 số hạng
  return s.approx.toFixed(4);
}

// Giá trị có ở dạng CHÍNH XÁC không (một căn hoặc tổng nhiều căn)?
export function hasExactValue(s: Scalar): boolean {
  return s.exact !== null || (s.sum != null && s.sum.terms.length > 0);
}

// Giá trị chính xác quy về float (để tự kiểm chéo với float độc lập).
export function exactValueToApprox(s: Scalar): number | null {
  if (s.sum && s.sum.terms.length > 0) return sumToApprox(s.sum);
  return s.exact ? exactToApprox(s.exact) : null;
}

// ============================================================================
// LỚP SỐ MỞ RỘNG: TỔNG NHIỀU CĂN  —  Σ (numᵢ·√radᵢ) / den
// ----------------------------------------------------------------------------
// Vì sao cần: Exact ở trên chỉ biểu diễn MỘT hữu tỉ nhân MỘT căn. Hình học THPT
// dùng Pytago/hệ thức lượng nối tiếp rất dễ sinh ra TỔNG hai căn khác nhau
// (vd a√2 + b√3). Trước đây addExact trả null ở trường hợp đó ⇒ rơi về float ⇒
// đáp bị đánh dấu "approximate" (và theo cổng chỉ-nhận-exact thì bị TỪ CHỐI).
// Lớp này đóng kín phép +,−,× cho tổng nhiều căn, và đóng phép ÷ khi mẫu có
// 1 hoặc 2 số hạng (nhân liên hợp). Căn LỒNG (√ của một tổng căn) vẫn NGOÀI
// trường — trả null, giữ đúng nguyên tắc "thà báo gần đúng còn hơn khẳng định sai".
//
// AN TOÀN: đây là lớp CỘNG THÊM. Kiểu Exact cũ giữ nguyên; giá trị nhiều số hạng
// có exact = null (code cũ thấy "không exact" → hành xử y như trước, không sai
// âm thầm), chỉ code mới đọc trường `sum`.
// ============================================================================

export type Term = { num: bigint; radicand: number }; // num·√radicand, radicand square-free ≥ 1
export type ExactSum = { terms: Term[]; den: bigint }; // Σ terms / den ; den > 0

// Trần số hạng: chặn bùng nổ tổ hợp khi nhân nhiều tổng. Vượt ⇒ null (rơi float an toàn).
export const MAX_SUM_TERMS = 8;

// Chuẩn hoá: tách thừa số chính phương khỏi mỗi căn, gộp cùng radicand, bỏ số hạng 0,
// sắp theo radicand, rút gọn gcd chung với mẫu, ép den > 0.
function normalizeSum(rawTerms: Term[], den: bigint): ExactSum | null {
  if (den === 0n) return null;
  let d = den;
  const acc = new Map<number, bigint>();
  for (const t of rawTerms) {
    if (t.num === 0n) continue;
    if (!Number.isInteger(t.radicand) || t.radicand < 1) return null;
    if (t.radicand > MAX_SAFE_RADICAND) return null;
    const { rad, factor } = extractSquare(t.radicand);
    const n = t.num * factor;
    acc.set(rad, (acc.get(rad) ?? 0n) + n);
  }
  let terms: Term[] = [];
  for (const [radicand, num] of acc) if (num !== 0n) terms.push({ num, radicand });
  if (terms.length === 0) return { terms: [], den: 1n }; // giá trị 0
  if (terms.length > MAX_SUM_TERMS) return null;
  if (d < 0n) { d = -d; terms = terms.map((t) => ({ num: -t.num, radicand: t.radicand })); }
  let g = d;
  for (const t of terms) g = bgcd(g, t.num);
  if (g > 1n) { d /= g; terms = terms.map((t) => ({ num: t.num / g, radicand: t.radicand })); }
  terms.sort((a, b) => a.radicand - b.radicand);
  return { terms, den: d };
}

export function sumFromExact(e: Exact): ExactSum {
  return e.num === 0n ? { terms: [], den: 1n } : { terms: [{ num: e.num, radicand: e.radicand }], den: e.den };
}

// Về Exact một số hạng (nếu được) — để code cũ dùng lại bình thường.
export function exactFromSum(s: ExactSum): Exact | null {
  if (s.terms.length === 0) return makeExact(0n, 1n, 1);
  if (s.terms.length !== 1) return null;
  return makeExact(s.terms[0].num, s.den, s.terms[0].radicand);
}

export function sumToApprox(s: ExactSum): number {
  let acc = 0;
  for (const t of s.terms) acc += Number(t.num) * Math.sqrt(t.radicand);
  return acc / Number(s.den);
}

export function isZeroSum(s: ExactSum): boolean { return s.terms.length === 0; }

export function negSum(a: ExactSum): ExactSum {
  return { terms: a.terms.map((t) => ({ num: -t.num, radicand: t.radicand })), den: a.den };
}

// a/da + b/db = (a·db + b·da)/(da·db) — LUÔN đóng (đây là điểm gỡ "trần" cũ).
export function addSum(a: ExactSum, b: ExactSum): ExactSum | null {
  const raw: Term[] = [
    ...a.terms.map((t) => ({ num: t.num * b.den, radicand: t.radicand })),
    ...b.terms.map((t) => ({ num: t.num * a.den, radicand: t.radicand })),
  ];
  return normalizeSum(raw, a.den * b.den);
}

export function subSum(a: ExactSum, b: ExactSum): ExactSum | null { return addSum(a, negSum(b)); }

// (Σ aᵢ√pᵢ)(Σ bⱼ√qⱼ) = Σ aᵢbⱼ·√(pᵢqⱼ) — đóng, có chặn trần radicand & số hạng.
export function mulSum(a: ExactSum, b: ExactSum): ExactSum | null {
  const raw: Term[] = [];
  for (const x of a.terms) for (const y of b.terms) {
    const radicand = x.radicand * y.radicand;
    if (radicand > MAX_SAFE_RADICAND) return null;
    raw.push({ num: x.num * y.num, radicand });
  }
  return normalizeSum(raw, a.den * b.den);
}

// Nghịch đảo: đóng khi mẫu có 1 số hạng (hữu tỉ hoá) hoặc 2 số hạng (nhân liên hợp).
// ≥3 số hạng ⇒ null (giới hạn được khai báo trung thực).
function invSum(b: ExactSum): ExactSum | null {
  if (b.terms.length === 0) return null; // chia 0
  if (b.terms.length === 1) {
    const { num: n, radicand: k } = b.terms[0];
    // 1 / (n√k/den) = den/(n√k) = den·√k/(n·k)
    return normalizeSum([{ num: b.den, radicand: k }], n * BigInt(k));
  }
  if (b.terms.length === 2) {
    // 1/(p+q) = (p−q)/(p²−q²); p² và q² đều hữu tỉ ⇒ mẫu về 1 số hạng.
    const p: ExactSum = { terms: [b.terms[0]], den: b.den };
    const q: ExactSum = { terms: [b.terms[1]], den: b.den };
    const conj = subSum(p, q);
    const p2 = mulSum(p, p), q2 = mulSum(q, q);
    if (!conj || !p2 || !q2) return null;
    const denom = subSum(p2, q2);
    if (!denom || denom.terms.length !== 1) return null;
    const invDenom = invSum(denom);
    return invDenom ? mulSum(conj, invDenom) : null;
  }
  return null;
}

export function divSum(a: ExactSum, b: ExactSum): ExactSum | null {
  const inv = invSum(b);
  return inv ? mulSum(a, inv) : null;
}

// √ chỉ đóng khi đối số là HỮU TỈ không âm (một số hạng, radicand 1). Căn lồng ⇒ null.
export function sqrtSum(a: ExactSum): ExactSum | null {
  if (a.terms.length === 0) return { terms: [], den: 1n };
  if (a.terms.length !== 1 || a.terms[0].radicand !== 1) return null;
  const e = exactFromSum(a);
  if (!e) return null;
  const r = sqrtExact(e);
  return r ? sumFromExact(r) : null;
}

// Hiển thị: "√2 + √3", "(2√2 − 3√5)/7", "5"…
export function displaySum(s: ExactSum): string {
  if (s.terms.length === 0) return '0';
  const piece = (t: Term, first: boolean) => {
    const neg = t.num < 0n;
    const n = neg ? -t.num : t.num;
    const sign = neg ? (first ? '-' : ' - ') : (first ? '' : ' + ');
    const body = t.radicand === 1 ? `${n}` : (n === 1n ? `√${t.radicand}` : `${n}√${t.radicand}`);
    return sign + body;
  };
  const body = s.terms.map((t, i) => piece(t, i === 0)).join('');
  if (s.den === 1n) return body;
  return s.terms.length === 1 ? `${body}/${s.den}` : `(${body})/${s.den}`;
}
