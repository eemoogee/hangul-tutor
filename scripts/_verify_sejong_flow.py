"""Contract and end-to-end checks for the UI-free Sejong slice."""

import contextlib
import io
import json
import re
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hangul_quiz_engine import HangulQuiz
from sejong_flow import SejongFlow

ROOT = Path(__file__).resolve().parents[1]
CONTENT = json.loads((ROOT / "data/sejong.json").read_text(encoding="utf-8"))
COUNT = 0


def check(name, fn):
    global COUNT
    fn()
    COUNT += 1
    print(f"PASS {name}")


def new_flow(seed=1):
    return SejongFlow(HangulQuiz(persist=False), CONTENT, seed=seed)


def answer_for(flow, events):
    if flow.phase == "before":
        return ""
    if flow.phase == "predict_reveal":
        return flow.current["target"]
    return flow.current["answer"]


def run(flow, *, mutate=None, tick=1000, first=None):
    events = first if first is not None else flow.start()
    transcript = [events]
    for step in range(300):
        if events[-1]["kind"] == "finished":
            return transcript
        answer = answer_for(flow, events)
        if mutate:
            answer = mutate(flow, events, answer, step)
        events = flow.submit(answer, active_ms=tick)
        transcript.append(events)
    raise AssertionError("flow did not finish")


def flattened(transcript):
    return [event for group in transcript for event in group]


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)


def reach_question(target, phase):
    flow = new_flow()
    events = flow.start()
    for _ in range(300):
        if flow.phase == phase and flow.current and flow.current.get("target") == target:
            return flow
        events = flow.submit(answer_for(flow, events))
    raise AssertionError(f"did not reach {target} in {phase}")


def mixup_tips():
    flow = reach_question("도", "build")
    result = flow.submit("다")[0]
    assert not result["correct"] and result["chosen_is"] == "다"
    assert result["tell"] == CONTENT["batches"][0]["confusion_pairs"][1]["tell"]
    assert result["line"]["line_id"] == "lines.miss.0"
    assert "다" in result["line"]["text"] and result["tell"] in result["line"]["text"]

    for target, answer, chosen, pair_index in (
        ("두부", "dobu", "도부", 2),
        ("너무", "namu", None, 1),
        ("도마", "domeo", None, 1),
        ("바다", "beoda", None, 1),
    ):
        flow = reach_question(target, "decode")
        events = flow.submit(answer)
        result = events[0]
        assert not result["correct"] and result.get("chosen_is") == chosen, (target, result)
        assert result["tell"] == CONTENT["batches"][1]["confusion_pairs"][pair_index]["tell"]
        assert result["line"]["line_id"] == ("lines.miss.0" if chosen else "lines.miss_no_tell")
        if chosen is None:
            assert not any(block in value for event in events for value in strings(event)
                           for block in ("누", "머", "버", "나무"))


def before_word_stays_hidden():
    for seed in range(1, 31):
        def every_third(flow, events, answer, step):
            if (flow.current and flow.current.get("card", {}).get("context") == "practice"
                    and step % 3 == 0):
                card = flow.current["card"]
                return (next(x for x in card["choices"] if x != answer)
                        if card["input"] == "choice" else "WRONG")
            return answer
        def fail_first_checks(flow, events, answer, step):
            if (flow.phase == "check" and flow.current["card"]["mode"] == "read_aloud"
                    and str(flow.batch_index) not in flow.check_results):
                return "WRONG"
            return answer
        for mutate in (None, every_third, fail_first_checks):
            events = flattened(run(new_flow(seed), mutate=mutate))
            start = next(i for i, e in enumerate(events) if e["kind"] == "before_word")
            end = next(i for i, e in enumerate(events)
                       if e["kind"] == "question" and e["context"] == "after")
            assert not any("나무" in value for event in events[start + 1:end]
                           for value in strings(event)), seed
            assert events[end]["display"] == "나무"
            after_result = next(i for i, e in enumerate(events[end + 1:], end + 1)
                                if e["kind"] == "result" and e["qid"] == events[end]["qid"])
            assert events[after_result + 1] == {
                "kind": "word_read", "ko": "나무", "roman": "namu", "en": "tree"}
            assert events[after_result + 2]["line_id"] == "lines.after_right"


