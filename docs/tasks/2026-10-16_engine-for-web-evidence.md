# Engine for web: verification evidence

## scripts/_verify_engine_web.py

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
ALL PASS: 9 checks
```


## scripts/_verify_decompose_syllable.py

```text
============================================================================
(a) PROMPT / LEAK — prompt shows the block, never its jamo
============================================================================
   block=사  cho=ㅅ jung=ㅏ jong=''
      prompt='Break **사** into its parts.\nWhich consonant + vowel make this block?'
      answer='ㅅ + ㅏ'  leaked=[]
   [PASS] prompt for 사 does not leak ㅅ/ㅏ  — leaked=[]
   block=고  cho=ㄱ jung=ㅗ jong=''
      prompt='Break **고** into its parts.\nWhich consonant + vowel make this block?'
      answer='ㄱ + ㅗ'  leaked=[]
   [PASS] prompt for 고 does not leak ㄱ/ㅗ  — leaked=[]
   block=가  cho=ㄱ jung=ㅏ jong=''
      prompt='Break **가** into its parts.\nWhich consonant + vowel make this block?'
      answer='ㄱ + ㅏ'  leaked=[]
   [PASS] prompt for 가 does not leak ㄱ/ㅏ  — leaked=[]
   block=사  cho=ㅅ jung=ㅏ jong=''
      prompt='Break **사** into its parts.\nWhich consonant + vowel make this block?'
      answer='ㅅ + ㅏ'  leaked=[]
   [PASS] prompt for 사 does not leak ㅅ/ㅏ  — leaked=[]
   [PASS] prompt for 도 does not leak ㄷ/ㅗ  — leaked=[]
   [PASS] prompt for 나 does not leak ㄴ/ㅏ  — leaked=[]
   [PASS] prompt for 도 does not leak ㄷ/ㅗ  — leaked=[]
   [PASS] prompt for 사 does not leak ㅅ/ㅏ  — leaked=[]
   [PASS] prompt for 도 does not leak ㄷ/ㅗ  — leaked=[]
   [PASS] prompt for 사 does not leak ㅅ/ㅏ  — leaked=[]
   [PASS] prompt for 사 does not leak ㅅ/ㅏ  — leaked=[]
   [PASS] prompt for 다 does not leak ㄷ/ㅏ  — leaked=[]
   [PASS] prompt for 사 does not leak ㅅ/ㅏ  — leaked=[]
   [PASS] prompt for 도 does not leak ㄷ/ㅗ  — leaked=[]
   [PASS] prompt for 도 does not leak ㄷ/ㅗ  — leaked=[]
   [PASS] prompt for 다 does not leak ㄷ/ㅏ  — leaked=[]
   [PASS] prompt for 모 does not leak ㅁ/ㅗ  — leaked=[]
   [PASS] prompt for 마 does not leak ㅁ/ㅏ  — leaked=[]
   [PASS] prompt for 소 does not leak ㅅ/ㅗ  — leaked=[]
   [PASS] prompt for 가 does not leak ㄱ/ㅏ  — leaked=[]
   [PASS] prompt for 하 does not leak ㅎ/ㅏ  — leaked=[]
   [PASS] prompt for 노 does not leak ㄴ/ㅗ  — leaked=[]
   [PASS] prompt for 마 does not leak ㅁ/ㅏ  — leaked=[]
   [PASS] prompt for 모 does not leak ㅁ/ㅗ  — leaked=[]
   [PASS] prompt for 호 does not leak ㅎ/ㅗ  — leaked=[]
   (25 decompose_syllable questions sampled in lesson 5)
   [PASS] at least one decompose_syllable question was served

