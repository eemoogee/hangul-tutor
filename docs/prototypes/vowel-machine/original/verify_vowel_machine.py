"""Focused browser checks for the separate Vowel Machine prototype."""
from pathlib import Path
import zipfile

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
URL = (ROOT / "index.html").as_uri()  # exercise the complete offline package


def state(page):
    return page.evaluate("""() => {const s=window.__vowelMachine.state, m=s[s.mode];
      return {mode:s.mode,methodOrder:s.methodOrder,phase:m.phase,found:[...m.found],
        prove:m.prove&&{index:m.prove.index,position:m.prove.position,
          sequence:m.prove.sequence,attempts:m.prove.attempts,assisted:m.prove.assisted,
          checked:m.prove.checked,records:m.prove.records},
        transfer:m.transfer&&{index:m.transfer.index,order:m.transfer.order,
          attempts:m.transfer.attempts,records:m.transfer.records},
        report:window.__vowelMachine.methodReport(s.mode),
        focused:document.activeElement?.dataset.focus};}""")


def hidden_target(page, target):
    assert page.locator("#glyph").inner_text() == "?"
    assert page.locator(".grid").count() == 0
    assert target not in page.locator(".shell").inner_text()
    assert target not in page.locator("#canvas").get_attribute("aria-label")
    assert target not in page.locator("#message").inner_text()


def complete_stroke_challenges(page):
    page.locator('[data-action="primary"]').click()
    assert state(page)["phase"] == "prove"
    assert state(page)["methodOrder"] == ["stroke"]
    assert state(page)["prove"]["position"] == {"axis":"vertical","side":1}
    hidden_target(page,"ㅓ")
    page.locator('[data-action="primary"]').click()
    page.locator('[data-action="primary"]').click()
    assert state(page)["prove"]["attempts"] == 2
    assert state(page)["prove"]["index"] == 0
    assert "long line is right" in page.locator("#message").inner_text().lower()
    page.locator('[data-action="secondary"]').click()
    assert state(page)["prove"]["assisted"]
    page.locator('[data-side="-1"]').click()
    assert not state(page)["prove"]["checked"]
    hidden_target(page,"ㅓ")
    page.locator('[data-action="primary"]').click()
    first=state(page)["prove"]["records"][0]
    assert first == {"target":"ㅓ","attempts":3,"firstIndependent":False,
                     "assisted":True,"errors":["ㅏ","ㅏ"]}, first
    page.locator('[data-action="primary"]').click()
    for actions,target in ((("turn",),"ㅜ"),(("turn","1"),"ㅏ"),(("turn",),"ㅗ")):
        hidden_target(page,target)
        for action in actions:
            page.locator('[data-action="turn"]' if action == "turn"
                         else f'[data-side="{action}"]').click()
        page.locator('[data-action="primary"]').click()
        assert state(page)["prove"]["checked"]
        page.locator('[data-action="primary"]').click()
    assert state(page)["phase"] == "transfer"
    assert state(page)["transfer"]["order"] == ["ㅓ","ㅜ","ㅏ","ㅗ"]
    assert page.locator("#canvas,.guide,#looseDot,.stem,.joint,.handle-ring").count() == 0
    assert page.locator(".machine-neutral .transfer-imprint").count() == 1
    assert page.locator(".machine-controls button").count() == 0
    page.locator('[data-choice="a"]').click()
    page.locator('[data-action="primary"]').click()
    assert state(page)["transfer"]["attempts"] == 1
    page.locator('[data-choice="eo"]').click()
    page.locator('[data-action="primary"]').click()
    page.locator('[data-action="primary"]').click()
    page.locator('[data-choice="u"]').click()
    page.locator('[data-action="primary"]').click()
    page.locator('[data-action="primary"]').click()
    for sound in ("a","o"):
        page.locator(f'[data-choice="{sound}"]').click()
        page.locator('[data-action="primary"]').click()
        page.locator('[data-action="primary"]').click()
    assert state(page)["phase"] == "complete"
    assert len(state(page)["transfer"]["records"]) == 4
    assert [r["target"] for r in state(page)["transfer"]["records"]] == state(page)["transfer"]["order"]
    assert "not establish independent reading" in page.locator(".summary-note").inner_text()


