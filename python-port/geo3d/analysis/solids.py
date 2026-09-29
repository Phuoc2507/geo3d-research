# -*- coding: utf-8 -*-
"""
solids.py — dịch từ api/_lib/kernel/analysis/solids.ts

Khối tròn xoay có TRỤC SONG SONG Oz: tại mỗi độ cao z, mặt cắt là một HÌNH TRÒN.
Đủ cho các dạng đề phổ thông (trụ, nón). Thể tích phần GIAO của hai khối = tích phân theo z của
diện tích "thấu kính" (giao hai hình tròn, có công thức đóng) — chính xác hơn Monte Carlo nhiều bậc.

Solid được biểu diễn bằng dict với khóa 'kind':
  {'kind': 'cylinder', 'cx', 'cy', 'radius', 'from', 'to'}
  {'kind': 'cone',     'cx', 'cy', 'baseRadius', 'baseZ', 'apexZ'}
"""
from __future__ import annotations
import math
from . import quadrature


def z_range(s: dict) -> tuple[float, float]:
    """Khoảng độ cao [zMin, zMax] mà khối tồn tại."""
    if s["kind"] == "cylinder":
        return (min(s["from"], s["to"]), max(s["from"], s["to"]))
    return (min(s["baseZ"], s["apexZ"]), max(s["baseZ"], s["apexZ"]))


def disk_at(s: dict, z: float) -> dict:
    """Mặt cắt tròn tại độ cao z (bán kính 0 nếu z ngoài khối)."""
    lo, hi = z_range(s)
    if z < lo or z > hi:
        return {"cx": 0, "cy": 0, "r": 0}
    if s["kind"] == "cylinder":
        return {"cx": s["cx"], "cy": s["cy"], "r": s["radius"]}
    t = (s["apexZ"] - z) / (s["apexZ"] - s["baseZ"])  # 1 ở đáy → 0 ở đỉnh
    return {"cx": s["cx"], "cy": s["cy"], "r": s["baseRadius"] * max(0, t)}


def lens_area(r1: float, r2: float, d: float) -> float:
    """Diện tích phần chung của hai hình tròn bán kính r1, r2, tâm cách nhau d."""
    if r1 <= 0 or r2 <= 0:
        return 0
    if d >= r1 + r2:
        return 0                                        # rời / tiếp xúc ngoài
    if d <= abs(r1 - r2):
        return math.pi * min(r1, r2) ** 2               # lồng trọn

    def clamp1(v: float) -> float:
        return -1 if v < -1 else (1 if v > 1 else v)

    a1 = r1 * r1 * math.acos(clamp1((d * d + r1 * r1 - r2 * r2) / (2 * d * r1)))
    a2 = r2 * r2 * math.acos(clamp1((d * d + r2 * r2 - r1 * r1) / (2 * d * r2)))
    tri = 0.5 * math.sqrt((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2))
    return a1 + a2 - tri


def intersection_volume(a: dict, b: dict) -> dict:
    """Thể tích phần chung hai khối = ∫ diện-tích-thấu-kính(z) dz trên đoạn độ cao chung.
    Trả {'value', 'estimatedError'}."""
    a_lo, a_hi = z_range(a)
    b_lo, b_hi = z_range(b)
    lo = max(a_lo, b_lo)
    hi = min(a_hi, b_hi)
    if hi <= lo:
        return {"value": 0, "estimatedError": 0}

    def f(z: float) -> float:
        d1 = disk_at(a, z)
        d2 = disk_at(b, z)
        return lens_area(d1["r"], d2["r"], math.hypot(d1["cx"] - d2["cx"], d1["cy"] - d2["cy"]))

    value, err = quadrature.integrate(f, lo, hi)
    return {"value": value, "estimatedError": err}
