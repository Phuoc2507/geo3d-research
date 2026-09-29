# -*- coding: utf-8 -*-
"""
Kiểm thử tầng DỰNG HÌNH (parser + phép dựng + dialect oxyz).
Ca kỳ vọng lấy từ các test gốc:
  api/_lib/kernel/dialects/__tests__/oxyzInput.test.ts
  api/_lib/kernel/dialects/__tests__/oxyz.test.ts
  api/_lib/kernel/dialects/__tests__/oxyz-circumsphere.test.ts
  api/_lib/kernel/__tests__/constructions.test.ts
Chạy: PYTHONIOENCODING=utf-8 python tests/test_build.py
"""
import sys, os, math
from fractions import Fraction
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geo3d.scalar import Exact
from geo3d import oxyz_input as OI
from geo3d import entities as E
from geo3d import constructions as K
from geo3d import vec3 as V
from geo3d import scalar as S
from geo3d.oxyz import execute_oxyz_plan


def ex(n, d=1, rad=1):
    """makeExact(n, d, rad) tương đương phía TS."""
    return Exact(Fraction(n, d), rad)


def approx_vec(v):
    return v.approx()


def close(a, b, tol=1e-9):
    return abs(a - b) <= tol


def vclose(v, xyz, tol=1e-9):
    ax = approx_vec(v)
    return all(close(ax[i], xyz[i], tol) for i in range(3))


# ==================== parseRational (oxyzInput.test.ts) ====================
def test_parse_so_nguyen():
    assert OI.parse_rational(5) == ex(5, 1, 1)
    assert OI.parse_rational(-3) == ex(-3, 1, 1)

def test_parse_thap_phan_number():
    assert OI.parse_rational(1.5) == ex(3, 2, 1)
    assert OI.parse_rational(-0.25) == ex(-1, 4, 1)

def test_parse_phan_so_chuoi():
    assert OI.parse_rational("3/2") == ex(3, 2, 1)
    assert OI.parse_rational("-7/4") == ex(-7, 4, 1)

def test_parse_thap_phan_va_nguyen_chuoi():
    assert OI.parse_rational("1.5") == ex(3, 2, 1)
    assert OI.parse_rational("12") == ex(12, 1, 1)

def test_parse_nem_dang_mu():
    try:
        OI.parse_rational(1e-7)
        raise AssertionError("phải ném với số dạng mũ")
    except AssertionError:
        raise
    except Exception:
        pass  # đúng: đã ném

def test_parse_can():
    assert OI.parse_rational("sqrt(3)") == ex(1, 1, 3)
    assert OI.parse_rational("√3") == ex(1, 1, 3)
    assert OI.parse_rational("2*sqrt(3)") == ex(2, 1, 3)
    assert OI.parse_rational("sqrt(3)/2") == ex(1, 2, 3)
    assert OI.parse_rational("2*sqrt(3)/3") == ex(2, 3, 3)
    assert OI.parse_rational("-sqrt(5)/2") == ex(-1, 2, 5)
    assert OI.parse_rational("2√3") == ex(2, 1, 3)

def test_parse_vec3s_hon_hop():
    v = OI.parse_vec3s([1, "3/2", -2])
    assert vclose(v, (1, 1.5, -2))
    assert v.y.exact == ex(3, 2, 1)


# ==================== executeOxyzPlan (oxyz.test.ts) ====================
def test_diem_mat_3diem_midpoint():
    et = execute_oxyz_plan([
        {"op": "oxyz_point", "name": "A", "at": [0, 0, 0]},
        {"op": "oxyz_point", "name": "B", "at": [1, 0, 0]},
        {"op": "oxyz_point", "name": "C", "at": [0, 1, 0]},
        {"op": "oxyz_plane", "name": "P", "by": {"form": "three_points", "a": "A", "b": "B", "c": "C"}},
        {"op": "oxyz_midpoint", "name": "M", "a": "A", "b": "B"},
    ])
    P = et.planes["P"]
    assert vclose(P.n, (0, 0, 1))
    assert P.d.exact == ex(0, 1, 1)
    M = et.points["M"]
    assert M.p.x.exact == ex(1, 2, 1)
    assert vclose(M.p, (0.5, 0, 0))

def test_mat_cau_tu_phuong_trinh():
    et = execute_oxyz_plan([
        {"op": "oxyz_sphere", "name": "S", "by": {"form": "equation", "a": -2, "b": -4, "c": -6, "d": 5}},
    ])
    Sp = et.spheres["S"]
    assert vclose(Sp.center, (1, 2, 3))
    assert Sp.r2.exact == ex(9, 1, 1)

def test_duong_qua_2diem_chi_phuong():
    et = execute_oxyz_plan([
        {"op": "oxyz_point", "name": "A", "at": [1, 0, 0]},
        {"op": "oxyz_point", "name": "B", "at": [1, 2, 2]},
        {"op": "oxyz_line", "name": "d", "by": {"form": "two_points", "a": "A", "b": "B"}},
    ])
    d = et.lines["d"]
    assert vclose(d.dir, (0, 2, 2))

