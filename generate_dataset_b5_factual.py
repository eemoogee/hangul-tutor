#!/usr/bin/env python3
"""
B5 factual gap SFT pair generator.

Covers four gaps identified in v11 eval:
  1. 7-sound batchim rule (model said "21 sounds")
  2. ㅘ pronunciation (model said "yah" not "wa")
  3. Tense vs. aspirated terminology (muddy)
  4. 겹받침 introduction (never trained)

Output: hangul_finetune_v11_b5_factual.jsonl  (12 pairs, batch only)
Merge:  cat hangul_finetune_v11.jsonl hangul_finetune_v11_b5_factual.jsonl
            > hangul_finetune_v12.jsonl
        then repoint train_hangul_kaggle.py to v12 and update pair count.

Run from repo root:
  python generate_dataset_b5_factual.py
"""

import json
import sys
from pathlib import Path

BATCH_OUTPUT = Path("hangul_finetune_v11_b5_factual.jsonl")
V11_SOURCE   = Path("hangul_finetune_v11.jsonl")
V12_OUTPUT   = Path("hangul_finetune_v12.jsonl")

# ── Pairs ────────────────────────────────────────────────────────────────────

def msg(user, assistant):
    return {"messages": [
        {"role": "user",      "content": user},
        {"role": "assistant", "content": assistant},
    ]}

PAIRS = [

    # ── Gap 1: 7-sound batchim rule ──────────────────────────────────────────

    msg(
        "How many sounds can appear at the end of a Korean syllable?",
        "Only 7 sounds can appear at the end of a Korean syllable, no matter which "
        "letter is written there. The 7 are: /k/ (ㄱ), /n/ (ㄴ), /t/ (ㄷ), /l/ (ㄹ), "
        "/m/ (ㅁ), /p/ (ㅂ), and /ng/ (ㅇ). For example, ㄱ, ㄲ, and ㅋ all reduce "
        "to the same /k/ sound at syllable end.",
    ),
    msg(
        "Why do ㄷ, ㅅ, and ㅈ all sound the same at the end of a syllable?",
        "Because Korean only allows 7 sounds at syllable-final position. Any consonant "
        "written there gets neutralized to its closest representative. ㄷ, ㅅ, ㅆ, ㅈ, "
        "ㅊ, ㅌ, and ㅎ all collapse to /t/. The spelling differs — the pronunciation doesn't.",
    ),
    msg(
        "Is it true that Korean has 7 batchim sounds?",
        "Yes. Even though many different consonants can be written as batchim, only 7 "
        "distinct sounds are actually pronounced: /k/, /n/, /t/, /l/, /m/, /p/, /ng/. "
        "Multiple letters share each slot — for instance ㅂ and ㅍ both produce /p/ "
        "at syllable end.",
    ),

    # ── Gap 2: ㅘ = "wa" ─────────────────────────────────────────────────────

    msg(
        "How do you pronounce ㅘ?",
        "ㅘ is pronounced 'wa' — like the 'wa' in 'wand'. It's a compound vowel made "
        "by combining ㅗ ('o') and ㅏ ('a'). You glide from the ㅗ sound into ㅏ quickly. "
        "Example: 봐 is 'bwa', 과 is 'gwa'.",
    ),
    msg(
        "What two vowels make up ㅘ?",
        "ㅘ is built from ㅗ + ㅏ. That combination produces a 'w' glide, so ㅘ sounds "
        "like 'wa'. A syllable like 화 (fire) is pronounced 'hwa', not 'hya'.",
    ),
    msg(
        "Does ㅘ sound like 'ya' or 'wa'?",
        "'wa'. The 'ya' sound belongs to ㅑ, which has a /y/ glide. ㅘ is built from "
        "ㅗ + ㅏ, which produces a /w/ glide — giving you 'wa'. Both feel like glide "
        "vowels, but the glide type is different: ㅑ glides through /y/, ㅘ glides through /w/.",
    ),

    # ── Gap 3: Tense vs. aspirated terminology ───────────────────────────────

    msg(
        "What's the difference between aspirated and tense consonants in Korean?",
        "Aspirated consonants — ㅋ, ㅌ, ㅍ, ㅊ — are released with a strong puff of "
        "air, like the hard 'k' in 'kite'. Tense consonants — ㄲ, ㄸ, ㅃ, ㅆ, ㅉ — "
        "are pronounced with a tightened throat and no air puff; they sound sharp and "
        "abrupt. Plain consonants (ㄱ, ㄷ, ㅂ, ㅅ, ㅈ) fall in between.",
    ),
    msg(
        "How are ㅋ and ㄲ different?",
        "Both are variations of ㄱ, but they differ in how: ㅋ is aspirated — you "
        "release it with a puff of breath (like 'k' in 'keep'). ㄲ is tense — you "
        "tighten your throat and release with no breath puff, producing a sharp, "
        "doubled sound. Romanized: ㅋ = k, ㄲ = kk.",
    ),
    msg(
        "Is ㄸ aspirated or tense?",
        "Tense. ㄸ (tt) is the tense version of ㄷ — pronounced with a tight throat, "
        "no puff of air. The aspirated version of ㄷ is ㅌ, which carries a breath "
        "release. Tense consonants are the doubled-romanization set: ㄲ (kk), ㄸ (tt), "
        "ㅃ (pp), ㅆ (ss), ㅉ (jj).",
    ),

    # ── Gap 4: 겹받침 (introductory level) ───────────────────────────────────

    msg(
        "What is 겹받침?",
        "겹받침 means 'double batchim' — two consonants written at the bottom of a "
        "syllable instead of one. For example, 닭 (chicken) has ㄺ at the bottom, "
        "which is ㄹ + ㄱ stacked together. Most of the time only one of the two "
        "consonants is actually pronounced.",
    ),
    msg(
        "If a syllable has two batchim consonants and the next syllable starts with a vowel, what happens?",
        "One of the consonants moves to the next syllable. For example, 닭이 is "
        "pronounced '달기' (dal-gi) — the ㄱ from ㄺ shifts to become the initial of 이. "
        "Which consonant moves depends on the specific cluster and environment, "
        "so it's best learned word by word at first.",
    ),
    msg(
        "How do you pronounce 읽다?",
        "읽다 is pronounced '익따' [ik-dda]. The batchim ㄺ is a double batchim "
        "(ㄹ + ㄱ). Before the consonant ㄷ, the ㄹ drops and ㄱ is pronounced — so "
        "읽 reduces to /ik/. The following ㄷ also tensifies to ㄸ in this environment, "
        "which is why the full word sounds like '익따', not '익다'.",
    ),
]

