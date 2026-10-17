"""Phone-sized browser checks for the static Sejong renderer."""

import contextlib
import json
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

from build_web import build


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
SHOTS = ROOT / "docs/tasks/2026-10-17_sejong-web-shots"
PASS = 0


def check(name, function):
    global PASS
    function()
    PASS += 1
    print(f"PASS {name}")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def log_message(self, *_):
        pass


def ready(page, url):
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_function("window.__sejongTest && window.__sejongTest.ready()", timeout=120000)


def current(page):
    return page.evaluate("window.__sejongTest.current()")


def click_answer(page, answer):
    card = current(page)["card"]
    history_before = len(page.evaluate("__sejongTest.history()"))
    if current(page)["await"]["input"] == "choice":
        options = page.locator("#controls button.choice")
        choices = options.all_text_contents()
        options.nth(choices.index(answer)).click()
    else:
        page.locator("#controls input").fill(answer)
        page.locator("#controls button.primary").click()
    page.wait_for_function("count => __sejongTest.history().length > count", arg=history_before)


def step(page, wrong=False):
    kind = page.locator("#screen").get_attribute("data-kind")
    if kind in ("question", "predict"):
        answer = page.evaluate("window.__sejongTest.answer()")
        card = current(page)["card"]
        if wrong and card.get("context") == "practice":
            if current(page)["await"]["input"] == "choice":
                answer = next(x for x in current(page)["await"]["choices"] if x != answer)
            else:
                answer = "wrong"
        click_answer(page, answer)
    else:
        page.locator("#controls button.primary").click()


def play(page, *, wrong_every_third=False, capture=None):
    cards = 0
    for _ in range(400):
        kind = page.locator("#screen").get_attribute("data-kind")
        if capture:
            capture(page, kind)
        if kind == "finished":
            return
        card = current(page)["card"]
        wrong = bool(wrong_every_third and kind == "question" and
                     card.get("context") == "practice" and cards % 3 == 2)
        if kind in ("question", "predict"):
            cards += 1
        step(page, wrong)
    raise AssertionError("browser flow did not finish")


def advance_to(page, predicate):
    for _ in range(200):
        if predicate(page):
            return
        step(page)
    raise AssertionError("target card not reached")


def screen_kind(page):
    return page.locator("#screen").get_attribute("data-kind")


def normalized(groups):
    def strip(value):
        if isinstance(value, list):
            return [strip(item) for item in value]
        if isinstance(value, dict):
            return {key: strip(item) for key, item in value.items()
                    if key not in ("active_ms", "time_text", "projected_minutes")}
        return value
    return strip(groups)


