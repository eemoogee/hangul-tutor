# Physical Hangul interaction — design synthesis (2026-10-19)

**Status:** synthesis of two Claude design reviews, preserved separately in `docs/notes/`. Not an implementation authorization. Statements marked **[speculative]** are design predictions to test, not findings.

**Sources (both by Claude, distinguished by topic):**
- `2026-10-19-physical-hangul-claude-review.md`: broad review of physical Hangul interaction (concepts, cues, the 3D question, a recommended experiment).
- `2026-10-19-physical-hangul-relief-exploded-review.md`: critique and proposal for the relief-based exploded syllable.

## Agreed principles

- **A syllable opens up; it doesn't break apart.** Pieces move a short distance, letters stay front-facing and readable, and nothing spins, tumbles or turns upside down.
- **Each piece moves in a direction set by its role in the syllable** (initial, vowel, final), not all in the same direction.
- **Restrained but real visual ambition.** The goal is an impressive, physical feeling of pieces opening, without arbitrary cube geometry or tumbling.
- **Pieces are always whole jamo.** No animation of strokes being drawn. The visual effects make no claims about how Hangul was historically designed.
- **The assembled state is real, readable Korean text.**

## Where the reviews differ

- **The relief review:** relief plus separation beats both flat and cube-like versions. **[speculative]**
- **The broad review:** a flat version with excellent motion may feel nearly as satisfying and read better. **[speculative]**
- **Unknown:** whether morphing toward standalone shapes helps beginners understand the structure.
- **How this milestone resolves it:** a three-condition comparison (see the task brief) that separates the effect of shape change (morphing) from the effect of relief.

## Typographic cautions

- **Contextual proportions depend on the typeface.** Many fonts draw a jamo with different proportions depending on its position. For example, the ㄴ in 나, 노 and 난 may differ, but how much (and whether) varies by font. The prototype will **deliberately** use distinct contextual forms as its chosen lettering model; this is a design choice, not a universal rule.
- **Key case: 난.** Under that lettering model, the initial ㄴ is compact and the final ㄴ is wide and flat, yet both must stay recognizable as the same underlying jamo. Seeing both morph toward one standalone ㄴ may be the most instructive moment. **[speculative]**
- **Authored vectors are not font construction.** Matched custom vectors demonstrate the idea of contextual change. They are not automatically an authentic account of how any particular font constructs its syllables. Keep "instructional vectors we authored" distinct from "outlines verified from a licensed font" in all documentation.
- **Morphing quality needs more than equal point counts.** It needs point correspondence, matching path topology (the same contours, in the same order and direction), and readable in-between shapes.
- **Ending on real text.** Authored pieces may not exactly match the font used for the assembled syllable; any crossfade between them must be documented.

## Candidate approaches

| Approach | Status |
|---|---|
| Relief-exploded syllable | **This milestone** (three-condition study) |
| Glass Slot Frame (the frame re-divides, 나→노) | Deferred |
| Shadow Page (lifted pieces leave ghost slots) | Deferred |
| Elastic Block (pieces compete for space in a fixed square) | Partly covered by the flat variants; otherwise deferred |
| Cube and rotation mechanics | **Deferred as core interactions.** Dramatic 3D remains a creative possibility, not part of this milestone. |

## Evaluation stance

Judge **physical feel** (how the interaction feels under the finger) and **visual spectacle** (how striking it looks) as separate criteria. A transformation can look astonishing but feel unsatisfying to manipulate. A simple interaction can feel wonderful without looking dramatic in a video. The goal is both. The three conditions should show how much morphing and relief each contribute. **[speculative: what the study will reveal]**

## Phases

- **This milestone:** reversible opening and closing, plus tapping a piece to inspect it.
- **Next phase (identified, not scheduled):** direct manipulation in the opened state. Lift a piece, substitute ㅏ→ㅗ, add a final consonant, and close into the new syllable. Most of the learning value is expected here. **[speculative]**

---

## Update 2026-10-20 — shading decision and geometry finding

**Source of the decision:** owner testing of the Syllable Lift Study on an Android phone and a desktop monitor. The study is a Claude artifact; a copy is at `docs/prototypes/syllable-lift-study/index.html`, with its font contours in `noto-contours.json`.

### Decided (owner)

- **Default face shading: "On lift."** A highlight-to-shadow sweep runs across the face of the *acting* piece only:
  - opening or closing the syllable: every piece
  - lifting a piece: only that piece
  - setting a piece down, or the other pieces when the selection changes: no sweep
- **Darker extruded side edge kept.** It grows as a piece rises and stays at full thickness while the piece is lifted. Roles: the sweep shows movement and changing contact; the edge shows the letter's thickness.
- **Options kept for development:** Bevel (understated alternative) and Always (special demonstrations). **Off** stays as the accessibility and comparison baseline.
- **Rejected after testing:** translucent plates behind pieces, the peeling corner (dog-ear), plate sheen, glowing shadows in dark mode (looked ghostly), and any tilt of the whole syllable plane. The owner wants letters to lift up and away individually.
- **Pending tuning:** shorten the sweep from about 1 s to about 0.5 s so it belongs to the lift rather than following it. Tune it together with direct manipulation, not as an independent animation.

**[speculative]** The face shading reads as the letter's face turning in the light. It was discovered through a rendering glitch the owner liked (letters dipping under their own shadow during the bounce), then rebuilt deliberately.

### Geometry finding (Noto Sans CJK KR Bold)

Outline command structures that match, so they can be interpolated point for point between real font shapes:

