# Physical Hangul interaction — independent design review (design-review agent, "Hyojangi")

**Author:** Hermes design-review agent (referred to as "Hyojangi"), 2026-10-19
**Status:** design proposals and predictions. **No claim here is a validated learning result.** Statements marked *Proven* refer to technical feasibility probed in a desktop browser, not to learning value, and not to behaviour on a physical phone.
**Provenance:** This file is a reconstruction of a review delivered in chat on 2026-10-19. It was not recovered from an original authored document, so wording is close to but not identical with the delivered text.

Scope: brief "Independent Design Review — Physical Hangul Interaction". Test syllables: 나, 노, 난.

## Core finding: occlusion is the depth cue, not Z position

Four renderings of 나 were produced and assessed blind (flat; shadow-extruded; `rotateY(32°)`; `translateZ(30px)`).

- **`translateZ` alone produced no perceptible depth.** Assessed as "nearly identical to flat". Z displacement is a depth *coordinate*; it is not a depth *cue*. Without a comparison plane the eye reads it as scale.
- **`rotateY` on a whole syllable reads as a tilted flat card.** Proportions skew, no thickness is perceived. A single rotated plane is still a single plane, and the typography is degraded for nothing.
- **Shadow extrusion reads as a floating object casting a shadow**, not as a solid body. Good for substance, wrong for depth.
- **Separate Z offsets on two jamo still did nothing. Overlap did everything.** When the ㅏ was placed so its excursion overlapped the ㄴ, self-occlusion read as unambiguous depth.

Interpretation: the rotating translucent cube worked because its **overlapping, self-occluding faces** provide continuous occlusion/disocclusion, not because of Z coordinate or rotation in the abstract. The same cue can be obtained from letterforms that belong to Hangul. That is the design problem.

**Caveat:** these assessments came from a single vision-model pass in desktop Chromium at `devicePixelRatio: 1`. It is a sanity check on reasoning, not human perception evidence.

## Critique: a 3D effect is probably not needed

1. **The metaphor is already spatial in 2D.** Hangul box composition is genuine planar structure (ㄴ left, ㅏ right, final below). Perspective foreshortens a vertical vowel stem and a horizontal consonant stem by different amounts, distorting the frame being taught.
2. **The strongest 3D impression came from the least meaningful geometry.** Translucency plus rotation yields real depth information from arbitrary planes. Depth cue worked; content did not carry it.
3. **"Physical" is not "3D".** Tactility comes from response — latency, overshoot, resistance, collision — not perspective. A flat object that resists and rebounds feels more physical than a perspective-distorted object that interpolates smoothly.

**Where 3D is justified:** occlusion between jamo that must occupy the same space. That is Hangul-native and is the subject of the recommended experiment.

## 1. Three concepts

**A. "The Squeezed Joint" (elastic compaction, no 3D).** Jamo begin large and loose; as they reach compositional position the box contracts and strokes abut and share edges. Assembly is a volume change, not a slide-together. 나 and 노 differ only by compression axis: ㅏ compresses x, ㅗ compresses y. The squeeze is the lesson.

**B. "Letterpress Impression" (lighting plus occlusion, single plane).** The workspace is paper under one directional light; jamo are raised metal type casting shadows. Depth comes entirely from consistent light direction, contact ambient occlusion, shadow length/softness encoding height, and an occlusion shadow falling from the top piece onto the piece below. 난 is the showcase: the final ㄴ is the same glyph as the initial, descending and shrinking into the 받침 position.

**C. "The Halved Block" (occlusion-first 3D).** The assembled block splits into two interlocking 3D halves along its own compositional seam and separates in depth. Letters are extruded on the flat faces, so every visible surface belongs to a letterform and the geometry *is* the typography. The halves interlock: the vowel's excursion into the consonant's column is a real notch, so separation reveals the fit. This is the answer to the cube's appeal without an arbitrary cube.

## 2. Perceptual cues, by concept

