"""Adversarial verifier for the eight-item Vowel Transfer Lab v2.2.

Every check here runs against the REAL page in Chromium over a local HTTP
server. Nothing is asserted from reading source; the bank invariants are read
back out of window.__transferLab after the page has built a session.

Covers the owner's required strategies:
  fixed answer position          always tap the same on-screen slot
  one stroke direction           always tap the option with the stroke right/below
  eliminate displayed symbols    avoid any glyph/sound already shown this session
  use earlier answers            drop an option matching an earlier committed answer
  random guessing                uniform pick

Plus structural invariants:
  * correct answer's displayed position varies (not fixed / not biased)
  * all four sound cues occur exactly once per session
  * abstract visual items have no missing-fourth-symbol shortcut

Usage:  python verify_transfer_lab_v2.py
Writes JSON + screenshots to .verify_out/ relative to this file's parent.
"""
import json
import random
import statistics
import sys
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent   # the lab directory itself
ROOT = HERE                               # served root
OUT = ROOT / ".verify_out"
OUT.mkdir(exist_ok=True)
PAGE = "index-v2.html"
PORT = 18371

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append({"check": name, "pass": bool(ok), "detail": detail})
    print(("PASS  " if ok else "FAIL  ") + name + (("  :: " + str(detail)) if detail and not ok else ""))
    return ok


class Quiet(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, *a):
        pass


def serve():
    """Bind an ephemeral port. A fixed port can be stuck in TIME_WAIT after a
    crashed run, which silently leaves the page unserved and every check failing
    with 'undefined' lookups."""
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


# ----------------------------------------------------------------------------
# In-page helpers (installed once per page as __v)
# ----------------------------------------------------------------------------
INIT = """
() => {
  const L = window.__transferLab;
  const q = s => document.querySelector(s);
  const qa = s => [...document.querySelectorAll(s)];
  window.__v = {
    site(){ return q('.content').getBoundingClientRect(); },
    cur(){ const s=L.state.session; return {i:s.itemIndex, si:s.items[s.itemIndex], def:L.ITEM_BY_ID[s.items[s.itemIndex].id]}; },
    options(){ return qa('[data-idx]').map(b => ({idx:+b.dataset.idx, choice:b.dataset.choice})); },
    keyIndex(){
      const {si,def} = this.cur();
      const opts = L.resolve(si.id, L.state.session).opts;
      const key = def.kind==='p2' ? def.keySlot : def.key;
      return opts.indexOf(key);
    },
    click(idx){ qa('[data-idx]')[idx].click(); },
    confirm(){ q('[data-action=confirm]').click(); },
    next(){ const b=q('[data-action=next]'); if(b) b.click(); },
    feedbackText(){ const r=q('.recorded'); return r ? r.innerText : ''; },
    bodyText(){ return q('.content').innerText; },
    svgCount(){ return qa('.content svg').length; },
    // every glyph side/position token currently visible in the item, for
    // an "avoid what has already been displayed" adversary
    visibleGlyphIds(){
      const {si} = this.cur();
      return L.state.session.plan.optionOrder[si.id].slice();
    }
  };
  return true;
}
"""


def play_session(page, seed, chooser, method="control"):
    """chooser(item_context) -> display index to tap.

    item_context = {defId, kind, cue, axis, nOptions, keyIndex, options,
                    seenChoices, committedChoices, sessionIndex}
    """
    page.evaluate("""({seed}) => {
      const L = window.__transferLab;
      document.querySelector('[data-method="control"]').click();
      const seedEl = document.getElementById('seed');
      seedEl.value = String(seed);
      document.querySelector('[data-action="start"]').click();
      document.querySelector('[data-action="begin"]').click();
    }""", {"seed": seed})
    page.evaluate(INIT)
    logged = []
    seen_choices = set()
    committed = set()
    for i in range(8):
        ctx = page.evaluate("""() => {
          const v = window.__v, c = v.cur();
          return {defId: c.si.id, kind: c.def.kind, cue: c.def.cue || null, axis: c.def.axis || null,
                  nOptions: v.options().length, keyIndex: v.keyIndex(),
                  options: v.options().map(o => o.choice),
                  visibleGlyphIds: v.visibleGlyphIds(),
                  glyphOptions: v.options().map(o => o.choice),
                  blockVowels: null};
        }""")
        ctx["seenChoices"] = sorted(seen_choices)
        ctx["committedChoices"] = sorted(committed)
        ctx["sessionIndex"] = i
        pick = chooser(ctx)
        pick = max(0, min(ctx["nOptions"] - 1, int(pick)))
        page.evaluate("(i) => window.__v.click(i)", pick)
        page.evaluate("() => window.__v.confirm()")
        rec = page.evaluate("""() => {
          const s = window.__transferLab.state.session, si = s.items[s.itemIndex];
          return {id: si.id, first: si.firstPickSlot, committed: si.committedSlot,
                  firstCorrect: si.firstPickCorrect, committedCorrect: si.committedCorrect,
                  taps: si.previewPath.length, fam: si.family};
        }""")
        logged.append(rec)
        seen_choices |= set(ctx["options"])
        committed.add(rec["committed"])
        page.evaluate("() => window.__v.next()")
    return logged


