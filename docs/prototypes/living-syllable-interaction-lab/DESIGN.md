# Living Syllable interaction lab — design exploration

This note precedes the implementation. The experiment is an unscored comparison, not a curriculum or a claim about learner outcomes.

## Tactile candidates

| Candidate | Physical behavior | Likely advantage | Risk |
| --- | --- | --- | --- |
| Lift and settle | Tap a persistent jamo to lift; tap a slot or drag near it; a restrained attraction and short damped settle completes the placement. | A placement feels authored by the learner, while the destination remains predictable. | Excessive magnetism could make a vague gesture feel like a correct one. |
| Living reflow | Use the same lift and settle, but let the already placed jamo begin to contract as final ㄴ nears the lower slot. | The learner can see why 난 needs a new lower region; nothing blinks out. | An in-between glyph is not conventional lettering, so the transition must be brief and reversible. |

The lab also keeps a **Basic** baseline: direct placement with a short, plain snap. All three treatments use the same tasks and semantic state. Lift and settle is treatment B; living reflow is C. Neither accepts a distant release as a placement. Tap-based slot buttons remain available in every treatment, including the drag-capable ones.

## Spatial candidates

| Candidate | Spatial behavior | Likely advantage | Risk |
| --- | --- | --- | --- |
| Two component panes | Only ㄴ and ㅏ occupy translucent planes. They fan apart in X, Y, and Z while the viewing frame tilts. | Plane edges, overlap, and parallax retain the source cube's strong depth cue without four unrelated faces. | The pane may be mistaken for part of Hangul unless the flat reading state and metaphor note are clear. |
| Volumetric jamo | The same two paths separate in depth with many darker layers behind each front stroke, without pane surfaces. | The letters themselves feel object-like and the original glyph identity remains central. | CSS layers have imperfect sidewalls and can look thin edge-on; true geometry would be needed for arbitrary angles. |

Both spatial candidates start and end as the same readable flat **나**, allow intermediate scrubbing, and hold still after opening. A controlled camera tilt makes depth visible without imposing continuous spin. The comparison deliberately asks whether panes clarify depth enough to justify their visual baggage. It does not assume either spatial treatment belongs in routine teaching.

## Smallest implementation

One standalone page contains: three construction treatments across **ㄴ + ㅏ → 나**, **나 + ㄴ → 난**, and **난 → 나 + ㄴ**; and the two spatial candidates for **나** only. The construction bench reuses the authored 360×320 jamo endpoint geometry from Exploding Syllable v2. Persistent SVG groups retain component identity; no font-outline swapping or whole-block fade determines completion. The spatial view reuses those paths on separately transformed CSS 3D elements. The DOM state model, not animation timing, determines the result. No production code or browser save is read or written.

## What the captures show

The [construction motion strip](captures/construction-motion-strip.png) shows a useful distinction: the final ㄴ can approach the lower place while ㄴ and ㅏ visibly give up height **before** release. The completed 난 and the reversed 나 + ㄴ are both readable in the authored monoline drawing. Basic is the clearest control condition but its short snap makes placement feel mechanical. Tactile gives a piece a selected/lifted state, partial attraction, and a restrained settle. Transformative offers the strongest causal payoff because the learner's approaching piece changes the space available to its neighbors. This is a design judgment from browser interaction and frames, not a learner preference result. The intermediate form is intentionally transitional rather than a valid static glyph.

The [spatial motion strip](captures/spatial-motion-strip.png) shows a clearer depth transformation than the earlier shallow-Z lift: the view tilts as two independently oriented, differently sized objects separate in X, Y, and Z. The panes communicate their planes and differing depths more quickly; the solid-stroke version keeps attention on the letters and has visible thickness. Neither fully reproduces the original cube's dramatic enclosure and multi-face overlap. The panes still look like cards, while the CSS stroke layers have imperfect sidewalls. On that criterion the spatial work is **promising but not yet a convincing final effect**. The study stops at 나 rather than extending a weak metaphor to 난.

The construction and spatial views are deliberately separate tabs. Returning to construction preserves the task state, but this prototype does not yet animate a direct handoff from an opened 3D view to a placeable 2D component. The distinction may be desirable: a reveal can mark a discovery, while construction can remain the everyday instrument. That is a hypothesis to test, not a decision to integrate both.

For this visual review, **C Transform** is the strongest tactile candidate and is the default. It makes final-consonant placement change the neighboring components in a way A and B do not. **Jamo panes** is the strongest depth demonstration and is the default spatial view; its translucent edges explain the different planes faster than the bare strokes. These are separate judgments about interaction and spectacle. The panel-free solid view preserves jamo identity more directly, and the panes are not yet ready to become a lesson representation.

## Next small milestone

Observe several first-time learners on a physical phone with the same three construction tasks, counterbalancing A/B/C order. Ask which piece moved, why the upper letters changed, and whether undo behaves as expected; record hesitation and misplacements as well as enjoyment. Have a fluent Korean reader or lettering designer review the authored 나/난 endpoints and intermediate shapes before treating the geometry as instruction. Separately ask whether the spatial reveal helps identify the two jamo or merely attracts attention. Only if that inspection effect earns clear value should a true sidewall/mesh study or a handoff animation be built. No production integration follows from these browser captures alone.
