// api/_lib/kernel/compute/query.ts
import { z } from 'zod';
import type { EntityTable } from '../entityTable';
import type { Entity, PointE } from '../entities';
import { resolveEntityE } from '../resolveE';
import { type ComputeOutcome, type DistanceAnswer, type AngleAnswer, type ScalarAnswer, certifyScalar, mixedPiScalarAnswer } from './answer';
import { type Scalar, sqrt, mul, add, sub, rat, div, neg } from '../scalar';
import { computeDistance } from './distance';
import { computeAngle } from './angle';
import { computeTetraVolume, computePyramidVolume, computePrismVolume, volumeRatio, computeSphereVolume, computeConvexHullVolume } from './volume';
import { coverageFraction, COVERAGE_MIN } from './decompCoverage';
import { computeTriangleArea, computePolygonArea, computeSphereArea } from './area';
import { coneVolume, cylinderVolume, coneArea, cylinderArea, coneSlant, coneFrustumVolume, coneFrustumArea, coneFrustumSlant, pyramidFrustumVolume } from './roundSolids';
import { computeRelativePosition, type RelPosAnswer } from './relative';
import { computeIntersection, type IntersectionAnswer } from './intersect';
import { planeEquationText, sphereEquationText, lineEquationText } from './equation';
import { type Vec3S, vec3s, subV, crossV, dotV } from '../vec3s';
import {
  type RelationVerdict, type AngleSq, type DistSq, decideZero, decideVecZero,
  perpVec, parallelVec, collinear, coplanar4, pointOnLine, pointOnPlane, midpoint, equalLength, lengthRatio,
  skewLines, lineInPlane, angleVectors, angleLines, angleLinePlane, equalAngle,
  distSqPointPoint, distSqPointLine, distSqPointPlane, equalDistance, equidistantPoints, concurrentLines,
} from './relations';

const Tok = z.string().min(1);
const ScalarInput = z.union([z.number(), z.string().min(1)]); // r, h cho nón/trụ: số / "p/q" / "sqrt(3)"
// Khối dùng trong volume_ratio. Trước đây CHỈ nhận tứ diện/chóp, nên bài "tỉ số thể tích chóp và
// LĂNG TRỤ" — dạng sách giáo khoa rất phổ biến — bị loại ngay ở schema dù engine thừa sức tính
// (computePrismVolume có sẵn, lại còn kiểm nắp có phải tịnh tiến của đáy không).
const SolidSpec = z.union([
  z.object({ solid: z.enum(['tetrahedron', 'pyramid']), points: z.array(Tok).min(3), apex: Tok.optional() }),
  z.object({ solid: z.literal('prism'), base: z.array(Tok).min(3), top: z.array(Tok).min(3) }),
  z.object({ solid: z.literal('convex_hull'), points: z.array(Tok).min(4) }),
]);

// Toán hạng "đối tượng thẳng" cho chứng minh vuông góc/song song: đường thẳng qua 2 điểm, mặt phẳng
// qua ≥3 điểm, hoặc một đường thẳng CÓ TÊN. (Mặt phẳng có tên: truyền theo 3 điểm nằm trên nó.)
const LinearArg = z.union([
  z.object({ line: z.tuple([Tok, Tok]) }),
  z.object({ plane: z.array(Tok).min(3) }),
  z.object({ entity: Tok }),
]);
const PosInt = z.number().int().positive();
const Pair = z.tuple([Tok, Tok]);
// Toán hạng CHỈ đường thẳng / CHỈ mặt phẳng (tập con của LinearArg; resolveLinear kiểm lại loại).
const LineArg = z.union([z.object({ line: Pair }), z.object({ entity: Tok })]);
const PlaneArg = z.union([z.object({ plane: z.array(Tok).min(3) }), z.object({ entity: Tok })]);
// GÓC để so sánh: góc ABC (đỉnh B, 0°..180°, có dấu) HOẶC góc giữa hai đối tượng thẳng (0°..90°).
const AngleArg = z.union([
  z.object({ points: z.tuple([Tok, Tok, Tok]) }),
  z.object({ a: LinearArg, b: LinearArg }),
]);
// KHOẢNG CÁCH để so sánh: điểm → đường/mặt, hoặc độ dài đoạn thẳng.
const DistArg = z.union([
  z.object({ point: Tok, to: LinearArg }),
  z.object({ points: Pair }),
]);

