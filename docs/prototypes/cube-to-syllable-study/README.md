# Cube-to-syllable visual study

Open `index.html` in a browser, or run `node serve.cjs` in this folder and visit `http://127.0.0.1:8892/`. It is a standalone, unscored visual experiment. The existing flat Exploding Syllable lab and the tutor are unchanged.

The owner supplied the original exploding-cube CSS on 2026-10-19. `style.css` keeps its unit-scaled `110u` face, `300u` hit area, `800u` perspective, `preserve-3d` cube, six face orientations, transparent pink panels, top/bottom transparent borders, `64u → 108u` radial separation, spring-like transform transition, and `-24°`/full-turn `spin` keyframes. The adaptation makes the front and right faces letter-bearing; four remaining translucent faces retain the cube's spatial scaffold. The rest view places a readable flat **나** over the loose cube. Opening hides that overlay and moves all faces outward while rotation begins. Reassemble returns to the readable block.

**01 Glass panels** is closest to the supplied cube. **02 Bare letters** retains the same oriented planes and spin but hides the surfaces. Fourteen thin copies behind each foreground glyph form a limited CSS extrusion. This makes letter depth more visible than ordinary flat text, but its edges are imperfect and the glyphs can disappear edge-on. A convincing freestanding 3D jamo with continuous sidewalls, lighting, and stable legibility from every angle would need authored mesh geometry or a 3D rendering engine. The panel version communicates the borrowed cube's spatial structure much more clearly.

The central object can be turned by dragging or by focusing it and using arrow keys. Opening starts rotation; the Pause/Resume button controls it. Reduced-motion preference disables automatic rotation. This is an inspection metaphor: written Hangul is flat, and the planes are not a claim about its actual construction.

Run `node --check app.js`, `node --check verify.cjs`, and `node verify.cjs` with Playwright and Chrome available. The verifier captures 390×844 and 320×568 screenshots under `.verify_out/cube-to-syllable-study/`. The prototype uses no hosted assets or audio. It has not been reviewed on a physical phone or by Korean typography readers.
