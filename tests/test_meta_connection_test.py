import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from threads_automation.connection_test import execute_live_test
from threads_automation.meta_client import PostingError, ThreadsSecrets
from threads_automation.posting import PublicMediaResolver
from threads_automation.preflight import run_preflight


class FixtureClient:
    def __init__(self): self.calls = []
    def create_image_container(self, text, url): self.calls.append(("parent", text, url)); return "parent-container-id"
    def create_text_container(self, text, reply_to_id=None): self.calls.append(("reply", text, reply_to_id)); return "reply-container-id"
    def publish(self, creation_id):
        self.calls.append(("publish", creation_id))
        return "parent-post-id" if creation_id == "parent-container-id" else "reply-post-id"


def preflight_transport(url, fields):
    if url.endswith("/me"):
        return {"id": "threads-user-id", "username": "test"}
    return {"data": [
        {"permission": "threads_basic", "status": "granted"},
        {"permission": "threads_content_publish", "status": "granted"},
    ]}


class ThreadsConnectionTestTests(unittest.TestCase):
    def test_mock_live_test_saves_parent_and_reply_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            result = execute_live_test(
                ThreadsSecrets("secret-not-logged", "threads-user-id", "v1"), FixtureClient(),
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
                    else {"data": [{"permission": "threads_basic", "status": "granted"}]})
        with self.assertRaises(PostingError) as caught:
            run_preflight(ThreadsSecrets("token", "threads-user-id", "v1"),
                          ["threads_basic", "threads_content_publish"], [], missing_permissions)
        self.assertEqual(caught.exception.code, "MISSING_PERMISSION")

    def test_flag_is_required_and_production_queue_stays_pending(self):
        result = subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "run_meta_connection_test.py")],
                                check=True, capture_output=True, text=True)
        self.assertIn("DRY RUN ONLY", result.stdout)
        queues = [json.loads(path.read_text()) for path in (REPO_ROOT / "data" / "queue").glob("ENG-*.json")]
        production = [item for item in queues if item.get("platform") == "threads" and
                      item["content_id"] in {entry["content_id"] for entry in
                      json.loads((REPO_ROOT / "data" / "queue" / "final-schedule-2026-08-20.json").read_text())["items"]}]
        self.assertEqual(len(production), 49)
        self.assertTrue(all(item["status"] == "pending" and "remote_post_id" not in item for item in production))


if __name__ == "__main__":
    unittest.main()
