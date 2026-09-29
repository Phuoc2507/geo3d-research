# -*- coding: utf-8 -*-
"""
Bộ kiểm thử cho 3 module giải tích phụ trợ: recognize / polyfit / solids.
Ca kỳ vọng LẤY TỪ file test gốc (.ts): recognize.test.ts, polyfit.test.ts,
analyze-polyfit-degrees.test.ts, solids.test.ts.
Chạy: PYTHONIOENCODING=utf-8 python tests/test_analysis_helpers.py
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geo3d.analysis.recognize import recognize_constant
from geo3d.analysis.polyfit import fit_poly, eval_poly, deriv_poly, extremum_of_poly
from geo3d.analysis.solids import disk_at, lens_area, intersection_volume


# --------- tiện ích assert (mô phỏng toBeCloseTo/toBe của vitest) ---------
def close(a, b, digits):
    # vitest toBeCloseTo: |a-b| < 0.5 * 10^(-digits)
    assert abs(a - b) < 0.5 * 10 ** (-digits), f"{a} !≈ {b} (digits={digits})"


def eq(a, b):
    assert a == b, f"{a!r} != {b!r}"


# =============================== recognize ===============================
def test_recognize_huu_ti():
    eq(recognize_constant(1.5).text, "3/2")
    eq(recognize_constant(4).text, "4")

def test_recognize_mot_can():
    eq(recognize_constant(math.sqrt(7)).text, "√7")
    eq(recognize_constant(math.sqrt(3) / 2).text, "√3/2")
    eq(recognize_constant(2 * math.sqrt(3)).text, "2√3")

def test_recognize_nhi_thuc_10_tru_2can7():
    r = recognize_constant(10 - 2 * math.sqrt(7))
    assert r is not None
    eq(r.text, "10 - 2√7")
    close(r.value, 4.7085, 4)

def test_recognize_khong_nhan_dang_null():
    assert recognize_constant(math.pi * 1.234567) is None

def test_recognize_can_b_lon():
    r = recognize_constant(165 * math.sqrt(385) / 196)
    assert r is not None
    eq(r.text, "165√385/196")

def test_recognize_dang_pi():
    eq(recognize_constant(math.pi / 3).text, "π/3")
    eq(recognize_constant(2 * math.pi).text, "2π")
    eq(recognize_constant(1 + math.pi).text, "1 + π")

def test_recognize_khong_khop_gia():
    assert recognize_constant(0.7234981123) is None
    assert recognize_constant(math.e * 1.37219) is None

def test_recognize_giu_dang_cu():
    eq(recognize_constant(math.sqrt(7)).text, "√7")
    eq(recognize_constant(10 - 2 * math.sqrt(7)).text, "10 - 2√7")
    eq(recognize_constant(1.5).text, "3/2")


# =============================== polyfit ===============================
def test_fit_ghim_he_so_dau():
    c = fit_poly(2, [(0, 0), (8, 0)], -1 / 3)   # [c0,c1,c2]
    close(c[0], 0, 10)
    close(c[1], 8 / 3, 10)
    close(c[2], -1 / 3, 10)

def test_fit_du_diem():
    c = fit_poly(2, [(0, 10), (20, 14), (40, 10)])
    close(c[0], 10, 10)
    close(c[1], 0.4, 10)
    close(c[2], -0.01, 10)

def test_eval_deriv():
    c = [0, 8 / 3, -1 / 3]
    close(eval_poly(c, 6), 4, 10)
    close(eval_poly(c, 0), 0, 10)
    d = deriv_poly(c)
    close(eval_poly(d, 6), -4 / 3, 10)

def test_extremum_dinh_parabol():
    r = extremum_of_poly([0, 8 / 3, -1 / 3], 0, 8)
    assert r is not None
    close(r["x"], 4, 6)
    close(r["y"], 16 / 3, 6)

def test_fit_sai_so_diem_nem():
    try:
        fit_poly(2, [(0, 0)], -1 / 3)
        raise AssertionError("mong đợi ném lỗi")
    except ValueError:
        pass

def test_fit_rang_buoc_dao_ham():
    c = fit_poly(3, [(0, 0), (2, 4), (3, 0)], None, [(2, 0)])
    close(c[0], 0, 9)
    close(c[1], 0, 9)
    close(c[2], 3, 9)
    close(c[3], -1, 9)

def test_fit_slope_voi_leading_ghim():
    c = fit_poly(2, [(0, 0)], -1 / 3, [(4, 0)])
    close(c[0], 0, 9)
    close(c[1], 8 / 3, 9)
    close(c[2], -1 / 3, 9)

def test_fit_tong_rang_buoc_sai_nem():
    try:
        fit_poly(3, [(0, 0), (2, 4)], None, [(2, 0)])   # 3 ràng buộc cho 4 ẩn
        raise AssertionError("mong đợi ném lỗi")
    except ValueError:
        pass

def test_extremum_loai_diem_uon():
    assert extremum_of_poly([0, 0, 0, 1], -1, 1) is None

def test_extremum_chon_max_min():
    c = [0, -3, 0, 1]   # -3x + x³
    mx = extremum_of_poly(c, -2, 2, "max")
    mn = extremum_of_poly(c, -2, 2, "min")
    close(mx["x"], -1, 6); close(mx["y"], 2, 6)
    close(mn["x"], 1, 6); close(mn["y"], -2, 6)

def test_extremum_parabola_khong_doi():
    r = extremum_of_poly([0, 8 / 3, -1 / 3], 0, 8)
    close(r["x"], 4, 6)
    close(r["y"], 16 / 3, 6)

# --- analyze-polyfit-degrees.test.ts ---
def test_fit_bac_1():
    c = fit_poly(1, [(0, 1), (2, 5)])
    close(eval_poly(c, 0), 1, 9)
    close(eval_poly(c, 2), 5, 9)
    close(eval_poly(c, 1), 3, 9)

def test_fit_bac_4():
    c = fit_poly(4, [(0, 0), (1, 1), (2, 16), (3, 81), (4, 256)])
    close(eval_poly(c, 2), 16, 6)
    close(eval_poly(c, 4), 256, 4)
    close(eval_poly(c, 2.5), 39.0625, 3)


# =============================== solids ===============================
CYL = {"kind": "cylinder", "cx": 0, "cy": 0, "radius": 2, "from": 0, "to": 4}
CONE = {"kind": "cone", "cx": 2, "cy": 0, "baseRadius": 2, "baseZ": 0, "apexZ": 4}

def test_disk_at():
    close(disk_at(CYL, 2)["r"], 2, 12)
    eq(disk_at(CYL, 9)["r"], 0)                 # ngoài khối
    close(disk_at(CONE, 0)["r"], 2, 12)         # đáy
    close(disk_at(CONE, 4)["r"], 0, 12)         # đỉnh
    close(disk_at(CONE, 2)["r"], 1, 12)         # giữa
    close(disk_at(CONE, 2)["cx"], 2, 12)

def test_lens_area():
    close(lens_area(2, 2, 0), math.pi * 4, 10)          # trùng tâm, bằng nhau
    eq(lens_area(2, 2, 4), 0)                            # tiếp xúc ngoài
    eq(lens_area(2, 2, 5), 0)                            # rời
    close(lens_area(2, 1, 0.5), math.pi, 10)            # tròn nhỏ nằm trọn
    close(lens_area(1, 1, 1), 2 * math.pi / 3 - math.sqrt(3) / 2, 10)

def test_intersection_tru_long_tru():
    inner = {"kind": "cylinder", "cx": 0, "cy": 0, "radius": 1, "from": 0, "to": 4}
    close(intersection_volume(CYL, inner)["value"], 4 * math.pi, 6)

def test_intersection_cau_8():
    v = intersection_volume(CYL, CONE)["value"]
    close(v, 64 * math.pi / 9 - 512 / 9 + 24 * math.sqrt(3), 5)
    close(v, 7.0205, 4)

def test_intersection_khong_chong_do_cao():
    above = {"kind": "cylinder", "cx": 0, "cy": 0, "radius": 2, "from": 10, "to": 12}
    eq(intersection_volume(CYL, above)["value"], 0)


# =============== runner mini (chạy bằng python thuần) ===============
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
