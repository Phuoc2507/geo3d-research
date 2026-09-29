# -*- coding: utf-8 -*-
"""
solver.py — dịch từ api/_lib/kernel/analysis/solver1d.ts + paramsolve.ts

Hai việc:
  1) GIẢI PHƯƠNG TRÌNH
     - solve_quadratic: bậc hai a x²+b x+c=0, giữ CHÍNH XÁC (căn/hữu tỉ) khi ở trong trường.
     - solve_all_param / solve_param: giải f(x)=target bằng SỐ (quét lưới đổi dấu + chia đôi),
       dùng cho hàm bất kỳ (không cần công thức nghiệm).
  2) TỐI ƯU 1 BIẾN
     - optimize_param: tìm max/min của f trên [lo,hi] bằng lưới thô + golden-section (không cần đạo hàm).
"""
from __future__ import annotations
import math
from .. import scalar as S
from ..scalar import Scalar


# ============================ GIẢI BẬC HAI (chính xác) ============================
def solve_quadratic(a: Scalar, b: Scalar, c: Scalar) -> list[Scalar]:
    """Giải a·x² + b·x + c = 0 trên R. Trả 0/1/2 nghiệm (Scalar). a=0 -> tuyến tính.
    Nghiệm giữ dạng exact khi Δ là số chính phương / trong trường; ngược lại rơi về số."""
    if S.is_zero(a):
        if S.is_zero(b):
            return []                                  # vô số hoặc vô nghiệm -> trả []
        return [S.neg(S.div(c, b))]                     # b x + c = 0
    disc = S.sub(S.mul(b, b), S.mul(S.mul(S.rat(4), a), c))   # Δ = b² − 4ac
    cmp = S.cmp_scalar(disc, S.rat(0))
    if cmp < 0:
        return []                                       # Δ < 0: vô nghiệm thực
    two_a = S.mul(S.rat(2), a)
    if cmp == 0:
        return [S.neg(S.div(b, two_a))]                 # nghiệm kép
    sq = S.sqrt(disc)
    return [S.div(S.sub(S.neg(b), sq), two_a),
            S.div(S.add(S.neg(b), sq), two_a)]          # (−b ± √Δ)/2a


# ============================ GIẢI f(x)=target (số) ============================
def solve_all_param(f, target: float, lo: float, hi: float, grid: int = 800) -> list[float]:
    """Quét lưới tìm MỌI ô đổi dấu của g=f−target rồi chia đôi. Trả tất cả nghiệm (đã khử trùng)."""
    g = lambda x: f(x) - target
    roots: list[float] = []

    def push(x):
        if not roots or abs(x - roots[-1]) > 1e-9:
            roots.append(x)

    x0, g0 = lo, g(lo)
    if g0 == 0:
        push(lo)
    for i in range(1, grid + 1):
        x1 = lo + (hi - lo) * i / grid
        g1 = g(x1)
        if g1 == 0:
            push(x1); x0, g0 = x1, g1; continue
        if g0 * g1 < 0:                                  # đổi dấu -> có nghiệm trong [x0,x1]
            a, b, ga = x0, x1, g0
            for _ in range(200):
                m = (a + b) / 2
                gm = g(m)
                if ga * gm <= 0:
                    b = m
                else:
                    a, ga = m, gm
                if b - a < 1e-13:
                    break
            push((a + b) / 2)
        x0, g0 = x1, g1
    return roots


def solve_param(f, target: float, lo: float, hi: float, grid: int = 800):
    """Trả nghiệm ĐẦU TIÊN của f(x)=target (kèm residual). None nếu không có."""
    roots = solve_all_param(f, target, lo, hi, grid)
    if not roots:
        return None
    x = roots[0]
    return {"x": x, "residual": abs(f(x) - target)}


# ============================ TỐI ƯU 1 BIẾN ============================
def optimize_param(f, lo: float, hi: float, sense: str, grid: int = 400):
    """Tìm max/min của f trên [lo,hi]: lưới thô tìm ô tốt nhất -> golden-section trong ô lân cận.
    sense = 'max' hoặc 'min'. Trả {'x', 'value'}."""
    sign = 1 if sense == "max" else -1
    bx, bv = lo, sign * f(lo)
    for i in range(1, grid + 1):
        x = lo + (hi - lo) * i / grid
        v = sign * f(x)
        if v > bv:
            bv, bx = v, x
    h = (hi - lo) / grid
    a = max(lo, bx - h)
    b = min(hi, bx + h)
    gr = (math.sqrt(5) - 1) / 2                          # tỉ lệ vàng
    c = b - gr * (b - a)
    d = a + gr * (b - a)
    for _ in range(200):
        if sign * f(c) > sign * f(d):
            b = d
        else:
            a = c
        c = b - gr * (b - a)
        d = a + gr * (b - a)
        if b - a < 1e-12:
            break
    x = (a + b) / 2
    return {"x": x, "value": f(x)}


# ============================ TỐI ƯU NHIỀU BIẾN ============================
# Dịch từ api/_lib/kernel/analysis/paramsolve.ts (nelderMead + optimizeMulti).
import time


