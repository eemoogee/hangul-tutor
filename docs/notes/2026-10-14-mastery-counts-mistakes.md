# Mistakes, hints and skips now count — 2026-10-14

**The problem.** An item (a letter, block or word) is "solid" when its
confidence score reaches 2. The old score was
`round(5 × accuracy × min(1, answers/8))`. For the first 8 answers that
reduces to `round(5 × right/8)`, so **wrong answers didn't count at all**.
3 right and 5 wrong was "solid", and a lesson could be marked done while
the learner was still missing its letters most of the time. A right answer
after `/hint` counted the same as one without help, and `/skip` recorded
nothing, so skipping the hard ones could never hold a lesson back.

## The new rule

Each item remembers its last 8 answers.

> **score = right answers in the last 8 − mistakes in the last 4**
> (then scaled to 0–5 the same way as before: 3 → solid)

- 3 right in a row is still solid, just as fast as before.
- A recent mistake cancels a right answer: 3 right mixed with 5 wrong is
  not solid.
- A mistake stops counting after 4 more answers, so a slip while you're
  still learning doesn't hold an item back for long.
- `/hint`, then a right answer: still right, still keeps your streak, but
  counts as neither right nor wrong for the score.
- `/skip` counts as a mistake on that item (and ends the streak, as
  before).

Progress saved before this change only has totals. Those are turned into a
history of the same size, with the mistakes placed first (oldest).

## Why 4 and not all 8

Measured with `scripts/_playtest_learners.py --runs 20 --quick --seed 7`.
It used the same simulated learners as the 2026-10-12 report and changed
only the scoring rule.

| Rule | Average learner, whole course | Struggling learner, whole course | Struggling: lessons "done" with some item still under 70% | Batchim-weak learner finishes the course |
|---|---|---|---|---|
| before (mistakes ignored) | 626 questions | 773 | 41% | 19 of 20 runs |
| mistakes count half, last 8 | 678 (+8%) | 951 (+23%) | 31% | 14 of 20 |
| **mistakes count, last 4 (chosen)** | **752 (+20%)** | **990 (+28%)** | **22%** | **13 of 20** |
| mistakes count, last 8 | 866 (+38%) | 1,414 (+83%) | 12% | 0 of 20 |

At the simulated 4–12 seconds per answer, the chosen rule takes the
average learner about 84 minutes for the whole course, up from 71.

The strictest rule is the most honest, but it nearly doubles the course
for a struggling learner. That brings back the "it keeps going with no
sense of progress" problem. The chosen rule removes about half the
lessons that were "done" too early, for a fifth more questions.

None of the rules help the ㅓ/ㅗ mixer: 58% under every rule. The
2026-10-12 report found the same. That learner can *never* improve past
65% (a hard cap in the simulator), so only targeted drills can catch it,
not a stricter bar.

## Getting stuck

The batchim-weak learner can never read final consonants better than 60%
(another hard cap). Under the new rule it sometimes can't finish Lessons
10–12. A real learner in that spot would just see an endless lesson. So
the end-of-round card now spots a stuck learner: at least 3 rounds in, and
nothing new became solid during the last round. Then it says *"A tough
one — fine to move on and come back later"* and offers `[n]` for the next
lesson, without marking the current one done. In Lesson 12, which has no
next lesson, it points to `/lessons` instead. (`/next` always allowed
leaving. The card just never said so.)

The simulator doesn't use the card, so its stall counts above are still
the "never finished on its own" numbers.

## Also fixed in the Conveyor game

- Choices are numbered 1–4, but only A–D was accepted. Typing `3` was
  graded wrong even when choice 3 was right.
- The hint was printed under every question before you answered, which
  often gave the answer away. It's now behind `/hint`, which works in the
  Conveyor too.
- Literal `**asterisks**` in questions and feedback, and a doubled mark
  ("✗ ❌ Not quite…").

## Checks

`python scripts/_verify_gameplay_fixes.py` now has 116 checks. 34 are new
and cover:

- the scoring rule, with old-progress conversion;
- hint and skip, in the engine and in the real CLI loop;
- the stuck offer;
- the Conveyor fixes.

On the old code, the key cases fail: 3 right + 5 wrong is "solid", `3`
doesn't pick choice 3, and the hint and `**` are both on screen. A full
playtest found no question-quality problems and no grading bugs.