const QueryEBase = z.union([
  z.object({ kind: z.literal('distance'), a: Tok, b: Tok }),
  z.object({ kind: z.literal('angle'), a: Tok, b: Tok }),
  z.object({ kind: z.literal('relative_position'), a: Tok, b: Tok }),
  z.object({ kind: z.literal('intersection'), a: Tok, b: Tok }),
  z.object({ kind: z.literal('equation'), target: Tok }),
  z.object({ kind: z.literal('volume'), solid: z.literal('sphere'), target: Tok }),
  z.object({ kind: z.literal('volume'), solid: z.enum(['tetrahedron', 'pyramid']), points: z.array(Tok).min(3), apex: Tok.optional() }),
  z.object({ kind: z.literal('volume'), solid: z.literal('prism'), base: z.array(Tok).min(3), top: z.array(Tok).min(3) }),
  // KHỐI ĐA DIỆN LỒI có các đỉnh cho trước ("khối đa diện lồi có các đỉnh là A, B, C, M, N, P"): engine
  // tự dựng các mặt của bao lồi rồi tính thể tích CHÍNH XÁC — không cần khối dịch xẻ khối (dễ thiếu mảnh)
  // hay thay bằng khối gần giống (chóp cụt cho nắp bị xoay — sai).
  z.object({ kind: z.literal('volume'), solid: z.literal('convex_hull'), points: z.array(Tok).min(4) }),
  z.object({ kind: z.literal('volume'), solid: z.enum(['cone', 'cylinder']), r: ScalarInput, h: ScalarInput }),
  z.object({ kind: z.literal('volume'), solid: z.literal('cone_frustum'), R: ScalarInput, r: ScalarInput, h: ScalarInput }),
  z.object({ kind: z.literal('volume'), solid: z.literal('pyramid_frustum'), s1: ScalarInput, s2: ScalarInput, h: ScalarInput }),
  z.object({ kind: z.literal('volume_ratio'), a: SolidSpec, b: SolidSpec }),
  z.object({ kind: z.literal('area'), shape: z.literal('sphere'), target: Tok }),
  z.object({ kind: z.literal('area'), shape: z.enum(['triangle', 'polygon']), points: z.array(Tok).min(3) }),
  z.object({ kind: z.literal('area'), shape: z.enum(['cone', 'cylinder']), part: z.enum(['lateral', 'total']), r: ScalarInput, h: ScalarInput }),
  z.object({ kind: z.literal('area'), shape: z.literal('cone_frustum'), part: z.enum(['lateral', 'total']), R: ScalarInput, r: ScalarInput, h: ScalarInput }),
  z.object({ kind: z.literal('slant'), r: ScalarInput, h: ScalarInput, R: ScalarInput.optional() }),
  z.object({ kind: z.literal('sphere_metric'), target: Tok, what: z.enum(['radius', 'diameter', 'top_z', 'bottom_z']) }),
  z.object({ kind: z.literal('point_coord'), target: Tok, axis: z.enum(['x', 'y', 'z']) }),
  // CHỨNG MINH QUAN HỆ: quyết định một mệnh đề kết luận bằng SỐ HỌC CHÍNH XÁC (perpVec/crossV = 0…).
  // Trả "Đúng"/"Sai" đã chứng nhận; nếu không quyết định được chính xác thì computeQuery TỪ CHỐI.
  z.object({ kind: z.literal('prove'), relation: z.enum(['perpendicular', 'parallel']), a: LinearArg, b: LinearArg }),
  z.object({ kind: z.literal('prove'), relation: z.literal('collinear'), points: z.array(Tok).length(3) }),
  z.object({ kind: z.literal('prove'), relation: z.literal('coplanar'), points: z.array(Tok).min(4) }),
  z.object({ kind: z.literal('prove'), relation: z.literal('point_on_line'), point: Tok, line: Pair }),
  z.object({ kind: z.literal('prove'), relation: z.literal('point_on_plane'), point: Tok, plane: z.array(Tok).min(3) }),
  z.object({ kind: z.literal('prove'), relation: z.literal('midpoint'), point: Tok, of: Pair }),
  z.object({ kind: z.literal('prove'), relation: z.literal('equal_length'), a: Pair, b: Pair }),
  z.object({ kind: z.literal('prove'), relation: z.literal('ratio'), a: Pair, b: Pair, value: z.tuple([PosInt, PosInt]) }),
  // Mở rộng SGK 11: chéo nhau, đường ⊂ mặt, góc bằng nhau, khoảng cách bằng nhau, cách đều, đồng quy.
  z.object({ kind: z.literal('prove'), relation: z.literal('skew'), a: LineArg, b: LineArg }),
  z.object({ kind: z.literal('prove'), relation: z.literal('line_in_plane'), line: LineArg, plane: PlaneArg }),
  z.object({ kind: z.literal('prove'), relation: z.literal('equal_angle'), a: AngleArg, b: AngleArg }),
  z.object({ kind: z.literal('prove'), relation: z.literal('equal_distance'), a: DistArg, b: DistArg }),
  z.object({ kind: z.literal('prove'), relation: z.literal('equidistant'), point: Tok, points: z.array(Tok).min(2).max(16) }),
  z.object({ kind: z.literal('prove'), relation: z.literal('concurrent'), lines: z.array(LineArg).min(3).max(12) }),
]);

