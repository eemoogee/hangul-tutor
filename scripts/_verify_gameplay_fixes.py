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
from unittest.mock import patch

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
    pending = E.PROGRESS_PATH.with_suffix(".json.tmp")
    if pending.exists():
        pending.unlink()
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

q = fresh()
q.progress["current_lesson"] = 2
q.save_progress()
real_replace = E.os.replace
replace_calls = []

def briefly_locked(src, dst):
    replace_calls.append((src, dst))
    if len(replace_calls) < 3:
        raise PermissionError("file in use")
    return real_replace(src, dst)

q.progress["current_lesson"] = 3
with patch.object(E.os, "replace", side_effect=briefly_locked), \
        patch.object(E.time, "sleep") as sleep, \
        contextlib.redirect_stdout(io.StringIO()) as notice:
    q.save_progress()
check("locked progress: retry then save succeeds",
      len(replace_calls) == 3 and sleep.call_count == 2
      and not notice.getvalue()
      and json.loads(E.PROGRESS_PATH.read_text(encoding="utf-8"))["current_lesson"] == 3
      and not E.PROGRESS_PATH.with_suffix(".json.tmp").exists())

q.progress["current_lesson"] = 4
q.progress["total_questions_answered"] = 17
with patch.object(E.os, "replace", side_effect=PermissionError("file in use")) as replace, \
        patch.object(E.time, "sleep") as sleep, \
        contextlib.redirect_stdout(io.StringIO()) as notice:
    q.save_progress()
pending = E.PROGRESS_PATH.with_suffix(".json.tmp")
check("locked progress: give up once, warn, and keep the complete temp file",
      replace.call_count == 5 and sleep.call_count == 4
      and notice.getvalue().count("Couldn't save progress") == 1
      and str(pending) in notice.getvalue()
      and json.loads(pending.read_text(encoding="utf-8"))["current_lesson"] == 4
      and json.loads(pending.read_text(encoding="utf-8"))["total_questions_answered"] == 17
      and json.loads(E.PROGRESS_PATH.read_text(encoding="utf-8"))["current_lesson"] == 3)

with patch.object(E.os, "replace", side_effect=PermissionError("file in use")), \
        patch.object(E.time, "sleep"), \
        contextlib.redirect_stdout(io.StringIO()) as repeated_notice:
    q.save_progress()
check("locked progress: repeated autosave does not repeat the warning",
      not repeated_notice.getvalue() and pending.exists())

saved_mtime = E.PROGRESS_PATH.stat().st_mtime_ns
E.os.utime(pending, ns=(saved_mtime + 1_000_000_000,) * 2)
q = E.HangulQuiz()
recovered = q.progress["current_lesson"] == 4 and q.progress["total_questions_answered"] == 17
q.save_progress()
check("locked progress: next start recovers newer temp, then saves it",
      recovered
      and json.loads(E.PROGRESS_PATH.read_text(encoding="utf-8"))["current_lesson"] == 4
      and json.loads(E.PROGRESS_PATH.read_text(encoding="utf-8"))["total_questions_answered"] == 17
      and not pending.exists())

pending.write_text(json.dumps({**q.progress, "current_lesson": 1}), encoding="utf-8")
saved_mtime = E.PROGRESS_PATH.stat().st_mtime_ns
E.os.utime(pending, ns=(saved_mtime - 1_000_000_000,) * 2)
check("older temp file cannot replace newer saved progress",
      E.HangulQuiz().progress["current_lesson"] == 4)

pending.write_text("{not json", encoding="utf-8")
E.os.utime(pending, ns=(saved_mtime + 1_000_000_000,) * 2)
with contextlib.redirect_stdout(io.StringIO()) as pending_notice:
    q = E.HangulQuiz()
check("corrupt newer temp keeps the last valid saved progress",
      q.progress["current_lesson"] == 4 and "Couldn't read pending progress" in pending_notice.getvalue()
      and pending.exists())

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

# 'ee' for the vowel ㅣ, in every block that has it (decided 2026-10-14).
ee = E.QuizQuestion(mode="read_aloud", prompt="", correct_answer="i",
                    accepted=sorted(q.roman_variants("이")), letter="이")
