# -*- coding: utf-8 -*-
"""
synthetic_execute.py — dịch từ api/_lib/kernel/execute.ts (+ ops/shapes.ts, ops/extrude.ts, ops/points.ts)

Thực thi op dựng hình của dialect TỔNG HỢP trên SymbolTable (float). Mỗi op là dict:
  {"op": "base", "shape": "square", "vertices": ["A","B","C","D"], "dims": {"edge": 1}}
  {"op": "perp_point", "name": "S", "from": "A", "to": "plane", "target": "ABCD", "length": ...}
  {"op": "foot", "name": "H", "from": "K", "onto": "plane", "target": "ABC"}
  {"op": "point", "name": "M", "def": {"kind": "midpoint", "of": ["A","B"]}}
  {"op": "intersect", "name": "G", "a": "AM", "b": "BN"}
  {"op": "edge", "from": "S", "to": "A"}

Các ops phụ trợ (shapes/extrude/points) được nội tuyến ở đây để KHÔNG phải tạo package con,
giữ đúng thuật toán float của bản gốc.
"""
from __future__ import annotations
import math
from .sym_types import (
    Vec3, vec3, add, sub, scale, dot, cross, length,
    centroid_of, plane_normal, project_point_onto_plane, project_point_onto_line,
    SymbolTable, EPS,
)
from .synthetic_resolve import resolve_entity


# ============================ ops/shapes.ts ============================
def build_square(edge: float) -> list[Vec3]:
    h = edge / 2
    return [vec3(-h, -h, 0), vec3(h, -h, 0), vec3(h, h, 0), vec3(-h, h, 0)]


def build_rectangle(width: float, height: float) -> list[Vec3]:
    hw = width / 2
    hh = height / 2
    return [vec3(-hw, -hh, 0), vec3(hw, -hh, 0), vec3(hw, hh, 0), vec3(-hw, hh, 0)]


def build_rhombus(diag1: float, diag2: float) -> list[Vec3]:
    h1 = diag1 / 2
    h2 = diag2 / 2
    return [vec3(-h1, 0, 0), vec3(0, -h2, 0), vec3(h1, 0, 0), vec3(0, h2, 0)]


def build_reg_polygon(n: int, edge: float) -> list[Vec3]:
    if n < 3:
        raise ValueError(f"reg_polygon requires n >= 3, got {n}")
    R = edge / (2 * math.sin(math.pi / n))
    pts: list[Vec3] = []
    for k in range(n):
        theta = (2 * math.pi * k) / n
        pts.append(vec3(R * math.cos(theta), R * math.sin(theta), 0))
    return pts


def build_triangle(dims: dict) -> list[Vec3]:
    tt = dims["triangleType"]
    if tt == "equilateral":
        a = dims["edge"]
        return [vec3(0, (a * math.sqrt(3)) / 2, 0), vec3(-a / 2, 0, 0), vec3(a / 2, 0, 0)]
    if tt == "right":
        leg1, leg2 = dims["leg1"], dims["leg2"]
        return [vec3(0, 0, 0), vec3(leg1, 0, 0), vec3(0, leg2, 0)]
    if tt == "isosceles":
        base, leg_length = dims["base"], dims["legLength"]
        half = base / 2
        h_sq = leg_length * leg_length - half * half
        if h_sq <= 0:
            raise ValueError(
                f"Invalid isosceles triangle: legLength ({leg_length}) too short for base ({base})"
            )
        h = math.sqrt(h_sq)
        return [vec3(0, h, 0), vec3(-half, 0, 0), vec3(half, 0, 0)]
    if tt == "sss":
        p1p2, p1p3, p2p3 = dims["p1p2"], dims["p1p3"], dims["p2p3"]
        if p1p2 + p1p3 <= p2p3 or p1p2 + p2p3 <= p1p3 or p1p3 + p2p3 <= p1p2:
            raise ValueError(
                f"Invalid triangle sides ({p1p2}, {p1p3}, {p2p3}): violate the triangle inequality"
            )
        p1 = vec3(0, 0, 0)
        p2 = vec3(p1p2, 0, 0)
        cos_angle = (p1p2 * p1p2 + p1p3 * p1p3 - p2p3 * p2p3) / (2 * p1p2 * p1p3)
        angle = math.acos(max(-1, min(1, cos_angle)))
        p3 = vec3(p1p3 * math.cos(angle), p1p3 * math.sin(angle), 0)
        return [p1, p2, p3]
    raise ValueError(f"unsupported triangleType: {tt}")


# ============================ ops/extrude.ts ============================
def extrude_prism(base_positions: list[Vec3], height: float) -> list[Vec3]:
    return [add(p, vec3(0, 0, height)) for p in base_positions]


