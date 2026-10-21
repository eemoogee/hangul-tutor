# Living Syllable: remove and return final ㄴ

Isolated interaction study for **난 → 나 + ㄴ → 난**. It is not a lesson or a handwriting stroke-order demonstration. The depth, thickness, and shadow are visual metaphors for lifting a completed jamo.

## Open it

Open [`index.html`](index.html) directly in a current browser; the file works from `file://` and needs no server, network request, framework, or downloaded font. For a phone, copy that one HTML file to the phone and open it in a browser that permits local HTML. The source font outlines are embedded; interface labels use system fonts.

**Phone file previews:** some attachment or file previewers display HTML and CSS but do not execute its JavaScript. The page then shows a static 난 and a message directing you to **Open in browser** or to download and open the file in Chrome. The controls require JavaScript. If the stage stays static after opening externally, record the browser name and whether the Open button changes the status; that would indicate a separate compatibility problem.

1. Tap the syllable or **Open**. This enters a ready state without moving or changing the assembled 난.
2. Tap final ㄴ or **Lift ㄴ**. It moves down, becomes a standalone ㄴ, and the remaining outlines become 나.
3. Tap the marked slot, the detached piece, or **Return ㄴ** to rebuild 난. Tap the assembled stage or **Close** to leave the ready state.
4. Optionally drag ㄴ. It follows the pointer within the stage's safe bounds. Release near the slot to seat it; release elsewhere to settle at the detached resting position. Nearness alone never seats it.

**Undo** reverses the last completed lift or return. **Reset** restores closed 난. Keyboard users can Tab to the controls and final piece, activate with Enter/Space, and press Escape to cancel an active drag or transition. Relief/Flat, four tuning sliders, **Copy settings**, and a forced reduced-motion toggle are included for owner testing. The operating system's reduced-motion setting also applies.

Under reduced motion, tap and button input remain available. A drag gesture switches at release without moving the piece through intermediate positions.

## Geometry and provenance

The supplied `docs/prototypes/syllable-lift-study/noto-contours.json` identifies its source as the KR face of **Noto Sans CJK KR Bold**, from a Debian/Ubuntu `fonts-noto-cjk` package, extracted with fontTools on 2026-10-19. That JSON records **SIL Open Font License 1.1**. The original font binary and extraction were not independently verified in this study.

The source paths for the initial ㄴ, vowel ㅏ, and final ㄴ in 난 and the corresponding initial ㄴ and ㅏ in 나 are embedded byte-for-byte as path strings. The standalone ㄴ path is translated **(+21, −306.5) font units** so its bounding-box center registers with the final ㄴ's center. This is a documented placement transform, not a change to the standalone contour's shape. The five contextual path strings were checked against the supplied JSON. The original JSON had SHA-256 `26413B9FE2935768E54A1F1B24D602126E3D48091D84A194A7F69F457256186E`; the Syllable Lift Study HTML had SHA-256 `F637E68947DE339867E221F00FBD57F97FDE8CB8CC10CFE5875D5B02560F39F8` before and after this work. Neither original was edited.

All three path pairs have matching command structure and are interpolated numerically each frame. The closed and detached endpoints use the font source outlines, subject to the standalone piece's placement transform. There is **no font-to-vector crossfade**. Reduced motion uses a brief fade between endpoint states, without planar travel or depth.

The final piece's HTML wrapper owns planar movement, perspective depth, and an outline-independent button hit area. Its SVG owns the outline morph and six offset edge copies, following the source study's relief technique. The shadow is on a separate flat layer. No ancestor of an active 3D piece uses clipping, filters, or reduced opacity. The shading pulse uses the source study's diagonal face gradient, shortened to 500 ms by default: all pieces on explicit open/close, only final ㄴ on lift, and no pulse on seating. Flat mode removes edges, shadow, shading, and Z movement while keeping geometry and timing. No plate, flap, whole-syllable rotation, or external graphics library is used.

