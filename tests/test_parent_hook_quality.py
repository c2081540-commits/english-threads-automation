import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from threads_automation.difficulty import (allowed_hooks, load_hook_policy,
                                           validate_hook_for_item,
                                           validate_hook_sequence)  # noqa: E402

INSTRUCTION_IDS = {
    "ENG-000008", "ENG-000020", "ENG-000027", "ENG-000032", "ENG-000039", "ENG-000044",
}


class ParentHookQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = []
        for number in range(6, 48):
            content_id = f"ENG-{number:06d}"
            queue = json.loads((REPO_ROOT / "data" / "queue" / f"{content_id}.json").read_text())
            if queue["status"] == "posted":
                continue
            master = json.loads((REPO_ROOT / "data" / "master" / "quiz" /
                                 f"{content_id}.json").read_text())
            master["threads_parent_text"] = queue["parent_text"]
            master["publish_at"] = queue["publish_at"]
            cls.items.append(master)
        cls.audit = json.loads((REPO_ROOT / "artifacts" / "weekly" / "2026-08-20" /
                                "thread-hook-audit.json").read_text())["items"]

    def test_all_unposted_hooks_pass_the_batch_quality_gate(self):
        self.assertEqual(len(self.items), 36)
        validate_hook_sequence(self.items)

    def test_audit_counts_and_instruction_hooks_are_revised(self):
        self.assertEqual(sum(row["decision"] == "KEEP" for row in self.audit), 13)
        self.assertEqual(sum(row["decision"] == "REVISE" for row in self.audit), 24)
        revised = {row["content_id"] for row in self.audit if "instruction-style" in row["reason"]}
        self.assertEqual(revised, INSTRUCTION_IDS)

    def test_instruction_phrases_and_answer_leaks_fail_closed(self):
        source = self.items[0]
        with self.assertRaisesRegex(ValueError, "instruction-style"):
            validate_hook_for_item(source, "画像を見て答えてみよう。")
        leaked = dict(source)
        leaked["best_answer"] = "rolling"
        leaked["acceptable_answers"] = ["rolling"]
        with self.assertRaisesRegex(ValueError, "reveals"):
            validate_hook_for_item(leaked, "rollingを覚えてる？")

    def test_generation_has_controlled_variation(self):
        for item in self.items:
            candidates = allowed_hooks(item)
            self.assertGreaterEqual(len(set(candidates)), 6)
            for candidate in candidates:
                policy = load_hook_policy()
                self.assertFalse(any(term in candidate for term in
                                     policy["instruction_style_substrings"]))


if __name__ == "__main__":
    unittest.main()
