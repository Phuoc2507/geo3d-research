# -*- coding: utf-8 -*-
"""
run.py — đường ống thực thi plan, dịch từ:
  api/_lib/kernel/run.ts        (run: ops -> entities -> asserts -> queries)
  api/_lib/kernel/verifyE.ts    (verify_assert_e trên EntityTable)
  api/_lib/kernel/compute/query.ts (compute_query: dispatch truy vấn)

Nhận plan dạng dict (giống JSON golden): {solidName, ops, asserts, queries}.
Thực thi op oxyz_* để dựng EntityTable (op 'edge' bỏ qua — chỉ để vẽ), kiểm ràng buộc, tính
truy vấn, rồi trả {ok, answers, violations, errors}. answers là danh sách CHUỖI đáp (như engine TS).
"""
from __future__ import annotations
import math
from . import scalar as S
from . import compute as C
from . import equation as EQ
from . import relative as REL
from . import round_solids as RS
from . import oxyz
from .oxyz import resolve_entity_e, execute_oxyz_op
from .entity_table import create_empty_entity_table
from .oxyz_input import parse_scalar
from .entities import Point, Line, Plane, Sphere
from . import entities as E
from . import synthetic_execute as SY
from . import sym_types as ST
from .plan_schema import OXYZ_OPS, OXYZ_POINT_OPS, is_oxyz_op
from .vec3 import Vec3 as Vec3E

DIST_TOL = 1e-6
ANGLE_TOL = 1e-3


# ============================ THỰC THI OPS (HỢP NHẤT) ============================
def _float_vec_to_vec3e(v: ST.Vec3) -> Vec3E:
    """Đổi Vec3 float (dialect tổng hợp) → Vec3 exact (float thuần, exact=None) để bồi vào EntityTable."""
    return Vec3E(S.num(v.x), S.num(v.y), S.num(v.z))


def _sync_symtab_to_entities(symtab: ST.SymbolTable, et, oxyz_point_names: set) -> None:
    """Bồi (thêm) mọi điểm/mặt/cạnh MỚI của SymbolTable float sang EntityTable.
    Bỏ qua điểm Oxyz (đã mirror vào symtab để op tổng hợp tham chiếu) — giữ bản EXACT trong et,
    KHÔNG ghi đè bằng float. Dịch từ syncSymtabToEntities (unifiedPlan.ts)."""
    for name, pos in symtab.points.items():
        if name in oxyz_point_names:
            continue                        # điểm Oxyz mirror — bản exact đã ở et
        if name not in et.points:
            et.points[name] = E.point_from_coords(_float_vec_to_vec3e(pos))
    for key, verts in symtab.named_planes.items():
        et.faces[key] = verts
        if len(verts) >= 3 and key not in et.planes:
            a = _float_vec_to_vec3e(symtab.points[verts[0]])
            b = _float_vec_to_vec3e(symtab.points[verts[1]])
            c = _float_vec_to_vec3e(symtab.points[verts[2]])
            et.planes[key] = E.plane_from_three_points(a, b, c)
    for e in symtab.edges:
        et.edges.add(e)
    for d in symtab.derived_points:
        et.derived_points.add(d)


def execute_plan(plan: dict):
    """Đường ống HỢP NHẤT (dịch executeUnifiedPlan, unifiedPlan.ts): mỗi op
      - oxyz_*  → execute_oxyz_op(op, et), rồi mirror điểm sang symtab (cho op tổng hợp sau).
      - còn lại → execute_op(op, symtab) rồi bồi symtab → et (KHÔNG ghi đè điểm oxyz exact).
    """
    symtab = SY.create_empty_symbol_table()
    et = create_empty_entity_table()
    oxyz_point_names: set = set()
    for op in plan.get("ops", []):
        kind = op.get("op")
        if is_oxyz_op(kind):
            execute_oxyz_op(op, et)
            if kind in OXYZ_POINT_OPS:
                name = op["name"]
                oxyz_point_names.add(name)
                # Mirror toạ độ float vào symtab để op tổng hợp (edge, foot…) tham chiếu được.
                pe = et.points.get(name)
                if pe is not None:
                    symtab.points[name] = ST.Vec3(pe.p.x.approx, pe.p.y.approx, pe.p.z.approx)
        else:
            SY.execute_op(op, symtab)
            _sync_symtab_to_entities(symtab, et, oxyz_point_names)
    return et


