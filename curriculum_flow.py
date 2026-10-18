"""Event-driven controller for the ordinary curriculum's normal practice mode.

The terminal's scheduling lives in hangul_cli._interactive_loop_body. This
controller copies that scheduling, while lesson_flow owns the check, card, and
advance decisions. Events contain data only; callers provide all presentation.
"""

import json
import random
from dataclasses import asdict

from hangul_quiz_engine import QuizQuestion, ROMANIZATION
from lesson_flow import (AdvanceFlow, ReadingCheckFlow, round_card_choice,
                         round_card_events)
from reading_check import CHECK_SIZE, ReadingCheck


# hangul_cli.py:1953, :1962, and :1955 respectively.
ROUND_SIZE = 10
STUCK_AFTER_ROUNDS = 3
REWARD_EVERY = 10

# hangul_cli.py:1940-1945. These are notices on the eventual round card.
STREAK_MILESTONES = {
    10: "🔥 10 in a row! You're getting the hang of this.",
    25: "🚀 25 in a row! Your eyes are starting to read Hangul on their own.",
    50: "🏅 50 in a row! These letters are sticking.",
    100: "👑 100 in a row! 대박! (amazing!)",
}


def _tuples(value):
    """Restore tuples in random.getstate() after a JSON round trip."""
    if isinstance(value, list):
        return tuple(_tuples(item) for item in value)
    return value


