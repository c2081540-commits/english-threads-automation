from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from .meta_client import PostingError
from .paths import QUEUE_DIR, REPO_ROOT

MEDIA_CONFIG = REPO_ROOT / "config" / "media_public.json"
RECEIPT_DIR = REPO_ROOT / "data" / "receipts"


def _write_json_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


class PublicMediaResolver:
    def __init__(self, checker=None):
        config = json.loads(MEDIA_CONFIG.read_text(encoding="utf-8"))
        self.base_url = config["base_url"]
        self.require_https = config["require_https"]
        self.verify_remote = config["verify_remote_before_post"]
        self.checker = checker or self._head

    @staticmethod
    def _head(url: str) -> bool:
        try:
            request = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(request, timeout=15) as response:
                return 200 <= response.status < 400
        except (urllib.error.URLError, TimeoutError):
            return False

    def resolve(self, asset: str) -> str:
        resolved = (REPO_ROOT / asset).resolve()
        try:
            relative = resolved.relative_to(REPO_ROOT)
        except ValueError as exc:
            raise PostingError("BLOCKED_MEDIA_URL", "Media asset must be inside the repository") from exc
        if not resolved.is_file():
            raise PostingError("BLOCKED_MEDIA_URL", f"Media asset is missing: {relative.as_posix()}")
        url = urljoin(self.base_url, relative.as_posix())
        if self.require_https and urlparse(url).scheme != "https":
            raise PostingError("BLOCKED_MEDIA_URL", "Public media URL must use HTTPS")
        if self.verify_remote and not self.checker(url):
            raise PostingError("BLOCKED_MEDIA_URL", "Public media URL is not anonymously reachable")
        return url


def select_one_due(now: datetime, queue_dir: Path = QUEUE_DIR) -> Path | None:
    candidates = []
    for path in queue_dir.glob("ENG-*.json"):
        queue = json.loads(path.read_text(encoding="utf-8"))
        if (queue.get("platform") == "threads" and queue.get("status") == "pending" and
                queue.get("execution_eligibility") == "scheduled"):
            publish_at = datetime.fromisoformat(queue["publish_at"])
            if publish_at <= now:
                candidates.append((publish_at, queue["content_id"], path))
    return min(candidates)[2] if candidates else None


def dry_run(queue: dict, resolver: PublicMediaResolver) -> str:
    if queue["content_type"] == "normal":
        return (f"{queue['content_id']} | threads | {queue['publish_at']} | Normal | asset=none | "
                "text=yes | text container -> publish")
    asset = resolver.resolve(queue["question_image"])
    answer_asset = resolver.resolve(queue["answer_image"])
    return (f"{queue['content_id']} | threads | {queue['publish_at']} | image Quiz | asset={asset} | "
            f"answer_asset={answer_asset} | "
            "parent_text=yes | reply=yes | image parent container -> publish parent -> "
            "reply image container(reply_to_id) -> publish reply")


def post_one(queue_path: Path, client, resolver: PublicMediaResolver,
             now: datetime | None = None) -> dict:
    now = now or datetime.now(ZoneInfo("Asia/Tokyo"))
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    if queue.get("status") != "pending":
        raise PostingError("DUPLICATE_PREVENTED", "Only pending content may be posted")
    if queue.get("execution_eligibility") != "scheduled" or datetime.fromisoformat(queue["publish_at"]) > now:
        raise PostingError("NOT_DUE", "Queue item is not eligible and due")
    receipt_path = RECEIPT_DIR / f"threads-{queue['content_id']}.json"
    parent_receipt_path = RECEIPT_DIR / f"threads-{queue['content_id']}-parent.json"
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        queue.update(status="posted", remote_post_id=receipt["remote_post_id"], posted_at=receipt["posted_at"])
        _write_json_atomic(queue_path, queue)
        return queue
    try:
        if queue["content_type"] == "normal":
            container = client.create_text_container(queue["text"])
            remote_id = client.publish(container)
        else:
            image_url = resolver.resolve(queue["question_image"])
            answer_image_url = resolver.resolve(queue["answer_image"])
            if parent_receipt_path.is_file():
                parent_id = json.loads(parent_receipt_path.read_text(encoding="utf-8"))["remote_post_id"]
            else:
                try:
                    parent_container = client.create_image_container(queue["parent_text"], image_url)
                    parent_id = client.publish(parent_container)
                except PostingError as exc:
                    if exc.code in {"INVALID_TOKEN", "NETWORK_TIMEOUT", "MALFORMED_API_RESPONSE"}:
                        raise
                    raise PostingError("THREADS_PARENT_FAILURE", str(exc)) from exc
                _write_json_atomic(parent_receipt_path,
                                   {"content_id": queue["content_id"], "platform": "threads",
                                    "remote_post_id": parent_id, "stage": "parent_posted",
                                    "posted_at": now.isoformat()})
            queue.update(parent_status="posted", parent_post_id=parent_id)
            _write_json_atomic(queue_path, queue)
            try:
                reply_container = client.create_image_container(
                    queue["answer_text"], answer_image_url, reply_to_id=parent_id)
                reply_id = client.publish(reply_container)
            except PostingError as exc:
                queue.update(status="failed", answer_status="failed",
                             error={"code": "THREADS_REPLY_FAILURE", "reason": str(exc)[:200]})
                _write_json_atomic(queue_path, queue)
                raise PostingError("THREADS_REPLY_FAILURE", str(exc)) from exc
            queue.update(answer_status="posted", remote_reply_id=reply_id)
            remote_id = parent_id
        posted_at = now.isoformat()
        _write_json_atomic(receipt_path, {"content_id": queue["content_id"], "platform": "threads",
                                         "remote_post_id": remote_id, "posted_at": posted_at})
        queue.update(status="posted", remote_post_id=remote_id, posted_at=posted_at, error=None)
        _write_json_atomic(queue_path, queue)
        return queue
    except PostingError as exc:
        if queue.get("status") != "failed":
            if exc.code in {"INVALID_TOKEN", "NETWORK_TIMEOUT", "MALFORMED_API_RESPONSE", "BLOCKED_MEDIA_URL"}:
                code = exc.code
            else:
                code = "THREADS_PARENT_FAILURE" if queue.get("content_type") == "quiz" else exc.code
            queue.update(status="failed", error={"code": code, "reason": str(exc)[:200]})
            if queue.get("content_type") == "quiz":
                queue.update(parent_status="failed")
            _write_json_atomic(queue_path, queue)
        raise
