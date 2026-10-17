# Task: replace the baseline/post-test with a one-word before/after

**For:** Codex · **Written:** 2026-10-16 · **Verifier:** Claude (in the owner's session)
**Why:** in playtest, opening with 8 guesses at unseen letters felt like failing before learning anything. The owner chose to replace it with one unscored "before" word that returns, typed, just before Victory 1. Purpose: make progress visible, not to test or diagnose.

## Ground rules

- Base on current `master` **after** `sejong-playtest-fixes` is merged and the owner's latest `data/sejong.json` is committed (it contains the new lines below). Own worktree: `git worktree add ../hangul-tutor-before -b sejong-before-after`.
- Change `sejong_flow.py`, `scripts/_verify_sejong_flow.py`, `docs/sejong-events.md`. Touch `sejong_cli.py` only if a new event field needs printing, and keep it minimal. Don't touch the engine, `reading_check.py`, or `data/sejong.json`.

## Content (already in `data/sejong.json`)

- `before_after`: `{"word": "나무", "roman": "namu", "en": "tree"}`
- `lines.before_show`, `lines.after_ask`, `lines.after_right`, `lines.after_close` (`{roman}`, `{en}` placeholders)
- `lines.baseline_offer`, `lines.baseline_skip`, `lines.baseline_zero` are still present (marked `deprecated`) so the current flow keeps working. The new flow must not use them; Claude removes them after this merges.

## Required behavior

1. **Remove the baseline and post-test entirely:** their phases, the offer/skip choice, `score` events with context `baseline`/`post_test`, and the D2 skip rule. Remove `baseline`/`post_test` from the contract's `context` list and the related `score` fields (`before`).
2. **Before:** right after the intro lines, emit a new event `{"kind": "before_word", "ko": "나무"}` (no romanization, no meaning), then `lines.before_show`, then continue with `lines.clock_start` and Batch 0 exactly as now. No input beyond the usual tap; nothing is graded or recorded as practice.
3. **After:** when the Batch 1 check passes, before the `victory_1` milestone: `lines.after_ask`, then a `question` with `context: "after"`, `display: "나무"`, `input: "text"`, `hint_available: false`, graded with `roman_variants` like decode (not passed to `quiz.answer`, not counted as practice).
   - Correct → `result` (no `line`) then `lines.after_right`.
   - Wrong → `result` (no `line`) then `lines.after_close` with placeholders filled. **No retry; the finale never blocks.**
   - Then the `victory_1` milestone as now.
4. Timer: the after-question's time counts (it's after the clock started); nothing before `clock_start` counts (unchanged).
5. Contract: document `before_word` (fields: `ko`) and `context: "after"` in `docs/sejong-events.md`. Renderer note: `before_word` occupies the screen until a tap, like `word_read`.

## Tests (update `scripts/_verify_sejong_flow.py`)

1. A full always-correct run contains exactly one `before_word` (before `clock_start`) and exactly one `after` question (after the last check `score`, before `victory_1`).
2. No event anywhere has context `baseline` or `post_test`; no line_id `lines.baseline_*` appears.
3. Wrong answer on the after-question → `after_close` with no `{` left, then `victory_1`; the run still finishes with outcome `victory_1`.
4. Correct answer → `after_right`; "namu" and an accepted variant both count as correct.
5. Resume: export/from_state between `before_word` and `clock_start`, and right before the after-question, gives the same events as an uninterrupted run.
6. Update or remove the old baseline/post-test checks; list which ones and why.
7. All other `scripts/_verify_*.py` still pass.

## Done when (paste evidence)

- [ ] Full output of every `scripts/_verify_*.py`.
- [ ] Regenerated seed-1 transcript.
- [ ] `git diff --stat` plus the full diffs of `sejong_flow.py` and `docs/sejong-events.md`.
- [ ] Anything you couldn't follow exactly, and why.

Commit on `sejong-before-after`; don't push.
