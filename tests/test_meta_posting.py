import json
import os
import sys
import tempfile
import unittest
import urllib.error
from io import BytesIO
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import threads_automation.posting as posting
from threads_automation.meta_client import (HttpTransport, PostingError, ThreadsMetaClient,
                                             ThreadsSecrets)


class FakeThreadsClient:
    def __init__(self, fail_publish_number=None, fail_reply=False):
        self.calls = []
        self.publish_count = 0
        self.fail_publish_number = fail_publish_number
        self.fail_reply = fail_reply

    def create_image_container(self, text, url, reply_to_id=None):
        self.calls.append(("image_reply" if reply_to_id else "image_parent", text, url, reply_to_id))
        return "reply-container" if reply_to_id else "parent-container"

    def create_text_container(self, text, reply_to_id=None):
        self.calls.append(("text", text, reply_to_id))
        return "reply-container" if reply_to_id else "normal-container"

    def create_text_reply(self, text, reply_to_id):
        self.calls.append(("text_reply", text, reply_to_id))
        if self.fail_reply:
            raise PostingError("THREADS_REPLY_FAILURE", "mock reply failure")
        return "reply-container"

    def container_status(self, creation_id):
        self.calls.append(("status", creation_id))
        return "FINISHED"

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
        queue["status"] = "pending"
        queue["parent_status"] = "pending"
        queue["answer_status"] = "pending"
        queue["parent_post_id"] = None
        for field in ("remote_post_id", "remote_reply_id", "posted_at", "error"):
            queue.pop(field, None)
        target = self.root / f"{content_id}.json"
        target.write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
        return target

    def test_quiz_parent_and_reply_success(self):
        target = self.queue_copy("ENG-000009")
        client = FakeThreadsClient()
        result = posting.post_one(target, client, self.resolver, datetime.fromisoformat("2026-08-20T16:00:00+09:00"))
        self.assertEqual([call[0] for call in client.calls], ["image_parent", "publish", "text_reply", "publish"])
        reply_call = client.calls[2]
        self.assertIn("💡 正解は A. by Friday", reply_call[1])
        self.assertEqual(reply_call[2], "parent-id")
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
        container_receipt = json.loads((self.root / "receipts" /
                                        "threads-ENG-000009-reply-container.json").read_text())
        self.assertEqual(container_receipt["reply_container_id"], "reply-container")
        self.assertEqual(container_receipt["parent_post_id"], "parent-id")

    def test_parent_receipt_resumes_at_reply_without_duplicate_parent(self):
        target = self.queue_copy("ENG-000009")
        receipt = self.root / "receipts" / "threads-ENG-000009-parent.json"
        receipt.parent.mkdir(parents=True)
        receipt.write_text(json.dumps({"remote_post_id": "existing-parent-id"}), encoding="utf-8")
        client = FakeThreadsClient()
        result = posting.post_one(target, client, self.resolver,
                                  datetime.fromisoformat("2026-08-20T16:00:00+09:00"))
        self.assertEqual([call[0] for call in client.calls], ["text_reply", "publish"])
        self.assertEqual(result["parent_post_id"], "existing-parent-id")

    def test_reply_only_recovery_reuses_parent_and_never_creates_parent(self):
        source = json.loads((REPO_ROOT / "data" / "queue" / "ENG-000017.json").read_text())
        source.update(status="failed", parent_status="posted", answer_status="failed",
                      error={"meta": {"payload": {"creation_id": "18096439436062590"}}})
        for field in ("remote_post_id", "remote_reply_id", "posted_at", "reply_recovery_attempts"):
            source.pop(field, None)
        target = self.root / "ENG-000017.json"
        target.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
        receipt = self.root / "receipts" / "threads-ENG-000017-parent.json"
        receipt.parent.mkdir(parents=True)
        receipt.write_text(json.dumps({"remote_post_id": source["parent_post_id"]}), encoding="utf-8")
        plan = posting.recover_reply(target, dry_run_only=True)
        self.assertEqual(plan["parent_action"], "reuse_only")
        client = FakeThreadsClient()
        result = posting.recover_reply(target, client, dry_run_only=False,
                                       now=datetime.fromisoformat("2026-08-21T19:00:00+09:00"))
        self.assertEqual([call[0] for call in client.calls], ["status", "publish"])
        self.assertEqual(plan["reply_container_id"], "18096439436062590")
        self.assertEqual(plan["container_action"], "reuse_only")
        self.assertEqual(plan["publish_endpoint"], "https://graph.threads.net/me/threads_publish")
        self.assertEqual(plan["response_id_type"], "reply_media_container_id")
        self.assertEqual(result["parent_post_id"], source["parent_post_id"])
        self.assertEqual(result["status"], "posted")

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
        self.assertIn("wait FINISHED -> publish reply", text)
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
            if content_id == "ENG-000009":
                queue["status"] = "pending"
                queue["parent_status"] = "pending"
                queue["answer_status"] = "pending"
                queue["parent_post_id"] = None
                for field in ("remote_post_id", "remote_reply_id", "posted_at"):
                    queue.pop(field, None)
            (queue_dir / f"{content_id}.json").write_text(json.dumps(queue), encoding="utf-8")
        self.assertIsNone(posting.select_one_due(datetime.fromisoformat("2026-08-20T14:00:00+09:00"), queue_dir))
        self.assertEqual(posting.select_one_due(datetime.fromisoformat("2026-08-20T16:00:00+09:00"), queue_dir).stem,
                         "ENG-000009")

    def test_malformed_queue_placeholder_and_answer_image_fail_closed(self):
        queue = json.loads(self.queue_copy("ENG-000009").read_text())
        queue["answer_image"] = "assets/answer.png"
        with self.assertRaises(PostingError):
            posting.validate_queue_for_post(queue)
        with self.assertRaises(PostingError) as caught:
            self.resolver.resolve("assets/question_images/ice-cream-placeholder.png")
        self.assertEqual(caught.exception.code, "BLOCKED_MEDIA_URL")

    def test_token_not_logged(self):
        token = "super-secret-token"
        client = ThreadsMetaClient(ThreadsSecrets(token, "user"),
                                   transport=lambda *_: (_ for _ in ()).throw(PostingError("INVALID_TOKEN", "invalid token")))
        with self.assertRaises(PostingError) as caught:
            client.publish("container")
        self.assertNotIn(token, str(caught.exception))

    def test_threads_client_uses_unversioned_threads_host(self):
        calls = []
        client = ThreadsMetaClient(ThreadsSecrets("token", "user"),
                                   transport=lambda url, fields: calls.append((url, fields)) or {"id": "container"})
        client.create_text_container("test")
        reply_id = client.create_text_reply("reply", "parent-post-id")
        self.assertEqual(reply_id, "container")
        self.assertEqual([call[0] for call in calls], ["https://graph.threads.net/me/threads"] * 2)
        self.assertEqual(calls[1][1], {"media_type": "TEXT", "text": "reply",
                                      "reply_to_id": "parent-post-id", "access_token": "token"})

    def test_publish_waits_for_finished_container(self):
        class StatusTransport:
            def __init__(self):
                self.statuses = iter(("IN_PROGRESS", "FINISHED"))
                self.calls = []
            def get(inner_self, url, fields):
                inner_self.calls.append(("get", url, fields))
                return {"id": "reply-container", "status": next(inner_self.statuses)}
            def __call__(inner_self, url, fields):
                inner_self.calls.append(("post", url, fields))
                return {"id": "published-reply"}
        transport = StatusTransport()
        client = ThreadsMetaClient(ThreadsSecrets("token", "user"), transport=transport)
        with patch("threads_automation.meta_client.time.sleep"):
            self.assertEqual(client.publish("reply-container"), "published-reply")
        self.assertEqual([call[0] for call in transport.calls], ["get", "get", "post"])
        self.assertEqual(transport.calls[-1][1], "https://graph.threads.net/me/threads_publish")

    def test_http_400_preserves_masked_meta_error_details(self):
        body = json.dumps({"error": {"message": "Invalid reply target", "type": "OAuthException",
                                     "code": 100, "error_subcode": 33,
                                     "fbtrace_id": "safe-trace"}}).encode()
        error = urllib.error.HTTPError("https://graph.threads.net/me/threads", 400,
                                      "Bad Request", {}, BytesIO(body))
        with patch("urllib.request.urlopen", side_effect=error), self.assertRaises(PostingError) as caught:
            HttpTransport(retries=0)("https://graph.threads.net/me/threads",
                                     {"media_type": "TEXT", "text": "reply",
                                      "reply_to_id": "parent", "access_token": "secret-token"})
        details = caught.exception.details
        self.assertEqual((details["http_status"], details["message"], details["type"],
                          details["code"], details["subcode"], details["fbtrace_id"]),
                         (400, "Invalid reply target", "OAuthException", 100, 33, "safe-trace"))
        self.assertNotIn("access_token", details["payload"])
        self.assertNotIn("secret-token", str(caught.exception))
        self.assertNotIn("secret-token", json.dumps(details))


if __name__ == "__main__":
    unittest.main()
