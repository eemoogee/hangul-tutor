# The Sejong Test — Implementation Spec

**Status:** Draft spec — revised 2026-09-22 (v2)
**Date:** 2026-09-22
**Revisions:** Interactive compose (predict/reveal), baseline opt-out,
read→decode split, 1-correct threshold, First Breakthrough milestone
at 4 letters, evidence hierarchy, vertical-slice-first implementation.

---

## 1. Overview

The Sejong Test is a guided first-run experience that lets the learner
*discover empirically* that Hangul is easy to learn. It is not a quiz
mode or a gamified lesson — it is a structured experiment where the
learner is both subject and observer.

### Core thesis

> Hangul Tutor doesn't merely teach Hangul.
> It conducts an experiment on the learner, and the learner's own
> performance is the evidence.

### Milestones

| Milestone | Trigger | Message |
|-----------|---------|---------|
| **First Breakthrough** | After Batch 0 (4 letters) | "I can build syllables." |
| **Victory 1** | After Batch 1 (8 letters) | "I can read Korean." |
| **Victory 2** | After Batch 5 (24 letters) | "I know the Korean alphabet." |

First Breakthrough is a *construction* claim (I can assemble pieces).
Victory 1 is a *capability* claim (I can do something real).
Victory 2 is a *knowledge* claim (I understand a system).

### Non-goals

- This does NOT replace the 12-lesson curriculum. It front-loads
  motivation so the curriculum feels like "what I can do now that I
  know the alphabet" rather than "lessons I still have to complete."
- This does NOT use the cumulative `LearnerItem` mastery model for
  progression. It uses a session-scoped mastery counter (fast threshold,
  designed for rapid advancement, not long-term retention).
- This does NOT optimize for Konglish loanword decoding. Letter selection
  is driven by pedagogical criteria, with real Korean words used as
  reward vocabulary.

---

## 2. Design Principles

1. **Demonstrate, don't assert.** The tutor proves Hangul is easy by
   showing the learner their own learning curve, not by telling them
   "Hangul is easy."

2. **Productive, not just receptive.** The learner builds syllables and
   reads words, not just identifies letters in multiple-choice quizzes.

3. **Composition as revelation.** The core "aha" moment is discovering
   that 1 consonant × N vowels = N syllables. The tutor engineers this
   discovery, doesn't lecture it.

4. **Low threshold, rapid advance.** Mastery threshold per phase is 1
   correct performance — enough to prove competence, not enough to
   create boredom. A wrong answer triggers retry of that item (not a
   counter reset). Long-term retention is the curriculum's job.

5. **Honest framing.** If a learner takes 45 minutes, the closing screen
   doesn't pretend it was fast. It honestly says what they accomplished
   and normalizes the difficulty of specific confusions (ㅓ/ㅗ).

6. **Resumable.** If the learner quits mid-test, `/sejong` picks up
   where they left off. State persists in `data/sejong_state.json`.

---

## 3. Letter Batching Strategy

24 letters divided into 6 batches across 4 stages. Batches are ordered
by: visual simplicity → phonological usefulness → compositional power →
contrast pair availability → frequency.

### Batch definitions

```
BATCH 0 — The Revelation (4 letters)
  Consonants: ㄴ /n/    ㄷ /d/
  Vowels:     ㅏ /a/    ㅗ /o/
  
  Rationale: ㄴ is two strokes, /n/ is universal. ㄷ contrasts visually
  with ㄴ (demonstrates the "extra stroke = different letter" principle).
  ㅏ and ㅗ are the simplest vertical and horizontal vowels.
  
  Syllables: 나 노 다 도 (4 from 4 letters)
  Words: 나 (I/me), 도 (also/degree)
  Confusion pairs: ㄴ↔ㄷ, ㅏ↔ㅗ


BATCH 1 — First Words (+4 letters, 8 total)
  Consonants: ㅁ /m/    ㅂ /b/
  Vowels:     ㅓ /eo/   ㅜ /u/
  
  Rationale: ㅁ and ㅂ are visually similar (both "box-like"), teaching
  that Korean distinguishes shapes precisely. ㅓ mirrors ㅏ (left vs
  right), ㅜ mirrors ㅗ (down vs up). Each new letter pairs with a
  known letter, reinforcing the contrast-discrimination skill.
  
  New syllables: 마 모 무 머 바 보 부 버 (8 more, 12 total)
  Words: 바다 (sea), 나무 (tree), 무 (radish), 모 (cap),
         보 (barley), 두 (two), 나 (I/me)
  Confusion pairs: ㅁ↔ㅂ, ㅓ↔ㅏ, ㅜ↔ㅗ


BATCH 2 — System Power (+4 letters, 12 total)
  Consonants: ㅅ /s/    ㄱ /g,k/
  Vowels:     ㅡ /eu/   ㅣ /i/
  
  Rationale: ㅅ is visually simple (peak), ㄱ is the simplest angle.
  ㅡ and ㅣ are single strokes — the learner sees that Korean has
  vowels made of just one line. These 4 letters unlock many new
  syllables with the 4 consonants already known.
  
  New syllables: 사 소 수 스 서 기 그 가 (subset shown)
  Words: 소 (cow), 기 (flag/spirit), 바나나 (banana!)
  Confusion pairs: ㅅ↔ㅈ, ㅡ↔ㅣ


BATCH 3 — The ㅇ Rule (+2 letters, 14 total)
  Consonants: ㅇ (silent/ng)
  Vowels:     ㅑ /ya/
  
  Rationale: ㅇ is the only letter with a positional sound rule
  (silent at syllable start, /ng/ at end). This is taught as a
  discovery: 아 = silent+ㅏ, not "ng+ㅏ". ㅑ introduces the
  "y-glide" pattern (ㅏ → ㅑ = a → ya).
  
  New syllables: 아 야 (and their use in real words)
  Words: 아이 (child), 야 (hey!/field)
  Confusion pairs: ㅏ↔ㅑ, ㅇ positional rule


BATCH 4 — Core Expansion (+6 letters, 20 total)
  Consonants: ㄹ /r,l/  ㅈ /j/  ㅊ /ch/  ㅎ /h/
  Vowels:     ㅕ /yeo/  ㅛ /yo/  ㅠ /yu/
  
  Rationale: ㄹ is the most complex basic consonant (wiggly shape).
  ㅈ/ㅊ/ㅎ complete the "plain/aspirated" triad (ㅈ vs ㅊ, with ㅈ
  resembling ㄷ with a hat). ㅕ/ㅛ/ㅠ complete the y-glide vowel set.
  
  New syllables: 라 로 루 러 리 류 자 저 조 주 처 초 추 하 호 후
  Words: 나라 (country), 누리 (world), 저 (that/I)
  Confusion pairs: ㅈ↔ㅊ, ㅓ↔ㅕ, ㅗ↔ㅛ


BATCH 5 — Aspirated Close (+4 letters, 24 total)
  Consonants: ㅋ /k/  ㅌ /t/  ㅍ /p/
  Vowels:     (none new)
  
  Rationale: These are the aspirated consonants — each is visually
  "base + extra stroke" (ㄱ→ㅋ, ㄷ→ㅌ, ㅂ→ㅍ). The learner discovers
  the visual pattern: more strokes = more air. This is the simplest
  batch because the learner already knows the base forms.
  
  New syllables: 카 코 쿠 키 타 토 투 티 파 포 푸 피
  Words: 토마토 (tomato), 파 (green onion), 코 (nose)
  Confusion pairs: ㄱ↔ㅋ, ㄷ↔ㅌ, ㅂ↔ㅍ
```

