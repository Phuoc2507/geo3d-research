# -*- coding: utf-8 -*-
"""
slice_volume.py — dịch từ api/_lib/kernel/analysis/sliceVolume.ts

Lõi tất định cho khối "thiết diện đã biết": V = ∫ k·side(t)² dt, side = |outer − inner|.
k theo hình lát: vuông=1, tam giác đều=√3/4, nửa tròn=π/8, chữ nhật=ratio.
Cũng có DIỆN TÍCH phẳng giữa hai đường (planar_area / build_area_region).
"""
from __future__ import annotations
import math
from . import revolution
from .quadrature import integrate

SECTION_KINDS = ("square", "equilateral", "semicircle", "rect")


def section_k(section: str, ratio: float = 1) -> float:
    """Hệ số k của diện tích thiết diện theo cạnh `side`."""
    if section == "square":
        return 1.0
    if section == "equilateral":
        return math.sqrt(3) / 4
    if section == "semicircle":
        return math.pi / 8          # đường kính = side
    if section == "rect":
        return ratio                # cạnh kia = ratio·side
    raise ValueError(f"loại thiết diện lạ: {section}")


_LATEX_S = {
    "square": "s^2",
    "equilateral": "\\tfrac{\\sqrt3}{4}s^2",
    "semicircle": "\\tfrac{\\pi}{8}s^2",
    "rect": "k\\,s^2",
}


def _fmt_bound(n: float) -> str:
    """Định dạng CẬN cho LaTeX (dịch fmtBound của quadrature.ts): nguyên giữ nguyên;
    thập phân làm tròn 3 chữ số (chỉ để hiển thị, giá trị tính toán vẫn đủ chính xác)."""
    if not math.isfinite(n):
        return str(n)
    if n == int(n):
        return str(int(n))
    return str(round(n * 1000) / 1000)


def _compile_side(outer, inner=None):
    """side(t) = |outer(t) − inner(t)| (inner vắng ⇒ |outer|)."""
    go = revolution.compile_profile(outer)
    gi = revolution.compile_profile(inner) if inner else None
    return lambda t: abs(go(t) - (gi(t) if gi else 0.0))


def slice_stack_volume(section, outer, domain, inner=None, ratio: float = 1):
    a, b = domain
    side = _compile_side(outer, inner)
    k = section_k(section, ratio)
    return integrate(lambda t: k * side(t) * side(t), a, b)


def _sample_side(outer, domain, inner=None, n: int = 64):
    a, b = domain
    side = _compile_side(outer, inner)
    out = []
    for i in range(n + 1):
        t = a + (b - a) * i / n
        s = side(t)
        out.append({"t": t, "side": max(0.0, s) if math.isfinite(s) else 0.0})
    return out


def build_slice_stack(id, section, outer, domain, color=None, inner=None, ratio=None, axis="Ox"):
    r = (ratio if (ratio and ratio > 0) else 1) if section == "rect" else None
    dom = revolution._refine_profile_bounds(outer, inner, domain)   # cận đáy = giao/cắt trục ⇒ vá cận vô tỉ
    value, estimated_error = slice_stack_volume(section, outer, dom, inner, r if r is not None else 1)
    verified = estimated_error <= 1e-6 * max(1, abs(value))
    dvar = "y" if axis == "Oy" else "x"
    latex = f"V=\\int_{{{_fmt_bound(dom[0])}}}^{{{_fmt_bound(dom[1])}}} {_LATEX_S[section]}\\,d{dvar}"
    volume = {"value": value, "latex": latex, "verified": verified, "estimatedError": estimated_error}
    out = {
        "id": id, "axis": axis, "domain": dom, "outer": outer,
        "section": section, "volume": volume, "color": color,
        "samples": _sample_side(outer, dom, inner),
    }
    if inner:
        out["inner"] = inner
    if r is not None:
        out["ratio"] = r
    return out


def planar_area(outer, inner, domain):
    a, b = domain
    gf = revolution.compile_profile(outer)
    gg = revolution.compile_profile(inner)
    return integrate(lambda x: abs(gf(x) - gg(x)), a, b)


def _sample_area(outer, inner, domain, n: int = 64):
    a, b = domain
    gf = revolution.compile_profile(outer)
    gg = revolution.compile_profile(inner)
    out = []
    for i in range(n + 1):
        x = a + (b - a) * i / n
        f = gf(x)
        g = gg(x)
        out.append({"x": x, "top": max(f, g), "bot": min(f, g)})
    return out


def build_area_region(id, outer, domain, inner=None, color=None, slab_depth=0.15):
    inr = inner if inner else {"kind": "const", "c": 0}
    dom = revolution._refine_profile_bounds(outer, inr, domain)   # cận = 2 hoành độ giao f=g ⇒ vá cận vô tỉ
    value, estimated_error = planar_area(outer, inr, dom)
    verified = estimated_error <= 1e-6 * max(1, abs(value))
    latex = f"S=\\int_{{{_fmt_bound(dom[0])}}}^{{{_fmt_bound(dom[1])}}} |f(x)-g(x)|\\,dx"
    area = {"value": value, "latex": latex, "verified": verified, "estimatedError": estimated_error}
    return {
        "id": id, "outer": outer, "inner": inr, "domain": dom,
        "area": area, "color": color, "slabDepth": slab_depth,
        "samples": _sample_area(outer, inr, dom),
    }
