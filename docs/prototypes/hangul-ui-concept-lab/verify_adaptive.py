"""Browser checks for the standalone adaptive composition experiment."""
import atexit
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
SHOTS = ROOT.parents[2] / ".verify_out" / "concept-lab"
SHOTS.mkdir(parents=True, exist_ok=True)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *_):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
Thread(target=server.serve_forever, daemon=True).start()
atexit.register(server.server_close)
atexit.register(server.shutdown)
URL = f"http://127.0.0.1:{server.server_port}/adaptive-composition.html"


def visible_shell(page, height):
    data = page.evaluate("""() => {
      const shell=document.querySelector('.shell').getBoundingClientRect();
      const footer=document.querySelector('.footer').getBoundingClientRect();
      const work=document.querySelector('.workspace');
      return {shellBottom:shell.bottom, footerBottom:footer.bottom,
              workClient:work.clientHeight, workScroll:work.scrollHeight,
              horizontal:document.documentElement.scrollWidth-innerWidth};
    }""")
    assert data["shellBottom"] <= height + 1, data
    assert data["footerBottom"] <= height + 1, data
    assert data["workClient"] > 35, data
    assert data["horizontal"] <= 1, data
    return data


with sync_playwright() as p:
    browser = p.chromium.launch()
    for width, height in ((390, 844), (320, 568)):
        context = browser.new_context(viewport={"width": width, "height": height},
                                      device_scale_factor=1, is_mobile=True, has_touch=True)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(URL, wait_until="domcontentloaded")
        assert page.locator('a[aria-label="Open unchanged baseline"]').get_attribute("href") == "baseline.html"
        for concept in ("a", "b", "c"):
            page.locator(f'[data-concept="{concept}"]').click()
            assert page.locator(".shell").get_attribute("class").endswith(f"theme-{concept}")
            visible_shell(page, height)
            page.locator('[data-tile="ㅗ"]').click()
            page.locator('[data-slot="vowel"]').click()
            assert "horizontal vowel" in page.locator(".feedback").inner_text()
            page.locator('[data-tile="ㅏ"]').click()
            page.locator('[data-slot="vowel"]').click()
            assert "makes 나" in page.locator(".feedback").inner_text()
            assert page.locator(".block.vertical .part").count() == 2
            vertical = [page.locator(".block.vertical .part").nth(i).bounding_box() for i in range(2)]
            assert vertical[0]["x"] < vertical[1]["x"]
            if width == 390:
                page.screenshot(path=str(SHOTS / f"{concept}-discover-390x844.png"))
            page.locator('[data-action="primary"]').last.click()
            assert "Choose the flat vowel" in page.locator(".task").inner_text()
            page.locator('[data-tile="ㅗ"]').click()
            page.locator('[data-slot="vowel"]').click()
            parts = [page.locator(".block.horizontal .part").nth(i).bounding_box() for i in range(2)]
            assert parts[0]["y"] < parts[1]["y"]
            assert "makes 노" in page.locator(".feedback").inner_text()
            page.locator('[data-mode="predict"]').click()
            page.locator('[data-predict="ㅓ"]').click()
            assert "changes the vowel sound" in page.locator(".feedback").inner_text()
            page.locator('[data-predict="ㅏ"]').click()
            assert "completes 나" in page.locator(".feedback").inner_text()
            if width == 390:
                page.screenshot(path=str(SHOTS / f"{concept}-predict-390x844.png"))
            page.locator('[data-action="primary"]').last.click()
            page.locator('[data-predict="ㅏ"]').click()
            assert "horizontal vowel" in page.locator(".feedback").inner_text() or "changes the vowel" in page.locator(".feedback").inner_text()
            page.locator('[data-predict="ㅗ"]').click()
            page.locator('[data-action="primary"]').last.click()
            page.locator('[data-predict="ㄷ"]').click()
            assert "first sound" in page.locator(".feedback").inner_text()
            page.locator('[data-predict="ㄴ"]').click()
            assert "completes 노" in page.locator(".feedback").inner_text()
            page.locator('[data-mode="recall"]').click()
            page.locator('[data-recall="consonant:ㄷ"]').click()
            page.locator('[data-recall="vowel:ㅏ"]').click()
            page.locator('[data-action="primary"]').last.click()
            assert "first sound" in page.locator(".feedback").inner_text()
            page.locator('[data-recall="consonant:ㄴ"]').click()
            page.locator('[data-recall="vowel:ㅗ"]').click()
            page.locator('[data-action="primary"]').last.click()
            assert "vowel sound" in page.locator(".feedback").inner_text()
            page.locator('[data-recall="vowel:ㅏ"]').click()
            page.locator('[data-action="primary"]').last.click()
            assert "built 나" in page.locator(".feedback").inner_text()
            if width == 390:
                page.screenshot(path=str(SHOTS / f"{concept}-recall-390x844.png"))
            page.locator('[data-action="primary"]').last.click()
            page.locator('[data-action="keyboard"]').first.click()
            visible_shell(page, height - 156)
            if width == 320 and concept == "c":
                page.screenshot(path=str(SHOTS / "c-recall-keyboard-320x568.png"))
            reach = page.evaluate("""() => ({
              input: document.querySelector('#answer').getBoundingClientRect().bottom,
              work: document.querySelector('.workspace').getBoundingClientRect().bottom
            })""")
            assert reach["input"] <= reach["work"] + 1, reach
            page.locator('[data-key="노"]').click()
            assert page.locator("#answer").input_value() == "노"
            page.locator('[data-action="primary"]').last.click()
            assert "built 노" in page.locator(".feedback").inner_text()
            page.locator('[data-action="keyboard"]').first.click()
            page.locator('[data-action="primary"]').last.click()
            assert page.locator(".task").inner_text().startswith("Read this Hangul")
            assert "“no”" not in page.locator(".task").inner_text().lower()
            assert "노 reads" not in page.locator(".dialogue").inner_text()
            page.locator("#answer").fill("na")
            page.locator('[data-action="primary"]').last.click()
            assert "Look again" in page.locator(".feedback").inner_text()
            page.locator("#answer").fill("no")
            page.locator('[data-action="primary"]').last.click()
            assert "노 reads" in page.locator(".feedback").inner_text()
            page.locator('[data-action="long"]').click()
            assert len(page.locator(".dialogue-text").inner_text()) > 70
            visible_shell(page, height)
            page.locator('[data-action="review"]').click()
            assert page.locator('[role="dialog"]').is_visible()
            page.locator('[data-review="predict:2"]').click()
            assert "Which consonant" in page.locator(".task").inner_text()
            page.locator('[data-action="back"]').click()
            assert "Which vowel" in page.locator(".task").inner_text()
            page.locator('[data-action="long"]').click()
            page.locator('[data-mode="discover"]').click()
            page.locator('[data-action="reset"]').click()
            visible_shell(page, height)
        assert not errors, errors
        print(f"PASS {width}x{height}: all three concepts, Discover/Predict/Recall, correction, keyboard, long text, Back/Review, layout")
        context.close()
    desktop = browser.new_context(viewport={"width": 390, "height": 844})
    page = desktop.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.locator('[data-tile="ㅏ"]').drag_to(page.locator('[data-slot="vowel"]'))
    assert "makes 나" in page.locator(".feedback").inner_text()
    print("PASS desktop drag-to-slot alternative")
    page.goto(URL + "?concept=c&mode=recall", wait_until="domcontentloaded")
    assert page.locator('[data-concept="c"]').get_attribute("aria-pressed") == "true"
    assert page.locator('[data-mode="recall"]').get_attribute("aria-selected") == "true"
    print("PASS direct concept and mode links")
    desktop.close()
    browser.close()