check("read_aloud: 'ee' accepted for 이", q.answer("ee", ee).correct)
check("'ee' accepted in any ㅣ block (기, 미, 인, bare ㅣ)",
      {"gee"} <= q.roman_variants("기") and {"mee"} <= q.roman_variants("미")
      and {"een"} <= q.roman_variants("인") and {"ee"} <= q.roman_variants("ㅣ"))
check("'ee' combines with 'sh' and 'l' (시 -> shee/see, 리 -> lee/ree)",
      {"si", "shi", "see", "shee"} <= q.roman_variants("시")
      and {"ri", "li", "ree", "lee"} <= q.roman_variants("리"))
check("'ee' works inside longer readings (아이 -> aee, 김치 -> geemchee)",
      {"aee"} <= q.roman_variants("아이") and "geemchee" in q.roman_variants("김치"))
check("'ee' is not accepted where there is no ㅣ (어, 의, 애)",
      not ({"ee", "eee", "uee", "aee"} & (q.roman_variants("어") | q.roman_variants("의")
                                          | q.roman_variants("애"))))

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

print("Phone-width screens (Termux is ~49 columns)")
import os as _os
import term_wrap as TW
_os.environ["HANGUL_WRAP"] = "49"
too_wide = []
buf = io.StringIO()
wrapped = TW.WrappingStdout(buf, width=49)
with contextlib.redirect_stdout(wrapped):
    import time as _t
    _sleep, _t.sleep = _t.sleep, (lambda *_: None)
    try:
        CLI._print_syllable_block_intro()
        for lesson in q.curriculum["lessons"]:
            info = q.start_lesson(lesson["id"])
            CLI.print_lesson_intro_rich(info, q)
            CLI.print_reference_table(q, info)
        CLI._print_help()
        CLI.print_romanization_key(q)
        CLI.print_cv_chart(q, y_vowels=True)
    finally:
        _t.sleep = _sleep
for line in buf.getvalue().split("\n"):
    if TW.display_width(line) > 49:
        too_wide.append(TW._ANSI.sub("", line)[:60])
_os.environ.pop("HANGUL_WRAP", None)
check("intros, tables, help, key and charts all fit 49 columns", not too_wide, too_wide[:3])
plain = TW._ANSI.sub("", buf.getvalue())
# The words a phone used to split ("com / pact", "ea / ch") must survive whole.
check("long lines break between words, not inside them",
      all(w in plain for w in ("compact", "syllable", "reshape", "depending", "consonant")),
      [w for w in ("compact", "syllable", "reshape", "depending", "consonant") if w not in plain])

print("A sense of progress (rounds, solid moments, next step)")
import builtins as _b
import re
import re as _re
import time as _t2


def _play(lesson_id, completed, answers, questions=()):
    """Drive the real CLI loop with scripted answers; returns its output.
    `questions`, if given, are served first instead of random ones."""
    qz = fresh()
    qz.progress["completed_lessons"] = list(completed)
    last = {}
    orig = qz.next_question
    forced = list(questions)

    def nq(*a, **k):
        last["q"] = forced.pop(0) if forced else orig(*a, **k)
        return last["q"]
    qz.next_question = nq
    script = iter(answers)

    def fake_input(prompt=""):
        v = next(script, None)
        if v is None:
            raise EOFError
        if v == "WRONG":
            qq = last["q"]
            wrong = [c for c in qq.choices if c != qq.correct_answer]
            return wrong[0] if wrong else ("zz" if qq.correct_answer.isascii() else "뷁")
        return last["q"].correct_answer if v == "RIGHT" else v
    real_input, _b.input = _b.input, fake_input
    real_sleep, _t2.sleep = _t2.sleep, (lambda *_: None)
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            CLI.interactive_loop(qz, type("A", (), {"mode": None, "sudden_death": False})(),
                                 qz.start_lesson(lesson_id))
    finally:
        _b.input, _t2.sleep = real_input, real_sleep
    return qz, _re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", out.getvalue())


