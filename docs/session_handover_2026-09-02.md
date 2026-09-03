# Hangul tutor — session handover (2026-09-02)

Picking up the fine-tuning experiment thread. This document covers what was
done today and exactly what to do next. Read `docs/decisions.md` for the
full reasoning behind any decision referenced here.

---

## Repo state

- Repo: `C:\Users\jefej\Documents\hangul-tutor`
- HEAD: `f552f0d` — working tree clean
- Live model: Qwen3-8B q4_k_m, `hf.co/eemoogee/hangul-expert-qwen3-8b`,
  pulled to local Ollama
- Dataset: `hangul_finetune_v11.jsonl`, 425 pairs (380 v10 + 45 B4
  aspirated/tense)
- Training script: `train_hangul_kaggle.py`, pointed at v11 dataset,
  WARMUP_STEPS=11, 2 epochs, T4 x2 (Kaggle)

---

## What was done this session

### Eval infrastructure (all committed)

1. **`production_probe.py` instrumented** (commits 5a67835, 6d43120,
   86bc6f7, d164912):
   - `classify()` now returns `(verdict, details)` tuple — adds `stance`,
     `named_wrong_component`, `gives_fix`, `sycophantic_accept` fields
   - `main()` writes `production_probe_raw.jsonl` (one record per run per
     item, 24 lines total for 12 items × 2 runs)
   - `"almost"` removed from DISAGREE — model uses it as praise, not
     rejection; was causing false-positive inverse-rule verdicts
   - `production_probe_raw.jsonl` added to `.gitignore`

2. **v11 inverse=2 confirmed classifier noise** — both instances were
   the "almost"-as-praise false positive; annotated in `evals/README.md`
   (commit d164912). v10/v11 inverse counts are upper bounds only — no
   raw transcripts exist to recheck.

3. **`docs/decisions.md` created** (commit 229f27b, with minor follow-up
   fixes through f552f0d) — running log of key decisions, failed
   experiments, and lessons. This is the new authoritative record of *why*
   decisions were made. Read it before designing any new data or training
   intervention.

4. **`hangul_finetune_gaps.md` deleted** (was stale v2 artifact, 145 pairs;
   canonical version regenerates from dataset generator).

---

## The immediate next action: epoch experiment

**What:** Retrain on the existing v11 dataset (425 pairs, no changes),
varying epochs only. Same hyperparameters, same probe, same Kaggle setup.

**Why this first:** It's the cheapest possible controlled test. If correction
behavior improves with more epochs, the problem is undertraining/setup, not
data — which changes the entire B5 data-design question. Run this before
writing any new pairs.

**Suggested epoch values to test:** 3 epochs (and optionally 4), compared
against the current 2-epoch baseline.

**How to run:**
- In `train_hangul_kaggle.py`, change `NUM_EPOCHS` (or equivalent) to 3
- Use Kaggle web UI "Save and Run All" — CLI push is unreliable for GPU
  allocation
- Dataset path on Kaggle: `/kaggle/input/<slug>/<filename>` (short form
  only — the longer `datasets/eemoogee/` path causes FileNotFoundError)
- After training completes, pull the new GGUF to local Ollama and run
  `python evals/production_probe.py`

**What to evaluate:**

Run the full probe and analyze using the **4-way capability vector** (not
just the sycophancy count):

| Metric | What it tells you |
|---|---|
| accept-correct | Does it recognize valid learner production? |
| reject-wrong | Does correction behavior fire at all? |
| named-wrong-component | Does it know *why* something is wrong? |
| sycophantic-accept | Does it override knowledge under confident learner framing? |

The JSONL output (`production_probe_raw.jsonl`) now captures all four
directly. Use this analysis snippet:

