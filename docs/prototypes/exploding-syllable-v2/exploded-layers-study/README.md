# Exploded Layers 3D study

This is an isolated visual experiment beside Exploding Syllable v2. Open [index.html](index.html) in a modern browser. It has no runtime dependencies or network assets. Open [reference.html](reference.html) to inspect the pure-CSS reference reproduction. The original v1, v2, relief study, and production lessons are unchanged.

## Reference and provenance

The task described a user-supplied pure-CSS “Exploded Layers” example, but no source file for that example was accessible in the project or supplied attachments. The public [CSS 3D Lab Exploded Layers model](https://css3dlab.edgarasneverdauskas.com/models/layers/) and its [snippet source](https://github.com/Evirtual/css-3d-lab/blob/main/src/models/snippets.ts) match the specified `perspective`, `preserve-3d`, `rotateX(58deg) rotateZ(-45deg)`, symmetric Z translation, and reversible `close` keyframes. `reference.html` transcribes those functional model rules and four `<i>` plates. Its page centering, heading, and caption are neutral scaffolding; they are not part of the model snippet. The reference deliberately retains the original repeating alternate animation, while the Hangul study uses explicit open/close controls. The author’s [license statement](https://github.com/Evirtual/css-3d-lab/blob/main/LICENSE) identifies individual model snippets as licensed under [MIT terms](https://github.com/Evirtual/css-3d-lab/blob/main/LICENSES/MIT-snippets.txt) and requires this notice: Copyright (c) 2026 Edgaras Neverdauskas (https://css3dlab.edgarasneverdauskas.com). The broader site is under a different license and is not copied here. We cannot establish whether this public snippet is byte-identical to the example the user viewed.

## Implementation

The study has three selectable presentations for **나** and **난**:

| Presentation | What moves | Depth cues |
| --- | --- | --- |
| Flat explosion | The authored v2 jamo paths interpolate from packed to free coordinates | None |
| Jamo relief | The same path interpolation | Eight side-stroke copies, a contact cue, `translateZ(72px)`, and slight component tilt, following the earlier [relief study](../depth-relief-study/README.md) |
| Exploded layers | Each jamo remains at its packed coordinate on a separate translucent plate | `perspective: 850px`, `transform-style: preserve-3d`, stack `rotateX(58deg) rotateZ(-45deg)`, and symmetric plate Z positions |

At rest, the Hangul plates share one plane, have no visible surface tint or border, and show the completed front-facing block. As the learner opens them, the stack turns to the source example’s angle and the plates separate at equal Z intervals: ±52.5px for 나, and −105/0/+105px for 난. The separate front-view inset keeps the orthographic arrangement visible throughout. Closing returns the same paths and plates to their original plane. The expanded state remains still; there is no required hover or continuous animation. Rotate-left/right buttons alter only the opened layer stack, by 15° steps, with a reset button. The range control allows inspection of intermediate frames. The stage and buttons support keyboard activation. Reduced-motion preference makes open/close immediate.

SVG contains the authored Hangul paths, while HTML plates and CSS handle perspective, surface tint, and positioning. JavaScript owns the syllable, mode, angle, and animation progress. There is no Three.js. No ancestor opacity, filter, or clipping property flattens the stack. The plate tint is RGBA background color on each plate, leaving the transformed children in the same 3D context.

## Visual assessment

The source reference reproduced a convincing stack of four translucent planes in Chromium. In the Hangul version, **plate borders, transparent overlap, perspective foreshortening, and symmetric vertical separation** make the layers read as distinct surfaces. The mid-transition frames show the shape moving from a readable front-facing block into a stack; depth becomes clearest after the angle opens substantially. The small front view is needed because the angled ㄴ and ㅏ strokes no longer look like their usual printed orientation. For 난, the three separated planes make component count especially clear, but their projected positions no longer read as the completed orthographic block.

The flat mode communicates the actual planar component arrangement most directly. The relief mode can suggest a piece lifting while leaving other jamo anchored, but the extra side strokes add weight to narrow forms. The layer mode most clearly conveys **physical depth**, while asking the learner to mentally map an invented stack back to the unchanged front view. The modes differ in movement, view angle, colors, plate borders, and contact cues; this is a presentation comparison, not a controlled learning test. No beginner comprehension outcome has been measured.

**Recommendation:** use the layer effect for a small instructional usability test only if learners can reliably map its angled plates back to the flat block. Test unfamiliar syllables for first-attempt component count, component identification, reconstruction, hesitation, and confusion against the flat presentation. Its visual depth alone does not establish educational value. The view may suit an optional inspection moment better than the primary teaching view.

## Verification

Run `verify.py` using Python with Playwright and installed Chromium. It captures the reference expanded and closed, then front/partially opened/expanded/restored states at 390×844 and 320×568, plus 난 at 50% and fully opened in all three modes. The checked Chromium run passed: source reference Z symmetry and closure; two- and three-jamo plate counts; Hangul Z symmetry; touch open/close; manual rotation; return to the front plane; mode changes; keyboard Enter/Space; reduced motion; no page errors; no horizontal page overflow; and plate bounds within the stage at both phone widths. The [captures](captures/) are the corresponding browser screenshots. `node --check app.js` also passed.

I visually inspected the reference open/closed, 나 front/intermediate/open, and 난 expanded/flat/relief captures, including the 320-pixel layout. The first pass projected plates beyond the phone stage; the final captures use a smaller phone model scale. An early relief rendering had unintended path fills; that was fixed before final captures. At 320 pixels the model and Korean strokes are smaller, and the page scrolls vertically to reach controls. No physical Android, alternate browser-engine, screen-reader, or beginner test has been conducted. Physical Android touch precision, stroke rendering, and animation smoothness remain to be checked.

Depth here is an inspection metaphor, not a structural feature of Hangul writing or handwriting stroke-order instruction.