def check_regeneration_and_fallback():
    from sejong_flow import make_reading_check as real_make
    for forced in (1, 12):
        flow = new_flow()
        events = flow.start()
        while not (flow.phase == "decode" and not flow.remaining):
            events = flow.submit(answer_for(flow, events))
        calls = 0
        def make(quiz):
            nonlocal calls
            calls += 1
            check = real_make(quiz)
            if calls <= forced:
                word = CONTENT["before_after"]["word"]
                check.questions[-1].letter = word
                check.questions[-1].correct_answer = "namu"
                check.questions[-1].accepted = ["namu"]
                check.transfer_targets[-1] = word
            return check
        with patch("sejong_flow.make_reading_check", side_effect=make):
            flow.submit(answer_for(flow, events))
        assert calls >= forced + (forced == 1)
        assert all(q.letter != "나무" for q in flow.check.questions)
        assert "나무" not in flow.check.transfer_targets


def retry_construction_and_lines():
    flow = new_flow()
    def fail_batch_one(flow, events, answer, step):
        if (flow.batch_index == 1 and flow.phase == "check"
                and flow.current["card"]["mode"] == "read_aloud"
                and "1" not in flow.check_results):
            return "WRONG"
        return answer
    events = flattened(run(flow, mutate=fail_batch_one))
    cards = [e for e in events if e["kind"] == "question" and e["context"] == "check"
             and e["mode"] == "build_syllable"]
    assert len(cards) == 1
    batch_one_scores = [e for e in events if e["kind"] == "score" and "construction" in e]
    assert [e["passed"] for e in batch_one_scores] == [False, True]
    assert batch_one_scores[-1]["correct"] == 5
    assert any(e["kind"] == "narrator" and e["line_id"] == "lines.decode_check_pass"
               for e in events)
    assert sum(e["kind"] == "narrator" and e["line_id"] == "lines.decode_check_perfect"
               for e in events) == 1  # Batch 0's first-attempt perfect score.
    for seed in range(1, 11):
        perfect = flattened(run(new_flow(seed)))
        assert sum(e["kind"] == "narrator" and e["line_id"] == "lines.decode_check_perfect"
                   for e in perfect) == 2


def streak_line_spacing():
    for seed in range(1, 31):
        groups = run(new_flow(seed))
        practice = [next(e for e in group if e["kind"] == "result") for group in groups
                    if any(e["kind"] == "result" and
                           e["qid"].split("-")[1] in ("recognize", "retrieve", "build", "decode")
                           for e in group)]
        for left, right in zip(practice, practice[1:]):
            a = left.get("line", {}).get("line_id", "")
            b = right.get("line", {}).get("line_id", "")
            assert not (a.startswith("lines.correct.") and b.startswith("lines.streak."))
            assert not (a.startswith("lines.streak.") and b.startswith("lines.correct."))


def cli_check_wording():
    from sejong_cli import render
    class Clock:
        def take(self):
            return 0
        def mark(self):
            pass
    contexts = {}
    card = {"kind": "question", "qid": "b1-check-1", "context": "check",
            "prompt": "Read this.", "display": "머"}
    output = io.StringIO()
    with contextlib.redirect_stdout(output), patch("builtins.input", return_value="wrong"):
        render([card, {"kind": "await", "input": "text"}], Clock(), contexts)
    with contextlib.redirect_stdout(output), patch("sejong_cli.wait_for_enter"):
        render([{"kind": "result", "qid": "b1-check-1", "correct": False,
                 "correct_answer": "meo", "tell": "Check the vowel.",
                 "line": {"speaker": "jeong", "text": "Not yet."}},
                {"kind": "score", "context": "check", "correct": 4, "size": 5}],
               Clock(), contexts)
    text = output.getvalue()
    assert "It reads meo." in text and "Reading check: 4 of 5" in text
    assert "Check the vowel." in text and "Try again later" not in text


