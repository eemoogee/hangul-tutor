# Shallow-depth jamo extraction — controlled A/B study

This is the fourth comparison inside the isolated Exploding Syllable v2 study. It asks whether a small impression of lifting one completed jamo from a shallow relief helps a beginner recognize syllable components. The assembled 나, 노, or 난 remains flat. Depth is an inspection metaphor, not a structural property of Hangul writing.

## Interaction and controls

Select **04 Lift**, then **A · Flat extraction** or **B · Shallow depth**. Tap a component to lift it; tap it again to return it. Tapping an adjacent component returns the first while lifting the new one. Other parts remain anchored. A labeled component button, the action and Reassemble buttons, the slider, Enter or Space on a focused SVG part, and optional continuous pointer dragging expose the same state without requiring drag, hover, or rotation. The flat condition remains usable with reduced motion; the motion preference also makes action animations immediate.

In both conditions, the same authored SVG `packed` and `free` polylines interpolate point by point. Planar coordinates, path identity, `480 ms` cubic easing, pointer and keyboard handling, color, stroke width, dashed original position, labels, and feedback text use the same code. Only the selected part can have a nonzero progress value after a completed action. The main SVG retains the shared grid and original-position marks. In Lift, its ordinary component group is hidden and each jamo is rendered in a separate HTML `.relief-piece` wrapper containing its own SVG path and transparent hit path.

The scene uses `perspective: 700px` with a centered perspective origin. JavaScript writes `--lift-z: 0px` for every wrapper in A, and `--lift-z: progress × 56px` for the selected wrapper in B. CSS applies `translate3d(0,0,var(--lift-z))` to that wrapper. The child SVG path supplies geometry and proportional deformation; CSS supplies perspective and compositing; JavaScript supplies selection, progress, and animation. All wrappers have Z = 0 at rest. The stage card and SVG wrappers allow overflow, and no ancestor filter, reduced opacity, or whole-syllable transform flattens the scene. The transparent SVG hit path lives inside the transformed wrapper, so its interactive position follows the projected stroke. `touch-action: none` on the scene and hit paths limits accidental page scrolling during an active drag.

## What differs between A and B

The only authored condition difference is the Z value. Perspective inherently changes the projected size and screen position of a forward piece; these are perceptual consequences of the depth manipulation, not separately controlled factors. It can also change browser antialiasing and produce some softness in a composited stroke. Those image-sampling effects cannot be eliminated while keeping CSS perspective. Device pixel density, browser engine, system font in the small reference, and focus indication can vary between sessions. The reference font is outside the animated comparison. No rotation, shadow, color, explicit scale, or whole-syllable tilt is exclusive to B.

The prototype has only three authored syllables and one custom monoline style. The unselected components stay geometrically anchored; a previously selected piece returns during an adjacent-piece switch. The full page scrolls vertically on a short screen. No physical Android phone, other browser engine, screen reader, or Korean lettering review has been completed. Simulated Chromium touch and viewport checks are recorded in [VERIFICATION.md](VERIFICATION.md).

## Beginner evaluation before an educational claim

First screen the custom endpoint drawings with a fluent Korean reader or letter designer. Then recruit beginners who have not practiced the test syllables. Counterbalance A→B and B→A order; use equivalent unfamiliar syllables and swap item sets between orders. The current three-item demo is too narrow for that study, so additional checked stimuli would be needed without changing this isolated prototype's inference.

After each condition, ask learners to (1) count jamo in an unfamiliar completed block, (2) identify the component that moved or changed, (3) decompose or reconstruct a new block without hints, and (4) explain how the parts' positions relate to the completed block. Record first-attempt accuracy for each task, hesitation time, confusion or wrong taps, requests for help, and the learner's own explanation. Keep prompts, exposure time, feedback, and device constant, and observe the tap target and readability on a physical phone. Visual appeal and completion speed may inform usability but cannot establish learning. A small session can identify promising behavior; it cannot prove a superior learning outcome.

## Recommendation

The controlled browser comparison is feasible, and the modest depth effect stays legible in the inspected Chromium captures. It merits a small physical-phone usability and beginner-comprehension test after the lettering review. There is no evidence yet to prefer B for teaching or to put it in production. Keep A available as the flat and reduced-motion alternative.
