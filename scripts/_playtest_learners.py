"""
Simulated-learner playtest: several kinds of learner play the whole course,
lesson 1 to 12, through the real quiz engine. Reports pacing, stalls,
repetition, mode mix and question-quality problems per lesson.

Run from the repo root:
    python scripts/_playtest_learners.py                 # 10 runs per learner
    python scripts/_playtest_learners.py --runs 3 --quick
    python scripts/_playtest_learners.py --json out.json  # also dump raw numbers

Never touches data/user_progress.json — progress goes to a temp folder.

How the simulated learner works
-------------------------------
Knowledge is tracked per letter AND position — ㄱ as a starting consonant
is a different skill from ㄱ as a final consonant (batchim). Each time a
letter-in-position appears in a question, the learner gets a little better
at it, rising from a starting chance toward a ceiling:

    p = ceiling - (ceiling - start) * exp(-times_seen / learn_rate)

A block is only as easy as its hardest letter (the minimum), and a word
multiplies its blocks together. Multiple choice adds a blind-guess chance.
Answers that come out wrong are PLAUSIBLE mistakes (a neighbouring vowel,
a look-alike choice), not random noise, so the engine's confusion tracking
gets realistic input.

Each learner plays in sittings of ~120 questions with a day's break in
between; every sitting saves and re-loads progress through the real code.
Time is simulated (4-12 s per answer) because the engine's spaced
repetition ("is this item due again yet?") runs on the clock.
"""

import argparse
import contextlib
import io
import json
import math
import random
import re
import statistics
import sys
import tempfile
import time as _real_time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import hangul_quiz_engine as E  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="hangul_playtest_"))
E.PROGRESS_PATH = TMP / "user_progress.json"


# ── Simulated clock ────────────────────────────────────────────────────────

class _Clock:
    """Stands in for the `time` module inside the engine."""
    def __init__(self):
        self.now = 1_800_000_000.0

    def time(self):
        return self.now

    def strftime(self, fmt, *a):
        return _real_time.strftime(fmt, _real_time.localtime(self.now))

    def advance(self, seconds):
        self.now += seconds


CLOCK = _Clock()
E.time = CLOCK

# Loading the 15k-sentence corpus is the slow part of HangulQuiz(); every
# simulated sitting builds a fresh engine, so load it once and reuse it.
_BIGRAMS = E.HangulQuiz._load_corpus_seen_bigrams(None)
E.HangulQuiz._load_corpus_seen_bigrams = lambda self: _BIGRAMS

with contextlib.redirect_stdout(io.StringIO()):
    import hangul_cli as CLI  # noqa: E402   (for the real on-screen render)

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

# Modes whose prompt is a SOUND and whose answer is a Hangul block.
SOUND_TO_HANGUL = {"spell", "match_sound", "build_syllable", "confusion_drill"}
# Modes whose answer is typed in English letters.
ROMAN_ANSWER = {"read_aloud", "read_word", "nonword_decode", "sequence_decode"}


# ── Learner profiles ───────────────────────────────────────────────────────

PROFILES = {
    "strong":     dict(start=0.75, ceiling=0.98, rate=4,
                       about="picks things up fast, ~95% accurate once warmed up"),
    "average":    dict(start=0.55, ceiling=0.93, rate=6,
                       about="steady learner, ~90% accurate once warmed up"),
    "struggling": dict(start=0.40, ceiling=0.85, rate=10,
                       about="slow to learn, tops out around 85%"),
    "eo_o_mixer": dict(start=0.55, ceiling=0.93, rate=6,
                       caps={("jung", "ㅓ"): 0.65, ("jung", "ㅗ"): 0.65},
                       swap={"ㅓ": "ㅗ", "ㅗ": "ㅓ"},
                       about="average, but keeps mixing up ㅓ and ㅗ (65% at best)"),
    "batchim_weak": dict(start=0.55, ceiling=0.93, rate=6, jong_cap=0.60,
                         about="average, but final consonants top out at 60%"),
    "clicker":    dict(start=0.55, ceiling=0.93, rate=6, clicks=True,
                       about="average, no Hangul keyboard — answers A-D whenever it can"),
    # Control group: knows NOTHING and never learns. Blind-guesses A-D on
    # multiple choice, gets every typed question wrong. If this learner can
    # finish a lesson, the mastery bar is measuring luck, not reading.
    "guesser":    dict(start=0.0, ceiling=0.0, rate=1, clicks=True,
                       about="CONTROL: knows nothing, guesses A-D at random"),
}


