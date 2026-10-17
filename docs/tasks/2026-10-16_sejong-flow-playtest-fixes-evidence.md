# Sejong playtest fixes — verification evidence

Worktree: `sejong-playtest-fixes`, based on master `8ea4290`.

## scripts\_verify_decompose_syllable.py (exit 0)

```text
============================================================================
(a) PROMPT / LEAK — prompt shows the block, never its jamo
============================================================================
   block=노  cho=ㄴ jung=ㅗ jong=''
      prompt='Break **노** into its parts.\nWhich consonant + vowel make this block?'
      answer='ㄴ + ㅗ'  leaked=[]
   [PASS] prompt for 노 does not leak ㄴ/ㅗ  — leaked=[]
   block=도  cho=ㄷ jung=ㅗ jong=''
      prompt='Break **도** into its parts.\nWhich consonant + vowel make this block?'
      answer='ㄷ + ㅗ'  leaked=[]
   [PASS] prompt for 도 does not leak ㄷ/ㅗ  — leaked=[]
   block=다  cho=ㄷ jung=ㅏ jong=''
      prompt='Break **다** into its parts.\nWhich consonant + vowel make this block?'
      answer='ㄷ + ㅏ'  leaked=[]
   [PASS] prompt for 다 does not leak ㄷ/ㅏ  — leaked=[]
   block=노  cho=ㄴ jung=ㅗ jong=''
      prompt='Break **노** into its parts.\nWhich consonant + vowel make this block?'
      answer='ㄴ + ㅗ'  leaked=[]
   [PASS] prompt for 노 does not leak ㄴ/ㅗ  — leaked=[]
   [PASS] prompt for 노 does not leak ㄴ/ㅗ  — leaked=[]
   [PASS] prompt for 호 does not leak ㅎ/ㅗ  — leaked=[]
   [PASS] prompt for 도 does not leak ㄷ/ㅗ  — leaked=[]
   [PASS] prompt for 다 does not leak ㄷ/ㅏ  — leaked=[]
   [PASS] prompt for 나 does not leak ㄴ/ㅏ  — leaked=[]
   [PASS] prompt for 노 does not leak ㄴ/ㅗ  — leaked=[]
   [PASS] prompt for 도 does not leak ㄷ/ㅗ  — leaked=[]
   [PASS] prompt for 하 does not leak ㅎ/ㅏ  — leaked=[]
   [PASS] prompt for 고 does not leak ㄱ/ㅗ  — leaked=[]
   [PASS] prompt for 사 does not leak ㅅ/ㅏ  — leaked=[]
   [PASS] prompt for 마 does not leak ㅁ/ㅏ  — leaked=[]
   [PASS] prompt for 도 does not leak ㄷ/ㅗ  — leaked=[]
   [PASS] prompt for 노 does not leak ㄴ/ㅗ  — leaked=[]
   [PASS] prompt for 호 does not leak ㅎ/ㅗ  — leaked=[]
   [PASS] prompt for 마 does not leak ㅁ/ㅏ  — leaked=[]
   [PASS] prompt for 고 does not leak ㄱ/ㅗ  — leaked=[]
   [PASS] prompt for 마 does not leak ㅁ/ㅏ  — leaked=[]
   [PASS] prompt for 마 does not leak ㅁ/ㅏ  — leaked=[]
   [PASS] prompt for 소 does not leak ㅅ/ㅗ  — leaked=[]
   [PASS] prompt for 사 does not leak ㅅ/ㅏ  — leaked=[]
   [PASS] prompt for 고 does not leak ㄱ/ㅗ  — leaked=[]
   (25 decompose_syllable questions sampled in lesson 5)
   [PASS] at least one decompose_syllable question was served

============================================================================
(b) CHOICES — well-formed, 4 options, correct present exactly once
============================================================================
   [PASS] choices for 고: 4 options  — ['ㄷ + ㅏ', 'ㄱ + ㅗ', 'ㅅ + ㅗ', 'ㅎ + ㅏ']
   [PASS] choices for 고: correct present once
   [PASS] choices for 고: no dupes
   [PASS] choices for 고: all 'X + Y' shaped  — bad=[]
      고 -> ㄱ + ㅗ   options=['ㄷ + ㅏ', 'ㄱ + ㅗ', 'ㅅ + ㅗ', 'ㅎ + ㅏ']
   [PASS] choices for 마: 4 options  — ['ㅁ + ㅗ', 'ㄷ + ㅗ', 'ㅁ + ㅏ', 'ㄴ + ㅏ']
   [PASS] choices for 마: correct present once
   [PASS] choices for 마: no dupes
   [PASS] choices for 마: all 'X + Y' shaped  — bad=[]
      마 -> ㅁ + ㅏ   options=['ㅁ + ㅗ', 'ㄷ + ㅗ', 'ㅁ + ㅏ', 'ㄴ + ㅏ']
   [PASS] choices for 사: 4 options  — ['ㅎ + ㅗ', 'ㄴ + ㅗ', 'ㅅ + ㅏ', 'ㄴ + ㅏ']
   [PASS] choices for 사: correct present once
   [PASS] choices for 사: no dupes
   [PASS] choices for 사: all 'X + Y' shaped  — bad=[]
      사 -> ㅅ + ㅏ   options=['ㅎ + ㅗ', 'ㄴ + ㅗ', 'ㅅ + ㅏ', 'ㄴ + ㅏ']
   [PASS] choices for 가: 4 options  — ['ㅁ + ㅏ', 'ㄱ + ㅏ', 'ㄴ + ㅏ', 'ㄴ + ㅗ']
   [PASS] choices for 가: correct present once
   [PASS] choices for 가: no dupes
   [PASS] choices for 가: all 'X + Y' shaped  — bad=[]
      가 -> ㄱ + ㅏ   options=['ㅁ + ㅏ', 'ㄱ + ㅏ', 'ㄴ + ㅏ', 'ㄴ + ㅗ']
   [PASS] choices for 호: 4 options  — ['ㄴ + ㅏ', 'ㅎ + ㅏ', 'ㅅ + ㅏ', 'ㅎ + ㅗ']
   [PASS] choices for 호: correct present once
   [PASS] choices for 호: no dupes
   [PASS] choices for 호: all 'X + Y' shaped  — bad=[]
      호 -> ㅎ + ㅗ   options=['ㄴ + ㅏ', 'ㅎ + ㅏ', 'ㅅ + ㅏ', 'ㅎ + ㅗ']
   [PASS] choices for 하: 4 options  — ['ㄱ + ㅗ', 'ㄴ + ㅗ', 'ㄷ + ㅏ', 'ㅎ + ㅏ']
   [PASS] choices for 하: correct present once
   [PASS] choices for 하: no dupes
   [PASS] choices for 하: all 'X + Y' shaped  — bad=[]
      하 -> ㅎ + ㅏ   options=['ㄱ + ㅗ', 'ㄴ + ㅗ', 'ㄷ + ㅏ', 'ㅎ + ㅏ']
   [PASS] choices for 노: 4 options  — ['ㅎ + ㅗ', 'ㄴ + ㅗ', 'ㅁ + ㅗ', 'ㄴ + ㅏ']
   [PASS] choices for 노: correct present once
   [PASS] choices for 노: no dupes
   [PASS] choices for 노: all 'X + Y' shaped  — bad=[]
      노 -> ㄴ + ㅗ   options=['ㅎ + ㅗ', 'ㄴ + ㅗ', 'ㅁ + ㅗ', 'ㄴ + ㅏ']
   [PASS] choices for 호: 4 options  — ['ㅁ + ㅏ', 'ㄴ + ㅗ', 'ㅎ + ㅗ', 'ㅅ + ㅏ']
   [PASS] choices for 호: correct present once
   [PASS] choices for 호: no dupes
   [PASS] choices for 호: all 'X + Y' shaped  — bad=[]
      호 -> ㅎ + ㅗ   options=['ㅁ + ㅏ', 'ㄴ + ㅗ', 'ㅎ + ㅗ', 'ㅅ + ㅏ']
   [PASS] choices for 가: 4 options  — ['ㅎ + ㅗ', 'ㅁ + ㅗ', 'ㄱ + ㅗ', 'ㄱ + ㅏ']
   [PASS] choices for 가: correct present once
   [PASS] choices for 가: no dupes
   [PASS] choices for 가: all 'X + Y' shaped  — bad=[]
      가 -> ㄱ + ㅏ   options=['ㅎ + ㅗ', 'ㅁ + ㅗ', 'ㄱ + ㅗ', 'ㄱ + ㅏ']
   [PASS] choices for 호: 4 options  — ['ㅎ + ㅗ', 'ㄷ + ㅗ', 'ㅁ + ㅗ', 'ㄱ + ㅗ']
   [PASS] choices for 호: correct present once
   [PASS] choices for 호: no dupes
   [PASS] choices for 호: all 'X + Y' shaped  — bad=[]
      호 -> ㅎ + ㅗ   options=['ㅎ + ㅗ', 'ㄷ + ㅗ', 'ㅁ + ㅗ', 'ㄱ + ㅗ']
   [PASS] choices for 사: 4 options  — ['ㄴ + ㅗ', 'ㅅ + ㅏ', 'ㄴ + ㅏ', 'ㅅ + ㅗ']
   [PASS] choices for 사: correct present once
   [PASS] choices for 사: no dupes
   [PASS] choices for 사: all 'X + Y' shaped  — bad=[]
      사 -> ㅅ + ㅏ   options=['ㄴ + ㅗ', 'ㅅ + ㅏ', 'ㄴ + ㅏ', 'ㅅ + ㅗ']
   [PASS] choices for 호: 4 options  — ['ㄱ + ㅗ', 'ㅅ + ㅏ', 'ㅎ + ㅗ', 'ㄴ + ㅏ']
   [PASS] choices for 호: correct present once
   [PASS] choices for 호: no dupes
   [PASS] choices for 호: all 'X + Y' shaped  — bad=[]
      호 -> ㅎ + ㅗ   options=['ㄱ + ㅗ', 'ㅅ + ㅏ', 'ㅎ + ㅗ', 'ㄴ + ㅏ']
   [PASS] choices for 마: 4 options  — ['ㄱ + ㅗ', 'ㅁ + ㅏ', 'ㄴ + ㅏ', 'ㄴ + ㅗ']
   [PASS] choices for 마: correct present once
   [PASS] choices for 마: no dupes
   [PASS] choices for 마: all 'X + Y' shaped  — bad=[]
      마 -> ㅁ + ㅏ   options=['ㄱ + ㅗ', 'ㅁ + ㅏ', 'ㄴ + ㅏ', 'ㄴ + ㅗ']
   [PASS] choices for 나: 4 options  — ['ㄱ + ㅗ', 'ㅎ + ㅏ', 'ㅅ + ㅗ', 'ㄴ + ㅏ']
   [PASS] choices for 나: correct present once
   [PASS] choices for 나: no dupes
   [PASS] choices for 나: all 'X + Y' shaped  — bad=[]
      나 -> ㄴ + ㅏ   options=['ㄱ + ㅗ', 'ㅎ + ㅏ', 'ㅅ + ㅗ', 'ㄴ + ㅏ']
   [PASS] choices for 가: 4 options  — ['ㄱ + ㅏ', 'ㅅ + ㅏ', 'ㅎ + ㅏ', 'ㄴ + ㅗ']
   [PASS] choices for 가: correct present once
   [PASS] choices for 가: no dupes
   [PASS] choices for 가: all 'X + Y' shaped  — bad=[]
      가 -> ㄱ + ㅏ   options=['ㄱ + ㅏ', 'ㅅ + ㅏ', 'ㅎ + ㅏ', 'ㄴ + ㅗ']

============================================================================
(c) GRADING — normalization accepted, order enforced
============================================================================
   block=모  expected='ㅁ + ㅗ'
   [PASS] answer('ㅁ + ㅗ') -> exact  — got True, feedback='✅ Correct! **모** = **ㅁ + ㅗ**.'
   [PASS] answer('ㅁ+ㅗ') -> no spaces  — got True, feedback='✅ Yes! **모** = **ㅁ + ㅗ**.'
   [PASS] answer('ㅁ,ㅗ') -> comma  — got True, feedback='✅ Nice! **모** = **ㅁ + ㅗ**.'
   [PASS] answer('ㅁㅗ') -> concatenated  — got True, feedback='✅ Nice! **모** = **ㅁ + ㅗ**.'
   [PASS] answer('  ㅁ  ㅗ  ') -> extra whitespace  — got True, feedback='✅ Spot on! **모** = **ㅁ + ㅗ**.'
   [PASS] answer('ㅗ + ㅁ') -> REVERSED order (must fail)  — got False, feedback="❌ Not quite — **모** = **ㅁ + ㅗ** (consonant first; you typed 'ㅗ + ㅁ')."
   [PASS] answer('ㅁ') -> consonant only  — got False, feedback="❌ Not quite — **모** = **ㅁ + ㅗ** (consonant first; you typed 'ㅁ')."
   [PASS] answer('ㅗ') -> vowel only  — got False, feedback="❌ Not quite — **모** = **ㅁ + ㅗ** (consonant first; you typed 'ㅗ')."
   [PASS] answer('') -> empty  — got False, feedback="❌ Not quite — **모** = **ㅁ + ㅗ** (consonant first; you typed '')."

============================================================================
(d) GATING — batchim lessons must fall back to spell
============================================================================
   [PASS] lesson 10 (Bottom Consonants (Batchim)) all spell  — modes=['spell']
   [PASS] lesson 11 (More Batchim) all spell  — modes=['spell']

============================================================================
(e) SWEEP — every lesson x 20 calls: no batchim, no bare jamo target
============================================================================
   lesson  2: 15 pool items checked
   lesson  3: 9 pool items checked
   lesson  4: 12 pool items checked
   lesson  5: 12 pool items checked
   lesson  6: 8 pool items checked
   lesson  7: 14 pool items checked
   lesson  8: 15 pool items checked
   lesson  9: 10 pool items checked
   lesson 10: 14 pool items checked
   lesson 11: 8 pool items checked
   lesson 12: 19 pool items checked

   decompose_syllable questions served across sweep: 180
   invalid targets that reached the mode: 0
   [PASS] zero batchim/bare-jamo targets reached decompose_syllable

============================================================================
(f) FALLBACK — pool-less lesson degrades to spell
============================================================================
   [PASS] no-pool lesson -> spell  — mode=spell

============================================================================
RESULT: ALL PASS
============================================================================
```

