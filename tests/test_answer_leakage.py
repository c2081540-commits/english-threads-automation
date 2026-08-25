import unittest

from threads_automation.formats import FormatValidationError, validate_answer_leakage


class AnswerLeakageTests(unittest.TestCase):
    def test_repeated_pattern_fails(self):
        record = {
            "format": "pattern", "answer_leakage": "PASS",
            "examples": ["take a break", "take notes", "take a seat", "___ a look"],
            "choices": ["have", "do", "make", "take"], "correct_answer": "take",
        }
        with self.assertRaises(FormatValidationError):
            validate_answer_leakage(record)

    def test_mixed_pattern_passes(self):
        record = {
            "format": "pattern", "answer_leakage": "PASS",
            "examples": ["a desk", "an email", "a meeting", "___ hour"],
            "choices": ["an", "a"], "correct_answer": "an",
        }
        validate_answer_leakage(record)

    def test_only_unseen_choice_fails(self):
        record = {
            "format": "pattern", "answer_leakage": "PASS",
            "examples": ["do homework", "make a mistake", "have lunch", "___ a look"],
            "choices": ["do", "make", "have", "take"], "correct_answer": "take",
        }
        with self.assertRaises(FormatValidationError):
            validate_answer_leakage(record)

    def test_review_status_is_required(self):
        with self.assertRaises(FormatValidationError):
            validate_answer_leakage({"format": "text"})


if __name__ == "__main__":
    unittest.main()
