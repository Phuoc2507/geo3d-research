# -*- coding: utf-8 -*-
"""
run_analysis.py — dịch từ api/_lib/kernel/analysis/runAnalysis.ts

Bộ ĐIỀU PHỐI GIẢI TÍCH: bọc ngoài run() (hình học số) — LLM khai hình có tham số tự do +
mục tiêu/điều kiện; engine thay tham số bằng SỐ, dựng hình, đọc truy vấn, rồi tối ưu/giải
theo tham số, cuối cùng LÀM ĐẸP số bằng recognize_constant.

Hàm chính: run_analysis(plan: dict) -> dict, xử lý các analyze kind:
  eval, expr(qua nguồn số), integrate, optimize, optimize_multi, solve, solve_multi,
  cone/cylinder/solid_volume (qua nguồn số solid_volume).

KHÁC BẢN GỐC (cố ý):
  1) Python run() trả answers dạng CHUỖI, nên KHÔNG dùng được cho tối ưu/giải theo số.
     Vì vậy có helper `query_value(q, et) -> float` (song song compute_query của run.py nhưng
     trả .approx của Answer) dùng cho quét/giải/tối ưu theo tham số.
  2) expr.eval_expr của Python KHÔNG nhận tham số `funcs` như bản TS. Để biểu thức gọi được
     hàm đa thức đã khai báo (vd f(z)), ta TIÊM tạm các hàm vào expr.FUNCS quanh mỗi lần eval
     rồi khôi phục (không sửa expr.py).
  3) Trực quan hoá: `entity_table_to_geometry_data` được thay bằng bản NHẸ chỉ gồm điểm (points)
     lấy từ EntityTable — đủ cho route "points>0"/toạ độ điểm; KHÔNG dựng cạnh/mặt 3D đầy đủ.
     `function_curves`/`build_analysis_figure` là thuần SỐ (poly coeffs → curve params + điểm mẫu)
     nên vẫn dựng để lộ đồ thị hàm. Phần animation cho mover (attachMoverAnimation) là trình bày
     thuần tuý — BỎ QUA (không ảnh hưởng phép tính, chỉ khâu hiển thị).
"""
from __future__ import annotations
import math
import time

from .. import compute as C
from .. import round_solids as RS
from .. import relative as REL
from .. import equation as EQ
from ..run import execute_plan, verify_assert_e
from ..oxyz import resolve_entity_e
from . import expr as EXPR
from .quadrature import integrate
from .solver import optimize_param, solve_param, optimize_multi
from .recognize import recognize_constant
from .polyfit import fit_poly, eval_poly, deriv_poly, extremum_of_poly
from .solids import intersection_volume


# ============================ TIỆN ÍCH BIỂU THỨC ============================
def eval_expr_f(src, env=None, funcs=None):
    """eval biểu thức, cho phép gọi HÀM khai báo (funcs) bằng cách tiêm tạm vào expr.FUNCS.
    Song song evalExpr(src, env, funcs) của bản TS mà KHÔNG sửa expr.py."""
    env = env or {}
    if not funcs:
        return EXPR.eval_expr(src, env)
    saved = {}
    for name, fn in funcs.items():
        saved[name] = EXPR.FUNCS.get(name, KeyError)
        EXPR.FUNCS[name] = fn
    try:
        return EXPR.eval_expr(src, env)
    finally:
        for name, prev in saved.items():
            if prev is KeyError:
                EXPR.FUNCS.pop(name, None)
            else:
                EXPR.FUNCS[name] = prev


def _num(v):
    """evalExpr(str(v), {}) — số hoá một trường (số hoặc chuỗi biểu thức không chứa biến)."""
    return eval_expr_f(str(v), {})


def numify(c, env, params):
    """Số hoá một entry toạ độ/tham số: nếu là chuỗi CÓ chứa tên tham số → eval; ngược lại giữ nguyên."""
    if isinstance(c, str):
        import re
        if any(re.search(r"\b" + re.escape(p) + r"\b", c) for p in params):
            return eval_expr_f(c, env)
    return c


# ============================ ĐỊNH DẠNG SỐ / ĐÁP ============================
def fmt_num(x: float) -> str:
    """Số thập phân gọn cho đáp không nhận dạng được (dịch fmtNum của bản gốc)."""
    if not math.isfinite(x):
        return "(lỗi)"
    digits = 2 if abs(x) >= 1000 else 4
    val = float(f"{x:.{digits}f}")
    if val == int(val):
        return str(int(val))
    return repr(val)


