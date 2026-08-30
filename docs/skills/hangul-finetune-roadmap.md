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
| **4** | Common errors / misconceptions | Wrong-vowel (ㅓ↔ㅗ, ㅐ↔ㅔ) and wrong-batchim pairs as *failed production attempts* (not belief-corrections) | Extend B3 probe: error must be diagnosed at the jamo level |
| **5** | Phonological rules (ㄴ-assimilation, tensification, ㄹ-liaison) | Rule pairs keyed on native-script forms (받침 lesson precedent: key on the Korean, not romanization) | Probe on novel rule-application examples |
| **6+** | TBD | Driven by the curriculum/pedagogy probe diff after the 8B retrain | Regression gate (`evals/`) |

Batch 5 is deferred until B3 proves the production-answer structure trains cleanly — a new answer
shape (evaluate → correct) is higher-risk than another fact layer, so it goes first and alone.

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

# Batch 4 — Common learner errors (production)

> **GATED.** B4 pair generation is gated on the B3 retrain eval diff. If the B3
> production probe shows clean grading (no sycophancy regression; EXACT/PARTIAL on
> wrong attempts), B4 proceeds. Otherwise B4 is deferred and re-scoped — do not
> generate B4 pairs until that diff is reviewed.

## Purpose

Deepen the model's diagnosis of the **highest-frequency learner errors** — the
wrong-vowel and wrong-batchim mistakes learners actually make — represented as
**failed production attempts** ("I wrote 메 for 'mae'"), NOT as belief-corrections
("I think ㅐ sounds like 'a in father'", already covered by the v9 correction pairs).

## Training-representation goal

Dense, varied coverage of the specific error classes so the model reliably
diagnoses *these* errors at the jamo level. This builds **depth** on B3's general
grading capability, concentrated on the two errors that dominate real learner
output: **wrong vowel** (ㅓ↔ㅗ, ㅐ↔ㅔ) and **wrong batchim** (spelling vs final sound).

## Pair formats (twin structure, as B3)

Each target = one wrong + one correct attempt (the B3 Option-B twin). Formats:

- **Wrong-vowel** — ㅓ↔ㅗ and ㅐ↔ㅔ, across varied consonant frames and in
  batchim-bearing syllables (where the vowel confusion is most audible):
  - "I wrote 메 for 'mae'. Is that right?" → reject, name ㅔ, give 매.
- **Wrong-batchim** — the spelling-vs-sound error: two letters that make the same
  final sound, learner wrote the wrong one:
  - "I tried to write 곧 and used ㅅ as the batchim. Is that right?" → reject, give 곧.
- **Misconception-as-production** (optional tail) — a learner belief that surfaces
  as a wrong spelling. Keep it as a production attempt, never a
  "what does X sound like" question (that is v9's territory).

Same ground-truth sources as B3: `_compose_syllable` / `_decompose_syllable` /
`JAMO` / `COMPOUND_COMPONENTS` / `_batchim_sound`.

## Graded-answer structure

Identical to B3 (three-beat): lead with explicit non-agreement → name the jamo
error → give the fix. Correct attempts confirm in one line. WRONG on a wrong
attempt = sycophancy regression — the same primary gate as B3.

## Wrong-attempt generation rule

Identical to B3 — confusable substitution only, never random jamo:
- vowel → `JAMO[vowel]["confusable"]` (ㅓ↔ㅗ, ㅐ↔ㅔ …)
- batchim → a different letter from the same `_batchim_sound` group (7-sound rule),
  so the wrong attempt is *plausible by sound, wrong by spelling*.
Every correction must be checkable against `_compose_syllable` / `_decompose_syllable`.

## Coverage target

≈ **40–50 pairs**, derived at generation time:
- ㅓ↔ㅗ and ㅐ↔ㅔ — the two dominant wrong-vowel confusions, ≥3 consonant frames each
  (including batchim contexts)
- wrong-batchim — each multi-letter sound group (ㄱ/ㄲ/ㅋ→k, ㄷ/ㅅ/ㅆ/ㅈ/ㅊ/ㅌ→t, ㅂ/ㅍ→p),
  using the clean minimal-pair pattern (곧/곳, 집/짚, 낮/낯)
- note: /k/ batchim has no clean single-syllable minimal pair (the 깎/각 confound —
  깎 = ㄲ+ㅏ+ㄲ carries a tense ㄲ initial too). Reuse the B3 accepted gap; do not force
  a two-syllable example.

## Eval hook

Extend `evals/production_probe.py` with B4-specific items (the specific common-error
pairs: ㅓ↔ㅗ, ㅐ↔ㅔ, wrong-batchim) added to the existing wrong/correct mix. Classify
EXACT/PARTIAL/WRONG as before. The B4 signal is whether the model diagnoses the
*specific* common error (ㅓ vs ㅗ, ㅐ vs ㅔ, wrong-batchim spelling), not just "any"
rejection.
