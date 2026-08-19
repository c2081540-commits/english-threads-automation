import json
from pathlib import Path

from .paths import IMAGE_DIR, QUEUE_DIR, require_file
from .validation import validate


def build_queue(master_path: Path) -> dict:
    source = require_file(master_path)
    try:
        content = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {source}: {exc}") from exc
    if not isinstance(content, dict):
        raise ValueError("Master JSON root must be an object")
    validate(content)
    content_id = content["content_id"]
    parent_id = f"{content_id}-parent"
    return {
        "content_id": content_id,
        "publish_at": content["publish_at"],
        "status": "pending",
        "posts": [
            {
                "queue_id": parent_id,
                "order": 1,
                "type": "parent",
                "reply_to": None,
                "image_path": str(IMAGE_DIR / f"{content_id}-question.png"),
                "text": content["threads_parent_text"],
                "status": "pending",
            },
            {
                "queue_id": f"{content_id}-answer",
                "order": 2,
                "type": "answer_reply",
                "reply_to": parent_id,
                "image_path": None,
                "text": content["threads_answer_text"],
                "status": "pending",
            },
        ],
    }


def write_queue(master_path: Path) -> Path:
    queue = build_queue(master_path)
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    target = QUEUE_DIR / f"{queue['content_id']}.json"
    target.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target
