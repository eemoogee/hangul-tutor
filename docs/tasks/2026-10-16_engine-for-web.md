# Task: engine changes for the Sejong web slice

**For:** Codex or Hermes · **Written:** 2026-10-16 · **Verifier:** Claude (in the owner's session)
**Context:** `docs/sejong-test-spec.md` (the experience), `data/sejong.json` (draft content). The browser will run this Python unchanged inside Pyodide. Read this whole brief before editing.

## Goal

Make `HangulQuiz` usable by a browser front end, without changing anything the terminal app or the existing tests rely on. You should need three small, additive changes. Do **not** build the Sejong flow itself, any UI, or any web files. That is a later task.

## Change 1 — run without touching files

Add a keyword argument: `HangulQuiz(persist: bool = True)`.

- `persist=True` (the default) must behave exactly as today.
- `persist=False`:
  - `__init__` starts from `self._new_progress()` and never reads `PROGRESS_PATH` or its `.json.tmp`.
  - `save_progress()` still updates the lifetime totals (`total_questions_answered`, `total_correct`, `streak_best`, `last_session`, and the `_saved_total`/`_saved_correct` bookkeeping) but writes no file.
  - No `print()` is reachable. Today the prints at lines ~634–703 and ~839 are all in the file load/save paths. Confirm with a grep and say so in the report.
- Curriculum, `word_contrasts.json` and the nonword exclusion sets still load from `DATA_DIR` as now (the browser places those files on a virtual disk).

## Change 2 — progress in and out as a JSON string

Add two methods:

- `export_state() -> str`: calls the same bookkeeping as `save_progress()` (refactor that bookkeeping into a private helper both share; don't copy it), then returns `json.dumps(self.progress, ensure_ascii=False)`.
- `import_state(text: str) -> None`: parses the JSON and runs it through the **same** schema checks and migrations `_load_progress` applies (`schema_version`, `_migrate_1_to_2`, `_migrate_2_to_3`, the newer-version read-only rule). Refactor so the dict-handling part of `_load_progress` is a helper that both use; the file-reading part stays in `_load_progress`.
  - On unreadable JSON or a non-dict, raise `ValueError` with a plain message. Never print.
  - On a newer `schema_version`, set `self._progress_read_only = True` and keep the data, exactly as the file path does.

## Change 3 — start a lesson that isn't in the curriculum

Add `start_custom_lesson(lesson: dict) -> dict`. It sets `self.current_lesson = lesson` and returns the same shape of dict `start_lesson()` returns. It must **not** change `progress["current_lesson"]`.

The Sejong batches will be passed in as lesson dicts with **`"id": 0`**, for example:

```python
{"id": 0, "title": "The Revelation", "letters": ["ㄴ","ㄷ","ㅏ","ㅗ"],
 "practice_syllables": ["나","노","다","도"], "mastery_syllables": ["나","노","다","도"],
 "confusion_pairs": [["ㄴ","ㄷ"],["ㅏ","ㅗ"]], "pronunciation": {}}
```

Id 0 was chosen because the engine compares lesson ids in several places. Check each one behaves sensibly for id 0, and list them in your report with what happens:

- `hangul_quiz_engine.py`: ~1035 (`<= 5` → build_syllable offered), ~1374 (next-lesson lookup), ~2009 (`< 10`), ~2945 (`current_lesson` advance — must not run for a custom lesson), and anything else you find.
- `reading_check.py`: ~61 (`>= 10`), ~106 (`prior["id"] <= lesson["id"]`).
- Also check `lesson_mastery()` and `complete_lesson()`: what happens if the CLI calls them while a custom lesson is active. If either would record a fake lesson 0 completion in progress, make it refuse (return without recording) for a lesson whose id isn't in the curriculum, and add a test for it.

`make_reading_check(quiz)` should then work unchanged on a custom lesson. Prove it in a test (below). Only change `reading_check.py` if the test shows it fails, and explain why.

## Out of scope

The Sejong flow, `lesson_flow.py`, `hangul_cli.py`, any HTML/JS, timers, and narrator text. Don't rename or reformat existing code. Don't touch `data/curriculum.json` or `data/sejong.json`.

## Tests — new file `scripts/_verify_engine_web.py`

Plain `assert`-style, runnable as `python scripts/_verify_engine_web.py`, printing one line per test and a final count. At least:

1. `persist=False`: create a quiz, answer 20 questions, call `save_progress()`. Assert `PROGRESS_PATH`'s modification time and bytes are unchanged (or the file is still absent), and that `total_questions_answered == 20`.
2. Round trip: answer 30 questions with `persist=False`, `s = export_state()`, then a new `HangulQuiz(persist=False)` with `import_state(s)`. Assert the two `progress` dicts are equal.
3. Migration: `import_state` of a schema-1 sample (build one by hand from what `_migrate_1_to_2` expects) gives a schema-3 dict.
4. Bad input: `import_state("not json")` and `import_state("[]")` both raise `ValueError`.
5. Newer version: `import_state` with `schema_version` = current + 1 sets `_progress_read_only`, and a later `export_state()` still returns the original data unchanged.
6. Custom lesson: `start_custom_lesson` with the Batch 0 dict above, then 200 `next_question()` + correct `answer()` calls with `random.seed(1)`. Assert:
   - every question's target uses only ㄴ ㄷ ㅏ ㅗ (or is one of those letters),
   - no exception,
   - `progress["current_lesson"]` unchanged,
   - `progress["completed_lessons"]` unchanged.
   Print the count of each mode seen.
7. Same as 6 for Batch 1 (letters ㄴ ㄷ ㅁ ㅂ ㅏ ㅗ ㅓ ㅜ; practice pool = every consonant+vowel block from those 8 letters, 16 blocks).
8. `make_reading_check(quiz)` on the Batch 0 and Batch 1 custom lessons returns 5 questions whose targets use only that lesson's letters.

## Done when (paste the evidence; a description is not enough)

- [ ] Full output of `python scripts/_verify_engine_web.py`.
- [ ] Full output of **every** existing `scripts/_verify_*.py`, all passing.
- [ ] `python sim_lesson.py --lesson 1 --questions 60 --seed 42` output tail, unchanged from before your edit (run it before and after; paste both tails).
- [ ] `git diff --stat` and the full diff of `hangul_quiz_engine.py` (and `reading_check.py` if touched).
- [ ] The id-comparison list from Change 3, with one line each on behavior at id 0.
- [ ] The grep showing no `print(` is reachable with `persist=False`.

Commit on a new branch `engine-for-web`; don't push (the owner pushes).
