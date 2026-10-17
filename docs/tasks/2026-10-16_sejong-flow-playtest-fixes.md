# Task: Sejong flow fixes from the owner's first playtest

**For:** Codex · **Written:** 2026-10-16 · **Verifier:** Claude (in the owner's session)
**Context:** the owner played `sejong_cli.py` start to Victory 1 (14 minutes). These are the flow fixes that playtest showed. Content fixes are already made in `data/sejong.json` (commit them with this work if they're still uncommitted; see "Content already changed" below).

## Ground rules

- Work in your own worktree: `git worktree add ../hangul-tutor-fixes -b sejong-playtest-fixes` (based on current `master`).
- Change only `sejong_flow.py` and `scripts/_verify_sejong_flow.py`. **Do not touch `sejong_cli.py`**: another session is editing it. Don't touch the engine, `reading_check.py`, or `data/sejong.json`. If a fix seems to need one of those, stop and report.
- Keep `docs/sejong-events.md` accurate; if a fix changes event behavior, update the contract in the same commit.

## Content already changed (in `data/sejong.json`, read it first)

- `lines.intro` is now 5 lines ending with "Twenty-four…". "The clock starts now." moved to **`lines.clock_start`**.
- New **`lines.predict_wrong.side`** / **`.stack`**, each with a `{vowel}` placeholder.
- `lines.predict_prompt` now asks "Which block do they make?"
- Letter `notice_line`s shortened; ㅓ no longer has one.

## Fixes

| # | Problem seen | Required behavior |
| --- | --- | --- |
| F1 | The clock started before the baseline, so the 8 test questions counted toward the wager. | Active time is counted only from the first Batch 0 `letter_intro` onward. Time sent with `submit()` before that is ignored. Emit `lines.clock_start` as a `narrator` event right before Batch 0's `batch_intro`, after the baseline (or its skip). |
| F2 | The baseline gave per-question feedback ("Try again later — u"), revealing answers during a before-measurement. | Baseline and post-test questions produce **no** `result` event. The next question follows immediately. The `score` event at the end still reports the total. Update the contract's `result` section to say so. |
| F3 | Jeong commented on every correct answer, rotating 4 lines about 40 times. | A correct practice answer gets a `lines.correct` line on about 1 in 3 answers (use the flow RNG), never on two consecutive correct answers, and never the same line twice in a row. Streak and word lines are unaffected. |
| F4 | A streak produced two Jeong lines in a row ("Hm. Correct." then "Five in a row"). | At streak 5/10/15, the streak line **is** the result's `line`. No separate correct line on that answer. |
| F5 | "Then my explanation needs improvement" fired after a single miss, because misses of the same item carried across phases. | `lines.repeated_miss` only after **3 consecutive wrong practice answers** (any items, within the current phase). Then reset the counter. All other misses use `lines.miss` / `lines.miss_no_tell`. |
| F6 | Batch 1's build phase asked 17 questions, including the 4 Batch 0 blocks already mastered. | A batch's build pool = blocks that contain **at least one of that batch's new letters** (Batch 0: 4, Batch 1: 12). |
| F7 | Build choices were too easy: for ㄷ+ㅓ the wrong options were 바 and 보, which you can rule out from the consonant alone. | Build distractors (3): at least one with the **same consonant, different vowel**, and at least one with the **same vowel, different consonant**, all from known letters. In Batch 0 (2×2 letters) that is the full set anyway. |
| F8 | A wrong predict pick got no reaction. | After a `predict` answer that's wrong, the `reveal` is followed by `lines.predict_wrong.side` or `.stack` (by the target vowel's layout) with `{vowel}` filled, then the existing `predict_reveal` line. |

## Tests to add or update in `scripts/_verify_sejong_flow.py`

1. F1: with `active_ms=60000` sent on every baseline answer, `victory_1.active_ms` excludes all of it. `lines.clock_start` appears exactly once, after the last baseline event and before Batch 0's `batch_intro`.
2. F2: no `result` with context baseline/post_test anywhere in a full run; `score` events still present.
3. F3: over 20 always-correct runs, the share of correct practice results carrying a `lines.correct.*` line is between 20% and 45%; never two consecutive correct results both with a correct line; never the same `line_id` twice in a row.
4. F4: no list contains two consecutive Jeong `narrator`/`line`s for one answer at a streak point. The streak line's `line_id` is on the `result` itself.
5. F5: a player alternating wrong/right never triggers `repeated_miss`; three wrongs in a row does, once.
6. F6: Batch 1 build cards = exactly 12 distinct targets in an always-correct run, none of 나 노 다 도.
7. F7: every build card's choices include a same-consonant and a same-vowel distractor (Batch 1).
8. F8: a deliberately wrong predict pick yields `reveal` → `predict_wrong.*` → `predict_reveal.*`; a right pick yields no `predict_wrong`.
9. All existing checks still pass (update any that assumed the old behavior, and list which ones you changed and why).

## Done when (paste evidence)

- [ ] Full output of `python scripts/_verify_sejong_flow.py` and every other `scripts/_verify_*.py`.
- [ ] A seed-1 always-correct event transcript (JSONL) regenerated.
- [ ] `git diff --stat` and the full diff of `sejong_flow.py` and `docs/sejong-events.md`.
- [ ] Anything you couldn't follow exactly, and why.

Commit on `sejong-playtest-fixes`; don't push.
