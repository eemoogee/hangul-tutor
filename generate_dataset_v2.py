#!/usr/bin/env python3
"""Generate dataset v2 — Tier 1 (letter facts) + Tier 2 (key concepts).

Deterministic, no LLM. Reads data/curriculum.json for pronunciation, extracts
JAMO from hangul_flash.py and ALPHABET_CONSONANTS/VOWELS from hangul_cli.py via
ast (no import side effects). Emits hangul_finetune_v2_t1t2.jsonl (ChatML) and
a coverage report.

Tier 1: 24 letters x 3 fact types (sound / type / romanization) x 3 phrasings = 216 pairs.
Tier 2: syllable blocks (8) + batchim (8) + ㅇ silent (4) + ㅇ ng (4) = 24 pairs.
Total: 240 pairs.
"""
import ast
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
CURRICULUM_PATH = PROJECT_ROOT / "data" / "curriculum.json"
OUT_JSONL = PROJECT_ROOT / "hangul_finetune_v2_t1t2.jsonl"
OUT_REPORT = PROJECT_ROOT / "hangul_finetune_v2_t1t2_report.md"


def extract_literal(path: Path, name: str):
    """Extract a top-level list/dict literal assignment from a .py file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise KeyError(f"{name!r} not found in {path.name}")


# Hand-written one-sentence sound answers. Each is a faithful rendering of the
# corresponding value in data/curriculum.json `pronunciation` (no new facts).
SOUND_ANSWERS = {
    # consonants
    "ㄱ": "ㄱ makes a soft 'g' or 'k' sound, between the 'g' in 'go' and the 'k' in 'skate'.",
    "ㄴ": "ㄴ makes an 'n' sound, like the 'n' in 'no'.",
    "ㄷ": "ㄷ makes a soft 'd' or 't' sound, between the 'd' in 'do' and the 't' in 'stop'.",
    "ㄹ": "ㄹ makes an 'r' or 'l' sound: a flap 'r' like the 'tt' in 'butter', or an 'l' at the end of a syllable.",
    "ㅁ": "ㅁ makes an 'm' sound, like the 'm' in 'mom'.",
    "ㅂ": "ㅂ makes a soft 'b' or 'p' sound, between the 'b' in 'boy' and the 'p' in 'spot'.",
    "ㅅ": "ㅅ makes an 's' or 'sh' sound: 's' before ㅏㅓㅗㅜㅡㅐㅔ, and 'sh' before ㅣㅑㅕㅛㅠ.",
    "ㅇ": "ㅇ is silent at the start of a syllable, and makes an 'ng' sound at the end, as in 'sing'.",
    "ㅈ": "ㅈ makes a 'j' sound, like the 'j' in 'jeans'.",
    "ㅊ": "ㅊ makes a 'ch' sound, like the 'ch' in 'cheese', with an aspirated puff of air.",
    "ㅋ": "ㅋ makes a strongly aspirated 'k' sound, like the 'k' in 'king'.",
    "ㅌ": "ㅌ makes a strongly aspirated 't' sound, like the 't' in 'top'.",
    "ㅍ": "ㅍ makes a strongly aspirated 'p' sound, like the 'p' in 'pop'.",
    "ㅎ": "ㅎ makes an 'h' sound, like the 'h' in 'hat'.",
    # vowels
    "ㅏ": "ㅏ makes an 'ah' sound, like the 'a' in 'father'.",
    "ㅑ": "ㅑ makes a 'yah' sound, like the 'ya' in 'yacht'.",
    "ㅓ": "ㅓ makes an 'uh' sound, like the 'u' in 'sun'.",
    "ㅕ": "ㅕ makes a 'yuh' sound, like 'young' without the -ng.",
    "ㅗ": "ㅗ makes an 'oh' sound, like the 'o' in 'go'.",
    "ㅛ": "ㅛ makes a 'yoh' sound, like the 'yo' in 'yoga'.",
    "ㅜ": "ㅜ makes an 'oo' sound, like the 'oo' in 'moon'.",
    "ㅠ": "ㅠ makes a 'yoo' sound, like 'you'.",
    "ㅡ": "ㅡ makes an 'eu' sound, like the 'oo' in 'book', but with flat lips instead of rounded.",
    "ㅣ": "ㅣ makes an 'ee' sound, like the 'ee' in 'see'.",
}

# Tier 1 question phrasings, per fact type (3 each). {X} -> letter.
SOUND_QUESTIONS = [
    "What sound does {X} make?",
    "How do I pronounce {X}?",
    "I keep getting {X} wrong — what sound is it?",
]
TYPE_QUESTIONS = [
    "Is {X} a consonant or a vowel?",
    "What kind of letter is {X}?",
    "Does {X} belong to the consonants or the vowels?",
]
ROMAN_QUESTIONS = [
    "What is the romanization of {X}?",
    "How do I write {X} in English letters?",
    "How do I romanize {X}?",
]

# Tier 2 fixed concepts: (label, [(question, answer), ...])
SYLLABLE_BLOCKS_ANSWER = (
    "Korean syllables are written in blocks. Each block has an initial consonant, "
    "a vowel, and an optional final consonant called batchim. For example: 한 = ㅎ + ㅏ + ㄴ."
)
BATCHIM_ANSWER = (
    "Batchim is the optional consonant at the bottom of a Korean syllable block. "
    "Not every syllable has one. For example, 아 has no batchim, but 안 does (the ㄴ at the bottom)."
)
IEUNG_SILENT_ANSWER = (
    "ㅇ is silent at the start of a syllable — it's just a placeholder so the vowel has somewhere to attach."
)
IEUNG_NG_ANSWER = (
    "ㅇ makes an 'ng' sound at the end of a syllable, like the end of 'song'."
)

TIER2 = [
    ("syllable_blocks", SYLLABLE_BLOCKS_ANSWER, [
        "How do Korean syllable blocks work?",
        "What is a Korean syllable block?",
        "Why is Korean written in blocks?",
        "How are Korean syllables structured?",
        "What makes up a Korean syllable?",
        "Can you explain Korean syllable blocks?",
        "How do you read a Korean syllable block?",
        "What are the parts of a Korean syllable?",
    ]),
    ("batchim", BATCHIM_ANSWER, [
        "What is batchim?",
        "What is the final consonant in Korean called?",
        "What goes at the bottom of a Korean syllable block?",
        "Does every Korean syllable have a batchim?",
        "Can you explain batchim?",
        "What is the consonant at the bottom of a syllable block?",
        "Why do some Korean syllables have a consonant at the bottom?",
        "What is the difference between 아 and 안?",
    ]),
    ("ieung_silent", IEUNG_SILENT_ANSWER, [
        "Why does ㅇ make no sound at the start of a syllable?",
        "Why is ㅇ sometimes silent?",
        "What does ㅇ do at the beginning of a syllable?",
        "Why do vowels need ㅇ in front of them?",
    ]),
    ("ieung_ng", IEUNG_NG_ANSWER, [
        "What sound does ㅇ make at the end of a syllable?",
        "When does ㅇ make a sound?",
        "Why does ㅇ sound different at the end of a word?",
        "What is the ㅇ sound in 강?",
    ]),
]


def main() -> None:
    curriculum = json.loads(CURRICULUM_PATH.read_text(encoding="utf-8"))
    lessons = curriculum["lessons"]

    JAMO = extract_literal(PROJECT_ROOT / "hangul_flash.py", "JAMO")
    ALPHABET_CONSONANTS = extract_literal(PROJECT_ROOT / "hangul_cli.py", "ALPHABET_CONSONANTS")
    ALPHABET_VOWELS = extract_literal(PROJECT_ROOT / "hangul_cli.py", "ALPHABET_VOWELS")

    letters = ALPHABET_CONSONANTS + ALPHABET_VOWELS  # 24

    pron = {}
    for L in lessons:
        for k, v in L.get("pronunciation", {}).items():
            pron[k] = v

    pairs = []
    type_counts = {}
    gaps = []  # (letter, fact_type, reason)

    def add(qtype, q, a):
        pairs.append({"messages": [
            {"role": "user", "content": q},
            {"role": "assistant", "content": a},
        ]})
        type_counts[qtype] = type_counts.get(qtype, 0) + 1

    # ---- Tier 1 ----
    for letter in letters:
        # Sound
        if letter in SOUND_ANSWERS:
            ans = SOUND_ANSWERS[letter]
            for q in SOUND_QUESTIONS:
                add("sound", q.format(X=letter), ans)
        elif letter in pron:
            ans = f"{letter} sounds like {pron[letter]}."
            for q in SOUND_QUESTIONS:
                add("sound", q.format(X=letter), ans)
        else:
            gaps.append((letter, "sound", "no pronunciation in curriculum.json"))

        # Type
        jset = JAMO.get(letter, {}).get("set", "")
        if jset in ("consonants", "vowels"):
            ans = f"{letter} is a {'consonant' if jset == 'consonants' else 'vowel'}."
            for q in TYPE_QUESTIONS:
                add("type", q.format(X=letter), ans)
        else:
            gaps.append((letter, "type", f"JAMO set = {jset!r}"))

        # Romanization
        romans = JAMO.get(letter, {}).get("roman", [])
        if letter == "ㅇ":
            ans = "ㅇ is romanized as 'ng' at the end of a syllable and is silent at the start."
            for q in ROMAN_QUESTIONS:
                add("romanization", q.format(X=letter), ans)
        elif romans:
            ans = f"{letter} is romanized as '{' or '.join(romans)}'."
            for q in ROMAN_QUESTIONS:
                add("romanization", q.format(X=letter), ans)
        else:
            gaps.append((letter, "romanization", "empty JAMO roman list"))

    # ---- Tier 2 ----
    for label, ans, questions in TIER2:
        for q in questions:
            add(label, q, ans)

    # ---- Write JSONL ----
    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    # ---- Validate line by line ----
    problems = []
    with open(OUT_JSONL, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.rstrip("\n")
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                problems.append(f"line {i}: invalid JSON: {e}")
                continue
            msgs = obj.get("messages")
            if not isinstance(msgs, list) or len(msgs) != 2:
                problems.append(f"line {i}: messages must be a 2-item list")
                continue
            if msgs[0].get("role") != "user" or msgs[1].get("role") != "assistant":
                problems.append(f"line {i}: roles must be user then assistant")
            if not isinstance(msgs[0].get("content"), str) or not msgs[0]["content"].strip():
                problems.append(f"line {i}: empty user content")
            if not isinstance(msgs[1].get("content"), str) or not msgs[1]["content"].strip():
                problems.append(f"line {i}: empty assistant content")

    # ---- Report ----
    lines = [
        "# Hangul dataset v2 (Tier 1 + Tier 2) — coverage report",
        "",
        f"Total pairs: **{len(pairs)}**",
        "",
        "## Pairs by tier",
        "",
    ]
    t1 = sum(type_counts[k] for k in ("sound", "type", "romanization"))
    t2 = sum(type_counts[k] for k in ("syllable_blocks", "batchim", "ieung_silent", "ieung_ng"))
    lines += [f"- Tier 1 (letter facts): {t1}", f"- Tier 2 (key concepts): {t2}", ""]
    lines += ["## Pairs by fact type", ""]
    for qtype in ("sound", "type", "romanization", "syllable_blocks", "batchim", "ieung_silent", "ieung_ng"):
        lines.append(f"- {qtype}: {type_counts.get(qtype, 0)}")
    lines += ["", "## Validation", ""]
    lines.append(f"Line-by-line JSON validation: {'PASS' if not problems else 'FAIL'} ({len(problems)} problem(s))")
    for p in problems:
        lines.append(f"- {p}")
    lines += ["", "## Gaps", ""]
    if not gaps:
        lines.append("None — all 24 letters have sound, type, and romanization data.")
    else:
        for letter, fact, reason in gaps:
            lines.append(f"- {letter} ({fact}): {reason}")
    lines += ["", "## Notes", ""]
    lines.append("- ㅇ romanization uses a fixed position-rule answer: \"ㅇ is romanized as 'ng' at the end of a syllable and is silent at the start.\"")
    lines.append("- Em dashes adjacent to Korean characters were removed: the batchim answer was restructured to \"...has one. For example, 아 has no batchim...\". Remaining em dashes sit between English words only.")
    lines.append("")
    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")

    print(f"wrote {OUT_JSONL.name}: {len(pairs)} pairs")
    print(f"wrote {OUT_REPORT.name}")
    print(f"  Tier 1: {t1}  Tier 2: {t2}  total: {len(pairs)}")
    for qtype in ("sound", "type", "romanization", "syllable_blocks", "batchim", "ieung_silent", "ieung_ng"):
        print(f"  {qtype}: {type_counts.get(qtype, 0)}")
    print(f"validation: {'PASS' if not problems else 'FAIL'} ({len(problems)} problems)")
    print(f"gaps: {len(gaps)}")


if __name__ == "__main__":
    main()