### Stage grouping

```
Stage 0: REVELATION    → Batch 0          (4 letters,  ~3 min)
                          → First Breakthrough: "I can build syllables."
Stage 1: FIRST WORDS   → Batch 1          (8 letters,  ~5 min)
                          → Victory 1: "I can read Korean."
Stage 2: CORE BUILD    → Batches 2, 3, 4  (20 letters, ~10 min)
Stage 3: COMPLETE      → Batch 5          (24 letters, ~3 min)
                          → Victory 2: "I know the core alphabet."
```

Estimated total: ~20 minutes for an average learner.

---

## 4. State Machine

### Phases within each batch

```
discover → predict/reveal → recognize → retrieve → discriminate → build → decode
```

Not every batch uses every phase. `predict/reveal` is interactive
narrative (not scored). Phase assignment per stage:

```
Stage 0 (Revelation):
  discover → predict/reveal → build → decode
  (predict/reveal is interactive narrative; build and decode are scored)

Stage 1 (First Words):
  discover → recognize → retrieve → build → decode
  (full cycle — this is where Victory 1 triggers)

Stage 2 (Core Build):
  discover → recognize → retrieve → discriminate → build → decode
  (full cycle with discrimination — these batches have real confusion pairs)

Stage 3 (Complete):
  discover → retrieve → build → decode
  (abbreviated — these are "base + stroke" letters, easy to learn)
```

### Phase definitions

| Phase | Quiz mode(s) | What it proves | Threshold |
|-------|-------------|----------------|-----------|
| discover | (narrative walkthrough) | Exposure | Automatic (all letters shown) |
| predict/reveal | (interactive narrative) | Compositional understanding | Automatic (learner predicts, then sees result) |
| recognize | `match_sound` | "I can identify it" | 1 correct per letter |
| retrieve | `spell` | "I can recall it" | 1 correct per letter |
| discriminate | `confusion_drill` | "I can tell it apart" | 1 correct per confusion pair |
| build | `build_syllable` | "I can use it" | 1 correct per consonant+vowel combo |
| decode | (custom: show syllable, sound it out) | "I can decode it" | 1 correct decode |

### Transition rules

```
1. All letters in the current batch must reach threshold in the
   current phase before the phase advances.
2. When the last phase of a batch completes, the batch advances.
3. When the last batch of a stage completes, a milestone screen shows.
4. If the learner gets a question wrong, that item is retried
   (not a counter reset — the item stays in the pool until answered
   correctly once). Wrong answers are not penalized.
5. The predict/reveal phase is never scored — it is interactive
   narrative where the learner makes a prediction and then sees the
   result. No right/wrong judgment.
```

### State diagram (simplified)

```
                    ┌─────────────┐
                    │  BASELINE   │ (opt-out, 8 multiple-choice)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
              ┌────►│  DISCOVER   │
              │     └──────┬──────┘
              │            │
              │     ┌──────▼────────┐
              │     │PREDICT/REVEAL │ (interactive, unscored)
              │     └──────┬────────┘
              │            │
              │     ┌──────▼──────┐
              │     │  RECOGNIZE  │── wrong ──┐
              │     └──────┬──────┘           │
              │            │ 1 correct        │ (retry same item)
              │     ┌──────▼──────┐           │
              │     │  RETRIEVE   │── wrong ──┘
              │     └──────┬──────┘
              │            │
              │     ┌──────▼──────┐
              │     │DISCRIMINATE │── wrong ──┐
              │     └──────┬──────┘           │
              │            │                   │
              │     ┌──────▼──────┐           │
              │     │   BUILD     │── wrong ──┘
              │     └──────┬──────┘
              │            │
              │     ┌──────▼──────┐
              │     │   DECODE    │
              │     └──────┬──────┘
              │            │
              │     ┌──────▼───────────┐
              │     │ BATCH DONE       │── more batches? ──┐
              │     │ (+ milestone if  │                    │
              │     │  stage boundary) │                    │
              │     └──────┬───────────┘                    │
              │            │ last in stage                  │
              └────────────┼────────────────────────────────┘
                           │ all stages done
                    ┌──────▼──────┐
                    │ POST-TEST   │ (same 8 items as baseline)
                    │ + RESULTS   │
                    └─────────────┘
```

---

## 5. Session Mastery Model

The Sejong Test uses a **session-scoped** mastery counter, separate
from the cumulative `LearnerItem` model. This allows rapid progression
(1 correct = phase complete for that item) without the spaced-repetition
intervals that `LearnerItem.due` enforces.

### Threshold: 1 correct + retry-on-error

Each item in the current phase's pool must be answered correctly once.
A wrong answer does not reset the counter — it simply means that item
stays in the pool and will be asked again until answered correctly.

```
correct → item removed from pool → next item
wrong   → item stays in pool     → same or different item next

pool empty → phase complete
```

This keeps the experience fast (most items pass on first try) while
requiring actual successful performance (every item must be answered
correctly at least once). The cumulative `LearnerItem` system provides
longer-term evidence that one exposure is equivalent to durable
mastery — that's the curriculum's job, not the Sejong Test's.

### Data structure

```python
# Per-letter, per-phase: 1 = mastered this phase, 0 = not yet
session_mastery: dict[str, dict[str, int]]

# Example (Stage 1, retrieve phase):
{
  "ㄴ": {"recognize": 1, "retrieve": 1, "build": 0},
  "ㄷ": {"recognize": 1, "retrieve": 1, "build": 0},
  "ㅏ": {"recognize": 1, "retrieve": 1, "build": 0},
  "ㅗ": {"recognize": 1, "retrieve": 1, "build": 0},
  "ㅁ": {"recognize": 1, "retrieve": 0, "build": 0},  # not yet
  "ㅂ": {"recognize": 0, "retrieve": 0, "build": 0},  # not yet
  "ㅓ": {"recognize": 0, "retrieve": 0, "build": 0},  # not yet
  "ㅜ": {"recognize": 1, "retrieve": 0, "build": 0},  # recognize done
}
```

### Phase thresholds

```python
PHASE_THRESHOLDS = {
    "recognize": 1,      # 1 correct match_sound per letter
    "retrieve": 1,       # 1 correct spell per letter
    "discriminate": 1,   # 1 correct confusion drill per pair
    "build": 1,          # 1 correct build_syllable per combo
    "decode": 1,         # 1 correct decode per syllable
}
# predict/reveal is unscored — no threshold
```

### Interaction with cumulative model

Letters answered correctly during the Sejong Test ARE recorded in
`LearnerItem` (via the normal `answer()` path), so the cumulative
mastery model benefits. But progression decisions use only the
session-scoped counter.

This means:
- A letter "mastered" in the Sejong Test (session counter = threshold)
  may still have low cumulative confidence (LearnerItem.confidence = 1)
- After the Sejong Test, the curriculum will naturally revisit these
  letters through its spaced-repetition system
- The Sejong Test gives a head start on cumulative mastery without
  requiring full retention to advance

---

## 6. The Baseline (Opt-Out)

Before the first batch, the tutor runs a brief baseline assessment.
This is the **opt-out default** — the pre/post comparison is central
evidence for the Sejong Test's thesis, so it should not be hidden
behind a choice most first-time users would skip.

### Baseline screen

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  QUICK BASELINE
  
  Before we teach you anything — let's see
  what you already recognize.
  
  We'll show you 8 Korean letters.
  Try to guess what sound each one makes.
  
  Don't worry if you get them all wrong.
  That's normal — and it's the point.
  We'll check again later.
  
  [Enter to begin]
  [Type /skip to skip the baseline]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Baseline questions

