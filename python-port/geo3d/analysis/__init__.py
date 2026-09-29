# -*- coding: utf-8 -*-
"""geo3d.analysis — nhánh giải tích.

  expr/quadrature/revolution/solver : biểu thức, tích phân, khối tròn xoay, giải & tối ưu
  recognize/polyfit/solids          : làm đẹp số, khớp đa thức, thể tích giao khối
  vessel/slice_volume/section_cut   : vật ghép khúc, lát cắt, cắt đa diện
  run_analysis                      : bộ ĐIỀU PHỐI giải tích (dịch runAnalysis.ts)
"""
from . import (
    expr, quadrature, revolution, solver,
    recognize, polyfit, solids,
    vessel, slice_volume, section_cut,
    run_analysis,
)

__all__ = [
    "expr", "quadrature", "revolution", "solver",
    "recognize", "polyfit", "solids",
    "vessel", "slice_volume", "section_cut",
    "run_analysis",
]
