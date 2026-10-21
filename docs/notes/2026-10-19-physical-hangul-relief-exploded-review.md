# Relief-based exploded syllable — design critique

**Author:** Claude (AI design review) · **Date:** 2026-10-19
**Status:** Design critique and proposal, preserved verbatim. Claims are design judgments, not validated learning results. Not an implementation authorization.
**Topic:** the proposed relief-based exploded syllable interaction (companion to `2026-10-19-physical-hangul-claude-review.md`, which covers the broader physical-interaction design review).

---

Yes — this sounds like the best synthesis so far.

What you're describing is neither the literal exploding cube nor the flat exploded-layers plates by themselves. It's more like:

Relief + controlled exploded syllable

A completed syllable:

- starts as normal readable Hangul
- swells into slight relief so the jamo feel like real pieces
- each jamo morphs toward a default standalone form
- then the pieces separate independently
- but only a little, and in meaningful directions
- with no tumbling, no flipping, no dramatic spinning

That feels much closer to Hangul Tutor's tone.


---

Why I think this is the right direction

It keeps the strengths of both experiments:

From Jamo relief

- letters feel like substantial pieces
- the object feels manipulable
- the result stays visually elegant

From Exploded layers

- components can move independently
- separation reads as a real structural opening
- you get the "exploded view" feeling without needing a cube

And it avoids what bothered you:

- no unrelated cube geometry
- no cards drifting around like unrelated panels
- no upside-down rotating letters
- no exaggerated movement that breaks readability


---

The key design principle

The syllable should not look like it breaks apart.

It should look like it opens up.

That means:

- mild separation
- component-aware paths
- front-facing orientation preserved
- clear relation between assembled and opened states

So for example:

나

- ㄴ shifts slightly left and forward
- ㅏ shifts slightly right and forward
- both morph from syllable-fitted shapes toward their standalone shapes

노

- ㄴ shifts slightly up/left and forward
- ㅗ shifts slightly down and forward

난

- initial ㄴ shifts slightly left/up and forward
- ㅏ shifts slightly right and forward
- final ㄴ shifts slightly downward and forward

Not huge distance. Just enough to say:
“these were compressed together, and now I can see the pieces.”


---

What the motion should feel like

I'd structure it as three phases:

1. Loosen

The completed syllable subtly relaxes:

- tiny lift
- faint seam visibility
- maybe a slight contact shadow or highlight

This tells the learner: this is made of parts.

2. Open

The jamo:

- gain slight thickness
- morph toward standalone default forms
- move outward independently
- separate just enough to be legible

This is the exploded moment.

3. Settle / hold

The opened pieces stabilize:

- no wobble chaos
- no further dramatic motion
- maybe a tiny settling motion

Then on close, all of it reverses cleanly.


---

The morphology should be controlled

This is really important.

You don't want:

- completed syllable shape → suddenly unrelated default letter

You want:

- completed syllable shape → intermediate shape → default letter shape

So the transformation feels continuous.

For example, the vowel inside 나 should gradually become a more ordinary standalone ㅏ, not just "swap" to another SVG at the end.


---

I would keep the 3D very mild

The 3D should help the effect, not dominate it.

I’d suggest:

- slight thickness
- small Z lift
- subtle shadow
- maybe very slight component-specific tilt
- but no global rotation
- and no strong perspective that makes Hangul hard to read

So the impression is:

> “This is a real object opening,”
not
“This is a 3D logo animation.”




---

My recommended next Codex brief

You could send something like this:


---

Codex brief — Relief-based exploded syllable

Build a new isolated experiment based on this direction:

Goal

Combine the strengths of the jamo relief and exploded layers studies.

We want a completed Hangul syllable to:

1. appear as normal readable text,
2. gain slight relief / materiality,
3. morph each jamo from its syllable-fit shape toward a mildly 3D-looking default standalone shape,
4. separate the jamo independently in small, meaningful directions,
5. hold in an exploded state,
6. and close smoothly back into the composed syllable.

Important constraints

- No spinning, tumbling, or upside-down letters.
- No dramatic cube-like rotation.
- No unrelated panel/card feeling.
- The movement should be modest and elegant.
- The exploded state should feel like the syllable has opened, not broken apart.
- Keep the assembled syllable front-facing and readable.
- Use only mild depth cues: slight thickness, slight Z lift, subtle shadow, optional tiny component-specific tilt.
- Jamo should move in different directions based on their role in the syllable, not all together in the same direction.

Initial syllables

Prototype:

- 나
- 노
- 난

Motion design

Use three phases:

1. Loosen — subtle release / seam awareness
2. Open — morph + independent separation
3. Hold / settle — stable exploded view

Closing should reverse these phases smoothly.

Shape behavior

Each jamo should morph continuously:

- from its assembled syllable-fit shape
- toward a default standalone shape

Avoid abrupt SVG swaps if possible.

Compare

Show:

- current relief version
- new relief-exploded version

Evaluation questions

- Does this feel more like a syllable opening up?
- Does the independent movement improve clarity?
- Does the morphing make the structure easier to understand?
- Is the depth subtle but noticeable?
- Does the effect still feel elegant on a phone?

Do not modify production code. Do not commit/push/merge/deploy without approval.


---

My design judgment

I think this has a better chance than either extreme:

- better than the pure cube-inspired 3D approach, because it's more relevant to Hangul
- better than the flat exploded layers approach, because it keeps the letters feeling like real pieces
- better than the simple relief lift alone, because it adds true component independence

So yes — I think this is the clearest version of the idea yet.

If you want, I can also turn your paragraph above into a cleaner, tighter Codex instruction in your preferred style.