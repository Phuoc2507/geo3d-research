# -*- coding: utf-8 -*-
"""
oxyz.py — dịch từ api/_lib/kernel/dialects/oxyz.ts (+ resolveE.ts, compute/intersect.ts)

Thực thi op dựng hình của dialect Oxyz trên EntityTable. Mỗi op là một dict (đọc từ JSON),
ví dụ {"op": "oxyz_point", "name": "A", "at": [0, 0, 0]}.

Op 'edge' (không thuộc oxyz) KHÔNG xử lý ở đây — để đường ống cấp trên bỏ qua.

Ghi chú: giao điểm (oxyz_intersect) dịch trực tiếp từ compute/intersect.ts vào file này
(hàm _compute_intersection) để KHÔNG phải sửa compute.py (đang được port song song).
"""
from __future__ import annotations
import math
import re
from . import scalar as S
from . import vec3 as V
from . import entities as E
from . import compute as C
from .vec3 import Vec3
from .entities import Point, Line, Plane, Sphere
from .entity_table import (
    EntityTable, create_empty_entity_table,
    set_point, set_line, set_plane, set_sphere,
)
from .oxyz_input import parse_scalar, parse_vec3s
from .constructions import (
    foot_on_plane, foot_on_line, reflect_across_plane, reflect_across_line,
    orthocenter, circumcenter,
)


# ============================ RESOLVER (dịch resolveE.ts) ============================
def _tokenize_point_names(raw: str, known: set[str]) -> list[str] | None:
    """Tách token thành các tên điểm (khớp dài nhất trước)."""
    names = sorted(known, key=len, reverse=True)
    tokens: list[str] = []
    rest = raw
    while len(rest) > 0:
        match = next((n for n in names if rest.startswith(n)), None)
        if match is None:
            return None
        tokens.append(match)
        rest = rest[len(match):]
    return tokens


def resolve_entity_e(token: str, et: EntityTable):
    """token → entity. Ưu tiên tên đã đăng ký; rồi ghép tên điểm ("AB"=đường,
    "ABC…"=mặt qua 3 điểm đầu). Ném nếu không giải được."""
    paren = re.match(r"^\((.+)\)$", token)
    inner = paren.group(1) if paren else token

    if inner in et.points:
        return et.points[inner]
    if inner in et.lines:
        return et.lines[inner]
    if inner in et.planes:
        return et.planes[inner]
    if inner in et.spheres:
        return et.spheres[inner]

    tokens = _tokenize_point_names(inner, set(et.points.keys()))
    if tokens is None:
        raise ValueError(
            f'Cannot resolve entity "{token}": not a named entity or a compound of known points'
        )
    if len(tokens) == 1:
        return et.points[tokens[0]]
    if len(tokens) == 2:
        return E.line_from_two_points(et.points[tokens[0]].p, et.points[tokens[1]].p)
    positions = [et.points[n].p for n in tokens]
    if len(tokens) > 3:
        cp = C.coplanarity_problem(positions, f'compound plane "{inner}"')
        if cp:
            raise ValueError(cp)
    return E.plane_from_three_points(positions[0], positions[1], positions[2])


# ============================ GIAO ĐIỂM (dịch compute/intersect.ts) ============================
class _IntersectionAnswer:
    __slots__ = ("result", "point", "point2", "line", "circle", "chord")

    def __init__(self, result, point=None, point2=None, line=None, circle=None, chord=None):
        self.result = result
        self.point = point
        self.point2 = point2
        self.line = line
        self.circle = circle
        self.chord = chord


def _plane_signed(pl: Plane, p: Vec3) -> S.Scalar:
    return S.add(V.dot_v(pl.n, p), pl.d)


def _point_on_plane(pl: Plane) -> Vec3:
    return V.scale_v(pl.n, S.div(S.neg(pl.d), V.len_sq_v(pl.n)))


def _i_line_plane(l: Line, pl: Plane) -> _IntersectionAnswer:
    dn = V.dot_v(l.dir, pl.n)
    if S.is_zero(dn):
        return _IntersectionAnswer("coincident") if S.is_zero(_plane_signed(pl, l.p)) \
            else _IntersectionAnswer("parallel")
    t = S.neg(S.div(_plane_signed(pl, l.p), dn))  # t = −(n·A+d)/(n·dir)
    return _IntersectionAnswer("point", point=E.point_from_coords(V.add_v(l.p, V.scale_v(l.dir, t))))


