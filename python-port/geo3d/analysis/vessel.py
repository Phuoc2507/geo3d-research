# -*- coding: utf-8 -*-
"""
vessel.py — dịch từ api/_lib/kernel/analysis/vessel.ts

Vật thể tròn xoay GHÉP KHÚC ("vessel": bình/lu/chậu/phễu/cốc), cho bằng SỐ ĐO trên thiết diện qua
trục — KHÔNG phải hàm r(x). Biên dạng = danh sách khúc {cylinder | frustum | sphereZone}.

CHÍNH XÁC NHẤT: thể tích tính HAI CÁCH độc lập rồi ĐỐI CHIẾU:
  1) Công thức ĐÓNG cho từng khúc (trụ / nón cụt / đới cầu) — cộng lại (đáp số chính, đúng tuyệt đối).
  2) Tích phân SỐ π∫r(x)²dx trên toàn biên dạng (tái dùng bộ Simpson tự-kiểm của quadrature).
verified = danh sách khúc HỢP LỆ (không hở/chồng/vượt cầu) VÀ hai cách khớp nhau trong dung sai.

Khúc (VesselSegment) là dict:
  {'type':'cylinder',   'x0','x1','r'}
  {'type':'frustum',    'x0','x1','r0','r1'}
  {'type':'sphereZone', 'x0','x1','R','c'}
"""
from __future__ import annotations
import math
from .quadrature import integrate


# ---- Thể tích ĐÓNG (chính xác) của một khúc quay quanh trục ----
def vessel_segment_volume(s) -> float:
    h = s["x1"] - s["x0"]
    t = s["type"]
    if t == "cylinder":
        # Trụ: V = π r² h.
        return math.pi * s["r"] * s["r"] * h
    if t == "frustum":
        # Nón cụt: V = π h/3 (r0² + r0 r1 + r1²).
        return (math.pi * h / 3) * (s["r0"] * s["r0"] + s["r0"] * s["r1"] + s["r1"] * s["r1"])
    if t == "sphereZone":
        # Đới/chỏm cầu: V = π [ R²·h − ((x1−c)³ − (x0−c)³)/3 ].
        u1 = s["x1"] - s["c"]
        u0 = s["x0"] - s["c"]
        return math.pi * (s["R"] * s["R"] * h - (u1 * u1 * u1 - u0 * u0 * u0) / 3)
    raise ValueError(f"loại khúc lạ: {t}")


# ---- Bán kính của một khúc tại toạ độ trục x (để lấy mẫu đường sinh) ----
def vessel_segment_radius(s, x: float) -> float:
    t = s["type"]
    if t == "cylinder":
        return max(0.0, s["r"])
    if t == "frustum":
        w = s["x1"] - s["x0"]
        tt = 0.0 if w == 0 else (x - s["x0"]) / w
        return max(0.0, s["r0"] + (s["r1"] - s["r0"]) * tt)
    d = s["R"] * s["R"] - (x - s["c"]) * (x - s["c"])
    return math.sqrt(d) if d > 0 else 0.0


# ---- Kiểm danh sách khúc có DỰNG ĐƯỢC một vật thể liền mạch không ----
def validate_vessel_segments(segs) -> dict:
    if not isinstance(segs, list) or len(segs) == 0:
        return {"ok": False, "reason": "không có khúc nào"}
    EPS = 1e-6
    for i, s in enumerate(segs):
        if not (math.isfinite(s["x0"]) and math.isfinite(s["x1"])):
            return {"ok": False, "reason": f"khúc {i}: toạ độ trục không hợp lệ"}
        if s["x1"] - s["x0"] <= EPS:
            return {"ok": False, "reason": f"khúc {i}: x1 phải lớn hơn x0"}
        t = s["type"]
        if t == "cylinder":
            if not (s["r"] >= 0):
                return {"ok": False, "reason": f"khúc {i}: bán kính âm"}
        elif t == "frustum":
            if not (s["r0"] >= 0) or not (s["r1"] >= 0):
                return {"ok": False, "reason": f"khúc {i}: bán kính âm"}
        else:
            # sphereZone: R>0 và [x0,x1] phải nằm trong [c−R, c+R].
            if not (s["R"] > 0):
                return {"ok": False, "reason": f"khúc {i}: bán kính cầu R phải > 0"}
            if abs(s["x0"] - s["c"]) > s["R"] + EPS or abs(s["x1"] - s["c"]) > s["R"] + EPS:
                return {"ok": False, "reason": f"khúc {i}: đoạn [x0,x1] vượt ra ngoài mặt cầu"}
        # Liền mạch: đầu khúc sau phải trùng cuối khúc trước (cho phép BẬC bán kính, không cho HỞ/CHỒNG trục).
        if i > 0 and abs(segs[i - 1]["x1"] - s["x0"]) > 1e-4:
            return {"ok": False, "reason": f"khúc {i}: không tiếp giáp khúc trước (hở/chồng dọc trục)"}
    return {"ok": True}


