# -*- coding: utf-8 -*-
"""
polyfit.py — dịch từ api/_lib/kernel/analysis/polyfit.ts

Tầng HÀM SỐ cho engine giải tích: khớp đa thức qua điểm (có thể ghim hệ số bậc cao nhất),
tính giá trị, đạo hàm, và tìm cực trị. Tất cả bằng SỐ (float) như bản gốc.
Hệ số luôn theo thứ tự [c0, c1, ..., cn] ứng với c0 + c1·x + ... + cn·xⁿ.
"""
from __future__ import annotations
from .solver import solve_all_param   # tương đương solveAllParam trong paramsolve.ts


def _solve_linear(A: list[list[float]], b: list[float]) -> list[float]:
    """Khử Gauss có chọn trụ (hệ nhỏ, n ≤ 6). Ném nếu suy biến."""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        piv = col
        for r in range(col + 1, n):
            if abs(M[r][col]) > abs(M[piv][col]):
                piv = r
        if abs(M[piv][col]) < 1e-12:
            raise ValueError("Khớp đa thức: hệ suy biến (điểm trùng/không xác định)")
        M[col], M[piv] = M[piv], M[col]
        for r in range(n):
            if r == col:
                continue
            f = M[r][col] / M[col][col]
            for c in range(col, n + 1):
                M[r][c] -= f * M[col][c]
    return [M[i][n] / M[i][i] for i in range(n)]


def fit_poly(
    degree: int,
    through: list[tuple[float, float]],
    leading: float | None = None,
    slope_at: list[tuple[float, float]] | None = None,
) -> list[float]:
    """Khớp đa thức bậc `degree` qua `through` VÀ ràng buộc đạo hàm `slope_at` ([x, f'(x)]).
    Nếu `leading` cho trước ⇒ hệ số bậc cao nhất bị GHIM, chỉ khớp `degree` hệ số còn lại.
    Tổng số ràng buộc (through + slope_at) phải BẰNG số ẩn."""
    if slope_at is None:
        slope_at = []
    n_unknown = degree + 1 if leading is None else degree
    n_given = len(through) + len(slope_at)
    if n_given != n_unknown:
        pinned = "" if leading is None else " (đã ghim hệ số đầu)"
        raise ValueError(
            f"fitPoly: cần {n_unknown} ràng buộc cho bậc {degree}{pinned}, nhận {n_given}"
        )
    A: list[list[float]] = []
    b: list[float] = []
    # Ràng buộc giá trị: c0 + c1·x + ... = y (trừ phần hệ số đã ghim).
    for x, y in through:
        row = [x ** k for k in range(n_unknown)]
        A.append(row)
        b.append(y if leading is None else y - leading * (x ** degree))
    # Ràng buộc đạo hàm: Σ k·c_k·x^(k−1) = s (trừ phần hệ số đã ghim).
    for x, s in slope_at:
        row = [0 if k == 0 else k * (x ** (k - 1)) for k in range(n_unknown)]
        A.append(row)
        b.append(s if leading is None else s - degree * leading * (x ** (degree - 1)))
    sol = _solve_linear(A, b)
    return sol if leading is None else [*sol, leading]


def eval_poly(c: list[float], x: float) -> float:
    """Horner."""
    s = 0.0
    for k in range(len(c) - 1, -1, -1):
        s = s * x + c[k]
    return s


def deriv_poly(c: list[float]) -> list[float]:
    d = [k * c[k] for k in range(1, len(c))]
    return d if d else [0]


def extremum_of_poly(
    c: list[float], lo: float, hi: float, sense: str | None = None
):
    """Cực trị = nghiệm f'(x)=0 trong [lo,hi] MÀ f''≠0 (loại điểm uốn).
    `sense`='max' (f''<0) / 'min' (f''>0); bỏ trống ⇒ cực trị thật đầu tiên.
    Trả {'x','y'} hoặc None."""
    d1 = deriv_poly(c)
    d2 = deriv_poly(d1)
    extrema = [
        {"x": x, "y": eval_poly(c, x), "curv": eval_poly(d2, x)}
        for x in solve_all_param(lambda x: eval_poly(d1, x), 0, lo, hi)
    ]
    extrema = [e for e in extrema if abs(e["curv"]) > 1e-9]  # f''≠0 ⇒ cực trị THẬT
    if sense == "max":
        pick = [e for e in extrema if e["curv"] < 0]
    elif sense == "min":
        pick = [e for e in extrema if e["curv"] > 0]
    else:
        pick = extrema
    if not pick:
        return None
    return {"x": pick[0]["x"], "y": pick[0]["y"]}
