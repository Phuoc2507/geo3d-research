# -*- coding: utf-8 -*-
"""
quadrature.py — dịch từ api/_lib/kernel/analysis/quadrature.ts

Tích phân xác định bằng Simpson kép có TỰ KIỂM: tính ở n rồi 2n khoảng, ước lượng sai số
theo Richardson |I₂ₙ − Iₙ|/15. Engine dùng để KHÔNG "trả bừa" khi chưa hội tụ:
kết quả chỉ được coi là 'verified' khi sai số ước lượng đủ nhỏ.
"""
from __future__ import annotations
import math


def simpson(f, a: float, b: float, n: int) -> float:
    m = n if n % 2 == 0 else n + 1        # Simpson cần số khoảng CHẴN
    h = (b - a) / m
    s = f(a) + f(b)
    for i in range(1, m):
        s += (4 if i % 2 else 2) * f(a + i * h)
    return s * h / 3


def integrate(f, a: float, b: float, tol: float = 1e-9, max_n: int = 1 << 18):
    """Tăng đôi lưới tới khi sai số ước lượng đủ nhỏ (tương đối) hoặc chạm trần lưới.
    Trả (value, estimated_error)."""
    n = 8
    prev = simpson(f, a, b, n)
    while True:
        n *= 2
        cur = simpson(f, a, b, n)
        err = abs(cur - prev) / 15
        if err <= tol * max(1, abs(cur)) or n >= max_n:
            return cur, err
        prev = cur


def _nearest_root(h, x0: float, w: float):
    """Nghiệm h(x)=0 gần x0 nhất trong [x0-w, x0+w]; None nếu không có nghiệm cắt."""
    N = 80
    lo, hi = x0 - w, x0 + w
    best, best_dist = None, math.inf

    def consider(root):
        nonlocal best, best_dist
        d = abs(root - x0)
        if d < best_dist:
            best_dist, best = d, root

    def safe_h(x):
        try:
            return h(x)
        except (ValueError, ZeroDivisionError):
            return math.nan

    px, py = lo, safe_h(lo)
    for i in range(1, N + 1):
        x = lo + (hi - lo) * i / N
        y = safe_h(x)
        if math.isfinite(py) and py == 0:
            consider(px)
        if math.isfinite(py) and math.isfinite(y) and py * y < 0:
            a1, b1, fa = px, x, py               # chia đôi trong [px, x]
            for _ in range(60):
                m = (a1 + b1) / 2
                try:
                    fm = h(m)
                except (ValueError, ZeroDivisionError):
                    break
                if not math.isfinite(fm):
                    break
                if fa * fm <= 0:
                    b1 = m
                else:
                    a1, fa = m, fm
            consider((a1 + b1) / 2)
        px, py = x, y
    if math.isfinite(py) and py == 0:
        consider(px)
    return best


def refine_bounds(h, domain):
    """Tinh chỉnh cận [a,b] về nghiệm CHÍNH XÁC của h (giao 2 đường / cắt trục).
    FAIL-SAFE: chỉ dời đầu mút khi có nghiệm cắt trong ±25% độ rộng; cận cho sẵn thì GIỮ nguyên."""
    a, b = domain
    span = b - a
    if not (span > 1e-12) or not math.isfinite(span):
        return (a, b)
    w = 0.25 * span
    na = _nearest_root(h, a, w)
    nb = _nearest_root(h, b, w)
    ra = na if na is not None else a
    rb = nb if nb is not None else b
    if not (rb > ra) or not math.isfinite(ra) or not math.isfinite(rb):
        return (a, b)
    return (ra, rb)