class CurriculumFlow:
    """Drive one ordinary curriculum session, one learner action at a time."""

    def __init__(self, quiz):
        self.quiz = quiz
        self.phase = "new"
        self.current_question = None
        self.hint_used = False
        self.mastery_offered = set()
        self.check_requested = False
        self.round_no = 1
        self.round_asked = 0
        self.round_right = 0
        self.round_left = None
        self.round_solid = []
        self.round_milestones = []
        self.round_reward_earned = False
        self.card = None
        self.check = None
        self.advance = None
        self.outcome = None

    def start(self):
        if self.phase != "new":
            raise ValueError("The curriculum flow has already started.")
        info = self.quiz.start_lesson()
        self.phase = "practice"
        return [{"kind": "lesson_started", "lesson": info,
                 "message": None, "rich": True}, *self._next()]

    def submit(self, answer: str, active_ms: int = 0):
        if self.phase in ("new", "done") or self.outcome == "quit":
            raise ValueError("The curriculum flow is not accepting answers.")
        if not isinstance(active_ms, (int, float)) or active_ms < 0:
            raise ValueError("active_ms must be nonnegative.")
        answer = str(answer).strip()
        if self.phase == "check":
            events = self.check.submit(answer)
            if self.check.outcome == "quit":
                self.outcome = "quit"
                return [*events, {"kind": "finished", "outcome": "quit"}]
            if self.check.outcome == "passed":
                self.check = None
                self.advance = AdvanceFlow(self.quiz, self.quiz.current_lesson["id"])
                events.extend(self.advance.start())
                if self.advance.finished:
                    self.phase = "done"
                    self.outcome = "curriculum_complete"
                    events.append({"kind": "finished", "outcome": "curriculum_complete"})
                else:
                    self.phase = "advance"
                return events
            if self.check.outcome == "practice":
                self.check = None
                self.phase = "practice"
                return [*events, *self._next()]
            return events
        if self.phase == "round":
            choice = round_card_choice(self.card, answer)
            if choice == "quit":
                self.outcome = "quit"
                return [{"kind": "finished", "outcome": "quit"}]
            self.round_no += 1
            self.round_asked = self.round_right = 0
            self.card = None
            if choice == "check":
                self.check_requested = True
            if choice == "next":
                return self._next_lesson()
            return self._next()
        if self.phase == "advance":
            if answer == "/quit":
                self.outcome = "quit"
                return [{"kind": "finished", "outcome": "quit"}]
            events = self.advance.submit(answer)
            if self.advance.finished:
                info = self.advance.lesson_info
                self.advance = None
                self.phase = "practice"
                if info is not None:
                    self._reset_round()
                events.extend(self._next())
            return events
        return self._submit_practice(answer, active_ms)

    def resume(self, reason: str):
        """Recreate the pending screen without advancing or grading anything."""
        if reason not in ("reopen", "pause"):
            raise ValueError("reason must be reopen or pause")
        if self.phase == "new":
            return self.start()
        if self.phase == "done":
            return [{"kind": "finished", "outcome": self.outcome}]
        self.outcome = None  # Quitting ends an invocation, not the saved lesson.
        if self.check is not None and self.check.outcome == "quit":
            self.check.outcome = None
        if self.phase == "practice":
            return [self._question_event()]
        if self.phase == "round":
            return [self.card, {"kind": "round_prompt"}]
        if self.phase == "advance":
            return [{"kind": "advance_prompt",
                     "lesson_id": self.advance.lesson_id + 1}]
        if self.phase == "check":
            check = self.check
            events = []
            if check.phase == "question":
                q = check.check.current
                events.append({"kind": "check_question", "letter": q.letter,
                               "number": check.check.index + 1,
                               "size": CHECK_SIZE,
                               "transfer": q.letter in check.check.transfer_targets,
                               "retry": check.check.index >= CHECK_SIZE})
                if check.assisted:
                    events.append({"kind": "check_hint", "hint": q.hint})
            elif check.phase == "practice":
                q = check.practice[0]
                events.append({"kind": "check_practice_question",
                               "letter": q.letter, "hint": q.hint})
            events.append({"kind": "check_input", "phase": check.phase})
            return events
        raise ValueError(f"Unknown curriculum phase: {self.phase}")

    def export_state(self):
        """Save the controller and engine as one JSON string for local storage."""
        check = None
        if self.check is not None:
            check = {"phase": self.check.phase, "assisted": self.check.assisted,
                     "outcome": self.check.outcome,
                     "practice": [asdict(q) for q in self.check.practice],
                     "check": None}
            if self.check.check is not None:
                c = self.check.check
                check["check"] = {
                    "lesson_id": c.lesson_id,
                    "questions": [asdict(q) for q in c.questions],
                    "transfer_targets": list(c.transfer_targets),
                    "index": c.index, "correct": list(c.correct),
                    "missed": {key: asdict(q) for key, q in c.missed.items()},
                    "retried": list(c.retried),
                }
        advance = None
        if self.advance is not None:
            advance = {"lesson_id": self.advance.lesson_id,
                       "finished": self.advance.finished,
                       "lesson_info": self.advance.lesson_info}
        progress = self.quiz.export_state()
        session_keys = ("session_streak", "session_correct", "session_total",
                        "session_skips", "session_best_streak", "_saved_total",
                        "_saved_correct", "_last_asked", "_comeback")
        state = {
            "version": 1, "quiz": progress,
            "rng_state": random.getstate(),
            "lesson_id": (self.quiz.current_lesson["id"]
                          if self.quiz.current_lesson else None),
            "session": {key: getattr(self.quiz, key) for key in session_keys},
            "phase": self.phase, "outcome": self.outcome,
            "current_question": (asdict(self.current_question)
                                 if self.current_question else None),
            "hint_used": self.hint_used,
            "mastery_offered": sorted(self.mastery_offered),
            "check_requested": self.check_requested,
            "round_no": self.round_no, "round_asked": self.round_asked,
            "round_right": self.round_right, "round_left": self.round_left,
            "round_solid": self.round_solid,
            "round_milestones": self.round_milestones,
            "round_reward_earned": self.round_reward_earned,
            "card": self.card, "check": check, "advance": advance,
        }
        return json.dumps(state, ensure_ascii=False)

    @classmethod
    def from_state(cls, quiz, text):
        """Restore a saved flow; reject missing or incompatible state."""
        try:
            state = json.loads(text)
            if (not isinstance(state, dict) or type(state["version"]) is not int
                    or state["version"] != 1):
                raise ValueError("Unsupported curriculum state version.")
            phase = state["phase"]
            if phase not in ("new", "practice", "round", "check", "advance", "done"):
                raise ValueError("Unknown curriculum phase.")
            quiz.import_state(state["quiz"])
            if state["lesson_id"] is not None:
                quiz.start_lesson(state["lesson_id"])
            session_keys = ("session_streak", "session_correct", "session_total",
                            "session_skips", "session_best_streak", "_saved_total",
                            "_saved_correct", "_last_asked", "_comeback")
            session = state["session"]
            if not isinstance(session, dict) or set(session) != set(session_keys):
                raise ValueError("Incomplete curriculum session.")
            for key in session_keys:
                value = session[key]
                setattr(quiz, key, tuple(value) if key == "_last_asked" else value)
            flow = cls(quiz)
            flow.phase = phase
            flow.outcome = state["outcome"]
            q = state["current_question"]
            flow.current_question = QuizQuestion(**q) if q else None
            flow.hint_used = state["hint_used"]
            flow.mastery_offered = set(state["mastery_offered"])
            flow.check_requested = state["check_requested"]
            for key in ("round_no", "round_asked", "round_right", "round_left",
                        "round_solid", "round_milestones", "round_reward_earned",
                        "card"):
                setattr(flow, key, state[key])
            if state["check"] is not None:
                saved = state["check"]
                flow.check = ReadingCheckFlow(quiz)
                flow.check.phase = saved["phase"]
                flow.check.assisted = saved["assisted"]
                flow.check.outcome = saved["outcome"]
                flow.check.practice = [QuizQuestion(**q) for q in saved["practice"]]
                c = saved["check"]
                if c is not None:
                    flow.check.check = ReadingCheck(
                        c["lesson_id"], [QuizQuestion(**q) for q in c["questions"]],
                        c["transfer_targets"], c["index"], set(c["correct"]),
                        {key: QuizQuestion(**q) for key, q in c["missed"].items()},
                        set(c["retried"]))
            if state["advance"] is not None:
                saved = state["advance"]
                flow.advance = AdvanceFlow(quiz, saved["lesson_id"])
                flow.advance.finished = saved["finished"]
                flow.advance.lesson_info = saved["lesson_info"]
            if ((phase == "practice" and flow.current_question is None)
                    or (phase == "round" and not isinstance(flow.card, dict))
                    or (phase == "advance" and flow.advance is None)
                    or (phase == "check" and (flow.check is None
                        or flow.check.phase not in ("question", "practice", "retry")
                        or flow.check.phase == "question" and
                        (flow.check.check is None or flow.check.check.current is None)
                        or flow.check.phase == "practice" and not flow.check.practice))
                    or (phase == "done" and flow.outcome is None)):
                raise ValueError("Incomplete curriculum phase.")
            random.setstate(_tuples(state["rng_state"]))
            return flow
        except (KeyError, TypeError, ValueError, AttributeError, IndexError) as exc:
            raise ValueError("Curriculum state could not be restored.") from exc

    def _submit_practice(self, answer, active_ms):
        question = self.current_question
        if answer == "/quit":
            self.quiz.save_progress()
            self.outcome = "quit"
            return [{"kind": "finished", "outcome": "quit"}]
        if answer == "/next":
            return self._next_lesson()
        if answer == "/check":
            if (self.quiz.lesson_mastery()["is_mastered"]
                    or self.quiz.current_lesson["id"] in self.quiz.progress["completed_lessons"]):
                self.check_requested = True
                self.current_question = None
                return self._next()
            return [{"kind": "notice", "text": "Make the lesson items solid first, then try /check."}]
        if answer == "/hint":
            if question.hint:
                self.hint_used = True
                return [{"kind": "hint", "text": question.hint}]
            return [{"kind": "notice", "text": "No hint for this one — you can /skip to see the answer."}]
        if answer == "/skip":
            self.quiz.record_skip(question)
            self.quiz.save_progress()
            self.current_question = None
            self.round_asked += 1
            return [{"kind": "result", "correct": False, "skipped": True,
                     "correct_answer": question.correct_answer,
                     "letter": question.letter}, *self._next()]
        if answer.startswith("/"):
            return [{"kind": "notice", "text": "That command is unavailable here."}]
        if not answer:
            return [{"kind": "notice", "text": "Blank answer; try /hint or /skip."}]
        nudge = self.quiz.script_mismatch(answer, question)
        if nudge:
            return [{"kind": "notice", "text": nudge}]
        left_before = self.quiz.unmastered_items()
        result = self.quiz.answer(answer, question, response_ms=active_ms,
                                  assisted=self.hint_used)
        streak = self.quiz.session_streak
        if result.correct and streak in STREAK_MILESTONES:
            self.round_milestones.append(STREAK_MILESTONES[streak])
        if result.correct and streak > 0 and streak % REWARD_EVERY == 0:
            self.round_reward_earned = True
        self.round_solid.extend(x for x in left_before
                                if x not in self.quiz.unmastered_items())
        self.quiz.save_progress()
        self.current_question = None
        self.round_asked += 1
        self.round_right += result.correct
        return [{"kind": "result", **asdict(result), "skipped": False,
                 "assisted": self.hint_used}, *self._next()]

    def _next(self):
        lid = self.quiz.current_lesson["id"]
        ready = self.quiz.lesson_mastery(lid)["is_mastered"]
        if (self.check_requested or
                (ready and lid not in self.quiz.progress["completed_lessons"]
                 and lid not in self.mastery_offered)):
            self.check_requested = False
            self.mastery_offered.add(lid)
            self.check = ReadingCheckFlow(self.quiz)
            self.phase = "check"
            events = self.check.start()
            if self.check.outcome is not None:
                self.check = None
                self.phase = "practice"
                events.extend(self._next())
            return events
        if self.current_question is None and self.round_asked >= ROUND_SIZE:
            events = round_card_events(
                self.quiz, self.round_no, self.round_right, self.round_asked,
                no_progress=len(self.quiz.unmastered_items()) >= (self.round_left or 0),
                solid_now=self.round_solid, milestones=self.round_milestones,
                reward_earned=self.round_reward_earned,
                stuck_after_rounds=STUCK_AFTER_ROUNDS)
            self.round_reward_earned = False
            self.card = events[0]
            self.phase = "round"
            return events
        if self.current_question is None:
            if self.round_asked == 0:
                self.round_left = len(self.quiz.unmastered_items())
            self.current_question = self.quiz.next_question()
            self.hint_used = False
        self.phase = "practice"
        return [self._question_event()]

    def _question_event(self):
        q = self.current_question
        event = {"kind": "question", "mode": q.mode, "prompt": q.prompt,
                 "choices": list(q.choices),
                 "input": "choice" if q.choices else "text",
                 "hint_available": bool(q.hint),
                 "round": {"index": self.round_asked + 1, "size": ROUND_SIZE}}
        lesson_one_reading_prompts = {
            "read_aloud": "How does this block sound? Type it in English letters.",
            "real_word": "A real Korean word! How does it sound? Type it in English letters.",
            "nonword_decode": "These blocks are not a real word. Read them in English letters.",
            "sequence_decode": "Read this whole sequence in English letters.",
        }
        if q.lesson_id == 1 and q.mode in lesson_one_reading_prompts:
            event["prompt"] = lesson_one_reading_prompts[q.mode]
            event["display"] = q.letter
        return event

    def _reset_round(self):
        self.current_question = None
        self.round_no, self.round_asked, self.round_right = 1, 0, 0
        self.round_left = None
        self.round_solid.clear()
        self.round_milestones.clear()

    def _next_lesson(self):
        lid = self.quiz.current_lesson["id"]
        if lid >= len(self.quiz.curriculum["lessons"]):
            return [{"kind": "notice", "text": "This is the last lesson — there is no next one."}]
        message = None
        if (lid not in self.quiz.progress["completed_lessons"]
                and self.quiz.lesson_mastery(lid)["is_mastered"]
                and self.quiz.reading_check_passed(lid)):
            message = self.quiz.complete_lesson()
            info = self.quiz.start_lesson(self.quiz.progress["current_lesson"])
        else:
            info = self.quiz.start_lesson(lid + 1)
        self._reset_round()
        return [{"kind": "lesson_started", "lesson": info,
                 "message": message, "rich": True}, *self._next()]


