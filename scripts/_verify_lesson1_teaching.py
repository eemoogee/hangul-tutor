"""Deterministic Lesson 1 guide and phone rendering checks.

Requires the same Playwright/Chromium setup as _verify_web.py.
"""

import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / ".verify_out" / "lesson1"
sys.path.insert(0, str(ROOT))
from curriculum_flow import CurriculumFlow, LessonOneTeaching  # noqa: E402
from hangul_quiz_engine import HangulQuiz, QuizQuestion  # noqa: E402
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
    first = guide.current()
    assert first["kind"] == "teaching_intro"
    assert "roughly “juhng.”" in first["dialogue"]
    first = guide.submit("/continue")
    assert first["kind"] == "teaching_predict"
    assert first["blocks"] == ["아", "어"]
    assert guide.submit("different")["correct"] is False
    guide = LessonOneTeaching.from_state(quiz.current_lesson, {}, guide.export_state())
    assert guide.current()["kind"] == "teaching_feedback"
    explorer = guide.submit("/continue")
    assert [item["jamo"] for item in explorer["letters"]] == quiz.current_lesson["letters"]
    assert [item["syllable"] for item in explorer["letters"]] == quiz.current_lesson["mastery_syllables"]
    assert guide.submit("ㅜ")["selected"] == "ㅜ"
    guide = LessonOneTeaching.from_state(quiz.current_lesson, {}, guide.export_state())
    assert guide.current()["selected"] == "ㅜ"
    assert guide.submit("/practice")["kind"] == "teaching_done"
    flow = CurriculumFlow(quiz)
    for mode in ("read_aloud", "real_word", "nonword_decode", "sequence_decode"):
        flow.current_question = QuizQuestion(mode=mode, prompt="Read **아**", correct_answer="a",
                                              lesson_id=1, letter="아")
        card = flow._question_event()
        assert card["display"] == "아"
        assert "아" not in card["prompt"]
    flow.current_question = QuizQuestion(mode="spell", prompt="Write a", correct_answer="아",
                                          lesson_id=1, letter="아")
    assert "display" not in flow._question_event()
    print("PASS Python guide content, response, and state restore")


