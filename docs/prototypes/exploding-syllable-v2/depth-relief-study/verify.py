"""Focused Chromium checks and review frames for the isolated 나 relief comparison."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "captures"
OUT.mkdir(exist_ok=True)
URL = (ROOT / "index.html").as_uri()


def state(page):
    return page.evaluate("window.__reliefStudy.snapshot()")


def front_paths(page, mode):
    return page.locator(f'[data-scene="{mode}"] .front').evaluate_all(
        "nodes => nodes.map(node => node.getAttribute('d'))"
    )


def point_on(page, mode, part="initial"):
    group = page.locator(f'[data-scene="{mode}"] [data-component="{part}"]')
    group.scroll_into_view_if_needed()
    return group.locator(".hit").evaluate("""path => {
      const r = path.getBoundingClientRect();
      for(let iy=1;iy<29;iy++)for(let ix=1;ix<29;ix++){
        const x=r.left+r.width*ix/30,y=r.top+r.height*iy/30;
        if(document.elementFromPoint(x,y)===path)return {x,y};
      }
      throw new Error('No visible pointer target on '+path.parentElement.dataset.component);
    }""")


with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    errors = []
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    page.goto(URL, wait_until="domcontentloaded")
    assert front_paths(page, "flat") == front_paths(page, "relief")
    assert state(page)["progress"] == {"initial": 0, "medial": 0}
    page.screenshot(path=str(OUT / "na-00-assembled-390.png"), full_page=True)

    p = point_on(page, "flat")
    page.mouse.click(p["x"], p["y"])
    page.wait_for_timeout(550)
    assert state(page)["progress"]["initial"] > .99
    assert state(page)["progress"]["medial"] == 0
    assert front_paths(page, "flat") == front_paths(page, "relief")
    p = point_on(page, "relief")
    page.mouse.click(p["x"], p["y"])
    page.wait_for_timeout(550)
    assert state(page)["progress"]["initial"] < .01

    for pct in (25, 50, 75, 100):
        page.locator("#progress").fill(str(pct))
        assert front_paths(page, "flat") == front_paths(page, "relief")
        assert abs(state(page)["progress"]["initial"] - pct / 100) < .01
        side = page.locator('[data-scene="relief"] [data-part="initial"] .side').first
        assert float(side.evaluate("el => getComputedStyle(el).opacity")) > 0
        page.screenshot(path=str(OUT / f"na-{pct:02d}-390.png"), full_page=True)
    shadow = page.locator('[data-scene="relief"] [data-shadow="initial"]')
    assert float(shadow.evaluate("el => getComputedStyle(el).opacity")) > 0
    assert page.locator('[data-scene="flat"] [data-part="initial"] .side').count() == 0
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")

    page.locator("#reassemble").click()
    page.wait_for_timeout(550)
    assert state(page)["progress"]["initial"] < .01
    assert front_paths(page, "flat") == front_paths(page, "relief")
    page.screenshot(path=str(OUT / "na-restored-390.png"), full_page=True)

    # An actual animated midpoint, in addition to the fixed scrubbed review frames.
    page.locator('[data-lift="medial"]').click()
    page.wait_for_timeout(160)
    assert 0 < state(page)["progress"]["medial"] < 1
    animated_paths = page.evaluate("""() => ['flat','relief'].map(mode =>
      [...document.querySelectorAll(`[data-scene="${mode}"] .front`)].map(node => node.getAttribute('d')))""")
    assert animated_paths[0] == animated_paths[1]
    page.screenshot(path=str(OUT / "na-medial-animated-mid-390.png"), full_page=True)
    page.wait_for_timeout(400)
    assert state(page)["progress"]["medial"] > .99
    assert state(page)["progress"]["initial"] < .01
    page.screenshot(path=str(OUT / "na-medial-100-390.png"), full_page=True)

    page.locator('[data-scene="relief"] [data-component="medial"]').focus()
    page.keyboard.press("Enter")
    page.wait_for_timeout(550)
    assert state(page)["progress"]["medial"] < .01

    page.set_viewport_size({"width": 320, "height": 568})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    page.locator('[data-lift="initial"]').click()
    page.wait_for_timeout(550)
    page.locator("#progress").fill("50")
    page.screenshot(path=str(OUT / "na-50-320.png"), full_page=True)
    page.locator("#progress").fill("100")
    page.screenshot(path=str(OUT / "na-100-320.png"), full_page=True)
    page.locator('[data-lift="medial"]').click()
    page.wait_for_timeout(550)
    assert state(page)["progress"]["medial"] > .99
    page.screenshot(path=str(OUT / "na-medial-100-320.png"), full_page=True)

    for width, height in ((390, 844), (320, 568)):
        touch = browser.new_page(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True)
        touch.on("pageerror", lambda error: errors.append(str(error)))
        touch.goto(URL, wait_until="domcontentloaded")
        p = point_on(touch, "relief")
        touch.touchscreen.tap(p["x"], p["y"])
        touch.wait_for_timeout(550)
        assert state(touch)["progress"]["initial"] > .99
        p = point_on(touch, "relief")
        touch.touchscreen.tap(p["x"], p["y"])
        touch.wait_for_timeout(550)
        assert state(touch)["progress"]["initial"] < .01
        assert touch.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        touch.close()

    reduced = browser.new_page(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
    reduced.goto(URL, wait_until="domcontentloaded")
    reduced.locator('[data-lift="initial"]').click()
    assert state(reduced)["progress"]["initial"] == 1
    reduced.locator("#reassemble").click()
    assert state(reduced)["progress"]["initial"] == 0
    assert not errors, errors
    print("PASS: synchronized geometry at 0/25/50/75/100%; tap and return in both panels; animated midpoint; side and ground cues; keyboard; simulated touch at 390x844 and 320x568; reduced motion; no page errors")
    print(f"Captures: {OUT}")
    browser.close()
