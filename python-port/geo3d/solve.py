# -*- coding: utf-8 -*-
"""
solve.py — bộ chạy "Construction Plan" + phân tầng độ tin cậy.
Gộp ý của kernel/index.ts (runPlan), verify.ts (verifyPlan) và kernel-bridge/classifyTier.js.

Một "plan" là dữ liệu THUẦN (giống JSON mà LLM xuất ra):
  points  : { tên: (x,y,z) }               — toạ độ hữu tỉ chính xác
  asserts : [ (quan hệ, [đối số], value?) ] — ràng buộc của đề, để engine tự kiểm
  queries : [ (loại, [đối số]) ]            — đại lượng cần tính

Engine dựng thực thể, KIỂM ràng buộc trước, rồi mới TÍNH, cuối cùng gán 1 trong 3 MỨC.
"""
from __future__ import annotations
from . import scalar as S
from . import entities as E
from . import compute as C
from . import verify as VF


def _resolve(token, points: dict[str, E.Point]):
    """Đổi một 'token' của đề thành thực thể.
    - "A"        -> điểm A
    - "AB"       -> đường thẳng qua A,B  (2 tên điểm ghép lại)
    - "ABC"      -> mặt phẳng qua A,B,C  (3 tên điểm ghép lại)
    (Bản rút gọn: tên điểm là 1 chữ cái. Engine gốc có bộ resolve mạnh hơn.)
    """
    if token in points:
        return points[token]
    names = list(token)
    if len(names) == 2 and all(n in points for n in names):
        return E.line_through(points[names[0]], points[names[1]])
    if len(names) == 3 and all(n in points for n in names):
        return E.plane_through(points[names[0]], points[names[1]], points[names[2]])
    raise ValueError(f"không phân giải được token '{token}'")


def _run_query(kind: str, args: list[str], points):
    ents = [_resolve(t, points) for t in args]
    if kind == "distance":
        return C.distance(ents[0], ents[1])
    if kind == "angle":
        return C.angle(ents[0], ents[1])
    if kind == "area":
        pts = [points[n] for n in args]           # area nhận danh sách TÊN ĐIỂM
        if len(pts) == 3:
            return C.triangle_area(*pts)
        return C.polygon_area(pts)
    if kind == "volume_tetra":
        return C.tetra_volume(*[points[n] for n in args])
    if kind == "volume_pyramid":
        *base, apex = [points[n] for n in args]   # đỉnh chóp là tên CUỐI
        return C.pyramid_volume(base, apex)
    raise ValueError(f"query chưa hỗ trợ: {kind}")


def _check_asserts(asserts, points) -> list[VF.Violation]:
    out = []
    for a in asserts:
        rel, args = a[0], a[1]
        value = a[2] if len(a) > 2 else None
        ents = [_resolve(t, points) for t in args]
        if rel == "perp":
            v = VF.assert_perp(ents[0], ents[1])
        elif rel == "parallel":
            v = VF.assert_parallel(ents[0], ents[1])
        elif rel == "coplanar":
            v = VF.assert_coplanar([points[n] for n in args])
        elif rel == "on":
            v = VF.assert_on(ents[0], ents[1])
        elif rel == "dist":
            v = VF.assert_dist(ents[0], ents[1], value)
        else:
            raise ValueError(f"assert chưa hỗ trợ: {rel}")
        if v:
            out.append(v)
    return out


def run_plan(plan: dict) -> dict:
    """Chạy plan -> trả { violations, answers, tier }."""
    points = {name: E.point(*xyz) for name, xyz in plan.get("points", {}).items()}
    violations = _check_asserts(plan.get("asserts", []), points)

    answers = []
    error = None
    if not violations:                              # vi phạm giả thiết thì KHÔNG tính tiếp
        try:
            for q in plan.get("queries", []):
                answers.append(_run_query(q[0], q[1], points))
        except ValueError as ex:
            error = str(ex)

    tier = classify_tier(violations, answers, error)
    return {"violations": violations, "answers": answers, "error": error, "tier": tier}


def classify_tier(violations, answers, error) -> dict:
    """3 MỨC an toàn — neo vào việc engine có thực sự giải được không.
       Mức 1: đã kiểm chứng (còn chia exact / numeric)
       Mức 3: violation / error / chưa giải được  -> KHÔNG khẳng định đáp số
    """
    if violations:
        return {"level": 3, "reason": "violation", "message": str(violations[0])}
    if error:
        return {"level": 3, "reason": "error", "message": error}
    if not answers:
        return {"level": 3, "reason": "unsolved", "message": "engine chưa chứng thực đáp số"}
    all_exact = all(not a.approximate for a in answers)
    return {"level": 1, "exactness": "exact" if all_exact else "numeric"}