| Morph | Structure | Interpolable |
|---|---|---|
| ㄴ in 나 ↔ initial ㄴ in 난 | identical (curved, upturned foot) | yes |
| ㅏ in 나 ↔ ㅏ in 난 ↔ standalone ㅏ | identical | yes |
| final ㄴ in 난 ↔ standalone ㄴ | identical (straight) | yes |
| initial ㄴ ↔ standalone ㄴ | curved vs. straight | no; would need authored shapes |

So **난 → 나 → 난** (removing and returning the final ㄴ) can run entirely on the font's own outlines. This is a property of this font, not of Korean type in general. It also refines the 난 caution above: in this font, the initial and final ㄴ differ in **form** (curved foot vs. straight), not only in proportion.

### Technical lessons from the Lift Study (carry into later prototypes)

1. **No two layers at the same depth in a 3D scene:** the browser flickers between them. Put shadows on their own flat layer, painted before the 3D letters.
2. **No CSS transitions or animations on transforms of SVG child elements inside a 3D-transformed container.** Chrome dropped the whole letter for several frames. Animate with `requestAnimationFrame`, writing SVG attributes, or transform HTML wrappers instead.
3. **Bouncy easing overshoots in depth too.** A piece can briefly pass behind other layers.
4. **Turn off text selection and the long-press menu on the stage.** A phone recording showed the selection highlight and menu appearing over the letters.
5. **Dark-mode depth needs dark shadows plus a lighter edge.** Glows read as ghostly.

---

## Update 2026-10-20 — Syllable Swap Study: motion decisions

**Prototype:** `docs/prototypes/syllable-swap-study/index.html` is the current version. `baseline-v2.html` is the version before these changes, kept for comparison. Both are copies of a Claude artifact.

### Approved and implemented (나 ↔ 노 only)

1. **True shape morph.** In 나 ↔ 노, ㄴ interpolates point by point between the font's two forms, with no fade:
   - 나's ㄴ is the font outline (curved, upturned foot).
   - 노's ㄴ is the font outline redrawn with the same commands; its straight edges are written as curves with their control points on the line.
   - Checked visually at 0, 25, 50, 75 and 100%: readable as ㄴ throughout.
   - Every other swap still uses the stretch-and-fade.
2. **Staggered reflow (default).** The neighbour starts reshaping first, the outgoing letter leaves 120 ms later, and the incoming letter follows 240 ms after the start. The motions overlap rather than run in sequence. A "Together" toggle keeps the old simultaneous timing for comparison.
3. **Squash on arrival.** An experimental toggle, off by default: a brief compression (6%) along the arrival direction. It needs checking for whether it reads as physical or makes the letters look rubbery.

**Test that decides this:** can the learner follow ㄴ as the same letter through its change in proportions?

**Expanding beyond 나 ↔ 노 waits** until the morph is confirmed readable, convincing and responsive on a physical phone.

### Deferred alternatives (documented; do not implement yet)

4. **Reshape in the air:** the letter lifts out, changes shape while raised, then settles. Adds spectacle but may hide the structural relationship.
5. **Automatic morph library (flubber):** fallback only. Automatic interpolation risks distorted Korean letterforms.
6. **Stroke-based flexing:** strokes lengthen and shorten like a jointed letter. An interesting future mechanic, but less faithful to the type.

### Pedagogical guardrail

The morph is a visual metaphor for positional forms and syllable layout. Do not teach that consonants bend or stretch when Korean is written, and make no claim about handwriting or historical construction.

### Rendering fix (same update)

A translucent box appeared behind letters, and letters looked blurry or pixelated when lifted, on Android Chrome and a desktop GPU browser. Probable cause, not confirmed on device: letter layers were marked for fast animation (`will-change: transform`). Chrome then rasterized each letter once and stretched that image in 3D, and could draw a layer's bounds as a solid block.

Fixes:
- `will-change` removed.
- Group opacity is applied only during a cross-fade.
- The CSS blur on shadows is replaced with a fill and a wider, fainter rim, which needs no filter.

Pending verification on a physical phone.

### Follow-up, same day (owner testing)

- **Staggered timing: approved** as the default.
- **Squash:** felt awkward because it fired after the landing had finished. It now compresses at the moment of impact, blended into the landing bounce, at half strength (3%), on both the arriving letter and its neighbour. Still off by default.
- **Box artifact: the first fix made it worse.** The box is a square matching the shading gradient's square, and it flashes with the shading sweep. Revised diagnosis: animating the shape opacity of a gradient-filled path made the browser draw the gradient into a temporary square without trimming it to the letter.
  Second fix:
  - The shading fades with `fill-opacity`.
  - Each outline layer is its own `<svg>` element, so cross-fades use plain CSS opacity.
  - No SVG group or shape opacity is used anywhere in a moving letter.

  Still awaiting confirmation on a physical phone. `baseline-v3.html` keeps the version before this fix.

---

## Status note 2026-10-21 — superseded studies

- **Codex's relief-exploded studies are superseded as starting points.** These are the "Exploding Syllable v2" V1/V2/V3 comparison, the exploded-layers view and the reference reproduction, in `.verify_out/exploding-syllable-prototype`, branch `codex/exploding-syllable-prototype`. Keep them as a record (see `docs/tasks/2026-10-19_relief-exploded-syllable-study.md`). Don't restart development from them.
- **Current visual and motion references:**
  - `docs/prototypes/syllable-lift-study/`: lift, thickness, shadows, "On lift" shading
  - `docs/prototypes/syllable-swap-study/`: swapping, the ㄴ morph, staggered timing (see `VERSIONS.md`)
  - Codex's **Input Comparison** (Tap vs. Drag), built on Swap v4
- **Also preserved:** `docs/prototypes/hangul-rain/`, an ambient digital-rain effect in Hangul. Candidate use: title, Sejong opening or victory screens, not inside gameplay.