def vessel_profile(segs) -> dict:
    return {"kind": "piecewise", "segments": segs}


# ---- Bán kính GHÉP KHÚC tại x (tương đương compileProfile 'piecewise' bên TS) ----
def _piecewise_radius(segs):
    def r(x: float) -> float:
        for s in segs:
            if x <= s["x1"] + 1e-12:
                return vessel_segment_radius(s, x)
        return vessel_segment_radius(segs[-1], x)
    return r


# ---- Số đo dễ đọc: bán kính 2 mép + chiều cao (xếp từ ĐÁY lên) ----
def vessel_segments_from_measures(measures) -> list:
    """Chuyển danh sách 'số đo' thành khúc nội bộ. sphereZone: TỰ SUY R & tâm c từ (rBottom, rTop, h):
        a = (rB² − rT² − h²)/(2h);  R = √(rB² + a²);  c = x0 − a.
    Số đo không hợp lệ (h≤0, loại lạ) ⇒ trả []."""
    if not isinstance(measures, list) or len(measures) == 0:
        return []
    segs = []
    x = 0.0
    for m in measures:
        try:
            h = float(m.get("h"))
        except (TypeError, ValueError):
            return []
        if not math.isfinite(h) or h <= 0:
            return []
        x0 = x
        x1 = x + h
        t = m.get("type")
        if t == "cylinder":
            segs.append({"type": "cylinder", "x0": x0, "x1": x1, "r": float(m["r"])})
        elif t == "frustum":
            segs.append({"type": "frustum", "x0": x0, "x1": x1,
                         "r0": float(m["rBottom"]), "r1": float(m["rTop"])})
        elif t == "sphereZone":
            try:
                rB = float(m["rBottom"])
                rT = float(m["rTop"])
            except (TypeError, ValueError, KeyError):
                return []
            if not math.isfinite(rB) or not math.isfinite(rT):
                return []
            a = (rB * rB - rT * rT - h * h) / (2 * h)
            R = math.sqrt(rB * rB + a * a)
            c = x0 - a
            segs.append({"type": "sphereZone", "x0": x0, "x1": x1, "R": R, "c": c})
        else:
            return []
        x = x1
    return segs


# ---- Mẫu đường sinh cho LatheGeometry ----
def sample_vessel_profile(segs) -> list:
    out = []
    for s in segs:
        n = 24 if s["type"] == "sphereZone" else 1
        for i in range(n + 1):
            x = s["x0"] + (s["x1"] - s["x0"]) * i / n
            pt = {"x": x, "r": vessel_segment_radius(s, x)}
            prev = out[-1] if out else None
            # Bỏ điểm trùng x với điểm trước TRỪ khi bán kính đổi (bậc) — giữ vai phẳng.
            if prev and abs(prev["x"] - x) < 1e-9 and abs(prev["r"] - pt["r"]) < 1e-9:
                continue
            out.append(pt)
    return out


def _fmt_num(v: float) -> str:
    r = round(v * 1e6) / 1e6
    return str(int(r)) if r == int(r) else str(r)


def vessel_volume(segs) -> dict:
    """Thể tích vật thể ghép: công thức đóng (chính) + tích phân số (đối chiếu)."""
    valid = validate_vessel_segments(segs)
    closed = sum(vessel_segment_volume(s) for s in segs)
    a = segs[0]["x0"] if segs else 0.0
    b = segs[-1]["x1"] if segs else 0.0
    r = _piecewise_radius(segs)
    num_value, _ = integrate(lambda x: math.pi * r(x) * r(x), a, b)
    gap = abs(closed - num_value)
    # Đối chiếu tương đối; ngưỡng nới nhẹ vì tích phân qua điểm gãy hội tụ chứ không tuyệt đối.
    agree = gap <= 1e-5 * max(1, abs(closed))
    return {
        "value": closed, "numeric": num_value, "gap": gap,
        "verified": valid["ok"] and agree,
        "reason": None if valid["ok"] else valid["reason"],
    }


def build_vessel_solid(id: str, segs, opts: dict | None = None) -> dict:
    """Dựng RevolutionSolid cho vật thể ghép — tái dùng type + renderer lathe. axis mặc định 'Oy'."""
    opts = opts or {}
    v = vessel_volume(segs)
    value, gap, verified = v["value"], v["gap"], v["verified"]
    a = segs[0]["x0"] if segs else 0.0
    b = segs[-1]["x1"] if segs else 0.0
    latex = f"V={_fmt_num(value)}"
    volume = {"value": value, "latex": latex, "verified": verified, "estimatedError": gap}
    return {
        "id": id,
        "outer": vessel_profile(segs),
        "axis": opts.get("axis", "Oy"),
        "domain": [a, b],
        "method": "disk",
        "color": opts.get("color"),
        "volume": volume,
        "samples": sample_vessel_profile(segs),
    }
