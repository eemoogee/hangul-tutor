# Task: Living Syllable — remove and return the final ㄴ of 난 (isolated prototype)

**Date:** 2026-10-20 · **Status:** DRAFT, awaiting owner approval before it is sent to Codex
**Scope:** one isolated interaction prototype. No production integration.

**Authorization**
- Do not modify production code (`web/`, engine files), curriculum data, existing prototypes, or unrelated uncommitted work.
- Use an isolated worktree. **Do not place it inside `.verify_out/`**: that folder is git-ignored, so uncommitted work there is easy to lose.
- Do not commit, push, merge or deploy without explicit owner approval. Report every changed file.

## Goal

A learner opens 난, removes its final ㄴ, watches the remaining letters become 나, and deliberately returns the ㄴ to rebuild 난.

**Success criterion:** placing the piece back feels like completing a small physical construction, not like triggering an animation.

Prioritize how the interaction feels in the hand over adding visual effects.

## Inputs (read first)

| Input | Use |
|---|---|
| `docs/prototypes/syllable-lift-study/index.html` | Visual and rendering baseline: font-derived pieces, extruded edges, shadows, and "On lift" shading. A rewrapped copy of the owner-tested Claude artifact; use it as reference, not as the flat comparison condition. Do not carry over its plate flap or automatic opening. |
| `docs/prototypes/syllable-lift-study/noto-contours.json` | Contours of 나, 노, 난, ㄴ, ㅏ and ㅗ from Noto Sans CJK KR Bold (SIL Open Font License 1.1), with source notes |
| `docs/notes/2026-10-19-physical-hangul-design-synthesis.md` | Principles, the **2026-10-20 update** (shading decision, geometry table, technical lessons), and the 난 caution |
| Earlier Codex studies (relief-exploded, Living Syllable Interaction Lab), if present | Reference only. Do not modify. |

## 1. Geometry: interpolate the font's own outlines

The whole sequence can run on real Noto outlines. These pairs have identical path command structures, so their coordinates can be interpolated number for number:

| Piece | From | To | Structure |
|---|---|---|---|
| initial ㄴ | its form in 난 | its form in 나 | `MVHCLCVHZ` |
| ㅏ | its form in 난 | its form in 나 | `MVHVHVHVZ` |
| final ㄴ (lifted) | its form in 난 | standalone ㄴ (U+3134) | `MVHVHVZ` |

**Requirements:**
- **Interpolate coordinates in script.** Parse each path into numbers, interpolate, and write the `d` attribute every frame with `requestAnimationFrame`. Do not use CSS `d` transitions or SVG SMIL.
- **The rest states are the font's own glyphs.** Seated 난 and resting 나 must be the exact outlines from `noto-contours.json`, so no crossfade to a different font should be needed. If one is needed anyway, document it.
- **Register outlines before interpolating.** The standalone ㄴ and the final ㄴ in 난 use different font coordinate origins. Define a stable anchor on the final piece, align the standalone outline to that anchor for shape interpolation, and apply the piece's screen-position translation separately. Do not let a change of outline origin add an unintended second movement. Keep both endpoint outlines unchanged apart from their documented placement transforms.
- **Check the in-between forms.** Identical path commands are a starting condition, not proof of readable morphing. Inspect the outlines and their overlap with the other letters at p = 0, 0.25, 0.5, 0.75 and 1, including during a return drag.
- **Out of scope:** morphing the *initial* ㄴ toward the standalone ㄴ. Its curved foot doesn't match the standalone ㄴ's straight structure. Don't fake it.
- **Don't claim** these transformations hold for Korean typefaces in general. They are properties of this font.

## 2. Interaction

Use a discrete **interaction state** (closed, ready, dragging, detached, settling) and one continuous **removal progress p**. At p = 0 the final ㄴ is seated and the outlines form 난; at p = 1 the final ㄴ is at its detached resting position and the remaining outlines form 나. p drives outline interpolation and the amount of relief. It does not replace the interaction state or the piece's actual screen position.

Define the final ㄴ's **seat anchor** and **detached resting anchor** in stage coordinates. During a drag, its wrapper follows the pointer 1:1; derive p by clamping the pointer-controlled anchor's distance from the seat anchor against the seat-to-detached travel distance. A tap or post-release settle animates the wrapper between those anchors and updates p from the same travel. Document the anchor and distance values so the visible movement and morph agree. Keep the assembled lettering within the stage's square syllable footprint; allow the detached ㄴ to rest beside that footprint.

- **Initial ㄴ and ㅏ:** interpolate 난 → 나 by p.
- **Lifted ㄴ:** interpolates final form → standalone ㄴ by p.
- **Footprint:** the assembled 난/나 lettering stays in the same square footprint. The detached ㄴ may rest beside it; the page must accommodate both without horizontal overflow.

**Tap path (primary, required):**
1. Tap 난 to enter the **ready** state. The outlines and piece positions still compose 난 at p = 0; opening only reveals the separate piece affordance and may play the agreed brief face sweep. It must not auto-open on a timer or separate the pieces in the screen plane.
2. Tap the final ㄴ to lift it out. p animates to 1, and the rest becomes 나.
3. A visible slot marker shows where the ㄴ belongs.
4. Tap the slot, or the ㄴ again, to return it. p animates to 0, and the syllable settles as 난 in the ready state. Tapping the assembled syllable away from a piece then closes it. Seating itself must not trigger a second all-piece opening/closing effect.

**Drag path (optional, equivalent):**
- **While dragging:** the ㄴ follows the finger 1:1 with no lag and no easing. p updates live, so 나 ↔ 난 previews continuously as the piece nears its slot.
- **Releasing inside the slot zone:** the piece moves to the seat anchor, p reaches 0, and 난 settles. The slot zone is measured around the seat anchor in stage coordinates, not around the transformed SVG outline.
- **Releasing outside the zone:** the piece moves to its detached resting anchor, p reaches 1, and the syllable stays 나. A partial drag must not leave an intermediate outline presented as a completed syllable.
- **Approaching is never enough.** Coming close must not complete the placement on its own; only a release or a tap does.

**Also required:**
- **Open/Close, Undo and Reset** as labeled buttons. The syllable tap is a shortcut, not the only way to change the closed/ready state. Undo reverses the last completed lift or seating action; Reset returns to closed 난 at p = 0.
- **Keyboard:** Tab to a piece; Enter to lift; Enter on the slot to return; the Open/Close button changes the closed/ready state; Esc during an active drag or transition cancels back to the state at its start; buttons for Undo and Reset.
- **Clear state:** a wrong placement never silently completes the syllable, and the current state ("난", "나 + ㄴ", "lifted") is always visible as text.

## 3. Visual treatment (decided; do not redesign)

Match the Syllable Lift Study:
- **Pieces stay front-facing.** Lifted pieces rise toward the viewer. If a slight component-only tilt helps expose thickness, keep it small enough that the jamo remains readable; do not reproduce the plate's peeling-corner flap.
- **The darker extruded edge** grows with height and persists while lifted.
- **The shadow** sits on a separate flat layer.
- **"On lift" face shading is the default.** The sweep plays only on the acting piece during its lift, and on all pieces only for closed → ready or ready → closed. Shorten the sweep to about 0.5 s and tie it to those events. Setting the ㄴ down is quiet, as recorded in the 2026-10-20 design decision; use a small positional settle for completion without another sweep.

**One toggle:** Relief (default) or Flat. Flat uses the same geometry, motion and timing, with no edges, shadows or sweep. It is the accessibility and comparison baseline.

**Do not add** rotating planes, translucent plates or cards, corner flaps, glows, or cube geometry.

## 4. Technical rules (learned from the Lift Study; required)

1. No two layers at the same 3D depth. Paint shadows on their own flat layer before the 3D letters.
2. No CSS transitions or animations on transforms of SVG child elements inside 3D-transformed containers: Chrome drops the whole letter for frames. Animate with `requestAnimationFrame` (attributes), or transform HTML wrapper elements.
3. Bouncy easing overshoots in depth as well. Keep letters from passing behind other layers.
4. On the stage: `touch-action: none`, pointer capture while dragging, `user-select: none`, and no long-press menu (`-webkit-touch-callout: none`). The page must not scroll while dragging.
5. Tap targets follow the visible pieces at every moment, minimum 44 × 44 px.
6. Dark mode: dark shadows plus a lighter edge, never glows.

## 5. Tuning panel

A small panel with:
- sliders for lift height, settle bounce, sweep duration, and slot-zone radius
- a **Copy settings** button that copies them as JSON

The owner will tune on the phone and paste the values back.

## 6. Accessibility and layout

- **Reduced motion:** clear before and after states, with short crossfades instead of movement.
- **Input:** no required audio, vibration or hover.
- **Layout:** no horizontal overflow; must work at 390 × 844 and 320 × 568.
- Check overflow and moving hit areas in closed, ready, intermediate drag, detached, and return frames. The supplied Lift Study showed a few pixels of horizontal overflow at 320 px in some transformed open frames.

## 7. Verification (keep it lean)

**Automated browser checks:**
- 난 composes correctly at rest.
- Tap path: lift → 나 → return → 난.
- Drag path: release outside the zone stays 나; release inside seats 난.
- Release from an intermediate drag settles to a complete endpoint; no partial glyph remains labeled as 나 or 난.
- Undo and Reset.
- Keyboard path.
- Reduced motion.
- No console errors; no clipping at both viewport sizes.

**Captures:** removal at p = 0, 0.25, 0.5, 0.75 and 1.

**Not required for this milestone:** separate long reports. Put results in the README.

Physical Android feel and learner comprehension are assessed by the owner, not by Codex.

## 8. Deliverables

1. `docs/prototypes/living-syllable-remove-return/index.html`: **one self-contained file** with outlines and required styling inline, no remote CSS or external fonts, so it can be opened directly on a phone. Name the source font in the README even if its outlines are embedded.
2. A README covering: controls; geometry sources (each outline marked "font outline" or "authored edit"); test results; known limitations; and one recommended next step.
3. Captures in the same folder.

## Out of scope

Vowel substitution (ㅏ→ㅗ), building syllables from scratch, the initial-ㄴ-to-standalone morph, sound, scoring, and curriculum integration. If this interaction works, vowel substitution and final-consonant changes follow the same model.
