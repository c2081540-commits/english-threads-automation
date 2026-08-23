import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
IG_ROOT = REPO_ROOT.parent / "english-instagram-automation"
sys.path.insert(0, str(REPO_ROOT / "src"))

from threads_automation.difficulty import (load_config, validate_hook_for_item)  # noqa: E402


class ThreadsDifficultyLevelTests(unittest.TestCase):
    def test_config_matches_instagram(self):
        self.assertEqual(load_config(), json.loads(
            (IG_ROOT / "config" / "difficulty_levels.json").read_text()))

    def test_unposted_hooks_match_level_and_question_type(self):
        recent = []
        for number in range(6, 48):
            content_id = f"ENG-{number:06d}"
            queue = json.loads((REPO_ROOT / "data" / "queue" / f"{content_id}.json").read_text())
            if queue["status"] == "posted":
                continue
            master = json.loads((REPO_ROOT / "data" / "master" / "quiz" /
                                 f"{content_id}.json").read_text())
            self.assertEqual(queue["difficulty_level"], master["difficulty_level"])
            self.assertEqual(queue["parent_text"], master["threads_parent_text"])
            validate_hook_for_item(master, queue["parent_text"])
            self.assertNotIn(queue["parent_text"], recent[-2:])
            recent.append(queue["parent_text"])

    def test_eng_000034_approved_hook_is_a_situation_hook(self):
        content_id="ENG-000034"
        master=json.loads((REPO_ROOT/"data/master/quiz"/f"{content_id}.json").read_text())
        queue=json.loads((REPO_ROOT/"data/queue"/f"{content_id}.json").read_text())
        self.assertEqual(master["production_category"],"situation")
        validate_hook_for_item(master,queue["parent_text"])


if __name__ == "__main__":
    unittest.main()
