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

from hangul_quiz_engine import (HangulQuiz, QuizQuestion, _initial_roman, _VOWEL_JAMO,
                                normalize_roman)
from hangul_conversation import (
    generate_conversation_turn, check_conversation_answer, build_template_sentence
)
from hangul_models import get_model, set_default_model, summarize_models
from hangul_rain import launch_rain_mode
from conveyor_game import run_conveyor, make_conveyor_state

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
    best_streak = max(quiz.progress.get("streak_best", 0), quiz.session_best_streak)

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
        # _vwidth, not len: a Hangul value (the Weakest letter) is 2 columns
        # wide, and len() under-counted it, pushing the right border out.
        pad = W - len(label_field) - _vwidth(value) - right_pad
        if pad < 0:
            pad = 0
        val = styled(value, *value_styles) if value_styles else value
        return f"║{label_field}{val}{' ' * (pad + right_pad)}║"

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
        lpad = (W - _vwidth(letters_str)) // 2
        rpad = W - _vwidth(letters_str) - lpad
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
DIM  = "\033[2m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

def styled(text: str, *styles) -> str:
    return ''.join(styles) + text + RESET


_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def md(text: str) -> str:
    """Render the engine's **bold** markers as real terminal bold. The quiz
    engine writes prompts and feedback with Markdown-style **...** (it has
    no terminal knowledge), and they used to reach the screen as literal
    asterisks: '✅ Correct! **가** is right.'"""
    return _MD_BOLD_RE.sub(lambda m: styled(m.group(1), BOLD), text)

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
ALPHABET_CONSONANTS   = ["ㄱ", "ㄴ", "ㄷ", "ㄹ", "ㅁ", "ㅂ", "ㅅ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"]
ALPHABET_VOWELS_BASIC = ["ㅏ", "ㅓ", "ㅗ", "ㅜ", "ㅡ", "ㅣ"]
ALPHABET_VOWELS_Y     = ["ㅑ", "ㅕ", "ㅛ", "ㅠ"]
ALPHABET_VOWELS       = ALPHABET_VOWELS_BASIC + ALPHABET_VOWELS_Y  # kept for any other reader

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
    "ㅂ": "A bucket with two handles sticking up — 'b' for bucket. 🪣",
    "ㅅ": "A mountain summit. ⛰️",
    "ㅇ": "A balloon — round and silent as it floats... until it lands with a boiNG! 🎈",
    "ㅈ": "A person mid-jump, leg kicking out behind. 🤸",
    "ㅊ": "ㅈ with a little hat — cheering 'ch!' Extra stroke = extra puff of air. 🎉",
    "ㅋ": "ㄱ with an extra line — a 'k' that kicks out a puff of air. 🔑",
    "ㅌ": "ㄷ with a lid on top — a 't' with a puff of air, like 'top'. 📦",
    "ㅍ": "Goalposts on a soccer field — a 'p' that puffs, like 'pop'. 🥅",
    "ㅎ": "A head wearing a little top hat — 'h' for hat. 🎩",
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

def _print_banner(glyphs: list, color=None, separator: str = " ", romans: list = None):
    """Print a decorative single-row banner of Hangul glyphs.
    color: a single ANSI code string, or None for plain.
    separator: string between glyphs, default single space.
    romans: if given, prints a muted romanization row underneath, each
    entry left-justified in a 2-char slot to align under the double-width
    Hangul glyphs (e.g. 'r/l' for ㄹ naturally takes the 3-col slot that
    the double-wide Hangul + separator occupy)."""
    line = separator.join(glyphs)
    if color:
        line = styled(line, color, BOLD)
    else:
        line = styled(line, BOLD)
    print(f"\n   {line}")
    if romans:
        roman_line = " ".join(r.ljust(2) for r in romans)
        print(f"   {styled(roman_line, DIM)}")
    print()


