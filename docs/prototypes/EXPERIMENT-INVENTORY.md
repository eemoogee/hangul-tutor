# Exploding syllable experiment inventory

These are standalone studies, separate from the tutor in `web/`. This inventory records their lineage; each linked README describes its own controls and limits. Browser checks use simulated devices, not a physical phone or learner study.

| Study | Role and lineage | Entry point | Verification |
| --- | --- | --- | --- |
| [Exploding Syllable v1](exploding-syllable-lab/README.md) | Original flat opening and direct-lift interaction baseline for 나, 노, 난. | `exploding-syllable-lab/index.html` | `node exploding-syllable-lab/verify.cjs` |
| [Exploding Syllable v2](exploding-syllable-v2/README.md) | Later typography and reflow study, retaining v1 separately. | `exploding-syllable-v2/index.html` | `exploding-syllable-v2/verify.py` |
| [Jamo relief](exploding-syllable-v2/depth-relief-study/README.md) | Later two-panel 나 depth revision beside v2. | `exploding-syllable-v2/depth-relief-study/index.html` | `exploding-syllable-v2/depth-relief-study/verify.py` |
| [Exploded layers](exploding-syllable-v2/exploded-layers-study/README.md) | Later CSS reference reproduction and Hangul layer study beside v2. | `exploding-syllable-v2/exploded-layers-study/index.html` | `exploding-syllable-v2/exploded-layers-study/verify.py` |
| [Cube to syllable](cube-to-syllable-study/README.md) | Separate cube metaphor based on owner-supplied CSS. | `cube-to-syllable-study/index.html` | `node cube-to-syllable-study/verify.cjs` |
| [Living Syllable Interaction Lab](living-syllable-interaction-lab/README.md) | Later construction and spatial-reveal comparison using v2 endpoint geometry. | `living-syllable-interaction-lab/index.html` | `node living-syllable-interaction-lab/verify.cjs` |
| [Relief-Exploded Syllable Study](relief-exploded-syllable-study/NOTES.md) | Latest three-variant separation/morph/relief comparison, reusing earlier approaches. | `relief-exploded-syllable-study/index.html` | `relief-exploded-syllable-study/verify.py` |

The PNGs in the study folders are intentional review captures. The verifiers may produce additional local output under the ignored `.verify_out/` worktree directory. No prototype loads production lessons, saved learner state, or a backend. The original owner-supplied CSS for the exploded-layers task was unavailable; that study's README distinguishes its public reference reconstruction from the unseen example. The cube study README records what was carried over from its owner-supplied example. The authored SVGs are instructional shapes, not general font outlines or handwriting order.

## Re-run the browser checks

The three `.cjs` verifiers need Node Playwright and Chrome. The four `.py` verifiers need Python Playwright and Chromium. Open any `index.html` directly, or use its local server where provided. The repository does not vendor these verification dependencies. All seven suites passed in local Chromium/Chrome automation on 2026-10-19; see each study's README for the checked behavior and remaining physical-phone requirements.