============================================================================
(b) CHOICES — well-formed, 4 options, correct present exactly once
============================================================================
   [PASS] choices for 모: 4 options  — ['ㅁ + ㅗ', 'ㄷ + ㅏ', 'ㅅ + ㅗ', 'ㄷ + ㅗ']
   [PASS] choices for 모: correct present once
   [PASS] choices for 모: no dupes
   [PASS] choices for 모: all 'X + Y' shaped  — bad=[]
      모 -> ㅁ + ㅗ   options=['ㅁ + ㅗ', 'ㄷ + ㅏ', 'ㅅ + ㅗ', 'ㄷ + ㅗ']
   [PASS] choices for 도: 4 options  — ['ㅁ + ㅏ', 'ㄴ + ㅏ', 'ㅅ + ㅏ', 'ㄷ + ㅗ']
   [PASS] choices for 도: correct present once
   [PASS] choices for 도: no dupes
   [PASS] choices for 도: all 'X + Y' shaped  — bad=[]
      도 -> ㄷ + ㅗ   options=['ㅁ + ㅏ', 'ㄴ + ㅏ', 'ㅅ + ㅏ', 'ㄷ + ㅗ']
   [PASS] choices for 노: 4 options  — ['ㅎ + ㅗ', 'ㅁ + ㅗ', 'ㄴ + ㅗ', 'ㅎ + ㅏ']
   [PASS] choices for 노: correct present once
   [PASS] choices for 노: no dupes
   [PASS] choices for 노: all 'X + Y' shaped  — bad=[]
      노 -> ㄴ + ㅗ   options=['ㅎ + ㅗ', 'ㅁ + ㅗ', 'ㄴ + ㅗ', 'ㅎ + ㅏ']
   [PASS] choices for 마: 4 options  — ['ㅎ + ㅏ', 'ㅅ + ㅗ', 'ㅁ + ㅏ', 'ㄴ + ㅏ']
   [PASS] choices for 마: correct present once
   [PASS] choices for 마: no dupes
   [PASS] choices for 마: all 'X + Y' shaped  — bad=[]
      마 -> ㅁ + ㅏ   options=['ㅎ + ㅏ', 'ㅅ + ㅗ', 'ㅁ + ㅏ', 'ㄴ + ㅏ']
   [PASS] choices for 다: 4 options  — ['ㅅ + ㅗ', 'ㄴ + ㅏ', 'ㄱ + ㅗ', 'ㄷ + ㅏ']
   [PASS] choices for 다: correct present once
   [PASS] choices for 다: no dupes
   [PASS] choices for 다: all 'X + Y' shaped  — bad=[]
      다 -> ㄷ + ㅏ   options=['ㅅ + ㅗ', 'ㄴ + ㅏ', 'ㄱ + ㅗ', 'ㄷ + ㅏ']
   [PASS] choices for 마: 4 options  — ['ㅁ + ㅏ', 'ㄱ + ㅏ', 'ㄱ + ㅗ', 'ㄴ + ㅏ']
   [PASS] choices for 마: correct present once
   [PASS] choices for 마: no dupes
   [PASS] choices for 마: all 'X + Y' shaped  — bad=[]
      마 -> ㅁ + ㅏ   options=['ㅁ + ㅏ', 'ㄱ + ㅏ', 'ㄱ + ㅗ', 'ㄴ + ㅏ']
   [PASS] choices for 하: 4 options  — ['ㅅ + ㅏ', 'ㅅ + ㅗ', 'ㄱ + ㅏ', 'ㅎ + ㅏ']
   [PASS] choices for 하: correct present once
   [PASS] choices for 하: no dupes
   [PASS] choices for 하: all 'X + Y' shaped  — bad=[]
      하 -> ㅎ + ㅏ   options=['ㅅ + ㅏ', 'ㅅ + ㅗ', 'ㄱ + ㅏ', 'ㅎ + ㅏ']
   [PASS] choices for 소: 4 options  — ['ㅅ + ㅗ', 'ㅎ + ㅏ', 'ㄷ + ㅏ', 'ㄱ + ㅗ']
   [PASS] choices for 소: correct present once
   [PASS] choices for 소: no dupes
   [PASS] choices for 소: all 'X + Y' shaped  — bad=[]
      소 -> ㅅ + ㅗ   options=['ㅅ + ㅗ', 'ㅎ + ㅏ', 'ㄷ + ㅏ', 'ㄱ + ㅗ']
   [PASS] choices for 마: 4 options  — ['ㅁ + ㅏ', 'ㅅ + ㅏ', 'ㄷ + ㅗ', 'ㄴ + ㅗ']
   [PASS] choices for 마: correct present once
   [PASS] choices for 마: no dupes
   [PASS] choices for 마: all 'X + Y' shaped  — bad=[]
      마 -> ㅁ + ㅏ   options=['ㅁ + ㅏ', 'ㅅ + ㅏ', 'ㄷ + ㅗ', 'ㄴ + ㅗ']
   [PASS] choices for 노: 4 options  — ['ㅅ + ㅗ', 'ㅎ + ㅗ', 'ㄴ + ㅗ', 'ㄱ + ㅗ']
   [PASS] choices for 노: correct present once
   [PASS] choices for 노: no dupes
   [PASS] choices for 노: all 'X + Y' shaped  — bad=[]
      노 -> ㄴ + ㅗ   options=['ㅅ + ㅗ', 'ㅎ + ㅗ', 'ㄴ + ㅗ', 'ㄱ + ㅗ']
   [PASS] choices for 고: 4 options  — ['ㅅ + ㅏ', 'ㅁ + ㅗ', 'ㄱ + ㅗ', 'ㅁ + ㅏ']
   [PASS] choices for 고: correct present once
   [PASS] choices for 고: no dupes
   [PASS] choices for 고: all 'X + Y' shaped  — bad=[]
      고 -> ㄱ + ㅗ   options=['ㅅ + ㅏ', 'ㅁ + ㅗ', 'ㄱ + ㅗ', 'ㅁ + ㅏ']
   [PASS] choices for 다: 4 options  — ['ㄱ + ㅗ', 'ㅅ + ㅗ', 'ㄷ + ㅏ', 'ㅎ + ㅏ']
   [PASS] choices for 다: correct present once
   [PASS] choices for 다: no dupes
   [PASS] choices for 다: all 'X + Y' shaped  — bad=[]
      다 -> ㄷ + ㅏ   options=['ㄱ + ㅗ', 'ㅅ + ㅗ', 'ㄷ + ㅏ', 'ㅎ + ㅏ']
   [PASS] choices for 다: 4 options  — ['ㅁ + ㅏ', 'ㅎ + ㅏ', 'ㄷ + ㅏ', 'ㅅ + ㅗ']
   [PASS] choices for 다: correct present once
   [PASS] choices for 다: no dupes
   [PASS] choices for 다: all 'X + Y' shaped  — bad=[]
      다 -> ㄷ + ㅏ   options=['ㅁ + ㅏ', 'ㅎ + ㅏ', 'ㄷ + ㅏ', 'ㅅ + ㅗ']
   [PASS] choices for 모: 4 options  — ['ㄱ + ㅏ', 'ㅎ + ㅗ', 'ㅁ + ㅗ', 'ㄴ + ㅗ']
   [PASS] choices for 모: correct present once
   [PASS] choices for 모: no dupes
   [PASS] choices for 모: all 'X + Y' shaped  — bad=[]
      모 -> ㅁ + ㅗ   options=['ㄱ + ㅏ', 'ㅎ + ㅗ', 'ㅁ + ㅗ', 'ㄴ + ㅗ']
   [PASS] choices for 노: 4 options  — ['ㅎ + ㅏ', 'ㄷ + ㅏ', 'ㅁ + ㅗ', 'ㄴ + ㅗ']
   [PASS] choices for 노: correct present once
   [PASS] choices for 노: no dupes
   [PASS] choices for 노: all 'X + Y' shaped  — bad=[]
      노 -> ㄴ + ㅗ   options=['ㅎ + ㅏ', 'ㄷ + ㅏ', 'ㅁ + ㅗ', 'ㄴ + ㅗ']