def browser_checks():
    build()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/?course=curriculum&test=1&seed=7"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 390, "height": 844},
                                          device_scale_factor=1, is_mobile=True, has_touch=True)
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_function("window.__curriculumTest?.ready()", timeout=120000)
            SHOTS.mkdir(parents=True, exist_ok=True)
            assert page.locator("#screen").get_attribute("data-kind") == "lesson1_teaching"
            assert "roughly “juhng.”" in page.locator(".dialogue-text").inner_text()
            page.reload()
            page.wait_for_function("window.__curriculumTest?.ready()", timeout=120000)
            assert "roughly “juhng.”" in page.locator(".dialogue-text").inner_text()
            page.screenshot(path=str(SHOTS / "intro-390x844.png"))
            page.set_viewport_size({"width": 320, "height": 568})
            intro_narrow = page.evaluate("""() => ({panel: document.querySelector('#screen').scrollHeight,
              panel_view: document.querySelector('#screen').clientHeight,
              controls_bottom: document.querySelector('#controls').getBoundingClientRect().bottom})""")
            assert intro_narrow["panel"] <= intro_narrow["panel_view"] + 1
            assert intro_narrow["controls_bottom"] <= 568
            print(f"INTRO_320x568 {intro_narrow}")
            page.screenshot(path=str(SHOTS / "intro-320x568.png"))
            page.set_viewport_size({"width": 390, "height": 844})
            page.get_by_role("button", name="Look at two blocks").click()
            assert page.locator("#controls button.choice").count() == 2
            assert page.locator("#controls button").all_text_contents() == ["ㅇ", "ㅏ and ㅓ", "Go straight to practice"]
            boxes = [page.locator(selector).bounding_box() for selector in
                     (".character-stage", ".dialogue-panel", ".teaching-exercise")]
            assert boxes[0]["y"] < boxes[1]["y"] < boxes[2]["y"]
            assert page.evaluate("document.documentElement.scrollHeight <= innerHeight + 1")
            assert page.evaluate("document.querySelector('#screen').scrollHeight <= document.querySelector('#screen').clientHeight + 1")
            page.screenshot(path=str(SHOTS / "predict-390x844.png"))
            page.set_viewport_size({"width": 320, "height": 568})
            predict_narrow = page.evaluate("""() => ({panel: document.querySelector('#screen').scrollHeight,
              panel_view: document.querySelector('#screen').clientHeight,
              controls_bottom: document.querySelector('#controls').getBoundingClientRect().bottom})""")
            assert predict_narrow["panel"] <= predict_narrow["panel_view"] + 1
            print(f"PREDICT_320x568 {predict_narrow}")
            page.screenshot(path=str(SHOTS / "predict-320x568.png"))
            page.set_viewport_size({"width": 390, "height": 844})
            print("PASS immediate learner choice and stage/dialogue/exercise order")

            page.locator("#controls button.choice").first.click()
            assert "YOU FOUND IT" in page.locator("#screen").inner_text()
            page.reload()
            page.wait_for_function("window.__curriculumTest?.ready()", timeout=120000)
            assert "YOU FOUND IT" in page.locator("#screen").inner_text()
            page.get_by_role("button", name="Meet the six vowels").click()
            assert page.locator(".vowel-tile").count() == 6
            assert page.evaluate("document.documentElement.scrollHeight <= innerHeight + 1")
            assert page.evaluate("document.querySelector('#screen').scrollHeight <= document.querySelector('#screen').clientHeight + 1")
            page.screenshot(path=str(SHOTS / "vowels-390x844.png"))
            page.set_viewport_size({"width": 320, "height": 568})
            narrow = page.evaluate("""() => ({page: document.documentElement.scrollHeight,
              viewport: innerHeight, panel: document.querySelector('#screen').scrollHeight,
              panel_view: document.querySelector('#screen').clientHeight,
              controls_bottom: document.querySelector('#controls').getBoundingClientRect().bottom})""")
            assert narrow["page"] <= narrow["viewport"] + 1
            assert narrow["controls_bottom"] <= narrow["viewport"]
            print(f"PHONE_320x568 {narrow}")
            page.set_viewport_size({"width": 390, "height": 844})
            page.evaluate("document.documentElement.style.fontSize = '200%'")
            enlarged = page.evaluate("""() => ({page: document.documentElement.scrollHeight,
              viewport: innerHeight, panel: document.querySelector('#screen').scrollHeight,
              panel_view: document.querySelector('#screen').clientHeight,
              controls_bottom: document.querySelector('#controls').getBoundingClientRect().bottom})""")
            assert enlarged["controls_bottom"] <= enlarged["viewport"]
            assert enlarged["panel_view"] > 100
            print(f"TEXT_200_PERCENT_390x844 {enlarged}")
            page.screenshot(path=str(SHOTS / "enlarged-text-390x844.png"))
            page.evaluate("document.documentElement.style.fontSize = ''")
            page.locator(".vowel-tile").filter(has_text="ㅜ").click()
            assert page.locator(".vowel-tile.selected").inner_text().startswith("ㅜ")
            page.reload()
            page.wait_for_function("window.__curriculumTest?.ready()", timeout=120000)
            assert page.locator(".vowel-tile.selected").inner_text().startswith("ㅜ")
            page.get_by_role("button", name="Start practice").click()
            assert page.locator("#screen").get_attribute("data-kind") == "question"
            question = page.evaluate("__curriculumTest.current().card")
            assert question["mode"] == "read_aloud"
            assert question["display"] == "아"
            assert "아" not in question["prompt"]
            assert page.locator("#screen .big-hangul").inner_text() == "아"
            page.screenshot(path=str(SHOTS / "practice-390x844.png"))
            page.reload()
            page.wait_for_function("window.__curriculumTest?.ready()", timeout=120000)
            assert page.evaluate("__curriculumTest.current().card") == question
            page.set_viewport_size({"width": 390, "height": 500})
            answer_button = page.locator("#controls button.primary")
            if answer_button.count():
                page.locator("#controls input").focus()
                bottom = answer_button.first.bounding_box()["y"] + answer_button.first.bounding_box()["height"]
                assert bottom <= 500, bottom
                print(f"KEYBOARD_SIM_390x500 answer_button_bottom={bottom:.1f}")
            page.set_viewport_size({"width": 390, "height": 844})
            print("PASS teaching and practice reload; first question reached with one passive Continue tap")

            page.get_by_role("button", name="Open menu").click()
            page.get_by_role("button", name="Review this lesson").click()
            page.wait_for_function("""() => {
                const image = document.querySelector('.character-stage img');
                return image?.complete && image.naturalWidth === 340 &&
                    image.naturalHeight === 448 && image.src.endsWith('/assets/jeong_hello.png');
            }""")
            page.screenshot(path=str(SHOTS / "revisit-390x844.png"))
            page.get_by_role("button", name="Go straight to practice").click()
            assert page.evaluate("__curriculumTest.current().card") == question
            print("PASS review and skip retain the unanswered question")
            page.evaluate("__curriculumTest.solidify()")
            page.get_by_role("button", name="Reading check").click()
            assert page.locator("#screen").get_attribute("data-kind") == "check_intro"
            page.get_by_role("button", name="Begin check").click()
            assert page.locator("#screen").get_attribute("data-kind") == "check_question"
            check_question = page.evaluate("__curriculumTest.current().card")
            page.reload()
            page.wait_for_function("window.__curriculumTest?.ready()", timeout=120000)
            assert page.evaluate("__curriculumTest.current().card") == check_question
            print("PASS reading-check reload keeps the same prompt (test-hook mastery setup)")
            context.close()

            keyboard_context = browser.new_context(viewport={"width": 390, "height": 844})
            keyboard_page = keyboard_context.new_page()
            keyboard_page.goto(url, wait_until="domcontentloaded")
            keyboard_page.wait_for_function("window.__curriculumTest?.ready()", timeout=120000)
            keyboard_page.locator("#menu-button").focus()
            keyboard_page.keyboard.press("Tab")
            assert keyboard_page.evaluate("document.activeElement.textContent") == "Look at two blocks"
            assert keyboard_page.evaluate("getComputedStyle(document.activeElement).outlineWidth") == "3px"
            keyboard_page.keyboard.press("Enter")
            keyboard_page.locator("#menu-button").focus()
            keyboard_page.keyboard.press("Tab")
            assert keyboard_page.evaluate("document.activeElement.textContent") == "ㅇ"
            keyboard_page.keyboard.press("Enter")
            assert "YOU FOUND IT" in keyboard_page.locator("#screen").inner_text()
            print("PASS keyboard navigation, visible focus, and Enter activation")
            cdp = keyboard_context.new_cdp_session(keyboard_page)
            cdp.send("Emulation.setPageScaleFactor", {"pageScaleFactor": 2})
            scale = keyboard_page.evaluate("visualViewport.scale")
            assert scale >= 1.9, scale
            keyboard_page.get_by_role("button", name="Meet the six vowels").focus()
            keyboard_page.keyboard.press("Enter")
            assert keyboard_page.locator(".vowel-tile").count() == 6
            print(f"PASS keyboard action at 200% emulated page scale (scale={scale})")
            cdp.send("Emulation.setPageScaleFactor", {"pageScaleFactor": 1})
            keyboard_context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    python_checks()
    browser_checks()
