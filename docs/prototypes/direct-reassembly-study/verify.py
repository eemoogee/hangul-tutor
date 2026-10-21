"""Chromium checks and review frames for the isolated direct-reassembly study.

Requires Python Playwright and installed Chromium. Run this file from anywhere.
Captures are intentional review artifacts in this prototype's captures/ folder.
"""

from pathlib import Path
from playwright.sync_api import sync_playwright


HERE = Path(__file__).resolve().parent
CAPTURES = HERE / "captures"
CAPTURES.mkdir(exist_ok=True)
URL = (HERE / "index.html").as_uri()


def shot(page, name, full=False):
    page.screenshot(path=str(CAPTURES / name), full_page=True)
    page.locator("#stage").screenshot(path=str(CAPTURES / name.replace(".png", "-stage.png")))


def snapshot(page):
    return page.evaluate("window.__directReassembly.snapshot()")


def wait_phase(page, phase):
    page.wait_for_function("p => window.__directReassembly.snapshot().phase === p", arg=phase)


def stage_bounds(page):
    return page.locator("#stage").bounding_box()


def assert_no_overflow(page):
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "horizontal overflow"
    stage = stage_bounds(page)
    for selector in ('.piece[data-part="initial"] .front', '.piece[data-part="medial"] .front', '.piece[data-part="final"] .front'):
        b = page.locator(selector).bounding_box()
        assert b and b["x"] >= stage["x"] - 3 and b["y"] >= stage["y"] - 3, selector
        assert b["x"] + b["width"] <= stage["x"] + stage["width"] + 3, selector
        assert b["y"] + b["height"] <= stage["y"] + stage["height"] + 3, selector


def hit_size(page):
    for selector in ('.piece[data-part="final"] .hit-box', '.slot-hit'):
        b = page.locator(selector).bounding_box()
        assert b["width"] >= 44 and b["height"] >= 44, (selector, b)


def drag(page, movements, release=True):
    box = page.locator('.piece[data-part="final"] .hit-box').bounding_box()
    x = box["x"] + box["width"] / 2
    y = box["y"] + box["height"] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    for dx, dy, frame in movements:
        page.mouse.move(x + dx, y + dy, steps=5)
        if frame:
            shot(page, frame)
    if release:
        page.mouse.up()


