# Hangul tutor — eval suite

Quality gate for every future training run. Three probes that measure three
different things the earlier ad-hoc sweeps kept conflating:

| Script | Measures | Question count |
|---|---|---|
| `curriculum_probe.py` | **Knowledge coverage** — consonants, vowels, batchim, syllable structure, stroke order, romanization | 22 |
| `pedagogy_probe.py` | **Tutoring behavior** — correction handling, mnemonics, explanation depth, follow-up/context retention, encouragement/learner tone | 10 |
| `production_probe.py` | **Production grading** — rejects wrong learner attempts, confirms correct ones (B3 anti-sycophancy check) | 12 (×2 runs) |

Both serve the target model in **non-thinking mode** (raw empty-think-block
prompt, temp 0) so results reflect the weights, not the Qwen3 chain-of-thought
bug. See the docstrings for the exact serving format.

## Running

```bash
# defaults to hf.co/eemoogee/hangul-expert-qwen3-8b on localhost:11434
python evals/curriculum_probe.py
python evals/pedagogy_probe.py
python evals/production_probe.py

# override model / endpoint
HANGUL_MODEL=hangul-expert:latest python evals/curriculum_probe.py
HANGUL_MODEL=my-model OLLAMA_API=http://localhost:11434 python evals/pedagogy_probe.py
```

## Grading

- `curriculum_probe.py` — grade each answer against the printed `EXPECTED`
  string. Track clean / partial / wrong per area.
- `pedagogy_probe.py` — for each response note whether it *corrects /
  explains / encourages* vs just *states a fact*, plus the tone-marker scan and
  think-bleed flag. `[HANG/TIMEOUT]` is itself a signal (OOD input loop).
- `production_probe.py` — auto-classifies each verdict EXACT / PARTIAL / WRONG
  and runs every question twice (run-to-run drift is a red flag). WRONG on a
  wrong-attempt = sycophancy regression; WRONG on a correct-attempt = inverse
  rule. Baseline is PENDING — record after the v10 retrain.

## Baseline — v8 Kaggle model (`hf.co/eemoogee/hangul-expert-qwen3-8b`)

Recorded **2026-08-30**, before any v9 correction-pair training.

**Curriculum (22): 12 clean / 5 partial / 5 wrong, zero think-bleed.**

Clean: ㄱ ㄷ ㅂ ㅅ ㅆ ㅗ ㅜ ㅡ, batchim def, 받침 def, ㄹ→r/l, 한→han.
Partial: ㄲ (tensed≈"aspirated"), ㅓ (sound right, no "eo" map), syllable parts &
  how-written (structure right, terminology bleed), ㄱ stroke (missing horizontal).
Wrong: ㅐ ("a in father"), ㅘ ("yah"), ㄱ-as-batchim ("aspirated g"),
  7-sound count (answered 24), ㅁ stroke (said 2).

**Pedagogy (10):**

- **Correction — FAILS.** Model *agrees* with wrong premises ("Yes, you're
  absolutely right!" on ㅐ="father"; "Your teacher is correct" on batchim=24
  sounds). Sycophancy; no correction examples in the v8 training set.
- **Mnemonic — structure yes, content no.** Visual cues volunteered, but ㅡ
  mnemonic anchored to "eu in 'soon'/'blue'" (that's the /oo/ sound).
- **Why — confident fabrication.** "7 pure + 14 nasalized/aspirated" invented
  for the 7-sound question; ㄹ r/l rule correct but example words hallucinated.
- **Follow-up — fragile.** Multi-turn worked once (vowels→hardest) but HUNG on
  batchim→example-word (OOD pronunciation + multi-turn loop).
- **Encouragement — strong.** Both questions got warm, structured, actionable
  responses ("You're not doing anything wrong… 🌟"). Tutoring affect survived.

## What this is for

After each retrain, re-run both probes and diff against this baseline. A v9
(correction-pair) run should move the **correction** dimension from "fails" to
"corrects" and lift the curriculum **wrong** rows (ㅐ, ㅘ, 7-sound, ㄱ-batchim,
ㅁ-stroke) to clean.