8 multiple-choice questions, one per letter from Batches 0+1:
ㄴ, ㄷ, ㅁ, ㅂ, ㅏ, ㅓ, ㅗ, ㅜ

Each shows the letter and 4 sound options (randomized).
Score recorded in `sejong_state["baseline_score"]`.

### Post-test (after Victory 1)

After Batch 1, the same 8 letters are tested again using the same
question format. The user-facing framing:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  LET'S CHECK AGAIN
  
  Same symbols. Same question.
  No hints this time.
  
  [Enter to begin]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Results comparison

```
  BEFORE              NOW
  1 / 8               8 / 8
  
  You learned 7 new symbols
  in X minutes.
```

That is the kind of evidence the Sejong Test should produce:
the learner's own before/after is the proof.

### If the baseline score is already high (≥6/8)

The learner already knows some Korean. The post-test comparison
won't show dramatic improvement. In this case:
- Skip the post-test comparison screen
- Adjust the closing: "You already recognized most of these letters.
  Now you understand how they work together."
- Still record the baseline score for the results screen

---

## 7. Narrative Screens

All narrative screens are hardcoded strings (no LLM generation),
rendered with the existing `styled()` ANSI helper.

### 7.1 Opening Screen

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  🏛️  THE SEJONG TEST
  
  In 1443, King Sejong created Hangul —
  the Korean alphabet — with a bold idea:
  
  Writing should be simple enough for
  anyone to learn.
  
  Let's put that to the test.
  
  We'll teach you a few letters at a time.
  You'll use them immediately — to build
  syllables and read real words.
  
  No score. No timer pressure.
  Just discovery.
  
  [Enter to begin]
  
  (Or type /skip to start with regular lessons)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 7.2 The Predict/Reveal (end of Stage 0)

This is interactive — the learner predicts, then sees the result.
Not scored. Not a quiz. The point is discovery.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Now watch what happens when letters combine.
  
  You know:
    ㄴ = n
    ㅏ = a
  
  What do you think this makes?
  
        ㄴ + ㅏ = ?
  
  [Enter to reveal]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

After Enter:

```
        ㄴ + ㅏ = 나
        
  You just built your first Korean syllable.
  
  나 = "na"
  It's a real Korean word — it means "I" or "me."
  
  Let's try another:
  
        ㄴ + ㅗ = ?
  
  [Enter]
```

```
        ㄴ + ㅗ = 노
        
  Same consonant, different vowel → different syllable.
  
  One more:
  
        ㄷ + ㅏ = ?
  
  [Enter]
```

```
        ㄷ + ㅏ = 다
        
  Different consonant, same vowel → also different.
  
  Look at the pattern:
  
    ㄴ + ㅏ  =  나   (na — I/me)
    ㄴ + ㅗ  =  노   (no — old/effort)
    ㄷ + ㅏ  =  다   (da — all/every)
    ㄷ + ㅗ  =  도   (do — also/city)
  
  Four letters. Four syllables.
  That's how Korean works.
  
  Letters → Blocks → Syllables → Words.
  And you just discovered it.
  
  [Enter to try building some yourself]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 7.3 First Breakthrough (end of Stage 0, after build phase)

Shown after the learner successfully builds syllables from Batch 0
letters. Brief — this is a mini-milestone, not a full victory screen.

```
  ✦ FIRST BREAKTHROUGH ✦
  
  You just built Korean syllables from scratch.
  
    나  노  다  도
  
  Four letters → four syllables.
  You now know how the system works:
  consonants and vowels stack into blocks.
  
  Let's keep going and see what you can read.
  
  [Enter to learn 4 more letters]
```

### 7.4 Victory 1 (end of Stage 1)

After Batch 1, the post-test runs first (§6), then:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ✦ YOU CAN READ KOREAN ✦
  
  You now know 8 letters:
  
    ㄴ ㄷ ㅁ ㅂ      ㅏ ㅓ ㅗ ㅜ
  
  Let's use them. Read this word:
  
    바  다
  
  바 = ㅂ + ㅏ = ba
  다 = ㄷ + ㅏ = da
  
  바다 means "sea."
  
  And this one:
  
    나  무
  
  나무 means "tree."
  
  ─────────────────────────────────
  
  You started knowing zero Korean letters.
  Now you're reading Korean words.
  
  Time elapsed: XX:XX
  
  ─────────────────────────────────
  
  With these 8 letters, you can build
  {N} different syllables. You've already
  proven that Hangul works the way
  King Sejong intended — simple pieces
  that combine into everything.
  
  [Enter to keep going]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Where `{N}` is computed from the cross-product: 4 consonants × 4 vowels
= 16 possible syllables.

### 7.5 Stage 2 Mini-Victories

After each batch in Stage 2, a brief progress screen:

```
  ✚ 4 MORE LETTERS MASTERED
  
  New: ㅅ ㄱ ㅡ ㅣ
  
  Words you can now read:
    소 (cow)    기 (flag)    바나나 (banana!)
  
  Total letters: 12/24
  Time: XX:XX
  
  [Enter to continue]
```

### 7.6 Victory 2 / Core Complete (end of Stage 3)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ✦ CORE HANGUL MASTERED ✦
  
  You now know the basic Korean alphabet.
  
    CONSONANTS              VOWELS
    ㄱ ㄴ ㄷ ㄹ ㅁ ㅂ ㅅ       ㅏ ㅑ ㅓ ㅕ
    ㅇ ㅈ ㅊ ㅋ ㅌ ㅍ ㅎ       ㅗ ㅛ ㅜ ㅠ
                            ㅡ ㅣ
  
  24 letters. Every one of them.
  
  You haven't learned every special case.
  You haven't learned tense consonants.
  You haven't learned compound vowels.
  You haven't mastered batchim pronunciation.
  
  But you now know the core building blocks
  of the Korean writing system.
  
  Time: XX:XX
  
  [Enter to see what comes next]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 7.7 The Complexity Reveal

Shown immediately after Victory 2, on [Enter]:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  HANGUL — THE FULL PICTURE
  
  ┌──────────────┬────────────────────────┐
  │  CORE   24   │  EXTENSIONS            │
  │  ████████████ │                        │
  │  ✓ DONE      │  Tense consonants      │
  │              │  ㄲ  ㄸ  ㅃ  ㅆ  ㅉ      │
  │              │  (same shape, more air) │
  │              │                        │
  │              │  Compound vowels       │
  │              │  ㅘ ㅙ ㅚ ㅝ ㅞ ㅟ ㅢ    │
  │              │  (two vowels, one sound)│
  │              │                        │
  │              │  Batchim rules         │
  │              │  (position changes     │
  │              │   the pronunciation)   │
  └──────────────┴────────────────────────┘
  
  Everything on the right is built from
  what you already know on the left.
  
  Tense consonants? Double the letter:
    ㄱ → ㄲ    ㄷ → ㄸ    ㅂ → ㅃ
  
  Compound vowels? Merge two vowels:
    ㅗ + ㅏ = ㅘ    ㅜ + ㅓ = ㅝ
  
  Batchim? Same consonants you know,
  pronounced differently at the bottom:
    ㄱ at top = "g"    ㄱ at bottom = unreleased "k"
  
  You're not starting over.
  You're extending what you just learned.
  
  [Enter to continue your journey]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 7.8 The Learning Curve

Shown on the final results screen:

```
  YOUR LEARNING CURVE
  
  Letters
  mastered
  24 ┤                                    ●
  20 ┤                              ●
  16 ┤                        ●
  12 ┤                  ●
   8 ┤            ●
   4 ┤      ●
   0 ┤●
     └──┬───┬───┬───┬───┬───┬───┬───┬───┬──
        0   3   6   9  12  15  18  21  24
                      minutes
  
  Average: {rate} letters per minute
  Fastest batch: Batch {N} ({time})
  Trickiest: {letter} (took {attempts} attempts)
