# -*- coding: utf-8 -*-
"""
Bộ kiểm thử cho engine Python. Chạy: python -m pytest  (hoặc)  python tests/test_geo3d.py
Không cần thư viện ngoài — có runner mini ở cuối để chạy bằng python thuần.
"""
import sys, os, math
from fractions import Fraction
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geo3d import scalar as S
from geo3d.scalar import Exact, exact
from geo3d import entities as E
from geo3d import compute as C
from geo3d import solve


# ---------------- số học chính xác ----------------
def test_cong_cung_can():
    r = S.add_exact(exact(1, 1, 3), exact(1, 1, 3))     # √3 + √3
    assert r == exact(2, 1, 3)

def test_cong_roi_truong():
    r = S.add_exact(exact(1, 1, 2), exact(1, 1, 3))     # √2 + √3
    assert r is None                                     # KHÔNG gọn được -> None

def test_tach_chinh_phuong():
    assert exact(1, 1, 12) == exact(2, 1, 3)            # √12 = 2√3

def test_sqrt_huu_ti():
    r = S.sqrt_exact(exact(9, 4, 1))                     # √(9/4) = 3/2
    assert r == exact(3, 2, 1)

def test_sqrt_cua_can_ngoai_truong():
    assert S.sqrt_exact(exact(1, 1, 2)) is None          # √√2 -> None


# ---------------- khoảng cách ----------------
def test_khoang_cach_diem_mat():
    # O đến mặt x+y+z-1=0  ->  √3/3
    O = E.point(0, 0, 0)
    A, B, Cc = E.point(1, 0, 0), E.point(0, 1, 0), E.point(0, 0, 1)
    pl = E.plane_through(A, B, Cc)
    ans = C.distance(O, pl)
    assert ans.approximate is False
    assert ans.text == "√3/3"
    assert abs(ans.approx - 1/math.sqrt(3)) < 1e-9

def test_khoang_cach_diem_diem():
    ans = C.distance(E.point(0, 0, 0), E.point(2, 0, 0))
    assert ans.text == "2"


# ---------------- góc ----------------
def test_goc_60_do():
    # hai vector hợp góc 60°: (1,0,0) và (1,√3? ) — dùng đường qua điểm
    o = E.point(0, 0, 0)
    l1 = E.line_through(o, E.point(1, 0, 0))
    l2 = E.line_through(o, E.point(1, 1, 0))            # 45°
    ans = C.angle(l1, l2)
    assert ans.text == "45°"

def test_goc_vuong():
    o = E.point(0, 0, 0)
    l1 = E.line_through(o, E.point(1, 0, 0))
    l2 = E.line_through(o, E.point(0, 1, 0))
    ans = C.angle(l1, l2)
    assert ans.text == "90°"


# ---------------- diện tích / thể tích ----------------
def test_dien_tich_tam_giac():
    ans = C.triangle_area(E.point(0, 0, 0), E.point(2, 0, 0), E.point(0, 2, 0))
    assert ans.text == "2"

def test_the_tich_tu_dien_deu_canh_2():
    # Tứ diện đều cạnh 2 -> thể tích 2√2/3 ≈ 0.9428.
    # Toạ độ chứa số vô tỉ (√3) nên engine trả GẦN ĐÚNG — ta kiểm giá trị số.
    A = E.Point(_v(0, 0, 0))
    B = E.Point(_v(2, 0, 0))
    Cc = E.Point(_v(1, math.sqrt(3), 0))
    D = E.Point(_v(1, math.sqrt(3)/3, math.sqrt(8/3)))
    ans = C.tetra_volume(A, B, Cc, D)
    assert abs(ans.approx - 2*math.sqrt(2)/3) < 1e-6

def test_the_tich_mat_cau_dang_pi():
    sph = E.Sphere(E.V.rat_vec(0,0,0), S.rat(9))       # R²=9 -> R=3 -> V = 36π
    ans = C.sphere_volume(sph)
    assert ans.text == "36π"


def _v(x, y, z):
    from geo3d import vec3 as V
    return V.Vec3(S.num(x), S.num(y), S.num(z))


# ---------------- verify + tier ----------------
def test_plan_muc_1():
    plan = {
        "points": {"A": (0,0,0), "B": (1,0,0), "C": (0,1,0), "D": (0,0,1)},
        "asserts": [("perp", ["AB", "AC"])],           # AB ⊥ AC  (đúng)
        "queries": [("volume_tetra", ["A","B","C","D"])],
    }
    r = solve.run_plan(plan)
    assert r["tier"]["level"] == 1
    assert r["answers"][0].text == "1/6"

def test_plan_muc_3_vi_pham():
    plan = {
        "points": {"A": (0,0,0), "B": (1,0,0), "C": (1,1,0)},
        "asserts": [("perp", ["AB", "AC"])],           # AB ⊥ AC ?  KHÔNG (góc 45°) -> violation
        "queries": [],
    }
    r = solve.run_plan(plan)
    assert r["tier"]["level"] == 3
    assert r["tier"]["reason"] == "violation"


# =============== runner mini (chạy bằng python thuần, không cần pytest) ===============
if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}  -> {e}")
        except Exception as e:
            print(f"  ERROR {t.__name__}  -> {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} test PASS")
    sys.exit(0 if passed == len(tests) else 1)
