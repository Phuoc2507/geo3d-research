# -*- coding: utf-8 -*-
"""
test_run_analysis.py — runner mini cho geo3d.analysis.run_analysis.

Ca kỳ vọng LẤY TỪ test gốc (vitest):
  api/_lib/kernel/analysis/__tests__/*.test.ts
Dùng ĐÚNG plan + ĐÚNG đáp kỳ vọng. So .text hoặc .approx theo ca.
Chạy: cd python-port && PYTHONIOENCODING=utf-8 python tests/test_run_analysis.py
"""
from __future__ import annotations
import io
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from geo3d.analysis.run_analysis import run_analysis

_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  PASS  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL  {name}   {detail}")


def close(a, b, ndigits):
    """Giống toBeCloseTo của vitest: |a-b| < 0.5·10^(-ndigits)."""
    if a is None or not isinstance(a, (int, float)) or not math.isfinite(a):
        return False
    return abs(a - b) < 0.5 * (10 ** (-ndigits))


# ============================ runAnalysis.test.ts ============================
def t_core():
    print("[runAnalysis.test.ts]")
    r = run_analysis({
        "solidName": "x", "parameters": [{"name": "t", "domain": [0, 10]}],
        "ops": [{"op": "oxyz_point", "name": "O", "at": [0, 0, 0]},
                {"op": "oxyz_point", "name": "P", "at": ["t", 0, 0]}],
        "analyze": {"kind": "solve", "parameter": "t",
                    "constraint": {"of": {"kind": "distance", "a": "O", "b": "P"}, "equals": 3},
                    "report": {"kind": "distance", "a": "O", "b": "P"}},
    })
    check("solve d(O,P)=3 → t=3", r["ok"] and close(r["parameter"]["value"], 3, 6) and close(r["answer"]["approx"], 3, 6), r)

    r = run_analysis({
        "solidName": "x", "parameters": [{"name": "t", "domain": [0, 5]}],
        "ops": [{"op": "oxyz_point", "name": "Q", "at": [2, 0, 0]},
                {"op": "oxyz_point", "name": "P", "at": ["t", 0, 0]}],
        "analyze": {"kind": "optimize", "parameter": "t", "sense": "min",
                    "objective": {"kind": "distance", "a": "P", "b": "Q"}},
    })
    check("optimize min d(P,Q) → t=2", r["ok"] and close(r["parameter"]["value"], 2, 5), r)

    r = run_analysis({
        "solidName": "x", "parameters": [{"name": "t", "domain": [0, 10]}],
        "ops": [{"op": "oxyz_point", "name": "O", "at": [0, 0, 0]},
                {"op": "oxyz_point", "name": "P", "at": ["t", 0, 0]}],
        "asserts": [{"relation": "dist", "args": ["O", "P"], "value": 99}],
        "analyze": {"kind": "solve", "parameter": "t",
                    "constraint": {"of": {"kind": "distance", "a": "O", "b": "P"}, "equals": 3},
                    "report": {"kind": "distance", "a": "O", "b": "P"}},
    })
    check("assert SAI → ok=false + violation", (not r["ok"]) and len(r["violations"]) > 0, r)

    r = run_analysis({
        "solidName": "x", "parameters": [{"name": "t", "domain": [0, 10]}],
        "ops": [{"op": "oxyz_point", "name": "O", "at": [0, 0, 0]},
                {"op": "oxyz_point", "name": "P", "at": ["t", 0, 0]}],
        "asserts": [{"relation": "dist", "args": ["O", "P"], "value": 3}],
        "analyze": {"kind": "solve", "parameter": "t",
                    "constraint": {"of": {"kind": "distance", "a": "O", "b": "P"}, "equals": 3},
                    "report": {"kind": "distance", "a": "O", "b": "P"}},
    })
    check("assert ĐÚNG → ok=true", r["ok"] and len(r["violations"]) == 0, r)

    r = run_analysis({
        "solidName": "x", "parameters": [{"name": "t", "domain": [0, 10]}],
        "ops": [{"op": "oxyz_point", "name": "O", "at": [0, 0, 0]},
                {"op": "oxyz_point", "name": "P", "at": ["t", 0, 0]}],
        "analyze": {"kind": "solve", "parameter": "t",
                    "constraint": {"of": {"kind": "distance", "a": "O", "b": "P"}, "equals": 3},
                    "report": {"kind": "distance", "a": "O", "b": "P"}},
    })
    g = r["geometry"]
    px = next((p for p in g["points"] if p["id"] == "P"), None) if g else None
    check("trả HÌNH tại nghiệm (points=2, P.x=3)",
          r["ok"] and g is not None and len(g["points"]) == 2 and px and close(px["x"], 3, 6), r)

    r = run_analysis({
        "solidName": "x",
        "solids": [{"name": "A", "kind": "cylinder", "center": [0, 0], "radius": 2, "from": 0, "to": 4},
                   {"name": "B", "kind": "cylinder", "center": [1, 0], "radius": 2, "from": 0, "to": 4}],
        "analyze": {"kind": "eval", "of": {"kind": "solid_volume", "of": ["A", "B"], "mode": "intersection"}},
    })
    check("eval solid_volume 2 trụ → HÌNH points>0",
          r["ok"] and r["geometry"] is not None and len(r["geometry"]["points"]) > 0, r)

    r = run_analysis({
        "solidName": "x",
        "parameters": [{"name": "a", "domain": [0, 4]}, {"name": "b", "domain": [0, 4]}],
        "functions": [{"name": "f", "form": "poly", "degree": 2, "through": [[0, 0], [1, 1], [2, 4]]}],
        "analyze": {"kind": "optimize_multi", "parameters": ["a", "b"], "sense": "min",
                    "objective": {"kind": "expr", "expr": "(a-1)^2 + (b-2)^2"}},
    })
    check("optimize_multi (1 function) → curves>0",
          r["ok"] and r["geometry"] is not None and len(r["geometry"]["curves"]) > 0, r)


