# Jamo Interaction Lab

An isolated Hangul Tutor prototype comparing three ways to place the **same two consonants** (ㄴ, ㄷ) and **same four vowel shapes** (ㅗ, ㅏ, ㅜ, ㅓ) in one syllable workspace. All four shapes remain listed in every condition; Rotate cycles one active vowel piece through them. It does not load Pyodide, the curriculum, Sejong, or production storage. It does not write browser storage or send a log to a server.

## Open it

From this prototype folder, run:

```powershell
node serve.mjs
```

The server prints a desktop URL and any LAN URLs it detects. Open the desktop URL on this computer.

Open one of the printed LAN URLs on a phone on the **same Wi-Fi**. If a system firewall asks, allow Node on the private network. Do not change router settings. No public deployment is needed. The page may also work from a local `file://` URL in browsers that allow local ES modules, but serving it over HTTP is more reliable.

Run the model checks from this directory with `node verify.mjs`.

## Participant path

1. Choose **Tap**, **Drag**, or **Rotate**. All modes use the same block positions, two consonants, four vowel shapes, four targets, feedback, and transfer item.
2. Explore freely. In Drag mode, drag a piece onto a block position. Tap selection followed by a position remains available for touch, keyboard, and motor accessibility; the action log identifies that fallback. In Rotate mode, turn the vowel through ㅗ → ㅏ → ㅜ → ㅓ, then choose **side** or **below** explicitly. Rotation never auto-places it.
3. Start the four targeted sound builds: **na, no, neo, nu**. The English labels are approximate sound cues. Sound-map labels are visible during practice; no audio is required.
4. Complete the **identical untutored transfer** in every condition: build **do** with ㄷ and ㅗ. The sound map disappears, there is one submission, and no correctness or positioning hint is given before that submission.
5. Add qualitative observations in the collapsible panel and download the JSON log before closing the tab. Logs are in memory only. The JSON records completion, placement errors, rotations, corrections, transfer first attempt, action method, and notes. Explore actions are logged but unscored.

For a comparison pilot, assign mode order across participants to reduce order effects. Observe whether they understand side/below placement, whether rotating helps or hinders, and whether drag snapping is discoverable. Record workarounds, verbal explanations, and accessibility alternatives. Speed and completion alone do not establish learning benefit.

## Design decisions and limits

- This is a comparative **interaction instrument**, not a new lesson or grading authority. Its local checks only decide whether a visible build matches an authored target. Do not merge those checks into production mastery or reading checks.
- The four vowel orientations can be pictured as physical rotations for this experiment. That is an invented mnemonic, **not** the documented historical derivation of Hangul vowels. The interface says so explicitly.
- The unchanged consonant is one persistent DOM element while vowels are replaced. The formed-block readout uses Unicode syllable composition only when the vowel occupies its standard side or lower position.
- The last task transfers a practiced vowel to a different consonant. It is a narrow transfer probe, not an independent reading or spoken-sound test; the text cue and visible inventory may support guessing.
- Drag has an accessible tap fallback. Use action-method logs when analyzing mode B; a participant who uses the fallback did not experience the drag condition as intended.
- No audio, Korean speaker review, phone hardware test, calibrated learning measure, or production integration is included. The sound labels are prototype approximations.
- At short viewports or enlarged text, natural scrolling is allowed to keep text and controls reachable. Nothing is clipped to force a one-screen layout.

Relevant design references: [Hangul Workshop brief](../../hangul-workshop-brief.md) (explore/correct/produce/transfer, stable component identity, input alternatives, and the distinction between discovery and assessment) and the [game plan](../../hangul_game_plan.md). The currently edited §8 proposals were read from the original checkout before creating this isolated branch; that separate uncommitted document change is not part of this prototype. Its evidence distinction is followed here: the physical rotation mnemonic is an invented interaction, not a historical account.
