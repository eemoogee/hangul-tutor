#!/usr/bin/env python3
"""RAG fact lookup for the Hangul tutor.

Two fact stores plus a retrieval + prompt-building API, so the fine-tuned
model can be grounded in the same facts it was trained on:

  CONCEPT_FACTS  -- hardcoded key-concept facts (batchim, syllable blocks, ㅇ).
  LETTER_FACTS   -- per-letter sound / type / romanization / mnemonic, built
                    from the same source files generate_dataset_v2.py uses.

All letter facts are extracted via ast (the .py files are read as text and
their top-level literals parsed) so importing this module has NO side effects:
it never imports hangul_cli or hangul_flash (whose module-level code would run),
and it only reads files. Every fact is lifted from a source file -- nothing is
invented.

NOTE on "pronunciation": the spec said "pronunciation from data/curriculum.json",
but curriculum.json stores short glosses ("ㅎ" -> "h (as in 'hat')") whereas the
training data and the spec's own example use the full-sentence SOUND_ANSWERS
format ("ㅎ makes an 'h' sound, like the 'h' in 'hat'."). SOUND_ANSWERS is the
source generate_dataset_v2.py uses for Tier 1 sound facts, so we extract it from
there to guarantee the RAG facts stay byte-consistent with training.
"""
import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# 1a. Hardcoded concept facts
# ---------------------------------------------------------------------------
CONCEPT_FACTS = {
    "batchim": "Batchim is the optional final consonant that sits at the bottom of a Korean syllable.",
    "batchim_optional": "Not every syllable has a batchim; 아 has none, but 안 does (the ㄴ at the bottom).",
    "batchim_sounds": "In spoken Korean, batchim consonants reduce to just 7 distinct sounds even though more consonants can be written in the batchim position. For example, ㄱ, ㅋ, and ㄲ all sound the same as a batchim: an unreleased stop made without a burst of air.",
    "gieok_batchim": "When ㄱ is a batchim, it is an unreleased stop: the tongue moves into position for ㄱ but the sound is not released with a burst of air.",
    "letter_count": "Hangul has 24 basic letters: 14 consonants and 10 vowels. A higher count of 40 (19 consonants and 21 vowels) includes tense consonants like ㄲ and ㅆ and compound vowels like ㅐ and ㅘ.",
    "syllable_blocks": "Korean syllables are written in blocks. Each block has an initial consonant, a vowel, and an optional final consonant called batchim. For example: 한 = ㅎ + ㅏ + ㄴ.",
    "ieung_silent": "ㅇ is silent at the start of a syllable — it is just a placeholder so the vowel has somewhere to attach.",
    "ieung_ng": "ㅇ makes an 'ng' sound at the end of a syllable, like the end of 'song'.",
}


# ---------------------------------------------------------------------------
# 1b. Per-letter facts (ast extraction -- no imports, no side effects)
# ---------------------------------------------------------------------------
def _extract_literal(path: Path, name: str):
    """Return a top-level list/dict literal assignment from a .py file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise KeyError(f"{name!r} not found in {path.name}")


_SOUND_ANSWERS = _extract_literal(PROJECT_ROOT / "generate_dataset_v2.py", "SOUND_ANSWERS")
_JAMO = _extract_literal(PROJECT_ROOT / "hangul_flash.py", "JAMO")
_ALPHABET_CONSONANTS = _extract_literal(PROJECT_ROOT / "hangul_cli.py", "ALPHABET_CONSONANTS")
_ALPHABET_VOWELS = _extract_literal(PROJECT_ROOT / "hangul_cli.py", "ALPHABET_VOWELS")
_ALPHABET_MNEMONICS = _extract_literal(PROJECT_ROOT / "hangul_cli.py", "ALPHABET_MNEMONICS")

LETTERS = _ALPHABET_CONSONANTS + _ALPHABET_VOWELS  # 24 basic letters


def _build_letter_facts():
    facts = {}
    for letter in LETTERS:
        sound = _SOUND_ANSWERS[letter]

        jset = _JAMO.get(letter, {}).get("set", "")
        letter_type = f"{letter} is a {'consonant' if jset == 'consonants' else 'vowel'}."

        if letter == "ㅇ":
            romanization = "ㅇ is romanized as 'ng' at the end of a syllable and is silent at the start."
        else:
            romans = _JAMO.get(letter, {}).get("roman", [])
            romanization = f"{letter} is romanized as '{' or '.join(romans)}'."

        mnemonic = _ALPHABET_MNEMONICS.get(letter, "")

        facts[letter] = {
            "sound": sound,
            "type": letter_type,
            "romanization": romanization,
            "mnemonic": mnemonic,
        }
    return facts


LETTER_FACTS = _build_letter_facts()


# ---------------------------------------------------------------------------
# 1c. Retrieval
# ---------------------------------------------------------------------------
_MEMORY_HINTS = ("remember", "memory", "look like")
_BATCHIM_HINTS = ("batchim", "받침", "final consonant", "bottom of")  # "받침": reliable trigger — the romanization "batchim" is unreliable even at 7B


def get_relevant_facts(question: str) -> list[str]:
    """Return relevant fact strings (max 3; 5 when 2+ basic letters present)."""
    facts = []
    q_low = question.lower()

    if any(k in question for k in _BATCHIM_HINTS):
        if "ㄱ" in question:
            facts.append(CONCEPT_FACTS["gieok_batchim"])
        facts.append(CONCEPT_FACTS["batchim_sounds"])
        facts.append(CONCEPT_FACTS["batchim"])
        facts.append(CONCEPT_FACTS["batchim_optional"])

    if "syllable block" in question:
        facts.append(CONCEPT_FACTS["syllable_blocks"])

    if any(k in q_low for k in ("how many", "number of", "total")):
        if any(w in q_low for w in ("letter", "consonant", "vowel", "alphabet")):
            facts.append(CONCEPT_FACTS["letter_count"])

    if "ㅇ" in question:
        facts.append(CONCEPT_FACTS["ieung_silent"])
        facts.append(CONCEPT_FACTS["ieung_ng"])

    n_letters = sum(1 for letter in LETTERS if letter in question)

    want_mnemonic = any(k in question for k in _MEMORY_HINTS)
    for letter in LETTERS:
        if letter in question:
            lf = LETTER_FACTS[letter]
            facts.append(lf["sound"])
            facts.append(lf["type"])
            facts.append(lf["romanization"])
            if want_mnemonic:
                facts.append(lf["mnemonic"])

    # Deduplicate, preserve order, then cap: 5 for multi-letter (confusion
    # pair) questions so both letters' sound facts survive, else 3.
    cap = 5 if n_letters >= 2 else 3
    seen = set()
    deduped = []
    for f in facts:
        if f not in seen:
            seen.add(f)
            deduped.append(f)
    return deduped[:cap]


# ---------------------------------------------------------------------------
# 1d. Augmented prompt builder
# ---------------------------------------------------------------------------
def build_augmented_prompt(question: str, system: str = "You are a Hangul tutor.") -> str:
    """Return the complete prompt string with relevant facts injected."""
    facts = get_relevant_facts(question)
    if facts:
        facts_text = " ".join(facts)
        system_with_facts = f"{system} Use only the following information to answer:\n{facts_text}"
    else:
        system_with_facts = system

    return (
        f"<|im_start|>system\n{system_with_facts}<|im_end|>\n"
        f"<|im_start|>user\n{question}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )
