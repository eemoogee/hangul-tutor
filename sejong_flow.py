"""UI-free, serializable Sejong Test slice. Renderers only display these events."""

import json
import random
from dataclasses import asdict

from hangul_quiz_engine import QuizQuestion, normalize_roman
from reading_check import ReadingCheck, make_reading_check, save_check_result, PASS_SCORE


def _tuples(value):
    if isinstance(value, list):
        return tuple(_tuples(item) for item in value)
    return value


class SejongFlow:
    def __init__(self, quiz, content, seed=None):
        self.quiz = quiz
        self.content = content
        self.rng = random.Random(seed)
        self.phase = "new"
        self.batch_index = 0
        self.letters_known = []
        self.active_ms = 0
        self.baseline_score = None
        self.post_score = None
        self.assessment_items = []
        self.assessment_correct = 0
        self.remaining = []
        self.round_size = 0
        self.round_index = 0
        self.qid_number = 0
        self.current = None
        self.current_engine_question = None
        self.screen = []
        self.assisted = False
        self.consecutive_wrong = 0
        self.repeated_miss_index = 0
        self.check = None
        self.check_results = {}
        self.check_practice = []
        self.streak = 0
        self.correct_line_index = 0
        self.last_correct_line = False
        self.words_read = []
        self.outcome = None

    def _line(self, path, **values):
        node = self.content
        for key in path.split("."):
            node = node[int(key)] if isinstance(node, list) else node[key]
        return {"kind": "narrator", "speaker": node["speaker"],
                "text": node["text"].format(**values), "line_id": path,
                "source": node["source"]}

    def _stage(self):
        batch = self.content["batches"][self.batch_index]
        return {"kind": "stage", "batch_id": batch["id"],
                "batch_name": batch["name"], "phase": self.phase,
                "letters_known": list(self.letters_known)}

    def _emit(self, events, prompt):
        last_card = next((event for event in reversed(events)
                          if event["kind"] in ("question", "predict")), None)
        if last_card is None:
            last_card = next((event for event in reversed(events)
                              if event["kind"] == "narrator"), None)
        self.screen = [self._stage()]
        if last_card is not None:
            self.screen.append(last_card)
        self.screen.append(prompt)
        return events + [prompt]

    def _finish(self, events):
        self.phase = "done"
        self.outcome = "victory_1"
        events.append(self._stage())
        events.append({"kind": "finished", "outcome": self.outcome})
        self.screen = events
        return events

    def _seed_engine(self):
        random.seed(self.rng.getrandbits(64))

    def _batch(self):
        return self.content["batches"][self.batch_index]

    def _known_blocks(self):
        consonants = [x for x in self.letters_known if self._letter(x)["type"] == "consonant"]
        vowels = [x for x in self.letters_known if self._letter(x)["type"] == "vowel"]
        return [self.quiz._compose_syllable(c, v) for c in consonants for v in vowels]

    def _letter(self, jamo):
        return next(letter for batch in self.content["batches"]
                    for letter in batch["letters"] if letter["jamo"] == jamo)

    def _custom_lesson(self):
        blocks = self._known_blocks()
        self.quiz.start_custom_lesson({"id": 0, "title": self._batch()["name"],
            "letters": list(self.letters_known), "practice_syllables": blocks,
            "mastery_syllables": blocks,
            "confusion_pairs": [p["pair"] for batch in self.content["batches"][:self.batch_index + 1]
                                for p in batch["confusion_pairs"]], "pronunciation": {}})

    def start(self):
        if self.phase != "new":
            raise ValueError("The Sejong Test has already started.")
        self.phase = "intro"
        events = [self._stage()]
        events += [self._line(f"lines.intro.{i}") for i in range(len(self.content["lines"]["intro"]))]
        events.append(self._line("lines.baseline_offer"))
        return self._emit(events, {"kind": "await", "input": "choice",
                                   "choices": ["Take the quick test", "Skip"]})

    def _assessment(self, phase):
        self.phase = phase
        self.assessment_items = [x["jamo"] for b in self.content["batches"] for x in b["letters"]]
        self.rng.shuffle(self.assessment_items)
        self.assessment_correct = 0
        return self._assessment_question([self._stage()])

    def _assessment_question(self, events):
        if not self.assessment_items:
            score = self.assessment_correct
            if self.phase == "baseline":
                self.baseline_score = score
                events.append({"kind": "score", "context": "baseline", "correct": score, "size": 8})
                if score == 0:
                    events.append(self._line("lines.baseline_zero"))
                return self._enter_batch(events)
            self.post_score = score
            events.append({"kind": "score", "context": "post_test", "correct": score,
                           "size": 8, "before": self.baseline_score})
            return self._victory(events)
        letter = self.assessment_items.pop(0)
        romans = [x["roman"] for b in self.content["batches"] for x in b["letters"]]
        answer = self._letter(letter)["roman"]
        choices = self.rng.sample([x for x in romans if x != answer], 3) + [answer]
        self.rng.shuffle(choices)
        return self._question(events, letter, "match_sound", answer,
                              "What sound does this letter make?", letter, "choice", choices,
                              context=self.phase, hint=False)

    def _enter_batch(self, events):
        batch = self._batch()
        self.phase = "discover"
        events.append(self._stage())
        if self.batch_index == 0:
            events.append(self._line("lines.clock_start"))
        events.append(self._line(f"lines.batch_intro.{batch['id']}"))
        for letter in batch["letters"]:
            intro = {"kind": "letter_intro", "jamo": letter["jamo"], "type": letter["type"],
                     "roman": letter["roman"], "sound": letter["sound"],
                     "shape": letter["shape"], "shape_source": letter["source"]}
            if "related" in letter:
                intro["related"] = letter["related"]
            if "notice_line" in letter:
                intro["notice_line"] = self._line_for_inline(letter["notice_line"],
                    f"batches.{self.batch_index}.letters.{batch['letters'].index(letter)}.notice_line")
            events.append(intro)
            self.letters_known.append(letter["jamo"])
        self._custom_lesson()
        return self._next_phase(events)

    def _line_for_inline(self, node, path):
        return {"kind": "narrator", "speaker": node["speaker"], "text": node["text"],
                "line_id": path, "source": node["source"]}

    def _next_phase(self, events):
        phases = self._batch()["phases"]
        if self.phase == "discover":
            next_index = 1
        else:
            next_index = phases.index(self.phase) + 1
        if next_index < len(phases):
            self.phase = phases[next_index]
            events.append(self._stage())
            if self.phase == "predict_reveal":
                return self._predict(events)
            return self._start_pool(events)
        return self._start_check(events)

    def _predict(self, events):
        p = self._batch()["predict_reveal"]
        options = self.rng.sample([x for x in self._known_blocks() if x != p["block"]], 2) + [p["block"]]
        self.rng.shuffle(options)
        self.current = {"kind": "predict", "target": p["block"], "choices": options}
        events.append(self._line("lines.predict_prompt", consonant=p["consonant"], vowel=p["vowel"]))
        events.append({"kind": "predict", "consonant": p["consonant"],
                       "vowel": p["vowel"], "choices": options})
        return self._emit(events, {"kind": "await", "input": "choice", "choices": options})

    def _start_pool(self, events):
        if self.phase in ("recognize", "retrieve"):
            self.remaining = [x["jamo"] for x in self._batch()["letters"]]
        elif self.phase == "build":
            new_letters = {x["jamo"] for x in self._batch()["letters"]}
            self.remaining = [block for block in self._known_blocks()
                              if any(part in new_letters for part in self.quiz._decompose_syllable(block)[:2])]
        elif self.phase == "decode":
            self.remaining = [x["ko"] for x in self._batch()["words"]]
        else:
            raise ValueError(self.phase)
        self.rng.shuffle(self.remaining)
        self.round_size = len(self.remaining)
        self.round_index = 0
        self.consecutive_wrong = 0
        return self._pool_question(events)

    def _build_choices(self, target):
        consonant, vowel, _ = self.quiz._decompose_syllable(target)
        blocks = self._known_blocks()
        same_consonant = [block for block in blocks if block != target
                          and self.quiz._decompose_syllable(block)[0] == consonant]
        same_vowel = [block for block in blocks if block != target
                      and self.quiz._decompose_syllable(block)[1] == vowel]
        choices = [target, self.rng.choice(same_consonant), self.rng.choice(same_vowel)]
        choices.append(self.rng.choice([block for block in blocks if block not in choices]))
        self.rng.shuffle(choices)
        return choices

    def _pool_question(self, events):
        if not self.remaining:
            if self.phase == "build" and self.batch_index == 0:
                events.append(self._milestone("first_breakthrough", "small",
                                              ["lines.first_breakthrough"]))
            return self._next_phase(events)
        target = self.remaining.pop(0)
        if self.phase == "recognize":
            letter = self._letter(target)
            options = [x["jamo"] for x in self.content["batches"][:self.batch_index + 1]
                       for x in x["letters"] if x["type"] == letter["type"]]
            choices = self.rng.sample([x for x in options if x != target], 3) + [target]
            self.rng.shuffle(choices)
            return self._question(events, target, "match_sound", target,
                "Which letter makes this sound?", letter["roman"], "choice", choices)
        if self.phase == "retrieve":
            return self._question(events, target, "read_aloud", self._letter(target)["roman"],
                                  "Type this letter's sound.", target, "text")
        if self.phase == "build":
            choices = self._build_choices(target)
            c, v, _ = self.quiz._decompose_syllable(target)
            return self._question(events, target, "build_syllable", target,
                                  "Which block do these letters build?", f"{c} + {v}",
                                  "choice", choices, parts=[c, v])
        return self._question(events, target, "read_aloud", self.quiz._word_romanization(target),
                              "How do you read this?", target, "text")

    def _question(self, events, target, mode, answer, prompt, display, input_type,
                  choices=None, context="practice", hint=True, parts=None):
        self.qid_number += 1
        qid = f"b{self.batch_index}-{self.phase}-{self.qid_number}"
        card = {"kind": "question", "qid": qid, "context": context, "mode": mode,
                "prompt": prompt, "display": display, "input": input_type,
                "hint_available": hint}
        if choices is not None:
            card["choices"] = choices
        if parts is not None:
            card["parts"] = parts
        if context in ("practice", "check_practice"):
            card["round"] = {"index": self.round_index + 1, "size": self.round_size}
        self.current = {"kind": "question", "target": target, "answer": answer,
                        "context": context, "card": card}
        self.assisted = False
        self.current_engine_question = QuizQuestion(mode=mode, prompt=prompt, letter=target,
            correct_answer=answer, choices=choices or [], lesson_id=0,
            accepted=sorted(self.quiz.roman_variants(target)) if input_type == "text" else [])
        events.append(card)
        awaiting = {"kind": "await", "input": input_type, "qid": qid}
        if choices is not None:
            awaiting["choices"] = choices
        if input_type == "text":
            awaiting["placeholder"] = "e.g. na"
        return self._emit(events, awaiting)

    def _start_check(self, events):
        self.phase = "check"
        self.consecutive_wrong = 0
        events += [self._stage(), self._line("lines.decode_check_intro")]
        return self._new_check(events)

    def _new_check(self, events):
        self._seed_engine()
        try:
            self.check = make_reading_check(self.quiz)
        except ValueError:
            familiar = list(dict.fromkeys(word["ko"] for word in self._batch()["words"]))
            if len(familiar) < 5:
                self.check = None
                self.check_results[str(self.batch_index)] = {"passed": False, "unavailable": True}
                events.append({"kind": "notice", "text": "No reading check is available; continuing."})
                return self._advance_after_check(events)
            targets = self.rng.sample(familiar, 5)
            questions = [QuizQuestion(
                mode="read_aloud", letter=target, lesson_id=0,
                prompt=f"How does {target} sound? Type it in English letters.",
                correct_answer=self.quiz._word_romanization(target),
                accepted=sorted(self.quiz.roman_variants(target)),
                hint=" / ".join(self.quiz._piece_hint(block) for block in target),
            ) for target in targets]
            self.check = ReadingCheck(0, questions, [])
        return self._check_question(events)

    def _advance_after_check(self, events):
        if self.batch_index == 0:
            self.batch_index = 1
            return self._enter_batch(events)
        if self.baseline_score is None or self.baseline_score >= 6:
            return self._victory(events)
        return self._assessment_with(events)

    def _check_question(self, events):
        if self.check.finished:
            score = len(self.check.correct)
            passed = self.check.passed
            self.check_results[str(self.batch_index)] = {"passed": passed, "correct": score}
            save_check_result(self.quiz, self.check)
            events.append({"kind": "score", "context": "check", "correct": score,
                           "size": len(self.check.questions), "pass_score": PASS_SCORE, "passed": passed})
            if passed:
                events.append(self._line("lines.decode_check_perfect" if score == 5
                                         else "lines.decode_check_pass"))
                return self._advance_after_check(events)
            events.append(self._line("lines.decode_check_fail"))
            self.phase = "check_practice"
            self.consecutive_wrong = 0
            self.check_practice = [q.letter for q in list(self.check.missed.values())[:3]]
            self.round_size = len(self.check_practice)
            self.round_index = 0
            return self._check_practice_question(events)
        q = self.check.current
        seen = self.quiz.progress.setdefault("reading_check_seen", [])
        if q.letter not in seen:
            seen.append(q.letter)
        return self._question(events, q.letter, "read_aloud", q.correct_answer,
                              "Read this without a hint.", q.letter, "text", context="check", hint=False)

    def _assessment_with(self, events):
        self.phase = "post_test"
        self.assessment_items = [x["jamo"] for b in self.content["batches"] for x in b["letters"]]
        self.rng.shuffle(self.assessment_items)
        self.assessment_correct = 0
        events.append(self._stage())
        return self._assessment_question(events)

    def _check_practice_question(self, events):
        if not self.check_practice:
            self.phase = "check"
            events.append(self._stage())
            return self._new_check(events)
        target = self.check_practice.pop(0)
        return self._question(events, target, "read_aloud", self.quiz._word_romanization(target),
                              "Practice this reading.", target, "text", context="check_practice")

    def _time_text(self):
        minutes = max(1, int(self.active_ms / 60000 + 0.5))
        return f"{minutes} minute" + ("" if minutes == 1 else "s")

    def _milestone(self, ident, seal, paths, verdict=None):
        time_text = self._time_text()
        event = {"kind": "milestone", "id": ident, "seal": seal,
                 "active_ms": self.active_ms, "time_text": time_text,
                 "lines": [self._line(path, time=time_text) for path in paths]}
        if verdict is not None:
            event["verdict"] = verdict
        return event

    def _victory(self, events):
        projected = self.active_ms / 60000 * 3
        tier = next(row["id"] for row in self.content["wager"]["verdict_tiers_minutes"]
                    if row["max"] is None or projected <= row["max"])
        events.append(self._milestone("victory_1", "full",
            ["lines.victory_1.0", "lines.victory_1.1", f"lines.pace_verdict.{tier}"],
            {"tier": tier, "projected_minutes": projected}))
        return self._finish(events)

    def _chosen_tell(self, answer, target):
        known_forms = self.letters_known + self._known_blocks()
        chosen = answer if answer in known_forms else None
        if chosen is None:
            chosen = next((form for form in known_forms
                           if normalize_roman(answer) in self.quiz.roman_variants(form)), None)
        if chosen is None or chosen == target:
            return None, None
        for batch in self.content["batches"][:self.batch_index + 1]:
            for pair in batch["confusion_pairs"]:
                if target in pair["pair"] and chosen in pair["pair"]:
                    return chosen, pair["tell"]
        return chosen, None

    def _reaction(self, correct, target, answer):
        if correct:
            self.streak += 1
            self.consecutive_wrong = 0
            if str(self.streak) in self.content["lines"]["streak"]:
                self.last_correct_line = False
                return self._line(f"lines.streak.{self.streak}"), None, None
            speak = not self.last_correct_line and self.rng.random() < 1 / 3
            self.last_correct_line = speak
            if speak:
                index = self.correct_line_index % len(self.content["lines"]["correct"])
                self.correct_line_index += 1
                return self._line(f"lines.correct.{index}"), None, None
            return None, None, None
        self.streak = 0
        self.last_correct_line = False
        self.consecutive_wrong += 1
        chosen, tell = self._chosen_tell(answer, target)
        if self.consecutive_wrong == 3:
            line = self._line(f"lines.repeated_miss.{self.repeated_miss_index % len(self.content['lines']['repeated_miss'])}")
            self.repeated_miss_index += 1
            self.consecutive_wrong = 0
        elif chosen and tell:
            line = self._line("lines.miss.0", chosen=chosen, tell=tell)
        else:
            line = self._line("lines.miss_no_tell")
        return line, chosen, tell

    def _hint(self, target):
        if target in self.letters_known:
            return self._letter(target)["sound"]
        return " / ".join(self.quiz._piece_hint(block) for block in target)

    def submit(self, answer: str, active_ms: int = 0):
        if self.outcome is not None:
            raise ValueError("The Sejong Test has ended.")
        if self.phase == "new":
            raise ValueError("Start the Sejong Test first.")
        if not isinstance(active_ms, int) or active_ms < 0:
            raise ValueError("active_ms must be a nonnegative integer.")
        if self.letters_known:
            self.active_ms += active_ms
        answer = str(answer)
        if answer == "/quit":
            self.outcome = "quit"
            return [{"kind": "finished", "outcome": "quit"}]
        if answer.startswith("/"):
            if answer == "/hint" and self.current and self.current.get("card", {}).get("hint_available"):
                self.assisted = True
                return [{"kind": "hint", "qid": self.current["card"]["qid"],
                         "text": self._hint(self.current["target"])}, self.screen[-1]]
            return [{"kind": "notice", "text": "That command is unavailable here."}, self.screen[-1]]
        if self.phase == "intro":
            if answer not in ("Take the quick test", "Skip"):
                return [{"kind": "notice", "text": "Choose a displayed option."}, self.screen[-1]]
            if answer == "Skip":
                return self._enter_batch([self._line("lines.baseline_skip")])
            return self._assessment("baseline")
        if self.phase == "predict_reveal":
            if answer not in self.current["choices"]:
                return [{"kind": "notice", "text": "Choose a displayed option."}, self.screen[-1]]
            p = self._batch()["predict_reveal"]
            c, v, _ = self.quiz._decompose_syllable(p["block"])
            layout = "side" if v in ("ㅏ", "ㅓ", "ㅣ") else "stack"
            events = [{"kind": "reveal", "block": p["block"], "parts": [c, v],
                       "layout": layout,
                       "roman": p["roman"], "meaning": p["meaning"],
                       "guessed_right": answer == p["block"]}]
            if answer != p["block"]:
                events.append(self._line(f"lines.predict_wrong.{layout}", vowel=v))
            events.append(self._line(f"lines.predict_reveal.{self.batch_index}"))
            return self._next_phase(events)
        if not self.current or self.current["kind"] != "question":
            raise ValueError("No question is open.")
        card = self.current["card"]
        if card["input"] == "choice" and answer not in card["choices"]:
            return [{"kind": "notice", "text": "Choose a displayed option."}, self.screen[-1]]
        if card["input"] == "text" and self.quiz.script_mismatch(answer, self.current_engine_question):
            return [{"kind": "notice", "text": "Type the sound in English letters."}, self.screen[-1]]
        target = self.current["target"]
        context = self.current["context"]
        if context in ("baseline", "post_test"):
            correct = answer == self.current["answer"]
            self.assessment_correct += int(correct)
            return self._assessment_question([])
        elif context == "check":
            correct = self.check.submit(answer)
        else:
            self._seed_engine()
            correct = self.quiz.answer(answer, self.current_engine_question,
                                       assisted=self.assisted).correct
        result = {"kind": "result", "qid": card["qid"], "correct": correct,
                  "answer": answer, "correct_answer": self.current["answer"],
                  "streak": self.streak, "requeued": False}
        events = [result]
        if context in ("practice", "check_practice"):
            line, chosen, tell = self._reaction(correct, target, answer)
            if line is not None:
                result["line"] = line
            result["streak"] = self.streak
            if chosen:
                result["chosen_is"] = chosen
            if tell:
                result["tell"] = tell
            self.round_index += 1
            if not correct:
                result["requeued"] = True
                self.round_size += 1
                if context == "practice":
                    self.remaining.append(target)
                else:
                    self.check_practice.append(target)
            if correct and self.phase == "decode" and target not in self.words_read:
                self.words_read.append(target)
                word = next(x for x in self._batch()["words"] if x["ko"] == target)
                payoff = {"kind": "word_read", "ko": target, "roman": word["roman"], "en": word["en"]}
                path = ("lines.first_word_read" if len(self.words_read) == 1 else
                        "lines.fool_word" if target == "바보" else
                        "lines.dodo_word" if target == "도도" else None)
                if path:
                    payoff["line"] = self._line(path)
                elif "first_read_line" in word:
                    payoff["line"] = self._line_for_inline(word["first_read_line"],
                        f"batches.{self.batch_index}.words.{self._batch()['words'].index(word)}.first_read_line")
                events.append(payoff)
        if context == "check":
            return self._check_question(events)
        if context == "check_practice":
            return self._check_practice_question(events)
        return self._pool_question(events)

    def resume(self, reason: str):
        if reason not in ("reopen", "pause"):
            raise ValueError("reason must be reopen or pause")
        if self.phase == "new":
            return self.start()
        if self.outcome == "victory_1":
            return [{"kind": "finished", "outcome": "victory_1"}]
        self.outcome = None  # a quit ends this invocation, not the saved lesson
        return [self._line("lines.resume_saved" if reason == "reopen" else "lines.return_after_pause"),
                *self.screen]

    def export_state(self):
        check = None
        if self.check is not None:
            check = {"lesson_id": self.check.lesson_id,
                     "questions": [asdict(q) for q in self.check.questions],
                     "transfer_targets": self.check.transfer_targets, "index": self.check.index,
                     "correct": list(self.check.correct),
                     "missed": {k: asdict(v) for k, v in self.check.missed.items()},
                     "retried": list(self.check.retried)}
        keys = ("phase", "batch_index", "letters_known", "active_ms", "baseline_score",
                "post_score", "assessment_items", "assessment_correct", "remaining",
                "round_size", "round_index", "qid_number", "current", "screen",
                "assisted", "consecutive_wrong", "repeated_miss_index", "check_results",
                "check_practice", "streak", "correct_line_index", "last_correct_line",
                "words_read", "outcome")
        state = {key: getattr(self, key) for key in keys}
        state["check"] = check
        state["rng_state"] = self.rng.getstate()
        state["quiz"] = self.quiz.export_state()
        return json.dumps(state, ensure_ascii=False)

    @classmethod
    def from_state(cls, quiz, content, text):
        state = json.loads(text)
        flow = cls(quiz, content)
        flow.quiz.import_state(state["quiz"])
        for key, value in state.items():
            if key not in ("quiz", "rng_state", "check"):
                setattr(flow, key, value)
        flow.rng.setstate(_tuples(state["rng_state"]))
        if flow.letters_known:
            flow._custom_lesson()
        c = state["check"]
        if c:
            flow.check = ReadingCheck(c["lesson_id"], [QuizQuestion(**q) for q in c["questions"]],
                c["transfer_targets"], c["index"], set(c["correct"]),
                {k: QuizQuestion(**v) for k, v in c["missed"].items()}, set(c["retried"]))
        if flow.current and flow.current.get("kind") == "question":
            cur = flow.current
            card = cur["card"]
            flow.current_engine_question = QuizQuestion(mode=card["mode"], prompt=card["prompt"],
                correct_answer=cur["answer"], choices=card.get("choices", []),
                lesson_id=0, letter=cur["target"],
                accepted=sorted(quiz.roman_variants(cur["target"])) if card["input"] == "text" else [])
        return flow
