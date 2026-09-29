# -*- coding: utf-8 -*-
"""
oxyz_input.py — dịch từ api/_lib/kernel/dialects/oxyzInput.ts

Parser toạ độ/số cho dialect Oxyz: số nguyên/thập phân/phân số + căn đơn.
  parseRational(5)        -> Exact(5)          (số nguyên)
  parseRational(1.5)      -> Exact(3/2)        (thập phân dạng number)
  parseRational('3/2')    -> Exact(3/2)        (phân số chuỗi)
  parseRational('2√3')    -> Exact(2·√3)       (căn)
  parseRational('sqrt(3)/2') -> Exact((1/2)·√3)
Rời trường an toàn: số dạng mũ (1e-7) -> ném, buộc truyền dạng chuỗi phân số.
"""
from __future__ import annotations
import re
from fractions import Fraction
from . import scalar as S
from .scalar import Exact, Scalar
from . import vec3 as V
from .vec3 import Vec3

RationalInput = "int | float | str"

_DEC_RE_A = re.compile(r"^\d*\.?\d+$")
_DEC_RE_B = re.compile(r"^\d+\.?\d*$")
INT_RE = re.compile(r"^[+-]?\d+$")


def _decimal_to_exact(s: str) -> Exact:
    """"1.5" / "-0.25" / "12" (thập phân hoặc nguyên, không mũ) -> Exact hữu tỉ."""
    neg = s.startswith("-")
    body = s[1:] if neg else s
    if not _DEC_RE_A.match(body) and not _DEC_RE_B.match(body):
        raise ValueError(f'Cannot parse rational from "{s}" (use "p/q" for fractions)')
    dot = body.find(".")
    if dot == -1:
        v = int(body)
        return Exact(Fraction(-v if neg else v), 1)
    int_part = body[:dot] or "0"
    frac_part = body[dot + 1:] or "0"
    den = 10 ** len(frac_part)
    num_abs = int(int_part) * den + int(frac_part)
    return Exact(Fraction(-num_abs if neg else num_abs, den), 1)


_SURD_NORMALIZE = re.compile(r"√\s*\(?\s*(\d+)\s*\)?")
_SURD_RE = re.compile(
    r"^([+-]?)(?:(\d+)(?:/(\d+))?\*?)?sqrt\((\d+)\)(?:/(\d+))?$", re.IGNORECASE
)


def _parse_surd(raw: str) -> Exact | None:
    """"sqrt(3)", "√3", "2*sqrt(3)", "sqrt(3)/2", "2*sqrt(3)/3", "-sqrt(5)/2" -> (num/den)·√rad."""
    s = _SURD_NORMALIZE.sub(r"sqrt(\1)", raw)
    s = re.sub(r"\s+", "", s)
    m = _SURD_RE.match(s)
    if not m:
        return None
    sign = -1 if m.group(1) == "-" else 1
    cnum = int(m.group(2)) if m.group(2) else 1
    cden = int(m.group(3)) if m.group(3) else 1
    rad = int(m.group(4))
    den = int(m.group(5)) if m.group(5) else 1
    return Exact(Fraction(sign * cnum, cden * den), rad)  # (sign·cnum)/(cden·den) · √rad


def parse_rational(input_) -> Exact:
    if isinstance(input_, bool):
        raise ValueError("Rational input must be a number or string, not bool")
    if isinstance(input_, (int, float)):
        import math
        if not math.isfinite(input_):
            raise ValueError("Rational input must be finite")
        # số nguyên (int, hoặc float nguyên như 5.0)
        if isinstance(input_, int) or float(input_).is_integer():
            return Exact(Fraction(int(input_)), 1)
        s = repr(input_)
        if "e" in s or "E" in s:
            raise ValueError(f'Number "{s}" is in exponent form; pass it as a string fraction instead')
        return _decimal_to_exact(s)

    s = input_.strip()
    if re.search(r"sqrt|√", s, re.IGNORECASE):
        surd = _parse_surd(s)
        if surd is None:
            raise ValueError(f'Cannot parse surd from "{input_}" (dùng "sqrt(3)", "sqrt(3)/2", "2*sqrt(3)")')
        return surd
    if "/" in s:
        parts = s.split("/")
        if len(parts) != 2 or not INT_RE.match(parts[0].strip()) or not INT_RE.match(parts[1].strip()):
            raise ValueError(f'Cannot parse rational from "{input_}" (expected "p/q" with integer p, q)')
        return Exact(Fraction(int(parts[0].strip()), int(parts[1].strip())), 1)  # ném nếu q = 0
    return _decimal_to_exact(s)


def parse_scalar(input_) -> Scalar:
    return S.from_exact(parse_rational(input_))


def parse_vec3s(c) -> Vec3:
    """c = [x, y, z] mỗi phần tử là số hoặc chuỗi."""
    return V.vec(parse_scalar(c[0]), parse_scalar(c[1]), parse_scalar(c[2]))
