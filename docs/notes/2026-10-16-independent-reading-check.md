# Independent reading before lesson completion

Practice confidence used to be enough to complete a lesson, even when all
answers came from recognition questions. A regression reproduces this on the
old master: Lesson 1 reaches the practice goal, then `complete_lesson()` marks
it complete without an independent reading answer.

## New flow

1. Reach the existing practice goal. Pool sizes and mastery thresholds do not change.
2. Read five prompts without choices or a timer: three representative lesson
   items, then two new combinations of already taught components.
3. Four independently correct prompts pass. A hinted prompt earns no credit
   until an unassisted retry; each hinted item returns at most once.
4. After a failed check, try up to three supported practice prompts from the
   misses, then choose a fresh check or ordinary practice.

The five prompts / four correct rule is a prototype to playtest, not a
validated retention measure. A single correct new combination suffices if
the other four readings are correct. Final-consonant lessons spread their
representative prompts across different endings; five prompts cannot cover
all seven endings exhaustively.

`/check` is available once the practice goal is reached, and on previously
completed lessons. `/next` and `/lesson N` still allow leaving an unfinished
lesson without completing it. Sudden death does not run completion checks.

## Generation and progress

New single blocks use only initial/vowel/final components found in the active
lesson's practice pool. If those combinations are already familiar, generate
a new two-block sequence (or three blocks if the two-block space is exhausted).
The engine's existing boundary guard avoids unsupported sound changes.
Combinations are not advertised as real words. Existing romanization variants
and vocabulary-specific accepted spellings still work.

`reading_check_seen` remembers prompts shown, including interrupted checks, so
retries do not label previously presented combinations as new. `reading_checks`
stores completed attempts' last score, attempt count, targets, and a lasting pass
flag. These optional additive fields do not require a schema migration.

A pass records completion immediately, even when the learner stays in the
lesson. Previously completed lessons remain complete. Interrupted checks restart
fresh; partial scores do not confer completion. Check and supported-practice
answers do not inflate ordinary practice scores, streaks, or item confidence.

The existing simulated-learner report measures practice readiness via
`lesson_mastery()`. Its course-finish figures do not include this new CLI check.
Use actual beginner playtesting to assess the extra time and difficulty.

## Verification

- `python scripts/_verify_reading_check.py`: 18 tests, including 180 generated
  checks across all 12 lessons, real CLI pass/stay behavior, hints, failure and
  retry, interruption, save/reload, old completions, and navigation bypasses.
- The recognition-only completion regression fails against the old master.
- `python scripts/_verify_gameplay_fixes.py`: all passing.
- Existing decomposition and missing-vowel/batchim verification scripts pass.
- Inspected a complete successful check using the 49-column output wrapper.

Still to validate on a phone: typing effort, naturalness of generated
combinations, perceived fairness of 4/5, and whether the supported practice
helps a beginner pass a genuinely new check.
