# Vowel Machine v0.3.1 · design experiment

Open [the playable prototype](index.html). The preserved [v0.2 baseline](index-v0.2.html) retains the earlier Explore-only implementation. [The earlier Vowel Forge](reference-vowel-forge.html) is an unchanged copy of the supplied `reference-vowel-forge.html` (SHA-256 `B4FE121E23352E65C6B906B014D99BCC97155CDB662517B88991193F52EBD821`). This experiment lives outside the Hangul Tutor product tree.

## The wider search

1. **Mirror rail:** A short joint glides through a fixed spine. Crossing the spine changes ㅏ to ㅓ or ㅗ to ㅜ. The player's hand makes the contrast visible in one uninterrupted motion.
2. **Three-key grammar:** ㆍ, ㅡ, and ㅣ are ingredients. The order of two taps yields one of four shapes. It might make structural knowledge more fluent, although a player could memorize sequences without seeing the geometry.
3. **Living syllable row:** Each vowel opens a ㄴ combination in a shared grid. The reward is new readable structure, not a score. A later version could add taught consonant rows and connect known blocks into words.
4. **Word circuit:** Known blocks connect to make a meaningful word, which changes the environment. This is promising for later lessons but would introduce untaught consonants or premature word meanings in a four-vowel prototype, so it was deferred.
5. **Counterfactual shadow:** The opposite vowel appears only as an unlabelled shadow. The learner predicts which part must move before touching it. This could make visual transformation a true puzzle, but the shadow may reveal the answer too early; it needs beginner observation before inclusion.

The small playable version combines the first three. The rail and keys are parallel experiments with separate in-memory discovery records, so a reviewer can switch between them without erasing either route. The row is a common consequence of both methods.

The current design does **not** assume the two input methods complement one another. The rail makes positional contrast unusually clear; the keys may speed recall yet invite sequence memorization. The point of comparing them is to see what beginners construct from sound cues and recognize immediately without either tool.

| Mechanic | Learner does | Learner discovers | Why it may engage | Educational risk |
| --- | --- | --- | --- | --- |
| Mirror rail | Drags the amber joint across the standing line, turns the base, then moves the joint across the lying line. Tap buttons provide the same actions. | Side and above/below placement distinguish ㅏ/ㅓ and ㅗ/ㅜ. | One continuous, reversible gesture produces a real letter change; there is no failure state. | A smooth visual morph could be mistaken for an account of actual handwriting stroke order. The prototype calls it a shape model, not a handwriting lesson. |
| Three-key grammar | Taps two of ㆍ, ㅡ, ㅣ, then reverses order or tries a different base. Invalid pairs are safe experiments. | A tiny set of elements can generate four distinct vowel shapes. | The learner starts predicting output from an internal rule. | Two-tap order can become rote button memorization. It is a prototype rule inspired by Cheonjiin, not a claim about every modern keypad. |
| Living row | Taps lit 나, 너, 노, 누 cells after making vowels. | A vowel affects a whole syllable block when paired with ㄴ. | The map grows because of what the learner built. | Seeing a block is not proof of being able to decode or pronounce it; a later lesson needs independent reading checks. |

## v0.3.1 learning loop

In **Explore**, move ㅏ's short joint left to reveal ㅓ, turn the base to see ㅗ, and move its joint below to reveal ㅜ. The three-key path can be explored in either order. Both paths keep independent discovery and challenge state. In **Prove**, the learner receives the approximate sound cues `eo`, `u`, `a`, and `o`, constructs a vowel, and explicitly checks it. The target glyph, syllable grid, and answer-giving dialogue are hidden until a correct submission. Moving through a target does not solve it. An incomplete key pair is not counted as an error. After two wrong submissions, a clue is offered and subsequent completion is marked assisted. Wrong answers preserve the current challenge and provide feedback about the differing component. The same four-item **Recognize the vowel** multiple-choice check follows either method on a clean, non-manipulable card. The first method uses ㅓ, ㅜ, ㅏ, ㅗ; the second uses ㅗ, ㅏ, ㅜ, ㅓ. Method order and transfer order are recorded in memory.

The in-memory record for each method keeps attempts, first unaided submission success, optional-clue use, and wrong constructions by target. Transfer records also keep attempts and wrong sound choices. Completion without the optional clue can still follow instructive wrong-answer feedback; it is labelled separately from first unaided success. The summary avoids raw tap counts because one rail movement and a two-key sequence are different actions. It is evidence about this immediate session, not a mastery score.

### Educational assumptions and open decisions

- This version assumes the four approximate Latin cues are sufficiently familiar after Explore to assess letter construction. It does not assess pronunciation, which needs human review or audio later.
- Rail Prove uses predeclared starting positions that require, across four cues, a side change, a base turn, or both. Every start is incorrect; always switching sides or always turning fails some targets. The deterministic sequence still permits sequence memorization across repeated plays. A later counterbalanced study could vary starts and sound-cue order while retaining comparable difficulty.
- The four-vowel recognition check uses identical items after each method in a different order, limiting simple answer-order reuse. It is immediate multiple-choice vowel recognition, not independent syllable reading or delayed retention.
- A more playful Prove wrapper could be a **repair task**: the machine's vowel fades from a syllable block and the learner restores it from a sound cue. The same hidden target, Check action, feedback, and evidence record would remain. Keep the present explicit Prove flow as the baseline for comparing that idea.

There are no points, automatic mastery thresholds, audio, network calls, or saved progress. Jeong's small image and separate dialogue respond **after** a gesture completes. The dark workbench remains in place through all phases; the row is temporarily covered during Prove.

## Historical boundary

The [National Hangeul Museum's explanation](https://www.hangeul.go.kr/exhibition/541) describes the three foundational vowel signs ㆍ, ㅡ, and ㅣ as heaven, earth, and human, and the positional combination of ㆍ with ㅡ or ㅣ to form ㅗ, ㅜ, ㅏ, and ㅓ. The sliding rail, the exact two-tap game rule, the glowing row, and Jeong's dialogue are **invented interactions**. The Latin labels are approximate reading cues, not audio or a pronunciation assessment.

## Verification and limits

**Historical v0.3 evidence:** The v0.2 verifier previously passed Chromium checks for both Explore routes. On October 19, v0.3 was exercised in the Codex in-app browser at 390×844 and 320×568. The independent review of the preserved v0.3 ZIP later ran its full verifier through an in-memory bundle in system Chromium and confirmed both sizes, drag, keyboard focus, reduced motion, and package integrity. It also found the rail shortcut and transfer presentation issues fixed in v0.3.1. That passing result applies to v0.3 only.

**Current v0.3.1 evidence:** Local in-app browser checks showed that switching sides alone fails the second rail cue; completing the rail with the needed turns reaches transfer. At 390×844, the four-item transfer and completion screens had no internal scrolling. At 320×568, the transfer choices and footer remained visible with reachable internal scrolling. The transfer DOM contains no rail canvas, guide, joint, or loose dot. `node --check` and Python source compilation passed. The expanded verifier includes adversarial rail strategies, transfer-order/result checks, and both-method paths; it has not run in this session because the local Python Playwright environment is unavailable. Direct `file://` access in the in-app browser remains blocked by its security policy. Physical-phone input, assistive technology, ordinary offline file loading, beginner comprehension, and delayed retention remain untested.
