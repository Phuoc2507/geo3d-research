# -*- coding: utf-8 -*-
"""
synthetic_resolve.py — dịch từ api/_lib/kernel/resolve.ts

Bản FLOAT của resolver cho dialect tổng hợp: token → ResolvedEntity trên SymbolTable.
Ưu tiên: điểm có tên → mặt đã đăng ký (named_planes) → ghép tên điểm
("AB" = đường, "ABC…" = mặt qua các điểm theo thứ tự token). Ném nếu không giải được.
"""
from __future__ import annotations
import re
from .sym_types import SymbolTable, Vec3, RPoint, RLine, RPlane

_PAREN_RE = re.compile(r"^\((.+)\)$")


def _tokenize_point_names(raw: str, known: set[str]) -> list[str] | None:
    """Tách token thành các tên điểm (khớp dài nhất trước)."""
    names = sorted(known, key=len, reverse=True)
    tokens: list[str] = []
    rest = raw
    while len(rest) > 0:
        match = next((n for n in names if rest.startswith(n)), None)
        if match is None:
            return None
        tokens.append(match)
        rest = rest[len(match):]
    return tokens


def _require_point(symtab: SymbolTable, name: str) -> Vec3:
    p = symtab.points.get(name)
    if p is None:
        raise ValueError(f'Unknown point "{name}"')
    return p


def resolve_entity(token: str, symtab: SymbolTable):
    paren = _PAREN_RE.match(token)
    inner = paren.group(1) if paren else token

    if inner in symtab.points:
        return RPoint(name=inner, pos=_require_point(symtab, inner))

    if inner in symtab.named_planes:
        names = symtab.named_planes[inner]
        return RPlane(points=names, positions=[_require_point(symtab, n) for n in names])

    known = set(symtab.points.keys())
    tokens = _tokenize_point_names(inner, known)
    if tokens is None:
        raise ValueError(
            f'Cannot resolve entity "{token}": it is not a known point, a registered '
            f"named plane, or a compound of known point names"
        )
    if len(tokens) == 1:
        return RPoint(name=tokens[0], pos=_require_point(symtab, tokens[0]))
    if len(tokens) == 2:
        return RLine(
            a=tokens[0], b=tokens[1],
            pos_a=_require_point(symtab, tokens[0]),
            pos_b=_require_point(symtab, tokens[1]),
        )
    return RPlane(points=tokens, positions=[_require_point(symtab, n) for n in tokens])
