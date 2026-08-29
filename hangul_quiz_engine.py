"""
hangul_quiz_engine.py — Adaptive Hangul quiz engine.

Tracks user progress across lessons, identifies confusion pairs, and generates
targeted drills. Uses a small local LLM (Ollama) for creative question variants
but all game logic, scoring, and drill selection is deterministic Python.

Quiz modes: spell, read_aloud, match_sound, build_syllable, sudden_death,
            missing_vowel, batchim_challenge, confusion_drill

Usage:
    from hangul_quiz_engine import HangulQuiz
    quiz = HangulQuiz()
    quiz.start_lesson(1)
    question = quiz.next_question()
    result = quiz.answer("가")
    print(result)
"""

import json
import random
import os
import re
import time
from pathlib import Path
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from typing import Optional

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent if '__file__' in dir() else Path.cwd()
DATA_DIR = PROJECT_ROOT / "data"
CURRICULUM_PATH = DATA_DIR / "curriculum.json"
PROGRESS_PATH = DATA_DIR / "user_progress.json"


# ── Data structures ────────────────────────────────────────────────────────

@dataclass
class QuizQuestion:
    mode: str
    prompt: str
    correct_answer: str
    choices: list[str] = field(default_factory=list)
    hint: str = ""
    lesson_id: int = 0
    letter: str = ""


@dataclass
class QuizResult:
    correct: bool
    user_answer: str
    expected: str
    feedback: str
    lesson_id: int
    letter: str

# ── Confusion-pair validity ───────────────────────────────────────────────

_JAMO_CHARS = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"

# Bare vowel jamo can never stand alone in written Korean — they always
# take the silent ㅇ placeholder (ㅏ -> 아). A bare jamo and its placeholder-
# composed form are the SAME vowel, not two different letters, so anywhere
# an answer is graded or a confusion pair is tracked, both forms need to
# normalize to one before comparison. Single source of truth for that set,
# used by HangulQuiz._compose_bare_vowel.
_VOWEL_JAMO = "ㅏㅓㅗㅜㅡㅣㅑㅕㅛㅠㅐㅔㅒㅖㅘㅙㅚㅝㅞㅟㅢ"


def _looks_like_hangul_target(s: str) -> bool:
    """True if s is a single Hangul syllable block or jamo letter — the
    only kind of value that makes sense in a 'type the Hangul for X'
    confusion drill. Filters out typos/garbage and non-Hangul answers
    (e.g. read_aloud's romanization guesses aren't Hangul at all, so a
    wrong read_aloud answer should never become a confusion-drill pair)."""
    if not s or len(s) != 1:
        return False
    if 0xAC00 <= ord(s) <= 0xD7A3:
        return True
    return s in _JAMO_CHARS

# ── Romanization ───────────────────────────────────────────────────────────
# The exact spelling system read_aloud grades typed answers against. Pulled
# out to module level (rather than buried in _hangul_to_roman_hint) so it
# can be exposed via HangulQuiz.get_romanization_table() — read_aloud used
# to expect learners to somehow already know this spelling ('eo' for ㅓ,
# 'eu' for ㅡ, etc.) with no way to look it up. Now the CLI can show it.
ROMANIZATION = {
    'ㄱ': 'g', 'ㄴ': 'n', 'ㄷ': 'd', 'ㄹ': 'r/l', 'ㅁ': 'm',
    'ㅂ': 'b', 'ㅅ': 's', 'ㅇ': 'ng', 'ㅈ': 'j', 'ㅊ': 'ch',
    'ㅋ': 'k', 'ㅌ': 't', 'ㅍ': 'p', 'ㅎ': 'h',
    'ㄲ': 'kk', 'ㄸ': 'tt', 'ㅃ': 'pp', 'ㅆ': 'ss', 'ㅉ': 'jj',
    'ㅏ': 'a', 'ㅓ': 'eo', 'ㅗ': 'o', 'ㅜ': 'u', 'ㅡ': 'eu', 'ㅣ': 'i',
    'ㅑ': 'ya', 'ㅕ': 'yeo', 'ㅛ': 'yo', 'ㅠ': 'yu',
    'ㅐ': 'ae', 'ㅔ': 'e', 'ㅒ': 'yae', 'ㅖ': 'ye',
    'ㅘ': 'wa', 'ㅙ': 'wae', 'ㅚ': 'oe', 'ㅝ': 'wo', 'ㅞ': 'we',
    'ㅟ': 'wi', 'ㅢ': 'ui'
}

# ── Engine ─────────────────────────────────────────────────────────────────