qz, out = _play(1, [1], ["RIGHT"] * CLI.ROUND_SIZE + ["n"])
check("a finished lesson says so up front", "finished this lesson before" in out)
check("every question shows where you are in the round", f"· 1/{CLI.ROUND_SIZE}" in out and f"· {CLI.ROUND_SIZE}/{CLI.ROUND_SIZE}" in out)
check("a round ends with a progress card", "── Round 1 ·" in out)
check("the card offers the next lesson when this one is done", "[n] Lesson 2" in out)
check("pressing n on the card moves you to the next lesson", qz.current_lesson["id"] == 2, qz.current_lesson["id"])

_real_rain, _real_conv = CLI.launch_rain_mode, CLI.run_conveyor
CLI.launch_rain_mode = CLI.run_conveyor = (lambda *a, **k: None)
try:
    qz, out = _play(1, [], ["RIGHT", "RIGHT", "/rain", "/conveyor"])
finally:
    CLI.launch_rain_mode, CLI.run_conveyor = _real_rain, _real_conv
check("after /rain and /conveyor the question comes back with its round counter",
      out.count(f"· 3/{CLI.ROUND_SIZE}") == 3, out.count(f"· 3/{CLI.ROUND_SIZE}"))

qz, out = _play(1, [], ["RIGHT"] * 30)
check("blocks are celebrated the moment they become solid", "is solid now!" in out)
check("an unfinished lesson's card lists what's still to go", "Still to go:" in out)

print("Question mix (found by scripts/_playtest_learners.py)")
q = fresh()
q.start_lesson(2)
mix = Counter(q.next_question().mode for _ in range(2000))
special = sum(mix[m] for m in ("confusion_drill", "word_contrast", "nonword_decode", "sequence_decode"))
check("special modes get real airtime (were ~0%)", 0.12 <= special / 2000 <= 0.30, dict(mix))
check("look-alike drills no longer appear on their own (decided 2026-10-14)",
      mix["confusion_drill"] == 0, dict(mix))

print("Mix-ups: shown side by side, then asked again")
q = fresh()
q.start_lesson(2)
miss = q.answer("라", E.QuizQuestion(mode="match_sound", prompt="", correct_answer="가",
                                     choices=["가", "라", "나", "다"], letter="가", lesson_id=2))
check("a mix-up is reported on the result",
      (miss.confused_target, miss.confused_with) == ("가", "라"), (miss.confused_target, miss.confused_with))
first_two = [q.next_question() for _ in range(2)]
check("the missed block isn't asked again straight away", len(q._comeback) == 1, q._comeback)
back = q.next_question()
check("the 3rd question asks the missed block again",
      back.mode == "match_sound" and back.letter == "가" and not q._comeback, (back.mode, back.letter))
check("...with the block it was mixed up with among the choices",
      "라" in back.choices and len(back.choices) == 4 and len(set(back.choices)) == 4, back.choices)
typo = q.answer("zz", E.QuizQuestion(mode="match_sound", prompt="", correct_answer="나",
                                      choices=["가", "라", "나", "다"], letter="나", lesson_id=2))
check("a typo is not a mix-up and queues nothing", typo.confused_with is None and not q._comeback)
q.answer("라", E.QuizQuestion(mode="match_sound", prompt="", correct_answer="가",
                              choices=["가", "라", "나", "다"], letter="가", lesson_id=2))
q.start_lesson(3)
asked = [q.next_question() for _ in range(4)]
check("a queued mix-up is dropped when you change lesson", not q._comeback, q._comeback)
import io as _io, contextlib as _cl
import hangul_cli as _cli_m
buf = _io.StringIO()
with _cl.redirect_stdout(buf):
    _cli_m.show_mixup(q, miss)
shown = re.sub(r"\x1b\[[0-9;]*m", "", buf.getvalue())
check("the miss shows both blocks with their sounds", "가 is ga" in shown and "라 is ra" in shown, shown)

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

print("Reading mix-ups inferred from taught blocks")