def contract():
    flow = new_flow()
    transcript = run(flow)
    required = {
        "narrator": ("speaker", "text", "line_id", "source"),
        "stage": ("batch_id", "batch_name", "phase", "letters_known"),
        "letter_intro": ("jamo", "type", "roman", "sound", "shape", "shape_source"),
        "predict": ("consonant", "vowel", "choices"),
        "reveal": ("block", "parts", "layout", "roman"),
        "question": ("qid", "context", "mode", "prompt", "display", "input", "hint_available"),
        "result": ("qid", "correct", "answer", "correct_answer", "streak", "requeued"),
        "word_read": ("ko", "roman", "en"),
        "before_word": ("ko",),
        "hint": ("qid", "text"), "notice": ("text",),
        "score": ("context", "correct", "size"),
        "milestone": ("id", "seal", "active_ms", "time_text", "lines"),
        "await": ("input",), "finished": ("outcome",),
    }
    known = []
    for group in transcript:
        assert sum(e["kind"] in ("await", "finished") for e in group) == 1
        assert group[-1]["kind"] in ("await", "finished")
        assert json.loads(json.dumps(group, ensure_ascii=False)) == group
        for e in group:
            assert "kind" in e
            for key in required.get(e["kind"], ()):
                assert key in e, (e, key)
            if e["kind"] == "stage":
                known = e["letters_known"]
            if e["kind"] == "question":
                for value in [e["display"], *e.get("choices", [])]:
                    for char in value:
                        if "가" <= char <= "힣":
                            c, v, final = flow.quiz._decompose_syllable(char)
                            assert c in known and v in known and not final, e
                        elif "ㄱ" <= char <= "ㅣ":
                            assert char in known, e
            if e["kind"] == "predict":
                assert all(all(c in known and v in known and not final
                    for c, v, final in [flow.quiz._decompose_syllable(block)])
                    for block in e["choices"])
            if e["kind"] == "result" and e["qid"].split("-")[1] in ("check", "after"):
                assert "line" not in e
            assert e.get("context") not in ("baseline", "post_test")
            for line in ([e] if e["kind"] == "narrator" else
                         [e["line"]] if e["kind"] in ("result", "word_read") and "line" in e else
                         e["lines"] if e["kind"] == "milestone" else []):
                node = CONTENT
                for key in line["line_id"].split("."):
                    node = node[int(key)] if isinstance(node, list) else node[key]
                assert line["source"] == node["source"]
                assert not re.search(r"\{[^}]+\}", line["text"])
                assert not line["line_id"].startswith("lines.baseline_")


def order_and_scores():
    events = flattened(run(new_flow()))
    phases = [(e["batch_id"], e["phase"]) for e in events if e["kind"] == "stage"]
    assert phases == [(0, "intro"), (0, "before"), (0, "discover"),
        (0, "predict_reveal"), (0, "build"), (0, "decode"), (0, "check"),
        (1, "discover"), (1, "predict_reveal"), (1, "recognize"),
        (1, "retrieve"), (1, "build"), (1, "decode"), (1, "check"),
        (1, "after"), (1, "done")], phases
    assert [e["context"] for e in events if e["kind"] == "score"] == [
        "check", "check"]
    assert [e["id"] for e in events if e["kind"] == "milestone"] == [
        "first_breakthrough", "victory_1"]
    assert events[-1] == {"kind": "finished", "outcome": "victory_1"}


def misses_requeue():
    counter = 0
    def miss(flow, events, answer, step):
        nonlocal counter
        if flow.current and flow.current.get("card", {}).get("context") == "practice":
            counter += 1
            if counter % 3 == 0:
                card = flow.current["card"]
                return (next(x for x in card["choices"] if x != answer)
                        if card["input"] == "choice" else "WRONG")
        return answer
    events = flattened(run(new_flow(), mutate=miss))
    assert any(e["kind"] == "result" and e["requeued"] for e in events)
    assert any(e["kind"] == "question" and e["qid"].startswith("b1-build-")
               and e.get("round", {}).get("size", 0) > 12 for e in events)
    assert events[-1]["outcome"] == "victory_1"


def narrator_and_words():
    misses = 0
    def three_wrong(flow, events, answer, step):
        nonlocal misses
        if flow.phase == "build" and flow.batch_index == 0 and misses < 3:
            misses += 1
            return next(x for x in flow.current["card"]["choices"] if x != answer)
        return answer
    events = flattened(run(new_flow(), mutate=three_wrong))
    lines = [e["line"]["line_id"] for e in events if e["kind"] == "result" and "line" in e]
    assert "lines.miss_no_tell" in lines
    assert sum(x.startswith("lines.repeated_miss.") for x in lines) == 1
    words = [e for e in events if e["kind"] == "word_read"]
    assert len(words) == 18 and len({w["ko"] for w in words}) == 18
    assert words[0]["line"]["line_id"] == "lines.first_word_read"
    for word, line_id in (("바보", "lines.fool_word"), ("도도", "lines.dodo_word")):
        payoff = next(w for w in words if w["ko"] == word)
        assert payoff["line"]["line_id"] == ("lines.first_word_read" if payoff is words[0]
                                                 else line_id)