```

The curve data is computed from `mastery_events` timestamps.

### 7.9 Closing Callback

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  SEJONG TEST COMPLETE
  
  Remember how Korean looked when you started?
  
  Those strange blocks and lines — 
  they seemed impossibly complex.
  
  Now you know what they are.
  You know how the system works.
  You can build syllables and read words.
  
  You proved King Sejong right.
  
  [Enter to continue with full lessons]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 8. The Predict/Reveal Phase

The predict/reveal phase is unique to the Sejong Test. It is
**interactive narrative** — not a quiz, not scored, not tracked in
`session_mastery`. Its purpose is to let the learner *experience*
composition as discovery rather than being *told* about it.

### Design principle

The learner predicts what a letter combination produces, then sees
the result. They are never expected to already know — the interaction
exists to create prediction and surprise, not assessment.

### Stage 0 Predict/Reveal

After discovering ㄴ, ㄷ, ㅏ, ㅗ (see §7.2 for the full interactive
sequence). The key interaction:

```
  You know:  ㄴ = n   ㅏ = a
  
  What do you think this makes?
  
        ㄴ + ㅏ = ?
  
  [Enter to reveal]
```

→ reveals `나`

Then the tutor shows the cross-product pattern:
- Same consonant + different vowels → different syllables
- Different consonant + same vowel → different syllables
- Letters combine freely — every consonant × every vowel

This is the central revelation. It must be interactive (learner
predicts before seeing) rather than passive (tutor shows all four at
once), because prediction makes the discovery the learner's own.

### Stage 1 Predict/Reveal

After discovering ㅁ, ㅂ, ㅓ, ㅜ (8 letters total), the tutor shows
the expanded cross-product:

```
  With your 4 new letters, you can now build:
  
    Consonants:  ㄴ  ㄷ  ㅁ  ㅂ
    Vowels:      ㅏ  ㅓ  ㅗ  ㅜ
  
  That's 4 × 4 = 16 possible syllables:
  
      나  너  노  누
      다  더  도  두
      마  머  모  무
      바  버  보  부
  
  Sixteen syllables from eight letters.
  And some of these are real Korean words:
  
      바다 (ba-da) = sea
      나무 (na-mu) = tree
      두   (du)    = two
  
  [Enter to start quizzing]
```

The syllable count is computed dynamically from the cross-product
of mastered consonants × mastered vowels using `_compose_syllable()`.

### Implementation

The predict/reveal phase is NOT routed through the quiz engine.
It is a scripted narrative sequence with `input()` prompts for
[Enter] and `print()` for reveals. No `QuizQuestion` is created,
no `answer()` is called, no `session_mastery` is updated.

```python
def run_predict_reveal(self, batch_idx: int):
    """Interactive narrative — predict a syllable, then see it."""
    batch = SEJONG_BATCHES[batch_idx]
    pairs = [
        (batch["consonants"][0], batch["vowels"][0]),
        (batch["consonants"][0], batch["vowels"][-1]),
        (batch["consonants"][-1], batch["vowels"][0]),
    ]
    for cho, jung in pairs:
        syl = self.quiz._compose_syllable(cho, jung)
        print(f"\n  {cho} + {jung} = ?")
        input(f"  {styled('[Enter to reveal]', CYAN)} ")
        print(f"\n  {cho} + {jung} = {styled(syl, BOLD, GREEN)}")
    # Then show the cross-product grid
    self._show_composition_grid()
```

---

## 9. The Decode Phase

The decode phase measures **reading ability** — can the learner sound
out Hangul syllables? It is deliberately separated from vocabulary
knowledge (knowing what a Korean word means).

### Why separate decode from meaning

The Sejong Test's claim is: "You learned to read the writing system."
If the read phase required identifying word meanings, then:
- A learner who can decode `바다` but doesn't know it means "sea"
  would fail — incorrectly suggesting they can't read
- A learner who already knows `바다` from prior exposure would pass
  without actually decoding — incorrectly suggesting the tutor worked

Decoding is the primary evidence. Real-word meaning is a motivational
payoff shown *after* successful decoding, not part of the assessment.

### Decode question format

```
Decode this:

  누 도

Sound out each block:
  누 = ? + ? = ?
  도 = ? + ? = ?

Type the romanization:
  > nudo

✓ Correct: nu-do
```

The learner types the romanization. The tutor checks it against
the expected romanization (derived from `_compose_syllable` inverse).
No meaning is asked.

For multi-syllable words (used in later stages as a reward):

```
Decode this:

  바 다

  > bada

✓ Correct: ba-da

바다 means "sea" — you just read a Korean word.
```

The meaning is revealed **after** successful decoding, as a reward,
not as part of the question.

### Implementation

```python
def _decode_question(self) -> QuizQuestion:
    """Show a syllable or word, ask for its romanization."""
    syllables = self._pick_decodable_syllables()
    target = syllables[0]  # single syllable for early stages
    cho, jung, jong = self.quiz._decompose_syllable(target)
    expected_roman = self.quiz._hangul_to_roman_hint(target)
    
    prompt = f"Decode this:\n\n  {target}\n\n"
    prompt += f"Type the romanization:"
    
    return QuizQuestion(
        mode="decode",
        prompt=prompt,
        correct_answer=expected_roman,
        choices=None,  # open-ended, not multiple choice
        hint=f"Break it apart: {cho} + {jung}" + (f" + {jong}" if jong else ""),
        lesson_id=f"sejong_decode",
        letter=target,
    )
```

### Decode pool selection

The decode pool is computed from the cross-product of all introduced
consonants × all introduced vowels. Single syllables for Stages 0-1,
multi-syllable words (from `SEJONG_WORDS`) for Stages 2-3.

### Real-word payoff (post-decode, not scored)

After a successful decode, if the syllable happens to be a real Korean
word (looked up in `SEJONG_WORDS`), show:

```
  ✓ Correct: ba-da
  
  바다 means "sea" — you just read a Korean word.
```

If it's not a real word, just confirm:

```
  ✓ Correct: nu-do
