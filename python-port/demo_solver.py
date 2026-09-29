# -*- coding: utf-8 -*-
"""demo_solver.py — Giải phương trình + tối ưu 1 biến. Chạy: python demo_solver.py"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from geo3d import scalar as S
from geo3d.analysis.solver import solve_quadratic, solve_param, optimize_param

print("=" * 70)
print("GIẢI PHƯƠNG TRÌNH BẬC HAI (giữ dạng căn chính xác)")
print("=" * 70)
for a, b, c, ten in [(1, -5, 6, "x² − 5x + 6 = 0"),
                     (1, 0, -7, "x² − 7 = 0"),
                     (2, -4, -3, "2x² − 4x − 3 = 0"),
                     (1, 0, 1, "x² + 1 = 0")]:
    rs = solve_quadratic(S.rat(a), S.rat(b), S.rat(c))
    if not rs:
        print(f"  {ten:20s} -> vô nghiệm thực")
    else:
        print(f"  {ten:20s} -> " + ", ".join(f"x = {r.text()}" for r in rs))
print()

print("=" * 70)
print("GIẢI f(x) = target BẰNG SỐ (quét đổi dấu + chia đôi)")
print("=" * 70)
r = solve_param(lambda x: x * x, 2, 0, 2)
print(f"  x² = 2 trên [0,2]  -> x ≈ {r['x']:.6f}  (√2, residual {r['residual']:.1e})")
r = solve_param(lambda x: math.exp(x) - 3*x, 0, 0, 1)   # e^x = 3x
print(f"  e^x = 3x trên [0,1] -> x ≈ {r['x']:.6f}")
print()

print("=" * 70)
print("TỐI ƯU 1 BIẾN (lưới thô + golden-section, không cần đạo hàm)")
print("=" * 70)
# Bài kinh điển: tấm bìa 12×12, cắt 4 góc vuông cạnh x, gấp thành hộp không nắp.
# Thể tích V(x) = x(12−2x)², x∈[0,6]. Tìm x để V lớn nhất.
V = lambda x: x * (12 - 2*x)**2
r = optimize_param(V, 0, 6, "max")
print("  Hộp không nắp từ tấm 12×12, cắt góc x:  V(x) = x(12−2x)²")
print(f"  -> x = {r['x']:.6f} cm,  V_max = {r['value']:.6f} cm³   (đáp: x=2, V=128)")
print()
# Chu vi cố định: hình chữ nhật chu vi 20, diện tích lớn nhất?
A = lambda x: x * (10 - x)                               # x + y = 10, A = x·y
r = optimize_param(A, 0, 10, "max")
print("  Hình chữ nhật chu vi 20, diện tích lớn nhất:  A(x) = x(10−x)")
print(f"  -> x = {r['x']:.6f},  A_max = {r['value']:.6f}   (đáp: hình vuông cạnh 5, A=25)")
