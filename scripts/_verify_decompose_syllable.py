"""VERIFY — decompose_syllable mode (block -> jamo pair), added 2026-09.

WHEN TO RUN: after editing _decompose_syllable_question / _decomposition_choices
/ _normalize_jamo_pair, after changing the answer() grading or the
_compose_bare_vowel skip tuple, or after any curriculum pool change.

WHAT IT CHECKS (all sections print real values, not PASS/FAIL alone):
  (a) PROMPT/LEAK  — the prompt must show the BLOCK and never its jamo.
  (b) CHOICES      — 4 options, correct present, distractors are well-formed
                     'X + Y' pairs, no duplicates, correct not duplicated.
  (c) GRADING      — exact / spaced / comma variants = True; reversed order
                     = False; both components required.
  (d) GATING       — batchim lessons (10,11) and any bare-jamo pick must fall
                     back to 'spell', never serve an unanswerable prompt.
  (e) SWEEP        — all lessons x N calls: zero batchim, zero bare-jamo
                     targets ever reach a decompose_syllable question.
  (f) FALLBACK     — pool-less lesson degrades to spell.

RUN:  python scripts/_verify_decompose_syllable.py   (from repo root)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hangul_quiz_engine import HangulQuiz, _JAMO_CHARS

q = HangulQuiz()
fails = []


def check(label, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    if not ok:
        fails.append(label)
    print(f"   [{mark}] {label}{('  — ' + detail) if detail else ''}")


print("=" * 76)
print("(a) PROMPT / LEAK — prompt shows the block, never its jamo")
print("=" * 76)
lesson = q._get_lesson(5)
q.current_lesson = lesson
shown = 0
for _ in range(25):
    question = q._decompose_syllable_question(lesson)
    if question.mode != "decompose_syllable":
        continue
    shown += 1
    cho, jung, jong = q._decompose_syllable(question.letter)
    leaked = [j for j in (cho, jung) if j and j in question.prompt]
    if shown <= 4:
        print(f"   block={question.letter}  cho={cho} jung={jung} jong={jong!r}")
        print(f"      prompt={question.prompt!r}")
        print(f"      answer={question.correct_answer!r}  leaked={leaked}")
    check(f"prompt for {question.letter} does not leak {cho}/{jung}",
          not leaked, f"leaked={leaked}")
print(f"   ({shown} decompose_syllable questions sampled in lesson 5)")
check("at least one decompose_syllable question was served", shown > 0)

print()
print("=" * 76)
print("(b) CHOICES — well-formed, 4 options, correct present exactly once")
print("=" * 76)
for _ in range(15):
    question = q._decompose_syllable_question(lesson)
    if question.mode != "decompose_syllable":
        continue
    c = question.correct_answer
    bad_shape = [o for o in question.choices if " + " not in o]
    check(f"choices for {question.letter}: 4 options", len(question.choices) == 4,
          f"{question.choices}")
    check(f"choices for {question.letter}: correct present once",
          question.choices.count(c) == 1)
    check(f"choices for {question.letter}: no dupes",
          len(set(question.choices)) == len(question.choices))
    check(f"choices for {question.letter}: all 'X + Y' shaped", not bad_shape,
          f"bad={bad_shape}")
    print(f"      {question.letter} -> {c}   options={question.choices}")

print()
print("=" * 76)
print("(c) GRADING — normalization accepted, order enforced")
print("=" * 76)
question = None
for _ in range(30):
    cand = q._decompose_syllable_question(lesson)
    if cand.mode == "decompose_syllable":
        question = cand
        break
cho, jung, _j = q._decompose_syllable(question.letter)
expected = question.correct_answer
print(f"   block={question.letter}  expected={expected!r}")
cases = [
    (expected, True, "exact"),
    (f"{cho}+{jung}", True, "no spaces"),
    (f"{cho},{jung}", True, "comma"),
    (f"{cho}{jung}", True, "concatenated"),
    (f"  {cho}  {jung}  ", True, "extra whitespace"),
    (f"{jung} + {cho}", False, "REVERSED order (must fail)"),
    (cho, False, "consonant only"),
    (jung, False, "vowel only"),
    ("", False, "empty"),
]
for user_input, want, label in cases:
    res = q.answer(user_input, question=question)
    check(f"answer({user_input!r}) -> {label}", res.correct == want,
          f"got {res.correct}, feedback={res.feedback!r}")

print()
print("=" * 76)
print("(d) GATING — batchim lessons must fall back to spell")
print("=" * 76)
for lid in (10, 11):
    lesson_b = q._get_lesson(lid)
    q.current_lesson = lesson_b
    modes = [q._decompose_syllable_question(lesson_b).mode for _ in range(12)]
    check(f"lesson {lid} ({lesson_b.get('title')}) all spell",
          set(modes) == {"spell"}, f"modes={sorted(set(modes))}")

print()
print("=" * 76)
print("(e) SWEEP — every lesson x 20 calls: no batchim, no bare jamo target")
print("=" * 76)
leaks = []
served = 0
for lesson_s in q.curriculum["lessons"]:
    pool_s = lesson_s.get("practice_syllables") or lesson_s.get("example_syllables")
    if not pool_s:
        continue
    q.current_lesson = lesson_s
    for _ in range(20):
        question = q._decompose_syllable_question(lesson_s)
        if question.mode != "decompose_syllable":
            continue
        served += 1
        cho, jung, jong = q._decompose_syllable(question.letter)
        if jong:
            leaks.append(("batchim", lesson_s["id"], question.letter, jong))
        if not cho or not jung:
            leaks.append(("bare-jamo", lesson_s["id"], question.letter, ""))
    print(f"   lesson {lesson_s['id']:>2}: {len(pool_s)} pool items checked")
print(f"\n   decompose_syllable questions served across sweep: {served}")
print(f"   invalid targets that reached the mode: {len(leaks)}")
for leak in leaks:
    print(f"     LEAK: {leak}")
check("zero batchim/bare-jamo targets reached decompose_syllable", not leaks)

print()
print("=" * 76)
print("(f) FALLBACK — pool-less lesson degrades to spell")
print("=" * 76)
empty_lesson = {"id": 999, "title": "Empty", "letters": ["ㄱ"]}
q.current_lesson = empty_lesson
res_q = q._decompose_syllable_question(empty_lesson)
check("no-pool lesson -> spell", res_q.mode == "spell", f"mode={res_q.mode}")

print()
print("=" * 76)
print(f"RESULT: {'ALL PASS' if not fails else str(len(fails)) + ' FAILURE(S)'}")
if fails:
    for f in fails:
        print(f"   - {f}")
print("=" * 76)
