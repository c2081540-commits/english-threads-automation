import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from threads_automation.builder import (build_normal_queue, build_quiz_queue,
                                        format_dry_run)  # noqa: E402
from threads_automation.content import (COMMON_FIELDS, load_quiz_master,
                                        validate_common_content, validate_hook)  # noqa: E402
from threads_automation.paths import (INSTAGRAM_MASTER_DIR, NORMAL_MASTER_DIR,
                                      QUIZ_MASTER_DIR)  # noqa: E402


class ContentPipelineTests(unittest.TestCase):
    quiz_ids = ("ENG-000002", "ENG-000003", "ENG-000005")

    def test_three_quiz_queues(self):
        queues = [build_quiz_queue(content_id) for content_id in self.quiz_ids]
        self.assertEqual([queue["content_type"] for queue in queues], ["quiz"] * 3)
        for queue in queues:
            self.assertEqual(queue["parent_status"], "pending")
            self.assertEqual(queue["answer_status"], "pending")
            self.assertIsNone(queue["parent_post_id"])
            self.assertTrue((REPO_ROOT / queue["question_image"]).is_file())
            self.assertNotIn("answer_image", queue)
            self.assertIn("💡 正解は ", queue["answer_text"])

    def test_parent_hook_does_not_repeat_question(self):
        for content_id in self.quiz_ids:
            master = load_quiz_master(content_id)
            queue = build_quiz_queue(content_id)
            self.assertNotIn(master["question"], queue["parent_text"])
            self.assertLessEqual(len(queue["parent_text"].splitlines()), 2)

    def test_normal_queue_and_shared_story_fields(self):
        queue = build_normal_queue("ENG-100001")
        master = json.loads((NORMAL_MASTER_DIR / "ENG-100001.json").read_text(encoding="utf-8"))
        self.assertEqual(queue["content_type"], "normal")
        self.assertEqual(queue["text"], master["threads_text"])
        self.assertTrue(master["story_headline"])
        self.assertTrue(master["story_body"])

    def test_dry_run_for_quiz_and_normal(self):
        quiz = format_dry_run(build_quiz_queue("ENG-000003"))
        self.assertIn("parent:", quiz)
        self.assertIn("image:", quiz)
        self.assertIn("reply media: none (TEXT-only)", quiz)
        self.assertIn("💡 正解は B. for", quiz)
        normal = format_dry_run(build_normal_queue("ENG-100001"))
        self.assertIn("DRY RUN Threads normal", normal)
        self.assertIn("単語を5個見る", normal)

    def test_instagram_common_fields_match(self):
        for content_id in self.quiz_ids:
            local = json.loads((QUIZ_MASTER_DIR / f"{content_id}.json").read_text(encoding="utf-8"))
            instagram = json.loads((INSTAGRAM_MASTER_DIR / f"{content_id}.json").read_text(encoding="utf-8"))
            validate_common_content(local, instagram)
            self.assertEqual({field: local[field] for field in COMMON_FIELDS},
                             {field: instagram[field] for field in COMMON_FIELDS})

    def test_instagram_best_answer_mismatch_fails_closed(self):
        local = json.loads((QUIZ_MASTER_DIR / "ENG-000003.json").read_text(encoding="utf-8"))
        instagram = dict(local)
        instagram["best_answer"] = "since"
        with self.assertRaisesRegex(ValueError, "best_answer mismatch"):
            validate_common_content(local, instagram)

    def test_prohibited_hook_fails_closed(self):
        for hook in ("日本人の90%が間違える", "正答率80%", "ほとんどの人が間違える", "ネイティブしか分からない"):
            with self.subTest(hook=hook), self.assertRaisesRegex(ValueError, "prohibited"):
                validate_hook(hook)

    def test_missing_required_quiz_field_fails_closed(self):
        source = json.loads((QUIZ_MASTER_DIR / "ENG-000003.json").read_text(encoding="utf-8"))
        del source["question"]
        source["content_id"] = "ENG-999999"
        temporary = QUIZ_MASTER_DIR / "ENG-999999.json"
        temporary.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
        try:
            with self.assertRaisesRegex(ValueError, "missing fields"):
                load_quiz_master("ENG-999999")
        finally:
            temporary.unlink()

    def test_scripts_are_cwd_independent(self):
        build_script = REPO_ROOT / "scripts" / "build_queue.py"
        dry_run_script = REPO_ROOT / "scripts" / "dry_run.py"
        queue_path = REPO_ROOT / "data" / "queue" / "ENG-000003.json"
        original = queue_path.read_bytes()
        try:
            built = subprocess.run([sys.executable, str(build_script), "quiz", "ENG-000003"],
                                   cwd="/private/tmp", check=True, capture_output=True, text=True)
            self.assertIn("ENG-000003.json", built.stdout)
            dry_run = subprocess.run([sys.executable, str(dry_run_script), "ENG-000003"],
                                     cwd="/private/tmp", check=True, capture_output=True, text=True)
            self.assertIn("💡 正解は B. for", dry_run.stdout)
        finally:
            queue_path.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