```

This keeps decoding as the primary evidence while making real words
an emotional bonus.

---

## 10. Data Structures

### sejong_state.json

```json
{
  "version": 1,
  "active": true,
  "started_at": "2026-09-22T14:30:00",
  "stage": 1,
  "batch": 1,
  "phase": "retrieve",
  "letters_introduced": ["ㄴ", "ㄷ", "ㅏ", "ㅗ", "ㅁ", "ㅂ", "ㅓ", "ㅜ"],
  "session_mastery": {
    "ㄴ": {"recognize": 1, "retrieve": 1, "build": 0},
    "ㄷ": {"recognize": 1, "retrieve": 0, "build": 0},
    "ㅏ": {"recognize": 1, "retrieve": 1, "build": 0},
    "ㅗ": {"recognize": 1, "retrieve": 1, "build": 0},
    "ㅁ": {"recognize": 1, "retrieve": 0, "build": 0},
    "ㅂ": {"recognize": 0, "retrieve": 0, "build": 0},
    "ㅓ": {"recognize": 0, "retrieve": 0, "build": 0},
    "ㅜ": {"recognize": 1, "retrieve": 0, "build": 0}
  },
  "mastery_events": [
    {"letter": "ㄴ", "phase": "recognize", "at": "2026-09-22T14:32:15"},
    {"letter": "ㅏ", "phase": "recognize", "at": "2026-09-22T14:32:45"},
    {"letter": "ㄷ", "phase": "recognize", "at": "2026-09-22T14:33:10"},
    {"letter": "ㅗ", "phase": "recognize", "at": "2026-09-22T14:33:40"},
    {"letter": "ㄴ", "phase": "retrieve", "at": "2026-09-22T14:35:00"},
    {"letter": "ㅏ", "phase": "retrieve", "at": "2026-09-22T14:35:30"}
  ],
  "baseline_score": null,
  "baseline_answers": {},
  "first_breakthrough_at": null,
  "victory_1_at": null,
  "victory_2_at": null,
  "posttest_score": null,
  "completed": false,
  "best_time_seconds": null,
  "words_decoded": ["나", "도"],
  "syllables_built": ["나", "노", "다", "도"]
}
```

### Computed fields (not stored, derived at display time)

- `elapsed_minutes`: `(now - started_at).total_seconds() / 60`
- `learning_curve_data`: from `mastery_events` timestamps
- `total_syllables_buildable`: cross-product of introduced consonants × vowels
- `letters_per_minute`: `len(letters_introduced) / elapsed_minutes`
- `best_time`: persisted across retakes (separate from current run time)

---

## 11. Integration with Existing Codebase

### New file: `sejong_test.py`

```
sejong_test.py
├── SejongTest class
│   ├── __init__(quiz: HangulQuiz)
│   ├── start()           — initialize state, show opening screen
│   ├── resume()          — resume from saved state
│   ├── run_phase()       — execute current phase (discover/compose/quiz)
│   ├── advance_phase()   — check threshold, advance or retry
│   ├── advance_batch()   — move to next batch, show progress screen
│   ├── advance_stage()   — move to next stage, show victory screen
│   ├── show_victory_1()  — Victory 1 narrative screen
│   ├── show_victory_2()  — Victory 2 + complexity reveal
│   ├── show_learning_curve() — ASCII learning curve
│   ├── run_baseline()    — opt-out before-test (8 multiple-choice)
│   ├── run_posttest()    — after batch 1, compare to baseline
│   ├── compute_buildable_syllables() — cross-product
│   ├── compute_readable_words() — filter SEJONG_WORDS
│   ├── save_state()      — write sejong_state.json
│   └── load_state()      — read sejong_state.json
├── SEJONG_BATCHES         — list of batch definitions
├── SEJONG_STAGES          — list of stage definitions (phase sequences)
├── SEJONG_WORDS           — dict of decodable words by letter set
├── PHASE_THRESHOLDS       — dict of phase → threshold count
└── NARRATIVE_SCREENS      — dict of screen name → formatted string
```

### Changes to existing files

#### `hangul_cli.py`

1. **Import sejong_test module** (top of file):
   ```python
   from sejong_test import SejongTest
   ```

2. **Modify `show_start_menu()`** (line ~561):
   - Add Sejong Test option for users with no progress:
   ```python
   has_progress = quiz.progress.get("total_questions_answered", 0) > 0
   sejong_state = SejongTest.load_state()
   
   if not has_progress and not sejong_state:
       # First ever launch — offer the Sejong Test
       print(f"   [Enter] Start — The Sejong Test (recommended)")
       print(f"   [a]     Alphabet Walkthrough — meet all 24 letters first")
       print(f"   [l]     Lesson list — pick any lesson")
       print(f"   [s]     Skip — start with regular lessons")
       print(f"   [q]     Quit")
   elif sejong_state and not sejong_state.get("completed"):
       # Sejong Test in progress — offer to resume
       print(f"   [Enter] Resume — The Sejong Test (Stage {stage+1})")
       print(f"   [a]     Alphabet Walkthrough")
       print(f"   [l]     Lesson list")
       print(f"   [q]     Quit")
   ```

3. **Add `/sejong` command** to slash-command dispatch (line ~1300):
   ```python
   elif cmd == "/sejong":
       sj = SejongTest(quiz)
       if sj.state and not sj.state.get("completed"):
           sj.resume()
       elif sj.state and sj.state.get("completed"):
           sj.show_results()
       else:
           sj.start()
   ```

4. **Add `/sejong` to MODE_ALIASES or help text** so users can discover it.

#### `hangul_quiz_engine.py`

**No changes required.** The Sejong Test works by:
- Creating a temporary lesson dict with the current batch's letters and
  computed practice_syllables
- Calling `quiz.next_question(mode=phase_mode, lesson=custom_lesson)`
  — wait, `next_question()` doesn't take a lesson parameter currently.

**Option A (preferred):** Add an optional `lesson` parameter to
`next_question()`:
```python
def next_question(self, mode: str = None, lesson: dict = None) -> QuizQuestion:
    lesson = lesson or self.current_lesson
    ...
```

**Option B:** Set `self.current_lesson` temporarily before calling
`next_question()`, then restore it. This is fragile and should be
avoided.

**Decision:** Option A. The change is a 1-line default assignment and
doesn't affect existing callers.

#### `data/curriculum.json`

**No changes required.** The Sejong Test defines its own batches
independently of the 12-lesson curriculum. After the test completes,
the tutor maps mastered letters to the appropriate curriculum lesson
for continuation.

---

## 12. Quiz Question Generation for Sejong Phases

The Sejong Test constructs constrained lesson dicts to feed the
existing quiz engine:

```python
def _make_sejong_lesson(self, batch_idx: int) -> dict:
    """Build a lesson dict for the quiz engine from a Sejong batch."""
    batch = SEJONG_BATCHES[batch_idx]
    consonants = batch["consonants"]
    vowels = batch["vowels"]
    
    # All letters in this batch + all previously introduced
    all_consonants = self._all_introduced_consonants()
    all_vowels = self._all_introduced_vowels()
    
    # Compute practice syllables from cross-product
    practice_syllables = []
    for c in all_consonants:
        for v in all_vowels:
            syl = self.quiz._compose_syllable(c, v)
            practice_syllables.append(syl)
    
    return {
        "id": f"sejong_{batch_idx}",
        "title": f"Sejong Batch {batch_idx}",
        "letters": batch["consonants"] + batch["vowels"],
        "practice_syllables": practice_syllables,
        "confusion_pairs": batch.get("confusion_pairs", []),
        "pronunciation": batch.get("pronunciation", {}),
    }
```

### Phase → mode mapping

```python
PHASE_TO_MODE = {
    "recognize": "match_sound",
    "retrieve": "spell",
    "discriminate": "confusion_drill",
    "build": "build_syllable",
    # "decode" is a custom question type (see §9)
    # "predict/reveal" is unscored narrative (see §8)
}
```

### Decode phase implementation

The decode phase doesn't map to an existing quiz mode. It's a custom
question generated by the Sejong Test itself (full spec in §9).
Unlike the old read phase, decode asks for romanization (not meaning),
keeping the evidence clean: "I can read the writing system."

```python
def _decode_question(self) -> QuizQuestion:
    """Show a syllable, ask for its romanization."""
    target = self._pick_decodable_syllable()
    cho, jung, jong = self.quiz._decompose_syllable(target)
    expected_roman = self.quiz._hangul_to_roman_hint(target)
    
    prompt = f"Decode this:\n\n  {target}\n\n"
    prompt += f"Type the romanization:"
    
    return QuizQuestion(
        mode="decode",
        prompt=prompt,
        correct_answer=expected_roman,
        choices=None,  # open-ended input
        hint=f"Break it apart: {cho} + {jung}" + (f" + {jong}" if jong else ""),
        lesson_id=f"sejong_decode",
        letter=target,
    )