def _fail(name: str, msg: str) -> dict:
    return {
        "ok": False,
        "parameter": {"name": name, "value": math.nan},
        "answer": {"approx": math.nan, "text": "(lỗi)", "approximate": True},
        "violations": [],
        "errors": [{"message": msg}],
        "geometry": None,
    }


# ============================ TRUY VẤN SỐ (song song compute_query) ============================
def _points(names, et):
    out = []
    for n in names:
        e = resolve_entity_e(n, et)
        if e.kind != "point":
            raise ValueError(f'"{n}" phải là điểm')
        out.append(e)
    return out


def query_value(q: dict, et) -> float:
    """Giống compute_query của run.py nhưng trả GIÁ TRỊ SỐ (.approx của Answer) thay vì .text.
    Dùng để tối ưu/giải theo tham số. angle trả số đo độ (Answer.approx của góc = độ)."""
    k = q["kind"]
    if k == "distance":
        return C.distance_pair(resolve_entity_e(q["a"], et), resolve_entity_e(q["b"], et)).approx
    if k == "angle":
        return C.angle(resolve_entity_e(q["a"], et), resolve_entity_e(q["b"], et)).approx
    if k == "volume":
        solid = q["solid"]
        if solid == "sphere":
            return C.sphere_volume(resolve_entity_e(q["target"], et)).approx
        if solid == "prism":
            return C.prism_volume(_points(q["base"], et), _points(q["top"], et)).approx
        if solid == "cone":
            return RS.cone_volume(q["r"], q["h"]).approx
        if solid == "cylinder":
            return RS.cylinder_volume(q["r"], q["h"]).approx
        if solid == "cone_frustum":
            return RS.cone_frustum_volume(q["R"], q["r"], q["h"]).approx
        if solid == "pyramid_frustum":
            return RS.pyramid_frustum_volume(q["s1"], q["s2"], q["h"]).approx
        pts = _points(q["points"], et)
        if solid == "tetrahedron":
            return C.tetra_volume(*pts).approx
        return C.pyramid_volume(pts, _points([q["apex"]], et)[0]).approx
    if k == "volume_ratio":
        from ..run import _solid_volume_scalar
        return C.volume_ratio(_solid_volume_scalar(q["a"], et), _solid_volume_scalar(q["b"], et)).approx
    if k == "area":
        shape = q["shape"]
        if shape == "sphere":
            return C.sphere_area(resolve_entity_e(q["target"], et)).approx
        if shape == "cone":
            return RS.cone_area(q["r"], q["h"], q["part"]).approx
        if shape == "cylinder":
            return RS.cylinder_area(q["r"], q["h"], q["part"]).approx
        if shape == "cone_frustum":
            return RS.cone_frustum_area(q["R"], q["r"], q["h"], q["part"]).approx
        pts = _points(q["points"], et)
        return (C.triangle_area(*pts) if shape == "triangle" else C.polygon_area(pts)).approx
    if k == "slant":
        return (RS.cone_frustum_slant(q["R"], q["r"], q["h"]) if q.get("R") is not None
                else RS.cone_slant(q["r"], q["h"])).approx
    if k == "sphere_metric":
        e = resolve_entity_e(q["target"], et)
        if e.kind != "sphere":
            raise ValueError("sphere_metric cần một mặt cầu")
        import math as _m
        from .. import scalar as S
        Rf = _m.sqrt(e.r2.approx)
        zc = e.center.z.approx
        what = q["what"]
        if what == "radius":
            return Rf
        if what == "diameter":
            return 2 * Rf
        if what == "top_z":
            return zc + Rf
        return zc - Rf
    if k == "point_coord":
        e = resolve_entity_e(q["target"], et)
        if e.kind != "point":
            raise ValueError("point_coord cần một điểm")
        s = e.p.x if q["axis"] == "x" else e.p.y if q["axis"] == "y" else e.p.z
        return s.approx
    raise ValueError(f"query không hỗ trợ (số): {k}")


# ============================ FIGURE (thuần SỐ) ============================
def _effective_degree(coeffs):
    deg = len(coeffs) - 1
    while deg > 0 and abs(coeffs[deg]) < 1e-12:
        deg -= 1
    return deg


