# -*- coding: utf-8 -*-
"""
golden_diff_all.py — DIFF TOÀN BỘ: engine PYTHON (geo3d.run) vs engine TS, trên mọi ca golden
mà op ∈ {oxyz_*, edge}. Đọc golden_all_ts.json (ground truth TS), chạy geo3d.run trên CÙNG plan,
so từng đáp. Chạy: python golden_diff_all.py  (sau khi node python-port/golden_run_all.mjs)
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from geo3d import run as R

here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "golden_all_ts.json"), encoding="utf-8-sig") as f:
    cases = json.load(f)

total_q = match = miss = err = 0
mismatches = []
errored = []
for c in cases:
    plan = {"solidName": c["id"], "ops": c["ops"], "asserts": c.get("asserts", []), "queries": c["queries"]}
    res = R.run(plan)
    py_ans = res["answers"]
    ts_ans = c["ts_answers"]
    for i, q in enumerate(c["queries"]):
        total_q += 1
        ts = ts_ans[i] if i < len(ts_ans) else "(thiếu)"
        py = py_ans[i] if i < len(py_ans) else None
        if py is None:
            err += 1
            errored.append((c["id"], q["kind"], ts, res["errors"]))
        elif py == ts:
            match += 1
        else:
            miss += 1
            mismatches.append((c["id"], q["kind"], ts, py))

print(f"TỔNG: {total_q} truy vấn | KHỚP {match} | LỆCH {miss} | LỖI {err}")
print(f"Tỉ lệ khớp: {match}/{total_q} = {100*match/total_q:.1f}%")

if mismatches:
    print("\n--- LỆCH (tối đa 30) ---")
    for cid, k, ts, py in mismatches[:30]:
        print(f"  {cid[:34]:34s} {k:16s} TS={ts!r:16} PY={py!r}")
if errored:
    print("\n--- LỖI (tối đa 30) ---")
    for cid, k, ts, e in errored[:30]:
        msg = (e[0] if e else "")[:70]
        print(f"  {cid[:34]:34s} {k:16s} TS={ts!r:14} -> {msg}")
