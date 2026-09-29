# -*- coding: utf-8 -*-
"""
round_solids.py — dịch từ api/_lib/kernel/compute/roundSolids.ts

Khối tròn xoay THPT: NÓN, TRỤ, NÓN CỤT, CHÓP CỤT. Nhận r/h là số hoặc chuỗi ("3", "3/2",
"sqrt(3)", "√3", "2*sqrt(3)/3"), trả đáp DẠNG π / CĂN chính xác (tái dùng _pi_answer /
certify_scalar của compute.py).
  • Nón:   V=(1/3)πr²h ·  Sxq=πrl ·  Stp=πr(l+r) ·  l=√(r²+h²)
  • Trụ:   V=πr²h ·       Sxq=2πrh · Stp=2πr(h+r)
  • Nón cụt: V=(1/3)πh(R²+Rr+r²) · Sxq=π(R+r)l · Stp=π(R+r)l+πR²+πr² · l=√(h²+(R−r)²)
  • Chóp cụt (đáy S1,S2, cao h, KHÔNG π): V=(1/3)h(S1+S2+√(S1·S2))
"""
from __future__ import annotations
import re
import math
from fractions import Fraction
from . import scalar as S
from .scalar import Scalar, Exact
from . import compute as C

# ---- parser Scalar nhỏ gọn (dịch ý parseRational/parseSurd của oxyzInput) ----
_INT_RE = re.compile(r"^[+-]?\d+$")
_DEC_RE = re.compile(r"^\d*\.?\d+$|^\d+\.?\d*$")
_SURD_RE = re.compile(r"^([+-]?)(?:(\d+)(?:/(\d+))?\*?)?sqrt\((\d+)\)(?:/(\d+))?$", re.IGNORECASE)


def _decimal_to_exact(s: str) -> Exact:
    neg = s.startswith("-")
    body = s[1:] if neg else s
    if not _DEC_RE.match(body):
        raise ValueError(f'Không phân tích được số hữu tỉ từ "{s}" (dùng "p/q" cho phân số)')
    if "." not in body:
        v = int(body)
        return Exact(Fraction(-v if neg else v), 1)
    dot = body.index(".")
    int_part = body[:dot] or "0"
    frac_part = body[dot + 1:] or "0"
    den = 10 ** len(frac_part)
    num_abs = int(int_part) * den + int(frac_part)
    return Exact(Fraction(-num_abs if neg else num_abs, den), 1)


def _parse_surd(raw: str) -> Exact | None:
    s = re.sub(r"√\s*\(?\s*(\d+)\s*\)?", r"sqrt(\1)", raw)
    s = re.sub(r"\s+", "", s)
    m = _SURD_RE.match(s)
    if not m:
        return None
    sign = -1 if m.group(1) == "-" else 1
    cnum = int(m.group(2)) if m.group(2) else 1
    cden = int(m.group(3)) if m.group(3) else 1
    rad = int(m.group(4))
    den = int(m.group(5)) if m.group(5) else 1
    return Exact(Fraction(sign * cnum, cden * den), rad)   # (sign·cnum)/(cden·den)·√rad


def parse_scalar(x) -> Scalar:
    if isinstance(x, bool):
        raise ValueError("đầu vào không hợp lệ")
    if isinstance(x, int):
        return S.from_exact(Exact(Fraction(x), 1))
    if isinstance(x, float):
        if not math.isfinite(x):
            raise ValueError("số phải hữu hạn")
        if x.is_integer():
            return S.from_exact(Exact(Fraction(int(x)), 1))
        return S.from_exact(_decimal_to_exact(repr(x)))
    s = str(x).strip()
    if re.search(r"sqrt|√", s, re.IGNORECASE):
        surd = _parse_surd(s)
        if surd is None:
            raise ValueError(f'Không phân tích được căn từ "{x}" (dùng "sqrt(3)", "sqrt(3)/2", "2*sqrt(3)")')
        return S.from_exact(surd)
    if "/" in s:
        parts = s.split("/")
        if len(parts) != 2 or not _INT_RE.match(parts[0].strip()) or not _INT_RE.match(parts[1].strip()):
            raise ValueError(f'Không phân tích được số hữu tỉ từ "{x}" (mong đợi "p/q")')
        return S.from_exact(Exact(Fraction(int(parts[0]), int(parts[1])), 1))
    return S.from_exact(_decimal_to_exact(s))


