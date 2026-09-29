# -*- coding: utf-8 -*-
"""
compute.py — dịch từ api/_lib/kernel/compute/{answer,distance,angle,area,volume}.ts

Tầng TÍNH: khoảng cách · góc · diện tích · thể tích + TỰ KIỂM (self-certificate).
Ý tưởng chung của mọi công thức:
  - Giữ đại lượng ở dạng BÌNH PHƯƠNG (hữu tỉ) rồi mới √, để phép toán không rời trường.
  - Sau khi có dạng exact, so với một FLOAT TÍNH ĐỘC LẬP; lệch quá dung sai -> vứt exact.
"""
from __future__ import annotations
import math
from fractions import Fraction
from . import scalar as S
from . import vec3 as V
from .scalar import Scalar, Exact
from .vec3 import Vec3
from .entities import Point, Line, Plane, Sphere

EPS = 1e-9


# ============================ TỰ KIỂM ============================
class Answer:
    """Kết quả một phép tính: text hiển thị + có phải gần đúng không + giá trị."""
    def __init__(self, kind: str, exact: Exact | None, approx: float, text: str, approximate: bool):
        self.kind = kind
        self.exact = exact
        self.approx = approx
        self.text = text
        self.approximate = approximate

    def __repr__(self):
        tag = "~" if self.approximate else "="
        return f"{self.kind} {tag} {self.text}"


def certify_scalar(kind: str, s: Scalar, float_ref: float) -> Answer:
    """So dạng exact với float tính độc lập; khớp -> giữ exact (chính xác), lệch -> hạ gần đúng."""
    tol = 1e-6 * max(1.0, abs(float_ref))
    if s.exact is not None and abs(s.exact.approx() - float_ref) <= tol:
        return Answer(kind, s.exact, s.exact.approx(), repr(s.exact), False)
    return Answer(kind, None, float_ref, f"{float_ref:.4f}", True)


# |cos φ| chính xác của các góc đẹp φ ∈ {0,30,45,60,90}
_NICE_ABSCOS = [
    (0, Exact(Fraction(1, 1), 1)),
    (30, Exact(Fraction(1, 2), 3)),
    (45, Exact(Fraction(1, 2), 2)),
    (60, Exact(Fraction(1, 2), 1)),
    (90, Exact(Fraction(0, 1), 1)),
]


def certify_angle(metric: Scalar, float_metric: float, complement: bool) -> Answer:
    """metric = |cos φ| (exact khi trong trường). Chỉ khẳng định góc đẹp khi exact KHỚP đúng
    |cos| của góc đẹp — không snap theo float. complement=True cho góc đường–mặt (= 90 − φ)."""
    exact_m = metric.exact
    if exact_m is not None and abs(exact_m.approx() - float_metric) > 1e-6:
        exact_m = None
    phi = math.degrees(math.acos(min(1.0, abs(float_metric))))
    angle_value = (90 - phi) if complement else phi
    nice = None
    if exact_m is not None:
        for deg, m in _NICE_ABSCOS:
            if exact_m == m:
                nice = (90 - deg) if complement else deg
                break
    if nice is not None:
        return Answer("angle", None, float(nice), f"{nice}°", False)
    return Answer("angle", None, angle_value, f"≈ {angle_value:.2f}°", True)


# ---- kiểm suy biến & đồng phẳng (tiền điều kiện) ----
def first_degenerate(entities) -> str | None:
    for e in entities:
        if isinstance(e, Plane) and V.len_sq_v(e.n).approx < EPS:
            return "Mặt phẳng suy biến (pháp tuyến = 0)"
        if isinstance(e, Line) and V.len_sq_v(e.dir).approx < EPS:
            return "Đường thẳng suy biến (chỉ phương = 0)"
        if isinstance(e, Sphere) and e.r2.approx <= EPS:
            return "Mặt cầu suy biến (R² <= 0)"
    return None


