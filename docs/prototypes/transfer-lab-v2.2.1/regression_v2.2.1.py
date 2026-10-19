"""
Regression tests for Transfer Lab v2.2.1 — the two must-fix defects from the
independent review of v2.2.

  BUG-1  Exported cueOrder/syllOrder disagreed with presented order.
  BUG-2  Unsaved observer notes were discarded on results toggle / next learner.

Tests drive the REAL page in Chromium (file:// load). render() is closure-
scoped, so the done screen is reached through the app's own delegated click
handler rather than by calling internal functions directly.

Both tests are expected to FAIL on frozen v2.2 and PASS on v2.2.1:
    python regression_v2.2.1.py <path/to/index-v2.html>
"""
import sys, pathlib, json

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
TARGET = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE / "index-v2.html"

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))


def reach_done_screen(page):
    """Drive the app to a rendered done screen via its own click delegation.

    The handler is registered on #app, so the probe must be INSIDE #app and the
    event must bubble -- a bare .click() on a body-level element never reaches
    it (that was a harness bug, not an app bug).
    """
    return page.evaluate("""() => {
        const L = window.__transferLab;
        const app = document.getElementById('app');
        const fire = action => {
            const b = document.createElement('button');
            b.dataset.action = action;
            app.appendChild(b);
            b.dispatchEvent(new MouseEvent('click', {bubbles:true}));
            b.remove();
        };

        L.state.method  = 'cold_control';
        L.state.session = L.makeSession('cold_control', '', 424242);
        L.state.screen  = 'done';
        L.state.showTester = false;
        fire('toggleTester');   // app handler -> render() -> doneHtml()
        fire('toggleTester');   // back to hidden summary

        return {
            screen: L.state.screen,
            hasVisual: !!document.getElementById('ex-visual'),
            hasObs: !!document.getElementById('obs'),
            hasToggle: !!document.querySelector('[data-action="toggleTester"]'),
            hasSave: !!document.querySelector('[data-action="saveNotes"]'),
        };
    }""")