```

---

## 13. Post-Test Flow

After the Sejong Test completes (Victory 2 + Complexity Reveal):

1. **Mark state as completed:**
   ```python
   state["completed"] = True
   state["completed_at"] = datetime.now().isoformat()
   ```

2. **Map progress to curriculum:**
   - All 24 core letters have `LearnerItem` entries with at least
     1 correct answer each (from the quiz phases)
   - The curriculum's Lesson 1 (basic vowels) and Lesson 2 (basic
     consonants) are largely covered
   - Set `current_lesson` to the first lesson that introduces letters
     NOT in the core set (likely Lesson 3 or 4, which cover tense/
     aspirated/compound letters)
   - Mark earlier lessons as completed if all their letters were
     mastered during the test

3. **Continue with normal curriculum:**
   - The learner proceeds through lessons 3-12
   - These now feel like "extensions" (as framed by the Complexity
     Reveal screen) rather than "lessons I haven't done"
   - The quiz engine's spaced-repetition naturally reinforces the
     core letters while introducing extensions

4. **The `/sejong` command shows results:**
   ```
   SEJONG TEST RESULTS (completed YYYY-MM-DD)
   
   Time: XX:XX
   Letters: 24/24
   Syllables built: N
   Words decoded: N
   
   [r] Retake the test
   [Enter] Back to lessons
   ```

---

## 14. Edge Cases

### Resumption

If the learner quits mid-test:
- `sejong_state.json` persists the current stage, batch, phase, and
  all mastery counters
- On next launch, `show_start_menu()` offers "Resume — The Sejong Test"
- The learner picks up at the exact question they were on

### Struggling learners

If a letter takes many attempts (>5 wrong answers):
- Show an encouraging screen:
  ```
  ㅓ and ㅗ look almost identical — even Korean
  learners mix them up. The trick:
  
    ㅓ points LEFT  (think: "left" = "eo")
    ㅗ points UP   (think: "up" = "o", mouth opens upward)
  ```
- Don't change the threshold — just give a hint and let them retry
- Track "struggled_letters" in state for the results screen

### Fast learners

If a learner breezes through (<10 minutes):
- The learning curve will show a steep ascent — that's the reward
- The closing screen adjusts tone:
  ```
  Time: 9:42
  
  King Sejong said a wise person could learn
  Hangul in a morning. You did it in under ten minutes.
  ```

### Quitting during a narrative screen

If the learner Ctrl+C during a narrative screen:
- The state is saved at the last phase transition
- On resume, the narrative screen is shown again (it's idempotent)

### The learner already knows some Korean

If the baseline scores high (≥6/8):
- Skip the post-test comparison (it won't show much improvement)
- Still run the full test — the composition and building phases
  are valuable even for learners with partial knowledge
- Adjust the closing screen:
  ```
  You already knew most of these letters.
  Now you understand how they work together —
  how letters combine into syllables,
  and how syllables combine into words.
  ```

---

## 15. Implementation Phases

### Vertical Slice First

The first implementation milestone is NOT all 24 letters. It is the
smallest complete experience that proves (or disproves) the core
design thesis:

```
BASELINE → BATCH 0 → BATCH 1 → VICTORY 1 → POST-TEST
```

This slice includes:
- The opt-out baseline (8 questions)
- The first 4 letters with predict/reveal + build + decode
- First Breakthrough milestone
- The next 4 letters with recognize + retrieve + build + decode
- The post-test comparison
- Victory 1 screen

If this slice produces the intended "I can read Korean" realization
in a real test with a naive learner, the remaining 16 letters are
straightforward extension. If it doesn't, the redesign is contained
to 8 letters rather than 24.

### Phase 1: Vertical Slice (estimated: 3 sessions)

- [ ] Create `sejong_test.py` with `SejongTest` class skeleton
- [ ] Define `SEJONG_BATCHES[0:2]` (first two batches only)
- [ ] Implement state load/save (`sejong_state.json`)
- [ ] Implement baseline (8 multiple-choice questions, opt-out)
- [ ] Implement `discover` phase (letter walkthrough for Batch 0)
- [ ] Implement `predict/reveal` phase (interactive, unscored)
- [ ] Implement `build` phase (wrapping `build_syllable`)
- [ ] Implement `decode` phase (custom: show syllable, type romanization)
- [ ] First Breakthrough screen
- [ ] Implement `recognize` and `retrieve` phases for Batch 1
- [ ] Session mastery tracking (1 correct + retry-on-error)
- [ ] Post-test (same 8 questions as baseline)
- [ ] Before/after comparison screen
- [ ] Victory 1 screen
- [ ] Add optional `lesson` parameter to `next_question()`
- [ ] Wire `/sejong` command into CLI
- [ ] Wire into `show_start_menu()` for first-run detection
- [ ] Test with clean `data/user_progress.json`

### Phase 2: Full Alphabet (estimated: 2 sessions)

- [ ] Define `SEJONG_BATCHES[2:6]` (remaining four batches)
- [ ] Implement `discriminate` phase (wrapping `confusion_drill`)
- [ ] Implement Batch 3 special handling (ㅇ positional rule discovery)
- [ ] Implement Batch 5 special handling (aspirated pattern discovery)
- [ ] Stage 2 mini-victory screens
- [ ] Victory 2 + Complexity Reveal screens
- [ ] Learning curve ASCII visualization
- [ ] Closing callback screen
- [ ] Best-time persistence across retakes

### Phase 3: Integration & Polish (estimated: 1 session)

- [ ] Post-test curriculum mapping (set current_lesson)
- [ ] Edge cases (resumption, struggling learners, fast learners)
- [ ] Resumability test (quit mid-test, relaunch, verify state)
- [ ] End-to-end test: clean install → Sejong Test → curriculum continuation

### Phase 4: Tuning (estimated: ongoing)

- [ ] Adjust batch ordering based on real learner data
- [ ] Tune phase thresholds (may need 2 correct for some phases)
- [ ] Add more words to `SEJONG_WORDS` as needed
- [ ] Refine narrative screen text based on feedback

---

## 16. Open Questions — RESOLVED (v2)

All five original questions have been decided:

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | Compose interactive? | **Yes — predict/reveal, not scored** | Prediction makes the discovery the learner's own, not a demonstration they watched |
| 2 | Victory 1 at 4 or 8? | **8 letters** (4 gets First Breakthrough) | 4 proves construction; 8 proves reading. Both are milestones but Victory 1 should be the bigger claim |
| 3 | Pre-test opt-in/out? | **Opt-out (baseline)** | The before/after is central evidence, not optional gamification |
| 4 | Persist best time? | **Yes, subordinate to learning result** | Gives retakes a reason; but the learning curve is the primary artifact |
| 5 | Reorder letters? | **Keep current order, ㅇ stays in Batch 3** | The positional-rule discovery is stronger after the learner understands consonant+vowel composition |

### Additional decisions (v2)

| Decision | Resolution |
|----------|------------|
| `read` phase conflates decoding with meaning | **Split**: `decode` (primary evidence, asks for romanization) + real-word payoff (post-decode, motivational) |
| Threshold contradiction (2 correct vs 1 correct) | **1 correct + retry-on-error** — fast progression, actual performance required |
| Should compose be routed through quiz engine? | **No** — it's interactive narrative (`input()`/`print()`), never scored |
| Implementation approach | **Vertical slice first**: baseline → Batch 0 → Batch 1 → Victory 1 → post-test. This slice proves (or disproves) the core experience before implementing all 24 letters |

---

## 17. Evidence Hierarchy

The Sejong Test produces multiple types of evidence. They are not
equal. This hierarchy guides what goes on the results screen and
what gets emphasized in narrative screens.

### Primary evidence (what the Sejong Test actually proves)

1. **Pre/post baseline comparison** — the learner's own before/after
   is the strongest evidence that learning happened
2. **Successful symbol retrieval** — the learner can recall letter→sound
3. **Successful syllable construction** — the learner can assemble pieces
4. **Pure decoding** — the learner can sound out unfamiliar Hangul
5. **Number of letters mastered** — cumulative count (24/24)
6. **Elapsed learning time** — how fast the primary evidence accumulated

### Secondary / motivational evidence (emotional payoff, not proof)

- Real Korean words decoded (바다 = sea)
- Word meanings revealed after successful decoding
- Personal-best time (for retakes)
- Historical framing (King Sejong)
- Achievement names and milestone screens
- Cross-product syllable count ("16 syllables from 8 letters")

### What the results screen prioritizes

```
SEJONG TEST COMPLETE