// GỘP KẾT QUẢ. Vốn từ truy vấn là một danh sách ĐÓNG các khối (tứ diện, lăng trụ, chóp cụt…): khi
// bài hỏi một khối KHÔNG có trong danh sách, khối dịch buộc phải chia nhỏ thành các phần dựng được —
// rồi engine trả về nhiều số rời vì không có phép cộng. Đo trên đề thi thật: 4/5 câu hệ trả lời SAI
// thực chất là engine đã tính ĐÚNG từng mảnh (vd 12√3 + 3√3 + 6√3 + 6√3 = 27√3 đúng đáp án) mà hệ
// không cộng lại được. `combine` lấp đúng chỗ đó, cộng/trừ trên SCALAR nên giữ nguyên tính chính xác.
export type CombineQuery = { kind: 'combine'; op: 'sum' | 'diff'; of: QueryE[] };
export type QueryE = z.infer<typeof QueryEBase> | CombineQuery;
export const QueryESchema: z.ZodType<QueryE> = z.lazy(() => z.union([
  QueryEBase,
  z.object({ kind: z.literal('combine'), op: z.enum(['sum', 'diff']), of: z.array(QueryESchema).min(2).max(12) }),
])) as z.ZodType<QueryE>;

type SolidSpecT = z.infer<typeof SolidSpec>;

export type EquationAnswer = { kind: 'equation'; text: string; approximate: boolean };
// Kết quả CHỨNG MINH QUAN HỆ: holds = mệnh đề đúng hay sai (đã chứng nhận CHÍNH XÁC — nếu không chứng
// nhận được thì computeQuery trả {ok:false}, không bao giờ tạo ra answer này với phỏng đoán float).
export type RelationProofAnswer = { kind: 'prove'; relation: string; holds: boolean; text: string; approximate: boolean; detail?: string };
export type QueryAnswer =
  | DistanceAnswer | AngleAnswer | ScalarAnswer | RelPosAnswer | IntersectionAnswer | EquationAnswer | RelationProofAnswer;

function asPoints(tokens: string[], et: EntityTable): PointE[] {
  return tokens.map((t) => {
    const e: Entity = resolveEntityE(t, et);
    if (e.kind !== 'point') throw new Error(`"${t}" must be a point`);
    return e;
  });
}

// Entity có bất kỳ hệ số nền nào chỉ là float (exact=null) ⇒ phương trình chỉ gần đúng.
function entityIsApprox(e: Entity): boolean {
  const anyNull = (ss: Scalar[]) => ss.some((s) => s.exact === null);
  if (e.kind === 'plane') return anyNull([e.n.x, e.n.y, e.n.z, e.d]);
  if (e.kind === 'sphere') return anyNull([e.center.x, e.center.y, e.center.z, e.r2]);
  if (e.kind === 'line') return anyNull([e.p.x, e.p.y, e.p.z, e.dir.x, e.dir.y, e.dir.z]);
  return false;
}

// Thể tích một khối (đã kiểm đồng phẳng qua compute) dưới dạng Scalar để tính tỉ số.
function solidVolumeScalar(spec: SolidSpecT, et: EntityTable): Scalar {
  let r;
  if (spec.solid === 'prism') {
    r = computePrismVolume(asPoints(spec.base, et), asPoints(spec.top, et));
  } else if (spec.solid === 'convex_hull') {
    r = computeConvexHullVolume(asPoints(spec.points, et));
  } else {
    const pts = asPoints(spec.points, et);
    if (spec.solid === 'tetrahedron') {
      if (pts.length !== 4) throw new Error('tetrahedron needs exactly 4 points');
      r = computeTetraVolume(pts[0], pts[1], pts[2], pts[3]);
    } else {
      if (!spec.apex) throw new Error('pyramid needs an apex');
      r = computePyramidVolume(pts, asPoints([spec.apex], et)[0]);
    }
  }
  if (!r.ok) throw new Error(r.problem);
  // Giữ NGUYÊN Scalar đầy đủ (có cả dạng tổng nhiều căn) — trước đây chỉ chép {approx, exact} nên
  // tỉ số của hai đại lượng dạng tổng căn bị mất tính chính xác.
  return r.answer.scalar ?? { approx: r.answer.approx, exact: r.answer.exact };
}

