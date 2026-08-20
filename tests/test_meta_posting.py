import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import threads_automation.posting as posting
from threads_automation.meta_client import (PostingError, ThreadsMetaClient,
                                             ThreadsSecrets)


class FakeThreadsClient:
    def __init__(self, fail_publish_number=None):
        self.calls = []
        self.publish_count = 0
        self.fail_publish_number = fail_publish_number

    def create_image_container(self, text, url):
        self.calls.append(("image_parent", text, url))
        return "parent-container"

    def create_text_container(self, text, reply_to_id=None):
        self.calls.append(("text", text, reply_to_id))
        return "reply-container" if reply_to_id else "normal-container"

    def publish(self, creation_id):
        self.publish_count += 1
        self.calls.append(("publish", creation_id))
        if self.publish_count == self.fail_publish_number:
            raise PostingError("PUBLISH_FAILURE", "mock publish failure")
        return "parent-id" if self.publish_count == 1 else "reply-id"


class ThreadsMetaPostingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.receipt_patch = patch.object(posting, "RECEIPT_DIR", self.root / "receipts")
        self.receipt_patch.start()
        self.resolver = posting.PublicMediaResolver(checker=lambda _: True)

    def tearDown(self):
        self.receipt_patch.stop()
        self.temporary.cleanup()

    def queue_copy(self, content_id):
        queue = json.loads((REPO_ROOT / "data" / "queue" / f"{content_id}.json").read_text(encoding="utf-8"))
        queue["execution_eligibility"] = "scheduled"
        target = self.root / f"{content_id}.json"
        target.write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
        return target

    def test_quiz_parent_and_reply_success(self):
        target = self.queue_copy("ENG-000009")
        client = FakeThreadsClient()
        result = posting.post_one(target, client, self.resolver, datetime.fromisoformat("2026-08-20T16:00:00+09:00"))
        self.assertEqual([call[0] for call in client.calls], ["image_parent", "publish", "text", "publish"])
        self.assertEqual(result["status"], "posted")
        self.assertEqual(result["parent_post_id"], "parent-id")
        self.assertEqual(result["remote_reply_id"], "reply-id")
        with self.assertRaises(PostingError):
            posting.post_one(target, client, self.resolver, datetime.fromisoformat("2026-08-20T16:00:00+09:00"))
        self.assertEqual(len(client.calls), 4)

    def test_parent_failure_is_recorded(self):
        target = self.queue_copy("ENG-000009")
        with self.assertRaises(PostingError) as caught:
            posting.post_one(target, FakeThreadsClient(fail_publish_number=1), self.resolver,
                             datetime.fromisoformat("2026-08-20T16:00:00+09:00"))
        self.assertEqual(caught.exception.code, "THREADS_PARENT_FAILURE")
        saved = json.loads(target.read_text())
        self.assertEqual((saved["status"], saved["parent_status"]), ("failed", "failed"))

    def test_reply_failure_preserves_posted_parent(self):
        target = self.queue_copy("ENG-000009")
        with self.assertRaises(PostingError) as caught:
            posting.post_one(target, FakeThreadsClient(fail_publish_number=2), self.resolver,
                             datetime.fromisoformat("2026-08-20T16:00:00+09:00"))
        self.assertEqual(caught.exception.code, "THREADS_REPLY_FAILURE")
        saved = json.loads(target.read_text())
        self.assertEqual(saved["parent_status"], "posted")
        self.assertEqual(saved["answer_status"], "failed")
        self.assertEqual(saved["parent_post_id"], "parent-id")

    def test_parent_receipt_resumes_at_reply_without_duplicate_parent(self):
        target = self.queue_copy("ENG-000009")
        receipt = self.root / "receipts" / "threads-ENG-000009-parent.json"
        receipt.parent.mkdir(parents=True)
        receipt.write_text(json.dumps({"remote_post_id": "existing-parent-id"}), encoding="utf-8")
        client = FakeThreadsClient()
        result = posting.post_one(target, client, self.resolver,
                                  datetime.fromisoformat("2026-08-20T16:00:00+09:00"))
        self.assertEqual([call[0] for call in client.calls], ["text", "publish"])
        self.assertEqual(result["parent_post_id"], "existing-parent-id")

    def test_normal_success(self):
        target = self.queue_copy("ENG-100002")
        result = posting.post_one(target, FakeThreadsClient(), self.resolver,
                                  datetime.fromisoformat("2026-08-21T00:00:00+09:00"))
        self.assertEqual(result["status"], "posted")

    def test_dry_run_covers_image_parent_reply_and_normal(self):
        quiz = json.loads(self.queue_copy("ENG-000009").read_text())
        normal = json.loads(self.queue_copy("ENG-100002").read_text())
        text = posting.dry_run(quiz, self.resolver)
        self.assertIn("publish parent", text)
        self.assertIn("reply text container(reply_to_id)", text)
        self.assertIn("text container -> publish", posting.dry_run(normal, self.resolver))

    def test_missing_secret_media_and_due_exclusions(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(PostingError) as caught:
            ThreadsSecrets.from_env()
        self.assertEqual(caught.exception.code, "MISSING_SECRET")
        with self.assertRaises(PostingError) as caught:
            posting.PublicMediaResolver(checker=lambda _: False).resolve("assets/question_images/ENG-000009-question.png")
        self.assertEqual(caught.exception.code, "BLOCKED_MEDIA_URL")
        queue_dir = self.root / "queue"
        queue_dir.mkdir()
        for content_id in ("ENG-000006", "ENG-000009"):
            queue = json.loads((REPO_ROOT / "data" / "queue" / f"{content_id}.json").read_text())
            (queue_dir / f"{content_id}.json").write_text(json.dumps(queue), encoding="utf-8")
        self.assertIsNone(posting.select_one_due(datetime.fromisoformat("2026-08-20T14:00:00+09:00"), queue_dir))
        self.assertEqual(posting.select_one_due(datetime.fromisoformat("2026-08-20T16:00:00+09:00"), queue_dir).stem,
                         "ENG-000009")

    def test_token_not_logged(self):
        token = "super-secret-token"
        client = ThreadsMetaClient(ThreadsSecrets(token, "user", "v1"),
                                   transport=lambda *_: (_ for _ in ()).throw(PostingError("INVALID_TOKEN", "invalid token")))
        with self.assertRaises(PostingError) as caught:
            client.publish("container")
        self.assertNotIn(token, str(caught.exception))


if __name__ == "__main__":
    unittest.main()