def coplanarity_problem(pts: list[Vec3], what: str, tol: float = EPS) -> str | None:
    """Trả thông điệp nếu các điểm KHÔNG đồng phẳng; None nếu đồng phẳng."""
    if len(pts) <= 3:
        return None
    p0 = pts[0]
    normal = None
    for i in range(1, len(pts)):
        for j in range(i + 1, len(pts)):
            n = V.cross_v(V.sub_v(pts[i], p0), V.sub_v(pts[j], p0))
            if not S.is_zero(V.len_sq_v(n)):
                normal = n
                break
        if normal is not None:
            break
    if normal is None:
        return None  # mọi điểm thẳng hàng -> đồng phẳng tầm thường
    n_len = math.sqrt(V.len_sq_v(normal).approx)
    for p in pts:
        tp = V.dot_v(V.sub_v(p, p0), normal)
        off = 0.0 if (tp.exact is not None and tp.exact.q == 0) else abs(tp.approx) / n_len
        if off > tol:
            return f"{what}: các đỉnh không đồng phẳng"
    return None


# ============================ KHOẢNG CÁCH ============================
def _f_len(a, b):
    return math.dist(a, b)


def _dist_point_point(a: Point, b: Point) -> Answer:
    sq = V.len_sq_v(V.sub_v(a.p, b.p))
    return certify_scalar("distance", S.sqrt(sq), _f_len(a.p.approx(), b.p.approx()))


def _dist_point_line(p: Point, l: Line) -> Answer:
    # d² = |(p-a)×dir|² / |dir|²
    sq = S.div(V.len_sq_v(V.cross_v(V.sub_v(p.p, l.p), l.dir)), V.len_sq_v(l.dir))
    ap, aa, ad = p.p.approx(), l.p.approx(), l.dir.approx()
    cr = _cross(_subf(ap, aa), ad)
    fref = _lenf(cr) / _lenf(ad)
    return certify_scalar("distance", S.sqrt(sq), fref)


def _dist_point_plane(p: Point, pl: Plane) -> Answer:
    signed = S.add(V.dot_v(pl.n, p.p), pl.d)         # n·p + d
    sq = S.div(S.mul(signed, signed), V.len_sq_v(pl.n))
    ap, an = p.p.approx(), pl.n.approx()
    fref = abs(_dotf(an, ap) + pl.d.approx) / _lenf(an)
    return certify_scalar("distance", S.sqrt(sq), fref)


