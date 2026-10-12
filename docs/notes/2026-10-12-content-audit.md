# Content audit — 2026-10-12

**The question:** the lessons felt unnatural and not engaging for casual
learners. Why, and what can be done with the content itself?

**How it was done:** a brand-new user's first session was played and the
screens read as a casual learner would see them; every learner-facing
string was then read (curriculum, mnemonics, prompts, feedback, word
lists, example sentences). Every Korean word and sentence that was added
was proofread, and every new lesson word is machine-checked to be readable
with only the letters taught so far (see the end). Example sentences are
shown only after answering, as exposure, so they may use letters not yet
taught.

## What was wrong

1. **No real words until Lesson 12.** Lessons 1–11 drilled letters and
   meaningless syllables (가, 나, 다…). A learner could finish Lesson 9
   without ever being told they'd just read 아빠 (dad) or 토끼 (rabbit).
   The only real words were an occasional "reward" every 5 correct answers.
2. **Textbook voice.** Lesson 4 was "Basic Consonants 3 — Affricate and
   aspirated consonants". Notes were long, jargon-heavy paragraphs
   ("jamo", "consonant slot", "placeholder"); four lessons had no note.
3. **The best content was hidden.**
   - Hand-written mnemonics existed for 24 letters, but only the first
     letter of each lesson showed one; the rest needed `/mnemonic`.
   - `formation` (ㅐ = ㅏ + ㅣ) and Lesson 1's `example_words` existed in
     the curriculum and were never displayed.
   - 16 letters (ㅐ ㅔ ㄲ ㅘ …) had no mnemonic at all.
4. **Flat, repetitive feedback.** "✅ Perfect! **아** is correct." after
   every right answer (with literal asterisks before PR #1);
   "romanizes as" jargon; two boilerplate lines under every question.
5. **A miss explained nothing for vowels:** "How it works: ㅏ = 아 /
   a = a".

## What changed

### Every lesson now has real words — 129 of them

Each lesson 1–11 lists real words built **only from letters taught so
far** (checked automatically — a word with an untaught letter fails the
verifier). They appear in four places:

- **The lesson opener** promises three of them.
- **A new "🌟 Real Word!" question** (~1 in 10 questions): read the word,
  then find out what it means.
- **When a lesson is mastered**, the app lists the words you can now read.
- **Lesson 10's batchim table** uses them as examples (물 water, 밥 rice…).

| Lesson | A few of its words |
|---|---|
| 1 | 아이 child, 오이 cucumber, 오 five |
| 2 | 나무 tree, 우리 we, 어머니 mother, 고기 meat |
| 3 | 바다 sea, 버스 bus, 나비 butterfly, 바나나 banana |
| 4 | 커피 coffee, 피자 pizza, 사자 lion, 토마토 tomato |
| 5 | 고구마 sweet potato, 모자 hat, 두부 tofu |
| 6 | 우유 milk, 여우 fox, 야구 baseball, 이야기 story |
| 7 | 개 dog, 노래 song, 시계 clock, 카메라 camera |
| 8 | 사과 apple, 돼지 pig, 의자 chair, 가위 scissors |
| 9 | 아빠 dad, 토끼 rabbit, 코끼리 elephant, 찌개 stew |
| 10 | 물 water, 밥 rice, 사랑 love, 친구 friend, 음악 music |
| 11 | 옷 clothes, 꽃 flower, 숲 forest, 닭 chicken |

### Lesson openers, before and after

Before:

```
── Lesson 4: Basic Consonants 3 ──
   Affricate and aspirated consonants
Watch for these look-alikes:
   ㅈ vs ㅊ · ㄱ vs ㅋ · ㄷ vs ㅌ · ㅂ vs ㅍ
Let's practice →
```

After:

```
── Lesson 4: Breathy Consonants ──
   Six letters with a puff of air — hello, 커피 (coffee)!

🎯 By the end you can read: 커피 coffee · 피자 pizza · 사자 lion

💡 Spot the pattern: ㅋ is ㄱ with an extra line, ㅌ is ㄷ with an extra
   line, ㅊ is ㅈ with a little mark on top. Extra stroke = extra puff of air.

👀 Look-alikes to watch for:
   ㅈ vs ㅊ · ㄱ vs ㅋ · ㄷ vs ㅌ · ㅂ vs ㅍ
Let's go →
```

All 12 titles, goal lines and notes were rewritten the same way: one
short, plain idea per lesson, with an example.

### The reference table shows everything it has

Every letter now shows its pronunciation, how it's built (for compound
vowels), and its mnemonic:

```
   ㅐ (ae)  —  e, as in 'bed'  [ㅏ + ㅣ]
        Looks like a ladder — climb it saying 'eh!' 🪜
```