def complete_key_challenges(page):
    page.locator('[data-mode="keys"]').click()
    assert len(state(page)["found"]) == 4
    page.locator('[data-action="primary"]').click()
    assert state(page)["phase"] == "prove"
    assert state(page)["methodOrder"] == ["stroke","keys"]
    assert state(page)["prove"]["sequence"] == []
    hidden_target(page,"ㅓ")
    page.locator('[data-key="ㆍ"]').click()
    page.locator('[data-action="primary"]').click()
    assert state(page)["prove"]["attempts"] == 0
    page.locator('[data-key="ㅡ"]').click()
    page.locator('[data-action="primary"]').click()
    assert state(page)["prove"]["attempts"] == 1
    page.locator('[data-mode="stroke"]').click()
    assert state(page)["phase"] == "complete"


def test_rail_shortcuts(browser):
    targets = ("ㅓ", "ㅜ", "ㅏ", "ㅗ")
    positions = {"ㅏ":("vertical",1), "ㅓ":("vertical",-1),
                 "ㅗ":("horizontal",-1), "ㅜ":("horizontal",1)}
    for tactic, expected_first in (("opposite",1),("turn",2)):
        context = browser.new_context(viewport={"width":390,"height":844})
        page = context.new_page()
        page.goto(URL, wait_until="domcontentloaded")
        for selector in ('[data-side="-1"]','[data-action="turn"]','[data-side="1"]'):
            page.locator(selector).click()
        page.locator('[data-action="primary"]').click()
        starts = []
        for target in targets:
            before = state(page)["prove"]["position"]
            starts.append(before)
            assert (before["axis"],before["side"]) != positions[target]
            hidden_target(page,target)
            if tactic == "opposite":
                page.locator(f'[data-side="{-before["side"]}"]').click()
            else:
                page.locator('[data-action="turn"]').click()
            page.locator('[data-action="primary"]').click()
            if not state(page)["prove"]["checked"]:
                current = state(page)["prove"]["position"]
                axis, side = positions[target]
                if current["axis"] != axis:
                    page.locator('[data-action="turn"]').click()
                if state(page)["prove"]["position"]["side"] != side:
                    page.locator(f'[data-side="{side}"]').click()
                page.locator('[data-action="primary"]').click()
                assert state(page)["prove"]["checked"]
            page.locator('[data-action="primary"]').click()
        assert state(page)["phase"] == "transfer"
        assert state(page)["report"]["firstIndependent"] == expected_first
        changes = {(p["axis"] != positions[t][0],p["side"] != positions[t][1])
                   for p,t in zip(starts,targets)}
        assert changes == {(False,True),(True,False),(True,True)}, changes
        print(f"PASS rail adversary {tactic}: {expected_first}/4 first independent")
        context.close()


