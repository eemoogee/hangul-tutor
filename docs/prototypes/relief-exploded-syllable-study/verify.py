"""Browser checks and review captures for the relief-exploded syllable study."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "captures"
OUT.mkdir(exist_ok=True)
URL = (ROOT / "index.html").as_uri()
SYLLABLES = {"나": ["initial", "medial"], "노": ["initial", "medial"], "난": ["initial", "medial", "final"]}
DIRS = {"나": [(-1, 0), (1, 0)], "노": [(0, -1), (0, 1)], "난": [(-1, -1), (1, -1), (0, 1)]}


def snapshot(page):
    return page.evaluate("window.__reliefExploded.snapshot()")


def matrices(page):
    return page.locator(".piece").evaluate_all("es => es.map(e => {const m=new DOMMatrixReadOnly(getComputedStyle(e).transform);return [m.m41,m.m42,m.m43]})")


def paths(page):
    return page.locator(".front").evaluate_all("es => es.map(e => e.getAttribute('d'))")


with sync_playwright() as pw:
    browser = pw.chromium.launch()
    errors = []
    for width, height in [(390, 844), (320, 568)]:
        context = browser.new_context(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True)
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(URL)
        topology = page.evaluate("window.__reliefExploded.topology()")
        assert all(p["packed"] == p["free"] for parts in topology.values() for p in parts), topology
        assert page.evaluate("""() => ['#stage','#pieces','.piece'].every(s => {
          const c=getComputedStyle(document.querySelector(s));
          return c.overflowX==='visible' && c.filter==='none' && c.opacity==='1';
        })"""), "3D ancestor is flattened"
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
        assert page.evaluate("""() => {
          const s=document.querySelector('#stage').getBoundingClientRect();
          return [...document.querySelectorAll('.ground svg')].every(e => {
            const r=e.getBoundingClientRect();
            return Math.abs(r.top-s.top)<1 && Math.abs(r.bottom-s.bottom)<1;
          });
        }"""), "ground overlays escaped the stage"
        for syllable, ids in SYLLABLES.items():
            page.locator(f'[data-syllable="{syllable}"]').tap()
            assert page.locator(".piece").count() == len(ids)
            assert page.locator("#type-glyph").text_content() == syllable
            assert 'Noto Sans KR' in page.locator('#type-glyph').evaluate('e => getComputedStyle(e).fontFamily')
            page.wait_for_timeout(150)
            page.locator(".stage-card").screenshot(path=str(OUT / f"{syllable}-closed-{width}.png"))
            compare = {}
            for variant in ("v1", "v2", "v3"):
                page.locator(f'[data-variant="{variant}"]').tap()
                assert snapshot(page)["duration"] == 760
                page.locator("#progress").fill("10")
                assert page.locator("#phase-label").text_content() == "LOOSEN"
                page.locator("#progress").fill("50")
                assert page.locator("#phase-label").text_content() == "OPEN"
                compare[variant] = {"middle": matrices(page), "midpaths": paths(page)}
                if variant == "v1":
                    page.locator('.hit-box').first.tap()
                    assert snapshot(page)['inspect'] == ids[0]
                    page.locator('#clear-inspect').tap()
                page.wait_for_timeout(160)
                page.locator(".stage-card").screenshot(path=str(OUT / f"{syllable}-{variant}-middle-{width}.png"))
                if variant == 'v2' or (variant == 'v3' and syllable == '난'):
                    for morph_label,timeline in [('25','35'),('50','53'),('75','72')]:
                        page.locator('#progress').fill(timeline)
                        assert page.locator('#phase-label').text_content() == 'OPEN'
                        assert all('NaN' not in d for d in paths(page))
                        page.locator('.stage-card').screenshot(path=str(OUT / f'{syllable}-{variant}-morph{morph_label}-{width}.png'))
                page.locator("#progress").fill("85")
                if syllable == "난" and variant == "v3":
                    page.locator(".stage-card").screenshot(path=str(OUT / f"{syllable}-{variant}-late-{width}.png"))
                page.locator("#progress").fill("100")
                compare[variant]["open"] = matrices(page)
                compare[variant]["openpaths"] = paths(page)
                assert page.locator("#phase-label").text_content() == "HOLD"
                page.locator(".stage-card").screenshot(path=str(OUT / f"{syllable}-{variant}-open-{width}.png"))
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (syllable,variant,width)
                boxes=page.locator(".hit-box").evaluate_all("es => es.map(e => {const r=e.getBoundingClientRect();return [r.width,r.height]})")
                assert all(w>=44 and h>=44 for w,h in boxes), (width,syllable,variant,boxes)
                if variant == "v3":
                    page.locator('.hit-box').first.tap()
                    assert snapshot(page)["inspect"] == ids[0]
                    assert matrices(page)[0][2] > 0
                    assert all(abs(m[2])<.01 for m in matrices(page)[1:])
                    page.wait_for_timeout(170)
                    page.locator(".stage-card").screenshot(path=str(OUT / f"{syllable}-v3-inspect-{width}.png"))
                    page.locator('#clear-inspect').tap()
                    assert snapshot(page)["inspect"] is None
                else:
                    page.locator('.hit-box').first.tap()
                    assert snapshot(page)["inspect"] == ids[0]
                    assert all(abs(m[2])<.01 for m in matrices(page))
                    assert page.locator('.front.inspected').count() == 1
                    page.locator('#clear-inspect').tap()
            assert compare["v1"]["middle"] == compare["v2"]["middle"] == compare["v3"]["middle"]
            assert compare["v1"]["open"] == compare["v2"]["open"] == compare["v3"]["open"]
            assert compare["v2"]["midpaths"] == compare["v3"]["midpaths"]
            assert compare["v2"]["openpaths"] == compare["v3"]["openpaths"]
            assert compare["v1"]["openpaths"] != compare["v2"]["openpaths"]
            for matrix,(dx,dy) in zip(compare["v3"]["open"], DIRS[syllable]):
                assert (dx==0 or matrix[0]*dx>0) and (dy==0 or matrix[1]*dy>0), (syllable,matrix)
            page.locator('[data-variant="v3"]').tap()
            page.locator('#progress').fill('0')
            page.wait_for_timeout(150)
            assert page.locator('#type-glyph').evaluate('e => getComputedStyle(e).opacity') == '1'

        # Actual reversible motion, tap while a piece is moving, and tuned values.
        page.locator('[data-syllable="난"]').tap()
        page.locator('#distance').fill('72')
        page.locator('#progress').fill('100')
        assert page.evaluate("""() => {
          const s=document.querySelector('#stage').getBoundingClientRect();
          return [...document.querySelectorAll('.front')].every(e => {
            const r=e.getBoundingClientRect();
            return r.left>=s.left-2 && r.right<=s.right+2 && r.top>=s.top-2 && r.bottom<=s.bottom+2;
          });
        }"""), f"maximum-distance shape overflow at {width}"
        page.locator('#progress').fill('0')
        page.locator('#distance').fill('55')
        page.locator('#duration').fill('800')
        page.locator('#depth').fill('9')
        assert (snapshot(page)['distance'],snapshot(page)['duration'],snapshot(page)['depth']) == (55,800,9)
        page.locator('#toggle').tap()
        page.wait_for_timeout(350)
        assert 0 < snapshot(page)['progress'] < 1
        assert page.locator('#phase-label').text_content() in ['LOOSEN','OPEN']
        page.wait_for_timeout(700)
        assert snapshot(page)['progress'] == 1
        page.screenshot(path=str(OUT / f"full-page-open-{width}.png"), full_page=True)
        page.locator('#toggle').tap()
        page.wait_for_timeout(900)
        assert snapshot(page)['progress'] == 0
        assert 'visible' in page.locator('#type-glyph').get_attribute('class').split()
        page.locator('#reduce').check()
        page.locator('#toggle').tap()
        assert snapshot(page)['progress'] == 1
        assert all(abs(m[2])<.01 for m in matrices(page))
        assert all(p.evaluate('e => getComputedStyle(e).fillOpacity') == '0' for p in page.locator('.side').all())
        context.close()

    keyboard=browser.new_page(viewport={"width":390,"height":844}, reduced_motion="reduce")
    keyboard.goto(URL)
    keyboard.locator('#stage').focus()
    keyboard.keyboard.press('Enter')
    assert snapshot(keyboard)['progress'] == 1
    assert all(abs(m[2])<.01 for m in matrices(keyboard))
    keyboard.locator('.piece-group').first.focus()
    keyboard.keyboard.press('Space')
    assert snapshot(keyboard)['inspect'] == 'initial'
    assert all(abs(m[2])<.01 for m in matrices(keyboard))
    keyboard.locator('#stage').focus()
    keyboard.keyboard.press('Space')
    assert snapshot(keyboard)['progress'] == 0
    keyboard.locator('#reduce').check()
    keyboard.locator('#toggle').click()
    assert snapshot(keyboard)['progress'] == 1
    keyboard.close()
    assert not errors, errors
    browser.close()

for syllable, state, width in [(s, state, w) for s in SYLLABLES for state,w in [('middle',390),('open',320)]]:
    cards=[Image.open(OUT / f'{syllable}-{v}-{state}-{width}.png').convert('RGB') for v in ('v1','v2','v3')]
    gap=10;label_height=28
    sheet=Image.new('RGB',(sum(c.width for c in cards)+gap*4,max(c.height for c in cards)+label_height+gap*2),'#e4ece9')
    draw=ImageDraw.Draw(sheet)
    x=gap
    for label,card in zip(('V1 fixed','V2 morph','V3 relief'),cards):
        draw.text((x+4,6),label,fill='#19383b')
        sheet.paste(card,(x,label_height+gap))
        x+=card.width+gap
    sheet.save(OUT / f'compare-{syllable}-{state}-{width}.png')
    for card in cards:card.close()
for width in (390,320):
    cards=[Image.open(OUT / f'난-v3-morph{pct}-{width}.png').convert('RGB') for pct in ('25','50','75')]
    gap=10;label_height=28
    sheet=Image.new('RGB',(sum(c.width for c in cards)+gap*4,max(c.height for c in cards)+label_height+gap*2),'#e4ece9')
    draw=ImageDraw.Draw(sheet);x=gap
    for label,card in zip(('25% morph','50% morph','75% morph'),cards):
        draw.text((x+4,6),label,fill='#19383b')
        sheet.paste(card,(x,label_height+gap));x+=card.width+gap
    sheet.save(OUT / f'compare-난-v3-morph-{width}.png')
    for card in cards:card.close()
print('PASS: topology, matched motion, morph, relief, hit size, directions, crossfade, tuning, touch, keyboard, reduced motion, 390/320 layouts')
