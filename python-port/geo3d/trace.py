# -*- coding: utf-8 -*-
"""
trace.py — dịch từ api/_lib/kernel/trace.ts

Nhật ký sự kiện thuần, không I/O, không mốc thời gian thực → kernel giữ tính xác định
và dễ kiểm thử. Bên gọi tự gắn đo thời gian quanh lời gọi kernel.
"""
from __future__ import annotations
from dataclasses import dataclass, field

# TraceStage ∈ {'execute', 'verify', 'repair', 'exactForm'}


@dataclass
class TraceEvent:
    stage: str
    message: str
    data: dict | None = None


class Trace:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def log(self, stage: str, message: str, data: dict | None = None) -> None:
        self.events.append(TraceEvent(stage, message, data))

    def summary(self) -> dict:
        by_stage: dict[str, int] = {}
        for e in self.events:
            by_stage[e.stage] = by_stage.get(e.stage, 0) + 1
        return {"totalEvents": len(self.events), "byStage": by_stage}