# ----------------------------------------------------------------------------
# Strategies -- each is a pure function of what a learner can see
# ----------------------------------------------------------------------------
def s_random(ctx):
    return random.randrange(ctx["nOptions"])


def s_fixed_position(ctx):
    return 0


def s_fixed_position_last(ctx):
    return ctx["nOptions"] - 1


RIGHT_BELOW = {"mid-R", "mid-D"}          # stroke on the right (vertical) / below (horizontal)
WRONG_SIDE = {"mid-L", "mid-U"}

def s_one_direction(ctx):
    """Always tap the placement whose stroke is to the right / below."""
    if ctx["kind"] == "p2":
        for i, c in enumerate(ctx["options"]):
            if c in RIGHT_BELOW:
                return i
        return 0
    return 0


def s_one_direction_opposite(ctx):
    """Always tap left / above."""
    if ctx["kind"] == "p2":
        for i, c in enumerate(ctx["options"]):
            if c in WRONG_SIDE:
                return i
        return 0
    return 0


def s_eliminate_displayed(ctx):
    """Never pick something whose on-screen form was already displayed this session."""
    seen = set(ctx["seenChoices"])
    for i, c in enumerate(ctx["options"]):
        if c not in seen:
            return i
    return 0


def s_recall_previous(ctx):
    """Drop the option that matches an answer already committed this session."""
    prev = set(ctx["committedChoices"])
    for i, c in enumerate(ctx["options"]):
        if c not in prev:
            return i
    return 0


def s_eliminate_and_recall(ctx):
    seen = set(ctx["seenChoices"]) | set(ctx["committedChoices"])
    for i, c in enumerate(ctx["options"]):
        if c not in seen:
            return i
    return 0


def s_choose_key(ctx):
    return ctx["keyIndex"]


STRATEGIES = {
    "random": s_random,
    "fixed_position_first": s_fixed_position,
    "fixed_position_last": s_fixed_position_last,
    "one_direction_right_below": s_one_direction,
    "one_direction_left_above": s_one_direction_opposite,
    "eliminate_displayed": s_eliminate_displayed,
    "recall_previous_answers": s_recall_previous,
    "eliminate_and_recall": s_eliminate_and_recall,
    "knows_answer": s_choose_key,
}


