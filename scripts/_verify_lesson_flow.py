"""Contract checks for the UI-independent lesson-flow events.

Run: python scripts/_verify_lesson_flow.py
"""

import json
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hangul_quiz_engine as engine
from lesson_flow import AdvanceFlow, ReadingCheckFlow, round_card_choice, round_card_events


class LessonFlowEvents(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        progress = patch.object(engine, "PROGRESS_PATH", Path(temp.name) / "progress.json")
        progress.start()
        self.addCleanup(progress.stop)
        self.quiz = engine.HangulQuiz()
        self.quiz.start_lesson(1)
        random.seed(7)

    def test_reading_check_events_include_next_input_and_survive_json(self):
        flow = ReadingCheckFlow(self.quiz)
        events = flow.start()
        self.assertEqual(events[-1], {"kind": "check_input", "phase": "question"})
        self.assertEqual(len(json.loads(json.dumps(events))), len(events))
        events = flow.submit("/hint")
        self.assertEqual([event["kind"] for event in events], ["check_hint", "check_input"])
        events = flow.submit("/skip")
        self.assertEqual(events[0]["kind"], "check_feedback")
        self.assertEqual(events[-1]["kind"], "check_input")
        json.dumps(events)
        flow.submit("/quit")
        self.assertEqual(flow.outcome, "quit")
        self.assertTrue(self.quiz.progress["reading_check_seen"])

    def test_round_card_events_and_actions(self):
        events = round_card_events(self.quiz, 3, 0, 10, no_progress=True)
        card = events[0]
        self.assertEqual(events[-1]["kind"], "round_prompt")
        self.assertIn("next", card["actions"])
        self.assertEqual(round_card_choice(card, "n"), "next")
        self.assertEqual(round_card_choice(card, "r"), "continue")
        json.dumps(events)

    def test_advance_browse_then_accept(self):
        self.quiz.progress["completed_lessons"].append(1)
        flow = AdvanceFlow(self.quiz, 1)
        self.assertEqual(flow.start()[-1]["kind"], "advance_prompt")
        browse = flow.submit("/lessons")
        self.assertEqual([event["kind"] for event in browse],
                         ["advance_lessons", "advance_prompt"])
        json.dumps(browse)
        started = flow.submit("yes")
        self.assertEqual(started[0]["kind"], "lesson_started")
        self.assertEqual(flow.lesson_info["id"], 2)
        json.dumps(started)


if __name__ == "__main__":
    unittest.main(verbosity=2)