# ============================ runAnalysis-expr.test.ts + Câu 4 ============================
def t_expr():
    print("[runAnalysis-expr.test.ts / Câu 4]")
    LANTERN = {"name": "f", "form": "poly", "degree": 2, "through": [[0, 10], [20, 14], [40, 10]]}
    r = run_analysis({"solidName": "lantern", "functions": [LANTERN],
                      "analyze": {"kind": "integrate", "variable": "z", "from": 0, "to": 40, "integrand": "2*f(z)^2"}})
    check("integrate 2 f(z)² ≈ 12949.33", r["ok"] and close(r["answer"]["approx"], 12949.33, 1), r)

    r = run_analysis({"solidName": "lantern", "functions": [LANTERN],
                      "parameters": [{"name": "z", "domain": [0, 40]}],
                      "analyze": {"kind": "optimize", "parameter": "z", "sense": "max",
                                  "objective": {"kind": "expr", "expr": "2*f(z)^2"}}})
    check("optimize expr max 2 f(z)² = 392 tại z=20",
          r["ok"] and close(r["answer"]["approx"], 392, 6) and close(r["parameter"]["value"], 20, 4), r)


# ============================ runAnalysis-functions.test.ts + Câu 1 ============================
def t_functions():
    print("[runAnalysis-functions.test.ts / Câu 1]")
    base = {
        "solidName": "f", "parameters": [{"name": "a", "domain": [-2, -0.01]}],
        "functions": [{"name": "f", "form": "poly", "degree": 2, "through": [[0, 0], [8, 0]], "leading": "a"}],
        "ops": [{"op": "curve_point", "name": "B", "f": "f", "x": 6},
                {"op": "curve_extremum", "name": "V", "f": "f", "domain": [0, 8]}],
        "analyze": {"kind": "solve", "parameter": "a",
                    "constraint": {"of": {"kind": "point_coord", "target": "B", "axis": "y"}, "equals": 4},
                    "report": {"kind": "point_coord", "target": "V", "axis": "y"}},
    }
    r = run_analysis(base)
    check("curve_point/extremum: a=-1/3, đỉnh 16/3",
          r["ok"] and close(r["parameter"]["value"], -1 / 3, 6) and close(r["answer"]["approx"], 16 / 3, 5), r)

    r = run_analysis(base)
    geo = r["geometry"]
    para = next((c for c in (geo.get("curves") or []) if c["type"] == "parabola"), None) if geo else None
    ok = (r["ok"] and geo and para
          and close(para["params"]["a"], -1 / 3, 5) and close(para["params"]["b"], 8 / 3, 5)
          and close(para["params"]["c"], 0, 6) and close(para["params"]["xMin"], 0, 6) and close(para["params"]["xMax"], 8, 6)
          and next((p for p in geo["points"] if p["id"] == "B"), None)
          and next((p for p in geo["points"] if p["id"] == "V"), None))
    check("geometry KÈM parabola + điểm B,V", bool(ok), r)

    # Câu 1: thang dài 5, tiếp tuyến tại x=6 → đỉnh 16/3 m = 533 cm
    r = run_analysis({
        "solidName": "haystack", "parameters": [{"name": "a", "domain": [-2, -0.01]}],
        "functions": [{"name": "f", "form": "poly", "degree": 2, "through": [[0, 0], [8, 0]], "leading": "a"}],
        "ops": [{"op": "curve_point", "name": "B", "f": "f", "x": 6},
                {"op": "tangent_line", "name": "T", "f": "f", "x": 6},
                {"op": "oxyz_plane", "name": "G", "by": {"form": "coeffs", "a": 0, "b": 1, "c": 0, "d": 0}},
                {"op": "oxyz_intersect", "name": "C", "a": "T", "b": "G"},
                {"op": "curve_extremum", "name": "V", "f": "f", "domain": [0, 8]}],
        "analyze": {"kind": "solve", "parameter": "a",
                    "constraint": {"of": {"kind": "distance", "a": "B", "b": "C"}, "equals": 5},
                    "report": {"kind": "point_coord", "target": "V", "axis": "y"}},
    })
    geo = r["geometry"]
    para = next((c for c in (geo.get("curves") or []) if c["type"] == "parabola"), None) if geo else None
    ok = (r["ok"] and close(r["parameter"]["value"], -1 / 3, 5) and close(r["answer"]["approx"], 16 / 3, 4)
          and round(r["answer"]["approx"] * 100) == 533
          and para and close(para["params"]["a"], -1 / 3, 5) and close(para["params"]["b"], 8 / 3, 5))
    check("Câu 1: a=-1/3, đỉnh 16/3 = 533 cm + parabola", bool(ok), r)


