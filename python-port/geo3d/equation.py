# -*- coding: utf-8 -*-
"""
equation.py — dịch từ api/_lib/kernel/compute/equation.ts

Sinh CHUỖI phương trình cho mặt phẳng / mặt cầu / đường thẳng.
  - planeEquationText:  khử mẫu về hệ số nguyên rút gọn, chuẩn hoá dấu hệ số dẫn đầu ('2x - y + 2z - 3 = 0').
  - sphereEquationText: dạng chính tắc '(x - 1)² + (y - 2)² + (z - 3)² = 9'.
  - lineEquationText:   dạng tham số 'x = 1 + 2t, ...'.
Chỉ hệ số hữu tỷ (exact, radicand 1) mới viết được dạng nguyên; ngược lại rơi về float.
"""
from __future__ import annotations
from fractions import Fraction
from math import gcd
from . import scalar as S
from .scalar import Scalar, Exact
from .entities import Plane, Sphere, Line


def _blcm(a: int, b: int) -> int:
    return abs(a // gcd(a, b) * b) if (a and b) else abs(a or b)


def _rational_coeffs(scalars: list[Scalar]):
    """Trả list (num, den) nếu MỌI hệ số là hữu tỷ exact; ngược lại None."""
    out = []
    for s in scalars:
        if s.exact is None or s.exact.radicand != 1:
            return None
        out.append((s.exact.q.numerator, s.exact.q.denominator))
    return out


def _format_linear(a: int, b: int, c: int, d: int) -> str:
    """'2x - y + 2z - 3 = 0' — bỏ hệ số 0, gộp dấu, ±1 ẩn hệ số."""
    parts = []

    def term(k: int, v: str):
        if k == 0:
            return
        neg = k < 0
        mag = "" if (v != "" and abs(k) == 1) else str(abs(k))
        if not parts:
            parts.append(f"{'-' if neg else ''}{mag}{v}")
        else:
            parts.append(f" {'-' if neg else '+'} {mag}{v}")

    term(a, "x")
    term(b, "y")
    term(c, "z")
    term(d, "")
    out = "".join(parts) if parts else "0"
    return f"{out} = 0"


def _fmt_num(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else f"{n:.4f}"


def _format_linear_approx(a: float, b: float, c: float, d: float) -> str:
    parts = []

    def term(k: float, v: str):
        if abs(k) < 1e-12:
            return
        neg = k < 0
        ab = abs(k)
        mag = "" if (v != "" and abs(ab - 1) < 1e-12) else _fmt_num(ab)
        if not parts:
            parts.append(f"{'-' if neg else ''}{mag}{v}")
        else:
            parts.append(f" {'-' if neg else '+'} {mag}{v}")

    term(a, "x")
    term(b, "y")
    term(c, "z")
    term(d, "")
    out = "".join(parts) if parts else "0"
    return f"{out} = 0"


def plane_equation_text(pl: Plane) -> str:
    rats = _rational_coeffs([pl.n.x, pl.n.y, pl.n.z, pl.d])
    if rats is None:
        return _format_linear_approx(pl.n.x.approx, pl.n.y.approx, pl.n.z.approx, pl.d.approx)
    D = 1
    for _, den in rats:
        D = _blcm(D, den)
    ints = [num * (D // den) for num, den in rats]
    g = 0
    for k in ints:
        g = gcd(g, k)
    if g == 0:
        g = 1
    a, b, c, d = (k // g for k in ints)
    lead = next((k for k in (a, b, c) if k != 0), None)
    if lead is not None and lead < 0:
        a, b, c, d = -a, -b, -c, -d
    return _format_linear(a, b, c, d)


def _display_int_exact(num: int, den: int) -> str:
    return repr(Exact(Fraction(num, den), 1))


def sphere_equation_text(s: Sphere) -> str:
    parts = [s.center.x, s.center.y, s.center.z]
    if any(c.exact is None or c.exact.radicand != 1 for c in parts) or s.r2.exact is None:
        return (f"tâm ≈ ({', '.join(_fmt_num(c.approx) for c in parts)}), "
                f"R² ≈ {_fmt_num(s.r2.approx)}")

    def var_part(c: Scalar, v: str) -> str:
        e = c.exact
        n = e.q.numerator
        if n == 0:
            return f"{v}²"
        neg = n < 0
        mag = _display_int_exact(-n if neg else n, e.q.denominator)
        return f"({v} {'+' if neg else '-'} {mag})²"

    return (f"{var_part(s.center.x, 'x')} + {var_part(s.center.y, 'y')} + "
            f"{var_part(s.center.z, 'z')} = {repr(s.r2.exact)}")


def line_equation_text(l: Line) -> str:
    """Dạng tham số: mỗi thành phần 'v = p0 ± |d|t'."""
    def comp(p0: Scalar, d: Scalar, v: str) -> str:
        d_neg = d.approx < 0
        d_mag = (S.neg(d) if d_neg else d).text()
        return f"{v} = {p0.text()} {'-' if d_neg else '+'} {d_mag}t"

    return ", ".join([
        comp(l.p.x, l.dir.x, "x"),
        comp(l.p.y, l.dir.y, "y"),
        comp(l.p.z, l.dir.z, "z"),
    ])
