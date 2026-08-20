import json
from pathlib import Path

from .content import (build_answer_text, load_normal_master, load_quiz_master,
                      question_image_path, select_hook)
from .paths import QUEUE_DIR


def build_quiz_queue(content_id: str) -> dict:
    content = load_quiz_master(content_id)
    _, image_path = question_image_path(content_id, allow_waiting=content["visual_required"] is True)
    waiting = content["visual_required"] is True and image_path is None
    return {
        "content_id": content_id,
        "content_type": "quiz",
        "parent_text": select_hook(content["category"], content_id),
        "question_image": image_path,
        "answer_text": build_answer_text(content),
        "publish_at": content["publish_at"],
        "parent_status": "WAITING_FOR_VISUAL" if waiting else "pending",
        "answer_status": "WAITING_FOR_PARENT" if waiting else "pending",
        "parent_post_id": None,
    }


def build_normal_queue(content_id: str) -> dict:
    content = load_normal_master(content_id)
    return {
        "content_id": content_id,
        "content_type": "normal",
        "text": content["threads_text"],
        "publish_at": content["publish_at"],
        "status": "pending",
    }


def build_content_queue(content_id: str, content_type: str) -> dict:
    if content_type == "quiz":
        return build_quiz_queue(content_id)
    if content_type == "normal":
        return build_normal_queue(content_id)
    raise ValueError("content_type must be quiz or normal")


def write_content_queue(content_id: str, content_type: str) -> Path:
    queue = build_content_queue(content_id, content_type)
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    target = QUEUE_DIR / f"{content_id}.json"
    target.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def format_dry_run(queue: dict) -> str:
    if queue.get("content_type") == "quiz":
        return "\n".join([
            f"DRY RUN Threads quiz | {queue['content_id']} | {queue['publish_at']}",
            f"status: {queue['parent_status']}",
            f"parent: {queue['parent_text']}",
            f"image: {queue['question_image']}",
            "answer:",
            queue["answer_text"],
        ])
    if queue.get("content_type") == "normal":
        return "\n".join([
            f"DRY RUN Threads normal | {queue['content_id']} | {queue['publish_at']}",
            queue["text"],
        ])
    raise ValueError("queue content_type must be quiz or normal")
