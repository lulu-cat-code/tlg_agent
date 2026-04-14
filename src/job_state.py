"""Helpers for writing background job status and event logs."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


STAGE_ORDER = [
    "queued",
    "parse",
    "plan",
    "map",
    "generate",
    "optimize",
    "validate",
    "review",
    "done",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def build_stage_list(current_stage: str, final_status: str | None = None) -> list[dict[str, str]]:
    stages: list[dict[str, str]] = []
    try:
        current_index = STAGE_ORDER.index(current_stage)
    except ValueError:
        current_index = -1

    for index, stage in enumerate(STAGE_ORDER):
        status = "pending"
        if stage == "done":
            if final_status == "succeeded":
                status = "done"
            elif final_status == "failed":
                status = "failed"
            elif final_status == "cancelled":
                status = "cancelled"
        elif current_index >= 0:
            if index < current_index:
                status = "done"
            elif index == current_index:
                status = "running"
        stages.append({"name": stage, "status": status})
    return stages


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_event(path: str | Path, message: str) -> None:
    target = Path(path)
    timestamp = utc_now_iso()
    with target.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")