def _print_syllable_block_intro():
    """Print the syllable block introduction shown at the vowel transition
    in the alphabet walkthrough. Explains CV block layout visually using
    two compact boxes (가 and 고), aligned CV equations with romanization,
    layout labels, and short notes on letter reshaping and the ㅇ placeholder.
    Kept as a standalone function so it can be called from other entry
    points if needed in future."""

    def compact_box(char, width=9):
        inner = width - 2
        pad = (inner - 2) // 2
        line = "│" + " " * pad + char + " " * (inner - pad - 2) + "│"
        top = "┌" + "─" * inner + "┐"
        bot = "└" + "─" * inner + "┘"
        return [top, line, bot]

    print()
    print(f"   {styled('In Korean, each syllable is written as one compact square — like this:', CYAN)}")
    print()

    left_box  = compact_box("가")
    right_box = compact_box("고")
    gap = "      "
    for l, r in zip(left_box, right_box):
        print("   " + l + gap + r)

    print()
    print("   " + styled(" ㄱ +  ㅏ  =  가", BOLD) + "     " + styled(" ㄱ +  ㅗ  =  고", BOLD))
    print("    g  +  a   =  ga           g  +  o   =  go")
    print()
    print("   consonant left, vowel right     consonant on top, vowel below")
    print()
    print(f"   {styled('💡 Notice how ㄱ takes a different shape in each block — letters', CYAN)}")
    print(f"   {styled('   reshape to fit the square depending on where the vowel sits.', CYAN)}")
    print()
    print("   " + styled("💡 Vowels don't appear alone in Korean. ㅏ is written 아, ㅓ is written 어 —", CYAN))
    print(f"   {styled('   the ㅇ in front is silent, just filling in until a real consonant arrives.', CYAN)}")
    print()


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
    ordered = [
        ("Consonants",   ALPHABET_CONSONANTS,   "🔤"),
        ("Basic Vowels", ALPHABET_VOWELS_BASIC,  "🎵"),
        ("Y-Vowels",     ALPHABET_VOWELS_Y,      "🎵"),
    ]
    total = len(ALPHABET_CONSONANTS) + len(ALPHABET_VOWELS_BASIC) + len(ALPHABET_VOWELS_Y)

    print(f"\n{styled('🇰🇷✨ The Hangul Alphabet ✨🇰🇷', BOLD, GREEN)}")
    intro_line = f"{total} letters — 14 consonants, 10 vowels. Let's meet them all!"
    print(f"{styled(intro_line, CYAN)}")
    print(f"{styled('Press Enter for the next letter, or type its romanization to try it. /skip to jump to lesson picking anytime.', CYAN)}")

    seen = 0
    for section_name, letters, icon in ordered:
        if section_name == "Consonants":
            print(f"\n{styled(f'{icon}  {section_name}', BOLD, YELLOW)}")
            _print_banner(list(ALPHABET_CONSONANTS), color=YELLOW,
                          romans=[roman_table.get(c, "") for c in ALPHABET_CONSONANTS])
        elif section_name == "Basic Vowels":
            # ── Consonants → Vowels transition ───────────────────────
            time.sleep(0.5)
            divider = styled("ㄱ ㄴ ㄷ ㄹ ㅁ ㅂ ㅅ ㅇ ㅈ ㅊ ㅋ ㅌ ㅍ ㅎ", YELLOW, BOLD)
            rule    = styled("─" * 45, YELLOW)
            print(f"\n   {divider}")
            print(f"   {rule}")
            try:
                input(f"\n   {styled('[↵  All 14 consonants done — now see what they can do]', CYAN)}")
            except (EOFError, KeyboardInterrupt):
                return
            # Syllable block intro — bridge between C and V
            _print_syllable_block_intro()
            print(f"\n{styled(f'{icon}  {section_name}', BOLD, YELLOW)}")
            _print_banner(ALPHABET_VOWELS_BASIC, color=CYAN,
                          romans=[roman_table.get(v, "") for v in ALPHABET_VOWELS_BASIC])
        elif section_name == "Y-Vowels":
            # ── Basic Vowels → Y-Vowels transition ───────────────────
            time.sleep(0.5)
            divider = styled("ㅏ ㅓ ㅗ ㅜ ㅡ ㅣ", CYAN, BOLD)
            rule    = styled("─" * 45, CYAN)
            print(f"\n   {divider}")
            print(f"   {rule}")
            try:
                input(f"\n   {styled('[↵  6 vowels down — 4 more to go]', CYAN)}")
            except (EOFError, KeyboardInterrupt):
                return
            print(f"\n{styled(f'{icon}  Y-Vowels', BOLD, YELLOW)}")
            _print_banner(ALPHABET_VOWELS_Y, color=CYAN,
                          romans=[roman_table.get(v, "") for v in ALPHABET_VOWELS_Y])
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
                # A slashed romanization like "r/l" means EITHER spelling is
                # right — roman_variants accepts "r" and "l" (and "r/l").
                if (normalize_roman(response) in quiz.roman_variants(letter)
                        or response.lower() == roman.lower()):
                    print(f"   {styled('✅ Nailed it!', GREEN)}")
                else:
                    msg = f'Close — {letter} is "{roman}". No score kept, just practice!'
                    print(f"   {styled(msg, YELLOW)}")

    print(f"\n{styled('🎉 You have met the whole Hangul alphabet! 🎉', BOLD, GREEN)}")

    # Simple strip banner — composed words only, no jamo row.
    # Meanings revealed on [↵].
    words   = ["하늘", "바람", "소리", "노래", "사랑"]
    SEP     = "   "
    inner   = SEP.join(words)
    # Border width: each Korean glyph is 2 display cols, plus separators and padding
    border_w = sum(2 for _ in "".join(words)) + (len(words) - 1) * len(SEP) + 4
    top  = "╔" + "═" * border_w + "╗"
    mid  = "║  " + inner + "  ║"
    bot  = "╚" + "═" * border_w + "╝"

    print()
    for line in (top, mid, bot):
        print(f"   {styled(line, GREEN, BOLD)}")
    print()

    try:
        input(f"   {styled('[↵]', CYAN)}")
    except (EOFError, KeyboardInterrupt):
        return

    meanings = ["sky", "wind", "sound", "song", "love"]
    print()
    print(f"   {styled(inner, GREEN, BOLD)}")
    # Each word is 2 Hangul blocks = 4 columns, plus the 3-space SEP = a
    # 7-column slot per word; pad each meaning to that slot so it sits
    # directly under its word (padding to 5 + SEP drifted 1 column per word).
    slot = 4 + len(SEP)
    print("   " + styled("".join(f"{m:<{slot}}" for m in meanings).rstrip(), CYAN))
    print()


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
        return quiz.start_lesson(int(choice) if choice else 1)
    except ValueError:
        # Not a number, or no such lesson (e.g. '99') — this used to crash
        # the app before the first question.
        print(f"{styled('No such lesson — starting at Lesson 1.', YELLOW)}")
        return quiz.start_lesson(1)


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
    """Startup banner shown on every launch. Demonstrates Hangul's
    combinatorial logic in two stages:
    1. Animate 한글 from its component jamo (slowed for impact).
    2. A 5x6 CV chart fills in: four C+V+syllable demonstrations at
       gradually accelerating pace, then remaining cells scatter in
       randomly. The chart shows the whole system at a glance before
       the learner has been taught a single letter."""

    # Stage 1: 한글 composition animation
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
            time.sleep(0.15)
        print()
        print(roman_line)
        time.sleep(0.3)
    time.sleep(0.3)
    print(f"\n   {styled('한글', BOLD, GREEN)}  —  \"Hangul\": literally, the great script")
    time.sleep(0.6)

    # Stage 2: CV chart animation
    _title_chart_animation()

    print(styled("\n✨  Learn to read Korean, one letter at a time  ✨", BOLD, GREEN))
    print()


def _title_chart_animation():
    """CV chart reveal for the title screen. Five consonants x six vowels.
    Four C+V+syllable demonstration pairs animate at gradually decreasing
    pace, then remaining cells scatter in randomly."""
    import random

    consonants = list("ㄱㄴㅁㅅㅎ")
    vowels     = list("ㅏㅓㅗㅜㅡㅣ")

    def dw(s):
        w = 0
        for ch in s:
            cp = ord(ch)
            if (0xAC00<=cp<=0xD7A3 or 0x1100<=cp<=0x11FF or 0x3130<=cp<=0x318F):
                w += 2
            else:
                w += 1
        return w

    def compose(cho, jung):
        CHOSEONG  = list("ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ")
        JUNGSEONG = list("ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ")
        try:
            code = 0xAC00 + (CHOSEONG.index(cho)*21*28) + (JUNGSEONG.index(jung)*28)
            return chr(code)
        except ValueError:
            return cho + jung

    def cell(content, *codes):
        s = styled(content, *codes) if codes else content
        return f" {s} "

    def raw_cell(content): return f" {content} "

    # Measure border from template row
    template = "\u2551" + raw_cell("ㄱ") + "\u2502" + "\u2502".join(raw_cell(compose("ㄱ", v)) for v in vowels) + "\u2551"
    row_dw = dw(template)
    pipe_cols = set()
    col = 0
    for ch in template:
        if ch == "\u2502":
            pipe_cols.add(col)
        col += 2 if (0xAC00<=ord(ch)<=0xD7A3 or 0x1100<=ord(ch)<=0x11FF or 0x3130<=ord(ch)<=0x318F) else 1

    def build_hline(left, div, right, fill="\u2550"):
        inner_w = row_dw - 2
        line = left; c = 1
        for _ in range(inner_w):
            line += div if c in pipe_cols else fill
            c += 1
        return line + right

    top   = build_hline("\u2554", "\u2564", "\u2557")
    div   = build_hline("\u255f", "\u253c", "\u2562", "\u2500")
    inner = build_hline("\u255f", "\u253c", "\u2562", "\u2500")
    bot   = build_hline("\u255a", "\u2567", "\u255d")

    revealed_c = set()
    revealed_v = set()
    filled     = set()

    def build_header():
        h = "\u2551" + cell("  ") + "\u2502"
        h += "\u2502".join(cell(vowels[vi], CYAN, BOLD) if vi in revealed_v else raw_cell("  ") for vi in range(len(vowels)))
        return h + "\u2551"

    def build_row(ci):
        cho = consonants[ci]
        c_cell = cell(cho, YELLOW, BOLD) if ci in revealed_c else raw_cell("  ")
        r = "\u2551" + c_cell + "\u2502"
        for vi in range(len(vowels)):
            if (ci, vi) in filled:
                r += cell(compose(cho, vowels[vi]), GREEN, BOLD)
            else:
                r += raw_cell("  ")
            if vi < len(vowels) - 1:
                r += "\u2502"
        return r + "\u2551"

    total_lines = 3 + (2 * len(consonants) - 1) + 1
    CURSOR_UP  = "\033[1A"
    CURSOR_COL = "\033[1G"

    def reprint_line(offset, new_line):
        sys.stdout.write(CURSOR_UP * offset + CURSOR_COL)
        sys.stdout.write(f"   {new_line}\n")
        sys.stdout.write("\n" * (offset - 1))
        sys.stdout.flush()

    def header_offset(): return total_lines - 1

    def row_offset(ci):
        return 1 + (len(consonants) - 1 - ci) * 2 + 1

    # Print initial blank skeleton
    print(f"   {styled(top, GREEN, BOLD)}")
    print(f"   {build_header()}")
    print(f"   {styled(div, GREEN, BOLD)}")
    for ci in range(len(consonants)):
        print(f"   {build_row(ci)}")
        if ci < len(consonants) - 1:
            print(f"   {styled(inner, GREEN, BOLD)}")
    print(f"   {styled(bot, GREEN, BOLD)}")
    time.sleep(0.5)

    # Demonstration pairs with gradually accelerating timings
    demo_pairs = [
        (consonants.index("ㄱ"), vowels.index("ㅏ")),
        (consonants.index("ㄴ"), vowels.index("ㅗ")),
        (consonants.index("ㅁ"), vowels.index("ㅣ")),
        (consonants.index("ㅅ"), vowels.index("ㅜ")),
    ]
    pair_timings = [
        (0.7, 0.7, 1.0),
        (0.5, 0.5, 0.7),
        (0.35, 0.35, 0.5),
        (0.2, 0.2, 0.3),
    ]

    for (ci, vi), (t_c, t_v, t_syl) in zip(demo_pairs, pair_timings):
        revealed_c.add(ci)
        reprint_line(row_offset(ci), build_row(ci))
        time.sleep(t_c)
        revealed_v.add(vi)
        reprint_line(header_offset(), build_header())
        time.sleep(t_v)
        filled.add((ci, vi))
        reprint_line(row_offset(ci), build_row(ci))
        time.sleep(t_syl)

    # Random scatter fill
    remaining = [(ci, vi)
                 for ci in range(len(consonants))
                 for vi in range(len(vowels))
                 if (ci, vi) not in filled]
    random.shuffle(remaining)

    for ci, vi in remaining:
        c_changed = ci not in revealed_c
        v_changed = vi not in revealed_v
        revealed_c.add(ci)
        revealed_v.add(vi)
        filled.add((ci, vi))
        if v_changed:
            reprint_line(header_offset(), build_header())
        if c_changed:
            reprint_line(row_offset(ci), build_row(ci))
        reprint_line(row_offset(ci), build_row(ci))
        time.sleep(0.07)

    time.sleep(0.5)


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