class Learner:
    def __init__(self, name, rng):
        self.name = name
        self.cfg = PROFILES[name]
        self.rng = rng
        self.seen = Counter()          # (position, jamo) -> times seen

    # -- knowledge --------------------------------------------------------
    def _parts(self, quiz, text):
        out = []
        for ch in text:
            if not E._is_hangul_char(ch):
                continue
            cho, jung, jong = quiz._decompose_syllable(ch)
            if not jung:                         # a bare letter
                pos = "jung" if ch in E._VOWEL_JAMO else "cho"
                out.append([(pos, ch)])
                continue
            block = [("jung", jung)]
            if cho and cho != "ㅇ":
                block.append(("cho", cho))
            if jong:
                block.append(("jong", jong))
            out.append(block)
        return out

    def _p_key(self, key):
        c = self.cfg
        ceiling = c["ceiling"]
        if key in c.get("caps", {}):
            ceiling = c["caps"][key]
        if key[0] == "jong" and "jong_cap" in c:
            ceiling = c["jong_cap"]
        start = min(c["start"], ceiling)
        return ceiling - (ceiling - start) * math.exp(-self.seen[key] / c["rate"])

    def p_correct(self, quiz, q):
        text = q.letter or q.correct_answer
        if q.mode == "konglish":
            return 0.7
        blocks = self._parts(quiz, text)
        if not blocks:
            return self.cfg["ceiling"]
        p = 1.0
        for block in blocks:
            p *= min(self._p_key(k) for k in block)
        if q.mode == "batchim_challenge":
            # The whole question is about the final consonant.
            jong = [k for b in blocks for k in b if k[0] == "jong"]
            if jong:
                p = min(p, self._p_key(jong[0]))
        if q.choices:
            p = p + (1 - p) / len(q.choices)
        return p

    def learn(self, quiz, q, was_wrong):
        for block in self._parts(quiz, (q.letter or "") + (q.other or "")):
            for key in block:
                # A miss that is then shown the right answer teaches a bit more.
                self.seen[key] += 1.5 if was_wrong else 1

    # -- answering --------------------------------------------------------
    def answer(self, quiz, q):
        """Return (text_typed, intended_correct)."""
        correct = self.rng.random() < self.p_correct(quiz, q)
        if correct:
            return self._say_right(quiz, q), True
        return self._say_wrong(quiz, q), False

    def _say(self, q, choice):
        if q.choices and self.cfg.get("clicks") and choice in q.choices:
            return "ABCD"[q.choices.index(choice)]
        return choice

    def _say_right(self, quiz, q):
        if q.mode in ROMAN_ANSWER and q.accepted and self.name == "strong" and self.rng.random() < 0.3:
            # Strong learners sometimes use another correct reading ('la' for 라).
            return self.rng.choice(q.accepted)
        if q.choices and self.cfg.get("clicks"):
            return self._say(q, q.correct_answer)
        return q.correct_answer

    def _say_wrong(self, quiz, q):
        wrong_choices = [c for c in (q.choices or []) if c != q.correct_answer]
        swap = self.cfg.get("swap", {})
        if wrong_choices:
            # Prefer the look-alike: the choice that differs only by a vowel
            # this learner confuses.
            target = q.correct_answer
            for c in wrong_choices:
                if len(c) == len(target) == 1 and E._is_hangul_char(c) and E._is_hangul_char(target):
                    a, b = quiz._decompose_syllable(c), quiz._decompose_syllable(target)
                    if a[0] == b[0] and a[2] == b[2] and swap.get(b[1]) == a[1]:
                        return self._say(q, c)
                if c in swap and swap.get(c) == target:
                    return self._say(q, c)
            return self._say(q, self.rng.choice(wrong_choices))
        # Typed answer with no choices: mangle one vowel.
        wrong = self._mutate(quiz, q.letter or q.correct_answer)
        if q.mode in ROMAN_ANSWER:
            return "".join(quiz._hangul_to_roman_hint(ch) for ch in wrong) or "x"
        return wrong

    def _mutate(self, quiz, text):
        chars = [c for c in text]
        idxs = [i for i, c in enumerate(chars) if 0xAC00 <= ord(c) <= 0xD7A3]
        if not idxs:
            return text + "?"
        i = self.rng.choice(idxs)
        cho, jung, jong = quiz._decompose_syllable(chars[i])
        swap = self.cfg.get("swap", {})
        new_jung = swap.get(jung) or self.rng.choice([v for v in "ㅏㅓㅗㅜㅡㅣ" if v != jung])
        chars[i] = quiz._compose_syllable(cho, new_jung, jong)
        return "".join(chars)