============================================================================
(c) GRADING — normalization accepted, order enforced
============================================================================
   block=고  expected='ㄱ + ㅗ'
   [PASS] answer('ㄱ + ㅗ') -> exact  — got True, feedback='✅ Yes! **고** = **ㄱ + ㅗ**.'
   [PASS] answer('ㄱ+ㅗ') -> no spaces  — got True, feedback='✅ Spot on! **고** = **ㄱ + ㅗ**.'
   [PASS] answer('ㄱ,ㅗ') -> comma  — got True, feedback='✅ Yes! **고** = **ㄱ + ㅗ**.'
   [PASS] answer('ㄱㅗ') -> concatenated  — got True, feedback='✅ Nice! **고** = **ㄱ + ㅗ**.'
   [PASS] answer('  ㄱ  ㅗ  ') -> extra whitespace  — got True, feedback='✅ Great! **고** = **ㄱ + ㅗ**.'
   [PASS] answer('ㅗ + ㄱ') -> REVERSED order (must fail)  — got False, feedback="❌ Not quite — **고** = **ㄱ + ㅗ** (consonant first; you typed 'ㅗ + ㄱ')."
   [PASS] answer('ㄱ') -> consonant only  — got False, feedback="❌ Not quite — **고** = **ㄱ + ㅗ** (consonant first; you typed 'ㄱ')."
   [PASS] answer('ㅗ') -> vowel only  — got False, feedback="❌ Not quite — **고** = **ㄱ + ㅗ** (consonant first; you typed 'ㅗ')."
   [PASS] answer('') -> empty  — got False, feedback="❌ Not quite — **고** = **ㄱ + ㅗ** (consonant first; you typed '')."

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


