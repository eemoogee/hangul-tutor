"""
game_io.py — CLI I/O wrapper for hangul-tutor CV games.

Responsibility boundary
-----------------------
This module owns exactly two things:
  1. Rendering game state and quiz content to the terminal.
  2. Reading raw player input from the terminal.

It does NOT:
  - Parse or dispatch slash-commands.
  - Grade answers.
  - Mutate GameState.
  - Contain any game logic.

All functions take plain data (GameState, QuizQuestion, QuizResult) and
either print to stdout or return a string. Nothing else.

Browser-conversion note
-----------------------
Every render function produces output through _print() and _styled().
To port to a browser, replace those two primitives — the render functions
themselves do not need to change.
"""

from __future__ import annotations

import sys
from typing import Optional

# Local import — QuizQuestion and QuizResult live in the engine.
# game_io does not import GameState directly; it receives state dicts
# or the relevant fields as arguments so this layer stays thin.
from hangul_quiz_engine import QuizQuestion, QuizResult
from game_state import ConveyorState


# ---------------------------------------------------------------------------
# ANSI color primitives
# (Kept local so game_io has no dependency on hangul_cli.py.)
# ---------------------------------------------------------------------------

if sys.platform == "win32":
    import os
    os.system("")  # Enable ANSI processing in the Windows console.

BOLD   = "\033[1m"
DIM    = "\033[2m"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"


def _styled(text: str, *styles: str) -> str:
    """Wrap text in ANSI style codes."""
    return "".join(styles) + text + RESET


def _print(*args, **kwargs) -> None:
    """
    Single print primitive for this module.
    Replace this function to redirect all game output (e.g. to a web layer).
    """
    print(*args, **kwargs)


# ---------------------------------------------------------------------------
# Mode display metadata
# (Maps internal mode strings to the icon and label the player sees.)
# ---------------------------------------------------------------------------

_MODE_META: dict[str, tuple[str, str]] = {
    "build":         ("🔨", "Build the Block"),
    "decompose":     ("🔍", "Break It Down"),
    "missing_vowel": ("❓", "Missing Vowel"),
    "read_aloud":    ("🔊", "Sound It Out"),
    "spell":         ("✏️",  "Spell It"),
    "match_sound":   ("👂", "Match the Sound"),
    "read_word":     ("📖", "Read the Word"),
    "nonword_decode":("🔣", "Decode"),
    "sequence_decode":("🔣", "Read the Sequence"),
    "confusion_drill":("⚡", "Confusion Drill"),
    "batchim_challenge":("🧱", "Final Consonant"),
}

_DEFAULT_META = ("📝", "Question")


def _mode_meta(mode: str) -> tuple[str, str]:
    return _MODE_META.get(mode, _DEFAULT_META)


# ---------------------------------------------------------------------------
# Render: game state header
# ---------------------------------------------------------------------------

def render_game_header(state: ConveyorState) -> None:
    """
    Print a compact one-line header showing the current game context.

    Example output:
        ── Conveyor  Lesson 3  Score: 12  Streak: 4  ▸ decompose ──
    """
    challenge = state.current_challenge or "—"
    icon, _ = _mode_meta(challenge)

    parts = [
        _styled("Conveyor", BOLD),
        f"Lesson {state.lesson_id}",
        f"Score: {_styled(str(state.score), BOLD)}",
        f"Streak: {_styled(str(state.streak), CYAN)}",
        f"▸ {icon} {challenge}",
    ]
    line = "  ".join(parts)
    _print(f"\n{_styled('── ', DIM)}{line}{_styled(' ──', DIM)}")


# ---------------------------------------------------------------------------
# Render: question card
# ---------------------------------------------------------------------------

def render_question(question: QuizQuestion, time_limit_ms: Optional[float] = None) -> None:
    """
    Print the question card: icon, mode label, prompt, and choices if any.

    time_limit_ms: when set, prints a time-limit reminder below the choices.

    Mirrors the structure of hangul_cli.print_question() but is kept
    local so game_io has no dependency on hangul_cli.py.
    """
    icon, label = _mode_meta(question.mode)

    _print()
    _print(f"  {icon}  {_styled(label, BOLD, CYAN)}")
    _print(f"  {question.prompt}")

    if question.choices:
        _print()
        for i, choice in enumerate(question.choices, 1):
            _print(f"    {_styled(str(i) + '.', DIM)} {choice}")

    if question.hint:
        _print(f"\n  {_styled('Hint: ' + question.hint, DIM)}")

    if time_limit_ms is not None:
        secs = time_limit_ms / 1000
        _print(f"  {_styled(f'⏱  {secs:.0f}s to answer', DIM)}")


# ---------------------------------------------------------------------------
# Render: result feedback
# ---------------------------------------------------------------------------

def render_result(result: QuizResult) -> None:
    """
    Print the result of one answered question.

    Correct answers are green; wrong answers are red with the expected answer.
    """
    if result.correct:
        _print(f"\n   {_styled('✓ ' + result.feedback, GREEN)}")
    else:
        _print(f"\n   {_styled('✗ ' + result.feedback, RED)}")
        _print(f"   {_styled('Expected: ' + result.expected, DIM)}")


# ---------------------------------------------------------------------------
# Render: game over
# ---------------------------------------------------------------------------

def render_game_over(state: ConveyorState) -> None:
    """
    Print the end-of-game summary.

    Called once, after state.done is True.
    """
    _print()
    _print(_styled("─" * 40, DIM))

    if state.outcome == "complete":
        _print(_styled("  🎉  Session complete!", BOLD + GREEN))
    elif state.outcome == "player":
        _print(_styled("  🏆  You win!", BOLD + GREEN))
    elif state.outcome == "draw":
        _print(_styled("  🤝  Draw!", BOLD + YELLOW))
    else:
        _print(_styled("  Game over.", BOLD))

    _print()
    _print(f"  Final score : {_styled(str(state.score), BOLD)}")
    _print(f"  Turns played: {state.turn}")
    _print(f"  Best streak : {_styled(str(state.best_streak), CYAN)}")
    _print(_styled("─" * 40, DIM))
    _print()


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

def render_timeout(elapsed_ms: float, limit_ms: float) -> None:
    """Print the timeout penalty message after a too-slow answer."""
    elapsed_s = elapsed_ms / 1000
    limit_s   = limit_ms   / 1000
    _print(f"\n   {_styled(f'⏰  Too slow!  ({elapsed_s:.1f}s — limit: {limit_s:.0f}s)', RED)}")
    _print(f"   {_styled('Correct answer recorded for practice, but no points this turn.', DIM)}")


def get_player_input() -> Optional[str]:
    """
    Read one line of input from the player.

    Returns
    -------
    str
        The raw input string, stripped of leading/trailing whitespace.
        May be an empty string (blank Enter) — the caller decides what
        to do with it.
    None
        If the player sends EOF (Ctrl-D) or a keyboard interrupt (Ctrl-C).
        The caller should treat None as a signal to exit the game loop.
    """
    try:
        raw = input(f"\n{_styled('>', BOLD)} ").strip()
        return raw
    except (EOFError, KeyboardInterrupt):
        return None
