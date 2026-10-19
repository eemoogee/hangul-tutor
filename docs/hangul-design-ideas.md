# Hangul Tutor — High-Level Design Ideas: What Hangul Should Say to the Player

> Purpose: a design-ideas document. It is about the *points the game should make* about Hangul,
> not about implementation. Nothing here is a spec; it is a set of ideas to draw from.

## The Strongest Takeaway

Not simply that Hangul is ingenious or easy to learn — but that **Hangul was deliberately invented
to make something difficult accessible to ordinary people, and its design reflects that purpose.**

This is particularly relevant to Hangul Tutor. The learner isn't just memorizing an unfamiliar
alphabet. They're discovering a system that was designed, nearly six centuries ago, *to be learned*.

Seven core ideas can be extracted from the story, each with a different role in the game. Some
provide emotional motivation, some explain the mechanics, and others supply historical context or
opportunities for humor.

---

## Seven Ideas Worth Preserving

### 1. Hangul was created for people who couldn't write their own language.
**Highest priority**

*Historical basis:* Sejong's own preface to the Hunminjeongeum explains that Korean differed from
Chinese and that people often struggled to express what they wished to say in writing. He describes
creating 28 letters for convenient everyday use.

This is perhaps the most important claim in the entire story. It is not just a statement about
literacy. It's a statement about **who writing is for**.

*Meaning for the game:* The player should understand immediately why Sejong's invention mattered.
There was a mismatch between the language people spoke and the writing available to them. Sejong
wanted to address it.

*Possible introductory line:*
> "For centuries, Koreans spoke their own language. Writing it was another matter. King Sejong
> decided to change that."

This introduces the problem, the protagonist, and the invention without requiring a history lesson.

### 2. Hangul was designed as a system, not a collection of arbitrary symbols.
**Highest priority**

*Historical basis:* The original explanatory text describes the design principles behind the
letters, including how basic consonants reflect speech organs and how related forms are derived.

This has direct consequences for teaching. The learner should **experience** Hangul's internal logic
rather than simply be told that it's logical.

ㄱ ㅋ ㄲ — related sounds, related letter shapes. (ㄲ is a modern doubled consonant rather than one of
the original basic shapes.)

*Meaning for the game:* When learners encounter a new consonant, visual animation can reveal what it
shares with a familiar one. The relationship itself becomes the lesson. This fits the interest in
animated Hangul forms that are both decorative and educational.

### 3. A small number of letters can unlock an astonishing number of syllables.
**Highest priority**

This is the strongest connection to the existing Sejong Test.

Hangul is alphabetic, but its letters are assembled into syllable blocks. Learners can therefore
produce many readable combinations from relatively few components.

Four letters, four syllables:
- ㄴ + ㅏ = 나
- ㄴ + ㅗ = 노
- ㄷ + ㅏ = 다
- ㄷ + ㅗ = 도

*Meaning for the game:* The existing principle of **composition as revelation** can now carry
historical significance. The player is experiencing the power of the invention, not just completing
an exercise.

Sejong might say:
> "Four letters. Four syllables. You see? The letters were designed to work together."

The moment of discovery should be the reward. The historical explanation can come afterward.

### 4. The letters embody an understanding of human speech.

*Historical basis:* Five original basic consonants were described using the shapes or positions of
the mouth, tongue, teeth, and throat. The vowels used a different framework, drawing on heaven,
earth, and humanity.

- ㄴ — tongue position
- ㅁ — mouth shape
- ㅏ — vowel structure

*Meaning for the game:* This provides an excellent foundation for occasional visual revelations.
For example, Jeong could explain why ㄴ has its shape, while Sejong introduces the principles behind
the writing system.

Do **not** teach all this at once. Reveal design principles when the learner encounters the relevant
letters.

There's also a useful distinction to preserve: Hangul's consonants and vowels were designed according
to *different* principles. We shouldn't present every letter as a diagram of the mouth.

### 5. The invention was controversial.

*Historical basis:* In 1444, Choe Man-ri and other scholars formally petitioned against the new
writing system. Their documented objections included concerns about established intellectual and
cultural relationships with China, the status of Chinese writing, and the consequences of
introducing a separate script.

This adds something that a purely celebratory account of Hangul lacks: **conflict**. It's remarkable
that an invention now regarded with such pride was initially opposed by influential scholars.

*Meaning for the game:* This could become a later historical interlude or a source of gentle humor.

Jeong might say:
> "The king invented an alphabet for ordinary people. Some very educated people objected."

