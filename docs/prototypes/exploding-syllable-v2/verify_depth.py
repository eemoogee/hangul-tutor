"""Browser comparison for the isolated flat and shallow-depth extraction modes."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[2] / ".verify_out" / "exploding-syllable-depth"
OUT.mkdir(parents=True, exist_ok=True)
URL = (ROOT / "index.html").as_uri()


def snapshot(page):
    return page.evaluate("window.__syllableV2.snapshot()")


def paths(page):
    return page.locator(".relief-component .stroke").evaluate_all(
        "nodes => nodes.map(node => node.getAttribute('d'))"
    )


def stroke_point(page, part="initial"):
    page.locator(f'.relief-component[data-part="{part}"]').scroll_into_view_if_needed()
    return page.locator(f'.relief-component[data-part="{part}"] .hit').evaluate("""path => {
      const p = path.getPointAtLength(path.getTotalLength() * .22);
      const q = new DOMPoint(p.x, p.y).matrixTransform(path.getScreenCTM());
      return {x:q.x,y:q.y};
    }""")


with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    errors = []
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    page.goto(URL, wait_until="domcontentloaded")
    page.locator('[data-method="extraction"]').click()
    assert snapshot(page)["condition"] == "flat"
    assert page.locator(".relief-piece").count() == 2
    assert page.locator("#lift-conditions").is_visible()
    rest = paths(page)
    page.screenshot(path=str(OUT / "01-flat-assembled.png"), full_page=True)

    point = stroke_point(page)
    page.mouse.click(point["x"], point["y"])
    page.wait_for_timeout(240)
    assert .2 < snapshot(page)["progress"]["initial"] < 1
    assert snapshot(page)["progress"]["medial"] == 0
    page.screenshot(path=str(OUT / "02-flat-partial.png"), full_page=True)
    page.wait_for_timeout(320)
    assert snapshot(page)["progress"]["initial"] > .99
    flat_full = paths(page)
    assert flat_full[1] == rest[1]
    page.screenshot(path=str(OUT / "03-flat-lifted.png"), full_page=True)

    lifted_point = stroke_point(page)
    page.mouse.click(lifted_point["x"], lifted_point["y"])
    page.wait_for_timeout(550)
    assert snapshot(page)["progress"]["initial"] < .01
    assert paths(page) == rest
    page.screenshot(path=str(OUT / "04-flat-restored.png"), full_page=True)

    page.locator("#progress").fill("50")
    flat_half = paths(page)
    page.locator('[data-condition="depth"]').click()
    assert snapshot(page)["condition"] == "depth"
    assert paths(page) == flat_half
    assert snapshot(page)["progress"]["initial"] == .5
    assert page.locator('[data-wrapper="initial"]').evaluate("el => getComputedStyle(el).transform").startswith("matrix3d")
    page.locator("#progress").fill("0")
    assert paths(page) == rest
    page.screenshot(path=str(OUT / "05-depth-assembled.png"), full_page=True)
    point = stroke_point(page)
    page.mouse.click(point["x"], point["y"])
    page.wait_for_timeout(240)
    assert .2 < snapshot(page)["progress"]["initial"] < 1
    assert snapshot(page)["progress"]["medial"] == 0
    z_partial = page.locator('[data-wrapper="initial"]').evaluate("el => getComputedStyle(el).transform")
    assert z_partial.startswith("matrix3d"), z_partial
    page.screenshot(path=str(OUT / "06-depth-partial.png"), full_page=True)
    page.wait_for_timeout(320)
    assert snapshot(page)["progress"]["initial"] > .99
    assert paths(page) == flat_full
    page.screenshot(path=str(OUT / "07-depth-lifted.png"), full_page=True)

    # A/B switching at a fixed state must leave every authored path and control value intact.
    depth_full = paths(page)
    page.locator('[data-condition="flat"]').click()
    assert paths(page) == depth_full
    assert snapshot(page)["progress"]["initial"] > .99
    flat_transform = page.locator('[data-wrapper="initial"]').evaluate("el => getComputedStyle(el).transform")
    assert flat_transform == "matrix(1, 0, 0, 1, 0, 0)", flat_transform
    page.locator('[data-condition="depth"]').click()
    point = stroke_point(page)
    page.mouse.click(point["x"], point["y"])
    page.wait_for_timeout(550)
    assert paths(page) == rest
    page.screenshot(path=str(OUT / "08-depth-restored.png"), full_page=True)

    # Adjacent pieces: the old one returns while the newly selected one lifts.
    point = stroke_point(page, "initial")
    page.mouse.click(point["x"], point["y"])
    page.wait_for_timeout(550)
    point = stroke_point(page, "medial")
    page.mouse.click(point["x"], point["y"])
    page.wait_for_timeout(550)
    assert snapshot(page)["progress"]["initial"] < .01
    assert snapshot(page)["progress"]["medial"] > .99
    page.locator('.relief-component[data-part="medial"]').focus()
    page.keyboard.press("Enter")
    page.wait_for_timeout(550)
    assert snapshot(page)["progress"]["medial"] < .01

    for width, height in [(390, 844), (320, 568)]:
        page.set_viewport_size({"width": width, "height": height})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        page.locator('[data-condition="depth"]').click()
        page.locator('.relief-component[data-part="initial"]').scroll_into_view_if_needed()
        point = stroke_point(page)
        page.mouse.click(point["x"], point["y"])
        page.wait_for_timeout(550)
        assert snapshot(page)["progress"]["initial"] > .99
        box = page.locator('[data-wrapper="initial"] .stroke').bounding_box()
        assert 0 <= box["x"] and box["x"] + box["width"] <= width
        page.screenshot(path=str(OUT / f"09-depth-{width}x{height}.png"), full_page=True)
        page.locator("#return-action").click()
        page.wait_for_timeout(550)

    touch = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    touch.on("pageerror", lambda error: errors.append(str(error)))
    touch.goto(URL, wait_until="domcontentloaded")
    touch.locator('[data-method="extraction"]').tap()
    touch.locator('[data-condition="depth"]').tap()
    point = stroke_point(touch)
    touch.touchscreen.tap(point["x"], point["y"])
    touch.wait_for_timeout(550)
    assert snapshot(touch)["progress"]["initial"] > .99
    point = stroke_point(touch)
    touch.touchscreen.tap(point["x"], point["y"])
    touch.wait_for_timeout(550)
    assert snapshot(touch)["progress"]["initial"] < .01
    before_scroll = touch.evaluate("scrollY")
    point = stroke_point(touch)
    cdp = touch.context.new_cdp_session(touch)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [point]})
    for step in range(1, 9):
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": point["x"] - step * 14, "y": point["y"] + step * 2}]})
        touch.wait_for_timeout(25)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    assert snapshot(touch)["progress"]["initial"] > .25
    assert abs(touch.evaluate("scrollY") - before_scroll) < 1
    small_touch = browser.new_page(viewport={"width": 320, "height": 568}, is_mobile=True, has_touch=True)
    small_touch.on("pageerror", lambda error: errors.append(str(error)))
    small_touch.goto(URL, wait_until="domcontentloaded")
    small_touch.locator('[data-method="extraction"]').tap()
    small_touch.locator('[data-condition="depth"]').tap()
    point = stroke_point(small_touch)
    small_touch.touchscreen.tap(point["x"], point["y"])
    small_touch.wait_for_timeout(550)
    assert snapshot(small_touch)["progress"]["initial"] > .99
    point = stroke_point(small_touch)
    small_touch.touchscreen.tap(point["x"], point["y"])
    small_touch.wait_for_timeout(550)
    assert snapshot(small_touch)["progress"]["initial"] < .01

    reduced = browser.new_page(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
    reduced.goto(URL, wait_until="domcontentloaded")
    reduced.locator('[data-method="extraction"]').click()
    reduced.locator('[data-choose="initial"]').click()
    assert snapshot(reduced)["progress"]["initial"] == 1
    reduced.locator('[data-condition="flat"]').click()
    assert snapshot(reduced)["progress"]["initial"] == 1
    reduced.locator('[data-choose="initial"]').click()
    assert snapshot(reduced)["progress"]["initial"] == 0

    assert not errors, errors
    print("PASS: direct taps and return; A/B SVG geometry; partial/full/restored; adjacent selection; keyboard; simulated touch tap at 390x844 and 320x568; touch drag without scroll; reduced motion; no page errors")
    print(f"Review frames: {OUT}")
    browser.close()
