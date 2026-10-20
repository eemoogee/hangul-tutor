# Vowel prototypes and current construction direction

These references preserve two historical experiments. Their interaction and assessment choices are evidence about what was built, not approval for production or proof of learning. The [Vowel Forge archive](vowel-forge/README.md) and [Vowel Machine archive](vowel-machine/README.md) give inventories and reproduction instructions.

## Two distinct learning tasks

1. **Construct an individual vowel:** begin with a fixed ㅣ or ㅡ base and position one or more short marks relative to it. For the first four shapes, right/left of ㅣ produces ㅏ/ㅓ; above/below ㅡ produces ㅗ/ㅜ. Standalone ㅣ and ㅡ are valid vowels, not merely input pieces. Later design must allow doubled strokes and compound vowels. This is a model of written shape structure, **not handwriting stroke order**.
2. **Combine completed jamo into a syllable block:** use an already formed consonant and vowel, such as ㄴ + ㅏ → 나, then edit or replace a component while keeping the other visible. The [Hangul workshop brief](../hangul-workshop-brief.md) describes a growing possibility board, repair, production, and later input transfer. A glowing row of blocks can show a consequence of vowel choice; it does not itself teach the first task or prove the second.

## What each reference contributes

| Reference | Main learner action | Assessment actually present | Reuse | Superseded or still open |
| --- | --- | --- | --- | --- |
| **Vowel Forge** | In one tab, order two of ㆍ/ㅡ/ㅣ; in the other, select ㅣ/ㅡ then tap or drag a short mark into a position. | Visible target vowel and sound, immediate correctness, hints, attempts, mode comparison. | Fixed base, positional targets, tap-to-place, reversible correction, shape preview. | Three-key sequence is later input transfer. Visible-answer completion and raw attempts cannot establish independent construction. Its ㄴ/ㄷ grid is a downstream block preview. |
| **Vowel Machine v0.3.1** | Slide a joint across a line and turn the base, or use three keys; explore then construct from a sound cue. | Check submission with hidden glyph, component feedback, optional clue after two misses, then four immediate vowel-recognition choices per method. | Explicit Check, target concealment, first unaided vs assisted records, non-drag controls, contrast feedback. | Rotation and a moving rail are superseded as the primary instruction. The four-item check is not delayed retention, pronunciation, or syllable reading. Its ㄴ row is only a preview. |
| **Approved fixed-base stem-and-stroke direction** | Start with a fixed ㅣ or ㅡ, tap a mark and tap a position; optional drag can express the same placement. | To be specified and tested separately from free exploration. | Primary direction for individual vowel construction. | Requires beginner and accessibility testing, later doubled-stroke/compound-vowel representation, and careful distinction from handwriting. No implementation is claimed here. |
| **Living Syllable workshop** | Combine completed jamo into blocks; lift, replace, and undo one component, with a growing consonant-by-vowel board. | The [workshop brief](../hangul-workshop-brief.md) proposes authored repair, production, and uncued transfer, distinct from discoveries. | Reuse the consequence grid and clear one-component changes after vowels are learned. | This is the block-combination task. The brief is a design plan; its proposed assessment and later audio/native-input paths are not verified as implemented by these vowel prototypes. |

## Current decisions and boundaries

- Fixed-base stem-and-stroke construction is primary for teaching vowel geometry. Tap-to-place is the accessible default; dragging is optional.
- Rotation is superseded as the main instructional mechanic. Vowel Machine's rail remains a historical contrast experiment.
- Cheonjiin-inspired three-key input is reserved for a later practical-input transfer activity, after shape construction. The prototypes' two-tap mapping is an invented game rule, not a claim about every contemporary keyboard.
- Standalone ㅡ and ㅣ count as vowels. The four-vowel prototypes do not assess them as answers. Future construction models must accommodate doubled strokes and compound vowels.
- Shape construction must not be described as handwriting stroke-order instruction. Approximate Latin cues are not pronunciation assessment.
- Historical discussion of ㆍ, ㅡ, and ㅣ belongs to sourced context. The game gestures, rail, grid lighting, scoring/records, and fictional dialogue are implementation decisions. They do not follow from the historical source.
- Discovery, immediate recognition, independent construction, syllable reading, delayed retention, and transfer are different evidence. The archived prototypes cover only some of these, and no beginner study result was supplied.

## Archive verification

The selected Forge HTML matched the downloaded ZIP member and the Vowel Machine reference copy by SHA-256. All eleven v0.3.1 ZIP members matched their local loose counterparts before archiving. Every archived executable file and image was copied without byte changes. The Vowel Machine note and reproduction ZIP have the one documented path redaction; their archived hashes therefore differ from the supplied originals. `.gitattributes` applies `-text` to both `original/` trees so a fresh Git checkout does not rewrite line endings. The per-prototype READMEs record each archived hash, original ZIP hash, and the redaction. The older v0.3 ZIP and generated screenshots were excluded from this v0.3.1 reference archive.

Chromium checks covered Forge's two paths and Vowel Machine's Explore, Prove, recognition, rail-shortcut cases, reduced motion, focus, and ZIP-member parity. The historical Vowel Machine verifier needed test-only corrections in a disposable copy; the archived script remains unchanged and does not pass unmodified. Neither check establishes real-phone behavior, screen-reader access, beginner comprehension, or retention. The two READMEs give the exact results and limits.
