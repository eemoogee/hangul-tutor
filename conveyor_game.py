"""
conveyor_game.py — Conveyor Belt Sorter game loop.

Responsibility boundary
-----------------------
This module owns the game loop: it sequences turns, applies scoring rules,
and decides when the game is over. It does NOT own:

  - Terminal rendering     → game_io.py
  - Question generation    → hangul_quiz_engine.py (next_question)
  - Answer grading         → hangul_quiz_engine.py (answer)
  - Learner mastery        → hangul_quiz_engine.py (LearnerItem)

The game loop receives a fully constructed ConveyorState and a
HangulQuiz instance. It mutates state in place and returns it
when the session ends.

Scoring rules (from game_config)
---------------------------------
  turn_limit     : int   — number of answered questions before the session ends.
  streak_bonuses : dict  — maps streak threshold (int) to bonus points (int).
                           Example: {3: 1, 5: 2, 10: 3}
                           At streak 3, score += 1 extra on top of base +1.
                           At streak 5, score += 2 extra. At streak 10, += 3.
                           Only the highest applicable threshold fires per turn.

Slash-commands recognised inside the game loop
-----------------------------------------------
  /quit   — exit immediately, outcome = "complete" (partial session counts).
  /score  — print current score and streak without consuming the question.
  /help   — print available commands.

All other slash-commands are silently ignored with a brief note.
The existing engine slash-commands (/hint, /skip, etc.) do not apply here —
the Conveyor loop manages its own prompt/answer cycle directly.
"""

from __future__ import annotations

import time
from typing import Optional

from hangul_quiz_engine import HangulQuiz
from game_state import ConveyorState
from game_io import (
    render_game_header,
    render_question,
    render_result,
    render_game_over,
    get_player_input,
    _print,
    _styled,
    BOLD, DIM, CYAN, YELLOW,
)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _streak_bonus(streak: int, bonuses: dict[int, int]) -> int:
    """
    Return the bonus points for the current streak level.

    Only the single highest applicable threshold fires — thresholds do not
    stack. If streak is 5 and bonuses = {3: 1, 5: 2, 10: 3}, returns 2.
    If no threshold is met, returns 0.
    """
    applicable = [bonus for threshold, bonus in bonuses.items() if streak >= threshold]
    return max(applicable, default=0)


def _apply_score(state: ConveyorState, correct: bool) -> int:
    """
    Update state.score and state.streak for one answered question.

    Returns the points earned this turn (for display).
    """
    bonuses: dict[int, int] = state.game_config.get("streak_bonuses", {})

    if correct:
        state.streak += 1
        state.best_streak = max(state.best_streak, state.streak)
        bonus = _streak_bonus(state.streak, bonuses)
        earned = 1 + bonus
        state.score += earned
    else:
        state.streak = 0
        earned = 0

    return earned


# ---------------------------------------------------------------------------
# Command handling
# ---------------------------------------------------------------------------

def _handle_command(cmd: str, state: ConveyorState) -> bool:
    """
    Handle a slash-command entered during the game.

    Returns True if the command should exit the game loop, False otherwise.
    """
    cmd = cmd.strip().lower()

    if cmd == "/quit":
        _print(f"\n  {_styled('Ending session early…', DIM)}")
        return True  # signal the loop to stop

    if cmd == "/score":
        _print(
            f"\n  Score: {_styled(str(state.score), BOLD)}  "
            f"Streak: {_styled(str(state.streak), CYAN)}  "
            f"Turn: {state.turn + 1}/{state.game_config.get('turn_limit', '?')}"
        )
        return False

    if cmd == "/help":
        _print(f"\n  {_styled('Commands:', BOLD)}")
        _print(f"    {_styled('/score', CYAN)}  — show current score and streak")
        _print(f"    {_styled('/quit',  CYAN)}  — end the session now")
        return False

    _print(f"\n  {_styled(f'{cmd!r} is not available here. Try /help.', DIM)}")
    return False


# ---------------------------------------------------------------------------
# Challenge sequence helpers
# ---------------------------------------------------------------------------

