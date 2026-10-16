"""Checks for the file-free engine boundary used by a browser front end."""

import json
import random
import sys
import tempfile
from collections import Counter
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hangul_quiz_engine as engine
from reading_check import make_reading_check, save_check_result


BATCH_0 = {
    "id": 0, "title": "The Revelation", "letters": ["ㄴ", "ㄷ", "ㅏ", "ㅗ"],
    "practice_syllables": ["나", "노", "다", "도"],
    "mastery_syllables": ["나", "노", "다", "도"],
    "confusion_pairs": [["ㄴ", "ㄷ"], ["ㅏ", "ㅗ"]], "pronunciation": {},
}


def batch_1(quiz):
    letters = ["ㄴ", "ㄷ", "ㅁ", "ㅂ", "ㅏ", "ㅗ", "ㅓ", "ㅜ"]
    blocks = [quiz._compose_syllable(c, v) for c in letters[:4] for v in letters[4:]]
    assert len(blocks) == 16
    return {"id": 0, "title": "First Words", "letters": letters,
            "practice_syllables": blocks, "mastery_syllables": blocks,
            "confusion_pairs": [["ㄴ", "ㄷ"], ["ㅏ", "ㅗ"]], "pronunciation": {}}


def assert_target_uses_letters(quiz, target, letters):
    allowed = set(letters)
    assert target, "question has no target"
    for block in target:
        if block in allowed:
            continue
        cho, jung, jong = quiz._decompose_syllable(block)
        assert cho in allowed and jung in allowed and not jong, (target, block)


def test_no_file_io():
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "progress.json"
        path.write_bytes(b"existing profile")
        before = (path.stat().st_mtime_ns, path.read_bytes())
        with patch.object(engine, "PROGRESS_PATH", path), \
             patch("builtins.print", side_effect=AssertionError("engine printed")):
            quiz = engine.HangulQuiz(persist=False)
            quiz.start_lesson(1)
            for _ in range(20):
                question = quiz.next_question()
                quiz.answer(question.correct_answer, question)
            quiz.save_progress()
        assert (path.stat().st_mtime_ns, path.read_bytes()) == before
        assert quiz.progress["total_questions_answered"] == 20


def test_round_trip():
    quiz = engine.HangulQuiz(persist=False)
    quiz.start_lesson(1)
    for _ in range(30):
        question = quiz.next_question()
        quiz.answer(question.correct_answer, question)
    state = quiz.export_state()
    restored = engine.HangulQuiz(persist=False)
    restored.import_state(state)
    assert quiz.progress == restored.progress
    assert restored.progress["total_questions_answered"] == 30


def test_migration():
    old = {"schema_version": 1, "current_lesson": 1, "completed_lessons": [],
           "mastered_letters": {"ㅏ": 3}, "confusion_counts": {}}
    quiz = engine.HangulQuiz(persist=False)
    quiz.import_state(json.dumps(old, ensure_ascii=False))
    assert quiz.progress["schema_version"] == engine.CURRENT_SCHEMA_VERSION == 3
    assert quiz.progress["learner_items"]["ㅏ"]["_migrated_confidence"] == 3


def test_bad_input():
    quiz = engine.HangulQuiz(persist=False)
    for text in ("not json", "[]"):
        try:
            quiz.import_state(text)
        except ValueError:
            pass
        else:
            raise AssertionError(f"accepted invalid progress: {text!r}")


def test_newer_version():
    future = {"schema_version": engine.CURRENT_SCHEMA_VERSION + 1,
              "future_field": {"keep": [1, 2, 3]}}
    quiz = engine.HangulQuiz(persist=False)
    quiz.import_state(json.dumps(future))
    quiz.session_total = 5
    quiz.save_progress()
    assert quiz._progress_read_only
    assert json.loads(quiz.export_state()) == future


def exercise_custom(lesson):
    quiz = engine.HangulQuiz(persist=False)
    prior_position = quiz.progress["current_lesson"]
    prior_completed = list(quiz.progress["completed_lessons"])
    info = quiz.start_custom_lesson(lesson)
    assert info["id"] == 0 and info["title"] == lesson["title"]
    assert quiz.progress["current_lesson"] == prior_position
    modes = Counter()
    random.seed(1)
    for _ in range(200):
        question = quiz.next_question()
        assert_target_uses_letters(quiz, question.letter, lesson["letters"])
        if question.mode == "missing_vowel":
            assert set(question.choices) <= set(lesson["letters"])
        quiz.answer(question.correct_answer, question)
        modes[question.mode] += 1
    assert quiz.progress["current_lesson"] == prior_position
    assert quiz.progress["completed_lessons"] == prior_completed
    return quiz, ", ".join(f"{mode}={count}" for mode, count in sorted(modes.items()))


def test_batch_0():
    _, modes = exercise_custom(BATCH_0)
    return modes


def test_batch_1():
    seed_quiz = engine.HangulQuiz(persist=False)
    _, modes = exercise_custom(batch_1(seed_quiz))
    return modes


def test_reading_checks():
    for lesson in (BATCH_0, batch_1(engine.HangulQuiz(persist=False))):
        quiz = engine.HangulQuiz(persist=False)
        quiz.start_custom_lesson(lesson)
        check = make_reading_check(quiz)
        assert len(check.questions) == 5
        assert len({question.letter for question in check.questions}) == 5
        assert not set(check.transfer_targets) & set(lesson["practice_syllables"])
        for question in check.questions:
            assert_target_uses_letters(quiz, question.letter, lesson["letters"])


def test_custom_completion_guard():
    quiz = engine.HangulQuiz(persist=False)
    quiz.start_custom_lesson(BATCH_0)
    for target in BATCH_0["mastery_syllables"]:
        item = quiz._get_item(target)
        item.history = "111"
        quiz._save_item(item)
    assert quiz.lesson_mastery()["is_mastered"]
    quiz.progress["reading_checks"] = {"0": {"passed": True}}
    before = (quiz.progress["current_lesson"], list(quiz.progress["completed_lessons"]))
    quiz.complete_lesson()
    assert (quiz.progress["current_lesson"], quiz.progress["completed_lessons"]) == before
    check = make_reading_check(quiz)
    while not check.finished:
        check.submit(check.current.correct_answer)
    assert check.passed
    save_check_result(quiz, check)
    assert quiz.progress["completed_lessons"] == before[1]


if __name__ == "__main__":
    checks = [
        ("persist=False leaves files untouched and counts 20 answers", test_no_file_io),
        ("30-answer JSON round trip", test_round_trip),
        ("schema 1 migrates to schema 3", test_migration),
        ("bad JSON and non-object are rejected", test_bad_input),
        ("newer schema remains read-only and unchanged", test_newer_version),
        ("Batch 0: 200 correct answers", test_batch_0),
        ("Batch 1: 200 correct answers", test_batch_1),
        ("both custom reading checks have five distinct taught targets", test_reading_checks),
        ("custom lesson cannot complete curriculum lesson 0", test_custom_completion_guard),
    ]
    for name, check in checks:
        detail = check()
        print(f"PASS {name}" + (f" | {detail}" if detail else ""))
    print(f"ALL PASS: {len(checks)} checks")
