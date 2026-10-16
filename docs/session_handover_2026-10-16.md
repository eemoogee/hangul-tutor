# Hangul tutor — app handover (2026-10-16)

This covers the **app's gameplay, content and design work**. The separate
model fine-tuning thread is in `docs/session_handover_2026-09-02.md` and
`docs/decisions.md`.

Paste this into a new session, or say "read
`docs/session_handover_2026-10-16.md`".

---

## Working with the owner

- **New to coding.** Explain terms and processes plainly: what a command
  does, what a PR is.
- **Don't suggest ending a session, wrapping up, or resting.** The one
  exception: say so when the conversation's context is filling up and a
  fresh session (with a handover) would work better.
- **Plays on an Android phone in Termux, about 49 columns wide.** Feedback
  usually arrives as phone screenshots with little or no text. Read them
  closely, as a QA pass: find what looks wrong and fix the real problems.
  A blue or video bubble on the right edge is another app, not the tutor.
- **Also runs on Windows.** `run_tutor.bat` runs it offline;
  `run_tutor_llm.ps1` turns on the optional Ollama features.
- **Likes:** simple, emphatic progression. That means short rounds, ⭐ "is
  solid now!" moments, real words as rewards, and a clear "lesson
  mastered → move on". Their complaint that "the lesson keeps going with
  no sense of making progress" drove the rounds work, so treat lesson
  length as a cost.
- **How to deliver:** small PRs into `master`, with a plain-language
  summary and measured numbers when a design choice has a cost. The owner
  merges PRs from the phone, then runs `git pull` in Termux.

## Repo state

- `master` is at `621fcbc` (2026-10-15). Nothing is uncommitted, and no
  PRs are open.
- Work since 2026-10-14 went **straight to master**, from sessions on the
  owner's computer and a Codex branch (`codex/progress-version`), not
  through PRs. Many of those commits have no description. The code and
  `scripts/_verify_gameplay_fixes.py` section titles are the best record.
- Checks, run from the repo root:
  - `python scripts/_verify_gameplay_fixes.py`: **222 checks, all
    passing**. Add a check for every fix, and confirm it fails on the old
    code before trusting it.
  - `python scripts/_verify_decompose_syllable.py` and
    `python scripts/_verify_missing_vowel_batchim_guard.py`.
  - `python scripts/_playtest_learners.py [--runs N] [--quick] [--seed S] [--json out.json] [--rule A-D]`
    is the simulated-learner playtest. It reports pacing, stalls, mode
    mix, real skill when the app says "mastered", repetition, grading
    bugs and question-quality problems. Use it to measure the cost of any
    pacing change, comparing against `git archive origin/master` with the
    same seed.
- Neither the verifier nor the playtest touches `data/user_progress.json`.

## How the app works now (the parts that changed recently)

**Mastery** (`LearnerItem` in `hangul_quiz_engine.py`)
- Each item keeps its last 8 answers in `history`:
  - `1` right on your own
  - `0` wrong
  - `h` right after `/hint`
  - `s` skipped
- Score = rights in the last 8 − mistakes in the last 4
  (`MISTAKE_WINDOW = 4`), scaled to 0–5. "Solid" means
  `MASTERY_CONFIDENCE = 2`, so 3 right in a row is solid.
- A lesson is mastered when every item in its mastery set is solid.
- Why 4 and not 8: the costs were measured in
  `docs/notes/2026-10-14-mastery-counts-mistakes.md`. With 8, the course
  took 38% more questions for an average learner.
- `/hint` still counts as right and keeps the streak, but gives no mastery
  credit. `/skip` counts as a miss and uses up a turn in the round.

**Rounds** (`hangul_cli.py`)
- Rounds are 10 questions (`ROUND_SIZE`). Each ends with a card showing
  the progress bar and "Still to go".
- After 3 or more rounds where nothing new became solid
  (`STUCK_AFTER_ROUNDS`), the card offers the next lesson without marking
  this one done. In Lesson 12 it points to `/lessons` instead.

**Mix-ups** (changed 2026-10-14)
- The standalone Look-alikes question is gone: it drilled preset pairs the
  learner had never confused.
- After a real miss, `show_mixup` puts the two blocks side by side with
  their sounds. The missed block then comes back 3 questions later as a
  "Find the Sound" question, with the confused block among the choices
  (`_queue_comeback`, `COMEBACK_AFTER`).
