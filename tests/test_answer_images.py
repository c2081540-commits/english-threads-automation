import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from threads_automation.answer_images import validate_answer_image


class AnswerImageTests(unittest.TestCase):
    def test_historical_schedule_answer_image_fixtures_pass_free_machine_checks(self):
        schedule = json.loads((REPO_ROOT / "data" / "queue" /
                               "final-schedule-2026-08-20.json").read_text())
        ids = [item["content_id"] for item in schedule["items"] if item["content_type"] == "quiz"]
        self.assertEqual(len(ids), len(set(ids)))
        results = [validate_answer_image(content_id) for content_id in ids]
        self.assertTrue(all(result["format"] == "PNG" and result["mode"] == "RGB" and
                            result["size"] == [1080, 1350] for result in results))

    def test_missing_answer_image_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "ENG-999999-answer.png"
            with self.assertRaises(FileNotFoundError):
                validate_answer_image("ENG-999999", missing, missing)


if __name__ == "__main__":
    unittest.main()
