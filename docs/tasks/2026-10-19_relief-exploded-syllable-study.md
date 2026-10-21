# Task: Relief-exploded syllable study (isolated prototype)

**Date:** 2026-10-19
**Background:** `docs/notes/2026-10-19-physical-hangul-design-synthesis.md` and the two Claude reviews it cites.

**Authorization**
- This is an isolated experiment. Do not modify production code (`web/`, engine files) or existing prototypes.
- Do not commit, push, merge or deploy without owner approval.

**Goal:** build three comparable versions of a reversible "syllable opens up" interaction for 나, 노 and 난. The owner and testers will judge them on physical phones. Aim for an impressive but restrained feeling of physical pieces opening: no arbitrary cube geometry, no tumbling, no spinning, no upside-down letters.

## 1. Three variants

All three use the same independent jamo composition model: every jamo is its own object, moving on its own path in its own direction. They share identical timing, directions, distances and controls.

- **V1 — flat, independent separation, no morphing.** Each jamo separates independently in the screen plane, keeping its in-syllable shape. It must show real independent jamo separation; it must **not** move a completed syllable glyph around as one rigid unit.
- **V2 — V1 plus morphing.** Same movement as V1; each jamo also morphs from its in-syllable shape toward its standalone shape.
- **V3 — V2 plus clearly visible relief.** Same movement and morphing as V2, plus relief that a viewer **notices immediately**: visible thickness, a contact shadow, and lighting that gives the pieces substance. A technically nonzero but imperceptible depth does not meet this requirement. The assembled syllable must remain flat and legible.

**Forward lift (Z-axis):**
- In V3, reserve forward lift mainly for the piece the learner taps to inspect.
- In V1 and V2, show an inspected piece with a flat highlight instead.

**Variant switcher:** on the page, so all three can be compared on one device.

## 2. Directions

Distances start at about 10–15% of block width, adjustable from the page.

| Syllable | Piece | Direction |
|---|---|---|
| 나 | ㄴ | left |
| 나 | ㅏ | right |
| 노 | ㄴ | up |
| 노 | ㅗ | down |
| 난 | initial ㄴ | up-left |
| 난 | ㅏ | up-right |
| 난 | final ㄴ | down |

## 3. Motion phases

1. **Loosen:** a faint seam appears between the pieces; slight lift in V3 only.
2. **Open:** pieces separate; morphing in V2 and V3.
3. **Hold:** settle once, then stay still.

Closing reverses the phases and ends on real text (section 5). Use spring-style easing; no continuous wobble.

## 4. Geometry

**Lettering model.** Deliberately use distinct contextual forms. Contextual proportions vary by typeface; this is the prototype's chosen model, not a universal rule. Forms needed:
- ㄴ: 나-initial, 노-initial, 난-initial, 난-final, standalone
- ㅏ: 나, 난, standalone
- ㅗ: 노, standalone

**Morphing acceptance criteria.** All three are required; equal point counts alone are not enough.
1. **Point correspondence:** each point maps to its counterpart in the other form.
2. **Matching path topology:** the same contours, in the same order and direction.
3. **Readable in-between shapes:** check at 25%, 50% and 75% of the morph; no blobs, self-intersections or unrecognizable letters.

**Source.**
- Investigate open-licence Korean fonts (for example Noto Sans KR or Pretendard, under the SIL Open Font License) as a reference or source, and record the licence.
- A font-extraction pipeline is **not** required. Hand-authored outlines are acceptable.
- In the notes, label each outline as "authored instructional vector" or "verified font outline." Matched authored vectors show the idea; they do not represent how any font actually constructs its syllables.

**The 난 check.** Both ㄴ forms keep distinct proportions in context, yet both morph toward one recognizable standalone ㄴ.

## 5. Ending on real text

- The closed state must display real, readable Korean text in a named font.
- If the authored pieces and the font glyph don't match exactly, use a brief crossfade (about 150 ms or less) after the pieces settle.
- Document the font, the crossfade, and any visible mismatch.

## 6. Safeguards

- **Reduced motion:** when the phone's reduce-motion setting is on, show clear assembled and opened states with a short crossfade. No movement and no depth.
- **Moving tap targets:** tap zones follow the pieces in every state; minimum 44 × 44 px.
- **CSS 3D flattening:**
  - No `overflow` other than visible, `filter`, or `opacity` below 1 on ancestors of 3D-transformed elements.
  - Wrap each SVG piece in its own HTML element.
  - Verify on device that depth actually renders.
- **Performance:** animate only position and transparency; never animate blur.
- **Screen widths:** must work at 390 px and 320 px.
- **Accuracy:** no stroke-drawing animation and no historical claims in on-screen text.

## 7. Deliverables

- **One page** in `docs/prototypes/`, with:
  - the variant switcher
  - tuning controls for distance, duration and depth
  - a reduced-motion toggle for testing
- **A short notes file** covering:
  - geometry sources, with each outline labelled as authored or verified, and the licence
  - the crossfade
  - screenshots of the 25%, 50% and 75% morph states
  - known issues
  - screenshots at 390 and 320 px

## 8. Evaluation (done by people, not Codex)

Score **physical feel** and **visual spectacle** separately for each variant.

**Device checks (owner):**
- smooth motion on the owner's Android phone
- letters readable at 320 px
- tap targets accurate while pieces move
- reduced-motion version correct
- V3 relief immediately noticeable while the assembled syllable stays flat and legible

**Beginner session** (about five absolute beginners, if available):
- Before opening 난: "How many pieces?"
- After opening: "Which pieces are the same letter?"
- Transfer, with 두 never shown: "Where would ㅜ go in 두?"
- Which version feels best to touch, and which looks most striking? Ask as two separate questions.

**What counts as a result:** record observations only. A sample this small gives direction, not evidence of learning gains. Make no learning claims from it.

## 9. Out of scope

Direct manipulation, substitution, sound, scoring, and integration with the curriculum. Manipulation and substitution (lift a piece, swap ㅏ→ㅗ, add a final, close into the new syllable) are the identified next phase.
