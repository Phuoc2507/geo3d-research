# -*- coding: utf-8 -*-
"""Test bộ giải: bậc hai (chính xác), giải f(x)=target (số), tối ưu 1 biến.
Chạy: python tests/test_solver.py  (hoặc python -m pytest)"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geo3d import scalar as S
from geo3d.analysis.solver import solve_quadratic, solve_all_param, solve_param, optimize_param


# ---------------- giải bậc hai (chính xác) ----------------
def test_bac_hai_hai_nghiem_nguyen():
    # x² − 5x + 6 = 0 -> 2, 3
    rs = solve_quadratic(S.rat(1), S.rat(-5), S.rat(6))
    texts = sorted(r.text() for r in rs)
    assert texts == ["2", "3"]

def test_bac_hai_nghiem_can():
    # x² − 7 = 0 -> ±√7  (giữ DẠNG CĂN chính xác)
    rs = solve_quadratic(S.rat(1), S.rat(0), S.rat(-7))
    texts = sorted(r.text() for r in rs)
    assert texts == ["-√7", "√7"]
    assert all(r.exact is not None for r in rs)          # exact, không phải số thập phân

def test_bac_hai_nghiem_kep():
    # x² − 2x + 1 = 0 -> 1 (kép)
    rs = solve_quadratic(S.rat(1), S.rat(-2), S.rat(1))
    assert len(rs) == 1 and rs[0].text() == "1"

def test_bac_hai_vo_nghiem():
    # x² + 1 = 0 -> [] (Δ < 0)
    assert solve_quadratic(S.rat(1), S.rat(0), S.rat(1)) == []

def test_tuyen_tinh():
    # 2x − 4 = 0 -> 2
    rs = solve_quadratic(S.rat(0), S.rat(2), S.rat(-4))
    assert len(rs) == 1 and rs[0].text() == "2"


# ---------------- giải f(x)=target bằng số ----------------
def test_giai_so_can_hai():
    r = solve_param(lambda x: x * x, 2, 0, 2)            # x² = 2 -> √2
    assert abs(r["x"] - math.sqrt(2)) < 1e-9
    assert r["residual"] < 1e-9

def test_giai_so_nhieu_nghiem():
    roots = solve_all_param(math.sin, 0, -0.5, 4)        # sin x = 0 trên [-0.5,4] -> 0 và π
    assert any(abs(x) < 1e-6 for x in roots)
    assert any(abs(x - math.pi) < 1e-6 for x in roots)


# ---------------- tối ưu 1 biến ----------------
def test_toi_uu_max():
    # max của −(x−1)² + 3 trên [0,3] -> x=1, value=3
    r = optimize_param(lambda x: -(x - 1)**2 + 3, 0, 3, "max")
    assert abs(r["x"] - 1) < 1e-6 and abs(r["value"] - 3) < 1e-6

def test_toi_uu_min():
    # min của x² trên [-2,2] -> x=0
    r = optimize_param(lambda x: x * x, -2, 2, "min")
    assert abs(r["x"]) < 1e-6 and abs(r["value"]) < 1e-9

def test_toi_uu_bai_thuc_te():
    # Hộp không nắp từ tấm 12×12 cắt góc x: V(x)=x(12−2x)², x∈[0,6]. Max tại x=2, V=128.
    V = lambda x: x * (12 - 2*x)**2
    r = optimize_param(V, 0, 6, "max")
    assert abs(r["x"] - 2) < 1e-6 and abs(r["value"] - 128) < 1e-6


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
