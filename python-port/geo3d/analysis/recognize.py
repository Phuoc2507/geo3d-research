# -*- coding: utf-8 -*-
"""
recognize.py — dịch từ api/_lib/kernel/analysis/recognize.ts

Nhận dạng một số thực về dạng "căn đẹp": hữu tỉ, a√b/c, p+q√r, hoặc dạng π (kπ/m, p+qπ).
CHỈ chấp nhận khi dựng-lại khớp x tới EPS (chặn khớp giả). Ưu tiên dạng đơn giản trước.
Đây là tầng "làm đẹp" số thập phân thành dạng căn/π; ở các nhánh số dùng float như bản gốc.
"""
from __future__ import annotations
import math

EPS = 1e-10


def _is_square_free(n: int) -> bool:
    if n < 2:
        return False
    d = 2
    while d * d <= n:
        if n % (d * d) == 0:
            return False
        d += 1
    return True


def _square_free_up_to(n: int) -> list[int]:
    return [k for k in range(2, n + 1) if _is_square_free(k)]


SQUAREFREE = _square_free_up_to(400)
MAX_DEN = 200


class Recognized:
    """Kết quả nhận dạng: .text (chuỗi đẹp) + .value (giá trị số dựng lại)."""
    __slots__ = ("text", "value")

    def __init__(self, text: str, value: float):
        self.text = text
        self.value = value

    def __repr__(self) -> str:
        return f"Recognized({self.text!r}, {self.value!r})"


def _round_half_up(v: float) -> int:
    """Giống Math.round của JS (làm tròn nửa lên +∞), khác round() của Python (nửa về chẵn)."""
    return math.floor(v + 0.5)


def _gcd(a: int, b: int) -> int:
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a or 1


def _as_rational(x: float, max_den: int):
    """Xấp xỉ x bằng phân số p/q (|q|≤max_den) nếu khớp EPS; trả dạng rút gọn (p, q) hoặc None."""
    for q in range(1, max_den + 1):
        p = _round_half_up(x * q)
        if abs(x - p / q) < EPS:
            g = _gcd(p, q)
            return (p // g, q // g)
    return None


def _fmt_rational(p: int, q: int) -> str:
    return f"{p}" if q == 1 else f"{p}/{q}"


def _fmt_surd_term(num: int, den: int, rad: int) -> str:
    """Định dạng số hạng căn (num/den)·√rad với num>0 giả định; caller lo dấu."""
    coeff = f"√{rad}" if num == 1 else f"{num}√{rad}"
    return coeff if den == 1 else f"{coeff}/{den}"


def _fmt_pi_term(num: int, den: int) -> str:
    """Định dạng số hạng π (num/den)·π với num>0 giả định; caller lo dấu."""
    coeff = "π" if num == 1 else f"{num}π"
    return coeff if den == 1 else f"{coeff}/{den}"


def recognize_constant(x: float):
    """Nhận dạng x -> Recognized(.text, .value) hoặc None nếu không khớp dạng đẹp nào."""
    # 1) Hữu tỉ
    q0 = _as_rational(x, MAX_DEN)
    if q0:
        p, q = q0
        return Recognized(_fmt_rational(p, q), p / q)

    # 2) a√b/c  (x = (p/q)·√b)
    for b in SQUAREFREE:
        s = x / math.sqrt(b)
        r = _as_rational(s, MAX_DEN)
        if r and r[0] != 0:
            rp, rq = r
            val = (rp / rq) * math.sqrt(b)
            if abs(val - x) < EPS:
                sign = "-" if rp < 0 else ""
                return Recognized(sign + _fmt_surd_term(abs(rp), rq, b), val)

    # 3) p + q√r  (nhị thức). Quét r và q hữu tỉ nhỏ; suy p rồi kiểm p hữu tỉ.
    for r in SQUAREFREE:
        root = math.sqrt(r)
        for qd in range(1, 9):
            for qn in range(-8, 9):
                if qn == 0:
                    continue
                qv = qn / qd
                p = _as_rational(x - qv * root, 16)
                if not p:
                    continue
                pp, pq = p
                val = pp / pq + qv * root
                if abs(val - x) < EPS:
                    q_abs_num = abs(qn)
                    g = _gcd(q_abs_num, qd)
                    surd = _fmt_surd_term(q_abs_num // g, qd // g, r)
                    op = "-" if qn < 0 else "+"
                    return Recognized(f"{_fmt_rational(pp, pq)} {op} {surd}", val)

    # 4) kπ/m  (x = (p/q)·π, den ≤ 64)
    rp = _as_rational(x / math.pi, 64)
    if rp and rp[0] != 0:
        pn, pq = rp
        val = (pn / pq) * math.pi
        if abs(val - x) < EPS:
            sign = "-" if pn < 0 else ""
            return Recognized(sign + _fmt_pi_term(abs(pn), pq), val)

    # 5) p + qπ  (quét q hữu tỉ nhỏ; suy p rồi kiểm p hữu tỉ den ≤ 16)
    for qd in range(1, 9):
        for qn in range(-8, 9):
            if qn == 0:
                continue
            qv = qn / qd
            p = _as_rational(x - qv * math.pi, 16)
            if not p or p[0] == 0:  # p=0 ⇒ đã bắt ở nhánh kπ/m
                continue
            pp, pq = p
            val = pp / pq + qv * math.pi
            if abs(val - x) < EPS:
                q_abs_num = abs(qn)
                g = _gcd(q_abs_num, qd)
                pi_term = _fmt_pi_term(q_abs_num // g, qd // g)
                op = "-" if qn < 0 else "+"
                return Recognized(f"{_fmt_rational(pp, pq)} {op} {pi_term}", val)

    return None