def test_keys_first(browser):
    context = browser.new_context(viewport={"width":390,"height":844})
    page = context.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.locator('[data-mode="keys"]').click()
    for pair in (("ㅣ","ㆍ"),("ㆍ","ㅣ"),("ㆍ","ㅡ"),("ㅡ","ㆍ")):
        for key in pair:
            page.locator(f'[data-key="{key}"]').click()
    page.locator('[data-action="primary"]').click()
    assert state(page)["methodOrder"] == ["keys"]
    assert state(page)["report"]["methodOrdinal"] == 1
    page.locator('[data-mode="stroke"]').click()
    for selector in ('[data-side="-1"]','[data-action="turn"]','[data-side="1"]'):
        page.locator(selector).click()
    page.locator('[data-action="primary"]').click()
    assert state(page)["methodOrder"] == ["keys","stroke"]
    assert state(page)["report"]["methodOrdinal"] == 2
    context.close()
    page.locator('[data-mode="keys"]').click()
    assert state(page)["prove"]["attempts"] == 1
    page.locator('[data-action="clear"]').click()
    for key in ("ㆍ","ㅣ"):
        page.locator(f'[data-key="{key}"]').click()
    page.locator('[data-action="primary"]').click()
    first=state(page)["prove"]["records"][0]
    assert first["attempts"] == 2 and not first["assisted"] and not first["firstIndependent"]
    page.locator('[data-action="primary"]').click()
    for pair,target in ((("ㅡ","ㆍ"),"ㅜ"),(("ㅣ","ㆍ"),"ㅏ"),(("ㆍ","ㅡ"),"ㅗ")):
        hidden_target(page,target)
        for key in pair:
            page.locator(f'[data-key="{key}"]').click()
        page.locator('[data-action="primary"]').click()
        page.locator('[data-action="primary"]').click()
    assert state(page)["phase"] == "transfer"
    assert state(page)["transfer"]["order"] == ["ㅗ","ㅏ","ㅜ","ㅓ"]
    assert page.locator("#canvas,.guide,#looseDot,.stem,.joint,.handle-ring").count() == 0
    for sound in ("o","a","u","eo"):
        page.locator(f'[data-choice="{sound}"]').click()
        page.locator('[data-action="primary"]').click()
        page.locator('[data-action="primary"]').click()
    assert state(page)["phase"] == "complete"
    assert len(state(page)["prove"]["records"]) == 4
    assert len(state(page)["transfer"]["records"]) == 4
    assert state(page)["report"]["methodOrdinal"] == 2
    assert state(page)["report"]["transferOrder"] == ["ㅗ","ㅏ","ㅜ","ㅓ"]
    page.locator('[data-action="primary"]').click()
    assert state(page)["phase"] == "explore" and len(state(page)["found"]) == 4
    page.locator('[data-action="primary"]').click()
    assert state(page)["prove"]["records"] == []
    page.locator('[data-action="secondary"]').click()
    page.locator('[data-mode="stroke"]').click()
    assert state(page)["phase"] == "complete"


def layout(page, width, height, no_scroll=False):
    result = page.evaluate("""() => {
      const shell=document.querySelector('.shell').getBoundingClientRect();
      const foot=document.querySelector('.foot').getBoundingClientRect();
      const content=document.querySelector('.content');
      return {page:document.documentElement.scrollHeight, viewport:innerHeight,
        shell:shell.bottom, foot:foot.bottom, content:content.scrollHeight,
        available:content.clientHeight, horizontal:document.documentElement.scrollWidth-innerWidth};
    }""")
    assert result["page"] <= height + 1, result
    assert result["shell"] <= height + 1, result
    assert result["foot"] <= height + 1, result
    assert result["horizontal"] <= 1, result
    if no_scroll:
        assert result["content"] <= result["available"] + 1, result
    return result


