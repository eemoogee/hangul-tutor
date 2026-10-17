# Hangul tutor: handover for the web controller work (updated 2026-10-17 after slice 1)

Read this note and verify the live Git state before acting on it.

## 0. Read this first
- **Repo:** `C:\Users\jefej\Documents\hangul-tutor`. The older handovers in
  `docs/` (`session_handover_2026-10-16.md`, `..._web-app.md`) are still useful for how the app works, but
  their "state" sections are out of date. Where they disagree with this note,
  trust this note and then `git log`.
- **The owner (Jeff, "eemoogee"):**
  - New to coding. Explain terms and commands plainly.
  - Never suggest ending the session, wrapping up or resting.
  - Wants short, concise replies.
  - Wants anything suboptimal flagged before proceeding: name the better
    option and its tradeoff, then let him decide.
  - Ask before generating files, and before any costly or long sequence of
    tool calls.
  - Plays on an Android phone in Termux (about 49 columns) and on Windows.
- **Coordination:** Codex handles scoped implementation and prepares
  reviewable Git changes. Hyojangi can run independent verification. The
  owner approves commits and pushes, runs terminal commands when needed, and
  playtests.
- **Agent behavior so far:** both agents stop when a precondition or the code
  contradicts the brief, and they report. That is good. Build preconditions
  into every brief.

## 1. Repo state (verified 2026-10-17, after slice 1)
- At this handover's preparation, `master` and `codex/web-controller` were
  both at `4cdcee4`; `origin/master` was `9e2257a`. A handover commit on
  `master` will move only that branch. Check `git log` for the live refs.
- Commits made this session, in order:
  - `f3a03ed`: the verifier writes screenshots to the ignored
    `.verify_out/shots/`, and a new `--shots-dir` flag repoints them.
  - `4cdcee4`: adds `requirements-web.txt` (`playwright==1.64.0`) and a
    docstring note in `scripts/_verify_web.py`.
  - Known blemish: the message of `f3a03ed` says "committed references were
    updated to match", but no reference screenshots changed. Decided NOT to
    amend: that would rewrite `4cdcee4` and orphan the tag.
- **Undo point:** annotated tag `before-web-controller` at `4cdcee4`.
  `git rev-parse` on it gives the tag's own hash; use
  `git rev-parse before-web-controller^{commit}` for the commit.
- **Branches:**
  - `codex/web-controller`: where the controller work goes.
  - `codex/flow-events-pilot`: stale and empty, still at `9e2257a`. Delete
    later with `git branch -d`.
  - `sejong-web`: merged. Keep it.
- **Uncommitted controller files:** `curriculum_flow.py` and
  `scripts/_verify_curriculum_flow.py` were untracked when this handover was
  prepared. Check `git status` before working on them.
- **Worktrees still present:** `-before`, `-f9`, `-fixes`, `-pt2`, `-web`.
  Check their cleanliness and merge state again before removal.
- **Commit trailers:** Hyojangi's commits end with
  `Co-authored-by: Hermes Agent`. No model names in commits or PRs.
- **Pushing:** only the owner pushes, from his own terminal. Do not push from
  a cloud session.

## 2. What the investigation found (this changed the plan)
- The 10-16 handover assumed the flow rules still had to be separated from
  printing in `hangul_cli.py`. That was wrong: `lesson_flow.py` already does
  it. Codex confirmed this and stopped without editing.
- `lesson_flow.py` public API:
  - `ReadingCheckFlow.start()` and `.submit(answer)`
  - `round_card_events(...)` and `round_card_choice(card, answer)`
  - `AdvanceFlow.start()` and `.submit(answer)`
  - Events are plain dicts with a `kind` field. Kinds: `check_intro`,
    `check_input`, `check_unavailable`, `check_question`, `check_hint`,
    `check_commands`, `check_script_mismatch`, `check_feedback`,
    `check_score`, `check_practice_intro`, `check_practice_question`,
    `check_practice_feedback`, `round_card`, `round_prompt`,
    `lesson_mastered`, `curriculum_complete`, `advance_prompt`,
    `advance_stay`, `lesson_started`, `advance_missing_lesson`,
    `advance_lessons`, `advance_help`.
- **The web app does not use `lesson_flow.py`.**
  - `scripts/build_web.py` bundles the engine, `reading_check.py`,
    `sejong_flow.py` and data, but not `lesson_flow.py`.
  - `web/app.js` loads those into Pyodide, makes `HangulQuiz(persist=False)`
    and a `SejongFlow`, and calls `flow.start()`, `flow.submit(...)` and
    `flow.resume(...)`. Exported state is saved in local storage.
  - `SejongFlow` is a self-contained two-batch Sejong slice using custom
    lesson ID 0. The ordinary 12-lesson curriculum is NOT playable in the
    browser.
- **What stays outside `lesson_flow.py`:** the decisions about WHEN to call
  it. Line numbers are from `9e2257a`; re-check them.
  - Reading check start: `_interactive_loop_body`, `hangul_cli.py` lines
    2439-2479 (`mastery_offered`, `check_requested`; condition at 2463-2466).
    `/check` eligibility at 2549-2556.
  - Round end: lines 2442-2447 and 2481-2501 (`round_asked >= ROUND_SIZE`). A
    skip counts at 2725. A graded answer updates `round_asked` and
    `round_right` at 2814-2817.
  - Lesson advance: lines 2469-2479 and 2492-2499, plus `/lesson` and `/next`
    at 2587-2616. `_go_to_next_lesson` at 2264-2277, `_advance_and_show` at
    1984-1994.