- Mix-ups are inferred only from unambiguous matches. Examples: reading
  어 as "o", missing-vowel answers saved as two blocks (모 typed for 미),
  final-consonant mix-ups, word-pair picks.
- `_clean_pair` drops consonant-vs-vowel nonsense pairs.

**Progress file**
- `user_progress.json` now carries a `schema_version` (currently 3), with
  migrations `_migrate_1_to_2` and `_migrate_2_to_3`.
- Legacy data is kept under `_legacy_*` keys rather than deleted.
- If a migration fails, or the file comes from a newer version, the
  original file is kept untouched.
- Saving retries if the file is locked, and recovers the temp copy.

**Other recent fixes**
- Stray key codes (End, arrow keys) are ignored in answers.
- The session summary shows skips separately from graded answers.
- The lesson-complete box previews the next lesson.
- The round counter is correct after the mini-games.
- Hangul Rain's status line fits a phone, with lives shown first.
- "ee" is accepted for ㅣ.
- Korean-claims accuracy audit:
  - the silent ㅇ wording is fixed;
  - only ㅊ ㅋ ㅌ ㅍ are described as breathy;
  - 학교 no longer accepts "hagyo";
  - "stops short" is used only for final ㄱ ㄷ ㅂ;
  - 10 checks guard the old wording.

**Unchanged foundations**
- 12 lessons in `data/curriculum.json`, with 129 real words across
  Lessons 1–11, each readable with the letters taught so far.
- `data/word_contrasts.json` holds the word pairs.
- `term_wrap.py` word-wraps all output to the phone's width.
- Conveyor and Rain are the mini-games, opened with `/conveyor` and
  `/rain`.

## Baseline (playtest, 10 runs per learner, seed 7, 2026-10-16)

| Learner | Whole course (median) | Finishes the course |
|---|---|---|
| strong | 574 questions, about 60 min | 10/10 |
| average | 721, about 80 min | 10/10 |
| struggling | 986, about 118 min | 10/10 |
| ㅓ/ㅗ mixer | 788 | 10/10 |
| batchim-weak (final consonants capped at 60%) | 2,126 | **5/10**: stuck in Lesson 12 |

No grading bugs and no question-quality problems were found.

## Open threads and ideas, roughly by value

1. **Terminal effects.** `scripts/_demo_hangul_effects.py`, with its frame
   check `scripts/_demo_frame_check.py`, shows candidate animations. None
   is wired into the app yet. The owner is meant to pick some by eye on
   the phone; then they move into a shared module that replaces the
   hand-rolled cursor code in `hangul_cli.py`.
2. **Stuck in Lesson 12.** The batchim-weak learner stalls in half its
   runs. The stuck card points to `/lessons`, but nothing steers the
   learner to review final consonants in Lesson 10 or 11. A targeted
   suggestion ("these words all miss the bottom consonant — try
   `/lesson 10`") would help.
3. **No cross-lesson review.**
   - Mix-up drills and comebacks only cover the current lesson, so the
     simulated ㅓ/ㅗ mixer stops getting ㅓ/ㅗ practice after Lesson 4.
   - A review session that mixes earlier lessons' weak items and words
     would help, especially when returning after a break.
4. **Real words in the games.** Rain and Conveyor still use single
   syllables. Dropping real words, and showing the meaning when one is
   cleared, would make them feel like reading.
5. **Content ideas, not started:**
   - a "phrase to recognise" per lesson (물 주세요);
   - a Sejong/history opener;
   - audio through Termux:API `termux-tts-speak`.
6. **Smaller items, last checked 2026-10-12–14; recheck first:**
   - only Lessons 5, 6, 11 and 12 have a `mastery_syllables` /
     `mastery_words` list; the others use their whole practice pool;
   - `/chart y` is wider than a phone screen;
   - `data/reading_practice.jsonl` has unnatural phrases (it's generated,
     so fix `generate_dataset.py`);
   - the translation grader on the optional LLM path may mis-handle
     negation;
   - `hangul_finetune_gaps.md` is stale.

## Conventions

- Commits and PR bodies end with the footer from the session's attribution
  settings. Never put model names in commits or PRs.
- Keep fixes minimal and measured. Re-read the diff adversarially, run the
  verifier and a playtest, then push.
- Dated notes go in `docs/notes/YYYY-MM-DD-topic.md`, in plain language,
  with before/after tables when a design choice has a cost.
