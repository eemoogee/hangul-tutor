# Task: `sejong_flow.py` — the Sejong Test slice as plain events

**For:** Codex · **Written:** 2026-10-16 · **Verifier:** Claude (in the owner's session)
**Read first, in this order:** `docs/sejong-events.md` (the contract you build against), `data/sejong.json` (all content and narrator lines), `docs/sejong-test-spec.md` §4–9, §14, §16 (the experience). Then `lesson_flow.py` (the same pattern, already in the repo) and `docs/tasks/2026-10-16_engine-for-web.md` (the engine features you will use).

**Which document wins:** `sejong-events.md` > `sejong.json` > this brief > `sejong-test-spec.md`. The spec predates the other three. Where it says `sejong_test.py`, `SejongTest`, `sejong_state.json`, `print()`/`input()` or `id: "sejong_0"`, ignore that. The class is `SejongFlow` in `sejong_flow.py`, state goes through `export_state()`, and the custom lesson id is `0`.

## Goal

Build the whole playable slice as a UI-free Python flow:

```
intro → baseline offer → baseline (or skip)
→ Batch 0: discover → predict_reveal → build → [First Breakthrough] → decode → check
→ Batch 1: discover → predict_reveal → recognize → retrieve → build → decode → check
→ post-test → before/after score → [Victory 1] → finished
```

Batch phases come from each batch's `phases` list in `sejong.json` (Batch 1 includes `predict_reveal`, unlike the spec). Every call returns events exactly as `sejong-events.md` defines them. Python decides everything a learner sees or is graded on; a renderer only draws.

Also build a **minimal terminal runner** so the owner can playtest before any web work (see "Terminal runner").

## How to use the engine

- One `HangulQuiz(persist=False)` per flow. Never touch `user_progress.json`.
- For each batch, build a custom lesson dict and call `quiz.start_custom_lesson(lesson)`. `id` is `0`; `letters` are **all letters known so far** (cumulative), and `practice_syllables` and `mastery_syllables` are every consonant × vowel block from those letters (`quiz._compose_syllable`): 4 in Batch 0, 16 in Batch 1.
- Build the question cards yourself (the engine's generators pick their own targets and write terminal-styled prompts). Grade and record each practice answer through `quiz.answer(text, QuizQuestion(...))`, using an engine mode name (`match_sound`, `spell`, `build_syllable`, `read_aloud`) so learner items and streaks update. For typed answers, accepted spellings come only from `quiz.roman_variants(target)`, which handles multi-block words. Do not add spellings (see `accepted_rule` in `sejong.json`).
- Korean typed where English letters are expected: `quiz.script_mismatch()` gives a `notice`, and the same `await` follows.
- The check uses `reading_check.make_reading_check(quiz)` and `ReadingCheck.submit()` on the batch's custom lesson.

### Lessons from today's engine review (must follow)

1. **Track each batch's check result in the flow's own state.** Every custom batch has id 0, so `quiz.progress["reading_checks"]["0"]` and `reading_check_passed(0)` are shared by all batches. Passing Batch 0's check must not count for Batch 1's. Do not use `reading_check_passed()` for flow decisions.
2. **Do not reuse `lesson_flow.round_card_events`** for Sejong batches: on a stuck custom lesson it offers "Next: Lesson 1".
3. **Deterministic replays:** use your own `random.Random(seed)` for every choice the flow makes, and save its state in `export_state()`. `make_reading_check` and other engine code use the global `random` module, so seed the global module from your RNG immediately before each such call. Otherwise the `export_state()`/`from_state()` replay test cannot pass.
4. Never call `quiz.lesson_mastery(0)` or `quiz.complete_lesson()` (the first raises, the second refuses). Use `lesson_mastery()` with no argument if you need it at all.

## Decisions (defaults; the owner may change any before you start)

| # | Decision |
|---|----------|
| D1 | **End order:** Batch 1 check passed → post-test → `score` (context `post_test`, with `before`) → `milestone` victory_1 → `finished` (outcome `victory_1`). Spec §7.4 order; §6 and §15 say the reverse. |
| D2 | **Post-test is skipped** when the baseline was skipped (nothing to compare) or scored ≥ 6/8 (spec §14). Victory 1 still shows. |
| D3 | **Decode phase** = read every word in the batch's `words` list once (text input). Single-block words (나, 다, 도, 노, 무, 너, 두) cover the blocks. Misses are re-queued. A `word_read` event follows the first correct read of each word. |
| D4 | **Check** = after each batch's decode: 5 prompts, 4 to pass (`reading_check.py` rules). On a fail: `decode_check_fail`, practice cards (`check_practice`) for up to 3 missed items, then a new check. No attempt limit. Pass lines: `decode_check_perfect` for 5/5, otherwise `decode_check_pass`. |
| D5 | **First Breakthrough** milestone (`seal: small`) comes after Batch 0's build phase, before its decode (spec §7.3). Lines: `lines.first_breakthrough`. |
| D6 | **Pace verdict:** `projected_minutes` = active minutes at Victory 1 × 3 (8 of 24 letters). `tier` = the first `wager.verdict_tiers_minutes` entry whose `max` ≥ projected (`null` = `longer`). Victory 1 `lines` = `lines.victory_1` (with `{time}` filled) then `lines.pace_verdict[tier]`. |
| D7 | **`time_text`:** whole minutes, rounded, at least "1 minute"; "N minutes" otherwise. |
| D8 | **Phase item pools** (session mastery: each item correct once, misses re-queued, `round.size` grows): recognize and retrieve = the batch's 4 new letters; build = every block in the batch's lesson (D-lesson above); decode = D3. |
| D9 | **Choices:** 4 options built only from known letters, correct answer included, shuffled by the flow's RNG. Recognize (`match_sound`) = show the sound, learner taps the letter. Predict uses 3 choices (contract). |
| D9b | **Retrieve** = show the letter, learner types its sound (`input: "text"`, graded with `mode="read_aloud"` and `accepted=sorted(quiz.roman_variants(letter))`). Romanization typing works on any phone keyboard, so no Korean keyboard is needed. Checked: all 8 slice letters grade correctly this way (ㅓ = eo only; ㅜ = u or oo). |
| D10 | **Narrator line rules.** `lines.correct`: rotate through the list. `lines.miss`: when `chosen_is` and a pair `tell` both exist; otherwise `lines.miss_no_tell` (humor rule: miss feedback stays plain). `lines.repeated_miss`: on the second miss of the same item. `lines.streak`: at 5, 10, 15. Words: the first `word_read` of the whole run uses `lines.first_word_read`; later words use their own `first_read_line`; 바보 uses `lines.fool_word` (`text`, not `playtest_alt`); 도도 uses `lines.dodo_word`; others get no line. `lines.baseline_zero` after a baseline score of 0. `first_times_only_gloss` is unclear: keep the full text every time and list it as an open question in your report. |
| D11 | **Hints:** practice cards only (`hint_available: false` on baseline, check and post-test cards, as the contract says). Text = the letter's `sound` for single letters, `quiz._piece_hint(block)` per block for blocks and words. |
| D12 | **Baseline:** 8 choice cards (show the letter, pick its sound), one per slice letter (ㄴ ㄷ ㅁ ㅂ ㅏ ㅓ ㅗ ㅜ), 4 sound options each from those 8 letters' `roman`. The post-test reuses the same 8 letters and options, freshly shuffled. Baseline and post-test answers are scored by the flow only: **do not** pass them to `quiz.answer()` (they are a measurement, not practice). |

**`related` field:** `sejong.json` has no `related` on any letter. Emit `related` only when the content provides it; do not hard-code letter relationships.

## Contract fix (change `docs/sejong-events.md` first, as it says)

The test line "No `question`, `predict` choice or `display` uses a letter outside `letters_known`" cannot hold for the **baseline**, which deliberately shows all 8 slice letters before any are taught. Amend that line to exempt cards with `context: "baseline"`, and keep it strict for everything else, including the post-test.

## Terminal runner

New file `sejong_cli.py`, run as `python sejong_cli.py`. Plain text, no colors needed. It follows the contract's display rules (Enter for the local taps, typed input for `await`), sends real active milliseconds (stop counting after 120 s idle), and saves `flow.export_state()` to `data/sejong_state.json` after every call. On start, if that file exists, it offers to resume (`from_state` + `resume("reopen")`). Add `data/sejong_state.json` to `.gitignore`. Do **not** edit `hangul_cli.py`: wiring `/sejong` into the app waits until the slice has been playtested.

## Out of scope

`web/`, any HTML/JS, Pyodide; `hangul_cli.py`; Batches 2+; the learning curve and results screens; mapping results into the curriculum (spec §13). **No engine changes:** if something seems to need one, stop and say what and why in your report instead. **No content changes** to `sejong.json`: report anything wrong or missing.

## Tests — new file `scripts/_verify_sejong_flow.py`

Runnable as `python scripts/_verify_sejong_flow.py`, one line per check, final count, nonzero exit on failure. Use a scripted "learner" that answers from the events alone (it may look up correct answers through the flow's internals for test purposes only). At least:

1. Every check listed under "Tests that pin this contract" in `sejong-events.md` (with the baseline exemption above).
2. All-correct run, baseline taken: reaches `finished` with `victory_1`; phases appear in the D-order above; `score` events for baseline, two checks and post-test; both milestones present.
3. Run with misses (every third practice answer wrong): misses are re-queued (`requeued: true`, `round.size` grows), the run still finishes, and no `result.line` appears on baseline, check or post-test cards.
4. Check fail path: fail Batch 0's check, see `decode_check_fail`, the `check_practice` cards, then a second check that passes.
5. Per-batch check independence: after passing Batch 0's check, Batch 1 still requires its own check.
6. Skip-baseline path: no post-test, `finished` still `victory_1`. Baseline 7/8 path: no post-test.
7. `resume("pause")` gives `return_after_pause` and repeats the current screen; `resume("reopen")` after `from_state` gives `resume_saved` and repeats it.
8. `/quit` mid-batch → `finished` `quit`; `from_state` on the saved text continues to the same end.
9. Every event list survives `json.loads(json.dumps(...))` unchanged.
10. No file I/O and no `print()` during a full run (same approach as `_verify_engine_web.py`'s file check, plus captured stdout).
11. Timer: the `active_ms` sums sent with `submit()` equal the Victory 1 milestone's `active_ms`, and `time_text`/`verdict` follow D6–D7.

## Done when (paste the evidence; a description is not enough)

- [ ] Full output of `python scripts/_verify_sejong_flow.py`, all passing.
- [ ] Full output of every existing `scripts/_verify_*.py`, all passing.
- [ ] One complete event transcript of an all-correct run (`seed=1`, baseline taken), as JSON lines, saved to `docs/tasks/2026-10-16_sejong-flow-transcript.jsonl`.
- [ ] A short terminal session from `sejong_cli.py`: start, a few answers, quit, restart, resume.
- [ ] The contract diff (`docs/sejong-events.md`) and `git diff --stat`.
- [ ] A list of every judgment call you made that this brief and the documents above did not settle.

Work in your own copy of the repo so other sessions using the main folder are not disturbed by branch switches:
`git worktree add ../hangul-tutor-flow -b sejong-flow`, then build, test and commit there. Don't push (the owner pushes).
