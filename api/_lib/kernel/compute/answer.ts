// api/_lib/kernel/compute/answer.ts
import { type Exact, type Scalar, displayScalar, exactToApprox, makeExact, hasExactValue, exactValueToApprox, neg } from '../scalar';
import { type Vec3S, subV, dotV, crossV, lenSqV } from '../vec3s';
import type { Entity } from '../entities';

// Ngưỡng float cho suy biến / song song (so trên đại lượng bình-phương).
export const EPS = 1e-9;

export type ComputeOutcome<T> = { ok: true; answer: T } | { ok: false; problem: string };

export type DistanceAnswer = {
  kind: 'distance';
  exact: Exact | null;
  approx: number;
  text: string;
  approximate: boolean;
  // Giá trị Scalar ĐẦY ĐỦ (gồm cả dạng tổng nhiều căn mà `exact` một-căn không chứa nổi).
  // Cần cho truy vấn `combine`: cộng/trừ các đại lượng đã tính mà KHÔNG mất tính chính xác.
  scalar?: Scalar;
};

export type AngleAnswer = {
  kind: 'angle';
  exactDegrees: number | null; // góc đẹp nếu nhận diện được
  degrees: number;
  // Giá trị SỐ tương ứng với `text` (độ khi hiện độ; giá trị lượng giác khi hiện cos/sin exact).
  // Mọi dạng đáp khác của engine đều có `approx`; tầng cầu nối (engineSolved) chỉ công nhận đáp có
  // `approx` hữu hạn ⇒ thiếu trường này thì MỌI bài góc bị xếp "Mức 3 — chưa chứng thực" dù đã
  // chứng nhận chính xác (45°, 60°…). Bổ sung để góc được đối xử như khoảng cách/thể tích.
  approx: number;
  exactCos: Exact | null; // |cos| (đường-đường/nhị diện) hoặc |sin| (đường-mặt) đã chứng nhận
  text: string;
  approximate: boolean;
};

// Trả thông điệp suy biến đầu tiên (không ném), để compute trả {ok:false} có cấu trúc.
export function firstDegenerate(entities: Entity[]): string | null {
  for (const e of entities) {
    if (e.kind === 'plane' && lenSqV(e.n).approx < EPS) return 'Degenerate plane (zero normal vector)';
    if (e.kind === 'line' && lenSqV(e.dir).approx < EPS) return 'Degenerate line (zero direction vector)';
    if (e.kind === 'sphere' && e.r2.approx <= EPS) return 'Degenerate sphere (radius squared <= 0)';
  }
  return null;
}

// So GIÁ TRỊ EXACT (exactToApprox) với một float tính ĐỘC LẬP; lệch quá dung sai ⇒ bỏ
// exact, dùng float. So exact (không phải bóng .approx) nên bắt được cả lỗi tầng số-học
// exact lẫn lỗi chép công thức.
export function certifyDistance(s: Scalar, floatRef: number): DistanceAnswer {
  const tol = 1e-6 * Math.max(1, Math.abs(floatRef));
  // Chấp nhận CẢ hai lớp: một-căn (exact) và TỔNG NHIỀU CĂN (sum). Vẫn bắt buộc qua
  // cross-check với float độc lập — lệch quá dung sai thì bỏ, hạ về gần đúng.
  const ev = hasExactValue(s) ? exactValueToApprox(s) : null;
  if (ev !== null && Math.abs(ev - floatRef) <= tol) {
    return { kind: 'distance', exact: s.exact, approx: ev, text: displayScalar(s), approximate: false, scalar: s };
  }
  return { kind: 'distance', exact: null, approx: floatRef, text: floatRef.toFixed(4), approximate: true, scalar: { approx: floatRef, exact: null, sum: null } };
}

const NICE_DEGREES = [0, 30, 45, 60, 90];

export function recognizeDegree(deg: number): number | null {
  for (const d of NICE_DEGREES) if (Math.abs(deg - d) < 1e-4) return d;
  return null;
}

// |cos φ| exact của các góc đẹp φ ∈ {0,30,45,60,90} giữa hai vector.
const NICE_ABSCOS: { phi: number; m: Exact }[] = [
  { phi: 0, m: makeExact(1n, 1n, 1) },
  { phi: 30, m: makeExact(1n, 2n, 3) },
  { phi: 45, m: makeExact(1n, 2n, 2) },
  { phi: 60, m: makeExact(1n, 2n, 1) },
  { phi: 90, m: makeExact(0n, 1n, 1) },
];
const exactEq = (a: Exact, b: Exact) => a.num === b.num && a.den === b.den && a.radicand === b.radicand;