# ── Question-quality checks (on what the learner actually sees) ────────────

def screen_text(quiz, q):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        CLI.print_question(q, quiz)
    lines = ANSI.sub("", buf.getvalue()).splitlines()
    # Drop the A-D choice lines and the generic footer lines.
    body = [l for l in lines if not re.match(r"\s+[A-D]\)", l)
            and "type the answer directly" not in l and "/hint" not in l]
    return "\n".join(body)


def quality_problems(quiz, q, render):
    probs = []
    if q.choices:
        if q.correct_answer not in q.choices:
            probs.append("correct answer missing from choices")
        if len(set(q.choices)) != len(q.choices):
            probs.append("duplicate choices")
    if q.mode in SOUND_TO_HANGUL and q.choices:
        target = quiz.roman_variants(q.correct_answer)
        twins = [c for c in q.choices if c != q.correct_answer
                 and quiz.roman_variants(c) & target]
        if twins:
            probs.append(f"choice sounds the same as the answer: {q.correct_answer}/{twins[0]}")
    if q.mode == "missing_vowel" and q.choices:
        cho, _, _ = quiz._decompose_syllable(q.letter)
        sounds = Counter(E.ROMANIZATION.get(v, v) for v in q.choices)
        if max(sounds.values()) > 1:
            probs.append("two vowel choices romanize the same")
    if render and q.mode == "confusion_drill":
        # The drill names ONE sound and shows both blocks. If that sound is
        # also printed next to a block, the learner can just match labels.
        sound = quiz._hangul_to_roman_hint(q.correct_answer)
        if len(re.findall(rf"(?<![a-z]){re.escape(sound)}(?![a-z])", render)) > 1:
            probs.append("answer visible on screen (confusion_drill: sound printed under its block)")
    if render and q.mode == "word_contrast" and not E._is_hangul_char(q.correct_answer[0]):
        # word -> meaning: the English answer must not already be on screen.
        words = [w for w in re.findall(r"[a-z]+", q.correct_answer.lower()) if len(w) > 2]
        if any(re.search(rf"\b{w}\b", render.lower()) for w in words):
            probs.append("answer visible on screen (word_contrast: meaning shown in translation)")
    if render and q.mode not in ("confusion_drill", "word_contrast", "match_sound"):
        # Does the screen show the answer before the learner answers?
        ans = q.correct_answer
        if E._is_hangul_char(ans[0]):
            shown = ans in render
            if q.mode == "spell" and q.letter in render:
                shown = True
        else:
            shown = re.search(rf"(?<![a-z]){re.escape(ans.lower())}(?![a-z])", render.lower()) is not None
            if q.mode == "batchim_challenge" and q.direction == "letter_to_sound":
                shown = shown and f"'{ans}'" in render     # bare 't' in "what" isn't a leak
            if q.mode in ROMAN_ANSWER:
                shown = shown and ans.lower() not in ("a", "i", "o", "u", "e")
        if shown:
            probs.append(f"answer visible on screen ({q.mode})")
    return probs


