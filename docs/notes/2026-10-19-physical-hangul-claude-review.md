# Physical Hangul interaction — independent design review (Claude)

**Author:** Claude (Opus), 2026-10-19
**Status:** design proposals and predictions. **No claim here is a validated learning result.** Statements marked *Proven* refer to technical feasibility in phone browsers, not to learning value.

Scope: brief "Independent Design Review — Physical Hangul Interaction". Test syllables: 나, 노, 난.

## Core challenge

The strongest 3D impression (rotating translucent surfaces) probably came from **parallax** (layers moving at different speeds as the view turns), **continuous change under the finger**, and **seeing through one layer to another**, not from the cube itself. The syllable's own frame (네모틀), divided into initial, vowel and final zones, can supply the same three properties with meaningful geometry.

Second hypothesis: the flat experiments may have felt ordinary because of their **motion**, not their lack of depth. Likely causes are even-speed or "ease" animation curves, no anticipation, no resistance, and no reaction from neighbouring pieces. Test this before investing in 3D.

## 1. Three concepts

**A. Glass Slot Frame (an exploded view with real structure).** The syllable sits in a thin, slightly see-through square frame. A tap tilts it about 12° and separates it along its own layout axis: 나 splits into two side-by-side cells (ㅏ slides right on a rail); 노 stacks (ㅗ drops down); 난 adds a wide bottom cell from which the final ㄴ slides down. Swapping ㅏ→ㅗ makes the frame **re-partition**: the vertical divider swings to horizontal, which shows the layout rule.

**B. Shadow Page (depth shown through light, not geometry).** The page is the writing surface. A lifted jamo rises toward the viewer, but its **shadow stays on the page as a ghost slot**, an answer key for where the piece belongs. ㅗ's shadow visibly doesn't fit the 나 gap but does fit the 노 slot. Flat at rest; depth only while examining, and the depth carries information. Variant to sketch: **letterpress**, with depth *into* the page; assembling presses the pieces down and leaves an inked, slightly sunken 나.

**C. Elastic Block (no depth: a fixed square the pieces share).** Pieces compete for space inside the block. ㄴ **leans away first**, then compresses and rises as ㅗ settles underneath. 나→난: the upper pieces squash upward and ㅏ shortens. Typographically honest: the ㄴ in 나, 노 and 난 is three different shapes, and the final ㄴ in 난 is wide and flat, unlike the initial ㄴ above it. The stretching is the lesson.

## 2. Physical cues

| Cue | A. Glass Frame | B. Shadow Page | C. Elastic Block |
|---|---|---|---|
| Depth | Parallax between frame and pieces; tilt that follows the finger | Shadow offset and blur grow with height; lifted piece slightly larger | None (deliberately flat) |
| Contact | Piece snaps onto its rail; frame lines brighten | Shadow tightens as the piece descends; contact darkening | Neighbour squashes, then recovers |
| Weight | Settling with one small overshoot | Lift slower than drop | Anticipation lean; momentum after release |
| Occlusion | Front frame edge passes over the pieces behind it | Lifted piece covers part of its own shadow | Overlap only during squash |

For all three: pieces follow the finger instantly with no delay; spring motion rather than fixed-length animations; lifting and dropping take different amounts of time.

## 3. Satisfaction without points or badges

- Resistance near a slot, then capture past a threshold.
- The block makes room (ㄴ moving aside for ㅗ).
- **Turning into real writing:** the pieces become the actual font rendering of the syllable.
- The syllable speaks: play the recorded syllable on seating, not a chime.
- A short vibration on Android (not available on iPhone).
- Something to do next: the finished block slides into a word slot (나 + 무 → 나무).

## 4. Technique ranking (for meaning per unit of effort)

1. Glyph shapes per slot (most meaning)
2. Motion timing and springs (most feel per cost)
3. Shadow and occlusion (cheap, readable depth)
4. Elastic stretching (strong meaning; only if the in-between shapes are well made)
5. Lighting on thick (extruded) letters (mostly decorative; check readability)
6. Generated letter shapes or a 3D engine (WebGL) (only if the simpler techniques fail)

## 5. Do we need 3D at all?

Probably not as a requirement. Hangul is two-dimensional, and beginners on a narrow phone need sharp, readable letters. Depth earns its place only when it carries information (a shadow showing where a piece belongs, a frame that re-divides). **Prediction, not a finding:** a flat version with excellent motion will feel about as satisfying and will read better. The experiment should be able to prove this wrong.

## 6. Dramatic 3D separation without cubes

Concept A's frame combined with concept B's shadows. The frame provides the see-through layers and the parallax, separation follows the real layout, and shadows keep the true flat writing visible. The dramatic moment is the frame changing its divisions (나→노) while the ㄴ stays the same visible object.

## Proven vs. speculative

- **Proven (works in phone browsers):** CSS 3D transforms; spring animation; morphing one SVG shape into another (a library such as flubber handles shapes with different point counts); vibration on Android Chrome (not iPhone Safari); playing recorded sound with the browser's audio system.
- **Practical but needs care:** separating a precomposed glyph into its jamo pieces (see below).
- **Speculative:** whether depth improves learning; whether ghost-slot shadows help beginners predict vowel placement; whether stretched in-between shapes look elegant or mushy.

## Failure modes

- **Fonts don't hand you the pieces.** Korean fonts draw 나 as one finished character. For a few syllables, pull the outlines out of an open-licence font (Noto Sans KR or Pretendard) with fontTools and group them by jamo by hand. This also makes the "turns into real writing" moment exact.
- **Morphing looks mushy** when outlines don't correspond point for point. Morph between matched, authored shapes, or fade between shapes during a short squash.
- **The 3D effect breaks silently.** `overflow: hidden`, `filter`, or `opacity` below 1 on a parent element flattens it. Animated blur is expensive on mid-range Android; use pre-blurred copies.
- **Korean letters blur** while moving in depth on some phones; check on a real device.
- **Tap zones drift** away from where tilted pieces appear on screen.
- **Spectacle crowds out the lesson.** If testers remember the animation but can't predict 도, it failed.

**Accuracy guardrail:** pieces are always whole jamo. Never animate strokes being drawn, and don't suggest that the depth or the frame is how Hangul was historically designed.

## 7. Recommended experiment: "Same syllable, two worlds"

- **Content:** 나, 노, 난, plus loose pieces ㄴ ㅏ ㅗ, extracted from one open-licence font, with separate shapes per slot (including the separate initial and final ㄴ in 난).
- **Flow:** tap 나 → it opens → tap ㅏ to lift → tap ㅗ → it settles, with ㄴ making room → it turns into real text and "no" plays. Then 나 + final ㄴ → 난, with the upper pieces squashing up.
- **Two versions with identical timing and springs:** Version 1 flat (concept C); Version 2 frame plus shadows (A + B).
- **Learning test:** before tapping, ask where ㅜ will go in 두; afterward, ask what changed between 나 and 난.
- **Feel test:** which version they want to touch again.
- **Performance and readability:** smooth motion on a real Android phone; letters readable on a 320px-wide screen.
- **Testers:** about five absolute beginners, never the designer or builder.
- **Decision rule:** if flat teaches as well and feels nearly as good, ship flat and keep depth for a single "inspect" moment.
