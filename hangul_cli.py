#!/usr/bin/env python3
"""
hangul_cli.py — Interactive Hangul learning tutor CLI.

Uses the HangulQuiz engine for deterministic quiz generation. Runs fully
offline by default — hardcoded mnemonics and template-built sentences, no
external dependencies. An optional --use-llm flag turns on local Ollama
enrichments (generated mnemonics for non-basic letters, LLM sentences,
encouragement, and a natural-language session summary) for anyone who has
Ollama installed; nothing requires it.

Usage:
    python hangul_cli.py                  # Interactive mode (offline)
    python hangul_cli.py --lesson 1       # Start at specific lesson
    python hangul_cli.py --mode spell     # Practice only spelling
    python hangul_cli.py --sudden-death   # One-life mode, count streak
    python hangul_cli.py --mnemonic ㄱ    # Print a mnemonic for a letter
    python hangul_cli.py --use-llm        # Enable optional Ollama enrichments
"""

import sys
import os
import re
import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
sys.path.insert(0, str(PROJECT_ROOT))

from hangul_quiz_engine import HangulQuiz, QuizQuestion, _initial_roman, _VOWEL_JAMO
from hangul_conversation import (
    generate_conversation_turn, check_conversation_answer, build_template_sentence
)
from hangul_models import get_model, set_default_model, summarize_models

# Whether optional Ollama enrichments are enabled. OFF by default — the app
# is fully functional offline. Set once from --use-llm in main(). Every
# Ollama-calling helper checks this and takes an offline path when it's
# False, so nothing ever blocks on (or errors out against) a model that
# isn't there.
USE_LLM = False

# ── Ollama helpers ─────────────────────────────────────────────────────────

