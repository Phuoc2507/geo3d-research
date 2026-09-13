// api/_lib/kernel/verifyE.ts
import type { AssertOp } from './planSchema';
import type { EntityTable } from './entityTable';
import type { Violation } from './types';
import type { PointE } from './entities';
import { resolveEntityE } from './resolveE';
import { computeDistance } from './compute/distance';
import { computeAngle } from './compute/angle';
import { computeRelativePosition } from './compute/relative';
import { type ComputeOutcome, coplanarityProblem, EPS } from './compute/answer';
import { parseScalar } from './dialects/oxyzInput';

const DIST_TOL = 1e-6;
const ANGLE_TOL = 1e-3;

// Giá trị assert (dist/angle) có thể là SỐ hoặc BIỂU THỨC CĂN ("sqrt(3)", "2*sqrt(3)/3"): LLM khai
// CHÍNH XÁC, engine eval — tránh LLM tự tính số thập phân thô (mất căn đẹp + rủi ro ảo giác).
function assertValueNum(v: number | string): number {
  return typeof v === 'number' ? v : parseScalar(v).approx;
}

// Góc giữa hai TIA chung đỉnh. computeAngle dùng quy ước góc giữa hai ĐƯỜNG THẲNG (|cos|) nên
// luôn nằm trong 0–90°: một assert "góc BAC = 120°" KHÔNG BAO GIỜ đậu được, dù hình dựng đúng.
// Đo trên đề thi thật: dạng "tam giác cân có góc ở đỉnh 120°" rất hay gặp và đều bị chặn oan.
// Khi hai token có dạng hai-điểm và CHUNG một đỉnh (vd "AB" và "AC" ⇒ đỉnh A) thì đỉnh xác định,
// nên tính được góc giữa hai TIA trong khoảng 0–180°. Trả null nếu không xác định được đỉnh.
const PAIR_RE = /^([A-Z]\d*'?)([A-Z]\d*'?)$/;
function rayAngleDeg(t1: string, t2: string, et: EntityTable): number | null {
  const m1 = t1.match(PAIR_RE), m2 = t2.match(PAIR_RE);
  if (!m1 || !m2) return null;
  const a = [m1[1], m1[2]], b = [m2[1], m2[2]];
  const vertex = a.find((n) => b.includes(n));
  if (!vertex) return null;
  const other1 = a.find((n) => n !== vertex), other2 = b.find((n) => n !== vertex);
  if (!other1 || !other2) return null;
  let O: PointE, P: PointE, Q: PointE;
  try {
    const eo = resolveEntityE(vertex, et), e1 = resolveEntityE(other1, et), e2 = resolveEntityE(other2, et);
    if (eo.kind !== 'point' || e1.kind !== 'point' || e2.kind !== 'point') return null;
    O = eo; P = e1; Q = e2;
  } catch { return null; }
  const u = [P.p.x.approx - O.p.x.approx, P.p.y.approx - O.p.y.approx, P.p.z.approx - O.p.z.approx];
  const v = [Q.p.x.approx - O.p.x.approx, Q.p.y.approx - O.p.y.approx, Q.p.z.approx - O.p.z.approx];
  const nu = Math.hypot(u[0], u[1], u[2]), nv = Math.hypot(v[0], v[1], v[2]);
  if (nu < EPS || nv < EPS) return null;
  const c = (u[0] * v[0] + u[1] * v[1] + u[2] * v[2]) / (nu * nv);
  return (Math.acos(Math.min(1, Math.max(-1, c))) * 180) / Math.PI;
}

function fail(relation: string, args: string[], message: string): Violation {
  return { kind: 'assert_failed', relation, args, message };
}

// compute {ok:false} nghĩa là "không đánh giá được assert" (tổ hợp không hỗ trợ / suy biến) →
// ném để run() xếp vào `errors`, KHÔNG phải `violations` (vốn dành cho vi phạm hình học).
function mustOk<T>(r: ComputeOutcome<T>): T {
  if (!r.ok) throw new Error(r.problem);
  return r.answer;
}

