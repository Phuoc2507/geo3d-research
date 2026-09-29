# -*- coding: utf-8 -*-
"""Test khối tròn xoay GHÉP/LÁT + cắt thiết diện + tối ưu/giải NHIỀU biến.
Ca kỳ vọng lấy từ các test gốc TS (vessel/sliceVolume/sectionCut/solve-multi/…).
Chạy: PYTHONIOENCODING=utf-8 python tests/test_analysis_solids.py"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geo3d.analysis.vessel import (
    vessel_segment_volume, validate_vessel_segments, vessel_volume,
    build_vessel_solid, sample_vessel_profile, vessel_segments_from_measures,
)
from geo3d.analysis.slice_volume import build_slice_stack, slice_stack_volume, section_k
from geo3d.analysis.section_cut import (
    build_polyhedron, resolve_section_point, plane_from_3,
    slice_convex_polyhedron, polygon_area_3d, build_section_cut,
)
from geo3d.analysis.solver import optimize_multi, nelder_mead

PI = math.pi


def close(a, b, tol=1e-9):
    assert abs(a - b) <= tol, f"{a} != {b} (tol {tol})"


# ============================ VESSEL — công thức đóng ============================
def test_vessel_tru():
    close(vessel_segment_volume({"type": "cylinder", "x0": 0, "x1": 5, "r": 2}), 20 * PI)

def test_vessel_non_cut():
    close(vessel_segment_volume({"type": "frustum", "x0": 0, "x1": 4, "r0": 3, "r1": 1}), 52 * PI / 3)

def test_vessel_non_dac():
    close(vessel_segment_volume({"type": "frustum", "x0": 0, "x1": 6, "r0": 3, "r1": 0}), 18 * PI)

def test_vessel_cau_day_du():
    # R=3, tâm c=3, [0,6] = cả đường kính ⇒ 4/3·π·27 = 36π.
    close(vessel_segment_volume({"type": "sphereZone", "x0": 0, "x1": 6, "R": 3, "c": 3}), 36 * PI)

def test_vessel_nua_cau():
    # R=3, tâm c=0, [0,3] = nửa cầu ⇒ 2/3·π·27 = 18π.
    close(vessel_segment_volume({"type": "sphereZone", "x0": 0, "x1": 3, "R": 3, "c": 0}), 18 * PI)


# ============================ VESSEL — validate ============================
def test_vessel_rong_khong_hop_le():
    assert validate_vessel_segments([])["ok"] is False

def test_vessel_ho_khong_hop_le():
    segs = [{"type": "cylinder", "x0": 0, "x1": 4, "r": 2},
            {"type": "cylinder", "x0": 5, "x1": 8, "r": 2}]
    assert validate_vessel_segments(segs)["ok"] is False

def test_vessel_cau_vuot_khong_hop_le():
    assert validate_vessel_segments([{"type": "sphereZone", "x0": 0, "x1": 5, "R": 2, "c": 0}])["ok"] is False

def test_vessel_binh_ruou_hop_le():
    segs = [{"type": "frustum", "x0": 0, "x1": 4, "r0": 5, "r1": 3},
            {"type": "sphereZone", "x0": 4, "x1": 8, "R": 5, "c": 8}]
    assert validate_vessel_segments(segs)["ok"] is True


# ============================ VESSEL — đối chiếu đóng vs số ============================
def test_vessel_volume_khop_verified():
    segs = [{"type": "frustum", "x0": 0, "x1": 4, "r0": 5, "r1": 3},
            {"type": "sphereZone", "x0": 4, "x1": 8, "R": 5, "c": 8}]
    v = vessel_volume(segs)
    assert v["verified"] is True
    expected = vessel_segment_volume(segs[0]) + vessel_segment_volume(segs[1])
    close(v["value"], expected, 1e-6)
    assert v["gap"] < 1e-4 * max(1, expected)

def test_vessel_ho_khong_verified():
    segs = [{"type": "cylinder", "x0": 0, "x1": 4, "r": 2},
            {"type": "cylinder", "x0": 5, "x1": 8, "r": 2}]
    assert vessel_volume(segs)["verified"] is False


# ============================ VESSEL — build solid ============================
def test_build_vessel_solid():
    segs = [{"type": "frustum", "x0": 0, "x1": 4, "r0": 5, "r1": 3},
            {"type": "sphereZone", "x0": 4, "x1": 8, "R": 5, "c": 8}]
    solid = build_vessel_solid("v1", segs)
    assert solid["volume"]["verified"] is True
    assert solid["domain"] == [0, 8]
    assert solid["axis"] == "Oy"
    assert solid["method"] == "disk"

def test_vessel_samples_vai_phang():
    segs = [{"type": "frustum", "x0": 0, "x1": 4, "r0": 5, "r1": 3},
            {"type": "sphereZone", "x0": 4, "x1": 8, "R": 5, "c": 8}]
    s = build_vessel_solid("v1", segs)["samples"]
    assert len(s) > 20                                    # khúc cầu ~24 điểm
    for i in range(1, len(s)):
        assert s[i]["x"] >= s[i - 1]["x"] - 1e-9
    for p in s:
        assert p["r"] >= 0


# ============================ VESSEL — số đo → khúc ============================
def test_measures_suy_cau():
    # rB=rT=8, h=12 ⇒ R=10, tâm c=6.
    segs = vessel_segments_from_measures([{"type": "sphereZone", "rBottom": 8, "rTop": 8, "h": 12}])
    assert len(segs) == 1
    s = segs[0]
    close(s["R"], 10, 1e-9)
    close(s["c"], 6, 1e-9)
    close(math.sqrt(s["R"]**2 - (s["x0"] - s["c"])**2), 8, 1e-9)
    close(math.sqrt(s["R"]**2 - (s["x1"] - s["c"])**2), 8, 1e-9)

def test_measures_khong_hop_le():
    assert vessel_segments_from_measures([{"type": "cylinder", "r": 2, "h": 0}]) == []
    assert vessel_segments_from_measures([{"type": "weird", "h": 2}]) == []

def test_measures_binh_ruou_5146pi():
    # nón cụt rB=15,rT=8,h=30 (=4090π) + đới cầu rB=rT=8,h=12 (=1056π) = 5146π.
    segs = vessel_segments_from_measures([
        {"type": "frustum", "rBottom": 15, "rTop": 8, "h": 30},
        {"type": "sphereZone", "rBottom": 8, "rTop": 8, "h": 12},
    ])
    solid = build_vessel_solid("bottle", segs)
    assert solid["volume"]["verified"] is True
    close(solid["volume"]["value"], 5146 * PI, 1e-4 * 5146 * PI)

def test_sample_vessel_vai_phang_2tru():
    segs = [{"type": "cylinder", "x0": 0, "x1": 3, "r": 2},
            {"type": "cylinder", "x0": 3, "x1": 6, "r": 4}]
    s = sample_vessel_profile(segs)
    at_x3 = sorted(p["r"] for p in s if abs(p["x"] - 3) < 1e-9)
    assert at_x3 == [2, 4]


# ============================ SLICE VOLUME ============================
SQRT_X = {"kind": "sqrt", "a": 1, "b": 0}   # side=√x ⇒ side²=x, ∫_0^4 x dx = 8

def test_slice_vuong():
    close(slice_stack_volume("square", SQRT_X, [0, 4])[0], 8, 1e-6)

def test_slice_nua_tron():
    close(slice_stack_volume("semicircle", SQRT_X, [0, 4])[0], PI, 1e-6)

def test_slice_tam_giac_deu():
    close(slice_stack_volume("equilateral", SQRT_X, [0, 4])[0], 2 * math.sqrt(3), 1e-6)

def test_slice_chu_nhat():
    close(slice_stack_volume("rect", SQRT_X, [0, 4], None, 2)[0], 16, 1e-6)

def test_slice_builder():
    s = build_slice_stack("s1", "square", SQRT_X, [0, 4])
    assert s["volume"]["verified"] is True
    close(s["volume"]["value"], 8, 1e-6)
    assert s["section"] == "square"
    assert len(s["samples"]) > 0
    close(s["samples"][-1]["t"], 4, 1e-9)
    close(s["samples"][-1]["side"], 2, 1e-6)

def test_slice_inner_outer():
    v = slice_stack_volume("square", {"kind": "const", "c": 2}, [0, 3], {"kind": "const", "c": 0})
    close(v[0], 12, 1e-6)

def test_slice_va_can_vo_ti():
    # đáy 2−x² cắt Ox tại ±√2; từ gợi ý ±1.41 ⇒ snap ±√2; V=64√2/15.
    s = build_slice_stack("s1", "square", {"kind": "poly", "coeffs": [2, 0, -1]}, [-1.41, 1.41])
    close(s["domain"][0], -math.sqrt(2), 1e-6)
    close(s["domain"][1], math.sqrt(2), 1e-6)
    close(s["volume"]["value"], 64 * math.sqrt(2) / 15, 1e-4)
    assert s["volume"]["verified"] is True

def test_slice_can_cho_san_giu():
    s = build_slice_stack("s1", "square", SQRT_X, [0, 4])
    close(s["domain"][0], 0, 1e-9)
    close(s["domain"][1], 4, 1e-9)
    close(s["volume"]["value"], 8, 1e-6)


# ============================ SECTION CUT ============================
def test_cube_dinh_canh_mat():
    p = build_polyhedron("cube", {"a": 2})
    assert len(p["vertices"]) == 8
    assert len(p["edges"]) == 12
    assert len(p["faces"]) == 6
    assert p["vertices"]["C"] == (2, 2, 0)
    assert p["vertices"]["A'"] == (0, 0, 2)

def test_pyramid_quad():
    p = build_polyhedron("pyramid-quad", {"a": 2, "b": 2, "h": 3})
    assert p["vertices"]["S"] == (1, 1, 3)
    assert len(p["vertices"]) == 5
    assert len(p["edges"]) == 8

def test_pyramid_apex_over():
    p = build_polyhedron("pyramid-quad", {"a": 2, "b": 2, "h": 3, "apexOver": "A"})
    assert p["vertices"]["S"] == (0, 0, 3)

def test_prism_tri():
    p = build_polyhedron("prism-tri", {"a": 2, "h": 4})
    assert len(p["vertices"]) == 6
    assert len(p["edges"]) == 9

def test_resolve_point():
    p = build_polyhedron("cube", {"a": 2})
    assert resolve_section_point(p, {"vertex": "B"}) == (2, 0, 0)
    assert resolve_section_point(p, {"onEdge": ["A", "B"], "t": 0.5}) == (1, 0, 0)

def test_plane_thang_hang_none():
    assert plane_from_3([(0, 0, 0), (1, 0, 0), (2, 0, 0)]) is None

def test_plane_phap_tuyen():
    pl = plane_from_3([(0, 0, 0), (1, 0, 0), (0, 1, 0)])
    assert abs(pl["normal"][0]) < 1e-9
    assert abs(pl["normal"][1]) < 1e-9
    assert abs(pl["normal"][2]) > 0

def test_cat_lap_phuong_tam_giac_deu():
    p = build_polyhedron("cube", {"a": 1})
    pt = [(0.5, 0, 0), (0, 0.5, 0), (0, 0, 0.5)]
    pl = plane_from_3(pt)
    polygon = slice_convex_polyhedron(p, pl["point"], pl["normal"])
    assert len(polygon) == 3
    close(polygon_area_3d(polygon), math.sqrt(3) / 8, 1e-6)

def test_cat_hop_song_song_day():
    p = build_polyhedron("box", {"a": 2, "b": 3, "c": 4})
    polygon = slice_convex_polyhedron(p, (0, 0, 1), (0, 0, 1))
    assert len(polygon) == 4
    close(polygon_area_3d(polygon), 6, 1e-6)

def test_cat_khong_giao():
    p = build_polyhedron("cube", {"a": 1})
    assert len(slice_convex_polyhedron(p, (0, 0, 5), (0, 0, 1))) == 0

def test_build_section_cut():
    r = build_section_cut("sec1", "cube", {"a": 1},
                          [{"onEdge": ["A", "B"], "t": 0.5},
                           {"onEdge": ["A", "D"], "t": 0.5},
                           {"onEdge": ["A", "A'"], "t": 0.5}])
    assert r["sectionCut"]["area"]["verified"] is True
    close(r["sectionCut"]["area"]["value"], math.sqrt(3) / 8, 1e-6)
    assert len(r["sectionCut"]["polygon"]) == 3

def test_build_section_cut_thang_hang_none():
    r = build_section_cut("sec1", "cube", {"a": 1},
                          [{"vertex": "A"}, {"onEdge": ["A", "B"], "t": 0.5}, {"vertex": "B"}])
    assert r is None


# ============================ OPTIMIZE MULTI / NELDER–MEAD ============================
def _v_sub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def _v_cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def _v_dot(a, b): return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def _v_norm(a): return math.sqrt(_v_dot(a, a))

def _line_dist(p1, u, p2, v):
    w = _v_sub(p1, p2)
    cr = _v_cross(u, v)
    n = _v_norm(cr)
    if n < 1e-12:                                    # song song
        return _v_norm(_v_cross(w, u)) / _v_norm(u)
    return abs(_v_dot(w, cr)) / n


def test_optimize_multi_2rang_buoc_dist():
    # P=(a,b,0); dist(O,P)=5 & dist(A,P)=5, O(0,0,0) A(6,0,0), b≥0 ⇒ a=3,b=4 ⇒ a+b=7.
    O, A = (0, 0, 0), (6, 0, 0)
    def resid(xs):
        a, b = xs
        P = (a, b, 0)
        dO = _v_norm(_v_sub(P, O))
        dA = _v_norm(_v_sub(P, A))
        return (dO - 5)**2 + (dA - 5)**2
    best = optimize_multi(resid, [0, 0], [6, 6], "min")
    assert best["value"] < 1e-6                       # residual ≈ 0 ⇒ có nghiệm
    close(best["xs"][0] + best["xs"][1], 7, 1e-2)

def test_optimize_multi_vo_nghiem():
    # dist(O,P)=100 trên hộp [0,1]² ⇒ không đạt được ⇒ residual lớn (bên gọi sẽ ok=false).
    O = (0, 0, 0)
    def resid(xs):
        P = (xs[0], xs[1], 0)
        return (_v_norm(_v_sub(P, O)) - 100)**2
    best = optimize_multi(resid, [0, 0], [1, 1], "min")
    assert best["value"] > 1.0                        # còn residual lớn

def test_optimize_multi_duong_cat_2_duong():
    # Δ qua A(0,2,1) chỉ phương (a,b,1) cắt D1,D2 ⇒ a+b=4 (dùng Nelder–Mead đánh bóng).
    A = (0, 2, 1)
    D1p, D1d = (3, 3, 2), (1, 2, 2)
    D2p, D2d = (-3, 1, 0), (2, 1, -1)
    def resid(xs):
        a, b = xs
        u = (a, b, 1)
        return _line_dist(A, u, D1p, D1d)**2 + _line_dist(A, u, D2p, D2d)**2
    best = optimize_multi(resid, [-10, -10], [10, 10], "min")
    assert best["value"] < 1e-4
    close(best["xs"][0] + best["xs"][1], 4, 1e-2)

def test_optimize_multi_muc_tieu_khoang_cach():
    # min sqrt((a-b)²+(f(a)-(b+1)/(b-2))²), f(a)=3a²−a³, a∈[2,3], b∈[2.05,7] ⇒ ≈0.7485.
    f = lambda a: 3*a*a - a*a*a
    def obj(xs):
        a, b = xs
        return math.sqrt((a - b)**2 + (f(a) - (b + 1)/(b - 2))**2)
    best = optimize_multi(obj, [2, 2.05], [3, 7], "min")
    close(best["value"], 0.7485, 3e-3)

def test_nelder_mead_rosenbrock():
    # NM tối thiểu Rosenbrock (thung lũng cong) từ (−1.2,1) ⇒ về (1,1), value≈0.
    rb = lambda xs: (1 - xs[0])**2 + 100*(xs[1] - xs[0]**2)**2
    xs = nelder_mead(rb, [-1.2, 1.0], [-5, -5], [5, 5], [0.5, 0.5], max_iter=4000)
    assert rb(xs) < 1e-3
    close(xs[0], 1, 5e-2)
    close(xs[1], 1, 5e-2)


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