def _i_plane_plane(p1: Plane, p2: Plane) -> _IntersectionAnswer:
    u = V.cross_v(p1.n, p2.n)
    if S.is_zero(V.len_sq_v(u)):
        return _IntersectionAnswer("coincident") if S.is_zero(_plane_signed(p2, _point_on_plane(p1))) \
            else _IntersectionAnswer("parallel")
    n1n1 = V.len_sq_v(p1.n)
    n2n2 = V.len_sq_v(p2.n)
    n1n2 = V.dot_v(p1.n, p2.n)
    det = V.len_sq_v(u)
    alpha = S.div(S.add(S.neg(S.mul(p1.d, n2n2)), S.mul(p2.d, n1n2)), det)
    beta = S.div(S.add(S.neg(S.mul(p2.d, n1n1)), S.mul(p1.d, n1n2)), det)
    p = V.add_v(V.scale_v(p1.n, alpha), V.scale_v(p2.n, beta))
    return _IntersectionAnswer("line", line=Line(p, u))


def _i_sphere_plane(s: Sphere, pl: Plane) -> _IntersectionAnswer:
    signed = _plane_signed(pl, s.center)
    d_sq = S.div(S.mul(signed, signed), V.len_sq_v(pl.n))
    c = S.cmp_scalar(d_sq, s.r2)
    if c > 0:
        return _IntersectionAnswer("none")
    foot = V.sub_v(s.center, V.scale_v(pl.n, S.div(signed, V.len_sq_v(pl.n))))
    if c == 0:
        return _IntersectionAnswer("tangent-point", point=E.point_from_coords(foot))
    return _IntersectionAnswer(
        "circle",
        circle={"center": E.point_from_coords(foot), "r2": S.sub(s.r2, d_sq)},
    )


def _i_line_sphere(l: Line, s: Sphere) -> _IntersectionAnswer:
    w = V.sub_v(l.p, s.center)
    a = V.len_sq_v(l.dir)
    b = S.mul(S.rat(2), V.dot_v(w, l.dir))
    cc = S.sub(V.len_sq_v(w), s.r2)
    disc = S.sub(S.mul(b, b), S.mul(S.mul(S.rat(4), a), cc))
    cmp = S.cmp_scalar(disc, S.rat(0))
    if cmp < 0:
        return _IntersectionAnswer("none")
    two_a = S.mul(S.rat(2), a)
    if cmp == 0:
        t = S.neg(S.div(b, two_a))
        return _IntersectionAnswer("tangent-point", point=E.point_from_coords(V.add_v(l.p, V.scale_v(l.dir, t))))
    sq = S.sqrt(disc)
    t1 = S.div(S.sub(S.neg(b), sq), two_a)
    t2 = S.div(S.add(S.neg(b), sq), two_a)
    return _IntersectionAnswer(
        "segment",
        point=E.point_from_coords(V.add_v(l.p, V.scale_v(l.dir, t1))),
        point2=E.point_from_coords(V.add_v(l.p, V.scale_v(l.dir, t2))),
        chord=S.sqrt(S.div(disc, a)),
    )


def _i_line_line(l1: Line, l2: Line) -> _IntersectionAnswer:
    cross = V.cross_v(l1.dir, l2.dir)
    w = V.sub_v(l2.p, l1.p)  # p2 − p1
    if S.is_zero(V.len_sq_v(cross)):
        return _IntersectionAnswer("coincident") if S.is_zero(V.len_sq_v(V.cross_v(w, l1.dir))) \
            else _IntersectionAnswer("parallel")
    if not S.is_zero(V.dot_v(w, cross)):
        return _IntersectionAnswer("none")  # chéo nhau (3D)
    t = S.div(V.dot_v(V.cross_v(w, l2.dir), cross), V.len_sq_v(cross))
    return _IntersectionAnswer("point", point=E.point_from_coords(V.add_v(l1.p, V.scale_v(l1.dir, t))))