The assembled 난 is also present as static SVG in the HTML. This preserves a readable reference when a file preview disables scripts; it sits behind the identical script-rendered outlines during the closed and ready states and disappears during movement.

## State and drag rules

The discrete states are `closed`, `ready`, `dragging`, `detached`, and `settling`. Removal progress `p` is 0 at seated 난 and 1 at fully detached 나 + ㄴ. During a drag the wrapper follows the pointer directly, while `p` is calculated from **downward movement along the seat-to-detached direction**. Sideways movement changes position, not shape. The pointer-controlled anchor is clamped to ±20% of stage width horizontally and −12% to +29% vertically to keep it visible; this is the known limit to one-to-one tracking at the stage edge. A drop outside the slot zone settles to the full detached endpoint, never a partly morphed resting glyph.

The transparent final-piece button moves with its HTML wrapper and stays centered on the registered outline family. Its rendered hit area is substantially larger than 44 × 44 px at both requested widths. The slot button is 48 × 48 px. Touch scrolling is suppressed only on the stage; the surrounding page can scroll normally.

## Verification

Automated checks used headless desktop Chrome through Playwright with mobile viewport and touch emulation. They opened the **local file**, with no HTTP server. Results:

| Check | 390 × 844 | 320 × 568 |
| --- | --- | --- |
| Tap open → lift → return | Pass | Pass |
| Drag outside → detached; drag to slot → seated | Pass | Pass |
| Lateral drag leaves `p = 0` | Pass | Pass |
| Undo, Reset, keyboard, Flat, reduced-motion endpoints | Pass | Pass |
| Horizontal overflow, including `p = 0, .25, .5, .75, 1` | 0 px | 0 px in exercised states |
| Final-piece hit area after lift | 146 × 111 px | 120 × 92 px |
| Page JavaScript errors | None | None |

A separate simulated-touch check at 320 px exercised real touch pointer events: tapping the stage, piece, and slot; dragging downward; and moving 50 px sideways. It observed `p ≈ .88` during downward drag, `p = 0` after sideways movement, and no page scroll during the drag. Forced reduced motion held the piece in place during its short fade and rendered the final position with no Z translation.

Dark mode was inspected at 390 px. The detached relief remained legible with a lighter side edge and dark contact shadow; the browser reported a 38 px Z transform. With the system reduced-motion setting, the edge and Z transform were absent.

After a phone screenshot showed a styled but empty stage in a file preview, the blank view was reproduced in desktop Chrome with JavaScript disabled. A static assembled 난 and a browser-opening instruction were added directly to the HTML. With JavaScript disabled at 320 × 568, the revised file showed all three static outlines and had 0 px horizontal overflow. With JavaScript enabled, the original interaction checks still passed. The phone preview's JavaScript policy has not been inspected directly, so this is a supported explanation rather than a confirmed device diagnosis.

Captures were taken at 390 px for `p = 0`, `.25`, `.5`, `.75`, and `1`, plus closed and detached states at both 390 and 320 px, one dark-mode detached view, and a simulated no-JavaScript preview at 320 px. See [`captures/`](captures/). Intermediate images are controlled render-state snapshots; the tap and drag checks above exercise the actual interaction.

## Known limits and next step

- The embedded outline shape, visual edge, and slot remain legible in desktop Chrome at the two simulated phone widths. **Physical Android Chrome testing remains required** for touch feel, projected depth, browser bars, text scaling, and frame smoothness.
- Lateral pointer travel is bounded near the stage edge. This protects visibility but should be judged on the owner's phone for any feeling of resistance.
- The detached ㄴ uses the source font's standalone form with an alignment offset; whether the in-between forms aid learning has not been tested with beginners.
- The page is vertically scrollable at 320 × 568. Its stage and controls remain reachable without horizontal scrolling.

**Recommended next step:** test the exact `index.html` file on the owner's Android phone, tune the four controls, and record whether returning ㄴ feels deliberate and whether learners recognize the transition to 나. Do not infer learning benefit from visual appeal or this browser check alone.