// Rút danh sách tứ diện + đỉnh của một combine CỘNG các thể tích ĐA DIỆN (tứ diện/chóp) để kiểm lấp
// kín. Chỉ áp khi MỌI mảnh là tứ diện/chóp; gặp mảnh khác (trụ, cầu, lăng trụ, combine lồng) ⇒ trả
// null để BỎ QUA chốt (không mạo hiểm chặn nhầm).
function combineSumTetrahedra(query: CombineQuery, et: EntityTable): { verts: [number, number, number][]; tetras: [[number, number, number], [number, number, number], [number, number, number], [number, number, number]][] } | null {
  if (query.op !== 'sum') return null;
  const tokV3 = (tok: string): [number, number, number] => {
    const e = resolveEntityE(tok, et);
    if (e.kind !== 'point') throw new Error(`"${tok}" must be a point`);
    return [e.p.x.approx, e.p.y.approx, e.p.z.approx];
  };
  const tetras: [[number, number, number], [number, number, number], [number, number, number], [number, number, number]][] = [];
  for (const sub of query.of) {
    const s = sub as { kind?: string; solid?: string; points?: string[]; apex?: string };
    if (s.kind !== 'volume') return null;
    if (s.solid === 'tetrahedron' && s.points && s.points.length === 4) {
      const p = s.points.map(tokV3);
      tetras.push([p[0], p[1], p[2], p[3]]);
    } else if (s.solid === 'pyramid' && s.points && s.points.length >= 3 && s.apex) {
      const base = s.points.map(tokV3);
      const apex = tokV3(s.apex);
      for (let i = 1; i + 1 < base.length; i++) tetras.push([base[0], base[i], base[i + 1], apex]); // quạt tam giác đáy
    } else {
      return null; // mảnh không phải tứ diện/chóp ⇒ bỏ qua chốt
    }
  }
  const key = (v: [number, number, number]) => v.map((x) => Math.round(x * 1e6)).join(',');
  const seen = new Set<string>();
  const verts: [number, number, number][] = [];
  for (const t of tetras) for (const v of t) { const k = key(v); if (!seen.has(k)) { seen.add(k); verts.push(v); } }
  return { verts, tetras };
}

// ————————————————————————— CHỨNG MINH QUAN HỆ —————————————————————————
type ProveQuery = Extract<z.infer<typeof QueryEBase>, { kind: 'prove' }>;

function ptVec(tok: string, et: EntityTable): Vec3S {
  const e = resolveEntityE(tok, et);
  if (e.kind !== 'point') throw new Error(`"${tok}" phải là điểm`);
  return e.p;
}

