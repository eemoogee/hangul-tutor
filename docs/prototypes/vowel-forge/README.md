# Vowel Forge reference archive

## Identity and provenance

Vowel Forge is an unversioned, single-file offline experiment. The supplied `vowel-forge-netlify-preview.zip` was present in a local download folder on 2026-10-19; its creation date is a file-system timestamp, not proof of authorship or the original creation date. The extracted `index.html` is the reference copy. Its SHA-256 matches the ZIP member and Vowel Machine's `reference-vowel-forge.html` byte for byte. No separate original README, design note, or verifier was found for Forge.

| Preserved file | Purpose | SHA-256 |
| --- | --- | --- |
| [original/index.html](original/index.html) | Complete runnable HTML, CSS, and JavaScript | `B4FE121E23352E65C6B906B014D99BCC97155CDB662517B88991193F52EBD821` |
| [original/vowel-forge-netlify-preview.zip](original/vowel-forge-netlify-preview.zip) | Supplied ZIP; one `index.html` member | `C46EA56FB967FEC1C438361223314D025881E2844179685326D5EA69BAB06044` |

The two archived files are byte-identical to the selected local originals. Git attributes disable text conversion under `original/`; verify raw bytes with SHA-256 rather than a Git blob hash. The ZIP and HTML contain no known machine-specific path. The original's authorship and complete revision history remain unverified.

## Implemented behavior

The four challenges target ㅏ, ㅓ, ㅗ, and ㅜ. **Three-key input** combines two taps of ㅣ, ㆍ, and ㅡ; order determines one of the four vowels. **Place strokes** asks for a fixed vertical ㅣ or horizontal ㅡ base, then a short mark on a side or above/below. The mark can be attached by tapping a target or dragging the token. Wrong pairs or positions give immediate feedback, and a hint supplies the target sequence or placement. Each correct vowel unlocks a column in a ㄴ/ㄷ syllable grid. The modes keep separate in-page progress, attempts, and hints; Compare results displays both records. Reset clears both. Target glyph and approximate Latin sound are visible during construction, so these challenges are guided construction, not independent recall or pronunciation checks. No audio, account, backend, or persistent save is implemented.

The page has tap targets and keyboard-operable controls in the source. Actual screen-reader usability and physical-device behavior require testing. Standalone ㅡ and ㅣ are ingredients here, not challenge answers. Doubled strokes and compound vowels are absent.

## Relationship to current design

Reuse the fixed ㅣ/ㅡ base, explicit position targets, immediate shape preview, and tap-to-place path for individual vowel construction. The visible syllable grid is a useful consequence after construction; it is a separate task from making a vowel. The exact three-key sequences belong to a later Cheonjiin-inspired practical-input transfer activity. A visible target, tap counts, and unlocked cells should not be treated as mastery evidence. Test whether learners can predict and explain positions without the displayed answer and whether tap and drag are usable on a phone. This geometric shape model is not handwriting stroke-order instruction. See the [comparison](../VOWEL-PROTOTYPES-COMPARISON.md).

## Reproduction and verification

Open [original/index.html](original/index.html) directly in a modern browser, or serve `original/` with a static HTTP server. There are no external runtime dependencies; installed fonts and browser rendering can vary. The original ZIP extracts to the same one-file page. To inspect it, switch between the two modes, complete each of the four vowels, make an incorrect pair and placement, use Hint and Compare results, then Reset.

Archive verification: Chromium opened the archived HTML at 390×844 and 320×568. At both sizes, scripted taps completed all four targets by keys and by stroke placement, unlocked the full grid, and displayed the both-modes summary. There were no page errors or horizontal overflow. The source paths and ZIP member were SHA-256 checked. This smoke check did not exercise physical drag, hint, Reset, a real phone, screen-reader use, or beginner comprehension; those interactions are source-inspected only where described above.
