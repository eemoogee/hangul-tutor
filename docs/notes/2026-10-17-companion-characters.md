# Companion characters: Jeong and Sejong (2026-10-17)

## Direction
- A comic duo. Jeong draws the learner into the experiment; Sejong is quietly
  pleased when the learner works out how it works. Imagined character designs,
  not historical likenesses.
- Four styles explored: ink & paper, storybook, game portraits, woodblock.
  Leaning: game-portrait clarity with woodblock texture.

## Decision: wait on final art and image integration
Final art waits until the game design is more concrete, because the design
decides how many poses are needed and where characters appear.

Cheap things to do meanwhile:
- Reserve a fixed-size character slot in web layouts so real art drops in
  without breaking them.
- Name poses by meaning (`hello`, `curious`, `delighted`), never by appearance,
  so art can be swapped by replacing files.
- Keep a list of moments where a character reacts (learner predicts, learner
  gets it wrong, discovery). That list becomes the art brief.

## Prototype reviewed (not in repo)
`hangul_mascot_fullscreen-6.html`: one 3-step lesson (나, 노, 마) with Jeong in
three embedded poses. Issues to fix if it is reused:
- Step 3 button labels ("ㅁ + ㅏ") match the question, so the answer can be
  found without reading Hangul (cross-question spoiler).
- Scrolling is disabled, so on short or sideways screens the Next button can
  end up out of reach.
- Steps are hard-coded instead of read from lesson data.
- No Sejong; the avatar next to Jeong's dialogue is a placeholder.
- Images are embedded as text in the HTML; use separate files once there is
  more than one lesson.
