from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from .paths import (HOOK_CONFIG_PATH, INSTAGRAM_MASTER_DIR, NORMAL_MASTER_DIR,
                    QUESTION_IMAGE_DIR, QUIZ_MASTER_DIR, REPO_ROOT,
                    require_direct_file)
from .validation import validate as validate_quiz_master

CONTENT_ID = re.compile(r"^ENG-\d{6}$")
FORBIDDEN_HOOKS = (
    re.compile(r"みんな.*間違"),
    re.compile(r"日本人の\s*\d+%"),
    re.compile(r"正答率\s*\d+%"),
    re.compile(r"ほとんどの人.*間違"),
    re.compile(r"ネイティブしか分からない"),
)
COMMON_FIELDS = ("content_id", "question", "choices", "best_answer", "answer_type")
NORMAL_FIELDS = {"content_id", "content_type", "theme", "threads_text",
                 "story_headline", "story_body", "publish_at"}


def _read_json(path: Path, expected_dir: Path, label: str) -> dict:
    source = require_direct_file(path, expected_dir, label)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {source}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} JSON root must be an object")
    return value


def load_quiz_master(content_id: str) -> dict:
    local = _read_json(QUIZ_MASTER_DIR / f"{content_id}.json", QUIZ_MASTER_DIR, "quiz master")
    validate_quiz_master(local)
    instagram = _read_json(INSTAGRAM_MASTER_DIR / f"{content_id}.json", INSTAGRAM_MASTER_DIR,
                           "Instagram master")
    validate_common_content(local, instagram)
    return local


def validate_common_content(local: dict, instagram: dict) -> None:
    for field in COMMON_FIELDS:
        if local.get(field) != instagram.get(field):
            raise ValueError(f"Instagram/Threads {field} mismatch")


def validate_hook(hook: str) -> None:
    if not isinstance(hook, str) or not hook.strip() or len(hook) > 80:
        raise ValueError("quiz hook must be a non-empty string of at most 80 characters")
    if any(pattern.search(hook) for pattern in FORBIDDEN_HOOKS):
        raise ValueError("quiz hook contains prohibited unsupported social proof")


def select_hook(category: str, content_id: str) -> str:
    config = _read_json(HOOK_CONFIG_PATH, HOOK_CONFIG_PATH.parent, "hook config")
    candidates = config.get(category)
    if not isinstance(candidates, list) or not candidates:
        raise ValueError(f"No hook candidates configured for category: {category}")
    for candidate in candidates:
        validate_hook(candidate)
    number = int(content_id.split("-")[1])
    return candidates[number % len(candidates)]


def question_image_path(content_id: str, allow_waiting: bool = False) -> tuple[Path | None, str | None]:
    path = QUESTION_IMAGE_DIR / f"{content_id}-question.png"
    if allow_waiting and not path.is_file():
        return None, None
    source = require_direct_file(path, QUESTION_IMAGE_DIR, "question image")
    return source, source.relative_to(REPO_ROOT).as_posix()


def choice_answer(content: dict) -> str:
    try:
        index = content["choices"].index(content["best_answer"])
    except (KeyError, ValueError):
        raise ValueError("best_answer must exactly match one choice")
    if index >= 26:
        raise ValueError("choice index exceeds supported labels")
    return f"{chr(ord('A') + index)}. {content['best_answer']}"


def build_answer_text(content: dict) -> str:
    parts = [f"💡 {content['answer_hint']}", f"✅ 正解は {choice_answer(content)}"]
    category = content["category"]
    if category == "grammar":
        parts.append(content["explanation"])
        if content.get("examples") and content.get("example_translations"):
            parts.append(f"{content['examples'][0]}\n＝{content['example_translations'][0]}")
        if content.get("key_difference"):
            parts.append(content["key_difference"])
    elif category == "vocabulary":
        parts.append(content["explanation"])
        if content.get("examples") and content.get("example_translations"):
            parts.append(f"{content['examples'][0]}\n＝{content['example_translations'][0]}")
        if content.get("key_difference"):
            parts.append(content["key_difference"])
    elif category == "situation":
        if content.get("also_natural"):
            parts.append(f"{content['also_natural']}\nでも自然です。")
        if content.get("explanation"):
            parts.append(content["explanation"])
    else:
        raise ValueError(f"Unsupported quiz category: {category}")
    text = "\n\n".join(parts)
    if len(text) > 500:
        raise ValueError("Threads answer text exceeds 500 characters")
    return text


def load_normal_master(content_id: str) -> dict:
    content = _read_json(NORMAL_MASTER_DIR / f"{content_id}.json", NORMAL_MASTER_DIR, "normal master")
    missing = sorted(NORMAL_FIELDS - content.keys())
    if missing:
        raise ValueError(f"missing normal fields: {', '.join(missing)}")
    if not isinstance(content["content_id"], str) or not CONTENT_ID.fullmatch(content["content_id"]):
        raise ValueError("normal content_id must match ENG-000001")
    if content["content_type"] != "normal":
        raise ValueError("normal content_type must be normal")
    for field, limit in (("theme", 80), ("threads_text", 500),
                         ("story_headline", 80), ("story_body", 240)):
        value = content[field]
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError(f"{field} must be a non-empty string of at most {limit} characters")
    try:
        parsed = datetime.fromisoformat(content["publish_at"])
        if parsed.tzinfo is None:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("publish_at must be an ISO 8601 datetime with timezone")
    return content
