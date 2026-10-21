# Syllable Swap Study — versions

Updated 2026-10-21. Newest first. Paths are relative to the repository root.

| Version | Where | Contents | Status |
|---|---|---|---|
| **Input Comparison** (Codex) | Branch `prototype/syllable-swap-input-comparison`, folder `docs/prototypes/syllable-swap-input-comparison/` | Built on the owner's export of Claude **v4**. Adds Tap vs. Drag input modes, Undo, a two-row tray at widths up to 420 px, a session-notes log with JSON export, and a fix for duplicate fallback letters on Android. Motion and visuals are unchanged from v4. | Committed and pushed. See its README. |
| **v4** (Claude) | `index.html` in this folder; also Claude artifact "Syllable Swap Study" version 4 | Box fix: each outline layer is its own `<svg>`; the shading fades with `fill-opacity`; no SVG group or shape opacity is used in moving letters. Squash fires at the moment of impact (3%), off by default. | Box gone on desktop (owner, 2026-10-21). Not yet checked on a phone. |
| **v3** (Claude) | `baseline-v3.html` | Point-by-point ㄴ morph for 나 ↔ 노 only. Staggered timing (approved). First squash attempt (felt awkward). First box fix (made the box worse). | Superseded |
| **v2** (Claude) | `baseline-v2.html` | First swap version: 16 syllables, tray, refusal bounce, stretch-and-fade reshaping. Showed the box artifact. | Superseded |

## Provenance of v4

**Known (verified 2026-10-21):**
- Claude's artifact source for v4 has SHA-256 `96D7B1F1B44B9963F7473D2202A75087E6DF0CA9067417D9EB0831197CD234DB`.
- `index.html` in this folder is that exact source with a 5-line header added in front (`<!doctype html>`, `<html lang="en">`, charset and viewport `<meta>` tags, and a provenance comment). Its SHA-256 is `A93F662A3C2B7FA0F7F509D6127F899E44172B85FEA46E705131BA636B297607`. Removing the first 5 lines reproduces the source hash above.

**Unresolved:**
- The Input Comparison README cites an owner-supplied export of v4 with SHA-256 `F94D38C949342D1B17B3D6E3092219BF64481AC4C4691A39BB610C0260366F20`. That export was saved from the published artifact page, which wraps the source in its own document skeleton.
- The export file is not in the repository. **It has not been checked** that the export contains the v4 source unchanged, or what its wrapper adds. Treat "the export differs only by its wrapper" as a probable explanation, not a verified fact.

## Correction log

Until 2026-10-21, a working copy of `index.html` held v3 by mistake (SHA-256 `BE969866BF6FAC71E4999F97FFAEC8B8B913D7D5DCCEF836B44073A540FE9770`). This is the hash the Input Comparison README calls "earlier". The committed `index.html` is v4.

## Main line

v4 and Input Comparison now differ only in the input features Codex added. Before further changes, the owner should choose which file future work goes into.

Design history and decisions: `docs/notes/2026-10-19-physical-hangul-design-synthesis.md`.
