# -*- coding: utf-8 -*-
"""
intersect.py — dịch từ api/_lib/kernel/compute/intersect.ts

GIAO của hai thực thể. Trả về IntersectionAnswer(result, point, point2, line, circle, chord).
  result ∈ {point, line, circle, tangent-point, segment, none, coincident, parallel}
Toàn bộ tính trên số hữu tỉ/căn exact khi có thể; toạ độ giao là nhị thức căn thì rời trường
(exact=None → số) NHƯNG chord=√(Δ/a) vẫn ở dưới một căn nên giữ exact được.
"""
from __future__ import annotations
from . import scalar as S
from . import vec3 as V
from .vec3 import Vec3
from .scalar import Scalar
from .entities import Point, Line, Plane, Sphere


class IntersectionAnswer:
    kind = "intersection"

    def __init__(self, result: str, point=None, point2=None, line=None, circle=None, chord=None):
        self.result = result
        self.point = point
        self.point2 = point2
        self.line = line
        self.circle = circle      # {"center": Point, "r2": Scalar}
        self.chord = chord        # Scalar

    def __repr__(self):
        return f"intersection: {self.result}"


def _plane_signed(pl: Plane, p: Vec3) -> Scalar:
    return S.add(V.dot_v(pl.n, p), pl.d)


def _point_on_plane(pl: Plane) -> Vec3:
    return V.scale_v(pl.n, S.div(S.neg(pl.d), V.len_sq_v(pl.n)))


def _pt(p: Vec3) -> Point:
    return Point(p)


def _i_line_plane(l: Line, pl: Plane) -> IntersectionAnswer:
    dn = V.dot_v(l.dir, pl.n)
    if S.is_zero(dn):
        return (IntersectionAnswer("coincident") if S.is_zero(_plane_signed(pl, l.p))
                else IntersectionAnswer("parallel"))
    t = S.neg(S.div(_plane_signed(pl, l.p), dn))          # t = −(n·A+d)/(n·dir)
    return IntersectionAnswer("point", point=_pt(V.add_v(l.p, V.scale_v(l.dir, t))))


def _i_plane_plane(p1: Plane, p2: Plane) -> IntersectionAnswer:
    u = V.cross_v(p1.n, p2.n)
    if S.is_zero(V.len_sq_v(u)):
        return (IntersectionAnswer("coincident") if S.is_zero(_plane_signed(p2, _point_on_plane(p1)))
                else IntersectionAnswer("parallel"))
    # p = α·n1 + β·n2 thoả n1·p=−d1, n2·p=−d2. det = |n1|²|n2|² − (n1·n2)² = |u|².
    n1n1 = V.len_sq_v(p1.n)
    n2n2 = V.len_sq_v(p2.n)
    n1n2 = V.dot_v(p1.n, p2.n)
    det = V.len_sq_v(u)
    alpha = S.div(S.add(S.neg(S.mul(p1.d, n2n2)), S.mul(p2.d, n1n2)), det)
    beta = S.div(S.add(S.neg(S.mul(p2.d, n1n1)), S.mul(p1.d, n1n2)), det)
    p = V.add_v(V.scale_v(p1.n, alpha), V.scale_v(p2.n, beta))
    return IntersectionAnswer("line", line=Line(p, u))


def _i_sphere_plane(s: Sphere, pl: Plane) -> IntersectionAnswer:
    signed = _plane_signed(pl, s.center)
    d_sq = S.div(S.mul(signed, signed), V.len_sq_v(pl.n))
    c = S.cmp_scalar(d_sq, s.r2)
    if c > 0:
        return IntersectionAnswer("none")
    foot = V.sub_v(s.center, V.scale_v(pl.n, S.div(signed, V.len_sq_v(pl.n))))
    if c == 0:
        return IntersectionAnswer("tangent-point", point=_pt(foot))
    return IntersectionAnswer("circle", circle={"center": _pt(foot), "r2": S.sub(s.r2, d_sq)})


def _i_line_sphere(l: Line, s: Sphere) -> IntersectionAnswer:
    # a·t² + b·t + c = 0, a=|dir|², b=2(w·dir), c=|w|²−r², w=A−C.
    w = V.sub_v(l.p, s.center)
    a = V.len_sq_v(l.dir)
    b = S.mul(S.rat(2), V.dot_v(w, l.dir))
    c = S.sub(V.len_sq_v(w), s.r2)
    disc = S.sub(S.mul(b, b), S.mul(S.mul(S.rat(4), a), c))
    cmp = S.cmp_scalar(disc, S.rat(0))
    if cmp < 0:
        return IntersectionAnswer("none")
    two_a = S.mul(S.rat(2), a)
    if cmp == 0:
        t = S.neg(S.div(b, two_a))
        return IntersectionAnswer("tangent-point", point=_pt(V.add_v(l.p, V.scale_v(l.dir, t))))
    sq = S.sqrt(disc)
    t1 = S.div(S.sub(S.neg(b), sq), two_a)
    t2 = S.div(S.add(S.neg(b), sq), two_a)
    return IntersectionAnswer(
        "segment",
        point=_pt(V.add_v(l.p, V.scale_v(l.dir, t1))),
        point2=_pt(V.add_v(l.p, V.scale_v(l.dir, t2))),
        chord=S.sqrt(S.div(disc, a)),
    )


def _i_line_line(l1: Line, l2: Line) -> IntersectionAnswer:
    cross = V.cross_v(l1.dir, l2.dir)
    w = V.sub_v(l2.p, l1.p)                                # p2 − p1
    if S.is_zero(V.len_sq_v(cross)):
        return (IntersectionAnswer("coincident") if S.is_zero(V.len_sq_v(V.cross_v(w, l1.dir)))
                else IntersectionAnswer("parallel"))
    if not S.is_zero(V.dot_v(w, cross)):
        return IntersectionAnswer("none")                 # chéo nhau (3D)
    t = S.div(V.dot_v(V.cross_v(w, l2.dir), cross), V.len_sq_v(cross))
    return IntersectionAnswer("point", point=_pt(V.add_v(l1.p, V.scale_v(l1.dir, t))))


def compute_intersection(a, b) -> IntersectionAnswer:
    from .compute import first_degenerate
    deg = first_degenerate([a, b])
    if deg:
        raise ValueError(deg)
    key = f"{a.kind}-{b.kind}"
    if key == "line-plane":
        return _i_line_plane(a, b)
    if key == "plane-line":
        return _i_line_plane(b, a)
    if key == "plane-plane":
        return _i_plane_plane(a, b)
    if key == "sphere-plane":
        return _i_sphere_plane(a, b)
    if key == "plane-sphere":
        return _i_sphere_plane(b, a)
    if key == "line-sphere":
        return _i_line_sphere(a, b)
    if key == "sphere-line":
        return _i_line_sphere(b, a)
    if key == "line-line":
        return _i_line_line(a, b)
    raise ValueError(f"giao chưa hỗ trợ cho {key}")
