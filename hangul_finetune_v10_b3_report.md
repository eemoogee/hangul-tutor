# Batch 3 Production/Practice — Coverage Report

Dataset: `hangul_finetune_v10.jsonl` — **380 pairs** = v9 (327) + B3 (53).
B3 = 18 pilot + 35 expansion. This report covers the 35-pair expansion.

## Expansion structure (35 pairs, twin layout)

| Format | Targets | Pairs | Split |
|--------|---------|-------|-------|
| Vowel substitutions | 6 | 12 | 6 wrong + 6 correct |
| Initial consonant substitutions | 4 | 8 | 4 wrong + 4 correct |
| Batchim substitutions | 3 | 6 | 3 wrong + 3 correct |
| Compound-vowel substitutions | 2 | 4 | 2 wrong + 2 correct |
| Production / construction | — | 5 | produce (ungraded) |
| **Total** | | **35** | **15 wrong + 15 correct + 5 produce** |

Grade families are 1:1 (15 wrong / 15 correct) — the Option B twin structure.
The 5 produce pairs keep the "just answer" signal alive so the model does not
learn the inverse rule of *always* grading.

## Minimal pairs (ground-truth targets)

**Vowel** (confusable substitution):
- ㅏ↔ㅓ → 하/허, 라/러
- ㅗ↔ㅜ → 호/후, 소/수
- ㅐ↔ㅔ → 매/메, 내/네

**Initial consonant** (representative 3-way contrast, different vowel frames):
- ㄱ vs ㅋ (plain / aspirated) → 가/카
- ㄷ vs ㄸ (plain / tense) → 도/또
- ㅂ vs ㅃ (plain / tense) → 부/뿌
- ㅅ vs ㅆ (plain / tense) → 시/씨

**Batchim** (vary written consonant within a sound group — spelling vs final sound):
- /t/ group → 곧 vs 곳 (ㄷ vs ㅅ)
- /p/ group → 집 vs 짚 (ㅂ vs ㅍ)
- /t/ group → 낮 vs 낯 (ㅈ vs ㅊ)

**Compound vowel** (whole-vowel confusion, via `JAMO.confusable`):
- ㅘ↔ㅝ → 과/궈
- ㅙ↔ㅞ → 돼/뒈

## Gap notes

- **/k/ batchim group NOT covered in the expansion.** ㄱ vs ㄲ has no real-word
  minimal pair that is not confounded — 깎 = ㄲ+ㅏ+ㄲ carries a tense ㄲ *initial*
  as well as the ㄲ batchim, so it differs from 각 by two letters, not one. A
  two-syllable example (부엌) would break the syllable-level format. **ACCEPTED**
  — /k/ batchim is covered by pilot pair 12 (박 = ㅂ+ㅏ+ㄱ, ㄱ batchim → /k/).
- **Compound-vowel component splits are now code-verified** via
  `COMPOUND_COMPONENTS` (added to `hangul_quiz_engine.py`). NFD confirmed Unicode
  keeps compound jungseong atomic (`ᅪ`, `ᅫ`…), so the map is the only
  component-level source.

## Verification

- **73/73 ground-truth facts pass** (`_compose_syllable`, `_decompose_syllable`,
  `COMPOUND_COMPONENTS`, `_batchim_sound`, `JAMO`).
- **0 duplicate questions** (within B3 and against v9).
- The generator's verifier caught and fixed **one hand-derivation error** during
  authoring (깎 vs 각 — the /k/ pair above), demonstrating the no-guess pipeline.