def reading_miss(lesson, mode, target, typed):
    quiz = fresh()
    quiz.start_lesson(lesson)
    expected = "".join(quiz._hangul_to_roman_hint(ch) for ch in target)
    question = E.QuizQuestion(mode=mode, prompt="", correct_answer=expected,
                              accepted=sorted(quiz.roman_variants(target)),
                              letter=target, lesson_id=lesson)
    return quiz, quiz.answer(typed, question)

for lesson, target, typed, other in ((3, "보", "beo", "버"),
                                      (4, "코", "keo", "커"),
                                      (4, "바", "pa", "파"),
                                      (10, "간", "gam", "감")):
    q, miss = reading_miss(lesson, "read_aloud", target, typed)
    check(f"lesson {lesson}: {target} read {typed} identifies {other}",
          not miss.correct and (miss.confused_target, miss.confused_with) == (target, other))

q, miss = reading_miss(3, "read_aloud", "보", "beo")
check("inferred pair is in flat and per-item confusion history",
      q.progress["confusion_counts"].get("버↔보") == 1
      and q._get_item("보").confusions.get("버") == 1
      and q._get_item("버").confusions.get("보") == 1)
for _ in range(2):
    q.next_question()
back = q.next_question()
check("inferred pair returns on the third question with the swapped block",
      back.mode == "match_sound" and back.letter == "보" and "버" in back.choices)

for mode, target, typed in (("real_word", "오이", "eoi"),
                            ("read_word", "오이", "eoi"),
                            ("nonword_decode", "오우", "eou"),
                            ("sequence_decode", "오우아", "eoua")):
    q, miss = reading_miss(1, mode, target, typed)
    check(f"{mode}: one changed block is recorded, not the whole word",
          not miss.correct and (miss.confused_target, miss.confused_with) == ("오", "어")
          and q._get_item("오").confusions.get("어") == 1
          and q._get_item("어").confusions.get("오") == 1
          and not q._get_item(target).confusions)

q = fresh()
q.start_lesson(2)
contrast = E.QuizQuestion(mode="word_contrast", prompt="", correct_answer="거기",
                          choices=["거기", "고기"], letter="거기", lesson_id=2,
                          direction="meaning_to_word")
miss = q.answer("고기", contrast)
check("word contrast: offered 고기 for 거기 records 고/거",
      not miss.correct and (miss.confused_target, miss.confused_with) == ("거", "고")
      and q.progress["confusion_counts"].get("고↔거") == 1
      and q._get_item("거").confusions.get("고") == 1
      and q._get_item("고").confusions.get("거") == 1
      and q._comeback[-1][1:3] == ["거", "고"])

for name, lesson, mode, target, typed in (
        ("typo", 3, "read_aloud", "보", "beox"),
        ("two changed blocks", 1, "real_word", "오이", "eoeu"),
        ("ambiguous reading", 11, "read_aloud", "가", "ot"),
        ("untaught letter", 1, "read_aloud", "아", "pa")):
    q, miss = reading_miss(lesson, mode, target, typed)
    check(f"reading mix-up: {name} records nothing",
          not miss.correct and miss.confused_with is None and not q._comeback
          and not q.progress["confusion_counts"])

q = fresh()
q.start_lesson(2)
two_block_contrast = E.QuizQuestion(mode="word_contrast", prompt="", correct_answer="거기",
                                    choices=["거기", "고가"], letter="거기", lesson_id=2,
                                    direction="meaning_to_word")
check("word contrast: an offered two-block alternative records nothing",
      q.answer("고가", two_block_contrast).confused_with is None)
single_contrast = E.QuizQuestion(mode="word_contrast", prompt="", correct_answer="거",
                                 choices=["거", "고"], letter="거", lesson_id=2,
                                 direction="meaning_to_word")
check("word contrast: a studied but unoffered block records nothing",
      q.answer("버", single_contrast).confused_with is None
      and not q.progress["confusion_counts"])

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

print("Mistakes, hints and skips count toward mastery")


def _q(letter, mode="match_sound", answer=None):
    return E.QuizQuestion(mode=mode, prompt="", correct_answer=answer or letter,
                          choices=[], letter=letter)


