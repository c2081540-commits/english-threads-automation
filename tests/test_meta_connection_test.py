import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from threads_automation.connection_test import execute_live_test
from threads_automation.local_env import load_workspace_env
from threads_automation.meta_client import PostingError, ThreadsSecrets
from threads_automation.posting import PublicMediaResolver
from threads_automation.preflight import run_preflight


class FixtureClient:
    def __init__(self): self.calls = []
    def create_image_container(self, text, url, reply_to_id=None):
        self.calls.append(("image", text, url, reply_to_id))
        return "reply-container-id" if reply_to_id else "parent-container-id"
    def create_text_container(self, text, reply_to_id=None):
        self.calls.append(("text", text, reply_to_id))
        return "reply-container-id"
    def create_text_reply(self, text, reply_to_id):
        self.calls.append(("text_reply", text, reply_to_id))
        return "reply-container-id"
    def publish(self, creation_id):
        self.calls.append(("publish", creation_id))
        return "parent-post-id" if creation_id == "parent-container-id" else "reply-post-id"


def preflight_transport(url, fields):
    if url.endswith("/me"):
        return {"id": "threads-user-id", "username": "test"}
    return {"data": [{"quota_usage": 0, "config": {"quota_total": 250}}]}


class ThreadsConnectionTestTests(unittest.TestCase):
    def test_workspace_env_loader_does_not_override_process_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("THREADS_ACCESS_TOKEN=file-token\nTHREADS_USER_ID=file-user\n")
            previous = os.environ.get("THREADS_ACCESS_TOKEN")
            os.environ["THREADS_ACCESS_TOKEN"] = "process-token"
            os.environ.pop("THREADS_USER_ID", None)
            try:
                load_workspace_env(path)
                self.assertEqual(os.environ["THREADS_ACCESS_TOKEN"], "process-token")
                self.assertEqual(os.environ["THREADS_USER_ID"], "file-user")
            finally:
                if previous is None:
                    os.environ.pop("THREADS_ACCESS_TOKEN", None)
                else:
                    os.environ["THREADS_ACCESS_TOKEN"] = previous
                os.environ.pop("THREADS_USER_ID", None)

    def test_mock_live_test_saves_parent_and_reply_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            result = execute_live_test(
                ThreadsSecrets("secret-not-logged", "threads-user-id"), FixtureClient(),
                PublicMediaResolver(checker=lambda _: True), preflight_transport,
                Path(directory) / "result.json")
            self.assertEqual(result["parent_container_id"], "parent-container-id")
            self.assertEqual(result["parent_post_id"], "parent-post-id")
            self.assertEqual(result["reply_container_id"], "reply-container-id")
            self.assertEqual(result["reply_post_id"], "reply-post-id")
            self.assertNotIn("secret-not-logged", json.dumps(result))

    def test_missing_permission_fails_closed(self):
        def missing_permissions(url, fields):
            return ({"id": "threads-user-id"} if url.endswith("/me")
                    else {"error": "permission denied"})
        with self.assertRaises(PostingError) as caught:
            run_preflight(ThreadsSecrets("token", "threads-user-id"),
                          ["threads_basic", "threads_content_publish"], [], missing_permissions)
        self.assertEqual(caught.exception.code, "MISSING_PERMISSION")

    def test_preflight_uses_unversioned_threads_host(self):
        urls = []
        def transport(url, fields):
            urls.append(url)
            return ({"id": "threads-user-id"} if url.endswith("/me") else
                    {"data": [{"quota_usage": 0}]})
        run_preflight(ThreadsSecrets("token", "threads-user-id"), ["threads_basic"], [], transport)
        self.assertEqual(urls, ["https://graph.threads.net/me",
                                "https://graph.threads.net/me/threads_publishing_limit"])

    def test_flag_is_required_and_production_queue_stays_unchanged(self):
        result = subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "run_meta_connection_test.py")],
                                check=True, capture_output=True, text=True)
        self.assertIn("DRY RUN ONLY", result.stdout)
        queues = [json.loads(path.read_text()) for path in (REPO_ROOT / "data" / "queue").glob("ENG-*.json")]
        production = [item for item in queues if item.get("platform") == "threads" and
                      item["content_id"] in {entry["content_id"] for entry in
                      json.loads((REPO_ROOT / "data" / "queue" / "final-schedule-2026-08-20.json").read_text())["items"]}]
        schedule_ids = {entry["content_id"] for entry in json.loads(
            (REPO_ROOT / "data" / "queue" / "final-schedule-2026-08-20.json").read_text())["items"]}
        self.assertEqual({item["content_id"] for item in production}, schedule_ids)
        posted = [item for item in production if item["status"] == "posted"]
        self.assertTrue(all(item.get("remote_post_id") and item.get("posted_at") for item in posted))
        self.assertTrue(all(item["status"] == "pending" and "remote_post_id" not in item
                            for item in production if item["status"] not in {"posted", "failed", "skipped"}))
        failed = [item for item in production if item["content_id"] == "ENG-000016"]
        self.assertTrue(all((item["status"], item["parent_status"], item["answer_status"]) ==
                            ("failed", "posted", "failed") for item in failed))


if __name__ == "__main__":
    unittest.main()
