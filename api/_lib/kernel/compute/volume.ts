// api/_lib/kernel/compute/volume.ts
import { type Scalar, div, neg, rat, add, mul, sqrt, hasExactValue, exactValueToApprox } from '../scalar';
import { type Vec3S, subV, dotV, crossV, lenSqV, addV, scaleV, toApproxVec } from '../vec3s';
import type { PointE, SphereE } from '../entities';
import { sub, scalarTriple, tetrahedronVolume, type Vec3, cross, dot, normalize, length } from '../vecMath';
import { type ComputeOutcome, type ScalarAnswer, certifyScalar, coplanarityProblem, isZeroS, piScalarAnswer } from './answer';

const av = toApproxVec;

// ×6 thể tích có dấu của tứ diện (a,b,c,d) = tích hỗn tạp (b−a, c−a, d−a).
function tripleScalar(a: Vec3S, b: Vec3S, c: Vec3S, d: Vec3S): Scalar {
  return dotV(subV(b, a), crossV(subV(c, a), subV(d, a)));
}
// Lấy dấu từ EXACT khi có (float có thể làm tròn ngược dấu ở ca gần suy biến).
function absS(s: Scalar): Scalar {
  return s.exact !== null ? (s.exact.num < 0n ? neg(s) : s) : (s.approx < 0 ? neg(s) : s);
}

export function tetraVolumeScalar(a: PointE, b: PointE, c: PointE, d: PointE): Scalar {
  return div(absS(tripleScalar(a.p, b.p, c.p, d.p)), rat(6n));
}

export function pyramidVolumeScalar(base: PointE[], apex: PointE): Scalar {
  let sum = rat(0n);
  for (let i = 1; i < base.length - 1; i++) {
    sum = add(sum, tripleScalar(base[0].p, base[i].p, base[i + 1].p, apex.p));
  }
  return div(absS(sum), rat(6n));
}

function fPyramid(base: Vec3[], apex: Vec3): number {
  let s = 0;
  for (let i = 1; i < base.length - 1; i++) {
    s += scalarTriple(sub(base[i], base[0]), sub(base[i + 1], base[0]), sub(apex, base[0]));
  }
  return Math.abs(s) / 6;
}

export function computeTetraVolume(a: PointE, b: PointE, c: PointE, d: PointE): ComputeOutcome<ScalarAnswer> {
  const floatRef = tetrahedronVolume(av(a.p), av(b.p), av(c.p), av(d.p));
  return { ok: true, answer: certifyScalar('volume', tetraVolumeScalar(a, b, c, d), floatRef) };
}

export function computePyramidVolume(base: PointE[], apex: PointE): ComputeOutcome<ScalarAnswer> {
  if (base.length < 3) return { ok: false, problem: 'pyramid base needs at least 3 vertices' };
  // Tiền-điều-kiện: đáy phải PHẲNG (tổng tứ diện có dấu vô nghĩa nếu đáy không phẳng).
  const cp = coplanarityProblem(base.map((p) => p.p), 'pyramid base');
  if (cp) return { ok: false, problem: cp };
  const floatRef = fPyramid(base.map((p) => av(p.p)), av(apex.p));
  return { ok: true, answer: certifyScalar('volume', pyramidVolumeScalar(base, apex), floatRef) };
}

// ×6 tổng thể tích có dấu của lăng trụ: xẻ đáy thành quạt tam giác (b0,bi,bi+1);
// mỗi tam-giác-đáy + tam-giác-nắp tương ứng = lăng trụ tam giác = 3 tứ diện.
export function prismVolumeScalar(base: PointE[], top: PointE[]): Scalar {
  let sum = rat(0n);
  for (let i = 1; i < base.length - 1; i++) {
    const b0 = base[0].p, bi = base[i].p, bj = base[i + 1].p;
    const t0 = top[0].p, ti = top[i].p, tj = top[i + 1].p;
    sum = add(sum, tripleScalar(b0, bi, bj, t0));
    sum = add(sum, tripleScalar(bi, bj, t0, ti));
    sum = add(sum, tripleScalar(bj, t0, ti, tj));
  }
  return div(absS(sum), rat(6n));
}

function fPrism(base: Vec3[], top: Vec3[]): number {
  let s = 0;
  for (let i = 1; i < base.length - 1; i++) {
    s += scalarTriple(sub(base[i], base[0]), sub(base[i + 1], base[0]), sub(top[0], base[0]));
    s += scalarTriple(sub(base[i + 1], base[i]), sub(top[0], base[i]), sub(top[i], base[i]));
    s += scalarTriple(sub(top[0], base[i + 1]), sub(top[i], base[i + 1]), sub(top[i + 1], base[i + 1]));
  }
  return Math.abs(s) / 6;
}

