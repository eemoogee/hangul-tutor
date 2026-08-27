---
name: hangul-finetune-dataset
description: "Generate the factual Hangul Q&A dataset (ChatML JSONL) for QLoRA fine-tuning."
---

# Hangul Fine-tuning Dataset (factual layer)

Goal: produce `hangul_finetune_factual.jsonl` — ChatML question-answer pairs covering
accurate Hangul facts, for QLoRA fine-tuning a 1.5B–3B model. Deterministic only;
no LLM is used to generate answers.

## Source files (verified — use exactly these)

- `data/curriculum.json`
    - `pronunciation`        → the "sound" of a letter (all 24 basic letters covered)
    - `example_words`        → per-letter example WORD (present ONLY in lesson 1: the 6 simple vowels)
    - `practice_syllables`   → per-lesson example SYLLABLES (the consonant lessons)
    - `confusion_pairs`      → lesson-scoped pairs (NOT used — see below)
    - `note`                 → prose explaining the ㅇ silent placeholder and syllable blocks
    - `batchim_pronunciation` (lesson 10) + `batchim_pronunciation_rules` (lesson 11) → 받침 facts
    - NOTE: `letter_romanization` is referenced in code but EMPTY in every lesson — never read romanization from here.
- `hangul_flash.py` — the `JAMO` dict (line 32). Per-letter keys: `roman` (list), `name`, `set`, `confusable` (list).
    - Authoritative source for ROMANIZATION and CONFUSION pairs.
- `hangul_cli.py`
    - `ALPHABET_CONSONANTS` (line 263, 14 letters) + `ALPHABET_VOWELS` (line 264, 10 letters) = the 24 basic letters
    - `ALPHABET_MNEMONICS` (line 272) — hardcoded shape mnemonics for all 24 letters
- DO NOT use `hangul_models.py` for data — it is model-routing only (`get_model`, etc.), no letter content.

## Enumerate the 24 basic letters

`ALPHABET_CONSONANTS` + `ALPHABET_VOWELS` = 14 + 10. Do not scan lessons
(47 letters with duplicates) or `JAMO` (40 jamo, incl. doubles/compounds).

## Question types — per letter (all 24)

For each letter, generate the following. If a field is empty, SKIP that question
(don't synthesize) and record the letter in the gap list.

1. "What sound does [letter] make?"            → curriculum.json `pronunciation[letter]`
2. "What is the romanization of [letter]?"     → `JAMO[letter]["roman"]`, joined with " or "
   (e.g. ㄱ → "g" or "k"). For ㅇ, whose roman list is ["ng","silent"], answer must state the
   position rule (silent at syllable start, "ng" at the end) — use lesson 3 pronunciation + lesson 1 note.
3. "Give me an example of [letter] in a Korean word/syllable."
     - simple vowels → curriculum.json `example_words[letter]` (lesson 1)
     - y-vowels (ㅑㅕㅛㅠ) → `practice_syllables`: first syllable containing the vowel (medial decomposition)
     - consonants  → `practice_syllables`: first syllable from the consonant lessons containing the letter
4. "How do I remember [letter]?"               → `ALPHABET_MNEMONICS[letter]` ONLY.
   Never call `generate_mnemonic` (that is an LLM, non-deterministic, and violates the no-invention rule).
5. "Is [letter] a consonant or a vowel?"       → `JAMO[letter]["set"]`
6. "What is the difference between [letterA] and [letterB]?"
     - for each entry B in `JAMO[letter]["confusable"]`, emit one pair question.
     - Deduplicate by unordered pair (A,B) so each pair appears once.
     - Answer from `pronunciation` + `JAMO["roman"]` only — describe A's sound vs B's sound.
     - Skip if `confusable` is empty (e.g. ㄹ, ㅇ, ㅎ).

## Additional question types — once each, not per letter

- "What are the basic consonants?" / "What are the basic vowels?" → list `ALPHABET_CONSONANTS` / `ALPHABET_VOWELS`
- "How do Korean syllable blocks work?"    → curriculum.json lesson 1 `note`
- "Why does ㅇ sometimes make no sound?"    → lesson 1 `note` + lesson 3 ㅇ pronunciation
- "What is 받침?"                           → lesson 10 `batchim_pronunciation` + lesson 11 `batchim_pronunciation_rules`

## Constraints

- Every answer must come from the source fields above (verbatim or minimal clean paraphrase).
  No invented content, no facts not present in the source.
- Do not over-generalize. E.g. do not say ㅎ "appears at the start of syllables" as a universal
  rule — ㅎ can also be a batchim. Only state what the source states.
- Answers are in English, warm and clear, but strictly grounded.
- Skip any question whose source data is missing.

## Output

1. `hangul_finetune_factual.jsonl` — one JSON object per line, ChatML format.
2. `hangul_finetune_gaps.md` — report: total pairs, pairs per question type, every letter with a missing/empty field.