# ── One learner, whole course ──────────────────────────────────────────────

SITTING = 120          # questions per sitting before the learner quits for the day

# What-if mastery rules (--rule). "A" is whatever the engine does today;
# the others are evaluated here without changing the engine, to compare
# the cost (questions) against the benefit (real skill at completion).
RULES = {
    "A": "engine as-is (confidence >= MASTERY_CONFIDENCE)",
    "B": "confidence >= 3",
    "C": "confidence >= 2 AND the item's last 2 answers were right",
    "D": "confidence >= 3 AND the item's last 2 answers were right",
}
RULE = "A"
HIST = defaultdict(list)          # item -> [True/False, ...] answer history


def rule_mastered(quiz, mset):
    if RULE == "A":
        return quiz.lesson_mastery()["is_mastered"]
    need = 3 if RULE in ("B", "D") else 2
    for s in mset:
        k = quiz._compose_bare_vowel(s)
        if quiz._get_item(k).confidence < need:
            return False
        if RULE in ("C", "D") and HIST[k][-2:] != [True, True]:
            return False
    return True


def play_course(profile, seed, max_q, lessons, check_render):
    rng = random.Random(seed)
    random.seed(seed)                       # the engine uses the global RNG
    HIST.clear()
    learner = Learner(profile, rng)
    if E.PROGRESS_PATH.exists():
        E.PROGRESS_PATH.unlink()
    quiz = E.HangulQuiz()
    quiz.start_lesson(lessons[0])

    out = {"profile": profile, "seed": seed, "lessons": {}, "grading_bugs": [],
           "quality": Counter(), "quality_examples": {}}

    # Record which mode the engine MEANT to ask vs. what it produced, to
    # catch silent fallbacks (e.g. missing_vowel quietly turning into spell).
    asked = []
    def wrap(qz):
        inner = qz._generate_question
        def gen(mode):
            q = inner(mode)
            asked.append((mode, q.mode))
            return q
        qz._generate_question = gen
    wrap(quiz)

    total_q = 0
    for lid in lessons:
        if quiz.current_lesson["id"] != lid:
            quiz.start_lesson(lid)
        L = dict(questions=0, correct=0, modes=Counter(), mode_right=Counter(),
                 fallbacks=Counter(), exposures=Counter(), back_to_back=0,
                 repeat_within_3=0, bar=[], bar_drops=0, tail=0, stalled=False,
                 drills=0, drills_on_confused=0, minutes=0.0, sittings=0,
                 nudges=0)
        recent = []
        mset = (quiz.current_lesson.get("mastery_words")
                or quiz.current_lesson.get("mastery_syllables")
                or quiz._get_lesson_syllable_pool(quiz.current_lesson))
        last_bar = 0
        best_bar = 0
        reached_n_minus_1 = None
        start_clock = CLOCK.now
        while True:
            if L["questions"] >= max_q:
                L["stalled"] = True
                break
            asked.clear()
            q = quiz.next_question()
            render = screen_text(quiz, q) if check_render else ""
            for p in quality_problems(quiz, q, render):
                kind = p.split(":")[0]
                out["quality"][kind] += 1
                out["quality_examples"].setdefault(kind, f"L{lid} {p} | {q.prompt[:70]!r}")
            for want, got in asked:
                if want != got:
                    L["fallbacks"][f"{want}->{got}"] += 1

            typed, meant_right = learner.answer(quiz, q)
            nudge = quiz.script_mismatch(typed, q)
            if nudge:
                L["nudges"] += 1
                typed, meant_right = learner._say_right(quiz, q), True
            res = quiz.answer(typed, q, response_ms=6000)
            if meant_right and not res.correct:
                out["grading_bugs"].append(f"L{lid} {q.mode}: typed {typed!r}, expected {q.correct_answer!r}")
            learner.learn(quiz, q, not res.correct)
            HIST[quiz._compose_bare_vowel(q.letter)].append(res.correct)
            if res.correct and q.mode in ("read_word", "nonword_decode", "sequence_decode"):
                for ch in q.letter:          # the engine credits each block too
                    HIST[ch].append(True)

            L["questions"] += 1
            total_q += 1
            L["correct"] += res.correct
            L["modes"][q.mode] += 1
            L["mode_right"][q.mode] += res.correct
            key = quiz._compose_bare_vowel(q.letter)
            L["exposures"][key] += 1
            if recent and recent[-1] == key:
                L["back_to_back"] += 1
            if key in recent[-3:]:
                L["repeat_within_3"] += 1
            recent.append(key)
            if q.mode == "confusion_drill":
                L["drills"] += 1
                swap = learner.cfg.get("swap", {})
                if swap:
                    j1 = quiz._decompose_syllable(q.letter)[1]
                    j2 = quiz._decompose_syllable(q.other)[1] if q.other else ""
                    if swap.get(j1) == j2:
                        L["drills_on_confused"] += 1

            CLOCK.advance(rng.uniform(4, 8) if res.correct else rng.uniform(8, 12))

            m = quiz.lesson_mastery()
            if m["mastered_count"] < last_bar:
                L["bar_drops"] += 1
            last_bar = m["mastered_count"]
            best_bar = max(best_bar, last_bar)
            L["bar"].append(last_bar)
            if reached_n_minus_1 is None and m["mastered_count"] >= m["pool_size"] - 1:
                reached_n_minus_1 = L["questions"]
            if rule_mastered(quiz, mset):
                break

            if total_q % SITTING == 0:              # quit for the day, come back
                quiz.save_progress()
                CLOCK.advance(20 * 3600)
                quiz = E.HangulQuiz()
                quiz.start_lesson(lid)
                wrap(quiz)
                L["sittings"] += 1

        # How well does the learner REALLY read the lesson's items at the
        # moment the app calls it mastered? Typed answer, no choices to
        # guess from — the learner model's true chance of reading each one.
        skills = [learner.p_correct(quiz, E.QuizQuestion(mode="read_aloud", prompt="",
                                                          correct_answer="", letter=s))
                  for s in mset]
        L["skill_min"] = round(min(skills), 3) if skills else None
        L["skill_mean"] = round(sum(skills) / len(skills), 3) if skills else None
        L["tail"] = L["questions"] - reached_n_minus_1 if reached_n_minus_1 else None
        L["minutes"] = round((CLOCK.now - start_clock - L["sittings"] * 20 * 3600) / 60, 1)
        L["pool_size"] = len(mset)
        L["final_bar"] = last_bar
        L["mset_exposure"] = {s: L["exposures"].get(quiz._compose_bare_vowel(s), 0) for s in mset}
        out["lessons"][lid] = L
        if not L["stalled"]:
            quiz.complete_lesson()
        else:
            quiz.save_progress()
            break                   # a real learner can't get past a stall
    return out


