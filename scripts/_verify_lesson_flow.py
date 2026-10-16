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


    # ── helpers ────────────────────────────────────────────────────────

    def _mastery_items(self):
        return [self.quiz._compose_bare_vowel(s)
                for s in self.quiz._mastery_set(self.quiz.current_lesson)]

    def _solidify(self, items):
        for key in items:
            item = self.quiz._get_item(key)
            item.correct += item.CONFIDENCE_RAMP
            item.history = "1" * item.CONFIDENCE_RAMP
            self.quiz._save_item(item)
            self.assertTrue(self.quiz._is_solid(key))

    def _assert_json_safe(self, events):
        """Events must survive a JSON round trip unchanged (no tuples, sets...)."""
        self.assertEqual(json.loads(json.dumps(events, ensure_ascii=False)), events)

    def _fail_check(self, flow):
        """Answer every check question wrong; return the last events."""
        events = []
        for _ in range(20):
            if flow.phase != "question":
                break
            events = flow.submit("zzz")
        return events

    # ── reading check ──────────────────────────────────────────────────

    def test_reading_check_pass_ends_without_another_prompt(self):
        flow = ReadingCheckFlow(self.quiz)
        events = flow.start()
        for _ in range(20):
            if flow.outcome is not None:
                break
            events = flow.submit(flow.check.current.correct_answer)
            self._assert_json_safe(events)
        self.assertEqual(flow.outcome, "passed")
        self.assertEqual(events[-1]["kind"], "check_score")
        self.assertTrue(events[-1]["passed"])
        self.assertTrue(self.quiz.progress["reading_checks"]["1"]["passed"])

    def test_reading_check_blank_and_bad_input_are_not_graded(self):
        flow = ReadingCheckFlow(self.quiz)
        flow.start()
        index = flow.check.index
        self.assertEqual(flow.submit(""), [{"kind": "check_input", "phase": "question"}])
        self.assertEqual(flow.submit("/foo")[0]["kind"], "check_commands")
        self.assertEqual(flow.submit("가")[0]["kind"], "check_script_mismatch")
        self.assertEqual(flow.check.index, index)

    def test_hinted_answer_is_not_independent_and_comes_back(self):
        flow = ReadingCheckFlow(self.quiz)
        flow.start()
        letter = flow.check.current.letter
        flow.submit("/hint")
        events = flow.submit(flow.check.current.correct_answer)
        self.assertTrue(events[0]["assisted"])
        self.assertNotIn(letter, flow.check.correct)
        questions = [e for e in events if e["kind"] == "check_question"]
        for _ in range(20):
            if flow.outcome is not None:
                break
            events = flow.submit(flow.check.current.correct_answer)
            questions += [e for e in events if e["kind"] == "check_question"]
        self.assertTrue(any(q["retry"] and q["letter"] == letter for q in questions))
        self.assertEqual(flow.outcome, "passed")

    def test_failed_check_practice_then_retry(self):
        flow = ReadingCheckFlow(self.quiz)
        flow.start()
        events = self._fail_check(flow)
        score = next(e for e in events if e["kind"] == "check_score")
        self.assertFalse(score["passed"])
        self.assertIn("check_practice_intro", [e["kind"] for e in events])
        self.assertEqual(events[-1], {"kind": "check_input", "phase": "practice"})
        practised = 0
        while flow.phase == "practice" and practised < 5:
            events = flow.submit(flow.practice[0].correct_answer)
            self.assertTrue(events[0]["correct"])
            practised += 1
        self.assertLessEqual(practised, 3)
        self.assertEqual(events[-1], {"kind": "check_input", "phase": "retry"})
        events = flow.submit("r")
        self.assertEqual(events[0]["kind"], "check_question")
        self.assertEqual(events[0]["number"], 1)
        self.assertIsNone(flow.outcome)
        self._assert_json_safe(events)

    def test_failed_check_enter_at_retry_goes_back_to_practice(self):
        flow = ReadingCheckFlow(self.quiz)
        flow.start()
        self._fail_check(flow)
        while flow.phase == "practice":
            self.assertFalse(flow.submit("zzz")[0]["correct"])
        self.assertEqual(flow.submit(""), [])
        self.assertEqual(flow.outcome, "practice")

    def test_reading_check_back_and_quit(self):
        flow = ReadingCheckFlow(self.quiz)
        flow.start()
        self.assertEqual(flow.submit("/back"), [])
        self.assertEqual(flow.outcome, "practice")
        with self.assertRaises(ValueError):
            flow.submit("a")
        flow = ReadingCheckFlow(self.quiz)
        flow.start()
        self._fail_check(flow)
        self.assertEqual(flow.submit(None), [])  # closed input in practice
        self.assertEqual(flow.outcome, "quit")

    # ── advance offer ──────────────────────────────────────────────────

    def test_advance_not_completed_does_nothing(self):
        flow = AdvanceFlow(self.quiz, 1)
        self.assertEqual(flow.start(), [])
        self.assertTrue(flow.finished)
        self.assertIsNone(flow.lesson_info)

    def test_advance_decline_or_closed_input_stays(self):
        self.quiz.progress["completed_lessons"].append(1)
        for answer in ("n", " No ", None):
            flow = AdvanceFlow(self.quiz, 1)
            flow.start()
            self.assertEqual(flow.submit(answer), [{"kind": "advance_stay"}])
            self.assertTrue(flow.finished)
            self.assertIsNone(flow.lesson_info)
        self.assertEqual(self.quiz.current_lesson["id"], 1)

    def test_advance_bad_input_then_jump(self):
        self.quiz.progress["completed_lessons"].append(1)
        total = len(self.quiz.curriculum["lessons"])
        flow = AdvanceFlow(self.quiz, 1)
        flow.start()
        self.assertEqual(flow.submit("/lesson 99"),
                         [{"kind": "advance_missing_lesson", "number": 99, "total": total},
                          {"kind": "advance_prompt", "lesson_id": 2}])
        self.assertEqual(flow.submit("maybe")[0]["kind"], "advance_help")
        self.assertFalse(flow.finished)
        started = flow.submit("/lesson 3")
        self.assertEqual(started[0]["kind"], "lesson_started")
        self.assertFalse(started[0]["rich"])
        self.assertIsNone(started[0]["message"])
        self.assertEqual(flow.lesson_info["id"], 3)
        self._assert_json_safe(started)

    def test_advance_on_last_lesson_completes_curriculum(self):
        last = len(self.quiz.curriculum["lessons"])
        self.quiz.start_lesson(last)
        self.quiz.progress["completed_lessons"].append(last)
        flow = AdvanceFlow(self.quiz, last)
        events = flow.start()
        self.assertEqual([e["kind"] for e in events], ["lesson_mastered", "curriculum_complete"])
        self.assertTrue(events[0]["words"])  # falls back to the vocabulary list
        self.assertTrue(flow.finished)
        self.assertIsNone(flow.lesson_info)
        self._assert_json_safe(events)

    # ── round card ─────────────────────────────────────────────────────

    def test_round_card_ready_offers_the_check(self):
        self._solidify(self._mastery_items())
        card = round_card_events(self.quiz, 1, 10, 10)[0]
        self.assertTrue(card["ready"])
        self.assertEqual(card["actions"], ["check", "continue", "quit"])
        self.assertEqual(round_card_choice(card, "r"), "check")
        self.assertEqual(round_card_choice(card, "n"), "continue")
        self.assertEqual(round_card_choice(card, None), "quit")

    def test_round_card_done_lesson(self):
        self.quiz.progress["completed_lessons"].append(1)
        card = round_card_events(self.quiz, 1, 5, 10)[0]
        self.assertEqual(card["next_lesson"]["id"], 2)
        self.assertEqual(card["actions"], ["check", "next", "continue", "quit"])
        self.assertEqual(round_card_choice(card, "/check"), "check")
        self.assertEqual(round_card_choice(card, "r"), "continue")  # [r] only when ready
        self.assertEqual(round_card_choice(card, "next"), "next")

    def test_round_card_last_lesson_has_no_next(self):
        self.quiz.start_lesson(len(self.quiz.curriculum["lessons"]))
        card = round_card_events(self.quiz, 5, 0, 10, no_progress=True)[0]
        self.assertTrue(card["stuck"])
        self.assertTrue(card["last"])
        self.assertIsNone(card["next_lesson"])
        self.assertNotIn("next", card["actions"])
        self.assertEqual(round_card_choice(card, "n"), "continue")

    def test_round_card_notices_are_filtered_and_cleared(self):
        items = self._mastery_items()
        self._solidify(items[:1])
        solid_now = [items[0], items[0], items[1]]  # a repeat and a not-solid item
        milestones = ["5 in a row!"]
        card = round_card_events(self.quiz, 1, 5, 10, solid_now=solid_now,
                                 milestones=milestones)[0]
        self.assertEqual(card["solid_now"], [items[0]])
        self.assertEqual(card["milestones"], ["5 in a row!"])
        self.assertEqual((solid_now, milestones), ([], []))
        self._assert_json_safe([card])

    def test_round_card_reward_word(self):
        card = round_card_events(self.quiz, 1, 5, 10, reward_earned=True)[0]
        self.assertIsNotNone(card["reward"])
        self.assertIn("word", card["reward"])
        card = round_card_events(self.quiz, 1, 5, 10, reward_earned=True,
                                 terminal_llm_reward=True)[0]
        self.assertIsNone(card["reward"])  # the terminal tries its LLM sentence first


if __name__ == "__main__":
    unittest.main(verbosity=2)