def _compute_intersection(a, b):
    """Trả dict {"ok": True, "answer": _IntersectionAnswer} hoặc {"ok": False, "problem": str}."""
    deg = C.first_degenerate([a, b])
    if deg:
        return {"ok": False, "problem": deg}
    key = f"{a.kind}-{b.kind}"
    if key == "line-plane":
        return {"ok": True, "answer": _i_line_plane(a, b)}
    if key == "plane-line":
        return {"ok": True, "answer": _i_line_plane(b, a)}
    if key == "plane-plane":
        return {"ok": True, "answer": _i_plane_plane(a, b)}
    if key == "sphere-plane":
        return {"ok": True, "answer": _i_sphere_plane(a, b)}
    if key == "plane-sphere":
        return {"ok": True, "answer": _i_sphere_plane(b, a)}
    if key == "line-sphere":
        return {"ok": True, "answer": _i_line_sphere(a, b)}
    if key == "sphere-line":
        return {"ok": True, "answer": _i_line_sphere(b, a)}
    if key == "line-line":
        return {"ok": True, "answer": _i_line_line(a, b)}
    return {"ok": False, "problem": f"intersection not supported for {key}"}


# ============================ THỰC THI OP ============================
def _require_point(et: EntityTable, name: str) -> Point:
    p = et.points.get(name)
    if p is None:
        raise ValueError(f'Oxyz: point "{name}" is referenced before it is defined')
    return p