def before_after_order_and_timer():
    flow = new_flow()
    events = flow.start()
    transcript = [events]
    expected_ms = 0
    for _ in range(300):
        if events[-1]["kind"] == "finished":
            break
        active_ms = 1000 if flow.letters_known else 60000
        if flow.letters_known:
            expected_ms += active_ms
        events = flow.submit(answer_for(flow, events), active_ms=active_ms)
        transcript.append(events)
    all_events = flattened(transcript)
    clock_positions = [i for i, event in enumerate(all_events)
                       if event["kind"] == "narrator" and event["line_id"] == "lines.clock_start"]
    assert len(clock_positions) == 1
    before_positions = [i for i, event in enumerate(all_events) if event["kind"] == "before_word"]
    assert len(before_positions) == 1
    assert all_events[before_positions[0]] == {"kind": "before_word", "ko": "나무"}
    before_show = next(i for i, event in enumerate(all_events)
                       if event["kind"] == "narrator" and event["line_id"] == "lines.before_show")
    batch_intro = next(i for i, event in enumerate(all_events)
                       if event["kind"] == "narrator" and event["line_id"] == "lines.batch_intro.0")
    assert before_positions[0] < before_show < clock_positions[0] == batch_intro - 1
    after_positions = [i for i, event in enumerate(all_events)
                       if event["kind"] == "question" and event["context"] == "after"]
    assert len(after_positions) == 1
    after_question = all_events[after_positions[0]]
    assert after_question["display"] == "나무" and after_question["input"] == "text"
    assert not after_question["hint_available"]
    last_score = max(i for i, event in enumerate(all_events)
                     if event["kind"] == "score" and event["context"] == "check")
    victory_index = next(i for i, event in enumerate(all_events)
                         if event["kind"] == "milestone" and event["id"] == "victory_1")
    assert last_score < after_positions[0] < victory_index
    victory = next(event for event in all_events
                   if event["kind"] == "milestone" and event["id"] == "victory_1")
    assert victory["active_ms"] == expected_ms


def no_deprecated_assessments():
    events = flattened(run(new_flow()))
    assert all(e.get("context") not in ("baseline", "post_test") for e in events)
    assert not any(e.get("line_id", "").startswith("lines.baseline_") for e in events)


def occasional_correct_lines():
    eligible_results = []
    for seed in range(20):
        transcript = run(new_flow(seed))
        events = flattened(transcript)
        results = [e for e in events if e["kind"] == "result" and e["correct"]
                   and e["qid"].split("-")[1] in ("recognize", "retrieve", "build", "decode")]
        eligible_results.extend(e for group in transcript
                                if not any(item["kind"] == "word_read" and "line" in item
                                           for item in group)
                                for e in group if e in results)
        previous_had_line = False
        line_ids = []
        for result in results:
            line_id = result.get("line", {}).get("line_id", "")
            has_correct_line = line_id.startswith("lines.correct.")
            assert not (previous_had_line and has_correct_line)
            previous_had_line = has_correct_line
            if has_correct_line:
                line_ids.append(line_id)
        assert all(a != b for a, b in zip(line_ids, line_ids[1:]))
    share = sum(e.get("line", {}).get("line_id", "").startswith("lines.correct.")
                for e in eligible_results) / len(eligible_results)
    assert .20 <= share <= .45, share


def streak_line_replaces_correct_line():
    transcript = run(new_flow())
    streaks = []
    for group in transcript:
        for event in group:
            if event["kind"] != "result" or event["streak"] not in (5, 10, 15):
                continue
            if event["qid"].split("-")[1] not in ("recognize", "retrieve", "build", "decode"):
                continue
            word_line = any(e["kind"] == "word_read" and "line" in e for e in group)
            if word_line:
                assert "line" not in event
            else:
                assert event["line"]["line_id"] == f"lines.streak.{event['streak']}"
            assert not any(e["kind"] == "narrator" and e["line_id"].startswith(
                ("lines.correct.", "lines.streak.")) for e in group)
            streaks.append(event["streak"])
    assert {5, 10, 15} <= set(streaks)


def consecutive_misses_only():
    attempt = 0
    def alternating(flow, events, answer, step):
        nonlocal attempt
        if flow.current and flow.current.get("card", {}).get("context") == "practice" and attempt < 20:
            attempt += 1
            if attempt % 2:
                card = flow.current["card"]
                return (next(x for x in card["choices"] if x != answer)
                        if card["input"] == "choice" else "WRONG")
        return answer
    events = flattened(run(new_flow(), mutate=alternating))
    assert not any(e["kind"] == "result" and e.get("line", {}).get("line_id", "").startswith(
        "lines.repeated_miss.") for e in events)
    wrongs = 0
    def triple(flow, events, answer, step):
        nonlocal wrongs
        if flow.batch_index == 0 and flow.phase == "build" and wrongs < 3:
            wrongs += 1
            return next(x for x in flow.current["card"]["choices"] if x != answer)
        return answer
    events = flattened(run(new_flow(), mutate=triple))
    repeated = [e for e in events if e["kind"] == "result" and
                e.get("line", {}).get("line_id", "").startswith("lines.repeated_miss.")]
    assert len(repeated) == 1