def _poly_curve(cid, coeffs, x_min, x_max):
    deg = _effective_degree(coeffs)

    def c(kk):
        return coeffs[kk] if kk < len(coeffs) else 0

    if deg <= 2:
        return {"id": cid, "type": "parabola", "params": {"a": c(2), "b": c(1), "c": c(0), "xMin": x_min, "xMax": x_max}}
    if deg == 3:
        return {"id": cid, "type": "cubic", "params": {"a": c(3), "b": c(2), "c": c(1), "d": c(0), "xMin": x_min, "xMax": x_max}}
    return {"id": cid, "type": "poly", "params": {"coeffs": list(coeffs), "xMin": x_min, "xMax": x_max}}


def function_curves(inp: dict):
    curves = []
    for fn_name, coeffs in inp["polys"].items():
        dom = inp["polyDomains"].get(fn_name, (0, 10))
        curves.append(_poly_curve(f"curve_{fn_name}", coeffs, dom[0], dom[1]))
    return curves


_RING = 16
_CURVE_SAMPLES = 24


def build_analysis_figure(name: str, inp: dict) -> dict:
    points, lines = [], []
    curves = function_curves(inp)
    for p in inp["points"]:
        points.append({"id": p["id"], "label": p["id"], "x": p["x"], "y": p["y"], "z": p["z"]})
    for fn_name, coeffs in inp["polys"].items():
        dom = inp["polyDomains"].get(fn_name, (0, 10))
        x_min, x_max = dom[0], dom[1]
        for kk in range(_CURVE_SAMPLES + 1):
            x = x_min + (x_max - x_min) * kk / _CURVE_SAMPLES
            points.append({"id": f"{fn_name}_s{kk}", "label": "", "x": x, "y": eval_poly(coeffs, x), "z": 0})
    for solid_name, s in inp["solids"].items():
        def ring_points(cx, cy, r, z, tag):
            ids = []
            for kk in range(_RING):
                theta = 2 * math.pi * kk / _RING
                pid = f"{solid_name}_{tag}{kk}"
                points.append({"id": pid, "label": "", "x": cx + r * math.cos(theta), "y": cy + r * math.sin(theta), "z": z})
                ids.append(pid)
            for kk in range(_RING):
                lines.append({"id": f"{solid_name}_{tag}L{kk}", "from": ids[kk], "to": ids[(kk + 1) % _RING], "style": "solid"})
            return ids

        if s["kind"] == "cylinder":
            bottom = ring_points(s["cx"], s["cy"], s["radius"], min(s["from"], s["to"]), "b")
            top = ring_points(s["cx"], s["cy"], s["radius"], max(s["from"], s["to"]), "t")
            for kk in range(0, _RING, 4):
                lines.append({"id": f"{solid_name}_g{kk}", "from": bottom[kk], "to": top[kk], "style": "solid"})
        else:
            base = ring_points(s["cx"], s["cy"], s["baseRadius"], s["baseZ"], "b")
            apex_id = f"{solid_name}_apex"
            points.append({"id": apex_id, "label": apex_id, "x": s["cx"], "y": s["cy"], "z": s["apexZ"]})
            for kk in range(0, _RING, 4):
                lines.append({"id": f"{solid_name}_e{kk}", "from": base[kk], "to": apex_id, "style": "solid"})
    return {"name": name, "points": points, "lines": lines, "curves": curves, "spheres": [], "planes": []}


def entity_points_geometry(et, name: str) -> dict:
    """Thay thế NHẸ cho entityTableToGeometryData: chỉ trích điểm từ EntityTable (đủ cho points>0,
    toạ độ điểm). KHÔNG dựng cạnh/mặt 3D đầy đủ — phần đó là trực quan hoá (bỏ qua, xem docstring)."""
    points = []
    for nm, pt in et.points.items():
        points.append({"id": nm, "label": nm, "x": pt.p.x.approx, "y": pt.p.y.approx, "z": pt.p.z.approx})
    return {"name": name, "points": points, "lines": [], "curves": [], "spheres": [], "planes": []}


# ============================ NGUỒN SỐ ============================
def _is_expr_src(s):
    return isinstance(s, dict) and s.get("kind") == "expr"


def _is_solid_vol_src(s):
    return isinstance(s, dict) and s.get("kind") == "solid_volume"


