#!/usr/bin/env python3
"""Explicit reply-only recovery entry point; dry-run unless --live-recovery is supplied."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from threads_automation.meta_client import ThreadsMetaClient, ThreadsSecrets  # noqa: E402
from threads_automation.local_env import load_workspace_env  # noqa: E402
from threads_automation.posting import QUEUE_DIR, recover_reply  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("content_id")
    parser.add_argument("--live-recovery", action="store_true",
                        help="Publish only an existing reply container using saved receipts")
    args = parser.parse_args()
    queue_path = QUEUE_DIR / f"{args.content_id}.json"
    if not queue_path.is_file():
        parser.error("queue does not exist")
    if not args.live_recovery:
        print(json.dumps(recover_reply(queue_path, dry_run_only=True),
                         ensure_ascii=False, indent=2))
        return 0
    load_workspace_env()
    result = recover_reply(queue_path,
                           ThreadsMetaClient(ThreadsSecrets.from_env()),
                           dry_run_only=False)
    print(json.dumps({"content_id": result["content_id"], "status": result["status"],
                      "parent_post_id": result["parent_post_id"],
                      "remote_reply_id": result["remote_reply_id"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
