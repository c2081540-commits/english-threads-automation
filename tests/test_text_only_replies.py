import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from threads_automation.content import validate_hook_guide  # noqa: E402


class TextOnlyReplyTests(unittest.TestCase):
    def test_all_production_quizzes_use_short_text_only_replies(self):
        for number in range(6, 48):
            queue = json.loads((REPO_ROOT / "data" / "queue" /
                                f"ENG-{number:06d}.json").read_text(encoding="utf-8"))
            self.assertNotIn("answer_image", queue)
            self.assertTrue(queue["answer_text"].startswith("💡 正解は "))
            self.assertLessEqual(len([line for line in queue["answer_text"].splitlines()
                                      if line.strip()]), 3)

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
