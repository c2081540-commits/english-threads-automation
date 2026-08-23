import json
import copy
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from threads_automation.content import (build_answer_text, choice_answer,
                                        validate_hook_guide)  # noqa: E402


class TextOnlyReplyTests(unittest.TestCase):
    def test_all_sources_use_enriched_validated_text_only_replies(self):
        for number in range(6, 48):
            content_id = f"ENG-{number:06d}"
            master = json.loads((REPO_ROOT / "data" / "master" / "quiz" /
                                 f"{content_id}.json").read_text(encoding="utf-8"))
            queue = json.loads((REPO_ROOT / "data" / "queue" /
                                f"{content_id}.json").read_text(encoding="utf-8"))
            self.assertNotIn("answer_image", queue)
            answer = build_answer_text(master)
            self.assertEqual(answer.splitlines()[0], f"💡 正解は {choice_answer(master)}")
            self.assertLessEqual(len(answer), 320)
            self.assertLessEqual(len([line for line in answer.splitlines() if line.strip()]), 5)
            self.assertIn("「", answer)
            self.assertNotIn(master["question"], answer)
            if queue["status"] != "posted":
                self.assertEqual(queue["answer_text"], answer)

    def test_current_reply_quality_fields_not_emoji_are_required(self):
        for number in range(6, 48):
            master = json.loads((REPO_ROOT / "data" / "master" / "quiz" /
                                 f"ENG-{number:06d}.json").read_text(encoding="utf-8"))
            queue = json.loads((REPO_ROOT / "data" / "queue" /
                                f"ENG-{number:06d}.json").read_text(encoding="utf-8"))
            if not master.get("learning_point"):
                self.assertEqual(queue["status"], "posted")
                continue
            text = master["threads_answer_text"]
            self.assertIn(master["best_answer"], text)
            self.assertTrue(master["explanation"].strip())
            self.assertTrue(master["examples"])
            self.assertTrue(master["example_translations"])
            self.assertTrue(master["learning_point"].strip())

    def test_posted_queue_and_receipts_remain_authoritative(self):
        for content_id in ("ENG-000009", "ENG-000012", "ENG-000013"):
            queue = json.loads((REPO_ROOT / "data" / "queue" / f"{content_id}.json").read_text())
            self.assertEqual(queue["status"], "posted")
            self.assertTrue(queue["remote_post_id"])
            self.assertTrue(queue["remote_reply_id"])
            self.assertTrue(queue["posted_at"])
            self.assertTrue((REPO_ROOT / "data" / "receipts" /
                             f"threads-{content_id}.json").is_file())

    def test_enriched_answer_validation_fails_closed(self):
        source = json.loads((REPO_ROOT / "data" / "master" / "quiz" /
                             "ENG-000013.json").read_text(encoding="utf-8"))
        bad_letter = copy.deepcopy(source)
        bad_letter["threads_answer_text"] = bad_letter["threads_answer_text"].replace(
            "💡 正解は B. was", "💡 正解は A. was")
        with self.assertRaisesRegex(ValueError, "letter or answer"):
            build_answer_text(bad_letter)
        repeated_question = copy.deepcopy(source)
        repeated_question["threads_answer_text"] += "\n" + source["question"]
        with self.assertRaises(ValueError):
            build_answer_text(repeated_question)
        too_long = copy.deepcopy(source)
        too_long["threads_answer_text"] = source["threads_answer_text"] + ("長" * 321)
        with self.assertRaisesRegex(ValueError, "320 characters"):
            build_answer_text(too_long)

    def test_text_hooks_and_guides_have_separate_roles(self):
        for number in range(6, 48):
            content_id = f"ENG-{number:06d}"
            master = json.loads((REPO_ROOT / "data" / "master" / "quiz" /
                                 f"{content_id}.json").read_text(encoding="utf-8"))
            queue = json.loads((REPO_ROOT / "data" / "queue" /
                                f"{content_id}.json").read_text(encoding="utf-8"))
            validate_hook_guide(queue["parent_text"], master.get("question_guide_ja"),
                                master["visual_required"])

    def test_question_only_is_required_as_reply_media(self):
        queues = [json.loads(path.read_text(encoding="utf-8"))
                  for path in (REPO_ROOT / "data" / "queue").glob("ENG-0000*.json")]
        self.assertTrue(all("question_image" in queue for queue in queues if queue.get("content_type") == "quiz"))
        self.assertTrue(all("answer_image" not in queue for queue in queues if queue.get("content_type") == "quiz"))


if __name__ == "__main__":
    unittest.main()
