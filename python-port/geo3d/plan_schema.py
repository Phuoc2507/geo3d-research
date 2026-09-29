# -*- coding: utf-8 -*-
"""
plan_schema.py — dịch (nhẹ) từ api/_lib/kernel/planSchema.ts + dialects danh mục op.

Bản gốc TS dùng zod để validate chặt. Ở đây KHÔNG cần zod — chỉ:
  - LIỆT KÊ đủ tên op của mỗi dialect (để đường ống hợp nhất phân luồng).
  - Vài helper phân loại op (synthetic vs oxyz, op tạo điểm oxyz).
  - Validate nhẹ dạng dict (kiểm khoá cần thiết) khi cần, ném lỗi rõ ràng.

Danh mục phải khớp:
  - ConstructionOp (execute.ts):  base, prism, pyramid, point, perp_point, foot, intersect, edge
  - OxyzOp (dialects/oxyz.ts + unifiedPlan.ts OXYZ_OPS)
  - AssertOp (planSchema.ts):     perp, parallel, coplanar, on, dist, angle
"""
from __future__ import annotations

# --- Op dựng của dialect TỔNG HỢP (synthetic), dịch từ execute.ts ---
SYNTHETIC_OPS: set[str] = {
    "base", "prism", "pyramid", "point", "perp_point", "foot", "intersect", "edge",
}

# --- Op dựng của dialect Oxyz (khớp OXYZ_OPS trong unifiedPlan.ts) ---
OXYZ_OPS: set[str] = {
    "oxyz_point", "oxyz_line", "oxyz_plane", "oxyz_sphere",
    "oxyz_midpoint", "oxyz_ratio", "oxyz_centroid", "oxyz_reflect",
    "oxyz_foot", "oxyz_reflect_across", "oxyz_orthocenter", "oxyz_circumcenter",
    "oxyz_intersect", "oxyz_circumsphere_offset",
}

# --- Op Oxyz tạo ra một ĐIỂM có tên (để phát hiện đụng tên & mirror sang symtab) ---
OXYZ_POINT_OPS: set[str] = {
    "oxyz_point", "oxyz_midpoint", "oxyz_ratio", "oxyz_centroid", "oxyz_reflect",
    "oxyz_foot", "oxyz_reflect_across", "oxyz_orthocenter", "oxyz_circumcenter",
    "oxyz_intersect",
}

# --- Kiểu định nghĩa điểm của op 'point' (PointOpSchema) ---
POINT_DEF_KINDS: set[str] = {"midpoint", "centroid", "ratio", "reflect"}

# --- Hình đáy của op 'base' (BaseOpSchema) ---
BASE_SHAPES: set[str] = {"square", "rectangle", "triangle", "reg_polygon", "rhombus"}

# --- Quan hệ assert (AssertOpSchema) ---
ASSERT_RELATIONS: set[str] = {"perp", "parallel", "coplanar", "on", "dist", "angle"}


def is_oxyz_op(kind: str) -> bool:
    """True nếu op thuộc dialect Oxyz. Khớp cả tiền tố 'oxyz_' cho an toàn."""
    return kind in OXYZ_OPS or (isinstance(kind, str) and kind.startswith("oxyz_"))


def is_synthetic_op(kind: str) -> bool:
    return kind in SYNTHETIC_OPS


def is_oxyz_point_op(kind: str) -> bool:
    return kind in OXYZ_POINT_OPS