def _answers(quiz, letter, seq, mode="match_sound"):
    """seq: '1' right, '0' wrong, 'h' right after a hint, 's' skip."""
    for c in seq:
        qq = _q(letter, mode)
        if c == "s":
            quiz.record_skip(qq)
        else:
            quiz.answer(letter if c in "1h" else "zz", qq, assisted=(c == "h"))


q = fresh()
q.start_lesson(2)
_answers(q, "가", "111")
check("3 right in a row makes an item solid (same pace as before)", q._is_solid("가"),
      q._get_item("가").confidence)
_answers(q, "나", "10101000")
check("3 right + 5 wrong is NOT solid (the old formula said it was)", not q._is_solid("나"),
      q._get_item("나").confidence)
_answers(q, "다", "000")
n = 0
while not q._is_solid("다") and n < 20:
    _answers(q, "다", "1")
    n += 1
check("an early slip is forgiven: 4 right answers after 3 misses make it solid",
      q._is_solid("다") and n <= 4, n)
_answers(q, "라", "11111111")
_answers(q, "라", "000")
check("a solid item that keeps getting missed stops being solid", not q._is_solid("라"),
      q._get_item("라").confidence)

legacy = {"correct": 3, "wrong": 5, "last_seen": 0.0}
it = E.LearnerItem.from_dict("마", legacy)
check("progress saved before this change: 3 right / 5 wrong reads as not solid",
      it.confidence < q.MASTERY_CONFIDENCE, (it.history, it.confidence))
it = E.LearnerItem.from_dict("마", {"correct": 12, "wrong": 0})
check("progress saved before this change: a clean record stays solid",
      it.confidence >= q.MASTERY_CONFIDENCE, (it.history, it.confidence))
it = E.LearnerItem.from_dict("마", E.LearnerItem.from_dict("마", legacy).to_dict())
check("answer history survives save and load", it.history == "00000111", it.history)
it = E.LearnerItem.from_dict("마", {"correct": 0, "wrong": 0, "_migrated_confidence": 4})
check("the very old 0-5 score still carries over as a floor", it.confidence == 4, it.confidence)

q = fresh()
q.start_lesson(2)
streak0 = q.session_streak
r = q.answer("가", _q("가"), assisted=True)
check("a right answer after /hint is still right and keeps the streak",
      r.correct and q.session_streak == streak0 + 1)
_answers(q, "가", "hhhh")
check("right answers after /hint don't make an item solid", not q._is_solid("가"),
      q._get_item("가").history)
q.answer("나무", E.QuizQuestion(mode="real_word", prompt="", correct_answer="namu",
                               accepted=["namu"], choices=[], letter="나무"), assisted=True)
check("a hinted word gives its blocks no credit", q._get_item("나").history == "",
      q._get_item("나").history)
q.answer("namu", E.QuizQuestion(mode="real_word", prompt="", correct_answer="namu",
                               accepted=["namu"], choices=[], letter="나무"))
check("an unhinted word still credits its blocks", q._get_item("나").history == "1",
      q._get_item("나").history)

q = fresh()
q.start_lesson(2)
_answers(q, "다", "111")
total0, streak = q.session_total, q.session_streak
q.record_skip(_q("다"))
it = q._get_item("다")
check("/skip counts as a miss on the item", it.history.endswith("s") and it.wrong == 1, it.history)
check("/skip ends the streak but isn't graded as an answer",
      q.session_streak == 0 and q.session_total == total0 and streak == 3)
_answers(q, "다", "s")
check("skipping the hard ones can't leave an item solid", not q._is_solid("다"),
      q._get_item("다").confidence)
check("/skip records no mix-up", not q._get_item("다").confusions)

# The real CLI loop: /hint then a right answer; /skip.
qz, out = _play(2, [1], ["/hint", "RIGHT", "/skip"], questions=[
    E.QuizQuestion(mode="spell", prompt="Type the Hangul for: na", correct_answer="나",
                   choices=["나", "다", "라", "가"], letter="나", hint="ㄴ + ㅏ"),
    E.QuizQuestion(mode="spell", prompt="Type the Hangul for: da", correct_answer="다",
                   choices=["나", "다", "라", "가"], letter="다", hint="ㄷ + ㅏ")])
