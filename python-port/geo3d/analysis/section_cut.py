# -*- coding: utf-8 -*-
"""
section_cut.py — dịch từ api/_lib/kernel/analysis/sectionCut.ts

Thiết diện = mặt phẳng ∩ khối đa diện lồi. LLM chỉ trích tham số; engine dựng & kiểm.
Vec3 là tuple (x, y, z). Poly là dict {'vertices', 'edges', 'faces'}.
"""
from __future__ import annotations
import math


# ---- Đại số vector ----
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _norm(a):
    return math.sqrt(_dot(a, a))


def _ring(names):
    """Sinh cạnh từ chu trình đỉnh (khép kín)."""
    return [(n, names[(i + 1) % len(names)]) for i, n in enumerate(names)]


def build_polyhedron(kind: str, dims: dict) -> dict:
    a = dims.get("a", 1)
    if kind in ("cube", "box"):
        bx = a if kind == "cube" else dims.get("b", a)
        cz = a if kind == "cube" else dims.get("c", a)
        vertices = {
            "A": (0, 0, 0), "B": (a, 0, 0), "C": (a, bx, 0), "D": (0, bx, 0),
            "A'": (0, 0, cz), "B'": (a, 0, cz), "C'": (a, bx, cz), "D'": (0, bx, cz),
        }
        bottom = ["A", "B", "C", "D"]
        top = ["A'", "B'", "C'", "D'"]
        edges = _ring(bottom) + _ring(top) + [
            ("A", "A'"), ("B", "B'"), ("C", "C'"), ("D", "D'"),
        ]
        faces = [
            bottom, top,
            ["A", "B", "B'", "A'"], ["B", "C", "C'", "B'"],
            ["C", "D", "D'", "C'"], ["D", "A", "A'", "D'"],
        ]
        return {"vertices": vertices, "edges": edges, "faces": faces}

    if kind == "pyramid-quad":
        bx = dims.get("b", a)
        h = dims.get("h", a)
        base_v = {
            "A": (0, 0, 0), "B": (a, 0, 0), "C": (a, bx, 0), "D": (0, bx, 0),
        }
        # apexOver: đỉnh S ngay TRÊN 1 đỉnh đáy hoặc trên TÂM đáy (chóp đều — mặc định).
        ao = dims.get("apexOver")
        foot = base_v[ao] if (ao and ao in base_v) else (a / 2, bx / 2, 0)
        vertices = dict(base_v)
        vertices["S"] = (foot[0], foot[1], h)
        base = ["A", "B", "C", "D"]
        edges = _ring(base) + [("S", "A"), ("S", "B"), ("S", "C"), ("S", "D")]
        faces = [base, ["A", "B", "S"], ["B", "C", "S"], ["C", "D", "S"], ["D", "A", "S"]]
        return {"vertices": vertices, "edges": edges, "faces": faces}

    # prism-tri: đáy tam giác đều cạnh a, cao h.
    h = dims.get("h", a)
    cy = (math.sqrt(3) / 2) * a
    vertices = {
        "A": (0, 0, 0), "B": (a, 0, 0), "C": (a / 2, cy, 0),
        "A'": (0, 0, h), "B'": (a, 0, h), "C'": (a / 2, cy, h),
    }
    bottom = ["A", "B", "C"]
    top = ["A'", "B'", "C'"]
    edges = _ring(bottom) + _ring(top) + [("A", "A'"), ("B", "B'"), ("C", "C'")]
    faces = [
        bottom, top,
        ["A", "B", "B'", "A'"], ["B", "C", "C'", "B'"], ["C", "A", "A'", "C'"],
    ]
    return {"vertices": vertices, "edges": edges, "faces": faces}


def resolve_section_point(poly: dict, spec: dict):
    if "vertex" in spec:
        v = poly["vertices"].get(spec["vertex"])
        if not v:
            raise ValueError(f"Đỉnh không tồn tại: {spec['vertex']}")
        return v
    n1, n2 = spec["onEdge"]
    v1 = poly["vertices"].get(n1)
    v2 = poly["vertices"].get(n2)
    if not v1 or not v2:
        raise ValueError(f"Cạnh không hợp lệ: {n1}{n2}")
    return _add(v1, _scale(_sub(v2, v1), spec["t"]))