# Retained as a public fallback — currently not called internally; print_lesson_intro_rich handles all three call sites.
def print_lesson_intro(introduction: str = "", note: str = ""):
    """Print a lesson's 'introduction' and/or 'note' text, if it has any.
    These carry real teaching content (e.g. the ㅇ-placeholder rule) that
    would otherwise never reach the screen."""
    if introduction:
        print(f"\n{styled('📘', CYAN)} {introduction}")
    if note:
        print(f"\n{styled('📝 Note:', YELLOW)} {note}")

def _extract_layout_example(layout_str: str) -> str:
    """Extract the example trio from a block_rules layout string.
    'C on left, V on right (e.g., ㄱ + ㅏ = 가)' → 'ㄱ + ㅏ = 가'
    Returns empty string if pattern not found."""
    import re
    m = re.search(r'e\.g\.,\s*(.+?)\)', layout_str)
    return m.group(1).strip() if m else ""

def print_lesson_intro_rich(lesson: dict, quiz):
    """Rich animated lesson intro for lessons with structured teaching data.
    Falls back to print_lesson_intro for lessons without it."""
    print()
    print(styled(f"── Lesson {lesson['id']}: {lesson['title']} ──", BOLD, CYAN))
    print(f"   {styled(lesson.get('description', ''), DIM)}")
    time.sleep(0.5)

    introduction = lesson.get("introduction", "")
    if introduction:
        print(introduction)
        time.sleep(0.6)

    letters = lesson.get("letters") or []
    # Every lesson's note is real teaching content (e.g. Lesson 11's
    # "곧 and 곳 both sound like 'got'") — it used to be shown only for
    # lessons that introduce new letters.
    note = lesson.get("note", "")
    if note:
        print(f"\n{styled('📝 Note:', YELLOW)} {note}")

    # Block-building rules are shown only for lessons that are ABOUT blocks
    # (no new letters). Lesson 1 also carries block_rules, but its examples
    # use ㄱ, which isn't taught until Lesson 2.
    block_rules = (lesson.get("block_rules") or {}) if not letters else {}
    if block_rules:
        print(styled("How syllable blocks are built:", YELLOW))
        time.sleep(0.3)
        for key in ("vertical_layout", "horizontal_layout"):
            layout = block_rules.get(key, "")
            example = _extract_layout_example(layout)
            if not example:
                continue
            parts = example.split(" + ")
            if len(parts) == 2 and "=" in parts[1]:
                cho, rest = parts
                jung, result = rest.split("=", 1)
                jung = jung.strip()
                result = result.strip()
                print("   ", end="", flush=True)
                print(cho, end="", flush=True)
                time.sleep(0.3)
                print(f" + {jung}", end="", flush=True)
                time.sleep(0.3)
                print(" = ", end="", flush=True)
                time.sleep(0.2)
                print(styled(result, GREEN, BOLD), end="", flush=True)
                print()
            else:
                print(f"   {example}")
        time.sleep(0.5)

    confusion_pairs = lesson.get("confusion_pairs") or []
    if confusion_pairs:
        print(styled("\nWatch for these look-alikes:", YELLOW))
        # A group can hold more than two letters (ㅚ ㅟ ㅙ ㅞ); the old
        # `for a, b in ...` unpacking crashed on those.
        rendered = " · ".join(
            " vs ".join(styled(x, CYAN) for x in group)
            for group in confusion_pairs[:4]
        )
        print(f"   {rendered}")
        time.sleep(0.5)

    # (Batchim rules aren't listed here: print_reference_table, which
    # always runs right after this, shows the same table.)

    print()
    print(styled("Let's practice →", GREEN))
    time.sleep(0.3)
    print()

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
    print(f"   {styled('Batchim (final consonant):', BOLD)} spelled by how it SOUNDS at the end of a block —")
    print("   ㄱㄲㅋ→k  ㄴ→n  ㄷㅌㅅㅆㅈㅊㅎ→t  ㄹ→l  ㅁ→m  ㅂㅍ→p  ㅇ→ng   e.g. 각 = 'gak', 옷 = 'ot'.")
    print(f"   {styled('Also accepted:', BOLD)} 'l' for a starting ㄹ (라 = ra or la), 'sh' for ㅅ before ㅣ (시 = si or shi).")


# Consonant and vowel sets for the CV chart.
# Basic vowels: the six simple vowels introduced in Lesson 1.
# Y-vowels: the four iotized vowels added in Lesson 6.
_CHART_CONSONANTS = list("ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ")
_CHART_VOWELS_BASIC = list("ㅏㅓㅗㅜㅡㅣ")
_CHART_VOWELS_Y     = list("ㅑㅕㅛㅠ")


