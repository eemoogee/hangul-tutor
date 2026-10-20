# Living Syllable interaction lab

Standalone browser comparison of tactile construction and an optional spatial reveal. It does not load the curriculum, Sejong, Pyodide, production saves, network assets, or audio. Nothing is scored or persisted.

## Open and play

Open `index.html` directly, or run `node serve.cjs` in this folder. The server prints a desktop URL and available LAN URLs. A phone can use a LAN URL while it and the computer are on the same Wi-Fi and the server is running; a private-network firewall prompt may need the owner's approval. This is local previewing, not a deployment.

**Construct:** C Transform opens by default; switch among A Basic, B Tactile, and C Transform. Every treatment uses the same three tasks: **ㄴ + ㅏ → 나**, **나 + ㄴ → 난**, and **난 → 나 + ㄴ**. Tap a component on the drawing or its labeled button to lift it; tap its outlined place or labeled place button. Dragging to the outlined area is optional. Undo reverses the last placement, including the final-consonant removal. Switching treatments restarts the current task for a comparable attempt. Back and Reset are available.

**Spatial reveal:** switch between translucent jamo panes and panel-free solid strokes. Open, close, scrub intermediate frames, and turn the opened view with buttons. The flat resting state remains readable. No continuous rotation takes control away from the reviewer. The spatial study uses **나** only; the full three-step construction sequence stays in the Construct tab.

## Files and provenance

`app.js` reuses the authored initial/vowel/final SVG endpoint coordinates from Exploding Syllable v2 (`../exploding-syllable-v2/app.js`); only the free final ㄴ is shifted 16 SVG units lower to make set-aside distinct from the lower slot. Each component keeps one persistent SVG group throughout a task and across tasks. The browser model stores placed/free component state and an undo stack; animation only presents state changes. This is local interaction logic, not a second curriculum or mastery engine.

The spatial view adapts the owner's exploding-cube mechanisms—perspective, `preserve-3d`, separate rotated planes, X/Y/Z motion, and translucency—but contains only two jamo-sized objects. It has no four blank scaffold faces. The second view uses twelve layered SVG strokes behind each front stroke to suggest volume. These are visual metaphors, not Hangul history or typography rules. See [DESIGN.md](DESIGN.md) for alternatives, trade-offs, and evaluation.

## Verify and review captures

From this folder, run `node --check app.js`, `node --check verify.cjs`, and `node verify.cjs` with Playwright and Chrome. The verifier exercises all three tasks in all three construction treatments, incomplete states, persistent component identity, drag approach reflow, attraction, undo, pane/solid depth, scrubbing and reassembly, keyboard activation, touch simulation, reduced motion, and 390×844/320×568 layouts. It writes PNGs to `.verify_out/living-syllable-interaction-lab/` in this worktree. `node capture.cjs` records six timed frames for each transition plus two contact sheets in the same output folder. Copies of the two sheets are kept in [captures](captures/) for portable review. Playwright video recording could not start its encoder in this sandbox (`spawn EPERM`), so the deliverable uses inspectable frame strips instead of video.

The 2026-10-19 local Chromium run passed all checks above with no page errors. At 390×844 the construction actions fit in the viewport. At 320×568 the page scrolls naturally to keep touch controls readable and reachable; the simulated 200% text setting keeps the spatial controls inside the card and tappable. The checks are Chromium simulations; physical phone touch accuracy, performance, screen-reader behavior, other browser engines, Korean typography review, and beginner comprehension remain untested.