def plane_from_3(p):
    if len(p) < 3:
        return None
    n = _cross(_sub(p[1], p[0]), _sub(p[2], p[0]))
    length = _norm(n)
    if length < 1e-9:
        return None                              # 3 điểm thẳng hàng
    return {"point": p[0], "normal": _scale(n, 1 / length)}


_EPS = 1e-7


def _round_key(v):
    return ",".join(f"{(0 if abs(x) < 1e-9 else x):.6f}" for x in v)


def _order_ring(pts, normal):
    """Sắp các điểm đồng phẳng theo vòng quanh trọng tâm."""
    if len(pts) < 3:
        return pts
    c = _scale(pts[0], 0)
    for p in pts:
        c = _add(c, p)
    c = _scale(c, 1 / len(pts))
    u0 = _sub(pts[0], c)
    u_len = _norm(u0)
    u = (1, 0, 0) if u_len < _EPS else _scale(u0, 1 / u_len)
    v = _cross(normal, u)

    def angle(p):
        return math.atan2(_dot(_sub(p, c), v), _dot(_sub(p, c), u))

    return sorted(pts, key=angle)


def slice_convex_polyhedron(poly: dict, point, normal):
    def d(vv):
        return _dot(_sub(vv, point), normal)

    seen = set()
    pts = []

    def push(vv):
        k = _round_key(vv)
        if k not in seen:
            seen.add(k)
            pts.append(vv)

    for n1, n2 in poly["edges"]:
        v1 = poly["vertices"][n1]
        v2 = poly["vertices"][n2]
        d1 = d(v1)
        d2 = d(v2)
        if abs(d1) < _EPS:
            push(v1)
        if abs(d2) < _EPS:
            push(v2)
        if d1 * d2 < -_EPS * _EPS:               # cắt hẳn qua cạnh
            t = d1 / (d1 - d2)
            push(_add(v1, _scale(_sub(v2, v1), t)))
    if len(pts) < 3:
        return []
    return _order_ring(pts, normal)


def polygon_area_3d(pts):
    """Diện tích đa giác phẳng 3D (Newell): ½‖Σ vi × vi+1‖."""
    if len(pts) < 3:
        return 0.0
    n = (0.0, 0.0, 0.0)
    for i in range(len(pts)):
        n = _add(n, _cross(pts[i], pts[(i + 1) % len(pts)]))
    return _norm(n) / 2


def _fan_area(pts):
    """Diện tích bằng quạt tam giác từ đỉnh 0 — cross-check thứ tự vòng."""
    s = 0.0
    for i in range(1, len(pts) - 1):
        s += _norm(_cross(_sub(pts[i], pts[0]), _sub(pts[i + 1], pts[0]))) / 2
    return s


def build_section_cut(id, kind, dims, specs, color="#f59e0b"):
    if not specs or len(specs) < 3:
        return None
    poly = build_polyhedron(kind, dims)
    try:
        resolved = [resolve_section_point(poly, s) for s in specs[:3]]
    except ValueError:
        return None
    pl = plane_from_3(resolved)
    if not pl:
        return None
    polygon = slice_convex_polyhedron(poly, pl["point"], pl["normal"])
    if len(polygon) < 3:
        return None
    a_newell = polygon_area_3d(polygon)
    a_fan = _fan_area(polygon)
    verified = abs(a_newell - a_fan) <= 1e-9 * max(1, a_newell) and a_newell > _EPS
    latex = f"S_{{\\text{{thiết diện}}}}={a_newell:.4f}"
    area = {"value": a_newell, "latex": latex, "verified": verified,
            "estimatedError": abs(a_newell - a_fan)}
    return {
        "sectionCut": {
            "id": id, "targetKind": kind, "polygon": [list(p) for p in polygon],
            "plane": {"point": pl["point"], "normal": pl["normal"]},
            "area": area, "color": color,
        },
        "poly": poly,
    }