## scripts\_verify_engine_web.py (exit 0)

```text
PASS persist=False leaves files untouched and counts 20 answers
PASS 30-answer JSON round trip
PASS schema 1 migrates to schema 3
PASS bad JSON and non-object are rejected
PASS newer schema remains read-only and unchanged
PASS Batch 0: 200 correct answers | build_syllable=17, match_sound=24, missing_vowel=16, nonword_decode=29, read_aloud=74, sequence_decode=21, spell=19
PASS Batch 1: 200 correct answers | build_syllable=16, match_sound=20, missing_vowel=21, nonword_decode=34, read_aloud=65, sequence_decode=24, spell=20
PASS both custom reading checks have five distinct taught targets
PASS custom lesson cannot complete curriculum lesson 0
PASS a failed import keeps progress and read-only state
PASS malformed old progress raises ValueError
ALL PASS: 11 checks
```

## scripts\_verify_gameplay_fixes.py (exit 0)

```text
Progress saving
  [PASS] v1 progress migrates scores, totals and old mix-up pairs
  [PASS] v1 migration saves the current schema version
  [PASS] current progress loads unchanged
  [PASS] save then load round trip is identical
  [PASS] failing migration keeps an exact backup and says so
  [PASS] failing temp migration backs up temp and saves the usable main
  [PASS] future temp leaves lesson 7 visible and both files unchanged after play
  [PASS] even an older future temp is protected from the next save
  [PASS] future main is never loaded, backed up or overwritten after play
  [PASS] older usable temp recovers progress when main is damaged
  [PASS] totals counted once across repeated saves
  [PASS] best streak survives a later miss
  [PASS] corrupt progress file -> fresh start + backup kept
  [PASS] locked progress: retry then save succeeds
  [PASS] locked progress: give up once, warn, and keep the complete temp file
  [PASS] locked progress: repeated autosave does not repeat the warning
  [PASS] locked progress: next start recovers newer temp, then saves it
  [PASS] older temp file cannot replace newer saved progress
  [PASS] corrupt newer temp keeps the last valid saved progress
Grading
  [PASS] lesson 1: every mode accepts its own answer
  [PASS] lesson 2: every mode accepts its own answer
  [PASS] lesson 3: every mode accepts its own answer
  [PASS] lesson 4: every mode accepts its own answer
  [PASS] lesson 5: every mode accepts its own answer
  [PASS] lesson 6: every mode accepts its own answer
  [PASS] lesson 7: every mode accepts its own answer
  [PASS] lesson 8: every mode accepts its own answer
  [PASS] lesson 9: every mode accepts its own answer
  [PASS] lesson 10: every mode accepts its own answer
  [PASS] lesson 11: every mode accepts its own answer
  [PASS] lesson 12: every mode accepts its own answer
  [PASS] spell: copying the shown romanization is re-prompted, not graded
  [PASS] spell: an A-D letter is still a valid answer
  [PASS] read_aloud: 'la' accepted for 라
  [PASS] read_aloud: 'shi' accepted for 시
  [PASS] bare ㄹ accepts 'r' and 'l'
  [PASS] read_aloud: 'ee' accepted for 이
  [PASS] 'ee' accepted in any ㅣ block (기, 미, 인, bare ㅣ)
  [PASS] 'ee' combines with 'sh' and 'l' (시 -> shee/see, 리 -> lee/ree)
  [PASS] 'ee' works inside longer readings (아이 -> aee, 김치 -> geemchee)
  [PASS] 'ee' is not accepted where there is no ㅣ (어, 의, 애)
  [PASS] missing_vowel: 오 accepted for ㅗ
  [PASS] missing_vowel (lesson 2): only taught vowels offered
Batchim questions are answerable
  [PASS] lesson 10: exactly one defensible answer per question
  [PASS] lesson 10: both question forms appear
  [PASS] lesson 11: exactly one defensible answer per question
  [PASS] lesson 11: both question forms appear
Made-up words at batchim boundaries
  [PASS] 갇문 and 갇아 boundaries are rejected
  [PASS] lessons 1-9 made-up word output matches the pre-fix seeds
  [PASS] lessons 10-12 never join batchim into a sound-changing next block
  [PASS] lesson 10 ten-seed question mix stays near the pre-fix mix
  [PASS] nonword still falls back after 20 rejected candidates
  [PASS] sequence still falls back after 20 rejected candidates
Confusion drills
  [PASS] lesson 1: drilled pair always romanizes differently
  [PASS] lesson 2: drilled pair always romanizes differently
  [PASS] lesson 3: drilled pair always romanizes differently
  [PASS] lesson 4: drilled pair always romanizes differently
  [PASS] lesson 5: drilled pair always romanizes differently
  [PASS] lesson 6: drilled pair always romanizes differently
  [PASS] lesson 7: drilled pair always romanizes differently
  [PASS] lesson 8: drilled pair always romanizes differently
  [PASS] lesson 9: drilled pair always romanizes differently
  [PASS] lesson 10: drilled pair always romanizes differently
  [PASS] lesson 11: drilled pair always romanizes differently
  [PASS] lesson 12: drilled pair always romanizes differently
Konglish
  [PASS] decode questions only use loanwords
  [PASS] 'mouse' accepted for 'mouse (computer)'
  [PASS] empty answer is never correct
  [PASS] kspell never offers a second correct spelling
Content
  [PASS] word contrast example uses 씻어요 (to wash)
Conversation
  [PASS] /talk with <3 mastered syllables returns None (no fake translation)
  [PASS] translation check ignores filler-word overlap
Lesson content (2026-10 content pass)
  [PASS] every lesson word uses only letters taught by its lesson
  [PASS] lessons 1-11 each have at least 4 real words
  [PASS] 손/선 (final consonants) not offered before batchim is taught
  [PASS] 손/선 offered once batchim is taught
  [PASS] real word: reading it right is graded right
  [PASS] real word: the meaning is revealed
  [PASS] real word: 'kimchi' accepted for 김치
  [PASS] lesson words count as real words (never served as 'not a real word')
  [PASS] every letter taught in lessons 1-9 has a mnemonic
  [PASS] every lesson's intro and reference table render
Phone-width screens (Termux is ~49 columns)
  [PASS] intros, tables, help, key and charts all fit 49 columns
  [PASS] long lines break between words, not inside them
A sense of progress (rounds, solid moments, next step)
  [PASS] a finished lesson says so up front
  [PASS] every question shows where you are in the round
  [PASS] a round ends with a progress card
  [PASS] the card offers the next lesson when this one is done
  [PASS] pressing n on the card moves you to the next lesson
  [PASS] after /rain and /conveyor the question comes back with its round counter
  [PASS] blocks that become solid are announced at round end
  [PASS] an unfinished lesson's card lists what's still to go
Question mix (found by scripts/_playtest_learners.py)
  [PASS] special modes get real airtime (were ~0%)
  [PASS] look-alike drills no longer appear on their own (decided 2026-10-14)
Mix-ups: shown side by side, then asked again
  [PASS] a mix-up is reported on the result
  [PASS] the missed block isn't asked again straight away
  [PASS] the 3rd question asks the missed block again
  [PASS] ...with the block it was mixed up with among the choices
  [PASS] a typo is not a mix-up and queues nothing
  [PASS] a queued mix-up is dropped when you change lesson
  [PASS] the miss shows both blocks with their sounds
Final-consonant mix-ups
  [PASS] sound_to_letter: records and shows built blocks with final sounds
  [PASS] sound_to_letter: queues the built blocks, then asks the comeback
  [PASS] sound_to_letter: comeback contrasts 각 and 갇
  [PASS] letter_to_sound: records and shows built blocks with final sounds
  [PASS] letter_to_sound: queues the built blocks, then asks the comeback
  [PASS] letter_to_sound: comeback contrasts 각 and 갇
  [PASS] lesson 11: a changed final sound also records whole blocks
  [PASS] mix-up feedback promises a comeback only when one was queued
  [PASS] lesson 10: no missing_vowel/decompose picked only to become spell
  [PASS] lesson 11: no missing_vowel/decompose picked only to become spell
  [PASS] lesson 1: a 어/오 mix-up counts as relevant to lesson 1
  [PASS] lesson 1: the drill targets the learner's own 어/오 mix-up
  [PASS] read-aloud: reading 어 as 'o' records a 어/오 mix-up
  [PASS] read-aloud: a typo is not recorded as a mix-up
Reading mix-ups inferred from taught blocks
  [PASS] lesson 3: 보 read beo identifies 버
  [PASS] lesson 4: 코 read keo identifies 커
  [PASS] lesson 4: 바 read pa identifies 파
  [PASS] lesson 10: 간 read gam identifies 감
  [PASS] inferred pair is in flat and per-item confusion history
  [PASS] inferred pair returns on the third question with the swapped block
  [PASS] real_word: one changed block is recorded, not the whole word
  [PASS] read_word: one changed block is recorded, not the whole word
  [PASS] nonword_decode: one changed block is recorded, not the whole word
  [PASS] sequence_decode: one changed block is recorded, not the whole word
  [PASS] word contrast: offered 고기 for 거기 records 고/거
  [PASS] reading mix-up: typo records nothing
  [PASS] reading mix-up: two changed blocks records nothing
  [PASS] reading mix-up: ambiguous reading records nothing
  [PASS] reading mix-up: untaught letter records nothing
  [PASS] word contrast: an offered two-block alternative records nothing
  [PASS] word contrast: a studied but unoffered block records nothing
  [PASS] confusion drill doesn't print each block's sound next to it
  [PASS] word contrast doesn't show a translation containing the answer
Mistakes, hints and skips count toward mastery
  [PASS] 3 right in a row makes an item solid (same pace as before)
  [PASS] 3 right + 5 wrong is NOT solid (the old formula said it was)
  [PASS] an early slip is forgiven: 4 right answers after 3 misses make it solid
  [PASS] a solid item that keeps getting missed stops being solid
  [PASS] progress saved before this change: 3 right / 5 wrong reads as not solid
  [PASS] progress saved before this change: a clean record stays solid
  [PASS] answer history survives save and load
  [PASS] the very old 0-5 score still carries over as a floor
  [PASS] a right answer after /hint is still right and keeps the streak
  [PASS] right answers after /hint don't make an item solid
  [PASS] a hinted word gives its blocks no credit
  [PASS] an unhinted word still credits its blocks
  [PASS] /skip counts as a miss on the item
  [PASS] /skip ends the streak but isn't graded as an answer
  [PASS] skipping the hard ones can't leave an item solid
  [PASS] /skip records no mix-up
  [PASS] CLI: /hint then a right answer is recorded as helped
  [PASS] CLI: says a hinted answer doesn't count toward solid
  [PASS] CLI: /skip is recorded as a miss and saved
  [PASS] a stuck learner isn't offered to move on too early
  [PASS] after 3 rounds with no progress, the card offers the next lesson
  [PASS] ...and n takes you there
  [PASS] ...without marking the unfinished lesson done
  [PASS] stuck in the last lesson: suggests reviewing an earlier one
  [PASS] a learner who is making progress isn't told to move on
Missing vowel answers and the mix-ups they save (phone screenshot, 2026-10-14)
  [PASS] missing vowel: typing the whole block (미) is right
  [PASS] missing vowel: typing the two letters apart (ㅁㅣ) is right
  [PASS] missing vowel: typing the consonant shown gets a nudge, not a grade
  [PASS] missing vowel: typing the consonant saves no mix-up
  [PASS] missing vowel: a wrong vowel is saved as the two blocks (모 for 미)
  [PASS] old saved pairs: consonant-vs-vowel ones aren't listed under 'Practice these'
  [PASS] old saved pairs: the drill gets 모↔미, not 오↔미 or ㄷ↔더
  [PASS] no question type saves a consonant-vs-vowel mix-up
  [PASS] /skip uses up a turn in the round (the next question is 2/10)
  [PASS] a round of skips still ends with its card
Conveyor game
  [PASS] a choice's number picks it (choices are shown as 1-4)
  [PASS] letters still pick too
  [PASS] a number past the last choice isn't a pick
  [PASS] typing the right choice's number is graded right
  [PASS] no literal ** in conveyor questions or feedback
  [PASS] the hint isn't shown before you answer
  [PASS] feedback has one ✓/✗ mark, not two
  [PASS] conveyor: /hint shows the hint on request
  [PASS] conveyor: answering 3 after /hint scores, without mastery credit
Stray key codes
  [PASS] End key code alone counts as blank
  [PASS] key codes around an answer are dropped
  [PASS] arrow/Home/F1 codes and a lone Esc are dropped
  [PASS] Hangul, spaces and slashes are untouched
  [PASS] the CLI's input() strips key codes
Lesson-complete box
  [PASS] lesson 1 done: box previews Lesson 2 (title + what it teaches), borders line up
  [PASS] lesson 2 done: box previews Lesson 3 (title + what it teaches), borders line up
  [PASS] lesson 3 done: box previews Lesson 4 (title + what it teaches), borders line up
  [PASS] lesson 4 done: box previews Lesson 5 (title + what it teaches), borders line up
  [PASS] lesson 5 done: box previews Lesson 6 (title + what it teaches), borders line up
  [PASS] lesson 6 done: box previews Lesson 7 (title + what it teaches), borders line up
  [PASS] lesson 7 done: box previews Lesson 8 (title + what it teaches), borders line up
  [PASS] lesson 8 done: box previews Lesson 9 (title + what it teaches), borders line up
  [PASS] lesson 9 done: box previews Lesson 10 (title + what it teaches), borders line up
  [PASS] lesson 10 done: box previews Lesson 11 (title + what it teaches), borders line up
  [PASS] lesson 11 done: box previews Lesson 12 (title + what it teaches), borders line up
Session summary with skips
  [PASS] ten skips: the round card and the summary agree
  [PASS] mixed answers and a skip: graded answers and skips shown apart
  [PASS] skips are counted for the session
  [PASS] record_skip counts one skip
The silent ㅇ is described correctly
  [PASS] Lesson 1 note: a vowel can't START a syllable alone (not 'never stands alone')
  [PASS] walkthrough: ㅇ 'comes first' (not 'in front': it sits on top of 오/우/으)
Korean-language claims (accuracy audit, 2026-10-14)
  [PASS] old wording gone: 't write a bare vowel alone'
  [PASS] old wording gone: 'at the front is silent'
  [PASS] old wording gone: 'glued onto the front'
  [PASS] old wording gone: 'literally, the great script'
  [PASS] old wording gone: 'Six letters with a puff'
  [PASS] Lesson 4: only ㅊ ㅋ ㅌ ㅍ are described as having a puff of air
  [PASS] 학교: 'hagyo' (drops the audible ㄱ) is no longer accepted
  [PASS] Lesson 10 note: only ㄱ, ㄷ, ㅂ are told to stop short
  [PASS] batchim hint: ㄴ ㄹ ㅁ ㅇ are not told to 'stop short'
  [PASS] batchim hint: ㄱ ㄷ ㅂ still are
Natural spellings: 'oo' for ㅜ, 'yoo' for ㅠ (2026-10-15)
  [PASS] 'oo' accepted in ㅜ blocks (구 goo, 누 noo, bare ㅜ)
  [PASS] ...inside words too (디구 deegoo, 우리 ooree)
  [PASS] 'yoo' accepted for ㅠ (유 yoo, 슈 shoo/syoo)
  [PASS] 'oo' not accepted where there's no ㅜ/ㅠ (오, 으, 어)
Which Word?: a first-time pair is a guess that can't count against you
  [PASS] first meeting with a pair is marked as discovery
  [PASS] a wrong first guess is ungraded: streak, accuracy and item history untouched
  [PASS] the same pair is graded from then on
  [PASS] ...so a later wrong answer counts
  [PASS] a right first guess counts normally
  [PASS] skipping a first-time pair doesn't break the streak or count as a miss
  [PASS] CLI: the guess is announced, and the miss is labelled as not counting
Reading reward: curated lesson words, no repeats, every 10 in a row
  [PASS] every eligible word shows once before any repeats
  [PASS] only words from this lesson or earlier
  [PASS] keeps going after the pool is used up
  [PASS] no reward after 5 or 9 in a row; one after 10
Hangul Rain
  [PASS] lesson 1: rain has something to play
  [PASS] lesson 10: rain has something to play
  [PASS] lesson 11: rain has something to play
  [PASS] lesson 12: rain has something to play
  [PASS] speed only steps up once per level (no runaway)
  [PASS] keystroke goes to the lowest (most urgent) invader
  [PASS] typing finishes the targeted invader
  [PASS] wrong key counts as a miss
  [PASS] rain status: lives come first
  [PASS] rain status: fits 48 columns with a big score
  [PASS] rain status: shows the quit hint
  [PASS] rain status: a miss replaces the quit hint while it flashes

RESULT: ALL PASS
```

