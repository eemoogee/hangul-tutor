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
    if flow.phase == "intro":
        return "Take the quick test"
    if flow.phase == "predict_reveal":
        return flow.current["target"]
    if flow.phase == "baseline":
        return next(x for x in flow.current["card"]["choices"] if x != flow.current["answer"])
    return flow.current["answer"]


def run(flow, *, baseline=True, mutate=None, tick=1000, first=None):
    events = first if first is not None else flow.start()
    transcript = [events]
    for step in range(300):
        if events[-1]["kind"] == "finished":
            return transcript
        answer = answer_for(flow, events)
        if flow.phase == "intro" and not baseline:
            answer = "Skip"
        if mutate:
            answer = mutate(flow, events, answer, step)
        events = flow.submit(answer, active_ms=tick)
        transcript.append(events)
    raise AssertionError("flow did not finish")


def flattened(transcript):
    return [event for group in transcript for event in group]


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
            if e["kind"] == "question" and e["context"] != "baseline":
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
            if e["kind"] == "result" and e["qid"].split("-")[1] == "check":
                assert "line" not in e
            if e["kind"] == "result":
                assert e["qid"].split("-")[1] not in ("baseline", "post_test")
            for line in ([e] if e["kind"] == "narrator" else
                         [e["line"]] if e["kind"] in ("result", "word_read") and "line" in e else
                         e["lines"] if e["kind"] == "milestone" else []):
                node = CONTENT
                for key in line["line_id"].split("."):
                    node = node[int(key)] if isinstance(node, list) else node[key]
                assert line["source"] == node["source"]
                assert not re.search(r"\{[^}]+\}", line["text"])


def order_and_scores():
    events = flattened(run(new_flow()))
    phases = [(e["batch_id"], e["phase"]) for e in events if e["kind"] == "stage"]
    assert phases == [(0, "intro"), (0, "baseline"), (0, "discover"),
        (0, "predict_reveal"), (0, "build"), (0, "decode"), (0, "check"),
        (1, "discover"), (1, "predict_reveal"), (1, "recognize"),
        (1, "retrieve"), (1, "build"), (1, "decode"), (1, "check"),
        (1, "post_test"), (1, "done")], phases
    assert [e["context"] for e in events if e["kind"] == "score"] == [
        "baseline", "check", "check", "post_test"]
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
    assert next(w for w in words if w["ko"] == "바보")["line"]["line_id"] == "lines.fool_word"
    assert next(w for w in words if w["ko"] == "도도")["line"]["line_id"] == "lines.dodo_word"


def clock_starts_after_baseline():
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
    baseline_end = max(i for i, event in enumerate(all_events)
                       if event["kind"] == "score" and event["context"] == "baseline")
    batch_intro = next(i for i, event in enumerate(all_events)
                       if event["kind"] == "narrator" and event["line_id"] == "lines.batch_intro.0")
    assert baseline_end < clock_positions[0] == batch_intro - 1
    victory = next(event for event in all_events
                   if event["kind"] == "milestone" and event["id"] == "victory_1")
    assert victory["active_ms"] == expected_ms


def assessments_have_no_feedback():
    events = flattened(run(new_flow()))
    assert not any(e["kind"] == "result" and e["qid"].split("-")[1]
                   in ("baseline", "post_test") for e in events)
    assert [e["context"] for e in events if e["kind"] == "score"
            and e["context"] in ("baseline", "post_test")] == ["baseline", "post_test"]


def occasional_correct_lines():
    correct_results = []
    for seed in range(20):
        events = flattened(run(new_flow(seed)))
        results = [e for e in events if e["kind"] == "result" and e["correct"]
                   and e["qid"].split("-")[1] in ("recognize", "retrieve", "build", "decode")]
        correct_results.extend(results)
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
                for e in correct_results) / len(correct_results)
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
            assert any(c == consonant and v != vowel for c, v, _ in parts)
            assert any(v == vowel and c != consonant for c, v, _ in parts)
        events = flow.submit(answer_for(flow, events))
    assert len(targets) == len(set(targets)) == 12
    assert not set(targets) & {"나", "노", "다", "도"}


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
        if flow.phase == "intro":
            answer = "Skip"
        elif flow.batch_index == 0 and flow.phase == "check":
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
            answer = "Skip" if flow.phase == "intro" else answer_for(flow, events)
            events = flow.submit(answer)
    assert flow.batch_index == 1
    assert flow.check_results["0"] == {"passed": False, "unavailable": True}
    assert any(e["kind"] == "notice" for e in events)
    assert events[-1]["kind"] == "await"


def skip_cases():
    assert not any(e["kind"] == "score" and e["context"] == "post_test"
                   for e in flattened(run(new_flow(), baseline=False)))
    count = 0
    def one_wrong(flow, events, answer, step):
        nonlocal count
        if flow.phase == "baseline":
            count += 1
            if count > 1:
                return flow.current["answer"]
        return answer
    events = flattened(run(new_flow(), mutate=one_wrong))
    assert any(e["kind"] == "score" and e["context"] == "baseline" and e["correct"] == 7 for e in events)
    assert not any(e["kind"] == "score" and e["context"] == "post_test" for e in events)


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
                     ("clock starts after baseline", clock_starts_after_baseline),
                     ("assessment answers stay hidden", assessments_have_no_feedback),
                     ("occasional correct lines", occasional_correct_lines),
                     ("streak line replaces correct line", streak_line_replaces_correct_line),
                     ("misses must be consecutive", consecutive_misses_only),
                     ("Batch 1 build targets and distractors", batch_one_build_targets_and_choices),
                     ("wrong predict reaction", wrong_predict_reaction),
                     ("misses requeued", misses_requeue), ("narrator and word payoff", narrator_and_words),
                     ("check retry and independence", check_retry_independence),
                     ("recognize reverses retrieve", recognize_reverses_retrieve),
                     ("40 failed Batch 0 checks", forty_failed_checks),
                     ("unavailable check advances", unavailable_check_advances),
                     ("baseline skip paths", skip_cases), ("resume, replay, quit", replay_resume_quit),
                     ("practice hints and script notices", hints_and_scripts),
                     ("file-free and silent", file_free), ("timer and verdict", timer)):
        check(name, fn)
    print(f"{COUNT} checks passed")
