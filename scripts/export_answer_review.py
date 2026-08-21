#!/usr/bin/env python3
"""Export full parent/image/reply review text for every unposted production quiz."""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_DIR = REPO_ROOT / "data" / "queue"
OUTPUT = REPO_ROOT / "artifacts" / "review" / "threads-answers-2026-08-20.txt"


def main() -> int:
    blocks = []
    for number in range(6, 48):
        content_id = f"ENG-{number:06d}"
        queue = json.loads((QUEUE_DIR / f"{content_id}.json").read_text(encoding="utf-8"))
        if queue["status"] == "posted":
            continue
        blocks.append("\n".join([
            f"=== {content_id} | {queue['publish_at']} | {queue['status']} ===",
            f"親フック: {queue['parent_text']}",
            f"question image: {queue['question_image']}",
            "回答TEXT:",
            queue["answer_text"],
        ]))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    print(f"output={OUTPUT} quizzes={len(blocks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