// Đường thẳng/mặt phẳng → vector đặc trưng (hướng của đường / pháp tuyến của mặt) + một điểm mốc trên nó.
type Linear = { kind: 'line' | 'plane'; v: Vec3S; ref: Vec3S };
function resolveLinear(arg: z.infer<typeof LinearArg>, et: EntityTable): Linear {
  if ('line' in arg) { const A = ptVec(arg.line[0], et); return { kind: 'line', v: subV(ptVec(arg.line[1], et), A), ref: A }; }
  if ('plane' in arg) { const A = ptVec(arg.plane[0], et), B = ptVec(arg.plane[1], et), C = ptVec(arg.plane[2], et); return { kind: 'plane', v: crossV(subV(B, A), subV(C, A)), ref: A }; }
  const e = resolveEntityE((arg as { entity: string }).entity, et);
  if (e.kind === 'line') return { kind: 'line', v: e.dir, ref: e.p };
  if (e.kind === 'plane') return { kind: 'plane', v: e.n, ref: pointOnPlaneE(e.n, e.d) };
  throw new Error('toán hạng thực thể chỉ hỗ trợ đường thẳng / mặt phẳng có tên');
}
// Một điểm mốc trên mặt n·x + d = 0: chọn trục có hệ số pháp tuyến KHÁC 0 CHÍNH XÁC, đặt x_i = −d/n_i.
// Không tìm được hệ số chính xác khác 0 ⇒ ném lỗi ⇒ computeQuery từ chối (không đoán từ float).
function pointOnPlaneE(n: Vec3S, d: Scalar): Vec3S {
  const zero = rat(0n);
  for (const axis of ['x', 'y', 'z'] as const) {
    const zd = decideZero(n[axis]);
    if (zd.exact && !zd.zero) {
      const t = div(neg(d), n[axis]);
      return vec3s(axis === 'x' ? t : zero, axis === 'y' ? t : zero, axis === 'z' ? t : zero);
    }
  }
  throw new Error('mặt phẳng có tên: pháp tuyến không có hệ số chính xác khác 0 — từ chối');
}
function asLine(arg: z.infer<typeof LinearArg>, et: EntityTable): Linear {
  const l = resolveLinear(arg, et);
  if (l.kind !== 'line') throw new Error('toán hạng phải là đường thẳng');
  return l;
}
function asPlane(arg: z.infer<typeof LinearArg>, et: EntityTable): Linear {
  const l = resolveLinear(arg, et);
  if (l.kind !== 'plane') throw new Error('toán hạng phải là mặt phẳng');
  return l;
}
// Góc → bình phương cosin + dấu (không acos).
function resolveAngle(arg: z.infer<typeof AngleArg>, et: EntityTable): AngleSq {
  if ('points' in arg) {
    const [A, B, C] = arg.points.map((t) => ptVec(t, et));
    return angleVectors(subV(A, B), subV(C, B));            // góc ABC tại đỉnh B
  }
  const a = resolveLinear(arg.a, et), b = resolveLinear(arg.b, et);
  if (a.kind === b.kind) return angleLines(a.v, b.v);        // đường–đường / mặt–mặt (qua pháp tuyến)
  const line = a.kind === 'line' ? a : b, plane = a.kind === 'plane' ? a : b;
  return angleLinePlane(line.v, plane.v);
}
// Khoảng cách → bình phương dạng num/den.
function resolveDist(arg: z.infer<typeof DistArg>, et: EntityTable): DistSq {
  if ('points' in arg) return distSqPointPoint(ptVec(arg.points[0], et), ptVec(arg.points[1], et));
  const P = ptVec(arg.point, et);
  const to = resolveLinear(arg.to, et);
  return to.kind === 'line' ? distSqPointLine(P, to.ref, to.v) : distSqPointPlane(P, to.ref, to.v);
}

// Vuông góc / song song giữa đường–đường, đường–mặt, mặt–mặt. Song song có kiểm THÊM "phân biệt"
// (không trùng/không nằm trên) để nhãn "song song" đúng nghĩa, không lẫn với "trùng"/"chứa".
function provePerpPar(rel: 'perpendicular' | 'parallel', a: Linear, b: Linear): RelationVerdict {
  const line = a.kind === 'line' ? a : b.kind === 'line' ? b : null;
  const plane = a.kind === 'plane' ? a : b.kind === 'plane' ? b : null;
  if (rel === 'perpendicular') {
    if (a.kind === b.kind) return perpVec(a.v, b.v);                 // đường⊥đường, mặt⊥mặt: hai vector đặc trưng ⊥
    return parallelVec((line as Linear).v, (plane as Linear).v);    // đường⊥mặt ⇔ hướng ∥ pháp tuyến
  }
  // parallel
  if (a.kind === 'line' && b.kind === 'line') {
    const cp = parallelVec(a.v, b.v);
    if (!cp.certified || !cp.holds) return cp;
    const on = decideVecZero(crossV(subV(b.ref, a.ref), a.v));       // điểm của b có trên đường a?
    if (!on.exact) return { holds: false, certified: false, detail: 'không phân biệt được trùng/khác đường chính xác' };
    return on.zero ? { holds: false, certified: true, detail: 'hai đường TRÙNG nhau, không phải song song' } : { holds: true, certified: true, detail: 'cùng phương và phân biệt' };
  }
  if (a.kind === 'plane' && b.kind === 'plane') {
    const cp = parallelVec(a.v, b.v);
    if (!cp.certified || !cp.holds) return cp;
    const on = decideZero(dotV(subV(b.ref, a.ref), a.v));            // điểm của mặt b có thuộc mặt a?
    if (!on.exact) return { holds: false, certified: false };
    return on.zero ? { holds: false, certified: true, detail: 'hai mặt TRÙNG nhau' } : { holds: true, certified: true };
  }
  // đường ∥ mặt ⇔ hướng ⊥ pháp tuyến VÀ điểm của đường KHÔNG thuộc mặt (nếu thuộc thì đường NẰM TRÊN mặt)
  const L = line as Linear, P = plane as Linear;
  const perp = perpVec(L.v, P.v);
  if (!perp.certified || !perp.holds) return perp;
  const on = decideZero(dotV(subV(L.ref, P.ref), P.v));
  if (!on.exact) return { holds: false, certified: false };
  return on.zero ? { holds: false, certified: true, detail: 'đường NẰM TRÊN mặt, không phải song song' } : { holds: true, certified: true };
}