Mnemonics now say their sound link outright ("A golf club mid-swing —
'g' for golf! ⛳") and there are 16 new ones, built on two patterns the
learner can reuse: *extra stroke = extra puff of air* (ㅋ ㅌ ㅊ ㅍ) and
*doubled = tight, no puff* (ㄲ ㄸ ㅃ ㅆ ㅉ). ㅙ ㅚ ㅞ are introduced as
"the three 'we' twins — same sound, different spelling".

### Friendlier questions and feedback

- Question names a casual learner can parse: *Spell It, Find the Sound,
  Build the Block, Take It Apart, Look-alikes, Which Word?, Made-up Word,
  Real Word!* (was *Match Sound, Decompose Syllable, Confusion Drill,
  Nonword Decode…*).
- Varied praise (*Yes! / Nice! / Spot on! / That's it!…*) and kinder
  misses: "❌ Not quite — 아 is read a (you typed 'zz')." No more
  "romanizes as".
- Short choices on one line (`A) 어   B) 으   C) 아   D) 오`) — easier to
  scan and it keeps the question on a phone screen.
- The "type the answer or pick A–D · /hint for a nudge" reminder shows for
  the first 4 questions of a session instead of under every question.
- A miss on a vowel now explains the silent ㅇ — "ㅇ (silent) + ㅏ = 아 —
  the ㅇ makes no sound, so it's just 'a'" — and shows the mnemonic for the
  letter you're learning.
- Skipping a real word still tells you what it means.

### More word pairs that teach a contrast

Six new pairs, each aimed at the confusion its lesson teaches: 우리/오리
(we/duck, ㅜ/ㅗ), 고기/거기 (meat/there, ㅗ/ㅓ), 비/피 (rain/blood, ㅂ/ㅍ),
기자/기차 (reporter/train, ㅈ/ㅊ), 달/딸 (moon/daughter, ㄷ/ㄸ), 방/빵
(room/bread, ㅂ/ㅃ). Each has a simple example sentence shown after you
answer.

### Korean and correctness fixes

- **Word pairs ignored where a letter sits.** 손/선 (hand/line) appeared
  from Lesson 3 because ㅅ, ㅗ and ㄴ are taught by then — but a *final*
  ㄴ isn't taught until Lesson 10. The readability check now knows letter
  positions, so these pairs wait for the batchim lessons.
- **Lesson 11's confusion pairs** all sounded identical (곧/곳, 밖/박…),
  so the drill couldn't use them; replaced with pairs that differ in sound
  (밖/밥, 옷/온, 먹/멍, 말/만), and the same-sound examples moved into the
  lesson note where they teach the rule.
- 학교 accepts "hakkyo" (how it's actually said); Lesson 5 no longer lists
  ㅐ/ㅔ as examples two lessons before they're taught; pronunciation guides
  tightened (ㅡ: "say 'oo', but keep your lips flat, like a grimace").
- Real words accept famous spellings where they exist (김치 → "kimchi").

## Left alone, on purpose

- **`data/reading_practice.jsonl`** has unnatural multi-word phrases
  ("새 발 = new foot", "작은 날 = small day", plain-form sentences like
  "나는 본다 = I look"). The app never shows them — the reward only uses
  single words — and the file is generated by `generate_dataset.py`, so
  hand edits would be lost. If the generator is used again, its phrase
  templates are worth rewriting in everyday 요-form ("커피 주세요").
- **Romanization under word-pair choices** (손 *son* / 선 *seon*) — it
  doesn't give the answer away, but it does remove the reading step.

## Bigger ideas for next time

1. **A sentence per lesson in Lesson 12-style "read it, then see it"** —
   e.g. Lesson 10: "물 주세요" (water, please). Needs grammar the course
   doesn't teach yet (주세요), so it should be presented as "a phrase to
   recognise", not "you can read this".
2. **Use the lesson words in the games.** Hangul Rain and the conveyor
   currently drop single syllables; dropping real words (and showing the
   meaning when you clear one) would make the games feel like reading.
3. **A review session** that mixes the words of every finished lesson —
   good for coming back after a break.
4. **Phone width.** `/chart y` is 56 columns wide and wraps on a narrow
   phone screen; the title screen chart is ~45 columns.

## Checks

- `python scripts/_verify_gameplay_fixes.py` — 73 checks, 10 of them new
  for content: every word readable by its lesson, ≥4 words in lessons 1–11,
  word pairs gated by final consonants, real-word grading and meaning,
  lesson words never served as "not a real word", every letter in lessons
  1–9 has a mnemonic, every lesson's screens render.
- `python scripts/_playtest_learners.py` — real words are 8–10% of
  questions in every lesson; lesson length barely moved (within ±5
  questions for the average learner — Lesson 6 grew most, 38 → 43);
  no question shows its answer on screen; no grading bugs.
