# v2 verification and evaluation

Checked 2026-10-19 against the uncommitted, isolated prototype. `node --check app.js` and the focused Python Playwright/Chromium `verify.py` passed. The browser run opened the local HTML, used 390×844 and 320×568 viewports, generated twelve capture frames, and reported no page or console errors.

| Requirement | Result and evidence |
| --- | --- |
| 나, 노, 난 and component inventory | All three selectors rendered; 나/노 had initial and medial groups, 난 had initial, medial, and final groups. The system-font reference changed with the selected endpoint. |
| Rigid separation baseline | At 0%, 50%, and 100%, the paths moved between packed and free positions. Reassemble returned them to 0%. [Frames 01–03](captures/). |
| Continuous deformation | Selected ㄴ changed its path through 50% while ㅏ's path remained unchanged. The same SVG group survived the move. 노 and 난 paths were also exercised. [Frames 04–07](captures/). |
| Responsive 나 ↔ 난 reflow | Adding final ㄴ changed both upper paths and made the persistent final group visible; dragging final ㄴ downward reversed part of the reflow; removing it returned both upper paths exactly to their initial SVG data. The initial group retained its DOM identity. [Frames 08–10 and 12](captures/). |
| Pointer, touch, and keyboard | Mouse drag and simulated CDP touch drag moved initial ㄴ while medial ㅏ remained anchored. Enter on a focused SVG component selected and then moved it. The slider and labeled buttons provide non-drag routes. |
| Reduced motion | With `prefers-reduced-motion: reduce`, the action reached the endpoint immediately. |
| Small screens and visibility | At 320×568 there was no document-wide horizontal overflow; primary controls were reachable by normal vertical scrolling. [Short-screen frame](captures/11-short-screen.png). Rest, midpoint, end, and reverse frames were visually inspected; no component disappeared unexpectedly or crossed the stage edge in those captures. |

The unchanged [v1 baseline](../exploding-syllable-lab/) remains in its original folder. Its authored SVG components, conventional-glyph crossfade, open/assembled states, per-component dragging, anchored unselected parts, requestAnimationFrame transitions, slider, keyboard support, reduced-motion branch, and browser verifier informed the v2 comparison. V2 reuses the **interaction concepts**, not the v1 source files or typography claims. The v1 file hashes were checked before and after this work, and its original `verify.cjs` browser suite passed again.

## What appears useful

Rigid separation most clearly answers “which part moved?” because the line lengths do not change. Deformation makes the shared-space tradeoff more visible, especially when only one component moves and the other remains anchored. Reflow makes the height change in 나 ↔ 난 directly inspectable; it is the strongest candidate for testing the central hypothesis. The dashed original paths help locate a selected part. These are design observations from the inspected frames, not learner findings.

The glow on selection, dotted grid, and easing make controls readable but are not themselves evidence of Hangul structure. The small system-font comparison helps show that the SVG is a model, yet visual similarity varies with the installed font. At 320×568 the full explanation scrolls below the main controls. Press-and-hold preview was considered but left out because a held touch conflicts with page scrolling and the slider/tap routes already expose intermediate states; this is a design choice to revisit after phone observation.

## Unverified and next step

No physical-phone test, screen-reader audit, Korean type-designer review, fluent-reader evaluation, or beginner learning study was performed. Intermediate reflow frames may look like nonstandard syllables; the UI labels them as transitional states. The geometry is one custom style and must not be generalized to other typefaces or used as handwriting instruction.

**Next small milestone:** conduct a five-person beginner comparison of a static decomposition, rigid separation, and reflow using one prompt: “What changed between 나 and 난, and what stayed the same?” Record component identification and explanation quality before and after each view, and ask a fluent Korean reader or type designer to screen the three endpoint drawings first. Do not integrate with production grading until that evidence is reviewed.

## Additional flat versus shallow-depth extraction check

The separate `verify_depth.py` opens the same local page in Chromium and exercises the fourth **Lift** mode. It checks direct taps on the visible SVG stroke before and after lifting, tap again to restore, a 50% state with identical SVG path data and control value in A and B, a fully lifted state with identical path data, and zero Z at rest. It also checks an adjacent-component switch, Enter on the focused component, and immediate endpoints under reduced motion. Simulated touch taps before and after lift worked in independent 390×844 and 320×568 sessions. A continuous CDP touch drag worked at 390×844; scroll position did not change during that drag. No page or console errors were reported.

At 390×844 and 320×568 in Chromium, the page had no horizontal overflow and the lifted path's measured bounds stayed within the viewport. The resulting [A/B state captures](captures/) were visually inspected at assembled, partial, fully lifted, and restored states. The projected stroke remained readable; at full depth it appeared slightly softer, consistent with perspective resampling. The short viewport required normal vertical scrolling to reach lower controls. The transformed transparent hit path moved with the visible component in the direct tap checks. CSS perspective was the only authored difference between A and B; its natural projected enlargement and possible antialiasing variation are unavoidable perceptual differences and are listed in [the comparison note](SHALLOW-DEPTH.md).

The browser checks are simulations. Physical Android touch accuracy, performance, text legibility, screen-reader behavior, and beginner comprehension remain unverified. This addition is a candidate for a small controlled usability test, not evidence that depth improves learning. The earlier three-mode verification above still passes after the fourth mode was added.