// Đồng phẳng ≥4 điểm: lấy bộ ba KHÔNG thẳng hàng (chính xác) đầu tiên làm mặt chuẩn, kiểm mọi điểm còn lại.
function coplanarMany(pts: Vec3S[]): RelationVerdict {
  const A = pts[0];
  let bi = -1, ci = -1;
  for (let i = 1; i < pts.length && bi < 0; i++) {
    for (let j = i + 1; j < pts.length; j++) {
      const cl = collinear(A, pts[i], pts[j]);
      if (cl.certified && !cl.holds) { bi = i; ci = j; break; }
    }
  }
  if (bi < 0) return { holds: false, certified: false, detail: 'không tìm được ba điểm không thẳng hàng (chính xác) để xác định mặt' };
  for (let k = 1; k < pts.length; k++) {
    if (k === bi || k === ci) continue;
    const cp = coplanar4(A, pts[bi], pts[ci], pts[k]);
    if (!cp.certified) return { holds: false, certified: false };
    if (!cp.holds) return { holds: false, certified: true, detail: `điểm thứ ${k + 1} không đồng phẳng` };
  }
  return { holds: true, certified: true };
}

const REL_LABEL: Record<string, string> = {
  perpendicular: 'vuông góc', parallel: 'song song', collinear: 'thẳng hàng', coplanar: 'đồng phẳng',
  point_on_line: 'điểm thuộc đường thẳng', point_on_plane: 'điểm thuộc mặt phẳng', midpoint: 'trung điểm',
  equal_length: 'hai đoạn bằng nhau', ratio: 'tỉ số độ dài',
  skew: 'hai đường thẳng chéo nhau', line_in_plane: 'đường thẳng nằm trong mặt phẳng', equal_angle: 'hai góc bằng nhau',
  equal_distance: 'hai khoảng cách bằng nhau', equidistant: 'điểm cách đều', concurrent: 'các đường thẳng đồng quy',
};

function computeProve(query: ProveQuery, et: EntityTable): ComputeOutcome<RelationProofAnswer> {
  let v: RelationVerdict;
  switch (query.relation) {
    case 'perpendicular':
    case 'parallel':
      v = provePerpPar(query.relation, resolveLinear(query.a, et), resolveLinear(query.b, et));
      break;
    case 'collinear': {
      const [A, B, C] = query.points.map((t) => ptVec(t, et));
      v = collinear(A, B, C);
      break;
    }
    case 'coplanar':
      v = coplanarMany(query.points.map((t) => ptVec(t, et)));
      break;
    case 'point_on_line':
      v = pointOnLine(ptVec(query.point, et), ptVec(query.line[0], et), ptVec(query.line[1], et));
      break;
    case 'point_on_plane':
      v = pointOnPlane(ptVec(query.point, et), ptVec(query.plane[0], et), ptVec(query.plane[1], et), ptVec(query.plane[2], et));
      break;
    case 'midpoint':
      v = midpoint(ptVec(query.point, et), ptVec(query.of[0], et), ptVec(query.of[1], et));
      break;
    case 'equal_length':
      v = equalLength(ptVec(query.a[0], et), ptVec(query.a[1], et), ptVec(query.b[0], et), ptVec(query.b[1], et));
      break;
    case 'ratio':
      v = lengthRatio(ptVec(query.a[0], et), ptVec(query.a[1], et), ptVec(query.b[0], et), ptVec(query.b[1], et), BigInt(query.value[0]), BigInt(query.value[1]));
      break;
    case 'skew': {
      const a = asLine(query.a, et), b = asLine(query.b, et);
      v = skewLines(a.ref, a.v, b.ref, b.v);
      break;
    }
    case 'line_in_plane': {
      const l = asLine(query.line, et), p = asPlane(query.plane, et);
      v = lineInPlane(l.ref, l.v, p.ref, p.v);
      break;
    }
    case 'equal_angle':
      v = equalAngle(resolveAngle(query.a, et), resolveAngle(query.b, et));
      break;
    case 'equal_distance':
      v = equalDistance(resolveDist(query.a, et), resolveDist(query.b, et));
      break;
    case 'equidistant':
      v = equidistantPoints(ptVec(query.point, et), query.points.map((t) => ptVec(t, et)));
      break;
    case 'concurrent':
      v = concurrentLines(query.lines.map((l) => { const L = asLine(l, et); return { a: L.ref, u: L.v }; }));
      break;
    default:
      return { ok: false, problem: `quan hệ chứng minh không hỗ trợ: ${(query as { relation: string }).relation}` };
  }
  const label = REL_LABEL[query.relation] ?? query.relation;
  // TỪ CHỐI khi không quyết định được bằng số học chính xác (thà từ chối còn hơn khẳng định từ float).
  if (!v.certified) return { ok: false, problem: `không chứng nhận được "${label}" bằng số học chính xác trên mô hình này — từ chối` };
  const text = `${v.holds ? 'Đúng' : 'Sai'}: ${label}${v.detail ? ` (${v.detail})` : ''}`;
  return { ok: true, answer: { kind: 'prove', relation: query.relation, holds: v.holds, text, approximate: false, detail: v.detail } };
}