# float helpers độc lập
def _subf(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def _dotf(a, b): return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def _cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def _lenf(a): return math.sqrt(a[0]**2+a[1]**2+a[2]**2)


def distance(a, b) -> Answer:
    deg = first_degenerate([a, b])
    if deg:
        raise ValueError(deg)
    key = f"{a.kind}-{b.kind}"
    if key == "point-point":
        return _dist_point_point(a, b)
    if key == "point-line":
        return _dist_point_line(a, b)
    if key == "line-point":
        return _dist_point_line(b, a)
    if key == "point-plane":
        return _dist_point_plane(a, b)
    if key == "plane-point":
        return _dist_point_plane(b, a)
    raise ValueError(f"distance chưa hỗ trợ cho {key}")


# ---- các cặp khoảng cách BỔ SUNG (dịch từ dLineLine/dLinePlane/dPlanePlane/dPointSphere) ----
def _pt(p: Vec3) -> Point:
    return Point(p)


def _f_line_line(a1, d1, a2, d2):
    cr = _cross(d1, d2)
    cl = _lenf(cr)
    if cl < EPS:
        # song song → điểm–đường
        return _lenf(_cross(_subf(a2, a1), d1)) / _lenf(d1)
    return abs(_dotf(_subf(a2, a1), cr)) / cl


def _dist_line_line(l1: Line, l2: Line) -> Answer:
    cr = V.cross_v(l1.dir, l2.dir)
    if S.is_zero(V.len_sq_v(cr)):
        return _dist_point_line(_pt(l1.p), l2)     # song song → điểm–đường
    r = V.sub_v(l2.p, l1.p)
    triple = V.dot_v(r, cr)
    dist_sq = S.div(S.mul(triple, triple), V.len_sq_v(cr))
    fref = _f_line_line(l1.p.approx(), l1.dir.approx(), l2.p.approx(), l2.dir.approx())
    return certify_scalar("distance", S.sqrt(dist_sq), fref)


def _dist_line_plane(l: Line, pl: Plane) -> Answer:
    if not S.is_zero(V.dot_v(l.dir, pl.n)):
        return certify_scalar("distance", S.rat(0), 0.0)   # cắt nhau
    return _dist_point_plane(_pt(l.p), pl)                  # song song → điểm–mặt


def _dist_plane_plane(p1: Plane, p2: Plane) -> Answer:
    if not S.is_zero(V.len_sq_v(V.cross_v(p1.n, p2.n))):
        return certify_scalar("distance", S.rat(0), 0.0)   # cắt nhau
    # chân đường vuông góc từ O xuống p1: n1·(neg(d1)/|n1|²)
    point_on_p1 = V.scale_v(p1.n, S.div(S.neg(p1.d), V.len_sq_v(p1.n)))
    return _dist_point_plane(_pt(point_on_p1), p2)


def _dist_point_sphere(p: Point, s: Sphere) -> Answer:
    pc = math.sqrt(V.len_sq_v(V.sub_v(p.p, s.center)).approx)
    R = math.sqrt(s.r2.approx)
    d = abs(pc - R)
    return certify_scalar("distance", S.num(d), d)          # rời trường ⇒ gần đúng


def distance_pair(a, b) -> Answer:
    """Dispatcher ĐẦY ĐỦ (dịch computeDistance): gồm cả các cặp bổ sung."""
    deg = first_degenerate([a, b])
    if deg:
        raise ValueError(deg)
    key = f"{a.kind}-{b.kind}"
    if key == "point-point":
        return _dist_point_point(a, b)
    if key == "point-line":
        return _dist_point_line(a, b)
    if key == "line-point":
        return _dist_point_line(b, a)
    if key == "point-plane":
        return _dist_point_plane(a, b)
    if key == "plane-point":
        return _dist_point_plane(b, a)
    if key == "line-line":
        return _dist_line_line(a, b)
    if key == "line-plane":
        return _dist_line_plane(a, b)
    if key == "plane-line":
        return _dist_line_plane(b, a)
    if key == "plane-plane":
        return _dist_plane_plane(a, b)
    if key == "point-sphere":
        return _dist_point_sphere(a, b)
    if key == "sphere-point":
        return _dist_point_sphere(b, a)
    raise ValueError(f"distance chưa hỗ trợ cho {key}")


# ============================ GÓC ============================
def _abs_cos(u: Vec3, v: Vec3) -> Scalar:
    d = V.dot_v(u, v)
    return S.sqrt(S.div(S.mul(d, d), S.mul(V.len_sq_v(u), V.len_sq_v(v))))


def _f_abs_cos(u, v):
    return abs(_dotf(u, v)) / (_lenf(u) * _lenf(v))


def angle(a, b) -> Answer:
    deg = first_degenerate([a, b])
    if deg:
        raise ValueError(deg)
    key = f"{a.kind}-{b.kind}"
    if key == "line-line":
        return certify_angle(_abs_cos(a.dir, b.dir), _f_abs_cos(a.dir.approx(), b.dir.approx()), False)
    if key == "plane-plane":
        return certify_angle(_abs_cos(a.n, b.n), _f_abs_cos(a.n.approx(), b.n.approx()), False)
    if key == "line-plane":
        return certify_angle(_abs_cos(a.dir, b.n), _f_abs_cos(a.dir.approx(), b.n.approx()), True)
    if key == "plane-line":
        return certify_angle(_abs_cos(b.dir, a.n), _f_abs_cos(b.dir.approx(), a.n.approx()), True)
    raise ValueError(f"angle chưa hỗ trợ cho {key}")


# ============================ DIỆN TÍCH ============================
def triangle_area(a: Point, b: Point, c: Point) -> Answer:
    cr = V.cross_v(V.sub_v(b.p, a.p), V.sub_v(c.p, a.p))
    s = S.sqrt(S.mul(S.rat(1, 4), V.len_sq_v(cr)))     # S² = (1/4)|u×v|²
    fa, fb, fc = a.p.approx(), b.p.approx(), c.p.approx()
    fref = _lenf(_cross(_subf(fb, fa), _subf(fc, fa))) / 2
    return certify_scalar("area", s, fref)


def polygon_area(pts: list[Point]) -> Answer:
    if len(pts) < 3:
        raise ValueError("đa giác cần >= 3 đỉnh")
    cp = coplanarity_problem([p.p for p in pts], "đa giác")
    if cp:
        raise ValueError(cp)
    n = len(pts)
    total = V.rat_vec(0, 0, 0)
    for i in range(n):
        total = V.add_v(total, V.cross_v(pts[i].p, pts[(i + 1) % n].p))
    s = S.sqrt(S.mul(S.rat(1, 4), V.len_sq_v(total)))
    # float ref
    sx = sy = sz = 0.0
    fp = [p.p.approx() for p in pts]
    for i in range(n):
        cr = _cross(fp[i], fp[(i + 1) % n])
        sx += cr[0]; sy += cr[1]; sz += cr[2]
    fref = _lenf((sx, sy, sz)) / 2
    return certify_scalar("area", s, fref)


# ============================ THỂ TÍCH ============================
def _triple(a: Vec3, b: Vec3, c: Vec3, d: Vec3) -> Scalar:
    """×6 thể tích có dấu tứ diện = (b-a)·[(c-a)×(d-a)]."""
    return V.dot_v(V.sub_v(b, a), V.cross_v(V.sub_v(c, a), V.sub_v(d, a)))


def _abs_s(s: Scalar) -> Scalar:
    """|s|, lấy dấu từ exact khi có (tránh float làm tròn ngược dấu)."""
    if s.exact is not None:
        return S.neg(s) if s.exact.q < 0 else s
    return S.neg(s) if s.approx < 0 else s


def _f_triple(a, b, c, d):
    u, v, w = _subf(b, a), _subf(c, a), _subf(d, a)
    return _dotf(u, _cross(v, w))


def tetra_volume(a: Point, b: Point, c: Point, d: Point) -> Answer:
    s = S.div(_abs_s(_triple(a.p, b.p, c.p, d.p)), S.rat(6))
    fref = abs(_f_triple(a.p.approx(), b.p.approx(), c.p.approx(), d.p.approx())) / 6
    return certify_scalar("volume", s, fref)


def pyramid_volume(base: list[Point], apex: Point) -> Answer:
    if len(base) < 3:
        raise ValueError("đáy chóp cần >= 3 đỉnh")
    cp = coplanarity_problem([p.p for p in base], "đáy chóp")
    if cp:
        raise ValueError(cp)                          # đáy không phẳng -> từ chối, KHÔNG bịa
    total = S.rat(0)
    for i in range(1, len(base) - 1):
        total = S.add(total, _triple(base[0].p, base[i].p, base[i + 1].p, apex.p))
    s = S.div(_abs_s(total), S.rat(6))
    # float ref
    fb = [p.p.approx() for p in base]
    fa = apex.p.approx()
    acc = 0.0
    for i in range(1, len(base) - 1):
        acc += _f_triple(fb[0], fb[i], fb[i + 1], fa)
    return certify_scalar("volume", s, abs(acc) / 6)


def sphere_volume(sph: Sphere) -> Answer:
    """V = (4/3)πR³ = (4/3)·r2·√r2·π. Trả dạng π chính xác khi √r2 biểu diễn được."""
    coeff = S.mul(S.rat(4, 3), S.mul(sph.r2, S.sqrt(sph.r2)))
    R = math.sqrt(sph.r2.approx)
    fref = (4 / 3) * math.pi * R ** 3
    return _pi_answer("volume", coeff, fref)


def sphere_area(sph: Sphere) -> Answer:
    """S = 4πR² = 4·r2·π."""
    coeff = S.mul(S.rat(4), sph.r2)
    fref = 4 * math.pi * sph.r2.approx
    return _pi_answer("area", coeff, fref)


def _pi_answer(kind: str, coeff: Scalar, float_ref: float) -> Answer:
    val = coeff.approx * math.pi
    tol = 1e-6 * max(1.0, abs(float_ref))
    if coeff.exact is not None and abs(val - float_ref) <= tol:
        d = repr(coeff.exact)
        if d == "1":
            text = "π"
        elif d == "-1":
            text = "-π"
        elif "/" in d:
            i = d.index("/")
            text = d[:i] + "π" + d[i:]
        else:
            text = d + "π"
        return Answer(kind, None, val, text, False)
    return Answer(kind, None, float_ref, f"{float_ref:.4f}", True)


def volume_ratio(a: Scalar, b: Scalar) -> Answer:
    if S.is_zero(b):
        raise ValueError("tỉ số thể tích: mẫu = 0")
    return certify_scalar("ratio", S.div(a, b), a.approx / b.approx)


# ---- LĂNG TRỤ (dịch prismVolumeScalar/translationMismatch/computePrismVolume) ----
def _prism_volume_scalar(base: list[Point], top: list[Point]) -> Scalar:
    """×6 tổng thể tích có dấu: mỗi tam-giác-đáy (b0,bi,bi+1) + nắp tương ứng = lăng trụ tam
    giác = 3 tứ diện. Chia đáy thành quạt tam giác rồi cộng lại."""
    total = S.rat(0)
    for i in range(1, len(base) - 1):
        b0, bi, bj = base[0].p, base[i].p, base[i + 1].p
        t0, ti, tj = top[0].p, top[i].p, top[i + 1].p
        total = S.add(total, _triple(b0, bi, bj, t0))
        total = S.add(total, _triple(bi, bj, t0, ti))
        total = S.add(total, _triple(bj, t0, ti, tj))
    return S.div(_abs_s(total), S.rat(6))


def _f_prism(base, top):
    acc = 0.0
    for i in range(1, len(base) - 1):
        acc += _f_triple(base[0], base[i], base[i + 1], top[0])
        acc += _f_triple(base[i], base[i + 1], top[0], top[i])
        acc += _f_triple(base[i + 1], top[0], top[i], top[i + 1])
    return abs(acc) / 6


def _translation_mismatch(base: list[Point], top: list[Point]) -> str | None:
    """Nắp phải là đáy TỊNH TIẾN: mọi top[i]−base[i] bằng nhau. Nếu không → không phải lăng trụ."""
    v0 = V.sub_v(top[0].p, base[0].p)
    for i in range(1, len(base)):
        d = V.sub_v(V.sub_v(top[i].p, base[i].p), v0)
        if not (S.is_zero(d.x) and S.is_zero(d.y) and S.is_zero(d.z)):
            return "prism: nắp không phải bản tịnh tiến của đáy (không phải lăng trụ)"
    return None


def prism_volume(base: list[Point], top: list[Point]) -> Answer:
    if len(base) < 3:
        raise ValueError("đáy lăng trụ cần >= 3 đỉnh")
    if len(top) != len(base):
        raise ValueError("lăng trụ: đáy và nắp phải cùng số đỉnh")
    cp_b = coplanarity_problem([p.p for p in base], "đáy lăng trụ")
    if cp_b:
        raise ValueError(cp_b)
    cp_t = coplanarity_problem([p.p for p in top], "nắp lăng trụ")
    if cp_t:
        raise ValueError(cp_t)
    mism = _translation_mismatch(base, top)
    if mism:
        raise ValueError(mism)
    fref = _f_prism([p.p.approx() for p in base], [p.p.approx() for p in top])
    return certify_scalar("volume", _prism_volume_scalar(base, top), fref)