def extrude_pyramid_apex(base_positions: list[Vec3], height: float) -> Vec3:
    c = centroid_of(base_positions)
    n = plane_normal(base_positions[0], base_positions[1], base_positions[2])
    return add(c, scale(n, height))


# ============================ ops/points.ts ============================
def midpoint(a: Vec3, b: Vec3) -> Vec3:
    return vec3((a.x + b.x) / 2, (a.y + b.y) / 2, (a.z + b.z) / 2)


def centroid_point(points: list[Vec3]) -> Vec3:
    total = vec3(0, 0, 0)
    for p in points:
        total = add(total, p)
    return scale(total, 1 / len(points))


def ratio_point(frm: Vec3, to: Vec3, t: float) -> Vec3:
    return add(frm, scale(sub(to, frm), t))


def reflect_point(point: Vec3, about: Vec3) -> Vec3:
    return sub(scale(about, 2), point)


def perp_point_from_plane(from_pos: Vec3, plane_positions: list[Vec3], length_: float) -> Vec3:
    p1, p2, p3 = plane_positions[0], plane_positions[1], plane_positions[2]
    n = plane_normal(p1, p2, p3)
    return add(from_pos, scale(n, length_))


def foot_on_plane(from_pos: Vec3, plane_positions: list[Vec3]) -> Vec3:
    p1, p2, p3 = plane_positions[0], plane_positions[1], plane_positions[2]
    n = plane_normal(p1, p2, p3)
    return project_point_onto_plane(from_pos, p1, n)


def foot_on_line(from_pos: Vec3, a: Vec3, b: Vec3) -> Vec3:
    return project_point_onto_line(from_pos, a, b)


def intersect_line_line(a1: Vec3, a2: Vec3, b1: Vec3, b2: Vec3) -> Vec3:
    d1 = sub(a2, a1)
    d2 = sub(b2, b1)
    r = sub(b1, a1)
    l1 = length(d1)
    l2 = length(d2)
    if l1 < EPS or l2 < EPS:
        raise ValueError("Degenerate line: a direction is zero-length (its two points coincide)")
    cross12 = cross(d1, d2)
    denom = dot(cross12, cross12)
    if length(cross12) / (l1 * l2) < EPS:
        raise ValueError("Lines are parallel; no unique intersection point exists")
    rlen = length(r)
    if rlen > EPS and abs(dot(r, cross12)) / (rlen * l1 * l2) > EPS:
        raise ValueError("Lines are skew (not coplanar); no intersection point exists")
    t = dot(cross(r, d2), cross12) / denom
    return add(a1, scale(d1, t))


def intersect_line_plane(a: Vec3, b: Vec3, plane_positions: list[Vec3]) -> Vec3:
    p1, p2, p3 = plane_positions[0], plane_positions[1], plane_positions[2]
    n = plane_normal(p1, p2, p3)
    d = sub(b, a)
    dlen = length(d)
    if dlen < EPS:
        raise ValueError("Degenerate line: its two points coincide (zero-length direction)")
    denom = dot(n, d)
    if abs(denom) / dlen < EPS:
        raise ValueError("Line is parallel to the plane; no unique intersection point exists")
    t = dot(n, sub(p1, a)) / denom
    return add(a, scale(d, t))


# ============================ execute.ts ============================
def create_empty_symbol_table() -> SymbolTable:
    return SymbolTable()


def _require_point(symtab: SymbolTable, name: str) -> Vec3:
    p = symtab.points.get(name)
    if p is None:
        raise ValueError(f'Unknown point "{name}" referenced before it was defined')
    return p


def _set_point(symtab: SymbolTable, name: str, pos: Vec3) -> None:
    if name in symtab.points:
        raise ValueError(f'Point "{name}" is already defined')
    symtab.points[name] = pos


def _set_derived_point(symtab: SymbolTable, name: str, pos: Vec3) -> None:
    """Đăng ký điểm dẫn xuất — như _set_point nhưng đánh dấu derived để nới lỏng suy biến."""
    _set_point(symtab, name, pos)
    symtab.derived_points.add(name)


def _edge_key(a: str, b: str) -> str:
    return f"{a}|{b}" if a < b else f"{b}|{a}"


def _add_edge(symtab: SymbolTable, a: str, b: str) -> None:
    symtab.edges.add(_edge_key(a, b))


def _add_cyclic_edges(symtab: SymbolTable, verts: list[str]) -> None:
    n = len(verts)
    for i in range(n):
        _add_edge(symtab, verts[i], verts[(i + 1) % n])


