"""generate_dataset_v2_b3_production.py — Batch 3 production/practice expansion.

Generates hangul_finetune_v10_b3_expansion.jsonl (35 pairs) in the twin
structure: 15 wrong-grade + 15 correct-grade + 5 produce. Every Hangul fact is
verified against ground truth BEFORE emission:
  _compose_syllable / _decompose_syllable / COMPOUND_COMPONENTS /
  _batchim_sound / JAMO.
No hand-derived Hangul survives to the output file — a failed fact aborts.

Run: python generate_dataset_v2_b3_production.py
"""
import json
from collections import Counter
from pathlib import Path

from hangul_quiz_engine import HangulQuiz, COMPOUND_COMPONENTS
from hangul_flash import JAMO

BASE = Path(__file__).resolve().parent
OUT = BASE / "hangul_finetune_v10_b3_expansion.jsonl"

q = HangulQuiz()  # full __init__ so _batchim_sound reads self.curriculum

# Each pair: (kind, user, assistant, facts)
#   kind ∈ {wrong, correct, produce}
#   fact tags:
#     d  ("d", syllable, cho, jung, jong)      decompose check
#     c  ("c", cho, jung, jong, syllable)      compose check
#     v  ("v", compound_vowel, c1, c2)         COMPOUND_COMPONENTS check
#     b  ("b", jong, sound)                    batchim sound check
#     r  ("r", jamo, roman)                    JAMO romanization check
PAIRS = [
    # ── Vowel substitutions (12 = 6 targets × twin) ─────────────────────────
    ("wrong", "I wrote 허 for 'ha'. Is that right?",
     "Not quite. You used ㅓ, which gives the 'eo' sound — that makes 허 ('heo'), not 'ha'. For 'ha' you want ㅏ: 하 = ㅎ + ㅏ.",
     [("d", "허", "ㅎ", "ㅓ", ""), ("d", "하", "ㅎ", "ㅏ", "")]),
    ("correct", "I wrote 하 for 'ha'. Is that right?",
     "Yes — 하 is correct: ㅎ (h) + ㅏ (a).",
     [("d", "하", "ㅎ", "ㅏ", "")]),
    ("wrong", "I wrote 러 for 'ra'. Is that right?",
     "Not quite. You used ㅓ, which gives the 'eo' sound — that makes 러 ('reo'), not 'ra'. For 'ra' you want ㅏ: 라 = ㄹ + ㅏ.",
     [("d", "러", "ㄹ", "ㅓ", ""), ("d", "라", "ㄹ", "ㅏ", "")]),
    ("correct", "I wrote 라 for 'ra'. Is that right?",
     "Yes — 라 is correct: ㄹ (r) + ㅏ (a).",
     [("d", "라", "ㄹ", "ㅏ", "")]),
    ("wrong", "I wrote 후 for 'ho'. Is that right?",
     "Not quite. You used ㅜ, which gives the 'u' sound — that makes 후 ('hu'), not 'ho'. For 'ho' you want ㅗ: 호 = ㅎ + ㅗ.",
     [("d", "후", "ㅎ", "ㅜ", ""), ("d", "호", "ㅎ", "ㅗ", "")]),
    ("correct", "I wrote 호 for 'ho'. Is that right?",
     "Yes — 호 is correct: ㅎ (h) + ㅗ (o).",
     [("d", "호", "ㅎ", "ㅗ", "")]),
    ("wrong", "I wrote 수 for 'so'. Is that right?",
     "Not quite. You used ㅜ, which gives the 'u' sound — that makes 수 ('su'), not 'so'. For 'so' you want ㅗ: 소 = ㅅ + ㅗ.",
     [("d", "수", "ㅅ", "ㅜ", ""), ("d", "소", "ㅅ", "ㅗ", "")]),
    ("correct", "I wrote 소 for 'so'. Is that right?",
     "Yes — 소 is correct: ㅅ (s) + ㅗ (o).",
     [("d", "소", "ㅅ", "ㅗ", "")]),
    ("wrong", "I wrote 메 for 'mae'. Is that right?",
     "Not quite. You used ㅔ, which gives the 'e' sound — that makes 메 ('me'), not 'mae'. For 'mae' you want ㅐ: 매 = ㅁ + ㅐ.",
     [("d", "메", "ㅁ", "ㅔ", ""), ("d", "매", "ㅁ", "ㅐ", ""), ("r", "ㅔ", "e"), ("r", "ㅐ", "ae")]),
    ("correct", "I wrote 매 for 'mae'. Is that right?",
     "Yes — 매 is correct: ㅁ (m) + ㅐ (ae).",
     [("d", "매", "ㅁ", "ㅐ", ""), ("r", "ㅐ", "ae")]),
    ("wrong", "I wrote 네 for 'nae'. Is that right?",
     "Not quite. You used ㅔ, which gives the 'e' sound — that makes 네 ('ne'), not 'nae'. For 'nae' you want ㅐ: 내 = ㄴ + ㅐ.",
     [("d", "네", "ㄴ", "ㅔ", ""), ("d", "내", "ㄴ", "ㅐ", "")]),
    ("correct", "I wrote 내 for 'nae'. Is that right?",
     "Yes — 내 is correct: ㄴ (n) + ㅐ (ae).",
     [("d", "내", "ㄴ", "ㅐ", "")]),

    # ── Initial consonant substitutions (8 = 4 targets × twin) ─────────────
    ("wrong", "I wrote 카 for 'ga'. Is that right?",
     "Not quite. You used ㅋ, which is aspirated — a strong burst of air — so 카 is 'ka', not 'ga'. For 'ga' you want the plain ㄱ: 가 = ㄱ + ㅏ.",
     [("d", "카", "ㅋ", "ㅏ", ""), ("d", "가", "ㄱ", "ㅏ", "")]),
    ("correct", "I wrote 가 for 'ga'. Is that right?",
     "Yes — 가 is correct: ㄱ (g) + ㅏ (a). ㄱ is the plain consonant, no burst of air.",
     [("d", "가", "ㄱ", "ㅏ", "")]),
    ("wrong", "I wrote 또 for 'do'. Is that right?",
     "Not quite. You used ㄸ, which is tense — a tighter, harder sound — so 또 is 'tto', not 'do'. For 'do' you want the plain ㄷ: 도 = ㄷ + ㅗ.",
     [("d", "또", "ㄸ", "ㅗ", ""), ("d", "도", "ㄷ", "ㅗ", "")]),
    ("correct", "I wrote 도 for 'do'. Is that right?",
     "Yes — 도 is correct: ㄷ (d) + ㅗ (o). ㄷ is the plain consonant.",
     [("d", "도", "ㄷ", "ㅗ", "")]),
    ("wrong", "I wrote 뿌 for 'bu'. Is that right?",
     "Not quite. You used ㅃ, which is tense, so 뿌 is 'ppu' — tighter than 'bu'. For 'bu' you want the plain ㅂ: 부 = ㅂ + ㅜ.",
     [("d", "뿌", "ㅃ", "ㅜ", ""), ("d", "부", "ㅂ", "ㅜ", "")]),
    ("correct", "I wrote 부 for 'bu'. Is that right?",
     "Yes — 부 is correct: ㅂ (b) + ㅜ (u). ㅂ is the plain consonant.",
     [("d", "부", "ㅂ", "ㅜ", "")]),
    ("wrong", "I wrote 씨 for 'si'. Is that right?",
     "Not quite. You used ㅆ, which is tense, so 씨 is 'ssi' — a longer, tenser 's'. For 'si' you want the plain ㅅ: 시 = ㅅ + ㅣ.",
     [("d", "씨", "ㅆ", "ㅣ", ""), ("d", "시", "ㅅ", "ㅣ", "")]),
    ("correct", "I wrote 시 for 'si'. Is that right?",
     "Yes — 시 is correct: ㅅ (s) + ㅣ (i). ㅅ is the plain consonant.",
     [("d", "시", "ㅅ", "ㅣ", "")]),

    # ── Batchim substitutions (6 = 3 targets × twin) ───────────────────────
    ("wrong", "I tried to write 곧 and used ㅅ as the batchim. Is that right?",
     "Not quite. ㅅ does make the /t/ sound in batchim position, so 곳 sounds right — but this word is spelled with ㄷ: 곧 = ㄱ + ㅗ + ㄷ. More than one letter can make the /t/ sound, so go by spelling, not sound alone.",
     [("d", "곳", "ㄱ", "ㅗ", "ㅅ"), ("d", "곧", "ㄱ", "ㅗ", "ㄷ"), ("b", "ㅅ", "t"), ("b", "ㄷ", "t")]),
    ("correct", "I want to write a syllable that ends in the /t/ sound. I wrote 곧, using ㄷ as the batchim. Is that right?",
     "Yes — 곧 = ㄱ + ㅗ + ㄷ. ㄷ as batchim makes the /t/ sound.",
     [("d", "곧", "ㄱ", "ㅗ", "ㄷ"), ("b", "ㄷ", "t")]),
    ("wrong", "I tried to write 집 and used ㅍ as the batchim. Is that right?",
     "Not quite. ㅍ makes the /p/ sound in batchim position, so 짚 sounds right — but this word is spelled with ㅂ: 집 = ㅈ + ㅣ + ㅂ. More than one letter can make the /p/ sound, so go by spelling, not sound alone.",
     [("d", "짚", "ㅈ", "ㅣ", "ㅍ"), ("d", "집", "ㅈ", "ㅣ", "ㅂ"), ("b", "ㅍ", "p"), ("b", "ㅂ", "p")]),
    ("correct", "I want to write a syllable that ends in the /p/ sound. I wrote 집, using ㅂ as the batchim. Is that right?",
     "Yes — 집 = ㅈ + ㅣ + ㅂ. ㅂ as batchim makes the /p/ sound.",
     [("d", "집", "ㅈ", "ㅣ", "ㅂ"), ("b", "ㅂ", "p")]),
    ("wrong", "I tried to write 낮 and used ㅊ as the batchim. Is that right?",
     "Not quite. ㅊ makes the /t/ sound in batchim position, so 낯 sounds right — but this word is spelled with ㅈ: 낮 = ㄴ + ㅏ + ㅈ. More than one letter can make the /t/ sound, so go by spelling, not sound alone.",
     [("d", "낯", "ㄴ", "ㅏ", "ㅊ"), ("d", "낮", "ㄴ", "ㅏ", "ㅈ"), ("b", "ㅊ", "t"), ("b", "ㅈ", "t")]),
    ("correct", "I want to write a syllable that ends in the /t/ sound. I wrote 낮, using ㅈ as the batchim. Is that right?",
     "Yes — 낮 = ㄴ + ㅏ + ㅈ. ㅈ as batchim makes the /t/ sound.",
     [("d", "낮", "ㄴ", "ㅏ", "ㅈ"), ("b", "ㅈ", "t")]),

    # ── Compound-vowel substitutions (4 = 2 targets × twin, whole-vowel) ───
    ("wrong", "I wrote 궈 for 'gwa'. Is that right?",
     "Not quite. 궈 uses ㅝ (ㅜ + ㅓ), so it's 'gwo', not 'gwa'. For 'gwa' you want ㅘ (ㅗ + ㅏ): 과 = ㄱ + ㅘ.",
     [("d", "궈", "ㄱ", "ㅝ", ""), ("d", "과", "ㄱ", "ㅘ", ""), ("v", "ㅝ", "ㅜ", "ㅓ"), ("v", "ㅘ", "ㅗ", "ㅏ")]),
    ("correct", "I wrote 과 for 'gwa'. Is that right?",
     "Yes — 과 is correct: ㄱ + ㅘ. ㅘ is the compound vowel built from ㅗ + ㅏ.",
     [("d", "과", "ㄱ", "ㅘ", ""), ("v", "ㅘ", "ㅗ", "ㅏ")]),
    ("wrong", "I wrote 뒈 for 'dwae'. Is that right?",
     "Not quite. 뒈 uses ㅞ (ㅜ + ㅔ), so it's 'dwe', not 'dwae'. For 'dwae' you want ㅙ (ㅗ + ㅐ): 돼 = ㄷ + ㅙ.",
     [("d", "뒈", "ㄷ", "ㅞ", ""), ("d", "돼", "ㄷ", "ㅙ", ""), ("v", "ㅞ", "ㅜ", "ㅔ"), ("v", "ㅙ", "ㅗ", "ㅐ")]),
    ("correct", "I wrote 돼 for 'dwae'. Is that right?",
     "Yes — 돼 is correct: ㄷ + ㅙ. ㅙ is the compound vowel built from ㅗ + ㅐ.",
     [("d", "돼", "ㄷ", "ㅙ", ""), ("v", "ㅙ", "ㅗ", "ㅐ")]),

    # ── Production / construction (5, ungraded) ────────────────────────────
    ("produce", "How do I write 'wa' in Hangul?",
     "와 — ㅇ + ㅘ. ㅘ is the compound vowel built from ㅗ + ㅏ, and since there's no initial consonant sound, ㅇ holds the initial position.",
     [("d", "와", "ㅇ", "ㅘ", ""), ("v", "ㅘ", "ㅗ", "ㅏ"), ("r", "ㅘ", "wa")]),
    ("produce", "How do I write 'wi' in Hangul?",
     "위 — ㅇ + ㅟ. ㅟ is the compound vowel built from ㅜ + ㅣ.",
     [("d", "위", "ㅇ", "ㅟ", ""), ("v", "ㅟ", "ㅜ", "ㅣ"), ("r", "ㅟ", "wi")]),
    ("produce", "How do I write 'han' in Hangul?",
     "한 — ㅎ + ㅏ + ㄴ. The final ㄴ is the batchim, which gives the 'n' ending.",
     [("d", "한", "ㅎ", "ㅏ", "ㄴ")]),
    ("produce", "How do I write 'chu' in Hangul?",
     "추 — ㅊ + ㅜ. ㅊ is the 'ch' consonant.",
     [("d", "추", "ㅊ", "ㅜ", "")]),
    ("produce", "What do I get if I combine ㅁ, ㅗ, and ㄹ?",
     "몰 — ㅁ + ㅗ + ㄹ. The ㄹ sits at the bottom as the batchim.",
     [("c", "ㅁ", "ㅗ", "ㄹ", "몰"), ("d", "몰", "ㅁ", "ㅗ", "ㄹ")]),
]


