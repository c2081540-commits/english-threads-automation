from __future__ import annotations

import json
from datetime import datetime, time
from pathlib import Path

from .paths import REPO_ROOT

SCHEDULE_CONFIG_PATH = REPO_ROOT / "config" / "schedule.json"
ALLOWED_STATUSES = {"pending", "posted", "failed", "skipped"}


def load_schedule_config(path: Path = SCHEDULE_CONFIG_PATH) -> dict:
    resolved = path.resolve()
    if resolved != SCHEDULE_CONFIG_PATH.resolve() or not resolved.is_file():
        raise FileNotFoundError(f"Required schedule config not found: {resolved}")
    value = json.loads(resolved.read_text(encoding="utf-8"))
    if value.get("timezone") != "Asia/Tokyo":
        raise ValueError("schedule timezone must be Asia/Tokyo")
    slots = value.get("quiz_slots")
    if not isinstance(slots, list) or len(slots) != 6 or len(set(slots)) != 6:
        raise ValueError("schedule requires six unique quiz slots")
    parsed = [_parse_slot(slot) for slot in slots]
    if _parse_slot(value.get("normal_slot")) in parsed:
        raise ValueError("normal slot must not overlap a quiz slot")
    if set(value.get("allowed_statuses", [])) != ALLOWED_STATUSES:
        raise ValueError("schedule allowed_statuses mismatch")
    if value.get("past_slot_policy") != "hold":
        raise ValueError("past slots must use hold policy")
    return value


def _parse_slot(value: str) -> time:
    try:
        return time.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid schedule slot: {value!r}") from exc


def eligibility(publish_at: str, now: datetime) -> str:
    target = datetime.fromisoformat(publish_at)
    if target.tzinfo is None or now.tzinfo is None:
        raise ValueError("publish_at and now must be timezone-aware")
    return "past_due_hold" if target < now else "scheduled"


def should_execute(queue: dict, now: datetime) -> bool:
    if queue.get("status") != "pending":
        return False
    if queue.get("execution_eligibility") != "scheduled":
        return False
    return datetime.fromisoformat(queue["publish_at"]) <= now
