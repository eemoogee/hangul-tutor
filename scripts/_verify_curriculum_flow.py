"""Deterministic checks for the Python-only ordinary curriculum controller."""

import contextlib
import io
import json
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import curriculum_flow as C
import hangul_cli as CLI
import hangul_quiz_engine as E
import reading_check


def solidify(quiz):
    for target in quiz._mastery_set(quiz.current_lesson):
        item = quiz._get_item(quiz._compose_bare_vowel(target))
        item.history = "111"
        quiz._save_item(item)
    assert quiz.lesson_mastery()["is_mastered"]


def fixed_questions(quiz):
    """Keep practice draws identical while retaining the real grading engine."""
    def draw(mode=None):
        target = quiz._mastery_set(quiz.current_lesson)[0]
        return E.QuizQuestion(
            mode="read_aloud", prompt=f"Read {target}", letter=target,
            correct_answer=quiz._word_romanization(target),
            accepted=sorted(quiz.roman_variants(target)),
            hint="Read the parts together.",
            lesson_id=quiz.current_lesson["id"])
    quiz.next_question = draw


def kinds(events):
    json.dumps(events, ensure_ascii=False)
    return [event["kind"] for event in events]


class CurriculumFlowChecks(unittest.TestCase):
    def setUp(self):
        random.seed(31)
        self.quiz = E.HangulQuiz(persist=False)
        fixed_questions(self.quiz)

    def restore(self, flow):
        quiz = E.HangulQuiz(persist=False)
        fixed_questions(quiz)
        clone = C.CurriculumFlow.from_state(quiz, flow.export_state())
        return clone

    def test_constants_match_cli(self):
        self.assertEqual(C.ROUND_SIZE, CLI.ROUND_SIZE)
        self.assertEqual(C.STUCK_AFTER_ROUNDS, CLI.STUCK_AFTER_ROUNDS)
        self.assertEqual(C.REWARD_EVERY, CLI.REWARD_EVERY)
        self.assertEqual(C.STREAK_MILESTONES, CLI.STREAK_MILESTONES)

    def test_practice_card_check_pass_and_advance(self):
        flow = C.CurriculumFlow(self.quiz)
        opening = flow.start()
        self.assertEqual(kinds(opening), ["lesson_started", "question"])
        self.assertNotIn("correct_answer", opening[-1])
        self.assertNotIn("hint", opening[-1])
        for turn in range(9):
            events = flow.submit(flow.current_question.correct_answer, 1200)
            self.assertEqual(flow.round_asked, turn + 1)
            self.assertIn("question", kinds(events))
        events = flow.submit(flow.current_question.correct_answer, 1200)
        self.assertEqual(kinds(events)[-2:], ["round_card", "round_prompt"])
        self.assertEqual(events[-2]["asked"], 10)
        self.assertEqual(flow.phase, "round")
        self.assertIn("question", kinds(flow.submit("")))
        solidify(self.quiz)
        self.assertIn("check_intro", kinds(flow.submit("/check")))
        for _ in range(5):
            answer = flow.check.check.current.correct_answer
            events = flow.submit(answer)
        self.assertIn("check_score", kinds(events))
        self.assertIn("advance_prompt", kinds(events))
        self.assertEqual(flow.phase, "advance")
        events = flow.submit("")
        self.assertIn("lesson_started", kinds(events))
        self.assertEqual(self.quiz.current_lesson["id"], 2)
        self.assertEqual(flow.round_no, 1)
        self.assertEqual(flow.round_asked, 0)

    def test_skip_consumes_turn_without_grade(self):
        flow = C.CurriculumFlow(self.quiz)
        flow.start()
        events = flow.submit("/skip")
        self.assertEqual(kinds(events), ["result", "question"])
        self.assertTrue(events[0]["skipped"])
        self.assertEqual(flow.round_asked, 1)
        self.assertEqual(flow.round_right, 0)
        self.assertEqual(self.quiz.session_skips, 1)
        self.assertEqual(self.quiz.session_total, 0)

    def test_hint_makes_answer_assisted(self):
        flow = C.CurriculumFlow(self.quiz)
        flow.start()
        target = flow.current_question.letter
        self.assertEqual(kinds(flow.submit("/hint")), ["hint"])
        events = flow.submit(flow.current_question.correct_answer)
        self.assertTrue(events[0]["correct"])
        self.assertTrue(events[0]["assisted"])
        self.assertEqual(flow.round_right, 1)
        self.assertFalse(self.quiz._is_solid(target))

    def test_next_navigates_without_completing_and_quit_ends(self):
        flow = C.CurriculumFlow(self.quiz)
        flow.start()
        events = flow.submit("/next")
        self.assertIn("lesson_started", kinds(events))
        self.assertEqual(self.quiz.current_lesson["id"], 2)
        self.assertNotIn(1, self.quiz.progress["completed_lessons"])
        self.assertEqual(flow.round_no, 1)
        self.assertEqual(kinds(flow.submit("/quit")), ["finished"])
        self.assertEqual(flow.outcome, "quit")
        self.assertIn("question", kinds(flow.resume("reopen")))
        self.assertIsNone(flow.outcome)

    def test_practice_restore_keeps_question_hint_and_session_totals(self):
        flow = C.CurriculumFlow(self.quiz)
        flow.start()
        self.assertEqual(kinds(flow.submit("/hint")), ["hint"])
        target = flow.current_question.correct_answer
        clone = self.restore(flow)
        self.assertEqual(clone.resume("reopen"), [flow._question_event()])
        self.assertTrue(clone.hint_used)
        self.assertEqual(clone.current_question.correct_answer, target)
        result = clone.submit(target)
        self.assertTrue(result[0]["assisted"])
        self.assertEqual(clone.quiz.progress["total_questions_answered"], 1)
        after = self.restore(clone)
        after.resume("pause")
        after.submit(after.current_question.correct_answer)
        self.assertEqual(after.quiz.progress["total_questions_answered"], 2)
        self.assertEqual(after.quiz.progress["total_correct"], 2)
        self.assertEqual(after.quiz.session_total, 2)

    def test_round_card_restore_keeps_counts_and_choice(self):
        flow = C.CurriculumFlow(self.quiz)
        flow.start()
        for _ in range(10):
            events = flow.submit("/skip")
        self.assertEqual(flow.phase, "round")
        clone = self.restore(flow)
        self.assertEqual(clone.resume("reopen"), events[-2:])
        self.assertEqual((clone.round_no, clone.round_asked, clone.round_right),
                         (1, 10, 0))
        self.assertIn("question", kinds(clone.submit("")))
        self.assertEqual((clone.round_no, clone.round_asked), (2, 0))

    def test_mid_check_restore_preserves_question_and_assistance(self):
        self.quiz.start_lesson(1)
        solidify(self.quiz)
        flow = C.CurriculumFlow(self.quiz)
        flow.start()
        flow.submit(flow.check.check.current.correct_answer)
        flow.submit("/hint")
        current = flow.check.check.current
        clone = self.restore(flow)
        self.assertEqual(kinds(clone.resume("reopen")),
                         ["check_question", "check_hint", "check_input"])
        self.assertEqual(clone.check.check.current.letter, current.letter)
        self.assertTrue(clone.check.assisted)
        self.assertEqual(kinds(clone.submit(current.correct_answer)),
                         kinds(flow.submit(current.correct_answer)))
        self.assertEqual(clone.check.check.index, flow.check.check.index)
        self.assertEqual(clone.check.check.retried, flow.check.check.retried)

    def test_failed_check_practice_and_retry_restore(self):
        self.quiz.start_lesson(1)
        solidify(self.quiz)
        flow = C.CurriculumFlow(self.quiz)
        flow.start()
        for _ in range(5):
            flow.submit("zzz")
        clone = self.restore(flow)
        self.assertEqual(kinds(clone.resume("reopen")),
                         ["check_practice_question", "check_input"])
        for _ in range(3):
            self.assertEqual(kinds(clone.submit("zzz")),
                             kinds(flow.submit("zzz")))
        retry = self.restore(clone)
        self.assertEqual(retry.resume("pause"),
                         [{"kind": "check_input", "phase": "retry"}])
        self.assertIn("check_question", kinds(retry.submit("r")))

    def test_quit_during_check_can_resume_same_question(self):
        self.quiz.start_lesson(1)
        solidify(self.quiz)
        flow = C.CurriculumFlow(self.quiz)
        flow.start()
        answer = flow.check.check.current.correct_answer
        self.assertEqual(kinds(flow.submit("/quit"))[-1], "finished")
        clone = self.restore(flow)
        self.assertEqual(kinds(clone.resume("reopen")),
                         ["check_question", "check_input"])
        self.assertEqual(clone.check.check.current.correct_answer, answer)
        self.assertIn("check_feedback", kinds(clone.submit(answer)))

    def test_bad_saved_phase_is_rejected(self):
        flow = C.CurriculumFlow(self.quiz)
        flow.start()
        saved = json.loads(flow.export_state())
        saved["phase"] = "check"
        with self.assertRaises(ValueError):
            C.CurriculumFlow.from_state(E.HangulQuiz(persist=False),
                                        json.dumps(saved, ensure_ascii=False))

    def test_restore_preserves_next_random_question(self):
        quiz = E.HangulQuiz(persist=False)
        random.seed(72)
        flow = C.CurriculumFlow(quiz)
        flow.start()
        saved = flow.export_state()
        original_events = flow.submit("/skip")
        clone = C.CurriculumFlow.from_state(E.HangulQuiz(persist=False), saved)
        self.assertEqual(clone.submit("/skip"), original_events)

    def test_advance_offer_restore_and_quit_resume(self):
        self.quiz.start_lesson(1)
        solidify(self.quiz)
        flow = C.CurriculumFlow(self.quiz)
        flow.start()
        for _ in range(5):
            flow.submit(flow.check.check.current.correct_answer)
        clone = self.restore(flow)
        self.assertEqual(kinds(clone.resume("reopen")), ["advance_prompt"])
        self.assertEqual(kinds(clone.submit("/quit")), ["finished"])
        restored = self.restore(clone)
        self.assertEqual(kinds(restored.resume("reopen")), ["advance_prompt"])
        self.assertIn("lesson_started", kinds(restored.submit("")))
        self.assertEqual(restored.quiz.current_lesson["id"], 2)

    def test_failed_check_practice_and_retry(self):
        self.quiz.start_lesson(1)
        solidify(self.quiz)
        flow = C.CurriculumFlow(self.quiz)
        self.assertIn("check_intro", kinds(flow.start()))
        for _ in range(5):
            events = flow.submit("zzz")
        self.assertIn("check_practice_intro", kinds(events))
        self.assertEqual(flow.check.phase, "practice")
        for _ in range(3):
            events = flow.submit("zzz")
        self.assertEqual(flow.check.phase, "retry")
        self.assertEqual(kinds(events), ["check_practice_feedback", "check_input"])
        self.assertIn("check_question", kinds(flow.submit("r")))
        for _ in range(5):
            events = flow.submit(flow.check.check.current.correct_answer)
        self.assertIn("advance_prompt", kinds(events))
        self.assertEqual(self.quiz.progress["reading_checks"]["1"]["attempts"], 2)

    def test_stay_after_pass_keeps_lesson(self):
        self.quiz.start_lesson(1)
        solidify(self.quiz)
        flow = C.CurriculumFlow(self.quiz)
        flow.start()
        for _ in range(5):
            flow.submit(flow.check.check.current.correct_answer)
        events = flow.submit("n")
        self.assertIn("advance_stay", kinds(events))
        self.assertEqual(self.quiz.current_lesson["id"], 1)
        self.assertIn(1, self.quiz.progress["completed_lessons"])
        self.assertEqual(flow.phase, "practice")

    def test_tenth_answer_opens_check_before_card(self):
        flow = C.CurriculumFlow(self.quiz)
        flow.start()
        for _ in range(9):
            flow.submit("/skip")
        self.assertEqual(flow.round_asked, 9)
        solidify(self.quiz)
        events = flow.submit(flow.current_question.correct_answer)
        self.assertIn("check_intro", kinds(events))
        self.assertNotIn("round_card", kinds(events))
        self.assertEqual(flow.round_asked, 10)
        self.assertEqual(flow.phase, "check")
        events = flow.submit("/back")
        self.assertIn("round_card", kinds(events))

    def test_cli_scheduler_drift_with_same_answer_stream(self):
        """Spy on the untouched terminal loop, then replay every input."""
        cli_quiz = E.HangulQuiz(persist=False)
        fixed_questions(cli_quiz)
        cli_trace, answers = [], []
        flags = {"round": False, "check": False, "offer": False,
                 "skips": 0, "requested": False, "check_object": None}
        original_round = CLI._round_card
        original_check = CLI._run_reading_check
        original_offer = CLI._offer_advance
        original_make = reading_check.make_reading_check

        def make_check(quiz):
            check = original_make(quiz)
            flags["check_object"] = check
            return check

        def spy_round(*args, **kwargs):
            cli_trace.append((len(answers), "round", args[1], args[2], args[3],
                              kwargs["no_progress"]))
            flags["round"] = True
            try:
                return original_round(*args, **kwargs)
            finally:
                flags["round"] = False

        def spy_check(*args, **kwargs):
            cli_trace.append((len(answers), "check", args[0].current_lesson["id"]))
            flags["check"] = True
            try:
                return original_check(*args, **kwargs)
            finally:
                flags["check"] = False

        def spy_offer(*args, **kwargs):
            cli_trace.append((len(answers), "advance", args[1]))
            flags["offer"] = True
            try:
                info = original_offer(*args, **kwargs)
            finally:
                flags["offer"] = False
            if info is not None:
                cli_trace.append((len(answers), "lesson", info["id"]))
            return info

        def terminal_input(prompt):
            if flags["round"]:
                answer = ""
            elif flags["check"]:
                answer = flags["check_object"].current.correct_answer
            elif flags["offer"]:
                answer = "y"
            elif flags["skips"] < 10:
                flags["skips"] += 1
                answer = "/skip"
            elif not flags["requested"]:
                solidify(cli_quiz)
                flags["requested"] = True
                answer = "/check"
            else:
                answer = "/quit"
            answers.append(answer)
            return answer

        random.seed(41)
        with patch.object(CLI, "input", side_effect=terminal_input), \
                patch.object(CLI, "_round_card", side_effect=spy_round), \
                patch.object(CLI, "_run_reading_check", side_effect=spy_check), \
                patch.object(CLI, "_offer_advance", side_effect=spy_offer), \
                patch.object(reading_check, "make_reading_check", side_effect=make_check), \
                patch.object(CLI, "print_question"), \
                patch.object(CLI, "print_lesson_intro_rich"), \
                patch.object(CLI, "print_reference_table"), \
                contextlib.redirect_stdout(io.StringIO()):
            CLI._interactive_loop_body(cli_quiz,
                                       SimpleNamespace(mode=None, sudden_death=False),
                                       cli_quiz.start_lesson(1), [], [])

        web_quiz = E.HangulQuiz(persist=False)
        fixed_questions(web_quiz)
        web_flow = C.CurriculumFlow(web_quiz)
        random.seed(41)
        web_flow.start()
        web_trace = []
        original_card_events = C.round_card_events
        turn = 0

        def spy_card_events(*args, **kwargs):
            web_trace.append((turn, "round", args[1], args[2], args[3],
                              kwargs["no_progress"]))
            return original_card_events(*args, **kwargs)

        with patch.object(C, "round_card_events", side_effect=spy_card_events):
            for turn, answer in enumerate(answers, start=1):
                if answer == "/check":
                    solidify(web_quiz)
                if (web_flow.phase == "check" and answer not in ("/check",)
                        and web_flow.check.check is not None
                        and web_flow.check.phase == "question"):
                    self.assertEqual(answer, web_flow.check.check.current.correct_answer)
                events = web_flow.submit(answer)
                kinds(events)
                for event in events:
                    if event["kind"] == "check_intro":
                        web_trace.append((turn, "check", web_quiz.current_lesson["id"]))
                    elif event["kind"] == "advance_prompt":
                        web_trace.append((turn, "advance", web_quiz.current_lesson["id"]))
                    elif event["kind"] == "lesson_started":
                        web_trace.append((turn, "lesson", event["lesson"]["id"]))
        self.assertEqual(cli_trace, web_trace)
        self.assertEqual(cli_quiz.current_lesson["id"], web_quiz.current_lesson["id"])
        self.assertEqual(answers[:10], ["/skip"] * 10)
        self.assertEqual(answers[10:12], ["", "/check"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
