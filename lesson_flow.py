"""UI-independent lesson flow for reading checks, round cards, and advancing.

Each step returns plain dictionaries. A caller renders the events and supplies
the next answer; no terminal input, printing, colors, or wrapping live here.
"""

from hangul_quiz_engine import normalize_roman
import reading_check

CHECK_SIZE = reading_check.CHECK_SIZE
PASS_SCORE = reading_check.PASS_SCORE


class ReadingCheckFlow:
    def __init__(self, quiz):
        self.quiz = quiz
        self.check = None
        self.phase = "new"
        self.assisted = False
        self.practice = []
        self.outcome = None

    def start(self):
        return self._with_prompt([
            {"kind": "check_intro", "size": CHECK_SIZE, "pass_score": PASS_SCORE},
            *self._new_check(),
        ])

    def _with_prompt(self, events):
        if self.outcome is None:
            events.append({"kind": "check_input", "phase": self.phase})
        return events

    def _new_check(self):
        try:
            self.check = reading_check.make_reading_check(self.quiz)
        except ValueError as error:
            self.outcome = "practice"
            return [{"kind": "check_unavailable", "reason": str(error)}]
        return self._question()

    def _question(self):
        q = self.check.current
        seen = self.quiz.progress.setdefault("reading_check_seen", [])
        if q.letter not in seen:
            seen.append(q.letter)
            self.quiz.save_progress()
        self.phase = "question"
        self.assisted = False
        return [{"kind": "check_question", "letter": q.letter,
                 "number": self.check.index + 1,
                 "size": CHECK_SIZE,
                 "transfer": q.letter in self.check.transfer_targets,
                 "retry": self.check.index >= CHECK_SIZE}]

    def submit(self, answer):
        if self.outcome is not None:
            raise ValueError("The reading check has ended.")
        if self.phase == "question":
            events = self._answer_question(answer)
        elif self.phase == "practice":
            events = self._answer_practice(answer)
        elif self.phase == "retry":
            events = self._answer_retry(answer)
        else:
            raise ValueError("Start the reading check before answering.")
        return self._with_prompt(events)

    def _leave(self, answer):
        if answer is None or answer.lower() in ("/quit", "/q", "/exit"):
            self.quiz.save_progress()
            self.outcome = "quit"
        elif answer.lower() in ("/back", "/practice"):
            self.outcome = "practice"
        return self.outcome is not None

    def _answer_question(self, answer):
        if self._leave(answer):
            return []
        q = self.check.current
        command = answer.lower()
        if command in ("/hint", "/h"):
            self.assisted = True
            return [{"kind": "check_hint", "hint": q.hint}]
        if not answer:
            return []
        skipped = command == "/skip"
        if command.startswith("/") and not skipped:
            return [{"kind": "check_commands"}]
        if not skipped and self.quiz.script_mismatch(answer, q):
            return [{"kind": "check_script_mismatch"}]
        correct = self.check.submit("" if skipped else answer,
                                    assisted=self.assisted and not skipped,
                                    skipped=skipped)
        result = {"kind": "check_feedback", "letter": q.letter,
                  "correct_answer": q.correct_answer, "answer": answer,
                  "assisted": self.assisted, "skipped": skipped,
                  "correct": correct}
        return [result, *(self._finish() if self.check.finished else self._question())]

    def _finish(self):
        reading_check.save_check_result(self.quiz, self.check)
        events = [{"kind": "check_score", "correct": len(self.check.correct),
                   "size": CHECK_SIZE, "pass_score": PASS_SCORE,
                   "passed": self.check.passed}]
        if self.check.passed:
            self.outcome = "passed"
            return events
        self.practice = list(self.check.missed.values())[:3]
        events.append({"kind": "check_practice_intro"})
        events.extend(self._next_practice())
        return events

    def _next_practice(self):
        if self.practice:
            self.phase = "practice"
            q = self.practice[0]
            return [{"kind": "check_practice_question", "letter": q.letter,
                     "hint": q.hint}]
        self.phase = "retry"
        return []

    def _answer_practice(self, answer):
        if self._leave(answer):
            return []
        q = self.practice.pop(0)
        result = {"kind": "check_practice_feedback", "letter": q.letter,
                  "correct_answer": q.correct_answer,
                  "correct": normalize_roman(answer) in q.accepted}
        return [result, *self._next_practice()]

    def _answer_retry(self, answer):
        if self._leave(answer):
            return []
        if answer.lower() not in ("r", "/check"):
            self.outcome = "practice"
            return []
        return self._new_check()