def _advance_challenge(state: ConveyorState) -> None:
    """
    Move to the next position in the challenge sequence.
    Wraps around so the sequence loops for the full turn_limit.
    """
    if state.challenge_sequence:
        state.challenge_index = (state.challenge_index + 1) % len(state.challenge_sequence)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_conveyor(engine: HangulQuiz, state: ConveyorState) -> ConveyorState:
    """
    Run the Conveyor Belt Sorter session to completion.

    Parameters
    ----------
    engine : A fully initialised HangulQuiz instance for the target lesson.
    state  : A ConveyorState constructed by the caller (see make_conveyor_state).

    Returns
    -------
    The mutated ConveyorState after the session ends. The caller can inspect
    state.score, state.turn, state.outcome, etc.
    """
    turn_limit: int = state.game_config.get("turn_limit", 20)
    # TODO: enforce state.time_limit_ms per question (design decision needed:
    #   auto-wrong on timeout? show countdown? penalty points?)

    current_question = None
    question_shown_at: Optional[float] = None

    while not state.done:
        # -- fetch a new question if needed --
        if current_question is None:
            mode = state.current_challenge  # e.g. "build", "decompose"
            current_question = engine.next_question(mode=mode)
            state.last_question = {
                "mode": current_question.mode,
                "prompt": current_question.prompt,
                "correct_answer": current_question.correct_answer,
                "choices": list(current_question.choices),
                "hint": current_question.hint,
                "lesson_id": current_question.lesson_id,
                "letter": current_question.letter,
            }
            render_game_header(state)
            render_question(current_question)
            question_shown_at = time.time()

        # -- read input --
        raw = get_player_input()

        if raw is None:
            # Ctrl-C / Ctrl-D — exit cleanly
            _print()
            break

        if not raw:
            # Blank Enter — re-prompt without consuming the question
            continue

        if raw.startswith("/"):
            should_quit = _handle_command(raw, state)
            if should_quit:
                break
            continue  # command handled; question still active

        # -- grade --
        elapsed_ms = (time.time() - question_shown_at) * 1000
        result = engine.answer(raw, current_question, response_ms=elapsed_ms)

        # -- update state --
        earned = _apply_score(state, result.correct)
        state.last_result = {
            "correct": result.correct,
            "user_answer": result.user_answer,
            "expected": result.expected,
            "feedback": result.feedback,
        }

        # -- render result --
        render_result(result)
        if earned > 1:
            _print(f"   {_styled(f'Streak bonus: +{earned - 1}', YELLOW)}")

        # -- advance --
        state.turn += 1
        _advance_challenge(state)
        current_question = None

        # -- check termination --
        if state.turn >= turn_limit:
            state.set_terminal("complete")

    # If we exited the loop without set_terminal (e.g. /quit or Ctrl-C),
    # mark the session complete so the caller always gets a clean state.
    if not state.done:
        state.set_terminal("complete")

    engine.save_progress()
    render_game_over(state)
    return state


# ---------------------------------------------------------------------------
# Constructor helper
# ---------------------------------------------------------------------------

def make_conveyor_state(
    lesson_id: int,
    active_cv: list[str],
    challenge_sequence: Optional[list[str]] = None,
    turn_limit: int = 20,
    streak_bonuses: Optional[dict[int, int]] = None,
    time_limit_ms: Optional[float] = None,
) -> ConveyorState:
    """
    Build a fresh ConveyorState with sensible defaults.

    Parameters
    ----------
    lesson_id          : Curriculum lesson number.
    active_cv          : Syllable strings in play (LearnerItem keys).
    challenge_sequence : Ordered list of challenge types. Defaults to a
                         balanced build/decompose rotation.
    turn_limit         : Number of questions before the session ends.
    streak_bonuses     : Bonus point thresholds. Defaults to {3:1, 5:2, 10:3}.
    time_limit_ms      : Per-question time limit. None = untimed.
    """
    if challenge_sequence is None:
        challenge_sequence = ["build_syllable", "decompose_syllable", "build_syllable", "decompose_syllable", "missing_vowel"]

    if streak_bonuses is None:
        streak_bonuses = {3: 1, 5: 2, 10: 3}

    return ConveyorState(
        game_id="conveyor",
        lesson_id=lesson_id,
        active_cv=active_cv,
        game_config={
            "turn_limit": turn_limit,
            "streak_bonuses": streak_bonuses,
        },
        challenge_sequence=challenge_sequence,
        time_limit_ms=time_limit_ms,
    )
