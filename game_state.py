"""
game_state.py — Serializable game state for hangul-tutor CV games.

Architecture boundary
---------------------
GameState describes what is happening in the game.
LearnerItem (in hangul_quiz_engine.py) describes what the learner knows.
QuizResult describes what just happened in a single attempt.

GameState.last_question / last_result are session-history snapshots only.
The game must not reconstruct learner mastery from them — that is the
quiz engine's job.

Game logic should call next_question() / answer() on the engine and then
update GameState; it should not bypass the engine to compute mastery itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_OUTCOMES = {"complete", "player", "cpu", "draw"}
# "complete" — solo drill finished all turns (Conveyor)
# "player"   — player won a competitive game (Territory)
# "cpu"      — cpu won a competitive game (Territory)
# "draw"     — neither side won (Territory)

# Valid challenge types for ConveyorState.challenge_sequence.
# Extend this as new question modes are wired into the games.
VALID_CHALLENGE_TYPES = {"build_syllable", "decompose_syllable", "missing_vowel", "read_aloud", "spell"}


# ---------------------------------------------------------------------------
# Base game state
# ---------------------------------------------------------------------------

@dataclass
class GameState:
    """
    Shared state for all CV games.

    Fields
    ------
    game_id         : Identifies which game is running ("conveyor", "territory", …).
    lesson_id       : The curriculum lesson this session is drawing from.
    active_cv       : Syllable strings in play this session. These are stable
                      LearnerItem keys — the engine is the source of truth for
                      what each syllable means; this list is a reference, not a
                      second definition.
    game_config     : Configuration set before the game starts and not changed
                      during play. Examples: difficulty label, romanization toggle.
                      If something changes as the game progresses, it belongs in
                      a runtime field, not here.
    score           : Points accumulated this session.
    turn            : Number of prompts presented so far.
    streak          : Current consecutive-correct streak.
    last_question   : Snapshot of the most recent QuizQuestion (as a plain dict),
                      for UI rendering. Session history only — not authoritative.
    last_result     : Snapshot of the most recent QuizResult (as a plain dict),
                      for UI rendering. Session history only — not authoritative.
    done            : True once the game has reached a terminal state.
    outcome         : Set by set_terminal(). One of VALID_OUTCOMES, or None while
                      the game is still in progress.
    state_version   : Incremented when the shape of this dataclass changes, so
                      old serialized states can be detected and handled gracefully.
    """

    game_id: str
    lesson_id: int
    active_cv: list[str] = field(default_factory=list)
    game_config: dict = field(default_factory=dict)

    # Runtime
    score: int = 0
    turn: int = 0
    streak: int = 0
    best_streak: int = 0

    # Last interaction snapshot (UI/session history only)
    last_question: Optional[dict] = None
    last_result: Optional[dict] = None

    # Terminal state
    done: bool = False
    outcome: Optional[str] = None

    state_version: int = 1

    # ------------------------------------------------------------------
    # Terminal state
    # ------------------------------------------------------------------

    def set_terminal(self, outcome: str) -> None:
        """
        Mark the game as finished.

        Parameters
        ----------
        outcome : One of VALID_OUTCOMES ("complete", "player", "cpu", "draw").
                  Use "complete" for solo drills that end after a fixed turn
                  count. Use "player"/"cpu"/"draw" for competitive games.

        Raises
        ------
        ValueError : If the game is already terminal, or if outcome is not
                     one of the recognised values.
        """
        if self.done:
            raise ValueError(
                f"Game is already terminal (outcome={self.outcome!r}). "
                "set_terminal() cannot be called twice."
            )
        if outcome not in VALID_OUTCOMES:
            raise ValueError(
                f"{outcome!r} is not a valid outcome. "
                f"Expected one of: {sorted(VALID_OUTCOMES)}"
            )
        self.done = True
        self.outcome = outcome

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "game_id": self.game_id,
            "lesson_id": self.lesson_id,
            "active_cv": list(self.active_cv),
            "game_config": dict(self.game_config),
            "score": self.score,
            "turn": self.turn,
            "streak": self.streak,
            "best_streak": self.best_streak,
            "last_question": self.last_question,
            "last_result": self.last_result,
            "done": self.done,
            "outcome": self.outcome,
            "state_version": self.state_version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameState":
        return cls(
            game_id=data["game_id"],
            lesson_id=data["lesson_id"],
            active_cv=data.get("active_cv", []),
            game_config=data.get("game_config", {}),
            score=data.get("score", 0),
            turn=data.get("turn", 0),
            streak=data.get("streak", 0),
            last_question=data.get("last_question"),
            last_result=data.get("last_result"),
            done=data.get("done", False),
            outcome=data.get("outcome"),
            state_version=data.get("state_version", 1),
        )


# ---------------------------------------------------------------------------
# Conveyor Belt Sorter
# ---------------------------------------------------------------------------

@dataclass
class ConveyorState(GameState):
    """
    State for the Conveyor Belt Sorter game.

    The conveyor presents a sequence of challenges, one at a time.
    Each challenge type maps to a quiz engine question mode; the engine
    generates the actual question — ConveyorState only tracks position
    in the sequence.

    Fields
    ------
    challenge_sequence : Ordered list of challenge type strings drawn from
                         VALID_CHALLENGE_TYPES. Determines what kind of
                         question the engine is asked for at each turn.
                         Set once at game start; does not change during play.
    challenge_index    : Index into challenge_sequence for the current turn.
                         Advances by 1 after each answer; wraps or terminates
                         depending on game logic.
    time_limit_ms      : Per-question time limit in milliseconds. None = untimed.
                         Lives here (not in game_config) because timing affects
                         runtime game behaviour, not just initial configuration.
    """

    challenge_sequence: list[str] = field(default_factory=list)
    challenge_index: int = 0
    time_limit_ms: Optional[float] = None

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def current_challenge(self) -> Optional[str]:
        """The challenge type for the current turn, or None if the sequence
        is exhausted."""
        if self.challenge_index < len(self.challenge_sequence):
            return self.challenge_sequence[self.challenge_index]
        return None

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "challenge_sequence": list(self.challenge_sequence),
            "challenge_index": self.challenge_index,
            "time_limit_ms": self.time_limit_ms,
        })
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ConveyorState":
        # JSON only allows string keys, so streak_bonuses round-trips as
        # {"3": 1, "5": 2, "10": 3}. Re-cast to int keys here so the rest
        # of the game logic always sees {3: 1, 5: 2, 10: 3}.
        config = dict(data.get("game_config", {}))
        if "streak_bonuses" in config:
            config["streak_bonuses"] = {
                int(k): v for k, v in config["streak_bonuses"].items()
            }

        obj = cls(
            game_id=data["game_id"],
            lesson_id=data["lesson_id"],
            active_cv=data.get("active_cv", []),
            game_config=config,
            score=data.get("score", 0),
            turn=data.get("turn", 0),
            streak=data.get("streak", 0),
            best_streak=data.get("best_streak", 0),
            last_question=data.get("last_question"),
            last_result=data.get("last_result"),
            done=data.get("done", False),
            outcome=data.get("outcome"),
            state_version=data.get("state_version", 1),
            challenge_sequence=data.get("challenge_sequence", []),
            challenge_index=data.get("challenge_index", 0),
            time_limit_ms=data.get("time_limit_ms"),
        )
        return obj