def round_card_events(quiz, round_no, right, asked, *, no_progress=False,
                      solid_now=None, milestones=None, reward_earned=False,
                      stuck_after_rounds=3, terminal_llm_reward=False):
    """Return one serializable card event, including its allowed actions."""
    lid = quiz.current_lesson["id"]
    mastery = quiz.lesson_mastery()
    left = quiz.unmastered_items()
    done = lid in quiz.progress["completed_lessons"]
    ready = mastery["is_mastered"] and not done
    last = lid >= len(quiz.curriculum["lessons"])
    stuck = not done and not ready and no_progress and round_no >= stuck_after_rounds
    solid = list(dict.fromkeys(x for x in (solid_now or []) if quiz._is_solid(x)))
    if solid_now is not None:
        solid_now.clear()
    notices = list(milestones or [])
    if milestones is not None:
        milestones.clear()
    missed = [(quiz._get_item(x).wrong, x) for x in left]
    missed.sort(key=lambda pair: -pair[0])
    next_lesson = quiz._get_lesson(lid + 1) if (done or stuck) and not last else None
    reward = quiz.reward_word() if reward_earned and not terminal_llm_reward else None
    return [{"kind": "round_card", "round_no": round_no, "right": right,
             "asked": asked, "lesson_id": lid, "mastery": dict(mastery),
             "left": list(left), "done": done, "ready": ready,
             "stuck": stuck, "last": last, "solid_now": solid,
             "milestones": notices, "reward_earned": reward_earned,
             "reward": reward,
             "trouble": [x for wrong, x in missed[:3] if wrong > 0],
             "next_lesson": {"id": next_lesson["id"], "title": next_lesson["title"]}
             if next_lesson else None,
             "actions": (["check"] if ready or done else [])
                        + (["next"] if next_lesson else [])
                        + ["continue", "quit"]},
            {"kind": "round_prompt"}]


def round_card_choice(card, answer):
    """Map one input to an allowed round action."""
    if answer is None or answer.lower() in ("q", "/q", "quit", "/quit"):
        return "quit"
    choice = answer.lower()
    if (card["ready"] and choice in ("r", "/check")) or (card["done"] and choice == "/check"):
        return "check"
    if choice in ("n", "/next", "next") and "next" in card["actions"]:
        return "next"
    return "continue"


class AdvanceFlow:
    def __init__(self, quiz, lesson_id):
        self.quiz = quiz
        self.lesson_id = lesson_id
        self.finished = False
        self.lesson_info = None

    def start(self):
        if self.lesson_id not in self.quiz.progress["completed_lessons"]:
            self.finished = True
            return []
        mastery = self.quiz.lesson_mastery(self.lesson_id)
        try:
            lesson = self.quiz._get_lesson(self.lesson_id)
            words = lesson.get("words") or lesson.get("vocabulary") or []
        except ValueError:
            words = []
        events = [{"kind": "lesson_mastered", "mastered_count": mastery["mastered_count"],
                   "pool_size": mastery["pool_size"],
                   "words": [{"word": w["word"], "meaning": w.get("meaning", "")}
                             for w in words]}]
        if self.lesson_id >= len(self.quiz.curriculum["lessons"]):
            self.quiz.complete_lesson()
            self.finished = True
            events.append({"kind": "curriculum_complete"})
        else:
            events.append({"kind": "advance_prompt", "lesson_id": self.lesson_id + 1})
        return events

    def submit(self, answer):
        if self.finished:
            raise ValueError("The advance offer has ended.")
        total = len(self.quiz.curriculum["lessons"])
        if answer is None or answer.strip().lower() in ("n", "no"):
            self.finished = True
            return [{"kind": "advance_stay"}]
        value = answer.strip().lower()
        if value in ("", "y", "yes"):
            message = self.quiz.complete_lesson()
            self.lesson_info = self.quiz.start_lesson(self.quiz.progress["current_lesson"])
            self.finished = True
            return [{"kind": "lesson_started", "lesson": self.lesson_info,
                     "message": message, "rich": True}]
        parts = answer.split()
        command = parts[0].lstrip("/").lower() if parts else ""
        if command == "lesson" and len(parts) == 2 and parts[1].isdigit():
            number = int(parts[1])
            if 1 <= number <= total:
                self.lesson_info = self.quiz.start_lesson(number)
                self.finished = True
                return [{"kind": "lesson_started", "lesson": self.lesson_info,
                         "message": None, "rich": False}]
            return [{"kind": "advance_missing_lesson", "number": number,
                     "total": total},
                    {"kind": "advance_prompt", "lesson_id": self.lesson_id + 1}]
        if command == "lessons":
            return [{"kind": "advance_lessons", "lessons": self.quiz.list_lessons(),
                     "current_id": self.quiz.current_lesson["id"]},
                    {"kind": "advance_prompt", "lesson_id": self.lesson_id + 1}]
        return [{"kind": "advance_help"},
                {"kind": "advance_prompt", "lesson_id": self.lesson_id + 1}]