// Nắp phải là đáy TỊNH TIẾN: mọi top[i]−base[i] phải bằng nhau. Nếu không (chóp cụt…) → không phải lăng trụ.
function translationMismatch(base: PointE[], top: PointE[]): string | null {
  const v0 = subV(top[0].p, base[0].p);
  for (let i = 1; i < base.length; i++) {
    const d = subV(subV(top[i].p, base[i].p), v0);
    if (!(isZeroS(d.x) && isZeroS(d.y) && isZeroS(d.z)))
      return 'prism: top face is not a parallel translate of the base (not a prism)';
  }
  return null;
}

export function computePrismVolume(base: PointE[], top: PointE[]): ComputeOutcome<ScalarAnswer> {
  if (base.length < 3) return { ok: false, problem: 'prism base needs at least 3 vertices' };
  if (top.length !== base.length) return { ok: false, problem: 'prism: base and top must have the same number of vertices' };
  const cpB = coplanarityProblem(base.map((p) => p.p), 'prism base');
  if (cpB) return { ok: false, problem: cpB };
  const cpT = coplanarityProblem(top.map((p) => p.p), 'prism top');
  if (cpT) return { ok: false, problem: cpT };
  const mism = translationMismatch(base, top);
  if (mism) return { ok: false, problem: mism };
  const floatRef = fPrism(base.map((p) => av(p.p)), top.map((p) => av(p.p)));
  return { ok: true, answer: certifyScalar('volume', prismVolumeScalar(base, top), floatRef) };
}

export function computeSphereVolume(s: SphereE): ScalarAnswer {
  // V = (4/3)·π·R³, với R³ = R²·√(R²) = r2·√r2. Hệ số (4/3)·r2·√r2 nằm trong trường (rational×căn) khi
  // √r2 biểu diễn được (thường gặp: r2 hữu tỉ) ⇒ đáp DẠNG π chính xác (vd r2=9 → 36π; r2=2 → 8√2π/3).
  const R = Math.sqrt(s.r2.approx);
  const floatRef = (4 / 3) * Math.PI * R * R * R;
  const coeff = mul(rat(4n, 3n), mul(s.r2, sqrt(s.r2)));
  return piScalarAnswer('volume', coeff, floatRef);
}

export function volumeRatio(a: Scalar, b: Scalar): ComputeOutcome<ScalarAnswer> {
  if (isZeroS(b)) return { ok: false, problem: 'volume ratio: denominator volume is zero' };
  return { ok: true, answer: certifyScalar('ratio', div(a, b), a.approx / b.approx) };
}

// ============================================================================
// THỂ TÍCH BAO LỒI của một tập điểm ("khối đa diện lồi có các đỉnh là A, B, C, M, N, P").
// ----------------------------------------------------------------------------
// Vì sao cần: nhiều đề cho một khối KHÔNG có tên trong danh mục (tứ diện/chóp/lăng trụ/chóp cụt) —
// vd ABCMNP với M, N, P là tâm ba mặt bên của lăng trụ. Khối dịch buộc phải XẺ khối (dễ thiếu mảnh)
// hoặc THAY bằng khối gần giống (chóp cụt — sai vì nắp bị xoay 180° so với đáy). Cả hai lỗi đều đo
// được trên đề thi thật. Ở đây engine tự dựng các MẶT của bao lồi rồi cộng thể tích các chóp từ một
// điểm trong — thuần số học CHÍNH XÁC trên Scalar, có float tham chiếu độc lập để tự kiểm.
//
// Cách làm (n điểm nhỏ, vét cạn): mỗi bộ ba điểm không thẳng hàng xác định một mặt phẳng; nó là mặt
// của bao lồi khi MỌI điểm còn lại nằm cùng một phía (dấu lấy từ số học chính xác khi có). Tập điểm
// nằm trên mặt đó là một mặt (đa giác lồi) — sắp theo góc quanh tâm mặt rồi quạt tam giác.
// Từ chối: điểm đồng phẳng (không thành khối) và điểm nằm HẲN TRONG bao lồi (không thể là "đỉnh" của
// khối đề mô tả — khối dịch có thể đã nhầm điểm).
// ============================================================================
type HullFace = { idx: number[] };

// Dấu của một Scalar: chính xác khi có dạng exact/sum; ngược lại so float với ngưỡng theo thang.
function signS(s: Scalar, scale: number): -1 | 0 | 1 {
  if (hasExactValue(s)) { const v = exactValueToApprox(s) as number; return v === 0 ? 0 : v < 0 ? -1 : 1; }
  if (s.sum && s.sum.terms.length === 0) return 0;
  if (s.exact !== null && s.exact.num === 0n) return 0;
  const v = s.approx;
  return Math.abs(v) <= 1e-9 * scale ? 0 : v < 0 ? -1 : 1;
}

