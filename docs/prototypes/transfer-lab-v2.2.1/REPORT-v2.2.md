# Vowel Transfer Lab v2.2 — eight-item build

Report for the approved design revision. Playable file: `index-v2.html`.

Everything below was measured with the scripts in this folder. Modeled
probabilities are labeled as modeled; nothing here is a learner result. No
learner has played this build.

---

## 1. What changed from the six-item draft

| Owner decision | Implementation |
| --- | --- |
| Eight items: 2 abstract visual, 4 sound-to-shape, 2 new-syllable | `ITEM BANK` in `index-v2.html`; 2 / 4 / 2, asserted by the verifier |
| a, eo, o, u exactly once per session, randomized | `buildPlan()` draws a cue order; all four always appear. verifier checks 240 sessions |
| Record item order, cue assignment, options for reproducibility | `session.plan` = `itemOrder`, `cueOrder`, `syllOrder`, `optionOrder`; a seed field on setup reproduces a session exactly |
| Abstract P1 as calibration, scored separately | `subscores.visual` never folds into a total; the tester note says P1 can be solved with no Hangul knowledge |
| Glyph notation internal only | `V60R` / `H20D` appear in the plan and report JSON, never in learner-facing text or labels |
| Neutral P2 preview, no feedback | preview renders the composed shape with no sound label; no check button exists |
| Log first pick / preview changes / final choice separately | `firstPickSlot`, `previewPath[]`, `committedSlot` + `firstPickCorrect`, `committedCorrect`, `previewChanges` |
| P3 uses ㅁ for both items | `BLOCKS` = 모 무 마 머 only; the ㄴ distractor from the draft is gone |
| No feedback between items | after confirm, the only text is "Recorded."; next item follows |
| No total pass/fail threshold | no threshold is computed anywhere; subscores only |

---

## 2. Correction of the earlier probability analysis

The earlier 19.5% figure modeled the visual items at 50% and the
sound-to-shape items at 50%, then treated the syllable items at 25%. It
therefore described a learner who is test-wise on three families, not one
who is random outside the visual items. It also predated the abstract-glyph
redesign. Both problems are corrected here.

**Two independent computations agree.** `model_baselines_v2.py` simulates
50,000 sessions per adversary using a byte-faithful copy of the page's
`mulberry32`/`stream`/`shuffled`. `verify_transfer_lab_v2.py` plays 200 real
seeded sessions per adversary in Chromium and reads the score from the app's
own report.

| Adversary | Model mean /8 | Browser mean /8 | Model P(≥4) | Model P(≥6) |
| --- | --- | --- | --- | --- |
| Random guessing | 2.00 | 2.09 | 11.2% | 0.5% |
| Fixed answer position (first) | 2.00 | 1.99 | 11.3% | 0.4% |
| Fixed answer position (last) | 2.00 | 1.98 | 11.3% | 0.4% |
| Always one stroke direction (right/below) | 3.00 | 2.99 | 26.2% | 0.4% |
| Eliminate displayed symbols | 2.00 | 1.99 | 11.3% | 0.4% |
| Use earlier answers to eliminate | 1.99 | 2.04 | 12.0% | 0.5% |
| Eliminate + recall combined | 2.00 | 1.99 | 11.3% | 0.4% |
| Single surface cue only (one binary feature, coin flip) | 3.00 | — | 34.5% | 3.1% |
| Knows the answer (harness sanity check) | 8.00 | 8.00 | 100% | 100% |

Family breakdown for the fixed-direction adversary: visual 0.48/2, sound
2.00/4, syllable 0.51/2. That 2.00/4 is not an accident of sampling — it is
exact by construction, and it is the whole point of the four-cue bank.

### What the numbers mean

- No non-learned strategy reaches 4/8 often. Random, fixed-position, and
  both elimination strategies sit at 11–12%, which is what 4-of-8 coin flips
  give.
- The one real residual is "single surface cue". A learner who knows only
  that vowel strokes attach at the middle (and nothing about which side is
  which sound) scores 2/4 on sound-to-shape plus coin flips elsewhere, and
  reaches 4/8 about a third of the time. This is a legitimate partial
  understanding, not a shortcut, but it means **4/8 must never be read as
  transfer**. That is why there is no threshold.
- The earlier 48.4% concern about a two-cue combination is gone: with
  abstract glyphs, "same position + side flips" *is* the intended rule, so a
  learner using it has done the visual analogy. It is calibration, not
  evidence of Hangul learning.

### Why the fixed-direction strategy cannot reach 2/2 on a pair

Each session contains all four cues: a and eo (opposite sides of the
vertical axis) and o and u (opposite sides of the horizontal axis). "Always
right" is correct for exactly one of {a, eo}, and "always below" is correct
for exactly one of {o, u}. So any fixed direction totals exactly 2/4, never
4/4. This holds for every session, not just on average, and the browser run
confirms it: 2.00/4 with a per-item rate of exactly 1.0 or 0.0.

---

## 3. Disclosed residual weaknesses

These are real. They are not fixed, because fixing them trades against other
properties.