// metric = |cos φ| giữa hai vector (exact khi ở trong trường); floatMetric = |cos φ| tính
// ĐỘC LẬP; complement=true cho góc đường–mặt (góc = 90 − φ). Chỉ khẳng định "góc đẹp" khi
// metric EXACT khớp đúng |cos| của một góc đẹp — KHÔNG dựa vào float snap; và exact phải qua
// cross-check với float độc lập (như certifyDistance).
export function certifyAngle(metric: Scalar, floatMetric: number, complement: boolean): AngleAnswer {
  let exactM: Exact | null = metric.exact;
  if (exactM !== null && Math.abs(exactToApprox(exactM) - floatMetric) > 1e-6) exactM = null;
  const phi = (Math.acos(Math.min(1, Math.abs(floatMetric))) * 180) / Math.PI;
  const angleValue = complement ? 90 - phi : phi;
  let niceDeg: number | null = null;
  if (exactM !== null) {
    const hit = NICE_ABSCOS.find((e) => exactEq(exactM as Exact, e.m));
    if (hit) niceDeg = complement ? 90 - hit.phi : hit.phi;
  }
  // Xuất đáp GÓC theo quy ước đề Việt Nam:
  //  • Góc ĐẸP (0/30/45/60/90) → hiện độ, vd "60°".
  //  • Góc KHÔNG đẹp nhưng CÓ metric exact → hiện chính giá trị lượng-giác exact được chứng nhận
  //    (|cos| cho đường–đường/mặt–mặt, |sin| cho đường–mặt) — đúng thứ đề hỏi khi góc không đẹp
  //    ("côsin của góc…", "sin của góc…"), thay vì số độ làm tròn. Trước đây luôn hiện "≈ x.xx°"
  //    nên bài hỏi côsin bị chấm sai dù engine đã có sẵn giá trị đúng.
  //  • Không có metric exact → giữ số độ xấp xỉ (đáp gần đúng, đánh dấu approximate).
  // Giá trị lượng giác chính xác theo nghĩa RỘNG (một căn HOẶC tổng nhiều căn), vẫn bắt buộc
  // qua cross-check với float độc lập.
  const evM = hasExactValue(metric) ? exactValueToApprox(metric) : null;
  const exactBroad = evM !== null && Math.abs(evM - floatMetric) <= 1e-6;
  const text =
    niceDeg !== null ? `${niceDeg}°`
    : exactBroad ? displayScalar(metric)
    : `≈ ${angleValue.toFixed(2)}°`;
  return {
    kind: 'angle',
    exactDegrees: niceDeg,
    degrees: niceDeg !== null ? niceDeg : angleValue,
    approx: niceDeg !== null ? niceDeg : exactBroad ? (evM as number) : angleValue,
    exactCos: exactM,
    text,
    approximate: niceDeg === null && !exactBroad,
  };
}

// Kiểm đồng phẳng cho polygon/đáy (tiền-điều-kiện của area/volume). Trả thông điệp nếu có
// đỉnh không nằm trên mặt của bộ ba không thẳng hàng đầu tiên; null nếu đồng phẳng (hoặc
// suy biến toàn thẳng hàng). Dùng isZeroS (exact khi có).
export function coplanarityProblem(pts: Vec3S[], what: string, tol: number = EPS): string | null {
  if (pts.length <= 3) return null;
  const p0 = pts[0];
  let normal: Vec3S | null = null;
  for (let i = 1; i < pts.length && normal === null; i++) {
    for (let j = i + 1; j < pts.length; j++) {
      const n = crossV(subV(pts[i], p0), subV(pts[j], p0));
      if (!isZeroS(lenSqV(n))) { normal = n; break; }
    }
  }
  if (normal === null) return null; // mọi điểm thẳng hàng ⇒ đồng phẳng tầm thường
  const nLen = Math.sqrt(lenSqV(normal).approx);
  for (const p of pts) {
    const tp = dotV(subV(p, p0), normal);
    // Đồng phẳng chính xác (Oxyz) → exact 0. Ngược lại so khoảng cách điểm–mặt CHUẨN HOÁ
    // (|(p−p0)·n|/|n|) với tolerance — không dùng tích hỗn tạp thô (phụ thuộc thang).
    const off = tp.exact !== null && tp.exact.num === 0n ? 0 : Math.abs(tp.approx) / nLen;
    if (off > tol) return `${what} vertices are not coplanar`;
  }
  return null;
}

// Đáp số vô hướng tổng quát (volume/area/ratio…) + self-certificate như certifyDistance.
export type ScalarAnswer = {
  kind: string;
  exact: Exact | null;
  approx: number;
  text: string;
  approximate: boolean;
  scalar?: Scalar; // xem chú thích ở DistanceAnswer — phần KHÔNG π của giá trị
  // Hệ số của π (đáp dạng kπ của khối tròn xoay: trụ/nón/cầu). Giá trị đầy đủ = scalar + piCoeff·π.
  // Có trường này thì `combine` gộp được các khối tròn xoay ("khối ghép": trụ khoét rãnh, trụ + nón…)
  // mà vẫn giữ dạng π chính xác — trước đây đáp π không mang Scalar nên combine từ chối gộp.
  piCoeff?: Scalar;
};

export function certifyScalar(kind: string, s: Scalar, floatRef: number): ScalarAnswer {
  const tol = 1e-6 * Math.max(1, Math.abs(floatRef));
  const ev = hasExactValue(s) ? exactValueToApprox(s) : null;
  if (ev !== null && Math.abs(ev - floatRef) <= tol) {
    return { kind, exact: s.exact, approx: ev, text: displayScalar(s), approximate: false, scalar: s };
  }
  return { kind, exact: null, approx: floatRef, text: floatRef.toFixed(4), approximate: true, scalar: { approx: floatRef, exact: null, sum: null } };
}

