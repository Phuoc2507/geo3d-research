# -*- coding: utf-8 -*-
"""
constructions.py — dịch từ api/_lib/kernel/constructions.ts

Phép dựng điểm dẫn xuất bằng số học CHÍNH XÁC (hữu tỉ + căn):
  - solve3: giải hệ 3 ẩn bằng Cramer (ném nếu suy biến).
  - foot_on_plane / foot_on_line: chân đường vuông góc.
  - reflect_across_plane / reflect_across_line: đối xứng qua mặt / qua đường.
  - orthocenter / circumcenter: trực tâm / tâm ngoại tiếp tam giác.
Các hàm nhận/trả Vec3; giữ normZeroS: chuẩn hoá -0.0 về 0.0 ở .approx để khớp golden.
"""
from __future__ import annotations
from . import scalar as S
from . import vec3 as V
from .scalar import Scalar
from .vec3 import Vec3
from .entities import Plane, Line


def _det3(u: Vec3, v: Vec3, w: Vec3) -> Scalar:
    return V.dot_v(u, V.cross_v(v, w))


def _norm_zero_s(s: Scalar) -> Scalar:
    """Chuẩn hoá -0.0 (float) về +0.0 để khớp golden; exact giữ nguyên."""
    return Scalar(0.0, s.exact) if s.approx == 0 else s


def solve3(r1: Vec3, r2: Vec3, r3: Vec3, b: Vec3) -> Vec3:
    """Giải hệ H·rᵢ = bᵢ (i=1,2,3) bằng Cramer. Ném nếu suy biến (det = 0)."""
    c0 = V.vec(r1.x, r2.x, r3.x)
    c1 = V.vec(r1.y, r2.y, r3.y)
    c2 = V.vec(r1.z, r2.z, r3.z)
    det_m = _det3(c0, c1, c2)
    if det_m.approx == 0 or (det_m.exact is not None and det_m.exact.q == 0):
        raise ValueError("Degenerate construction: linear system has no unique solution")
    return V.vec(
        _norm_zero_s(S.div(_det3(b, c1, c2), det_m)),
        _norm_zero_s(S.div(_det3(c0, b, c2), det_m)),
        _norm_zero_s(S.div(_det3(c0, c1, b), det_m)),
    )


def foot_on_plane(p: Vec3, pl: Plane) -> Vec3:
    """Chân đường vuông góc từ p xuống mặt: p − ((n·p + d)/|n|²)·n."""
    t = S.div(S.add(V.dot_v(pl.n, p), pl.d), V.len_sq_v(pl.n))
    return V.sub_v(p, V.scale_v(pl.n, t))


def foot_on_line(p: Vec3, l: Line) -> Vec3:
    """Chân đường vuông góc từ p xuống đường: a + (((p−a)·dir)/|dir|²)·dir."""
    t = S.div(V.dot_v(V.sub_v(p, l.p), l.dir), V.len_sq_v(l.dir))
    return V.add_v(l.p, V.scale_v(l.dir, t))


def reflect_across_plane(p: Vec3, pl: Plane) -> Vec3:
    return V.sub_v(V.scale_v(foot_on_plane(p, pl), S.rat(2)), p)  # 2·foot − p


def reflect_across_line(p: Vec3, l: Line) -> Vec3:
    return V.sub_v(V.scale_v(foot_on_line(p, l), S.rat(2)), p)


def orthocenter(a: Vec3, b: Vec3, c: Vec3) -> Vec3:
    """Trực tâm: H thoả (H−B)·(C−B)=0, (H−A)·(C−A)=0, H thuộc mặt (ABC)."""
    n = V.cross_v(V.sub_v(b, a), V.sub_v(c, a))
    r1 = V.sub_v(c, b)
    r2 = V.sub_v(c, a)
    return solve3(r1, r2, n, V.vec(V.dot_v(a, r1), V.dot_v(b, r2), V.dot_v(a, n)))


def circumcenter(a: Vec3, b: Vec3, c: Vec3) -> Vec3:
    """Tâm ngoại tiếp: O·(B−A)=(|B|²−|A|²)/2, O·(C−A)=(|C|²−|A|²)/2, O∈(ABC)."""
    n = V.cross_v(V.sub_v(b, a), V.sub_v(c, a))
    half = S.rat(1, 2)
    r1 = V.sub_v(b, a)
    r2 = V.sub_v(c, a)
    b1 = S.mul(S.sub(V.len_sq_v(b), V.len_sq_v(a)), half)
    b2 = S.mul(S.sub(V.len_sq_v(c), V.len_sq_v(a)), half)
    return solve3(r1, r2, n, V.vec(b1, b2, V.dot_v(a, n)))