def run_case(browser, width, height, mode):
    context = browser.new_context(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True, device_scale_factor=1)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.goto(URL)
    page.evaluate("document.fonts.ready")
    assert page.evaluate('document.fonts.check(\'400 176px "Noto KR Study"\', "난")'), "bundled Korean font not loaded"
    assert page.locator("#font-status").inner_text() == ""
    page.locator(f'[data-mode="{mode}"]').click()
    prefix = f"{mode}-{width}"
    assert snapshot(page)["phase"] == "closed"
    assert_no_overflow(page)
    shot(page, f"{prefix}-00-assembled.png", full=True)

    page.locator("#open").click()
    wait_phase(page, "open")
    hit_size(page)
    assert_no_overflow(page)
    shot(page, f"{prefix}-01-open.png")
    upper_before = page.locator('.piece[data-part="initial"]').evaluate("e => e.style.transform"), page.locator('.piece[data-part="medial"]').evaluate("e => e.style.transform")
    front_open = [page.locator(f'.piece[data-part="{part}"] .front').get_attribute("d") for part in ("initial", "medial", "final")]

    # Direct tap on the moving final-piece hit area, not only its labelled button.
    page.locator('.piece[data-part="final"] .hit-box').click()
    wait_phase(page, "lifted")
    upper_after = page.locator('.piece[data-part="initial"]').evaluate("e => e.style.transform"), page.locator('.piece[data-part="medial"]').evaluate("e => e.style.transform")
    assert upper_before == upper_after, "upper pieces shifted during lift"
    assert page.locator('.piece[data-part="final"] .front').get_attribute("d") != front_open[2], "final ㄴ did not expand during lift"
    assert [page.locator(f'.piece[data-part="{part}"] .front').get_attribute("d") for part in ("initial", "medial")] == front_open[:2]
    assert_no_overflow(page)
    hit_size(page)
    z = page.locator('.piece[data-part="final"]').evaluate("e => e.style.transform")
    if mode == "flat":
        assert z.endswith("0px)"), z
    else:
        assert z.endswith("32px)"), z
    shot(page, f"{prefix}-02-lifted.png")

    s = stage_bounds(page)["width"] / 360
    drag(page, [(25*s, 10*s, f"{prefix}-03-moved-away.png")])
    wait_phase(page, "lifted")
    assert "outside its lower slot" in page.locator("#status").inner_text()
    assert snapshot(page)["place"] == 0, "invalid release placed the piece"

    # Approach the lower slot in stages. The upper components should start
    # adjusting before the valid release; the return still needs that release.
    drag(page, [(-3*s, -14*s, f"{prefix}-04-approach-25.png"),
                (-6*s, -28*s, f"{prefix}-05-approach-50.png"),
                (-9*s, -42*s, f"{prefix}-06-approach-75.png"),
                (-12*s, -55*s, f"{prefix}-07-at-slot.png")], release=False)
    assert snapshot(page)["phase"] == "dragging"
    assert snapshot(page)["place"] == 0, "assembly completed before placement"
    assert page.locator('.piece[data-part="initial"] .front').get_attribute("d") != front_open[0], "upper geometry did not accommodate returning ㄴ"
    assert page.locator("#slot-outline").get_attribute("class").endswith("near")
    page.mouse.up()
    page.wait_for_function("window.__directReassembly.snapshot().phase === 'returning' && window.__directReassembly.snapshot().place >= .5")
    shot(page, f"{prefix}-08-seating.png")
    wait_phase(page, "complete")
    page.wait_for_timeout(150)  # Let the documented text handoff finish.
    assert page.locator("#type-glyph").get_attribute("class").endswith("visible")
    assert_no_overflow(page)
    shot(page, f"{prefix}-09-complete.png", full=True)

    page.locator("#undo").click()
    assert snapshot(page)["phase"] == "lifted"
    page.locator(".slot-hit").click()
    wait_phase(page, "complete")
    page.locator("#undo").click()
    assert snapshot(page)["phase"] == "lifted"
    page.locator('.piece[data-part="final"] .hit-box').click()
    wait_phase(page, "complete")
    page.locator("#reset").click()
    assert snapshot(page)["phase"] == "closed"

    # Keyboard route: open, lift, use the labelled slot control, and reset.
    page.locator("#stage").focus()
    page.keyboard.press("Enter")
    wait_phase(page, "open")
    page.locator("#final-control").focus()
    page.keyboard.press("Enter")
    wait_phase(page, "lifted")
    page.locator("#slot-control").focus()
    page.keyboard.press("Space")
    wait_phase(page, "complete")
    page.locator("#reset").click()

    # Reduced-motion simulation suppresses translation animation and depth.
    page.locator("#reduce").check()
    page.locator("#open").click()
    assert snapshot(page)["phase"] == "open"
    page.locator("#final-control").click()
    assert snapshot(page)["phase"] == "lifted"
    assert page.locator('.piece[data-part="final"]').evaluate("e => e.style.transform").endswith("0px)")
    page.locator("#final-control").click()
    assert snapshot(page)["phase"] == "complete"
    assert_no_overflow(page)
    assert not errors, errors
    context.close()
    return front_open


with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for width, height in ((390, 844), (320, 568)):
        flat = run_case(browser, width, height, "flat")
        relief = run_case(browser, width, height, "relief")
        assert flat == relief, "front-face geometry differs by treatment"
    context = browser.new_context(viewport={"width": 320, "height": 568}, reduced_motion="reduce")
    page = context.new_page()
    page.goto(URL)
    page.locator('[data-mode="relief"]').click()
    page.locator("#open").click()
    assert snapshot(page)["phase"] == "open"
    page.locator("#final-control").click()
    assert snapshot(page)["phase"] == "lifted"
    assert page.locator('.piece[data-part="final"]').evaluate("e => e.style.transform").endswith("0px)")
    page.locator("#final-control").click()
    assert snapshot(page)["phase"] == "complete"
    context.close()
    browser.close()

print("PASS: font, matched front geometry, tap, drag, invalid/valid placement, anchored lift, undo/reset, keyboard, reduced motion, 390/320 layouts, no page errors")