| Cue | A. Squeezed Joint | B. Impression | C. Halved Block |
|---|---|---|---|
| Depth | None (deliberate) | Directional shadow, contact occlusion | Self-occluding thick edges; kinetic depth under parallax |
| Contact | Non-uniform scale with slight thickening | Shadow snaps from long/soft to short/dark on seating | Hard stop then mechanical slide of the notch seating |
| Weight | Resistance that springs back if over-pressed | Lift slower than drop | Double haptic tick on the seating slide |
| Occlusion | Shared stroke at the join | Top piece casts shadow onto the piece below | Halves occlude each other along the seam |

## 3. Satisfaction without points, badges or celebration

- **Hard stop instead of a snap.** A piece that reaches its destination and refuses to go further feels solid; snap-to-target feels digital.
- **Misalignment resistance.** An off-angle piece drags asymmetrically so the error is felt in the hand before it is seen.
- **Inertia with correct mass.** Heavier pieces decelerate slower; a heavy 받침 teaches that it sits underneath.
- **Sound as material, not reward.** A dry contact tick with mass-dependent pitch; no rising arpeggio.
- **Removal of looseness.** Satisfaction is the transition from jitter to stillness.
- **Micro-camera settle.** A 1–2px scene shift as if the surface took the impact.

## 4. Proven vs speculative

**Proven present in the browser:** `perspective`, `preserve-3d`, `rotate3d`, `translateZ`, `backdrop-filter`, WebGL2. Directional shadow plus overlap is a robust depth illusion and cheap.

**Unverified, materially risky:**
- `preserve-3d` rendering stability on the target phone under load; coplanar extruded faces z-fight; WebKit `preserve-3d` has long-lived bugs.
- Extruding ㅏ (vertical stem with rightward excursion) correctly requires procedural geometry, not a font glyph.
- Anisotropic scaling of font glyphs may read as a broken font rather than compression.
- Device-tilt parallax on iOS requires `DeviceOrientationEvent.requestPermission` — a modal interruption frequently refused.
- Nothing was tested on a physical phone: touch latency, OLED visibility in daylight, and Safari behaviour are all unmeasured.

## 5. Likely failure modes

- Anisotropic scale of authored glyphs looking like a rendering bug (concept A).
- CSS shadows cannot produce convincing contact-hugging ambient occlusion; needs SVG filters or canvas compositing. Shadows vanish on OLED in daylight (concept B).
- z-fighting and `preserve-3d` instability (concept C).
- Spectacle crowding out the lesson: if testers remember the effect but cannot predict 도, it failed.
- Perspective distortion of the composition frame itself.

**Accuracy guardrail:** pieces are always whole jamo. Never animate strokes being drawn. Do not suggest depth, cubes or frames reflect how Hangul was historically designed.

## 6. Recommendation: "Seam Split" spike

One syllable (나), two halves (ㄴ-face and ㅏ-face) as flat SVG with ~6px extrusion. The gesture is a **horizontal drag along the seam** — no free orbit, no cube, no tilt permission.

Three counterbalanced conditions: **A** flat separation (existing baseline); **B** impression only (flat with contact-occlusion shadows snapping short on assembly); **C** seam split (extruded interlocking halves).

Measure: (i) can they name the two parts after 60s; (ii) time to assemble unaided; (iii) do they describe the parts as "beside each other" or "joined"; (iv) unprompted replay rate as an honest proxy for wonder. Extend to 노 and 난 only if C wins — 노 tests whether the notch difference is perceptible, 난 tests three planes.

**Why:** it isolates whether occlusion earns depth without arbitrary geometry, in one controlled manipulation, cheap enough to run before an engine decision.

## Open questions carried forward

- Which sense of 난 is being taught; it is also a real word with several meanings, not only a composition exercise.
- Whether "compressed letterforms and shared strokes" holds up under review by a Hangul type designer. These are general type-practice claims, not verified against a typeface built for this.