## scripts\_verify_lesson_flow.py (exit 0)

```text
test_advance_bad_input_then_jump (__main__.LessonFlowEvents.test_advance_bad_input_then_jump) ... ok
test_advance_browse_then_accept (__main__.LessonFlowEvents.test_advance_browse_then_accept) ... ok
test_advance_decline_or_closed_input_stays (__main__.LessonFlowEvents.test_advance_decline_or_closed_input_stays) ... ok
test_advance_not_completed_does_nothing (__main__.LessonFlowEvents.test_advance_not_completed_does_nothing) ... ok
test_advance_on_last_lesson_completes_curriculum (__main__.LessonFlowEvents.test_advance_on_last_lesson_completes_curriculum) ... ok
test_failed_check_enter_at_retry_goes_back_to_practice (__main__.LessonFlowEvents.test_failed_check_enter_at_retry_goes_back_to_practice) ... ok
test_failed_check_practice_then_retry (__main__.LessonFlowEvents.test_failed_check_practice_then_retry) ... ok
test_hinted_answer_is_not_independent_and_comes_back (__main__.LessonFlowEvents.test_hinted_answer_is_not_independent_and_comes_back) ... ok
test_reading_check_back_and_quit (__main__.LessonFlowEvents.test_reading_check_back_and_quit) ... ok
test_reading_check_blank_and_bad_input_are_not_graded (__main__.LessonFlowEvents.test_reading_check_blank_and_bad_input_are_not_graded) ... ok
test_reading_check_events_include_next_input_and_survive_json (__main__.LessonFlowEvents.test_reading_check_events_include_next_input_and_survive_json) ... ok
test_reading_check_pass_ends_without_another_prompt (__main__.LessonFlowEvents.test_reading_check_pass_ends_without_another_prompt) ... ok
test_round_card_done_lesson (__main__.LessonFlowEvents.test_round_card_done_lesson) ... ok
test_round_card_events_and_actions (__main__.LessonFlowEvents.test_round_card_events_and_actions) ... ok
test_round_card_last_lesson_has_no_next (__main__.LessonFlowEvents.test_round_card_last_lesson_has_no_next) ... ok
test_round_card_notices_are_filtered_and_cleared (__main__.LessonFlowEvents.test_round_card_notices_are_filtered_and_cleared) ... ok
test_round_card_ready_offers_the_check (__main__.LessonFlowEvents.test_round_card_ready_offers_the_check) ... ok
test_round_card_reward_word (__main__.LessonFlowEvents.test_round_card_reward_word) ... ok

----------------------------------------------------------------------
Ran 18 tests in 1.194s

OK
```

