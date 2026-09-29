# -*- coding: utf-8 -*-
"""
verify.py — dịch từ api/_lib/kernel/verify.ts

Kiểm các RÀNG BUỘC của đề (⊥, ∥, đồng phẳng, thuộc, khoảng cách, góc).
Nếu mô hình vi phạm giả thiết -> trả 'violation' thay vì để engine tính bừa.

Lưu ý xử lý đường–mặt: directionOf(plane) trả PHÁP TUYẾN, nên:
  - line ⊥ plane  ⟺ line song song pháp tuyến  (|cos| ≈ 1)
  - line ∥ plane  ⟺ line vuông góc pháp tuyến  (|cos| ≈ 0)
"""
from __future__ import annotations
import math
from .entities import Point, Line, Plane

DIST_TOL = 1e-6
ANGLE_TOL_DEG = 1e-3


def _dir_of(e):
    """Vector đại diện: đường -> chỉ phương; mặt -> pháp tuyến (dạng float)."""
    if isinstance(e, Line):
        return e.dir.approx()
    if isinstance(e, Plane):
        return e.n.approx()
    raise ValueError(f"không lấy được hướng cho {type(e).__name__}")


def _sub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def _dot(a, b): return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def _cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def _len(a): return math.sqrt(_dot(a, a))
def _norm(a):
    l = _len(a)
    return (a[0]/l, a[1]/l, a[2]/l) if l else (0.0, 0.0, 0.0)


def _is_line_plane(a, b):
    return (isinstance(a, Line) and isinstance(b, Plane)) or (isinstance(a, Plane) and isinstance(b, Line))


class Violation:
    def __init__(self, relation, message, expected=None, actual=None):
        self.relation = relation
        self.message = message
        self.expected = expected
        self.actual = actual

    def __repr__(self):
        return f"VIOLATION[{self.relation}] {self.message}"


def assert_perp(a, b) -> Violation | None:
    raw = abs(_dot(_norm(_dir_of(a)), _norm(_dir_of(b))))
    actual = (1 - raw) if _is_line_plane(a, b) else raw
    if actual < DIST_TOL:
        return None
    return Violation("perp", f"Chờ ⊥ nhưng |cos| = {raw:.6f}", 0, actual)


def assert_parallel(a, b) -> Violation | None:
    da, db = _norm(_dir_of(a)), _norm(_dir_of(b))
    actual = abs(_dot(da, db)) if _is_line_plane(a, b) else _len(_cross(da, db))
    if actual < DIST_TOL:
        return None
    return Violation("parallel", f"Chờ ∥ nhưng lệch = {actual:.6f}", 0, actual)


def assert_coplanar(points: list[Point]) -> Violation | None:
    pos = [p.p.approx() for p in points]
    if len(pos) <= 3:
        return None
    p0 = pos[0]
    n = _cross(_sub(pos[1], p0), _sub(pos[2], p0))
    nl = _len(n)
    if nl < 1e-12:
        return None
    for p in pos:
        if abs(_dot(_sub(p, p0), n)) / nl > DIST_TOL:
            return Violation("coplanar", "Các điểm không đồng phẳng")
    return None


def _dist_point_line(p, a, b):
    ab = _sub(b, a)
    return _len(_cross(_sub(p, a), ab)) / _len(ab)


def _dist_point_plane(p, pt_on, n):
    return abs(_dot(_sub(p, pt_on), n)) / _len(n)


def assert_on(p: Point, e) -> Violation | None:
    """Điểm p có nằm trên đường/mặt e không."""
    pp = p.p.approx()
    if isinstance(e, Line):
        a = e.p.approx()
        dv = e.dir.approx()
        b = (a[0] + dv[0], a[1] + dv[1], a[2] + dv[2])   # điểm thứ hai trên đường
        actual = _dist_point_line(pp, a, b)
    elif isinstance(e, Plane):
        actual = _dist_point_plane(pp, _point_on_plane(e), e.n.approx())
    else:
        raise ValueError("'on' cần đường hoặc mặt")
    if actual < DIST_TOL:
        return None
    return Violation("on", f"Chờ điểm nằm trên, nhưng khoảng cách = {actual:.6f}", 0, actual)


def _point_on_plane(pl: Plane):
    """Một điểm bất kỳ trên mặt n·x+d=0: lấy chân vuông góc từ gốc = -d/|n|² · n."""
    n = pl.n.approx()
    d = pl.d.approx
    k = -d / _dot(n, n)
    return (n[0]*k, n[1]*k, n[2]*k)


def assert_dist(a, b, expected: float) -> Violation | None:
    if isinstance(a, Point) and isinstance(b, Point):
        actual = _len(_sub(a.p.approx(), b.p.approx()))
    elif isinstance(a, Point) and isinstance(b, Plane):
        actual = _dist_point_plane(a.p.approx(), _point_on_plane(b), b.n.approx())
    else:
        raise ValueError("dist: tổ hợp chưa hỗ trợ")
    if abs(actual - expected) < DIST_TOL:
        return None
    return Violation("dist", f"Chờ dist = {expected}, nhận {actual:.6f}", expected, actual)
