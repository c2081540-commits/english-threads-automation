import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))


class WeeklyThreadsTests(unittest.TestCase):
    def test_all_49_queues_exist_and_match_type(self):
        for number in range(6, 48):
            content_id = f"ENG-{number:06d}"
            queue = json.loads((REPO_ROOT / "data" / "queue" / f"{content_id}.json").read_text(encoding="utf-8"))
            self.assertEqual((queue["content_id"], queue["content_type"]), (content_id, "quiz"))
        for number in range(2, 9):
            content_id = f"ENG-{100000 + number:06d}"
            queue = json.loads((REPO_ROOT / "data" / "queue" / f"{content_id}.json").read_text(encoding="utf-8"))
            self.assertEqual((queue["content_id"], queue["content_type"]), (content_id, "normal"))

    def test_visual_queue_states(self):
        expected_visual = {8, 10, 14, 16, 20, 23, 26, 27, 32, 34, 39, 41, 44, 46}
        for number in expected_visual:
            queue = json.loads((REPO_ROOT / "data" / "queue" / f"ENG-{number:06d}.json").read_text(encoding="utf-8"))
            self.assertEqual(queue["parent_status"],
                             "posted" if number == 14 else "pending")
            self.assertIsNotNone(queue["question_image"])
            self.assertTrue((REPO_ROOT / queue["question_image"]).is_file())


if __name__ == "__main__":
    unittest.main()