## scripts\_verify_missing_vowel_batchim_guard.py (exit 0)

```text
============================================================================
(a) BATCHIM LESSONS — expect mode 'spell' every time (guard fires)
============================================================================

lesson 10: Bottom Consonants (Batchim)   pool=14
  pool contents: 각 간 갇 갈 감 갑 강 먹 문 믿 물 몸 밥 방
  modes over 12 calls: ['spell', 'spell', 'spell', 'spell', 'spell', 'spell', 'spell', 'spell', 'spell', 'spell', 'spell', 'spell']
  distinct modes: ['spell']
  -> PASS (all spell)
     sample: mode=spell  prompt='Type the Hangul for: **gang**'
     sample: mode=spell  prompt='Type the Hangul for: **mun**'

lesson 11: More Batchim   pool=8
  pool contents: 방 밥 말 문 곰 먹 밖 옷
  modes over 12 calls: ['spell', 'spell', 'spell', 'spell', 'spell', 'spell', 'spell', 'spell', 'spell', 'spell', 'spell', 'spell']
  distinct modes: ['spell']
  -> PASS (all spell)
     sample: mode=spell  prompt='Type the Hangul for: **bak**'
     sample: mode=spell  prompt='Type the Hangul for: **bang**'

============================================================================
(b) BARE-CV LESSONS — expect mode 'missing_vowel' retained (no regression)
============================================================================

lesson 5: Building Blocks   pool=12
  modes over 12 calls: ['missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel']
  distinct modes: ['missing_vowel']
  -> PASS (all missing_vowel)
     sample: mode=missing_vowel
             prompt='**ㄱ** + ? = **ga**\nWhich vowel completes it?'
             correct_answer='ㅏ'  choices=['ㅗ', 'ㅡ', 'ㅏ', 'ㅣ']

lesson 7: ㅐ, ㅔ and Friends   pool=14
  modes over 12 calls: ['missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel']
  distinct modes: ['missing_vowel']
  -> PASS (all missing_vowel)
     sample: mode=missing_vowel
             prompt='**ㄴ** + ? = **ne**\nWhich vowel completes it?'
             correct_answer='ㅔ'  choices=['ㅑ', 'ㅐ', 'ㅔ', 'ㅣ']

============================================================================
(c) GRADING CHECK — bare-CV missing_vowel still grades correct/incorrect
============================================================================
target block      : 모
correct_answer    : 'ㅗ'
choices           : ['ㅓ', 'ㅗ', 'ㅣ', 'ㅜ']
answer(correct)   -> correct=True  feedback=✅ Spot on! **ㅗ** is right.
answer('ㅓ')   -> correct=False  feedback=❌ Not quite — it's **ㅗ**.

============================================================================
(d) EXHAUSTIVE — every lesson, 20 calls, confirm zero batchim leaks
============================================================================
  lesson  2: checked 20 calls
  lesson  3: checked 20 calls
  lesson  4: checked 20 calls
  lesson  5: checked 20 calls
  lesson  6: checked 20 calls
  lesson  7: checked 20 calls
  lesson  8: checked 20 calls
  lesson  9: checked 20 calls
  lesson 10: checked 20 calls
  lesson 11: checked 20 calls
  lesson 12: checked 20 calls

  batchim syllables that leaked through as missing_vowel: 0
  -> PASS: no batchim syllable ever served as a missing_vowel question
```

