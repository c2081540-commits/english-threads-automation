#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from threads_automation.connection_test import execute_live_test, load_test_payload  # noqa: E402
from threads_automation.local_env import load_workspace_env  # noqa: E402
from threads_automation.meta_client import ThreadsMetaClient, ThreadsSecrets  # noqa: E402
from threads_automation.posting import PublicMediaResolver  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-test", action="store_true", help="Post the dedicated API test fixture")
    args = parser.parse_args()
    if not args.live_test:
        payload = load_test_payload()
        print(f"DRY RUN ONLY | {payload['content_id']} | add --live-test to perform the isolated test post")
        return
    load_workspace_env()
    secrets = ThreadsSecrets.from_env()
    result = execute_live_test(secrets, ThreadsMetaClient(secrets), PublicMediaResolver())
    print(json.dumps({"content_id": result["content_id"], "parent_post_id": result["parent_post_id"],
                      "reply_post_id": result["reply_post_id"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
