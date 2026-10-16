"""Independent-reading checks through the real engine and CLI, using temp data.

Run: python scripts/_verify_reading_check.py
"""

import contextlib
import io
import random
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hangul_quiz_engine as E
import hangul_cli as CLI
from reading_check import make_reading_check, save_check_result


class ReadingChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path_patch = patch.object(E, "PROGRESS_PATH", Path(self.tmp.name) / "p.json")
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)
        self.q = E.HangulQuiz()
        self.q.start_lesson(1)
        random.seed(7)

    def ready(self, lid=1):
        self.q.start_lesson(lid)
        for target in self.q._mastery_set(self.q.current_lesson):
            item = self.q._get_item(self.q._compose_bare_vowel(target))
            item.history = "111"
            self.q._save_item(item)

    def answer_all(self, check, misses=0):
        for i in range(5):
            check.submit("wrong" if i < misses else check.current.correct_answer)

    def test_recognition_alone_cannot_complete_or_skip_into_completion(self):
        for _ in range(100):
            q = self.q.next_question(mode="match_sound")
            self.q.answer(q.correct_answer, q)
            if self.q.lesson_mastery()["is_mastered"]:
                break
        self.assertTrue(self.q.lesson_mastery()["is_mastered"])
        self.q.complete_lesson()
        self.assertNotIn(1, self.q.progress["completed_lessons"])
        with patch.object(CLI.time, "sleep"), contextlib.redirect_stdout(io.StringIO()):
            CLI._go_to_next_lesson(self.q)
        self.assertEqual(self.q.current_lesson["id"], 2)
        self.assertNotIn(1, self.q.progress["completed_lessons"])

    def test_all_lessons_have_five_unique_answerable_prompts(self):
        for seed in range(15):
            random.seed(seed)
            for lid in range(1, 13):
                with self.subTest(seed=seed, lesson=lid):
                    self.q.start_lesson(lid)
                    check = make_reading_check(self.q)
                    self.assertEqual(len(check.questions), 5)
                    self.assertEqual(len({q.letter for q in check.questions}), 5)
                    self.assertEqual(len(check.transfer_targets), 2)
                    for q in check.questions:
                        self.assertEqual(q.choices, [])
                        self.assertIn(E.normalize_roman(q.correct_answer), q.accepted)
                        self.assertEqual(q.prompt.count("**"), 2)
                        self.assertIn("**" + q.letter + "**", q.prompt)
                    for target in check.transfer_targets:
                        self.assertTrue(self.q._safe_nonword_boundaries(target, self.q.current_lesson))

    def test_generated_components_are_taught_and_new(self):
        for lid in range(1, 13):
            self.q.start_lesson(lid)
            pool = self.q._get_lesson_syllable_pool(self.q.current_lesson)
            components = [self.q._decompose_syllable(s) for s in pool]
            allowed = [set(p[i] for p in components) for i in range(3)]
            for target in make_reading_check(self.q).transfer_targets:
                self.assertNotIn(target, pool)
                for ch in target:
                    for i, part in enumerate(self.q._decompose_syllable(ch)):
                        self.assertIn(part, allowed[i])

    def test_new_combinations_do_not_repeat_exposed_items(self):
        first = make_reading_check(self.q)
        self.q.progress["reading_check_seen"] = [q.letter for q in first.questions]
        second = make_reading_check(self.q)
        self.assertFalse(set(first.transfer_targets) & set(second.transfer_targets))

    def test_four_of_five_passes_and_survives_reload_without_advancing(self):
        self.ready()
        check = make_reading_check(self.q)
        self.answer_all(check, misses=1)
        save_check_result(self.q, check)
        loaded = E.HangulQuiz()
        self.assertTrue(loaded.reading_check_passed(1))
        self.assertIn(1, loaded.progress["completed_lessons"])
        self.assertEqual(loaded.progress["current_lesson"], 1)
        self.assertEqual(loaded.progress["reading_checks"]["1"]["last_score"], 4)

    def test_three_of_five_does_not_complete(self):
        self.ready()
        check = make_reading_check(self.q)
        self.answer_all(check, misses=2)
        save_check_result(self.q, check)
        self.assertFalse(self.q.reading_check_passed())
        self.assertNotIn(1, self.q.progress["completed_lessons"])

    def test_hints_require_independent_retry_and_cannot_loop_forever(self):
        check = make_reading_check(self.q)
        target = check.current.letter
        check.submit(check.current.correct_answer, assisted=True)
        self.assertNotIn(target, check.correct)
        while check.index < 5:
            check.submit(check.current.correct_answer)
        self.assertFalse(check.finished)
        self.assertEqual(check.current.letter, target)
        check.submit(check.current.correct_answer, assisted=True)
        self.assertTrue(check.finished)
        self.assertNotIn(target, check.correct)
        self.assertEqual(len(check.questions), 6)
        # Four OTHER independently read prompts may still pass the 4/5 rule.
        self.assertTrue(check.passed)

    def test_independent_hint_retry_counts_only_once(self):
        check = make_reading_check(self.q)
        check.submit(check.current.correct_answer, assisted=True)
        while not check.finished:
            check.submit(check.current.correct_answer)
        self.assertEqual(len(check.correct), 5)

    def test_interrupted_check_has_no_result_or_completion(self):
        self.ready()
        check = make_reading_check(self.q)
        for _ in range(4):
            check.submit(check.current.correct_answer)
        save_check_result(self.q, check)
        self.assertFalse(check.passed)
        self.assertNotIn("reading_checks", self.q.progress)
        self.assertNotIn(1, self.q.progress["completed_lessons"])

    def test_existing_completions_are_preserved(self):
        self.q.progress["completed_lessons"] = [1, 2]
        self.q.save_progress()
        loaded = E.HangulQuiz()
        loaded.start_lesson(2)
        loaded.complete_lesson()
        self.assertEqual(loaded.progress["completed_lessons"], [1, 2])
        self.assertEqual(loaded.progress["current_lesson"], 3)

    def test_check_answers_do_not_inflate_practice_scores(self):
        check = make_reading_check(self.q)
        self.answer_all(check)
        self.assertEqual(self.q.session_total, 0)
        self.assertEqual(self.q.progress["learner_items"], {})

    def test_natural_romanizations_are_accepted(self):
        self.q.start_lesson(12)
        self.q.current_lesson = dict(self.q.current_lesson,
                                     mastery_words=["한글", "사랑", "김치"])
        check = make_reading_check(self.q)
        q = next(q for q in check.questions if q.letter == "한글")
        self.assertIn("hangul", q.accepted)
        self.assertIn("hangeul", q.accepted)

    def test_real_cli_pass_then_stay_records_completion(self):
        self.ready()
        active = []
        original = make_reading_check

        def build(quiz):
            check = original(quiz)
            active.append(check)
            return check

        def answer(prompt):
            if active and not active[-1].finished:
                return active[-1].current.correct_answer
            if "Move on" in prompt:
                return "n"
            return "/quit"

        args = SimpleNamespace(mode=None, sudden_death=False)
        with patch("reading_check.make_reading_check", side_effect=build), \
                patch.object(CLI, "input", side_effect=answer), \
                patch.object(CLI.time, "sleep"), \
                contextlib.redirect_stdout(io.StringIO()):
            CLI._interactive_loop_body(self.q, args, self.q.start_lesson(1), [], [])
        self.assertIn(1, self.q.progress["completed_lessons"])
        self.assertEqual(self.q.current_lesson["id"], 1)
        self.assertTrue(self.q.reading_check_passed())

    def test_cli_hints_skips_and_quit_do_not_grant_completion(self):
        self.ready()
        answers = iter(["/hint", "/skip", "/quit"])
        out = io.StringIO()
        with patch.object(CLI, "_ask", side_effect=lambda _: next(answers)), \
                contextlib.redirect_stdout(out):
            self.assertEqual(CLI._run_reading_check(self.q), "quit")
        self.assertNotIn(1, self.q.progress["completed_lessons"])
        self.assertNotIn("reading_checks", self.q.progress)
        self.assertTrue(self.q.progress["reading_check_seen"])

    def test_cli_passes_and_keeps_round_statistics_separate(self):
        self.ready()
        check = make_reading_check(self.q)
        answers = iter([q.correct_answer for q in check.questions])
        with patch("reading_check.make_reading_check", return_value=check), \
                patch.object(CLI, "_ask", side_effect=lambda _: next(answers)), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(CLI._run_reading_check(self.q), "passed")
        self.assertIn(1, self.q.progress["completed_lessons"])
        self.assertEqual(self.q.session_total, 0)

    def test_cli_failed_check_offers_targeted_practice_then_new_check(self):
        self.ready()
        first, second = make_reading_check(self.q), make_reading_check(self.q)
        answers = iter(["wrong"] * 5 + ["wrong"] * 3 + ["r"] +
                       [q.correct_answer for q in second.questions])
        out = io.StringIO()
        with patch("reading_check.make_reading_check", side_effect=[first, second]), \
                patch.object(CLI, "_ask", side_effect=lambda _: next(answers)), \
                contextlib.redirect_stdout(out):
            self.assertEqual(CLI._run_reading_check(self.q), "passed")
        self.assertIn("practise the tricky ones", out.getvalue())
        self.assertEqual(self.q.progress["reading_checks"]["1"]["attempts"], 2)

    def test_resume_ready_profile_enters_check_before_normal_question(self):
        self.ready()
        info = self.q.start_lesson(1)
        args = SimpleNamespace(mode=None, sudden_death=False)
        with patch.object(CLI, "_run_reading_check", return_value="quit") as run, \
                patch.object(CLI, "print_reference_table") as table, \
                patch.object(CLI, "print_lesson_intro_rich"), \
                patch.object(self.q, "next_question") as next_question:
            CLI._interactive_loop_body(self.q, args, info, [], [])
        run.assert_called_once()
        table.assert_not_called()
        next_question.assert_not_called()

    def test_round_card_and_exit_summary_do_not_claim_recognition_completion(self):
        self.ready()
        out = io.StringIO()
        with patch.object(CLI, "_ask", return_value="r"), contextlib.redirect_stdout(out):
            self.assertEqual(CLI._round_card(self.q, 1, 10, 10), "check")
        self.assertNotIn("Lesson 1 is done", out.getvalue())
        with patch.object(CLI, "print_lesson_complete") as complete, \
                contextlib.redirect_stdout(io.StringIO()):
            CLI._print_session_summary(self.q)
        complete.assert_not_called()

    def test_misses_are_marked_not_yet_with_what_was_typed(self):
        self.ready()
        check = make_reading_check(self.q)
        answers = iter(["wrong"] * 5 + ["x"] * 3 + [""])
        out = io.StringIO()
        with patch("reading_check.make_reading_check", return_value=check), \
                patch.object(CLI, "_ask", side_effect=lambda _: next(answers)), \
                contextlib.redirect_stdout(out):
            self.assertEqual(CLI._run_reading_check(self.q), "practice")
        text = out.getvalue()
        self.assertIn("Not yet", text)
        self.assertIn("you typed 'wrong'", text)
        self.assertIn("you need 4", text)

    def test_targeted_practice_asks_before_revealing_the_answer(self):
        self.ready()
        check = make_reading_check(self.q)
        seen = []
        answers = iter(["wrong"] * 5 + ["x"] * 3 + [""])
        out = io.StringIO()

        def ask(prompt):
            if "Try its sound" in prompt:
                seen.append(out.getvalue().split("practise the tricky ones")[-1])
            return next(answers)

        with patch("reading_check.make_reading_check", return_value=check), \
                patch.object(CLI, "_ask", side_effect=ask), \
                contextlib.redirect_stdout(out):
            CLI._run_reading_check(self.q)
        self.assertEqual(len(seen), 3)
        self.assertNotIn("\u2192", seen[0])

    def test_round_card_accepts_check_on_a_completed_lesson(self):
        self.q.progress["completed_lessons"].append(1)
        with patch.object(CLI, "_ask", return_value="/check"), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(CLI._round_card(self.q, 1, 10, 10), "check")
        with patch.object(CLI, "_ask", return_value=""), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(CLI._round_card(self.q, 1, 10, 10), "continue")


if __name__ == "__main__":
    unittest.main(verbosity=2)
