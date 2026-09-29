# -*- coding: utf-8 -*-
"""
parity_check.py — Đối chiếu kết quả engine PYTHON với giá trị mà bộ TEST GỐC (TypeScript)
khẳng định, TRÊN CÙNG bộ toạ độ đầu vào. (Máy này không có Node nên không diff engine đang chạy;
đây là đối chiếu với 'expected' do chính tác giả engine gốc viết trong *.test.ts.)
Chạy: python parity_check.py
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from geo3d import scalar as S
from geo3d import entities as E
from geo3d import compute as C
from geo3d.compute import _triple, _abs_s
from geo3d.analysis.solver import solve_quadratic
from geo3d.analysis.quadrature import integrate
from geo3d.analysis import revolution as R

rows = []   # (mô tả, kỳ vọng của test TS, kết quả Python)

# --- distance (distance.test.ts) ---
rows.append(("dist (0,0,0)-(2,1,2)  [distance.test.ts]", "3",
             C.distance(E.point(0,0,0), E.point(2,1,2)).text))
rows.append(("dist (1,1,1)->mp x+y+z=0", "√3",
             C.distance(E.point(1,1,1), E.Plane(E.V.rat_vec(1,1,1), S.rat(0))).text))
rows.append(("dist (0,2,0)->trục Ox", "2",
             C.distance(E.point(0,2,0), E.Line(E.V.rat_vec(0,0,0), E.V.rat_vec(1,0,0))).text))

# --- volume (volume.test.ts) ---
rows.append(("thể tích tứ diện đơn vị  [volume.test.ts]", "1/6",
             C.tetra_volume(E.point(0,0,0), E.point(1,0,0), E.point(0,1,0), E.point(0,0,1)).text))
rows.append(("thể tích chóp đáy vuông cạnh 2 cao 3", "4",
             C.pyramid_volume([E.point(0,0,0),E.point(2,0,0),E.point(2,2,0),E.point(0,2,0)], E.point(1,1,3)).text))

# tỉ số thể tích: v1=1/6, v2=8/6 -> 1/8
v1 = S.div(_abs_s(_triple(E.point(0,0,0).p,E.point(1,0,0).p,E.point(0,1,0).p,E.point(0,0,1).p)), S.rat(6))
v2 = S.div(_abs_s(_triple(E.point(0,0,0).p,E.point(2,0,0).p,E.point(0,2,0).p,E.point(0,0,2).p)), S.rat(6))
rows.append(("tỉ số thể tích (1/6)/(8/6)", "1/8", C.volume_ratio(v1, v2).text))

# --- solver (solver1d.test.ts) ---
rs = solve_quadratic(S.rat(1), S.rat(-5), S.rat(6))
rows.append(("x²−5x+6=0  [solver1d.test.ts]", "['2', '3']", str(sorted(r.text() for r in rs))))
rs = solve_quadratic(S.rat(1), S.rat(0), S.rat(-7))
rows.append(("x²−7=0", "['-√7', '√7']", str(sorted(r.text() for r in rs))))

# --- revolution (revolution.test.ts) ---
res = R.build_revolution_oy(R.poly([0,1]), (0,1), inner=R.poly([0,0,1]))
rows.append(("y=x & y=x² quay quanh Oy  [revolution.test.ts]", "π/6 (0.523599)", f"{res['value']:.6f}"))

# --- integral ---
val,_ = integrate(lambda x: x*x, 0, 1)
rows.append(("∫₀¹ x² dx  [quadrature.test.ts]", "1/3 (0.333333)", f"{val:.6f}"))


# ---- in bảng đối chiếu ----
def norm(s):
    # so số: nếu cả hai parse được thành float thì so gần đúng
    try:
        return round(float(s.split("(")[-1].rstrip(")")), 5)
    except Exception:
        return s.strip()

print(f"{'PHÉP TÍNH':50s} {'TEST TS kỳ vọng':18s} {'PYTHON':14s} KẾT QUẢ")
print("-" * 100)
ok = 0
for desc, ts_exp, py in rows:
    a, b = norm(ts_exp), norm(py)
    match = (a == b) or (isinstance(a, float) and isinstance(b, float) and abs(a-b) < 1e-4)
    # so trực tiếp chuỗi khi không phải số
    if not match:
        match = ts_exp.split(" (")[0].strip() == py.strip()
    flag = "✅ KHỚP" if match else "❌ LỆCH"
    if match: ok += 1
    print(f"{desc:50s} {ts_exp:18s} {py:14s} {flag}")
print("-" * 100)
print(f"{ok}/{len(rows)} khớp với giá trị bộ test TypeScript gốc khẳng định.")