// Ghép hệ số (rational×căn) với π thành chuỗi gọn: '8'→'8π', '8/3'→'8π/3', '2√2/3'→'2√2π/3', '1'→'π'.
function piText(s: Scalar): string {
  const d = displayScalar(s);
  if (d === '1') return 'π';
  if (d === '-1') return '-π';
  // Hệ số là TỔNG nhiều căn ⇒ phải bọc ngoặc, nếu không '√2 + √3' + 'π' đọc thành √2 + (√3·π).
  const multi = (s.sum?.terms.length ?? 0) > 1;
  if (multi) return d.startsWith('(') ? d.replace(')/', ')π/') : `(${d})π`;
  const slash = d.indexOf('/');
  return slash >= 0 ? d.slice(0, slash) + 'π' + d.slice(slash) : d + 'π';
}

// Đáp số dạng (hệ số)·π — cho thể tích/diện tích mặt cầu. `coeff` là hệ số ĐÚNG (rational×căn); nếu
// coeff là exact và giá trị coeff·π khớp float tham chiếu (self-check) ⇒ trả DẠNG π CHÍNH XÁC (vd '36π',
// '8√2π/3'); ngược lại rơi về số thập phân. Trường `exact` giữ null vì π không nằm trong trường (num/den/căn).
export function piScalarAnswer(kind: string, coeff: Scalar, floatRef: number): ScalarAnswer {
  const evC = hasExactValue(coeff) ? exactValueToApprox(coeff) : null;
  const val = (evC ?? coeff.approx) * Math.PI;
  const tol = 1e-6 * Math.max(1, Math.abs(floatRef));
  if (evC !== null && Math.abs(val - floatRef) <= tol) {
    return { kind, exact: null, approx: val, text: piText(coeff), approximate: false, piCoeff: coeff };
  }
  // Gần đúng: vẫn mang Scalar float để combine gộp được (kết quả gộp sẽ là gần đúng — trung thực).
  return { kind, exact: null, approx: floatRef, text: floatRef.toFixed(4), approximate: true, scalar: { approx: floatRef, exact: null, sum: null } };
}

// Đáp HỖN HỢP p + q·π (vd khối ghép hình hộp + nửa cầu: 8 + 16π/3). `plain` là phần không π, `pi` là hệ số
// của π; cả hai phải chính xác và tổng phải khớp float tham chiếu độc lập — không thì hạ về gần đúng.
// Trường hợp một trong hai phần bằng 0 chính xác thì quy về certifyScalar / piScalarAnswer thông thường
// (giữ nguyên định dạng đáp quen thuộc "27√3", "36π").
export function mixedPiScalarAnswer(kind: string, plain: Scalar, pi: Scalar, floatRef: number): ScalarAnswer {
  const exactZero = (s: Scalar): boolean => hasExactValue(s) && exactValueToApprox(s) === 0;
  if (exactZero(pi)) return certifyScalar(kind, plain, floatRef);
  if (exactZero(plain)) return piScalarAnswer(kind, pi, floatRef);
  const evP = hasExactValue(plain) ? exactValueToApprox(plain) : null;
  const evC = hasExactValue(pi) ? exactValueToApprox(pi) : null;
  const tol = 1e-6 * Math.max(1, Math.abs(floatRef));
  if (evP !== null && evC !== null && Math.abs(evP + evC * Math.PI - floatRef) <= tol) {
    const negPi = evC < 0;
    const piPart = piText(negPi ? neg(pi) : pi);
    const text = `${displayScalar(plain)} ${negPi ? '-' : '+'} ${piPart}`;
    return { kind, exact: null, approx: evP + evC * Math.PI, text, approximate: false, scalar: plain, piCoeff: pi };
  }
  return { kind, exact: null, approx: floatRef, text: floatRef.toFixed(4), approximate: true, scalar: { approx: floatRef, exact: null, sum: null } };
}

// Kiểm một Scalar bằng 0 (exact chính xác khi có, ngược lại ngưỡng float).
export function isZeroS(s: Scalar): boolean {
  return s.exact !== null ? s.exact.num === 0n : Math.abs(s.approx) < EPS;
}

// So sánh hai Scalar: -1 / 0 / 1. Chính xác khi cả hai exact cùng radicand (gồm hữu tỷ
// radicand 1); ngược lại dùng float. So (num/den)√r ⇔ so num·den chéo (√r>0, den>0).
export function cmpScalar(a: Scalar, b: Scalar): number {
  if (a.exact !== null && b.exact !== null && a.exact.radicand === b.exact.radicand) {
    const lhs = a.exact.num * b.exact.den;
    const rhs = b.exact.num * a.exact.den;
    return lhs < rhs ? -1 : lhs > rhs ? 1 : 0;
  }
  const d = a.approx - b.approx;
  return Math.abs(d) < EPS ? 0 : d < 0 ? -1 : 1;
}
