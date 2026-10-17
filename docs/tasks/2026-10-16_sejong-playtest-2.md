# Task: Sejong fixes from the owner's second playtest

**For:** Codex · **Written:** 2026-10-16 · **Verifier:** Claude (in the owner's session)
**Context:** the owner played `sejong_cli.py` end to end on `master` at `9f649c7` (12 minutes, one failed Batch 1 check then a pass). These five fixes came out of that run.

## Ground rules

- Own worktree from current `master`: `git worktree add ../hangul-tutor-pt2 -b sejong-playtest-2`.
- Change `sejong_flow.py`, `scripts/_verify_sejong_flow.py`, `docs/sejong-events.md`, and in `sejong_cli.py` only what fix 5 needs.
- **Do not touch `data/sejong.json`**: the owner is trimming word lines in it at the same time. Tests must not depend on which words have a `first_read_line`.
- Don't touch the engine or `reading_check.py`. If something seems to need them, stop and report.

## Fixes

### P1. Mix-up tips for block and word mistakes
**Seen:** picking 다 for ㄷ+ㅗ (the ㅏ/ㅗ mix-up) and typing "namu" for 너무 (the ㅓ/ㅏ mix-up) both got "Not yet. Look again." `_chosen_tell` only finds a tip when the answer and target are single letters.

**Required:**
- **Choice answers:** if the picked block differs from the target in exactly one letter, and those two letters are a taught `confusion_pairs` pair (current or earlier batch), return that pair's `tell`.
- **Typed answers:** for each block of the target, and each letter in it that belongs to a taught pair, swap in its partner to make a candidate. If the typed answer is in `quiz.roman_variants(candidate)`, use that candidate and pair (e.g. 너무 typed "namu" → candidate 나무, tell for ㅓ/ㅏ; 두부 typed "dobu" → candidate 도부, tell for ㅜ/ㅗ). The first match wins, scanning blocks left to right.
- **Never name a hidden form:** if the candidate is or contains a not-yet-revealed held-back block (누 머 버 before Batch 1's check) or is the before/after word, omit `chosen_is`, still set `result.tell`, and use `lines.miss_no_tell` as the line. Example: 도마 typed "domeo" → no "That's 도머"; tell only.
- Letter-level tips keep working as now. No tips on check or after cards (unchanged).

### P2. The before/after word is never shown in between
**Seen:** 나무 was the second word in Batch 1's decode phase, with its "Tree." payoff, so the final "And now?" repeated something already read.

**Required:**
- Between the `before_word` event and the after question, `content["before_after"]["word"]` never appears in any event field: not in decode pools, the check's familiar-word fallback, check `new combinations` (if `make_reading_check` produces it, regenerate deterministically from the flow RNG, then fall back to replacing that item with a practised one), tips (P1), or narrator text.
- On a **correct** after answer, emit `word_read` `{ko, roman, en}` (no `line`) before `lines.after_right`, so the learner gets the meaning. The wrong path is unchanged (`after_close` already gives it). Note in the contract that `word_read` can follow the after question.

### P3. Retries
**Seen:** after a failed Batch 1 check and practice, the retry repeated the construction card (ㅁ+ㅓ, just answered), and a 5/5 retry got "Five of five. Show-off."

**Required:**
- The construction card is shown on the **first** check attempt only. Retries go straight to the reading check.
- `lines.decode_check_perfect` only on a first-attempt 5/5 (either batch). A passing retry uses `lines.decode_check_pass`.

### P4. Spacing around streak lines
**Seen:** Jeong spoke on 5 of 9 Batch 1 build answers, including a generic comment directly before a streak line (더 then 마).

**Required:** no `lines.correct` comment on the answer right **before** a streak line would fire (the streak after this answer is one below a `lines.streak` key), or right **after** a streak line. Streak lines and word lines themselves are unchanged. (The owner is reducing word lines in the content separately.)

### P5. Terminal wording (`sejong_cli.py`)
- A wrong answer on a **check** or **after** card prints `It reads <answer>.` instead of `Try again later — <answer>` (those cards don't come back). Practice misses keep the current wording. The CLI already sees each question's `context`; remember it for the matching `result`.
- `score` prints `Reading check: 4 of 5`, not `check: 4 / 5`.
- When a `result` has `tell` that isn't already inside its `line` text, print the tell on its own line (needed for P1's hidden-form case).

## Tests to add or update in `scripts/_verify_sejong_flow.py`

1. P1 choice: in Batch 0 build, picking the one-letter-different block for a taught pair gives `chosen_is`, `tell`, and a `lines.miss` line with both filled.
2. P1 typed: "dobu" for 두부 → `chosen_is` 도부 + ㅜ/ㅗ tell; "namu" for 너무 → tell for ㅓ/ㅏ and **no** `chosen_is` (나무 is the before/after word).
3. P1 hidden: "domeo" for 도마 and "beoda" for 바다 → tell present, no `chosen_is`, line `lines.miss_no_tell`; no held-back block anywhere in the event list.
4. P2: over 30 runs (always-correct, every-3rd-wrong, and runs that fail each check once), no event between `before_word` and the after question contains 나무 in any string field. A correct after answer yields `word_read` (나무, namu, tree, no line) then `after_right`.
5. P3: a run that fails Batch 1's first check shows exactly one construction card; a 5/5 retry gets `decode_check_pass`, not `decode_check_perfect`; a first-attempt 5/5 still gets `decode_check_perfect`.
6. P4: over 30 always-correct runs, no `lines.correct.*` line on the practice answer immediately before or after a `lines.streak.*` line.
7. P5: render a check-card miss and a `score` through the CLI's event printer: `It reads …` and `Reading check: N of M`.
8. Everything existing still passes (held-back leak scan, one line per answer, replay after `from_state`). List any check you changed and why.

## Done when (paste evidence)

- [ ] Full output of `python scripts/_verify_sejong_flow.py` and every other `scripts/_verify_*.py`.
- [ ] Seed-1 always-correct transcript (JSONL) regenerated.
- [ ] `git diff --stat`, and the full diff of `sejong_flow.py`, `sejong_cli.py` and `docs/sejong-events.md`.
- [ ] Anything you couldn't follow exactly, and why.

Commit on `sejong-playtest-2`; don't push.
