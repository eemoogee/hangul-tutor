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
import math
import random
import os
import re
import sys
import time
from pathlib import Path
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from typing import Optional

# ── Paths ──────────────────────────────────────────────────────────────────
# Read-only data ships with the app; when frozen by PyInstaller it is bundled
# and extracted to sys._MEIPASS. Writable progress lives next to the exe when
# frozen (a onefile exe's temp dir would otherwise be wiped on exit).
PROJECT_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
DATA_DIR = PROJECT_ROOT / "data"
CURRICULUM_PATH = DATA_DIR / "curriculum.json"
WORD_CONTRASTS_PATH = DATA_DIR / "word_contrasts.json"
KONGLISH_VOCAB_PATH = DATA_DIR / "konglish_vocab.json"
READING_PRACTICE_PATH = DATA_DIR / "reading_practice.jsonl"
TATOEBA_KOR_PATH = DATA_DIR / "tatoeba_kor_sentences.tsv"
PROGRESS_PATH = (Path(sys.executable).parent if getattr(sys, "frozen", False) else DATA_DIR) / "user_progress.json"


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
    other: str = ""
    direction: str = ""
    contrast_type: str = ""
    example_ko: str = ""
    example_en: str = ""
    other_example_ko: str = ""
    other_example_en: str = ""
    # Alternate accepted answers beyond correct_answer — currently used by
    # read_word, whose vocabulary entries carry an accepted_romanizations
    # list (e.g. both 'hangul' and 'hangeul'). Empty for every other mode,
    # which just grade against correct_answer as before.
    accepted: list[str] = field(default_factory=list)


@dataclass
class QuizResult:
    correct: bool
    user_answer: str
    expected: str
    feedback: str
    lesson_id: int
    letter: str


@dataclass
class Syllable:
    """Everything a renderer needs to show one Hangul syllable block AND
    its relationship to its parts, in one place. This is the shared seam
    between the quiz engine (which already has correct compose/decompose/
    romanize logic, buried in private HangulQuiz methods) and any
    presentation code (CLI reference tables, contrastive rows, confusion
    drills) that wants to display a block alongside its components —
    exactly the pairing the title screen's _composition_rows() does by
    hand today for exactly two hardcoded words.

    text: the composed block itself, e.g. '한'.
    romanization: the whole-syllable romanization, e.g. 'han'.
    cho / jung / jong: the raw jamo parts ('' for jong when there is no
        final consonant), same as HangulQuiz._decompose_syllable returns.
    components: (jamo, romanization) pairs in left-to-right/top-to-bottom
        reading order, ending with (text, romanization) as the LAST
        entry — i.e. already shaped exactly as _composition_rows(cells)
        expects, so a caller can do
            _composition_rows(syllable.components)
        with no reshaping. For a syllable with no final consonant this is
        [(cho, cho_roman), (jung, jung_roman), (text, romanization)] — 3
        entries, same shape as the title screen's ㅎ+ㅏ+ㄴ=한 row family
        naturally becomes with jong=''.
    is_bare_vowel: True when this syllable is a vowel written with the
        silent ㅇ placeholder because it has no real initial consonant
        (아, 어, 오, ...) — i.e. has_real_consonant() would be False.
        Lets a caller decide, e.g., whether to show the "vowels can't
        stand alone" framing for this particular block.
    """
    text: str
    romanization: str
    cho: str
    jung: str
    jong: str
    components: list = field(default_factory=list)
    is_bare_vowel: bool = False


# Every question mode's PROMPT direction, for next_question()'s directional
# mode-selection bias (see _hangul_first_weight and the bucket-weighted pick
# in next_question). Romanization-first: the prompt shows/names a sound and
# asks for Hangul — spell, match_sound, build_syllable, missing_vowel all
# work this way (missing_vowel's hint even re-states the romanization). This
# is real scaffolding for a total beginner, but left at a flat uniform mix
# forever it lets a learner pattern-match sound-strings to Hangul shapes
# without ever needing to actually READ the Hangul first — the "romanization
# as crutch" gap flagged in external review. Hangul-first: the prompt shows
# Hangul and asks for the sound/spelling — read_aloud is the direct case;
# batchim_challenge counts too, since it shows a real composed Hangul stem
# (cho+jung already visible) and asks the learner to complete the SPELLING,
# with its distractor logic specifically designed to defeat sound-only
# guessing (see _batchim_question's same_sound_in_choices comment) — closer
# in character to reading/writing than to romanization-driven recall.
# read_word is the whole-word case of read_aloud — the prompt shows a
# Hangul word and asks for its romanization — so it belongs in the same
# bucket. (It also has to be classified SOMEWHERE: next_question only
# draws from the two direction buckets whenever both are non-empty, so a
# mode in neither is effectively never selected when both spell and
# read_aloud are due.)
# confusion_drill and word_contrast are deliberately left out of both
# buckets: their prompt shape varies by entry/pair rather than having one
# fixed direction, so they stay outside this weighting rather than being
# force-fit into either bucket.
ROMANIZATION_FIRST_MODES = frozenset({"spell", "match_sound", "build_syllable", "missing_vowel", "decompose_syllable"})
HANGUL_FIRST_MODES = frozenset({"read_aloud", "read_word", "batchim_challenge"})


@dataclass
class LearnerItem:
    """Everything the app knows about the learner's relationship to one
    thing — a jamo, a syllable, a word. This is the richer replacement
    for the plain int(0-5) that used to live directly in
    progress['mastered_letters']; that flat score is now just a derived
    property (`confidence`) computed from correct/wrong, so every
    existing call site that reads a 0-5 number (get_mastered_syllables,
    the various >=3 checks) keeps working unchanged.

    Wired into answer() (via _record_learner_item) for correct/wrong/
    confusions/seen tracking, and into all six per-mode question
    generators (via _select_from_pool) for due-based item selection
    within a mode. NOT yet wired into next_question()'s MODE selection
    (chosen_mode = mode or random.choice(available_modes) is still
    uniform random — which mode gets picked doesn't consult .due at
    all, only which item within an already-chosen mode does).
    """
    key: str
    correct: int = 0
    wrong: int = 0
    last_seen: float = 0.0
    # Set only by migration from the old flat mastered_letters score.
    # Was originally a hard override (confidence returned this exact
    # value until cleared entirely on the first new answer) — that
    # caused two problems, both found via testing rather than assumed:
    # (1) clearing it outright on one new CORRECT answer collapsed old
    # scores 3/4/5 all onto the same lower value (the "migration
    # cliff"); (2) a naive fix (seeding correct=score**2 to survive
    # that cliff) solved (1) but made a migrated "mastered" item nearly
    # immovable by a WRONG answer, since 25 accumulated correct answers
    # swamp one new miss.
    #
    # Now it's a FLOOR, not an override: confidence is
    # max(computed_from_correct/wrong, migrated_confidence -
    # wrong_since_migration), so a fresh correct answer can only ever
    # raise it (never triggers a cliff), and each new wrong answer
    # erodes the floor by one point instead of being absorbed by a
    # huge seeded correct count. Once the floor decays to 0 or the
    # real correct/wrong evidence naturally exceeds it, this stops
    # doing anything and can be left as-is (no forced cleanup needed —
    # see the confidence property).
    _migrated_confidence: Optional[int] = None
    _wrong_since_migration: int = 0
    # {other_key: count} — how often this item gets confused with each
    # other item. Lives on the item itself now, instead of a separate
    # flat progress['confusion_counts'] dict keyed by "A↔B" strings.
    confusions: dict = field(default_factory=dict)
    # Per-question-mode tallies, e.g. {"spell": 4, "read_aloud": 2,
    # "confusion_drill": 1} — one entry per QuizQuestion.mode value this
    # item has actually been quizzed under, so different question types
    # stay distinguishable instead of collapsing into one number
    # (review §17's recognize/produce/construct idea, using this app's
    # real mode names rather than that abstraction).
    seen: dict = field(default_factory=dict)
    # Exponential moving average of response time in milliseconds —
    # captures HOW FAST the learner answers, not just whether they got
    # it right. A 1-second correct answer (fluent recognition) and a
    # 20-second correct answer (effortful sounding-out) are meaningfully
    # different learning states, and this field lets the app distinguish
    # them eventually. Update formula: first data point seeds the value
    # directly (no averaging against zero); subsequent points blend 80%
    # old / 20% new, so recent performance weighs more but outliers
    # don't whiplash the number. Known limitation: the timer starts when
    # the question is DISPLAYED and stops when answer() is called, so a
    # /hint request during a question inflates that answer's measured
    # time — this is accepted for now (simple, not hint-aware); a more
    # precise version that separates hint-tainted answers was considered
    # and explicitly deferred.
    avg_response_ms: float = 0.0

    # How many answers (at perfect accuracy) it takes to reach full
    # confidence — the pacing knob for the formula below. Chosen
    # deliberately (not derived): roughly matches "a solid, repeated
    # streak" rather than either a single lucky guess or an unrealistic
    # 25-answer grind. See the confidence property for the formula
    # this feeds and why the earlier sqrt-based version was replaced.
    CONFIDENCE_RAMP = 8

    @property
    def confidence(self) -> int:
        """0-5, same scale and meaning as the old mastered_letters int,
        so min_confidence=N checks elsewhere in this file don't need to
        change.

        round(5 * ratio * min(1, total/CONFIDENCE_RAMP)): ratio is
        accuracy (correct/total), and the min(1, total/RAMP) term ramps
        linearly from 0 up to full weight over the first RAMP answers,
        then plateaus — so a single lucky guess (1/1) still reads low
        (confidence 1, not 5), but a sustained streak reaches full
        confidence over roughly RAMP answers, not RAMP**2 like the
        earlier sqrt-based version.

        That earlier version was replaced after testing showed it
        didn't do what its own docstring claimed: round(ratio *
        total**0.5) needed 25 correct answers at perfect accuracy to
        reach confidence 5, not "a strong track record (8/10)" as
        documented — 8/10 actually produced confidence 3 under that
        formula, verified directly. This version's ramp is a
        deliberate pacing choice (how many answers "mastered" should
        take), decided explicitly rather than left as an accidental
        side effect of the dampening curve's shape.

        Migrated items carry a _migrated_confidence FLOOR (see the
        field's docstring for why it's a floor and not an override —
        a hard override or a squared-seed both had real problems,
        found via direct testing, not either one working around the
        other). The floor erodes by one per wrong answer since
        migration and never blocks a correct answer from raising
        confidence past it.
        """
        total = self.correct + self.wrong
        if total == 0:
            computed = 0
        else:
            ratio = self.correct / total
            weight = min(1, total / self.CONFIDENCE_RAMP)
            computed = max(0, min(5, round(5 * ratio * weight)))

        if self._migrated_confidence is None:
            return computed
        floor = max(0, self._migrated_confidence - self._wrong_since_migration)
        return max(computed, floor)

    @property
    def due(self) -> bool:
        """Simple spaced-repetition-lite (review §16): the more
        confident we are, the longer we wait before asking again."""
        if self.last_seen == 0:
            return True
        gap_seconds = (30, 60, 180, 600, 1800, 3600)[self.confidence]
        return (time.time() - self.last_seen) >= gap_seconds

    def to_dict(self) -> dict:
        """Dataclasses don't serialize to JSON on their own — this is
        what actually gets written into progress['learner_items']."""
        return {
            "correct": self.correct,
            "wrong": self.wrong,
            "last_seen": self.last_seen,
            "confusions": dict(self.confusions),
            "seen": dict(self.seen),
            "_migrated_confidence": self._migrated_confidence,
            "_wrong_since_migration": self._wrong_since_migration,
            "avg_response_ms": self.avg_response_ms,
        }

    @classmethod
    def from_dict(cls, key: str, data: dict) -> "LearnerItem":
        return cls(
            key=key,
            correct=data.get("correct", 0),
            wrong=data.get("wrong", 0),
            last_seen=data.get("last_seen", 0.0),
            confusions=dict(data.get("confusions", {})),
            seen=dict(data.get("seen", {})),
            _migrated_confidence=data.get("_migrated_confidence"),
            _wrong_since_migration=data.get("_wrong_since_migration", 0),
            avg_response_ms=data.get("avg_response_ms", 0.0),
        )

