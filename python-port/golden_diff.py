# -*- coding: utf-8 -*-
"""
golden_diff.py — DIFF phần HÌNH HỌC: đáp engine PYTHON vs engine TS trên các ca GOLDEN thật.
Đọc golden_ts.json (do golden_run.mjs xuất), tái dựng điểm + truy vấn, tính bằng Python, so text.
Chạy: python golden_diff.py   (sau khi node python-port/golden_run.mjs)
"""
import sys, os, re, json
from fractions import Fraction
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from geo3d import scalar as S
from geo3d.scalar import Exact
from geo3d import vec3 as V
from geo3d import entities as E
from geo3d import compute as C

# ---- parse một toạ độ (int / "p/q" / "[k*]sqrt(n)[/d]") -> Scalar ----
_COORD = re.compile(r"^\s*(-?)(\d+)?\*?sqrt\((\d+)\)(?:/(\d+))?\s*$")
def parse_coord(v):
    if isinstance(v, (int,)):
        return S.rat(v)
    if isinstance(v, float):
        return S.rat(int(v)) if v == int(v) else S.num(v)
    s = str(v).strip()
    m = _COORD.match(s)
    if m:
        sign, coeff, n, d = m.groups()
        c = Fraction(int(coeff) if coeff else 1, int(d) if d else 1)
        if sign == "-":
            c = -c
        return S.from_exact(Exact(c, int(n)))            # (c)·√n
    if "/" in s:                                          # p/q
        p, q = s.split("/")
        return S.rat(int(p), int(q))
    return S.rat(int(s))                                  # số nguyên dạng chuỗi


def build_points(pts_json):
    out = {}
    for name, at in pts_json.items():
        sx, sy, sz = (parse_coord(c) for c in at)
        out[name] = E.Point(V.Vec3(sx, sy, sz))
    return out


# ---- resolver token -> entity (khớp dài nhất, như resolveE.ts) ----
def resolve(token, points):
    if token in points:
        return points[token]
    names = sorted(points.keys(), key=len, reverse=True)
    toks, rest = [], token
    while rest:
        m = next((n for n in names if rest.startswith(n)), None)
        if not m:
            raise ValueError(f"không phân giải '{token}'")
        toks.append(m); rest = rest[len(m):]
    if len(toks) == 1:
        return points[toks[0]]
    if len(toks) == 2:
        return E.line_through(points[toks[0]], points[toks[1]])
    return E.plane_through(points[toks[0]], points[toks[1]], points[toks[2]])


def solid_volume_scalar(spec, points):
    pts = [points[n] for n in spec["points"]]
    if spec["solid"] == "tetrahedron":
        a = C.tetra_volume(*pts)
    else:
        a = C.pyramid_volume(pts, points[spec["apex"]])
    return S.Scalar(a.approx, a.exact)


def run_query(q, points):
    k = q["kind"]
    if k == "distance":
        return C.distance(resolve(q["a"], points), resolve(q["b"], points)).text
    if k == "angle":
        return C.angle(resolve(q["a"], points), resolve(q["b"], points)).text
    if k == "area":
        pts = [points[n] for n in q["points"]]
        return (C.triangle_area(*pts) if q["shape"] == "triangle" else C.polygon_area(pts)).text
    if k == "volume":
        pts = [points[n] for n in q["points"]]
        if q["solid"] == "tetrahedron":
            return C.tetra_volume(*pts).text
        return C.pyramid_volume(pts, points[q["apex"]]).text
    if k == "volume_ratio":
        return C.volume_ratio(solid_volume_scalar(q["a"], points), solid_volume_scalar(q["b"], points)).text
    raise ValueError(f"query không hỗ trợ: {k}")


# ---- chạy diff ----
here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "golden_ts.json"), encoding="utf-8-sig") as f:
    cases = json.load(f)

print(f"{'CA GOLDEN':26s} {'TRUY VẤN':16s} {'TS':12s} {'PYTHON':12s} KẾT QUẢ")
print("-" * 86)
match = miss = err = 0
for c in cases:
    pts = build_points(c["points"])
    for i, q in enumerate(c["queries"]):
        ts = c["ts_answers"][i] if i < len(c["ts_answers"]) else "(thiếu)"
        try:
            py = run_query(q, pts)
        except Exception as e:
            py = f"[{type(e).__name__}]"; err += 1
            print(f"{c['id'][:26]:26s} {q['kind'][:16]:16s} {ts:12s} {py:12s} ⚠️ lỗi")
            continue
        ok = ts == py
        if ok: match += 1
        else: miss += 1
        print(f"{c['id'][:26]:26s} {q['kind'][:16]:16s} {ts:12s} {py:12s} {'✅' if ok else '❌'}")
print("-" * 86)
print(f"KHỚP {match} | LỆCH {miss} | LỖI {err}  (trên {sum(len(c['queries']) for c in cases)} truy vấn)")
