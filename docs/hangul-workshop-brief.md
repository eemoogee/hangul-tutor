# Hangul Workshop — development concept and plan

**Status:** Design brief, 2026-10-17. This proposes an experience and build order; it does not change the current Sejong Test specification or curriculum by itself.

## The idea

The workshop grows out of the [Hangul Key Pad prototype](../archive/Hangul%20Key%20Pad.html). Its first job is to let a learner *see and control* how Hangul pieces become a syllable. Its later job is to help that learner correct, produce, and eventually type Korean without the workshop's scaffolding.

The core progression is **explore → correct → produce → transfer**:

1. **Explore:** freely assemble and change blocks. There is no wrong answer in this mode; every consonant–vowel pairing is a possible written syllable, even if it is not a word on the discovery shelf.
2. **Correct:** repair one meaningful error against a known sound, image, or context. A target makes the edit assessable.
3. **Produce:** hear a known syllable or word and build it without seeing its spelling.
4. **Transfer:** perform a comparable task without hints, and later try a device's Korean keyboard.

The workshop is an instrument for learning, not a replacement for the existing quiz engine or the Sejong Test's independent reading checks. Free exploration gives the learner ownership. Targeted tasks supply evidence of what they can do.

## How it fits the existing game

| Point in the journey | Workshop experience | Main learning claim |
| --- | --- | --- |
| Batch 0: ㄴ ㄷ ㅏ ㅗ | Large learned-letter pad, live block assembly, undo, small 2×2 board, open exploration | “I can make and take apart a block.” |
| Batch 1: ㅁ ㅂ ㅓ ㅜ | Board grows to 4×4; vowel-swap surgery, word discoveries, first authored contrasts and word repairs | “I can change one part and understand the result.” |
| Batch 2 | Add the newly taught letters and appropriate board regions; vary contrasts without exposing unlearned answers | “The same construction rule scales.” |
| Batch 3: ㅇ | Resolve the prototype's vowel-first refusal through a required ㅇ + vowel discovery; then open vowel-initial listening prompts | “I know why 아 begins with a silent written consonant.” |
| Remaining core batches | Broaden the authored repairs and spoken production set as letters are taught | “I can use the system beyond the first examples.” |
| Victory 2 and after | Optional guided move to phone or hardware Korean input; keep the workshop available for practice | “I can carry this skill outside the game.” |
| Later curriculum | Extend the same instrument to compound vowels and final consonants, with new movement and prediction challenges | “New rules extend the system I already know.” |

This preserves the current [Sejong batch order](sejong-test-spec.md): ㅇ remains in Batch 3. Its reveal belongs inside the workshop's main progression, rather than an optional lab left until after the listening mechanic. A small early listen-and-build teaser can use learned consonant–vowel syllables; the **full** mode waits for ㅇ. Moving ㅇ earlier would be an explicit curriculum revision requiring learner testing, not a silent workshop implementation choice.

## The workshop's central surface

The composition area and the possibility board should act as one interface. With Batch 0's two consonants and two vowels, the board begins as 2×2. At Batch 1 it becomes the 4×4 board. Rows represent consonants and columns vowels; a cell represents the resulting syllable. It is a map of reachable changes, not merely a gallery or a scorecard.

Starting at **나**, the learner taps to lift **ㅏ**, taps **ㅗ** to place it, and arrives at **노**. The board's focus moves to the corresponding cell. A neighboring cell can glow as a possible one-piece move, but an assessment must hide that guidance. The word shelf is a second layer: a curated real word lights up when found. It must not imply that every unlisted syllable or sequence is invalid. Use **“Not on this shelf yet; you can still read it”** instead of the prototype's “Not a word.”

For surgery, the visual insight is persistence: **the ㄴ was there the whole time**. Keep the unchanged component as the same visible object during a swap. The outgoing vowel lifts, the incoming vowel travels to its side or bottom position, and the board marker moves in step. Because correct Hangul proportions differ between side and stacked vowels, the consonant may resize around a stable anchor; it must not disappear in a whole-block dissolve. Begin with vowel swaps such as 나 → 노, whose change in placement is obvious. Consonant swaps come later.