export function computeQuery(query: QueryE, et: EntityTable): ComputeOutcome<QueryAnswer> {
  try {
    switch (query.kind) {
      case 'combine': {
        // Mỗi mảnh là một giá trị plain + pi·π (đa diện: pi = 0; khối tròn xoay: plain = 0; combine lồng /
        // đáp hỗn hợp: cả hai). Cộng/trừ TỪNG THÀNH PHẦN trên Scalar nên giữ nguyên tính chính xác, và
        // "khối ghép" tròn xoay (trụ khoét rãnh, trụ chồng nón…) gộp được ở tầng truy vấn.
        const ZERO = rat(0n);
        const parts: { plain: Scalar; pi: Scalar; approx: number; kind: string }[] = [];
        for (const sub of query.of) {
          const r = computeQuery(sub, et);
          if (!r.ok) return r;
          const a = r.answer as { kind?: string; scalar?: Scalar; piCoeff?: Scalar; approx?: number };
          if (!a || (!a.scalar && !a.piCoeff) || typeof a.approx !== 'number') {
            return { ok: false, problem: 'combine chỉ gộp được đại lượng SỐ (khoảng cách, diện tích, thể tích…)' };
          }
          parts.push({ plain: a.scalar ?? ZERO, pi: a.piCoeff ?? ZERO, approx: a.approx, kind: a.kind ?? 'combine' });
        }
        let plainTotal = parts[0].plain, piTotal = parts[0].pi;
        let floatRef = parts[0].approx;
        for (let i = 1; i < parts.length; i++) {
          plainTotal = query.op === 'sum' ? add(plainTotal, parts[i].plain) : sub(plainTotal, parts[i].plain);
          piTotal = query.op === 'sum' ? add(piTotal, parts[i].pi) : sub(piTotal, parts[i].pi);
          floatRef = query.op === 'sum' ? floatRef + parts[i].approx : floatRef - parts[i].approx;
        }
        // CHỐT KIỂM XẺ KHỐI: cộng các thể tích tứ diện/chóp phải LẤP KÍN khối đích. Nếu phần rã có lỗ
        // hổng (mô hình chia thiếu mảnh) thì tổng nhỏ hơn khối thật — engine sẽ đóng dấu một đáp SAI.
        // Từ chối chứng nhận thay vì trả đáp sai (chuyển "sai tự tin" → "từ chối").
        const decomp = combineSumTetrahedra(query, et);
        if (decomp) {
          const cov = coverageFraction(decomp.verts, decomp.tetras);
          if (cov < COVERAGE_MIN) {
            return { ok: false, problem: `phần rã khối không lấp kín (phủ ${(cov * 100).toFixed(0)}%) — có thể thiếu mảnh; từ chối chứng nhận` };
          }
        }
        // Vẫn qua chứng chỉ tự kiểm như mọi đáp khác: so dạng chính xác với tổng float tính độc lập
        // (float tham chiếu là tổng các .approx của từng mảnh — mỗi mảnh đã tự kiểm riêng).
        return { ok: true, answer: mixedPiScalarAnswer(parts[0].kind, plainTotal, piTotal, floatRef) };
      }
      case 'distance': return computeDistance(resolveEntityE(query.a, et), resolveEntityE(query.b, et));
      case 'angle': return computeAngle(resolveEntityE(query.a, et), resolveEntityE(query.b, et));
      case 'prove': return computeProve(query, et);
      case 'relative_position': return computeRelativePosition(resolveEntityE(query.a, et), resolveEntityE(query.b, et));
      case 'intersection': return computeIntersection(resolveEntityE(query.a, et), resolveEntityE(query.b, et));
      case 'equation': {
        const e = resolveEntityE(query.target, et);
        const text = e.kind === 'plane' ? planeEquationText(e)
          : e.kind === 'sphere' ? sphereEquationText(e)
          : e.kind === 'line' ? lineEquationText(e)
          : null;
        if (text === null) return { ok: false, problem: `no equation for a ${e.kind}` };
        return { ok: true, answer: { kind: 'equation', text, approximate: entityIsApprox(e) } };
      }
      case 'volume': {
        if (query.solid === 'sphere') {
          const e = resolveEntityE(query.target, et);
          if (e.kind !== 'sphere') return { ok: false, problem: 'volume(sphere) needs a sphere' };
          return { ok: true, answer: computeSphereVolume(e) };
        }
        if (query.solid === 'prism') {
          return computePrismVolume(asPoints(query.base, et), asPoints(query.top, et));
        }
        if (query.solid === 'convex_hull') return computeConvexHullVolume(asPoints(query.points, et));
        if (query.solid === 'cone') return { ok: true, answer: coneVolume(query.r, query.h) };
        if (query.solid === 'cylinder') return { ok: true, answer: cylinderVolume(query.r, query.h) };
        if (query.solid === 'cone_frustum') return { ok: true, answer: coneFrustumVolume(query.R, query.r, query.h) };
        if (query.solid === 'pyramid_frustum') return { ok: true, answer: pyramidFrustumVolume(query.s1, query.s2, query.h) };
        const pts = asPoints(query.points, et);
        if (query.solid === 'tetrahedron') {
          if (pts.length !== 4) return { ok: false, problem: 'tetrahedron needs exactly 4 points' };
          return computeTetraVolume(pts[0], pts[1], pts[2], pts[3]);
        }
        if (!query.apex) return { ok: false, problem: 'pyramid needs an apex' };
        return computePyramidVolume(pts, asPoints([query.apex], et)[0]);
      }
      case 'volume_ratio':
        return volumeRatio(solidVolumeScalar(query.a, et), solidVolumeScalar(query.b, et));
      case 'area': {
        if (query.shape === 'sphere') {
          const e = resolveEntityE(query.target, et);
          if (e.kind !== 'sphere') return { ok: false, problem: 'area(sphere) needs a sphere' };
          return { ok: true, answer: computeSphereArea(e) };
        }
        if (query.shape === 'cone') return { ok: true, answer: coneArea(query.r, query.h, query.part) };
        if (query.shape === 'cylinder') return { ok: true, answer: cylinderArea(query.r, query.h, query.part) };
        if (query.shape === 'cone_frustum') return { ok: true, answer: coneFrustumArea(query.R, query.r, query.h, query.part) };
        const pts = asPoints(query.points, et);
        if (query.shape === 'triangle') {
          if (pts.length !== 3) return { ok: false, problem: 'triangle area needs exactly 3 points' };
          return computeTriangleArea(pts[0], pts[1], pts[2]);
        }
        return computePolygonArea(pts);
      }
      case 'sphere_metric': {
        const e = resolveEntityE(query.target, et);
        if (e.kind !== 'sphere') return { ok: false, problem: 'sphere_metric needs a sphere' };
        // R = √(r2) tính trong TRƯỜNG (rational×căn) ⇒ bán kính/đường kính/đỉnh-chỏm ra CĂN CHÍNH XÁC
        // khi biểu diễn được (vd r2=2 → R=√2; r2=9 → R=3), thay vì số thập phân như trước.
        const R = sqrt(e.r2);
        const Rf = Math.sqrt(e.r2.approx);
        const zc = e.center.z;
        const s: Scalar = query.what === 'radius' ? R
          : query.what === 'diameter' ? mul(rat(2n), R)
          : query.what === 'top_z' ? add(zc, R)
          : sub(zc, R);
        const ref = query.what === 'radius' ? Rf
          : query.what === 'diameter' ? 2 * Rf
          : query.what === 'top_z' ? zc.approx + Rf
          : zc.approx - Rf;
        return { ok: true, answer: certifyScalar('sphere_metric', s, ref) };
      }
      case 'slant': return { ok: true, answer: query.R != null ? coneFrustumSlant(query.R, query.r, query.h) : coneSlant(query.r, query.h) };
      case 'point_coord': {
        const e = resolveEntityE(query.target, et);
        if (e.kind !== 'point') return { ok: false, problem: 'point_coord needs a point' };
        const s = query.axis === 'x' ? e.p.x : query.axis === 'y' ? e.p.y : e.p.z;
        return { ok: true, answer: certifyScalar('point_coord', s, s.approx) };
      }
    }
  } catch (e) {
    return { ok: false, problem: (e as Error).message };
  }
}
