# -*- coding: utf-8 -*-
"""
revolution.py — dịch từ api/_lib/kernel/analysis/revolution.ts

Khối tròn xoay, lõi tất định + tự kiểm sai số:
  - Quanh Ox, phương pháp ĐĨA/VÀNH KHĂN:  V = π ∫ |r_ng² − r_tr²| dx
  - Quanh Oy, phương pháp VỎ TRỤ (shell):  V = 2π ∫ x·|outer(x) − inner(x)| dx
  - Quanh Oy, ĐĨA theo y (đường x = g(y)):  V = π ∫ |x_ng² − x_tr²| dy

'ProfileFn' (biên dạng r theo biến trục) là một dict. Dùng helper poly/sqrtp/const/expr để tạo.
Kết quả trả 'verified=True' CHỈ khi sai số tích phân ước lượng đủ nhỏ — nếu không, KHÔNG khẳng định.
"""
from __future__ import annotations
import math
from .quadrature import integrate, refine_bounds
from .expr import parse_expr


# ---- Các loại biên dạng (ProfileFn) ----
def poly(coeffs):        return {"kind": "poly", "coeffs": list(coeffs)}   # a0 + a1 x + a2 x² ...
def sqrtp(a, b=0.0):     return {"kind": "sqrt", "a": a, "b": b}           # a√x + b
def const(c):            return {"kind": "const", "c": c}
def expr(s):             return {"kind": "expr", "expr": s}


def compile_profile(f):
    """Biên dịch một biên dạng thành hàm nhanh (x -> float)."""
    kind = f["kind"]
    if kind == "poly":
        cs = f["coeffs"]
        return lambda x: sum(c * x ** i for i, c in enumerate(cs))
    if kind == "sqrt":
        a, b = f["a"], f["b"]
        return lambda x: a * math.sqrt(x) + b
    if kind == "const":
        c = f["c"]
        return lambda x: c
    if kind == "expr":
        g = parse_expr(f["expr"])
        # gán giá trị cho CẢ x lẫn y để biểu thức viết theo y (đường x=g(y)) vẫn chạy
        return lambda x: g({"x": x, "y": x})
    raise ValueError(f"biên dạng lạ: {kind}")


def eval_profile(f, x: float) -> float:
    return compile_profile(f)(x)


def _refine_profile_bounds(outer, inner, domain, baseline=0.0):
    go = compile_profile(outer)
    gi = compile_profile(inner) if inner else None
    h = lambda x: go(x) - (gi(x) if gi else baseline)
    return refine_bounds(h, domain)


# ============================ QUANH Ox (đĩa / vành khăn) ============================
def revolution_volume_disk(outer, domain, inner=None, axis_y=0.0):
    a, b = domain
    go = compile_profile(outer)
    gi = compile_profile(inner) if inner else None

    def f(x):
        ro = go(x) - axis_y
        ri = (gi(x) - axis_y) if gi else 0.0
        # |ro² − ri²| để thể tích luôn ≥ 0 và bền với việc gán nhầm thứ tự trong/ngoài
        return math.pi * abs(ro * ro - ri * ri)

    return integrate(f, a, b)


def build_revolution_ox(outer, domain, inner=None, axis_y=0.0):
    dom = _refine_profile_bounds(outer, inner, domain, axis_y)
    value, err = revolution_volume_disk(outer, dom, inner, axis_y)
    verified = err <= 1e-6 * max(1, abs(value))
    return {
        "axis": "Ox", "method": "washer" if inner else "disk",
        "domain": dom, "value": value, "estimated_error": err, "verified": verified,
    }


# ============================ QUANH Oy (vỏ trụ) ============================
def revolution_volume_shell_oy(outer, domain, inner=None):
    a, b = domain
    go = compile_profile(outer)
    gi = compile_profile(inner) if inner else None

    def f(x):
        h = abs(go(x) - gi(x)) if gi else go(x)
        return 2 * math.pi * x * h

    return integrate(f, a, b)


def build_revolution_oy(outer, domain, inner=None):
    dom = _refine_profile_bounds(outer, inner, domain)
    value, err = revolution_volume_shell_oy(outer, dom, inner)
    verified = err <= 1e-6 * max(1, abs(value))
    return {
        "axis": "Oy", "method": "shell",
        "domain": dom, "value": value, "estimated_error": err, "verified": verified,
    }


# ============================ QUANH Oy (đĩa theo y, đường x=g(y)) ============================
def build_revolution_oy_disk(outer, domain, inner=None):
    dom = _refine_profile_bounds(outer, inner, domain)
    value, err = revolution_volume_disk(outer, dom, inner)   # tái dùng: tích phân π|ro²−ri²| trên [c,d]
    verified = err <= 1e-6 * max(1, abs(value))
    return {
        "axis": "Oy", "method": "washer" if inner else "disk",
        "domain": dom, "value": value, "estimated_error": err, "verified": verified,
    }
