import json
import sys
import unittest
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
IG_ROOT = REPO_ROOT.parent / "english-instagram-automation"
sys.path.insert(0, str(REPO_ROOT / "src"))

from threads_automation.schedule import load_schedule_config, should_execute


class FinalThreadsScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schedule = json.loads((REPO_ROOT / "data" / "queue" /
                                   "final-schedule-2026-08-20.json").read_text(encoding="utf-8"))
        cls.queues = [json.loads((REPO_ROOT / "data" / "queue" /
                                 f"{item['content_id']}.json").read_text(encoding="utf-8"))
                      for item in cls.schedule["items"]]

    def test_schedule_config_matches_instagram(self):
        self.assertEqual(load_schedule_config(), json.loads(
            (IG_ROOT / "config" / "schedule.json").read_text(encoding="utf-8")))

    def test_all_49_queues_are_unique_and_known_post_is_reconciled(self):
        self.assertEqual(len(self.queues), 49)
        self.assertEqual(len({queue["content_id"] for queue in self.queues}), 49)
        self.assertTrue(all(queue["platform"] == "threads" for queue in self.queues))
        posted = [queue for queue in self.queues if queue["status"] == "posted"]
        self.assertEqual([queue["content_id"] for queue in posted], ["ENG-000009"])
        self.assertEqual(sum(queue["status"] == "pending" for queue in self.queues), 48)
        quizzes = [queue for queue in self.queues if queue["content_type"] == "quiz"]
        self.assertTrue(all(queue["parent_status"] == queue["answer_status"] == "pending"
                            for queue in quizzes if queue["content_id"] != "ENG-000009"))
        self.assertEqual((posted[0]["parent_status"], posted[0]["answer_status"]), ("posted", "posted"))

    def test_all_shared_master_fields_and_slots_match(self):
        quiz_fields = ("content_id", "question", "choices", "best_answer", "publish_at")
        normal_fields = ("content_id", "theme", "threads_text", "story_headline", "story_body", "publish_at")
        for queue in self.queues:
            content_id = queue["content_id"]
            if queue["content_type"] == "quiz":
                local_path = REPO_ROOT / "data" / "master" / "quiz" / f"{content_id}.json"
                ig_path = IG_ROOT / "data" / "master" / f"{content_id}.json"
                fields = quiz_fields
            else:
                local_path = REPO_ROOT / "data" / "master" / "normal" / f"{content_id}.json"
                ig_path = IG_ROOT / "data" / "master" / "normal" / f"{content_id}.json"
                fields = normal_fields
            local = json.loads(local_path.read_text(encoding="utf-8"))
            instagram = json.loads(ig_path.read_text(encoding="utf-8"))
            self.assertEqual({field: local[field] for field in fields},
                             {field: instagram[field] for field in fields})
            self.assertEqual(queue["publish_at"], local["publish_at"])

    def test_fourteen_visuals_are_ready_and_identical(self):
        visual_ids = (8, 10, 14, 16, 20, 23, 26, 27, 32, 34, 39, 41, 44, 46)
        for number in visual_ids:
            content_id = f"ENG-{number:06d}"
            queue = json.loads((REPO_ROOT / "data" / "queue" / f"{content_id}.json").read_text(encoding="utf-8"))
            self.assertNotIn("WAITING", json.dumps(queue))
            threads_image = REPO_ROOT / queue["question_image"]
            instagram_image = IG_ROOT / "artifacts" / "images" / f"{content_id}-question.png"
            self.assertEqual(threads_image.read_bytes(), instagram_image.read_bytes())
            self.assertNotIn("placeholder", queue["question_image"])

    def test_all_42_questions_match_instagram_and_replies_are_text_only(self):
        quizzes = [queue for queue in self.queues if queue["content_type"] == "quiz"]
        self.assertEqual(len(quizzes), 42)
        for queue in quizzes:
            content_id = queue["content_id"]
            self.assertNotIn("answer_image", queue)
            threads_question = REPO_ROOT / queue["question_image"]
            instagram_question = IG_ROOT / "artifacts" / "images" / f"{content_id}-question.png"
            self.assertEqual(threads_question.read_bytes(), instagram_question.read_bytes())
            local = json.loads((REPO_ROOT / "data" / "master" / "quiz" /
                                f"{content_id}.json").read_text())
            instagram = json.loads((IG_ROOT / "data" / "master" /
                                    f"{content_id}.json").read_text())
            self.assertEqual(local["content_id"], instagram["content_id"])
            self.assertEqual(local["best_answer"], instagram["best_answer"])
            self.assertEqual(local.get("question_guide_ja"), instagram.get("question_guide_ja"))

    def test_past_slots_are_held_and_posted_is_not_reposted(self):
        held = [queue for queue in self.queues if queue["execution_eligibility"] == "past_due_hold"]
        self.assertEqual([queue["content_id"] for queue in held],
                         ["ENG-000006", "ENG-000007", "ENG-000008", "ENG-000010", "ENG-000011",
                          "ENG-100002"])
        queue = dict(self.queues[3], status="posted", execution_eligibility="scheduled")
        self.assertFalse(should_execute(queue, datetime.fromisoformat("2026-08-21T00:00:00+09:00")))


if __name__ == "__main__":
    unittest.main()