## scripts\_verify_reading_check.py (exit 0)

```text
test_all_lessons_have_five_unique_answerable_prompts (__main__.ReadingChecks.test_all_lessons_have_five_unique_answerable_prompts) ... ok
test_check_answers_do_not_inflate_practice_scores (__main__.ReadingChecks.test_check_answers_do_not_inflate_practice_scores) ... ok
test_cli_failed_check_offers_targeted_practice_then_new_check (__main__.ReadingChecks.test_cli_failed_check_offers_targeted_practice_then_new_check) ... ok
test_cli_hints_skips_and_quit_do_not_grant_completion (__main__.ReadingChecks.test_cli_hints_skips_and_quit_do_not_grant_completion) ... ok
test_cli_passes_and_keeps_round_statistics_separate (__main__.ReadingChecks.test_cli_passes_and_keeps_round_statistics_separate) ... ok
test_existing_completions_are_preserved (__main__.ReadingChecks.test_existing_completions_are_preserved) ... ok
test_four_of_five_passes_and_survives_reload_without_advancing (__main__.ReadingChecks.test_four_of_five_passes_and_survives_reload_without_advancing) ... ok
test_generated_components_are_taught_and_new (__main__.ReadingChecks.test_generated_components_are_taught_and_new) ... ok
test_hints_require_independent_retry_and_cannot_loop_forever (__main__.ReadingChecks.test_hints_require_independent_retry_and_cannot_loop_forever) ... ok
test_independent_hint_retry_counts_only_once (__main__.ReadingChecks.test_independent_hint_retry_counts_only_once) ... ok
test_interrupted_check_has_no_result_or_completion (__main__.ReadingChecks.test_interrupted_check_has_no_result_or_completion) ... ok
test_misses_are_marked_not_yet_with_what_was_typed (__main__.ReadingChecks.test_misses_are_marked_not_yet_with_what_was_typed) ... ok
test_natural_romanizations_are_accepted (__main__.ReadingChecks.test_natural_romanizations_are_accepted) ... ok
test_new_combinations_do_not_repeat_exposed_items (__main__.ReadingChecks.test_new_combinations_do_not_repeat_exposed_items) ... ok
test_real_cli_pass_then_stay_records_completion (__main__.ReadingChecks.test_real_cli_pass_then_stay_records_completion) ... ok
test_recognition_alone_cannot_complete_or_skip_into_completion (__main__.ReadingChecks.test_recognition_alone_cannot_complete_or_skip_into_completion) ... ok
test_resume_ready_profile_enters_check_before_normal_question (__main__.ReadingChecks.test_resume_ready_profile_enters_check_before_normal_question) ... ok
test_round_card_accepts_check_on_a_completed_lesson (__main__.ReadingChecks.test_round_card_accepts_check_on_a_completed_lesson) ... ok
test_round_card_and_exit_summary_do_not_claim_recognition_completion (__main__.ReadingChecks.test_round_card_and_exit_summary_do_not_claim_recognition_completion) ... ok
test_targeted_practice_asks_before_revealing_the_answer (__main__.ReadingChecks.test_targeted_practice_asks_before_revealing_the_answer) ... ok
test_three_of_five_does_not_complete (__main__.ReadingChecks.test_three_of_five_does_not_complete) ... ok

----------------------------------------------------------------------
Ran 21 tests in 1.662s

OK
```