def batch_one_build_targets_and_choices():
    flow = new_flow()
    events = flow.start()
    targets = []
    while events[-1]["kind"] != "finished":
        if flow.batch_index == 1 and flow.phase == "build":
            target = flow.current["target"]
            card = flow.current["card"]
            targets.append(target)
            consonant, vowel, _ = flow.quiz._decompose_syllable(target)
            distractors = [x for x in card["choices"] if x != target]
            parts = [flow.quiz._decompose_syllable(x) for x in distractors]
            assert len(distractors) == 3 and len(set(card["choices"])) == 4
            assert not set(card["choices"]) & {"누", "머", "버"}
            assert any(c == consonant and v != vowel for c, v, _ in parts)
            assert any(v == vowel and c != consonant for c, v, _ in parts)
        events = flow.submit(answer_for(flow, events))
    assert len(targets) == len(set(targets)) == 9
    assert set(targets) == {"너", "더", "두", "마", "모", "무", "바", "보", "부"}


def held_back_before_check():
    for seed in range(1, 11):
        events = flattened(run(new_flow(seed)))
        check_start = next(i for i, event in enumerate(events)
                           if event["kind"] == "stage" and event["batch_id"] == 1
                           and event["phase"] == "check")
        def strings(value):
            if isinstance(value, str):
                yield value
            elif isinstance(value, dict):
                for child in value.values():
                    yield from strings(child)
            elif isinstance(value, list):
                for child in value:
                    yield from strings(child)
        assert not any(block in value for event in events[:check_start]
                       for value in strings(event) for block in ("누", "머", "버"))


def construction_and_first_attempt():
    held = {"누", "머", "버"}
    for seed in range(1, 11):
        flow = new_flow(seed)
        events = flow.start()
        while not (flow.batch_index == 1 and flow.phase == "check"):
            events = flow.submit(answer_for(flow, events))
        card = flow.current["card"]
        target = flow.current["target"]
        assert card["context"] == "check" and card["mode"] == "build_syllable"
        assert card["input"] == "choice" and not card["hint_available"]
        assert card["parts"] == list(flow.quiz._decompose_syllable(target)[:2])
        assert target in held and len(set(card["choices"])) == 4
        assert set(card["choices"]) & held == {target}
        c, v = card["parts"]
        distractors = [flow.quiz._decompose_syllable(x) for x in card["choices"] if x != target]
        assert any(dc == c and dv != v for dc, dv, _ in distractors)
        assert any(dv == v and dc != c for dc, dv, _ in distractors)
        assert held.isdisjoint(flow.quiz.current_lesson["practice_syllables"])
        assert held.isdisjoint(flow.quiz.current_lesson["mastery_syllables"])
        events = flow.submit(target)
        assert events[0]["correct"] and "line" not in events[0]
        assert flow.quiz.progress["learner_items"].get(target)
        assert set(flow.check.transfer_targets) == held - {target}
        transcript = run(flow, first=events)
        score = next(e for e in flattened(transcript) if e["kind"] == "score")
        assert score["construction"] == {"target": target, "correct": True}
        assert flow.check_results["1"]["first_attempt"] == {
            "construction": True,
            "new_read": {block: True for block in flow.check.transfer_targets}}

    flow = new_flow()
    def wrong_construction(flow, events, answer, step):
        if flow.batch_index == 1 and flow.phase == "check":
            if flow.current["card"]["mode"] == "build_syllable":
                return next(x for x in flow.current["card"]["choices"] if x != answer)
            if flow.check.index == 4:
                return "WRONG"
        return answer
    scores = [e for e in flattened(run(flow, mutate=wrong_construction)) if e["kind"] == "score"]
    assert scores[-1]["passed"] and scores[-1]["correct"] == 4
    assert scores[-1]["construction"]["correct"] is False
    assert flow.check_results["1"]["first_attempt"]["construction"] is False

    flow = new_flow()
    first_targets = None
    def fail_first_reading(flow, events, answer, step):
        nonlocal first_targets
        if (flow.batch_index == 1 and flow.phase == "check" and flow.check is not None
                and flow.current["card"]["mode"] == "read_aloud"):
            if first_targets is None:
                first_targets = list(flow.check.transfer_targets)
            if "first_attempt" not in flow.check_results.get("1", {}) and flow.check.index >= 3:
                return "WRONG"
        return answer
    events = flattened(run(flow, mutate=fail_first_reading))
    scores = [e for e in events if e["kind"] == "score"]
    assert [score["passed"] for score in scores[-2:]] == [False, True]
    assert scores[-2]["correct"] == 3
    assert any(e["kind"] == "question" and e["context"] == "check_practice" for e in events)
    assert flow.check_results["1"]["first_attempt"] == {
        "construction": True, "new_read": {block: False for block in first_targets}}