24 / 24 CORE LETTERS                    ← primary #5
18:42                                    ← primary #6
                                         ← primary #1 (if baseline ran)
  Before: 1/8    Now: 8/8

LEARNING CURVE                           ← primary #6 visualized
  4 letters    3:02
  8 letters    6:47
  12 letters   9:31
  ...
  24 letters  18:42

Personal best: 17:03                     ← secondary (subordinate)
```

The learning curve is the scientific result. The personal best is
just a reason to try again. Real words are shown during the test as
motivational payoff, not on the results screen as evidence.

---

## Appendix A: Complete Batch Definitions

```python
SEJONG_BATCHES = [
    {
        "id": 0,
        "name": "The Revelation",
        "consonants": ["ㄴ", "ㄷ"],
        "vowels": ["ㅏ", "ㅗ"],
        "pronunciation": {
            "ㄴ": "n (as in 'no')",
            "ㄷ": "d (soft, between 'd' in 'do' and 't' in 'stop')",
            "ㅏ": "a (as in 'father')",
            "ㅗ": "o (as in 'go')",
        },
        "confusion_pairs": [["ㄴ", "ㄷ"], ["ㅏ", "ㅗ"]],
        "mnemonics": {
            "ㄴ": "A knee, bent and ready to kneel. 🦵",
            "ㄷ": "A door, propped open on its hinge. 🚪",
            "ㅏ": "An arm reaching right as your mouth opens — 'ah'! 👉",
            "ㅗ": "A little flag, planted proudly on its pole. 🚩",
        },
        "phases": ["discover", "predict/reveal", "build", "decode"],
    },
    {
        "id": 1,
        "name": "First Words",
        "consonants": ["ㅁ", "ㅂ"],
        "vowels": ["ㅓ", "ㅜ"],
        "pronunciation": {
            "ㅁ": "m (as in 'mom')",
            "ㅂ": "b (soft, between 'b' in 'bus' and 'p' in 'spin')",
            "ㅓ": "eo (uh, as in 'sun' — not 'uh-oh')",
            "ㅜ": "u (oo, as in 'moon')",
        },
        "confusion_pairs": [["ㅁ", "ㅂ"], ["ㅓ", "ㅏ"], ["ㅜ", "ㅗ"]],
        "mnemonics": {
            "ㅁ": "A square mouth, lips pressed together, humming 'mmm'. 👄",
            "ㅂ": "A tiny table standing on two legs. 🪑",
            "ㅓ": "The mirror image of ㅏ — pointing left instead. 👈",
            "ㅜ": "An umbrella, handle hanging down. ☂️",
        },
        "phases": ["discover", "predict/reveal", "recognize", "retrieve", "build", "decode"],
    },
    {
        "id": 2,
        "name": "System Power",
        "consonants": ["ㅅ", "ㄱ"],
        "vowels": ["ㅡ", "ㅣ"],
        "pronunciation": {
            "ㅅ": "s (as in 'sun')",
            "ㄱ": "g/k (soft, between 'g' in 'go' and 'k' in 'skate')",
            "ㅡ": "eu (like 'oo' in 'book' but flatten your lips)",
            "ㅣ": "ee (as in 'see')",
        },
        "confusion_pairs": [["ㅅ", "ㅈ"], ["ㅡ", "ㅣ"]],
        "mnemonics": {
            "ㅅ": "A mountain summit. ⛰️",
            "ㄱ": "Looks like a golf club mid-swing! ⛳",
            "ㅡ": "A flat horizon line — flat mouth, no rounding. 〰️",
            "ㅣ": "A person standing tall and thin, saying 'ee'. 🧍",
        },
        "phases": ["discover", "recognize", "retrieve", "discriminate", "build", "decode"],
    },
    {
        "id": 3,
        "name": "The ㅇ Rule",
        "consonants": ["ㅇ"],
        "vowels": ["ㅑ"],
        "pronunciation": {
            "ㅇ": "silent at syllable start; 'ng' at syllable end",
            "ㅑ": "ya (like 'ya' in 'yard')",
        },
        "confusion_pairs": [["ㅏ", "ㅑ"]],
        "mnemonics": {
            "ㅇ": "A balloon — silent as it floats... until it lands with a boiNG! 🎈",
            "ㅑ": "Like ㅏ, but waving with both hands — 'ya ya ya!' 👋",
        },
        "phases": ["discover", "recognize", "retrieve", "build", "decode"],
        "special": "silent_ng_rule",  # triggers the ㅇ positional discovery sequence
    },
    {
        "id": 4,
        "name": "Core Expansion",
        "consonants": ["ㄹ", "ㅈ", "ㅊ", "ㅎ"],
        "vowels": ["ㅕ", "ㅛ", "ㅠ"],
        "pronunciation": {
            "ㄹ": "r/l (flap r like 'tt' in 'butter', or l at syllable end)",
            "ㅈ": "j (soft, between 'j' in 'jump' and 'ch' in 'church')",
            "ㅊ": "ch (aspirated, like 'ch' in 'church' with a puff of air)",
            "ㅎ": "h (as in 'hello')",
            "ㅕ": "yeo (like 'yuh' — the y-version of ㅓ)",
            "ㅛ": "yo (like 'yo!' — the y-version of ㅗ)",
            "ㅠ": "yu (like 'you' — the y-version of ㅜ)",
        },
        "confusion_pairs": [["ㅈ", "ㅊ"], ["ㅓ", "ㅕ"], ["ㅗ", "ㅛ"]],
        "mnemonics": {
            "ㄹ": "A wiggly river, bending back and forth. 🌊",
            "ㅈ": "A person mid-jump, leg kicking out behind. 🤸",
            "ㅊ": "Jumping and cheering, with a little spark above! 🎉",
            "ㅎ": "A face wearing a little top hat. 🎩",
            "ㅕ": "Like ㅓ, waving both hands the other way. 🙌",
            "ㅛ": "A flag with two flaps, fluttering. 🎏",
            "ㅠ": "An umbrella with two spokes — extra rainy. 🌧️",
        },
        "phases": ["discover", "recognize", "retrieve", "discriminate", "build", "decode"],
    },
    {
        "id": 5,
        "name": "Aspirated Close",
        "consonants": ["ㅋ", "ㅌ", "ㅍ"],
        "vowels": [],
        "pronunciation": {
            "ㅋ": "k (strongly aspirated, like 'k' in 'kite' with a big puff)",
            "ㅌ": "t (strongly aspirated, like 't' in 'time' with a big puff)",
            "ㅍ": "p (strongly aspirated, like 'p' in 'pie' with a big puff)",
        },
        "confusion_pairs": [["ㄱ", "ㅋ"], ["ㄷ", "ㅌ"], ["ㅂ", "ㅍ"]],
        "mnemonics": {
            "ㅋ": "A key with an extra tooth. 🔑",
            "ㅌ": "The middle prong of a trident. 🔱",
            "ㅍ": "Goalposts on a soccer field. 🥅",
        },
        "phases": ["discover", "retrieve", "build", "decode"],
        "special": "aspirated_pattern",  # triggers the "extra stroke = more air" discovery
    },
]
```

## Appendix B: Decodable Word List (Partial)

```python
SEJONG_WORDS = [
    # Batch 0 words (ㄴㄷ + ㅏㅗ)
    {"ko": "나", "en": "I / me", "batch": 0},
    {"ko": "도", "en": "also / degree", "batch": 0},
    {"ko": "노", "en": "old / effort", "batch": 0},
    
    # Batch 1 words (+ㅁㅂㅓㅜ)
    {"ko": "바다", "en": "sea", "batch": 1},
    {"ko": "나무", "en": "tree", "batch": 1},
    {"ko": "무", "en": "radish", "batch": 1},
    {"ko": "모", "en": "cap / wool", "batch": 1},
    {"ko": "두", "en": "two", "batch": 1},
    {"ko": "보", "en": "barley / treasure", "batch": 1},
    {"ko": "누", "en": "who (archaic)", "batch": 1},
    
    # Batch 2 words (+ㅅㄱㅡㅣ)
    {"ko": "소", "en": "cow", "batch": 2},
    {"ko": "기", "en": "flag / spirit", "batch": 2},
    {"ko": "바나나", "en": "banana", "batch": 2},
    {"ko": "나비", "en": "butterfly", "batch": 2},
    {"ko": "고기", "en": "meat / fish", "batch": 2},
    {"ko": "기다", "en": "to crawl", "batch": 2},
    {"ko": "시다", "en": "sour", "batch": 2},
    {"ko": "마시다", "en": "to drink", "batch": 2},
    
    # Batch 3 words (+ㅇㅑ)
    {"ko": "아이", "en": "child", "batch": 3},
    {"ko": "야", "en": "hey! / field", "batch": 3},
    {"ko": "아가", "en": "baby", "batch": 3},
    
    # Batch 4 words (+ㄹㅈㅊㅎㅕㅛㅠ)
    {"ko": "나라", "en": "country", "batch": 4},
    {"ko": "누리", "en": "world", "batch": 4},
    {"ko": "저", "en": "that / I (humble)", "batch": 4},
    {"ko": "하늘", "en": "sky", "batch": 4},
    {"ko": "하루", "en": "one day", "batch": 4},
    
    # Batch 5 words (+ㅋㅌㅍ)
    {"ko": "토마토", "en": "tomato", "batch": 5},
    {"ko": "파", "en": "green onion", "batch": 5},
    {"ko": "코", "en": "nose", "batch": 5},
    {"ko": "크다", "en": "to be big", "batch": 5},
]
```

## Appendix C: ASCII Learning Curve Algorithm

```python
def render_learning_curve(mastery_events: list, total_minutes: int) -> str:
    """Render an ASCII line chart of cumulative letters mastered over time."""
    if not mastery_events:
        return ""
    
    # Build cumulative count at each minute mark
    max_minutes = max(20, total_minutes + 2)
    width = 40
    height = 8
    
    # Count letters mastered (unique letter+phase reaching threshold)
    # at each minute boundary
    curve_points = []
    for minute in range(0, max_minutes + 1, max(1, max_minutes // width)):
        count = sum(
            1 for e in mastery_events
            if (parse_time(e["at"]) - start_time).total_seconds() / 60 <= minute
        )
        curve_points.append((minute, count))
    
    # Render (simplified — full implementation would use asciichartpy
    # or a hand-rolled Bresenham line renderer)
    # ...
    return chart_string
```

For the initial implementation, a simple step-function chart works:

```
  24 ┤                                    ●
  20 ┤                              ●
  16 ┤                        ●
  12 ┤                  ●
   8 ┤            ●
   4 ┤      ●
   0 ┤●
     └──┬───┬───┬───┬───┬───┬───┬───┬───┬──
        0   3   6   9  12  15  18  21  24
```

Each `●` is placed at the (minute, cumulative_letters) coordinate.
Lines connect the dots with simple ASCII characters.




-----------------------------------------------------------

9-22-2026 feedback from GPT:

I’ve got the spec. It’s a much more concrete version of the idea we were discussing: the **Sejong Test as a first-run experiment**, with two explicit victories—“You can read Korean” at 8 letters and “I know the Korean alphabet” at 24. 

My main reaction is that **the conceptual direction is now very strong**. In particular, I think these choices are exactly right:

* **Demonstrate rather than assert** that Hangul is easy. 
* Make the learner **produce/build things**, rather than merely recognize symbols. 
* Make **composition itself the revelation**: one consonant × multiple vowels suddenly generates multiple syllables. 
* Keep the Sejong Test's mastery threshold deliberately lightweight because **long-term retention belongs to the normal curriculum**. 
* Don't distort the curriculum around Konglish just to produce flashy early words. 

I would, however, make **one important conceptual change before implementing it**:

### Don't think of this primarily as a 24-letter speedrun.

The strongest thing in the spec is actually **Stage 0**. Four symbols produce a genuine conceptual breakthrough:

> ㄴ + ㅏ → 나
> ㄴ + ㅗ → 노
> ㄷ + ㅏ → 다
> ㄷ + ㅗ → 도

The learner discovers that the same consonant can combine with different vowels and vice versa. 

That is the moment where the product proves its thesis.

I'd therefore treat the experience as three increasingly impressive discoveries:

**1. "I can recognize Korean letters."**
↓
**2. "Wait—I can *build* Korean syllables."**
↓
**3. "Wait—I know the whole basic alphabet."**

The current Victory 1 wording—**"You can read Korean"**—is compelling, but the spec's own Stage 0 already gives the learner a potentially even earlier emotional victory: **"I just figured out how Korean writing works."**

That distinction matters because your larger goal isn't simply getting people through 24 symbols quickly. It's making them think:

> **"Korean writing isn't this mysterious thing I imagined. I understand the mechanism."**

And the existing spec is actually very close to accomplishing that.

I would also keep the **before/after experiment**. The pretest is arguably one of the most distinctive parts of the entire design: the learner sees themselves go from essentially random guessing to 8/8 on the same symbols.  That's much stronger evidence of "look how quickly you learned this" than a timer alone.

So my recommendation before coding would be:

**Preserve the architecture, but make the learner's discoveries—not elapsed time—the primary drama.** The timer and learning curve should be evidence of what happened, rather than the thing the learner is trying to optimize.

That would make the Sejong Test feel less like a gamified lesson and much more like the **demonstration experiment you originally envisioned**.