# ============================ multiopt / Câu 5 ============================
def t_multiopt():
    print("[runAnalysis-multiopt.test.ts / Câu 5]")
    r = run_analysis({
        "solidName": "c5",
        "functions": [{"name": "f", "form": "poly", "degree": 3, "through": [[0, 0], [2, 4], [3, 0]], "slopeAt": [[2, 0]]}],
        "parameters": [{"name": "a", "domain": [2, 3]}, {"name": "b", "domain": [2.05, 7]}],
        "analyze": {"kind": "optimize_multi", "parameters": ["a", "b"], "sense": "min",
                    "objective": {"kind": "expr", "expr": "sqrt((a-b)^2 + (f(a)-(b+1)/(b-2))^2)"}},
    })
    check("optimize_multi f'(2)=0 → 0.7485", r["ok"] and close(r["answer"]["approx"], 0.7485, 3), r)

    r = run_analysis({
        "solidName": "pool",
        "functions": [{"name": "f", "form": "poly", "degree": 3, "through": [[0, 0], [2, 4], [3, 0]], "slopeAt": [[2, 0]]}],
        "parameters": [{"name": "a", "domain": [2, 3]}, {"name": "b", "domain": [2.05, 7]}],
        "analyze": {"kind": "optimize_multi", "parameters": ["a", "b"], "sense": "min",
                    "objective": {"kind": "expr", "expr": "10*sqrt((a-b)^2 + (f(a)-(b+1)/(b-2))^2)"}},
    })
    check("Câu 5: MN ngắn nhất ≈ 7.49 m",
          r["ok"] and close(r["answer"]["approx"], 7.485, 2) and round(r["answer"]["approx"], 2) == 7.49, r)


# ============================ solids / Câu 8 ============================
def t_solids():
    print("[runAnalysis-solids.test.ts / Câu 8]")
    r = run_analysis({
        "solidName": "two-cyl",
        "solids": [{"name": "A", "kind": "cylinder", "center": [0, 0], "radius": 2, "from": 0, "to": 4},
                   {"name": "B", "kind": "cylinder", "center": [0, 0], "radius": 1, "from": 0, "to": 4}],
        "analyze": {"kind": "eval", "of": {"kind": "solid_volume", "of": ["A", "B"], "mode": "intersection"}},
    })
    check("eval trụ lồng trụ = 4π", r["ok"] and close(r["answer"]["approx"], 4 * math.pi, 5), r)

    r = run_analysis({
        "solidName": "x",
        "solids": [{"name": "A", "kind": "cylinder", "center": [0, 0], "radius": 1, "from": 0, "to": 1}],
        "analyze": {"kind": "eval", "of": {"kind": "solid_volume", "of": ["A", "Z"], "mode": "intersection"}},
    })
    check("khối chưa khai báo → ok=false", not r["ok"], r)

    r = run_analysis({
        "solidName": "cone-cyl",
        "solids": [{"name": "T", "kind": "cylinder", "center": [0, 0], "radius": 2, "from": 0, "to": 4},
                   {"name": "N", "kind": "cone", "center": [2, 0], "baseRadius": 2, "baseZ": 0, "apexZ": 4}],
        "analyze": {"kind": "eval", "of": {"kind": "solid_volume", "of": ["T", "N"], "mode": "intersection"}},
    })
    check("Câu 8: nón ∩ trụ ≈ 7.02 dm³",
          r["ok"] and close(r["answer"]["approx"], 7.0205, 3) and round(r["answer"]["approx"], 2) == 7.02, r)


