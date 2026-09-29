# -*- coding: utf-8 -*-
"""
demo_analysis.py — Giải vài bài GIẢI TÍCH bằng engine Python (tích phân + khối tròn xoay).
Chạy:  python demo_analysis.py
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from geo3d.analysis.quadrature import integrate
from geo3d.analysis import revolution as R


def show_int(tieu_de, f, a, b, dap_ly_thuyet=None):
    val, err = integrate(f, a, b)
    ok = "verified" if err <= 1e-6 * max(1, abs(val)) else "CHƯA hội tụ"
    print(tieu_de)
    print(f"  = {val:.6f}   (sai số ước lượng {err:.1e} → {ok})")
    if dap_ly_thuyet is not None:
        print(f"  đáp lý thuyết: {dap_ly_thuyet:.6f}")
    print()


def show_rev(tieu_de, res, dap_ly_thuyet=None):
    print(tieu_de)
    ok = "verified" if res["verified"] else "CHƯA hội tụ (không khẳng định)"
    print(f"  quanh {res['axis']} ({res['method']}), cận {tuple(round(x,4) for x in res['domain'])}")
    print(f"  V = {res['value']:.6f}   (sai số {res['estimated_error']:.1e} → {ok})")
    if dap_ly_thuyet is not None:
        print(f"  đáp lý thuyết: {dap_ly_thuyet:.6f}")
    print()


print("=" * 70)
print("TÍCH PHÂN XÁC ĐỊNH (Simpson kép + tự kiểm sai số Richardson)")
print("=" * 70)
show_int("∫₀¹ x² dx", lambda x: x*x, 0, 1, 1/3)
show_int("∫₀^π sin x dx", math.sin, 0, math.pi, 2)
show_int("∫₁^e (1/x) dx", lambda x: 1/x, 1, math.e, 1)

print("=" * 70)
print("KHỐI TRÒN XOAY")
print("=" * 70)
# y = √x quay quanh Ox trên [0,1] -> V = π/2
show_rev("BÀI A: y=√x quay quanh Ox trên [0,1]",
         R.build_revolution_ox(R.sqrtp(1, 0), (0, 1)), math.pi/2)

# nửa đường tròn r=√(1-x²) quay quanh Ox -> khối cầu V = 4π/3
show_rev("BÀI B: r=√(1-x²) quay quanh Ox trên [-1,1] (ra khối CẦU)",
         R.build_revolution_ox(R.expr("sqrt(1 - x^2)"), (-1, 1)), 4*math.pi/3)

# miền giữa outer=x, inner=x² quay quanh Oy (vỏ trụ) -> V = π/6
# CHÚ Ý: cận đưa gần đúng [0.02, 0.97], engine tự snap về [0,1]
show_rev("BÀI C: miền giữa y=x và y=x² quay quanh Oy — cận cho gần đúng [0.02, 0.97]",
         R.build_revolution_oy(R.poly([0, 1]), (0.02, 0.97), inner=R.poly([0, 0, 1])), math.pi/6)