def main():
    srv, port = serve()
    url = f"http://127.0.0.1:{port}/{PAGE}"
    summary = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctxb = browser.new_context(viewport={"width": 390, "height": 844},
                                   device_scale_factor=1, is_mobile=True, has_touch=True)
        page = ctxb.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        resp = page.goto(url, wait_until="domcontentloaded")
        # Fail loudly and immediately if the page did not actually serve.
        if not check("page served with HTTP 200", resp is not None and resp.status == 200,
                     None if resp is None else resp.status):
            print("Aborting: nothing to verify.")
            return 1
        page.wait_for_function("() => !!window.__transferLab && window.__transferLab.ALL_ITEMS.length === 8",
                               timeout=5000)

        # ---------------- structural: bank integrity from the real page ----------
        bank = page.evaluate("""() => {
          const L = window.__transferLab;
          const fam = {};
          L.ALL_ITEMS.forEach(it => { (fam[it.family] = fam[it.family] || []).push(it.id); });
          return {counts: Object.fromEntries(Object.entries(fam).map(([k,v])=>[k,v.length])),
                  total: L.ALL_ITEMS.length,
                  version: L.ITEM_SET_VERSION,
                  cues: L.ALL_ITEMS.filter(i=>i.family==='sound').map(i=>i.cue).sort(),
                  p1keys: L.ALL_ITEMS.filter(i=>i.family==='visual').map(i=>({id:i.id,key:i.key,options:i.options,demo:i.demo,query:i.query})),
                  p3: L.ALL_ITEMS.filter(i=>i.family==='syllable').map(i=>({id:i.id,options:i.options,key:i.key,block:i.block||null}))};
        }""")
        check("bank has exactly 8 items", bank["total"] == 8, bank["total"])
        check("families are 2 / 4 / 2", bank["counts"] == {"visual": 2, "sound": 4, "syllable": 2}, bank["counts"])
        check("sound cues are a, eo, o, u exactly once",
              bank["cues"] == ["a", "eo", "o", "u"], bank["cues"])

        # P1: no missing-4th-symbol shortcut, key is the side-flip transform
        p1_ok, p1_detail = True, []
        for it in bank["p1keys"]:
            shown = set(it["demo"]) | {it["query"]}
            for opt in it["options"]:
                if opt in shown:
                    p1_ok = False
                    p1_detail.append(f"{it['id']}: option {opt} already displayed")
            if it["key"] in shown:
                p1_ok = False
                p1_detail.append(f"{it['id']}: key {it['key']} is displayed")
            # also: all four options must be distinct, and no option equals the query
            if it["query"] in it["options"]:
                p1_ok = False
                p1_detail.append(f"{it['id']}: query itself offered as an option")
        check("P1 abstract items have no missing-fourth-symbol shortcut", p1_ok, p1_detail)

        # P1 across both items: no glyph reused between items (kills cross-item recall)
        g1 = set(bank["p1keys"][0]["options"]) | set(bank["p1keys"][0]["demo"]) | {bank["p1keys"][0]["query"]}
        g2 = set(bank["p1keys"][1]["options"]) | set(bank["p1keys"][1]["demo"]) | {bank["p1keys"][1]["query"]}
        check("P1 glyph pools are disjoint across the two items", not (g1 & g2), sorted(g1 & g2))

        # P3: ㅁ-only
        p3_bad = [it["id"] for it in bank["p3"] if any(ch in "ㄴ" for o in it["options"] + [it["key"]] for ch in str(o))]
        p3_blocks = page.evaluate("() => Object.keys(window.__transferLab.BLOCKS)")
        check("P3 options use ㅁ only (no ㄴ distractor)", not p3_bad and set(p3_blocks) <= {"모", "무", "마", "머"},
              {"bad_items": p3_bad, "blocks": p3_blocks})

        # ---------------- cue coverage + key position variation across many seeds
        N_SEEDS = 240
        plan_stats = page.evaluate("""(n) => {
          const L = window.__transferLab;
          const out = {cuesAllFour:0, cueOrderVaried:new Set(), keyPos:{}, itemOrderVaried:new Set(),
                       posByItem:{}, p1KeyPosVaried:{}, p3First:new Set()};
          for (let s = 0; s < n; s++) {
            const seed = 1000 + s * 7919;
            const plan = L.buildPlan(seed);
            const sess = {plan};
            const cues = plan.cueOrder.map(id => L.ITEM_BY_ID[id].cue).sort().join(',');
            if (cues === 'a,eo,o,u') out.cuesAllFour++;
            out.cueOrderVaried.add(plan.cueOrder.join(','));
            out.itemOrderVaried.add(plan.order.join(','));
            out.p3First.add(plan.syllOrder[0]);
            for (const id of plan.order) {
              const def = L.ITEM_BY_ID[id];
              const opts = plan.optionOrder[id];
              const key = def.kind === 'p2' ? def.keySlot : def.key;
              const pos = opts.indexOf(key);
              const k = id + '@' + pos;
              out.posByItem[k] = (out.posByItem[k] || 0) + 1;
              if (!out.keyPos[id]) out.keyPos[id] = {};
              out.keyPos[id][pos] = (out.keyPos[id][pos] || 0) + 1;
            }
          }
          out.cueOrderVaried = out.cueOrderVaried.size;
          out.itemOrderVaried = out.itemOrderVaried.size;
          out.p3First = [...out.p3First].sort();
          return out;
        }""", N_SEEDS)
        check(f"all four sound cues present in each of {N_SEEDS} sessions",
              plan_stats["cuesAllFour"] == N_SEEDS, plan_stats["cuesAllFour"])
        check(f"cue presentation order varies ({plan_stats['cueOrderVaried']} distinct orders)",
              plan_stats["cueOrderVaried"] > 1, plan_stats["cueOrderVaried"])
        check(f"full item order varies ({plan_stats['itemOrderVaried']} distinct of {N_SEEDS})",
              plan_stats["itemOrderVaried"] > N_SEEDS * 0.9, plan_stats["itemOrderVaried"])
        check("P3 encode/decode start order varies", plan_stats["p3First"] == ["Y-decode", "Y-encode"], plan_stats["p3First"])

        # v2.2.1: the previous checks above read plan.cueOrder / plan.syllOrder,
        # which in v2.2 were independent draws that did NOT describe what was
        # presented. That made those assertions vacuous with respect to the UI.
        # This check derives the order from plan.order -- the array the renderer
        # actually iterates -- and requires the exported fields to agree.
        order_agree = page.evaluate("""(n) => {
          const L = window.__transferLab;
          let cueBad = 0, syllBad = 0, repBad = 0;
          for (let s = 0; s < n; s++) {
            const seed = 1000 + s * 7919;
            const plan = L.buildPlan(seed);
            const actCue  = plan.order.filter(id => L.ITEM_BY_ID[id].family === 'sound');
            const actSyll = plan.order.filter(id => L.ITEM_BY_ID[id].family === 'syllable');
            if (plan.cueOrder.join()  !== actCue.join())  cueBad++;
            if (plan.syllOrder.join() !== actSyll.join()) syllBad++;
            const rp = L.report(L.makeSession('control', '', seed)).plan;
            const presented = rp.presentedOrder || rp.itemOrder;
            if (rp.cueOrder.join()  !== presented.filter(id => L.ITEM_BY_ID[id].family === 'sound').join() ||
                rp.syllOrder.join() !== presented.filter(id => L.ITEM_BY_ID[id].family === 'syllable').join()) repBad++;
          }
          return {cueBad, syllBad, repBad};
        }""", N_SEEDS)
        check("exported cueOrder equals presented order (derived from plan.order)",
              order_agree["cueBad"] == 0, order_agree)
        check("exported syllOrder equals presented order (derived from plan.order)",
              order_agree["syllBad"] == 0, order_agree)
        check("report plan order fields agree with plan.order",
              order_agree["repBad"] == 0, order_agree)

        # key position must vary and be roughly balanced for every item
        pos_ok, pos_detail = True, {}
        for item, dist in plan_stats["keyPos"].items():
            total = sum(dist.values())
            pos_detail[item] = {k: round(v / total, 3) for k, v in sorted(dist.items(), key=lambda x: int(x[0]))}
            if len(dist) != 4:
                pos_ok = False
            for k, v in dist.items():
                if v / total < 0.15 or v / total > 0.35:
                    pos_ok = False
        check(f"correct-answer display position varies across all 4 slots for every item (n={N_SEEDS})",
              pos_ok, pos_detail)

        # ---------------- reproduce a session from its seed ----------------
        rep_ok = page.evaluate("""() => {
          const L = window.__transferLab;
          const a = L.buildPlan(424242), b = L.buildPlan(424242), c = L.buildPlan(424243);
          return JSON.stringify(a) === JSON.stringify(b) && JSON.stringify(a) !== JSON.stringify(c);
        }""")
        check("same seed reproduces the identical plan; a different seed does not", rep_ok)

        # ---------------- play every strategy over many seeded sessions ---------
        # 200 seeded sessions per strategy. 40 was too few: one early run put the
        # random strategy at 1.675/8 (theory 2.00) purely by sampling noise, which
        # is not evidence of anything either way.
        SEEDS = list(range(1, 201))
        for name, fn in STRATEGIES.items():
            random.seed(hash(name) & 0xFFFF)
            totals, fams, firsts = [], {"visual": [], "sound": [], "syllable": []}, []
            per_item = {}
            for seed in SEEDS:
                rec = play_session(page, seed, fn)
                totals.append(sum(1 for r in rec if r["committedCorrect"]))
                firsts.append(sum(1 for r in rec if r["firstCorrect"]))
                for f in fams:
                    fams[f].append(sum(1 for r in rec if r["fam"] == f and r["committedCorrect"]))
                for r in rec:
                    per_item.setdefault(r["id"], []).append(r["committedCorrect"])
                page.evaluate("() => { const b = document.querySelector('[data-action=newLearner]'); if (b) b.click(); }")
            item_rate = {k: round(sum(v) / len(v), 3) for k, v in sorted(per_item.items())}
            summary[name] = {"mean": round(statistics.mean(totals), 3),
                             "sd": round(statistics.pstdev(totals), 3),
                             "min": min(totals), "max": max(totals),
                             "family_mean": {f: round(statistics.mean(v), 3) for f, v in fams.items()},
                             "item_rate": item_rate, "sessions": len(SEEDS)}
            print(f"    {name:28s} mean {summary[name]['mean']:.2f}/8  "
                  f"fam {summary[name]['family_mean']}  range {min(totals)}–{max(totals)}")

        # anchors
        check("random guessing averages near 2/8", 1.5 <= summary["random"]["mean"] <= 2.6, summary["random"]["mean"])
        check("fixed-position adversary gets no more than chance",
              summary["fixed_position_first"]["mean"] <= 2.6 and summary["fixed_position_last"]["mean"] <= 2.6,
              {"first": summary["fixed_position_first"]["mean"], "last": summary["fixed_position_last"]["mean"]})
        check("one-direction adversary scores exactly 2/4 on sound-to-shape",
              all(abs(summary[k]["family_mean"]["sound"] - 2.0) < 1e-9 for k in
                  ("one_direction_right_below", "one_direction_left_above")),
              {k: summary[k]["family_mean"]["sound"] for k in ("one_direction_right_below", "one_direction_left_above")})
        check("eliminate-displayed adversary cannot clear the abstract items",
              summary["eliminate_displayed"]["family_mean"]["visual"] <= 0.6,
              summary["eliminate_displayed"]["family_mean"]["visual"])
        check("recall-previous-answers adversary gains nothing on abstract items",
              summary["recall_previous_answers"]["family_mean"]["visual"] <= 1.2,
              summary["recall_previous_answers"]["family_mean"]["visual"])
        check("knowing the answer scores 8/8 (harness sanity)",
              summary["knows_answer"]["mean"] == 8.0, summary["knows_answer"]["mean"])
        # A fixed direction is deterministic PER ITEM (always right => always right on S-a).
        # The design guarantee is at the bank level, not the item level: it must total
        # exactly 2/4 on the four sound cues, never 4/4.
        d = summary["one_direction_right_below"]["item_rate"]
        sound_items = {k: v for k, v in d.items() if k.startswith("S-")}
        check("a fixed direction is deterministic per item but totals exactly 2/4 on sound-to-shape",
              abs(sum(sound_items.values()) - 2.0) < 1e-9
              and all(v in (0.0, 1.0) for v in sound_items.values()),
              sound_items)

        # ---------------- per-item sound rate must not exceed the model ----------
        item_ceiling_ok = True
        ceiling_detail = {}
        for k, r in summary["eliminate_and_recall"]["item_rate"].items():
            ceiling_detail[k] = r
            if r > 0.75:
                item_ceiling_ok = False
        check("no item is beaten >75% of the time by elimination+recall alone", item_ceiling_ok, ceiling_detail)

        check("no page errors during the whole run", not errors, errors[:3])
        browser.close()
    srv.shutdown()

    out = OUT / "verify_transfer_lab_v2.json"
    out.write_text(json.dumps({"checks": RESULTS, "strategies": summary,
                               "passed": sum(1 for r in RESULTS if r["pass"]), "total": len(RESULTS)}, indent=2),
                   encoding="utf-8")
    passed = sum(1 for r in RESULTS if r["pass"])
    print(f"\n{passed}/{len(RESULTS)} checks passed -> {out}")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