hinted = [k for k, v in qz.progress["learner_items"].items() if v.get("history") == "h"]
check("CLI: /hint then a right answer is recorded as helped", hinted == ["나"],
      {k: v.get("history") for k, v in qz.progress["learner_items"].items()})
check("CLI: says a hinted answer doesn't count toward solid", "With a hint" in out)
skipped = [k for k, v in qz.progress["learner_items"].items() if v.get("history") == "s"]
check("CLI: /skip is recorded as a miss and saved",
      skipped == ["다"] and E.PROGRESS_PATH.exists()
      and json.loads(E.PROGRESS_PATH.read_text(encoding="utf-8"))["learner_items"]
          .get(skipped[0], {}).get("history") == "s", skipped)

R10 = ["WRONG"] * CLI.ROUND_SIZE
qz, out = _play(2, [1], R10 + [""] + R10 + [""] + R10 + ["n"])
cards = out.split("── Round ")[1:]
check("a stuck learner isn't offered to move on too early",
      len(cards) >= 3 and all("move on" not in c for c in cards[:2]), len(cards))
check(f"after {CLI.STUCK_AFTER_ROUNDS} rounds with no progress, the card offers the next lesson",
      len(cards) >= 3 and "move on" in cards[2] and "[n] Lesson 3" in cards[2])
check("...and n takes you there", qz.current_lesson["id"] == 3, qz.current_lesson["id"])
check("...without marking the unfinished lesson done", 2 not in qz.progress["completed_lessons"])
qz, out = _play(12, list(range(1, 12)), R10 + [""] + R10 + [""] + R10 + [""])
check("stuck in the last lesson: suggests reviewing an earlier one",
      "earlier lesson" in out.split("── Round 3")[-1])
qz, out = _play(2, [1], (["RIGHT"] * CLI.ROUND_SIZE + [""]) * 3)
check("a learner who is making progress isn't told to move on", "move on" not in out)

print("Missing vowel answers and the mix-ups they save (phone screenshot, 2026-10-14)")


def _mv():
    return E.QuizQuestion(mode="missing_vowel", prompt="**ㅁ** + ? = **mi**", correct_answer="ㅣ",
                          choices=["ㅡ", "ㅜ", "ㅗ", "ㅣ"], letter="미")


q = fresh()
q.start_lesson(2)
check("missing vowel: typing the whole block (미) is right", q.answer("미", _mv()).correct)
check("missing vowel: typing the two letters apart (ㅁㅣ) is right", q.answer("ㅁㅣ", _mv()).correct)
check("missing vowel: typing the consonant shown gets a nudge, not a grade",
      q.script_mismatch("ㅁ", _mv()) is not None and q.script_mismatch("ㅣ", _mv()) is None)
q.answer("ㅁ", _mv())
check("missing vowel: typing the consonant saves no mix-up",
      not q.progress["confusion_counts"] and not q._pairs_from_learner_items(),
      (q.progress["confusion_counts"], q._pairs_from_learner_items()))
q.answer("ㅗ", _mv())
check("missing vowel: a wrong vowel is saved as the two blocks (모 for 미)",
      [c["pair"] for c in q._top_confusions()] == ["모↔미"]
      and set(q._pairs_from_learner_items()) == {"모↔미"},
      (q._top_confusions(), q._pairs_from_learner_items()))

q = fresh()
q.start_lesson(2)
q.progress["confusion_counts"] = {"ㄷ↔ㅓ": 4, "ㅈ↔ㅏ": 3, "ㅗ↔ㅣ": 2, "미↔ㅣ": 2, "다↔타": 1}
q._save_item(E.LearnerItem.from_dict("미", {"confusions": {"ㅗ": 2, "ㅁ": 1, "ㅣ": 1}}))
q._save_item(E.LearnerItem.from_dict("ㄷ", {"confusions": {"더": 3}}))
shown = [c["pair"] for c in q._top_confusions()]
check("old saved pairs: consonant-vs-vowel ones aren't listed under 'Practice these'",
      shown == ["오↔이", "다↔타"], shown)