## 3. The current task: web controller for the ordinary curriculum
- **Decision (owner chose "option 1"):** write a fresh controller module and
  leave the terminal loop (`_interactive_loop_body`) untouched. Copy the
  scheduling rules, delegate cards, checks and advances to `lesson_flow.py`,
  and mirror `SejongFlow`'s interface (`start`, `submit`, `resume`, export
  state) so `web/app.js` can swap controllers with minimal change.
- **Tradeoff:** the rules will live in two places and could drift apart.
  Mitigation: a drift check that feeds identical answers to the terminal
  logic and the controller and compares round and advance decisions.
- **Slice 1 implemented, not committed:** `curriculum_flow.py` provides
  `CurriculumFlow.start()` and `.submit(answer, active_ms=0)` for ordinary
  practice. It delegates round cards, reading checks, and advance offers to
  `lesson_flow.py`. It does not alter the terminal loop, engine, or web app.
  Its new events are `question`, `result`, `hint`, `notice`, and `finished`, in
  addition to events from `lesson_flow.py`. Practice supports answers,
  `/hint`, `/skip`, `/check`, `/next`, and `/quit`. Other CLI commands, modes,
  games, and menus are outside this slice.
- **Slice 1 verification reported by Codex:** the new deterministic verifier
  ran 9 tests, including a CLI/controller scheduling drift test. The reading
  check verifier ran 21 tests; the gameplay verifier printed 237 PASS lines;
  the decomposition and missing-vowel/batchim verifiers passed. These results
  were reported before this handover update; rerun them when Python is
  available. The drift test directly makes both quizzes ready before `/check`,
  so it does not yet compare naturally earned mastery timing against the CLI.
- **Next controller step:** add export/restore/resume, including reload during
  a reading check. Then bundle the ordinary curriculum controller in
  `scripts/build_web.py` and render its events in `web/app.js`, verifying each
  small step. Keep work on `codex/web-controller`; commit only with the
  owner's approval.

## 4. Verification checklist (after any web change)
- `python scripts/build_web.py`, then `python scripts/_verify_web.py` must
  show **9/9 PASS**. Use `C:\Users\jefej\hermes-env` Python, the only place
  Playwright is installed. A plain interpreter fails with "No module named
  'playwright'". Setup is in `requirements-web.txt`.
- `git status` must show only the intended files.
- If `hangul_cli.py` or the engine is touched: `scripts/_verify_gameplay_fixes.py`
  (237 PASS lines at the last reported run), `scripts/_verify_reading_check.py` (21),
  `_verify_decompose_syllable.py`, `_verify_missing_vowel_batchim_guard.py`.
  All passed at the last known state.
- Known gap: `scripts/_playtest_learners.py` still calls `complete_lesson()`,
  which now records nothing without a passed reading check. Its completion and
  time figures only reflect practice readiness.

## 5. Ground rules for every agent brief
- Include preconditions that stop the agent when wrong: current branch,
  expected `git status`, HEAD hash.
- No commits or pushes without the owner's explicit "commit".
- Stage exact paths, never `git add -A`. Delete branches only with `-d`,
  never `-D`.
- Report with pasted command output, not summaries. Verify an item is still
  open before working on it.
- Check Korean and Hangul content for accuracy before encoding it (도 is
  "also", not do-re-mi).
- Do not switch branches while another agent is working. All agents share
  one folder.
- Brief template:

```
Repo: C:\Users\jefej\Documents\hangul-tutor, branch <name> (confirm).
Task: <one sentence>
Files: <exact paths>
Done when: <observable result>
Do not: commit, push, touch files outside the list.
Report: paste <specific command output>.
```

## 6. Roadmap, in order
1. **Continue the controller** with state export/restore/resume, then web
   bundling and rendering, verifying each step (section 3).
2. **Worktree cleanup:** list first, skip anything dirty, unmerged or in
   use, remove with `git worktree remove` (no `--force`). Then delete
   `codex/flow-events-pilot` with `-d`.
3. **When the controller works, ask the owner:**
   - Merge to `master`, tag it (e.g. `web-controller-v1`), and push from his
     terminal.
   - Whether to try the Sejong slice on Netlify with a few beginners first.
     `_headers` exists, but Netlify hasn't been used. Playtest observer
     sheet: a private Claude doc "Hangul Tutor Beginner Playtest Sheet" (not
     in the repo). Give each tester their own folder copy with
     `user_progress.json` deleted.
4. **Fix the playtest script** so it accounts for the reading check.
5. **Later, from the 10-16 handover (by value):**
   - Terminal effects (`scripts/_demo_hangul_effects.py`), picked by the
     owner by eye.
   - Learners stuck in Lesson 12 (batchim-weak finished only 5/10): steer
     them to review Lessons 10 or 11.
   - Cross-lesson review.
   - Real words in Rain and Conveyor.
   - Content ideas: phrases like 물 주세요, a Sejong history opener, Termux
     TTS.
   - Companion characters (Jeong and Sejong):
     `docs/notes/2026-10-17-companion-characters.md`. Final art waits until
     the game design is firmer.
   - Sejong Test spec: `docs/sejong-test-spec.md`. Long; quote only the
     relevant section.

## 7. Open decisions for the owner
- Whether to amend `f3a03ed`'s message (recommended: no).
- Whether to deploy the Sejong slice for beginner testing before the larger
  build.

## 8. Not verified (check first)
- Line numbers in section 2 (from `9e2257a`; `hangul_cli.py` hasn't been
  edited since).
- Whether the extra worktrees are clean and merged; their presence was
  verified, but they were not inspected for cleanup.
- During this handover update, the shell could not rerun Python checks:
  `hermes-env` pointed to a missing Python 3.11 installation and `py -0p`
  reported none installed. Check the runtime before future verification.
