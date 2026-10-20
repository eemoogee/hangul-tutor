# Korean typography research for the v2 study

Research checked 2026-10-19. This note separates encoded syllable structure, type design, and our own animation. It does not claim to describe every Korean font.

## Findings from primary and specialist sources

| Finding | Evidence | Scope |
| --- | --- | --- |
| A modern Hangul syllable can be decomposed into leading consonant, vowel, and optional trailing consonant. 나 is ㄴ+ㅏ; 노 is ㄴ+ㅗ; 난 is ㄴ+ㅏ+ㄴ. | [Unicode §3.12](https://www.unicode.org/versions/Unicode18.0.0/core-spec/chapter-3/), [National Institute of Korean Language](https://www.korean.go.kr/eng_hangeul/principle/001.html) | Character identity and order, not visual outlines. |
| Hangul type often fits phonemic parts into a square block. Side vowels and lower vowels create different spatial arrangements. | [Jiwon Yu at MoMA](https://www.moma.org/explore/inside_out/2015/02/05/korean-hangul-typeface-design-a-unique-game-of-modular-design/), [Microsoft Hangul font development](https://learn.microsoft.com/en-us/typography/script-development/hangul) | Broad type-design principle. Exact proportions differ by style and glyph. |
| The number and shape of parts affect spacing within the block; adding a final consonant may require different leading and medial forms. | [MoMA](https://www.moma.org/explore/inside_out/2015/02/05/korean-hangul-typeface-design-a-unique-game-of-modular-design/) discusses context-sensitive spacing; [Microsoft](https://learn.microsoft.com/en-us/typography/script-development/hangul) describes contextual leading, vowel, and trailing jamo forms for Old Hangul OpenType shaping. | Evidence that contextual form is a real type-design concern, not a universal numeric transformation. Microsoft's feature discussion focuses on Old Hangul shaping in Uniscribe. |
| Both fixed-width and proportional-width Hangul fonts exist. Jamo sequences may need context-sensitive rendering and are often converted to precomposed syllables for display. | [W3C Korean layout requirements](https://www.w3.org/TR/klreq/), §§4.1–4.2 | The W3C document includes draft/incomplete sections. It does not provide canonical path coordinates for these three syllables. |
| Precomposed Unicode syllables encode a character and support algorithmic decomposition, but do not provide separate SVG paths for their constituent jamo. | [Unicode §3.12](https://www.unicode.org/versions/Unicode18.0.0/core-spec/chapter-3/) specifies character mappings; [Microsoft](https://learn.microsoft.com/en-us/typography/script-development/hangul) distinguishes character processing from font glyph shaping. | Inference from what the standards encode. Outlines belong to a font and cannot be recovered as standardized jamo paths from the code point alone. |

Jiwon Yu's MoMA essay shows square and out-of-square modules, and demonstrates that even nominally similar parts vary in size, placement, and spacing between typefaces. We therefore did not trace one font's outline or apply one transformation to all fonts. The small SVG set is an **instructional lettering model** with approximately constant stroke weight and point-by-point interpolation. The conventional glyph beside it is rendered by the reader's installed system font as a comparison. Different devices may show a different reference glyph.

### Two local font observations

For a bounded font comparison, the installed **Malgun Gothic** and **Noto Sans KR** were rendered at a nominal 120 px with Pillow on this Windows host. The ink bounding-box widths/heights for Malgun Gothic were 나 `99×113`, 노 `104×85`, 난 `96×109`; Noto Sans KR gave 나 `95×106`, 노 `97×82`, 난 `93×103`. Standalone compatibility ㄴ and ㅏ occupied very different extents from the completed syllables in both fonts. This confirms that even the overall ink dimensions of these selected glyphs differ by font and syllable. The measurements do **not** identify which pixels belong to a particular jamo, prove how a font constructed the glyph, or justify the prototype's exact component coordinates. No font file or outline is included in the archive.

## What the prototype chooses

- One geometric, monoline style, drawn in SVG by this project. No proprietary font assets or outlines are redistributed.
- Three examples only: 나 (side-by-side), 노 (stacked), 난 (final consonant). The initial ㄴ in 나 and 난 is the same linguistic component but uses different authored endpoints; the two ㄴs in 난 have distinct initial and final roles.
- Separation mode translates each packed shape rigidly. Deformation mode interpolates each line point between a packed and a standalone drawing. Reflow mode interpolates upper-part drawings between 나 and 난 while the final ㄴ enters or leaves.
- Mid-transition drawings are visual explanations, **not valid characters for typesetting**. In particular, a partly visible final consonant is a transition frame, not an alternate syllable spelling.
- A component's DOM/SVG identity persists through an interaction. Its path coordinates change; its linguistic identity does not.

## Uncertainties and review gates

The selected dimensions, line endings, and motion paths are not established by Unicode, W3C, Microsoft, or MoMA. They need a fluent Korean reader and Korean type designer to assess legibility, especially 난 with a final ㄴ, intermediate reflow frames, and whether the standalone proportions feel natural. The conventional reference may differ substantially by OS font. A beginner comparison must test whether the animation improves structural understanding beyond a static decomposition, preferably by asking learners to identify which component moved and why the upper parts changed. No such learner outcome is claimed here.
