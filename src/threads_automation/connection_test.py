from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .paths import REPO_ROOT
from .posting import PublicMediaResolver
from .preflight import run_preflight

PAYLOAD_PATH = REPO_ROOT / "data" / "test_payloads" / "threads-quiz.json"
CONFIG_PATH = REPO_ROOT / "config" / "api_test.json"


def _write_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_test_payload() -> dict:
    payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    if payload.get("content_id") != "META-TEST-THREADS-QUIZ":
        raise ValueError("Threads live test requires its dedicated content_id")
    if payload.get("parent_text") != "API接続テスト" or payload.get("reply_text") != "API接続テスト：返信確認":
        raise ValueError("Threads live test text mismatch")
    return payload


def execute_live_test(secrets, client, resolver: PublicMediaResolver,
                      preflight_transport=None, result_path: Path | None = None) -> dict:
    payload = load_test_payload()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    media_url = resolver.resolve(payload["question_image"])
    preflight = run_preflight(secrets, config["required_permissions"], [media_url], preflight_transport)
    parent_container_id = client.create_image_container(payload["parent_text"], media_url)
    parent_post_id = client.publish(parent_container_id)
    reply_container_id = client.create_text_container(payload["reply_text"], reply_to_id=parent_post_id)
    reply_post_id = client.publish(reply_container_id)
    result = {"content_id": payload["content_id"], "platform": "threads", "preflight": preflight,
              "parent_container_id": parent_container_id, "parent_post_id": parent_post_id,
              "reply_container_id": reply_container_id, "reply_post_id": reply_post_id,
              "completed_at": datetime.now(ZoneInfo("Asia/Tokyo")).isoformat()}
    target = result_path or (REPO_ROOT / config["result_path"])
    _write_atomic(target, result)
    return result
