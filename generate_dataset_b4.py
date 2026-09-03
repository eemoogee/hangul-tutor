"""
generate_dataset_b4.py

Generates hangul_finetune_v10_b4.jsonl — 45 factual pairs covering the
aspirated and tense consonant distinctions for the ㄱ, ㄷ, and ㅂ groups
(15 pairs per group: base/aspirated/tense contrasts + identification).

Romanization is DERIVED from the live JAMO dict in hangul_flash.py (never
hardcoded), and a verify-before-emit pass checks every emitted fact against
JAMO before the file is written. If any check fails, no file is written.

Output format matches hangul_finetune_v10.jsonl (plain ChatML, user+assistant
only, no system message):
{"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}

Usage:
    python generate_dataset_b4.py
    python generate_dataset_b4.py --output path/to/output.jsonl
"""

import json
import re
import argparse
import sys
from pathlib import Path

from hangul_flash import JAMO


# ---------------------------------------------------------------------------
# Group definitions: base -> aspirated -> tense, plus a pedagogical example
# word whose initial sound illustrates the aspirated (breathy) consonant.
# Only the example word is hardcoded — it is a sound illustration, NOT a
# romanization claim. All romanization values come from JAMO.
# ---------------------------------------------------------------------------

GROUPS = [
    {"base": "ㄱ", "aspirated": "ㅋ", "tense": "ㄲ", "example_word": "kit"},
    {"base": "ㄷ", "aspirated": "ㅌ", "tense": "ㄸ", "example_word": "top"},
    {"base": "ㅂ", "aspirated": "ㅍ", "tense": "ㅃ", "example_word": "pop"},
]

# The known-bad tense romanizations that a previous hand-written draft used.
# These must never appear in the output; the verify pass asserts this.
FORBIDDEN_ROMANS = {"gg", "dd", "bb"}


def _build_group(g):
    """Build the 15 (question, answer) pairs for one consonant group."""
    B, A, T = g["base"], g["aspirated"], g["tense"]
    w = g["example_word"]
    ar = JAMO[A]["roman"][0]   # aspirated romanization, derived from JAMO
    tr = JAMO[T]["roman"][0]   # tense romanization, derived from JAMO

    return [
        # --- base vs aspirated (3 phrasings) ---
        (
            f"What is the difference between {B} and {A}?",
            f'{B} is a base consonant. {A} is its aspirated counterpart — pronounced with a puff of air, like the "{ar}" in "{w}."',
        ),
        (
            f"How does {A} differ from {B}?",
            f'{A} is the aspirated version of {B}. It is pronounced with a burst of air, like the "{ar}" in "{w}." {B} has no such breath.',
        ),
        (
            f"I keep mixing up {B} and {A}. What's the difference?",
            f'The key difference is aspiration. {A} is pronounced with a puff of air, like the "{ar}" in "{w}." {B} is the base consonant — no extra breath.',
        ),

        # --- base vs tense (3 phrasings) ---
        (
            f"What is the difference between {B} and {T}?",
            f'{B} is a base consonant. {T} is its tense counterpart — a sharper, more pressed version of {B}. It is sometimes romanized as "{tr}".',
        ),
        (
            f"How does {T} differ from {B}?",
            f'{T} is the tense version of {B}. It is pronounced with more tension — sharper and more pressed. You may sometimes see it written as "{tr}" in romanization.',
        ),
        (
            f"I keep mixing up {B} and {T}. What's the difference?",
            f'The key difference is tension. {T} is a sharper, more pressed version of {B}. It is sometimes romanized as "{tr}".',
        ),

        # --- aspirated vs tense (3 phrasings) ---
        (
            f"What is the difference between {A} and {T}?",
            f'{A} is aspirated — pronounced with a puff of air, like the "{ar}" in "{w}." {T} is tense — a sharper, more pressed sound. They are not the same consonant.',
        ),
        (
            f"How does {T} differ from {A}?",
            f'{A} adds aspiration — a puff of air, like the "{ar}" in "{w}." {T} adds tension — it is sharper and more pressed. They are distinct sounds.',
        ),
        (
            f"I keep mixing up {A} and {T}. What's the difference?",
            f'{A} is aspirated — pronounced with a puff of air, like the "{ar}" in "{w}." {T} is tense — sharper and more pressed. They are different consonants.',
        ),

        # --- three-way comparison (3 phrasings) ---
        (
            f"What is the difference between {B}, {A}, and {T}?",
            f'{B} is the consonant that {A} and {T} are built from. {A} is aspirated — pronounced with a puff of air, like the "{ar}" in "{w}." {T} is tense — sharper and more pressed.',
        ),
        (
            f"How are {B}, {A}, and {T} related?",
            f'They form a three-way consonant contrast. {B} is the base consonant, {A} is aspirated — a puff of air, like the "{ar}" in "{w}" — and {T} is tense — sharper and more pressed.',
        ),
        (
            f"Can you explain {B}, {A}, and {T}?",
            f'All three are related consonants. {B} is the consonant that {A} and {T} are built from. {A} is aspirated — pronounced with a puff of air, like the "{ar}" in "{w}" — and {T} is tense — a sharper, more pressed sound.',
        ),

        # --- identification (3 pairs) ---
        (
            f"Which of {B}, {A}, and {T} is the aspirated consonant?",
            f'{A} is the aspirated consonant. It is pronounced with a puff of air, like the "{ar}" in "{w}."',
        ),
        (
            f"Which of {B}, {A}, and {T} is the tense consonant?",
            f'{T} is the tense consonant. It is a sharper, more pressed version of {B}.',
        ),
        (
            f"Which of {B}, {A}, and {T} is the base consonant?",
            f'{B} is the base consonant. It is the consonant that {A} and {T} are built from.',
        ),
    ]


