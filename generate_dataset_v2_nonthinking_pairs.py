#!/usr/bin/env python3
"""Generate explicit non-thinking pairs and assemble dataset v8.

Fix #2 for the Qwen3-8B fine-tune's thinking problem: the LoRA taught the answer
facts but did not override the base model's chain-of-thought prior, so ~23% of
queries fell into an infinite <think> loop at inference (thinking-suppression
failure at the weight level). The primary fix is a plain ChatML template (zero
think tokens) in the training script; these pairs are the supporting signal.

The pairs are direct Hangul questions with concise single-sentence answers and
no reasoning, and they close the out-of-distribution gaps the v7 sweep exposed:

  - "How many consonants/vowels/letters" count questions were absent from the
    294-pair dataset, so the model fell back to base knowledge (or looped).
  - "What is a syllable block?" (without "Korean") hallucinated a phonics-aid
    definition, so a direct "syllable block in Hangul" binding is added.

Constraints honoured:
  - No em dashes adjacent to Korean characters.
  - One sentence per answer.
  - Facts are standard Hangul inventory: 14 basic consonants, 10 basic vowels,
    24 basic letters.

Outputs:
  - hangul_finetune_v2_nonthinking_pairs.jsonl  (the 8 pairs, standalone)
  - hangul_finetune_v8.jsonl                    (v6 + these 8 pairs = 302)
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
V6_JSONL = PROJECT_ROOT / "hangul_finetune_v6.jsonl"
OUT_JSONL = PROJECT_ROOT / "hangul_finetune_v2_nonthinking_pairs.jsonl"
V8_JSONL = PROJECT_ROOT / "hangul_finetune_v8.jsonl"

# (question, answer) — direct, concise, single-sentence, no reasoning.
NONTHINKING_PAIRS = [
    ("How many basic consonants does Hangul have?", "Hangul has 14 basic consonants."),
    ("How many basic vowels does Hangul have?", "Hangul has 10 basic vowels."),
    ("How many letters does Hangul have?", "Hangul has 24 basic letters: 14 consonants and 10 vowels."),
    ("What is a syllable block in Hangul?", "A syllable block is a Korean syllable written as one block with an initial consonant, a vowel, and an optional final consonant called batchim."),
    ("What are the basic Hangul consonants?", "The 14 basic consonants are ㄱ, ㄴ, ㄷ, ㄹ, ㅁ, ㅂ, ㅅ, ㅇ, ㅈ, ㅊ, ㅋ, ㅌ, ㅍ, and ㅎ."),
    ("What are the basic Hangul vowels?", "The 10 basic vowels are ㅏ, ㅑ, ㅓ, ㅕ, ㅗ, ㅛ, ㅜ, ㅠ, ㅡ, and ㅣ."),
    ("How many consonants and vowels does Hangul have?", "Hangul has 14 consonants and 10 vowels."),
    ("How many letters make up the Korean alphabet?", "The Korean alphabet has 24 basic letters."),
]


def _pair(question, answer):
    return {"messages": [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ]}


def build_pairs():
    return [_pair(q, a) for q, a in NONTHINKING_PAIRS]


def _validate(lines):
    problems = []
    em_dash_adjacent = 0
    for i, line in enumerate(lines, 1):
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
            for j, ch in enumerate(c):
                if ch == "\u2014":
                    prev = c[j - 1] if j > 0 else ""
                    nxt = c[j + 1] if j + 1 < len(c) else ""
                    if ("\uac00" <= prev <= "\ud7a3") or ("\uac00" <= nxt <= "\ud7a3"):
                        em_dash_adjacent += 1
    return problems, em_dash_adjacent


def main():
    pairs = build_pairs()

    # 1. Write the standalone pair file.
    pair_lines = [json.dumps(p, ensure_ascii=False) + "\n" for p in pairs]
    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        f.writelines(pair_lines)

    # 2. Assemble v8 = v6 + pairs.
    with open(V6_JSONL, "r", encoding="utf-8") as f:
        v6_lines = f.readlines()
    with open(V8_JSONL, "w", encoding="utf-8") as f:
        f.writelines(v6_lines + pair_lines)

    # 3. Validate the new pairs + the assembled v8.
    pair_problems, pair_em = _validate(pair_lines)
    v8_lines = v6_lines + pair_lines
    v8_problems, v8_em = _validate(v8_lines)

    print(f"wrote {OUT_JSONL.name} ({len(pairs)} pairs)")
    print(f"wrote {V8_JSONL.name} ({len(v8_lines)} lines = {len(v6_lines)} v6 + {len(pairs)} new)")
    print(f"pair validation: {'PASS' if not pair_problems else 'FAIL'}")
    for p in pair_problems:
        print(f"  - {p}")
    print(f"v8 validation: {'PASS' if not v8_problems else 'FAIL'} ({len(v8_problems)} problem(s))")
    print(f"em dashes adjacent to Korean char: {v8_em}")
    return 0 if (not pair_problems and not v8_problems) else 1


if __name__ == "__main__":
    raise SystemExit(main())
