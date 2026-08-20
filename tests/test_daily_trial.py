import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from threads_automation.builder import (build_normal_queue, build_quiz_queue,
                                        format_dry_run)


class DailyTrialTests(unittest.TestCase):
    QUIZ_IDS = tuple(f"ENG-{number:06d}" for number in range(6, 12))

    def test_six_quiz_queues_and_one_normal_queue(self):
        queues = [build_quiz_queue(content_id) for content_id in self.QUIZ_IDS]
        self.assertEqual(len(queues), 6)
        self.assertTrue(all(queue["content_type"] == "quiz" for queue in queues))
        normal = build_normal_queue("ENG-100002")
        self.assertEqual(normal["content_type"], "normal")

    def test_instagram_common_master_data_matches(self):
        instagram_dir = REPO_ROOT.parent / "english-instagram-automation" / "data" / "master"
        for content_id in self.QUIZ_IDS:
            local = json.loads((REPO_ROOT / "data" / "master" / "quiz" / f"{content_id}.json").read_text(encoding="utf-8"))
            instagram = json.loads((instagram_dir / f"{content_id}.json").read_text(encoding="utf-8"))
            for field in ("content_id", "question", "choices", "best_answer", "answer_type"):
                self.assertEqual(local[field], instagram[field])
        local_normal = (REPO_ROOT / "data" / "master" / "normal" / "ENG-100002.json").read_bytes()
        instagram_normal = (instagram_dir / "normal" / "ENG-100002.json").read_bytes()
        self.assertEqual(local_normal, instagram_normal)

    def test_visual_quiz_waits_without_dummy_image(self):
        queue = build_quiz_queue("ENG-000008")
        self.assertIsNone(queue["question_image"])
        self.assertEqual(queue["parent_status"], "WAITING_FOR_VISUAL")
        self.assertEqual(queue["answer_status"], "WAITING_FOR_PARENT")

    def test_ready_quiz_and_normal_dry_runs(self):
        quiz_text = format_dry_run(build_quiz_queue("ENG-000006"))
        self.assertIn("parent:", quiz_text)
        self.assertIn("answer:", quiz_text)
        normal_text = format_dry_run(build_normal_queue("ENG-100002"))
        self.assertIn("DRY RUN Threads normal", normal_text)

    def test_cwd_independent(self):
        previous = Path.cwd()
        try:
            os.chdir(tempfile.gettempdir())
            self.assertEqual(build_quiz_queue("ENG-000006")["content_id"], "ENG-000006")
        finally:
            os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
