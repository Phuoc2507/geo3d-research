# -*- coding: utf-8 -*-
"""
relative.py — dịch từ api/_lib/kernel/compute/relative.ts

Vị trí TƯƠNG ĐỐI giữa hai thực thể (đường/mặt/cầu/điểm). Tất cả so sánh dùng đại lượng
bình-phương (giữ trong trường), và cmp_scalar (exact khi có) để phân biệt cắt/tiếp xúc/rời.
Trả về RelPos(relation=<chuỗi tiếng Việt>).
"""
from __future__ import annotations
from . import scalar as S
from . import vec3 as V
from .vec3 import Vec3
from .entities import Line, Plane, Sphere, Point


class RelPos:
    kind = "relative_position"

    def __init__(self, relation: str):
        self.relation = relation

    def __repr__(self):
        return f"relative_position: {self.relation}"


def _rel(relation: str) -> RelPos:
    return RelPos(relation)


def _is_zero_vec(v: Vec3) -> bool:
    return S.is_zero(V.len_sq_v(v))


def _plane_signed(pl: Plane, p: Vec3):
    return S.add(V.dot_v(pl.n, p), pl.d)      # n·p + d


def _point_on_plane(pl: Plane) -> Vec3:
    return V.scale_v(pl.n, S.div(S.neg(pl.d), V.len_sq_v(pl.n)))


def _rel_line_line(l1: Line, l2: Line) -> RelPos:
    cr = V.cross_v(l1.dir, l2.dir)
    if _is_zero_vec(cr):
        if _is_zero_vec(V.cross_v(V.sub_v(l2.p, l1.p), l1.dir)):
            return _rel("trùng nhau")
        return _rel("song song")
    return _rel("cắt nhau") if S.is_zero(V.dot_v(V.sub_v(l2.p, l1.p), cr)) else _rel("chéo nhau")


def _rel_line_plane(l: Line, pl: Plane) -> RelPos:
    if not S.is_zero(V.dot_v(l.dir, pl.n)):
        return _rel("cắt nhau")
    return _rel("đường nằm trên mặt") if S.is_zero(_plane_signed(pl, l.p)) else _rel("song song")


def _rel_plane_plane(p1: Plane, p2: Plane) -> RelPos:
    if not _is_zero_vec(V.cross_v(p1.n, p2.n)):
        return _rel("cắt nhau")
    return _rel("trùng nhau") if S.is_zero(_plane_signed(p2, _point_on_plane(p1))) else _rel("song song")


def _rel_sphere_plane(s: Sphere, pl: Plane) -> RelPos:
    signed = _plane_signed(pl, s.center)
    d_sq = S.div(S.mul(signed, signed), V.len_sq_v(pl.n))
    c = S.cmp_scalar(d_sq, s.r2)
    return _rel("cắt theo đường tròn" if c < 0 else "tiếp xúc" if c == 0 else "rời nhau")


def _rel_point_sphere(pt: Point, s: Sphere) -> RelPos:
    c = S.cmp_scalar(V.len_sq_v(V.sub_v(pt.p, s.center)), s.r2)
    return _rel("điểm nằm trong" if c < 0 else "điểm nằm trên" if c == 0 else "điểm nằm ngoài")


def _rel_sphere_line(s: Sphere, l: Line) -> RelPos:
    cr = V.cross_v(V.sub_v(s.center, l.p), l.dir)
    d_sq = S.div(V.len_sq_v(cr), V.len_sq_v(l.dir))
    c = S.cmp_scalar(d_sq, s.r2)
    return _rel("cắt nhau" if c < 0 else "tiếp xúc" if c == 0 else "rời nhau")


def compute_relative_position(a, b) -> RelPos:
    from .compute import first_degenerate
    deg = first_degenerate([a, b])
    if deg:
        raise ValueError(deg)
    key = f"{a.kind}-{b.kind}"
    if key == "line-line":
        return _rel_line_line(a, b)
    if key == "line-plane":
        return _rel_line_plane(a, b)
    if key == "plane-line":
        return _rel_line_plane(b, a)
    if key == "plane-plane":
        return _rel_plane_plane(a, b)
    if key == "sphere-plane":
        return _rel_sphere_plane(a, b)
    if key == "plane-sphere":
        return _rel_sphere_plane(b, a)
    if key == "point-sphere":
        return _rel_point_sphere(a, b)
    if key == "sphere-point":
        return _rel_point_sphere(b, a)
    if key == "sphere-line":
        return _rel_sphere_line(a, b)
    if key == "line-sphere":
        return _rel_sphere_line(b, a)
    raise ValueError(f"vị trí tương đối chưa hỗ trợ cho {key}")