def build_records():
    """Return the list of ChatML records (one dict per pair)."""
    records = []
    for g in GROUPS:
        for user, assistant in _build_group(g):
            records.append(
                {
                    "messages": [
                        {"role": "user", "content": user},
                        {"role": "assistant", "content": assistant},
                    ]
                }
            )
    return records


def verify(records):
    """Verify-before-emit: check every fact against JAMO. Return error list."""
    errors = []

    # (1) Every group letter must exist in JAMO.
    for g in GROUPS:
        for key in ("base", "aspirated", "tense"):
            if g[key] not in JAMO:
                errors.append(f"group letter {g[key]!r} missing from JAMO")

    # (2) Tense/aspirated romanization must be single-valued (templates emit
    #     exactly one romanization string for these).
    for g in GROUPS:
        for key in ("aspirated", "tense"):
            vals = JAMO[g[key]]["roman"]
            if len(vals) != 1:
                errors.append(f"{g[key]} romanization {vals!r} is not single-valued")

    # (3) Schema: plain ChatML, user+assistant only, no system message.
    for i, rec in enumerate(records, 1):
        if set(rec.keys()) != {"messages"}:
            errors.append(f"pair {i}: unexpected top-level keys {sorted(rec.keys())}")
        msgs = rec.get("messages", [])
        if len(msgs) != 2:
            errors.append(f"pair {i}: expected 2 messages, got {len(msgs)}")
            continue
        roles = [m.get("role") for m in msgs]
        if roles != ["user", "assistant"]:
            errors.append(f"pair {i}: role order {roles} != ['user', 'assistant']")
        for m in msgs:
            if "system" in m:
                errors.append(f"pair {i}: system message disallowed")

    # (4) Every Hangul glyph in the output must be a JAMO key.
    hangul = re.compile(r"[\u3130-\u318f\uac00-\ud7a3]")
    for i, rec in enumerate(records, 1):
        for m in rec["messages"]:
            for ch in hangul.findall(m["content"]):
                if ch not in JAMO:
                    errors.append(f"pair {i}: Hangul glyph {ch!r} not in JAMO")

    # (5) Regression guard: the known-bad tense romanizations must never appear.
    for i, rec in enumerate(records, 1):
        answer = rec["messages"][1]["content"]
        for bad in FORBIDDEN_ROMANS:
            if f'"{bad}' in answer:
                errors.append(f"pair {i}: forbidden romanization {bad!r} in answer")

    # (6) Every emitted romanization claim matches JAMO for its letter.
    for g in GROUPS:
        tr = JAMO[g["tense"]]["roman"][0]
        ar = JAMO[g["aspirated"]]["roman"][0]
        for i, rec in enumerate(records, 1):
            answer = rec["messages"][1]["content"]
            for m in re.finditer(r'(?:romanized|written)\s+as\s+"([^"]+)"', answer):
                if g["tense"] in answer and m.group(1) != tr:
                    errors.append(
                        f"pair {i}: tense claim {m.group(1)!r} != JAMO {tr!r}"
                    )
            # aspirated romanization appears in the 'like the "X" in ...' clause
            for m in re.finditer(r'like the "([^"]+)" in', answer):
                if g["aspirated"] in answer and m.group(1) != ar:
                    errors.append(
                        f"pair {i}: aspirated claim {m.group(1)!r} != JAMO {ar!r}"
                    )

    return errors


def main():
    parser = argparse.ArgumentParser(description="Generate hangul_finetune_v10_b4.jsonl")
    parser.add_argument(
        "--output",
        default="hangul_finetune_v10_b4.jsonl",
        help="Output file path (default: hangul_finetune_v10_b4.jsonl)",
    )
    args = parser.parse_args()

    records = build_records()
    assert len(records) == 45, f"Expected 45 pairs, got {len(records)}"

    problems = verify(records)
    if problems:
        for p in problems:
            print(f"VERIFY FAILED: {p}", file=sys.stderr)
        print(f"{len(problems)} verification error(s); NOT writing output.", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Verified + wrote {len(records)} pairs to {output_path}")


if __name__ == "__main__":
    main()
