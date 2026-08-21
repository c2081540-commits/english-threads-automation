#!/usr/bin/env python3
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from threads_automation.meta_client import ThreadsMetaClient, ThreadsSecrets  # noqa: E402
from threads_automation.posting import (PublicMediaResolver, dry_run, post_one, recover_reply,
                                        select_one_due)  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Actually call Meta API; omitted means dry-run")
    parser.add_argument("--now", help="ISO 8601 override for deterministic dry-run")
    args = parser.parse_args()
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(ZoneInfo("Asia/Tokyo"))
    path = select_one_due(now)
    if path is None:
        print("NO_DUE_ITEM")
        return
    queue = json.loads(path.read_text(encoding="utf-8"))
    resolver = PublicMediaResolver() if args.live else PublicMediaResolver(checker=lambda _: True)
    is_reply_recovery = ((queue.get("status"), queue.get("parent_status"),
                          queue.get("answer_status")) == ("failed", "posted", "failed"))
    if not args.live:
        if is_reply_recovery:
            print(json.dumps(recover_reply(path, dry_run_only=True), ensure_ascii=False, indent=2))
        else:
            print(dry_run(queue, resolver))
        return
    client = ThreadsMetaClient(ThreadsSecrets.from_env())
    result = (recover_reply(path, client, dry_run_only=False, now=now)
              if is_reply_recovery else post_one(path, client, resolver, now))
    print(json.dumps({"content_id": result["content_id"], "status": result["status"],
                      "remote_post_id": result["remote_post_id"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
