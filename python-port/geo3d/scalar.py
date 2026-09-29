# -*- coding: utf-8 -*-
"""
scalar.py  — dịch từ api/_lib/kernel/scalar.ts

Số CHÍNH XÁC:  Exact = (q)·√radicand,  q là phân số (Fraction), radicand nguyên dương square-free.
Số LAI:        Scalar = { approx: float, exact: Exact | None }  — luôn có float, có exact khi tính được.

Nguyên tắc "rời trường an toàn": phép nào không biểu diễn được trong trường (hữu tỉ + một căn)
thì trả None ở tầng Exact — engine KHÔNG bịa một số thập phân rồi coi là chính xác.
"""
from __future__ import annotations
from fractions import Fraction
import math

# Trần radicand: vượt qua thì căn/tích dễ tràn số → làm tròn sai → trả None (rơi về float).
MAX_SAFE_RADICAND = 10**12


def _extract_square(r: int) -> tuple[int, int]:
    """r = factor² · rad, rad không còn thừa số chính phương. Trả (rad, factor). Ví dụ 12 -> (3, 2)."""
    if r < 1:
        raise ValueError(f"radicand phải nguyên dương, nhận {r}")
    rad, factor, f = r, 1, 2
    while f * f <= rad:
        while rad % (f * f) == 0:
            rad //= f * f
            factor *= f
        f += 1
    return rad, factor


class Exact:
    """Giá trị chính xác = q · √radicand. radicand == 1 nghĩa là hữu tỉ thuần."""
    __slots__ = ("q", "radicand")

    def __init__(self, q: Fraction, radicand: int = 1):
        if q == 0:
            self.q, self.radicand = Fraction(0), 1
            return
        rad, factor = _extract_square(radicand)   # √12 -> 2√3
        self.q = q * factor
        self.radicand = rad

    def approx(self) -> float:
        """Đổi ra float — CHỈ để đối chiếu, không dùng để lưu đáp."""
        return float(self.q) * math.sqrt(self.radicand)

    def __eq__(self, other) -> bool:
        return isinstance(other, Exact) and self.q == other.q and self.radicand == other.radicand

    def __repr__(self) -> str:
        n, d = self.q.numerator, self.q.denominator
        if self.radicand == 1:
            return f"{n}" if d == 1 else f"{n}/{d}"
        can = f"√{self.radicand}"
        if n == 1:
            tu = can
        elif n == -1:
            tu = f"-{can}"
        else:
            tu = f"{n}{can}"
        return tu if d == 1 else f"{tu}/{d}"


# ---- Phép toán trên Exact. add/sub CHỈ ĐÓNG khi cùng radicand, ngược lại None ----
def exact(n: int, d: int = 1, radicand: int = 1) -> Exact:
    return Exact(Fraction(n, d), radicand)


def add_exact(a: Exact, b: Exact) -> Exact | None:
    if a.q == 0:
        return b
    if b.q == 0:
        return a
    if a.radicand != b.radicand:
        return None                                  # ← rời trường: √2 + √3 không gọn được
    return Exact(a.q + b.q, a.radicand)


def neg_exact(a: Exact) -> Exact:
    return Exact(-a.q, a.radicand)


def sub_exact(a: Exact, b: Exact) -> Exact | None:
    return add_exact(a, neg_exact(b))


def mul_exact(a: Exact, b: Exact) -> Exact | None:
    radicand = a.radicand * b.radicand
    if radicand > MAX_SAFE_RADICAND:
        return None
    return Exact(a.q * b.q, radicand)


def div_exact(a: Exact, b: Exact) -> Exact | None:
    if b.q == 0:
        raise ZeroDivisionError("Exact chia cho 0")
    radicand = a.radicand * b.radicand
    if radicand > MAX_SAFE_RADICAND:
        return None
    # (a.q√ra)/(b.q√rb) = (a.q/b.q)·√ra/√rb = (a.q/(b.q·rb))·√(ra·rb)
    return Exact(a.q / (b.q * b.radicand), radicand)


def sqrt_exact(a: Exact) -> Exact | None:
    """√ của một hữu tỉ: √(n/d)=√(n·d)/d. √ của một căn thì ngoài trường -> None."""
    if a.radicand != 1 or a.q < 0:
        return None
    if a.q == 0:
        return Exact(Fraction(0))
    n, d = a.q.numerator, a.q.denominator
    radicand = n * d
    if radicand > MAX_SAFE_RADICAND:
        return None
    return Exact(Fraction(1, d), radicand)


# ============================ Scalar (số lai) ============================
class Scalar:
    __slots__ = ("approx", "exact")

    def __init__(self, approx: float, exact: Exact | None):
        self.approx = approx
        self.exact = exact

    def text(self) -> str:
        return repr(self.exact) if self.exact is not None else f"{self.approx:.4f}"

    def __repr__(self) -> str:
        return self.text()


def num(n: float) -> Scalar:
    """Số float thuần (không có dạng exact)."""
    return Scalar(n, None)


def from_exact(e: Exact) -> Scalar:
    return Scalar(e.approx(), e)


def rat(n: int, d: int = 1) -> Scalar:
    """Số hữu tỉ chính xác."""
    return from_exact(exact(n, d, 1))


def add(a: Scalar, b: Scalar) -> Scalar:
    e = add_exact(a.exact, b.exact) if (a.exact and b.exact) else None
    return Scalar(a.approx + b.approx, e)


def sub(a: Scalar, b: Scalar) -> Scalar:
    e = sub_exact(a.exact, b.exact) if (a.exact and b.exact) else None
    return Scalar(a.approx - b.approx, e)


def mul(a: Scalar, b: Scalar) -> Scalar:
    e = mul_exact(a.exact, b.exact) if (a.exact and b.exact) else None
    return Scalar(a.approx * b.approx, e)


def div(a: Scalar, b: Scalar) -> Scalar:
    e = div_exact(a.exact, b.exact) if (a.exact and b.exact and b.exact.q != 0) else None
    return Scalar(a.approx / b.approx, e)


def neg(a: Scalar) -> Scalar:
    return Scalar(-a.approx, neg_exact(a.exact) if a.exact else None)


def sqrt(a: Scalar) -> Scalar:
    e = sqrt_exact(a.exact) if a.exact else None
    return Scalar(math.sqrt(a.approx) if a.approx >= 0 else float("nan"), e)


def is_zero(s: Scalar) -> bool:
    """0 chính xác khi có exact, ngược lại theo ngưỡng float."""
    if s.exact is not None:
        return s.exact.q == 0
    return abs(s.approx) < 1e-9


def cmp_scalar(a: Scalar, b: Scalar) -> int:
    """So sánh 2 Scalar -> -1 / 0 / 1. Chính xác khi cả hai exact cùng radicand; ngược lại dùng float."""
    if a.exact is not None and b.exact is not None and a.exact.radicand == b.exact.radicand:
        # so (q_a)√r với (q_b)√r ⇔ so q_a với q_b (√r>0)
        if a.exact.q < b.exact.q:
            return -1
        return 1 if a.exact.q > b.exact.q else 0
    d = a.approx - b.approx
    return 0 if abs(d) < 1e-9 else (-1 if d < 0 else 1)
