"""Short independent reading checks, separate from practice/mastery scoring."""

from dataclasses import dataclass, field
from itertools import product
import random

from hangul_quiz_engine import QuizQuestion, normalize_roman


CHECK_SIZE = 5
PASS_SCORE = 4


@dataclass
class ReadingCheck:
    lesson_id: int
    questions: list[QuizQuestion]
    transfer_targets: list[str]
    index: int = 0
    correct: set[str] = field(default_factory=set)
    missed: dict[str, QuizQuestion] = field(default_factory=dict)
    retried: set[str] = field(default_factory=set)

    @property
    def finished(self):
        return self.index >= len(self.questions)

    @property
    def passed(self):
        return self.finished and len(self.correct) >= PASS_SCORE

    @property
    def current(self):
        return None if self.finished else self.questions[self.index]

    def submit(self, answer, assisted=False, skipped=False):
        """Grade without altering practice scores. Each hinted item returns once.

        A repeat hint cannot create an endless check. Wrong independent answers
        go to the follow-up practice, rather than being drilled until they pass.
        """
        q = self.current
        if q is None:
            raise ValueError("The reading check is finished.")
        right = not skipped and normalize_roman(answer) in set(q.accepted)
        if right and not assisted:
            self.correct.add(q.letter)
            self.missed.pop(q.letter, None)
        else:
            self.missed[q.letter] = q
        if assisted and q.letter not in self.retried:
            self.retried.add(q.letter)
            self.questions.append(q)
        self.index += 1
        return right


def _features(quiz, target, lesson):
    """Spread representative items across new letters / final consonants."""
    focus = set(lesson.get("letters", []))
    final_lesson = lesson["id"] >= 10
    out = set()
    for ch in target:
        cho, jung, jong = quiz._decompose_syllable(ch)
        for position, value in (("initial", cho), ("vowel", jung)):
            if value in focus:
                out.add((position, value))
        if final_lesson and jong:
            out.add(("final", jong))
    return out


def _representatives(quiz, pool, lesson, count):
    remaining = list(dict.fromkeys(pool))
    random.shuffle(remaining)
    chosen, covered = [], set()
    while remaining and len(chosen) < count:
        target = max(remaining, key=lambda s: len(_features(quiz, s, lesson) - covered))
        chosen.append(target)
        covered.update(_features(quiz, target, lesson))
        remaining.remove(target)
    return chosen


def make_reading_check(quiz):
    """Three lesson items and two previously unpractised combinations.

    New blocks recombine only components from the current lesson's pool.
    When that is impossible (e.g. six vowel-only blocks), use new two-block
    sequences. Boundaries use the engine's existing pronunciation guard.
    These are labelled combinations, not promised to be real Korean words.
    """
    lesson = quiz.current_lesson
    if lesson is None:
        raise ValueError("Choose a lesson first.")
    pool = quiz._mastery_set(lesson)
    familiar = _representatives(quiz, pool, lesson, 3)
    if len(familiar) != 3:
        raise ValueError("This lesson needs at least three reading targets.")
    blocks = list(dict.fromkeys(quiz._get_lesson_syllable_pool(lesson)))
    parts = [quiz._decompose_syllable(s) for s in blocks if len(s) == 1]
    parts = [p for p in parts if p[0] and p[1]]
    seen = set(quiz.progress.get("learner_items", {}))
    seen.update(quiz.progress.get("reading_check_seen", []))
    # A custom lesson is not in the curriculum loop below, but its own
    # practice targets still cannot count as new transfer combinations.
    seen.update(pool)
    seen.update(quiz._get_lesson_syllable_pool(lesson))
    for prior in quiz.curriculum["lessons"]:
        if prior["id"] <= lesson["id"]:
            seen.update(quiz._get_lesson_syllable_pool(prior))
            seen.update(quiz._mastery_set(prior))
    # Also exclude blocks already encountered inside words/sequences.
    seen_blocks = {ch for target in seen for ch in target}
    candidates = []
    if parts:
        initials = sorted({p[0] for p in parts})
        vowels = sorted({p[1] for p in parts})
        finals = sorted({p[2] for p in parts})
        for cho, jung, jong in product(initials, vowels, finals):
            block = quiz._compose_syllable(cho, jung, jong)
            if block not in seen_blocks:
                candidates.append(block)
    transfer = _representatives(quiz, candidates, lesson, 2)
    if len(transfer) < 2:
        for length in (2, 3):
            sequences = ["".join(chars) for chars in product(blocks, repeat=length)
                         if len(set(chars)) > 1 and "".join(chars) not in seen
                         and quiz._safe_nonword_boundaries("".join(chars), lesson)]
            random.shuffle(sequences)
            # Prefer sequences not identified as existing words by the corpus.
            sequences.sort(key=lambda s: s in quiz.known_lexical_items
                           or s in quiz.corpus_seen_bigrams)
            transfer.extend(sequences[:2 - len(transfer)])
            if len(transfer) == 2:
                break
    if len(transfer) != 2:
        raise ValueError("No new safe combinations remain for this lesson.")
    vocabulary = {entry["word"]: entry for entry in
                  lesson.get("vocabulary", []) + lesson.get("words", [])}
    questions = []
    for target in familiar + transfer:
        entry = vocabulary.get(target, {})
        accepted = quiz.roman_variants(target)
        accepted.update(normalize_roman(s) for s in
                        entry.get("accepted_romanizations", []) + entry.get("also", []))
        questions.append(QuizQuestion(
            mode="read_aloud", letter=target, lesson_id=lesson["id"],
            prompt=f"How does **{target}** sound? Type it in English letters.",
            correct_answer=quiz._word_romanization(target),
            accepted=sorted(accepted), choices=[],
            hint=" / ".join(quiz._piece_hint(ch) for ch in target),
        ))
    return ReadingCheck(lesson["id"], questions, transfer)


def save_check_result(quiz, check):
    """Store only completed checks; preserve old completed lessons and schema."""
    if not check.finished:
        return
    records = quiz.progress.setdefault("reading_checks", {})
    previous = records.get(str(check.lesson_id), {})
    records[str(check.lesson_id)] = {
        "passed": bool(previous.get("passed") or check.passed),
        "last_score": len(check.correct), "out_of": CHECK_SIZE,
        "attempts": previous.get("attempts", 0) + 1,
        "targets": [q.letter for q in check.questions[:CHECK_SIZE]],
        "transfer_targets": check.transfer_targets,
    }
    if (check.passed
            and any(lesson["id"] == check.lesson_id for lesson in quiz.curriculum["lessons"])
            and check.lesson_id not in quiz.progress["completed_lessons"]):
        quiz.progress["completed_lessons"].append(check.lesson_id)
    quiz.save_progress()