# ============================ HÀM CHÍNH ============================
def run_analysis(plan: dict) -> dict:
    plan = dict(plan)  # bản sao nông (để có thể chèn op mover)
    ops = list(plan.get("ops", []))
    parameters = plan.get("parameters", []) or []
    functions = plan.get("functions", []) or []
    solids_decl = plan.get("solids", []) or []
    asserts = plan.get("asserts", []) or []
    solid_name = plan.get("solidName")
    analyze = plan["analyze"]
    kind = analyze["kind"]

    param_names = [p["name"] for p in parameters]

    # Vật chuyển động M(t)=A+t·(B−A) = oxyz_ratio; tiêm để optimize/solve tính được.
    mover = plan.get("mover")
    if mover and "parameter" in analyze:
        exists = any(o.get("name") == mover["point"] for o in ops)
        if not exists:
            ops = ops + [{"op": "oxyz_ratio", "name": mover["point"], "a": mover["from"], "b": mover["to"], "t": analyze["parameter"]}]

    # ---- đơn vị hiển thị + dựng đáp thống nhất ----
    answer_scale = _num(plan["answerScale"]) if plan.get("answerScale") is not None else 1.0
    answer_unit = f" {plan['answerUnit']}" if plan.get("answerUnit") else ""

    def mk_answer(val):
        display = val * answer_scale if math.isfinite(val) else val
        nice = recognize_constant(display) if math.isfinite(display) else None
        num = nice.text if nice else fmt_num(display)
        return {"approx": display, "text": num + answer_unit, "approximate": not nice}

    # ---- khớp mọi hàm khai báo tại env → coeffs + funcs ----
    def fit_at(env):
        coeffs, funcs = {}, {}
        for fd in functions:
            pts = [(eval_expr_f(str(px), env), eval_expr_f(str(py), env)) for (px, py) in fd["through"]]
            lead = eval_expr_f(str(fd["leading"]), env) if fd.get("leading") is not None else None
            slopes = [(eval_expr_f(str(sx), env), eval_expr_f(str(ss), env)) for (sx, ss) in fd.get("slopeAt", [])]
            c = fit_poly(fd["degree"], pts, lead, slopes)
            coeffs[fd["name"]] = c
            funcs[fd["name"]] = (lambda cc: (lambda x: eval_poly(cc, x)))(c)
        return coeffs, funcs

    # ---- dựng khối tại env ----
    def build_solids(env):
        out = {}
        for sd in solids_decl:
            def n(v):
                return eval_expr_f(str(v), env)
            if sd["kind"] == "cylinder":
                out[sd["name"]] = {"kind": "cylinder", "cx": n(sd["center"][0]), "cy": n(sd["center"][1]),
                                   "radius": n(sd["radius"]), "from": n(sd["from"]), "to": n(sd["to"])}
            else:
                out[sd["name"]] = {"kind": "cone", "cx": n(sd["center"][0]), "cy": n(sd["center"][1]),
                                   "baseRadius": n(sd["baseRadius"]), "baseZ": n(sd["baseZ"]), "apexZ": n(sd["apexZ"])}
        return out

    def build_figure_input(env):
        polys, _ = fit_at(env)
        poly_domains = {}
        for fd in functions:
            xs = [eval_expr_f(str(px), env) for (px, _py) in fd["through"]]
            if xs:
                poly_domains[fd["name"]] = (min(xs), max(xs))
        points = []
        for op in ops:
            if op.get("op") == "oxyz_point" and isinstance(op.get("at"), list):
                at = [eval_expr_f(str(c), env) for c in op["at"]]
                points.append({"id": str(op["name"]), "x": at[0], "y": at[1], "z": at[2] if len(at) > 2 else 0})
        return {"polys": polys, "polyDomains": poly_domains, "points": points, "solids": build_solids(env)}

    def with_function_curves(geo, env):
        if not functions:
            return geo
        if not geo:
            fig = build_analysis_figure(solid_name or "figure", build_figure_input(env))
            return fig if fig["curves"] else geo
        curves = function_curves(build_figure_input(env))
        if not curves:
            return geo
        g = dict(geo)
        g["curves"] = list(g.get("curves") or []) + curves
        return g

    def solid_volume_at(env, src):
        built = build_solids(env)
        a = built.get(src["of"][0])
        b = built.get(src["of"][1])
        if a is None:
            raise ValueError(f'Khối "{src["of"][0]}" chưa khai báo trong solids')
        if b is None:
            raise ValueError(f'Khối "{src["of"][1]}" chưa khai báo trong solids')
        return intersection_volume(a, b)["value"]

    # ---- hạ op (hàm→hình học) + thay tham số từ env ----
    def concrete_ops_env(env):
        fitted, _ = fit_at(env)

        def need_fn(name):
            c = fitted.get(name)
            if c is None:
                raise ValueError(f'Hàm "{name}" chưa khai báo trong functions')
            return c

        out = []
        for op in ops:
            o = op
            opk = o.get("op")
            if opk == "curve_point":
                c = need_fn(o["f"]); x = eval_expr_f(str(o["x"]), env)
                out.append({"op": "oxyz_point", "name": o["name"], "at": [x, eval_poly(c, x), 0]})
            elif opk == "tangent_line":
                c = need_fn(o["f"]); x = eval_expr_f(str(o["x"]), env); slope = eval_poly(deriv_poly(c), x)
                out.append({"op": "oxyz_line", "name": o["name"], "by": {"form": "point_dir", "base": [x, eval_poly(c, x), 0], "dir": [1, slope, 0]}})
            elif opk == "curve_extremum":
                c = need_fn(o["f"]); dom = o["domain"]
                ex = extremum_of_poly(c, eval_expr_f(str(dom[0]), env), eval_expr_f(str(dom[1]), env))
                if not ex:
                    raise ValueError(f'curve_extremum: hàm "{o["f"]}" không có cực trị trong miền')
                out.append({"op": "oxyz_point", "name": o["name"], "at": [ex["x"], ex["y"], 0]})
            elif opk == "oxyz_point" and isinstance(o.get("at"), list):
                out.append({**o, "at": [numify(c, env, param_names) for c in o["at"]]})
            elif opk == "oxyz_circumsphere_offset":
                out.append({**o, "t": numify(o["t"], env, param_names)})
            elif opk == "oxyz_plane" and isinstance(o.get("by"), dict) and o["by"].get("form") == "coeffs":
                by = o["by"]
                out.append({**o, "by": {**by, "a": numify(by["a"], env, param_names), "b": numify(by["b"], env, param_names),
                                        "c": numify(by["c"], env, param_names), "d": numify(by["d"], env, param_names)}})
            elif opk == "oxyz_ratio":
                out.append({**o, "t": numify(o["t"], env, param_names)})
            elif opk == "oxyz_line" and isinstance(o.get("by"), dict) and o["by"].get("form") == "point_dir":
                by = o["by"]
                out.append({**o, "by": {**by, "base": [numify(c, env, param_names) for c in by["base"]],
                                        "dir": [numify(c, env, param_names) for c in by["dir"]]}})
            else:
                out.append(op)
        return out

    def eval_query_env(env, src):
        if _is_expr_src(src):
            try:
                return eval_expr_f(src["expr"], env, fit_at(env)[1])
            except Exception:
                return None
        if _is_solid_vol_src(src):
            try:
                return solid_volume_at(env, src)
            except Exception:
                return None
        try:
            co = concrete_ops_env(env)
            et = execute_plan({"solidName": solid_name, "ops": co})
        except Exception:
            return None
        try:
            return query_value(src, et)
        except Exception:
            return None

    def eval_queries_env(env, sources):
        values = [None] * len(sources)
        geometric = []
        for i, source in enumerate(sources):
            if _is_expr_src(source):
                try:
                    values[i] = eval_expr_f(source["expr"], env, fit_at(env)[1])
                except Exception:
                    values[i] = None
            elif _is_solid_vol_src(source):
                try:
                    values[i] = solid_volume_at(env, source)
                except Exception:
                    values[i] = None
            else:
                geometric.append((i, source))
        if not geometric:
            return values
        try:
            et = execute_plan({"solidName": solid_name, "ops": concrete_ops_env(env)})
        except Exception:
            return values
        for (i, source) in geometric:
            try:
                values[i] = query_value(source, et)
            except Exception:
                values[i] = None
        return values

    # ---- integrate ----
    if kind == "integrate":
        az = analyze
        try:
            _, funcs = fit_at({})
            frm = eval_expr_f(str(az["from"]), {}, funcs)
            to = eval_expr_f(str(az["to"]), {}, funcs)
            r_val, _err = integrate(lambda x: eval_expr_f(az["integrand"], {az["variable"]: x}, funcs), frm, to)
            return {"ok": True, "parameter": {"name": az["variable"], "value": math.nan},
                    "answer": mk_answer(r_val), "violations": [], "errors": [],
                    "geometry": build_analysis_figure(az["variable"], build_figure_input({}))}
        except Exception as e:
            return _fail(az["variable"], str(e))

    # ---- eval ----
    if kind == "eval":
        src = analyze["of"]
        try:
            if _is_solid_vol_src(src):
                val = solid_volume_at({}, src)
            elif _is_expr_src(src):
                val = eval_expr_f(src["expr"], {}, fit_at({})[1])
            else:
                return _fail("-", 'analyze.eval chỉ nhận nguồn "expr" hoặc "solid_volume"')
            return {"ok": math.isfinite(val), "parameter": {"name": "-", "value": math.nan},
                    "answer": mk_answer(val), "violations": [], "errors": [],
                    "geometry": build_analysis_figure(solid_name or "figure", build_figure_input({}))}
        except Exception as e:
            return _fail("-", str(e))

    # ---- optimize_multi ----
    if kind == "optimize_multi":
        az = analyze
        src = az["objective"]
        names = az["parameters"]
        if not _is_expr_src(src):
            return _fail(",".join(names), 'optimize_multi chỉ nhận objective dạng "expr"')
        decls = [next((p for p in parameters if p["name"] == nm), None) for nm in names]
        for nm, d in zip(names, decls):
            if d is None:
                return _fail(",".join(names), f'parameter "{nm}" chưa khai báo')
        try:
            los = [eval_expr_f(str(d["domain"][0]), {}) for d in decls]
            his = [eval_expr_f(str(d["domain"][1]), {}) for d in decls]

            def objective(xs):
                env = {nm: xs[i] for i, nm in enumerate(names)}
                return eval_expr_f(src["expr"], env, fit_at(env)[1])

            best = optimize_multi(objective, los, his, az["sense"])
            env_best = {nm: best["xs"][i] for i, nm in enumerate(names)}
            return {"ok": math.isfinite(best["value"]), "parameter": {"name": ",".join(names), "value": math.nan},
                    "answer": mk_answer(best["value"]), "violations": [], "errors": [],
                    "geometry": build_analysis_figure(",".join(names), build_figure_input(env_best))}
        except Exception as e:
            return _fail(",".join(names), str(e))

    # ---- solve_multi ----
    if kind == "solve_multi":
        az = analyze
        names = az["parameters"]
        decls = [next((p for p in parameters if p["name"] == nm), None) for nm in names]
        for nm, d in zip(names, decls):
            if d is None:
                return _fail(",".join(names), f'parameter "{nm}" chưa khai báo')
        try:
            los = [eval_expr_f(str(d["domain"][0]), {}) for d in decls]
            his = [eval_expr_f(str(d["domain"][1]), {}) for d in decls]

            def env_of(xs):
                return {nm: xs[i] for i, nm in enumerate(names)}

            constraints = az["constraints"]

            def residuals_of(env):
                qvals = eval_queries_env(env, [c["of"] for c in constraints])
                res = []
                for i, c in enumerate(constraints):
                    v = qvals[i]
                    if v is None or not math.isfinite(v):
                        res.append(None)
                    else:
                        res.append(v - eval_expr_f(str(c["equals"]), env))
                return res

            def objective(xs):
                env = env_of(xs)
                s = 0.0
                for r in residuals_of(env):
                    if r is None:
                        return math.inf
                    s += r * r
                return s

            deadline = time.time() * 1000 + 20000
            best = optimize_multi(objective, los, his, "min", 8, 0, 4, deadline)
            env_best = env_of(best["xs"])
            resid_tol = 1e-4
            max_resid = 0.0
            for r in residuals_of(env_best):
                if r is None:
                    return _fail(",".join(names), "ràng buộc không đánh giá được tại nghiệm")
                max_resid = max(max_resid, abs(r))
            if max_resid > resid_tol:
                return _fail(",".join(names), f"không giải được (residual {max_resid:.2e})")
            violations, errors, geometry = [], [], None
            try:
                et = execute_plan({"solidName": solid_name, "ops": concrete_ops_env(env_best)})
                for a in asserts:
                    try:
                        v = verify_assert_e(a, et)
                        if v:
                            violations.append(v)
                    except Exception as e:
                        errors.append({"message": f"assert {a.get('relation')}: {e}"})
                if len(et.points) > 0:
                    geometry = entity_points_geometry(et, solid_name or "figure")
            except Exception as e:
                errors = [{"message": str(e)}]
            rep = eval_query_env(env_best, az["report"])
            val = math.nan if rep is None else rep
            return {"ok": len(violations) == 0 and len(errors) == 0 and math.isfinite(val),
                    "parameter": {"name": ",".join(names), "value": math.nan},
                    "answer": mk_answer(val), "violations": violations, "errors": errors,
                    "geometry": with_function_curves(geometry, env_best) if geometry
                    else build_analysis_figure(",".join(names), build_figure_input(env_best))}
        except Exception as e:
            return _fail(",".join(names), str(e))

    # ---- 1 tham số: optimize / solve ----
    pname = analyze["parameter"]
    decl = next((p for p in parameters if p["name"] == pname), None)
    if not decl:
        return _fail(pname, f'parameter "{pname}" chưa khai báo')
    lo = eval_expr_f(str(decl["domain"][0]), {})
    hi = eval_expr_f(str(decl["domain"][1]), {})

    def concrete_ops(value):
        return concrete_ops_env({pname: value})

    def eval_query(value, src):
        return eval_query_env({pname: value}, src)

    def finalize(value, src):
        env = {pname: value}
        violations, errors, val, geometry = [], [], math.nan, None
        if _is_expr_src(src) or _is_solid_vol_src(src):
            try:
                val = solid_volume_at(env, src) if _is_solid_vol_src(src) else eval_expr_f(src["expr"], env, fit_at(env)[1])
            except Exception as e:
                return _fail(pname, str(e))
            if len(ops) > 0:
                try:
                    et = execute_plan({"solidName": solid_name, "ops": concrete_ops(value)})
                    for a in asserts:
                        try:
                            v = verify_assert_e(a, et)
                            if v:
                                violations.append(v)
                        except Exception as e:
                            errors.append({"message": f"assert {a.get('relation')}: {e}"})
                    if len(et.points) > 0:
                        geometry = entity_points_geometry(et, solid_name or "figure")
                except Exception as e:
                    errors = [{"message": str(e)}]
        else:
            try:
                co = concrete_ops(value)
            except Exception as e:
                return _fail(pname, str(e))
            try:
                et = execute_plan({"solidName": solid_name, "ops": co})
            except Exception as e:
                return _fail(pname, str(e))
            try:
                val = query_value(src, et)
            except Exception:
                val = math.nan
            for a in asserts:
                try:
                    v = verify_assert_e(a, et)
                    if v:
                        violations.append(v)
                except Exception as e:
                    errors.append({"message": f"assert {a.get('relation')}: {e}"})
            if len(et.points) > 0:
                geometry = entity_points_geometry(et, solid_name or "figure")
        return {"ok": len(violations) == 0 and len(errors) == 0 and math.isfinite(val),
                "parameter": {"name": pname, "value": value},
                "answer": mk_answer(val), "violations": violations, "errors": errors,
                "geometry": with_function_curves(geometry, env)}

    if kind == "optimize":
        obj = analyze["objective"]

        def f(x):
            v = eval_query(x, obj)
            if v is None:
                raise ValueError("objective lỗi tại tham số")
            return v

        try:
            best = optimize_param(f, lo, hi, analyze["sense"])
        except Exception as e:
            return _fail(pname, str(e))
        return finalize(best["x"], obj)

    if kind == "solve":
        target = eval_expr_f(str(analyze["constraint"]["equals"]), {})
        cof = analyze["constraint"]["of"]

        def g(x):
            v = eval_query(x, cof)
            if v is None:
                raise ValueError("constraint lỗi tại tham số")
            return v

        try:
            sol = solve_param(g, target, lo, hi)
        except Exception as e:
            return _fail(pname, str(e))
        if not sol:
            return _fail(pname, "không tìm được nghiệm tham số trong miền")
        return finalize(sol["x"], analyze["report"])

    return _fail("?", f"analyze kind không hỗ trợ: {kind}")


def run_any(plan: dict):
    """Dispatch: có `analyze` ⇒ run_analysis; ngược lại run() thường."""
    if isinstance(plan, dict) and "analyze" in plan:
        return run_analysis(plan)
    from ..run import run as _run
    return _run(plan)
