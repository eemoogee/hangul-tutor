# Simulated-learner playtest — 2026-10-12

**What was done:** seven simulated learners each played the whole course
(Lessons 1–12) 20 times through the real quiz engine — about 110,000
questions in total. Every question was also checked for quality: is the
answer among the choices, do two choices sound the same, does the screen
give the answer away, is a right answer ever marked wrong.

Re-run it any time (about a minute):

```
python scripts/_playtest_learners.py              # full report
python scripts/_playtest_learners.py --runs 3     # quick look
python scripts/_playtest_learners.py --rule B     # try a different mastery rule
```

It never touches `data/user_progress.json`.

## The learners

| Learner | How it behaves |
|---|---|
| strong | learns fast, ~95% accurate once warmed up |
| average | steady, ~90% once warmed up |
| struggling | slow, tops out around 85% |
| eo_o_mixer | average, but keeps mixing up ㅓ and ㅗ (65% at best, forever) |
| batchim_weak | average, but final consonants top out at 60%, forever |
| clicker | average, no Hangul keyboard — answers A–D whenever it can |
| guesser | control group: knows nothing, guesses at random |

Each learner gets better at each letter *in each position* (ㄱ at the start
of a block is a different skill from ㄱ at the bottom) every time it sees it.
They play in sittings of 120 questions with a day's break, so progress is
saved and reloaded through the real code. Time is simulated (4–12 seconds
per answer), because the engine's "is this due for review?" logic uses the
clock.

**Limitation to keep in mind:** the ㅓ/ㅗ and batchim weaknesses are hard
caps — those learners *never* improve past them, no matter how much they
practise. Real people do. So the numbers for those two learners show what
the app does *in response* to a weakness, not whether its drills would
fix one.

## Headline numbers (after today's fixes)

Questions needed to finish each lesson (median of 20 runs):

| Lesson | strong | average | struggling |
|---:|---:|---:|---:|
| 1 | 25 | 31 | 37 |
| 2 | 55 | 68 | 82 |
| 3 | 30 | 38 | 44 |
| 4 | 46 | 56 | 72 |
| 5 | 30 | 29 | 37 |
| 6 | 32 | 38 | 49 |
| 7 | 52 | 62 | 76 |
| 8 | 60 | 74 | 90 |
| 9 | 44 | 47 | 61 |
| 10 | 52 | 66 | 80 |
| 11 | 25 | 28 | 34 |
| 12 | 62 | 69 | 84 |
| **Whole course** | **512** | **614** | **751** |

At ~8 seconds an answer, the whole course is about **70 minutes** of play
for an average learner. Lessons 5 and 11 are short because many of their
blocks were already mastered in earlier lessons (가, 나, 다 … carry over
from Lesson 2; 방, 밥, 문, 먹 from Lesson 10).

The guesser never got a single item mastered in 1,500 questions, so the
mastery bar can't be passed by luck.

## Bugs found and fixed

| # | Problem | Before | After |
|---|---|---|---|
| 1 | Confusion drills, word contrasts and both nonword decoders almost never appeared. They have no item pool, so the "is anything due?" filter dropped them, and they're in neither direction bucket, so the bucket draw never picked them. | 1.1% of questions | 18.7% |
| 2 | A Lesson 1 mix-up (어↔오) never counted as "relevant to Lesson 1" (the check compared blocks against bare letters), so drills fell back to the preset ㅏ/ㅓ, ㅗ/ㅜ pairs. | ㅓ/ㅗ mixer drilled on ㅓ/ㅗ: 0 times | 88 times (27 of 73 drills in L1) |
| 3 | Mistakes made while reading aloud (≈30% of all questions) were never recorded: reading 어 as "o" is the ㅓ/ㅗ mix-up, but it was thrown away. | not recorded | recorded when it clearly matches a studied block |
| 4 | In Lessons 10–12, missing-vowel and decompose questions were picked, found a batchim block they can't handle, and silently became spelling questions. | 4,811 silent swaps; spelling = 47% of Lesson 10 | 1 swap; spelling = 23% |
| 5 | **Confusion drills printed the answer:** "which one is **a**?" followed by 아 with "a" under it and 어 with "eo" under it. Present since before PR #1. | every drill | fixed — blocks shown without labels |
| 6 | **Word contrasts printed the answer:** "물도 주세요. *Please give me water, too.* — the highlighted word means? A) more B) also / too". | translation shown first | translation shown after answering |
| 7 | A drill on a consonant pair could mix bare letters (ㅊ, ㅈ) with blocks (밖, 먹) under a prompt saying "cha". | mixed | always whole blocks (차, 자) |

Also: sequence decode and whole-word reading showed a generic ❓ icon.

