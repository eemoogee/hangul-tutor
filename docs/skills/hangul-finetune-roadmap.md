---
name: hangul-finetune-roadmap
description: "Forward roadmap for the Hangul fine-tuning dataset — production/practice layer, question variety, and per-batch eval hooks."
---

# Hangul Fine-tuning Roadmap (post-v10)

Current position: `hangul_finetune_v10.jsonl` = **380 pairs** (v9 327 + B3 53: 18 pilot + 35 expansion).
Through v9, the dataset was **declarative/conceptual Q→A** — the model only ever learned to *emit facts*, never
to *judge a learner's output*, even though the app runs production through five quiz modes
(`spell`, `build_syllable`, `missing_vowel`, `batchim_challenge`, `confusion_drill`). B3 (v10) added the
production/practice layer to close that gap.

Guiding rule: every batch is defined by **purpose → training-representation goal → eval hook**. No batch
means "add more pairs about X" without a probe that verifies the gap actually closed. This is the lesson
of v3→v6: coverage churn came from batches scoped by topic, not by a verifiable gap.

---

## Roadmap

| Batch | Purpose | Training-representation goal | Eval hook |
|-------|---------|------------------------------|-----------|
| **3** | Production/practice — teach the model to evaluate a learner's written/produced attempt | Graded feedback pairs (produce + grade), deterministic compose/decompose targets | New production probe: wrong attempt must be rejected (not rubber-stamped), error named, target given |
| **4** | Aspirated/tense factual grounding — supply the letter knowledge the correction layer lacks | Declarative base/aspirated/tense contrast pairs (45), romanization derived from JAMO | Extend production probe: 카/가, 따/다 must be rejected with aspiration/tension named |
| **5** | Batchim (spelling-vs-sound) + phonological rules (ㄴ-assimilation, tensification, ㄹ-liaison) | Batchim grounding + wrong-batchim production pairs; rule pairs keyed on native-script forms | Probe on novel batchim + rule-application examples |
| **6+** | TBD | Driven by the curriculum/pedagogy probe diff after the 8B retrain | Regression gate (`evals/`) |

Batch 5 (batchim + phonological rules) is deferred until the B4 aspirated/tense grounding is in and
re-probed — batchim was moved out of B4 into B5 this session (the v10 probe showed 곧's batchim
rubber-stamped), and B5 also waits on B3's production-answer structure proving clean.

---

# Batch 3 — Production / Practice

**Goal:** close the production gap. Train the model to (a) *produce* the correct Hangul for a
romanization / jamo prompt, and (b) *grade* a learner's attempt — agree on a correct attempt,
explicitly reject a wrong one, name the specific jamo error, and give the correction.

## Ground-truth sources (verified — use exactly these)

- `hangul_quiz_engine.py`
    - `_compose_syllable(cho, jung, jong="")` (L813) — compose jamo → syllable block (targets)
    - `_decompose_syllable(syllable)` (L873) — decompose block → `(cho, jung, jong)` (attempt checking)
    - `_compose_bare_vowel(s)` (L767) — bare vowel + silent ㅇ placeholder (ㅏ → 아)
    - `_batchim_sound(jong)` (L894) — final-consonant sound mapping (7-sound rule)
- `hangul_flash.py` — `JAMO` dict (L32). Keys: `roman` (list), `name`, `set`, `confusable` (list).
    - Authoritative source for ROMANIZATION and CONFUSION pairs (the wrong-attempt generator).
- `data/curriculum.json`
    - `lessons[].practice_syllables` / `example_words` → target syllables and words
    - `confusion_pairs_global` → common-error pair list (overlaps `JAMO` confusable)
- DO NOT use `hangul_models.py` for data — model-routing only.

## Formats (five, one per production quiz mode)

Each format has **two prompt families**:

- **(A) Produce** — learner asks how to write/say something; assistant produces the answer **and** shows
  the jamo breakdown (so the model learns to *emit* Hangul with its structure, not just a bare glyph).
- **(B) Grade** — learner presents an attempt (correct or wrong); assistant grades it (structure below).

### 1. `spell` — romanization → Hangul
- (A) "How do I write 'ga' in Hangul?" → "Write **가** — it's ㄱ + ㅏ."
- (B) "I wrote 가 for 'ga'. Is that right?" → correct / wrong variants.

### 2. `build_syllable` — jamo → block
- (A) "Combine ㄱ and ㅏ into one syllable." → "**가**."
- (B) "Is 가 the right way to combine ㄱ and ㅏ?" → correct / wrong variants.