// Kiểm một assert trên EntityTable, tái dùng compute layer. Trả Violation | null.
// Ném (→ run() bọc thành error) khi token không giải được hoặc assert không đánh giá được.
export function verifyAssertE(assert: AssertOp, et: EntityTable): Violation | null {
  const args = assert.args;
  switch (assert.relation) {
    case 'on': {
      const a = resolveEntityE(args[0], et);
      const b = resolveEntityE(args[1], et);
      if (a.kind === 'point') {
        // điểm thuộc đường/mặt ⇔ khoảng cách = 0
        const ans = mustOk(computeDistance(a, b));
        const tol = assert.tolerance ?? DIST_TOL;
        return ans.approx < tol ? null : fail('on', args, `${args[0]} not on ${args[1]} (distance ${ans.approx.toFixed(6)})`);
      }
      // đường/mặt "nằm trong / trùng" — KHÔNG dùng distance (compute quy ước cắt-nhau ⇒ 0);
      // phải dùng vị trí tương đối để phân biệt "chứa nhau" với "chỉ cắt nhau".
      const rel = mustOk(computeRelativePosition(a, b)).relation;
      const contained = rel === 'đường nằm trên mặt' || rel === 'trùng nhau';
      return contained ? null : fail('on', args, `${args[0]} not contained in ${args[1]} (${rel})`);
    }
    case 'dist': {
      const ans = mustOk(computeDistance(resolveEntityE(args[0], et), resolveEntityE(args[1], et)));
      const tol = assert.tolerance ?? DIST_TOL;
      return Math.abs(ans.approx - assertValueNum(assert.value!)) < tol ? null : fail('dist', args, `dist(${args[0]},${args[1]})=${ans.approx.toFixed(6)}, expected ${assert.value}`);
    }
    case 'perp': {
      const ans = mustOk(computeAngle(resolveEntityE(args[0], et), resolveEntityE(args[1], et)));
      const tol = assert.tolerance ?? ANGLE_TOL;
      return Math.abs(ans.degrees - 90) < tol ? null : fail('perp', args, `${args[0]} not perpendicular to ${args[1]} (angle ${ans.degrees.toFixed(4)}°)`);
    }
    case 'parallel': {
      const ans = mustOk(computeAngle(resolveEntityE(args[0], et), resolveEntityE(args[1], et)));
      const tol = assert.tolerance ?? ANGLE_TOL;
      return Math.abs(ans.degrees) < tol ? null : fail('parallel', args, `${args[0]} not parallel to ${args[1]} (angle ${ans.degrees.toFixed(4)}°)`);
    }
    case 'angle': {
      const ans = mustOk(computeAngle(resolveEntityE(args[0], et), resolveEntityE(args[1], et)));
      const tol = assert.tolerance ?? ANGLE_TOL;
      const want = assertValueNum(assert.value!);
      if (Math.abs(ans.degrees - want) < tol) return null;
      // Chỉ THÊM một đường đậu: góc giữa hai TIA khi đỉnh xác định (cho phép khai góc tù).
      const ray = rayAngleDeg(args[0], args[1], et);
      if (ray !== null && Math.abs(ray - want) < tol) return null;
      return fail('angle', args, `angle(${args[0]},${args[1]})=${ans.degrees.toFixed(4)}°${ray !== null ? ` (giữa hai tia: ${ray.toFixed(4)}°)` : ''}, expected ${assert.value}°`);
    }
    case 'coplanar': {
      const pts = args.map((t) => resolveEntityE(t, et));
      if (pts.some((p) => p.kind !== 'point')) throw new Error('coplanar requires point arguments');
      const cp = coplanarityProblem(pts.map((p) => (p as PointE).p), 'points', assert.tolerance ?? EPS);
      return cp ? fail('coplanar', args, cp) : null;
    }
  }
}