with sync_playwright() as p:
    browser = p.chromium.launch()
    for width, height in ((390, 844), (320, 568)):
        context = browser.new_context(viewport={"width": width, "height": height},
                                      device_scale_factor=1, is_mobile=True, has_touch=True)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(URL, wait_until="domcontentloaded")
        assert page.locator("#glyph").inner_text() == "ㅏ"
        assert page.locator(".cell.open").count() == 1
        layout(page, width, height, no_scroll=width == 390)
        if width == 390:
            page.screenshot(path=str(ROOT / "stroke-start-390x844.png"))
        page.locator('[data-side="-1"]').click()
        assert page.locator("#glyph").inner_text() == "ㅓ"
        assert page.locator('.cell.open[data-cell="ㅓ"]').count() == 1
        page.locator('[data-action="turn"]').click()
        assert page.locator("#glyph").inner_text() == "ㅗ"
        page.locator('[data-side="1"]').click()
        assert page.locator("#glyph").inner_text() == "ㅜ"
        assert page.locator(".cell.open").count() == 4
        page.locator('.cell[data-cell="ㅗ"]').click()
        assert "ㄴ + ㅗ" in page.locator("#composition").inner_text()
        if width == 390:
            page.screenshot(path=str(ROOT / "stroke-row-390x844.png"))
        layout(page, width, height, no_scroll=width == 390)
        page.locator('[data-mode="keys"]').click()
        assert page.locator(".cell.open").count() == 0
        for first, second, expected in (("ㅣ", "ㆍ", "ㅏ"), ("ㆍ", "ㅣ", "ㅓ"),
                                        ("ㆍ", "ㅡ", "ㅗ"), ("ㅡ", "ㆍ", "ㅜ")):
            page.locator(f'[data-key="{first}"]').click()
            page.locator(f'[data-key="{second}"]').click()
            assert page.locator("#glyph").inner_text() == expected
            assert page.locator(f'.cell.open[data-cell="{expected}"]').count() == 1
        assert page.locator(".cell.open").count() == 4
        if width == 390:
            page.wait_for_timeout(600)
            page.screenshot(path=str(ROOT / "three-key-row-390x844.png"))
        layout(page, width, height, no_scroll=width == 390)
        page.locator('[data-key="ㅣ"]').click()
        page.locator('[data-key="ㅡ"]').click()
        assert "do not make" in page.locator("#message").inner_text()
        page.locator('[data-action="clear"]').click()
        assert page.locator("#glyph").inner_text() == "·"
        page.locator('[data-mode="stroke"]').click()
        assert page.locator(".cell.open").count() == 4
        page.locator('[data-action="about"]').click()
        assert page.locator('[role="dialog"]').is_visible()
        assert "imagined" in page.locator('[role="dialog"]').inner_text().lower() or "dialogue" in page.locator('[role="dialog"]').inner_text().lower()
        page.locator('[data-action="about"]').last.click()
        assert page.evaluate("[...document.images].every(i => i.complete && i.naturalWidth > 0)")
        complete_stroke_challenges(page)
        layout(page, width, height, no_scroll=width == 390)
        complete_key_challenges(page)
        layout(page, width, height, no_scroll=width == 390)
        assert not errors, errors
        print(f"PASS {width}x{height}: Explore, Prove, transfer, retry, assistance, mode memory, replay, assets, layout={layout(page,width,height,no_scroll=width==390)}")
        context.close()
    context = browser.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
    page = context.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
    handle = page.locator("#dragHit").bounding_box()
    start_x = handle["x"] + handle["width"] / 2
    start_y = handle["y"] + handle["height"] / 2
    canvas = page.locator("#canvas").bounding_box()
    page.mouse.move(start_x, start_y)
    page.mouse.down()
    page.mouse.move(canvas["x"] + canvas["width"] * .26, start_y, steps=8)
    page.mouse.up()
    assert page.locator("#glyph").inner_text() == "ㅓ"
    assert page.evaluate("getComputedStyle(document.querySelector('.cell')).animationDuration") == "0s"
    page.locator('[data-side="1"]').focus()
    page.keyboard.press("Enter")
    assert page.locator("#glyph").inner_text() == "ㅏ"
    assert state(page)["focused"] == "side-1"
    page.locator('[data-action="about"]').click()
    page.keyboard.press("Escape")
    assert page.locator('[role="dialog"]').count() == 0
    assert state(page)["focused"] == "about"
    print("PASS drag, keyboard focus, and reduced-motion preference")
    context.close()
    test_rail_shortcuts(browser)
    test_keys_first(browser)
    browser.close()

package = ROOT / "vowel-machine-v0.3.1.zip"
assert package.exists(), package
with zipfile.ZipFile(package) as archive:
    for relative in ("index.html", "app.js", "DESIGN_NOTES.md", "BEGINNER_TEST.md",
                     "reference-vowel-forge.html", "index-v0.2.html", "README.md",
                     "assets/jeong_hello.png", "assets/jeong_curious.png",
                     "assets/jeong_delighted.png"):
        assert archive.read(relative) == (ROOT / relative).read_bytes(), relative
print("PASS portable offline package")
