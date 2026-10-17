"""Regression checks for the plain-text playtest runner's input prompts."""

import contextlib
import io
import unittest
from pathlib import Path
from sys import path
from unittest.mock import patch

path.insert(0, str(Path(__file__).resolve().parents[1]))
from sejong_cli import render  # noqa: E402


class Clock:
    def __init__(self):
        self.marks = 0

    def mark(self):
        self.marks += 1

    def take(self):
        return 123


class CliInputTest(unittest.TestCase):
    def run_events(self, events, replies):
        clock = Clock()
        output = io.StringIO()
        with patch("builtins.input", side_effect=replies) as entered:
            with contextlib.redirect_stdout(output):
                result = render(events, clock)
        return result, output.getvalue(), entered.call_args_list, clock

    def test_typed_answer_is_not_silently_consumed_by_pause(self):
        events = [
            {"kind": "narrator", "speaker": "jeong", "text": "Look at the pieces."},
            {"kind": "await", "input": "choice", "choices": ["도", "노", "나"]},
        ]
        result, output, prompts, clock = self.run_events(events, ["na", "", "2"])
        self.assertEqual(result, ("노", 123))
        self.assertIn("Press Enter without typing", output)
        self.assertEqual(prompts[-1].args[0], "Choice (1-3 or exact option): ")
        self.assertEqual(clock.marks, 1)

    def test_result_pause_explains_accidental_choice(self):
        events = [
            {"kind": "result", "correct": False, "correct_answer": "나"},
            {"kind": "await", "input": "text"},
        ]
        result, output, _, _ = self.run_events(events, ["3", "", "na"])
        self.assertEqual(result, ("na", 123))
        self.assertIn("Answers go at the choice or text prompt", output)

    def test_continue_sends_only_an_empty_answer(self):
        events = [{"kind": "await", "input": "continue"}]
        result, output, _, _ = self.run_events(events, ["hello", ""])
        self.assertEqual(result, ("", 123))
        self.assertIn("Press Enter without typing", output)


if __name__ == "__main__":
    unittest.main()
