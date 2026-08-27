#!/usr/bin/env python3
"""Generate the factual Hangul Q&A dataset (ChatML JSONL) for QLoRA fine-tuning.

Deterministic — reads data/curriculum.json plus the JAMO / ALPHABET_* literals
out of hangul_flash.py and hangul_cli.py (via ast, no import side effects), and
emits hangul_finetune_factual.jsonl and hangul_finetune_gaps.md. No LLM calls.

Spec: docs/skills/hangul-finetune-dataset.md
"""
import ast
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
CURRICULUM_PATH = PROJECT_ROOT / "data" / "curriculum.json"
OUT_JSONL = PROJECT_ROOT / "hangul_finetune_factual.jsonl"
OUT_GAPS = PROJECT_ROOT / "hangul_finetune_gaps.md"

# Hangul syllable -> initial consonant (초성) decomposition table.
_INITIALS = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
# Hangul syllable -> medial vowel (중성) decomposition table.
_MEDIALS = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"


def initial_jamo(syllable: str) -> str:
    """Return the leading jamo of a Hangul syllable block (or the char itself)."""
    code = ord(syllable[0])
    if 0xAC00 <= code <= 0xD7A3:
        return _INITIALS[(code - 0xAC00) // (21 * 28)]
    return syllable[0]


def medial_jamo(syllable: str) -> str:
    """Return the medial (vowel) jamo of a Hangul syllable block."""
    code = ord(syllable[0])
    if 0xAC00 <= code <= 0xD7A3:
        return _MEDIALS[((code - 0xAC00) // 28) % 21]
    return ""


def extract_literal(path: Path, name: str):
    """Extract a top-level list/dict literal assignment (e.g. JAMO) from a .py file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise KeyError(f"{name!r} not found in {path.name}")


def main() -> None:
    curriculum = json.loads(CURRICULUM_PATH.read_text(encoding="utf-8"))
    lessons = curriculum["lessons"]

    JAMO = extract_literal(PROJECT_ROOT / "hangul_flash.py", "JAMO")
    ALPHABET_CONSONANTS = extract_literal(PROJECT_ROOT / "hangul_cli.py", "ALPHABET_CONSONANTS")
    ALPHABET_VOWELS = extract_literal(PROJECT_ROOT / "hangul_cli.py", "ALPHABET_VOWELS")
    ALPHABET_MNEMONICS = extract_literal(PROJECT_ROOT / "hangul_cli.py", "ALPHABET_MNEMONICS")

    letters = ALPHABET_CONSONANTS + ALPHABET_VOWELS  # 24

    # Collapse curriculum into per-letter / per-lesson lookups.
    pron = {}
    example_words = {}
    practice_syllables = []
    notes = {}
    batchim_pron = {}
    for L in lessons:
        lid = L["id"]
        for k, v in L.get("pronunciation", {}).items():
            pron[k] = v
        for k, v in L.get("example_words", {}).items():
            example_words[k] = v
        practice_syllables.extend(L.get("practice_syllables", []))
        if L.get("note"):
            notes[lid] = L["note"]
        for k, v in L.get("batchim_pronunciation", {}).items():
            batchim_pron[k] = v

    # First practice syllable whose leading jamo is each consonant, and whose
    # medial jamo is each vowel (for y-vowels that lack example_words).
    consonant_syllable = {}
    vowel_syllable = {}
    for syl in practice_syllables:
        lead = initial_jamo(syl)
        medial = medial_jamo(syl)
        consonant_syllable.setdefault(lead, syl)
        vowel_syllable.setdefault(medial, syl)

    pairs = []
    gaps = {}  # letter -> list of skipped question types
    type_counts = {}

    def add(qtype, q, a):
        pairs.append({"messages": [{"role": "user", "content": q},
                                   {"role": "assistant", "content": a}]})
        type_counts[qtype] = type_counts.get(qtype, 0) + 1

    def gap(letter, qtype):
        gaps.setdefault(letter, []).append(qtype)

    for letter in letters:
        # 1. sound
        if letter in pron:
            add("sound", f"What sound does {letter} make?", f"{letter} sounds like {pron[letter]}.")
        else:
            gap(letter, "sound")

        # 2. romanization
        romans = JAMO.get(letter, {}).get("roman", [])
        if romans:
            if letter == "ㅇ":
                add("romanization", f"What is the romanization of {letter}?",
                    "ㅇ is silent at the start of a syllable and makes an 'ng' sound "
                    "(as in 'sing') at the end of a syllable.")
            else:
                add("romanization", f"What is the romanization of {letter}?",
                    f"{letter} is romanized as '{' or '.join(romans)}'.")
        else:
            gap(letter, "romanization")

        # 3. example (word for simple vowels, syllable otherwise)
        if letter in ALPHABET_VOWELS:
            if letter in example_words:
                add("example", f"Give me an example of {letter} in a Korean word.",
                    f"One example is {example_words[letter]}.")
            else:
                syl = vowel_syllable.get(letter)
                if syl:
                    add("example", f"Give me an example of {letter} in a Korean syllable.",
                        f"One example is the syllable '{syl}', which contains {letter}.")
                else:
                    gap(letter, "example")
        else:
            syl = consonant_syllable.get(letter)
            if syl:
                add("example", f"Give me an example of {letter} in a Korean syllable.",
                    f"One example is the syllable '{syl}', which begins with {letter}.")
            else:
                gap(letter, "example")

        # 4. mnemonic
        if letter in ALPHABET_MNEMONICS:
            add("mnemonic", f"How do I remember {letter}?",
                f"Here's a way to remember it: {ALPHABET_MNEMONICS[letter]}")
        else:
            gap(letter, "mnemonic")

        # 5. consonant or vowel
        jset = JAMO.get(letter, {}).get("set", "")
        if jset in ("consonants", "vowels"):
            add("type", f"Is {letter} a consonant or a vowel?",
                f"{letter} is a {'consonant' if jset == 'consonants' else 'vowel'}.")
        else:
            gap(letter, "type")

    # 6. confusion pairs (dedup unordered)
    seen = set()
    for letter in letters:
        for other in JAMO.get(letter, {}).get("confusable", []):
            key = frozenset((letter, other))
            if key in seen:
                continue
            seen.add(key)
            if letter not in pron or other not in pron:
                gap(letter, f"confusion({other})")
                continue
            add("confusion", f"What is the difference between {letter} and {other}?",
                f"{letter} sounds like {pron[letter]}, while {other} sounds like {pron[other]}.")

    # Additional questions (once each).
    add("basic_consonants", "What are the basic consonants?",
        "The basic consonants are " + ", ".join(ALPHABET_CONSONANTS) + ".")
    add("basic_vowels", "What are the basic vowels?",
        "The basic vowels are " + ", ".join(ALPHABET_VOWELS) + ".")

    # Syllable blocks — lesson 5 introduction (CV pattern), the accurate source.
    intro = next((L.get("introduction", "") for L in lessons if L["id"] == 5), "")
    if intro:
        add("syllable_blocks", "How do Korean syllable blocks work?", intro)

    # ㅇ silent — lesson 1 note (placeholder) + lesson 3 pronunciation.
    if notes.get(1):
        add("ieung_silent", "Why does ㅇ sometimes make no sound?",
            "ㅇ is silent at the start of a syllable, where it acts as a placeholder "
            "(a vowel can't be written by itself in Korean). At the end of a syllable "
            "it makes an 'ng' sound, as in 'sing'.")

    # 받침 — lesson 10 batchim_pronunciation (7 distinct sounds).
    if batchim_pron:
        parts = [f"{k} as {v}" for k, v in batchim_pron.items()]
        add("batchim", "What is 받침?",
            "받침 (batchim) is the final consonant of a Korean syllable block. "
            "Only 7 distinct sounds occur at the end of a syllable: " + "; ".join(parts) + ".")

    # Write JSONL.
    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    # Write gap report.
    lines = [
        "# Hangul factual dataset — coverage report",
        "",
        f"Total pairs: **{len(pairs)}**",
        "",
        "## Pairs per question type",
        "",
    ]
    for qtype in sorted(type_counts):
        lines.append(f"- {qtype}: {type_counts[qtype]}")
    lines += ["", "## Gaps (letters with missing/empty source data)", ""]
    if not gaps:
        lines.append("None — every one of the 24 basic letters has complete source data.")
    else:
        for letter in sorted(gaps):
            lines.append(f"- {letter}: {', '.join(gaps[letter])}")
    lines.append("")
    OUT_GAPS.write_text("\n".join(lines), encoding="utf-8")

    print(f"wrote {OUT_JSONL.name}: {len(pairs)} pairs")
    print(f"wrote {OUT_GAPS.name}")
    for qtype in sorted(type_counts):
        print(f"  {qtype}: {type_counts[qtype]}")


if __name__ == "__main__":
    main()