def print_cv_chart(quiz: HangulQuiz, y_vowels: bool = False, compact: bool = False):
    """Print a consonant × vowel syllable chart.

    y_vowels=True adds the four iotized vowels (ㅑㅕㅛㅠ) as extra columns.
    compact=True omits the horizontal row separators, halving the height.

    Colors follow the app's conventions with one addition: vowel headers
    are CYAN (reference/info), consonant headers are YELLOW (lesson
    context), composed syllable blocks are bold GREEN (matching
    _composition_rows' convention throughout the app). The distinction
    between C and V headers helps first-time learners not read the
    header row as part of the syllable grid.

    Border style: double-line outer (╔═╗) with single-line inner grid
    (┼─│) — the double outer reads as "this is a reference poster",
    inner lines stay subordinate."""

    vowels = _CHART_VOWELS_BASIC + (_CHART_VOWELS_Y if y_vowels else [])
    roman  = quiz.get_romanization_table()

    # Cell width: 1 space + double-width Hangul glyph (2 cols) + 1 space = 4
    # display columns. All jamo and composed syllable blocks are exactly
    # 2 display columns wide in monospace, so no per-cell padding tricks needed.
    CW = 4  # cell display width including borders

    def cell(content, *style_codes):
        """Return a styled 4-wide cell body (no border chars)."""
        s = styled(content, *style_codes) if style_codes else content
        return f" {s} "

    def hline(left, mid, right, fill="═"):
        """Full-width horizontal rule: one CW-wide run per column (the
        consonant column plus one per vowel), joined by `mid`. The runs
        used to be CW-1 wide, so every column drifted one space left of
        the │ dividers in the rows below."""
        return left + mid.join([fill * CW] * (len(vowels) + 1)) + right

    def inner_hline():
        return hline("╟", "┼", "╢", "─")

    variant = "y-vowels" if y_vowels else "basic"
    layout  = "compact" if compact else "full"
    title   = f"CV Syllable Chart — {variant}, {layout}"
    print(f"\n{styled(title, BOLD, CYAN)}")

    # Top border
    print(hline("╔", "╤", "╗"))

    # Vowel header row: empty corner cell + one cell per vowel
    header = "║" + cell("  ") + "│"
    header += "│".join(cell(v, CYAN, BOLD) for v in vowels)
    header += "║"
    print(header)

    # Separator between header and body
    print(hline("╟", "┼", "╢", "─"))

    # Body: one row per consonant
    for i, cho in enumerate(_CHART_CONSONANTS):
        row = "║" + cell(cho, YELLOW, BOLD) + "│"
        cells = []
        for jung in vowels:
            syl = quiz._compose_syllable(cho, jung)
            cells.append(cell(syl, GREEN, BOLD))
        row += "│".join(cells) + "║"
        print(row)
        # Row separator (omitted in compact mode; always omitted after last row)
        if not compact and i < len(_CHART_CONSONANTS) - 1:
            print(inner_hline())

    # Bottom border
    print(hline("╚", "╧", "╝"))
    print()

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
            return None
        _disc_parts = response.split()
        if (_disc_parts and _disc_parts[0].lstrip('/').lower() == 'lesson'
                and len(_disc_parts) == 2 and _disc_parts[1].isdigit()):
            _n = int(_disc_parts[1])
            _total = len(quiz.curriculum['lessons'])
            if 1 <= _n <= _total:
                print(f"{styled('Walkthrough ended early.', YELLOW)}")
                _ni = quiz.start_lesson(_n)
                print_lesson_intro(_ni.get('introduction', ''), _ni.get('note', ''))
                print_reference_table(quiz, _ni)
                return _ni
            print(f"{styled(f'Lesson {_n} not found — there are {_total} lessons.', YELLOW)}")
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
            return None
        _r_parts = response.split()
        if (_r_parts and _r_parts[0].lstrip('/').lower() == 'lesson'
                and len(_r_parts) == 2 and _r_parts[1].isdigit()):
            _n = int(_r_parts[1])
            _total = len(quiz.curriculum['lessons'])
            if 1 <= _n <= _total:
                print(f"{styled('Walkthrough ended early.', YELLOW)}")
                _ni = quiz.start_lesson(_n)
                print_lesson_intro(_ni.get('introduction', ''), _ni.get('note', ''))
                print_reference_table(quiz, _ni)
                return _ni
            print(f"{styled(f'Lesson {_n} not found — there are {_total} lessons.', YELLOW)}")
        if response:
            # Same check as the alphabet walkthrough: "r" or "l" both count
            # for ㄹ (the old exact match demanded the literal text "r/l").
            if (normalize_roman(response) in quiz.roman_variants(letter)
                    or response.lower() == roman.lower()):
                print(f"   {styled('✅ Correct!', GREEN)}")
            else:
                msg = f'Not quite — {letter} is "{roman}".'
                print(f"   {styled(msg, YELLOW)} (This one's just for practice, no score kept.)")

    print(f"\n{styled('🐣 Walkthrough complete!', GREEN)} Type /table for a quick-reference recap anytime, or just answer the next question to start quizzing.")


def _print_prompt(text: str):
    """Print an engine prompt with **bold** rendered and EVERY line indented
    (multi-line prompts used to indent only their first line)."""
    for line in md(text).split("\n"):
        print(line if line.startswith(" ") else "   " + line)


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
        "decompose_syllable": "🔬",
        "batchim_challenge": "📦", "confusion_drill": "⚡",
        "word_contrast": "📖", "sudden_death": "💀", "nonword_decode": "🔣"
    }
    mode_labels = {"read_aloud": "Sound It Out", "nonword_decode": "Decode"}
    icon = mode_icons.get(q.mode, "❓")
    label = mode_labels.get(q.mode, q.mode.replace('_', ' ').title())
    print(f"\n{icon} {styled(label, CYAN)}")

    rendered = False
    if quiz is not None and q.mode in ("build_syllable", "missing_vowel", "decompose_syllable", "confusion_drill", "word_contrast") and q.letter:
        try:
            syl = quiz.syllable_breakdown(q.letter)
            if q.mode == "build_syllable":
                # Safe to show cho/jung/(jong) — that's the given puzzle —
                # but not the composed result, which is the answer. Cut
                # syl.components before its last (whole-block) entry.
                given = syl.components[:-1]
                print(f"   Build the syllable for {styled(syl.romanization, BOLD)}")
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
            elif q.mode == "decompose_syllable":
                # The INVERSE of build_syllable, so the inverse rule applies:
                # the composed BLOCK is safe to show (it is the question) and
                # the jamo are NOT (they are the answer). build_syllable shows
                # the jamo and hides the block; here we show the block and
                # hide the jamo. Never print syl.cho / syl.jung / syl.components
                # in this branch.
                print(f"   Break this block into its parts:")
                print(f"   {styled(syl.text, BOLD, CYAN)}   "
                      f"=   {styled('?', BOLD, YELLOW)} + "
                      f"{styled('?', BOLD, YELLOW)}")
                print("   Which consonant + vowel make it?")
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
                      f"which one is {styled(syl.romanization, BOLD)}?")
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
                    _print_prompt(q.prompt)
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
                    _print_prompt(q.prompt)
                    print(f"   {target_line}")
                    print(f"   {other_line}")
                rendered = True
        except Exception:
            pass  # fall through to plain q.prompt below

    # nonword_decode: prompt is already fully composed by the engine
    # (includes the "not a real word" framing), so just print it as-is.
    if q.mode == "nonword_decode":
        _print_prompt(q.prompt)
        rendered = True

    if not rendered:
        _print_prompt(q.prompt)

    if q.choices:
        labels = ['A', 'B', 'C', 'D']
        for label, choice in zip(labels, q.choices):
            print(f"     {styled(label + ')', CYAN)} {choice}")
        # More modes now carry a choices list (not just the original MC
        # ones), so it's worth spelling out that typing the real answer
        # directly still works too — this isn't a forced multiple-choice.
        print(f"   {styled('(type the answer directly, or answer with a letter)', CYAN)}")
    # Hints used to print automatically here, which made the /hint command
    # pointless — there was nothing left to reveal. Now we just point at
    # /hint and let the learner ask for it if they want it.
    if q.hint:
        print(f"   {styled('💡 Type /hint if you want a hint.', YELLOW)}")