def test_nem_khi_diem_chua_dinh_nghia():
    try:
        execute_oxyz_plan([{"op": "oxyz_midpoint", "name": "M", "a": "A", "b": "B"}])
        raise AssertionError("phải ném khi tham chiếu điểm chưa định nghĩa")
    except AssertionError:
        raise
    except Exception:
        pass

def test_foot_hinh_chieu():
    et = execute_oxyz_plan([
        {"op": "oxyz_point", "name": "S", "at": [0, 0, 3]},
        {"op": "oxyz_plane", "name": "P", "by": {"form": "coeffs", "a": 0, "b": 0, "c": 1, "d": 0}},
        {"op": "oxyz_foot", "name": "H", "from": "S", "onto": "plane", "target": "P"},
    ])
    assert vclose(et.points["H"].p, (0, 0, 0))
    assert "H" in et.derived_points

def test_orthocenter_tam_giac_vuong():
    et = execute_oxyz_plan([
        {"op": "oxyz_point", "name": "A", "at": [0, 0, 0]},
        {"op": "oxyz_point", "name": "B", "at": [1, 0, 0]},
        {"op": "oxyz_point", "name": "C", "at": [0, 1, 0]},
        {"op": "oxyz_orthocenter", "name": "H", "of": ["A", "B", "C"]},
    ])
    assert vclose(et.points["H"].p, (0, 0, 0))

def test_reflect_across_mat():
    et = execute_oxyz_plan([
        {"op": "oxyz_point", "name": "A", "at": [1, 1, 1]},
        {"op": "oxyz_plane", "name": "P", "by": {"form": "coeffs", "a": 0, "b": 0, "c": 1, "d": 0}},
        {"op": "oxyz_reflect_across", "name": "A2", "point": "A", "across": "plane", "target": "P"},
    ])
    assert vclose(et.points["A2"].p, (1, 1, -1))

def test_intersect_duong_mat():
    et = execute_oxyz_plan([
        {"op": "oxyz_line", "name": "d", "by": {"form": "point_dir", "base": [0, 0, 5], "dir": [0, 0, 1]}},
        {"op": "oxyz_plane", "name": "P", "by": {"form": "coeffs", "a": 0, "b": 0, "c": 1, "d": 0}},
        {"op": "oxyz_intersect", "name": "I", "a": "d", "b": "P"},
    ])
    assert vclose(et.points["I"].p, (0, 0, 0))


# ==================== circumsphere_offset (oxyz-circumsphere.test.ts) ====================
def test_circumsphere_offset_t0():
    # A(0,0,10),B(4,0,6),C(0,4,6); t=0 ⇒ tâm=(4/3,4/3,22/3), R=4√6/3.
    et = execute_oxyz_plan([
        {"op": "oxyz_point", "name": "A", "at": [0, 0, 10]},
        {"op": "oxyz_point", "name": "B", "at": [4, 0, 6]},
        {"op": "oxyz_point", "name": "C", "at": [0, 4, 6]},
        {"op": "oxyz_circumsphere_offset", "name": "S", "of": ["A", "B", "C"], "t": 0},
    ])
    Sp = et.spheres["S"]
    assert vclose(Sp.center, (4/3, 4/3, 22/3), tol=1e-9)
    radius = math.sqrt(Sp.r2.approx)
    assert close(radius, 4 * math.sqrt(6) / 3, tol=1e-6)
    top_z = Sp.center.z.approx + radius
    assert close(top_z, 22/3 + 4 * math.sqrt(6) / 3, tol=1e-6)


# ==================== constructions (constructions.test.ts) ====================
def test_foot_on_plane_construction():
    pl = E.plane_from_coeffs(S.rat(0), S.rat(0), S.rat(1), S.rat(0))
    assert vclose(K.foot_on_plane(V.rat_vec(1, 1, 1), pl), (1, 1, 0))

def test_foot_on_line_construction():
    l = E.line_from_point_dir(V.rat_vec(0, 0, 0), V.rat_vec(1, 0, 0))
    assert vclose(K.foot_on_line(V.rat_vec(0, 2, 0), l), (0, 0, 0))

def test_reflect_plane_construction():
    pl = E.plane_from_coeffs(S.rat(0), S.rat(0), S.rat(1), S.rat(0))
    assert vclose(K.reflect_across_plane(V.rat_vec(1, 1, 1), pl), (1, 1, -1))

def test_reflect_line_construction():
    l = E.line_from_point_dir(V.rat_vec(0, 0, 0), V.rat_vec(1, 0, 0))
    assert vclose(K.reflect_across_line(V.rat_vec(0, 2, 0), l), (0, -2, 0))

def test_orthocenter_construction():
    H = K.orthocenter(V.rat_vec(0, 0, 0), V.rat_vec(1, 0, 0), V.rat_vec(0, 1, 0))
    assert vclose(H, (0, 0, 0))

def test_circumcenter_construction():
    O = K.circumcenter(V.rat_vec(0, 0, 0), V.rat_vec(2, 0, 0), V.rat_vec(0, 2, 0))
    assert O.x.exact == ex(1, 1, 1)
    assert vclose(O, (1, 1, 0))


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
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}  -> {e}")
        except Exception as e:
            print(f"  ERROR {t.__name__}  -> {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} test PASS")
    sys.exit(0 if passed == len(tests) else 1)
