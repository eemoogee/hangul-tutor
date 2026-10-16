# Hangul tutor: handover for the web-app direction (2026-10-16, later session)

Read `docs/session_handover_2026-10-16.md` first (owner preferences, repo
conventions, how the app works). This note adds what changed afterwards and
the new direction. Paste it into a new session, or say "read
`docs/session_handover_2026-10-16_web-app.md`".

---

## Decision: aim for a web / phone app, not a terminal game

The owner expects casual learners will not use a terminal, especially on a
phone (they use Termux themselves). The goal is something installable or
openable from a link. The terminal app stays as the place to try teaching
ideas and as the test harness.

## What is settled and what carries over

- **Reusable as is:** the engine (`hangul_quiz_engine.py`, 3,508 lines),
  `reading_check.py`, `game_state.py`, the curriculum and the tests. The
  engine has 16 `print` calls and one `input`; `reading_check.py` and
  `game_state.py` have none. The 16 prints were not inspected.
- **Tied to the terminal:** `hangul_cli.py` (2,949 lines, 61 functions, 330
  `print` calls, 19 places that wait for typing).
  - 21 helper functions (314 lines) neither print nor ask: reusable.
  - 11 functions (about 1,010 lines) both print and ask, and hold the flow
    rules (when a round ends, when the reading check starts, when a lesson
    advances). The largest is `_interactive_loop_body` (407 lines, 22 engine
    calls): the riskiest piece to untangle.
  - Print-only screens (`print_question`, `print_reference_table`, lesson
    intro, and so on) map to web screens.
- **Rebuild, don't port:** Rain, Conveyor, `term_wrap.py` (about 1,000 lines
  of terminal size, animation and live-key code). The Ollama chat/model code
  is not needed for the web.
- These sizes come from counting, not from tracing behaviour.

## Suggested first step (a pilot, not a rewrite)

Separate the flow rules from printing, starting with the newest and cleanest
code: `_run_reading_check`, `_round_card`, `_offer_advance` (about 230
lines). Make them return plain "what to show next" events that the terminal
prints. Keep `scripts/_verify_reading_check.py` (21 tests) and
`scripts/_verify_gameplay_fixes.py` passing. If it feels natural, repeat the
pattern on `_interactive_loop_body`.

Likely web plan, untested: run the Python in the browser as a static page
(tester opens a link, nothing to install), installable on a phone home
screen. Progress saving (`PROGRESS_PATH` in the engine) would need to move to
browser storage. Decide full rewrite, accounts or an app-store build later.

## What changed in this session

- `data/curriculum.json`: explicit `mastery_syllables` for Lessons 1-4 and
  7-10. They copy each lesson's existing practice pool, so pacing did not
  change. Lessons 5, 6, 11 already had lists; Lesson 12 uses `mastery_words`.
- Stuck card (`hangul_cli.py`, `_print_trouble_items`): names up to three
  unfinished items the learner missed most.
- **Independent reading check** (`reading_check.py` plus changes in
  `hangul_cli.py` and `complete_lesson()`): once the practice goal is reached,
  five prompts with no choices (three lesson items, two new combinations),
  four right to pass, hinted prompts return once for an independent try. A
  pass is what records lesson completion. `/check` also works on finished
  lessons, at a question prompt and at the round card. Check answers do not
  change practice scores. Saved in progress as `reading_checks` and
  `reading_check_seen` (optional, additive).
  - Design write-up: `docs/notes/2026-10-16-independent-reading-check.md`.
  - 21 tests in `scripts/_verify_reading_check.py`.
  - Merge note: commit 24ae148 clears round notices when the lesson changes;
    the check flow now does that where the lesson advances.
- Walked through by hand on Lessons 2 and 5: pass, fail, retry, `/hint`,
  `/back`, `/quit`. Misses now read "Not yet" with what was typed; the
  "tricky ones" practice asks before revealing the answer; the fail line
  states the pass mark.

## Open items and unverified claims

- **Not validated with real beginners.** Whether 4 of 5 feels fair, how hard
  typing sounds is on a phone, and whether the new combinations feel natural
  are all unknown. Observer sheet: a private Claude doc titled "Hangul Tutor
  Beginner Playtest Sheet" (not in the repo). Give each tester their own
  folder copy with `user_progress.json` deleted.
- **The simulated-learner playtest ignores the check.**
  `scripts/_playtest_learners.py` still calls `complete_lesson()`, which now
  records nothing without a passed check. It loops over lessons by number, so
  it still runs, but its completion and finish-time figures are practice
  readiness only.
- The new combinations in Lessons 2 and 5 were two-block pairings of
  practiced blocks (all single blocks were already used), so they resemble
  the "Made-up Word" practice questions. If testers pass too easily, make
  them harder first.
- Still open from the outside review: rounds that build to a real word;
  cross-lesson review; Rain feeding the engine and its stricter romanization;
  Conveyor untimed and without a real decision; softening the
  "production over recognition" rule in `docs/hangul_game_plan.md`.
- The older handover's item about only Lessons 5, 6, 11, 12 having mastery
  lists is now out of date.
- The owner's own `user_progress.json` was changed during testing (Lessons 1,
  2, 5 complete; Lesson 5 shows 9 of 12 solid). A backup copy is on their
  desktop.

## Cautions for the next session

- Do not push from a cloud session: it has no GitHub login. The owner pushes
  from their own terminal.
- Ask before large changes. The owner prefers short plans, plain language,
  and a flag when a cheaper method exists.