Use **tap to lift, tap to place** as the primary interaction. It works for a thumb and does not require precise dragging. Backspace remains predictable and reversible. Dragging could be an optional later affordance, never the only way to play.

## The three main activities

### 1. Open bench and surgery

Free play keeps the prototype's low-pressure qualities: tap anything known, watch a block assemble, undo it, and find words on a hidden shelf. The discovery shelf and occasional invitations (“Make a vowel sit below,” “Reach 노 from 나”) give direction without turning the bench into a quiz. Found words can carry a gloss and a small scene or image; a readable nonword still receives neutral reading feedback.

Surgery adds direct editing of a completed block. The player selects the component to replace and chooses another learned component. The system shows what changed and retains what did not. Longer **word paths** are a later extension of this board traversal, using authored, meaningful endpoints rather than random legal syllables.

Surgery is exploratory evidence, not a mastery test. Without a target, any legal CV result is acceptable. Count a discovery as a discovery; do not treat it as proof that the learner can retrieve a particular spelling or sound.

### 2. Repair

A repair task starts with a known target and one deliberate error. For example, after teaching **바다** with a sea image, show **버다** and ask the player to restore the word. The image supplies the goal, while the earlier encounter supplies its spelling; an unfamiliar picture alone would leave a beginner guessing. Keep initial repairs to one component in a syllable or short word. Sentence repair belongs to a later unit.

Author repairs from the contrast sequence already being taught: introduce ㅏ/ㅓ, let the learner observe the contrast, then ask them to repair a known example, then revisit it later without the cue. Draw errors from controlled minimal pairs and known letters. The repair should name or visually isolate the changed component after an attempt, rather than merely report “wrong.” Meaning-based repair can run without audio; sound-based repair joins the spoken-audio set.

### 3. Listen and build

This expansion is **audio-bearing**. Spoken audio is part of its content and quality scope, separate from the prototype's musical tap and completion effects. Use a small curated set of syllable and word recordings aligned with taught letters. Provide replay and an untimed first attempt. Prompt with sound, then ask the learner to build the written form without a visible romanization answer.

Before Batch 3, prompts may use syllables with known initials. At Batch 3, revisit the pad's earlier “a block can't start with a vowel” refusal. The learner explicitly builds **ㅇ + ㅏ = 아** and discovers that ㅇ is silent in this position. Only then introduce vowel-initial spoken prompts such as 아, 어, 오, and 우 when their vowels are known. Do not auto-insert ㅇ during this first discovery: the learner should perform the new rule.

If spoken audio is unavailable, offer a clearly labeled meaning- or text-based construction activity. Do not score that as equivalent evidence of listening. Speech recognition and microphone input are outside the first workshop expansion.

## Assessment and proof

The current Sejong experience treats the learner's own performance as evidence. The workshop should do the same without turning its sandbox into a monitored test. Keep its two kinds of state distinct:

- **Discovery state:** board cells visited, words found, transformations tried. This supports curiosity and a personal record; it does not grant reading mastery.
- **Assessment state:** authored repair and listen-and-build targets, correctness, hint use, and later independent transfer tasks. These can feed the existing lesson and reading-check rules through the quiz engine rather than a second mastery system.

A workshop post-test can use the same instrument with the training cues removed: give a starting block and a known sound or meaning, ask the learner to make the target, and avoid highlighting the destination. A separate decomposition prompt gives an unfamiliar but legal block and asks which pieces it contains. These show whether the learner understood composition, rather than merely learned to tap a displayed target. Measure correction and production separately; free-play activity and speed are not substitutes for either.

The current Sejong Test's baseline, checkpoints, and Victory milestones remain their own flow. The workshop can supply additional evidence, but a workshop visit should not silently change those pass rules.

## Input and feedback over time

Keep the learned-letter screen pad available throughout. It is especially useful for first encounters with a rule, repair, accessibility, and low-friction phone use. As learners advance, fade hints and offer a device-appropriate route to native Korean input. A learner can opt into their phone keyboard or a hardware keyboard; setup guidance should be optional and tied to the device, since the workshop's left/right visual grouping is not a promise about every phone layout. Native input becomes a meaningful transfer challenge after the learner understands the pieces, not a prerequisite for the first lesson. The workshop remains reachable after that transition.

