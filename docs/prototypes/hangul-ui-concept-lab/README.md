# Hangul Tutor adaptive composition lab

Open `adaptive-composition.html` in a browser. `baseline.html` is an unchanged byte-for-byte copy of the original `C:/Users/jefej/Downloads/hangul-ui-concept-lab.html` (SHA-256 `51BE755B4914F3216D6C26518A565017E7EACEF2D85A83662E7E69FFDC8D733C`). The new experiment links back to it. The three Jeong PNGs in `assets/` are copies of the selected tutor assets.

The experiment is standalone and local. It does not use the Python curriculum controller, persist mastery, or alter a production build.

## Try the same activity in A, B, and C

Switch visual concepts across the top. Switch Discover, Predict, and Recall manually. Each concept keeps its own mode progress while switching. The outer header, workspace, dialogue, and action area retain their positions.

- **Discover:** Place ㅏ to the right of ㄴ for 나, then ㅗ below ㄴ for 노. Tap a vowel and its dotted slot, or drag the vowel to the slot.
- **Predict:** Fill missing vowels and then a missing consonant. Feedback identifies the component that changed.
- **Recall:** Build from “na” and “no” with less guidance, using tiles or a Hangul input. The last screen separately asks for the sound of a Hangul block without displaying the answer first.

Jeong reacts after an answer or placement, while tile selection and dragging remain uninterrupted. The demo keyboard is a layout simulator, not a substitute for real device testing. Back and Review let a reviewer revisit steps; no mastery thresholds are recorded.

## Feel of the three concepts

| Concept | Interaction feel |
| --- | --- |
| A · Illustrated Storybook | Warm, conversational discovery; the shared syllable frame sits in a picture-book scene. |
| B · Living Workbook | Clearest component positions and correction notes; good for deliberate practice. |
| C · Interactive Hangul Stage | Strongest sense of assembling a block; the high-contrast stage emphasizes the result. |

`verify_adaptive.py` checks all concepts and modes at 390×844 and 320×568, including error correction, long text, Back/Review, simulated keyboard reachability, vertical/horizontal vowel positions, and a desktop drag-to-slot path. It starts a temporary localhost HTTP server on an available port and writes screenshots to the repository's ignored `.verify_out/concept-lab/` directory. Run it with a Python environment that has Playwright and Chromium installed. The HTML files also open directly without a server.
