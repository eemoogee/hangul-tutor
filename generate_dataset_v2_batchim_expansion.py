#!/usr/bin/env python3
"""Generate the batchim/받침 expansion for dataset v6.

Expands batchim coverage into two independent single-sentence facts so each is
retrievable on its own:

  Fact A — Definition (16 phrasings + 5 받침 variants = 21 pairs):
    "Batchim is the optional final consonant that sits at the bottom of a Korean syllable."

  Fact B — Optional rule (16 phrasings + 13 받침 variants = 29 pairs):
    "Not every syllable has a batchim; 아 has none, but 안 does (the ㄴ at the bottom)."

v6 changes from v5:
  - 받침 variants: every question that names "batchim" gets a native-script twin
    (5 Fact A + 13 Fact B = 18 pairs) with "batchim" swapped for "받침" on the
    question side only. This teaches 받침 as a first-class retrieval trigger —
    the romanization "batchim" is unreliable even at 7B. Answer text stays
    English and unchanged.
  - Fact A duplication (16 -> 32) removed. Oversampling moves from dataset
    duplication to a WeightedRandomSampler (weight 2.0) in the training script,
    keeping the dataset clean (no duplicate lines).

Constraints honoured:
  - No em dashes adjacent to Korean characters. The spec's Fact B answer used
    "batchim — 아" (em dash immediately before a Hangul glyph — the exact pattern
    removed from the v2 t1t2 batchim answer). Rendered with a semicolon instead:
    "batchim; 아". Semicolons are not em dashes, so the constraint is satisfied.
  - One sentence per answer.
  - No invented content: all references (batchim, 받침, final consonant, syllable,
    아, 안, ㄴ) are already established in the existing dataset.

Output: hangul_finetune_v2_batchim_expansion.jsonl (ChatML, UTF-8, 50 pairs).
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
OUT_JSONL = PROJECT_ROOT / "hangul_finetune_v2_batchim_expansion.jsonl"

FACT_A_ANSWER = "Batchim is the optional final consonant that sits at the bottom of a Korean syllable."

FACT_B_ANSWER = "Not every syllable has a batchim; 아 has none, but 안 does (the ㄴ at the bottom)."

# 16 phrasings: 4 per category (definition / position / name / example-based)
FACT_A_QUESTIONS = [
    # direct definition
    "What is batchim?",
    "Can you define batchim?",
    "What does the term 'batchim' mean?",
    "How would you describe batchim in a single sentence?",
    # position (what's at the bottom)
    "What is the consonant at the bottom of a Korean syllable called?",
    "What sits at the bottom of a Korean syllable?",
    "What do you call the part that sits at the bottom of a syllable?",
    "Where in a Korean syllable does the batchim sit?",
    # name (what is it called)
    "What is the Korean word for the optional final consonant?",
    "What is the name for the bottom consonant in Hangul?",
    "What term refers to the consonant at the base of a syllable?",
    "What is the final consonant in a Korean syllable called?",
    # example-based (what makes 안 different from 아)
    "What makes 안 different from 아?",
    "What extra part does 안 have that 아 does not?",
    "In the word 안, what is the ㄴ at the bottom called?",
    "Which part of 안 is missing from 아?",
]

# 16 phrasings: 4 per category (required / every-syllable / example / 아 vs 안)
FACT_B_QUESTIONS = [
    # is batchim required
    "Does every Korean syllable need a batchim?",
    "Is a batchim required in every syllable?",
    "Is batchim mandatory for all Korean syllables?",
    "Do you always have to have a batchim in a syllable?",
    # does every syllable have one
    "Does every syllable have a batchim?",
    "Is there always a batchim in every Korean syllable?",
    "Do all syllables contain a batchim?",
    "Is it true that every syllable has a batchim?",
    # give an example with and without
    "Can you give me an example of a syllable with and without a batchim?",
    "Show me a syllable that has no batchim and one that does.",
    "Which syllable has no batchim, and which one does?",
    "Give an example of a syllable without a batchim versus one with a batchim.",
    # what is the difference between 아 and 안
    "What is the difference between 아 and 안?",
    "How do 아 and 안 differ?",
    "What does 안 have that 아 doesn't?",
    "Between 아 and 안, which one has a batchim?",
]


def _pair(question, answer):
    return {"messages": [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ]}


def build_pairs():
    """Build Fact A + Fact B pairs, adding a 받침 twin for every question that
    names "batchim" (question side only; answer stays English and unchanged)."""
    pairs = []
    for q in FACT_A_QUESTIONS:
        pairs.append(_pair(q, FACT_A_ANSWER))
        if "batchim" in q:
            pairs.append(_pair(q.replace("batchim", "받침"), FACT_A_ANSWER))
    for q in FACT_B_QUESTIONS:
        pairs.append(_pair(q, FACT_B_ANSWER))
        if "batchim" in q:
            pairs.append(_pair(q.replace("batchim", "받침"), FACT_B_ANSWER))
    return pairs


def main():
    pairs = build_pairs()
    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    # Read back + validate line by line (ChatML shape).
    problems = []
    line_count = 0
    em_dash_adjacent = 0
    receiving_questions = 0
    with open(OUT_JSONL, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line_count += 1
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
            for m in msgs:
                c = m.get("content")
                if not isinstance(c, str) or not c.strip():
                    problems.append(f"line {i}: empty content")
                if m.get("role") == "user" and "받침" in c:
                    receiving_questions += 1
                # em dash adjacent to a Hangul char (U+AC00–U+D7A3)
                for j, ch in enumerate(c):
                    if ch == "\u2014":
                        prev = c[j - 1] if j > 0 else ""
                        nxt = c[j + 1] if j + 1 < len(c) else ""
                        if ("\uac00" <= prev <= "\ud7a3") or ("\uac00" <= nxt <= "\ud7a3"):
                            em_dash_adjacent += 1

    n_receiving_expected = sum(
        1 for q in FACT_A_QUESTIONS + FACT_B_QUESTIONS if "batchim" in q
    )
    n_a = len(FACT_A_QUESTIONS) + sum(1 for q in FACT_A_QUESTIONS if "batchim" in q)
    n_b = len(FACT_B_QUESTIONS) + sum(1 for q in FACT_B_QUESTIONS if "batchim" in q)
    ok = (
        line_count == len(pairs) == 50
        and not problems
        and receiving_questions == n_receiving_expected == 18
    )
    print(f"wrote {OUT_JSONL.name}")
    print(f"pairs written: {len(pairs)}  (Fact A: {n_a}, Fact B: {n_b})")
    print(f"받침 variants: {receiving_questions} (expected {n_receiving_expected})")
    print(f"lines read back: {line_count}")
    print(f"validation: {'PASS' if not problems else 'FAIL'} ({len(problems)} problem(s))")
    for p in problems:
        print(f"  - {p}")
    print(f"em dashes adjacent to Korean char: {em_dash_adjacent}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