def show_breakdown(quiz: HangulQuiz, q: QuizQuestion):
    """After a miss, show HOW the answer is built instead of only what it
    is — the same composition row (ㄱ + ㅏ = 가, sounds underneath) the
    lessons teach with, so every mistake doubles as a mini-lesson. Multi-
    block answers (words, nonwords) get one 'block = sound' per syllable.
    Silently does nothing for anything it can't break down safely."""
    text = q.letter
    if not text or q.mode in ("word_contrast", "konglish", "konglish_spell"):
        return
    try:
        blocks = [ch for ch in text if 0xAC00 <= ord(ch) <= 0xD7A3]
        if len(blocks) == 1 and len(text) == 1:
            syl = quiz.syllable_breakdown(text)
            jamo_pieces, roman_line, indent = _composition_rows(syl.components)
            print(f"   {styled('How it works:', DIM)}")
            print(indent + "".join(jamo_pieces))
            print(roman_line)
            if syl.jong and q.mode == "batchim_challenge":
                print(f"   {styled(f'At the bottom of a block, {syl.jong} sounds like {quiz._batchim_sound(syl.jong)!r}.', DIM)}")
        elif len(blocks) > 1:
            parts = [f"{b} = {quiz.syllable_breakdown(b).romanization}" for b in blocks]
            print(f"   {styled('Block by block:', DIM)} " + "  ·  ".join(parts))
    except Exception:
        pass


MODE_ALIASES = {
    "spell": "spell",
    "read": "read_aloud", "read_aloud": "read_aloud",
    "match": "match_sound", "match_sound": "match_sound",
    "build": "build_syllable", "build_syllable": "build_syllable",
    "vowel": "missing_vowel", "missing_vowel": "missing_vowel",
    "batchim": "batchim_challenge", "batchim_challenge": "batchim_challenge",
    "confusion": "confusion_drill", "confusion_drill": "confusion_drill",
    "contrast": "word_contrast", "word_contrast": "word_contrast",
    "decompose": "decompose_syllable", "decompose_syllable": "decompose_syllable",
    "word": "read_word", "read_word": "read_word",
    "decode": "nonword_decode", "nonword_decode": "nonword_decode",
    "sequence": "sequence_decode", "sequence_decode": "sequence_decode",
    "auto": None, "random": None,
}
MODE_USAGE = "spell, read, match, build, decompose, vowel, batchim, confusion, contrast, word, decode, sequence, or auto"

KNOWN_ACTIONS = {
    'q', 'quit', 'exit', 'help', 'roman', 'romanize', 'romanization',
    'stats', 'lessons', 'lesson', 'mode', 'mnemonic', 'talk',
    'template', 'konglish', 'kspell', 'hint', 'h', 'skip', 'intro', 'table',
    'alphabet', 'rain', 'conveyor', 'chart',
}

# Sudden death: start with this many hearts, lose one per miss. A streak of
# SUDDEN_DEATH_HEAL_EVERY correct answers wins one back, up to the maximum.
SUDDEN_DEATH_LIVES = 3
SUDDEN_DEATH_HEAL_EVERY = 10

# Offline streak milestones — a small celebration that needs no LLM.
STREAK_MILESTONES = {
    10: "🔥 10 in a row! You're getting the hang of this.",
    25: "🚀 25 in a row! Your eyes are starting to read Hangul on their own.",
    50: "🏅 50 in a row! That's real fluency with these letters.",
    100: "👑 100 in a row! 대박! (amazing!)",
}

# Longest the mastery bar is drawn; bigger pools are scaled down to fit.
MASTERY_BAR_WIDTH = 20


