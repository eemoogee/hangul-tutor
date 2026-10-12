"""
Regression checks for the 2026-09 bug-fix / gameplay pass.

Run from the repo root:   python scripts/_verify_gameplay_fixes.py

Uses a throwaway progress file, so it never touches data/user_progress.json.
Prints PASS/FAIL per check and exits non-zero if anything fails.
"""

import io
import json
import random
import sys
import tempfile
import contextlib
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import hangul_quiz_engine as E  # noqa: E402

TMP = Path(tempfile.mkdtemp())
E.PROGRESS_PATH = TMP / "user_progress.json"

import hangul_rain as R  # noqa: E402
import hangul_conversation as C  # noqa: E402

random.seed(1234)
failures = []


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def fresh():
    if E.PROGRESS_PATH.exists():
        E.PROGRESS_PATH.unlink()
    return E.HangulQuiz()


print("Progress saving")
q = fresh()
q.start_lesson(2)
for _ in range(3):
    qq = q.next_question()
    q.answer(qq.correct_answer, qq)
q.save_progress()
q.save_progress()          # complete_lesson() + per-answer saves = many saves
q.complete_lesson()
check("totals counted once across repeated saves",
      q.progress["total_questions_answered"] == 3, q.progress["total_questions_answered"])

q = fresh()
q.start_lesson(2)
for _ in range(4):
    qq = q.next_question()
    q.answer(qq.correct_answer, qq)
qq = q.next_question()
q.answer("zzz", qq)
q.save_progress()
check("best streak survives a later miss", q.progress["streak_best"] == 4, q.progress["streak_best"])

E.PROGRESS_PATH.write_text("{not json", encoding="utf-8")
with contextlib.redirect_stdout(io.StringIO()):
    q = E.HangulQuiz()
check("corrupt progress file -> fresh start + backup kept",
      q.progress["current_lesson"] == 1 and any(TMP.glob("user_progress.backup-*.json")))

print("Grading")
q = fresh()
for lid in range(1, 13):
    q.start_lesson(lid)
    bad = []
    for _ in range(150):
        qq = q.next_question()
        if not q.answer(qq.correct_answer, qq).correct:
            bad.append((qq.mode, qq.correct_answer))
    check(f"lesson {lid}: every mode accepts its own answer", not bad, bad[:3])

q.start_lesson(2)
spell = q._spell_question(q.current_lesson)
roman = q._hangul_to_roman_hint(spell.correct_answer)
check("spell: copying the shown romanization is re-prompted, not graded",
      q.script_mismatch(roman, spell) is not None)
check("spell: an A-D letter is still a valid answer", q.script_mismatch("B", spell) is None)

ra = E.QuizQuestion(mode="read_aloud", prompt="", correct_answer="ra",
                    accepted=sorted(q.roman_variants("라")), letter="라")
check("read_aloud: 'la' accepted for 라", q.answer("la", ra).correct)
si = E.QuizQuestion(mode="read_aloud", prompt="", correct_answer="si",
                    accepted=sorted(q.roman_variants("시")), letter="시")
check("read_aloud: 'shi' accepted for 시", q.answer("shi", si).correct)
check("bare ㄹ accepts 'r' and 'l'", {"r", "l"} <= q.roman_variants("ㄹ"))

mv = E.QuizQuestion(mode="missing_vowel", prompt="", correct_answer="ㅗ",
                    choices=["ㅗ", "ㅏ", "ㅜ", "ㅣ"], letter="노")
check("missing_vowel: 오 accepted for ㅗ", q.answer("오", mv).correct)

q.start_lesson(2)
early = set()
for _ in range(200):
    mq = q._missing_vowel_question(q.current_lesson)
    if mq.mode == "missing_vowel":
        early |= set(mq.choices)
check("missing_vowel (lesson 2): only taught vowels offered",
      early <= set("ㅏㅓㅗㅜㅡㅣ"), early - set("ㅏㅓㅗㅜㅡㅣ"))

print("Batchim questions are answerable")
for lid in (10, 11):
    q.start_lesson(lid)
    dirs = Counter()
    ok = True
    for _ in range(300):
        bq = q._batchim_question(q.current_lesson)
        dirs[bq.direction] += 1
        if bq.direction == "sound_to_letter":
            sounds = [q._batchim_sound(c) for c in bq.choices]
            ok &= len(set(sounds)) == len(sounds)      # one letter per sound
        else:
            ok &= bq.correct_answer in bq.choices
            ok &= len(set(bq.choices)) == len(bq.choices)
    check(f"lesson {lid}: exactly one defensible answer per question", ok)
    check(f"lesson {lid}: both question forms appear", len(dirs) == 2, dict(dirs))