def replay_mid_check():
    flow = new_flow()
    events = flow.start()
    while not (flow.batch_index == 1 and flow.phase == "check"):
        events = flow.submit(answer_for(flow, events))
    for _ in range(2):
        clone = SejongFlow.from_state(HangulQuiz(persist=False), CONTENT, flow.export_state())
        assert clone.construction_target == flow.construction_target
        answer = answer_for(flow, events)
        assert clone.submit(answer) == flow.submit(answer)
        events = flow.screen
    clone = SejongFlow.from_state(HangulQuiz(persist=False), CONTENT, flow.export_state())
    while flow.outcome is None:
        answer = answer_for(flow, events)
        assert clone.submit(answer) == flow.submit(answer)
        events = flow.screen


def one_jeong_line_per_answer():
    for seed in range(1, 31):
        transcript = run(new_flow(seed))
        words = [e for group in transcript for e in group if e["kind"] == "word_read"]
        assert words[0]["line"]["line_id"] == "lines.first_word_read"
        for index, group in enumerate(transcript):
            assert not (any(e["kind"] == "result" and "line" in e for e in group)
                        and any(e["kind"] == "word_read" and "line" in e for e in group))
            if any(e["kind"] == "word_read" and "line" in e for e in group):
                next_result = next((e for e in transcript[index + 1]
                                    if e["kind"] == "result"), None)
                if next_result is not None and next_result["correct"]:
                    assert not next_result.get("line", {}).get("line_id", "").startswith(
                        "lines.correct.")


def wrong_predict_reaction():
    def reach_predict(batch_index):
        flow = new_flow()
        events = flow.start()
        while not (flow.batch_index == batch_index and flow.phase == "predict_reveal"):
            events = flow.submit(answer_for(flow, events))
        return flow
    for batch_index, layout in ((0, "side"), (1, "stack")):
        flow = reach_predict(batch_index)
        wrong = next(x for x in flow.current["choices"] if x != flow.current["target"])
        events = flow.submit(wrong)
        assert [e["line_id"] if e["kind"] == "narrator" else e["kind"]
                for e in events[:3]] == ["reveal", f"lines.predict_wrong.{layout}",
                                        f"lines.predict_reveal.{batch_index}"]
        assert "{" not in events[1]["text"]
    flow = reach_predict(0)
    events = flow.submit(flow.current["target"])
    assert not any(e["kind"] == "narrator" and e["line_id"].startswith("lines.predict_wrong.")
                   for e in events)


def check_retry_independence():
    flow = new_flow()
    failed = False
    def miss_first_check(flow, events, answer, step):
        nonlocal failed
        if flow.batch_index == 0 and flow.phase == "check" and not failed:
            if flow.check.index == 4:
                failed = True
            return "WRONG"
        return answer
    events = flattened(run(flow, mutate=miss_first_check))
    assert any(e["kind"] == "narrator" and e["line_id"] == "lines.decode_check_fail" for e in events)
    assert any(e["kind"] == "question" and e["context"] == "check_practice" for e in events)
    scores = [e for e in events if e["kind"] == "score" and e["context"] == "check"]
    assert len(scores) == 3 and [e["passed"] for e in scores] == [False, True, True]
    assert flow.check_results["0"]["passed"] and flow.check_results["1"]["passed"]


def recognize_reverses_retrieve():
    flow = new_flow()
    events = flow.start()
    while flow.phase != "recognize":
        events = flow.submit(answer_for(flow, events))
    for _ in range(4):
        card = flow.current["card"]
        target = flow.current["target"]
        letter = flow._letter(target)
        assert card["mode"] == "match_sound" and card["input"] == "choice"
        assert card["display"] == letter["roman"] and flow.current["answer"] == target
        assert len(card["choices"]) == len(set(card["choices"])) == 4
        assert target in card["choices"]
        assert all(flow._letter(choice)["type"] == letter["type"]
                   for choice in card["choices"])
        events = flow.submit(target)
    assert flow.phase == "retrieve"
    assert flow.current["card"]["display"] == flow.current["target"]
    assert flow.current["card"]["input"] == "text"