def nelder_mead(g, x0, los, his, step, max_iter=200, over_deadline=None):
    """Nelder–Mead (đơn hình) — tối thiểu hoá g KHÔNG cần đạo hàm; xử lý tốt 'thung lũng chéo/cong'
    mà hạ-toạ-độ hay KẸT. Giữ trong hộp [los,his] bằng cách kẹp mọi điểm trước khi đánh giá."""
    if over_deadline is None:
        over_deadline = lambda: False
    n = len(x0)

    def clamp(xs):
        return [max(los[d], min(his[d], x)) for d, x in enumerate(xs)]

    def ev(xs):
        return g(clamp(xs))

    simplex = []
    p0 = clamp(list(x0))
    simplex.append({"xs": p0, "v": ev(p0)})
    for d in range(n):
        p = list(p0)
        p[d] += step[d] if step[d] else 1e-3
        pc = clamp(p)
        simplex.append({"xs": pc, "v": ev(pc)})

    alpha, gamma, rho, sigma = 1.0, 2.0, 0.5, 0.5
    for _ in range(max_iter):
        if over_deadline():
            break
        simplex.sort(key=lambda s: s["v"])
        # hội tụ: đơn hình đủ nhỏ (đường kính theo toạ độ)
        dia = 0.0
        for d in range(n):
            mn, mx = math.inf, -math.inf
            for s in simplex:
                mn = min(mn, s["xs"][d])
                mx = max(mx, s["xs"][d])
            dia = max(dia, mx - mn)
        if dia < 1e-10:
            break
        worst = simplex[n]
        cen = [0.0] * n
        for i in range(n):
            for d in range(n):
                cen[d] += simplex[i]["xs"][d] / n
        reflect = [cen[d] + alpha * (cen[d] - worst["xs"][d]) for d in range(n)]
        vr = ev(reflect)
        if vr < simplex[0]["v"]:
            expand = [cen[d] + gamma * (cen[d] - worst["xs"][d]) for d in range(n)]
            ve = ev(expand)
            simplex[n] = {"xs": clamp(expand), "v": ve} if ve < vr else {"xs": clamp(reflect), "v": vr}
        elif vr < simplex[n - 1]["v"]:
            simplex[n] = {"xs": clamp(reflect), "v": vr}
        else:
            contract = [cen[d] + rho * (worst["xs"][d] - cen[d]) for d in range(n)]
            vc = ev(contract)
            if vc < worst["v"]:
                simplex[n] = {"xs": clamp(contract), "v": vc}
            else:
                for i in range(1, n + 1):
                    base = simplex[0]["xs"]
                    xs = clamp([base[d] + sigma * (simplex[i]["xs"][d] - base[d]) for d in range(n)])
                    simplex[i] = {"xs": xs, "v": ev(xs)}
    simplex.sort(key=lambda s: s["v"])
    return simplex[0]["xs"]


def optimize_multi(f, los, his, sense, grid_per_dim=40, rounds=60, restarts=5, deadline_ms=None):
    """Tối ưu NHIỀU biến trên hộp [los,his]: quét lưới thô, rồi HẠ TOẠ ĐỘ (golden-section từng chiều)
    từ K Ô TỐT NHẤT (đa-điểm-xuất-phát), rồi ĐÁNH BÓNG bằng Nelder–Mead (chống kẹt thung lũng chéo).
    sense = 'max' | 'min'. Trả {'xs', 'value'}."""
    n = len(los)
    sign = 1 if sense == "max" else -1
    gr = (math.sqrt(5) - 1) / 2

    # Cắt thời gian: objective có thể gọi dựng hình mỗi eval ⇒ rất đắt. Quá hạn ⇒ DỪNG SỚM.
    def over_deadline():
        return deadline_ms is not None and time.time() * 1000 > deadline_ms

    # Quét lưới, thu mọi ô kèm giá trị.
    cells = []
    total = (grid_per_dim + 1) ** n
    for t in range(total):
        if over_deadline():
            break
        rem = t
        xs = []
        for d in range(n):
            i = rem % (grid_per_dim + 1)
            rem //= (grid_per_dim + 1)
            xs.append(los[d] + (his[d] - los[d]) * i / grid_per_dim)
        cells.append({"xs": xs, "v": sign * f(xs)})
    if not cells:                                    # quá hạn trước ô đầu
        xs = list(los)
        return {"xs": xs, "value": f(xs)}
    cells.sort(key=lambda c: c["v"], reverse=True)   # tốt nhất (theo sign) lên đầu
    starts = cells[:max(1, restarts)]

    # Hạ toạ độ từ một điểm xuất phát.
    def refine(start):
        xs = list(start)
        for _ in range(rounds):
            if over_deadline():
                break
            for d in range(n):
                h = (his[d] - los[d]) / grid_per_dim
                a = max(los[d], xs[d] - h)
                b = min(his[d], xs[d] + h)
                c = b - gr * (b - a)
                e = a + gr * (b - a)
                for _ in range(80):
                    xc = list(xs); xc[d] = c
                    xe = list(xs); xe[d] = e
                    if sign * f(xc) > sign * f(xe):
                        b = e
                    else:
                        a = c
                    c = b - gr * (b - a)
                    e = a + gr * (b - a)
                    if b - a < 1e-9:                 # 1e-9 đủ chính xác, nhanh hơn 1e-13
                        break
                xs[d] = (a + b) / 2
        return {"xs": xs, "value": f(xs)}

    best = refine(starts[0]["xs"])
    for s in range(1, len(starts)):
        if over_deadline():
            break
        cand = refine(starts[s]["xs"])
        if sign * cand["value"] > sign * best["value"]:
            best = cand

    # ĐÁNH BÓNG bằng Nelder–Mead từ nghiệm tốt nhất + vài ô lưới đầu. g = −sign·f.
    def g(xs):
        return -sign * f(xs)

    nm_step = [(his[d] - los[d]) / grid_per_dim for d in range(n)]
    nm_starts = [best["xs"]] + [s["xs"] for s in starts[:3]]
    for st in nm_starts:
        if over_deadline():
            break
        nm_xs = nelder_mead(g, st, los, his, nm_step, 200, over_deadline)
        fv = f(nm_xs)
        if sign * fv > sign * best["value"]:
            best = {"xs": nm_xs, "value": fv}
    return best