class HangulQuiz:
    def __init__(self):
        self.curriculum = self._load_curriculum()
        self.progress = self._load_progress()
        self.current_lesson = None
        self.session_streak = 0
        self.session_correct = 0
        self.session_total = 0

    # ── Data loading ───────────────────────────────────────────────────

    def _load_curriculum(self) -> dict:
        with open(CURRICULUM_PATH, encoding='utf-8') as f:
            return json.load(f)

    def _load_progress(self) -> dict:
        if PROGRESS_PATH.exists():
            with open(PROGRESS_PATH, encoding='utf-8') as f:
                return json.load(f)
        return {
            "current_lesson": 1,
            "completed_lessons": [],
            "mastered_letters": {},
            "confusion_counts": {},
            "total_questions_answered": 0,
            "total_correct": 0,
            "streak_best": 0,
            "last_session": None
        }

    def save_progress(self):
        self.progress["last_session"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.progress["total_questions_answered"] = self.session_total + self.progress.get("total_questions_answered", 0)
        self.progress["total_correct"] = self.session_correct + self.progress.get("total_correct", 0)
        if self.session_streak > self.progress.get("streak_best", 0):
            self.progress["streak_best"] = self.session_streak
        PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PROGRESS_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.progress, f, indent=2, ensure_ascii=False)

    # ── Lesson management ──────────────────────────────────────────────

    def start_lesson(self, lesson_id: int = None) -> dict:
        """Begin a lesson. If no ID given, resume from last position."""
        if lesson_id is None:
            lesson_id = self.progress.get("current_lesson", 1)
        self.current_lesson = self._get_lesson(lesson_id)
        self.progress["current_lesson"] = lesson_id
        return {
            "id": lesson_id,
            "title": self.current_lesson["title"],
            "description": self.current_lesson.get("description", ""),
            "introduction": self.current_lesson.get("introduction", ""),
            "note": self.current_lesson.get("note", ""),
            "letters": self.current_lesson.get("letters", []),
            "letter_count": len(self.current_lesson.get("letters", [])),
            "confusion_pairs": self.current_lesson.get("confusion_pairs", []),
            # Reference-table material — pulled straight from curriculum.json
            # so the CLI can show a full pronunciation/stroke-order/batchim/
            # vocabulary table at the start of a lesson instead of just one
            # mnemonic. Not every lesson has every field; the CLI picks
            # whichever is present.
            "pronunciation": self.current_lesson.get("pronunciation", {}),
            "stroke_order": self.current_lesson.get("stroke_order", {}),
            "batchim_pronunciation": self.current_lesson.get("batchim_pronunciation", {}),
            "batchim_pronunciation_rules": self.current_lesson.get("batchim_pronunciation_rules", {}),
            "vocabulary": self.current_lesson.get("vocabulary", []),
            "block_rules": self.current_lesson.get("block_rules", {}),
            "letter_romanization": {l: ROMANIZATION.get(l, "") for l in self.current_lesson.get("letters", [])}
        }

    def _get_lesson(self, lesson_id: int) -> dict:
        for lesson in self.curriculum["lessons"]:
            if lesson["id"] == lesson_id:
                return lesson
        raise ValueError(f"Lesson {lesson_id} not found")

    def list_lessons(self) -> list[dict]:
        return [{"id": l["id"], "title": l["title"],
                 "completed": l["id"] in self.progress["completed_lessons"]}
                for l in self.curriculum["lessons"]]

    # ── Question generation ────────────────────────────────────────────

    def next_question(self, mode: str = None) -> QuizQuestion:
        """Generate the next quiz question. Mode is auto-chosen unless specified."""
        if self.current_lesson is None:
            self.start_lesson()

        lesson = self.current_lesson
        available_modes = ["spell", "read_aloud", "match_sound"]

        # Restrict modes based on lesson content
        if lesson.get("practice_syllables") or lesson.get("example_syllables"):
            available_modes += ["build_syllable", "missing_vowel"]
        if "batchim_pronunciation_rules" in lesson or "batchim_pronunciation" in lesson:
            available_modes.append("batchim_challenge")

        # If the user has real tracked confusions, occasionally trigger a drill.
        # If not, but this lesson calls out known-tricky pairs (e.g. ㅓ vs ㅗ),
        # drill those proactively at a lower rate — no need to wait for mistakes.
        has_confusions = any(int(v) >= 2 for v in self.progress.get("confusion_counts", {}).values())
        has_curriculum_pairs = bool(lesson.get("confusion_pairs"))
        if has_confusions and random.random() < 0.3:
            available_modes.append("confusion_drill")
        elif has_curriculum_pairs and random.random() < 0.15:
            available_modes.append("confusion_drill")

        chosen_mode = mode or random.choice(available_modes)
        return self._generate_question(chosen_mode)

    def _generate_question(self, mode: str) -> QuizQuestion:
        lesson = self.current_lesson

        if mode == "spell":
            return self._spell_question(lesson)
        elif mode == "read_aloud":
            return self._read_aloud_question(lesson)
        elif mode == "match_sound":
            return self._match_sound_question(lesson)
        elif mode == "build_syllable":
            return self._build_syllable_question(lesson)
        elif mode == "missing_vowel":
            return self._missing_vowel_question(lesson)
        elif mode == "batchim_challenge":
            return self._batchim_question(lesson)
        elif mode == "confusion_drill":
            return self._confusion_drill_question()
        else:
            return self._spell_question(lesson)

    def _make_choices(self, target: str, pool: list[str], n: int = 4) -> list[str]:
        """Build a shuffled multiple-choice list: target plus up to n-1
        wrong answers drawn from pool, padded from the broader known-
        syllable set if pool is too small to supply enough distinct wrong
        answers. Originally only match_sound had this — pulled out so any
        mode can offer a letter-choice alternative alongside typing."""
        candidates = [s for s in pool if s != target]
        wrong = random.sample(candidates, min(n - 1, len(candidates)))
        if len(wrong) < n - 1:
            extra_pool = self._get_known_syllables()
            extra = [s for s in extra_pool if s != target and s not in wrong]
            wrong += random.sample(extra, min(n - 1 - len(wrong), len(extra)))
        choices = [target] + wrong
        random.shuffle(choices)
        return choices

    @staticmethod
    def resolve_choice(user_input: str, choices: list[str]) -> str:
        """If user_input looks like a letter answer ('B', 'B)', 'a.', etc.)
        for a question that has choices, resolve it to the actual choice
        text. Otherwise return user_input unchanged, so typing the real
        answer directly always still works. Shared by answer() and by any
        CLI handler (like /kspell) that grades outside the main quiz loop,
        so letter-answering works everywhere choices exist, not just in
        the original three multiple-choice modes."""
        if not choices:
            return user_input
        letter_only = user_input.strip(" .)():-").upper()
        if len(letter_only) == 1 and letter_only in "ABCD":
            idx = ord(letter_only) - ord('A')
            if idx < len(choices):
                return choices[idx]
        return user_input

    def _spell_question(self, lesson: dict) -> QuizQuestion:
        """Show romanization, user types Hangul — or picks from a
        multiple-choice list for anyone without a way to type Hangul."""
        pool = self._get_lesson_syllable_pool(lesson)
        target = random.choice(pool)

        roman = self._hangul_to_roman_hint(target)
        cho, jung, jong = self._decompose_syllable(target)
        if not cho and not jung:
            # Bare single jamo (a letter, not a composed syllable) — e.g.
            # a consonant shown on its own for pure letter recognition.
            # Previously this ended with "just type {target}" — a hint
            # that IS the answer. Describes the expected answer FORMAT
            # instead (a lone jamo, not a composed block) without naming
            # the letter itself.
            hint = f"This is a single jamo on its own, no vowel attached — write just that one shape (romanizes as '{roman}')."
        elif cho == 'ㅇ' and not jong:
            # Vowel-only syllable — Korean can't write a bare vowel, so it
            # always gets a silent ㅇ placeholder in front. Previously
            # ended with ": {target}" — the composed answer itself. Now
            # names the target VOWEL jamo (jung) for clarity — since that's
            # not the final answer, just one ingredient in it — without
            # spelling out the composed syllable that combines it with ㅇ.
            hint = f"The vowel {jung} romanizes as '{roman}'. Since a vowel can't stand alone in Korean, it gets a silent 'ㅇ' glued onto the front, combining into one syllable block."
        elif cho and jung:
            # Fixed a real bug here too: this used to slice the
            # romanization STRING assuming the consonant is always exactly
            # one character (roman[0]) — which silently breaks for ㄹ
            # ('r/l') and every tense consonant ('kk','tt','pp','ss','jj').
            # E.g. for 까 it would've said "starts with 'k', vowel 'ka'"
            # instead of "starts with 'kk', vowel 'a'". Looking up each
            # jamo's own romanization directly avoids that.
            cho_roman = ROMANIZATION.get(cho, '?')
            jung_roman = ROMANIZATION.get(jung, '?')
            if jong:
                jong_roman = ROMANIZATION.get(jong, '?')
                hint = f"It starts with '{cho_roman}', has the vowel '{jung_roman}', and ends with a '{jong_roman}' batchim sound."
            else:
                hint = f"It starts with '{cho_roman}' and has the vowel '{jung_roman}'."
        else:
            # Previously "The answer is {target}" — an outright giveaway.
            hint = f"Sound out the romanization '{roman}' one piece at a time."
        return QuizQuestion(
            mode="spell",
            prompt=f"Type the Hangul for: **{roman}**",
            correct_answer=target,
            choices=self._make_choices(target, pool),
            hint=hint,
            lesson_id=lesson["id"],
            letter=target
        )

    def _read_aloud_question(self, lesson: dict) -> QuizQuestion:
        """Show Hangul, ask the user to type its romanization. Graded by
        exact match against the app's spelling system (see ROMANIZATION /
        get_romanization_table()) — not a spoken self-report, so the prompt
        and hint say so explicitly rather than implying you just say it
        aloud and press Enter."""
        target = random.choice(self._get_lesson_syllable_pool(lesson))

        return QuizQuestion(
            mode="read_aloud",
            prompt=f"How would you romanize **{target}**? (Type it — e.g. 'ga', 'eo', 'wae')",
            correct_answer=self._hangul_to_roman_hint(target),
            hint="Not sure of the spelling system? Type /roman to see the full romanization key.",
            lesson_id=lesson["id"],
            letter=target
        )

    def _match_sound_question(self, lesson: dict) -> QuizQuestion:
        """Multiple choice: pick the right Hangul given romanization."""
        items = self._get_lesson_syllable_pool(lesson)
        if len(items) < 4:
            # Supplement from previous lessons
            pool = self._get_known_syllables()
            items = (list(set(items + random.sample(pool, min(4 - len(items), len(pool))))))
        target = random.choice(items)
        return QuizQuestion(
            mode="match_sound",
            prompt=f"Which Hangul is pronounced **{self._hangul_to_roman_hint(target)}**?",
            correct_answer=target,
            choices=self._make_choices(target, items),
            lesson_id=lesson["id"],
            letter=target
        )

    def _build_syllable_question(self, lesson: dict) -> QuizQuestion:
        """Give consonant + vowel, user assembles the syllable — or picks
        the finished result from a multiple-choice list."""
        pool = lesson.get("practice_syllables") or lesson.get("example_syllables")
        if pool:
            target = random.choice(pool)
        else:
            return self._spell_question(lesson)  # fallback

        # Decompose syllable into consonant + vowel
        cho, jung, jong = self._decompose_syllable(target)
        return QuizQuestion(
            mode="build_syllable",
            prompt=f"Build the syllable for **{self._hangul_to_roman_hint(target)}**\n"
                   f"Consonant: {cho}  |  Vowel: {jung}" +
                   (f"  |  Batchim: {jong}" if jong else ""),
            correct_answer=target,
            choices=self._make_choices(target, pool),
            hint=f"Place {'them vertically' if jung in 'ㅏㅓㅣㅐㅔㅑㅕㅒㅖ' else 'them horizontally'}",
            lesson_id=lesson["id"],
            letter=target
        )

    def _missing_vowel_question(self, lesson: dict) -> QuizQuestion:
        """Show consonant + romanization, user picks the vowel."""
        pool = lesson.get("practice_syllables") or lesson.get("example_syllables")
        if pool:
            target = random.choice(pool)
        else:
            return self._spell_question(lesson)

        cho, jung, jong = self._decompose_syllable(target)
        roman = self._hangul_to_roman_hint(target)
        vowel_options = random.sample(["ㅏ", "ㅓ", "ㅗ", "ㅜ", "ㅡ", "ㅣ", "ㅑ", "ㅕ", "ㅛ", "ㅠ", "ㅐ", "ㅔ"], 4)
        if jung not in vowel_options:
            vowel_options[random.randint(0, 3)] = jung
        random.shuffle(vowel_options)
        return QuizQuestion(
            mode="missing_vowel",
            prompt=f"**{cho}** + ? = **{roman}**\nWhich vowel completes it?",
            correct_answer=jung,
            choices=vowel_options,
            hint=f"Think: '{roman}' — what vowel makes that sound after '{cho}'?",
            lesson_id=lesson["id"],
            letter=target
        )

    def _batchim_sound_groups(self) -> dict:
        """Map each batchim letter to the OTHER letters that share its
        real pronunciation, from curriculum data (batchim_pronunciation_
        rules — e.g. lesson 11's 'ㄷㅌㅅㅆㅈㅊㅎ all pronounced as ㄷ [t]').
        Used to pick genuinely confusable wrong answers: letters that
        SOUND the same but are spelled differently. Without this, a
        prompt or hint that names the target sound is a complete
        giveaway whenever the candidate letters each have a distinct
        sound — as they do in the simplified 7-letter set used before
        this rule data exists. With it, sound alone no longer picks a
        unique answer, so getting it right actually takes knowing the
        spelling, not just reading off the sound."""
        groups = {}
        for lesson in self.curriculum.get("lessons", []):
            rules = lesson.get("batchim_pronunciation_rules")
            if not rules:
                continue
            for letters_str, _desc in rules.items():
                letters = list(letters_str)
                for l in letters:
                    groups.setdefault(l, set()).update(x for x in letters if x != l)
        return groups

    def _batchim_question(self, lesson: dict) -> QuizQuestion:
        """Show word with missing batchim, user picks correct final consonant."""
        examples = lesson.get("example_syllables", [])
        if not examples:
            return self._spell_question(lesson)

        target = random.choice(examples)
        cho, jung, jong = self._decompose_syllable(target)
        if not jong:
            return self._spell_question(lesson)

        batchim_options = ["ㄱ", "ㄴ", "ㄷ", "ㄹ", "ㅁ", "ㅂ", "ㅇ"]

        # Prefer distractors that share the target's REAL sound (per
        # curriculum pronunciation-rule data) over arbitrary other
        # letters — see _batchim_sound_groups for why.
        sound_groups = self._batchim_sound_groups()
        confusable = list(sound_groups.get(jong, []))
        wrong = random.sample(confusable, min(3, len(confusable)))
        if len(wrong) < 3:
            remaining = [b for b in batchim_options if b != jong and b not in wrong]
            wrong += random.sample(remaining, min(3 - len(wrong), len(remaining)))
        choices = [jong] + wrong
        random.shuffle(choices)

        # The hint naming the target sound is only a fair partial hint
        # when at least one WRONG choice shares that same sound — only
        # then does "the sound is X" fail to single out one letter on its
        # own. If no confusable distractor made it into this question
        # (no rule data yet for this letter — the simplified early-lesson
        # set), say so honestly rather than presenting a full giveaway as
        # if it were a nudge.
        sound = self._batchim_sound(jong)
        same_sound_in_choices = any(
            c != jong and self._batchim_sound(c) == sound for c in choices
        )
        if same_sound_in_choices:
            hint = f"The final sound is '{sound}' — but more than one letter here can make that sound, so go by spelling, not sound alone."
        else:
            hint = f"The final sound is '{sound}'."

        return QuizQuestion(
            mode="batchim_challenge",
            prompt=f"**{cho}{jung}** + ?\nWhich batchim completes **{self._hangul_to_roman_hint(target)}**?",
            correct_answer=jong,
            choices=choices,
            hint=hint,
            lesson_id=lesson["id"],
            letter=target
        )

    def _lesson_relevant(self, s: str, lesson: dict) -> bool:
        """True if s is one of THIS lesson's own listed letters, or is
        literally one of its practice/example/vocabulary syllables — not
        just 'shares a vowel with something in the lesson,' which would
        match almost anything (nearly every syllable in every lesson
        contains one of the six basic vowels, so that check would still
        let old vowel-confusion pairs sneak into an unrelated batchim or
        consonant lesson in disguise)."""
        if s in lesson.get("letters", []):
            return True
        if s in lesson.get("practice_syllables", []):
            return True
        if s in lesson.get("example_syllables", []):
            return True
        if any(s == v.get("word") for v in lesson.get("vocabulary", [])):
            return True
        return False

    def _confusion_drill_question(self) -> QuizQuestion:
        """Target letters the user consistently confuses — scoped to the
        CURRENT lesson wherever possible. Confusion counts persist across
        every session forever with no decay, so without this scoping the
        biggest historical count (almost always early vowel mistakes from
        lesson 1, which had a huge head start accumulating) permanently
        drowns out anything from later lessons — you'd get drilled on
        아/어/이/우/으 in a batchim lesson ten sessions later. Preference
        order: (1) worst mistake relevant to this lesson, (2) curriculum-
        suggested pair for this lesson, (3) worst mistake overall as a
        last resort so the drill still has something to show."""
        confusion_counts = self.progress.get("confusion_counts", {})
        tracked_pairs = []
        for k, v in confusion_counts.items():
            if v < 1 or "↔" not in k:
                continue
            parts = k.split("↔")
            # Defensively re-validate even old/pre-existing entries — a
            # bad pair saved before this check existed shouldn't come
            # back to haunt future drills.
            if len(parts) == 2 and all(_looks_like_hangul_target(p) for p in parts):
                tracked_pairs.append((k, v))

        # Bare vowel jamo are never valid standalone Korean writing —
        # compose them with the silent ㅇ placeholder before ever showing
        # or requiring one as an answer (e.g. ㅓ vs ㅗ becomes 어 vs 오).
        # Consonants stay bare, since naming a consonant letter on its own
        # is correct as-is. See _compose_bare_vowel for the shared rule.
        compose = self._compose_bare_vowel

        def is_lesson_relevant(pa: str, pb: str) -> bool:
            return (self._lesson_relevant(pa, self.current_lesson)
                    or self._lesson_relevant(pb, self.current_lesson))

        def non_degenerate_pairs():
            """Yields (pa, pb) composed pairs, worst (highest count) first,
            skipping ones that collapse to the same letter once composed."""
            for pair_key, _count in sorted(tracked_pairs, key=lambda kv: -kv[1]):
                pa, pb = pair_key.split("↔")
                pa, pb = compose(pa), compose(pb)
                if pa != pb:
                    yield pa, pb

        a = b = None

        # Preference 1: worst mistake that's actually relevant to the
        # lesson you're in right now.
        for pa, pb in non_degenerate_pairs():
            if is_lesson_relevant(pa, pb):
                a, b = pa, pb
                break

        # Preference 2: no relevant tracked mistake yet — proactively
        # drill a pair this lesson calls out as commonly confused.
        if a is None:
            groups = [g for g in self.current_lesson.get("confusion_pairs", []) if len(g) >= 2]
            if groups:
                a, b = random.sample(random.choice(groups), 2)
                a, b = compose(a), compose(b)

        # Preference 3 (last resort): no lesson-relevant data at all —
        # fall back to the single worst mistake overall, same as the old
        # behavior, rather than showing nothing.
        if a is None:
            for pa, pb in non_degenerate_pairs():
                a, b = pa, pb
                break

        if a is None:
            return self._spell_question(self.current_lesson)

        target = random.choice([a, b])
        other = b if target == a else a

        # Choices always include both drilled letters (target and the
        # thing it's confused with), padded with a couple more distractors
        # so it's not a trivial two-option pick given the "not X" prompt
        # already names one of them.
        pool_source = self._get_lesson_syllable_pool(self.current_lesson) if self.current_lesson else []
        extras = [s for s in pool_source if s not in (target, other)]
        pad = random.sample(extras, min(2, len(extras)))
        if len(pad) < 2:
            known = self._get_known_syllables()
            more = [s for s in known if s not in (target, other) and s not in pad]
            pad += random.sample(more, min(2 - len(pad), len(more)))
        choices = [target, other] + pad
        random.shuffle(choices)

        return QuizQuestion(
            mode="confusion_drill",
            prompt=f"⚠️ Confusion drill! Type the Hangul for:\n"
                   f"**{self._hangul_to_roman_hint(target)}**  (not {self._hangul_to_roman_hint(other)})",
            correct_answer=target,
            choices=choices,
            hint=f"Careful — commonly confused with {other}. Both look/sound similar.",
            lesson_id=0,
            letter=target
        )

    # ── Answer checking ────────────────────────────────────────────────

    def answer(self, user_input: str, question: QuizQuestion = None) -> QuizResult:
        """Check the user's answer against the expected."""
        if question is None:
            question = getattr(self, '_last_question', None)
        self._last_question = question

        # If this question has choices, a bare/punctuated A-D letter
        # resolves to the choice it refers to — this now applies to EVERY
        # mode that has choices (spell, build_syllable, and
        # confusion_drill included, not just the original three
        # multiple-choice modes), so anyone without a way to type Hangul
        # has a path through every mode. Direct typing still passes
        # through unchanged for anyone who didn't type a letter.
        user_clean = self.resolve_choice(user_input.strip(), question.choices)
        expected = question.correct_answer

        # A bare vowel jamo and its silent-ㅇ-composed form are the same
        # vowel (see _compose_bare_vowel) — normalize both sides before
        # grading so typing 'ㅏ' when 아 is expected (or the reverse)
        # counts as correct. Skipped for read_aloud, whose 'expected' is
        # a romanization string like 'eo', not Hangul at all. ALSO
        # skipped for missing_vowel: that mode's correct_answer and
        # choices are deliberately bare vowel jamo representing a
        # COMPONENT of a larger consonant+vowel+batchim formula (e.g.
        # 'ㄱ + ? = guk'), never a free-standing composed syllable —
        # composing 'ㅜ' into '우' here would show a "correct" answer
        # that was never actually one of the options on screen.
        if question.mode not in ("read_aloud", "missing_vowel"):
            user_clean = self._compose_bare_vowel(user_clean)
            expected = self._compose_bare_vowel(expected)

        is_correct = False
        feedback = ""

        if question.mode == "read_aloud":
            # Graded as an exact romanization spelling match — see
            # _read_aloud_question for why this isn't a spoken self-report.
            is_correct = user_clean.lower() == expected.lower()
            if is_correct:
                feedback = f"✅ Correct! **{question.letter}** romanizes as **{expected}**."
            else:
                feedback = f"❌ **{question.letter}** romanizes as **{expected}**. You typed '{user_clean}'."
        elif question.mode in ("match_sound", "missing_vowel", "batchim_challenge"):
            is_correct = user_clean == expected
            if is_correct:
                feedback = f"✅ Correct! **{expected}** is right."
            else:
                feedback = f"❌ Not quite. The answer is **{expected}**."
        else:
            is_correct = user_clean == expected
            if is_correct:
                feedback = f"✅ Perfect! **{user_clean}** is correct."
            else:
                feedback = f"❌ You typed **{user_clean}** but the answer is **{expected}**."

        # Track progress
        self.session_total += 1
        if is_correct:
            self.session_correct += 1
            self.session_streak += 1
            self._mark_mastered(question.letter, confidence=1)
        else:
            self.session_streak = 0
            self._mark_mastered(question.letter, confidence=-1)
            # Record confusion — only when both sides are real single
            # Hangul/jamo characters. read_aloud's "expected" is a
            # romanization string (e.g. "eo"), not Hangul, so a wrong
            # read_aloud guess should never be recorded here; same for any
            # stray typo the user typed that isn't a plausible letter.
            if (question.letter and user_clean
                    and _looks_like_hangul_target(user_clean)
                    and _looks_like_hangul_target(expected)):
                pair = f"{user_clean}↔{expected}"
                self.progress.setdefault("confusion_counts", {})
                self.progress["confusion_counts"][pair] = self.progress["confusion_counts"].get(pair, 0) + 1

        return QuizResult(
            correct=is_correct,
            user_answer=user_clean,
            expected=expected,
            feedback=feedback,
            lesson_id=question.lesson_id,
            letter=question.letter
        )

    def _mark_mastered(self, item: str, confidence: int):
        """Track which letters/syllables the user knows. +1 for correct, -1 for wrong."""
        if not item:
            return
        self.progress.setdefault("mastered_letters", {})
        current = self.progress["mastered_letters"].get(item, 0)
        self.progress["mastered_letters"][item] = max(0, min(5, current + confidence))

    # ── Progress & stats ──────────────────────────────────────────────

    def get_mastered_syllables(self, min_confidence: int = 3) -> list[str]:
        """Mastered letters/syllables at or above min_confidence, filtered
        to valid single-Hangul-character keys — the same defensive check
        get_progress_summary applies. Public so hangul_cli.py (which feeds
        this into sentence generation) doesn't need to read
        quiz.progress['mastered_letters'] raw and risk passing a stale
        invalid key (e.g. the historical 'wrong' entry) into code that
        expects an actual syllable, like has_real_consonant/
        _decompose_syllable."""
        return [k for k, v in self.progress.get("mastered_letters", {}).items()
                if v >= min_confidence and _looks_like_hangul_target(k)]

    def get_progress_summary(self) -> dict:
        # Defensively filter to valid single-Hangul-character keys only —
        # same principle as _top_confusions/_confusion_drill_question re-
        # validating old confusion pairs. mastered_letters had no such
        # guard, so a stale invalid key from an already-fixed bug (e.g. a
        # literal "wrong" from an old code path) could still inflate these
        # counts if it ever reached >=3, even with no current way to write
        # one. This makes the read side safe regardless of what's already
        # sitting in a given user's saved progress file.
        valid_mastered = {k: v for k, v in self.progress.get("mastered_letters", {}).items()
                           if _looks_like_hangul_target(k)}
        return {
            "current_lesson": self.progress["current_lesson"],
            "completed_lessons": self.progress["completed_lessons"],
            "mastered_count": sum(1 for v in valid_mastered.values() if v >= 3),
            "total_mastered": len(valid_mastered),
            "session_streak": self.session_streak,
            "session_score": f"{self.session_correct}/{self.session_total}",
            "session_pct": round(100 * self.session_correct / max(1, self.session_total)),
            "streak_best": self.progress.get("streak_best", 0),
            "top_confusions": self._top_confusions(5)
        }

    def _top_confusions(self, n: int = 5) -> list:
        counts = self.progress.get("confusion_counts", {})

        # See _compose_bare_vowel for why this normalization is needed
        # before comparing or displaying pairs — a bare vowel jamo and its
        # placeholder-composed form (ㅏ vs 아) are the same vowel, and
        # without this, pairs like 'ㅏ↔아' showed up in "Practice these"
        # as fake confusions.
        compose = self._compose_bare_vowel

        # Merge by unordered pair so 'a↔b' and 'b↔a' (or two raw keys that
        # normalize to the same pair once composed) count as one entry
        # rather than splitting the same confusion across display rows.
        merged = {}
        for k, v in counts.items():
            parts = k.split("↔")
            if len(parts) != 2 or not all(_looks_like_hangul_target(p) for p in parts):
                continue
            pa, pb = compose(parts[0]), compose(parts[1])
            if pa == pb:
                continue  # degenerate — same vowel, different written form
            key = frozenset((pa, pb))
            if key not in merged:
                merged[key] = [pa, pb, 0]
            merged[key][2] += v

        sorted_pairs = sorted(merged.values(), key=lambda x: -x[2])[:n]
        return [{"pair": f"{pa}↔{pb}", "count": v} for pa, pb, v in sorted_pairs]

    def complete_lesson(self):
        """Mark the current lesson as completed."""
        if self.current_lesson:
            lid = self.current_lesson["id"]
            if lid not in self.progress["completed_lessons"]:
                self.progress["completed_lessons"].append(lid)
            self.progress["current_lesson"] = min(lid + 1, len(self.curriculum["lessons"]))
            self.save_progress()
            return f"Lesson {lid} complete! Next: Lesson {self.progress['current_lesson']}"
        return "No active lesson."

    # ── Helpers ────────────────────────────────────────────────────────

    def _compose_bare_vowel(self, s: str) -> str:
        """Normalize a bare vowel jamo to its silent-ㅇ-composed syllable
        form (ㅏ -> 아); anything else (consonants, already-composed
        syllables, multi-char strings) passes through unchanged. Single
        source of truth for this — used when GRADING an answer (answer()),
        when picking a confusion-drill pair (_confusion_drill_question),
        and when summarizing confusion stats (_top_confusions) — so a
        learner typing 'ㅏ' where 아 is expected is treated as the same
        vowel everywhere in the app, not a wrong answer or a fake
        confusion between two 'different' letters in some call sites and
        not others."""
        return self._letter_to_syllable(s) if s in _VOWEL_JAMO else s

    def _letter_to_syllable(self, letter: str) -> str:
        """Combine a letter with a default vowel/consonant to make a full syllable block."""
        if letter in "ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎㄲㄸㅃㅆㅉ":
            return self._compose_syllable(letter, "ㅏ", "")  # default: add 'a'
        if letter in "ㅏㅓㅗㅜㅡㅣㅑㅕㅛㅠㅐㅔㅒㅖㅘㅙㅚㅝㅞㅟㅢ":
            return self._compose_syllable("ㅇ", letter, "")  # default: add silent 'ㅇ'
        return letter

    def _get_lesson_syllable_pool(self, lesson: dict) -> list[str]:
        """Best available pool of quizzable single-syllable strings for a
        lesson, in priority order:
          1. practice_syllables — curated drill set, if the lesson has one
          2. example_syllables — real-word examples (e.g. batchim lessons)
          3. letters — bare letters, composed with the silent ㅇ placeholder
             if they're vowels (consonants are fine shown bare)
          4. a small hardcoded default, so callers never get an empty pool
        This single fallback chain is shared by spell/read_aloud/match_sound
        so a lesson only needs to add ONE of these fields to become usable —
        no more silently falling back to hardcoded '가' content."""
        if lesson.get("practice_syllables"):
            return lesson["practice_syllables"]
        if lesson.get("example_syllables"):
            return lesson["example_syllables"]
        if lesson.get("letters"):
            pool = []
            for letter in lesson["letters"]:
                if letter in "ㅏㅓㅗㅜㅡㅣㅑㅕㅛㅠㅐㅔㅒㅖㅘㅙㅚㅝㅞㅟㅢ":
                    pool.append(self._letter_to_syllable(letter))
                else:
                    pool.append(letter)
            return pool
        return ["가", "나", "다"]

    def _compose_syllable(self, cho: str, jung: str, jong: str = "") -> str:
        """Compose a Hangul syllable block from jamo components."""
        CHOSEONG = ['ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ','ㅆ',
                     'ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']
        JUNGSEONG = ['ㅏ','ㅐ','ㅑ','ㅒ','ㅓ','ㅔ','ㅕ','ㅖ','ㅗ','ㅘ','ㅙ','ㅚ',
                      'ㅛ','ㅜ','ㅝ','ㅞ','ㅟ','ㅠ','ㅡ','ㅢ','ㅣ']
        JONGSEONG = ['','ㄱ','ㄲ','ㄳ','ㄴ','ㄵ','ㄶ','ㄷ','ㄹ','ㄺ','ㄻ','ㄼ',
                      'ㄽ','ㄾ','ㄿ','ㅀ','ㅁ','ㅂ','ㅄ','ㅅ','ㅆ','ㅇ','ㅈ',
                      'ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']
        try:
            cho_idx = CHOSEONG.index(cho)
            jung_idx = JUNGSEONG.index(jung)
            jong_idx = JONGSEONG.index(jong) if jong else 0
            code = 0xAC00 + (cho_idx * 21 * 28) + (jung_idx * 28) + jong_idx
            return chr(code)
        except ValueError:
            return cho + jung + jong  # fallback for non-standard combinations

    def _hangul_to_roman_hint(self, hangul: str) -> str:
        """Simple romanization hint for a syllable or letter."""
        # Handle single letters
        single_map = ROMANIZATION
        if hangul in single_map:
            return single_map[hangul]

        # Syllable decomposition
        try:
            cho, jung, jong = self._decompose_syllable(hangul)
            roman_cho = single_map.get(cho, '?')
            roman_jung = single_map.get(jung, '?')

            # Silent ㅇ: just the vowel sound
            if cho == 'ㅇ' and not jong:
                return roman_jung

            roman_jong = f"-{single_map.get(jong, '?')}" if jong else ""
            return f"{roman_cho}{roman_jung}{roman_jong}"
        except:
            return hangul

    def get_romanization_table(self) -> dict:
        """Public accessor for the exact jamo -> romanization spelling used
        to grade read_aloud answers, so the CLI can show learners the full
        key instead of leaving them to guess the spelling system."""
        return dict(ROMANIZATION)

    def has_real_consonant(self, syllable: str) -> bool:
        """True if a syllable has a genuine initial consonant sound, not
        just the silent ㅇ placeholder — i.e. it's actually capable of
        carrying lexical meaning as part of a real word. A bare-vowel
        form like 아/어/오 (composed with the placeholder so it can be
        written at all) is NOT real-word material on its own: stringing
        several of them together isn't a Korean sentence, just noise.
        Used to gate constrained sentence generation — asking an LLM for
        a "real, natural sentence" using only vowel-placeholder syllables
        is an impossible task and just produces a hallucinated string
        with a made-up translation."""
        cho, jung, jong = self._decompose_syllable(syllable)
        return bool(cho) and cho != 'ㅇ'

    def _decompose_syllable(self, syllable: str) -> tuple:
        """Decompose a Hangul syllable into (choseong, jungseong, jongseong)."""
        if len(syllable) == 1 and ord(syllable) < 0xAC00:
            # Single jamo, not a syllable
            return ('', '', '')

        code = ord(syllable) - 0xAC00
        jong = code % 28
        jung = ((code - jong) // 28) % 21
        cho = ((code - jong) // 28) // 21

        CHOSEONG = ['ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ','ㅆ',
                     'ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']
        JUNGSEONG = ['ㅏ','ㅐ','ㅑ','ㅒ','ㅓ','ㅔ','ㅕ','ㅖ','ㅗ','ㅘ','ㅙ','ㅚ',
                      'ㅛ','ㅜ','ㅝ','ㅞ','ㅟ','ㅠ','ㅡ','ㅢ','ㅣ']
        JONGSEONG = ['','ㄱ','ㄲ','ㄳ','ㄴ','ㄵ','ㄶ','ㄷ','ㄹ','ㄺ','ㄻ','ㄼ',
                      'ㄽ','ㄾ','ㄿ','ㅀ','ㅁ','ㅂ','ㅄ','ㅅ','ㅆ','ㅇ','ㅈ',
                      'ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']

        return (CHOSEONG[cho], JUNGSEONG[jung], JONGSEONG[jong] if jong > 0 else '')

    def _batchim_sound(self, jong: str) -> str:
        """Get the real pronounced sound for a batchim letter. Derived
        from curriculum data (batchim_pronunciation_rules — same source
        as _batchim_sound_groups) rather than a separately hand-
        maintained table. That old table had silently drifted out of
        sync with the curriculum's own groups — it was missing ㅋ and ㄺ
        entirely, despite the curriculum explicitly listing both under
        'ㄱㄲㅋㄳㄺ → k'. Deriving from one authoritative source avoids
        that kind of drift happening again."""
        for lesson in self.curriculum.get("lessons", []):
            rules = lesson.get("batchim_pronunciation_rules")
            if not rules:
                continue
            for letters_str, desc in rules.items():
                if jong in letters_str:
                    match = re.search(r'\[(\w+)\]', desc)
                    if match:
                        return match.group(1)
        # Simplified early-lesson letters (ㄱㄴㄷㄹㅁㅂㅇ) are taught before
        # batchim_pronunciation_rules exists, each as its own plain sound.
        simple = {'ㄱ': 'k', 'ㄴ': 'n', 'ㄷ': 't', 'ㄹ': 'l', 'ㅁ': 'm', 'ㅂ': 'p', 'ㅇ': 'ng'}
        return simple.get(jong, '?')

    def _get_known_syllables(self) -> list[str]:
        """Get all syllables from completed lessons."""
        known = []
        for lesson in self.curriculum["lessons"]:
            if lesson["id"] in self.progress["completed_lessons"]:
                known.extend(lesson.get("practice_syllables", []))
                known.extend(lesson.get("example_syllables", []))
        if not known:
            known = ["가", "나", "다", "라", "마", "바", "사", "아", "자"]
        return known

    # ── Konglish mode ──────────────────────────────────────────────────

    def _load_konglish(self) -> dict:
        with open(DATA_DIR / "konglish_vocab.json", encoding='utf-8') as f:
            return json.load(f)

    def get_konglish_vocab(self) -> dict:
        """Public accessor for the word/meaning vocab data (same source
        Konglish quizzes use) — for anything outside this class that
        needs real word+meaning pairs, e.g. building genuinely meaningful
        template sentences without an LLM."""
        return self._load_konglish()

    def konglish_question(self, category: str = None) -> QuizQuestion:
        """Generate a Konglish decoding question — show Korean, user guesses English."""
        vocab = self._load_konglish()
        all_words = []
        cats = list(vocab["categories"].keys()) if category is None else [category]
        for cat in cats:
            if cat in vocab["categories"]:
                all_words.extend(vocab["categories"][cat])

        word = random.choice(all_words)
        return QuizQuestion(
            # Romanization used to be spliced straight into the prompt text
            # (visible unconditionally, before the learner even attempts it).
            # It's a gated hint now — only shown on /hint — so sounding it
            # out from the raw hangul is the actual exercise.
            mode="konglish",
            prompt=f"Sound this out and guess the English word:\n\n   **{word['ko']}**",
            correct_answer=word["en"],
            hint=f"Romanized: {word['hint']} — read each syllable block out loud.",
            lesson_id=0,
            letter=word["ko"]
        )

    def konglish_spell_question(self) -> QuizQuestion:
        """Show English word, user spells it in Hangul — or picks from a
        multiple-choice list of other words' Hangul spellings."""
        vocab = self._load_konglish()
        all_words = []
        for cat in vocab["categories"]:
            all_words.extend(vocab["categories"][cat])

        word = random.choice(all_words)
        other_spellings = [w["ko"] for w in all_words if w["ko"] != word["ko"]]
        choices = [word["ko"]] + random.sample(other_spellings, min(3, len(other_spellings)))
        random.shuffle(choices)
        return QuizQuestion(
            mode="konglish_spell",
            # Romanization used to sit unconditionally in the prompt here
            # too (same bug already fixed for konglish_question) — moved
            # into the gated hint so spelling it out is the real exercise.
            prompt=f"Spell this in Hangul: **{word['en']}**",
            correct_answer=word["ko"],
            choices=choices,
            hint=f"Romanized: {word['hint']} — it's written exactly how it sounds.",
            lesson_id=0,
            letter=word["ko"]
        )


# ── Demo ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    quiz = HangulQuiz()
    info = quiz.start_lesson(1)
    print(f"Lesson {info['id']}: {info['title']}")
    print(f"Letters: {', '.join(info['letters'])}")

    for i in range(5):
        q = quiz.next_question()
        print(f"\n--- {q.mode} ---")
        print(q.prompt)
        if q.choices:
            print(f"  Choices: {' | '.join(q.choices)}")
        user = input("> ").strip()
        result = quiz.answer(user, q)
        print(result.feedback)
        print(f"  Streak: {quiz.session_streak}")

    print(f"\n{quiz.get_progress_summary()}")