def run():
    if not TARGET.exists():
        print(f"missing target: {TARGET}")
        return 2

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        js_errors = []
        page.on("pageerror", lambda e: js_errors.append(str(e)))
        page.goto(TARGET.as_uri())
        page.wait_for_function("() => !!window.__transferLab")

        # ------------------------------------------------------------------
        # BUG-1: exported order must equal presented order
        # ------------------------------------------------------------------
        bug1 = page.evaluate("""() => {
            const L = window.__transferLab;
            let cueBad = 0, syllBad = 0, n = 0;
            const bad = [];
            for (let i = 0; i < 200; i++) {
                const seed = 1000 + i * 7919;
                const plan = L.buildPlan(seed);
                const rep  = L.report(L.makeSession('cold_control', '', seed));
                const actCue  = plan.order.filter(id => L.ITEM_BY_ID[id].family === 'sound');
                const actSyll = plan.order.filter(id => L.ITEM_BY_ID[id].family === 'syllable');
                n++;
                if (rep.plan.cueOrder.join()  !== actCue.join())  { cueBad++;  if (bad.length < 3) bad.push({seed, what:'cue',  got:rep.plan.cueOrder, want:actCue}); }
                if (rep.plan.syllOrder.join() !== actSyll.join()) { syllBad++; if (bad.length < 3) bad.push({seed, what:'syll', got:rep.plan.syllOrder, want:actSyll}); }
            }
            const probe = L.buildPlan(12345);
            const repProbe = L.report(L.makeSession('cold_control', '', 12345));
            const presentedOk = Array.isArray(repProbe.plan.presentedOrder) &&
                repProbe.plan.presentedOrder.join() === probe.order.join();
            return {n, cueBad, syllBad, bad, presentedOk,
                    staleField: 'itemOrder' in repProbe.plan,
                    probe: {presented: repProbe.plan.presentedOrder,
                            cue: repProbe.plan.cueOrder,
                            syll: repProbe.plan.syllOrder}};
        }""")

        check(f"BUG-1 exported cueOrder matches presented order across {bug1['n']} seeds",
              bug1["cueBad"] == 0, f"{bug1['cueBad']} mismatch(es) {bug1['bad'][:2]}")
        check(f"BUG-1 exported syllOrder matches presented order across {bug1['n']} seeds",
              bug1["syllBad"] == 0, f"{bug1['syllBad']} mismatch(es) {bug1['bad'][:2]}")
        check("BUG-1 report exposes plan.presentedOrder == plan.order",
              bug1["presentedOk"], json.dumps(bug1["probe"]))
        check("BUG-1 misleading plan.itemOrder field removed",
              not bug1["staleField"],
              "renamed to presentedOrder" if not bug1["staleField"] else "itemOrder still exported")

        varies = page.evaluate("""() => {
            const L = window.__transferLab;
            const cue = new Set(), syll = new Set();
            for (let i = 0; i < 200; i++) {
                const pl = L.buildPlan(5000 + i * 104729);
                cue.add(pl.order.filter(id => L.ITEM_BY_ID[id].family==='sound').join());
                syll.add(pl.order.filter(id => L.ITEM_BY_ID[id].family==='syllable').join());
            }
            return {cue: cue.size, syll: syll.size};
        }""")
        check("derived cue order still varies across seeds", varies["cue"] > 1, f"{varies['cue']} variants")
        check("derived syllable order still varies across seeds", varies["syll"] > 1, f"{varies['syll']} variants")

        repro = page.evaluate("""() => {
            const L = window.__transferLab;
            const a = JSON.stringify(L.buildPlan(777));
            return {same: a === JSON.stringify(L.buildPlan(777)),
                    diff: a !== JSON.stringify(L.buildPlan(778))};
        }""")
        check("fixed seed reproduces identical plan", repro["same"])
        check("different seed yields different plan", repro["diff"])

        # ------------------------------------------------------------------
        # BUG-2: notes survive toggle / export / next learner
        # ------------------------------------------------------------------
        page.goto(TARGET.as_uri())
        page.wait_for_function("() => !!window.__transferLab")

        state = reach_done_screen(page)
        check("done screen renders note fields and controls",
              state["hasVisual"] and state["hasObs"] and state["hasToggle"],
              json.dumps(state))

        if state["hasVisual"] and state["hasObs"]:
            VISUAL = "I counted the strokes and flipped them."
            OBS = "Learner hesitated about 6s on the first block item."

            page.fill("#ex-visual", VISUAL)
            page.fill("#obs", OBS)

            page.click('[data-action="toggleTester"]')
            a = {"visual": page.input_value("#ex-visual"), "obs": page.input_value("#obs")}
            check("BUG-2 notes survive tester-summary toggle",
                  a["visual"] == VISUAL and a["obs"] == OBS, json.dumps(a))

            page.click('[data-action="toggleTester"]')
            b = {"visual": page.input_value("#ex-visual"), "obs": page.input_value("#obs")}
            check("BUG-2 notes survive toggling back",
                  b["visual"] == VISUAL and b["obs"] == OBS, json.dumps(b))

            exported = page.evaluate(
                "() => JSON.parse(JSON.stringify(window.__transferLab.report(window.__transferLab.state.session)))")
            check("BUG-2 typed notes reach the exported report (no Save pressed)",
                  exported["explanations"]["visual"] == VISUAL and exported["observerNote"] == OBS,
                  f"visual={exported['explanations']['visual']!r} obs={exported['observerNote']!r}")

            page.click('[data-action="newLearner"]')
            stored = page.evaluate("""() => window.__transferLab.loadSessions()
                .map(s => ({visual: (s.explanations||{}).visual, obs: s.observerNote}))""")
            hit = [s for s in stored if s["visual"] == VISUAL and s["obs"] == OBS]
            check("BUG-2 notes persisted to storage across next learner",
                  len(hit) == 1, f"{len(stored)} stored, {len(hit)} matched")
        else:
            check("BUG-2 notes survive tester-summary toggle", False, "done screen did not render")
            check("BUG-2 typed notes reach the exported report (no Save pressed)", False, "not reached")
            check("BUG-2 notes persisted to storage across next learner", False, "not reached")

        check("no uncaught JavaScript page errors", len(js_errors) == 0,
              "; ".join(js_errors[:3]))
        browser.close()

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} assertions passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(run())
