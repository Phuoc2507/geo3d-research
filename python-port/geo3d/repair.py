# -*- coding: utf-8 -*-
"""
repair.py — dịch từ api/_lib/kernel/repair.ts

Sửa xác định (deterministic) trên SymbolTable float cho hai quan hệ 'on' và 'perp':
  - 'on'   : chiếu điểm về đúng đường/mặt (nếu sai số đủ nhỏ so với thước đo hình).
  - 'perp' : đưa đường về đúng pháp tuyến của mặt (giữ đầu mút nằm trong mặt làm neo).
Từ chối nếu sai số lớn (nghi lỗi ngữ nghĩa, không phải nhiễu số) hoặc quan hệ chưa hỗ trợ.
"""
from __future__ import annotations
from dataclasses import dataclass
from .sym_types import (
    SymbolTable, Violation,
    add, sub, scale, dot, length,
    plane_normal, project_point_onto_plane, project_point_onto_line, distance_point_to_plane,
)
from .synthetic_resolve import resolve_entity

# Ngưỡng sai số tương đối cho 'on' (theo thước đo hình): vượt ⇒ nghi lỗi ngữ nghĩa.
REPAIR_MAX_RELATIVE_ERROR = 0.01
# Ngưỡng góc tuyệt đối cho 'perp' (1 − |cos φ|, không thứ nguyên) ≈ 2.56°.
REPAIR_MAX_PERP_ERROR = 1e-3


@dataclass
class RepairResult:
    repaired: bool
    reason: str | None = None


def _reference_scale(symtab: SymbolTable) -> float:
    positions = list(symtab.points.values())
    max_dist = 0.0
    n = len(positions)
    for i in range(n):
        for j in range(i + 1, n):
            max_dist = max(max_dist, length(sub(positions[i], positions[j])))
    return max_dist or 1.0


def attempt_deterministic_repair(violation: Violation, symtab: SymbolTable) -> RepairResult:
    if violation.kind != "assert_failed":
        return RepairResult(False, "Only assert_failed violations are eligible for deterministic repair")
    if violation.relation != "on" and violation.relation != "perp":
        return RepairResult(False, f'Deterministic repair is not implemented for relation "{violation.relation}"')
    if not violation.args or len(violation.args) != 2:
        return RepairResult(False, "Expected exactly 2 args for on/perp repair")

    if violation.actual is not None:
        if violation.relation == "on":
            scale_ = _reference_scale(symtab)
            if violation.actual / scale_ > REPAIR_MAX_RELATIVE_ERROR:
                return RepairResult(
                    False,
                    "Error exceeds the deterministic-repair threshold; likely a semantic mistake, not numeric noise",
                )
        elif violation.actual > REPAIR_MAX_PERP_ERROR:
            return RepairResult(
                False,
                "Angular error exceeds the deterministic-repair threshold; likely a semantic mistake, not numeric noise",
            )

    if violation.relation == "on":
        point_tok, entity_tok = violation.args
        point = resolve_entity(point_tok, symtab)
        entity = resolve_entity(entity_tok, symtab)
        if point.type != "point":
            return RepairResult(False, f'"{point_tok}" is not a point')
        if entity.type == "plane":
            n = plane_normal(entity.positions[0], entity.positions[1], entity.positions[2])
            symtab.points[point.name] = project_point_onto_plane(point.pos, entity.positions[0], n)
            return RepairResult(True)
        if entity.type == "line":
            symtab.points[point.name] = project_point_onto_line(point.pos, entity.pos_a, entity.pos_b)
            return RepairResult(True)
        return RepairResult(False, f'Cannot project onto entity of type "{entity.type}"')

    # relation == 'perp'
    line_tok, other_tok = violation.args
    line_entity = resolve_entity(line_tok, symtab)
    other_entity = resolve_entity(other_tok, symtab)
    if line_entity.type != "line":
        return RepairResult(
            False, f'Deterministic perp-repair requires the first arg to be a line, got "{line_entity.type}"'
        )
    if other_entity.type != "plane":
        return RepairResult(False, "Deterministic perp-repair for line-vs-line is not implemented in Phase 1")
    normal = plane_normal(other_entity.positions[0], other_entity.positions[1], other_entity.positions[2])
    plane_point = other_entity.positions[0]
    dist_a = distance_point_to_plane(line_entity.pos_a, plane_point, normal)
    dist_b = distance_point_to_plane(line_entity.pos_b, plane_point, normal)
    # Đầu mút gần mặt hơn là neo; di chuyển đầu còn lại.
    if dist_a <= dist_b:
        anchor_name, anchor_pos = line_entity.a, line_entity.pos_a
        moved_name, moved_pos = line_entity.b, line_entity.pos_b
    else:
        anchor_name, anchor_pos = line_entity.b, line_entity.pos_b
        moved_name, moved_pos = line_entity.a, line_entity.pos_a
    seg_len = length(sub(moved_pos, anchor_pos))
    side = 1 if dot(sub(moved_pos, anchor_pos), normal) >= 0 else -1
    new_moved = add(anchor_pos, scale(normal, side * seg_len))
    symtab.points[moved_name] = new_moved
    return RepairResult(True)
