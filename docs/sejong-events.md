# Sejong Test — event contract (v1)

**Status:** agreed interface, 2026-10-16. Both sides build against this file: `sejong_flow.py` (Python, produces events) and `web/app.js` (browser, draws them). The terminal wrapper `/sejong` draws the same events. Change this file first, then the code.

Related: `docs/sejong-test-spec.md` (what the experience is), `data/sejong.json` (letters, words, every narrator line), `docs/tasks/2026-10-16_engine-for-web.md` (engine changes this depends on).

## The rule

**Python decides; the screen draws.** Python chooses every question, grades every answer, and picks every narrator line, with placeholders already filled in. The renderer chooses only layout, animation, and button labels like "Continue". If a renderer has to decide what to *say* or whether an answer was right, the contract is missing something; add it here instead.

This is the same pattern as `lesson_flow.py` (plain dicts with a `"kind"` key), so `ReadingCheckFlow` habits carry over.

## Python API

```python
flow = SejongFlow(quiz, content, seed=None)   # quiz: HangulQuiz(persist=False) in the browser
events = flow.start()                          # first run
events = flow.submit(answer: str, active_ms: int = 0)
events = flow.resume(reason: str)              # "reopen" | "pause"
text   = flow.export_state()                   # JSON str: quiz progress + flow position + timer
flow   = SejongFlow.from_state(quiz, content, text)
```

- `content` is `data/sejong.json`, parsed.
- `seed` makes question order repeatable for tests.
- `answer` is the text typed, or the exact `choices` string tapped. `""` means a tap on a "continue" prompt.
- Commands: `"/hint"` (only when the current question says `hint_available`), `"/quit"`. Anything else starting with `/` returns a `notice` and changes nothing.
- `active_ms` is the active time since the previous call, already idle-capped by the renderer (see Timer). Python ignores time sent before the first Batch 0 `letter_intro`; it adds later time to the saved total.
- `resume("reopen")` after the app is reopened from saved state; `resume("pause")` after the page comes back from being hidden or idle. Each returns the right narrator line, then repeats the current screen so the renderer can redraw it.
- Every returned list ends with exactly one `await` or one `finished` event.

## Display rules for renderers

1. Show events in list order.
2. `narrator`, `letter_intro`, `reveal`, `word_read` and `milestone` each occupy the screen until the learner taps. The tap is handled locally: **no Python call**. Then show the next event.
3. `stage` updates the header and shows nothing by itself.
4. `result` replaces the practice or check question card it answers (same `qid`) and waits for a local tap. Baseline and post-test answers go directly to the next question or the final `score`, without per-question feedback.
5. On `await`, show the input and send the answer with `submit()`.
6. Unknown `kind`: skip it and log it. Unknown fields: ignore them. Python may add fields without breaking older renderers.
7. After every `submit()`, save `flow.export_state()` (browser: IndexedDB).

## Events

All events are dicts. **Bold** fields are always present; others may be absent.

### `narrator`
A line from Jeong or Sejong.

| Field | Type | Notes |
| --- | --- | --- |
| **speaker** | `"jeong"` \| `"sejong"` | Drives the name tag / portrait |
| **text** | str | Final text, placeholders filled |
| **line_id** | str | Key path in `sejong.json`, e.g. `"lines.intro.2"`, `"words.바다.first_read_line"`. For playtest notes. |
| **source** | `"real…"` \| `"invented"` | Copied from `sejong.json`. A renderer may style real quotes differently. |

### `stage`
Header update when the batch or phase changes.

| Field | Type | Notes |
| --- | --- | --- |
| **batch_id** | int | 0 or 1 in the slice |
| **batch_name** | str | "The Revelation" |
| **phase** | str | `intro`, `baseline`, `discover`, `predict_reveal`, `recognize`, `retrieve`, `build`, `decode`, `check`, `post_test`, `done` |
| **letters_known** | list[str] | Every letter taught so far, in teaching order |

### `letter_intro`
One new letter, one screen.

| Field | Type | Notes |
| --- | --- | --- |
| **jamo** | str | "ㄷ" |
| **type** | `"consonant"` \| `"vowel"` | |
| **roman** | str | Revised Romanization, "d" |
| **sound** | str | "a soft d, between …" |
| **shape** | str | The Haerye-based explanation |
| **shape_source** | str | `"haerye"` |
| related | str | A known letter this one builds on ("ㄴ" for ㄷ). Lets the renderer show the two side by side, so the learner sees the relationship before Jeong explains it. |
| notice_line | narrator | Jeong's observation, if the letter has one |

