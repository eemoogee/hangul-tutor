"""Focused Lesson 1 flow, save, and phone rendering checks."""
import json
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / ".verify_out" / "lesson1"
sys.path.insert(0, str(ROOT))
from curriculum_flow import LessonOneTeaching  # noqa: E402
from hangul_quiz_engine import HangulQuiz  # noqa: E402
from build_web import build  # noqa: E402


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "web"), **kwargs)
    def log_message(self, *_):
        pass


def python_checks():
    quiz = HangulQuiz(persist=False)
    quiz.start_lesson(1)
    guide = LessonOneTeaching(quiz.current_lesson)
    assert guide.current()["kind"] == "teaching_intro"
    assert "correct_answer" not in guide.current()
    assert guide.submit("/continue")["pair"]["first"] == "ㅏ"
    assert guide.submit("ㅏ")["correct"] is False
    assert guide.submit("/continue")["pair"]["first"] == "ㅗ"
    assert guide.submit("ㅜ")["correct"] is True
    assert len(guide.submit("/continue")["letters"]) == 6
    assert guide.submit("/continue")["step"] == 0
    assert guide.submit("ㅇ")["step"] == 1
    restored = LessonOneTeaching.from_state(quiz.current_lesson, {}, guide.export_state())
    assert restored.current()["step"] == 1
    assert restored.submit("ㅏ")["result"] == "ㅇ + ㅏ = 아. Read it as a."
    assert restored.submit("/practice")["kind"] == "teaching_done"
    for actions in ((), ("/continue",), ("/continue", "ㅓ"),
                    ("/continue", "ㅓ", "/continue", "ㅜ", "/continue", "ㅣ"),
                    ("/continue", "ㅓ", "/continue", "ㅜ", "/continue", "/continue", "ㅇ")):
        skipped = LessonOneTeaching(quiz.current_lesson)
        for action in actions:
            skipped.submit(action)
        assert skipped.submit("/skip")["kind"] == "teaching_done"
        assert LessonOneTeaching.from_state(quiz.current_lesson, {},
                                            skipped.export_state()).current()["kind"] == "teaching_done"
    for phase in ("intro", "predict", "feedback", "explore", "done"):
        old = json.dumps({"phase": phase,
                          "choice": "ㅇ" if phase in ("feedback", "explore") else None,
                          "selected": "ㅜ" if phase == "explore" else None})
        normalized = LessonOneTeaching.from_state(quiz.current_lesson, {}, old)
        LessonOneTeaching.from_state(quiz.current_lesson, {}, normalized.export_state())
    print("PASS Python pair choices, construction, and legacy state normalization")


