from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from .content import validate_hook_guide

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "config" / "difficulty_levels.json"
HOOK_POLICY_PATH = REPO_ROOT / "config" / "thread_hook_policy.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_hook_policy() -> dict:
    return json.loads(HOOK_POLICY_PATH.read_text(encoding="utf-8"))


def question_type(item: dict) -> str:
    if item.get("production_category") == "situation":
        return "situation"
    return "visual" if item.get("visual_required") else "text"


def validate_level(item: dict) -> None:
    if item.get("difficulty_level") not in load_config()["levels"]:
        raise ValueError(f"difficulty_level must be L1, L2, or L3: {item.get('content_id')}")


def allowed_hooks(item: dict) -> list[str]:
    validate_level(item)
    kind = question_type(item)
    learning_point = item.get("learning_point", "")
    if kind == "situation":
        topic_kind = "situation"
    elif kind == "visual":
        topic_kind = "visual"
    elif "と" in learning_point or "使い分け" in learning_point:
        topic_kind = "contrast"
    else:
        topic_kind = "form"
    policy = load_hook_policy()
    patterns = policy["generation_patterns"][item["difficulty_level"]][kind]
    return [pattern.format(topic=topic) for pattern in patterns
            for topic in policy["topic_options"][topic_kind]]


def validate_hook_for_item(item: dict, hook: str) -> None:
    validate_level(item)
    policy = load_hook_policy()
    if not isinstance(hook, str) or not hook.strip() or len(hook) > policy["max_length"]:
        raise ValueError(f"invalid hook length: {item.get('content_id')}")
    if any(term in hook for term in policy["instruction_style_substrings"]):
        raise ValueError(f"instruction-style hook is prohibited: {item.get('content_id')}")
    kind = question_type(item)
    learning_point = item.get("learning_point", "")
    for constraint in policy["content_constraints"]:
        if not any(term in hook for term in constraint["hook_terms"]):
            continue
        if "question_types" in constraint and kind not in constraint["question_types"]:
            raise ValueError(f"hook/question type mismatch: {item.get('content_id')}")
        if "learning_point_terms" in constraint and not any(
                term in learning_point for term in constraint["learning_point_terms"]):
            raise ValueError(f"hook/learning point mismatch: {item.get('content_id')}")
    answer_values = [item.get("best_answer", ""), *item.get("acceptable_answers", [])]
    normalized_hook = re.sub(r"\s+", "", hook).casefold()
    for answer in answer_values:
        normalized_answer = re.sub(r"\s+", "", str(answer)).casefold().strip(".!?")
        if len(normalized_answer) >= 3 and normalized_answer in normalized_hook:
            raise ValueError(f"hook reveals the answer: {item.get('content_id')}")
    validate_hook_guide(hook, item.get("question_guide_ja"), item["visual_required"])


def _normalized_hook(value: str) -> str:
    return re.sub(r"[\W_]+", "", value.casefold())


def validate_hook_sequence(items: list[dict]) -> None:
    policy = load_hook_policy()
    ordered = sorted(items, key=lambda item: item["publish_at"])
    for index, item in enumerate(ordered):
        hook = item["threads_parent_text"]
        validate_hook_for_item(item, hook)
        recent = ordered[max(0, index - policy["exact_duplicate_window"]):index]
        if any(previous["threads_parent_text"] == hook for previous in recent):
            raise ValueError(f"exact hook duplicate within 20: {item['content_id']}")
        same_day_previous = [previous for previous in recent
                             if previous["publish_at"][:10] == item["publish_at"][:10]]
        normalized = _normalized_hook(hook)
        for previous in same_day_previous:
            ratio = SequenceMatcher(None, _normalized_hook(previous["threads_parent_text"]),
                                    normalized).ratio()
            if ratio >= policy["similar_same_day_threshold"]:
                raise ValueError(f"similar hook on same day: {item['content_id']}")


def choose_hook(item: dict, recently_used: list[str]) -> str:
    candidates = allowed_hooks(item)
    start = int(item["content_id"].split("-")[1]) % len(candidates)
    for offset in range(len(candidates)):
        candidate = candidates[(start + offset) % len(candidates)]
        if candidate in recently_used[-load_hook_policy()["exact_duplicate_window"]:]:
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