def execute_op(op: dict, symtab: SymbolTable) -> None:
    kind = op["op"]

    if kind == "base":
        shape = op["shape"]
        dims = op["dims"]
        if shape == "square":
            positions = build_square(dims["edge"])
        elif shape == "rectangle":
            positions = build_rectangle(dims["width"], dims["height"])
        elif shape == "rhombus":
            positions = build_rhombus(dims["diag1"], dims["diag2"])
        elif shape == "reg_polygon":
            positions = build_reg_polygon(dims["n"], dims["edge"])
        elif shape == "triangle":
            positions = build_triangle(dims)
        else:
            raise ValueError(f"base: unsupported shape {shape}")
        for i, name in enumerate(op["vertices"]):
            _set_point(symtab, name, positions[i])
        symtab.named_planes["".join(op["vertices"])] = list(op["vertices"])
        _add_cyclic_edges(symtab, op["vertices"])

    elif kind == "prism":
        base_positions = [_require_point(symtab, n) for n in op["base"]]
        top_positions = extrude_prism(base_positions, op["height"])
        for i, name in enumerate(op["top"]):
            _set_point(symtab, name, top_positions[i])
        symtab.named_planes["".join(op["top"])] = list(op["top"])
        _add_cyclic_edges(symtab, op["top"])
        for i, base_name in enumerate(op["base"]):
            _add_edge(symtab, base_name, op["top"][i])

    elif kind == "pyramid":
        base_positions = [_require_point(symtab, n) for n in op["base"]]
        apex_pos = extrude_pyramid_apex(base_positions, op["height"])
        _set_point(symtab, op["apex"], apex_pos)
        for base_name in op["base"]:
            _add_edge(symtab, op["apex"], base_name)

    elif kind == "point":
        d = op["def"]
        dk = d["kind"]
        if dk == "midpoint":
            pos = midpoint(_require_point(symtab, d["of"][0]), _require_point(symtab, d["of"][1]))
        elif dk == "centroid":
            pos = centroid_point([_require_point(symtab, n) for n in d["of"]])
        elif dk == "ratio":
            pos = ratio_point(_require_point(symtab, d["from"]), _require_point(symtab, d["to"]), d["t"])
        elif dk == "reflect":
            pos = reflect_point(_require_point(symtab, d["point"]), _require_point(symtab, d["about"]))
        else:
            raise ValueError(f"point: unsupported def kind {dk}")
        _set_derived_point(symtab, op["name"], pos)

    elif kind == "perp_point":
        from_pos = _require_point(symtab, op["from"])
        plane = resolve_entity(op["target"], symtab)
        if plane.type != "plane":
            raise ValueError(
                f'perp_point target "{op["target"]}" must resolve to a plane, got "{plane.type}"'
            )
        _set_derived_point(
            symtab, op["name"], perp_point_from_plane(from_pos, plane.positions[0:3], op["length"])
        )

    elif kind == "foot":
        from_pos = _require_point(symtab, op["from"])
        target = resolve_entity(op["target"], symtab)
        if op["onto"] == "plane":
            if target.type != "plane":
                raise ValueError(f'foot onto plane: "{op["target"]}" must resolve to a plane')
            pos = foot_on_plane(from_pos, target.positions[0:3])
        else:
            if target.type != "line":
                raise ValueError(f'foot onto line: "{op["target"]}" must resolve to a line')
            pos = foot_on_line(from_pos, target.pos_a, target.pos_b)
        _set_derived_point(symtab, op["name"], pos)

    elif kind == "intersect":
        a = resolve_entity(op["a"], symtab)
        b = resolve_entity(op["b"], symtab)
        if a.type == "line" and b.type == "line":
            pos = intersect_line_line(a.pos_a, a.pos_b, b.pos_a, b.pos_b)
        elif a.type == "line" and b.type == "plane":
            pos = intersect_line_plane(a.pos_a, a.pos_b, b.positions[0:3])
        elif a.type == "plane" and b.type == "line":
            pos = intersect_line_plane(b.pos_a, b.pos_b, a.positions[0:3])
        else:
            raise ValueError(
                f'intersect: unsupported combination "{a.type}" x "{b.type}" '
                f"(plane-plane intersection is out of scope for Phase 1)"
            )
        _set_derived_point(symtab, op["name"], pos)

    elif kind == "edge":
        _require_point(symtab, op["from"])
        _require_point(symtab, op["to"])
        _add_edge(symtab, op["from"], op["to"])

    else:
        raise ValueError(f"executeOp: op không hỗ trợ: {kind}")


def execute_plan(plan: dict) -> SymbolTable:
    symtab = create_empty_symbol_table()
    for op in plan["ops"]:
        execute_op(op, symtab)
    return symtab
