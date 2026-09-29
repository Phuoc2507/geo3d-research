# -*- coding: utf-8 -*-
"""
test_synthetic.py — kiểm thử dialect TỔNG HỢP (synthetic) đã port sang Python.

Lấy ca từ các test gốc:
  api/_lib/kernel/__tests__/{resolve,execute,repair,unifiedPlan,integration}.test.ts

Chạy: python tests/test_synthetic.py   (runner mini utf-8, PASS/FAIL, sys.exit)
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geo3d import sym_types as ST
from geo3d import scalar as S
from geo3d.synthetic_resolve import resolve_entity
from geo3d.synthetic_execute import (
    create_empty_symbol_table, execute_op, execute_plan as sy_execute_plan,
)
from geo3d.repair import attempt_deterministic_repair
from geo3d.trace import Trace
from geo3d import run as R


def _almost(a, b, tol=1e-8):
    return abs(a - b) <= tol


# ============================ resolve.test.ts ============================
def _make_symtab():
    st = ST.SymbolTable()
    st.points.update({
        "A": ST.vec3(0, 0, 0), "B": ST.vec3(1, 0, 0), "C": ST.vec3(1, 1, 0),
        "D": ST.vec3(0, 1, 0), "A'": ST.vec3(0, 0, 2), "B'": ST.vec3(1, 0, 2),
        "C'": ST.vec3(1, 1, 2), "S": ST.vec3(0, 0, 3),
    })
    st.named_planes["ABCD"] = ["A", "B", "C", "D"]
    return st


def test_resolve_single_point():
    r = resolve_entity("A", _make_symtab())
    assert r.type == "point" and r.name == "A" and (r.pos.x, r.pos.y, r.pos.z) == (0, 0, 0)


def test_resolve_two_letter_line():
    r = resolve_entity("SA", _make_symtab())
    assert r.type == "line" and r.a == "S" and r.b == "A"
    assert (r.pos_a.z, r.pos_b.z) == (3, 0)


def test_resolve_three_letter_plane():
    r = resolve_entity("ABC", _make_symtab())
    assert r.type == "plane" and r.points == ["A", "B", "C"]
    assert (r.positions[1].x, r.positions[2].y) == (1, 1)


def test_resolve_paren_named_plane():
    r = resolve_entity("(ABCD)", _make_symtab())
    assert r.type == "plane" and r.points == ["A", "B", "C", "D"]


def test_resolve_primed_points():
    r = resolve_entity("A'B'", _make_symtab())
    assert r.type == "line" and r.a == "A'" and r.b == "B'"


def test_resolve_unresolvable_throws():
    try:
        resolve_entity("XYZ", _make_symtab())
    except ValueError as e:
        assert 'Cannot resolve entity "XYZ"' in str(e)
        return
    assert False, "phải ném"


# ============================ execute.test.ts ============================
def test_execute_square_perp_point():
    plan = {"ops": [
        {"op": "base", "shape": "square", "vertices": ["A", "B", "C", "D"], "dims": {"edge": 1}},
        {"op": "perp_point", "name": "S", "from": "A", "to": "plane", "target": "ABCD",
         "length": math.sqrt(2)},
    ]}
    st = sy_execute_plan(plan)
    assert len(st.points) == 5
    A, Sp = st.points["A"], st.points["S"]
    assert _almost(Sp.x, A.x) and _almost(Sp.y, A.y)
    assert _almost(ST.distance(Sp, A), math.sqrt(2))
    assert st.named_planes["ABCD"] == ["A", "B", "C", "D"]
    assert "A|B" in st.edges and "C|D" in st.edges and "A|D" in st.edges


def test_execute_prism_edges():
    plan = {"ops": [
        {"op": "base", "shape": "triangle", "vertices": ["A", "B", "C"],
         "dims": {"triangleType": "equilateral", "edge": 2}},
        {"op": "prism", "base": ["A", "B", "C"], "top": ["A1", "B1", "C1"], "height": 5},
    ]}
    st = sy_execute_plan(plan)
    A, A1 = st.points["A"], st.points["A1"]
    assert _almost(A1.x, A.x) and _almost(A1.y, A.y) and _almost(A1.z, A.z + 5)
    assert "A|A1" in st.edges and "B|B1" in st.edges and "A1|B1" in st.edges


def test_execute_pyramid_apex():
    plan = {"ops": [
        {"op": "base", "shape": "triangle", "vertices": ["A", "B", "C"],
         "dims": {"triangleType": "equilateral", "edge": 3}},
        {"op": "pyramid", "base": ["A", "B", "C"], "apex": "S", "height": 6},
    ]}
    st = sy_execute_plan(plan)
    A, B, C, Sp = (st.points[n] for n in ["A", "B", "C", "S"])
    assert _almost(Sp.x, (A.x + B.x + C.x) / 3) and _almost(Sp.y, (A.y + B.y + C.y) / 3)
    assert _almost(Sp.z, 6)
    assert "A|S" in st.edges and "B|S" in st.edges and "C|S" in st.edges


def test_execute_midpoint():
    plan = {"ops": [
        {"op": "base", "shape": "square", "vertices": ["A", "B", "C", "D"], "dims": {"edge": 2}},
        {"op": "point", "name": "M", "def": {"kind": "midpoint", "of": ["A", "B"]}},
    ]}
    st = sy_execute_plan(plan)
    A, B, M = st.points["A"], st.points["B"], st.points["M"]
    assert _almost(M.x, (A.x + B.x) / 2) and _almost(M.y, (A.y + B.y) / 2)
    assert "M" in st.derived_points


def test_execute_double_define_throws():
    st = create_empty_symbol_table()
    execute_op({"op": "base", "shape": "square", "vertices": ["A", "B", "C", "D"],
                "dims": {"edge": 1}}, st)
    try:
        execute_op({"op": "point", "name": "A", "def": {"kind": "midpoint", "of": ["B", "C"]}}, st)
    except ValueError as e:
        assert "already defined" in str(e)
        return
    assert False, "phải ném"


def test_execute_unknown_point_throws():
    st = create_empty_symbol_table()
    try:
        execute_op({"op": "point", "name": "M", "def": {"kind": "midpoint", "of": ["X", "Y"]}}, st)
    except ValueError as e:
        assert 'Unknown point "X"' in str(e)
        return
    assert False, "phải ném"


# ============================ repair.test.ts ============================
def _base_square_symtab():
    st = create_empty_symbol_table()
    st.points.update({"A": ST.vec3(0, 0, 0), "B": ST.vec3(1, 0, 0),
                      "C": ST.vec3(1, 1, 0), "D": ST.vec3(0, 1, 0)})
    st.named_planes["ABCD"] = ["A", "B", "C", "D"]
    return st


def _on_actual(point_tok, entity_tok, st):
    e = resolve_entity(entity_tok, st)
    p = resolve_entity(point_tok, st).pos
    if e.type == "line":
        return ST.distance_point_to_line(p, e.pos_a, e.pos_b)
    n = ST.plane_normal(e.positions[0], e.positions[1], e.positions[2])
    return ST.distance_point_to_plane(p, e.positions[0], n)


def _perp_actual(line_tok, plane_tok, st):
    l = resolve_entity(line_tok, st)
    pl = resolve_entity(plane_tok, st)
    n = ST.plane_normal(pl.positions[0], pl.positions[1], pl.positions[2])
    d = ST.sub(l.pos_b, l.pos_a)
    cos = ST.dot(d, n) / (ST.length(d) * ST.length(n))
    return 1 - abs(cos)


def test_repair_on_line_snap():
    st = _base_square_symtab()
    st.points["M"] = ST.vec3(0.5, 0.0003, 0)
    v = ST.Violation("assert_failed", relation="on", args=["M", "AB"],
                     actual=_on_actual("M", "AB", st))
    res = attempt_deterministic_repair(v, st)
    assert res.repaired
    assert _on_actual("M", "AB", st) < 1e-6


def test_repair_on_plane_snap():
    st = _base_square_symtab()
    st.points["P"] = ST.vec3(0.5, 0.5, 0.0004)
    v = ST.Violation("assert_failed", relation="on", args=["P", "ABCD"],
                     actual=_on_actual("P", "ABCD", st))
    res = attempt_deterministic_repair(v, st)
    assert res.repaired
    assert _almost(st.points["P"].z, 0, 1e-6)


def test_repair_perp_reanchor():
    st = _base_square_symtab()
    st.points["S"] = ST.vec3(0.005, 0, math.sqrt(2))
    v = ST.Violation("assert_failed", relation="perp", args=["AS", "ABCD"],
                     actual=_perp_actual("AS", "ABCD", st))
    res = attempt_deterministic_repair(v, st)
    assert res.repaired
    assert _perp_actual("AS", "ABCD", st) < 1e-6


def test_repair_declines_large_error():
    st = _base_square_symtab()
    st.points["S"] = ST.vec3(5, 5, 5)
    v = ST.Violation("assert_failed", relation="perp", args=["SA", "ABCD"],
                     actual=_perp_actual("SA", "ABCD", st))
    res = attempt_deterministic_repair(v, st)
    assert not res.repaired and res.reason


def test_repair_declines_non_assert():
    st = _base_square_symtab()
    res = attempt_deterministic_repair(ST.Violation("degenerate", message="x"), st)
    assert not res.repaired


def test_repair_declines_dist():
    st = _base_square_symtab()
    res = attempt_deterministic_repair(
        ST.Violation("assert_failed", relation="dist", args=["A", "B"]), st)
    assert not res.repaired


# ============================ trace.test.ts ============================
def test_trace_log_and_summary():
    tr = Trace()
    tr.log("execute", "m1")
    tr.log("verify", "m2")
    tr.log("verify", "m3")
    s = tr.summary()
    assert s["totalEvents"] == 3 and s["byStage"]["verify"] == 2


# ============================ unifiedPlan.test.ts (qua run.execute_plan) ============================
def test_unified_oxyz_exact_sphere_and_midpoint():
    plan = {"solidName": "mix", "ops": [
        {"op": "oxyz_point", "name": "A", "at": [0, 0, 0]},
        {"op": "oxyz_point", "name": "B", "at": [1, 2, 2]},
        {"op": "oxyz_sphere", "name": "S", "by": {"form": "center_point", "center": "A", "through": "B"}},
        {"op": "oxyz_midpoint", "name": "M", "a": "A", "b": "B"},
    ]}
    et = R.execute_plan(plan)
    assert et.spheres["S"].r2.exact == S.exact(9, 1, 1)      # R² = 1+4+4 = 9
    assert et.points["M"].p.x.exact == S.exact(1, 2, 1)      # M.x = 1/2


def test_unified_mix_float_and_exact():
    plan = {"solidName": "mix2", "ops": [
        {"op": "base", "shape": "square", "vertices": ["P", "Q", "R", "T"], "dims": {"edge": 2}},
        {"op": "oxyz_point", "name": "A", "at": [3, 4, 0]},
    ]}
    et = R.execute_plan(plan)
    assert len(et.points) == 5
    assert et.points["P"].p.x.exact is None                  # tổng hợp: float-only
    assert et.points["A"].p.x.exact == S.exact(3, 1, 1)      # Oxyz: exact
    assert "PQRT" in et.planes


def test_unified_edge_with_oxyz_points():
    """edge (op tổng hợp) tham chiếu điểm Oxyz đã mirror; không thêm điểm mới vào et."""
    plan = {"solidName": "e", "ops": [
        {"op": "oxyz_point", "name": "A", "at": [0, 0, 0]},
        {"op": "oxyz_point", "name": "B", "at": [1, 1, 1]},
        {"op": "edge", "from": "A", "to": "B"},
    ]}
    et = R.execute_plan(plan)
    assert "A|B" in et.edges
    assert set(et.points.keys()) == {"A", "B"}


# ============================ integration.test.ts ============================
def test_integration_prism_foot_intersect():
    plan = {"solidName": "ABC.A1B1C1", "ops": [
        {"op": "base", "shape": "triangle", "vertices": ["A", "B", "C"],
         "dims": {"triangleType": "equilateral", "edge": 2}},
        {"op": "prism", "base": ["A", "B", "C"], "top": ["A1", "B1", "C1"], "height": 4},
        {"op": "point", "name": "K", "def": {"kind": "midpoint", "of": ["A1", "B1"]}},
        {"op": "foot", "name": "H", "from": "K", "onto": "plane", "target": "ABC"},
        {"op": "point", "name": "M", "def": {"kind": "midpoint", "of": ["B", "C"]}},
        {"op": "point", "name": "N", "def": {"kind": "midpoint", "of": ["A", "C"]}},
        {"op": "intersect", "name": "G", "a": "AM", "b": "BN"},
    ]}
    et = R.execute_plan(plan)
    assert _almost(et.points["H"].p.z.approx, 0, 1e-8)
    # G là trọng tâm tam giác ABC (giao 2 trung tuyến)
    A = et.points["A"].p.approx()
    B = et.points["B"].p.approx()
    C = et.points["C"].p.approx()
    G = et.points["G"].p.approx()
    assert _almost(G[0], (A[0] + B[0] + C[0]) / 3, 1e-8)
    assert _almost(G[1], (A[1] + B[1] + C[1]) / 3, 1e-8)


def test_integration_full_run_with_asserts_and_query():
    """Chạy full run(): dựng hình tổng hợp + assert + query khoảng cách."""
    plan = {"solidName": "S.ABCD", "ops": [
        {"op": "base", "shape": "square", "vertices": ["A", "B", "C", "D"], "dims": {"edge": 1}},
        {"op": "perp_point", "name": "S", "from": "A", "to": "plane", "target": "ABCD",
         "length": math.sqrt(2)},
    ], "asserts": [], "queries": [
        {"kind": "distance", "a": "S", "b": "A"},
    ]}
    res = R.run(plan)
    assert res["ok"], res
    # khoảng cách S..A = sqrt(2) ≈ 1.4142
    assert res["answers"][0].startswith("1.4142")


# =============== runner mini ===============
if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}  -> {e}")
        except Exception as e:
            print(f"  ERROR {t.__name__}  -> {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} test PASS")
    sys.exit(0 if passed == len(tests) else 1)