def main():
    if not (WEB / "pyodide/pyodide.js").exists():
        raise SystemExit("Run scripts/fetch_pyodide.py first")
    build()
    SHOTS.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/?test=1&seed=1"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            def context(scheme="light", **kwargs):
                return browser.new_context(viewport={"width": 412, "height": 915},
                    is_mobile=True, has_touch=True, color_scheme=scheme, **kwargs)

            def smoke(scheme):
                ctx = context(scheme)
                page = ctx.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("console", lambda message: errors.append(message.text)
                        if message.type == "error" and "font" not in message.text.lower() else None)
                ready(page, url)
                assert not errors, errors
                assert page.locator("#screen").get_attribute("data-kind") == "narrator"
                assert page.locator(".letter-chip").count() == 0
                assert page.evaluate("getComputedStyle(document.body).backgroundColor")
                ctx.close()
            check("load without console errors in light and dark", lambda: [smoke(x) for x in ("light", "dark")])

            def full_runs():
                for wrong in (False, True):
                    ctx = context()
                    page = ctx.new_page()
                    ready(page, url)
                    play(page, wrong_every_third=wrong)
                    assert page.evaluate("__sejongTest.state().outcome") == "victory_1"
                    ctx.close()
            check("always-correct and every-third-wrong runs finish", full_runs)

            def coverage_and_inputs():
                ctx = context()
                page = ctx.new_page()
                ready(page, url)
                hinted = False
                script_notice = False
                upper_na = False
                unknown = False
                for _ in range(220):
                    kind = screen_kind(page)
                    if kind == "finished":
                        break
                    card = current(page)["card"]
                    if kind == "question" and card["hint_available"] and not hinted:
                        page.locator("#controls .hint-button").click()
                        assert page.locator(".hint-text").count() == 1
                        hinted = True
                    if kind == "question" and card["display"] == "나" and card["input"] == "text":
                        if not script_notice:
                            click_answer(page, "나")
                            assert screen_kind(page) == "question" and page.locator(".notice").count() == 1
                            script_notice = True
                        if not upper_na:
                            field = page.locator("#controls input")
                            assert field.get_attribute("autocapitalize") == "none"
                            assert field.get_attribute("autocorrect") == "off"
                            assert field.get_attribute("autocomplete") == "off"
                            assert field.get_attribute("spellcheck") == "false"
                            assert field.get_attribute("enterkeyhint") == "go"
                            assert current(page)["await"]["placeholder"] == field.get_attribute("placeholder")
                            click_answer(page, "NA")
                            latest = page.evaluate("__sejongTest.history().at(-1)")
                            assert any(event["kind"] == "result" and event["correct"] for event in latest), latest
                            upper_na = True
                            continue
                    if kind == "question" and not unknown:
                        page.evaluate("__sejongTest.inject({kind:'future_event'})")
                        assert screen_kind(page) == "question"
                        unknown = True
                    step(page)
                assert screen_kind(page) == "finished"
                kinds = {event["kind"] for group in page.evaluate("__sejongTest.history()") for event in group}
                assert {"stage", "narrator", "before_word", "letter_intro", "predict", "reveal",
                        "question", "result", "hint", "notice", "word_read", "score", "milestone",
                        "await", "finished"} <= kinds, kinds
                assert hinted and script_notice and upper_na and unknown
                log = page.evaluate("__sejongTest.log()")
                assert any(x["input_type"] == "choice" for x in log), log[:8]
                assert any(x["input_type"] == "text" for x in log)
                assert any(x["hint_used"] for x in log)
                assert page.evaluate("window.__sejongTest !== undefined")
                page.locator("#controls button", has_text="Copy results").click()
                report = json.loads(page.locator(".dialog textarea").input_value())
                assert report["app_version"].startswith("sejong-web-1:")
                assert report["log"] == log and report["active_ms"] == page.evaluate("__sejongTest.state().active_ms")
                ctx.close()
            check("event coverage, unknown kind, text input, hint and results", coverage_and_inputs)

            def resume_card(context_name):
                ctx = context()
                page = ctx.new_page()
                ready(page, url)
                advance_to(page, lambda p: screen_kind(p) == "question" and
                           current(p)["card"]["context"] == context_name and
                           current(p)["card"]["mode"] == "read_aloud")
                before = current(page)["card"]
                snapshot = page.evaluate("localStorage.getItem('sejong.slice.v1')")
                assert snapshot
                history_len = len(page.evaluate("__sejongTest.history()"))
                clone_ctx = context()
                clone_ctx.add_init_script("localStorage.setItem('sejong.slice.v1', " + json.dumps(snapshot) + ")")
                clone = clone_ctx.new_page()
                ready(clone, url)
                assert "Your place is saved" in clone.locator("#screen").inner_text()
                step(clone)
                assert current(clone)["card"]["qid"] == before["qid"]
                assert current(clone)["card"]["display"] == before["display"]
                play(page)
                play(clone)
                original_tail = page.evaluate("__sejongTest.history()")[history_len:]
                clone_tail = clone.evaluate("__sejongTest.history()")[1:]
                assert normalized(original_tail) == normalized(clone_tail)
                assert page.evaluate("__sejongTest.state().outcome") == clone.evaluate("__sejongTest.state().outcome")
                clone_ctx.close(); ctx.close()
            check("reload and replay mid-batch", lambda: resume_card("practice"))
            check("reload and replay mid-check", lambda: resume_card("check"))

            def timer_pauses():
                ctx = context()
                page = ctx.new_page()
                ready(page, url)
                advance_to(page, lambda p: screen_kind(p) == "question")
                page.evaluate("__sejongTest.hidden()")
                step(page)
                assert "clock stopped" in page.locator("#screen").inner_text()
                step(page)
                assert screen_kind(page) == "question"
                page.evaluate("__sejongTest.idle(180000)")
                assert page.evaluate("__sejongTest.clock().paused")
                step(page)
                assert "clock stopped" in page.locator("#screen").inner_text()
                step(page)
                play(page)
                submissions = page.evaluate("__sejongTest.submissions()")
                counted = sum(item["ms"] for item in submissions if item["letters_known"])
                assert page.evaluate("__sejongTest.state().active_ms") == counted
                assert max(item["ms"] for item in submissions) < 130000
                ctx.close()
            check("hidden and idle time stop the clock", timer_pauses)

            def storage_failure():
                ctx = context()
                ctx.add_init_script("Object.defineProperty(window, 'localStorage', {get(){throw Error('blocked')}})")
                page = ctx.new_page()
                ready(page, url)
                play(page)
                assert screen_kind(page) == "finished"
                ctx.close()
            check("storage exceptions do not stop play", storage_failure)

            def public_hook_absent():
                ctx = context()
                page = ctx.new_page()
                page.goto(url.split("?")[0], wait_until="domcontentloaded")
                page.wait_for_function("document.querySelector('#screen')?.dataset.kind === 'narrator'", timeout=120000)
                assert page.evaluate("window.__sejongTest === undefined")
                ctx.close()
            check("answer hook is absent outside test mode", public_hook_absent)

            def screenshots_and_timings():
                names = ("loading", "before_word", "letter_intro", "predict", "reveal",
                         "build_card", "miss_with_tip", "word_read", "check", "milestone", "finished")
                for scheme in ("light", "dark"):
                    ctx = context(scheme)
                    page = ctx.new_page()
                    started = time.perf_counter()
                    page.goto(url, wait_until="domcontentloaded")
                    assert screen_kind(page) == "loading"
                    page.screenshot(path=str(SHOTS / f"{scheme}-loading.png"))
                    page.wait_for_function("window.__sejongTest && window.__sejongTest.ready()", timeout=120000)
                    cold = time.perf_counter() - started
                    first_steps = page.evaluate("__sejongTest.timings()")
                    started = time.perf_counter()
                    page.reload(wait_until="domcontentloaded")
                    page.wait_for_function("window.__sejongTest && window.__sejongTest.ready()", timeout=120000)
                    cached = time.perf_counter() - started
                    cached_steps = page.evaluate("__sejongTest.timings()")
                    print("LOAD_TIMINGS", scheme, json.dumps({"cold_s": round(cold, 3),
                        "cached_s": round(cached, 3), "cold_steps_s": first_steps,
                        "cached_steps_s": cached_steps}))
                    seen = {"loading"}
                    missed = False
                    for _ in range(220):
                        kind = screen_kind(page)
                        card = current(page)["card"]
                        event = current(page)["visible"]
                        name = kind
                        if kind == "question" and card.get("mode") == "build_syllable" and card.get("context") == "practice":
                            name = "build_card"
                        elif kind == "question" and card.get("context") == "check":
                            name = "check"
                        elif kind == "result" and event and not event["correct"] and (event.get("tell") or event.get("chosen_is") or event.get("line")):
                            name = "miss_with_tip"
                        if name in names and name not in seen:
                            if name == "reveal":
                                page.wait_for_timeout(1200)
                            page.screenshot(path=str(SHOTS / f"{scheme}-{name}.png"))
                            seen.add(name)
                        if kind == "finished":
                            break
                        wrong = (kind == "question" and card.get("context") == "practice" and
                                 card.get("mode") == "build_syllable" and not missed)
                        if wrong:
                            missed = True
                        step(page, wrong)
                    assert seen == set(names), (scheme, sorted(set(names) - seen))
                    ctx.close()
            check("phone screenshots in light and dark, with cold and cached timings", screenshots_and_timings)

            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print(f"{PASS} web checks passed")


if __name__ == "__main__":
    main()
