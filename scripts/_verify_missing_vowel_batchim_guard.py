"""VERIFY — the batchim guard in _missing_vowel_question (added 2026-09).

WHEN TO RUN: after editing _missing_vowel_question, or after any change to
_decompose_syllable / lesson pool data that could re-admit batchim syllables.

WHAT IT CHECKS (four sections, all print real values — not PASS/FAIL alone):
  (a) batchim lessons 10-11 -> every call must fall back to mode 'spell'
  (b) bare-CV lessons 5,7   -> mode 'missing_vowel' retained (no regression)
  (c) grading: correct answer still grades True, a wrong vowel grades False
  (d) exhaustive sweep: all 11 lessons x 20 calls, asserting ZERO batchim
      syllables ever reach a missing_vowel question

CAVEAT — read before trusting section (b): this probe intermittently reports
'spell' for a bare-CV lesson, and that is NOT the batchim guard failing. It is a
SEPARATE, still-unfixed bug: `_select_from_pool` can return a bare jamo (not a
composed block), `_decompose_syllable` then returns ('','',''), jong is falsy so
the guard passes, and the prompt is built with an empty vowel. If you see
'spell' on lesson 5/7, confirm which cause applies before reporting a failure.

RUN:  python scripts/_verify_missing_vowel_batchim_guard.py   (from repo root)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hangul_quiz_engine import HangulQuiz

q = HangulQuiz()

def probe(lesson_id, n=12):
    lesson = q._get_lesson(lesson_id)
    q.current_lesson = lesson
    modes, samples = [], []
    for _ in range(n):
        question = q._missing_vowel_question(lesson)
        modes.append(question.mode)
        if len(samples) < 3:
            samples.append(question)
    return lesson, modes, samples

print("=" * 76)
print("(a) BATCHIM LESSONS — expect mode 'spell' every time (guard fires)")
print("=" * 76)
for lid in (10, 11):
    lesson, modes, samples = probe(lid)
    pool = lesson.get("practice_syllables") or lesson.get("example_syllables")
    print(f"\nlesson {lid}: {lesson.get('title')}   pool={len(pool)}")
    print(f"  pool contents: {' '.join(pool)}")
    print(f"  modes over 12 calls: {modes}")
    print(f"  distinct modes: {sorted(set(modes))}")
    verdict = "PASS (all spell)" if set(modes) == {"spell"} else "FAIL"
    print(f"  -> {verdict}")
    for s in samples[:2]:
        print(f"     sample: mode={s.mode}  prompt={s.prompt[:70]!r}")

print()
print("=" * 76)
print("(b) BARE-CV LESSONS — expect mode 'missing_vowel' retained (no regression)")
print("=" * 76)
for lid in (5, 7):
    lesson, modes, samples = probe(lid)
    pool = lesson.get("practice_syllables") or lesson.get("example_syllables")
    print(f"\nlesson {lid}: {lesson.get('title')}   pool={len(pool)}")
    print(f"  modes over 12 calls: {modes}")
    print(f"  distinct modes: {sorted(set(modes))}")
    verdict = "PASS (all missing_vowel)" if set(modes) == {"missing_vowel"} else "FAIL"
    print(f"  -> {verdict}")
    s = samples[0]
    print(f"     sample: mode={s.mode}")
    print(f"             prompt={s.prompt!r}")
    print(f"             correct_answer={s.correct_answer!r}  choices={s.choices}")

print()
print("=" * 76)
print("(c) GRADING CHECK — bare-CV missing_vowel still grades correct/incorrect")
print("=" * 76)
lesson = q._get_lesson(5)
q.current_lesson = lesson
question = q._missing_vowel_question(lesson)
print(f"target block      : {question.letter}")
print(f"correct_answer    : {question.correct_answer!r}")
print(f"choices           : {question.choices}")
res_ok = q.answer(question.correct_answer, question=question)
print(f"answer(correct)   -> correct={res_ok.correct}  feedback={res_ok.feedback}")
wrong = [c for c in question.choices if c != question.correct_answer][0]
res_bad = q.answer(wrong, question=question)
print(f"answer({wrong!r})   -> correct={res_bad.correct}  feedback={res_bad.feedback}")

print()
print("=" * 76)
print("(d) EXHAUSTIVE — every lesson, 20 calls, confirm zero batchim leaks")
print("=" * 76)
leaks = []
for lesson in q.curriculum["lessons"]:
    pool = lesson.get("practice_syllables") or lesson.get("example_syllables")
    if not pool:
        continue
    q.current_lesson = lesson
    for _ in range(20):
        question = q._missing_vowel_question(lesson)
        if question.mode != "missing_vowel":
            continue
        cho, jung, jong = q._decompose_syllable(question.letter)
        if jong:
            leaks.append((lesson["id"], question.letter, jong))
    print(f"  lesson {lesson['id']:>2}: checked 20 calls")
print(f"\n  batchim syllables that leaked through as missing_vowel: {len(leaks)}")
if leaks:
    for leak in leaks:
        print(f"    LEAK: lesson {leak[0]} syllable {leak[1]} jong={leak[2]}")
else:
    print("  -> PASS: no batchim syllable ever served as a missing_vowel question")
