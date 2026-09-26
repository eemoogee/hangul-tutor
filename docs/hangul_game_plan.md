# Hangul CV Game — Design Plan & Task Queue

## 1. Project Overview

A suite of simple games teaching Korean consonant-vowel (CV) pair construction and decomposition, aimed at beginner Hangul learners. Built as CLI game modes inside `hangul-tutor`, with architecture kept browser-convertible from the start. Each game wraps the existing `hangul_quiz_engine.py` rather than building a new learning engine. The educational target is active retrieval — the player constructs or decomposes CV pairs on every turn, not just recognizes pre-built syllables.

Target users: hangul-tutor learners, classroom students (solo and eventual multiplayer).

---

## 2. Core Design Principles

These apply to every game variant regardless of format.

**Require production, not recognition.**
Rank prompt types by educational value:
1. `ㄷ + ㅗ → type 도` (best — construction)
2. `도 → select/type ㄷ + ㅗ` (strong — decomposition)
3. Coordinate → syllable, syllable → coordinate (useful)
4. Recognition only / locate visible cell (weakest — avoid as primary mechanic)

**Vary retrieval direction.**
A learner who can read 도 may still fail to produce it from ㄷ + ㅗ. Rotate among:
- Jamo → syllable block
- Syllable block → jamo
- Romanization → syllable block
- Syllable block → consonant or vowel identity

**Use small inventories deliberately.**
Start with 3×3 (e.g., ㄱ ㄴ ㄷ × ㅏ ㅓ ㅗ = 9 pairs). Add one consonant or vowel after ~85–90% accuracy. Don't expose the full CV space until confidence is established.

**Give diagnostic feedback, not just right/wrong.**
Example:
> Prompt: `ㄴ + ㅓ` — You answered: `노`
> `노` uses ㄴ correctly, but its vowel is ㅗ. ㅓ makes `너`.

**Earned reveal on grid games.**
Unclaimed cells show `?`. The board is not an answer key — it's a record of what the player has earned.

**Browser-ready architecture from day one.**
- Keep game logic (state, turn management, scoring) fully separate from display/input
- Use simple data structures (dicts, lists) for state — easy to serialize to JSON later
- No terminal-specific libraries in game logic layer (curses etc. goes in a thin CLI wrapper only)

---

## 3. Game Concepts — Ranked by Consensus

All three AI sources (DeepSeek, ChatGPT, Perplexity) were consulted. Rankings reflect consensus across ease of coding, replay value, and educational effectiveness.

### Tier 1 — Build first

**Conveyor-Belt Sorter** (Coding 5/5 · Replay 4/5 · Education 4/5)
Stream of CV prompts. Player routes each to the correct lane (consonant, vowel, or syllable). Timed or untimed. Highest retrieval density per minute. Best first prototype — essentially a prompt loop with a score counter.

**Territory Grid / CV Fusion** (Coding 5/5 · Replay 4/5 · Education 5/5)
Labeled grid: rows = consonants, columns = vowels. Player clicks/selects a cell, must answer a CV prompt correctly to claim it. Computer claims random cells. Win by completing a row or column. Cells show `?` until claimed (earned reveal). Beginner mode shows romanization; advanced shows nothing.

### Tier 2 — Build second

**Hangul Battleship** (Coding 4/5 · Replay 5/5 · Education 4/5)
Hidden CV targets on a jamo-labeled board. Player fires by constructing a syllable from a coordinate. Hit/miss feedback. Best game-feel of the options. Prototype: 5 hidden single-cell targets, 10 shots, 5×5 board.

**Sequence Duel / CV Chain** (Coding 5/5 · Replay 4/5 · Education 5/5)
Cumulative memory chain. Each round replays prior pairs and adds one new one. Alternates construction and decomposition directions. Maximum educational value per line of code. Good as a daily challenge mode.

### Tier 3 — Future consideration

**Hangul Drop** (Tetris-style falling CV blocks)
Most complex build. High concept but separate project scope. Revisit after Tier 1–2 are stable.

**Micro-Deck Builder**
CV pairs as playable cards. Highest long-term replay potential. More state management required. Good stretch goal.

