# Task: Sejong F9–F10 — a real final check, and one Jeong line per answer

**For:** Codex · **Written:** 2026-10-16 · **Verifier:** Claude (in the owner's session)
**Builds on:** the F1–F8 playtest fixes (already in `master`) **and** `docs/tasks/2026-10-16_sejong-before-after.md`. That task also changes the end of Batch 1, so start only after it is merged into `master`, and build on top of it.

## Why

Batch 1's reading check is meant to prove the learner can read blocks they have **never practised**. Today every consonant-vowel block is practised, so `make_reading_check` falls back to two-block sequences of practised blocks (seen in testing: 도노, 버다, 마바, 다모). That measures repetition, not composition.

Holding back three blocks from all practice fixes this. Tested against the real `reading_check.py` (seeds 1–5): with 누, 머, 버 held back and 누 answered once as a construction card, `make_reading_check` picks exactly **머 and 버** as its two new combinations every time. **No change to `reading_check.py` or the engine is needed.**

Why these three: every Batch 1 block that appears in a word is needed for the decode phase, which leaves only 누, 더, 머, 버 unused. Holding back all four would leave ㅓ practised in a single block (너), and F7 could not give 너 a same-vowel distractor. With 더 kept, ㅓ is practised in 너 and 더, and every build card still gets both distractor types.

## Ground rules

- Own worktree: `git worktree add ../hangul-tutor-f9 -b sejong-held-back master`.
- Change `sejong_flow.py`, `scripts/_verify_sejong_flow.py` and `docs/sejong-events.md`. In `data/sejong.json`, add **only** the one key below. Don't touch `sejong_cli.py`, the engine or `reading_check.py`; if something seems to need them, stop and report.

## Changes

1. **Content:** add `"held_back": ["누", "머", "버"]` to Batch 1 in `data/sejong.json`. Batch 0 has none (it only has 4 blocks).
2. **Practice blocks** = known blocks minus every `held_back` block of the current and earlier batches. Use practice blocks everywhere a block can appear before Batch 1's check: the custom lesson's `practice_syllables` and `mastery_syllables`, the build pool (F6 rule → Batch 1 build = exactly 너 더 두 마 모 무 바 보 부), build distractors (F7 rule), predict choices, and any hint or narrator text.
3. **Batch 1's final check has two parts:**
   - **Construction first:** one `question` card, `context: "check"`, `mode: "build_syllable"`, `input: "choice"`, `parts` shown, target = one held-back block picked with the flow RNG. Choices: the target, a same-consonant and a same-vowel distractor, and one more, with all distractors from practice blocks. No hint and no `result.line` (check rules). Grade it through `quiz.answer()`; that records the block as seen, which keeps it out of the reading check.
   - **Then the existing reading check** (`make_reading_check`, 5 prompts, pass 4). Its two new combinations will be the other two held-back blocks.
   - The pass rule is unchanged: reading 4 of 5. Construction is recorded, not required.
4. **Score:** Batch 1's check `score` gets an optional `construction` field, `{"target": "누", "correct": true}`. Update the contract's `score` section, and note that Batch 1's check may open with one `build_syllable` card.
5. **First-attempt record:** in the flow's per-batch check results, keep the **first** attempt separately, as `{"construction": bool, "new_read": {"머": true, "버": false}}`. A retry after check practice is no longer new reading, so it doesn't overwrite this record. This is the playtest's evidence.
6. Batch 0's check is unchanged.
7. `export_state()` / `from_state()` must still replay identically. Save the chosen construction block.

## F10 — one Jeong line per answer

**Problem (measured on the F1–F8 code):** on decode answers, the result's comment (`lines.correct` or `lines.streak`) is followed by the word's payoff line in `word_read`, so Jeong speaks twice for one answer. This happened 156 times over 30 always-correct runs (about 5 per run). In every run, the first word read lands on streak 5: "Five in a row." then "You read it without me."

**Required:** at most one Jeong line per answer. Priority: the word's payoff line (`first_word_read`, `fool_word`, `dodo_word` or the word's `first_read_line`) > streak line > correct line. When a `word_read` carries a line, the `result` carries no `line`. A streak line displaced this way is dropped (not moved to the next answer); the streak count itself is unchanged. For F3's "never two correct answers in a row" rule, a word line counts as Jeong having spoken. When `word_read` has no line, the F3/F4 rules apply as now.

## Tests to add in `scripts/_verify_sejong_flow.py`

1. Always-correct runs, seeds 1–10: no event before Batch 1's `check` stage contains 누, 머 or 버 in any string field (display, choices, parts, predict, reveal, word_read, narrator text).
2. Batch 1 build targets = exactly the 9 blocks above.
3. Every Batch 1 build card has a same-consonant and a same-vowel distractor (F7 still holds), and none of its choices is held back.
4. Batch 1's check opens with one construction card on a held-back block; the reading check's `transfer_targets` = the other two held-back blocks; the `score` carries `construction`.
5. Construction wrong + reading 4/5 → passes. Construction right + reading 3/5 → the existing fail → practice → retry path. The first-attempt record keeps the first results after the retry.
6. `export_state()` mid-check → `from_state()` → same answers → same events.
7. F10: over 30 always-correct runs, no single `submit()` list has both a `result.line` and a `word_read.line`, and the run's first `word_read` still carries `lines.first_word_read`.
8. All existing checks pass (list any you had to change, and why).

## Later (not this task)

Any block board or 16-block grid in the web version must not show 누, 머 or 버 before Batch 1's check: hide them, or show them as "?" until the check reveals them.

## Done when (paste evidence)

- [ ] Full output of `python scripts/_verify_sejong_flow.py` and every other `scripts/_verify_*.py`.
- [ ] A seed-1 always-correct transcript (JSONL) regenerated.
- [ ] `git diff --stat`, plus the full diff of `sejong_flow.py`, `docs/sejong-events.md` and `data/sejong.json`.
- [ ] Anything you couldn't follow exactly, and why.

Commit on `sejong-held-back`; don't push.