check("old saved pairs: the drill gets 모↔미, not 오↔미 or ㄷ↔더",
      set(q._pairs_from_learner_items()) == {"모↔미"}, q._pairs_from_learner_items())

q = fresh()
mixed = []
for lid in (2, 3, 5, 6):
    q.start_lesson(lid)
    for _ in range(120):
        qq = q.next_question()
        for t in set(qq.choices or []) | {ch for ch in qq.prompt if E._looks_like_hangul_target(ch)}:
            if t != qq.correct_answer:
                q.answer(t, qq)
for k in list(q.progress["confusion_counts"]) + list(q._pairs_from_learner_items()):
    a, b = k.split("↔")
    if E._is_consonant_jamo(a) != E._is_consonant_jamo(b):
        mixed.append(k)
check("no question type saves a consonant-vs-vowel mix-up", not mixed, sorted(set(mixed))[:5])

qz, out = _play(2, [1], ["/skip", "RIGHT"])
check("/skip uses up a turn in the round (the next question is 2/10)",
      f"· 1/{CLI.ROUND_SIZE}" in out and f"· 2/{CLI.ROUND_SIZE}" in out
      and out.count(f"· 1/{CLI.ROUND_SIZE}") == 1)
qz, out = _play(2, [1], ["/skip"] * CLI.ROUND_SIZE + ["q"])
check("a round of skips still ends with its card", f"── Round 1 · 0 of {CLI.ROUND_SIZE} right" in out)

print("Conveyor game")
import game_io as GIO
import conveyor_game as CONV
ch = ["가", "나", "다", "라"]
check("a choice's number picks it (choices are shown as 1-4)",
      E.HangulQuiz.resolve_choice("3", ch) == "다" and E.HangulQuiz.resolve_choice("3.", ch) == "다")
check("letters still pick too", E.HangulQuiz.resolve_choice("c", ch) == "다")
check("a number past the last choice isn't a pick", E.HangulQuiz.resolve_choice("4", ch[:3]) == "4")
q = fresh()
q.start_lesson(5)
qq = E.QuizQuestion(mode="build_syllable", prompt="Build: ㄱ + ㅏ", correct_answer="가",
                    choices=["나", "다", "가", "라"], letter="가", hint="ㄱ + ㅏ = 가")
check("typing the right choice's number is graded right", q.answer("3", qq).correct)
stars = hint_shown = doubled = 0
for lid in (2, 5, 10, 12):
    q.start_lesson(lid)
    for mode in ("build_syllable", "decompose_syllable", "missing_vowel", None):
        for _ in range(15):
            qq = q.next_question(mode=mode)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                GIO.render_question(qq)
                GIO.render_result(q.answer("zz", qq))
                GIO.render_result(q.answer(qq.correct_answer, qq))
            text = _ansi.sub("", buf.getvalue())
            stars += "**" in text
            doubled += "✗ ❌" in text or "✓ ✅" in text
            hint_shown += bool(qq.hint) and ("Hint:" in text or qq.hint in text.split("✗")[0])
check("no literal ** in conveyor questions or feedback", stars == 0, stars)
check("the hint isn't shown before you answer", hint_shown == 0, hint_shown)
check("feedback has one ✓/✗ mark, not two", doubled == 0, doubled)

conv_q = E.QuizQuestion(mode="build_syllable", prompt="Build: ㄱ + ㅏ", correct_answer="가",
                        choices=["나", "다", "가", "라"], letter="가", hint="ㄱ + ㅏ = 가")
q = fresh()
q.start_lesson(5)
q.next_question = lambda mode=None: conv_q
script = iter(["/hint", "3"])
real_input, _b.input = _b.input, (lambda prompt="": next(script, None) or (_ for _ in ()).throw(EOFError))
buf = io.StringIO()
try:
    with contextlib.redirect_stdout(buf):
        CONV.run_conveyor(q, CONV.make_conveyor_state(5, ["가"], turn_limit=1))
finally:
    _b.input = real_input
text = _ansi.sub("", buf.getvalue())
check("conveyor: /hint shows the hint on request", "ㄱ + ㅏ = 가" in text)
check("conveyor: answering 3 after /hint scores, without mastery credit",
      "Final score : 1" in text and q._get_item("가").history == "h",
      (q._get_item("가").history, text[-300:]))