def execute_oxyz_op(op: dict, et: EntityTable) -> None:
    kind = op["op"]

    if kind == "oxyz_point":
        set_point(et, op["name"], parse_vec3s(op["at"]))

    elif kind == "oxyz_line":
        by = op["by"]
        if by["form"] == "two_points":
            a = _require_point(et, by["a"])
            b = _require_point(et, by["b"])
            set_line(et, op["name"], E.line_from_two_points(a.p, b.p))
        else:  # point_dir
            set_line(et, op["name"], E.line_from_point_dir(parse_vec3s(by["base"]), parse_vec3s(by["dir"])))

    elif kind == "oxyz_plane":
        by = op["by"]
        if by["form"] == "three_points":
            a = _require_point(et, by["a"])
            b = _require_point(et, by["b"])
            c = _require_point(et, by["c"])
            set_plane(et, op["name"], E.plane_from_three_points(a.p, b.p, c.p))
        elif by["form"] == "point_normal":
            point = _require_point(et, by["point"])
            set_plane(et, op["name"], E.plane_from_point_normal(point.p, parse_vec3s(by["normal"])))
        else:  # coeffs
            set_plane(et, op["name"], E.plane_from_coeffs(
                parse_scalar(by["a"]), parse_scalar(by["b"]), parse_scalar(by["c"]), parse_scalar(by["d"]),
            ))

    elif kind == "oxyz_sphere":
        by = op["by"]
        if by["form"] == "center_radius":
            center = _require_point(et, by["center"])
            r = parse_scalar(by["radius"])
            set_sphere(et, op["name"], E.sphere_from_center_radius2(center.p, S.mul(r, r)))
        elif by["form"] == "center_point":
            center = _require_point(et, by["center"])
            through = _require_point(et, by["through"])
            set_sphere(et, op["name"], E.sphere_from_center_point(center.p, through.p))
        elif by["form"] == "four_points":
            a = _require_point(et, by["a"])
            b = _require_point(et, by["b"])
            c = _require_point(et, by["c"])
            d = _require_point(et, by["d"])
            set_sphere(et, op["name"], E.sphere_from_four_points(a.p, b.p, c.p, d.p))
        else:  # equation: x²+y²+z² + a·x + b·y + c·z + d = 0
            set_sphere(et, op["name"], E.sphere_from_equation(
                parse_scalar(by["a"]), parse_scalar(by["b"]), parse_scalar(by["c"]), parse_scalar(by["d"]),
            ))

    elif kind == "oxyz_midpoint":
        a = _require_point(et, op["a"])
        b = _require_point(et, op["b"])
        set_point(et, op["name"], V.scale_v(V.add_v(a.p, b.p), S.rat(1, 2)), True)

    elif kind == "oxyz_ratio":
        a = _require_point(et, op["a"])
        b = _require_point(et, op["b"])
        t = parse_scalar(op["t"])
        set_point(et, op["name"], V.add_v(a.p, V.scale_v(V.sub_v(b.p, a.p), t)), True)  # A + t·(B−A)

    elif kind == "oxyz_centroid":
        pts = [_require_point(et, n).p for n in op["of"]]
        total = pts[0]
        for i in range(1, len(pts)):
            total = V.add_v(total, pts[i])
        set_point(et, op["name"], V.scale_v(total, S.rat(1, len(pts))), True)

    elif kind == "oxyz_reflect":
        point = _require_point(et, op["point"])
        about = _require_point(et, op["about"])
        set_point(et, op["name"], V.sub_v(V.scale_v(about.p, S.rat(2)), point.p), True)  # 2·about − point

    elif kind == "oxyz_foot":
        frm = _require_point(et, op["from"])
        target = resolve_entity_e(op["target"], et)
        if op["onto"] == "plane":
            if target.kind != "plane":
                raise ValueError(f'oxyz_foot onto plane: "{op["target"]}" is not a plane')
            set_point(et, op["name"], foot_on_plane(frm.p, target), True)
        else:
            if target.kind != "line":
                raise ValueError(f'oxyz_foot onto line: "{op["target"]}" is not a line')
            set_point(et, op["name"], foot_on_line(frm.p, target), True)

    elif kind == "oxyz_reflect_across":
        pt = _require_point(et, op["point"])
        target = resolve_entity_e(op["target"], et)
        if op["across"] == "plane":
            if target.kind != "plane":
                raise ValueError(f'oxyz_reflect_across plane: "{op["target"]}" is not a plane')
            set_point(et, op["name"], reflect_across_plane(pt.p, target), True)
        else:
            if target.kind != "line":
                raise ValueError(f'oxyz_reflect_across line: "{op["target"]}" is not a line')
            set_point(et, op["name"], reflect_across_line(pt.p, target), True)

    elif kind == "oxyz_orthocenter":
        a, b, c = (_require_point(et, n).p for n in op["of"])
        set_point(et, op["name"], orthocenter(a, b, c), True)

    elif kind == "oxyz_circumcenter":
        a, b, c = (_require_point(et, n).p for n in op["of"])
        set_point(et, op["name"], circumcenter(a, b, c), True)

    elif kind == "oxyz_intersect":
        r = _compute_intersection(resolve_entity_e(op["a"], et), resolve_entity_e(op["b"], et))
        if not r["ok"]:
            raise ValueError(r["problem"])
        res = r["answer"].result
        if res in ("point", "tangent-point"):
            set_point(et, op["name"], r["answer"].point.p, True)
        else:
            why = {
                "parallel": "hai đối tượng song song — không có giao điểm",
                "coincident": "hai đối tượng trùng nhau — vô số giao điểm, không xác định một điểm",
                "none": "hai đối tượng không cắt nhau (chéo nhau) — không có giao điểm",
                "line": "giao là một ĐƯỜNG (mặt×mặt) — dùng query intersection, không phải op oxyz_intersect",
            }.get(res, f"không phải một điểm ({res})")
            raise ValueError(f'oxyz_intersect: {op["a"]} ∩ {op["b"]} — {why}')

    elif kind == "oxyz_circumsphere_offset":
        a = _require_point(et, op["of"][0]).p
        b = _require_point(et, op["of"][1]).p
        c = _require_point(et, op["of"][2]).p
        Q = circumcenter(a, b, c)
        normal = V.cross_v(V.sub_v(b, a), V.sub_v(c, a))
        nlen = math.sqrt(V.len_sq_v(normal).approx)
        tv = parse_scalar(op["t"]).approx
        center = V.add_v(Q, V.scale_v(normal, S.num(tv / nlen)))  # Q + (t/|n|)·n  (số)
        r2 = V.len_sq_v(V.sub_v(center, a))
        set_sphere(et, op["name"], E.sphere_from_center_radius2(center, r2))

    else:
        raise ValueError(f"executeOxyzOp: op không hỗ trợ: {kind}")


def execute_oxyz_plan(ops: list[dict]) -> EntityTable:
    et = create_empty_entity_table()
    for op in ops:
        execute_oxyz_op(op, et)
    return et