---

## 4. Challenge Engine — Bridge to hangul_quiz_engine.py

**Do not build a new challenge engine.** `hangul_quiz_engine.py` (120 KB, ~60 methods) is a mature, adaptive quiz engine. The games hook into it; they don't replace it.

### Key seams for game integration

| Entry point | Purpose |
|---|---|
| `next_question(mode=...)` | Generate the next prompt |
| `_generate_question(mode=...)` | Direct question generation |
| `answer(user_input, question, response_ms=...)` → `QuizResult` | Grade a response |
| `lesson_mastery()` | Completion gate |
| `LearnerItem.confidence` | Adaptive signal — which pairs need more work |
| `MASTERY_CONFIDENCE` / `MASTERY_FRACTION` | Mastery thresholds |

### Most relevant existing question types for CV games

| Method | What it does | Game use |
|---|---|---|
| `_build_syllable_question` | Assemble syllable from parts | Primary — construction direction |
| `_missing_vowel_question` | Which vowel completes this syllable | Primary — decomposition direction |
| `_spell_question` | Type Hangul for a romanization | Beginner mode prompts |
| `_read_aloud_question` | Romanize a displayed syllable | Reverse direction |
| `_match_sound_question` | Pick Hangul for a sound | Alternative prompt type |
| `_confusion_drill_question` | Drill the learner's own confusions | Adaptive difficulty |

### Audit task (before building)
Confirm `_build_syllable_question` and `_missing_vowel_question` cover both construction and decomposition directions for bare CV pairs (no batchim). If gaps exist, extend rather than replace.

---

## 5. Hangul-Tutor Integration

### Architecture decision
Games are a new **game mode** inside hangul-tutor, selectable from `hangul_cli.py` menus alongside existing lesson/quiz modes.

### Integration points
- **Entry:** New menu option in `hangul_cli.py` → routes to game selection → launches chosen game
- **Prompt generation:** Game calls `next_question(mode=...)` or a thin CV-specific wrapper
- **Grading:** Game calls `answer()` and reads `QuizResult` for correctness + diagnostic text
- **Mastery tracking:** Game writes back through existing `_record_learner_item` — progress persists in learner profile
- **Adaptive difficulty:** Read `LearnerItem.confidence` to weight which CV pairs appear more in game prompts

### CLI vs browser plan
- **Phase 1:** CLI only — thin display/input layer over game logic
- **Phase 2 (future):** Browser front-end — game logic unchanged, only swap the I/O layer
- **Constraint now:** No terminal-specific code (curses, etc.) inside game logic. CLI wrapper only.

### Open questions
- Does `hangul_cli.py` have a clean plugin/mode registration pattern, or will adding a game mode require modifying the menu logic directly?
- Should games share a learner session with the current lesson, or run as standalone scored sessions?
- Multiplayer (classroom) is out of scope for Phase 1 but worth keeping in mind for state design.

---

## 6. Task Queue

Ordered by recommended build sequence. Each task is self-contained.

### Phase 1 — Foundation

- [x] **Audit `_build_syllable_question` and `_missing_vowel_question`** ✅
  Completed. Findings: construction direction exists but over-scaffolded (prompt hands both jamo to learner). Decomposition direction (block → jamo) was entirely absent across the engine. Both gaps addressed — see below.

- [x] **Add `_decompose_syllable_question`** ✅ (commit dcd527d)
  New question type: show a syllable block (e.g. 도), player produces jamo pair (ㄷ + ㅗ). Bare CV only. Grading is order-enforced, formatting-normalized. Wired into gating, dispatch, grading, and CLI render. Drawing at ~13% in CV lessons, matching build_syllable rate.

- [x] **Fix `_missing_vowel_question` batchim bug** ✅ (commit dcd527d)
  Added missing `if jong` guard. Lessons 10–11 (100% batchim) were mis-grading every question on the vowel alone — 22 syllables. Now correctly degrades to spell.

- [ ] **Design game state interface**
  Define a simple shared data structure (Python dict or dataclass) for game state: current board/track, scores, turn count, active CV inventory, last prompt, last result. Must be JSON-serializable. Estimate: 1 session.