### 3. `missing_vowel` / `missing_jamo` — fill the gap
- (A) "The vowel is missing from ㅅ_ㄹ to spell 'seol'. What goes in the middle?" → "ㅓ."
- (B) graded variants on a filled-in attempt.

### 4. `batchim_challenge` — fill the final consonant
- (A) "Which final consonant completes 'ma_' to spell 'man'?" → "ㄴ."
- (B) graded variants, including wrong-batchim attempts (see wrong-attempt rules).

### 5. `confusion_drill` / recognition→production bridge — "I can read it, how do I write it?"
- (A) "I can read 가, but how do I write it out?" → jamo sequence → composed block.
- (B) graded variants on confusable pairs (ㅓ↔ㅗ, ㅐ↔ㅔ, ㅅ↔ㅆ …).

> **Keyboard caveat:** "how do I *type* it" (2-set keyboard key mapping) is a NEW fact domain not present
> in any current source. Scope B3's recognition→production to *writing/spelling in Hangul* (which the app's
> `spell` mode already does). Real keyboard-layout mapping is DEFERRED to a later batch, behind a verified source.

## Grade-answer structure (anti-sycophancy — non-negotiable)

Every grade answer must follow this shape. This is the load-bearing fix: the v9 correction pairs stopped
the model rubber-stamping *facts*; grade pairs stop it rubber-stamping *attempts*.

- **Correct attempt** → confirm + restate structure:
  "Yes — 가 is correct: ㄱ + ㅏ."
- **Wrong attempt** → THREE mandatory beats:
  1. explicit non-agreement (lead with "Not quite", "Close, but no", "Almost — one jamo is off"),
  2. name the specific jamo error ("you used ㅗ, which makes 'go'"),
  3. give the correct form ("for 'ga' you want ㅏ: 가 = ㄱ + ㅏ").

A wrong attempt that gets "yes, you're right" is the exact sycophancy regression this batch must not
reintroduce — it is the primary eval failure mode.

## Wrong-attempt generation (deterministic — plausible errors only)

Wrong attempts are generated by substituting a **confusable jamo** into the target, never random noise:

- Vowel errors → substitute `JAMO[target_vowel]["confusable"]` (ㅏ→ㅓ/ㅑ, ㅓ→ㅏ/ㅕ, ㅐ→ㅔ …).
- Consonant errors → substitute `JAMO[target_consonant]["confusable"]` (ㄱ→ㅋ/ㄲ, ㄷ→ㄴ/ㅌ/ㄸ …).
- Batchim errors → substitute a different letter from the same `_batchim_sound` group (7-sound rule), so the
  wrong attempt is *plausible by sound but wrong by spelling* — matching the real error learners make
  (the "more than one letter makes this sound" case already in `_batchim_question`'s hint logic).

This guarantees every "wrong" attempt maps 1:1 to a deterministically-correct correction, and every
correction is checkable against `_compose_syllable` / `_decompose_syllable`.

## Coverage target

Cover every format above with at least one (A)-produce and one (B)-grade pair, where the grade family
carries at least one correct and one wrong variant. Target ≈ **50–60 pairs**, final count derived at
generation time and reported in the coverage report (as v1's 145 was). Coverage priorities:

- 14 basic consonants + 10 basic vowels → spell/build produce pairs
- 11 compound vowels (ㅐ ㅒ ㅔ ㅖ ㅘ ㅙ ㅚ ㅝ ㅞ ㅟ ㅢ) → build pairs (the OOD gap from the last probe)
- 5 tense consonants (ㄲ ㄸ ㅃ ㅆ ㅉ) → at least one grade pair each (they are frequent confusables)
- wrong-vowel + wrong-batchim grade pairs → at least one per `confusion_pairs_global` entry

## Constraints

- Every target and every correction must come from `_compose_syllable` / `_decompose_syllable` /
  `_compose_bare_vowel` / `_batchim_sound` — no free-form Hangul invention.
- Romanization answers must match `JAMO[letter]["roman"]`; for ㅇ use the position rule (silent at start,
  "ng" at end), never a naive `" or ".join` of `["ng","silent"]`.
- Wrong attempts are confusable substitutions only — never random jamo.
- Grade answers are English, warm, and lead with the non-agreement beat on wrong attempts.
- Em dash immediately before a Hangul glyph is disallowed (repo-wide rule) — use a semicolon or restructure
  ("…spell 'seol'; the middle vowel is ㅓ").

## Output

1. `hangul_finetune_v10.jsonl` — v9 (327) + B3 production pairs.
2. `hangul_finetune_v10_b3_report.md` — pairs per format, per letter, wrong-attempt coverage, and the
   final derived count.

## Eval hook

Extend `evals/` with a **production probe**: present N grade prompts (mix of correct and wrong attempts)
through the no-RAG serving path (empty-think-block template, temp 0, per-question try/except — see
`references/qwen3-serving-and-probes.md`). Classify each answer:

- **EXACT** — correct verdict + jamo error named + correct target
- **PARTIAL** — right verdict, simplified correction (this 1.5B's normal baseline)
- **WRONG** — agrees with a wrong attempt (sycophancy regression) or names the wrong jamo

Only WRONG counts as failure. Run twice (run-to-run variance is itself a red flag — v6 lesson).

---

# Batch 4 — Aspirated/tense factual grounding (declarative)

> **RE-SCOPED (this session).** The original B4 spec was "common learner errors"
> (wrong-vowel ㅓ↔ㅗ/ㅐ↔ㅔ + wrong-batchim, as production attempts). The v10 retrain
> eval re-scoped it: production shows the correction behavior is now
> **knowledge-gated** — the model rejects wrong attempts it can verify (허→하, 무→모)
> but rubber-stamps the ones where its own letter knowledge is weak (카≠가, 따≠다,
> 곧's batchim). Correction behavior trained in v9/v10, but it can't fire without
> the underlying factual grounding. So B4 = **aspirated/tense factual grounding**
> only. **Batchim is moved to B5** (the 곧's-batchim failure), and wrong-vowel is
> already covered by B3's grade pairs (허→하, 무→모 now verify correctly).

## Purpose

Teach the **base / aspirated / tense** three-way consonant distinction as plain
declarative Q→A facts, so the model has the letter knowledge to *verify* a
learner's attempt before grading it. This is the factual floor the v10 grade
layer was missing.

## Training-representation goal

Dense coverage of the aspirated/tense contrast for the three consonant groups
that have all three members (base, aspirated, tense): **ㄱ/ㅋ/ㄲ**, **ㄷ/ㅌ/ㄸ**,
**ㅂ/ㅍ/ㅃ**. The model must be able to answer "what's the difference between ㄱ and
ㅋ" and "which of these is tense" without RAG, so the grade layer can catch
카-for-'ga' and 따-for-'da'.

## Pair formats (declarative, 15 per group × 3 groups = 45)

Each group, six question families (base/aspirated/tense contrasts + identification):

- base vs aspirated — 3 phrasings
- base vs tense — 3 phrasings
- aspirated vs tense — 3 phrasings
- three-way comparison — 3 phrasings
- identification (which is base / aspirated / tense) — 3 pairs

## Ground-truth sources (verified — use exactly these)

- `hangul_flash.py` — `JAMO` dict is the ROMANIZATION ground truth:
  `ㄲ→["kk"]`, `ㄸ→["tt"]`, `ㅃ→["pp"]`, `ㅆ→["ss"]`, `ㅉ→["jj"]`.
  - The generator DERIVES romanization from `JAMO` (`JAMO[letter]["roman"][0]`),
    never hardcodes it — the `gg/dd/bb` mistake this session came from a
    hand-written draft that didn't check against `JAMO`.
- `generate_dataset_b4.py` runs a **verify-before-emit** pass: every emitted
  romanization claim must equal the `JAMO` value; any mismatch aborts without
  writing the file.

## Constraints

- Romanization claims must match `JAMO[letter]["roman"]` exactly — derived, not hardcoded.
- Em dash immediately before a Hangul glyph is disallowed (repo-wide rule).
- Plain ChatML, user+assistant only, no system message (all versions).

## Coverage target

**45 pairs** = 15 × 3 groups (ㄱ/ㅋ/ㄲ, ㄷ/ㅌ/ㄸ, ㅂ/ㅍ/ㅃ).

## Output

1. `hangul_finetune_v10_b4.jsonl` — 45 aspirated/tense factual-grounding pairs.
2. `generate_dataset_b4.py` — generator (derive-from-JAMO + verify-before-emit).

## Eval hook

Extend `evals/production_probe.py` with the specific failures the v10 eval named:
카-for-'ga' (aspirated) and 따-for-'da' (tense). The B4 signal is whether the model
now *rejects* these (its letter knowledge is grounded) rather than rubber-stamping.
Classify EXACT/PARTIAL/WRONG as before; WRONG on 카/따 = the grounding gap persisting.