# ============================ VERIFY ASSERT ============================
def _assert_value_num(v):
    return v if isinstance(v, (int, float)) else parse_scalar(v).approx


def verify_assert_e(a: dict, et):
    """Trả thông điệp Violation (str) hoặc None. Ném nếu không đánh giá được (→ errors)."""
    rel = a["relation"]
    args = a["args"]
    tol = a.get("tolerance")
    if rel == "on":
        A = resolve_entity_e(args[0], et)
        B = resolve_entity_e(args[1], et)
        if A.kind == "point":
            ans = C.distance_pair(A, B)
            t = tol if tol is not None else DIST_TOL
            return None if ans.approx < t else f"{args[0]} not on {args[1]} (distance {ans.approx:.6f})"
        r = REL.compute_relative_position(A, B).relation
        return None if r in ("đường nằm trên mặt", "trùng nhau") else f"{args[0]} not contained in {args[1]} ({r})"
    if rel == "dist":
        ans = C.distance_pair(resolve_entity_e(args[0], et), resolve_entity_e(args[1], et))
        t = tol if tol is not None else DIST_TOL
        return None if abs(ans.approx - _assert_value_num(a["value"])) < t else f"dist({args[0]},{args[1]})={ans.approx:.6f}, expected {a['value']}"
    if rel in ("perp", "parallel", "angle"):
        ans = C.angle(resolve_entity_e(args[0], et), resolve_entity_e(args[1], et))
        t = tol if tol is not None else ANGLE_TOL
        deg = ans.approx                  # angle Answer .approx = số đo độ
        if rel == "perp":
            return None if abs(deg - 90) < t else f"{args[0]} not ⊥ {args[1]} ({deg:.4f}°)"
        if rel == "parallel":
            return None if abs(deg) < t else f"{args[0]} not ∥ {args[1]} ({deg:.4f}°)"
        return None if abs(deg - _assert_value_num(a["value"])) < t else f"angle({args[0]},{args[1]})={deg:.4f}°, expected {a['value']}°"
    if rel == "coplanar":
        pts = [resolve_entity_e(t_, et) for t_ in args]
        if any(p.kind != "point" for p in pts):
            raise ValueError("coplanar requires point arguments")
        cp = C.coplanarity_problem([p.p for p in pts], "points", tol if tol is not None else C.EPS)
        return cp
    raise ValueError(f"assert không hỗ trợ: {rel}")


# ============================ QUERY DISPATCH ============================
def _points(names, et):
    out = []
    for n in names:
        e = resolve_entity_e(n, et)
        if e.kind != "point":
            raise ValueError(f'"{n}" phải là điểm')
        out.append(e)
    return out


def _solid_volume_scalar(spec, et):
    pts = _points(spec["points"], et)
    if spec["solid"] == "tetrahedron":
        ans = C.tetra_volume(*pts)
    else:
        ans = C.pyramid_volume(pts, _points([spec["apex"]], et)[0])
    return S.Scalar(ans.approx, ans.exact)