print("Stray key codes")
import term_wrap as _tw
check("End key code alone counts as blank", _tw.strip_key_codes("\x1b[F") == "")
check("key codes around an answer are dropped",
      _tw.strip_key_codes("\x1b[Fbanana\x1b[D") == "banana")
check("arrow/Home/F1 codes and a lone Esc are dropped",
      _tw.strip_key_codes("\x1b[A\x1bOH\x1bOP\x1b") == "")
check("Hangul, spaces and slashes are untouched",
      _tw.strip_key_codes("바나나 /hint") == "바나나 /hint")
import hangul_cli as _cli_k
_real, _b.input = _b.input, (lambda prompt="": "\x1b[Fga")
try:
    check("the CLI's input() strips key codes", _cli_k.input("> ") == "ga")
finally:
    _b.input = _real

print("Lesson-complete box")
for lid in range(1, 12):
    qb = fresh()
    qb.start_lesson(lid)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        CLI.print_lesson_complete(qb)
    box = [l for l in _re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", buf.getvalue()).splitlines() if l.startswith(("║", "╔", "╠", "╚"))]
    after_next = box[[i for i, l in enumerate(box) if "Next" in l][0] + 1:-1] if any("Next" in l for l in box) else []
    nxt = qb._get_lesson(lid + 1)
    ok = (len(after_next) == 2 and nxt["title"][:20] in after_next[0]
          and after_next[1].strip("║ ") != ""
          and len({CLI._vwidth(l) for l in box}) == 1)
    check(f"lesson {lid} done: box previews Lesson {lid + 1} (title + what it teaches), borders line up",
          ok, after_next)

print("Session summary with skips")
qz, out = _play(1, [], ["/skip"] * CLI.ROUND_SIZE + ["q"])
check("ten skips: the round card and the summary agree",
      "0 of 10 right" in out and "Correct: no answers yet · 10 skipped" in out,
      [l for l in out.splitlines() if "Correct" in l or "right" in l][-3:])
qz, out = _play(1, [], ["RIGHT", "WRONG", "/skip", "RIGHT"])
check("mixed answers and a skip: graded answers and skips shown apart",
      "Correct: 2 of 3 answered (67%) · 1 skipped" in out,
      [l for l in out.splitlines() if "Correct" in l][-1:])
qs = fresh()
check("skips are counted for the session", qs.session_skips == 0)
qs.start_lesson(1)
qs.record_skip(qs.next_question())
check("record_skip counts one skip", qs.session_skips == 1 and qs.session_total == 0)

print("The silent ㅇ is described correctly")
_l1_note = fresh()._get_lesson(1).get("note", "")
_cli_src = open(CLI.__file__, encoding="utf-8").read()
check("Lesson 1 note: a vowel can't START a syllable alone (not 'never stands alone')",
      "can't start a syllable by itself" in _l1_note
      and "never stands alone" not in _l1_note and "always gets" not in _l1_note, _l1_note)
check("walkthrough: ㅇ 'comes first' (not 'in front': it sits on top of 오/우/으)",
      "can't start a syllable by itself" in _cli_src
      and "Vowels never appear alone" not in _cli_src and "The ㅇ in front" not in _cli_src)

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

# Status line fits a phone (~49 columns): lives and score never cut off.
lvl = R.RainLevel(12, [("가", "ga")], previous_points=99999)
hud = lvl.hud_text()
check("rain status: lives come first", hud.startswith("<3 <3 <3"), hud)
check("rain status: fits 48 columns with a big score", len(hud) <= 48, (len(hud), hud))
check("rain status: shows the quit hint", "Esc=quit" in hud, hud)
lvl.last_miss, lvl.miss_flash = "x", 3
check("rain status: a miss replaces the quit hint while it flashes",
      "miss: 'x'" in lvl.hud_text() and "Esc" not in lvl.hud_text(), lvl.hud_text())

print()
if failures:
    print(f"RESULT: {len(failures)} FAILED — {failures}")
    sys.exit(1)
print("RESULT: ALL PASS")
