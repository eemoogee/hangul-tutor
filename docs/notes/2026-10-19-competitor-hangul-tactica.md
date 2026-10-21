# Competitor note — Hangul Tactica (2026-10-19)

**Status:** benchmark notes for the next design cycle. Not a decision; changes no priorities.

## Verified vs. unverified

**Verified** (studio page, hazybyte.studio/hangul-tactica, checked 2026-10-19):
- Campaign with chapters: "Campaign screens introduce chapter material before puzzle play takes over."
- Core puzzle is recognition: "Rotate 2x2 blocks, place your move, and recognize jamo through feedback."
- Pair Rush: "Match Hangul glyphs with Roman counterparts." Also Typing Drill, Flashcards, Library.
- The page does not describe learners assembling syllable blocks from jamo.

**Unverified** (from an AI research summary citing the App Store listing; not checked directly):
- Version 1.3.0 (2026-09-02) redesign: 22-chapter story campaign, eight "Court Tests", palace/village scenes.
- Characters **Sejong and Inji** (apparently Jeong In-ji, the same figure as our Jeong).
- Glyph Slide and Glyph Orbit modes, Study Insights, Review Queue, Proof Boards, final consonant clusters.
- Version 1.3.1 expanded the app to iPad and Mac.

→ Check the App Store listing directly before treating the character/story overlap as fact.

## Where we differ (claims to test, not assume)

- **Platform:** Tactica is Apple-only. Hangul Tutor runs in a phone browser (tested on Android) and has an offline Python version.
- **Core verb:** every turn builds or breaks apart a syllable (game plan §2), rather than matching jamo to Roman labels.
- **Evidence of learning:** independent reading checks and mastery rules, not just practice volume.
- **Candidate tracks** (game plan §8): early real-word reading via loanwords, and real pronunciation rules (연음).
- **Jeong's role:** the historical irony that Jeong In-ji's postface aimed for learning *without a teacher*. The tutor's job is to make himself unnecessary (`hangul-design-ideas.md`).

## Positioning (agreed direction)

A Hangul **construction toy that gradually reveals the history**, not a historical adventure with practice added. This matches `hangul-design-ideas.md`: don't make players sit through history; let them experience the invention. The competitor is a benchmark, not a reason to change priorities. No mini-game arms race; decide on palace art or scenery by learning value, not by whether Tactica has it.

## Competitor play test (about 30 minutes, free opening chapters)

Record what was observed, not what to copy.

1. How quickly does a complete beginner start manipulating Hangul?
2. Does the learner assemble and decode syllables, or mainly match jamo to Romanized labels?
3. How do Sejong and Inji appear and speak, and do they affect gameplay?
4. Does the narrative help learning or interrupt it?
5. What can the learner do independently after 10–15 minutes?
6. **What does it never teach?** For example: block layout rules, sound changes across syllables, reading real words. These gaps are differentiation opportunities.

## Verified Learning Loop — October 19, 2026

**Source:** Hangul Tactica — How It Works (hazybyte.studio/hangul-tactica/how-it-works/, fetched 2026-10-19). The My Planner item is sourced from the product page (hazybyte.studio/hangul-tactica/); the How It Works page does not mention My Planner.

### Confirmed from the developer's description

- **Puzzle-first campaign:** Learners rotate and place 2×2 blocks to align matching symbols.
- **Bidirectional recognition:** Korean-to-Roman and Roman-to-Korean paths follow the same chapter sequence.
- **Multiple review modes:** Flashcards, Typing Drill, and Pair Rush provide different ways to revisit chapter material.
- **Structured review:** The Library provides companion explanations, history and culture, and references.
- **My Planner** (product page, not the How It Works page): My Planner organizes learning into four recurring activities: learn new material through Campaign, practice the same day through Flashcards and Pair Rush, recall yesterday's chapter, and revisit older chapters.
- **Defined scope:** The product emphasizes jamo familiarity as preparation for broader Korean study, rather than promising fluency.

My Planner is a documented feature; its effectiveness as an adaptive learning system has not been established. We should not assume it tracks individual error patterns in the way we are designing Hangul Tutor to do.

### Interpretation for Hangul Tutor

Hangul Tactica appears to place substantial emphasis on recognizing and recalling jamo and their Romanized equivalents.

Hangul Tutor's proposed differentiation is **constructive understanding**: learners directly manipulate jamo, discover positional rules, construct syllables, transform existing blocks, and eventually read unfamiliar words.

This distinction remains a hypothesis until actual gameplay is examined. Hangul Tactica may teach syllable construction more deeply than its public description indicates.

### Design opportunity

Hangul Tactica's structured learning-and-review cycle provides a useful benchmark for our adaptive progression system.

Jeong could help learners understand *why* a particular activity is recommended, using their history of confusions and successes. This gives the character an instructional function beyond narration.

### Competitive benchmark

After approximately 20 minutes, can an absolute beginner independently construct and read a previously unseen Hangul syllable without relying on Romanization?

This could become a common evaluation criterion for both products and for our planned tap/drag/rotate interaction experiment.

### Questions for hands-on evaluation

- Does the campaign require actual syllable construction or primarily symbol matching?
- When and how are learners introduced to vowel placement rules?
- Are unseen syllables tested without Romanization?
- How does the app decide when material needs reviewing?
- Does historical narration support discovery or interrupt play?
- Can the learner transfer knowledge to unfamiliar syllables after a short session?

**Status:** Officially documented features distinguished from provisional competitive analysis. No hands-on observations recorded yet.

## Observations

_(fill in after playing)_