## scripts\_verify_sejong_flow.py (exit 0)

```text
PASS event contract
PASS all-correct order and scores
PASS clock starts after baseline
PASS assessment answers stay hidden
PASS occasional correct lines
PASS streak line replaces correct line
PASS misses must be consecutive
PASS Batch 1 build targets and distractors
PASS wrong predict reaction
PASS misses requeued
PASS narrator and word payoff
PASS check retry and independence
PASS recognize reverses retrieve
PASS 40 failed Batch 0 checks
PASS unavailable check advances
PASS baseline skip paths
PASS resume, replay, quit
PASS practice hints and script notices
PASS file-free and silent
PASS timer and verdict
20 checks passed
```

## Diff stat before adding this evidence

```text
 docs/sejong-events.md                              |  16 +-
 docs/tasks/2026-10-16_sejong-flow-transcript.jsonl | 142 ++++++++--------
 scripts/_verify_sejong_flow.py                     | 181 +++++++++++++++++++--
 sejong_flow.py                                     |  84 +++++++---
 4 files changed, 304 insertions(+), 119 deletions(-)
```

## Full flow and contract diff

```text
diff --git a/docs/sejong-events.md b/docs/sejong-events.md
index 62d31d7..ce80614 100644
--- a/docs/sejong-events.md
+++ b/docs/sejong-events.md
@@ -25,7 +25,7 @@ flow   = SejongFlow.from_state(quiz, content, text)
 - `seed` makes question order repeatable for tests.
 - `answer` is the text typed, or the exact `choices` string tapped. `""` means a tap on a "continue" prompt.
 - Commands: `"/hint"` (only when the current question says `hint_available`), `"/quit"`. Anything else starting with `/` returns a `notice` and changes nothing.
-- `active_ms` is the active time since the previous call, already idle-capped by the renderer (see Timer). Python adds it to the saved total.
+- `active_ms` is the active time since the previous call, already idle-capped by the renderer (see Timer). Python ignores time sent before the first Batch 0 `letter_intro`; it adds later time to the saved total.
 - `resume("reopen")` after the app is reopened from saved state; `resume("pause")` after the page comes back from being hidden or idle. Each returns the right narrator line, then repeats the current screen so the renderer can redraw it.
 - Every returned list ends with exactly one `await` or one `finished` event.

@@ -34,7 +34,7 @@ flow   = SejongFlow.from_state(quiz, content, text)
 1. Show events in list order.
 2. `narrator`, `letter_intro`, `reveal`, `word_read` and `milestone` each occupy the screen until the learner taps. The tap is handled locally: **no Python call**. Then show the next event.
 3. `stage` updates the header and shows nothing by itself.
-4. `result` replaces the question card it answers (same `qid`) and waits for a local tap.
+4. `result` replaces the practice or check question card it answers (same `qid`) and waits for a local tap. Baseline and post-test answers go directly to the next question or the final `score`, without per-question feedback.
 5. On `await`, show the input and send the answer with `submit()`.
 6. Unknown `kind`: skip it and log it. Unknown fields: ignore them. Python may add fields without breaking older renderers.
 7. After every `submit()`, save `flow.export_state()` (browser: IndexedDB).
@@ -88,6 +88,7 @@ Unscored guess before a block is revealed. Always followed by an `await` with `i

 ### `reveal`
 The block assembles. Comes after the predict answer, whatever was picked.