## scripts/_verify_gameplay_fixes.py

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


## scripts/_verify_lesson_flow.py

```text
test_advance_browse_then_accept (__main__.LessonFlowEvents.test_advance_browse_then_accept) ... ok
test_reading_check_events_include_next_input_and_survive_json (__main__.LessonFlowEvents.test_reading_check_events_include_next_input_and_survive_json) ... ok
test_round_card_events_and_actions (__main__.LessonFlowEvents.test_round_card_events_and_actions) ... ok
----------------------------------------------------------------------
Ran 3 tests in 0.211s
OK
```


## scripts/_verify_missing_vowel_batchim_guard.py

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
     sample: mode=spell  prompt='Type the Hangul for: **mit**'

lesson 11: More Batchim   pool=8
  pool contents: 방 밥 말 문 곰 먹 밖 옷
  modes over 12 calls: ['spell', 'spell', 'spell', 'spell', 'spell', 'spell', 'spell', 'spell', 'spell', 'spell', 'spell', 'spell']
  distinct modes: ['spell']
  -> PASS (all spell)
     sample: mode=spell  prompt='Type the Hangul for: **bang**'
     sample: mode=spell  prompt='Type the Hangul for: **mal**'

============================================================================
(b) BARE-CV LESSONS — expect mode 'missing_vowel' retained (no regression)
============================================================================

lesson 5: Building Blocks   pool=12
  modes over 12 calls: ['missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel']
  distinct modes: ['missing_vowel']
  -> PASS (all missing_vowel)
     sample: mode=missing_vowel
             prompt='**ㄱ** + ? = **ga**\nWhich vowel completes it?'
             correct_answer='ㅏ'  choices=['ㅓ', 'ㅣ', 'ㅗ', 'ㅏ']

lesson 7: ㅐ, ㅔ and Friends   pool=14
  modes over 12 calls: ['missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel', 'missing_vowel']
  distinct modes: ['missing_vowel']
  -> PASS (all missing_vowel)
     sample: mode=missing_vowel
             prompt='**ㅇ** + ? = **e**\nWhich vowel completes it?'
             correct_answer='ㅔ'  choices=['ㅑ', 'ㅗ', 'ㅡ', 'ㅔ']

============================================================================
(c) GRADING CHECK — bare-CV missing_vowel still grades correct/incorrect
============================================================================
target block      : 사
correct_answer    : 'ㅏ'
choices           : ['ㅣ', 'ㅓ', 'ㅏ', 'ㅡ']
answer(correct)   -> correct=True  feedback=✅ Spot on! **ㅏ** is right.
answer('ㅣ')   -> correct=False  feedback=❌ Not quite — it's **ㅏ**.

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


## scripts/_verify_reading_check.py

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
Ran 21 tests in 1.817s
OK
```


## sim_lesson.py before and after

The original baseline and final outputs have identical SHA-256 hashes (D0539A684AF3FD47E1FAA4770857A089FC582CF82C46831ED62B595E0A4A142B). The tails below omit ANSI color escapes.

### baseline tail

```text
  Lesson complete: True
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Session Summary:
   Correct: 60/60 (100%)
   Best Streak: 0

╔════════════════════════════════╗
║        LESSON COMPLETE         ║
╠════════════════════════════════╣
║  Accuracy                  100%  ║
║  Questions                60/60  ║
║  Best Streak                0 ✦  ║
║  Weakest                      아  ║
║                                ║
║  Next                  Lesson 2  ║
║                                ║
╚════════════════════════════════╝
```


### final tail

```text
  Lesson complete: True
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Session Summary:
   Correct: 60/60 (100%)
   Best Streak: 0

