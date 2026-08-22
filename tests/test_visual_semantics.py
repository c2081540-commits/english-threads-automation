import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from threads_automation.validation import ValidationError, validate


TARGETS = {
    "ENG-000008", "ENG-000010", "ENG-000020", "ENG-000026", "ENG-000027",
    "ENG-000032", "ENG-000034", "ENG-000039", "ENG-000041", "ENG-000044",
    "ENG-000046",
}


class VisualSemanticTests(unittest.TestCase):
    def test_audited_visuals_pass_the_fixed_semantic_gate(self):
        for content_id in TARGETS:
            master = json.loads((ROOT / "data/master/quiz" / f"{content_id}.json").read_text())
            validate(master)
            self.assertTrue(master["visual_semantic_consistency"])
            self.assertEqual(master["visual_semantics"]["completed_sentence"],
                             master["question"].replace("___", master["best_answer"]))

    def test_completed_sentence_mismatch_fails_closed(self):
        master = json.loads((ROOT / "data/master/quiz/ENG-000020.json").read_text())
        master["visual_semantics"]["completed_sentence"] = "wrong"
        with self.assertRaisesRegex(ValidationError, "completed_sentence"):
            validate(master)


if __name__ == "__main__":
    unittest.main()
