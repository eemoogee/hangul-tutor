"""Full-playthrough smoke test for v2.2.1: play all 8 items correctly through
the real UI at two viewport sizes, then confirm the export is coherent.
Guards against the buildPlan/report edits breaking normal play.
"""
import sys, pathlib, json
from playwright.sync_api import sync_playwright

TARGET = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path("index-v2.html").resolve()
ok_all = True

with sync_playwright() as p:
    browser = p.chromium.launch()
    for vw, vh in [(390, 844), (320, 568)]:
        page = browser.new_page(viewport={"width": vw, "height": vh})
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(TARGET.as_uri())
        page.wait_for_function("() => !!window.__transferLab")

        # choose method, start with a fixed seed
        page.click('[data-method="control"]')
        page.fill("#seed", "12345") if page.query_selector("#seed") else None
        page.click('[data-action="start"]')
        page.click('[data-action="begin"]')

        played = 0
        for _ in range(8):
            # find the correct option index for the current item
            idx = page.evaluate("""() => {
                const L = window.__transferLab;
                const s = L.state.session;
                const si = s.items[s.itemIndex];
                const {def, opts} = L.resolve(si.id, s);
                const key = def.kind === 'p2' ? def.keySlot
                          : def.kind === 'p1'  ? def.key
                          : def.key;
                return opts.indexOf(key);
            }""")
            assert idx >= 0, "correct option not found in options"
            page.click(f'.opt[data-idx="{idx}"], .ghost[data-idx="{idx}"]')
            page.click('[data-action="confirm"]')
            played += 1
            # after confirm, only "Recorded" feedback should appear
            page.click('[data-action="next"], [data-action="finish"]')

        rep = page.evaluate("() => JSON.parse(JSON.stringify(window.__transferLab.report(window.__transferLab.state.session)))")
        subs = rep["subscores"]
        total = sum(v["committed"] for v in subs.values())
        presented = rep["plan"].get("presentedOrder") or rep["plan"].get("itemOrder")
        cues = rep["plan"]["cueOrder"]
        sylls = rep["plan"]["syllOrder"]
        cue_ok = cues == [x for x in presented if x.startswith("S-")]
        syll_ok = sylls == [x for x in presented if x.startswith("Y-")]
        print(f"[{vw}x{vh}] played={played}/8 committed_total={total}/8 "
              f"cueOrder_derived_ok={cue_ok} syllOrder_derived_ok={syll_ok} js_errors={len(errs)}")
        if total != 8 or not cue_ok or not syll_ok or errs:
            ok_all = False
            print("   FAIL detail:", json.dumps({"subscores": subs, "presented": presented,
                                                 "cue": cues, "syll": sylls, "errors": errs[:2]}))
        page.close()
    browser.close()

print("\nFULL PLAYTHROUGH:", "PASS" if ok_all else "FAIL")
sys.exit(0 if ok_all else 1)