# ── Verifier ─────────────────────────────────────────────────────────────────

def verify(pair: dict, idx: int) -> list:
    errors = []
    tag = f"[pair #{idx}]"

    if "messages" not in pair:
        errors.append(f"{tag} missing 'messages' key")
        return errors

    msgs = pair["messages"]
    if len(msgs) != 2:
        errors.append(f"{tag} expected 2 messages, got {len(msgs)}")
        return errors

    if msgs[0].get("role") != "user":
        errors.append(f"{tag} first message role should be 'user'")
    if msgs[1].get("role") != "assistant":
        errors.append(f"{tag} second message role should be 'assistant'")

    for m in msgs:
        if not m.get("content", "").strip():
            errors.append(f"{tag} empty content in role '{m.get('role')}'")

    if len(msgs[1].get("content", "")) < 40:
        errors.append(f"{tag} assistant response suspiciously short")

    return errors


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    errors = []
    for idx, pair in enumerate(PAIRS, 1):
        errors.extend(verify(pair, idx))

    if errors:
        print("VERIFY FAILED — not writing output:")
        for e in errors:
            print(" ", e)
        sys.exit(1)

    # Write batch file
    with BATCH_OUTPUT.open("w", encoding="utf-8") as f:
        for pair in PAIRS:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    print(f"OK — wrote {len(PAIRS)} pairs to {BATCH_OUTPUT}")

    # Optionally merge into v12
    if V11_SOURCE.exists():
        v11_lines = V11_SOURCE.read_text(encoding="utf-8").splitlines()
        b5_lines  = BATCH_OUTPUT.read_text(encoding="utf-8").splitlines()
        v12_lines = v11_lines + b5_lines
        V12_OUTPUT.write_text("\n".join(v12_lines) + "\n", encoding="utf-8")
        print(f"Merged  → {V12_OUTPUT} ({len(v12_lines)} pairs total)")
    else:
        print(f"Note: {V11_SOURCE} not found — skipping v12 merge.")
        print(f"Merge manually: cat {V11_SOURCE} {BATCH_OUTPUT} > {V12_OUTPUT}")


if __name__ == "__main__":
    main()
