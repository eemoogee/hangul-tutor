# Transfer Lab v2.2.1 — changes

**Base:** frozen `transfer-lab-v2.2-eight.zip` (SHA-256 `7260a25c7e0f2ce47a3b381acccd7f15358581b7652c1fa6189e89af619a709d`).
That package is **not modified**. v2.2.1 is a separate copy.

**Scope:** the two "must fix before participant data collection" items from the
independent v2.2 review, plus the verifier gap that let bug 1 through. No other
behaviour was intentionally changed.

---

## Fixed

### 1. Exported cue/syllable order disagreed with presented order

**Cause.** `buildPlan()` drew `plan.order` (the array the renderer iterates) and
then separately drew `plan.cueOrder` / `plan.syllOrder` from independent RNG
streams (salts 2 and 3). Nothing rendered from the latter two; they existed only
to be exported, where they were labelled as if they described the session.

**Measured on v2.2** (independent reproduction, 200 seeds `1000 + i*7919`):

| field | disagreements with presented order |
|---|---|
| `cueOrder` | 190 / 200 |
| `syllOrder` | 83 / 200 |

The review reported 95/100 and 45/100 on its own seed set; same defect, different
sampling. Seed 12345 reproduced exactly: exported `S-a,S-u,S-eo,S-o`, presented
`S-u,S-eo,S-o,S-a`.

**Fix.** `cueOrder` and `syllOrder` are now *derived* from `order` by family
filter, never drawn:

```js
const cueOrder  = order.filter(id => FAMILY_BY_ID[id] === 'sound');
const syllOrder = order.filter(id => FAMILY_BY_ID[id] === 'syllable');
```

`FAMILY_BY_ID` added next to `ITEM_BY_ID` for the lookup.

**Seed-neutrality.** Verified across 200 seeds that the fix changes **neither**
the presented order nor any option order (0/200 differences for both). Any
session recorded under v2.2 re-derives the same items in the same order; only the
previously-wrong labels are corrected. `shuffled()` consumes RNG proportional to
array length, which is why the old length-dependent draws could never have
matched the eight-item presentation order.

**Export schema.** `plan.itemOrder` is renamed **`plan.presentedOrder`** so the
one truthful field is not confusable with the two derived ones. This is a
breaking change for any downstream parser; v2.2.1 reports are not
schema-identical to v2.2.

### 2. Unsaved observer notes were discarded

**Cause.** `doneHtml()` renders the four note textareas from
`session.explanations.*` / `session.observerNote`. Only `saveNotes()` wrote those
fields. `toggleTester` called `render()` with no harvest, so any typed-but-unsaved
text was replaced with the unchanged empty state and lost silently. The same
exposure existed on `newLearner`, `downloadReport` and `copyReport`.

**Fix.** New `harvestNotes()` writes the four textareas into session state, and is
called before every path that rerenders or exports from the done screen:

- `toggleTester` — harvest, then rerender
- `copyReport` / `downloadReport` — harvest before building JSON
- `saveNotes` — now delegates to `harvestNotes()`
- `newLearner` — harvest, `upsertSession()`, then reset
- `erase` (first tap) — harvest, so the confirmation step cannot lose notes

`harvestNotes()` is a no-op unless `state.session` exists and `screen === 'done'`,
so it cannot leak setup-screen values into a session.

## Tests added

### `regression_v2.2.1.py`
Drives the real page in Chromium. Must **fail on v2.2** and **pass on v2.2.1**.

- exports agree with presented order over 200 seeds (cue and syllable)
- `plan.presentedOrder` present and equal to `plan.order`
- stale `plan.itemOrder` field gone
- derived orders still *vary* across seeds (guards over-correction to fixed order)
- fixed seed reproducible; different seed differs
- notes survive tester-summary toggle (both directions)
- typed notes reach the export with no Save pressed
- notes persisted to storage across Next learner
- no uncaught page errors

Result: **v2.2 6/14** (8 failures = the two bugs), **v2.2.1 14/14**.

> Harness note: the first version of this test clicked a probe button appended to
> `<body>`, which never reaches the delegated handler on `#app`, so the done screen
> failed to render and BUG-2 reported false failures. The probe is now appended to
> `#app` and dispatches a bubbling click. If a future harness "cannot render" the
> done screen, check this first.

### `smoke_playthrough.py`
Plays all 8 items correctly through the real UI at 390×844 and 320×568, then
asserts 8/8 committed and that exported order matches the presented order.

Result: v2.2 **FAIL** (order fields wrong), v2.2.1 **PASS** at both viewports.

### Verifier strengthened (`verify_transfer_lab_v2.py`)
Three checks added, deriving order from `plan.order` rather than trusting the
report fields. The original check `cue presentation order varies` read
`plan.cueOrder` — the field nothing renders — and so passed while the export was
wrong.

Result: **v2.2 22/25** (three new checks fail, 230 cue mismatches), **v2.2.1 25/25**.

---

## Deliberately NOT changed

Left as the review described, for a separate decision:

- **P1 prompt reveals its rule** (review item 3). Both P1 items still say the short
  stroke "keeps its place and moves to the other side". This means P1 measures
  rule *comprehension*, not rule *inference*. Either neutralise the prompt or
  relabel the construct in the report — an instrument-design choice, not a bug fix.
- **README nonlearning-strategy claim** (item 5). `README.md:110` still says no
  non-learned strategy exceeds chance except `single_surface_cue` at 34.5%. The
  bundled model shows `one_direction` at **26.2%** vs `random` at **11.2%**, so the
  sentence is wrong as written. Correcting it changes a stated finding, so it is
  left for the owner.
- **Report/README descriptions of v2.2 behaviour** — `REPORT-v2.2.md` and
  `RUN-VERIFICATION.txt` describe v2.2 and its 22 checks. They are not rewritten
  here; the verifier now reports 25.
- **Screen-reader gaps** (item 7), **missing baseline scripts** (item 6), **P1
  construct label** — unchanged.

## Still not verified

- No physical phone, touch, or text-scale testing.
- No screen-reader testing.
- No human comprehension, learning, or retention evidence.
- The 50 000-session model baselines in `model_baselines_v2.json` remain the
  author's output; they were not regenerated here (the generating scripts are not
  in the package).
- Verifier and tests were run with system Chromium via Playwright against
  `file://` URLs. No HTTP server was used, so the "served with HTTP 200" property
  remains untested in this copy.