def forty_failed_checks():
    flow = new_flow()
    events = flow.start()
    failures = 0
    fallback_seen = False
    for _ in range(1000):
        if events[-1]["kind"] == "finished":
            break
        answer = answer_for(flow, events)
        if flow.batch_index == 0 and flow.phase == "check":
            fallback_seen |= flow.check.transfer_targets == []
            if failures < 40:
                answer = "WRONG"
        events = flow.submit(answer)
        assert events[-1]["kind"] in ("await", "finished")
        assert json.loads(json.dumps(events, ensure_ascii=False)) == events
        failures += sum(e["kind"] == "score" and e["context"] == "check"
                        and not e["passed"] and flow.batch_index == 0 for e in events)
    assert failures == 40, failures
    assert fallback_seen, "retry pool never exercised familiar-only fallback"
    assert flow.check_results["0"]["passed"]
    assert events[-1] == {"kind": "finished", "outcome": "victory_1"}


def unavailable_check_advances():
    content = json.loads(json.dumps(CONTENT, ensure_ascii=False))
    content["batches"][0]["words"] = content["batches"][0]["words"][:4]
    flow = SejongFlow(HangulQuiz(persist=False), content, seed=1)
    events = flow.start()
    with patch("sejong_flow.make_reading_check", side_effect=ValueError("No new safe combinations remain")):
        for _ in range(100):
            if flow.batch_index == 1:
                break
            answer = answer_for(flow, events)
            events = flow.submit(answer)
    assert flow.batch_index == 1
    assert flow.check_results["0"] == {"passed": False, "unavailable": True}
    assert any(e["kind"] == "notice" for e in events)
    assert events[-1]["kind"] == "await"


def after_answers():
    for answer, correct, line_id in (("namu", True, "lines.after_right"),
                                     ("namoo", True, "lines.after_right"),
                                     ("WRONG", False, "lines.after_close")):
        flow = new_flow()
        events = flow.start()
        while flow.phase != "after":
            events = flow.submit(answer_for(flow, events))
        before = flow.quiz.session_total
        events = flow.submit(answer, active_ms=777)
        assert events[0]["kind"] == "result" and events[0]["correct"] is correct
        assert "line" not in events[0] and not events[0]["requeued"]
        if correct:
            assert events[1] == {"kind": "word_read", "ko": "나무",
                                 "roman": "namu", "en": "tree"}
        line = events[2] if correct else events[1]
        assert line["line_id"] == line_id and "{" not in line["text"]
        assert next(e for e in events if e["kind"] == "milestone")["id"] == "victory_1"
        assert events[-1] == {"kind": "finished", "outcome": "victory_1"}
        assert flow.quiz.session_total == before


def replay_resume_quit():
    flow = new_flow()
    events = flow.start()
    for _ in range(15):
        events = flow.submit(answer_for(flow, events), 300)
    saved = flow.export_state()
    clone = SejongFlow.from_state(HangulQuiz(persist=False), CONTENT, saved)
    assert clone.resume("reopen")[0]["line_id"] == "lines.resume_saved"
    assert clone.resume("pause")[0]["line_id"] == "lines.return_after_pause"
    assert clone.screen == flow.screen
    for _ in range(300):
        if events[-1]["kind"] == "finished":
            break
        a = answer_for(flow, events)
        events = flow.submit(a, 300)
        replica = clone.submit(a, 300)
        assert events == replica
    assert events[-1] == {"kind": "finished", "outcome": "victory_1"}
    flow = new_flow()
    events = flow.start()
    for _ in range(20):
        events = flow.submit(answer_for(flow, events), 300)
    saved = flow.export_state()
    assert flow.submit("/quit") == [{"kind": "finished", "outcome": "quit"}]
    continued = SejongFlow.from_state(HangulQuiz(persist=False), CONTENT, saved)
    assert flattened(run(continued, first=continued.resume("reopen")))[-1]["outcome"] == "victory_1"