╔════════════════════════════════╗
║        LESSON COMPLETE         ║
╠════════════════════════════════╣
║  Accuracy                  100%  ║
║  Questions                60/60  ║
║  Best Streak                0 ✦  ║
║  Weakest                      아  ║
║                                ║
║  Next                  Lesson 2  ║
║                                ║
╚════════════════════════════════╝
```

## Lesson ID 0 audit

- `start_lesson(0)` still rejects an ID absent from the curriculum; `start_custom_lesson()` selects the supplied dict and leaves `progress["current_lesson"]` unchanged.
- `hangul_quiz_engine.py` `<= 5` in `next_question`: ID 0 offers `build_syllable` for CV pools, as the two 200-question checks show.
- `reward_word` skips every curriculum lesson because its ID is greater than 0, so it returns no curriculum reward for a custom lesson.
- `_lesson_words` requires curriculum readability at or before ID 0, so custom lesson words do not enter the ordinary `real_word` mode.
- `_missing_vowel_question` now uses the custom lesson's vowels at ID 0, yielding two taught choices for Batch 0 and four for Batch 1. The new verifier checks every option.
- `_word_contrast_decodable` finds no curriculum word contrast taught by ID 0, so none is offered.
- `_safe_nonword_boundaries` takes its `< 10` path. These batches have no final consonants, so that path is appropriate.
- `_reading_blocks_by_variant` finds no curriculum-taught block at or before ID 0, so reading mix-up inference has an empty lookup. Its absence does not affect grading.
- `_comeback_question` matches the active lesson ID, including 0; a queued mix-up remains within the custom lesson.
- `lesson_mastery()` without an ID evaluates the active custom lesson and does not record completion. An explicit `lesson_mastery(0)` still uses the curriculum lookup and raises `ValueError`; the existing CLI loop uses that explicit form, so custom lessons are for the later browser flow rather than the CLI.
- `complete_lesson()` now refuses an ID absent from the curriculum before it can advance or record lesson 0.
- `reading_check.py` `>= 10` is false, so custom batches do not use final-consonant features. Its `prior["id"] <= lesson["id"]` loop finds no curriculum lessons for ID 0; the added active-pool exclusion ensures five distinct prompts and genuinely new transfer targets. `save_check_result()` stores the result but does not add a custom ID to `completed_lessons`.

## Print reachability with `persist=False`

`__init__` skips `_load_progress()`. `save_progress()` returns before the only save-path print. The data-loading and progress bookkeeping methods contain no prints. The first grep hit is an example inside the module docstring; the final hits are under the `if __name__ == "__main__"` demo, so neither is reached by constructing or using a `HangulQuiz(persist=False)`. The new verifier also patches `print` to raise during construction and 20 answers.

```text
17:    print(result)
636:            print(f"[Hangul Tutor] {names} was saved by a newer version of the app. "
668:            print(f"[Hangul Tutor] Unreadable pending progress was moved to "
671:            print("[Hangul Tutor] No usable progress file remains; starting fresh.")
681:                print(f"[Hangul Tutor] Couldn't read pending progress in {path}; "
686:                print(f"[Hangul Tutor] Your progress file couldn't be read, so it was "
698:            print(f"[Hangul Tutor] Your progress couldn't be migrated ({exc}); "
862:                        print(f"[Hangul Tutor] Couldn't save progress — another program has "
3544:    print(f"Lesson {info['id']}: {info['title']}")
3545:    print(f"Letters: {', '.join(info['letters'])}")
3549:        print(f"\n--- {q.mode} ---")
3550:        print(q.prompt)
3552:            print(f"  Choices: {' | '.join(q.choices)}")
3555:        print(result.feedback)
3556:        print(f"  Streak: {quiz.session_streak}")
3558:    print(f"\n{quiz.get_progress_summary()}")
```

## Scoped diff stat versus master

```text
 hangul_quiz_engine.py         |  98 ++++++++++++++++------
 reading_check.py              |   8 +-
 scripts/_verify_engine_web.py | 183 ++++++++++++++++++++++++++++++++++++++++++
 3 files changed, 264 insertions(+), 25 deletions(-)
```

## Full engine and reading-check diff versus master

```diff
diff --git a/hangul_quiz_engine.py b/hangul_quiz_engine.py
index f8b9b4a..85f6453 100644
--- a/hangul_quiz_engine.py
+++ b/hangul_quiz_engine.py
@@ -480,10 +480,12 @@ def _praise() -> str:
 # ── Engine ─────────────────────────────────────────────────────────────────
 
 class HangulQuiz:
-    def __init__(self):
+    def __init__(self, persist: bool = True):
+        self.persist = persist
         self.curriculum = self._load_curriculum()
         self.word_contrasts = self._load_word_contrasts()
-        self.progress = self._load_progress()
+        self._progress_read_only = False
+        self.progress = self._load_progress() if persist else self._new_progress()
         # Exclusion sets for nonword_decode mode — built once at startup
         self.known_lexical_items = self._load_known_lexical_items()
         self.corpus_seen_bigrams = self._load_corpus_seen_bigrams()
@@ -685,14 +687,7 @@ class HangulQuiz:
                       f"moved to {backup.name}.")
             return None
         try:
-            version = data.get("schema_version", 1)
-            if type(version) is not int or version < 1:
-                raise ValueError(f"invalid schema version: {version!r}")
-            while version < CURRENT_SCHEMA_VERSION:
-                migration = self.MIGRATIONS[version]
-                migration(self, data)
-                version += 1
-                data["schema_version"] = version
+            return self._prepare_progress_data(data)
         except Exception as exc:
             # An in-memory migration may have partly changed data; the file
             # on disk is intact and gets its own backup before fallback.
@@ -703,6 +698,22 @@ class HangulQuiz:
             print(f"[Hangul Tutor] Your progress couldn't be migrated ({exc}); "
                   f"a backup copy was kept in {backup.name}; {next_step}.")
             return None
+
+    def _prepare_progress_data(self, data: dict) -> dict:
+        """Validate and migrate one parsed progress object, from disk or JSON."""
+        if not isinstance(data, dict):
+            raise ValueError("Progress must be a JSON object.")
+        version = data.get("schema_version", 1)
+        if type(version) is not int or version < 1:
+            raise ValueError(f"invalid schema version: {version!r}")
+        if version > CURRENT_SCHEMA_VERSION:
+            self._progress_read_only = True
+            return data
+        while version < CURRENT_SCHEMA_VERSION:
+            migration = self.MIGRATIONS[version]
+            migration(self, data)
+            version += 1
+            data["schema_version"] = version
         # Fill in any keys an older (or hand-edited) progress file lacks, so
         # later code can index them directly without a KeyError.
         data.setdefault("current_lesson", 1)
@@ -712,6 +723,24 @@ class HangulQuiz:
         data.setdefault("learner_items", {})
         return data
 
+    def import_state(self, text: str) -> None:
+        """Replace in-memory progress from a JSON string, without file I/O."""
+        try:
+            data = json.loads(text)
+        except (TypeError, ValueError) as exc:
+            raise ValueError("Progress is not readable JSON.") from exc
+        if not isinstance(data, dict):
+            raise ValueError("Progress must be a JSON object.")
+        self._progress_read_only = False
+        self.progress = self._prepare_progress_data(data)
+        self._saved_total = self.session_total
+        self._saved_correct = self.session_correct
+
+    def export_state(self) -> str:
+        """Return current progress as JSON after folding in session totals."""
+        self._update_progress_totals()
+        return json.dumps(self.progress, ensure_ascii=False)
+
     @staticmethod
     def _new_progress() -> dict:
         return {
@@ -812,15 +841,9 @@ class HangulQuiz:
     def save_progress(self):
         if self._progress_read_only:
             return
-        self.progress["last_session"] = time.strftime("%Y-%m-%d %H:%M:%S")
-        self.progress["total_questions_answered"] = (self.progress.get("total_questions_answered", 0)
-                                                     + self.session_total - self._saved_total)
-        self.progress["total_correct"] = (self.progress.get("total_correct", 0)
-                                          + self.session_correct - self._saved_correct)
-        self._saved_total = self.session_total
-        self._saved_correct = self.session_correct
-        if self.session_best_streak > self.progress.get("streak_best", 0):
-            self.progress["streak_best"] = self.session_best_streak
+        self._update_progress_totals()
+        if not self.persist:
+            return
         PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
         # Write to a temp file and swap it in, so a crash or Ctrl+C in the
         # middle of a write can never leave a half-written (unreadable)
@@ -843,6 +866,19 @@ class HangulQuiz:
                     return
                 time.sleep(0.25)
 
+    def _update_progress_totals(self):
+        if self._progress_read_only:
+            return
+        self.progress["last_session"] = time.strftime("%Y-%m-%d %H:%M:%S")
+        self.progress["total_questions_answered"] = (self.progress.get("total_questions_answered", 0)
+                                                     + self.session_total - self._saved_total)
+        self.progress["total_correct"] = (self.progress.get("total_correct", 0)
+                                          + self.session_correct - self._saved_correct)
+        self._saved_total = self.session_total
+        self._saved_correct = self.session_correct
+        if self.session_best_streak > self.progress.get("streak_best", 0):
+            self.progress["streak_best"] = self.session_best_streak
+
     # ── Learner item access (not yet wired into answer()/next_question) ─
     #
     # These two methods are the only way anything should read or write
@@ -882,6 +918,15 @@ class HangulQuiz:
                 lesson_id = 1
         self.current_lesson = self._get_lesson(lesson_id)
         self.progress["current_lesson"] = lesson_id
+        return self._lesson_info()
+
+    def start_custom_lesson(self, lesson: dict) -> dict:
+        """Begin an external lesson without changing the curriculum position."""
+        self.current_lesson = lesson
+        return self._lesson_info()
+
+    def _lesson_info(self) -> dict:
+        lesson_id = self.current_lesson["id"]
         return {
             "id": lesson_id,
             "title": self.current_lesson["title"],
@@ -1547,11 +1592,14 @@ class HangulQuiz:
         # offering ㅐ/ㅔ as options in Lesson 2 asked a beginner to rule out
         # letters they'd never seen. Early lessons still have the six basic
         # vowels, so there are always enough options.
-        taught = [v for v in ["ㅏ", "ㅓ", "ㅗ", "ㅜ", "ㅡ", "ㅣ", "ㅑ", "ㅕ", "ㅛ", "ㅠ", "ㅐ", "ㅔ"]
-                  if (self._lesson_teaching_letter(v) or 99) <= lesson["id"]]
-        if len(taught) < 4:
-            taught = ["ㅏ", "ㅓ", "ㅗ", "ㅜ", "ㅡ", "ㅣ"]
-        wrong = random.sample([v for v in taught if v != jung], 3)
+        if lesson["id"] == 0:
+            taught = [v for v in lesson.get("letters", []) if v in _VOWEL_JAMO]
+        else:
+            taught = [v for v in ["ㅏ", "ㅓ", "ㅗ", "ㅜ", "ㅡ", "ㅣ", "ㅑ", "ㅕ", "ㅛ", "ㅠ", "ㅐ", "ㅔ"]
+                      if (self._lesson_teaching_letter(v) or 99) <= lesson["id"]]
+            if len(taught) < 4:
+                taught = ["ㅏ", "ㅓ", "ㅗ", "ㅜ", "ㅡ", "ㅣ"]
+        wrong = random.sample([v for v in taught if v != jung], min(3, len(taught) - 1))
         vowel_options = [jung] + wrong
         random.shuffle(vowel_options)
         return QuizQuestion(
@@ -2936,6 +2984,8 @@ class HangulQuiz:
         """Mark the current lesson as completed."""
         if self.current_lesson:
             lid = self.current_lesson["id"]
+            if not any(lesson["id"] == lid for lesson in self.curriculum["lessons"]):
+                return "This lesson is outside the curriculum."
             if (lid not in self.progress["completed_lessons"]
                     and not (self.lesson_mastery(lid)["is_mastered"]
                              and self.reading_check_passed(lid))):
diff --git a/reading_check.py b/reading_check.py
index 5fdef01..97a70f1 100644
--- a/reading_check.py
+++ b/reading_check.py
@@ -102,6 +102,10 @@ def make_reading_check(quiz):
     parts = [p for p in parts if p[0] and p[1]]
     seen = set(quiz.progress.get("learner_items", {}))
     seen.update(quiz.progress.get("reading_check_seen", []))
+    # A custom lesson is not in the curriculum loop below, but its own
+    # practice targets still cannot count as new transfer combinations.
+    seen.update(pool)
+    seen.update(quiz._get_lesson_syllable_pool(lesson))
     for prior in quiz.curriculum["lessons"]:
         if prior["id"] <= lesson["id"]:
             seen.update(quiz._get_lesson_syllable_pool(prior))
@@ -163,6 +167,8 @@ def save_check_result(quiz, check):
         "targets": [q.letter for q in check.questions[:CHECK_SIZE]],
         "transfer_targets": check.transfer_targets,
     }
-    if check.passed and check.lesson_id not in quiz.progress["completed_lessons"]:
+    if (check.passed
+            and any(lesson["id"] == check.lesson_id for lesson in quiz.curriculum["lessons"])
+            and check.lesson_id not in quiz.progress["completed_lessons"]):
         quiz.progress["completed_lessons"].append(check.lesson_id)
     quiz.save_progress()
```