_S = parse_scalar


# ---- đường sinh ----
def _slant(r: Scalar, h: Scalar) -> Scalar:
    return S.sqrt(S.add(S.mul(r, r), S.mul(h, h)))          # √(r²+h²)


def _frustum_slant(R: Scalar, r: Scalar, h: Scalar) -> Scalar:
    d = S.sub(R, r)
    return S.sqrt(S.add(S.mul(h, h), S.mul(d, d)))          # √(h²+(R−r)²)


# ---- NÓN ----
def cone_volume(r_in, h_in):
    r, h = _S(r_in), _S(h_in)
    coeff = S.mul(S.rat(1, 3), S.mul(S.mul(r, r), h))       # (1/3)·r²·h
    return C._pi_answer("volume", coeff, (1 / 3) * math.pi * r.approx * r.approx * h.approx)


def cone_slant(r_in, h_in):
    r, h = _S(r_in), _S(h_in)
    return C.certify_scalar("slant", _slant(r, h), math.hypot(r.approx, h.approx))


def cone_area(r_in, h_in, part: str):
    r, h = _S(r_in), _S(h_in)
    l = _slant(r, h)
    lf = math.hypot(r.approx, h.approx)
    if part == "lateral":
        return C._pi_answer("area", S.mul(r, l), math.pi * r.approx * lf)          # π r l
    return C._pi_answer("area", S.mul(r, S.add(l, r)), math.pi * r.approx * (lf + r.approx))  # π r (l+r)


# ---- TRỤ ----
def cylinder_volume(r_in, h_in):
    r, h = _S(r_in), _S(h_in)
    return C._pi_answer("volume", S.mul(S.mul(r, r), h), math.pi * r.approx * r.approx * h.approx)


def cylinder_area(r_in, h_in, part: str):
    r, h = _S(r_in), _S(h_in)
    if part == "lateral":
        return C._pi_answer("area", S.mul(S.rat(2), S.mul(r, h)), 2 * math.pi * r.approx * h.approx)  # 2π r h
    return C._pi_answer("area", S.mul(S.rat(2), S.mul(r, S.add(h, r))),
                        2 * math.pi * r.approx * (h.approx + r.approx))                               # 2π r (h+r)


# ---- NÓN CỤT ----
def cone_frustum_volume(R_in, r_in, h_in):
    R, r, h = _S(R_in), _S(r_in), _S(h_in)
    coeff = S.mul(S.rat(1, 3), S.mul(h, S.add(S.add(S.mul(R, R), S.mul(R, r)), S.mul(r, r))))
    rf = (1 / 3) * math.pi * h.approx * (R.approx * R.approx + R.approx * r.approx + r.approx * r.approx)
    return C._pi_answer("volume", coeff, rf)


def cone_frustum_slant(R_in, r_in, h_in):
    R, r, h = _S(R_in), _S(r_in), _S(h_in)
    return C.certify_scalar("slant", _frustum_slant(R, r, h), math.hypot(h.approx, R.approx - r.approx))


def cone_frustum_area(R_in, r_in, h_in, part: str):
    R, r, h = _S(R_in), _S(r_in), _S(h_in)
    l = _frustum_slant(R, r, h)
    lf = math.hypot(h.approx, R.approx - r.approx)
    lateral_coeff = S.mul(S.add(R, r), l)                   # (R+r) l
    lat_rf = math.pi * (R.approx + r.approx) * lf
    if part == "lateral":
        return C._pi_answer("area", lateral_coeff, lat_rf)  # π(R+r)l
    coeff = S.add(lateral_coeff, S.add(S.mul(R, R), S.mul(r, r)))
    rf = lat_rf + math.pi * (R.approx * R.approx + r.approx * r.approx)
    return C._pi_answer("area", coeff, rf)


# ---- CHÓP CỤT (đáy S1, S2, cao h; KHÔNG có π) ----
def pyramid_frustum_volume(s1_in, s2_in, h_in):
    s1, s2, h = _S(s1_in), _S(s2_in), _S(h_in)
    coeff = S.mul(S.rat(1, 3), S.mul(h, S.add(S.add(s1, s2), S.sqrt(S.mul(s1, s2)))))
    rf = (1 / 3) * h.approx * (s1.approx + s2.approx + math.sqrt(s1.approx * s2.approx))
    return C.certify_scalar("volume", coeff, rf)