def before_after_resume():
    flow = new_flow()
    events = flow.start()
    assert flow.phase == "before"
    assert [e["kind"] for e in flow.screen] == ["stage", "before_word", "narrator", "await"]
    clone = SejongFlow.from_state(HangulQuiz(persist=False), CONTENT, flow.export_state())
    assert clone.resume("reopen")[1:] == flow.screen
    assert clone.submit("", 60000) == flow.submit("", 60000)
    assert flow.active_ms == clone.active_ms == 0
    while flow.phase != "after":
        answer = answer_for(flow, events)
        events = flow.submit(answer, 300)
        assert events == clone.submit(answer, 300)
    saved = flow.export_state()
    clone = SejongFlow.from_state(HangulQuiz(persist=False), CONTENT, saved)
    assert clone.resume("reopen")[1:] == flow.screen
    assert clone.submit("namu", 500) == flow.submit("namu", 500)


def hints_and_scripts():
    flow = new_flow()
    events = flow.start()
    while flow.phase != "retrieve":
        events = flow.submit(answer_for(flow, events))
    qid = flow.current["card"]["qid"]
    target = flow.current["target"]
    before = flow.quiz.session_total
    notice = flow.submit(flow.current["target"])
    assert notice[0]["kind"] == "notice" and notice[-1]["qid"] == qid
    assert flow.quiz.session_total == before
    hinted = flow.submit("/hint")
    assert hinted[0]["kind"] == "hint" and hinted[-1]["qid"] == qid
    assert flow.current["card"]["hint_available"]
    events = flow.submit(flow.current["answer"])
    assert events[0]["correct"] and flow.quiz.session_total == before + 1
    assert "h" in flow.quiz._get_item(flow.quiz._compose_bare_vowel(target)).history


def file_free():
    flow = new_flow()
    out = io.StringIO()
    with contextlib.redirect_stdout(out), \
         patch("builtins.open", side_effect=AssertionError("file I/O")), \
         patch("pathlib.Path.open", side_effect=AssertionError("file I/O")):
        run(flow)
    assert out.getvalue() == ""


def timer():
    flow = new_flow()
    transcript = run(flow, tick=15000)
    milestone = next(e for e in flattened(transcript) if e["kind"] == "milestone" and e["id"] == "victory_1")
    first_batch_group = next(i for i, group in enumerate(transcript)
                             if any(e["kind"] == "letter_intro" for e in group))
    assert milestone["active_ms"] == 15000 * (len(transcript) - first_batch_group - 1)
    minutes = max(1, int(milestone["active_ms"] / 60000 + .5))
    assert milestone["time_text"] == f"{minutes} minute" + ("" if minutes == 1 else "s")
    assert milestone["verdict"]["projected_minutes"] == milestone["active_ms"] / 60000 * 3
    expected = next(row["id"] for row in CONTENT["wager"]["verdict_tiers_minutes"]
                    if row["max"] is None or milestone["verdict"]["projected_minutes"] <= row["max"])
    assert milestone["verdict"]["tier"] == expected


if __name__ == "__main__":
    for name, fn in (("event contract", contract), ("all-correct order and scores", order_and_scores),
                     ("before/after order and clock", before_after_order_and_timer),
                     ("no deprecated assessments", no_deprecated_assessments),
                     ("occasional correct lines", occasional_correct_lines),
                     ("streak line replaces correct line", streak_line_replaces_correct_line),
                     ("misses must be consecutive", consecutive_misses_only),
                     ("Batch 1 build targets and distractors", batch_one_build_targets_and_choices),
                     ("held-back blocks stay unseen before check", held_back_before_check),
                     ("construction and first-attempt evidence", construction_and_first_attempt),
                     ("mid-check replay", replay_mid_check),
                     ("one Jeong line per answer", one_jeong_line_per_answer),
                     ("block and word mix-up tips", mixup_tips),
                     ("before word stays hidden until after", before_word_stays_hidden),
                     ("check regeneration and fallback", check_regeneration_and_fallback),
                     ("retry construction and perfect lines", retry_construction_and_lines),
                     ("streak line spacing", streak_line_spacing),
                     ("CLI check wording", cli_check_wording),
                     ("wrong predict reaction", wrong_predict_reaction),
                     ("misses requeued", misses_requeue), ("narrator and word payoff", narrator_and_words),
                     ("check retry and independence", check_retry_independence),
                     ("recognize reverses retrieve", recognize_reverses_retrieve),
                     ("40 failed Batch 0 checks", forty_failed_checks),
                     ("unavailable check advances", unavailable_check_advances),
                     ("after answers and close", after_answers),
                     ("resume at before and after", before_after_resume),
                     ("resume, replay, quit", replay_resume_quit),
                     ("practice hints and script notices", hints_and_scripts),
                     ("file-free and silent", file_free), ("timer and verdict", timer)):
        check(name, fn)
    print(f"{COUNT} checks passed")