def _ask(prompt: str) -> Optional[str]:
    """input() that returns None instead of raising on Ctrl+C / closed
    input. Used by the nested prompts inside commands (/talk, /konglish,
    ...), where a Ctrl+C used to crash straight out of the app with a
    traceback — skipping the progress save."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def _mastery_bar(done: int, total: int) -> str:
    if total <= MASTERY_BAR_WIDTH:
        return "█" * done + "░" * (total - done)
    filled = round(MASTERY_BAR_WIDTH * done / total)
    return "█" * filled + "░" * (MASTERY_BAR_WIDTH - filled)


def _advance_and_show(quiz: HangulQuiz) -> dict:
    """Run complete_lesson (which marks the current lesson done and bumps
    current_lesson) and show the lesson the learner lands on next, its
    intro/note and reference table. Returns that new lesson_info so the
    caller can keep its own 'lesson' variable in sync."""
    msg = quiz.complete_lesson()
    new_info = quiz.start_lesson(quiz.progress["current_lesson"])
    print(f"\n{styled('📖 ' + msg, BOLD)}")
    print_lesson_intro_rich(new_info, quiz)
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

    total_lessons = len(quiz.curriculum["lessons"])
    while True:
        ans = _ask(f"\n{styled(f'Move on to Lesson {lesson_id + 1}? [Y/n] ', CYAN)}")
        if ans is None:
            break
        a = ans.strip().lower()
        if a in ("", "y", "yes"):
            return _advance_and_show(quiz)
        if a in ("n", "no"):
            break
        # Allow a subset of slash commands while the advance prompt is open
        # so the learner isn't trapped without navigation.
        parts = ans.split()
        cmd0 = parts[0].lstrip("/").lower() if parts else ""
        if cmd0 == "lesson" and len(parts) == 2 and parts[1].isdigit():
            n = int(parts[1])
            if 1 <= n <= total_lessons:
                new_info = quiz.start_lesson(n)
                print_lesson_intro(new_info.get("introduction", ""), new_info.get("note", ""))
                print_reference_table(quiz, new_info)
                return new_info
            print(f"{styled(f'Lesson {n} not found — there are {total_lessons} lessons.', YELLOW)}")
        elif cmd0 == "lessons":
            print(f"\n{styled('📚 Lessons:', BOLD)}")
            for _l in quiz.list_lessons():
                _mark = styled('✓', GREEN) if _l['completed'] else ''
                _here = styled('  ← you are here', CYAN) if _l['id'] == quiz.current_lesson['id'] else ''
                print(f"   {_l['id']:2}. {_l['title']} {_mark}{_here}")
        else:
            print(f"{styled('Type Y/n to decide, /lessons to browse, or /lesson N to jump.', YELLOW)}")
    print(f"{styled('No rush — staying here. Type /lessons to see all lessons, or /lesson N to jump to one whenever you want.', YELLOW)}")
    return None


def _show_reading_reward(quiz: HangulQuiz):
    """Every 5-answer streak, show something real the learner can read.
    Offline (default) this is an instant real word they can already spell;
    with --use-llm it tries a live model sentence first and falls back to
    the same word if that fails."""
    known = quiz.get_mastered_syllables(min_confidence=3)
    if len(known) < 3:
        return
    # Only the LLM path actually builds a sentence; the offline path returns
    # a single exposure word, so a "Building a sentence" banner there would
    # be a lie.
    if USE_LLM:
        print(f"\n{styled('📖 Building a sentence from what you know...', YELLOW)}")
    sentence = generate_mini_sentence(known, quiz) if USE_LLM else None
    turn_mode = "read_translate" if sentence else None
    if not sentence:
        turn = build_template_sentence(known, quiz)
        if turn and turn.get("korean"):
            eng = turn.get("english")
            sentence = f"{styled(turn['korean'], BOLD)}  —  {eng}" if eng else turn["korean"]
            turn_mode = turn.get("mode")
    if not sentence:
        return
    # vocab_exposure means a real single word the learner can spell, not a
    # sentence — framing it as "you can now read" would overclaim.
    if turn_mode == "vocab_exposure":
        print(f"\n{styled('📖 A real Korean word you can already spell:', GREEN)}")
    else:
        print(f"\n{styled('📖 You can now read:', GREEN)}")
    print(f"   {sentence}")


def _print_exposure(turn: dict):
    """Show a single-word / bare-syllable exposure turn — no grading."""
    label = ("📖 A real Korean word you can already spell:"
             if turn.get("mode") == "vocab_exposure"
             else "📖 Practice reading these syllables:")
    print(f"\n{styled(label, GREEN)}")
    print(f"   {styled(turn['korean'], BOLD)}")
    if turn.get("english"):
        print(f"   {styled(turn['english'], YELLOW)}")


def _run_talk(quiz: HangulQuiz):
    """/talk — read a Korean sentence built from mastered syllables."""
    print(f"\n{styled('💬 Finding a Korean sentence you can read...', CYAN)}")
    turn = generate_conversation_turn(quiz, mode="read_translate", use_llm=USE_LLM)
    if not turn:
        print(f"   {styled('Not enough syllables mastered yet — keep practicing!', YELLOW)}")
        return
    if turn.get("mode") in ("vocab_exposure", "syllable_practice"):
        # Exposure (the offline or LLM-failed fallback), not a sentence to
        # translate — shown honestly, with no fake grading or streak bump.
        _print_exposure(turn)
        return
    method_labels = {'template': '📋 Template', 'tatoeba': '📚 Real sentence', 'llm': '🤖 LLM'}
    label = method_labels.get(turn.get('method', 'llm'), '🤖 LLM')
    print(f"\n{styled(f'{label} — read this Korean:', CYAN)}")
    print(f"   {styled(turn['korean'], BOLD)}")
    if not turn.get("english"):
        # No trusted translation to grade against — grading the learner
        # against a placeholder like "(translation unavailable)" marked every
        # answer wrong and reset their streak. Make it a self-check instead.
        print(f"   {styled('(No translation available for this one — read it aloud as a self-check.)', YELLOW)}")
        return
    print(f"\n   {styled('Translate to English:', YELLOW)}")
    user = _ask(f"{styled('>', BOLD)} ")
    if not user:
        print(f"   The Korean means: {styled(turn['english'], BOLD)}")
        return
    result = check_conversation_answer(user, turn, quiz)
    print(f"   {md(result['feedback'])}")
    if result.get('correct'):
        quiz.session_streak += 1
        quiz.session_best_streak = max(quiz.session_best_streak, quiz.session_streak)
    else:
        quiz.session_streak = 0


def _ask_with_hint(q: QuizQuestion) -> Optional[str]:
    """Prompt for an answer, letting /hint be typed first. None = cancelled."""
    while True:
        user = _ask(f"\n{styled('>', BOLD)} ")
        if user is None:
            return None
        if user.lower() in ('/hint', '/h'):
            print(f"   {styled('💡', YELLOW)} {q.hint}" if q.hint else "   (No hint for this one.)")
            continue
        return user


def _run_konglish(quiz: HangulQuiz):
    """/konglish — sound out an English loanword written in Hangul."""
    q = quiz.konglish_question()
    print_question(q)
    user = _ask_with_hint(q)
    if user is None:
        return
    # Lenient on form ('mouse' for 'mouse (computer)', either side of
    # 'mart / store'), strict on content — an empty answer or a stray
    # letter is never correct (the old substring check accepted both).
    if quiz.check_konglish(user, q):
        print(f"   ✅ Yes! {styled(q.letter, BOLD)} = {q.correct_answer}")
    else:
        print(f"   Not quite — it's {styled(q.correct_answer, BOLD)}. "
              f"Sound it out: {q.letter} = {q.hint.split(' — ')[0].replace('Romanized: ', '')}")


def _run_kspell(quiz: HangulQuiz):
    """/kspell — spell an English loanword in Hangul."""
    q = quiz.konglish_spell_question()
    print_question(q)
    user = _ask_with_hint(q)
    if user is None:
        return
    # Grades outside quiz.answer(), so resolve an A-D letter here too.
    resolved = quiz.resolve_choice(user, q.choices)
    if resolved == q.correct_answer:
        print(f"   ✅ Perfect! {styled(resolved, BOLD)} is right.")
    else:
        print(f"   ❌ The Hangul spelling is {styled(q.correct_answer, BOLD)}")


def _print_help():
    print(f"""
{styled('Commands:', BOLD)}
  {styled('/stats', CYAN)}      — Show your progress
  {styled('/lessons', CYAN)}    — List all lessons (or just type a lesson number)
  {styled('/lesson N', CYAN)}   — Jump to lesson N
  {styled('/mode NAME', CYAN)}  — Practice one question type: {MODE_USAGE}
  {styled('/alphabet', CYAN)}   — Walk through all 24 basic letters, consonants then vowels
  {styled('/intro', CYAN)}      — Walk through this lesson's letters one at a time

{styled('While answering:', BOLD)}
  {styled('/hint', CYAN)}       — A nudge for the current question (also {styled('/h', CYAN)})
  {styled('/skip', CYAN)}       — Reveal the answer and move on (resets your streak)

{styled('Reference:', BOLD)}
  {styled('/table', CYAN)}      — This lesson's reference table
  {styled('/roman', CYAN)}      — The full romanization (spelling) key
  {styled('/chart', CYAN)}      — Consonant × vowel syllable chart
                 {styled('/chart compact', CYAN)}  — same, no row separators
                 {styled('/chart y', CYAN)}        — add the y-vowels (ㅑ ㅕ ㅛ ㅠ)
  {styled('/mnemonic X', CYAN)} — A memory trick for letter X

{styled('Games & extras:', BOLD)}
  {styled('/rain', CYAN)}       — Hangul Rain: type falling syllables before they land
  {styled('/conveyor', CYAN)}   — Conveyor: build and decompose syllables against the clock
  {styled('/talk', CYAN)}       — Read a Korean sentence made from syllables you've mastered
  {styled('/template', CYAN)}   — Same, but instant (no LLM)
  {styled('/konglish', CYAN)}   — Sound out an English loanword written in Hangul
  {styled('/kspell', CYAN)}     — Spell an English loanword in Hangul
  {styled('/quit', CYAN)}       — Save and exit
