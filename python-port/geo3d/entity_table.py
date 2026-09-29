# -*- coding: utf-8 -*-
"""
entity_table.py — dịch từ api/_lib/kernel/entityTable.ts (+ setPointE… từ dialects/oxyz.ts)

Bảng thực thể: điểm/đường/mặt/cầu tra theo tên, cùng lớp mesh kế thừa (faces/edges/derivedPoints).
Tên phải DUY NHẤT xuyên mọi loại entity — nếu không resolver (point→line→plane→sphere) sẽ âm
thầm che entity trùng tên. Vì thế set_* luôn bắt va chạm định-nghĩa-lại qua ensure_name_free.
"""
from __future__ import annotations
from . import entities as E
from .entities import Point, Line, Plane, Sphere
from .vec3 import Vec3


class EntityTable:
    __slots__ = ("points", "lines", "planes", "spheres", "faces", "edges", "derived_points")

    def __init__(self):
        self.points: dict[str, Point] = {}
        self.lines: dict[str, Line] = {}
        self.planes: dict[str, Plane] = {}
        self.spheres: dict[str, Sphere] = {}
        # Lớp mesh/render kế thừa Phase 1:
        self.faces: dict[str, list[str]] = {}
        self.edges: set[str] = set()
        self.derived_points: set[str] = set()


def create_empty_entity_table() -> EntityTable:
    return EntityTable()


def ensure_name_free(et: EntityTable, name: str, kind: str) -> None:
    if name in et.points or name in et.lines or name in et.planes or name in et.spheres:
        raise ValueError(f'Oxyz: name "{name}" is already used; cannot define {kind} "{name}"')


def set_point(et: EntityTable, name: str, p: Vec3, derived: bool = False) -> None:
    """`derived` đánh dấu điểm phụ trợ (midpoint/ratio/centroid/reflect/foot…) để tầng trên
    xử lý suy biến giống derived points của dialect tổng hợp."""
    ensure_name_free(et, name, "point")
    et.points[name] = E.point_from_coords(p)
    if derived:
        et.derived_points.add(name)


def set_line(et: EntityTable, name: str, l: Line) -> None:
    ensure_name_free(et, name, "line")
    et.lines[name] = l


def set_plane(et: EntityTable, name: str, pl: Plane) -> None:
    ensure_name_free(et, name, "plane")
    et.planes[name] = pl


def set_sphere(et: EntityTable, name: str, s: Sphere) -> None:
    ensure_name_free(et, name, "sphere")
    et.spheres[name] = s