def compute_query(q: dict, et) -> str:
    k = q["kind"]
    if k == "distance":
        return C.distance_pair(resolve_entity_e(q["a"], et), resolve_entity_e(q["b"], et)).text
    if k == "angle":
        return C.angle(resolve_entity_e(q["a"], et), resolve_entity_e(q["b"], et)).text
    if k == "relative_position":
        return REL.compute_relative_position(resolve_entity_e(q["a"], et), resolve_entity_e(q["b"], et)).relation
    if k == "equation":
        e = resolve_entity_e(q["target"], et)
        if e.kind == "plane":
            return EQ.plane_equation_text(e)
        if e.kind == "sphere":
            return EQ.sphere_equation_text(e)
        if e.kind == "line":
            return EQ.line_equation_text(e)
        raise ValueError(f"no equation for {e.kind}")
    if k == "volume":
        solid = q["solid"]
        if solid == "sphere":
            return C.sphere_volume(resolve_entity_e(q["target"], et)).text
        if solid == "prism":
            return C.prism_volume(_points(q["base"], et), _points(q["top"], et)).text
        if solid == "cone":
            return RS.cone_volume(q["r"], q["h"]).text
        if solid == "cylinder":
            return RS.cylinder_volume(q["r"], q["h"]).text
        if solid == "cone_frustum":
            return RS.cone_frustum_volume(q["R"], q["r"], q["h"]).text
        if solid == "pyramid_frustum":
            return RS.pyramid_frustum_volume(q["s1"], q["s2"], q["h"]).text
        pts = _points(q["points"], et)
        if solid == "tetrahedron":
            return C.tetra_volume(*pts).text
        return C.pyramid_volume(pts, _points([q["apex"]], et)[0]).text
    if k == "volume_ratio":
        return C.volume_ratio(_solid_volume_scalar(q["a"], et), _solid_volume_scalar(q["b"], et)).text
    if k == "area":
        shape = q["shape"]
        if shape == "sphere":
            return C.sphere_area(resolve_entity_e(q["target"], et)).text
        if shape == "cone":
            return RS.cone_area(q["r"], q["h"], q["part"]).text
        if shape == "cylinder":
            return RS.cylinder_area(q["r"], q["h"], q["part"]).text
        if shape == "cone_frustum":
            return RS.cone_frustum_area(q["R"], q["r"], q["h"], q["part"]).text
        pts = _points(q["points"], et)
        return (C.triangle_area(*pts) if shape == "triangle" else C.polygon_area(pts)).text
    if k == "slant":
        return (RS.cone_frustum_slant(q["R"], q["r"], q["h"]) if q.get("R") is not None else RS.cone_slant(q["r"], q["h"])).text
    if k == "sphere_metric":
        e = resolve_entity_e(q["target"], et)
        if e.kind != "sphere":
            raise ValueError("sphere_metric cần một mặt cầu")
        R = S.sqrt(e.r2)
        Rf = math.sqrt(e.r2.approx)
        zc = e.center.z
        what = q["what"]
        if what == "radius":
            s, ref = R, Rf
        elif what == "diameter":
            s, ref = S.mul(S.rat(2), R), 2 * Rf
        elif what == "top_z":
            s, ref = S.add(zc, R), zc.approx + Rf
        else:
            s, ref = S.sub(zc, R), zc.approx - Rf
        return C.certify_scalar("sphere_metric", s, ref).text
    if k == "point_coord":
        e = resolve_entity_e(q["target"], et)
        if e.kind != "point":
            raise ValueError("point_coord cần một điểm")
        s = e.p.x if q["axis"] == "x" else e.p.y if q["axis"] == "y" else e.p.z
        return C.certify_scalar("point_coord", s, s.approx).text
    raise ValueError(f"query không hỗ trợ: {k}")


# ============================ RUN ============================
def run(plan: dict) -> dict:
    violations, errors, answers = [], [], []
    try:
        et = execute_plan(plan)
    except Exception as e:
        return {"ok": False, "answers": [], "violations": [], "errors": [str(e)]}

    for a in plan.get("asserts", []):
        try:
            v = verify_assert_e(a, et)
            if v:
                violations.append(v)
        except Exception as e:
            errors.append(f"assert {a.get('relation')}: {e}")

    for q in plan.get("queries", []):
        try:
            answers.append(compute_query(q, et))
        except Exception as e:
            errors.append(f"query {q.get('kind')}: {e}")

    return {"ok": len(violations) == 0 and len(errors) == 0,
            "answers": answers, "violations": violations, "errors": errors}