""")


def interactive_loop(quiz: HangulQuiz, args, lesson_info: dict):
    """Main interactive quiz loop. Progress is saved after every answer and
    again on the way out — including Ctrl+C or an unexpected error, which
    used to exit without saving anything from the session."""
    print(f"\n{styled('🇰🇷 Hangul Tutor', BOLD, GREEN)}")
    engine_label = f"Ollama: {summarize_models()}" if USE_LLM else "Offline (no LLM needed)"
    print(f"{engine_label} | Lesson: {quiz.current_lesson['title']}")
    print(f"Type {styled('/help', CYAN)} for commands, {styled('/quit', RED)} to exit")

    try:
        _interactive_loop_body(quiz, args, lesson_info)
    except KeyboardInterrupt:
        print(f"\n{styled('👋 안녕히 가세요! (Goodbye!)', GREEN)}")
    finally:
        quiz.save_progress()
    _print_session_summary(quiz)


def _print_session_summary(quiz: HangulQuiz):
    summary = quiz.get_progress_summary()
    print(f"\n{styled('📊 Session Summary:', BOLD)}")
    print(f"   Correct: {summary['session_score']} ({summary['session_pct']}%)")
    print(f"   Best streak this session: {quiz.session_best_streak}   (all-time: {summary['streak_best']})")
    if summary['top_confusions']:
        print(f"   Practice these: {', '.join(c['pair'] for c in summary['top_confusions'])}")
    if quiz.session_total and USE_LLM:
        # Optional natural-language recap (--use-llm), as the flag promises.
        print(f"   {generate_session_summary(build_session_data(quiz))}")

    # Structured lesson-complete block — only shown when the current lesson
    # is actually mastered, so quitting mid-lesson doesn't print a false
    # "LESSON COMPLETE" banner.
    if (quiz.current_lesson is not None
            and quiz.lesson_mastery(quiz.current_lesson["id"])["is_mastered"]):
        print_lesson_complete(quiz)


def _interactive_loop_body(quiz: HangulQuiz, args, lesson_info: dict):
    # --mode locks the quiz to a single question type; None means auto-pick
    locked_mode = args.mode
    if locked_mode:
        print(f"Mode locked to: {styled(locked_mode, CYAN)}")

    # Show the lesson's teaching content. Use lesson_info (from
    # quiz.start_lesson()), NOT the raw quiz.current_lesson dict — only
    # lesson_info has computed fields like letter_romanization.
    lesson = lesson_info
    print_lesson_intro_rich(lesson, quiz)
    print_reference_table(quiz, lesson)

    # Show a mnemonic for the first letter as a warm welcome. Offline this
    # is instant (hardcoded table); only with --use-llm, and only for a
    # letter without a stock mnemonic, does it make a blocking model call —
    # in which case say so, since that can take a moment on a cold start.
    if lesson.get("letters"):
        first_letter = lesson["letters"][0]
        if USE_LLM and first_letter not in ALPHABET_MNEMONICS:
            print(f"\n{styled('🧠 Generating a mnemonic...', YELLOW)} (first response from a model can take a moment)")
        mnemonic = mnemonic_for(first_letter)
        print(f"\n{styled('🧠 Mnemonic for', YELLOW)} {styled(first_letter, BOLD)}:")
        print(f"   {mnemonic}")

    sudden_death = args.sudden_death
    lives = SUDDEN_DEATH_LIVES
    run_answered = run_correct = run_streak = run_best = 0
    if sudden_death:
        print(f"\n{styled('💀 SUDDEN DEATH', BOLD, RED)} — {SUDDEN_DEATH_LIVES} hearts. "
              f"Each miss costs one; every {SUDDEN_DEATH_HEAL_EVERY} in a row wins one back.")

    current_question = None
    # Lesson ids the learner has already been offered advancement on and
    # said "not yet" to — so a mastered-but-not-advanced lesson doesn't
    # re-prompt after every single subsequent correct answer.
    mastery_offered = set()
    # Cache the last mastery bar value so we only reprint it when it changes.
    _last_mastery_val = (-1, -1)
    # The streak value the reading reward last fired at. The reward used
    # to re-fire whenever a new question was drawn while the streak still
    # sat on a multiple of 5 — e.g. after /skip or /mode.
    last_reward_streak = 0

    # Wall-clock time when the current question was first displayed —
    # used to compute response_time_ms for the per-item EMA. Persists
    # through /hint passes without being reset.
    question_shown_at = None

    while True:
        if current_question is None:
            streak = quiz.session_streak
            if (not sudden_death and streak >= 5 and streak % 5 == 0
                    and streak != last_reward_streak):
                last_reward_streak = streak
                _show_reading_reward(quiz)
            current_question = quiz.next_question(mode=locked_mode)
            # Only draw the question card when it's actually new — /hint and
            # other commands don't redraw it (it's still visible above).
            print_question(current_question, quiz)
            question_shown_at = time.time()

        try:
            user_input = input(f"\n{styled('>', BOLD)} ").strip()
        except EOFError:
            print(f"\n{styled('👋 안녕히 가세요! (Goodbye!)', GREEN)}")
            return

        # Blank Enter: don't grade it as a wrong answer — re-prompt.
        if not user_input:
            print(f"{styled('(blank — /hint for a hint, /skip to reveal the answer)', YELLOW)}")
            continue

        # Bare lesson number ("5", "5.") → jump to that lesson, so the
        # /lessons list is actually navigable. Answers are never bare digits
        # (Hangul, romanization, or A-D), so this can't collide with a real
        # answer; out-of-range ids are caught by the /lesson handler.
        _num = user_input.strip(" .)():-")
        if _num.isdigit():
            user_input = f"/lesson {_num}"

        # ── Commands ─────────────────────────────────────────────────
        if user_input.startswith('/'):
            cmd = user_input[1:].split()
            if not cmd:
                continue
            action = cmd[0].lower()

            if action in ('q', 'quit', 'exit'):
                print(f"\n{styled('👋 안녕히 가세요! (Goodbye!)', GREEN)}")
                return

            elif action == 'help':
                _print_help()

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
                m = quiz.lesson_mastery()
                if m["pool_size"]:
                    print(f"   This lesson: {m['mastered_count']}/{m['pool_size']} solid "
                          f"(need {m['needed']} to master)")
                for label, key in (("Hangul Rain best", "rain_best"),
                                   ("Sudden death best", "sudden_death_best")):
                    if quiz.progress.get(key):
                        print(f"   {label}: {quiz.progress[key]}")

            elif action == 'lessons':
                print(f"\n{styled('📚 Lessons:', BOLD)}")
                for l in quiz.list_lessons():
                    mark = styled('✓', GREEN) if l['completed'] else ''
                    here = styled('  ← you are here', CYAN) if l['id'] == quiz.current_lesson['id'] else ''
                    print(f"   {l['id']:2}. {l['title']} {mark}{here}")
                print(f"{styled('   Jump to one by typing its number (e.g. 5) or /lesson 5.', YELLOW)}")

            elif action == 'lesson':
                if len(cmd) < 2:
                    print(f"{styled('Usage: /lesson N  (e.g. /lesson 5) — /lessons lists them all.', YELLOW)}")
                    continue
                try:
                    info = quiz.start_lesson(int(cmd[1]))
                except (ValueError, IndexError):
                    total = len(quiz.curriculum["lessons"])
                    print(f"{styled(f'Invalid lesson number — pick 1 to {total}.', RED)}")
                    continue
                print_lesson_intro_rich(info, quiz)
                print_reference_table(quiz, info)
                # Keep 'lesson' in sync so /intro and /table follow the jump,
                # and drop the leftover question from the old lesson.
                lesson = info
                current_question = None

            elif action == 'intro':
                _intro_result = run_beginner_intro(quiz, lesson)
                if _intro_result is not None:
                    lesson = _intro_result
                    current_question = None

            elif action == 'alphabet':
                run_alphabet_intro(quiz)

            elif action == 'table':
                print_reference_table(quiz, lesson)

            elif action == 'chart':
                flags = [t.lower() for t in cmd[1:]]
                print_cv_chart(quiz, y_vowels=('y' in flags), compact=('compact' in flags))

            elif action == 'rain':
                try:
                    print("Launching Hangul Rain... (Esc to quit)")
                    launch_rain_mode(quiz)
                    quiz.save_progress()
                except RuntimeError as e:
                    print(str(e))
                except KeyboardInterrupt:
                    pass
                # Redraw the outstanding question so the quiz resumes where
                # it left off.
                if current_question:
                    print_question(current_question, quiz)

            elif action == 'conveyor':
                try:
                    _pool = quiz._get_lesson_syllable_pool(lesson)
                    _state = make_conveyor_state(
                        lesson_id=lesson.get('id', 0),
                        active_cv=_pool,
                    )
                    print("Launching Conveyor... (/quit to exit)")
                    run_conveyor(quiz, _state)
                    quiz.save_progress()
                except (RuntimeError, ValueError) as e:
                    print(str(e))
                except KeyboardInterrupt:
                    pass
                if current_question:
                    print_question(current_question, quiz)

            elif action == 'mode':
                choice = cmd[1].lower() if len(cmd) > 1 else ""
                if choice in MODE_ALIASES:
                    locked_mode = MODE_ALIASES[choice]
                    current_question = None  # force new question in the new mode
                    label = locked_mode or "auto (a mix of everything)"
                    print(f"{styled(f'Mode: {label}', CYAN)}")
                else:
                    print(f"{styled(f'Usage: /mode NAME — one of: {MODE_USAGE}', RED)}")

            elif action == 'mnemonic':
                letter = cmd[1] if len(cmd) > 1 else ""
                if not letter:
                    print(f"{styled('Usage: /mnemonic ㄱ', RED)}")
                else:
                    print(f"\n{styled(f'🧠 Mnemonic for {letter}:', YELLOW)}")
                    print(f"   {mnemonic_for(letter)}")

            elif action == 'talk':
                _run_talk(quiz)

            elif action == 'template':
                # Always an exposure turn (a real word, or bare syllables) —
                # shown honestly: no "translate this", no grading.
                _print_exposure(build_template_sentence(
                    quiz.get_mastered_syllables(min_confidence=3), quiz))

            elif action == 'konglish':
                _run_konglish(quiz)

            elif action == 'kspell':
                _run_kspell(quiz)

            elif action in ('hint', 'h'):
                if current_question.hint:
                    print(f"   {styled('💡', YELLOW)} {md(current_question.hint)}")
                else:
                    print(f"   {styled('No hint for this one — you can /skip to see the answer.', YELLOW)}")

            elif action == 'skip':
                print(f"   Answer was: {styled(current_question.correct_answer, GREEN)}")
                show_breakdown(quiz, current_question)
                # Skipping ends the streak — otherwise a streak could be
                # kept alive by skipping every hard question.
                if quiz.session_streak:
                    print(f"   {styled('Streak reset.', DIM)}")
                quiz.session_streak = 0
                run_streak = 0
                current_question = None

            elif action not in KNOWN_ACTIONS:
                print(f"{styled(f'Unknown command: /{action}', RED)} — type /help to see what's available.")

            continue

        # ── Answer ───────────────────────────────────────────────────
        # Wrong writing system (e.g. 'ga' where Hangul is expected)? Say so
        # and let them try again, rather than grading it.
        nudge = quiz.script_mismatch(user_input, current_question)
        if nudge:
            print(f"   {styled(nudge, YELLOW)}")
            continue

        elapsed_ms = (time.time() - question_shown_at) * 1000 if question_shown_at else None
        result = quiz.answer(user_input, current_question, response_ms=elapsed_ms)
        print(f"   {md(result.feedback)}")
        if not result.correct:
            show_breakdown(quiz, current_question)

        if sudden_death:
            run_answered += 1
            if result.correct:
                run_correct += 1
                run_streak += 1
                run_best = max(run_best, run_streak)
                if run_streak % SUDDEN_DEATH_HEAL_EVERY == 0 and lives < SUDDEN_DEATH_LIVES:
                    lives += 1
                    print(f"   {styled('💖 +1 heart for the streak!', GREEN)}")
            else:
                run_streak = 0
                lives -= 1
            hearts = "❤️ " * lives + "🖤 " * (SUDDEN_DEATH_LIVES - lives)
            print(f"   {hearts} {styled(f'Score: {run_correct}', BOLD)}")
            if lives <= 0:
                quiz.save_progress()
                best = quiz.progress.get("sudden_death_best", 0)
                print(f"\n{styled('💀 GAME OVER', BOLD, RED)}")
                print(f"   Correct answers: {run_correct} of {run_answered}   Longest streak: {run_best}")
                if run_correct > best:
                    quiz.progress["sudden_death_best"] = run_correct
                    print(f"   {styled('🏆 New personal best!', BOLD, GREEN)}")
                else:
                    print(f"   Personal best: {best}")
                again = _ask(f"\n{styled('Play again? [Y/n] ', CYAN)}")
                if again is None or again.lower() not in ("", "y", "yes"):
                    return
                lives = SUDDEN_DEATH_LIVES
                run_answered = run_correct = run_streak = run_best = 0
        else:
            streak = quiz.session_streak
            print(f"   {styled(f'🔥 Streak: {streak}', GREEN if streak > 3 else '')}")
            if result.correct and streak in STREAK_MILESTONES:
                print(f"   {styled(STREAK_MILESTONES[streak], BOLD, YELLOW)}")

            m = quiz.lesson_mastery()
            if m["pool_size"] > 0 and quiz.current_lesson["id"] not in quiz.progress["completed_lessons"]:
                _mc, _ps = m["mastered_count"], m["pool_size"]
                if (_mc, _ps) != _last_mastery_val:
                    _last_mastery_val = (_mc, _ps)
                    bar = _mastery_bar(_mc, _ps)
                    print(f"   {styled(f'📊 Mastery: {_mc}/{_ps} [{bar}]', CYAN)}")

        # Periodic encouragement — an optional Ollama flourish, so it only
        # runs with --use-llm (silent otherwise, no hang).
        if (result.correct and USE_LLM and quiz.session_streak > 0
                and quiz.session_streak % 7 == 0):
            print(f"\n{styled('🌟 Generating encouragement...', YELLOW)}")
            accuracy = 100 * quiz.session_correct / max(1, quiz.session_total)
            enc = generate_encouragement(quiz.session_streak, accuracy)
            if not enc.startswith('['):
                print(f"\n{styled('🌟', YELLOW)} {enc}")

        # Lesson progression (normal mode only). When the active lesson's
        # pool crosses the mastery bar, congratulate once and offer to
        # advance; mastery_offered stops it re-asking after a "not yet".
        if result.correct and not sudden_death:
            _lid = quiz.current_lesson["id"]
            if (_lid not in quiz.progress["completed_lessons"]
                    and _lid not in mastery_offered
                    and quiz.lesson_mastery(_lid)["is_mastered"]):
                mastery_offered.add(_lid)
                _advanced = _offer_advance(quiz, _lid)
                if _advanced is not None:
                    lesson = _advanced

        # Save after every answer, so nothing is lost if the window closes.
        quiz.save_progress()
        current_question = None


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
    parser.add_argument("--mode", choices=sorted(k for k, v in MODE_ALIASES.items() if v),
                        metavar="MODE", help=f"Lock to a single quiz mode: {MODE_USAGE}")
    parser.add_argument("--sudden-death", action="store_true",
                        help=f"Survival mode: {SUDDEN_DEATH_LIVES} hearts, lose one per miss")
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
    if args.mode:
        args.mode = MODE_ALIASES[args.mode]   # accept short names like 'read'

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