export function convexHullFaces(pts: Vec3S[]): { ok: true; faces: HullFace[] } | { ok: false; problem: string } {
  const n = pts.length;
  if (n < 4) return { ok: false, problem: 'convex hull needs at least 4 points' };
  const fp = pts.map(toApproxVec);
  let span = 0;
  for (const p of fp) span = Math.max(span, Math.abs(p.x), Math.abs(p.y), Math.abs(p.z));
  span = Math.max(1, span);
  const faces = new Map<string, HullFace>();
  let allCoplanar = true;
  let sawPlane = false;
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) for (let k = j + 1; k < n; k++) {
    const nrm = crossV(subV(pts[j], pts[i]), subV(pts[k], pts[i]));
    const nLen = Math.sqrt(lenSqV(nrm).approx);
    if (signS(lenSqV(nrm), span * span * span * span) === 0) continue; // ba điểm thẳng hàng
    sawPlane = true;
    let pos = false, negS = false;
    const on: number[] = [];
    for (let l = 0; l < n; l++) {
      // |d|/|n| là khoảng cách điểm–mặt ⇒ ngưỡng float chuẩn hoá theo |n|·thang.
      const sg = signS(dotV(subV(pts[l], pts[i]), nrm), nLen * span);
      if (sg > 0) pos = true; else if (sg < 0) negS = true; else on.push(l);
      if (pos && negS) break;
    }
    if (pos && negS) continue;           // mặt cắt qua khối ⇒ không phải mặt bao lồi
    if (pos || negS) allCoplanar = false;
    const key = on.join(',');
    if (!faces.has(key)) faces.set(key, { idx: on });
  }
  if (!sawPlane) return { ok: false, problem: 'convex hull: all points are collinear' };
  if (allCoplanar) return { ok: false, problem: 'convex hull: all points are coplanar (no solid)' };
  const covered = new Set<number>();
  for (const f of faces.values()) for (const i of f.idx) covered.add(i);
  for (let l = 0; l < n; l++) {
    if (!covered.has(l)) return { ok: false, problem: `convex hull: point #${l + 1} lies strictly inside the hull (not a vertex)` };
  }
  return { ok: true, faces: [...faces.values()] };
}

// Sắp các điểm (đồng phẳng, tạo đa giác lồi) theo góc quanh tâm mặt — dùng float, chỉ để lấy THỨ TỰ.
function orderFace(idx: number[], fp: Vec3[]): number[] {
  const c = { x: 0, y: 0, z: 0 };
  for (const i of idx) { c.x += fp[i].x / idx.length; c.y += fp[i].y / idx.length; c.z += fp[i].z / idx.length; }
  let nrm: Vec3 = { x: 0, y: 0, z: 0 };
  for (let a = 1; a < idx.length && length(nrm) < 1e-12; a++) for (let b = a + 1; b < idx.length; b++) {
    nrm = cross(sub(fp[idx[a]], fp[idx[0]]), sub(fp[idx[b]], fp[idx[0]]));
    if (length(nrm) >= 1e-12) break;
  }
  const u = normalize(sub(fp[idx[0]], c));
  const v = normalize(cross(normalize(nrm), u));
  return idx.slice().sort((a, b) => {
    const pa = sub(fp[a], c), pb = sub(fp[b], c);
    return Math.atan2(dot(pa, v), dot(pa, u)) - Math.atan2(dot(pb, v), dot(pb, u));
  });
}

export function convexHullVolumeScalar(pts: Vec3S[]): { ok: true; scalar: Scalar; floatRef: number } | { ok: false; problem: string } {
  const hull = convexHullFaces(pts);
  if (!hull.ok) return hull;
  const fp = pts.map(toApproxVec);
  // Điểm trong: trung bình cộng các điểm (bao lồi 3 chiều ⇒ nằm hẳn trong). Tính CHÍNH XÁC.
  let cS: Vec3S = pts[0];
  for (let i = 1; i < pts.length; i++) cS = addV(cS, pts[i]);
  cS = scaleV(cS, rat(1n, BigInt(pts.length)));
  const cF = toApproxVec(cS);
  let sum = rat(0n);
  let floatRef = 0;
  for (const f of hull.faces) {
    const ord = orderFace(f.idx, fp);
    // Chóp đáy = mặt (quạt tam giác từ đỉnh đầu), đỉnh = điểm trong. Các tứ diện quạt cùng dấu ⇒ |Σ|.
    let faceS = rat(0n);
    let faceF = 0;
    for (let t = 1; t < ord.length - 1; t++) {
      faceS = add(faceS, tripleScalar(pts[ord[0]], pts[ord[t]], pts[ord[t + 1]], cS));
      faceF += scalarTriple(sub(fp[ord[t]], fp[ord[0]]), sub(fp[ord[t + 1]], fp[ord[0]]), sub(cF, fp[ord[0]]));
    }
    sum = add(sum, absS(faceS));
    floatRef += Math.abs(faceF);
  }
  return { ok: true, scalar: div(sum, rat(6n)), floatRef: floatRef / 6 };
}

export function computeConvexHullVolume(pts: PointE[]): ComputeOutcome<ScalarAnswer> {
  const r = convexHullVolumeScalar(pts.map((p) => p.p));
  if (!r.ok) return r;
  return { ok: true, answer: certifyScalar('volume', r.scalar, r.floatRef) };
}
