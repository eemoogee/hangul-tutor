# Task: the Sejong slice in the browser (`web/`)

**For:** Codex · **Written:** 2026-10-17 · **Verifier:** Claude (in the owner's session)
**Read first:** `docs/sejong-events.md` (the contract this page draws), `sejong_flow.py` and `sejong_cli.py` (the terminal renderer of the same events), `archive/Hangul Key Pad.html` (the look to follow). Background: the owner's phone speed test already showed the Python engine runs in a phone browser through Pyodide, and the owner chose to keep Python rather than port to JavaScript.

## Goal

A page that plays the whole Sejong slice on a phone: it loads Pyodide, runs `sejong_flow.py` unchanged, and draws its events. One link, no install, playable by a beginner on their own phone. **Python decides; the page draws** (contract, "The rule"): the page never grades, never picks text, never decides what comes next.

## Ground rules

- Own worktree from current `master`: `git worktree add ../hangul-tutor-web -b sejong-web`.
- New files under `web/`, plus `scripts/build_web.py`, `scripts/fetch_pyodide.py` and `scripts/_verify_web.py`. You may add renderer notes to `docs/sejong-events.md` (for example the storage line).
- **Do not change** `sejong_flow.py`, the engine, `reading_check.py`, `sejong_cli.py` or `data/`. If the page seems to need a Python change, stop and report what and why: the contract changes first, in a separate task.

## Decisions (defaults; the owner may change any before you start)

| # | Decision |
|---|----------|
| W1 | **Hosting:** published as a Claude artifact, the same way as the speed test (Claude publishes it after verification). The page must also work served from a plain local folder (`python -m http.server` in `web/`). So: relative URLs only, no service worker, no external scripts. Google Fonts is the one allowed outside link, and the page must still work if it fails. |
| W2 | **Pyodide 0.26.4, bundled** (not from a CDN), the version the speed test proved. `scripts/fetch_pyodide.py` downloads `pyodide.js`, `pyodide.asm.js`, `pyodide.asm.wasm`, `python_stdlib.bin.wasm` (or `python_stdlib.zip`, whichever 0.26.4 ships) and `pyodide-lock.json` into `web/pyodide/`. Add `web/pyodide/` to `.gitignore`. |
| W3 | **Engine files:** `scripts/build_web.py` copies `hangul_quiz_engine.py`, `reading_check.py`, `sejong_flow.py` and every data file `HangulQuiz()` and the flow open (`curriculum.json`, `word_contrasts.json`, `konglish_vocab.json`, `reading_practice.jsonl`, `tatoeba_kor_sentences.tsv`, `sejong.json`) into `web/engine/`, plus a `manifest.json` listing them with a content hash. Gitignore `web/engine/` too; the build makes it. The page fetches the manifest, writes the files into Pyodide's file system, and runs `HangulQuiz(persist=False)` + `SejongFlow`. |
| W4 | **Saving:** after every `submit()`, save `flow.export_state()` with `APP_VERSION` under one `localStorage` key, every read and write in try/catch (storage can be missing or throw; the page must still play). On load with a saved state: `SejongFlow.from_state(...)` + `resume("reopen")`. If that raises, or the saved version is from an incompatible build, start fresh and say so in one line. |
| W5 | **Timer** exactly as the contract's Timer section: count active ms; stop when the page is hidden or after 120 s without input; on the next interaction after a stop, call `resume("pause")` first; send the elapsed ms with each `submit()`. The time is never shown during questions. |
| W6 | **Inputs:** choices are large buttons (at least 48 px tall, Hangul in the Hangul font). Typed answers use the phone's own keyboard, so no Korean keyboard is needed: `<input type="text" autocapitalize="none" autocorrect="off" autocomplete="off" spellcheck="false" enterkeyhint="go">`, the `await.placeholder` as placeholder, a submit button, and Enter submits. Keep the prompt visible when the keyboard opens. A hint button appears only when `hint_available` and sends `/hint`. The Key Pad is not used in this slice. |
| W7 | **Look:** follow the Key Pad: its colour tokens (light and dark, `prefers-color-scheme`), Gowun Batang for Hangul, a plain sans for UI. One event per screen, large Hangul, short lines. The only ambient progress is the `letters_known` row in the header (one chip per letter, in teaching order) and the phase's round bar (`round.index` of `round.size`). No percentages, no empty checkboxes. Narrator lines show a name tag (Jeong / King Sejong); lines whose `source` starts with "real" get a small "historical" mark. |
| W8 | **Playtest results, local only:** a small menu (corner button) with **Copy results** and **Start over** (in-page confirm, never `alert`/`confirm`). Copy results puts JSON on the clipboard, falling back to selecting it on screen: `app_version`, user agent, start and finish times, `active_ms`, the latest `export_state()`, and a log with one entry per answered card (`qid`, `context`, `mode`, input type choice/text, the answer, `correct`, hint used, ms from card shown to answer). The same button appears on the finished screen. Nothing is sent anywhere. |
| W9 | **Loading screen:** title, then steps with timings (download Python ~14 MB, load the lessons, start), as on the speed-test page. On failure, show the error and a Retry button. |
| W10 | **No audio** in this version. |

## How each event is drawn

Follow the contract's "Display rules for renderers" (order, local taps, `result` replacing its card, unknown kinds skipped and logged). On top of those:

| Event | Drawn as |
|---|---|
| `stage` | Header only: batch name and the `letters_known` chips. |
| `narrator` | Name tag + text; tap or Continue to go on. |
| `before_word` | The word alone, very large; nothing else. |
| `letter_intro` | The letter very large, then roman, sound, shape. If `related` is present, show that letter beside it. `notice_line` below as a Jeong line. |
| `predict` | `ㄴ + ㅏ = ?` and the three choices. |
| `reveal` | The two parts slide into place (`layout` side or stack, as the Key Pad animates a block), then roman and meaning. Respect `prefers-reduced-motion`. |
| `question` | Prompt, the big `display` (or `parts` as `ㄴ + ㅏ` for build cards), round bar, input. |
| `result` | Replaces the card: correct or not, then the useful fact first (`correct_answer`, `chosen_is`, `tell`), then Jeong's `line`. A miss on a check or after card reads "It reads …" (it does not come back). |
| `hint` | Text under the open question; the same `await` follows. |
| `word_read` | Word large, roman, meaning, then the line if present. |
| `score` | "Reading check: 4 of 5" with pass or fail styling. |
| `milestone` | A seal stamp (`small` or `full`), `time_text`, then each line in order. |
| `notice` | A short message that fades; the same input stays. |
| `finished` | End screen: the outcome, Copy results, Start over. |

## Tests — `scripts/_verify_web.py` (Playwright, Python)

Install with `pip install playwright` and `python -m playwright install chromium`. The script builds `web/`, serves it from a local port, and opens it at phone size (412×915, touch, mobile). Add a test hook only behind `?test=1` that exposes the open card's correct answer; it must not exist without that flag.

1. The page loads with no console errors (font failures excepted) in light and dark mode.
2. An always-correct run plays from the first screen to `finished`. A run with every third practice answer wrong also reaches `finished`.
3. Every event kind in the contract is drawn at least once across those runs; an injected unknown kind is skipped without breaking the page.
4. Reload mid-batch and mid-check: the page resumes at the same screen with `lines.resume_saved`, and the remaining answers produce the same events as an uninterrupted run.
5. Timer: simulated hidden time and 3 minutes without input are not counted. `lines.return_after_pause` is shown on the next interaction. The `active_ms` at Victory 1 equals the sum of the counted ms the page sent.
6. The text input has the attributes in W6. Typing "NA" for 나 is accepted. Typing 나 in Korean gets the contract's `notice`.
7. Copy results produces JSON with `app_version`, and log entries that tell choice from text answers and hinted from unhinted ones.
8. With `localStorage` throwing, the page still plays to the end, without saving.
9. Screenshots at phone size, light and dark, saved under `docs/tasks/2026-10-17_sejong-web-shots/`: loading, `before_word`, `letter_intro`, `predict`, `reveal`, a build card, a miss with a tip, `word_read`, the check, a milestone, finished.
10. Every existing `scripts/_verify_*.py` still passes.

## Out of scope

Batches 2 and later, audio, the 16-block board, accounts, servers or analytics, installing as an app (PWA), the Key Pad, and any change to Python or content.

## Done when (paste evidence)

- [ ] Full output of `python scripts/_verify_web.py` and every other `scripts/_verify_*.py`.
- [ ] The screenshots from test 9.
- [ ] Load timings from one cold and one cached load (desktop is fine; the owner will test the phone).
- [ ] `git diff --stat`, and the full diff of `docs/sejong-events.md`.
- [ ] Anything you couldn't follow exactly, and why.

Commit on `sejong-web`; don't push.