print("Confusion drills")
for lid in range(1, 13):
    q.start_lesson(lid)
    same = set()
    for _ in range(60):
        cq = q._confusion_drill_question()
        if cq.mode == "confusion_drill" and \
                q._hangul_to_roman_hint(cq.letter) == q._hangul_to_roman_hint(cq.other):
            same.add((cq.letter, cq.other))
    check(f"lesson {lid}: drilled pair always romanizes differently", not same, same)

print("Konglish")
cats = set(q.LOANWORD_CATEGORIES)
vocab = q.get_konglish_vocab()["categories"]
loan_ko = {w["ko"] for c in cats for w in vocab[c]}
seen = {q.konglish_question().letter for _ in range(300)}
check("decode questions only use loanwords", seen <= loan_ko)
check("'mouse' accepted for 'mouse (computer)'",
      q.check_konglish("mouse", E.QuizQuestion(mode="konglish", prompt="", correct_answer="mouse (computer)")))
check("empty answer is never correct",
      not q.check_konglish("", E.QuizQuestion(mode="konglish", prompt="", correct_answer="banana")))
dup = 0
for _ in range(300):
    kq = q.konglish_spell_question()
    meaning = q.konglish_answers(kq.correct_answer and next(
        w["en"] for c in cats for w in vocab[c] if w["ko"] == kq.correct_answer))
    for ch in kq.choices:
        if ch == kq.correct_answer:
            continue
        other = next(w["en"] for c in cats for w in vocab[c] if w["ko"] == ch)
        dup += bool(q.konglish_answers(other) & meaning)
check("kspell never offers a second correct spelling", dup == 0, dup)

print("Content")
wc = json.loads((ROOT / "data" / "word_contrasts.json").read_text(encoding="utf-8"))
check("word contrast example uses 씻어요 (to wash)",
      any(i["example_ko"] == "손을 씻어요." for e in wc for i in e["items"]))

print("Conversation")
q = fresh()
q.start_lesson(1)
check("/talk with <3 mastered syllables returns None (no fake translation)",
      C.generate_conversation_turn(q, use_llm=False) is None)
res = C.check_conversation_answer("it is a dog", {"mode": "read_translate", "english": "it is a cat"}, q)
check("translation check ignores filler-word overlap", not res["correct"])

print("Lesson content (2026-10 content pass)")
q = fresh()
bad, thin = [], []
for lesson in q.curriculum["lessons"]:
    for w in lesson.get("words", []):
        r = q.readable_from(w["word"])
        if r is None or r > lesson["id"]:
            bad.append((lesson["id"], w["word"], r))
    if lesson["id"] <= 11 and len(lesson.get("words", [])) < 4:
        thin.append(lesson["id"])
check("every lesson word uses only letters taught by its lesson", not bad, bad[:5])
check("lessons 1-11 each have at least 4 real words", not thin, thin)

q.start_lesson(3)
check("손/선 (final consonants) not offered before batchim is taught",
      all(e["items"][0]["form"] != "손" for e in q._available_word_contrasts()))
q.start_lesson(10)
check("손/선 offered once batchim is taught",
      any(e["items"][0]["form"] == "손" for e in q._available_word_contrasts()))

q.start_lesson(4)
rw = q._real_word_question(q.current_lesson)
res = q.answer(rw.correct_answer, rw)
check("real word: reading it right is graded right", res.correct, rw)
check("real word: the meaning is revealed", rw.meaning and rw.meaning in res.feedback, res.feedback)
q.start_lesson(10)
kimchi = E.QuizQuestion(mode="real_word", prompt="", correct_answer="gimchi",
                        accepted=sorted(q.roman_variants("김치") | {"kimchi"}), letter="김치")
check("real word: 'kimchi' accepted for 김치", q.answer("kimchi", kimchi).correct)

lesson_words = {w["word"] for l in q.curriculum["lessons"] for w in l.get("words", [])}
check("lesson words count as real words (never served as 'not a real word')",
      lesson_words <= q.known_lexical_items, sorted(lesson_words - q.known_lexical_items)[:5])

with contextlib.redirect_stdout(io.StringIO()):
    import hangul_cli as CLI
taught = [x for l in q.curriculum["lessons"] if l["id"] <= 9 for x in l.get("letters", [])]
missing = [x for x in taught if x not in CLI.ALPHABET_MNEMONICS]
check("every letter taught in lessons 1-9 has a mnemonic", not missing, missing)
errors = []
for lesson in q.curriculum["lessons"]:
    info = q.start_lesson(lesson["id"])
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            import time as _t
            _sleep, _t.sleep = _t.sleep, (lambda *_: None)
            try:
                CLI.print_lesson_intro_rich(info, q)
                CLI.print_reference_table(q, info)
            finally:
                _t.sleep = _sleep
    except Exception as e:
        errors.append((lesson["id"], repr(e)))
check("every lesson's intro and reference table render", not errors, errors)

