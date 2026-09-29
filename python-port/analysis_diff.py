# -*- coding: utf-8 -*-
"""
analysis_diff.py — DIFF nhánh GIẢI TÍCH: geo3d.analysis.run_analysis (Python) vs engine TS.
Đọc analysis_plans.json (plan) + analysis_ts.json (đáp engine TS), chạy Python, so ok/param/approx/text.
Chạy: python analysis_diff.py  (sau khi node python-port/node_analysis.mjs)
"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from geo3d.analysis.run_analysis import run_analysis

here = os.path.dirname(os.path.abspath(__file__))
plans = json.load(open(os.path.join(here, "analysis_plans.json"), encoding="utf-8-sig"))
ts = json.load(open(os.path.join(here, "analysis_ts.json"), encoding="utf-8-sig"))


def _none_like(x):
    return x is None or (isinstance(x, float) and math.isnan(x))


def close(a, b, rtol=1e-4, atol=1e-4):
    # TS trả null khi không có tham số đơn; Python trả nan — coi là tương đương ("không có").
    if _none_like(a) or _none_like(b):
        return _none_like(a) and _none_like(b)
    return abs(a - b) <= atol + rtol * max(1.0, abs(b))


print(f"{'PLAN':34s} {'trường':7s} {'TS':16s} {'PYTHON':16s} KQ")
print("-" * 92)
ok_all = True
per_plan = []
for item in plans:
    pid = item["id"]
    t = ts.get(pid, {})
    r = run_analysis(item["plan"])
    py = {
        "ok": r.get("ok"),
        "param": (r.get("parameter") or {}).get("value") if isinstance(r.get("parameter"), dict) else None,
        "approx": (r.get("answer") or {}).get("approx") if isinstance(r.get("answer"), dict) else None,
        "text": (r.get("answer") or {}).get("text") if isinstance(r.get("answer"), dict) else None,
    }
    checks = []
    checks.append(("ok", t.get("ok"), py["ok"], t.get("ok") == py["ok"]))
    if t.get("param") is not None or py["param"] is not None:
        checks.append(("param", t.get("param"), py["param"], close(py["param"], t.get("param"))))
    if t.get("approx") is not None or py["approx"] is not None:
        checks.append(("approx", t.get("approx"), py["approx"], close(py["approx"], t.get("approx"))))
    if t.get("text") is not None or py["text"] is not None:
        checks.append(("text", t.get("text"), py["text"], t.get("text") == py["text"]))
    plan_ok = all(c[3] for c in checks)
    ok_all = ok_all and plan_ok
    per_plan.append((pid, plan_ok))
    for i, (field, tv, pv, good) in enumerate(checks):
        head = pid[:34] if i == 0 else ""
        tvs = f"{tv:.5g}" if isinstance(tv, float) else str(tv)
        pvs = f"{pv:.5g}" if isinstance(pv, float) else str(pv)
        print(f"{head:34s} {field:7s} {tvs:16.16s} {pvs:16.16s} {'✅' if good else '❌'}")
print("-" * 92)
npass = sum(1 for _, ok in per_plan if ok)
print(f"{npass}/{len(per_plan)} plan giải tích: Python KHỚP engine TS (ok+param+approx+text).")
