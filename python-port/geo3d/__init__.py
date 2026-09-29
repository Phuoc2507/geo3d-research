# -*- coding: utf-8 -*-
"""geo3d — engine hình học ký hiệu (bản Python, dịch từ api/_lib/kernel/).

Trụ cột:
  scalar       : số chính xác (num/den)·√r + "rời trường an toàn"
  vec3/entities: vector chính xác + điểm/đường/mặt/cầu
  compute      : công thức tính (khoảng cách/góc/diện tích/thể tích) + TỰ KIỂM
  round_solids : trụ/nón/nón cụt/chóp cụt
  equation/relative/intersect : phương trình, vị trí tương đối, giao
  constructions/oxyz/oxyz_input/entity_table : dựng hình từ plan (dialect Oxyz)
  verify       : kiểm ràng buộc (⊥ ∥ đồng phẳng thuộc khoảng cách)
  run          : đường ống plan -> dựng -> kiểm -> tính -> 3 mức (giống engine gốc)
  analysis.*   : tích phân, khối tròn xoay, giải phương trình, tối ưu
"""
from . import (
    scalar, vec3, entities, compute, verify, solve,
    round_solids, equation, relative, intersect,
    constructions, oxyz, oxyz_input, entity_table, run,
)

__all__ = [
    "scalar", "vec3", "entities", "compute", "verify", "solve",
    "round_solids", "equation", "relative", "intersect",
    "constructions", "oxyz", "oxyz_input", "entity_table", "run",
]
