# -*- coding: utf-8 -*-
"""
diff_engines.py — DIFF TRỰC TIẾP: engine PYTHON vs engine TS ĐANG CHẠY.
Đọc parity_ts.json (do node_parity.mjs xuất từ bundle TS), tính lại bằng Python, so từng số.
Chạy: python diff_engines.py   (sau khi đã chạy node python-port/node_parity.mjs)
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from geo3d.analysis import revolution as R

here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "parity_ts.json"), encoding="utf-8-sig") as f:  # utf-8-sig: bỏ BOM của PowerShell
    ts = json.load(f)

# Tính CÙNG các ca bằng engine Python
py = {
    "Ox y=x [0,1] -> pi/3":               R.revolution_volume_disk(R.poly([0, 1]), (0, 1))[0],
    "Ox y=sqrt(x) [0,1] -> pi/2":         R.revolution_volume_disk(R.sqrtp(1, 0), (0, 1))[0],
    "Ox r=sqrt(1-x^2) [-1,1] -> 4pi/3":   R.revolution_volume_disk(R.expr("sqrt(1 - x^2)"), (-1, 1))[0],
    "Ox vanh khan sqrt(x)&x [0,1] -> pi/6": R.revolution_volume_disk(R.sqrtp(1, 0), (0, 1), R.poly([0, 1]))[0],
    "Oy vo tru y=x & y=x^2 [0,1] -> pi/6":  R.revolution_volume_shell_oy(R.poly([0, 1]), (0, 1), R.poly([0, 0, 1]))[0],
}

print(f"{'CA':40s} {'ENGINE TS':16s} {'ENGINE PYTHON':16s} {'|LỆCH|':12s}")
print("-" * 90)
ok = 0
for k in ts:
    a, b = ts[k], py[k]
    d = abs(a - b)
    match = d < 1e-9
    if match: ok += 1
    print(f"{k:40s} {a:<16.12f} {b:<16.12f} {d:.1e} {'✅' if match else '❌'}")
print("-" * 90)
print(f"{ok}/{len(ts)} ca: engine Python trùng engine TS trong sai số 1e-9.")