print("Question mix (found by scripts/_playtest_learners.py)")
q = fresh()
q.start_lesson(2)
mix = Counter(q.next_question().mode for _ in range(2000))
special = sum(mix[m] for m in ("confusion_drill", "word_contrast", "nonword_decode", "sequence_decode"))
check("special modes get real airtime (were ~0%)", 0.12 <= special / 2000 <= 0.30, dict(mix))
check("confusion drills appear without any recorded mistakes", mix["confusion_drill"] > 0, dict(mix))

for lid in (10, 11):
    q.start_lesson(lid)
    asked = Counter()
    inner = q._generate_question
    q._generate_question = lambda m, inner=inner: (asked.update([m]), inner(m))[1]
    for _ in range(500):
        q.next_question()
    q._generate_question = inner
    check(f"lesson {lid}: no missing_vowel/decompose picked only to become spell",
          asked["missing_vowel"] == 0 and asked["decompose_syllable"] == 0, dict(asked))

q = fresh()
q.start_lesson(1)
for _ in range(3):
    q.answer("오", E.QuizQuestion(mode="match_sound", prompt="", correct_answer="어",
                                 choices=["어", "오", "아", "우"], letter="어"))
check("lesson 1: a 어/오 mix-up counts as relevant to lesson 1", q._relevant_tracked_pair() is not None)
pairs = Counter(frozenset((d.letter, d.other)) for d in (q._confusion_drill_question() for _ in range(100)))
check("lesson 1: the drill targets the learner's own 어/오 mix-up",
      pairs.most_common(1)[0][0] == frozenset(("어", "오")), pairs.most_common(3))

q = fresh()
q.start_lesson(1)
q.answer("o", E.QuizQuestion(mode="read_aloud", prompt="", correct_answer="eo",
                             accepted=["eo"], letter="어"))
check("read-aloud: reading 어 as 'o' records a 어/오 mix-up",
      "어↔오" in q._pairs_from_learner_items())
q.answer("zzz", E.QuizQuestion(mode="read_aloud", prompt="", correct_answer="a",
                               accepted=["a"], letter="아"))
check("read-aloud: a typo is not recorded as a mix-up",
      all("아" not in k for k in q._pairs_from_learner_items()))

with contextlib.redirect_stdout(io.StringIO()):
    import hangul_cli as CLI
import re as _re
_ansi = _re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
q = fresh()
q.start_lesson(1)
leaks = 0
for _ in range(40):
    d = q._confusion_drill_question()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        CLI.print_question(d, q)
    # Skip the A-D choice lines and the footer ("...if you want a hint"
    # contains a standalone 'a', which isn't a leak).
    screen = "\n".join(l for l in _ansi.sub("", buf.getvalue()).splitlines()
                       if "/hint" not in l and "type the answer" not in l)
    sound = q._hangul_to_roman_hint(d.correct_answer)
    leaks += len(_re.findall(rf"(?<![a-z]){sound}(?![a-z])", screen)) > 1
check("confusion drill doesn't print each block's sound next to it", leaks == 0, leaks)

q.start_lesson(2)
leaks = 0
for _ in range(200):
    wq = q._generate_question("word_contrast")
    if wq.contrast_type != "lexical_vs_grammar_form" or wq.direction != "word_to_meaning":
        continue
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        CLI.print_question(wq, q)
    screen = _ansi.sub("", buf.getvalue()).lower()
    screen = "\n".join(l for l in screen.splitlines() if not _re.match(r"\s+[a-d]\)", l))
    leaks += any(_re.search(rf"\b{w}\b", screen) for w in _re.findall(r"[a-z]{3,}", wq.correct_answer.lower()))
check("word contrast doesn't show a translation containing the answer", leaks == 0, leaks)

print("Hangul Rain")
q = fresh()
for lid in (1, 10, 11, 12):
    q.start_lesson(lid)
    check(f"lesson {lid}: rain has something to play", bool(R._build_pool(q)))
lvl = R.RainLevel(1, [("가", "ga")])
lvl.bottom_row, lvl.max_x = 1000, 60
for _ in range(400):
    lvl.move(None)
check("speed only steps up once per level (no runaway)", lvl.speed >= R.START_SPEED - 1, lvl.speed)
lvl = R.RainLevel(1, [("가", "ga"), ("나", "na")])
lvl.bottom_row, lvl.max_x = 1000, 60
a, b = R.Invader("가", "ga", 5), R.Invader("가", "ga", 20)
a.y, b.y = 3, 9
lvl.invaders = [a, b]
lvl.create_new_in = 999
lvl.move("g")
check("keystroke goes to the lowest (most urgent) invader", b.damage == 1 and a.damage == 0)
lvl.move("a")
check("typing finishes the targeted invader", b.disabled)
lvl.move("x")
check("wrong key counts as a miss", lvl.misses == 1)

print()
if failures:
    print(f"RESULT: {len(failures)} FAILED — {failures}")
    sys.exit(1)
print("RESULT: ALL PASS")
