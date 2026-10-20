# Relief-exploded syllable study — notes

Open [index.html](index.html) directly in a modern browser. It is a standalone, offline comparison of **나, 노, 난** across V1 flat/fixed, V2 flat/morphing, and V3 relief/morphing. No curriculum or existing prototype source is loaded or changed. The page has no direct manipulation, substitution, sound, or scoring.

## Geometry and provenance

I inspected Exploding Syllable v2's [geometry specification](../exploding-syllable-v2/GEOMETRY.md) and [source](../exploding-syllable-v2/app.js), the [Jamo Relief study](../exploding-syllable-v2/depth-relief-study/README.md), and the [Living Syllable Interaction Lab](../living-syllable-interaction-lab/README.md) before building this experiment. This study retains v2's independent jamo identities, segment/point topology, and three-syllable scope. **Every SVG face is an authored instructional vector, not a verified font outline.** The new packed coordinates were visually recalibrated against locally rendered regular Noto Sans KR at the closed endpoint. The Living Syllable lab informed persistent parts and explicit tap controls. The relief study informed the eight offset SVG face copies and contact cue. None of those earlier files was edited.

Each ㄴ uses one six-vertex filled L outline. Each ㅏ and ㅗ uses the same two four-vertex rectangular subpaths for all its forms. Context and standalone forms have the same command order and point count, so direct interpolation cannot swap topology. A single canonical standalone centerline is translated to each part's packed center before interpolation. The authored centerline dimensions (SVG units) are:

| Jamo/form | Packed width × height | Standalone target width × height |
| --- | ---: | ---: |
| ㄴ in 나, initial | 76 × 91 | 98 × 112 |
| ㄴ in 노, initial | 97 × 59 | 98 × 112 |
| ㄴ in 난, initial | 74 × 62 | 98 × 112 |
| ㄴ in 난, final | 92 × 39 | 98 × 112 |
| ㅏ in 나 | 28 × 146 | 58 × 120 |
| ㅏ in 난 | 27 × 102 | 58 × 120 |
| ㅗ in 노 | 131 × 53 | 130 × 68 |

Thus the two ㄴ pieces in 난 begin with distinct contextual proportions but move toward the same standalone dimensions. The final ㄴ remains a separate DOM/SVG component throughout. Noto's printed 노 joins the upper baseline and vowel stem; the study represents them as two independently movable shapes that meet at rest. A fluent Korean reader and type designer should review all forms and the intermediate morphs before educational use.

## Typeface and license

