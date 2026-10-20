"""Focused browser checks and review frames for the isolated v2 study."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[2] / ".verify_out" / "exploding-syllable-v2"
OUT.mkdir(parents=True, exist_ok=True)
URL = (ROOT / "index.html").as_uri()


def state(page):
    return page.evaluate("window.__syllableV2.snapshot()")


def d(page, part):
    return page.locator(f'#parts [data-part="{part}"] .stroke').get_attribute("d")


with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    errors = []
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    page.goto(URL, wait_until="domcontentloaded")
    assert state(page)["syllable"] == "나"
    assert page.locator("#parts [data-part]").count() == 2
    page.screenshot(path=str(OUT / "01-na-separation-rest.png"), full_page=True)

    first = d(page, "initial")
    page.locator("#progress").fill("50")
    assert abs(state(page)["progress"]["initial"] - .5) < .01
    assert d(page, "initial") != first
    page.screenshot(path=str(OUT / "02-na-separation-mid.png"), full_page=True)
    page.locator("#progress").fill("100")
    page.screenshot(path=str(OUT / "03-na-separation-open.png"), full_page=True)
    page.locator("#return-action").click()
    page.wait_for_timeout(550)
    assert all(value < .01 for value in state(page)["progress"].values())

    page.locator('[data-method="deformation"]').click()
    initial_node = page.locator('#parts [data-part="initial"]')
    initial_handle = initial_node.evaluate("node => {node.dataset.identity='kept'; return node.dataset.identity}")
    assert initial_handle == "kept"
    medial_rest = d(page, "medial")
    page.locator('[data-choose="initial"]').click()
    page.locator("#progress").fill("50")
    assert initial_node.get_attribute("data-identity") == "kept"
    assert d(page, "medial") == medial_rest
    page.screenshot(path=str(OUT / "04-na-deformation-mid.png"), full_page=True)
    page.locator("#progress").fill("100")
    page.screenshot(path=str(OUT / "05-na-deformation-open.png"), full_page=True)
    page.locator("#progress").fill("0")
    assert d(page, "medial") == medial_rest

    page.locator('[data-syllable="노"]').click()
    assert state(page)["syllable"] == "노"
    page.locator("#progress").fill("50")
    page.screenshot(path=str(OUT / "06-no-deformation-mid.png"), full_page=True)
    page.locator('[data-syllable="난"]').click()
    assert page.locator("#parts [data-part]").count() == 3
    page.locator("#progress").fill("100")
    page.screenshot(path=str(OUT / "07-nan-expanded.png"), full_page=True)

    page.locator('[data-method="reflow"]').click()
    assert state(page)["flow"] == 1
    page.locator("#return-action").click()
    page.wait_for_timeout(550)
    assert state(page)["flow"] < .01
    assert page.locator('#parts [data-part="final"]').count() == 1
    page.locator('#parts [data-part="initial"]').evaluate("el => el.dataset.identity='reflow-kept'")
    first_initial = d(page, "initial")
    first_medial = d(page, "medial")
    page.screenshot(path=str(OUT / "08-reflow-na.png"), full_page=True)
    page.locator("#progress").fill("50")
    assert d(page, "initial") != first_initial and d(page, "medial") != first_medial
    assert page.locator('#parts [data-part="final"]').evaluate("el => Number(getComputedStyle(el).opacity)") > .1
    page.screenshot(path=str(OUT / "09-reflow-mid.png"), full_page=True)
    page.locator("#progress").fill("100")
    assert state(page)["flow"] > .99
    assert page.locator('#parts [data-part="initial"]').get_attribute("data-identity") == "reflow-kept"
    page.screenshot(path=str(OUT / "10-reflow-nan.png"), full_page=True)
    final_box = page.locator('#parts [data-part="final"] .hit').bounding_box()
    fx, fy = final_box["x"] + final_box["width"] * .25, final_box["y"] + final_box["height"] * .5
    page.mouse.move(fx, fy)
    page.mouse.down()
    page.mouse.move(fx, fy + 90, steps=10)
    page.mouse.up()
    assert state(page)["flow"] < .8, state(page)
    page.locator("#progress").fill("0")
    assert d(page, "initial") == first_initial and d(page, "medial") == first_medial
    assert page.locator('#parts [data-part="final"]').count() == 1
    page.screenshot(path=str(OUT / "12-reflow-reassembled.png"), full_page=True)

    page.locator('[data-method="deformation"]').click()
    page.locator('[data-syllable="나"]').click()
    page.locator('#parts [data-part="initial"]').focus()
    page.keyboard.press("Enter")
    assert state(page)["selected"] == "initial"
    page.keyboard.press("Enter")
    page.wait_for_timeout(550)
    assert state(page)["progress"]["initial"] > .99
    assert state(page)["progress"]["medial"] < .01
    page.locator("#return-action").click()
    page.wait_for_timeout(550)
    path = page.locator('#parts [data-part="initial"] .hit')
    box = path.bounding_box()
    x, y = box["x"] + box["width"] * .25, box["y"] + box["height"] * .48
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x - 100, y + 12, steps=12)
    page.mouse.up()
    assert state(page)["progress"]["initial"] > .25
    assert state(page)["progress"]["medial"] < .01

    touch = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    touch.on("pageerror", lambda error: errors.append(str(error)))
    touch.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    touch.goto(URL, wait_until="domcontentloaded")
    touch.locator('[data-method="deformation"]').tap()
    hit_box = touch.locator('#parts [data-part="initial"] .hit').bounding_box()
    tx, ty = hit_box["x"] + hit_box["width"] * .25, hit_box["y"] + hit_box["height"] * .48
    cdp = touch.context.new_cdp_session(touch)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": tx, "y": ty}]})
    for step in range(1, 9):
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": tx - step * 14, "y": ty + step * 2}]})
        touch.wait_for_timeout(25)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    assert state(touch)["progress"]["initial"] > .25, state(touch)
    assert state(touch)["progress"]["medial"] < .01

    page.set_viewport_size({"width": 320, "height": 568})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    page.locator("#main-action").scroll_into_view_if_needed()
    page.screenshot(path=str(OUT / "11-short-screen.png"), full_page=True)

    reduced = browser.new_page(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
    reduced.on("pageerror", lambda error: errors.append(str(error)))
    reduced.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    reduced.goto(URL, wait_until="domcontentloaded")
    reduced.locator("#main-action").click()
    assert all(value > .99 for value in state(reduced)["progress"].values())
    assert not errors, errors
    print("PASS: 3 syllables; rigid separation; component deformation; reversible 나↔난 reflow; persistent SVG identity; keyboard; pointer and touch drag; 390×844 and 320×568; reduced motion; no page errors")
    print(f"Review frames: {OUT}")
    browser.close()
