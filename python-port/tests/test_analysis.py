# -*- coding: utf-8 -*-
"""Test nhánh giải tích: parser biểu thức, tích phân, khối tròn xoay.
Chạy: python tests/test_analysis.py  (hoặc python -m pytest)"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geo3d.analysis.expr import eval_expr
from geo3d.analysis.quadrature import integrate, refine_bounds
from geo3d.analysis import revolution as R


# ---------------- parser biểu thức ----------------
def test_expr_uu_tien():
    assert abs(eval_expr("1 + 2*3") - 7) < 1e-12
    assert abs(eval_expr("2^3^2") - 512) < 1e-9      # ^ phải-kết-hợp: 2^(3^2)=2^9
    assert abs(eval_expr("-2^2") - (-4)) < 1e-12     # đơn nguyên lỏng hơn ^: -(2^2)

def test_expr_ham_va_bien():
    assert abs(eval_expr("sqrt(x)", {"x": 9}) - 3) < 1e-12
    assert abs(eval_expr("sin(pi/2)") - 1) < 1e-12

def test_expr_bien_chua_gan():
    try:
        eval_expr("x + 1")
        assert False, "phải ném lỗi biến chưa gán"
    except ValueError:
        pass


# ---------------- tích phân ----------------
def test_tich_phan_x_binh():
    val, err = integrate(lambda x: x * x, 0, 1)     # ∫₀¹ x² = 1/3
    assert abs(val - 1/3) < 1e-8
    assert err < 1e-6                                # tự kiểm: sai số ước lượng nhỏ

def test_tich_phan_sin():
    val, _ = integrate(math.sin, 0, math.pi)        # ∫₀^π sin = 2
    assert abs(val - 2) < 1e-8


# ---------------- tinh chỉnh cận (snap về giao điểm) ----------------
def test_refine_bounds_snap_giao_diem():
    # y=x và y=x² giao tại 0 và 1; đưa cận gần đúng [0.02, 0.97] -> snap về ~[0,1]
    h = lambda x: x - x * x
    a, b = refine_bounds(h, (0.02, 0.97))
    assert abs(a - 0) < 1e-6 and abs(b - 1) < 1e-6

def test_refine_bounds_giu_can_cho_san():
    # cận x=2 KHÔNG phải nghiệm gần đó -> giữ nguyên (fail-safe)
    h = lambda x: x - x * x
    a, b = refine_bounds(h, (2.0, 3.0))
    assert a == 2.0 and b == 3.0


# ---------------- khối tròn xoay ----------------
def test_ox_dia_r_bang_x():
    # y=x quay quanh Ox trên [0,1]: V = π∫x² = π/3
    res = R.build_revolution_ox(R.poly([0, 1]), (0, 1))
    assert res["verified"] is True
    assert abs(res["value"] - math.pi/3) < 1e-6

def test_ox_sqrt():
    # y=√x quay quanh Ox trên [0,1]: V = π∫x = π/2
    res = R.build_revolution_ox(R.sqrtp(1, 0), (0, 1))
    assert abs(res["value"] - math.pi/2) < 1e-6

def test_ox_mat_cau():
    # nửa cung tròn r=√(1-x²) quay quanh Ox trên [-1,1] -> khối cầu V = 4π/3
    res = R.build_revolution_ox(R.expr("sqrt(1 - x^2)"), (-1, 1))
    assert abs(res["value"] - 4*math.pi/3) < 1e-6

def test_ox_vanh_khan():
    # miền giữa outer=√x và inner=x quay quanh Ox trên [0,1]
    # V = π∫(x - x²) dx = π(1/2 - 1/3) = π/6
    res = R.build_revolution_ox(R.sqrtp(1, 0), (0, 1), inner=R.poly([0, 1]))
    assert abs(res["value"] - math.pi/6) < 1e-6

def test_oy_vo_tru():
    # miền giữa outer=x và inner=x² quay quanh Oy trên [0,1]
    # V = 2π∫x(x - x²) dx = 2π(1/3 - 1/4) = π/6
    res = R.build_revolution_oy(R.poly([0, 1]), (0, 1), inner=R.poly([0, 0, 1]))
    assert abs(res["value"] - math.pi/6) < 1e-6


# =============== runner mini ===============
if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t(); print(f"  PASS  {t.__name__}"); passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}  -> {e}")
        except Exception as e:
            print(f"  ERROR {t.__name__}  -> {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} test PASS")
    sys.exit(0 if passed == len(tests) else 1)