def browser_checks():
    build()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/?course=curriculum&test=1&seed=7"
    SHOTS.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 390, "height": 844},
                                          device_scale_factor=1, is_mobile=True, has_touch=True)
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_function("window.__curriculumTest?.ready()", timeout=120000)
            held = page.evaluate("__curriculumTest.state()")

            def reload_step(step):
                page.reload()
                page.wait_for_function("window.__curriculumTest?.ready()", timeout=120000)
                assert page.locator("#screen").get_attribute("data-step") == step
                state = page.evaluate("__curriculumTest.state()")
                assert state["current_question"] == held["current_question"]
                assert state["round_asked"] == held["round_asked"]
                for width, height in ((390, 744), (320, 568)):
                    page.set_viewport_size({"width": width, "height": height})
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                    action = page.locator("#controls button").last
                    action.scroll_into_view_if_needed()
                    assert action.bounding_box()["y"] + action.bounding_box()["height"] <= height + 1
                page.set_viewport_size({"width": 390, "height": 844})
                page.evaluate("window.scrollTo(0, 0)")

            def shot(name):
                page.screenshot(path=str(SHOTS / f"{name}-390x844.png"))

            assert page.locator("#screen").get_attribute("data-step") == "teaching_intro"
            assert "I’m Jeong" in page.locator(".dialogue-text").inner_text()
            assert page.locator(".lesson-vowel-strip span").count() == 6
            shot("intro")
            reload_step("teaching_intro")
            page.get_by_role("button", name="Try the first pair").click()
            shot("prediction")
            reload_step("teaching_pair_predict")
            page.get_by_role("button", name="ㅏ", exact=True).click()
            assert "short stroke moves left" in page.locator(".dialogue-text").inner_text()
            assert "lips not rounded" in page.locator(".pair-comparison").inner_text()
            shot("wrong-feedback")
            reload_step("teaching_pair_result")
            page.get_by_role("button", name="Try the next pair").click()
            reload_step("teaching_pair_predict")
            assert page.locator(".pair-target").inner_text().startswith("ㅗ")
            page.get_by_role("button", name="ㅗ", exact=True).click()
            assert "Below the line gives you ㅜ" in page.locator(".dialogue-text").inner_text()
            reload_step("teaching_pair_result")
            page.get_by_role("button", name="Meet the other two").click()
            assert page.locator(".vowel-tile").count() == 6
            assert "lips flat" in page.locator("#screen").inner_text()
            shot("reference")
            reload_step("teaching_explore")
            page.get_by_role("button", name="ㅜ, u, 우").click()
            assert page.locator(".memory-cue summary").inner_text() == "Memory cue"
            reload_step("teaching_explore")
            assert page.locator(".vowel-tile.selected").inner_text().startswith("ㅜ")
            page.get_by_role("button", name="Build your first block").click()
            reload_step("teaching_construct")
            assert page.locator(".construction-view").inner_text().count("□") == 2
            page.get_by_role("button", name="ㅇ", exact=True).click()
            reload_step("teaching_construct")
            assert page.locator(".construction-view").inner_text().count("□") == 1
            page.get_by_role("button", name="ㅏ", exact=True).click()
            reload_step("teaching_construct")
            assert "ㅇ + ㅏ = 아. Read it as a." in page.locator("#screen").inner_text()
            shot("construction")
            page.get_by_role("button", name="Start practice").click()
            assert page.locator("#screen").get_attribute("data-kind") == "question"
            assert page.evaluate("__curriculumTest.state().current_question") == held["current_question"]
            assert page.evaluate("__curriculumTest.state().round_asked") == held["round_asked"]
            shot("practice")
            page.reload()
            page.wait_for_function("window.__curriculumTest?.ready()", timeout=120000)
            assert page.locator("#screen").get_attribute("data-kind") == "question"
            page.get_by_role("button", name="Open menu").click()
            page.get_by_role("button", name="Review this lesson").click()
            page.get_by_role("button", name="Go straight to practice").click()
            assert page.evaluate("__curriculumTest.state().current_question") == held["current_question"]
            print("PASS every teaching reload, two wrong choices, construction, and held question")

            skip_context = browser.new_context(viewport={"width": 390, "height": 844})
            skip_page = skip_context.new_page()
            skip_page.goto(url, wait_until="domcontentloaded")
            skip_page.wait_for_function("window.__curriculumTest?.ready()", timeout=120000)
            skip_held = skip_page.evaluate("__curriculumTest.state().current_question")
            skip_page.get_by_role("button", name="Go straight to practice").click()
            assert skip_page.locator("#screen").get_attribute("data-kind") == "question"
            assert skip_page.evaluate("__curriculumTest.state().current_question") == skip_held
            skip_context.close()
            print("PASS first-visit skip releases the unchanged held question")

            keyboard_context = browser.new_context(viewport={"width": 390, "height": 844},
                                                   reduced_motion="reduce")
            keyboard_page = keyboard_context.new_page()
            keyboard_page.goto(url, wait_until="domcontentloaded")
            keyboard_page.wait_for_function("window.__curriculumTest?.ready()", timeout=120000)
            keyboard_page.locator("#menu-button").focus()
            keyboard_page.keyboard.press("Tab")
            assert keyboard_page.evaluate("document.activeElement.textContent") == "Try the first pair"
            assert keyboard_page.evaluate("getComputedStyle(document.activeElement).outlineWidth") == "3px"
            keyboard_page.keyboard.press("Enter")
            keyboard_page.locator("#controls button.choice").last.focus()
            keyboard_page.keyboard.press("Enter")
            assert keyboard_page.locator("#screen").get_attribute("data-step") == "teaching_pair_result"
            keyboard_context.close()
            print("PASS keyboard focus and reduced-motion choice activation")

            page.get_by_role("button", name="Open menu").click()
            page.get_by_role("button", name="Review this lesson").click()
            for width, height in ((390, 844), (320, 568)):
                page.set_viewport_size({"width": width, "height": height})
                metrics = page.evaluate("""() => ({width:document.documentElement.scrollWidth,
                  viewport:innerWidth, page:document.documentElement.scrollHeight,
                  action:document.querySelector('#controls').getBoundingClientRect().bottom})""")
                assert metrics["width"] <= metrics["viewport"] + 1, metrics
                assert metrics["action"] <= metrics["page"] + 1, metrics
                print(f"WELCOME_{width}x{height}", metrics)
            page.set_viewport_size({"width": 390, "height": 844})
            page.evaluate("document.documentElement.style.fontSize = '200%'")
            metrics = page.evaluate("""() => ({width:document.documentElement.scrollWidth,
              viewport:innerWidth, page:document.documentElement.scrollHeight,
              action:document.querySelector('#controls').getBoundingClientRect().bottom})""")
            assert metrics["width"] <= metrics["viewport"] + 1, metrics
            assert metrics["action"] <= metrics["page"] + 1, metrics
            page.screenshot(path=str(SHOTS / "enlarged-text-390x844.png"), full_page=True)
            print("TEXT_200_PERCENT", metrics)
            context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    python_checks()
    browser_checks()