- [ ] **Build CLI I/O wrapper**
  Thin layer: render game state to terminal, accept input, return to game logic. No game logic inside this layer. Estimate: 1 session.

### Phase 2 — First Game: Conveyor-Belt Sorter

- [ ] **Build Conveyor-Belt Sorter game logic**
  Prompt loop, lane routing, streak counter, score, diagnostic feedback on wrong answers. Untimed first. Hook into `next_question` / `answer()`.

- [ ] **Add timing mode**
  Optional countdown per prompt. Difficulty setting: generous / standard / blitz.

- [ ] **Connect to hangul_cli.py menu**
  Add game as selectable mode. Confirm mastery tracking writes back correctly.

### Phase 3 — Second Game: Territory Grid / CV Fusion

- [ ] **Build grid game logic**
  4×4 board (4 consonants × 4 vowels). Earned reveal (`?` on unclaimed cells). Player turn: select cell → answer prompt → claim or lose turn. Computer turn: claim random unclaimed cell. Win condition: complete a row or column.

- [ ] **Add beginner/advanced mode toggle**
  Beginner: show romanization in row/column headers. Advanced: jamo only.

- [ ] **Connect to hangul_cli.py menu**

### Phase 4 — Additional Games

- [ ] **Hangul Battleship**
  5×5 jamo-labeled board. 5 hidden targets. 10 shots. Gate each shot behind a CV construction prompt.

- [ ] **Sequence Duel / CV Chain**
  Cumulative chain mode. Cap at 5–7 items. Alternate construction and decomposition. Good daily challenge candidate.

### Phase 5 — Future / Browser

- [ ] **Browser conversion**
  Swap CLI I/O wrapper for a web front-end (HTML/CSS/JS). Game logic layer unchanged.

- [ ] **Multiplayer / classroom mode**
  Revisit architecture for shared game state across players.

- [ ] **Hangul Drop (Tetris-style)**
  Separate scoping session needed before adding to queue.

### Phase 6 — Core Experience Polish (low priority, post-game)

- [ ] **Play-test current lesson flow after recent bug fixes**
  Before changing anything, play a full lesson and note where it feels aimless or endless. Determine whether problems are structural or just framing. Do this before any UX changes below.

- [ ] **Add round intro screen**
  Display scope at lesson start: focus letters, keyword anchor if applicable.
  Model: letslearnhangul.com "New letters for this round" screen. No engine changes — CLI display only.

- [ ] **Add visible progress indicator during quiz**
  Show question N of X so the learner knows the session has an endpoint. Requires agreeing on a question cap per session if one doesn't exist.

- [ ] **Investigate question cap / session length**
  Determine whether the engine already enforces a session length or draws from the pool until mastery thresholds are hit. If the latter, consider a soft cap with a "keep going?" prompt rather than an endless loop.

---

## 7. Deferred Bugs — Known, Not Fixed

These were identified during active work sessions. Not urgent, not forgotten.

**`_missing_vowel_question` — bare jamo in pool (intermittent)**
`_select_from_pool` can return a bare jamo rather than a composed block. This causes `_decompose_syllable` to return `('', '', '')`, and `''` gets injected into the vowel options list. Intermittent — only appears when pool contains bare jamo entries. Pre-existing, out of scope for the decompose_syllable session.

**`_build_syllable_question` — prompt leaks the decomposition answer**
The prompt prints `Consonant: ㄷ | Vowel: ㅗ` — exactly what `_decompose_syllable_question` asks the learner to produce. If both modes run in the same lesson, `build_syllable` can telegraph the answer to the next decompose prompt. Flagged with a `⚠️ KNOWN ISSUE` comment in the code (commit dcd527d). Fix requires a curriculum-sequencing decision: gate `build_syllable` to earlier lessons, or suppress the jamo display in later ones.

**`curriculum.json` — `block_rules` orphaned**
`block_rules` was added to lesson 1 (vertical/horizontal vowel layout rules with examples). No code currently reads it. Content is correct and useful — it's waiting for a feature that doesn't exist yet. The `note` field it was originally paired with has been restored alongside it.

