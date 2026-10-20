# Open a Syllable — visual interaction lab

An isolated, unscored Hangul Tutor experiment. It opens **나**, **노**, and **난** into separately manipulable jamo, then lets the learner reassemble them. It does not load the curriculum, Sejong, Pyodide, learner saves, or a backend. No prototype or production file outside this folder was edited.

## Open it

Open `index.html` directly in a desktop browser, or run `node serve.cjs` from this folder. The server prints a desktop URL and available LAN URLs. For a phone, use a LAN URL while the computer and phone are on the same Wi-Fi and the server is running. A system firewall may ask whether Node can accept private-network connections; the prototype does not change firewall settings. No audio or network assets are required.

Choose a block, then compare **Structure** with **Glyph bridge**. Structure begins with colored geometric components already discernible inside the block. Glyph bridge begins with a conventional font glyph and crossfades into the same geometric components when opened. **Open all** separates every component; the slider allows slow inspection and reversal. **Pull a letter** keeps the unchosen components anchored: drag a colored stroke outward or back, or select it and use the button, slider, or a second tap. Keyboard focus and Enter/Space work on the components; the labeled component chips are another tap/keyboard route. A detached component stays detached until returned. Reassemble closes the whole block.

## Visual model and limits

The SVG contains an authored path for each component. Its points interpolate continuously between a compact block arrangement and a larger standalone drawing. The part is the same SVG element throughout the movement. A dashed footprint and the faint original paths show where detached letters belonged. For **난**, the two ㄴ shapes are separate elements with separate initial/final roles.

The Glyph bridge does **not** morph real font outlines. It fades a conventionally rendered Unicode syllable into simplified custom geometry before the component paths spread apart. These drawings explain side, lower, and final positions; they are not universal Korean typeface construction, official handwriting stroke order, or a graded reading task. The direct mode's legibility at intermediate positions and the shape proportions need review with Korean readers and beginners. The sound of each syllable is outside this visual experiment.

This prototype is instructionally separate from Vowel Machine: Vowel Machine constructs a **vowel** from its base and short mark; this lab separates or assembles **already formed jamo** inside a syllable block. A future shared component stage or gesture layer could serve both, but they should keep different content and grading models. The existing Living Syllable workshop brief and Jamo Interaction Lab informed the persistent-part and tap-alternative choices; neither was modified.

## Verification

Run `node --check app.js`, `node --check verify.cjs`, and `node verify.cjs` in an environment with Playwright's Node package and Chrome. The browser verifier uses the local HTML file by default; set `PROTOTYPE_URL` to test the running HTTP route. It writes screenshots to the worktree's ignored `.verify_out/exploding-syllable-shots/` folder. On 2026-10-19, the checks passed against both the local file and the HTTP route in desktop Chrome automation: three syllables, reversible automatic separation, partial scrubbing, the conventional-glyph bridge, anchored direct lift, pointer drag, touch tap, keyboard control, 390×844 and 320×568 layouts, reduced motion, and no page errors. At 320×568 the main controls are reachable without horizontal overflow; the explanation below them naturally scrolls. These are simulated browser sizes and inputs, not a real-phone or learner study.

Useful generated frames are `na-type-closed-390x844.png`, `na-open-390x844.png`, `no-open-390x844.png`, `nan-final-pulled-390x844.png`, and `nan-closed-320x568.png`. The verifier also captures a mid-transition glyph bridge and a direct drag state.

## What this small build reveals

- The anchored letter plus a dashed footprint makes an **incomplete** block possible to inspect. The final ㄴ in 난 can move away while the initial ㄴ and ㅏ stay put.
- Structure is clearer about *which component moved*. Glyph bridge gives a familiar starting glyph, but its fade into the custom drawing is a visible design choice, not a literal typographic morph. Which is easier for a beginner remains untested.
- The same geometry supports automatic opening, scrubbed inspection, and direct manipulation. The first tap can select a part; the second lifts it. Dragging need not be the only way to play.

## Next experiments, after review

1. Give a few learners who do not know Hangul a before/after component-identification and placement task. Ask what moved and what stayed, rather than judging the interaction by speed alone.
2. Have a Korean typography reviewer assess the custom strokes, especially the compact form and final ㄴ in 난. Decide whether the Glyph bridge earns its crossfade or whether the structural view is sufficient.
3. Try one reverse construction task: place the **existing** ㄴ and ㅏ into 나 without revealing the finished block. Keep that distinct from building ㅏ out of strokes.
4. If the interaction becomes lesson content, let Python choose the prompt and evaluate the learner response. Do not copy this prototype's animation state into mastery or save logic.