### `predict`
Unscored guess before a block is revealed. Always followed by an `await` with `input: "choice"`.

| Field | Type | Notes |
| --- | --- | --- |
| **consonant** | str | "ㄴ" |
| **vowel** | str | "ㅏ" |
| **choices** | list[str] | 3 blocks, one correct, built only from known letters |

### `reveal`
The block assembles. Comes after the predict answer, whatever was picked.
After a wrong prediction, the next event is a `narrator` from `lines.predict_wrong.side` or `.stack` (matching the target vowel's layout), followed by `lines.predict_reveal`. A right prediction goes straight to `lines.predict_reveal`.

| Field | Type | Notes |
| --- | --- | --- |
| **block** | str | "나" |
| **parts** | [str, str] | ["ㄴ", "ㅏ"] |
| **layout** | `"side"` \| `"stack"` | Vertical vowels (ㅏ ㅓ ㅣ) sit beside the consonant; horizontal ones (ㅗ ㅜ ㅡ) sit below. Drives the animation. |
| **roman** | str | "na" |
| meaning | str | "I, me" if the block is a word |
| guessed_right | bool | Whether the predict choice matched |

### `question`
One question card.

| Field | Type | Notes |
| --- | --- | --- |
| **qid** | str | Unique within the run, e.g. `"b0-build-7"` |
| **context** | `"practice"` \| `"baseline"` \| `"check"` \| `"check_practice"` \| `"post_test"` | Check and baseline cards look plainer: no streak, no hint |
| **mode** | str | Engine mode (`build_syllable`, `read_aloud`, `match_sound`, …). For logs and styling only. |
| **prompt** | str | Instruction line, e.g. "How do you read this?" |
| **display** | str | The big glyph, block or word. May be `""` when the prompt says it all. |
| parts | list[str] | For build questions: the pieces to show |
| **input** | `"choice"` \| `"text"` | |
| choices | list[str] | Present when `input == "choice"` |
| **hint_available** | bool | |
| round | {index, size} | Position in the current phase, for the round bar. `size` can grow if a missed item is re-queued. |

Build cards offer at least one distractor with the same consonant and a different vowel, and one with the same vowel and a different consonant. Batch 1 asks only blocks containing a new Batch 1 letter.

### `result`
The grade for a practice or check question. Baseline and post-test questions emit no `result`; only their final `score` is shown. The renderer shows the useful fact first, then the line.

| Field | Type | Notes |
| --- | --- | --- |
| **qid** | str | Matches the question |
| **correct** | bool | |
| **answer** | str | What the learner gave |
| **correct_answer** | str | Display form |
| chosen_is | str | If the wrong answer is another real letter/block, what it is ("ㅋ") |
| tell | str | The confusion-pair tell from `sejong.json` ("ㄷ has the extra stroke on top.") |
| line | narrator | Jeong's reaction, if any. Correct practice lines are occasional; a streak at 5/10/15 uses its streak line here instead. After three consecutive wrong practice answers in one phase, this is `lines.repeated_miss`. Absent on check cards. |
| **streak** | int | Current streak after this answer (0 after a miss) |
| requeued | bool | True when a missed item will come back later this phase |

### `word_read`
The payoff after a real word is read correctly for the first time.

| Field | Type | Notes |
| --- | --- | --- |
| **ko** | str | "바다" |
| **roman** | str | "bada" |
| **en** | str | "sea" |
| line | narrator | The `first_read_line`, if the word has one |

### `hint`
| Field | Type |
| --- | --- |
| **qid** | str |
| **text** | str |

The question stays open; the next `await` is for the same `qid`. A hinted correct answer counts for practice but is marked assisted (check rules: `reading_check.py`).

### `score`
End of the baseline, the decode check, or the post-test.

| Field | Type | Notes |
| --- | --- | --- |
| **context** | `"baseline"` \| `"check"` \| `"post_test"` | |
| **correct** | int | |
| **size** | int | |
| pass_score | int | Check only (4) |
| passed | bool | Check only |
| before | int | Post-test only: the baseline score, for the before/after screen |

### `milestone`
| Field | Type | Notes |
| --- | --- | --- |
| **id** | `"first_breakthrough"` \| `"victory_1"` | |
| **seal** | `"small"` \| `"full"` | Size of the stamp animation |
| **active_ms** | int | Total active time so far |
| **time_text** | str | Python-formatted, e.g. "11 minutes" |
| **lines** | list[narrator] | Spoken after the stamp, in order |
| verdict | {tier, projected_minutes} | Victory 1 only. `tier` is a `wager.verdict_tiers_minutes` id; the matching `pace_verdict` line is already in `lines`. |

### `notice`
A short system message that changes nothing, e.g. "Type the sound in English letters" when Korean was typed, or an unknown command. `{text}`. Followed by the same `await` again.

### `await`
What the renderer should ask for next. Always last in the list (unless `finished`).

| Field | Type | Notes |
| --- | --- | --- |
| **input** | `"choice"` \| `"text"` \| `"continue"` | `continue` = one button; send `""` |
| choices | list[str] | For `choice` |
| qid | str | The open question, if any |
| placeholder | str | For `text`, e.g. "e.g. na" |

### `finished`
`{outcome: "victory_1" | "quit"}`. After `victory_1` the slice is over; the renderer shows its end screen.

## Timer

- The renderer counts active milliseconds. It stops counting when the page is hidden (`visibilitychange`) or after **120 s** without input, and resumes on the next interaction.
- It sends the elapsed active time with every `submit()`. Python starts the saved total at the first Batch 0 `letter_intro`, after the baseline or skip, and emits `lines.clock_start` immediately before Batch 0's intro line.
- The time is shown **only** on `milestone` screens, never during questions.
- When counting resumes after a hide or idle stop, the renderer calls `resume("pause")` before anything else, so Jeong's "the clock stopped" line is true.

## Example (start of Batch 0, abbreviated)

```python
flow.start() ->
[ {"kind":"stage","batch_id":0,"batch_name":"The Revelation","phase":"intro","letters_known":[]},
  {"kind":"narrator","speaker":"sejong","text":"My people could not write their own words. …","line_id":"lines.intro.0","source":"real, paraphrased (Sejong's preface)"},
  … the rest of the intro lines …,
  {"kind":"narrator","speaker":"jeong","text":"First, how much can you read already? …","line_id":"lines.baseline_offer","source":"invented"},
  {"kind":"await","input":"choice","choices":["Take the quick test","Skip"]} ]

flow.submit("Skip", active_ms=41000) ->
[ {"kind":"narrator","speaker":"jeong","text":"Skipping the test. Confident, or cautious? We shall see.","line_id":"lines.baseline_skip","source":"invented"},
  {"kind":"stage","batch_id":0,"batch_name":"The Revelation","phase":"discover","letters_known":[]},
  {"kind":"narrator","line_id":"lines.clock_start", …},
  {"kind":"narrator","speaker":"jeong","text":"Four letters. Two consonants, two vowels. That is enough to begin.", …},
  {"kind":"letter_intro","jamo":"ㄴ","type":"consonant","roman":"n","sound":"n, as in 'no'","shape":"Your tongue tip touching …","shape_source":"haerye"},
  {"kind":"letter_intro","jamo":"ㄷ", …, "related":"ㄴ","notice_line":{"speaker":"jeong","text":"ㄴ, with an added stroke. …"}},
  … ㅏ, ㅗ …,
  {"kind":"stage", …, "phase":"predict_reveal","letters_known":["ㄴ","ㄷ","ㅏ","ㅗ"]},
  {"kind":"predict","consonant":"ㄴ","vowel":"ㅏ","choices":["나","노","다"]},
  {"kind":"await","input":"choice","choices":["나","노","다"]} ]
```

## Tests that pin this contract (`scripts/_verify_sejong_flow.py`)

- Every list returned by `start`, `submit` and `resume` ends with exactly one `await` or `finished`.
- Every event has `kind`, and every **bold** field above for its kind.
- Every `narrator.line_id` resolves to a line in `sejong.json`, and its `text` has no unfilled `{placeholder}`.
- No `question` (except `context: "baseline"`), `predict` choice or `display` uses a letter outside `letters_known`. The post-test remains strict.
- Baseline and post-test cards emit no `result`; check results have no `line`.
- `export_state()` → `from_state()` mid-batch, then the same answers, gives the same events as an uninterrupted run (same seed).
