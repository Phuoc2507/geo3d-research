# -*- coding: utf-8 -*-
"""
demo.py — Giải vài bài mẫu END-TO-END bằng engine Python, để thấy cả 3 MỨC an toàn.
Chạy:  python demo.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from geo3d import solve


def show(tieu_de, plan):
    print("=" * 70)
    print(tieu_de)
    r = solve.run_plan(plan)
    if r["violations"]:
        print("  Ràng buộc bị vi phạm:")
        for v in r["violations"]:
            print("   -", v)
    for a in r["answers"]:
        dau = "≈ (gần đúng)" if a.approximate else "= (chính xác)"
        print(f"  {a.kind}: {dau} {a.text}")
    if r["error"]:
        print("  Lỗi tính:", r["error"])
    t = r["tier"]
    nhan = {1: "MỨC 1 — đã kiểm chứng", 2: "MỨC 2 — thang chữ", 3: "MỨC 3 — chưa kiểm chứng"}[t["level"]]
    extra = f" ({t.get('exactness')})" if t["level"] == 1 else f" [{t.get('reason')}]"
    print(f"  => {nhan}{extra}")
    print()


# BÀI 1 — Chóp O.ABC vuông tại O, OA=OB=OC=1. Tính thể tích + khoảng cách O đến (ABC).
# Đề CHO đủ dữ kiện -> engine kiểm ràng buộc vuông góc, tính chính xác -> MỨC 1.
show(
    "BÀI 1: Chóp O.ABC, OA,OB,OC đôi một vuông góc, độ dài 1.\n"
    "       Hỏi thể tích O.ABC và khoảng cách O đến mặt (ABC).",
    {
        "points": {"O": (0, 0, 0), "A": (1, 0, 0), "B": (0, 1, 0), "C": (0, 0, 1)},
        "asserts": [
            ("perp", ["OA", "OB"]),
            ("perp", ["OB", "OC"]),
            ("perp", ["OA", "OC"]),
        ],
        "queries": [
            ("volume_tetra", ["O", "A", "B", "C"]),
            ("distance", ["O", "ABC"]),
            ("area", ["A", "B", "C"]),
        ],
    },
)

# BÀI 2 — Góc giữa hai mặt phẳng. Lập phương ABCD.A'B'C'D' cạnh 1.
# Góc giữa (ABCD) và (ACC'A')? -> ra góc đẹp 90° hoặc 45° tuỳ mặt.
show(
    "BÀI 2: Trong hệ Oxyz, góc giữa mặt (Oxy) và mặt (x=y).",
    {
        "points": {"O": (0, 0, 0), "X": (1, 0, 0), "Y": (0, 1, 0),
                   "P": (1, 1, 0), "Q": (1, 1, 1)},
        "asserts": [],
        # (Oxy) qua O,X,Y ; mặt chéo qua O,P,Q
        "queries": [("angle", ["OXY", "OPQ"])],
    },
)

# BÀI 3 — Đề SAI dữ kiện: khẳng định AB ⊥ AC nhưng toạ độ cho góc 45°.
# Engine BẮT mâu thuẫn -> từ chối chứng nhận -> MỨC 3 (thà không trả còn hơn trả sai).
show(
    "BÀI 3 (đề mâu thuẫn): nói 'AB ⊥ AC' nhưng toạ độ lại cho góc 45°.",
    {
        "points": {"A": (0, 0, 0), "B": (1, 0, 0), "C": (1, 1, 0)},
        "asserts": [("perp", ["AB", "AC"])],
        "queries": [("area", ["A", "B", "C"])],
    },
)