class LessonOneTeaching:
    """Small, ungraded Lesson 1 guide. Python owns its steps and content.

    The ordinary CurriculumFlow has already selected the first practice
    question. The web view holds that question while this guide is active.
    """

    def __init__(self, lesson, mnemonics=None):
        if lesson.get("id") != 1:
            raise ValueError("This guide is only for Lesson 1.")
        self.lesson = lesson
        self.mnemonics = mnemonics or {}
        self.letters = list(lesson["letters"])
        self.syllables = dict(zip(self.letters, lesson["mastery_syllables"]))
        if len(self.letters) != 6 or len(self.syllables) != 6:
            raise ValueError("Lesson 1 must have six vowel examples.")
        self.phase = "intro"
        self.choice = None
        self.selected = None

    def current(self):
        base = {"speaker": "jeong", "pose": "hello", "lesson_id": 1}
        if self.phase == "intro":
            return {**base, "kind": "teaching_intro",
                    "dialogue": "I’m Jeong—roughly “juhng.” The eo in my name represents one vowel sound, not “ee-oh.” We’ll learn it in this lesson."}
        if self.phase == "predict":
            return {**base, "kind": "teaching_predict",
                    "dialogue": "Look at these two blocks. They share one shape.",
                    "blocks": [self.syllables["ㅏ"], self.syllables["ㅓ"]],
                    "prompt": "Which shape appears in both blocks?",
                    "choices": [{"value": "ㅇ", "label": "ㅇ"},
                                {"value": "different", "label": "ㅏ and ㅓ"}]}
        if self.phase == "feedback":
            return {**base, "kind": "teaching_feedback",
                    "correct": self.choice == "ㅇ",
                    "dialogue": "The shared ㅇ is silent at the start. The vowel gives each block its sound.",
                    "blocks": [self.syllables["ㅏ"], self.syllables["ㅓ"]],
                    "explanation": "아 sounds like ‘ah’. 어 sounds like ‘uh’."}
        if self.phase == "explore":
            letters = [{"jamo": letter, "syllable": self.syllables[letter],
                        "roman": ROMANIZATION[letter],
                        "sound": self.lesson["pronunciation"][letter],
                        "memory": self.mnemonics.get(letter, "")}
                       for letter in self.letters]
            return {**base, "kind": "teaching_explore",
                    "dialogue": "Meet six vowels. Tap one for a memory cue, then start practice.",
                    "letters": letters, "selected": self.selected}
        return {"kind": "teaching_done", "lesson_id": 1}

    def submit(self, action):
        action = str(action)
        if self.phase == "done":
            raise ValueError("Lesson 1 teaching is finished.")
        if action == "/skip":
            self.phase = "done"
        elif self.phase == "intro" and action == "/continue":
            self.phase = "predict"
        elif self.phase == "predict" and action in ("ㅇ", "different"):
            self.choice = action
            self.phase = "feedback"
        elif self.phase == "feedback" and action == "/continue":
            self.phase = "explore"
            self.selected = None
        elif self.phase == "explore" and action in self.letters:
            self.selected = action
        elif self.phase == "explore" and action == "/practice":
            self.phase = "done"
        else:
            raise ValueError("Invalid Lesson 1 teaching action.")
        return self.current()

    def export_state(self):
        return json.dumps({"phase": self.phase, "choice": self.choice,
                           "selected": self.selected}, ensure_ascii=False)

    @classmethod
    def from_state(cls, lesson, mnemonics, text):
        state = json.loads(text)
        guide = cls(lesson, mnemonics)
        phase, choice, selected = state["phase"], state["choice"], state["selected"]
        if (phase not in ("intro", "predict", "feedback", "explore", "done")
                or choice not in (None, "ㅇ", "different")
                or selected not in (None, *guide.letters)
                or phase in ("intro", "predict") and (choice is not None or selected is not None)
                or phase == "feedback" and (choice is None or selected is not None)
                or phase == "explore" and choice is None):
            raise ValueError("Invalid Lesson 1 teaching state.")
        guide.phase, guide.choice, guide.selected = phase, choice, selected
        return guide
