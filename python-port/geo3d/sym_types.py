# -*- coding: utf-8 -*-
"""
sym_types.py — dịch từ api/_lib/kernel/types.ts + api/_lib/kernel/vecMath.ts

Kiểu dữ liệu & phép toán FLOAT cho dialect TỔNG HỢP (synthetic).
Khác hẳn scalar.py/vec3.py (số lai exact) của dialect Oxyz: ở đây toạ độ là float thuần
(giống bản gốc TypeScript dùng number), phục vụ SymbolTable của execute.ts.

Gộp:
  - types.ts   : Vec3 (float), SymbolTable, ResolvedEntity, Violation.
  - vecMath.ts : add/sub/scale/dot/cross/length/normalize/plane_normal/project… + EPS.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import math

EPS = 1e-6


# ============================ Vec3 (float) ============================
@dataclass
class Vec3:
    x: float
    y: float
    z: float


def vec3(x: float, y: float, z: float) -> Vec3:
    return Vec3(x, y, z)


def add(a: Vec3, b: Vec3) -> Vec3:
    return Vec3(a.x + b.x, a.y + b.y, a.z + b.z)


def sub(a: Vec3, b: Vec3) -> Vec3:
    return Vec3(a.x - b.x, a.y - b.y, a.z - b.z)


def scale(a: Vec3, s: float) -> Vec3:
    return Vec3(a.x * s, a.y * s, a.z * s)


def dot(a: Vec3, b: Vec3) -> float:
    return a.x * b.x + a.y * b.y + a.z * b.z


def cross(a: Vec3, b: Vec3) -> Vec3:
    return Vec3(
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x,
    )


def length(a: Vec3) -> float:
    return math.sqrt(dot(a, a))


def normalize(a: Vec3) -> Vec3:
    ln = length(a)
    if ln < EPS:
        raise ValueError("Cannot normalize a zero-length vector")
    return Vec3(a.x / ln, a.y / ln, a.z / ln)


def lerp(a: Vec3, b: Vec3, t: float) -> Vec3:
    return add(a, scale(sub(b, a), t))


def centroid_of(points: list[Vec3]) -> Vec3:
    if len(points) == 0:
        raise ValueError("Cannot compute centroid of an empty point list")
    total = Vec3(0.0, 0.0, 0.0)
    for p in points:
        total = add(total, p)
    return scale(total, 1 / len(points))


def distance(a: Vec3, b: Vec3) -> float:
    return length(sub(a, b))


def plane_normal(p1: Vec3, p2: Vec3, p3: Vec3) -> Vec3:
    """Pháp tuyến đơn vị của mặt qua p1,p2,p3, lật về phía +z khi mặt không (gần) thẳng đứng.
    Ném nếu 3 điểm thẳng hàng."""
    n = cross(sub(p2, p1), sub(p3, p1))
    ln = length(n)
    if ln < EPS:
        raise ValueError("Cannot compute a plane normal: the three points are collinear")
    unit = scale(n, 1 / ln)
    if unit.z < -EPS:
        unit = scale(unit, -1)
    return unit


def distance_point_to_plane(p: Vec3, plane_point: Vec3, normal: Vec3) -> float:
    return abs(dot(sub(p, plane_point), normal))


def project_point_onto_plane(p: Vec3, plane_point: Vec3, normal: Vec3) -> Vec3:
    d = dot(sub(p, plane_point), normal)
    return sub(p, scale(normal, d))


def distance_point_to_line(p: Vec3, a: Vec3, b: Vec3) -> float:
    d = normalize(sub(b, a))
    ap = sub(p, a)
    proj = scale(d, dot(ap, d))
    return length(sub(ap, proj))


def project_point_onto_line(p: Vec3, a: Vec3, b: Vec3) -> Vec3:
    d = normalize(sub(b, a))
    t = dot(sub(p, a), d)
    return add(a, scale(d, t))


# ============================ SymbolTable ============================
@dataclass
class SymbolTable:
    """Bảng ký hiệu FLOAT của dialect tổng hợp.
      - points        : tên → Vec3 (float)
      - named_planes  : tên mặt (vd 'ABCD') → danh sách tên đỉnh
      - edges         : khoá 'A|B' (A<B) cho từng cạnh
      - derived_points: tên điểm dẫn xuất (midpoint/foot/intersect…) — được miễn suy biến
    """
    points: dict[str, Vec3] = field(default_factory=dict)
    named_planes: dict[str, list[str]] = field(default_factory=dict)
    edges: set[str] = field(default_factory=set)
    derived_points: set[str] = field(default_factory=set)


# ============================ ResolvedEntity ============================
@dataclass
class RPoint:
    name: str
    pos: Vec3
    type: str = "point"


@dataclass
class RLine:
    a: str
    b: str
    pos_a: Vec3
    pos_b: Vec3
    type: str = "line"


@dataclass
class RPlane:
    points: list[str]
    positions: list[Vec3]
    type: str = "plane"


# ============================ Violation ============================
@dataclass
class Violation:
    kind: str                      # 'assert_failed' | 'degenerate' | 'underconstrained'
    message: str = ""
    relation: str | None = None
    args: list[str] | None = None
    expected: float | None = None
    actual: float | None = None