```python
import json
rows = [json.loads(l) for l in open("production_probe_raw.jsonl", encoding="utf-8")]
accept_correct = sum(1 for r in rows if r["attempt_type"] == "correct" and r["stance"] == "accept")
reject_wrong   = sum(1 for r in rows if r["attempt_type"] == "wrong"   and r["stance"] == "reject")
named          = sum(1 for r in rows if r["attempt_type"] == "wrong"   and r["stance"] == "reject" and r["named_wrong_component"])
sycophantic    = sum(1 for r in rows if r["sycophantic_accept"])
print(f"accept-correct: {accept_correct}")
print(f"reject-wrong: {reject_wrong}")
print(f"reject-wrong AND named component: {named}")
print(f"sycophantic accepts: {sycophantic}")
```

**Also run a regression suite** covering basic Hangul facts, batchim
knowledge, B4 consonant distinctions (ㄱ/ㅋ/ㄲ, ㄷ/ㅌ/ㄸ, ㅂ/ㅍ/ㅃ),
and correct production attempts. Precedent: v6 WeightedRandomSampler
improved batchim while degrading letter facts — any epoch change that
improves sycophancy rejection must be checked for regression elsewhere
before it's called stable.

---

## B5 experiment sequence (after epoch experiment)

Regardless of epoch result, B5 has four factual gaps to close in parallel
data work:

1. **7-sound batchim rule** — model said "21 distinct sounds" (correct: 7)
2. **ㅘ pronunciation** — model said "yah like yacht" (correct: "wa")
3. **Tense vs aspirated terminology** — model says "tense, aspirated"
   conflating two distinct categories; tense ≠ aspirated
4. **겹받침 (double batchim)** — concept never trained; model currently
   says "zero or one batchim" which is wrong

These are straightforward data fixes and can be designed independently of
the sycophancy experiment sequence.

**Full sycophancy experiment sequence:**

1. Epoch experiment (running now / next)
2. If flat: scaling curve analysis — B3→B4→v11 using 4-way capability
   vector. Treat as observational (B4 changed factual representation AND
   correction-pair volume — not a clean isolation). Stated correctly as:
   "across successive datasets incorporating additional correction examples
   and targeted factual grounding, sycophantic-accept behavior remained
   unchanged."
3. If learnable-but-weak: ratio/oversampling experiment targeting
   correction behavior specifically. v6 batchim oversampling result does
   NOT generalize as prior evidence against this.
4. If all flat: document as "strong evidence of a capability boundary
   under the tested 8B/QLoRA regime" — NOT "wall substantially confirmed."
   Distinction: the training recipe failed robustly ≠ no possible QLoRA
   configuration on Qwen3-8B could learn it.

---

## Key classifier warnings (don't forget these)

- `stance == "reject"` is NOT a clean "true inverse-rule regression" proxy
  — it inherits the same DISAGREE/AGREE substring matching. A `stance ==
  "reject"` verdict on a correct attempt could still be a trigger-word
  false positive. Spot-check `model_raw_response` text when analyzing
  inverse counts.
- DISAGREE/AGREE lists need periodic review as model phrasing patterns
  become known. Don't just add markers — check whether the model uses the
  same word in a confirming context.
- Inverse counts from v10 and v11 are upper bounds only. Don't use them
  as clean trend-line data.

---

## Documentation update process

- `evals/README.md` — update after every Kaggle run (new baseline)
- `docs/decisions.md` — update when any experiment produces a new finding
  or reverses a prior decision; trigger is "experiment concluded," not
  "model retrained"
- `docs/skills/hangul-finetune-roadmap.md` — update when batch plan changes
- Start each new session by checking whether the last experiment's conclusion
  made it into `docs/decisions.md` before designing the next intervention

---

## Commit history reference (today)

| Hash | Description |
|---|---|
| 5a67835 | feat(evals): production_probe instrumentation |
| 6d43120 | fix(evals): drop "almost" from DISAGREE |
| 86bc6f7 | chore: gitignore production_probe_raw.jsonl |
| d164912 | docs(evals): note v11 inverse=2 confirmed classifier noise |
| 229f27b | docs: add decisions and lessons log (initial population) |
| cae04dc | docs(decisions): fix 10/6 notation and hyphen artifact |
| e71cf2d | docs(decisions): fix nested parens in sycophancy metric notation |
| f552f0d | docs(decisions): reorder sycophancy metric clause for readability |