**P3 cross-item elimination (accepted by the owner).** Y-encode offers 모 마
무 머. Y-decode's answer is 머; its options are meo ma mu mo. A learner who
remembers committing "머" in the encode item can use that memory as one
signal on decode. Measured effect is small: the elimination adversary scores
0.325 on Y-encode and 0.20 on Y-decode against a chance rate of 0.25. The
decode item is *below* chance for the strategy because its option set has no
repeat. Disclosing rather than removing this preserved the ㅁ-only design.

**An option set token like "머" appears in both P3 items.** The four taught
vowels exhaust the possible ㅁ blocks, so any two ㅁ items must share option
material. Accepted.

**The four sound cues yield only two distinct option *sets*.** S-a and S-eo
present the same four vertical placements; S-o and S-u the same four
horizontal ones. Only the correct answer differs. A learner repeats a set
1-in-3 of the time across items. Harmless for elimination (nothing is ever
removed by recall) but worth knowing when reading a session log.

**P1 cannot separate "extracted the rule" from "combined two surface cues".**
With four options there is no way to distinguish them. This is why P1 is
calibration and is scored apart.

**No audio.** a / eo / o / u are presented as romanized text. A learner
without Korean phonology may not know how "eo" sounds. This is a content
dependency, not a bug, and it is why a cold control is required.

**Session length.** Eight items of mixed families is longer than six. At
~20–25 s per item that is roughly three minutes. Unverified on a real phone.

---

## 4. One-shot and neutrality guarantees

- After `Confirm`, every option button is `disabled`; there is no retry path.
- Between items, the only feedback string is `Recorded.` The verifier asserts
  that neither "correct" nor "wrong" appears in the item body at any point.
- No check/submit control exists on P2. The preview is not an answer check.
- Keys live only in the JS closure; the DOM carries `data-choice` identifiers
  on options but no correctness marker (test hook `data-choice` equals the
  option slot id, not the answer).

---

## 5. Verification actually run

```
verify_transfer_lab_v2.py   22/22 checks passed
  - bank is 2/4/2 with cues a,eo,o,u exactly once
  - P1: no option in either item is a glyph already displayed (no
    missing-fourth shortcut); glyph pools disjoint across items;
    query never offered as an option
  - P3: ㅁ only, no ㄴ distractor
  - 240 sessions: all four cues present, 24 distinct cue orders,
    238/240 distinct item orders, key position spans all 4 slots for
    every item and stays within 15–35% per slot
  - same seed reproduces the plan; different seed does not
  - 9 adversaries x 200 sessions each, all inside expected bounds
  - zero page errors across the entire run

shoot_v2_layouts.py         0 layout / leak problems
  - 390x844 and 320x568, every item family
  - confirm button on screen at every step (foot bottom 826/844, 568/568)
  - no horizontal overflow at either size
  - preview text contains no correctness language, no check button present
```

Evidence: `.verify_out/verify_transfer_lab_v2.json`,
`.verify_out/model_baselines_v2.json`, `.verify_out/shots-v2/`.

### What is NOT verified

- No learner has played it. No beginner, no control, no pilot.
- Not tested on a physical phone or with system text enlargement.
- No Korean-language human review of the prompts.
- The `single_surface_cue` adversary is a *model* of partial knowledge, not a
  measured learner distribution.
- Memory use, save/reload behaviour under browser quota pressure, and
  behaviour if `crypto.getRandomValues` is unavailable are unexercised.

---

## 6. Observation protocol for a first supervised session

Per learner, ~10 minutes. Run one learner at a time; do not discuss answers.

**Before**
1. If the learner just used a Vowel Machine, record which method (Rail /
   Three keys). Otherwise select **Cold control**.
2. Leave the seed blank so the session is drawn fresh, and note the seed the
   app records — that is what makes the session reproducible later.
3. Say: "There are eight short puzzles in a mixed order. No scores, no
   timer, and I won't tell you if you're right until the end."

**During (say nothing; write down)**
- Any point where the learner pauses more than 5 s on the abstract shapes.
  That is the moment the analogy either lands or does not.
- On "fix the print": whether they tap one position and confirm, or tap
  two or more to compare prints. Both are recorded automatically, but the
  observer should note *why* they changed ("I compared them", "I wasn't
  sure", "I remembered it").
- Whether they ask what "eo" sounds like. That is the audio gap.
- Whether they reference seeing a similar block earlier in the same session
  (the P3 overlap).

**After, per family (2 minutes each)**
- Abstract shapes: "How did you know what to do?"
- Fix the print: "What told you where the stroke goes?"
- New friend ㅁ: "How did you read that block?"

**Interpretation guardrails**
- Do not treat 8/8 as transfer. The constructs are separate.
- A high abstract-shapes score with low sound-to-shape is the expected
  pattern for a learner who has good visual reasoning but has not learned
  the vowel-sound mapping. That is a useful finding, not a failure.
- 4/8 is at or below what a single-surface-cue learner produces. It carries
  no evidentiary weight.
- Report the three subscores and the four explanations, never a total.

---

## 7. Recommendation before a pilot

Run this build on the owner's phone first, then 3–5 beginners with at least
one cold control. Do not make any claim about learning from this build alone:
eights items in one sitting measures immediate, feedback-free performance.
Retention would need a delayed re-run.
