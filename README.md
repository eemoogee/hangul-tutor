# Hangul Tutor

A local-first Korean Hangul learning toolkit. All game logic, scoring, and drill
selection is deterministic Python — a small local LLM (via [Ollama](https://ollama.com))
is used only for creative enrichments like mnemonics and natural sentence
translation, and every tool degrades gracefully if Ollama isn't running.

## Requirements

- Python 3.10+ (standard library only — no pip installs needed)
- [Ollama](https://ollama.com) installed and running locally, with a model pulled
  (default: `qwen2.5:1.5b`) — optional. Without it, mnemonics/translations are
  skipped or replaced with instant template/self-check fallbacks.

## Configuring local models (`hangul_models.py`)

Every LLM call goes through Ollama, and each creative task can run on its own
model — start everything on one small/fast model, then upgrade individual
tasks once you know which ones actually benefit from something bigger.

**Tasks:** `mnemonic` (letter mnemonics), `encouragement` (streak messages),
`sentence` (constrained sentence generation for mini-sentences and `/talk`),
`translate` (translating a fixed Tatoeba sentence).

**Resolution order**, per task:
1. `HANGUL_MODEL_<TASK>` env var — task-specific override, e.g. `HANGUL_MODEL_MNEMONIC`
2. `--model` flag on `hangul_cli.py` — shared runtime override for every task
3. `HANGUL_OLLAMA_MODEL` env var — shared fallback
4. Hardcoded default: `qwen2.5:1.5b`

**Example — try a bigger model just for mnemonics, keep everything else fast:**

```
HANGUL_MODEL_MNEMONIC=qwen3:8b python hangul_cli.py
```

**Example — force everything to one model for a session:**

```
python hangul_cli.py --model qwen3:8b
```

The session banner shows what's active, e.g. `Model: qwen2.5:1.5b (mnemonic→qwen3:8b)`.

## Project layout

```
hangul_cli.py            Interactive tutor — lessons, adaptive quizzes, mnemonics, conversation
hangul_quiz_engine.py     Quiz engine library (lesson tracking, question generation, scoring)
hangul_conversation.py    Constrained sentence generation for the /talk command
hangul_models.py          Per-task local model configuration (see below)
hangul_flash.py           Standalone keyboard-first flashcard drill (Hangul <-> Roman)
generate_dataset.py       Builds data/reading_practice.jsonl from the curriculum + Konglish bank

data/curriculum.json           12-lesson progressive curriculum (vowels -> consonants -> batchim)
data/konglish_vocab.json       Konglish word bank (6 categories) for sound-it-out practice
data/tatoeba_kor_sentences.tsv 15,825 real Korean sentences, filtered by mastered syllables for /talk
data/reading_practice.jsonl    Generated reading-practice dataset (output of generate_dataset.py)
data/user_progress.json        Auto-created — hangul_cli.py progress (mastery, streaks, confusions)
data/flash_progress.json       Auto-created — hangul_flash.py progress (separate from the above)
```

---

## Hangul Tutor CLI (`hangul_cli.py`)

The main interactive tutor. Walks through 12 lessons (vowels, consonants,
syllable blocks, batchim) with seven quiz modes, adapts to your mistakes, and
uses Ollama for mnemonics and short constrained Korean sentences.

**Usage:**

```
python hangul_cli.py                  # Interactive mode, resumes last lesson
python hangul_cli.py --lesson 1       # Start at a specific lesson
python hangul_cli.py --mode spell     # Lock to one quiz mode for the whole session
python hangul_cli.py --sudden-death   # One wrong answer = game over, tracks streak
python hangul_cli.py --mnemonic ㄱ    # One-off: generate a mnemonic for a letter
python hangul_cli.py --model llama3.2:1b-instruct-q4_K_M   # Use a different Ollama model
```

**In-session commands:**

| Command | Effect |
|---|---|
| `/stats` | Show progress: mastery count, streak, top confusion pairs |
| `/lessons` | List all 12 lessons and completion status |
| `/lesson N` | Jump to lesson N |
| `/mode NAME` | Lock quiz mode — `spell`, `read`, `match`, `build`, `vowel`, `batchim`, `confusion`, or `auto` to unlock |
| `/mnemonic X` | Get an LLM-generated mnemonic for letter X |
| `/talk` | Read a Korean sentence built only from syllables you've mastered, then translate it |
| `/template` | Same as `/talk` but instant, no LLM |
| `/konglish` | Decode a Konglish word (sound it out, guess the English) |
| `/kspell` | Spell an English word in Hangul |
| `/hint` | Show a hint for the current question |
| `/skip` | Reveal the answer and move on |
| `/quit` | Save and exit |

**Quiz modes:** `spell`, `read_aloud`, `match_sound`, `build_syllable`,
`missing_vowel`, `batchim_challenge`, `confusion_drill`. Mode selection is
weighted by lesson content, and `confusion_drill` targets letters you've
actually mixed up — falling back to curriculum-suggested trouble pairs
(e.g. ㅓ vs ㅗ, ㅐ vs ㅔ) before you've made any real mistakes yet.

**`/talk` sentence sources, in priority order:**
1. A real sentence from the Tatoeba corpus, filtered to syllables you've mastered
2. An LLM-generated sentence, validated syllable-by-syllable and retried on failure
3. A template sentence — instant, always valid

---

## Hangul Flashcard Drill (`hangul_flash.py`)

A standalone keyboard-first flashcard tool for Hangul <-> Roman drilling. No
Hangul keyboard required — all input is ASCII.

**Two-direction drill:**
- **Hangul -> Roman:** See `ㄱ`, type `g` or `k` — plain ASCII input
- **Roman -> Hangul:** See `"g"`, pick from 4 numbered Hangul options (1-4 keys)

**Features:**
- 40 jamo across 4 sets (consonants, vowels, basic, compounds)
- Weighted randomization favors wrong/confused pairs
- Adaptive distractors prioritize known confusion pairs in R->H mode
- In-game stats (`s` key) with live tracking
- Rank system: Novice -> Beginner -> Intermediate -> Advanced -> Master
- Progress persistence: `data/flash_progress.json` (saved every 10 rounds)
- Quick lookup: `python hangul_flash.py --lookup g` or `--lookup ㄱ`

**Usage:**

```
python hangul_flash.py                  # Mixed drill, basic set (24 jamo)
python hangul_flash.py --set vowels     # Vowels only
python hangul_flash.py --set consonants # Consonants only
python hangul_flash.py --direction h2r  # Hangul->Roman only
python hangul_flash.py --direction r2h  # Roman->Hangul only (number keys)
python hangul_flash.py --hard           # All 40 jamo, including compounds
python hangul_flash.py --lookup ch      # Quick lookup: ch -> ㅊ
python hangul_flash.py --stats          # Lifetime accuracy and confusion pairs
```

Mid-session: type `s` any time to see stats without breaking the drill, `q` to
quit and save.

---

## Reading Practice Dataset Generator (`generate_dataset.py`)

Builds `data/reading_practice.jsonl` — five levels of progressively harder
reading material, all constrained to syllables covered by the curriculum by
that point, so nothing appears before it's learnable.

| Level | Content | Example |
|---|---|---|
| 1 | Single Konglish words | 바나나 -> banana |
| 2 | Short native words | 나비, 우유, 고기 |
| 3 | Two-syllable combos | 큰 개, 새 집 |
| 4 | Pattern drills | 가 나 다 라 마 바 사 |
| 5 | Short phrases (3-4 syllables) | 나는 가요 |

**Usage:**

```
python generate_dataset.py                  # 1000 entries, all levels
python generate_dataset.py --count 5000     # 5000 entries
python generate_dataset.py --level 1,2      # Only levels 1 and 2
python generate_dataset.py --output custom.jsonl --seed 7
```

Each line of output is a JSON object:
`{korean, english, level, syllables, lesson_max, source, hint}`.

---

## Notes

- `hangul_quiz_engine.py` and `hangul_conversation.py` are internal libraries
  used by `hangul_cli.py` — they aren't run directly, though each has a small
  demo under `if __name__ == "__main__":` for standalone testing.
- All progress files (`user_progress.json`, `flash_progress.json`) are created
  automatically on first run and are independent of each other.