All of these have regression checks in `scripts/_verify_gameplay_fixes.py`
(now 63 checks), and the new checks were confirmed to **fail on the old
code** and pass on the new.

## Design findings — your call, nothing changed

### 1. "Mastered" sometimes means "can read it about 60–75% of the time"

An item counts as mastered at confidence 2, which is about 3 right
answers. The playtest measured each learner's real reading accuracy on the
lesson's items at the moment the lesson completed:

| Learner | Average skill at "mastered" | Weakest item |
|---|---|---|
| strong | ~96% | ~94% |
| average | ~88% | ~84% |
| struggling | ~76% | ~70% (as low as 59% in Lesson 1) |
| eo_o_mixer | ~85% | **~65%** in the ㅓ/ㅗ lessons |
| batchim_weak | ~50–60% in Lessons 10–12 | **36%** in Lesson 12 |

I tested four rules (on the fixed engine) to see if a stricter bar would help:

| Rule | Average learner, whole course | Struggling learner: lessons passed with an item under 70% | Runs that got permanently stuck |
|---|---|---|---|
| A — today (confidence ≥ 2) | 617 questions | 47% | batchim_weak 1/20 |
| B — confidence ≥ 3 | 1,089 | 10% | batchim_weak **20/20** |
| C — ≥ 2 and last 2 answers right | 1,163 | 9% | struggling 13/20, batchim_weak 20/20, mixer 4/20 |
| D — ≥ 3 and last 2 answers right | 1,618 | 4% | struggling 13/20, batchim_weak 20/20, mixer 2/20 |

**Recommendation: keep rule A.** Stricter rules roughly double or triple
the course and trap weaker learners, and *none* of them helped the ㅓ/ㅗ
mixer (it still passed 58–59% of its lessons with an item under 70%, under
every rule). A specific weakness is better caught by targeted drills — which is
exactly what bugs 1–3 above had broken. Worth re-checking after the fixes
have been used for real.

### 2. Most lessons don't have a `mastery_syllables` list

The engine's comment says every lesson should have one, but only Lessons 5,
6, 11 and 12 do. The other eight fall back to their whole practice pool
(e.g. all 15 syllables in Lesson 2). It works — no stalls — but if you meant
to pick a focused set for each lesson, those eight still need one.

### 3. A learner stuck on one word just gets asked it again

In 1 of 20 runs the batchim-weak learner was asked 한국 185 times (53 right)
without finishing Lesson 12. Mostly that's the hard cap in the learner
model, but it shows the app has no other way to help: no "let's review
Lesson 10's final consonants" suggestion after many misses on one item.
A possible feature, not a bug.

### 4. Nonsense-word decoding is the hardest question type

Average learner accuracy: 3-block sequences 52%, 2-block nonwords 63%,
everything else 80–94%. That's expected (more blocks = more chances to
slip) but they're now ~7% of questions. If they feel too punishing,
`SPECIAL_MODE_RATE` and the weights in `_special_modes` in
`hangul_quiz_engine.py` are the knobs.

### 5. Word contrasts show the romanization of each word

"Which word means *hand*? 손 **son** / 선 **seon**". That doesn't give the
answer away (you still need to know which one means hand), so I left it —
but it does mean you don't have to *read* the Hangul. Your call.

### 6. Content edits from PR #1 that didn't survive the merge

`data/curriculum.json` on master has these back to their earlier versions:

- **Lesson 11's confusion pairs** (곧/곳, 밖/박, 있/잇, 낮/낫) all sound
  identical, so the drill can't use any of them. In normal play this just
  means Lesson 11 only drills mix-ups you actually made; but `/mode
  confusion` in Lesson 11 falls back to unrelated pairs like 유/요.
  PR #1 had replaced them with pairs that differ in sound (밖/밥, 옷/온,
  먹/멍, 말/만) and moved the same-sound examples into the lesson note.
- The fuller ㅓ description, "hakkyo" as an accepted reading of 학교, and
  Lesson 5 not listing ㅐ/ㅔ (taught in Lesson 7) as examples.

If that was deliberate, ignore this; if it was a merge accident, they can
be restored in one small commit.

## What looked healthy

- No grading bugs: a correct answer was never marked wrong (all accepted
  spellings, A–D letters and alternate readings like "la" for 라 tested).
- No answer-missing-from-choices, no duplicate choices, no two choices that
  sound the same.
- The mastery bar never went backwards in a typical lesson.
- The same item twice in a row: ~1% or less.
- The clicker learner (A–D only) progressed exactly as fast as the average
  learner, so not having a Hangul keyboard isn't a handicap.
- Progress survived every save-and-reload between sittings (about 5 per
  course, ~100 per learner type across the 20 runs) without a problem.