+After a wrong prediction, the next event is a `narrator` from `lines.predict_wrong.side` or `.stack` (matching the target vowel's layout), followed by `lines.predict_reveal`. A right prediction goes straight to `lines.predict_reveal`.

 | Field | Type | Notes |
 | --- | --- | --- |
@@ -114,8 +115,10 @@ One question card.
 | **hint_available** | bool | |
 | round | {index, size} | Position in the current phase, for the round bar. `size` can grow if a missed item is re-queued. |

+Build cards offer at least one distractor with the same consonant and a different vowel, and one with the same vowel and a different consonant. Batch 1 asks only blocks containing a new Batch 1 letter.
+
 ### `result`
-The grade for one question. The renderer shows the useful fact first, then the line.
+The grade for a practice or check question. Baseline and post-test questions emit no `result`; only their final `score` is shown. The renderer shows the useful fact first, then the line.

 | Field | Type | Notes |
 | --- | --- | --- |
@@ -125,7 +128,7 @@ The grade for one question. The renderer shows the useful fact first, then the l
 | **correct_answer** | str | Display form |
 | chosen_is | str | If the wrong answer is another real letter/block, what it is ("ㅋ") |
 | tell | str | The confusion-pair tell from `sejong.json` ("ㄷ has the extra stroke on top.") |
-| line | narrator | Jeong's reaction, if any. Absent on baseline, check and post-test cards. |
+| line | narrator | Jeong's reaction, if any. Correct practice lines are occasional; a streak at 5/10/15 uses its streak line here instead. After three consecutive wrong practice answers in one phase, this is `lines.repeated_miss`. Absent on check cards. |
 | **streak** | int | Current streak after this answer (0 after a miss) |
 | requeued | bool | True when a missed item will come back later this phase |

@@ -188,7 +191,7 @@ What the renderer should ask for next. Always last in the list (unless `finished
 ## Timer

 - The renderer counts active milliseconds. It stops counting when the page is hidden (`visibilitychange`) or after **120 s** without input, and resumes on the next interaction.
-- It sends the elapsed active time with every `submit()`. Python owns the total and saves it in `export_state()`.
+- It sends the elapsed active time with every `submit()`. Python starts the saved total at the first Batch 0 `letter_intro`, after the baseline or skip, and emits `lines.clock_start` immediately before Batch 0's intro line.
 - The time is shown **only** on `milestone` screens, never during questions.
 - When counting resumes after a hide or idle stop, the renderer calls `resume("pause")` before anything else, so Jeong's "the clock stopped" line is true.

@@ -205,6 +208,7 @@ flow.start() ->
 flow.submit("Skip", active_ms=41000) ->
 [ {"kind":"narrator","speaker":"jeong","text":"Skipping the test. Confident, or cautious? We shall see.","line_id":"lines.baseline_skip","source":"invented"},
   {"kind":"stage","batch_id":0,"batch_name":"The Revelation","phase":"discover","letters_known":[]},
+  {"kind":"narrator","line_id":"lines.clock_start", …},
   {"kind":"narrator","speaker":"jeong","text":"Four letters. Two consonants, two vowels. That is enough to begin.", …},
   {"kind":"letter_intro","jamo":"ㄴ","type":"consonant","roman":"n","sound":"n, as in 'no'","shape":"Your tongue tip touching …","shape_source":"haerye"},
   {"kind":"letter_intro","jamo":"ㄷ", …, "related":"ㄴ","notice_line":{"speaker":"jeong","text":"ㄴ, with an added stroke. …"}},
@@ -220,5 +224,5 @@ flow.submit("Skip", active_ms=41000) ->
 - Every event has `kind`, and every **bold** field above for its kind.
 - Every `narrator.line_id` resolves to a line in `sejong.json`, and its `text` has no unfilled `{placeholder}`.
 - No `question` (except `context: "baseline"`), `predict` choice or `display` uses a letter outside `letters_known`. The post-test remains strict.
-- `result.line` never appears on baseline, check or post-test cards.
+- Baseline and post-test cards emit no `result`; check results have no `line`.
 - `export_state()` → `from_state()` mid-batch, then the same answers, gives the same events as an uninterrupted run (same seed).
diff --git a/sejong_flow.py b/sejong_flow.py
index 804be66..402a798 100644
--- a/sejong_flow.py
+++ b/sejong_flow.py
@@ -35,12 +35,14 @@ class SejongFlow:
         self.current_engine_question = None
         self.screen = []
         self.assisted = False
-        self.misses = {}
+        self.consecutive_wrong = 0
+        self.repeated_miss_index = 0
         self.check = None
         self.check_results = {}
         self.check_practice = []
         self.streak = 0
         self.correct_line_index = 0
+        self.last_correct_line = False
         self.words_read = []
         self.outcome = None

@@ -143,7 +145,10 @@ class SejongFlow:
     def _enter_batch(self, events):
         batch = self._batch()
         self.phase = "discover"
-        events += [self._stage(), self._line(f"lines.batch_intro.{batch['id']}")]
+        events.append(self._stage())
+        if self.batch_index == 0:
+            events.append(self._line("lines.clock_start"))
+        events.append(self._line(f"lines.batch_intro.{batch['id']}"))
         for letter in batch["letters"]:
             intro = {"kind": "letter_intro", "jamo": letter["jamo"], "type": letter["type"],
                      "roman": letter["roman"], "sound": letter["sound"],
@@ -190,7 +195,9 @@ class SejongFlow:
         if self.phase in ("recognize", "retrieve"):
             self.remaining = [x["jamo"] for x in self._batch()["letters"]]
         elif self.phase == "build":
-            self.remaining = self._known_blocks()
+            new_letters = {x["jamo"] for x in self._batch()["letters"]}
+            self.remaining = [block for block in self._known_blocks()
+                              if any(part in new_letters for part in self.quiz._decompose_syllable(block)[:2])]
         elif self.phase == "decode":
             self.remaining = [x["ko"] for x in self._batch()["words"]]
         else:
@@ -198,8 +205,21 @@ class SejongFlow:
         self.rng.shuffle(self.remaining)
         self.round_size = len(self.remaining)
         self.round_index = 0
+        self.consecutive_wrong = 0
         return self._pool_question(events)

+    def _build_choices(self, target):
+        consonant, vowel, _ = self.quiz._decompose_syllable(target)
+        blocks = self._known_blocks()
+        same_consonant = [block for block in blocks if block != target
+                          and self.quiz._decompose_syllable(block)[0] == consonant]
+        same_vowel = [block for block in blocks if block != target
+                      and self.quiz._decompose_syllable(block)[1] == vowel]
+        choices = [target, self.rng.choice(same_consonant), self.rng.choice(same_vowel)]
+        choices.append(self.rng.choice([block for block in blocks if block not in choices]))
+        self.rng.shuffle(choices)
+        return choices
+
     def _pool_question(self, events):
         if not self.remaining:
             if self.phase == "build" and self.batch_index == 0:
@@ -219,8 +239,7 @@ class SejongFlow:
             return self._question(events, target, "read_aloud", self._letter(target)["roman"],
                                   "Type this letter's sound.", target, "text")
         if self.phase == "build":
-            choices = self.rng.sample([x for x in self._known_blocks() if x != target], 3) + [target]
-            self.rng.shuffle(choices)
+            choices = self._build_choices(target)
             c, v, _ = self.quiz._decompose_syllable(target)
             return self._question(events, target, "build_syllable", target,
                                   "Which block do these letters build?", f"{c} + {v}",
@@ -257,6 +276,7 @@ class SejongFlow:

     def _start_check(self, events):
         self.phase = "check"
+        self.consecutive_wrong = 0
         events += [self._stage(), self._line("lines.decode_check_intro")]
         return self._new_check(events)

@@ -304,6 +324,7 @@ class SejongFlow:
                 return self._advance_after_check(events)
             events.append(self._line("lines.decode_check_fail"))
             self.phase = "check_practice"
+            self.consecutive_wrong = 0
             self.check_practice = [q.letter for q in list(self.check.missed.values())[:3]]
             self.round_size = len(self.check_practice)
             self.round_index = 0
@@ -371,21 +392,30 @@ class SejongFlow:
     def _reaction(self, correct, target, answer):
         if correct:
             self.streak += 1
-            index = self.correct_line_index % len(self.content["lines"]["correct"])
-            self.correct_line_index += 1
-            line = self._line(f"lines.correct.{index}")
-            bonus = [self._line(f"lines.streak.{self.streak}")] if str(self.streak) in self.content["lines"]["streak"] else []
-            return line, bonus, None, None
+            self.consecutive_wrong = 0
+            if str(self.streak) in self.content["lines"]["streak"]:
+                self.last_correct_line = False
+                return self._line(f"lines.streak.{self.streak}"), None, None
+            speak = not self.last_correct_line and self.rng.random() < 1 / 3
+            self.last_correct_line = speak
+            if speak:
+                index = self.correct_line_index % len(self.content["lines"]["correct"])
+                self.correct_line_index += 1
+                return self._line(f"lines.correct.{index}"), None, None
+            return None, None, None
         self.streak = 0
-        self.misses[target] = self.misses.get(target, 0) + 1
+        self.last_correct_line = False
+        self.consecutive_wrong += 1
         chosen, tell = self._chosen_tell(answer, target)
-        if self.misses[target] >= 2:
-            line = self._line(f"lines.repeated_miss.{(self.misses[target] - 2) % len(self.content['lines']['repeated_miss'])}")
+        if self.consecutive_wrong == 3:
+            line = self._line(f"lines.repeated_miss.{self.repeated_miss_index % len(self.content['lines']['repeated_miss'])}")
+            self.repeated_miss_index += 1
+            self.consecutive_wrong = 0
         elif chosen and tell:
             line = self._line("lines.miss.0", chosen=chosen, tell=tell)
         else:
             line = self._line("lines.miss_no_tell")
-        return line, [], chosen, tell
+        return line, chosen, tell

     def _hint(self, target):
         if target in self.letters_known:
@@ -399,7 +429,8 @@ class SejongFlow:
             raise ValueError("Start the Sejong Test first.")
         if not isinstance(active_ms, int) or active_ms < 0:
             raise ValueError("active_ms must be a nonnegative integer.")
-        self.active_ms += active_ms
+        if self.letters_known:
+            self.active_ms += active_ms
         answer = str(answer)
         if answer == "/quit":
             self.outcome = "quit"
@@ -421,11 +452,14 @@ class SejongFlow:
                 return [{"kind": "notice", "text": "Choose a displayed option."}, self.screen[-1]]
             p = self._batch()["predict_reveal"]
             c, v, _ = self.quiz._decompose_syllable(p["block"])
+            layout = "side" if v in ("ㅏ", "ㅓ", "ㅣ") else "stack"
             events = [{"kind": "reveal", "block": p["block"], "parts": [c, v],
-                       "layout": "side" if v in ("ㅏ", "ㅓ", "ㅣ") else "stack",
+                       "layout": layout,
                        "roman": p["roman"], "meaning": p["meaning"],
-                       "guessed_right": answer == p["block"]},
-                      self._line(f"lines.predict_reveal.{self.batch_index}")]
+                       "guessed_right": answer == p["block"]}]
+            if answer != p["block"]:
+                events.append(self._line(f"lines.predict_wrong.{layout}", vowel=v))
+            events.append(self._line(f"lines.predict_reveal.{self.batch_index}"))
             return self._next_phase(events)
         if not self.current or self.current["kind"] != "question":
             raise ValueError("No question is open.")
@@ -439,6 +473,7 @@ class SejongFlow:
         if context in ("baseline", "post_test"):
             correct = answer == self.current["answer"]
             self.assessment_correct += int(correct)
+            return self._assessment_question([])
         elif context == "check":
             correct = self.check.submit(answer)
         else:
@@ -450,14 +485,14 @@ class SejongFlow:
                   "streak": self.streak, "requeued": False}
         events = [result]
         if context in ("practice", "check_practice"):
-            line, bonus, chosen, tell = self._reaction(correct, target, answer)
-            result["line"] = line
+            line, chosen, tell = self._reaction(correct, target, answer)
+            if line is not None:
+                result["line"] = line
             result["streak"] = self.streak
             if chosen:
                 result["chosen_is"] = chosen
             if tell:
                 result["tell"] = tell
-            events += bonus
             self.round_index += 1
             if not correct:
                 result["requeued"] = True
@@ -479,8 +514,6 @@ class SejongFlow:
                     payoff["line"] = self._line_for_inline(word["first_read_line"],
                         f"batches.{self.batch_index}.words.{self._batch()['words'].index(word)}.first_read_line")
                 events.append(payoff)
-        if context in ("baseline", "post_test"):
-            return self._assessment_question(events)
         if context == "check":
             return self._check_question(events)
         if context == "check_practice":
@@ -510,8 +543,9 @@ class SejongFlow:
         keys = ("phase", "batch_index", "letters_known", "active_ms", "baseline_score",
                 "post_score", "assessment_items", "assessment_correct", "remaining",
                 "round_size", "round_index", "qid_number", "current", "screen",
-                "assisted", "misses", "check_results", "check_practice", "streak",
-                "correct_line_index", "words_read", "outcome")
+                "assisted", "consecutive_wrong", "repeated_miss_index", "check_results",
+                "check_practice", "streak", "correct_line_index", "last_correct_line",
+                "words_read", "outcome")
         state = {key: getattr(self, key) for key in keys}
         state["check"] = check
         state["rng_state"] = self.rng.getstate()
```

## Existing checks updated

- `misses_requeue` now submits an actual wrong choice for choice cards and checks Batch 1 build growth against its new 12-card pool. The old `WRONG` string triggered only a notice on choice cards.
- `narrator_and_words` now expects the repeated-miss line after three consecutive wrong answers, rather than two misses of one target.
- `timer` now counts calls after the first Batch 0 `letter_intro`; intro and baseline time are excluded.
- `contract` now rejects assessment `result` events, while still checking that check results omit narrator lines.

## Deviations

None. `data/sejong.json` content changes were already committed on master in `8ea4290`; this branch did not edit that file or `sejong_cli.py`.
