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
            if e["kind"] == "result" and e["qid"].split("-")[1] in ("baseline", "check", "post_test"):
                assert "line" not in e
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
                return "WRONG"
        return answer
    events = flattened(run(new_flow(), mutate=miss))
    assert any(e["kind"] == "result" and e["requeued"] for e in events)
    assert any(e["kind"] == "question" and e.get("round", {}).get("size", 0) > 16 for e in events)
    assert events[-1]["outcome"] == "victory_1"


def narrator_and_words():
    first_target = None
    misses = 0
    def twice(flow, events, answer, step):
        nonlocal first_target, misses
        if flow.phase == "build" and flow.batch_index == 0:
            if first_target is None:
                first_target = flow.current["target"]
            if flow.current["target"] == first_target and misses < 2:
                misses += 1
                return next(x for x in flow.current["card"]["choices"] if x != answer)
        return answer
    events = flattened(run(new_flow(), mutate=twice))
    lines = [e["line"]["line_id"] for e in events if e["kind"] == "result" and "line" in e]
    assert "lines.miss_no_tell" in lines
    assert any(x.startswith("lines.repeated_miss.") for x in lines)
    words = [e for e in events if e["kind"] == "word_read"]
    assert len(words) == 18 and len({w["ko"] for w in words}) == 18
    assert words[0]["line"]["line_id"] == "lines.first_word_read"
    assert next(w for w in words if w["ko"] == "바보")["line"]["line_id"] == "lines.fool_word"
    assert next(w for w in words if w["ko"] == "도도")["line"]["line_id"] == "lines.dodo_word"


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
    assert milestone["active_ms"] == 15000 * (len(transcript) - 1)
    minutes = max(1, int(milestone["active_ms"] / 60000 + .5))
    assert milestone["time_text"] == f"{minutes} minute" + ("" if minutes == 1 else "s")
    assert milestone["verdict"]["projected_minutes"] == milestone["active_ms"] / 60000 * 3
    expected = next(row["id"] for row in CONTENT["wager"]["verdict_tiers_minutes"]
                    if row["max"] is None or milestone["verdict"]["projected_minutes"] <= row["max"])
    assert milestone["verdict"]["tier"] == expected


if __name__ == "__main__":
    for name, fn in (("event contract", contract), ("all-correct order and scores", order_and_scores),
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
