from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from .content import validate_hook_guide

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "config" / "difficulty_levels.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def question_type(item: dict) -> str:
    if item.get("production_category") == "situation":
        return "situation"
    return "visual" if item.get("visual_required") else "text"


def validate_level(item: dict) -> None:
    if item.get("difficulty_level") not in load_config()["levels"]:
        raise ValueError(f"difficulty_level must be L1, L2, or L3: {item.get('content_id')}")


def allowed_hooks(item: dict) -> list[str]:
    validate_level(item)
    return load_config()["hook_pools"][item["difficulty_level"]][question_type(item)]


def validate_hook_for_item(item: dict, hook: str) -> None:
    if hook not in allowed_hooks(item):
        raise ValueError(f"hook is not allowed for difficulty/question type: {item.get('content_id')}")
    validate_hook_guide(hook, item.get("question_guide_ja"), item["visual_required"])


def choose_hook(item: dict, recently_used: list[str]) -> str:
    candidates = allowed_hooks(item)
    start = int(item["content_id"].split("-")[1]) % len(candidates)
    for offset in range(len(candidates)):
        candidate = candidates[(start + offset) % len(candidates)]
        if candidate in recently_used[-2:]:
            continue
        try:
            validate_hook_for_item(item, candidate)
        except ValueError:
            continue
        return candidate
    raise ValueError(f"no non-duplicating hook is available: {item['content_id']}")


def validate_distribution(items: list[dict], require_weekly_42: bool = True) -> dict:
    config = load_config()
    ordered = sorted(items, key=lambda item: item["publish_at"])
    by_day: dict[str, list[dict]] = defaultdict(list)
    for item in ordered:
        validate_level(item)
        by_day[item["publish_at"][:10]].append(item)
    daily = {}
    for day, entries in by_day.items():
        counts = Counter(item["difficulty_level"] for item in entries)
        if len(entries) == 6:
            for level, limits in config["daily"].items():
                if not limits["min"] <= counts[level] <= limits["max"]:
                    raise ValueError(f"daily difficulty distribution mismatch: {day} {dict(counts)}")
        run = 1
        for previous, current in zip(entries, entries[1:]):
            run = run + 1 if previous["difficulty_level"] == current["difficulty_level"] else 1
            if run > config["max_consecutive_same"]:
                raise ValueError(f"difficulty repeats too many times: {day}")
        daily[day] = dict(counts)
    weekly = Counter(item["difficulty_level"] for item in ordered)
    if require_weekly_42:
        if len(ordered) != 42:
            raise ValueError("weekly difficulty validation requires 42 quizzes")
        for level, limits in config["weekly_42"].items():
            if level == "most_common":
                continue
            if not limits["min"] <= weekly[level] <= limits["max"]:
                raise ValueError(f"weekly difficulty distribution mismatch: {dict(weekly)}")
        if weekly[config["weekly_42"]["most_common"]] != max(weekly.values()):
            raise ValueError("L2 must be the most common weekly difficulty")
    return {"daily": daily, "weekly": dict(weekly)}