The feel should be consistent across activities: generous touch targets, clear component colors with non-color cues, a light press response, a distinct block-completion response, and a reversible lift on undo. Spoken audio, effect sounds, and haptics need separate controls. Reduced-motion mode should show equally clear before/after states. Screen readers should be told the current block and selected component; keyboard users must be able to perform lift and place without a pointer.

Jeong introduces a rule or appears at a milestone, then leaves the bench to the player. The prototype's found-word lines can become rare authored payoffs; routine exploration should be answered by the block, board, sound, and concise status text. A quiet workshop feels owned by the learner.

## Technical shape

1. **One deterministic composition model.** Represent the current sequence as components and edit actions, not as text scraped from the display. It must support tap, lift, place, undo, incomplete blocks, and later ㅇ, compound vowels, and final consonants. The browser view renders the model; animations do not decide the result.
2. **Stable component identity for motion.** Keep element identity across surgery edits so unchanged pieces do not blink or get recreated. Test both the logical result and the visible transition. Honor reduced motion.
3. **One grading authority.** The workshop UI can detect curated shelf discoveries, but assessed answers should go through the existing Python quiz/flow rules. Keep the browser's input and animation layer separate from correctness and mastery decisions, as the [Sejong event contract](sejong-events.md) requires.
4. **One answer format across inputs.** The pad emits component edits; a native keyboard supplies composed Korean text. Convert both to the same normalized answer for the grader. With native IME input, wait until composition is committed before checking the answer; do not grade an in-progress character.
5. **Curated content.** Store authored word paths, contrast/repair pairs, meanings or images, spoken clips, and provenance together. Mark which letters and rules each item needs so no prompt relies on material not yet taught. A finite discovery shelf is not a dictionary.
6. **Resumable, bounded state.** Persist unlocks, discoveries, and unfinished tasks with the rest of learner progress. Keep sound/haptic preferences separate from mastery. Avoid a completion demand to fill every board cell.

## Build order and checks

**Slice A — workshop foundation.** Integrate the Batch 0/1 pad, 2×2-to-4×4 board, open bench, curated shelf, and tap-based vowel surgery. Verify that an unchanged component persists through a swap, the board follows the actual syllable, backspace reverses one action, and unlisted results are described neutrally. A short beginner observation should test whether the next tap is predictable.

**Slice B — assessable correction.** Add one authored contrast sequence and a few one-change repairs with a taught target and visible ground truth. Verify that a learner can explain what they changed, and that a missed repair returns later rather than turning the workshop into a punishment loop.

**Slice C — ㅇ and spoken production.** Make the Batch 3 ㅇ reveal a playable workshop moment. Add the curated recordings and listen-and-build for taught forms, with replay, accessible fallback, and no romanization answer on the production screen. Check the recordings with Korean speakers and verify that a learner understands why 아 needs ㅇ in writing.

**Slice D — transfer.** Add uncued edit/decomposition post-test tasks, then an optional native-input path and device-specific setup help. Compare performance on the pad and native input to detect dependence on the scaffold. Keep the workshop as a practice choice.

**Later extensions.** Compound vowels turn a former “second vowel refused” moment into a new legal composition. Final consonants add a bottom position and later a rearrangement prediction challenge. Preserve the same edit/undo model; do not bolt on separate composers for each rule. Longer word paths and sentence-level repair wait until word-level behavior is clear in beginner tests.

## Questions to settle during prototyping

- Does the 4×4 board help learners *predict* a swap, or do they use it only as a word checklist? Test both with and without reachable-neighbor highlights.
- Can a persistent consonant stay visually legible while changing proportions between side and stacked vowel layouts? Prototype this motion before committing to a graphic style.
- Which first repair pair gives a novice enough prior knowledge to edit confidently? Test the target image and teaching sequence together.
- How many distinct spoken forms are needed for meaningful listen-and-build without making audio production the dominant cost? Decide from the authored prompt set, then record and check that set.
- At what point does optional native input become inviting rather than an interruption? Use actual phone and desktop playtests, not only completion time.

The success condition is a learner who can explore without fear, repair a known word for a reason, construct a heard form, and carry the skill beyond the workshop. The board, animation, and sound serve those behaviors; they are not completion goals on their own.