# ── Confusion-pair validity ───────────────────────────────────────────────

_JAMO_CHARS = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"

# Bare vowel jamo can never stand alone in written Korean — they always
# take the silent ㅇ placeholder (ㅏ -> 아). A bare jamo and its placeholder-
# composed form are the SAME vowel, not two different letters, so anywhere
# an answer is graded or a confusion pair is tracked, both forms need to
# normalize to one before comparison. Single source of truth for that set,
# used by HangulQuiz._compose_bare_vowel.
_VOWEL_JAMO = "ㅏㅓㅗㅜㅡㅣㅑㅕㅛㅠㅐㅔㅒㅖㅘㅙㅚㅝㅞㅟㅢ"

# Compound vowels occupy a single jungseong slot but are built from two
# component jamo. This map is the verified source for component-level
# descriptions (e.g. ㅘ = ㅗ + ㅏ), so dataset pairs never hand-derive the
# split. TRAPS: ㅙ → ㅗ + ㅐ (NOT ㅗ + ㅣ, which is ㅚ), and ㅘ → ㅗ + ㅏ
# (NOT ㅜ + ㅓ, which is ㅝ). Used by the B3 production dataset generator.
COMPOUND_COMPONENTS = {
    "ㅐ": ("ㅏ", "ㅣ"),
    "ㅒ": ("ㅑ", "ㅣ"),
    "ㅔ": ("ㅓ", "ㅣ"),
    "ㅖ": ("ㅕ", "ㅣ"),
    "ㅘ": ("ㅗ", "ㅏ"),
    "ㅙ": ("ㅗ", "ㅐ"),
    "ㅚ": ("ㅗ", "ㅣ"),
    "ㅝ": ("ㅜ", "ㅓ"),
    "ㅞ": ("ㅜ", "ㅔ"),
    "ㅟ": ("ㅜ", "ㅣ"),
    "ㅢ": ("ㅡ", "ㅣ"),
}


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


def _initial_roman(jamo: str) -> str:
    """Romanization of a jamo in INITIAL position. ㅇ is SILENT here (the
    placeholder, contributes no sound), and ㄹ is 'r' — the 'r/l' in
    ROMANIZATION is a display convention for the bare letter, not a real
    initial-consonant spelling (concatenating it produced the 'r/la'
    garbage)."""
    if jamo == "ㅇ":
        return ""
    if jamo == "ㄹ":
        return "r"
    return ROMANIZATION.get(jamo, "?")


# ── Engine ─────────────────────────────────────────────────────────────────

