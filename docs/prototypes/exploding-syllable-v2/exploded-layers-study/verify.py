"""Chromium visual and interaction checks for the isolated exploded-layer study."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "captures"
OUT.mkdir(exist_ok=True)


def snap(page, name, full=False):
    if full:
        page.screenshot(path=str(OUT / name), full_page=True)
    else:
        page.locator(".study").screenshot(path=str(OUT / name))


with sync_playwright() as pw:
    browser = pw.chromium.launch()
    errors = []
    page = browser.new_page(viewport={"width": 1000, "height": 700}, device_scale_factor=1)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto((ROOT / "reference.html").as_uri())
    page.locator(".layers i").first.wait_for()
    assert page.locator(".layers i").count() == 4
    assert page.locator(".layers").evaluate("e => getComputedStyle(e).transformStyle") == "preserve-3d"
    assert "rotateX(58deg) rotateZ(-45deg)" in (ROOT / "reference.html").read_text(encoding="utf-8")
    page.evaluate("document.getAnimations().forEach(a => {a.pause(); a.currentTime = 0})")
    page.screenshot(path=str(OUT / "reference-expanded.png"))
    zs = page.locator(".layers i").evaluate_all("es => es.map(e => new DOMMatrixReadOnly(getComputedStyle(e).transform).m43)")
    assert len(set(zs)) == 4 and abs(zs[0] + zs[3]) < .01 and abs(zs[1] + zs[2]) < .01, zs
    page.evaluate("document.getAnimations().forEach(a => {a.currentTime = 2600})")
    page.screenshot(path=str(OUT / "reference-closed.png"))
    zs_closed = page.locator(".layers i").evaluate_all("es => es.map(e => getComputedStyle(e).transform)")
    assert len(set(zs_closed)) == 1, zs_closed

    for width, height in [(390, 844), (320, 568)]:
        context = browser.new_context(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True)
        mobile = context.new_page()
        mobile.on("pageerror", lambda e: errors.append(str(e)))
        mobile.goto((ROOT / "index.html").as_uri())
        assert mobile.locator(".plate").count() == 2
        assert mobile.locator("#front-view path").count() == 2
        assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
        snap(mobile, f"na-front-{width}.png", full=True)
        mobile.locator("#toggle").tap()
        mobile.wait_for_timeout(240)
        p = mobile.evaluate("window.__layersStudy.snapshot().progress")
        assert 0 < p < 1, p
        snap(mobile, f"na-angled-intermediate-{width}.png")
        mobile.wait_for_timeout(650)
        assert mobile.evaluate("window.__layersStudy.snapshot().progress") == 1
        assert mobile.locator("#rotate-right").is_enabled()
        assert mobile.evaluate("""() => {
          const area = document.querySelector('.scene-wrap').getBoundingClientRect();
          return [...document.querySelectorAll('.plate')].every(p => {
            const r=p.getBoundingClientRect();
            return r.left >= area.left-2 && r.right <= area.right+2 && r.top >= area.top-2 && r.bottom <= area.bottom+2;
          });
        }"""), f"plate projection overflow at {width}"
        snap(mobile, f"na-expanded-{width}.png", full=True)
        mobile.locator("#rotate-right").tap()
        assert mobile.evaluate("window.__layersStudy.snapshot().angle") == 15
        mobile.locator("#reset-angle").tap()
        mobile.locator("#scene").tap(position={"x": 150, "y": 150})
        mobile.wait_for_timeout(820)
        assert mobile.evaluate("window.__layersStudy.snapshot().progress") == 0
        snap(mobile, f"na-restored-{width}.png")
        mobile.locator('[data-syllable="난"]').tap()
        assert mobile.locator(".plate").count() == 3
        assert mobile.locator("#front-view path").count() == 3
        mobile.locator("#progress").fill("50")
        snap(mobile, f"nan-midpoint-{width}.png")
        mobile.locator("#progress").fill("100")
        zs = mobile.locator(".plate").evaluate_all("es => es.map(e => new DOMMatrixReadOnly(getComputedStyle(e).transform).m43)")
        assert len(zs) == 3 and abs(zs[0] + zs[2]) < .01 and abs(zs[1]) < .01, zs
        snap(mobile, f"nan-expanded-{width}.png")
        assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
        mobile.locator('[data-mode="flat"]').tap()
        assert mobile.locator(".component").count() == 3
        snap(mobile, f"nan-flat-{width}.png")
        mobile.locator('[data-mode="relief"]').tap()
        assert mobile.locator(".component .side").count() == 24
        snap(mobile, f"nan-relief-{width}.png")
        context.close()

    keyboard = browser.new_page(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
    keyboard.goto((ROOT / "index.html").as_uri())
    keyboard.locator("#scene").focus()
    keyboard.keyboard.press("Enter")
    assert keyboard.evaluate("window.__layersStudy.snapshot().progress") == 1
    keyboard.keyboard.press("Space")
    assert keyboard.evaluate("window.__layersStudy.snapshot().progress") == 0
    keyboard.close()
    assert not errors, errors
    browser.close()
    print("PASS: reference open/closed, study na/nan modes, midpoint, touch, keyboard, reduced motion, and both phone viewports")