The closed state is **real Unicode text** (`나`, `노`, `난`) with CSS `font-family: "Noto Sans KR", "Malgun Gothic", sans-serif`, regular weight. The test host has Noto Sans KR installed. The browser study does not redistribute a font file or load a remote font, so a physical phone without that family will show a fallback; compare the closed glyph on that device before judging the crossfade. [Noto Sans CJK's official license](https://github.com/notofonts/noto-cjk/blob/main/Sans/LICENSE) is SIL Open Font License 1.1. [Pretendard's project README](https://github.com/orioncactus/pretendard/blob/main/packages/pretendard/docs/en/README.md) also identifies its SIL Open Font License; it was investigated but not used. Neither font's outline is copied into the SVG artwork.

After closing movement settles, the authored faces fade out and the real text fades in over **120 ms**. Opening reverses the fade before movement. This is an endpoint handoff, not a path swap during motion. Noto's curved or optically adjusted edges differ from the study's square-ended, monoline geometry; the crossfade is visible on close inspection. The mismatch may be larger with a fallback font. The hand-authored packed positions approximate the local Noto rendering, not every device or weight.

## Motion and comparison controls

All three variants use the same directional vectors, distance slider, duration, timeline, and one settle. Default movement is 42 SVG units (about 12% of the 360-unit stage width); diagonal directions are normalized. The first 16% of the timeline reveals a faint seam while pieces stay in place. From 16–90%, pieces separate and V2/V3 interpolate the same face outline toward the standalone form. The last 10% returns a 3.5% positional overshoot to the endpoint once, then holds still. Closing reverses the timeline and ends on real text. There is no continuous wobble or rotation.

V1 keeps each packed face rigid. V2 changes only the face geometry. V3 has V2's exact front face and planar movement, plus eight darker copies offset by the relief-depth control and a low-opacity, unblurred contact ellipse. During loosen these copies expose roughly a fifth of their final side offset. No component rotates. Only a tapped piece in opened V3 receives forward `translateZ` (six times the depth slider, 42 px by default) under a 1250 px perspective; V1/V2 apply the same warm selection color with no Z movement. This is an approximate side surface, not mesh extrusion. Relief thickness and contact cue are bundled in V3, so this page does **not** isolate their individual effects.

Each jamo is in its own HTML wrapper around an SVG. The wrapper carries the transform and the SVG carries the outline interpolation. Hit paths follow the transformed piece; an additional transparent 58 × 58 SVG-unit hit box provides at least 44 × 44 CSS pixels at the tested narrow width. Labeled buttons are another 44 px tap route. The stage and jamo groups support keyboard Enter/Space. Ancestors of transformed pieces keep `overflow: visible`, computed opacity 1, and no CSS filter. The real-text crossfade changes the opacity of leaf faces rather than the 3D ancestor. There is no animated blur or shadow.

System reduced-motion preference and the on-page simulation switch both use immediate assembled/opened positions with a short opacity fade. Side thickness, contact shadow, and Z inspection are suppressed. The opened arrangement remains available without motion.

## Browser verification and captures

Run `verify.py` with Python Playwright and Chromium; `node --check app.js` checks syntax. The latest local Chromium run passed at **390×844** and **320×568** with simulated touch: matched front paths and planar transforms across variants at equivalent states; topology equality; directions; separate initial/final ㄴ; stage and ground bounds; maximum distance; 44 px targets; reversible live timing; tapping a moving part and an opened part; inspection Z only in V3; flat selection in V1/V2; tuning controls; keyboard; system and simulated reduced motion; text endpoint; and no page error or horizontal overflow. These are browser simulations, not physical-device results.

The [captures](captures/) include closed, 50%-timeline, and opened frames for every syllable and variant at both widths. V2 has additional **25%, 50%, and 75% of the morph phase** captures for all three syllables at both widths; [난 V3's three morph frames at 320 px](captures/compare-난-v3-morph-320.png) are also grouped together. The [나 midpoint variant comparison at 390 px](captures/compare-나-middle-390.png) and [난 open variant comparison at 320 px](captures/compare-난-open-320.png) place V1/V2/V3 together. Additional [85% 난 relief](captures/난-v3-late-320.png), [inspected 난](captures/난-v3-inspect-320.png), and [full 320 px page](captures/full-page-open-320.png) show the settle and phone layout. At 320 px the page scrolls vertically to reach tuning controls. In the inspected frames, the SVG side edges are clearly visible while the front jamo remain identifiable. The contact ellipses and packed-position seams are deliberately faint. At high relief depth or with the final ㄴ near the bottom, the view has less spare room; the maximum-distance browser check confirms the face bounds still fit the 360-unit stage.

I visually reviewed the 25/50/75 morph frames for ㄴ, ㅏ, and ㅗ at both widths. Their L and bar contours remain separate and recognizable; I saw no blobs, contour reversals, or self-intersections. This is a browser-frame judgment, not a fluent Korean lettering review.

The browser captures do not establish smoothness or hit precision on a physical Android phone. Verify touch targeting during motion, Noto/fallback text, relief projection, 320 px legibility, and reduce-motion behavior on that device. Screen-reader announcements and other browser engines also need checking. No learner study has been conducted.

For a small beginner session, counterbalance V1/V2/V3 order and ask about 난's component count before opening, the repeated ㄴ after opening, and where ㅜ would go in unseen 두. Record first attempts, hesitation, confusion, and reconstruction. Ask **which version feels best to touch** and **which looks most striking** as separate questions. Around five beginners can guide iteration, not establish improved learning. These are future human evaluations, not results of this prototype.