# ── Report ─────────────────────────────────────────────────────────────────

def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "-"


def report(results, lessons, max_q):
    by_profile = defaultdict(list)
    for r in results:
        by_profile[r["profile"]].append(r)

    print("\n" + "=" * 78)
    print("QUESTIONS NEEDED TO FINISH EACH LESSON (median over runs; STALL = hit the cap)")
    print("=" * 78)
    header = "lesson " + "".join(f"{p[:12]:>13}" for p in by_profile)
    print(header)
    for lid in lessons:
        row = f"{lid:>6} "
        for p, runs in by_profile.items():
            done = [r["lessons"][lid] for r in runs if lid in r["lessons"]]
            stalls = sum(L["stalled"] for L in done)
            reached = len(done)
            qs = med([L["questions"] for L in done if not L["stalled"]])
            cell = f"{qs:.0f}" if qs is not None else "-"
            if stalls:
                cell += f" ({stalls}S)"
            if reached < len(runs):
                cell += f" [{reached}/{len(runs)}]"
            row += f"{cell:>13}"
        print(row)
    print("(nS) = n runs stalled at the cap; [k/n] = only k of n runs got this far")

    print("\nMINUTES OF PLAY PER LESSON (median, all learners; simulated 4-12 s/answer)")
    for lid in lessons:
        mins = [r["lessons"][lid]["minutes"] for r in results if lid in r["lessons"]]
        print(f"   L{lid:<3} {med(mins) or 0:>6.1f} min")

    print("\nTHE LONG TAIL: questions spent waiting for the LAST mastery item (median)")
    for lid in lessons:
        tails = [r["lessons"][lid]["tail"] for r in results if lid in r["lessons"]]
        qs = [r["lessons"][lid]["questions"] for r in results if lid in r["lessons"]]
        t, q = med(tails), med(qs)
        if t is not None and q:
            print(f"   L{lid:<3} last item took {t:.0f} of {q:.0f} questions ({pct(t, q)})")

    print("\nREAL READING SKILL WHEN THE APP SAYS 'MASTERED'")
    print("   (learner's true chance of reading each mastery item, typed, no choices;")
    print("    'weakest' = the least-known item in the set; median over runs)")
    print("   lesson " + "".join(f"{p[:12]:>13}" for p in by_profile if p != "guesser"))
    for lid in lessons:
        row = f"   {lid:>6} "
        for p, runs in by_profile.items():
            if p == "guesser":
                continue
            done = [r["lessons"][lid] for r in runs if lid in r["lessons"] and not r["lessons"][lid]["stalled"]]
            lo, mean = med([L["skill_min"] for L in done]), med([L["skill_mean"] for L in done])
            row += f"{(f'{100*mean:.0f}% ({100*lo:.0f}%)' if lo is not None else '-'):>13}"
        print(row)
    print("   format: average skill (weakest item)")

    g = by_profile.get("guesser")
    if g:
        bars = [(r["lessons"][1]["final_bar"], r["lessons"][1]["pool_size"]) for r in g if 1 in r["lessons"]]
        print(f"\nCONTROL (guesser, knows nothing): best mastery bar reached in lesson 1 after "
              f"{max_q} questions: {max(b for b, _ in bars)}/{bars[0][1]}")

    print("\nMASTERY BAR GOING BACKWARDS (median drops per lesson)")
    for lid in lessons:
        drops = [r["lessons"][lid]["bar_drops"] for r in results if lid in r["lessons"]]
        print(f"   L{lid:<3} {med(drops) or 0:>4.0f}")

    print("\nMODE MIX PER LESSON (share of questions, all learners)")
    for lid in lessons:
        modes = Counter()
        for r in results:
            if lid in r["lessons"]:
                modes.update(r["lessons"][lid]["modes"])
        tot = sum(modes.values())
        print(f"   L{lid:<3} " + ", ".join(f"{m} {pct(n, tot)}" for m, n in modes.most_common()))

    print("\nACCURACY BY MODE (average learner — big gaps mean a mode is much harder)")
    acc = defaultdict(lambda: [0, 0])
    for r in by_profile.get("average", []):
        for L in r["lessons"].values():
            for m, n in L["modes"].items():
                acc[m][0] += L["mode_right"][m]
                acc[m][1] += n
    for m, (a, b) in sorted(acc.items(), key=lambda kv: kv[1][0] / max(1, kv[1][1])):
        print(f"   {m:<20} {pct(a, b):>5}  ({b} questions)")

    print("\nSILENT FALLBACKS (engine picked one mode, served another)")
    fb = Counter()
    for r in results:
        for lid, L in r["lessons"].items():
            for k, n in L["fallbacks"].items():
                fb[(lid, k)] += n
    for (lid, k), n in sorted(fb.items()):
        print(f"   L{lid:<3} {k:<36} {n}")
    if not fb:
        print("   none")

    print("\nREPETITION (all learners)")
    for lid in lessons:
        b2b = sum(r["lessons"][lid]["back_to_back"] for r in results if lid in r["lessons"])
        w3 = sum(r["lessons"][lid]["repeat_within_3"] for r in results if lid in r["lessons"])
        tot = sum(r["lessons"][lid]["questions"] for r in results if lid in r["lessons"])
        print(f"   L{lid:<3} same item twice in a row {pct(b2b, tot):>4}   within 3 questions {pct(w3, tot):>4}")

    print("\nEXPOSURE SPREAD over each lesson's mastery set (average learner, median run)")
    for lid in lessons:
        spreads = []
        for r in by_profile.get("average", []):
            if lid in r["lessons"]:
                ex = list(r["lessons"][lid]["mset_exposure"].values())
                if ex:
                    spreads.append((min(ex), max(ex)))
        if spreads:
            lo = med([s[0] for s in spreads]); hi = med([s[1] for s in spreads])
            print(f"   L{lid:<3} least-asked item {lo:.0f}x, most-asked {hi:.0f}x")

    mixer = by_profile.get("eo_o_mixer", [])
    if mixer:
        print("\nADAPTIVENESS: does the ㅓ/ㅗ mixer get drilled on ㅓ/ㅗ?")
        for lid in lessons:
            d = sum(r["lessons"][lid]["drills"] for r in mixer if lid in r["lessons"])
            on = sum(r["lessons"][lid]["drills_on_confused"] for r in mixer if lid in r["lessons"])
            avg_d = sum(r["lessons"][lid]["drills"] for r in by_profile.get("average", []) if lid in r["lessons"])
            if d or avg_d:
                print(f"   L{lid:<3} mixer drills {d:>4} (on ㅓ/ㅗ: {on:>3})   average learner drills {avg_d:>4}")

    print("\nNUDGES (answered in the wrong writing system, re-prompted)")
    for p, runs in by_profile.items():
        n = sum(L["nudges"] for r in runs for L in r["lessons"].values())
        print(f"   {p:<14} {n}")

    print("\nQUESTION-QUALITY PROBLEMS (count, first example)")
    qual = Counter(); ex = {}
    for r in results:
        qual.update(r["quality"])
        for k, v in r["quality_examples"].items():
            ex.setdefault(k, v)
    for k, n in qual.most_common():
        print(f"   {n:>6}  {k}\n           e.g. {ex[k]}")
    if not qual:
        print("   none")

    bugs = [b for r in results for b in r["grading_bugs"]]
    print(f"\nGRADING BUGS (a correct answer marked wrong): {len(bugs)}")
    for b in Counter(bugs).most_common(10):
        print(f"   {b[1]}x {b[0]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--runs", type=int, default=10, help="runs per learner profile")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--max-q", type=int, default=1500,
                    help="questions per lesson before calling it a stall")
    ap.add_argument("--profiles", default=",".join(PROFILES))
    ap.add_argument("--lessons", default="1-12")
    ap.add_argument("--quick", action="store_true",
                    help="skip the on-screen render check (much faster)")
    ap.add_argument("--json", help="also write raw per-run numbers here")
    ap.add_argument("--rule", choices=sorted(RULES), default="A",
                    help="what-if mastery rule: " + "; ".join(f"{k} = {v}" for k, v in RULES.items()))
    args = ap.parse_args()
    global RULE
    RULE = args.rule
    print(f"Mastery rule {RULE}: {RULES[RULE]}")

    a, _, b = args.lessons.partition("-")
    lessons = list(range(int(a), int(b or a) + 1))
    profiles = args.profiles.split(",")

    print("Learners:")
    for p in profiles:
        print(f"   {p:<14} {PROFILES[p]['about']}")

    results = []
    t0 = _real_time.time()
    for p in profiles:
        for i in range(args.runs):
            # Check the rendered screen on the first run of each profile only.
            check = (not args.quick) and i == 0
            results.append(play_course(p, args.seed * 1000 + i, args.max_q, lessons, check))
        print(f"   ...{p} done ({_real_time.time() - t0:.0f}s)", file=sys.stderr)

    report(results, lessons, args.max_q)
    if args.json:
        slim = []
        for r in results:
            r2 = dict(r)
            r2["quality"] = dict(r["quality"])
            r2["lessons"] = {lid: {k: (dict(v) if isinstance(v, Counter) else v)
                                   for k, v in L.items() if k != "bar"}
                             for lid, L in r["lessons"].items()}
            slim.append(r2)
        Path(args.json).write_text(json.dumps(slim, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
