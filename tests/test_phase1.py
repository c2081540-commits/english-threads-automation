import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from threads_automation.paths import MASTER_DIR  # noqa: E402
from threads_automation.queue import build_queue  # noqa: E402
from threads_automation.validation import ValidationError, validate  # noqa: E402


class Phase1Tests(unittest.TestCase):
    def setUp(self):
        self.content = json.loads((MASTER_DIR / "ENG-000001.json").read_text())

    def test_sample_builds_parent_and_linked_reply(self):
        queue = build_queue(MASTER_DIR / "ENG-000001.json")
        self.assertEqual(queue["content_id"], "ENG-000001")
        self.assertEqual(queue["posts"][1]["reply_to"], queue["posts"][0]["queue_id"])

    def test_validation_fail_closed_cases(self):
        mutations = [
            ("content_id", None), ("question", ""), ("choices", ["since"]),
            ("best_answer", "from"), ("answer_type", "unknown"),
            ("publish_at", "tomorrow"), ("visual_description", ""),
        ]
        for field, value in mutations:
            broken = dict(self.content)
            broken[field] = value
            with self.subTest(field=field), self.assertRaises(ValidationError):
                validate(broken)

    def test_master_path_cannot_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                build_queue(Path(directory) / "ENG-000001.json")


if __name__ == "__main__":
    unittest.main()