# ============================ parametric-contract (Câu 9, Câu 10) ============================
def t_parametric():
    print("[parametric-contract.test.ts (Câu 9, Câu 10)]")
    r = run_analysis({
        "solidName": "poles", "parameters": [{"name": "t", "domain": [0, 20]}],
        "ops": [{"op": "oxyz_point", "name": "A", "at": [0, 0, 10]},
                {"op": "oxyz_point", "name": "B", "at": [4, 0, 6]},
                {"op": "oxyz_point", "name": "C", "at": [0, 4, 6]},
                {"op": "oxyz_circumsphere_offset", "name": "S", "of": ["A", "B", "C"], "t": "t"}],
        "analyze": {"kind": "solve", "parameter": "t",
                    "constraint": {"of": {"kind": "sphere_metric", "target": "S", "what": "top_z"}, "equals": 14},
                    "report": {"kind": "sphere_metric", "target": "S", "what": "radius"}},
    })
    check("Câu 9: R = 10 - 2√7 (approx)", r["ok"] and close(r["answer"]["approx"], 10 - 2 * math.sqrt(7), 4), r)
    check("Câu 9: text = '10 - 2√7'", r["answer"]["text"] == "10 - 2√7", r["answer"]["text"])

    r = run_analysis({
        "solidName": "panel", "parameters": [{"name": "th", "domain": [0.02, 1.55]}],
        "ops": [{"op": "oxyz_point", "name": "A", "at": [-1, 0, 0]},
                {"op": "oxyz_point", "name": "B", "at": [1, 0, 0]},
                {"op": "oxyz_point", "name": "S", "at": [0, 0, 4]},
                {"op": "oxyz_point", "name": "C", "at": [1, "3*cos(th)", "3*sin(th)"]},
                {"op": "oxyz_point", "name": "D", "at": [-1, "3*cos(th)", "3*sin(th)"]},
                {"op": "oxyz_plane", "name": "ground", "by": {"form": "coeffs", "a": 0, "b": 0, "c": 1, "d": 0}},
                {"op": "oxyz_line", "name": "SC", "by": {"form": "two_points", "a": "S", "b": "C"}},
                {"op": "oxyz_line", "name": "SD", "by": {"form": "two_points", "a": "S", "b": "D"}},
                {"op": "oxyz_intersect", "name": "C1", "a": "SC", "b": "ground"},
                {"op": "oxyz_intersect", "name": "D1", "a": "SD", "b": "ground"}],
        "analyze": {"kind": "optimize", "parameter": "th", "sense": "max",
                    "objective": {"kind": "area", "shape": "polygon", "points": ["A", "B", "C1", "D1"]}},
    })
    check("Câu 10: max diện tích hình thang ≈ 16.518",
          r["ok"] and close(r["answer"]["approx"], 16.518, 2) and close(math.sin(r["parameter"]["value"]), 0.878, 2), r)


# ============================ analyze-mover-solve.test.ts ============================
def t_mover():
    print("[analyze-mover-solve.test.ts]")
    r = run_analysis({
        "solidName": "mv",
        "ops": [{"op": "oxyz_point", "name": "A", "at": [0, 0, 0]},
                {"op": "oxyz_point", "name": "B", "at": [10, 0, 0]}],
        "parameters": [{"name": "t", "domain": [0, 1]}],
        "mover": {"point": "M", "from": "A", "to": "B"},
        "analyze": {"kind": "solve", "parameter": "t",
                    "constraint": {"of": {"kind": "distance", "a": "M", "b": "A"}, "equals": 4},
                    "report": {"kind": "distance", "a": "M", "b": "A"}},
    })
    check("mover: dist(M,A)=4 → report 4", r["ok"] and close(r["answer"]["approx"], 4, 3), r)


def main():
    for fn in (t_core, t_expr, t_functions, t_multiopt, t_solids, t_parametric, t_mover):
        fn()
    print(f"\n==== {_PASS} PASS / {_PASS + _FAIL} total ====")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