def ollama_chat(prompt: str, system: str = "", temperature: float = 0.7, model: str = None) -> str:
    """Call Ollama with a prompt and return the response."""
    if model is None:
        model = get_model("sentence")
    try:
        cmd = ["ollama", "run", model]
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        result = subprocess.run(
            cmd,
            input=full_prompt,
            capture_output=True,
            text=True,
            timeout=60,
            encoding='utf-8'
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return f"[Ollama error: {result.stderr.strip()[:100]}]"
    except FileNotFoundError:
        return "[Ollama not found — is it installed and on PATH?]"
    except subprocess.TimeoutExpired:
        return (f"[Ollama timed out after 60s using '{model}' — this model may be too slow for your "
                f"machine, or still loading for the first time. Try 'ollama run {model}' directly in "
                f"a separate terminal to see how long it actually takes, or restart with a smaller "
                f"--model.]")
    except Exception as e:
        return f"[Ollama error: {e}]"

def generate_mnemonic(letter: str, user_context: str = "") -> str:
    """Generate a personalized mnemonic for a Hangul letter."""
    curriculum_path = PROJECT_ROOT / "data" / "curriculum.json"
    with open(curriculum_path, encoding='utf-8') as f:
        curriculum = json.load(f)

    pron, strokes = _lookup_letter_info(curriculum, letter)
    info = f"Pronunciation: {pron}\nShape: {', '.join(strokes)}" if pron else ""

    system = "You are a creative Hangul teacher. Generate short, memorable mnemonics."
    prompt = f"""Create a mnemonic for the Korean letter '{letter}'.

Technical info:
{info}

{f"The user says this is memorable to them: '{user_context}'." if user_context else ""}

Rules:
- Make it visual — link the letter's SHAPE to something in English
- Keep it under 3 sentences
- Make it funny or surprising if possible
- Reference the user's personal context if provided

Mnemonic:"""

    return ollama_chat(prompt, system, temperature=0.9, model=get_model("mnemonic"))

def mnemonic_for(letter: str) -> str:
    """Return a mnemonic for a letter, offline-first. The 24 basic letters
    have hand-written, instant mnemonics in ALPHABET_MNEMONICS — always
    used first, and the only source needed for the core curriculum. Only
    when --use-llm is on AND the letter isn't in that table (e.g. a tense
    or compound letter) does this fall back to a live Ollama generation,
    and even then a failed call (which generate_mnemonic returns as a
    '[...]' string) is swallowed rather than shown as if it were the
    mnemonic — the old bug where '/mnemonic' printed '[Ollama not found]'
    verbatim. With no mnemonic available, returns a gentle nudge instead
    of an error."""
    fixed = ALPHABET_MNEMONICS.get(letter)
    if fixed:
        return fixed
    if USE_LLM:
        generated = generate_mnemonic(letter)
        if generated and not generated.startswith("["):
            return generated
    return f"(No stock mnemonic for {letter} — picture its shape and tie it to its sound.)"

def generate_mini_sentence(known_syllables: list[str], quiz: HangulQuiz) -> str:
    """Generate a tiny Korean sentence using only the syllables the user knows."""
    # Real words need a genuine initial consonant somewhere — a pile of
    # bare vowel-placeholder syllables (아/어/오/우/으/이, still all you'd
    # have at e.g. lesson 1) can't form an actual Korean sentence no
    # matter how many of them you've mastered. Asking the model to invent
    # a "real, natural sentence" from vowels alone just produces a
    # hallucinated string with a fabricated translation — worse than
    # showing nothing, since it looks legitimate to a beginner.
    real_word_syllables = [s for s in known_syllables if quiz.has_real_consonant(s)]
    if len(real_word_syllables) < 3:
        return None

    system = "You are a Korean language teacher. Create tiny Korean sentences using ONLY the syllables provided. Never use syllables outside the list. Include English translation."
    prompt = f"""Create a tiny Korean sentence (2-4 words) using ONLY these syllables:
{', '.join(known_syllables[:20])}

Rules:
- ONLY use combinations of the syllables listed above — nothing else
- Include the English translation
- Make it a real, natural sentence (even if very simple)
- Keep response short: just the Korean sentence and translation

Sentence:"""

    result = ollama_chat(prompt, system, temperature=0.5, model=get_model("sentence"))
    if result.startswith("["):
        # ollama_chat's own convention for a failed call (not found, timed
        # out, error) — returning it here would show it to the user AS
        # the sentence, which is exactly what happened before this check
        # existed: "📖 You can now read: [Ollama timed out]".
        return None
    return result

def generate_encouragement(streak: int, correct_pct: float, mode: str = "") -> str:
    """Generate personalized encouragement based on performance."""
    system = "You are an encouraging Korean tutor. Be warm, brief (1-2 lines), and supportive."
    prompt = f"""The student has a streak of {streak} correct answers and is {int(correct_pct)}% accurate.
{f'Mode: {mode}' if mode else ''}
Give a short, warm encouragement. Mention something specific about their progress."""

    return ollama_chat(prompt, system, temperature=0.8, model=get_model("encouragement"))

def build_session_data(quiz: HangulQuiz) -> dict:
    """Build the session_data dict for generate_session_summary from the quiz
    engine's existing state. strong/struggling letters are derived from
    cumulative mastery confidence (0-5) as a proxy — no new tracking fields
    are added to the engine."""
    mastered = quiz.progress.get("mastered_letters", {})
    return {
        "questions_answered": quiz.session_total,
        "accuracy_pct": round(100 * quiz.session_correct / max(1, quiz.session_total)),
        "ending_streak": quiz.session_streak,
        "strong_letters": [l for l, v in mastered.items() if v >= 4],
        "struggling_letters": [l for l, v in mastered.items() if v <= 1],
    }


def print_lesson_complete(quiz) -> None:
    """Print a structured lesson-complete summary block.
    Pure reformatting of data already tracked — no new fields, no Ollama calls."""
    W = 32  # inner width (between ║...║)

    # Guard: if current_lesson is somehow None at quit time, skip Weakest/Next silently.
    has_lesson = quiz.current_lesson is not None

    # --- Data ---
    accuracy = round(100 * quiz.session_correct / max(1, quiz.session_total))
    questions = quiz.session_total
    best_streak = quiz.progress.get("streak_best", 0)

    # Weakest letter scoped to current lesson's pool
    weakest = None
    if has_lesson:
        lesson_pool = set(quiz._get_lesson_syllable_pool(quiz.current_lesson))
        mastered = quiz.progress.get("mastered_letters", {})
        lesson_mastered = {k: v for k, v in mastered.items() if k in lesson_pool}
        if lesson_mastered:
            weakest = min(lesson_mastered, key=lambda k: lesson_mastered[k])

    # Next lesson
    next_lesson = None
    if has_lesson:
        try:
            nxt = quiz._get_lesson(quiz.current_lesson["id"] + 1)
            next_lesson = {"title": nxt["title"], "letters": nxt.get("letters", [])}
        except ValueError:
            pass

    # --- Render ---
    def kv_row(label: str, value: str, value_styles=()) -> str:
        """One key-value row inside the box. value_styles applied only to value."""
        label_field = f"  {label:<14}"  # left-align label in 16-char field (2 indent + 14)
        right_pad = 2
        pad = W - len(label_field) - len(value) - right_pad
        if pad < 0:
            pad = 0
        val = styled(value, *value_styles) if value_styles else value
        return f"║{label_field}{val}{' ' * pad}║"

    def blank_row() -> str:
        return f"║{' ' * W}║"

    lines = [
        styled("╔" + "═" * W + "╗", CYAN),
        styled(f"║{'LESSON COMPLETE':^{W}}║", BOLD, CYAN),
        styled("╠" + "═" * W + "╣", CYAN),
    ]

    lines.append(kv_row("Accuracy", f"{accuracy}%"))
    lines.append(kv_row("Questions", str(questions)))
    lines.append(kv_row("Best Streak", f"{best_streak} ✦"))

    # Weakest: omit entirely if None (no mastered data for this lesson yet)
    if weakest:
        lines.append(kv_row("Weakest", weakest, (YELLOW,)))

    # Next lesson: show up to 5 letters, append "…" if more
    if next_lesson:
        lines.append(blank_row())
        lines.append(kv_row("Next", f"Lesson {quiz.current_lesson['id'] + 1}", (GREEN,)))
        letters = next_lesson["letters"]
        if len(letters) > 5:
            letters_str = " ".join(letters[:5]) + " …"
        else:
            letters_str = " ".join(letters)
        lpad = (W - len(letters_str)) // 2
        rpad = W - len(letters_str) - lpad
        lines.append(f"║{' ' * lpad}{letters_str}{' ' * rpad}║")

    lines.append(styled("╚" + "═" * W + "╝", CYAN))
    print("\n" + "\n".join(lines) + "\n")


# ANSI escape sequences (terminal cursor/color codes) that small local models
# sometimes emit into their output — stripped before returning the summary.
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def generate_session_summary(session_data: dict) -> str:
    """Generate a 2-3 sentence session summary via the local Ollama model.
    Falls back to a deterministic template if Ollama is unavailable or errors."""
    system = (
        "You write short, warm session summaries for a Hangul learning app. "
        "Use only the data provided. Do not invent letters, stats, or facts. "
        "Never state a number of correct or wrong answers — the data does not include one. "
        "Write in English. 2-3 sentences maximum."
    )

    parts = [f"The learner answered {session_data['questions_answered']} questions "
             f"at {session_data['accuracy_pct']}% accuracy."]

    if session_data["ending_streak"] >= 3:
        parts.append(f"They ended on a {session_data['ending_streak']}-question streak.")

    if session_data["strong_letters"]:
        parts.append(f"Strong letters: {', '.join(session_data['strong_letters'])}.")

    if session_data["struggling_letters"]:
        parts.append(f"Letters to work on: {', '.join(session_data['struggling_letters'])}.")

    prompt = " ".join(parts) + " Write a session summary."

    # Only reach for Ollama when enrichments are on; otherwise go straight
    # to the deterministic template below (the sentinel just routes there),
    # so a normal offline /quit never eats a 60s model timeout.
    result = ollama_chat(
        prompt=prompt,
        system=system,
        temperature=0.75,
        model=get_model("summary"),
    ) if USE_LLM else "[offline]"
    if result.startswith("["):
        # ollama_chat's convention for a failed call (not found / timeout /
        # error) — fall back to a hardcoded template so the feature degrades
        # gracefully instead of crashing.
        strong = ", ".join(session_data["strong_letters"]) or None
        weak = ", ".join(session_data["struggling_letters"]) or None

        lines = [f"Session complete — {session_data['questions_answered']} questions "
                 f"at {session_data['accuracy_pct']}%."]
        if strong:
            lines.append(f"Strong letters: {strong}.")
        if weak:
            lines.append(f"Worth revisiting: {weak}.")
        return " ".join(lines)
    # Strip ANSI escape sequences the model may emit (terminal cursor codes).
    return _ANSI_RE.sub("", result).strip()

# ── CLI ────────────────────────────────────────────────────────────────────

# Enable ANSI color codes on Windows (older cmd.exe won't render them otherwise)
if sys.platform == "win32":
    os.system("")

BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

def styled(text: str, *styles) -> str:
    return ''.join(styles) + text + RESET

# ── Letter reveal ─────────────────────────────────────────────────────────
# Present a single letter as its REAL glyph, featured in a framed "card"
# with a short pop-in reveal. The terminal's own font draws every Hangul
# letter far more accurately than any in-terminal ASCII grid could — the
# old 5x5 block animation was recognizable for straight letters (ㅁ/ㄷ/ㅏ)
# but fell apart on curves and diagonals (ㅇ/ㅎ/ㅅ/ㅈ) and printed a crude
# duplicate right beside the real letter — so this shows the letter itself,
# big and clean. No stroke count: this app teaches reading recognition, not
# handwriting stroke order.

def reveal_letter(letter: str, pause: float = 0.55):
    """Reveal one letter in a framed card: draw the empty frame, pop the
    real glyph in, then brighten it — a quick, deliberate 'ta-da', redrawn
    in place (cursor-up overwrite) so it animates rather than scrolls.
    'Big' is expressed through the frame, bold/color emphasis and
    whitespace, since a terminal can't scale a single character's font."""
    inner_w = 7  # inner width of the card, in terminal columns

    top = "   ┌" + "─" * inner_w + "┐"
    bot = "   └" + "─" * inner_w + "┘"
    blank_row = "   │" + " " * inner_w + "│"

    def mid(styles) -> str:
        # Center the glyph by VISUAL width — jamo/syllables are double-width.
        w = _vwidth(letter)
        left = (inner_w - w) // 2
        right = inner_w - w - left
        glyph = styled(letter, *styles) if styles else " " * w
        return "   │" + " " * left + glyph + " " * right + "│"

    frames = [
        [top, blank_row, mid(None), blank_row, bot],          # empty slot
        [top, blank_row, mid((CYAN,)), blank_row, bot],       # glyph pops in
        [top, blank_row, mid((BOLD, CYAN)), blank_row, bot],  # brightens, holds
    ]
    height = len(frames[0])
    for i, frame in enumerate(frames):
        print("\n".join(frame))
        time.sleep(pause if i == len(frames) - 1 else 0.12)
        if i < len(frames) - 1:
            # Overwrite this frame in place with the next one, so it reads
            # as a reveal rather than a stack of printed boxes.
            sys.stdout.write(f"\033[{height}F")
            sys.stdout.flush()


def _lookup_letter_info(curriculum: dict, letter: str) -> tuple:
    """Find a letter's pronunciation and stroke order by scanning the
    curriculum's lessons. Factored out of generate_mnemonic (which used
    to do this same scan inline) so there's one place that knows how to
    find this data, reused by both the Ollama mnemonic prompt and the
    alphabet walkthrough below."""
    for lesson in curriculum["lessons"]:
        if letter in lesson.get("letters", []):
            pron = lesson.get("pronunciation", {}).get(letter, "")
            strokes = lesson.get("stroke_order", {}).get(letter, [])
            return pron, strokes
    return "", []

# The real, standard Hangul alphabet order — what every Korean dictionary,
# keyboard layout, and textbook uses. NOT the same as curriculum.json's
# lesson order (which groups letters by teaching difficulty across
# separate lesson files, e.g. simple vowels in lesson 1 but y-vowels
# tucked into lesson 6). This is consonants first, then vowels, each in
# their canonical sequence — 14 + 10 = the 24 basic letters.
ALPHABET_CONSONANTS = ["ㄱ", "ㄴ", "ㄷ", "ㄹ", "ㅁ", "ㅂ", "ㅅ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"]
ALPHABET_VOWELS = ["ㅏ", "ㅑ", "ㅓ", "ㅕ", "ㅗ", "ㅛ", "ㅜ", "ㅠ", "ㅡ", "ㅣ"]

# Hand-written, instant, visual/eye-catching shape mnemonics for the full
# alphabet walkthrough. Deliberately NOT generated live via Ollama (unlike
# generate_mnemonic elsewhere) — a brand-new learner's very first pass
# through all 24 letters should feel snappy, not stall on 24 sequential
# model calls (and not risk failing if Ollama isn't running yet). These
# are fixed but still genuinely fun/memorable on their own.
ALPHABET_MNEMONICS = {
    "ㄱ": "Looks like a golf club mid-swing! ⛳",
    "ㄴ": "A knee, bent and ready to kneel. 🦵",
    "ㄷ": "A door, propped open on its hinge. 🚪",
    "ㄹ": "A wiggly river, bending back and forth. 🌊",
    "ㅁ": "A square mouth, lips pressed together, humming a low 'mmm'. 👄",
    "ㅂ": "A tiny table standing on two legs. 🪑",
    "ㅅ": "A mountain summit. ⛰️",
    "ㅇ": "A balloon — round and silent as it floats... until it lands with a boiNG! 🎈",
    "ㅈ": "A person mid-jump, leg kicking out behind. 🤸",
    "ㅊ": "Jumping and cheering, with a little spark above! 🎉",
    "ㅋ": "A key with an extra tooth. 🔑",
    "ㅌ": "The middle prong of a trident. 🔱",
    "ㅍ": "Goalposts on a soccer field. 🥅",
    "ㅎ": "A face wearing a little top hat, tipped just so. 🎩",
    "ㅏ": "An arm reaching right as your mouth opens — 'ah'! 👉",
    "ㅑ": "Like ㅏ, but waving with both hands — 'ya ya ya!' 👋",
    "ㅓ": "The mirror image of ㅏ — pointing left instead. 👈",
    "ㅕ": "Like ㅓ, waving both hands the other way. 🙌",
    "ㅗ": "A little flag, planted proudly on its pole. 🚩",
    "ㅛ": "A flag with two flaps, fluttering. 🎏",
    "ㅜ": "An umbrella, handle hanging down. ☂️",
    "ㅠ": "An umbrella with two spokes — extra rainy. 🌧️",
    "ㅡ": "A flat horizon line — no rounding, just a flat mouth. 〰️",
    "ㅣ": "A person standing tall and thin, saying 'ee'. 🧍",
}

# Letters whose pronunciation genuinely depends on WHERE they sit in a
# syllable, not just what they are — a fundamentally different kind of
# fact than "here's how this letter sounds." Among the 24 basic letters,
# only ㅇ has this (silent as an initial placeholder, 'ng' as a final
# consonant/batchim); everything else sounds the same regardless of
# position. Flagged separately and prominently rather than folded into
# the normal pronunciation line, so it doesn't read as just one more
# unremarkable fact among many.
POSITIONAL_QUIRKS = {
    "ㅇ": "SILENT at the start of a syllable — but sounds like 'ng' at the end!",
}

def run_alphabet_intro(quiz: HangulQuiz):
    """The full 24-letter Hangul alphabet, front to back, in the real
    canonical order — consonants then vowels — meant as THE first thing a
    brand-new learner sees. Distinct from run_beginner_intro (which walks
    just the current lesson's letters for reference/review): this is a
    one-time, celebratory, extra-eye-catching first pass across the whole
    alphabet, with a visual mnemonic for every letter and no lesson
    boundaries to break the flow."""
    curriculum = quiz.curriculum
    roman_table = quiz.get_romanization_table()
    ordered = [("Consonants", ALPHABET_CONSONANTS, "🔤"), ("Vowels", ALPHABET_VOWELS, "🎵")]
    total = len(ALPHABET_CONSONANTS) + len(ALPHABET_VOWELS)

    print(f"\n{styled('🇰🇷✨ The Hangul Alphabet ✨🇰🇷', BOLD, GREEN)}")
    intro_line = f"{total} letters — 14 consonants, 10 vowels. Let's meet them all!"
    print(f"{styled(intro_line, CYAN)}")
    print(f"{styled('Press Enter for the next letter, or type its romanization to try it. /skip to jump to lesson picking anytime.', CYAN)}")

    seen = 0
    for section_name, letters, icon in ordered:
        print(f"\n{styled(f'{icon}  {section_name}', BOLD, YELLOW)}")
        for letter in letters:
            seen += 1
            roman = roman_table.get(letter, "")
            pron, _ = _lookup_letter_info(curriculum, letter)
            mnemonic = ALPHABET_MNEMONICS.get(letter, "")
            quirk = POSITIONAL_QUIRKS.get(letter, "")

            print(f"\n{styled(f'[{seen}/{total}]', BOLD)}\n")
            reveal_letter(letter)
            if roman:
                print(f"      romanizes as: {styled(roman, BOLD)}")
            if quirk:
                print(f"      {styled('⚡ ' + quirk, BOLD, YELLOW)}")
            if pron:
                print(f"      sounds like: {pron}")
            if mnemonic:
                print(f"      {styled('💡 ' + mnemonic, GREEN)}")

            try:
                response = input(f"\n{styled('[Enter=next, or type romanization]', CYAN)} {styled('>', BOLD)} ").strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\n{styled('Alphabet walkthrough ended early — no worries, come back anytime with /alphabet.', YELLOW)}")
                return
            if response.lower() in ('/skip', 'skip'):
                print(f"{styled('Skipping ahead to lesson picking!', YELLOW)}")
                return
            if response:
                resp = response.lower()
                # A slashed romanization like "r/l" means EITHER spelling is
                # right — accept "r" and "l" too, not just the literal "r/l".
                accepted = [p.strip() for p in roman.lower().split("/")]
                if resp == roman.lower() or resp in accepted:
                    print(f"   {styled('✅ Nailed it!', GREEN)}")
                else:
                    msg = f'Close — {letter} is "{roman}". No score kept, just practice!'
                    print(f"   {styled(msg, YELLOW)}")

    print(f"\n{styled('🎉 You have met the whole Hangul alphabet! 🎉', BOLD, GREEN)}")


def _offer_lesson_picker(quiz: HangulQuiz) -> dict:
    """Show the lesson list and let the learner pick where to go next,
    instead of silently forcing a specific lesson order on them. Returns
    the lesson_info for whatever they picked (or lesson 1 if they just
    press Enter)."""
    print(f"\n{styled('📚 Where would you like to start?', BOLD)}")
    for l in quiz.list_lessons():
        mark = styled('✓', GREEN) if l['completed'] else ''
        print(f"   {l['id']:2}. {l['title']} {mark}")
    try:
        choice = input(f"\n{styled('Lesson number (or Enter for Lesson 1):', CYAN)} ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = ""
    try:
        lid = int(choice) if choice else 1
    except ValueError:
        lid = 1
    return quiz.start_lesson(lid)


_HANGUL_WIDE_RANGES = (
    (0x1100, 0x11FF),  # Hangul Jamo block
    (0x3130, 0x318F),  # Hangul Compatibility Jamo — the standalone ㅎㅏㄴ etc. used throughout this app
    (0xAC00, 0xD7A3),  # Hangul Syllables (composed blocks like 한, 글)
)

def _vwidth(s: str) -> int:
    """Approximate terminal column width: Hangul jamo/syllables render
    double-width in virtually every terminal, everything else single-
    width. Naively aligning a Hangul line over a Latin-romanization line
    at the same string INDEX drifts off, since 'ㅎ' occupies 2 columns
    but 'h' occupies 1 — this is what makes width-aware padding below
    actually necessary rather than cosmetic."""
    return sum(2 if any(lo <= ord(c) <= hi for lo, hi in _HANGUL_WIDE_RANGES) else 1
               for c in s)

def _pad_to(s: str, width: int) -> str:
    return s + " " * max(0, width - _vwidth(s))

def _composition_rows(cells, connector=" + ", final_connector="   =   ", indent="   "):
    """cells: list of (jamo, romanization) tuples, last entry is the
    assembled result (e.g. ('한', 'han')). Every jamo/romanization pair
    is padded to the same visual column width so the romanization line
    lines up under its jamo in a real terminal. Only the actual jamo/
    result characters get colored — connectors ('+', '=') stay plain, so
    the color draws the eye to the letters themselves, not the notation
    around them. Romanization is intentionally left fully monochrome:
    the point is to keep visual focus on the Hangul, with romanization
    as a quiet reference underneath rather than competing for attention.

    Returns (jamo_pieces, roman_line, indent) — jamo_pieces is a list of
    already-styled text units (one per jamo/connector), left unjoined so
    a caller can reveal them one at a time for a typewriter effect;
    roman_line is the plain, fully-joined monochrome line, shown all at
    once beneath once the jamo line finishes revealing."""
    n = len(cells)
    jamo_pieces, roman_pieces = [], []
    for i, (j, r) in enumerate(cells):
        w = max(_vwidth(j), _vwidth(r))
        is_result = (i == n - 1)
        jamo_pieces.append(styled(_pad_to(j, w), BOLD, GREEN if is_result else CYAN))
        roman_pieces.append(_pad_to(r, w))
        if i < n - 1:
            sep = final_connector if i == n - 2 else connector
            jamo_pieces.append(sep)  # plain — not styled, distinct from the letters
            roman_pieces.append(sep)
    roman_line = indent + "".join(roman_pieces)  # fully monochrome
    return jamo_pieces, roman_line, indent


def _highlight_in_sentence(sentence: str, target: str) -> Optional[str]:
    """Return `sentence` with the FIRST/ONLY occurrence of `target` styled
    bold+GREEN (matching _composition_rows' convention of GREEN for the
    piece under focus), or None if it can't highlight safely.

    Fails closed rather than guessing: returns None (never a fabricated
    or over-eager highlight) when target doesn't appear in sentence at
    all, or appears more than once. A naive sentence.replace(target, ...)
    would highlight EVERY occurrence — for a particle like 도, a longer
    sentence could easily contain it twice for unrelated reasons, and
    lighting up both would either look broken or, worse, accidentally
    hint at the answer through visual pattern rather than content. One
    confirmed occurrence is what every seed example is written to have;
    if content ever violates that, the caller should fall back to plain
    text rather than this function inventing a highlight that isn't
    trustworthy."""
    count = sentence.count(target)
    if count != 1:
        return None
    idx = sentence.index(target)
    before, after = sentence[:idx], sentence[idx + len(target):]
    return before + styled(target, BOLD, GREEN) + after


def print_title_screen():
    """A quick startup banner with a light reveal effect. Shown on EVERY
    launch (not just first-run), so it's deliberately brief — a couple
    seconds total — rather than the slower, savor-it pacing used for the
    alphabet/letter animations, which only play once per letter and can
    afford to linger. Each composition row types out letter by letter
    (dramatic but quick — well under a second per row) rather than
    appearing all at once, then the romanization line beneath it appears
    in full once the jamo line finishes.

    Rather than just claim Hangul is rational and easy, this DEMONSTRATES
    it: builds the word 한글 ('Hangul', the writing system's own name)
    live from its component jamo (ㅎ+ㅏ+ㄴ=한, ㄱ+ㅡ+ㄹ=글) — the exact
    same combining logic every syllable in the app uses — with
    romanization aligned underneath each jamo so the sound-mapping is as
    visible as the shape-mapping. Decomposition verified against the
    actual Unicode Hangul syllable formula, not eyeballed."""
    print()
    rows = [
        [("ㅎ", "h"), ("ㅏ", "a"), ("ㄴ", "n"), ("한", "han")],
        [("ㄱ", "g"), ("ㅡ", "eu"), ("ㄹ", "l"), ("글", "geul")],
    ]
    for cells in rows:
        jamo_pieces, roman_line, indent = _composition_rows(cells)
        sys.stdout.write(indent)
        for piece in jamo_pieces:
            sys.stdout.write(piece)
            sys.stdout.flush()
            time.sleep(0.08)
        print()  # close out the jamo line once fully revealed
        print(roman_line)
        time.sleep(0.2)
    time.sleep(0.2)
    print(f"\n   {styled('한글', BOLD, GREEN)}  —  \"Hangul\": literally, the great script")
    time.sleep(0.35)
    print(styled("\n✨  Learn to read Korean, one letter at a time  ✨", BOLD, GREEN))
    print()


def show_start_menu(quiz: HangulQuiz) -> dict:
    """The real entry point for every launch — title screen, then a menu:
    resume (default, one keystroke), the full alphabet walkthrough, or
    the lesson list. Replaces the old behavior of always dropping
    straight into Lesson 1's quiz, and replaces the earlier first-run-
    only Y/n prompt (which only ever appeared once, on a completely
    untouched profile) with something offered every time — so alphabet/
    lesson-picking stay reachable without already knowing the slash
    commands exist, while resuming stays the fast, one-keystroke path
    once there's real progress to resume."""
    print_title_screen()

    # start_lesson() with no argument resumes to whatever current_lesson
    # already is — same resume semantics as main()'s own default, just
    # surfaced here so the menu can show WHERE that resume point is
    # before asking the learner to commit to it.
    resume_info = quiz.start_lesson()
    has_progress = quiz.progress.get("total_questions_answered", 0) > 0
    resume_label = "Continue" if has_progress else "Start"

    print(f"{styled('📚 Where to?', BOLD)}")
    print(f"   {styled('[Enter]', CYAN)} {resume_label} — Lesson {resume_info['id']}: {resume_info['title']}")
    print(f"   {styled('[a]', CYAN)}     Alphabet Walkthrough — meet all 24 letters first")
    print(f"   {styled('[l]', CYAN)}     Lesson list — pick any lesson")
    print(f"   {styled('[q]', CYAN)}     Quit")

    try:
        choice = input(f"\n{styled('>', BOLD)} ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        choice = "q"

    if choice == "q":
        print(f"\n{styled('👋 안녕히 가세요! (Goodbye!)', GREEN)}")
        sys.exit(0)
    if choice == "a":
        run_alphabet_intro(quiz)
        return _offer_lesson_picker(quiz)
    if choice == "l":
        return _offer_lesson_picker(quiz)
    return resume_info


def print_lesson_intro(introduction: str = "", note: str = ""):
    """Print a lesson's 'introduction' and/or 'note' text, if it has any.
    These carry real teaching content (e.g. the ㅇ-placeholder rule) that
    would otherwise never reach the screen."""
    if introduction:
        print(f"\n{styled('📘', CYAN)} {introduction}")
    if note:
        print(f"\n{styled('📝 Note:', YELLOW)} {note}")

def print_reference_table(quiz: HangulQuiz, lesson: dict):
    """Print a full reference table for the lesson's letters/content before
    quizzing starts, so the learner sees every pronunciation up front
    instead of picking it up one mnemonic at a time. Picks whichever kind
    of reference data the lesson actually has: per-letter pronunciation,
    batchim rules, or vocabulary. Stroke order is intentionally NOT shown
    here — it's covered visually by the /alphabet and /intro animations,
    and as text it was judged unnecessary clutter for this app's actual
    purpose (letter recognition, not calligraphy).

    For the pronunciation branch (vowel/consonant-introduction lessons),
    this now also shows each letter as a COMPOSED block (아, not just ㅏ),
    via quiz.syllable_breakdown() + _composition_rows() — the same
    composition primitive the title screen uses, reused here instead of
    staying a title-screen one-off. This is the fix for the reported gap:
    the vertical list of lone letters was the one place in the app where
    the composed-block visual disappeared. See lessons.hangul-tutor for
    the fuller design rationale (whole → decompose → reconstruct).

    Consonant lessons (ones with a practice_syllables pool — vowel-only
    Lesson 1 doesn't have one) additionally get a CONTRASTIVE ROW: the
    lesson's own consonants against one shared vowel (가 나 다 라 마 —
    "same vowel, changing consonant"), so the pattern is visible as soon
    as a consonant has something to combine with, not deferred to a
    later lesson."""
    pronunciation = lesson.get("pronunciation") or {}
    batchim_pron = lesson.get("batchim_pronunciation") or {}
    batchim_rules = lesson.get("batchim_pronunciation_rules") or {}
    vocabulary = lesson.get("vocabulary") or []
    block_rules = lesson.get("block_rules") or {}
    letter_romanization = lesson.get("letter_romanization") or {}

    if pronunciation:
        print(f"\n{styled('📋 Reference Table', BOLD, CYAN)}")
        letters = lesson.get("letters", [])

        # Composed-block row: each letter shown as a real syllable block
        # (아, 가, ...) with romanization aligned underneath, not just the
        # bare jamo. Skipped only if composition fails for every letter
        # (shouldn't happen for the 24 basic letters this branch covers,
        # but falling through to the plain list below is a safe default
        # rather than crashing the reference table over a display extra).
        composed_cells = []
        for letter in letters:
            try:
                syl = quiz.syllable_breakdown(letter)
                composed_cells.append((syl.text, syl.romanization))
            except Exception:
                pass
        if composed_cells:
            jamo_pieces, roman_line, indent = _composition_rows(
                composed_cells, connector="   ", final_connector="   "
            )
            # No '=' final_connector here — this is a peer row of blocks
            # (아 어 오 우 으 이), not a single composition building up to
            # one result, so the visual shouldn't imply one.
            sys.stdout.write(indent)
            for piece in jamo_pieces:
                sys.stdout.write(piece)
            print()
            print(roman_line)
            print()

        for letter in letters:
            pron = pronunciation.get(letter, "")
            code = letter_romanization.get(letter, "")
            code_str = f" ({code})" if code else ""
            line = f"   {styled(letter, BOLD)}{code_str}  —  {pron}"
            print(line)
            quirk = POSITIONAL_QUIRKS.get(letter, "")
            if quirk:
                print(f"        {styled('⚡ ' + quirk, BOLD, YELLOW)}")

        # Contrastive row(s) — only for lessons that actually introduce a
        # consonant with something to combine against (practice_syllables
        # present). Group the lesson's own practice syllables by shared
        # vowel so the row reads as "same vowel, changing consonant"
        # (가 나 다 라 마), the Axis-1 pattern from the redesign, using
        # syllables the lesson already curated rather than inventing new
        # combinations it hasn't taught yet.
        practice = lesson.get("practice_syllables") or []
        if practice:
            by_vowel = {}
            by_cho = {}
            for syll in practice:
                try:
                    syl = quiz.syllable_breakdown(syll)
                except Exception:
                    continue
                by_vowel.setdefault(syl.jung, []).append(syl)
                by_cho.setdefault(syl.cho, []).append(syl)
            # Show at most one contrastive row per vowel that has more
            # than one consonant behind it — a single-entry "row" isn't a
            # contrast. Sorted for stable, predictable output rather than
            # dict insertion order.
            rows = [sylls for sylls in by_vowel.values() if len(sylls) > 1]
            if rows:
                print(f"   {styled('Same vowel, different consonant:', BOLD)}")
                for sylls in rows:
                    cells = [(s.text, s.romanization) for s in sylls]
                    jamo_pieces, roman_line, indent = _composition_rows(
                        cells, connector="   ", final_connector="   "
                    )
                    sys.stdout.write(indent)
                    for piece in jamo_pieces:
                        sys.stdout.write(piece)
                    print()
                    print(roman_line)
                print()
            # Axis 2: same consonant, changing vowel — the complementary
            # pattern to Axis 1. Same structure, just grouped by syl.cho
            # instead of syl.jung.
            rows_cho = [sylls for sylls in by_cho.values() if len(sylls) > 1]
            if rows_cho:
                print(f"   {styled('Same consonant, different vowel:', BOLD)}")
                for sylls in rows_cho:
                    cells = [(s.text, s.romanization) for s in sylls]
                    jamo_pieces, roman_line, indent = _composition_rows(
                        cells, connector="   ", final_connector="   "
                    )
                    sys.stdout.write(indent)
                    for piece in jamo_pieces:
                        sys.stdout.write(piece)
                    print()
                    print(roman_line)
                print()
    elif batchim_pron:
        print(f"\n{styled('📋 Batchim Reference Table', BOLD, CYAN)}")
        for letter, pron in batchim_pron.items():
            print(f"   {styled(letter, BOLD)}  —  {pron}")
    elif batchim_rules:
        print(f"\n{styled('📋 Batchim Merger Reference', BOLD, CYAN)}")
        for group, rule in batchim_rules.items():
            print(f"   {styled(group, BOLD)}  —  {rule}")
    elif vocabulary:
        print(f"\n{styled('📋 Vocabulary Reference', BOLD, CYAN)}")
        for entry in vocabulary:
            print(f"   {styled(entry['word'], BOLD)}  —  {entry['meaning']}")
            print(f"        {entry.get('breakdown', '')}")
    elif block_rules:
        print(f"\n{styled('📋 Syllable Block Layout', BOLD, CYAN)}")
        if block_rules.get("vertical_layout"):
            print(f"   {styled('Vertical vowels', BOLD)} ({', '.join(block_rules.get('vertical_vowels', []))}): {block_rules['vertical_layout']}")
        if block_rules.get("horizontal_layout"):
            print(f"   {styled('Horizontal vowels', BOLD)} ({', '.join(block_rules.get('horizontal_vowels', []))}): {block_rules['horizontal_layout']}")

def print_romanization_key(quiz: HangulQuiz):
    """Print the full jamo → romanization spelling key that read_aloud
    grades typed answers against. Without this, read_aloud effectively
    asked learners to guess an unwritten spelling system (e.g. that ㅓ is
    specifically spelled 'eo', not 'uh' or 'aw')."""
    table = quiz.get_romanization_table()
    consonants = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
    vowels = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
    print(f"\n{styled('🔤 Romanization Key', BOLD, CYAN)}")
    print(f"   {styled('Consonants:', BOLD)}")
    print("   " + "   ".join(f"{l}={table[l]}" for l in consonants if l in table))
    print(f"   {styled('Vowels:', BOLD)}")
    print("   " + "   ".join(f"{l}={table[l]}" for l in vowels if l in table))
    print(f"   {styled('Batchim (final consonant):', BOLD)} appended after a dash using the")
    print(f"   same consonant codes above — e.g. 각 (ㄱ+ㅏ+ㄱ batchim) romanizes as 'ga-g'.")

def run_beginner_intro(quiz: HangulQuiz, lesson: dict):
    """Walk through the current lesson's letters one at a time — letter,
    romanization, pronunciation, stroke order — at the learner's own pace.
    After each letter, a single prompt covers both use cases: press Enter
    to just move on (pure browsing), or type the romanization to try it
    right there (untimed, not scored, no streak/progress impact — this is
    a warm-up, not a quiz). Separate from print_reference_table, which
    stays as a quick all-at-once lookup; this is the slower, guided
    first-pass version for true beginners."""
    letters = lesson.get("letters", [])
    if not letters:
        print(f"\n{styled('This lesson has no individual letters to walk through — try /table instead.', YELLOW)}")
        return

    pronunciation = lesson.get("pronunciation") or {}
    letter_romanization = lesson.get("letter_romanization") or {}
    roman_table = quiz.get_romanization_table()

    # ── Silent-ㅇ discovery sequence (vowel-only lessons only) ──────
    # For lessons where every letter is a bare vowel jamo, show the
    # pattern BEFORE the per-letter walkthrough: a vowel can't stand
    # alone in real writing, so Korean fills the consonant slot with
    # silent ㅇ. The learner sees the same pattern repeat across
    # multiple vowels (ㅇ+ㅏ→아, ㅇ+ㅓ→어, ㅇ+ㅗ→오) before ever
    # building anything — discovering the rule from the pattern, not
    # being told it as a fact in a note.
    is_vowel_only_lesson = all(letter in _VOWEL_JAMO for letter in letters)
    if is_vowel_only_lesson:
        first_letter = letters[0]
        print(f"\n{styled('🔍 Before we begin — a quick discovery:', BOLD, CYAN)}")
        print(f"   Can {styled(first_letter, BOLD)} stand alone as a real Korean syllable?")
        time.sleep(0.8)
        print(f"\n   {styled('Not in real writing.', BOLD, YELLOW)}")
        print(f"   Every syllable needs something in the consonant slot.")
        print(f"   Korean fills that slot with {styled('ㅇ', BOLD)} — silent, just a placeholder.")
        time.sleep(0.6)
        print(f"\n   {styled('Watch the pattern:', CYAN)}")

        # Show up to 3 vowels composed with silent ㅇ
        discovery_letters = letters[:3]
        for vowel in discovery_letters:
            syl = quiz.syllable_breakdown(vowel)
            roman = letter_romanization.get(vowel) or roman_table.get(vowel, "")
            # Build cells showing the silent ㅇ explicitly:
            # (ㅇ, "") + (vowel, roman) → (composed, roman)
            cells = [
                ("ㅇ", ""),
                (vowel, roman),
                (syl.text, syl.romanization),
            ]
            jamo_pieces, roman_line, indent = _composition_rows(cells)
            sys.stdout.write(indent)
            for piece in jamo_pieces:
                sys.stdout.write(piece)
            print()
            print(roman_line)
            time.sleep(0.3)

        # Interactive prompt: ask what they have in common, accept any response
        composed_names = [quiz.syllable_breakdown(v).text for v in discovery_letters]
        print(f"\n   {styled('What do', CYAN)} {', '.join(composed_names)} {styled('all have in common?', CYAN)}")
        try:
            response = input(f"   {styled('>', BOLD)} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{styled('Walkthrough ended early.', YELLOW)}")
            return
        # UNGRADED — accept any response (including blank), no validation
        # The reveal comes AFTER they respond (or press Enter with nothing)
        print(f"\n   {styled('The', GREEN)} {styled('ㅇ', BOLD, GREEN)} {styled('at the front is silent in all of them.', GREEN)}")
        print(f"   {styled('Every vowel needs it, since Korean can' + chr(39) + 't write a bare vowel alone.', GREEN)}")
        time.sleep(0.5)

        print(f"\n{styled('Now let' + chr(39) + 's meet the vowels themselves:', BOLD, GREEN)}")

    print(f"\n{styled('🐣 Beginner Walkthrough', BOLD, GREEN)} — {len(letters)} letter(s) in this lesson")
    print(f"{styled('Press Enter to move on, or type the romanization to try it. Type /skip to end early.', CYAN)}")

    for i, letter in enumerate(letters, start=1):
        roman = letter_romanization.get(letter) or roman_table.get(letter, "")
        pron = pronunciation.get(letter, "")

        print(f"\n{styled(f'Letter {i} of {len(letters)}', BOLD)}\n")
        reveal_letter(letter)
        if roman:
            print(f"      romanizes as: {styled(roman, BOLD)}")
        quirk = POSITIONAL_QUIRKS.get(letter, "")
        if quirk:
            print(f"      {styled('⚡ ' + quirk, BOLD, YELLOW)}")
        if pron:
            print(f"      sounds like: {pron}")

        try:
            response = input(f"\n{styled('[Enter=next, or type romanization]', CYAN)} {styled('>', BOLD)} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{styled('Walkthrough ended early.', YELLOW)}")
            return

        if response.lower() in ('/skip', 'skip'):
            print(f"{styled('Walkthrough ended early.', YELLOW)}")
            return
        if response:
            if response.lower() == roman.lower():
                print(f"   {styled('✅ Correct!', GREEN)}")
            else:
                msg = f'Not quite — {letter} is "{roman}".'
                print(f"   {styled(msg, YELLOW)} (This one's just for practice, no score kept.)")

    print(f"\n{styled('🐣 Walkthrough complete!', GREEN)} Type /table for a quick-reference recap anytime, or just answer the next question to start quizzing.")


def print_question(q: QuizQuestion, quiz: HangulQuiz = None):
    """Display a question with styling.

    build_syllable and missing_vowel already carry a composition inside
    their prompt string (e.g. "Consonant: ㄴ | Vowel: ㅏ", or
    "ㄷ + ? = di") — this used to render as plain labeled text instead of
    the visual composition row (ㄴ + ㅏ → 나) the title screen and
    reference table now use everywhere else. confusion_drill had a
    related but distinct gap: the pair it drills (target vs. other) was
    already correctly selected by the engine, but "other" only ever
    appeared as a romanization string inside the prompt/hint and as MCQ
    choices — never as a composed block shown alongside target, so the
    side-by-side contrast never actually rendered. With quiz passed in,
    all three modes render through _composition_rows instead of
    q.prompt's plain text, so the visual doesn't disappear the moment a
    real quiz question starts. Every other mode is unchanged — same
    q.prompt string as before — and if quiz isn't passed (or breakdown
    fails) this falls straight back to the old plain-text rendering, so
    nothing regresses if it's ever called the old way.

    missing_vowel needs particular care: q.letter is the FULL target
    syllable (e.g. '디'), whose decomposition includes the very vowel
    being asked about — so this branch shows only the consonant and a
    '?' placeholder, never the composed block or the vowel jamo, exactly
    like the plain-text prompt it replaces ("ㄷ + ? = di") did.
    confusion_drill has no such leak concern — the task is telling two
    known blocks apart, not guessing a hidden piece — so both are shown
    in full."""
    mode_icons = {
        "spell": "🔤", "read_aloud": "🔊", "match_sound": "🎯",
        "build_syllable": "🧩", "missing_vowel": "🔍",
        "batchim_challenge": "📦", "confusion_drill": "⚡",
        "word_contrast": "📖", "sudden_death": "💀", "nonword_decode": "🔣"
    }
    mode_labels = {"read_aloud": "Sound It Out", "nonword_decode": "Decode"}
    icon = mode_icons.get(q.mode, "❓")
    label = mode_labels.get(q.mode, q.mode.replace('_', ' ').title())
    print(f"\n{icon} {styled(label, CYAN)}")

    rendered = False
    if quiz is not None and q.mode in ("build_syllable", "missing_vowel", "confusion_drill", "word_contrast") and q.letter:
        try:
            syl = quiz.syllable_breakdown(q.letter)
            if q.mode == "build_syllable":
                # Safe to show cho/jung/(jong) — that's the given puzzle —
                # but not the composed result, which is the answer. Cut
                # syl.components before its last (whole-block) entry.
                given = syl.components[:-1]
                print(f"   Build the syllable for **{syl.romanization}**")
                jamo_pieces, roman_line, indent = _composition_rows(
                    given, connector=" + ", final_connector=" + "
                )
                sys.stdout.write(indent)
                for piece in jamo_pieces:
                    sys.stdout.write(piece)
                print("   =   ?")
                print(roman_line)
                rendered = True
            elif q.mode == "missing_vowel":
                # Only the consonant is safe to show — jung IS the answer,
                # and the composed block would give it away via its shape.
                roman = quiz._hangul_to_roman_hint(q.letter)
                cho_roman = _initial_roman(syl.cho) if syl.cho != "ㅇ" else ""
                w = max(_vwidth(syl.cho), _vwidth(cho_roman))
                jamo_line = (f"   {styled(_pad_to(syl.cho, w), BOLD, CYAN)} + "
                             f"{styled('?', BOLD, YELLOW)}   =   {styled(roman, BOLD, GREEN)}")
                roman_line = f"   {_pad_to(cho_roman, w)}   ?"
                print(jamo_line)
                print(roman_line)
                print("   Which vowel completes it?")
                rendered = True
            elif q.mode == "confusion_drill" and q.other:
                # Genuinely contrastive render (the gap identified against
                # §20 of the design review): previously the drilled pair
                # only appeared as a romanization string inside the prompt
                # and as two of the four MCQ choices — never as composed
                # blocks shown side by side. Both blocks are safe to show
                # in full here (unlike build_syllable/missing_vowel above):
                # the task is "which of these two is {roman}", not "guess
                # the hidden piece", so showing both doesn't hand over the
                # answer — the learner still has to match sound to shape.
                other_syl = quiz.syllable_breakdown(q.other)
                pair_cells = [(syl.text, syl.romanization),
                              (other_syl.text, other_syl.romanization)]
                jamo_pieces, roman_line, indent = _composition_rows(
                    pair_cells, connector="     ", final_connector="     "
                )
                print(f"   {styled('⚠️ Confusion drill', BOLD, YELLOW)} — "
                      f"which one is **{syl.romanization}**?")
                sys.stdout.write(indent)
                for piece in jamo_pieces:
                    sys.stdout.write(piece)
                print()
                print(roman_line)
                rendered = True
            elif q.mode == "word_contrast" and q.contrast_type == "lexical_minimal_pair" and q.other:
                # Rendering POLICY gated on contrast_type, not just mode —
                # this is the actual point of carrying contrast_type on
                # the QuizQuestion at all. lexical_minimal_pair is the
                # only contrast_type this branch knows how to render as a
                # bare composed block: two ordinary standalone words,
                # neither needing a grammatical host (see
                # word_contrasts.json's verification notes on 개/게 and
                # 손/선). lexical_vs_grammar_form has its OWN branch below
                # (host-context / example-sentence rendering) precisely
                # because a hosted form like 도 rendered as a bare block
                # would misrepresent it as a standalone word — the exact
                # mistake flagged when 더/도 was first considered for the
                # seed set. Anything still unrecognized falls through to
                # plain q.prompt.
                other_syl = quiz.syllable_breakdown(q.other)
                target_syl = quiz.syllable_breakdown(q.letter)
                if q.direction == "word_to_meaning":
                    # Show the target's composed block; ask what it means.
                    # Not showing "other" here at all — the choices list
                    # already carries both glosses, and showing the OTHER
                    # Hangul form would just be visual noise for a
                    # question that isn't asking the learner to compare
                    # two Hangul shapes.
                    print(f"   {styled(target_syl.text, BOLD, CYAN)}"
                          f"  ({styled(target_syl.romanization, BOLD, GREEN)})")
                    print("   ...means?")
                else:
                    # meaning_to_word: show both composed blocks side by
                    # side, unlabeled as to which is correct — same
                    # non-leaking pattern as confusion_drill above. The
                    # learner has to match the named meaning to the right
                    # shape, not just recognize a lone block.
                    pair_cells = [(target_syl.text, target_syl.romanization),
                                  (other_syl.text, other_syl.romanization)]
                    jamo_pieces, roman_line, indent = _composition_rows(
                        pair_cells, connector="     ", final_connector="     "
                    )
                    print(f"   {q.prompt}")
                    sys.stdout.write(indent)
                    for piece in jamo_pieces:
                        sys.stdout.write(piece)
                    print()
                    print(roman_line)
                rendered = True
            elif (q.mode == "word_contrast" and q.contrast_type == "lexical_vs_grammar_form"
                  and q.other and q.example_ko and q.other_example_ko):
                # Host-context rendering for a contrast_type where at
                # least one side (a particle like 도) is never grammatical
                # as a bare standalone word. Reusing the composed-block
                # branch above for this would be the exact mistake this
                # whole branch exists to avoid — so instead of a bare
                # block, the target is shown highlighted INSIDE a real
                # example sentence (example_ko/example_en, already
                # required to exist for this entry to be selected at all
                # — see _entry_renderable). _highlight_in_sentence fails
                # closed (returns None) if the target doesn't appear
                # exactly once in its own sentence; this branch falls
                # back to the plain sentence, unhighlighted, rather than
                # silently mis-highlighting or crashing — the sentence
                # itself is still correct and useful even without the
                # visual emphasis.
                target_line = (_highlight_in_sentence(q.example_ko, q.letter)
                                or q.example_ko)
                if q.direction == "word_to_meaning":
                    # Only the target's sentence — showing "other"'s
                    # sentence here would be the same kind of unneeded
                    # noise flagged for the composed-block branch above;
                    # the choices list already carries both glosses.
                    print(f"   {target_line}")
                    print(f"   {styled(q.example_en, CYAN)}")
                    print("   ...the highlighted word means?")
                else:
                    # meaning_to_word: both example sentences, each with
                    # its own word highlighted, unlabeled as to which is
                    # correct — same non-leaking pattern as
                    # confusion_drill and the composed-block branch above.
                    # This is what actually gives the grammar context: the
                    # learner sees 도 attached to a noun and 더 standing
                    # in front of a verb, not two words presented as if
                    # they behaved the same way.
                    other_line = (_highlight_in_sentence(q.other_example_ko, q.other)
                                  or q.other_example_ko)
                    print(f"   {q.prompt}")
                    print(f"   {target_line}")
                    print(f"   {other_line}")
                rendered = True
        except Exception:
            pass  # fall through to plain q.prompt below

    # nonword_decode: prompt is already fully composed by the engine
    # (includes the "not a real word" framing), so just print it as-is.
    if q.mode == "nonword_decode":
        print(f"   {q.prompt}")
        rendered = True

    if not rendered:
        print(f"   {q.prompt}")

    if q.choices:
        labels = ['A', 'B', 'C', 'D']
        for label, choice in zip(labels, q.choices):
            print(f"     {label}) {choice}")
        # More modes now carry a choices list (not just the original MC
        # ones), so it's worth spelling out that typing the real answer
        # directly still works too — this isn't a forced multiple-choice.
        print(f"   {styled('(type the answer directly, or answer with a letter)', CYAN)}")
    # Hints used to print automatically here, which made the /hint command
    # pointless — there was nothing left to reveal. Now we just point at
    # /hint and let the learner ask for it if they want it.
    if q.hint:
        print(f"   {styled('💡 Type /hint if you want a hint.', YELLOW)}")

MODE_ALIASES = {
    "spell": "spell",
    "read": "read_aloud", "read_aloud": "read_aloud",
    "match": "match_sound", "match_sound": "match_sound",
    "build": "build_syllable", "build_syllable": "build_syllable",
    "vowel": "missing_vowel", "missing_vowel": "missing_vowel",
    "batchim": "batchim_challenge", "batchim_challenge": "batchim_challenge",
    "confusion": "confusion_drill", "confusion_drill": "confusion_drill",
    "contrast": "word_contrast", "word_contrast": "word_contrast",
    "auto": None, "random": None,
}

KNOWN_ACTIONS = {
    'q', 'quit', 'exit', 'help', 'roman', 'romanize', 'romanization',
    'stats', 'lessons', 'lesson', 'mode', 'mnemonic', 'talk',
    'template', 'konglish', 'kspell', 'hint', 'skip', 'intro', 'table',
    'alphabet',
}

def _advance_and_show(quiz: HangulQuiz) -> dict:
    """Run complete_lesson (which marks the current lesson done and bumps
    current_lesson) and show the lesson the learner lands on next, its
    intro/note and reference table. Returns that new lesson_info so the
    caller can keep its own 'lesson' variable in sync."""
    msg = quiz.complete_lesson()
    new_info = quiz.start_lesson(quiz.progress["current_lesson"])
    print(f"\n{styled('📖 ' + msg, BOLD)}")
    print_lesson_intro(new_info.get("introduction", ""), new_info.get("note", ""))
    print_reference_table(quiz, new_info)
    return new_info


def _offer_advance(quiz: HangulQuiz, lesson_id: int):
    """Called the moment a lesson tips over the mastery bar. Congratulates,
    then either finishes the curriculum (last lesson) or offers to move to
    the next one. Returns the new lesson_info if the learner advanced, or
    None if they declined or this was the final lesson."""
    total = len(quiz.curriculum["lessons"])
    m = quiz.lesson_mastery(lesson_id)
    print(f"\n{styled('🎉 Lesson mastered!', BOLD, GREEN)} "
          f"You've got {m['mastered_count']} of {m['pool_size']} solid.")

    if lesson_id >= total:
        # Final lesson — mark it done and celebrate the whole curriculum.
        quiz.complete_lesson()
        print(f"{styled('🏆 That was the final lesson — you have read your way through the entire Hangul curriculum! 축하합니다! 🏆', BOLD, GREEN)}")
        print(f"{styled('Keep drilling any lesson with /lesson N, or check /stats.', CYAN)}")
        return None

    try:
        ans = input(f"\n{styled(f'Move on to Lesson {lesson_id + 1}? [Y/n] ', CYAN)}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        ans = "n"
    if ans in ("", "y", "yes"):
        return _advance_and_show(quiz)
    print(f"{styled('No rush — staying here. Type /lessons to see all lessons, or /lesson N to jump to one whenever you want.', YELLOW)}")
    return None


def interactive_loop(quiz: HangulQuiz, args, lesson_info: dict):
    """Main interactive quiz loop."""
    print(f"\n{styled('🇰🇷 Hangul Tutor', BOLD, GREEN)}")
    engine_label = f"Ollama: {summarize_models()}" if USE_LLM else "Offline (no LLM needed)"
    print(f"{engine_label} | Lesson: {quiz.current_lesson['title']}")
    print(f"Type {styled('/help', CYAN)} for commands, {styled('/quit', RED)} to exit")

    # --mode locks the quiz to a single question type; None means auto-pick
    locked_mode = args.mode
    if locked_mode:
        print(f"Mode locked to: {styled(locked_mode, CYAN)}")

    # Show the lesson's teaching content (e.g. the ㅇ-placeholder rule) —
    # this data already existed in curriculum.json but was never displayed.
    # Use lesson_info (from quiz.start_lesson()), NOT the raw
    # quiz.current_lesson dict — only lesson_info has computed fields like
    # letter_romanization; the raw curriculum entry doesn't carry those.
    lesson = lesson_info
    print_lesson_intro(lesson.get("introduction", ""), lesson.get("note", ""))
    print_reference_table(quiz, lesson)

    # Show a mnemonic for the first letter as a warm welcome. Offline this
    # is instant (hardcoded table); only with --use-llm, and only for a
    # letter without a stock mnemonic, does it make a blocking model call —
    # in which case say so, since that can take a moment on a cold start.
    if "letters" in lesson and lesson["letters"]:
        first_letter = lesson["letters"][0]
        if USE_LLM and first_letter not in ALPHABET_MNEMONICS:
            print(f"\n{styled('🧠 Generating a mnemonic...', YELLOW)} (first response from a model can take a moment)")
        mnemonic = mnemonic_for(first_letter)
        print(f"\n{styled('🧠 Mnemonic for', YELLOW)} {styled(first_letter, BOLD)}:")
        print(f"   {mnemonic}")

    waiting_for_question = not args.sudden_death
    current_question = None
    sudden_death_lives = 3
    # Lesson ids the learner has already been offered advancement on and
    # said "not yet" to — so a mastered-but-not-advanced lesson doesn't
    # re-prompt after every single subsequent correct answer.
    mastery_offered = set()

    # Wall-clock time when the current question was first displayed —
    # used to compute response_time_ms for the per-item EMA. Set only
    # inside the is_new_question branch (same scope as current_question
    # itself), so it persists through /hint passes without being reset.
    question_shown_at = None

    while True:
        is_new_question = False

        if args.sudden_death:
            if sudden_death_lives <= 0:
                print(f"\n{styled('💀 SUDDEN DEATH — GAME OVER!', RED)}")
                print(f"   Streak: {quiz.session_streak} | Score: {quiz.session_correct}/{quiz.session_total}")
                break
            if current_question is None:
                current_question = quiz.next_question(mode="sudden_death" if sudden_death_lives == 1 else locked_mode)
                is_new_question = True

        if current_question is None:
            # Determine question mode based on progress
            if quiz.session_streak >= 5 and quiz.session_streak % 5 == 0:
                # Every 5-correct streak, reward with a readable snippet.
                # Offline (default) this is an instant template sentence
                # built from real words the learner can spell; with
                # --use-llm it tries a live model sentence first and falls
                # back to the same template if that fails.
                known = quiz.get_mastered_syllables(min_confidence=3)
                if len(known) >= 3:
                    # Only the LLM path actually builds a sentence; the
                    # offline template path returns a single exposure word, so
                    # a "Building a sentence" banner there would be a lie.
                    if USE_LLM:
                        print(f"\n{styled('📖 Building a sentence from what you know...', YELLOW)}")
                    sentence = generate_mini_sentence(known, quiz) if USE_LLM else None
                    turn_mode = "read_translate" if sentence else None
                    if not sentence:
                        turn = build_template_sentence(known, quiz)
                        if turn and turn.get("korean"):
                            eng = turn.get("english")
                            sentence = f"{turn['korean']}  —  {eng}" if eng else turn["korean"]
                            turn_mode = turn.get("mode")
                    if sentence:
                        # vocab_exposure means build_template_sentence
                        # found a real word the learner can spell, but
                        # deliberately did NOT wrap it in grammar
                        # (이것은/입니다 etc.) the learner hasn't mastered
                        # yet — see build_template_sentence's docstring.
                        # Framing this as "you can now read" would repeat
                        # exactly the honesty problem that check exists
                        # to prevent, so exposure content gets its own,
                        # more honest framing instead.
                        if turn_mode == "vocab_exposure":
                            print(f"\n{styled('📖 A real Korean word you can already spell:', GREEN)}")
                        else:
                            print(f"\n{styled('📖 You can now read:', GREEN)}")
                        print(f"   {sentence}")
                    else:
                        # Previously this just trailed off with no
                        # resolution — "Building..." printed, then
                        # silence, looking like the app hung or forgot.
                        print(f"   {styled('(Not enough combinable syllables yet — keep practicing!)', YELLOW)}")
            current_question = quiz.next_question(mode=locked_mode)
            is_new_question = True

        # Only redraw the full question card when it's actually a NEW
        # question — previously this ran every single loop pass, so
        # something like /hint (which doesn't advance the question) would
        # print the hint and then immediately redraw the whole card right
        # under it, looking like the question had just reset. The card is
        # already visible a few lines up in scrollback; no need to force
        # it again for commands that don't change what's being asked.
        if is_new_question:
            print_question(current_question, quiz)
            question_shown_at = time.time()

        # Get user input
        try:
            user_input = input(f"\n{styled('>', BOLD)} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{styled('👋 안녕히 가세요! (Goodbye!)', GREEN)}")
            break

        # Blank Enter: don't grade it as a wrong answer (and don't feed ""
        # into quiz.answer(), which an old _compose_bare_vowel bug turned
        # into "ㅏ" and minted phantom confusions). Re-prompt with a nudge.
        if not user_input:
            if current_question:
                print(f"{styled('(blank — /hint for a hint, /skip to reveal the answer)', YELLOW)}")
            continue

        # Bare lesson number ("5", "5.") → jump to that lesson, so the
        # /lessons list is actually navigable. Answers are never bare digits
        # (Hangul, romanization, or A-D), so this can't collide with a real
        # answer; out-of-range ids are caught by the /lesson handler.
        _num = user_input.strip(" .)():-")
        if _num.isdigit():
            user_input = f"/lesson {_num}"

        # Handle commands
        if user_input.startswith('/'):
            cmd = user_input[1:].lower().split()
            if not cmd:
                continue
            action = cmd[0]

            if action in ('q', 'quit', 'exit'):
                print(f"\n{styled('👋 안녕히 가세요! (Goodbye!)', GREEN)}")
                break

            elif action == 'help':
                print(f"""
{styled('Commands:', BOLD)}
  {styled('/stats', CYAN)}    — Show your progress
  {styled('/lessons', CYAN)}  — List all lessons
  {styled('/lesson N', CYAN)} — Jump to lesson N
  {styled('/mode NAME', CYAN)}— Lock quiz mode (spell, read, match, build, vowel, batchim, confusion, auto)
  {styled('/alphabet', CYAN)} — Walk through all 24 basic letters, consonants then vowels
  {styled('/intro', CYAN)}    — Walk through this lesson's letters one at a time (true-beginner mode)
  {styled('/table', CYAN)}    — Show this lesson's reference table again
  {styled('/roman', CYAN)}    — Show the full romanization key (what "read aloud" grades you against)
  {styled('/mnemonic X', CYAN)}— Get a mnemonic for letter X
  {styled('/talk', CYAN)}     — Try reading a Korean sentence (uses your mastered syllables)
  {styled('/template', CYAN)} — Same, but instant (no LLM)
  {styled('/konglish', CYAN)} — Decode a Konglish word (sound it out, guess English)
  {styled('/kspell', CYAN)}   — Spell an English word in Hangul
  {styled('/quit', CYAN)}     — Exit
""")

            elif action in ('roman', 'romanize', 'romanization'):
                print_romanization_key(quiz)

            elif action == 'stats':
                summary = quiz.get_progress_summary()
                print(f"\n{styled('📊 Your Progress', BOLD)}")
                for k, v in summary.items():
                    if k == 'top_confusions':
                        if v:
                            print(f"   Confused pairs: {', '.join(c['pair'] for c in v)}")
                    else:
                        print(f"   {k.replace('_', ' ').title()}: {v}")

            elif action == 'lessons':
                print(f"\n{styled('📚 Lessons:', BOLD)}")
                for l in quiz.list_lessons():
                    mark = styled('✓', GREEN) if l['completed'] else ''
                    print(f"   {l['id']:2}. {l['title']} {mark}")
                print(f"{styled('   Jump to one with /lesson N (e.g. /lesson 5).', YELLOW)}")

            elif action == 'lesson' and len(cmd) > 1:
                try:
                    lid = int(cmd[1])
                    info = quiz.start_lesson(lid)
                    title = info['title']
                    print(f"\n{styled(f'📖 Lesson {lid}: {title}', BOLD)}")
                    print(f"   {info['description']}")
                    print_lesson_intro(info.get('introduction', ''), info.get('note', ''))
                    print_reference_table(quiz, info)
                    # Keep the loop's 'lesson' variable in sync — previously
                    # only the local 'info' was updated here, so /intro and
                    # /table (which both read the outer 'lesson' var) would
                    # keep showing whichever lesson was active at the start
                    # of the session, not the one just jumped to.
                    lesson = info
                    # Previously this didn't touch current_question, so
                    # jumping lessons left one leftover question from
                    # whatever lesson/mode was active before — mismatched
                    # against the lesson intro that was just printed.
                    current_question = None
                except (ValueError, IndexError):
                    print(f"{styled('Invalid lesson number', RED)}")

            elif action == 'intro':
                run_beginner_intro(quiz, lesson)

            elif action == 'alphabet':
                run_alphabet_intro(quiz)

            elif action == 'table':
                print_reference_table(quiz, lesson)

            elif action == 'mode':
                choice = cmd[1].lower() if len(cmd) > 1 else ""
                if choice in MODE_ALIASES:
                    locked_mode = MODE_ALIASES[choice]
                    current_question = None  # force new question in the new mode
                    label = locked_mode or "auto (random)"
                    print(f"{styled(f'Mode: {label}', CYAN)}")
                else:
                    print(f"{styled('Usage: /mode <spell|read|match|build|vowel|batchim|confusion|auto>', RED)}")

            elif action == 'mnemonic':
                letter = cmd[1] if len(cmd) > 1 else ""
                if not letter:
                    print(f"{styled('Usage: /mnemonic ㄱ', RED)}")
                else:
                    mnemonic = mnemonic_for(letter)
                    print(f"\n{styled(f'🧠 Mnemonic for {letter}:', YELLOW)}")
                    print(f"   {mnemonic}")

            elif action == 'talk':
                print(f"\n{styled('💬 Generating a Korean sentence...', CYAN)}")
                turn = generate_conversation_turn(quiz, mode="read_translate",
                                                   use_llm=USE_LLM)
                if turn:
                    turn_mode = turn.get("mode")
                    if turn_mode in ("vocab_exposure", "syllable_practice"):
                        # Single-word / bare-syllable EXPOSURE (the offline or
                        # LLM-failed fallback), not a sentence to translate.
                        # Show it honestly — no fake "translate this", no
                        # grading, no streak bump. The old path graded it
                        # always-correct via check_conversation_answer's
                        # fall-through, silently inflating the streak.
                        label = ("📖 A real Korean word you can already spell:"
                                 if turn_mode == "vocab_exposure"
                                 else "📖 Practice reading these syllables:")
                        print(f"\n{styled(label, GREEN)}")
                        print(f"   {styled(turn['korean'], BOLD)}")
                        if turn.get("english"):
                            print(f"   {styled(turn['english'], YELLOW)}")
                    else:
                        method = turn.get('method', 'llm')
                        method_labels = {'template': '📋 Template', 'tatoeba': '📚 Real sentence', 'llm': '🤖 LLM'}
                        label = method_labels.get(method, '🤖 LLM')
                        print(f"\n{styled(f'{label} — read this Korean:', CYAN)}")
                        print(f"   {styled(turn['korean'], BOLD)}")
                        print(f"\n   {styled('Translate to English:', YELLOW)}")
                        user = input(f"{styled('>', BOLD)} ").strip()
                        result = check_conversation_answer(user, turn, quiz)
                        print(f"   {result['feedback']}")
                        if result.get('correct'):
                            quiz.session_streak += 1
                        else:
                            quiz.session_streak = 0
                else:
                    print(f"   {styled('Not enough syllables mastered yet — keep practicing!', YELLOW)}")

            elif action == 'template':
                mastered = quiz.get_mastered_syllables(min_confidence=3)
                turn = build_template_sentence(mastered, quiz)
                # build_template_sentence now only ever returns an exposure
                # turn (vocab_exposure / syllable_practice) — a single word or
                # bare syllables, never a read_translate sentence. Show it
                # honestly: no "translate this" prompt, no grading.
                turn_mode = turn.get("mode")
                label = ("📖 A real Korean word you can already spell:"
                         if turn_mode == "vocab_exposure"
                         else "📖 Practice reading these syllables:")
                print(f"\n{styled(label, GREEN)}")
                print(f"   {styled(turn['korean'], BOLD)}")
                if turn.get("english"):
                    print(f"   {styled(turn['english'], YELLOW)}")

            elif action == 'konglish':
                q = quiz.konglish_question()
                print_question(q)
                # Loop so /hint can be typed before committing to an answer —
                # previously this was a single blocking input() with no
                # chance to ask for the hint that print_question pointed to.
                while True:
                    user = input(f"\n{styled('>', BOLD)} ").strip()
                    if user.lower() in ('/hint', '/h') and q.hint:
                        print(f"   {styled('💡', YELLOW)} {q.hint}")
                        continue
                    break
                # Exact (case/space-insensitive) match. The old substring
                # test marked an empty Enter or a stray single letter
                # correct — "" is "in" every string, and "a" is in
                # "camera" — so it's a real comparison now, and empty input
                # is always wrong.
                ans = " ".join(user.lower().split())
                if ans and ans == " ".join(q.correct_answer.lower().split()):
                    print(f"   ✅ Yes! **{q.letter}** = {q.correct_answer}")
                else:
                    print(f"   Not quite — it's **{q.correct_answer}** (sounds like: {q.letter})")

            elif action == 'kspell':
                q = quiz.konglish_spell_question()
                print_question(q)
                while True:
                    user = input(f"\n{styled('>', BOLD)} ").strip()
                    if user.lower() in ('/hint', '/h') and q.hint:
                        print(f"   {styled('💡', YELLOW)} {q.hint}")
                        continue
                    break
                # This grades outside the main quiz.answer() path, so it
                # needs its own call to the same letter-resolution helper
                # — otherwise typing 'B' here would just be marked wrong
                # instead of resolving to the choice it refers to.
                resolved = quiz.resolve_choice(user, q.choices)
                if resolved == q.correct_answer:
                    print(f"   ✅ Perfect! **{resolved}** is right.")
                else:
                    print(f"   ❌ The Hangul spelling is **{q.correct_answer}**")

            elif action == 'hint' and current_question:
                print(f"   {styled('💡', YELLOW)} {current_question.hint}")

            elif action == 'skip' and current_question:
                print(f"   Answer was: {styled(current_question.correct_answer, GREEN)}")
                current_question = None

            elif action in ('hint', 'skip'):
                # Recognized command, just not applicable right now — distinct
                # from a genuinely unknown command (handled below).
                print(f"{styled('No active question to do that with.', YELLOW)}")

            elif action not in KNOWN_ACTIONS:
                # Previously fell through silently — e.g. '/12.' instead of
                # '/lesson 12' just reprinted the same question with no sign
                # anything went wrong. Now it says so.
                print(f"{styled(f'Unknown command: /{action}', RED)} — type /help to see what's available.")

            continue

        # Process answer
        if current_question:
            # Compute response time — elapsed since the question was
            # displayed. Falls back to None (not measured) if
            # question_shown_at was never set (e.g. a question that
            # somehow bypassed the display branch). None means the
            # timing update is skipped entirely in _record_learner_item.
            if question_shown_at is not None:
                elapsed_ms = (time.time() - question_shown_at) * 1000
            else:
                elapsed_ms = None
            result = quiz.answer(user_input, current_question, response_ms=elapsed_ms)
            print(f"   {result.feedback}")

            # quiz.answer() already updates quiz.session_streak internally
            # (+1 on correct, reset to 0 on wrong) — this used to ALSO
            # bump it here, so every correct answer counted twice and the
            # displayed streak ran at double speed. Sudden-death lives and
            # the encouragement trigger still need handling here; the
            # streak number itself doesn't.
            if result.correct:
                if args.sudden_death:
                    sudden_death_lives += 1
                # Periodic encouragement — an optional Ollama flourish, so
                # it only runs with --use-llm (silent otherwise, no hang).
                # Accuracy is real session accuracy now; it used to be
                # streak/streak, i.e. always 100%, making the message wrong.
                if USE_LLM and quiz.session_streak > 0 and quiz.session_streak % 7 == 0:
                    print(f"\n{styled('🌟 Generating encouragement...', YELLOW)}")
                    accuracy = 100 * quiz.session_correct / max(1, quiz.session_total)
                    enc = generate_encouragement(quiz.session_streak, accuracy)
                    if not enc.startswith('['):
                        print(f"\n{styled('🌟', YELLOW)} {enc}")
            else:
                if args.sudden_death:
                    sudden_death_lives -= 1

            if args.sudden_death:
                print(f"   {styled(f'❤️ Lives: {sudden_death_lives}', RED if sudden_death_lives == 1 else '')}")
            else:
                print(f"   {styled(f'🔥 Streak: {quiz.session_streak}', GREEN if quiz.session_streak > 3 else '')}")

            # Lesson progression (normal mode only). When the active
            # lesson's pool crosses the mastery bar, congratulate once and
            # offer to advance. mastery_offered suppresses re-asking after a
            # "not yet", so the learner isn't nagged on every later answer.
            if result.correct and not args.sudden_death:
                _lid = quiz.current_lesson["id"]
                if (_lid not in quiz.progress["completed_lessons"]
                        and _lid not in mastery_offered
                        and quiz.lesson_mastery(_lid)["is_mastered"]):
                    mastery_offered.add(_lid)
                    _advanced = _offer_advance(quiz, _lid)
                    if _advanced is not None:
                        lesson = _advanced

            current_question = None

    # Save on exit
    quiz.save_progress()
    summary = quiz.get_progress_summary()
    print(f"\n{styled('📊 Session Summary:', BOLD)}")
    print(f"   Correct: {summary['session_score']} ({summary['session_pct']}%)")
    print(f"   Best Streak: {summary['streak_best']}")
    if summary['top_confusions']:
        print(f"   Practice these: {', '.join(c['pair'] for c in summary['top_confusions'])}")

    # Structured lesson-complete block (deterministic — no Ollama call).
    print_lesson_complete(quiz)

# ── Entry point ────────────────────────────────────────────────────────────

def main():
    # Force UTF-8 on standard streams so Hangul renders correctly and does
    # not raise UnicodeEncodeError when output is redirected (e.g. the frozen
    # onefile exe piped to a file falls back to cp1252 otherwise). Harmless on
    # a real console, where Python already uses the Unicode console API.
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr, sys.stdin):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (AttributeError, ValueError, OSError):
                pass
    parser = argparse.ArgumentParser(description="🇰🇷 Hangul Tutor CLI")
    parser.add_argument("--lesson", type=int, default=None, help="Start at lesson N")
    parser.add_argument("--mode", choices=["spell", "read_aloud", "match_sound",
                        "build_syllable", "missing_vowel", "batchim_challenge",
                        "confusion_drill"], help="Lock to a single quiz mode")
    parser.add_argument("--sudden-death", action="store_true", help="One wrong = game over")
    parser.add_argument("--mnemonic", type=str, help="Print a mnemonic for a Hangul letter and exit")
    parser.add_argument("--use-llm", action="store_true",
                        help="Enable optional local-Ollama enrichments: generated mnemonics for "
                             "letters without a stock one, LLM-built sentences, encouragement, and a "
                             "natural-language session summary. Off by default — the app is fully "
                             "functional offline without it.")
    parser.add_argument("--model", type=str, default=None,
                        help="Ollama model for the optional enrichments (default: qwen2.5:1.5b). "
                             "Passing it implies --use-llm. Override individual tasks with "
                             "HANGUL_MODEL_MNEMONIC / _ENCOURAGEMENT / _SENTENCE / _TRANSLATE / "
                             "_SUMMARY env vars.")
    args = parser.parse_args()

    # Enable the optional Ollama path when explicitly asked (--use-llm) or
    # implicitly when a model is named (--model), since naming a model with
    # enrichments off would be a silent no-op.
    global USE_LLM
    USE_LLM = args.use_llm or bool(args.model)

    # Only override the shared fallback if the user actually passed --model —
    # otherwise leave it to HANGUL_OLLAMA_MODEL / HANGUL_MODEL_* env vars.
    if args.model:
        set_default_model(args.model)

    # Quick mnemonic lookup (no quiz)
    if args.mnemonic:
        mnemonic = mnemonic_for(args.mnemonic)
        print(f"Mnemonic for {args.mnemonic}:")
        print(mnemonic)
        return

    # --lesson N is a direct power-user jump — skips the title/menu
    # entirely and goes straight to that lesson, same as before. With no
    # --lesson given, show_start_menu() handles both the fresh-profile
    # and returning-user cases: title screen, then a menu with resume as
    # the one-keystroke default (start_lesson(None) under the hood, same
    # resume-from-progress logic as always) alongside the alphabet
    # walkthrough and lesson list as visible, no-slash-command-needed
    # options — not just a first-run-only prompt.
    quiz = HangulQuiz()
    if args.lesson:
        lesson_info = quiz.start_lesson(args.lesson)
    else:
        lesson_info = show_start_menu(quiz)
    interactive_loop(quiz, args, lesson_info)


if __name__ == "__main__":
    main()
