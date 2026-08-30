#!/usr/bin/env python3
"""Generate dataset v2 — Tier 3 (session summaries) + Tier 4 (progress notes).

Deterministic, no LLM, no file/import dependencies. All 12 pairs are hardcoded
below and emitted as ChatML JSONL to hangul_finetune_v2_t3t4.jsonl.

Tier 3: 6 session-summary pairs.
  Prompt: "Write a short session summary. Questions answered: {n}.
           [Accuracy: {x}%.] [Strong letters: {list}.] [Weak letters: {list}.]
           Ending streak: {n}."
  Rule: omit the Accuracy line when questions answered < 15.

Tier 4: 6 progress-note pairs.
  Prompt: "Write a short progress note. Lessons completed: {n} of 12.
           Total questions answered: {n}. Mastered letters: {list or 'none'}.
           Letters to review: {list or 'none'}."
  Mastered/review lists render as "ㅏ (ah), ㅓ (eo), ...".

Total: 12 pairs.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
OUT_JSONL = PROJECT_ROOT / "hangul_finetune_v2_t3t4.jsonl"

ACCURACY_MIN_QUESTIONS = 15  # omit the Accuracy line below this many questions


def fmt_letters(letters):
    """'ㅎ, ㅁ, ㄴ' from a list, or 'none' when empty."""
    return ", ".join(letters) if letters else "none"


def fmt_romanized(items):
    """'ㅏ (ah), ㅓ (eo)' from (char, roman) tuples, or 'none' when empty."""
    return ", ".join(f"{ch} ({roman})" for ch, roman in items) if items else "none"


# ---- Tier 3: (questions, accuracy_or_None, strong, weak, streak, answer) ----
TIER3 = [
    (24, 88, ["ㅎ", "ㅁ", "ㄴ"], ["ㄹ"], 6,
     "Solid session — ㅎ, ㅁ, and ㄴ are looking reliable. ㄹ is still the one to watch. Ending on a 6-question streak is a good sign."),
    (15, 47, [], ["ㄹ", "ㄷ", "ㅈ"], 0,
     "Tough session — ㄹ, ㄷ, and ㅈ are giving you trouble. That's normal early on. Worth spending more time with those three before moving on."),
    (20, 100, ["ㅏ", "ㅓ", "ㅗ", "ㅜ"], [], 20,
     "Perfect session — every answer correct. The basic vowels are clearly locked in. Ready to push further."),
    (10, 70, ["ㅁ"], ["ㅂ"], 3,
     "ㅁ is solid, ㅂ still needs work. Ending on a 3-question streak suggests things were clicking toward the end."),
    (8, None, [], [], 1,
     "Good start — keep at it."),
    (30, 55, ["ㄴ"], ["ㄹ", "ㄷ", "ㅈ", "ㅊ"], 2,
     "ㄴ is your strongest right now. ㄹ, ㄷ, ㅈ, and ㅊ all need attention — focus on one at a time."),
]

# ---- Tier 4: (lessons, total_questions, mastered, review, answer) ----
# mastered/review are lists of (hangul, romanization) tuples.
TIER4 = [
    (1, 45,
     [("ㅏ", "ah"), ("ㅓ", "eo"), ("ㅗ", "oh")],
     [("ㅡ", "eu")],
     "Lesson 1 of 12 complete. ㅏ, ㅓ, and ㅗ are solid. ㅡ still needs work before moving on."),
    (5, 230,
     [("ㅏ", "ah"), ("ㅓ", "eo"), ("ㅗ", "oh"), ("ㅜ", "oo"), ("ㅡ", "eu"), ("ㅣ", "ee"),
      ("ㄴ", "n"), ("ㄷ", "d"), ("ㄱ", "g/k")],
     [("ㄹ", "r"), ("ㅈ", "j")],
     "Five lessons complete. Nine letters mastered including all the basic vowels. ㄹ and ㅈ keep coming up as trouble spots. That's common at this stage."),
    (8, 450,
     [("ㅏ", "ah"), ("ㅓ", "eo"), ("ㅗ", "oh"), ("ㅜ", "oo"), ("ㅡ", "eu"), ("ㅣ", "ee"),
      ("ㄴ", "n"), ("ㄷ", "d"), ("ㄱ", "g/k"), ("ㅁ", "m"), ("ㅂ", "b"), ("ㅅ", "s"), ("ㅎ", "h")],
     [],
     "Eight lessons in and thirteen letters mastered with no letters to review. Strong foundation. The remaining lessons will introduce more complex patterns."),
    (3, 120,
     [("ㅏ", "ah"), ("ㅓ", "eo")],
     [("ㄹ", "r"), ("ㅡ", "eu"), ("ㅈ", "j"), ("ㅊ", "ch")],
     "Three lessons complete. ㅏ and ㅓ are locked in. ㄹ, ㅡ, ㅈ, and ㅊ still need work."),
    (1, 20, [], [],
     "Just getting started. Keep going."),
    (11, 680,
     [("ㅏ", "ah"), ("ㅓ", "eo"), ("ㅗ", "oh"), ("ㅜ", "oo"), ("ㅡ", "eu"), ("ㅣ", "ee"),
      ("ㄴ", "n"), ("ㄷ", "d"), ("ㄱ", "g/k"), ("ㅁ", "m"), ("ㅂ", "b"), ("ㅅ", "s"), ("ㅎ", "h"),
      ("ㄹ", "r"), ("ㅈ", "j"), ("ㅊ", "ch"), ("ㅋ", "k"), ("ㅌ", "t"), ("ㅍ", "p")],
     [("ㅑ", "ya"), ("ㅕ", "yeo")],
     "Eleven lessons complete and nineteen letters mastered. ㅑ and ㅕ are the last ones needing attention. Almost there."),
]


def tier3_prompt(questions, accuracy, strong, weak, streak):
    parts = [f"Write a short session summary. Questions answered: {questions}."]
    if accuracy is not None and questions >= ACCURACY_MIN_QUESTIONS:
        parts.append(f"Accuracy: {accuracy}%.")
    parts.append(f"Strong letters: {fmt_letters(strong)}.")
    parts.append(f"Weak letters: {fmt_letters(weak)}.")
    parts.append(f"Ending streak: {streak}.")
    return " ".join(parts)


def tier4_prompt(lessons, total, mastered, review):
    return " ".join([
        "Write a short progress note.",
        f"Lessons completed: {lessons} of 12.",
        f"Total questions answered: {total}.",
        f"Mastered letters: {fmt_romanized(mastered)}.",
        f"Letters to review: {fmt_romanized(review)}.",
    ])


def build_pairs():
    pairs = []
    for questions, accuracy, strong, weak, streak, answer in TIER3:
        pairs.append({
            "messages": [
                {"role": "user", "content": tier3_prompt(questions, accuracy, strong, weak, streak)},
                {"role": "assistant", "content": answer},
            ]
        })
    for lessons, total, mastered, review, answer in TIER4:
        pairs.append({
            "messages": [
                {"role": "user", "content": tier4_prompt(lessons, total, mastered, review)},
                {"role": "assistant", "content": answer},
            ]
        })
    return pairs


def main():
    pairs = build_pairs()
    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    # Read back + validate line by line.
    problems = []
    line_count = 0
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
            if not isinstance(msgs[0].get("content"), str) or not msgs[0]["content"].strip():
                problems.append(f"line {i}: empty user content")
            if not isinstance(msgs[1].get("content"), str) or not msgs[1]["content"].strip():
                problems.append(f"line {i}: empty assistant content")

    ok = line_count == len(pairs) == 12 and not problems
    print(f"wrote {OUT_JSONL.name}")
    print(f"pairs written: {len(pairs)}  (Tier 3: {len(TIER3)}, Tier 4: {len(TIER4)})")
    print(f"lines read back: {line_count}")
    print(f"validation: {'PASS' if not problems else 'FAIL'} ({len(problems)} problem(s))")
    for p in problems:
        print(f"  - {p}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
