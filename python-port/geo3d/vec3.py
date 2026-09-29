# -*- coding: utf-8 -*-
"""
vec3.py — dịch từ api/_lib/kernel/vec3s.ts

Vector 3 chiều mà mỗi thành phần là một Scalar (số lai float+exact).
Nhờ đó dot/cross/len² đều giữ được dạng chính xác khi có thể.
"""
from __future__ import annotations
from . import scalar as S
from .scalar import Scalar


class Vec3:
    __slots__ = ("x", "y", "z")

    def __init__(self, x: Scalar, y: Scalar, z: Scalar):
        self.x, self.y, self.z = x, y, z

    def approx(self) -> tuple[float, float, float]:
        return (self.x.approx, self.y.approx, self.z.approx)

    def __repr__(self):
        return f"({self.x}, {self.y}, {self.z})"


def vec(x: Scalar, y: Scalar, z: Scalar) -> Vec3:
    return Vec3(x, y, z)


def rat_vec(x, y, z) -> Vec3:
    """Vector với toạ độ hữu tỉ chính xác. Chấp nhận int hoặc (num, den)."""
    def r(v):
        return S.rat(*v) if isinstance(v, tuple) else S.rat(v)
    return Vec3(r(x), r(y), r(z))


def add_v(a: Vec3, b: Vec3) -> Vec3:
    return Vec3(S.add(a.x, b.x), S.add(a.y, b.y), S.add(a.z, b.z))


def sub_v(a: Vec3, b: Vec3) -> Vec3:
    return Vec3(S.sub(a.x, b.x), S.sub(a.y, b.y), S.sub(a.z, b.z))


def scale_v(a: Vec3, s: Scalar) -> Vec3:
    return Vec3(S.mul(a.x, s), S.mul(a.y, s), S.mul(a.z, s))


def neg_v(a: Vec3) -> Vec3:
    return Vec3(S.neg(a.x), S.neg(a.y), S.neg(a.z))


def dot_v(a: Vec3, b: Vec3) -> Scalar:
    return S.add(S.add(S.mul(a.x, b.x), S.mul(a.y, b.y)), S.mul(a.z, b.z))


def cross_v(a: Vec3, b: Vec3) -> Vec3:
    return Vec3(
        S.sub(S.mul(a.y, b.z), S.mul(a.z, b.y)),
        S.sub(S.mul(a.z, b.x), S.mul(a.x, b.z)),
        S.sub(S.mul(a.x, b.y), S.mul(a.y, b.x)),
    )


def len_sq_v(a: Vec3) -> Scalar:
    return dot_v(a, a)
