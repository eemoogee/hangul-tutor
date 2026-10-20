# Component geometry specification

All coordinates are in the `360 × 320` SVG viewBox. The dashed frame is only a spatial cue. Each component is a persistent `<g>` with one visible path and one transparent hit path. Each visible line is an authored polyline with round caps and joins, `9` SVG units wide. No font outline is stretched or extracted.

| Syllable | Component | Packed arrangement | Free arrangement |
| --- | --- | --- | --- |
| 나 | initial ㄴ | Left region, tall vertical then short baseline | Moves left; baseline widens and vertical shortens |
| 나 | medial ㅏ | Narrow right column, tall stem and short right branch | Moves right; branch lengthens |
| 노 | initial ㄴ | Upper region, wide baseline | Moves toward upper left and gains height |
| 노 | medial ㅗ | Lower region, short vertical above wide horizontal | Moves toward lower right; both strokes gain room |
| 난 | initial ㄴ | Upper left, shorter than in 나 | Moves left and becomes taller/wider |
| 난 | medial ㅏ | Upper right, shorter than in 나 | Moves right and becomes taller/wider |
| 난 | final ㄴ | Lower region, wider baseline | Moves down; vertical and baseline gain room |

The exact vertices are the `GLYPHS` data at the top of [app.js](app.js). The paths retain identical point counts between paired endpoints, so each corresponding point can interpolate directly without a shape swap. For a point `P`, deformation uses `P(t) = (1−t)·Ppacked + t·Pfree`, with `t` from 0 to 1. Rigid separation instead translates every packed point by the same fraction of the packed-to-free centroid displacement; its stroke lengths stay fixed. This makes the first two modes a controlled comparison.

Reflow has a different pair of endpoints: the upper initial and medial paths start at the packed **나** drawing and end at the packed **난** drawing. The final ㄴ has a persistent SVG group; it starts offset below and transparent, then approaches its packed 난 position as opacity rises. The same scalar `t` drives all three parts. Endpoints are meant to read as 나 and 난. The intermediate image is intentionally labeled “reflowing,” because it may not be a conventional glyph.

The drawing is deliberately narrow: it models one geometric style, three syllables, and one final consonant. It cannot generalize to arbitrary jamo combinations, compound vowels, other typefaces, or handwriting order. A Korean lettering review is needed before educational reuse.
