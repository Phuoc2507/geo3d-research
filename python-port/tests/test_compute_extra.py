# -*- coding: utf-8 -*-
"""
Kiểm thử cho các module TÍNH bổ sung: distance (line-line/line-plane/plane-plane/point-sphere),
prism volume, round_solids, equation, relative, intersect.
Các ca kỳ vọng lấy từ file test gốc trong api/_lib/kernel/compute/__tests__/.
Chạy: PYTHONIOENCODING=utf-8 python tests/test_compute_extra.py
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geo3d import scalar as S
from geo3d.scalar import Exact
from fractions import Fraction
from geo3d import vec3 as V
from geo3d.entities import Point, Line, Plane, Sphere
from geo3d import compute as C
from geo3d import equation as EQ
from geo3d import relative as R
from geo3d import intersect as I
from geo3d import round_solids as RS


# ---------- helpers dựng thực thể ----------
def _s(v):
    return S.rat(*v) if isinstance(v, tuple) else S.rat(v)


def P(x, y, z):
    return Point(V.rat_vec(x, y, z))


def LN(p, d):
    return Line(V.rat_vec(*p), V.rat_vec(*d))


def line_two(a, b):
    from geo3d.entities import line_through
    return line_through(P(*a), P(*b))


def PLC(a, b, c, d):
    return Plane(V.vec(_s(a), _s(b), _s(c)), _s(d))


def SPH(center, r2):
    return Sphere(V.rat_vec(*center), _s(r2))


def approx3(pt):
    return pt.p.approx()


def close(a, b, tol=1e-9):
    return abs(a - b) <= tol


# ================= KHOẢNG CÁCH bổ sung =================
def test_dist_line_line_cheo_nhau():
    l1 = LN((0, 0, 0), (1, 0, 0))
    l2 = LN((0, 0, 1), (0, 1, 0))
    ans = C._dist_line_line(l1, l2)
    assert ans.text == "1", ans.text
    assert ans.approximate is False


def test_dist_line_line_qua_dispatcher():
    l1 = LN((0, 0, 0), (1, 0, 0))
    l2 = LN((0, 0, 1), (0, 1, 0))
    ans = C.distance_pair(l1, l2)
    assert ans.text == "1"


def test_dist_line_plane_song_song():
    l = LN((0, 0, 1), (1, 0, 0))           # ∥ mặt z=0, cao 1
    pl = PLC(0, 0, 1, 0)
    ans = C.distance_pair(l, pl)
    assert ans.text == "1", ans.text


def test_dist_line_plane_cat_nhau():
    l = LN((0, 0, 1), (0, 0, 1))           # cắt z=0
    pl = PLC(0, 0, 1, 0)
    ans = C.distance_pair(l, pl)
    assert ans.text == "0", ans.text


def test_dist_plane_plane_song_song():
    p1 = PLC(0, 0, 1, 0)                   # z=0
    p2 = PLC(0, 0, 1, -2)                  # z=2
    ans = C.distance_pair(p1, p2)
    assert ans.text == "2", ans.text


def test_dist_plane_plane_cat_nhau():
    ans = C.distance_pair(PLC(0, 0, 1, 0), PLC(0, 1, 0, 0))
    assert ans.text == "0"


def test_dist_point_sphere():
    s = SPH((0, 0, 0), 4)                  # R=2
    ans = C.distance_pair(P(5, 0, 0), s)
    assert ans.approximate is True
    assert close(ans.approx, 3.0)


# ================= THỂ TÍCH LĂNG TRỤ =================
def test_prism_lap_phuong_canh_3():
    b = [P(0, 0, 0), P(3, 0, 0), P(3, 3, 0), P(0, 3, 0)]
    t = [P(0, 0, 3), P(3, 0, 3), P(3, 3, 3), P(0, 3, 3)]
    ans = C.prism_volume(b, t)
    assert ans.text == "27", ans.text


def test_prism_hop_2x3x4():
    b = [P(0, 0, 0), P(2, 0, 0), P(2, 3, 0), P(0, 3, 0)]
    t = [P(0, 0, 4), P(2, 0, 4), P(2, 3, 4), P(0, 3, 4)]
    ans = C.prism_volume(b, t)
    assert ans.text == "24", ans.text


def test_prism_tam_giac_vuong():
    b = [P(0, 0, 0), P(1, 0, 0), P(0, 1, 0)]
    t = [P(0, 0, 5), P(1, 0, 5), P(0, 1, 5)]
    ans = C.prism_volume(b, t)
    assert ans.text == "5/2", ans.text


def test_prism_tu_choi_khac_so_dinh():
    b = [P(0, 0, 0), P(1, 0, 0), P(0, 1, 0)]
    t = [P(0, 0, 5), P(1, 0, 5)]
    try:
        C.prism_volume(b, t)
        assert False, "phải raise"
    except ValueError:
        pass


def test_prism_tu_choi_khong_tinh_tien():
    b = [P(0, 0, 0), P(2, 0, 0), P(2, 2, 0), P(0, 2, 0)]
    t = [P(0, 0, 3), P(1, 0, 3), P(1, 1, 3), P(0, 1, 3)]  # chóp cụt
    try:
        C.prism_volume(b, t)
        assert False, "phải raise"
    except ValueError:
        pass


# ================= KHỐI TRÒN XOAY =================
def test_cone_volume():
    assert RS.cone_volume(3, 4).text == "12π"


def test_cylinder_volume():
    assert RS.cylinder_volume(3, 4).text == "36π"


def test_cone_slant():
    assert RS.cone_slant(3, 4).text == "5"


def test_cone_area_lateral():
    assert RS.cone_area(3, 4, "lateral").text == "15π"


def test_cone_area_total():
    assert RS.cone_area(3, 4, "total").text == "24π"


def test_cylinder_area_lateral():
    assert RS.cylinder_area(3, 4, "lateral").text == "24π"


def test_cylinder_area_total():
    assert RS.cylinder_area(3, 4, "total").text == "42π"


def test_cone_frustum_volume():
    assert RS.cone_frustum_volume(2, 1, 3).text == "7π"


def test_cone_frustum_slant():
    assert RS.cone_frustum_slant(2, 1, 3).text == "√10"


def test_pyramid_frustum_volume():
    assert RS.pyramid_frustum_volume(9, 1, 3).text == "13"


def test_parse_scalar_surd_va_phan_so():
    assert RS.parse_scalar("1/2").exact == Exact(Fraction(1, 2), 1)
    assert close(RS.parse_scalar("sqrt(3)/2").approx, math.sqrt(3) / 2)
    # nón bán kính √3, cao 1 → (1/3)π·3·1 = π
    assert RS.cone_volume("sqrt(3)", 1).text == "π"


# ================= PHƯƠNG TRÌNH =================
def test_plane_eq_he_so_nguyen():
    assert EQ.plane_equation_text(PLC(2, -1, 2, -3)) == "2x - y + 2z - 3 = 0"


def test_plane_eq_tu_3_diem():
    from geo3d.entities import plane_through
    pl = plane_through(P(0, 0, 0), P(1, 0, 0), P(0, 1, 0))
    assert EQ.plane_equation_text(pl) == "z = 0"


def test_plane_eq_khu_mau():
    pl = PLC((1, 2), 1, 0, 0)               # (1/2)x + y = 0
    assert EQ.plane_equation_text(pl) == "x + 2y = 0"


def test_sphere_eq():
    s = SPH((1, 2, 3), 9)
    assert EQ.sphere_equation_text(s) == "(x - 1)² + (y - 2)² + (z - 3)² = 9"


def test_line_eq_tham_so():
    l = LN((1, 0, 0), (2, 1, -1))
    txt = EQ.line_equation_text(l)
    assert "x = 1 + 2t" in txt, txt
    assert "z = 0 - 1t" in txt, txt


# ================= VỊ TRÍ TƯƠNG ĐỐI =================
def test_rel_line_line():
    assert R.compute_relative_position(LN((0, 0, 0), (1, 0, 0)), LN((0, 0, 1), (0, 1, 0))).relation == "chéo nhau"
    assert R.compute_relative_position(LN((0, 0, 0), (1, 0, 0)), LN((0, 0, 0), (0, 1, 0))).relation == "cắt nhau"
    assert R.compute_relative_position(LN((0, 0, 0), (1, 0, 0)), LN((0, 1, 0), (2, 0, 0))).relation == "song song"


def test_rel_sphere_plane():
    s = SPH((0, 0, 0), 4)
    assert R.compute_relative_position(s, PLC(0, 0, 1, 0)).relation == "cắt theo đường tròn"
    assert R.compute_relative_position(s, PLC(0, 0, 1, -2)).relation == "tiếp xúc"
    assert R.compute_relative_position(s, PLC(0, 0, 1, -3)).relation == "rời nhau"


def test_rel_point_sphere():
    s = SPH((0, 0, 0), 4)
    assert R.compute_relative_position(P(0, 0, 0), s).relation == "điểm nằm trong"
    assert R.compute_relative_position(P(2, 0, 0), s).relation == "điểm nằm trên"
    assert R.compute_relative_position(P(3, 0, 0), s).relation == "điểm nằm ngoài"


def test_rel_sphere_line():
    s = SPH((0, 0, 0), 4)
    assert R.compute_relative_position(s, LN((0, 0, 0), (1, 0, 0))).relation == "cắt nhau"
    assert R.compute_relative_position(s, LN((0, 2, 0), (1, 0, 0))).relation == "tiếp xúc"
    assert R.compute_relative_position(s, LN((0, 3, 0), (1, 0, 0))).relation == "rời nhau"


# ================= GIAO =================
def test_inter_line_plane():
    l = LN((0, 0, 5), (0, 0, 1))
    a = I.compute_intersection(l, PLC(0, 0, 1, 0))
    assert a.result == "point"
    x, y, z = approx3(a.point)
    assert close(x, 0) and close(y, 0) and close(z, 0)


def test_inter_plane_plane():
    a = I.compute_intersection(PLC(0, 0, 1, 0), PLC(0, 1, 0, 0))  # z=0 ∩ y=0 = Ox
    assert a.result == "line"
    dx, dy, dz = a.line.dir.approx()
    assert close(dy, 0) and close(dz, 0) and abs(dx) > 0
    px, py, pz = a.line.p.approx()
    assert close(px, 0) and close(py, 0) and close(pz, 0)


def test_inter_sphere_plane():
    s = SPH((0, 0, 0), 4)
    a = I.compute_intersection(s, PLC(0, 0, 1, -1))              # z=1 → đường tròn
    assert a.result == "circle"
    cx, cy, cz = approx3(a.circle["center"])
    assert close(cx, 0) and close(cy, 0) and close(cz, 1)
    assert a.circle["r2"].exact == Exact(Fraction(3), 1)
    b = I.compute_intersection(s, PLC(0, 0, 1, -2))              # z=2 → tiếp điểm
    assert b.result == "tangent-point"
    assert close(approx3(b.point)[2], 2)
    c = I.compute_intersection(s, PLC(0, 0, 1, -3))              # z=3 → rời
    assert c.result == "none"


def test_inter_line_line():
    l1 = LN((0, 0, 0), (1, 1, 0)); l2 = LN((2, 0, 0), (-1, 1, 0))
    a = I.compute_intersection(l1, l2)
    assert a.result == "point"
    x, y, z = approx3(a.point)
    assert close(x, 1) and close(y, 1) and close(z, 0)
    # 3D đồng phẳng
    b = I.compute_intersection(LN((0, 0, 0), (1, 1, 1)), LN((2, 2, 2), (1, -1, 0)))
    assert b.result == "point"
    assert all(close(v, 2) for v in approx3(b.point))
    # song song / trùng / chéo
    assert I.compute_intersection(LN((0, 0, 0), (1, 0, 0)), LN((0, 1, 0), (2, 0, 0))).result == "parallel"
    assert I.compute_intersection(LN((0, 0, 0), (1, 0, 0)), LN((3, 0, 0), (2, 0, 0))).result == "coincident"
    assert I.compute_intersection(LN((0, 0, 0), (1, 0, 0)), LN((0, 0, 1), (0, 1, 0))).result == "none"


def test_inter_line_sphere_chord():
    l = LN((-5, 0, 0), (1, 0, 0))
    s = SPH((0, 0, 0), 4)
    a = I.compute_intersection(l, s)
    assert a.result == "segment"
    assert a.chord.text() == "4", a.chord.text()
    assert close(a.chord.approx, 4.0)


def test_inter_line_sphere_tiep_va_roi():
    s = SPH((0, 0, 0), 4)
    assert I.compute_intersection(LN((0, 0, 2), (1, 0, 0)), s).result == "tangent-point"
    assert I.compute_intersection(LN((0, 0, 3), (1, 0, 0)), s).result == "none"


def test_inter_line_sphere_cau3():
    # D(20,0,9), E(0,16,12), cầu tâm O r²=400 → chord = 584√665/665
    l = line_two((20, 0, 9), (0, 16, 12))
    s = SPH((0, 0, 0), 400)
    a = I.compute_intersection(l, s)
    assert a.result == "segment"
    assert a.chord.text() == "584√665/665", a.chord.text()
    assert close(a.chord.approx, 22.6465, 1e-3)


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