class HangulQuiz:
    def __init__(self):
        self.curriculum = self._load_curriculum()
        self.word_contrasts = self._load_word_contrasts()
        self.progress = self._load_progress()
        # Exclusion sets for nonword_decode mode — built once at startup
        self.known_lexical_items = self._load_known_lexical_items()
        self.corpus_seen_bigrams = self._load_corpus_seen_bigrams()
        self.current_lesson = None
        self.session_streak = 0
        self.session_correct = 0
        self.session_total = 0

    # ── Data loading ───────────────────────────────────────────────────

    def _load_curriculum(self) -> dict:
        with open(CURRICULUM_PATH, encoding='utf-8') as f:
            return json.load(f)

    def _load_word_contrasts(self) -> list:
        """Stage 3 seed content (lexical minimal pairs like 개/게, 손/선) —
        see word_contrasts.json. Optional: unlike curriculum.json, this
        file's absence should never break the app, since it's new content
        layered on top of the existing lesson structure, not a dependency
        of it. Missing/malformed file -> empty list -> word_contrast mode
        simply never gets selected (see next_question's available_modes),
        same degrade-gracefully spirit as this file's other data loads."""
        try:
            with open(WORD_CONTRASTS_PATH, encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _load_known_lexical_items(self) -> set:
        """Build KNOWN_LEXICAL_ITEMS exclusion set for nonword_decode mode.
        Combines:
        - Every "korean" field value from reading_practice.jsonl (JSON Lines)
        - Every "ko" field value from konglish_vocab.json (all categories)
        Returns empty set on any file error (defensive loading)."""
        items = set()
        # Load reading_practice.jsonl
        try:
            with open(READING_PRACTICE_PATH, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if "korean" in entry:
                            items.add(entry["korean"])
                    except json.JSONDecodeError:
                        continue
        except (FileNotFoundError, OSError):
            pass
        # Load konglish_vocab.json
        try:
            with open(KONGLISH_VOCAB_PATH, encoding='utf-8') as f:
                data = json.load(f)
                # Structure: {"categories": {category_name: [{"ko": ..., "en": ...}, ...]}}
                if "categories" in data and isinstance(data["categories"], dict):
                    for category_entries in data["categories"].values():
                        if isinstance(category_entries, list):
                            for entry in category_entries:
                                if isinstance(entry, dict) and "ko" in entry:
                                    items.add(entry["ko"])
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass
        return items

    def _load_corpus_seen_bigrams(self) -> set:
        """Build CORPUS_SEEN_BIGRAMS exclusion set for nonword_decode mode.
        Extracts all 2-syllable substrings from Hangul runs in Tatoeba corpus.
        Returns empty set on any file error (defensive loading)."""
        import re
        bigrams = set()
        hangul_run_re = re.compile(r'[\uac00-\ud7a3]+')
        try:
            with open(TATOEBA_KOR_PATH, encoding='utf-8') as f:
                for line in f:
                    # TSV format: id\tlang\tsentence (no header)
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        sentence = parts[2]
                        # Extract all maximal Hangul runs
                        for match in hangul_run_re.finditer(sentence):
                            run = match.group()
                            # Extract all 2-character sliding windows
                            for i in range(len(run) - 1):
                                bigrams.add(run[i:i+2])
        except (FileNotFoundError, OSError):
            pass
        return bigrams

    def _load_progress(self) -> dict:
        if PROGRESS_PATH.exists():
            with open(PROGRESS_PATH, encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {
                "current_lesson": 1,
                "completed_lessons": [],
                "mastered_letters": {},
                "confusion_counts": {},
                "total_questions_answered": 0,
                "total_correct": 0,
                "streak_best": 0,
                "last_session": None
            }
        data.setdefault("learner_items", {})
        self._migrate_old_progress(data)
        return data

    def _migrate_old_progress(self, data: dict) -> None:
        """Backfill learner_items from the old flat mastered_letters
        ints, so nobody's existing user_progress.json is wiped or
        orphaned when this field is introduced. A key already present
        in learner_items (already migrated, or created fresh under the
        new system) is left untouched — this only fills gaps.

        The old int had no win/loss breakdown, just a single 0-5 score.
        _migrated_confidence carries it forward as a FLOOR (see that
        field's docstring on LearnerItem for the two approaches tried
        and rejected before this one — a hard override caused a
        collapse-to-2 cliff on the first new correct answer; seeding
        correct=score**2 fixed that but made the item nearly immovable
        by a wrong answer, since 25 accumulated corrects swamp one
        miss). Because confidence now reads _migrated_confidence as a
        floor rather than baking it into correct/wrong, correct/wrong
        can go back to seeding at 0 — the floor alone carries the old
        score forward, and ordinary new answers (right OR wrong) behave
        exactly like any other item's from the start, with the floor
        simply guaranteeing confidence never reads BELOW the old score
        until enough wrong answers erode it one point at a time.
        """
        old = data.get("mastered_letters", {})
        items = data["learner_items"]
        for key, score in old.items():
            if key in items:
                continue
            score = max(0, min(5, int(score)))
            items[key] = LearnerItem(
                key=key, correct=0, wrong=0,
                _migrated_confidence=score,
            ).to_dict()

    def save_progress(self):
        self.progress["last_session"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.progress["total_questions_answered"] = self.session_total + self.progress.get("total_questions_answered", 0)
        self.progress["total_correct"] = self.session_correct + self.progress.get("total_correct", 0)
        if self.session_streak > self.progress.get("streak_best", 0):
            self.progress["streak_best"] = self.session_streak
        PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PROGRESS_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.progress, f, indent=2, ensure_ascii=False)

    # ── Learner item access (not yet wired into answer()/next_question) ─
    #
    # These two methods are the only way anything should read or write
    # progress['learner_items'] — callers get/modify a LearnerItem
    # object, never touch the raw dict directly. That keeps the JSON
    # shape as an implementation detail instead of something scattered
    # across the file (which is exactly the kind of duplication that
    # bit mastered_letters/confusion_counts before).

    def _get_item(self, key: str) -> LearnerItem:
        """Fetch the LearnerItem for `key`, creating a fresh (all-zero)
        one if it doesn't exist yet. Never returns None — callers can
        always read .confidence, .due, etc. safely."""
        raw = self.progress["learner_items"].get(key)
        if raw is None:
            return LearnerItem(key=key)
        return LearnerItem.from_dict(key, raw)

    def _save_item(self, item: LearnerItem) -> None:
        """Write a LearnerItem back into progress['learner_items'].
        Caller is responsible for calling save_progress() afterward
        (same pattern as every other progress mutation in this file —
        this only updates the in-memory dict, it doesn't hit disk)."""
        self.progress["learner_items"][item.key] = item.to_dict()

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

    def _select_from_pool(self, pool: list[str]) -> str:
        """Pick the next item to quiz from a syllable/letter pool, using
        LearnerItem.due (review §16: "a good tutor should behave like
        'you got this right three times, let's leave it alone for a
        while' rather than a random question generator").

        Behavior:
          - If one or more pool items are due (never seen, or their
            spaced-repetition gap has elapsed), pick uniformly among
            just those. This is the only behavior change from the old
            `random.choice(pool)` — confident items get skipped in
            favor of ones that actually need practice.
          - If NOTHING in the pool is due (everything was just quizzed
            and confidently answered a moment ago), fall back to
            uniform random over the whole pool, exactly like before.
            This also covers a pool of brand-new items with no
            learner_items history yet, where every fresh LearnerItem's
            .due defaults to True anyway (see LearnerItem.due) — so a
            new learner sees no behavior change at all.

        This is deliberately a thin selection layer on top of the
        existing pool, not a replacement for it — lesson content and
        pool composition (_get_lesson_syllable_pool) are untouched.
        """
        if not pool:
            return pool  # let the caller's existing empty-pool handling fire, unchanged
        due_items = [s for s in pool if self._get_item(s).due]
        return random.choice(due_items) if due_items else random.choice(pool)

    def _mode_target_pool(self, mode: str, lesson: dict) -> list[str]:
        """The syllable pool `mode` draws its quiz target from — used by
        next_question() to bias MODE selection toward modes that have a
        due item, one level up from _select_from_pool (which only biases
        WHICH item within an already-chosen mode). Mirrors each per-mode
        generator's actual pool, so due-ness is computed against the same
        items the chosen mode would actually quiz:
          - spell / read_aloud / match_sound -> _get_lesson_syllable_pool
          - read_word                       -> mastery_words
          - build_syllable / missing_vowel / decompose_syllable
                                            -> practice_syllables or example_syllables
          - batchim_challenge               -> example_syllables
          - confusion_drill (or anything else) -> no syllable pool, returns []
        """
        if mode in ("spell", "read_aloud", "match_sound"):
            return self._get_lesson_syllable_pool(lesson)
        if mode == "read_word":
            return lesson.get("mastery_words", [])
        if mode in ("build_syllable", "missing_vowel", "decompose_syllable"):
            return lesson.get("practice_syllables") or lesson.get("example_syllables") or []
        if mode == "batchim_challenge":
            return lesson.get("example_syllables", [])
        return []

    def _lesson_avg_confidence(self, lesson: dict) -> float:
        """Mean .confidence (0-5) across this lesson's own syllable pool —
        the mastery signal next_question()'s directional bias reads. Reuses
        _get_lesson_syllable_pool (the same pool spell/read_aloud/match_sound
        already draw from) rather than introducing a new notion of "this
        lesson's items". Empty pool -> 0.0 (a lesson with nothing tracked
        yet is treated as needing full scaffolding, same as a fresh item
        with 0 correct/0 wrong already reads as confidence 0)."""
        pool = self._get_lesson_syllable_pool(lesson)
        if not pool:
            return 0.0
        return sum(self._get_item(s).confidence for s in pool) / len(pool)

    def _hangul_first_weight(self, lesson: dict) -> float:
        """Probability of preferring the Hangul-first bucket (read_aloud /
        batchim_challenge) over the romanization-first bucket, given this
        lesson's average confidence. Linear from 0.25 at confidence 0 (~75%
        romanization-first — close to the old uniform-random mix, so early
        lessons barely feel different) to 0.80 at confidence 5 (~20%
        romanization-first — occasional, deliberately not eliminated; see
        ROMANIZATION_FIRST_MODES' docstring for why romanization stays as
        permanent light scaffolding rather than a beginner-only mode).
        Chosen as Option B in the crutch-tapering design discussion: mirrors
        confusion_drill's existing 0.15/0.30 "occasional, not dominant"
        rates rather than inventing an unrelated number, and degrades
        gracefully — even a bug in confidence computation can't push this
        past its 0.25-0.80 range into something absurd like 95%/5%."""
        avg_confidence = self._lesson_avg_confidence(lesson)
        return 0.25 + (0.80 - 0.25) * (avg_confidence / 5)

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
            # decompose_syllable rides along with build_syllable (its inverse)
            # rather than carrying its own independent rate gate — the two are
            # one construction/deconstruction pair and share a pool + a gating
            # condition. Whether they should ALSO share a rate is a curriculum
            # question, tracked as the known-issue comment in
            # _build_syllable_question.
            available_modes.append("decompose_syllable")

        # Whole-word reading (Lesson 12 and any other word-based lesson).
        # Deliberately NOT added to available_modes here: these modes get
        # drawn through the direction-bucket logic below, and a word-based
        # lesson's read_word is meant to be the PRIMARY exercise, not one
        # competitor among several. Adding it there diluted the observed
        # rate to ~20% even behind a 60% gate — the gate fired 60% of the
        # time, then the hangul-first bucket split between read_aloud and
        # read_word, then the due-preference filter could drop it again
        # (0.60 × 0.60 × 0.5 ≈ 0.20). It's selected directly up front in
        # the mode pick below instead. See READ_WORD_RATE.
        if "batchim_pronunciation_rules" in lesson or "batchim_pronunciation" in lesson:
            available_modes.append("batchim_challenge")

        # If the user has real tracked confusions, occasionally trigger a drill.
        # If not, but this lesson calls out known-tricky pairs (e.g. ㅓ vs ㅗ),
        # drill those proactively at a lower rate — no need to wait for mistakes.
        # Sourced from the same _pairs_from_learner_items() that
        # _confusion_drill_question itself now reads, so this gate and
        # the drill it's gating agree on what counts as "has confusions"
        # — previously this checked the old flat confusion_counts dict
        # while the drill (after this patch) reads learner_items, which
        # could disagree in edge cases (e.g. this said yes, the drill
        # found nothing usable, or vice versa).
        has_confusions = any(v >= 2 for v in self._pairs_from_learner_items().values())
        has_curriculum_pairs = bool(lesson.get("confusion_pairs"))
        if has_confusions and random.random() < 0.3:
            available_modes.append("confusion_drill")
        elif has_curriculum_pairs and random.random() < 0.15:
            available_modes.append("confusion_drill")

        # Stage 3: meaningful word contrasts (see word_contrasts.json).
        # Gated on _available_word_contrasts() actually returning
        # something decodable for THIS lesson — an empty/missing content
        # file or a lesson too early for any seeded pair both correctly
        # result in this mode never being offered, rather than being
        # offered and then silently degrading every time (see the
        # degrade-to-spell fallback in _generate_question, which exists
        # as a safety net, not as the expected path).
        if self._available_word_contrasts() and random.random() < 0.15:
            available_modes.append("word_contrast")

        # Nonword decode: tests phoneme-by-phoneme decoding, not lexical
        # recognition. Gated on pool having at least 2 distinct syllables
        # (needed to form a 2-syllable nonword). 15% rate matches
        # word_contrast's occasional-not-dominant pattern.
        if len(self._get_lesson_syllable_pool(lesson)) >= 2 and random.random() < 0.15:
            available_modes.append("nonword_decode")

        # sequence_decode: 3-syllable nonword. Needs pool >= 3 distinct
        # syllables. Same 15% occasional rate as nonword_decode.
        if len(self._get_lesson_syllable_pool(lesson)) >= 3 and random.random() < 0.15:
            available_modes.append("sequence_decode")

        if mode:
            chosen_mode = mode
        elif lesson.get("mastery_words") and random.random() < self.READ_WORD_RATE:
            # Word-based lesson: whole-word reading is the primary
            # exercise (see READ_WORD_RATE). Picked directly here rather
            # than through the bucket/available_modes logic below, so the
            # observed rate actually matches READ_WORD_RATE instead of
            # being diluted by the hangul-first split and due filter.
            # WHICH word is still due-based — _read_word_question routes
            # its mastery_words pool through _select_from_pool.
            chosen_mode = "read_word"
        else:
            # Prefer modes whose current-lesson pool has at least one due
            # item — mirroring _select_from_pool's due-preference one level
            # up (which MODE gets picked, not just which item within a mode).
            # Fall back to uniform random over every available mode when
            # nothing is due, exactly like _select_from_pool does. .due
            # stays the PRIMARY filter, unchanged from before this method
            # was extended — an item genuinely due for review should never
            # get skipped just because of the directional bias below.
            due_modes = [
                m for m in available_modes
                if any(self._get_item(s).due for s in self._mode_target_pool(m, lesson))
            ]
            candidates = due_modes if due_modes else available_modes

            # Directional bias (see ROMANIZATION_FIRST_MODES / HANGUL_FIRST_
            # MODES / _hangul_first_weight): applied WITHIN whatever .due
            # already narrowed candidates to, not instead of it. Split
            # candidates into the two direction buckets; confusion_drill/
            # word_contrast/anything else fall into neither and are pooled
            # separately as "unbiased" so they're never favored OR
            # penalized by this weighting.
            roman_bucket = [m for m in candidates if m in ROMANIZATION_FIRST_MODES]
            hangul_bucket = [m for m in candidates if m in HANGUL_FIRST_MODES]
            other_bucket = [m for m in candidates if m not in ROMANIZATION_FIRST_MODES
                             and m not in HANGUL_FIRST_MODES]

            if roman_bucket and hangul_bucket:
                # Both directions available — weighted pick between them,
                # then uniform within whichever bucket wins. other_bucket
                # entries (confusion_drill, word_contrast) get folded in at
                # their own natural frequency by being eligible from either
                # draw's uniform-within-candidates fallback below instead —
                # see the else branch.
                hangul_first_weight = self._hangul_first_weight(lesson)
                if random.random() < hangul_first_weight:
                    chosen_mode = random.choice(hangul_bucket)
                else:
                    chosen_mode = random.choice(roman_bucket)
            else:
                # Only one direction present (or neither — e.g. a
                # confusion_drill/word_contrast-only candidate set) — the
                # bias has nothing to weigh between, so fall back to the
                # original uniform pick over ALL candidates, direction
                # buckets and other_bucket alike. This is exactly the old
                # behavior for lessons/situations where the split doesn't
                # apply, not a new code path.
                chosen_mode = random.choice(candidates)
        return self._generate_question(chosen_mode)

    def _generate_question(self, mode: str) -> QuizQuestion:
        lesson = self.current_lesson

        if mode == "spell":
            return self._spell_question(lesson)
        elif mode == "read_aloud":
            return self._read_aloud_question(lesson)
        elif mode == "read_word":
            if lesson.get("mastery_words"):
                return self._read_word_question(lesson)
            return self._read_aloud_question(lesson)  # degrade-gracefully, same as confusion_drill/word_contrast
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
        elif mode == "word_contrast":
            available = self._available_word_contrasts()
            if available:
                return self._word_contrast_question(random.choice(available))
            return self._spell_question(lesson)  # same degrade-gracefully pattern as confusion_drill
        elif mode == "nonword_decode":
            return self._nonword_decode_question(lesson)
        elif mode == "sequence_decode":
            return self._sequence_decode_question(lesson)
        elif mode == "decompose_syllable":
            return self._decompose_syllable_question(lesson)
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
        target = self._select_from_pool(pool)

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
        elif cho == 'ㅇ' and jong:
            # Silent placeholder + batchim (음, 안, 앙...). The ㅇ still
            # contributes no initial sound, so the syllable starts with the
            # vowel, not with "ng" — 'ngeu-m' would be wrong.
            jung_roman = ROMANIZATION.get(jung, '?')
            jong_roman = self._batchim_sound(jong)
            hint = f"The ㅇ is silent, so it starts with the vowel '{jung_roman}' and ends with a '{jong_roman}' batchim sound."
        elif cho and jung:
            # Fixed a real bug here too: this used to slice the
            # romanization STRING assuming the consonant is always exactly
            # one character (roman[0]) — which silently breaks for ㄹ
            # ('r/l') and every tense consonant ('kk','tt','pp','ss','jj').
            # E.g. for 까 it would've said "starts with 'k', vowel 'ka'"
            # instead of "starts with 'kk', vowel 'a'". Looking up each
            # jamo's own romanization directly avoids that.
            cho_roman = _initial_roman(cho)
            jung_roman = ROMANIZATION.get(jung, '?')
            if jong:
                jong_roman = self._batchim_sound(jong)
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
            # Also accept the romanization the prompt already showed — a
            # learner who types 'i' when asked for 이 clearly knows the
            # answer; penalising them for using the form the question
            # itself displayed is misleading feedback.
            accepted=[roman],
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
        target = self._select_from_pool(self._get_lesson_syllable_pool(lesson))

        return QuizQuestion(
            mode="read_aloud",
            prompt=f"How would you romanize **{target}**? (Type it — e.g. 'a', 'eo', 'u')",
            correct_answer=self._hangul_to_roman_hint(target),
            hint="Not sure of the spelling system? Type /roman to see the full romanization key.",
            lesson_id=lesson["id"],
            letter=target
        )

    def _read_word_question(self, lesson: dict) -> QuizQuestion:
        """Show a whole word from lesson['mastery_words'], ask the user to
        type its romanization. Same shape as _read_aloud_question, but the
        target is a full word rather than a single syllable, and grading is
        against that word's accepted_romanizations list (a word can have
        more than one accepted spelling, e.g. 'hangul'/'hangeul') instead
        of the app's single-syllable ROMANIZATION string. Word selection
        still goes through _select_from_pool, keyed on the word string, so
        it gets the same spaced-repetition due preference as every other
        mode."""
        target = self._select_from_pool(lesson["mastery_words"])

        # Look up this word's vocabulary entry for its meaning, breakdown,
        # and accepted romanizations. A word with no matching entry (data
        # drift) still produces a usable question: fall back to the
        # syllabus-derived romanization as the single accepted answer and
        # leave the breakdown hint empty rather than crashing.
        vocab = next((v for v in lesson.get("vocabulary", [])
                      if v.get("word") == target), None)
        accepted = list(vocab.get("accepted_romanizations", [])) if vocab else []
        if not accepted:
            accepted = [self._word_romanization(target)]
        breakdown = vocab.get("breakdown", "") if vocab else ""

        return QuizQuestion(
            mode="read_word",
            prompt=f"Read this word aloud, then type its romanization:\n\n   **{target}**",
            correct_answer=accepted[0],
            accepted=accepted,
            hint=breakdown,
            lesson_id=lesson["id"],
            letter=target
        )

    def _word_romanization(self, word: str) -> str:
        """Concatenated per-syllable romanization for a whole word — the
        fallback answer for a mastery word whose vocabulary entry is
        missing or carries no accepted_romanizations. Reuses
        _hangul_to_roman_hint (the same source read_aloud grades against)
        so a multi-syllable word stays consistent with single-syllable
        spelling. No separator, matching how '한글' composes to 'hangeul'
        rather than 'han-geul'."""
        return "".join(self._hangul_to_roman_hint(ch) for ch in word)

    def _match_sound_question(self, lesson: dict) -> QuizQuestion:
        """Multiple choice: pick the right Hangul given romanization."""
        items = self._get_lesson_syllable_pool(lesson)
        if len(items) < 4:
            # Supplement from previous lessons
            pool = self._get_known_syllables()
            items = (list(set(items + random.sample(pool, min(4 - len(items), len(pool))))))
        target = self._select_from_pool(items)
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
            target = self._select_from_pool(pool)
        else:
            return self._spell_question(lesson)  # fallback

        # Decompose syllable into consonant + vowel
        #
        # ⚠️ KNOWN ISSUE (flagged 2026-09, not yet fixed — needs a curriculum
        # pass): this mode PRINTS the decomposition it just computed
        # ("Consonant: {cho} | Vowel: {jung}") as part of its prompt. That is
        # the exact answer decompose_syllable mode asks for, so the two modes
        # overlap: build_syllable gives the jamo away and only tests block
        # assembly, while decompose_syllable hides the block and tests the
        # jamo. Running both in the same lesson (which they do — see
        # next_question) means a learner can be told "ㄷ + ㅗ" by one question
        # and then asked to produce "ㄷ + ㅗ" by the next. The intended fix is
        # a curriculum/sequencing decision (gate build_syllable to the lessons
        # where block assembly is still the new skill, and let
        # decompose_syllable take over once assembly is established), which is
        # why this is a comment and not a code change here.
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
            target = self._select_from_pool(pool)
        else:
            return self._spell_question(lesson)

        cho, jung, jong = self._decompose_syllable(target)

        # Batchim guard — without this, a batchim target is served as
        # "ㄷ + ? = dot" and graded on the vowel ALONE, silently accepting
        # an answer that ignores the final consonant entirely. Measured
        # impact before this guard: lessons 10 and 11 are 100% batchim
        # (22 pool syllables, 0 bare CV), so every missing_vowel question
        # in those two lessons mis-graded. Mirrors the same guard in
        # _batchim_question (~line 1108), which rejects the INVERSE case
        # (no batchim) for the same class of reason: the mode's single
        # graded component can't represent the target, so degrade to
        # spell rather than grade a partial answer as correct.
        if jong:
            return self._spell_question(lesson)

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

    def _decompose_syllable_question(self, lesson: dict) -> QuizQuestion:
        """Show a composed block, user names its consonant + vowel.

        The INVERSE of build_syllable: there the jamo pair is given and the
        block is the answer; here the block is given and the jamo pair is
        the answer. Because of that inversion, the prompt and the choices
        must never render the block's component letters — the block is safe
        to show (it is the question), the jamo are not (they are the answer).

        Bare CV only. Batchim targets and bare-jamo pool entries both degrade
        to _spell_question rather than being served with an unanswerable or
        ambiguous prompt (see the guards below).

        correct_answer is a formatted string "ㄷ + ㅗ" — order-significant,
        both components required. Graded via _normalize_jamo_pair so that
        input spacing/punctuation ('ㄷ+ㅗ', 'ㄷ ㅗ') is not what is being
        tested, while component ORDER still is ('ㅗㄷ' fails)."""
        pool = lesson.get("practice_syllables") or lesson.get("example_syllables")
        if not pool:
            return self._spell_question(lesson)  # same fallback as siblings

        target = self._select_from_pool(pool)
        cho, jung, jong = self._decompose_syllable(target)

        # Bare jamo (not a composed block) — nothing to decompose.
        if not cho and not jung:
            return self._spell_question(lesson)
        # Batchim — out of scope for this mode for now. Measured pool
        # composition (scripts/_probe_pool_cv_vs_batchim.py): 102/136 are
        # bare CV, and lessons 2-9 are 100% bare CV, so this guard leaves
        # the mode fully usable where it matters rather than degrading it.
        if jong:
            return self._spell_question(lesson)

        answer = f"{cho} + {jung}"
        return QuizQuestion(
            mode="decompose_syllable",
            prompt=(f"Break **{target}** into its parts.\n"
                    f"Which consonant + vowel make this block?"),
            correct_answer=answer,
            choices=self._decomposition_choices(cho, jung, pool),
            hint=(f"Say it: '{self._hangul_to_roman_hint(target)}' — "
                  f"which two letters combine into that sound?"),
            lesson_id=lesson["id"],
            letter=target
        )

    def _decomposition_choices(self, cho: str, jung: str, pool: list[str]) -> list[str]:
        """Distractor jamo-pairs for decompose_syllable, drawn from the SAME
        lesson pool so the wrong answers are plausible (real syllables this
        learner has met) rather than random noise.

        _make_choices can't be reused here: it draws whole SYLLABLES from the
        pool, whereas this mode's options are 'consonant + vowel' PAIRS.
        Each distractor is another bare-CV pool item decomposed the same way,
        deduped against the correct answer, then shuffled in."""
        correct = f"{cho} + {jung}"
        candidates = []
        for syllable in pool:
            if syllable == f"{cho}{jung}":
                continue
            d_cho, d_jung, d_jong = self._decompose_syllable(syllable)
            if not d_cho and not d_jung:
                continue          # bare jamo — not a composed block
            if d_jong:
                continue          # batchim — not a valid option shape
            pair = f"{d_cho} + {d_jung}"
            if pair != correct and pair not in candidates:
                candidates.append(pair)

        wrong = random.sample(candidates, min(3, len(candidates)))

        # Small lessons may not yield 3 distinct wrong pairs — pad from the
        # broader known set so the question always has a usable option count.
        if len(wrong) < 3:
            pool_for_pad = self._get_known_syllables()
            for syllable in random.sample(pool_for_pad, min(len(pool_for_pad), 40)):
                if len(wrong) >= 3:
                    break
                d_cho, d_jung, d_jong = self._decompose_syllable(syllable)
                if not d_cho or not d_jung or d_jong:
                    continue
                pair = f"{d_cho} + {d_jung}"
                if pair != correct and pair not in candidates and pair not in wrong:
                    wrong.append(pair)

        choices = [correct] + wrong
        random.shuffle(choices)
        return choices

    def _normalize_jamo_pair(self, s: str) -> str:
        """Strip everything but the jamo from a decompose_syllable answer so
        that typing 'ㄷ+ㅗ', 'ㄷ,ㅗ' or 'ㄷ ㅗ' all compare equal.

        Preserves ORDER — 'ㅗㄷ' normalizes to 'ㅗㄷ' and does NOT match
        'ㄷㅗ'. That is deliberate: this mode tests whether the learner knows
        which letter is the consonant and which is the vowel, so accepting a
        reversed pair would grade away the exact thing being taught."""
        if not s:
            return ""
        return "".join(ch for ch in s if ch in _JAMO_CHARS)

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

        target = self._select_from_pool(examples)
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

    def _pairs_from_learner_items(self) -> dict:
        """Reconstruct the same {'A↔B': count} shape _confusion_drill_
        question already expects (and the rest of that function's logic
        — lesson-relevance scoping, degenerate-pair filtering, the
        three-tier fallback — is untouched), but sourced from the
        richer per-item learner_items[*].confusions instead of the old
        flat progress['confusion_counts'].

        This is the intended payoff of storing confusions on the item
        itself (see LearnerItem docstring and _record_learner_item):
        the same data _confusion_drill_question always wanted, just
        collected from where it now actually lives. The old
        confusion_counts dict is still being written in parallel by
        answer() and still backs get_progress_summary/_top_confusions
        elsewhere — this method and its caller are the only place that
        switches over to the new source.

        A pair key's count is the SUM of both directions (item X
        confused-with Y, and item Y confused-with X), since which one
        got typed and which was expected can vary answer to answer —
        the drill cares that the pair gets mixed up, not which
        direction happened more.
        """
        pairs: dict = {}
        for key, raw in self.progress.get("learner_items", {}).items():
            item = LearnerItem.from_dict(key, raw)
            for other, count in item.confusions.items():
                if not count:
                    continue
                # Order-independent pair key so X↔Y and Y↔X merge into
                # one entry instead of appearing as two separate pairs.
                pair_key = "↔".join(sorted((key, other)))
                pairs[pair_key] = pairs.get(pair_key, 0) + count
        return pairs

    def _lesson_teaching_letter(self, letter: str) -> Optional[int]:
        """Which lesson id first introduces this jamo (via its 'letters'
        list), or None if no lesson teaches it. Used to gate word_contrast
        content on actual decodability — see _word_contrast_decodable."""
        for lesson in self.curriculum.get("lessons", []):
            if letter in lesson.get("letters", []):
                return lesson["id"]
        return None

    def _word_contrast_decodable(self, entry: dict) -> bool:
        """True only if EVERY jamo in EVERY item's form has been taught by
        (at or before) the current lesson — i.e. the learner could
        actually decode both words with what they've seen so far, not
        just the target vowel pair in isolation.

        This matters because gating on the vowel contrast's own lesson
        alone would be wrong here: 손/선 (ㅓ/ㅗ, taught in Lesson 1) also
        needs ㅅ, which isn't taught until Lesson 3 — so surfacing this
        pair from Lesson 1 onward would claim the learner can read a word
        containing an untaught consonant. This project has hit exactly
        that class of bug before (sentence-exposure claiming readability
        of untaught grammar) and it was treated as a priority fix, not a
        cosmetic one — so this check derives decodability from the
        curriculum's own 'letters' lists rather than hardcoding per-entry
        lesson numbers, which would silently go stale if curriculum.json
        is ever reordered or extended.

        No current_lesson set -> nothing is decodable yet (conservative
        default, matches the rest of this class's None-current_lesson
        handling elsewhere)."""
        if self.current_lesson is None:
            return False
        current_id = self.current_lesson["id"]
        for item in entry.get("items", []):
            form = item.get("form", "")
            for ch in form:
                cho, jung, jong = self._decompose_syllable(ch)
                for jamo in (cho, jung, jong):
                    if not jamo:
                        continue
                    taught_at = self._lesson_teaching_letter(jamo)
                    if taught_at is None or taught_at > current_id:
                        return False
        return True

    def _entry_renderable(self, entry: dict) -> bool:
        """Two separate questions, kept separate on purpose:

        contrast_type says HOW an eligible entry gets presented (bare
        composed block vs. example-sentence-with-highlight) — that's a
        renderer capability question, answered by print_question having
        a branch for this contrast_type at all.

        requires_host says WHETHER the entry actually carries the
        context data its own presentation needs to be shown safely. An
        item that requires a host MUST have real example_ko/example_en
        content to attach that host context to — otherwise there's
        nothing for the host-context renderer to highlight into, and
        the entry has no safe fallback (a bare block would misrepresent
        a particle like 도 as a standalone word, which is the exact
        mistake this flag exists to prevent).

        So: a requires_host item without example_ko/example_en is never
        renderable, full stop — not by this contrast_type, not by
        falling back to bare-block rendering either. A malformed future
        entry that claims lexical_vs_grammar_form but forgot to fill in
        its example sentences must fail closed here, not get selected
        and then fail (or worse, mis-render) downstream in the CLI."""
        for item in entry.get("items", []):
            if item.get("requires_host") and not (
                item.get("example_ko") and item.get("example_en")
            ):
                return False
        return True

    def _available_word_contrasts(self) -> list[dict]:
        """word_contrasts entries that are both decodable so far AND
        renderable — see _entry_renderable for what "renderable" means
        here. contrast_type is no longer used as an exclusion filter by
        itself: lexical_vs_grammar_form entries (e.g. 더/도) are now
        eligible once they carry real example sentences, via the
        host-context render path in print_question. requires_host
        entries lacking that context remain excluded, same as before —
        see _entry_renderable's docstring for why that has to fail
        closed rather than fall back to a bare-block rendering that
        would misrepresent a particle as a standalone word."""
        return [
            e for e in self.word_contrasts
            if self._entry_renderable(e) and self._word_contrast_decodable(e)
        ]

    def _word_contrast_question(self, entry: dict) -> QuizQuestion:
        """Stage 3: meaningful contrast, not just visual/sound (see the
        design discussion this content type came out of — Stage 1/2 are
        jamo and composed-block contrast, already covered by
        confusion_drill; Stage 3 attaches MEANING to the contrast, which
        is a different learning operation, not just another rendering
        mode). Alternates direction across calls — word-to-meaning and
        meaning-to-word — because always asking the same direction lets
        meaning become a crutch for decoding rather than an additional
        retrieval dimension in its own right. The content file itself
        stays direction-agnostic (one meaning_en per item, e.g. 'dog' for
        개); this method decides direction per call, not the data.

        direction and contrast_type are carried on the returned
        QuizQuestion (not baked only into a plain-text prompt) precisely
        so print_question can apply the right rendering POLICY, not just
        display whatever text happens to be here — a hosted form
        (contrast_type == 'lexical_vs_grammar_form') must never render as
        a bare composed block once that path exists, and that decision
        belongs to the renderer reading contrast_type, not to prompt
        string content the renderer can't safely parse back apart. prompt
        is still set to a reasonable plain-text fallback for any caller
        that isn't quiz-aware (e.g. print_question(q, quiz=None))."""
        items = entry["items"]
        target_idx = random.randrange(len(items))
        target = items[target_idx]
        other = items[1 - target_idx] if len(items) == 2 else random.choice(
            [i for i in items if i is not target]
        )

        word_to_meaning = random.random() < 0.5
        direction = "word_to_meaning" if word_to_meaning else "meaning_to_word"
        if word_to_meaning:
            prompt = f"**{target['form']}** means...?"
            correct_answer = target["meaning_en"]
            choices = [target["meaning_en"], other["meaning_en"]]
        else:
            prompt = f"Which word means \"{target['meaning_en']}\"?"
            correct_answer = target["form"]
            choices = [target["form"], other["form"]]
        random.shuffle(choices)

        return QuizQuestion(
            mode="word_contrast",
            prompt=prompt,
            correct_answer=correct_answer,
            choices=choices,
            hint=f"{target['form']} ({target['romanization']}) vs "
                 f"{other['form']} ({other['romanization']}) — "
                 f"the difference is {entry['confusion']['display_label']}.",
            lesson_id=self.current_lesson["id"] if self.current_lesson else 0,
            letter=target["form"],
            other=other["form"],
            direction=direction,
            contrast_type=entry.get("contrast_type", ""),
            example_ko=target.get("example_ko", ""),
            example_en=target.get("example_en", ""),
            other_example_ko=other.get("example_ko", ""),
            other_example_en=other.get("example_en", "")
        )

    def _generate_nonword_candidate(self, lesson: dict) -> Optional[str]:
        """Generate a 2-syllable nonword candidate for nonword_decode mode.
        Returns None if no valid candidate can be generated (pool too small
        or all attempts rejected)."""
        pool = self._get_lesson_syllable_pool(lesson)
        # Need at least 2 distinct syllables to form a 2-syllable nonword
        if len(pool) < 2:
            return None
        # Pick 2 distinct syllables
        try:
            s1, s2 = random.sample(pool, 2)
        except ValueError:
            # Pool has fewer than 2 distinct items
            return None
        # Guard against identical values (random.sample picks distinct positions,
        # but pool could have duplicate values)
        if s1 == s2:
            return None
        candidate = s1 + s2
        # Reject if in KNOWN_LEXICAL_ITEMS (hard exclusion)
        if candidate in self.known_lexical_items:
            return None
        # Reject if in CORPUS_SEEN_BIGRAMS (soft exclusion)
        if candidate in self.corpus_seen_bigrams:
            return None
        return candidate

    def _generate_sequence_candidate(self, lesson: dict) -> Optional[str]:
        """Generate a 3-syllable nonword candidate for sequence_decode mode.
        Returns None if no valid candidate can be generated."""
        pool = self._get_lesson_syllable_pool(lesson)
        if len(pool) < 3:
            return None
        try:
            s1, s2, s3 = random.sample(pool, 3)
        except ValueError:
            return None
        # Guard against any duplicate values (random.sample picks distinct
        # positions, but pool can contain duplicate values)
        if len({s1, s2, s3}) < 3:
            return None
        candidate = s1 + s2 + s3
        # Hard exclusion: reject if the full trigram is a known lexical item
        if candidate in self.known_lexical_items:
            return None
        # Soft exclusion: reject if ANY embedded bigram (s1+s2 or s2+s3)
        # appears in the corpus bigram set — a 3-syllable string won't appear
        # in CORPUS_SEEN_BIGRAMS directly (those are 2-char strings), but its
        # sub-pairs might, which would make it feel like a partial real word.
        if (s1 + s2) in self.corpus_seen_bigrams:
            return None
        if (s2 + s3) in self.corpus_seen_bigrams:
            return None
        return candidate

    def _nonword_decode_question(self, lesson: dict) -> QuizQuestion:
        """Generate a nonword_decode question: 2-syllable nonword that the
        learner must decode phoneme-by-phoneme. Falls back to _spell_question
        if no valid candidate can be generated after 20 retries."""
        candidate = None
        for _ in range(20):
            candidate = self._generate_nonword_candidate(lesson)
            if candidate is not None:
                break
        # Fallback: if all 20 retries failed, degrade to spell mode
        if candidate is None:
            return self._spell_question(lesson)
        # Build the question
        s1, s2 = candidate[0], candidate[1]
        syl1 = self.syllable_breakdown(s1)
        syl2 = self.syllable_breakdown(s2)
        roman1 = syl1.romanization
        roman2 = syl2.romanization
        correct_answer = roman1 + roman2
        prompt = f"**{candidate}** — this isn't a real Korean word. Just read it: type the pronunciation."
        hint = f"Sound out each block separately: {s1} = {roman1}, {s2} = {roman2}"
        return QuizQuestion(
            mode="nonword_decode",
            prompt=prompt,
            correct_answer=correct_answer,
            hint=hint,
            lesson_id=lesson["id"],
            letter=candidate,
        )

    def _sequence_decode_question(self, lesson: dict) -> QuizQuestion:
        """Generate a sequence_decode question: 3-syllable nonword the
        learner must decode as one continuous romanization string.
        Falls back to _spell_question if no valid candidate after 20 retries."""
        candidate = None
        for _ in range(20):
            candidate = self._generate_sequence_candidate(lesson)
            if candidate is not None:
                break
        if candidate is None:
            return self._spell_question(lesson)
        s1, s2, s3 = candidate[0], candidate[1], candidate[2]
        syl1 = self.syllable_breakdown(s1)
        syl2 = self.syllable_breakdown(s2)
        syl3 = self.syllable_breakdown(s3)
        roman1 = syl1.romanization
        roman2 = syl2.romanization
        roman3 = syl3.romanization
        correct_answer = roman1 + roman2 + roman3
        prompt = (
            f"**{candidate}** — not a real word. "
            f"Read the whole sequence: type the full pronunciation."
        )
        hint = (
            f"Sound out each block: "
            f"{s1} = {roman1}, {s2} = {roman2}, {s3} = {roman3}"
        )
        return QuizQuestion(
            mode="sequence_decode",
            prompt=prompt,
            correct_answer=correct_answer,
            hint=hint,
            lesson_id=lesson["id"],
            letter=candidate,
        )

    def _confusion_drill_question(self) -> QuizQuestion:
        """Target letters the user consistently confuses — scoped to the
        CURRENT lesson wherever possible. Confusion counts persist across
        every session forever with no decay, so without this scoping the
        biggest historical count (almost always early vowel mistakes from
        lesson 1, which had a huge head start accumulating) permanently
        drowns out anything from later lessons — you'd get drilled on
        아/어/이/우/으 in a batchim lesson ten sessions later. Preference
        order: (1) worst mistake relevant to this lesson, (2) curriculum-
        suggested pair for this lesson, (2b) curriculum-wide global
        confusion pair if the lesson has none of its own, (3) worst
        mistake overall as a last resort so the drill still has something
        to show."""
        confusion_counts = self._pairs_from_learner_items()
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

        # Preference 2b: lesson has no own confusion_pairs (or it was
        # empty) — try the curriculum-wide global list instead. Same
        # shape as a lesson's confusion_pairs, so the same selection
        # pattern applies.
        if a is None:
            groups = [g for g in self.curriculum.get("confusion_pairs_global", []) if len(g) >= 2]
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
            letter=target,
            other=other
        )

    # ── Answer checking ────────────────────────────────────────────────

    def answer(self, user_input: str, question: QuizQuestion = None, response_ms: Optional[float] = None) -> QuizResult:
        """Check the user's answer against the expected.

        response_ms: wall-clock milliseconds between the question
        being displayed and this call. Passed through to
        _record_learner_item to update the per-item EMA. None means
        "not measured" (e.g. programmatic callers that don't time,
        or external callers that don't pass it) — the timing update
        is skipped entirely, no crash, no made-up default."""
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
        # that was never actually one of the options on screen. ALSO
        # skipped for word_contrast: in its word-to-meaning direction,
        # correct_answer is an English gloss ('dog'), not Hangul at all —
        # same reasoning as read_aloud. In its meaning-to-word direction
        # the answer IS Hangul, but always an already-composed syllable
        # (손/선/개/게, never a bare jamo), so the normalization would be
        # a no-op there anyway; excluding the whole mode is simpler and
        # more honest than relying on that being a coincidence. ALSO
        # skipped for nonword_decode: correct_answer is a concatenated
        # romanization string (e.g. 'nudo'), not Hangul at all. ALSO
        # skipped for read_word: same reasoning as read_aloud — the
        # expected answer is a romanization ('hangeul'), and the word
        # itself lives in question.letter. ALSO skipped for
        # decompose_syllable: correct_answer is a jamo PAIR string
        # ('ㄷ + ㅗ'), not a composed block — _compose_bare_vowel would try
        # to read it as a single jamo and mangle it into a lone composed
        # syllable. The mode grades its own way (see the branch below).
        if question.mode not in ("read_aloud", "read_word", "missing_vowel", "word_contrast", "nonword_decode", "sequence_decode", "decompose_syllable"):
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
        elif question.mode == "read_word":
            # Whole-word reading: accept any of the word's
            # accepted_romanizations, compared with hyphens/spaces/case
            # normalized away so 'han-geul', 'Han Geul' and 'hangeul' all
            # count as the same answer (see _normalize_roman).
            accepted = question.accepted or [question.correct_answer]
            is_correct = self._normalize_roman(user_clean) in [
                self._normalize_roman(a) for a in accepted
            ]
            if is_correct:
                feedback = f"✅ Correct! **{question.letter}** reads as **{expected}**."
            else:
                feedback = f"❌ **{question.letter}** reads as **{expected}**. You typed '{user_clean}'."
        elif question.mode == "nonword_decode":
            # Graded as an exact romanization spelling match (case-insensitive),
            # same as read_aloud. The answer is a concatenated romanization
            # of two syllables (e.g. 'nudo' for 누도).
            is_correct = user_clean.lower() == expected.lower()
            if is_correct:
                feedback = f"✅ Correct! **{question.letter}** decodes as **{expected}**."
            else:
                feedback = f"❌ **{question.letter}** decodes as **{expected}**. You typed '{user_clean}'."
        elif question.mode == "sequence_decode":
            is_correct = user_clean.lower() == expected.lower()
            if is_correct:
                feedback = f"✅ Correct! **{question.letter}** reads as **{expected}**."
            else:
                feedback = f"❌ **{question.letter}** reads as **{expected}**. You typed '{user_clean}'."
        elif question.mode in ("match_sound", "missing_vowel", "batchim_challenge"):
            is_correct = user_clean == expected
            if is_correct:
                feedback = f"✅ Correct! **{expected}** is right."
            else:
                feedback = f"❌ Not quite. The answer is **{expected}**."
        elif question.mode == "decompose_syllable":
            # Graded on the jamo PAIR, order-significant, both components
            # required. _normalize_jamo_pair strips spacing/punctuation so
            # 'ㄷ+ㅗ' and 'ㄷ ㅗ' both count, but NOT order — 'ㅗㄷ' fails,
            # because knowing which letter is the consonant is the point.
            is_correct = (self._normalize_jamo_pair(user_clean)
                          == self._normalize_jamo_pair(expected))
            if is_correct:
                feedback = (f"✅ Correct! **{question.letter}** is "
                            f"**{expected}**.")
            else:
                feedback = (f"❌ Not quite. **{question.letter}** is "
                            f"**{expected}** (consonant first). "
                            f"You typed '{user_clean}'.")
        else:
            # Check correct_answer first, then any accepted alternates
            # (e.g. spell mode accepts the romanization string that the
            # prompt already showed, so typing 'i' for 이 counts correct).
            is_correct = (user_clean == expected
                          or user_clean.lower() in [a.lower() for a in (question.accepted or [])])
            if is_correct:
                feedback = f"✅ Perfect! **{expected}** is correct."
            else:
                feedback = f"❌ You typed **{user_clean}** but the answer is **{expected}**."

        # Track progress
        self.session_total += 1
        if is_correct:
            self.session_correct += 1
            self.session_streak += 1
            self._mark_mastered(question.letter, confidence=1)
            self._record_learner_item(question, correct=True, response_ms=response_ms)
        else:
            self.session_streak = 0
            self._mark_mastered(question.letter, confidence=-1)
            # Record confusion — only when both sides are real single
            # Hangul/jamo characters. read_aloud's "expected" is a
            # romanization string (e.g. "eo"), not Hangul, so a wrong
            # read_aloud guess should never be recorded here; same for any
            # stray typo the user typed that isn't a plausible letter.
            #
            # confused_with is user_clean, NOT expected: the mix-up this
            # item had was with what the LEARNER typed, mirroring the
            # existing f"{user_clean}↔{expected}" pair semantics right
            # below. Passing expected here would have made an item
            # record itself as confused with itself in most modes, since
            # question.letter == expected for everything except
            # confusion_drill (see _record_learner_item's docstring).
            valid_pair = (question.letter and user_clean
                          and _looks_like_hangul_target(user_clean)
                          and _looks_like_hangul_target(expected))
            self._record_learner_item(
                question, correct=False,
                confused_with=user_clean if valid_pair else None,
                response_ms=response_ms,
            )
            if valid_pair:
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
        # Normalize a bare vowel jamo to its composed form (ㅏ -> 아) so a
        # vowel's mastery lives under ONE key. Otherwise missing_vowel (whose
        # question.letter is the bare jamo) and every other mode (composed)
        # split the same vowel across two mastered_letters entries, and
        # lesson_mastery — which checks the composed pool — undercounts.
        item = self._compose_bare_vowel(item)
        self.progress.setdefault("mastered_letters", {})
        current = self.progress["mastered_letters"].get(item, 0)
        self.progress["mastered_letters"][item] = max(0, min(5, current + confidence))

    def _record_learner_item(self, question: QuizQuestion, correct: bool, confused_with: Optional[str] = None, response_ms: Optional[float] = None):
        """Update the richer LearnerItem record for this question's
        letter, in PARALLEL with _mark_mastered's flat int and the
        confusion_counts dict above — neither of those is touched or
        replaced by this method. Every existing reader of
        mastered_letters/confusion_counts (get_mastered_syllables,
        get_progress_summary, _top_confusions, _confusion_drill_question,
        lesson_mastery, next_question's has_confusions check) keeps
        reading exactly what it always has; this only adds a second,
        richer record alongside it so nothing that already works can
        break. next_question/_confusion_drill_question switching over to
        read learner_items instead is a deliberately separate, later
        step — that one changes what the learner is actually shown, so
        it gets its own review rather than riding along with this one.

        confused_with should be what the LEARNER typed (user_clean), not
        the expected answer — question.letter is normally the same
        value as `expected`, so recording a confusion against expected
        would have this item list itself as its own confusion partner
        in most modes. The caller already validates confused_with
        against _looks_like_hangul_target before passing it, matching
        the guard the confusion_counts write uses.

        Not called for questions with no letter (mirrors the `if not
        item: return` guard in _mark_mastered above).
        """
        item_key = question.letter
        if not item_key:
            return
        # Normalize bare vowel -> composed (ㅣ -> 이) so learner_items uses
        # the SAME key as _mark_mastered's mastered_letters. missing_vowel's
        # question.letter is the bare jamo; without this the two records
        # split a vowel across two keys and re-create the split this
        # migration is removing.
        item_key = self._compose_bare_vowel(item_key)

        item = self._get_item(item_key)

        if correct:
            item.correct += 1
        else:
            item.wrong += 1
            # No hard clear of _migrated_confidence here (a prior version
            # did that on any first new answer — see LearnerItem's
            # docstring for why that caused a "migration cliff": old
            # scores 3, 4, 5 all collapsed to the same value on the very
            # next correct answer). A correct answer needs no special
            # handling at all now — confidence is naturally
            # max(computed, floor), so it can only go up or hold, never
            # cliff. A wrong answer erodes the floor by exactly one
            # point, same as it would erode a non-migrated item's
            # confidence — this is the only place that erosion happens.
            item._wrong_since_migration += 1
            if confused_with and _looks_like_hangul_target(confused_with) and confused_with != item_key:
                item.confusions[confused_with] = item.confusions.get(confused_with, 0) + 1
                # Symmetric confusion recording. The flat confusion_counts
                # dict above keys on the UNORDERED pair, so one wrong answer
                # fed both directions at once — but this per-item record
                # only ever updated the EXPECTED letter's item (어's
                # confusions["아"] when 아 was typed for 어). The TYPED
                # letter's item never learned about the mix-up, so a drill
                # or summary sourced from learner_items could miss half of
                # it. Record it on BOTH items, guarded exactly like the
                # existing write above.
                typed_item = self._get_item(confused_with)
                typed_item.confusions[item_key] = typed_item.confusions.get(item_key, 0) + 1
                self._save_item(typed_item)

        item.last_seen = time.time()
        item.seen[question.mode] = item.seen.get(question.mode, 0) + 1

        # Update the EMA response time — only when a real measurement
        # was passed in (None means "not measured", e.g. programmatic
        # callers that don't time). First data point seeds directly;
        # subsequent points blend 80% old / 20% new.
        if response_ms is not None:
            if item.avg_response_ms == 0.0:
                item.avg_response_ms = response_ms
            else:
                item.avg_response_ms = item.avg_response_ms * 0.8 + response_ms * 0.2

        self._save_item(item)


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

    # Mastery thresholds for auto-advancing a lesson. A learner is
    # considered to have mastered a lesson once MASTERY_FRACTION of the
    # lesson's quizzable pool has reached confidence MASTERY_CONFIDENCE
    # (the same >=3 bar get_progress_summary already calls "mastered").
    # A fraction rather than "every item" is deliberate: pools run up to
    # 42 syllables (Lesson 5) and questions are randomly sampled, so
    # requiring 100% would be a grind and some items might never even be
    # shown. Both are plain constants so the bar is easy to tune.
    MASTERY_CONFIDENCE = 2
    MASTERY_FRACTION = 0.65

    # Share of questions in a word-based lesson (one with mastery_words)
    # that are whole-word reading. Primary rather than occasional because
    # such a lesson's mastery is measured per word (see lesson_mastery),
    # so word questions must dominate the session for that trigger to be
    # reachable in a normal session. Chosen so words are the clear
    # majority while spell/read_aloud/match_sound still run ~40% of the
    # time to keep sharpening the single-syllable components.
    READ_WORD_RATE = 0.60

    def lesson_mastery(self, lesson_id: int = None) -> dict:
        """Report mastery of a lesson's quiz pool. Uses the SAME pool the
        quiz actually draws from (_get_lesson_syllable_pool) and reads
        LearnerItem.confidence (the ratio/ramp signal) rather than the
        flat mastered_letters int, so mastery is consistent with the
        confidence signal .due, the romanization taper, and every other
        adaptive system already reads. Returns a dict with mastered_count,
        pool_size, needed (items required to tip over), fraction, and
        is_mastered. is_mastered is False for an empty pool (nothing to
        master)."""
        lesson = self._get_lesson(lesson_id) if lesson_id is not None else self.current_lesson
        if lesson is None:
            return {"mastered_count": 0, "pool_size": 0, "needed": 0,
                    "fraction": 0.0, "is_mastered": False}
        # Word-based lessons (Lesson 12) track mastery per WORD rather than
        # per syllable — the same word string is what _read_word_question
        # quizzes and what _record_learner_item keys its LearnerItem on, so
        # the pool to measure must match. Lessons with mastery_syllables
        # (5, 6, 11) declare a focused SUBSET of their practice_syllables as
        # the mastery target, so the gate checks against that rather than
        # the full pool — question generation still draws from the full
        # practice_syllables via _get_lesson_syllable_pool, untouched.
        # Every other lesson keeps its existing syllable pool.
        if lesson.get("mastery_words"):
            pool = lesson["mastery_words"]
        elif lesson.get("mastery_syllables"):
            pool = lesson["mastery_syllables"]
        else:
            pool = self._get_lesson_syllable_pool(lesson)
        pool_size = len(pool)
        mastered_count = sum(1 for s in pool
                             if self._get_item(s).confidence >= self.MASTERY_CONFIDENCE)
        # Round up so e.g. a 6-item pool needs 5 (ceil(4.8)), never 4.
        needed = math.ceil(pool_size * self.MASTERY_FRACTION) if pool_size else 0
        is_mastered = pool_size > 0 and mastered_count >= needed
        return {
            "mastered_count": mastered_count,
            "pool_size": pool_size,
            "needed": needed,
            "fraction": (mastered_count / pool_size) if pool_size else 0.0,
            "is_mastered": is_mastered,
        }

    # ── Helpers ────────────────────────────────────────────────────────

    def _normalize_roman(self, s: str) -> str:
        """Strip hyphens, spaces, lowercase for flexible romanization matching."""
        return s.replace("-", "").replace(" ", "").lower()

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
        not others.

        The len(s) != 1 guard is load-bearing: _VOWEL_JAMO is a string, so
        `"" in _VOWEL_JAMO` is always True (empty is a substring of any
        string) — without the guard, an empty answer collapsed to 'ㅏ'."""
        if len(s) != 1:
            return s
        return self._letter_to_syllable(s) if s in _VOWEL_JAMO else s

    def _letter_to_syllable(self, letter: str) -> str:
        """Combine a letter with a default vowel/consonant to make a full syllable block."""
        if len(letter) != 1:
            return letter
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
          4. lesson 1's letters composed with silent ㅇ (bare vowels →
             아/어/오/우/으/이) — every learner encounters these first,
             so they're always parseable. Derived from curriculum.json
             rather than hardcoded.
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
        # Last resort: lesson 1's vowels composed with silent ㅇ.
        lesson_1 = self.curriculum["lessons"][0]
        return [self._letter_to_syllable(v) for v in lesson_1.get("letters", [])]

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

        # Syllable decomposition — initial consonant position-aware (ㅇ
        # silent, ㄹ→'r'), final consonant by its real batchim SOUND (ㄱ→'k',
        # ㄷ→'t', ㅂ→'p', …) via _batchim_sound. No "-" separator: the whole
        # syllable is one romanization ('한'→'han', '각'→'gak'), matching the
        # title screen. The old code concatenated ROMANIZATION['ㄹ']='r/l'
        # into 'r/la', and the "-" was a teaching crutch for the vowel/final
        # distinction that has no place outside the batchim-intro lessons.
        try:
            cho, jung, jong = self._decompose_syllable(hangul)
            roman_cho = _initial_roman(cho)
            roman_jung = single_map.get(jung, '?')

            # Silent ㅇ: just the vowel sound
            if cho == 'ㅇ' and not jong:
                return roman_jung

            roman_jong = self._batchim_sound(jong) if jong else ""
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

    def syllable_breakdown(self, hangul: str) -> "Syllable":
        """Public entry point for 'give me this syllable's parts, composed
        and romanized, ready to render' — the seam that was missing before:
        _decompose_syllable/_compose_syllable/_hangul_to_roman_hint already
        did all this work internally, but nothing outside HangulQuiz could
        call it directly, so hangul_cli.py's title screen built its own
        separate hardcoded (jamo, romanization) pairs instead of reusing
        this engine's tested composition logic.

        Accepts either an already-composed block ('한') or a bare jamo
        letter, vowel or consonant ('ㅏ', 'ㄱ') — a bare letter is composed
        with its default partner first (via _letter_to_syllable, the same
        helper _compose_bare_vowel and _get_lesson_syllable_pool rely on)
        so the caller always gets back a real syllable block, never a
        naked jamo with nothing to decompose.

        Returns a Syllable whose .components is already shaped for
        _composition_rows() — see Syllable's docstring for the exact
        shape and the CVC vs. CV difference (jong present vs. '').
        """
        if len(hangul) == 1 and ord(hangul) < 0xAC00:
            # Bare jamo (below the composed-syllable code point range —
            # same check _decompose_syllable itself uses) — compose with
            # its default partner (same rule _compose_bare_vowel and
            # _letter_to_syllable already use) before decomposing, so
            # cho/jung/jong are never blank.
            hangul = self._letter_to_syllable(hangul)

        cho, jung, jong = self._decompose_syllable(hangul)
        romanization = self._hangul_to_roman_hint(hangul)

        components = []
        if cho == "ㅇ":
            # Silent placeholder: don't show "ㅇ + a" as if ㅇ contributes
            # a sound — that's the exact "learn the rule from a note"
            # pattern the redesign is moving away from. The vowel IS the
            # whole sound here, so components starts directly from jung.
            components.append((jung, ROMANIZATION.get(jung, "?")))
        else:
            components.append((cho, _initial_roman(cho)))
            components.append((jung, ROMANIZATION.get(jung, "?")))
        if jong:
            components.append((jong, self._batchim_sound(jong)))
        components.append((hangul, romanization))

        return Syllable(
            text=hangul,
            romanization=romanization,
            cho=cho,
            jung=jung,
            jong=jong,
            components=components,
            is_bare_vowel=(cho == "ㅇ" and not jong),
        )

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
        """Get all syllables from completed lessons, with safe fallbacks.

        Priority order:
          1. Syllables from completed lessons (real learned content).
          2. Current lesson's own pool — so a learner mid-first-lesson
             gets distractors from what they're currently studying, not
             arbitrary untaught syllables.
          3. Lesson 1's letters composed with silent ㅇ (bare vowels →
             아/어/오/우/으/이) — every learner encounters these first,
             so they're always parseable. Derived from curriculum.json
             rather than hardcoded, so it stays in sync if lesson 1
             changes.
        """
        known = []
        for lesson in self.curriculum["lessons"]:
            if lesson["id"] in self.progress["completed_lessons"]:
                known.extend(lesson.get("practice_syllables", []))
                known.extend(lesson.get("example_syllables", []))
        if known:
            return known

        # No completed lessons yet — use current lesson's pool if available
        if self.current_lesson:
            pool = self._get_lesson_syllable_pool(self.current_lesson)
            if pool:
                return pool

        # Last resort: lesson 1's vowels composed with silent ㅇ.
        # Every learner has seen these; they're always safe distractors.
        lesson_1 = self.curriculum["lessons"][0]
        return [self._letter_to_syllable(v) for v in lesson_1.get("letters", [])]

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