This is a better narrative hook than reducing all opposition to scholars wanting peasants to remain
illiterate. The actual debate was more complicated, which makes it more interesting.

### 6. Hangul's accessibility was an explicit design ambition.

Jeong In-ji's 1446 postface famously praises how quickly the letters could be learned. This is
historical testimony to their intended simplicity — **not** proof that everyone can master Korean
reading in a morning.

*Meaning for the game:* This gives a compelling connection between the historical ambition and the
modern learner's experience.

Possible line:
> "The king wanted ordinary people to learn his letters without years of study. Nearly six hundred
> years later, you're about to test his idea."

This is especially useful in the very first session. It makes the player part of the story without
promising unrealistic results.

### 7. Hangul survived because people continued using it.

The longer story of Hangul includes its use by different social groups, its coexistence with Chinese
characters, later language reform, and its growing importance as a symbol of Korean identity.

*Meaning for the game:* This is better suited to later chapters than the opening lesson. It gives the
curriculum a sense of historical progression: invention, adoption, resistance, survival, and modern
everyday use.

There is also a natural payoff when the learner begins reading real Korean words and eventually
encounters the names 정 and 세종. The alphabet that once needed an explanation is now the alphabet
surrounding Korean speakers in daily life.

---

## How to Integrate These Ideas

Do **not** make players sit through a historical introduction. Instead, use the history to give
meaning to the learning moments that already exist.

- **Opening encounter with Sejong** → People needed a practical way to write Korean → Establish why
  Hangul was invented.
- **First four letters** → Simplicity and accessibility → Establish learner confidence.
- **First syllable combinations** → A small set of letters can produce many syllables → Create the
  revelation.
- **Letter-family exercises** → Related shapes encode related sounds → Reveal the underlying design.
- **Jeong's commentary** → Scholars explained and promoted the invention → Give the historical setting
  personality.
- **Later historical interlude** → Some officials opposed the alphabet → Introduce conflict and
  stakes.
- **Reading real words** → Hangul became a living everyday script → Connect the invention to modern
  Korea.

---

## An Important Distinction: History Versus Invented Story

A historical tag is particularly useful here. The supplied narrative makes several statements that
are more dramatic than the evidence warrants. Distinguish three kinds of material:

**Documented history**
Sejong created the alphabet in 1443. It was published with explanations in 1446. Jeong In-ji wrote
its postface. Choe Man-ri submitted a petition opposing the invention in 1444. These are supported by
surviving documents.

**Historical interpretation**
The alphabet challenged established barriers to literacy. Its introduction had social implications.
However, the claim that opposition was *primarily* motivated by a desire to keep commoners illiterate
oversimplifies the documented controversy. Historians continue to examine its political and cultural
context.

**Fictional storytelling**
Sejong and Jeong speaking directly to the learner, arguing about teaching techniques, or joking about
court scholars. These can make excellent game material, **provided the player understands that the
dialogue is imagined.**

### One Specific Correction That Matters

The description of Sejong **assembling the Hall of Worthies to invent the script together is not an
established historical fact.** Contemporary records explicitly credit Sejong with its creation, and
scholars including Jeong In-ji prepared its explanations. The precise division of creative work is
debated.

That actually leaves considerable room for the fictional Jeong character, without needing to assign
him historically undocumented activities.

---

## The Core Message

Of the seven ideas, elevate three to the level of enduring design principles:

- **Purpose** — Hangul was invented to make written expression more accessible.
- **Ingenuity** — The letters were carefully designed around sounds and systematic relationships.
- **Discovery** — The learner can experience that ingenuity firsthand by putting letters together and
  reading something meaningful.

Together, these suggest a narrative progression:

> A problem worth solving → an ingenious invention → an invention you can use yourself.

For the Sejong opening, lean toward something like:

> "Nearly six hundred years ago, King Sejong faced a problem. His people spoke Korean, but writing it
> was difficult. So he created a new alphabet — one designed to be learned. Its name today is Hangul."

Then let the player experience the invention.

---

## The Jeong Irony

There is one particularly good historical detail worth considering for Jeong's character. The real
Jeong In-ji's postface says that the explanatory materials were prepared so a reader could learn the
letters **without a teacher**.

For a beginner learning game featuring a fictional teacher named Jeong, that's an almost perfect
piece of historical irony: **the teacher's ultimate job is to make himself unnecessary.**

That captures something essential about both Hangul's original purpose and what Hangul Tutor should
aspire to accomplish: give people the tools to read for themselves.