def verify():
    failures, checks = [], 0
    for kind, user, assistant, facts in PAIRS:
        for f in facts:
            checks += 1
            tag = f[0]
            try:
                if tag == "d":
                    syl, cho, jung, jong = f[1], f[2], f[3], f[4]
                    got = q._decompose_syllable(syl)
                    exp = (cho, jung, jong)
                    if got != exp:
                        failures.append(f"[{kind}] decompose {syl}: got {got}, expected {exp}")
                elif tag == "c":
                    cho, jung, jong, syl = f[1], f[2], f[3], f[4]
                    got = q._compose_syllable(cho, jung, jong)
                    if got != syl:
                        failures.append(f"[{kind}] compose {cho}+{jung}+{jong}: got {got!r}, expected {syl!r}")
                elif tag == "v":
                    cv, c1, c2 = f[1], f[2], f[3]
                    got = COMPOUND_COMPONENTS.get(cv)
                    if got != (c1, c2):
                        failures.append(f"[{kind}] components {cv}: got {got}, expected ({c1},{c2})")
                elif tag == "b":
                    jong, sound = f[1], f[2]
                    got = q._batchim_sound(jong)
                    if got != sound:
                        failures.append(f"[{kind}] batchim {jong}: got {got!r}, expected {sound!r}")
                elif tag == "r":
                    jamo, roman = f[1], f[2]
                    romans = JAMO.get(jamo, {}).get("roman", [])
                    if roman not in romans:
                        failures.append(f"[{kind}] roman {jamo}: {roman!r} not in {romans}")
            except Exception as e:  # noqa: BLE001
                failures.append(f"[{kind}] fact {f} raised {e!r}")
    return checks, failures


def main():
    checks, failures = verify()
    print(f"verification: {checks} checks, {len(failures)} failures")
    for f in failures:
        print("  FAIL:", f)
    if failures:
        print("ABORT — nothing emitted.")
        return 1
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        for kind, user, assistant, _facts in PAIRS:
            rec = {"messages": [{"role": "user", "content": user},
                                {"role": "assistant", "content": assistant}]}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    kinds = Counter(k for k, *_ in PAIRS)
    print(f"emitted {len(PAIRS)} pairs -> {OUT}")
    print(f"kinds: wrong={kinds['wrong']} correct={kinds['correct']} produce={kinds['produce']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
