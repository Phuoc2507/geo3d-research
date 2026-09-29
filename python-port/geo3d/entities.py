# -*- coding: utf-8 -*-
"""
entities.py — dịch gọn từ api/_lib/kernel/entities.ts

Bốn thực thể hình học: điểm, đường thẳng, mặt phẳng, mặt cầu.
- Point:  p (Vec3)
- Line:   điểm p + vector chỉ phương dir
- Plane:  pháp tuyến n + hằng số d  (mặt phẳng: n·x + d = 0)
- Sphere: tâm center + r2 (bán kính bình phương, giữ chính xác)
"""
from __future__ import annotations
from dataclasses import dataclass
from . import scalar as S
from . import vec3 as V
from .scalar import Scalar
from .vec3 import Vec3


@dataclass
class Point:
    p: Vec3
    kind: str = "point"


@dataclass
class Line:
    p: Vec3
    dir: Vec3
    kind: str = "line"


@dataclass
class Plane:
    n: Vec3
    d: Scalar
    kind: str = "plane"


@dataclass
class Sphere:
    center: Vec3
    r2: Scalar
    kind: str = "sphere"


# ---- Dựng tiện lợi ----
def point(x, y, z) -> Point:
    return Point(V.rat_vec(x, y, z))


def line_through(a: Point, b: Point) -> Line:
    """Đường thẳng qua 2 điểm."""
    return Line(a.p, V.sub_v(b.p, a.p))


def plane_through(a: Point, b: Point, c: Point) -> Plane:
    """Mặt phẳng qua 3 điểm: n = (b-a)×(c-a), d = -n·a."""
    n = V.cross_v(V.sub_v(b.p, a.p), V.sub_v(c.p, a.p))
    d = S.neg(V.dot_v(n, a.p))
    return Plane(n, d)


# ============================================================================
# Bồi thêm (dịch từ api/_lib/kernel/entities.ts) — dựng thực thể TỪ Vec3 (Vec3S)
# thay vì từ Point, phục vụ tầng dựng hình (oxyz). KHÔNG xoá/đổi hàm cũ ở trên.
# ============================================================================
def point_from_coords(p: Vec3) -> Point:
    return Point(p)


def line_from_two_points(a: Vec3, b: Vec3) -> Line:
    """Đường qua 2 điểm (Vec3): điểm gốc a, chỉ phương b−a."""
    return Line(a, V.sub_v(b, a))


def line_from_point_dir(p: Vec3, dir: Vec3) -> Line:
    return Line(p, dir)


def plane_from_three_points(a: Vec3, b: Vec3, c: Vec3) -> Plane:
    """Mặt qua 3 điểm (Vec3): pháp tuyến = (b−a)×(c−a), d = −n·a."""
    n = V.cross_v(V.sub_v(b, a), V.sub_v(c, a))
    d = S.neg(V.dot_v(n, a))
    return Plane(n, d)


def plane_from_point_normal(point: Vec3, n: Vec3) -> Plane:
    return Plane(n, S.neg(V.dot_v(n, point)))


def plane_from_coeffs(a: Scalar, b: Scalar, c: Scalar, d: Scalar) -> Plane:
    return Plane(Vec3(a, b, c), d)


def sphere_from_center_radius2(center: Vec3, r2: Scalar) -> Sphere:
    return Sphere(center, r2)


def sphere_from_center_point(center: Vec3, on_sphere: Vec3) -> Sphere:
    return Sphere(center, V.len_sq_v(V.sub_v(on_sphere, center)))


def sphere_from_equation(a: Scalar, b: Scalar, c: Scalar, d: Scalar) -> Sphere:
    """Mặt cầu từ x²+y²+z² + a·x + b·y + c·z + d = 0.
    Tâm = (−a/2, −b/2, −c/2); R² = tâm.x²+tâm.y²+tâm.z² − d."""
    half = S.rat(1, 2)
    cx = S.neg(S.mul(a, half))
    cy = S.neg(S.mul(b, half))
    cz = S.neg(S.mul(c, half))
    center = Vec3(cx, cy, cz)
    r2 = S.sub(S.add(S.add(S.mul(cx, cx), S.mul(cy, cy)), S.mul(cz, cz)), d)
    return Sphere(center, r2)


def _det3(u: Vec3, v: Vec3, w: Vec3) -> Scalar:
    """det 3×3 với các CỘT là u,v,w: det = u·(v×w)."""
    return V.dot_v(u, V.cross_v(v, w))


def sphere_from_four_points(p0: Vec3, p1: Vec3, p2: Vec3, p3: Vec3) -> Sphere:
    """Mặt cầu ngoại tiếp 4 điểm. Tâm X: X·aᵢ = bᵢ, aᵢ=Pᵢ−P0, bᵢ=(|Pᵢ|²−|P0|²)/2.
    Giải bằng Cramer (exact hữu tỉ). 4 điểm đồng phẳng ⇒ det=0 ⇒ ném."""
    half = S.rat(1, 2)
    a1 = V.sub_v(p1, p0)
    a2 = V.sub_v(p2, p0)
    a3 = V.sub_v(p3, p0)
    q0 = V.dot_v(p0, p0)
    b1 = S.mul(S.sub(V.dot_v(p1, p1), q0), half)
    b2 = S.mul(S.sub(V.dot_v(p2, p2), q0), half)
    b3 = S.mul(S.sub(V.dot_v(p3, p3), q0), half)
    c0 = V.vec(a1.x, a2.x, a3.x)
    c1 = V.vec(a1.y, a2.y, a3.y)
    c2 = V.vec(a1.z, a2.z, a3.z)
    b_vec = V.vec(b1, b2, b3)
    det_m = _det3(c0, c1, c2)
    if det_m.approx == 0 or (det_m.exact is not None and det_m.exact.q == 0):
        raise ValueError("The four points are coplanar; no unique circumscribing sphere")
    center = V.vec(
        S.div(_det3(b_vec, c1, c2), det_m),
        S.div(_det3(c0, b_vec, c2), det_m),
        S.div(_det3(c0, c1, b_vec), det_m),
    )
    return Sphere(center, V.len_sq_v(V.sub_v(center, p0)))
