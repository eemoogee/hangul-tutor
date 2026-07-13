#!/usr/bin/env python3
"""
generate_dataset.py — Build a CC0 Hangul reading-practice dataset.

Five levels of progressive difficulty, all constrained to syllables from
the curriculum + Konglish word bank. Every entry is something a beginner
can decode character-by-character and recognize.

Level 1: Single Konglish words (바나나 → banana)
Level 2: Short native words (나비, 우유, 고기)
Level 3: Two-syllable combos (큰 개, 새 집)
Level 4: Pattern drills (가 나 다 라 마 바 사)
Level 5: Short sentences and phrases using subject/verb lookup tables
        (나는 가요 → I go, 좋은 책 → good book, 이것은 개예요 → this is a dog)

Output: data/reading_practice.jsonl
  {korean, english, level, syllables, lesson_max, source, hint}

Usage:
  python generate_dataset.py                    # default: 1000 entries
  python generate_dataset.py --count 5000       # 5000 entries
  python generate_dataset.py --level 1,2        # only levels 1 and 2
"""

import json
import random
import argparse
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"

# ── Syllable helpers ───────────────────────────────────────────────────────

def decompose(syl: str) -> tuple | None:
    """Hangul syllable → (cho_idx, jung_idx, jong_idx) or None."""
    if len(syl) != 1:
        return None
    code = ord(syl)
    if code < 0xAC00 or code > 0xD7A3:
        return None
    code -= 0xAC00
    return (code // (21 * 28), (code // 28) % 21, code % 28)


def has_batchim(syllable: str) -> bool:
    """True if a Hangul syllable ends in a consonant (batchim) rather
    than a bare vowel. Determines which allomorph a following particle or
    copula needs — 이에요 vs 예요, 은 vs 는, 이 vs 가, and so on."""
    d = decompose(syllable)
    return d is not None and d[2] != 0


def copula_polite(noun: str) -> str:
    """Attach the correct polite copula ending: 이에요 after a
    consonant-final (batchim) noun, bare 예요 after a vowel-final noun.
    Getting this wrong produces real, incorrect Korean, not just a style
    mismatch — e.g. 책예요 ("book" + bare 예요) is ungrammatical; it has
    to be 책이에요."""
    return f"{noun}이에요" if has_batchim(noun[-1]) else f"{noun}예요"


CHO = ['ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ','ㅆ',
       'ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']
JUNG = ['ㅏ','ㅐ','ㅑ','ㅒ','ㅓ','ㅔ','ㅕ','ㅖ','ㅗ','ㅘ','ㅙ','ㅚ',
        'ㅛ','ㅜ','ㅝ','ㅞ','ㅟ','ㅠ','ㅡ','ㅢ','ㅣ']
JONG = ['','ㄱ','ㄲ','ㄳ','ㄴ','ㄵ','ㄶ','ㄷ','ㄹ','ㄺ','ㄻ','ㄼ',
        'ㄽ','ㄾ','ㄿ','ㅀ','ㅁ','ㅂ','ㅄ','ㅅ','ㅆ','ㅇ','ㅈ',
        'ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']


def compose(cho: str, jung: str, jong: str = "") -> str:
    """Compose jamo → Hangul syllable block."""
    try:
        ci = CHO.index(cho)
        ji = JUNG.index(jung)
        ki = JONG.index(jong) if jong else 0
        return chr(0xAC00 + ci * 21 * 28 + ji * 28 + ki)
    except ValueError:
        return cho + jung + jong


def extract_syllables(text: str) -> list[str]:
    return [c for c in text if decompose(c) is not None]


# ── Data loading ───────────────────────────────────────────────────────────

def load_curriculum():
    with open(DATA_DIR / "curriculum.json", encoding='utf-8') as f:
        return json.load(f)


def load_konglish():
    with open(DATA_DIR / "konglish_vocab.json", encoding='utf-8') as f:
        return json.load(f)


# ── Syllable banks per lesson ──────────────────────────────────────────────

def build_syllable_banks(curriculum: dict) -> dict[int, set[str]]:
    """For each lesson, collect all syllables the learner would know by then."""
    banks = {}
    known = set()

    for lesson in curriculum["lessons"]:
        lid = lesson["id"]
        # Add any practice syllables from this lesson
        for syl in lesson.get("practice_syllables", []):
            if decompose(syl):
                known.add(syl)
        # Also generate syllables from the lesson's letters
        for letter in lesson.get("letters", []):
            if letter in CHO + ['ㄲ','ㄸ','ㅃ','ㅆ','ㅉ']:
                for v in 'ㅏㅓㅗㅜㅡㅣ':
                    known.add(compose(letter, v))
            elif letter in JUNG:
                for c in 'ㄱㄴㄷㄹㅁㅂㅅㅇㅈ':
                    known.add(compose(c, letter))
        banks[lid] = set(known)

    return banks


# ── Shared entry builder ───────────────────────────────────────────────────

def _make_entry(ko: str, en: str, level: int, syls: list, source: str,
                syllable_banks: dict) -> dict:
    """Build a standard entry dict, computing lesson_max from banks."""
    lesson_max = 0
    for lid, bank in sorted(syllable_banks.items()):
        if syls and all(s in bank for s in syls):
            lesson_max = max(lesson_max, lid)
    return {
        "korean": ko,
        "english": en,
        "level": level,
        "syllables": syls,
        "lesson_max": lesson_max or max(syllable_banks.keys()),
        "source": source,
        "hint": "",
    }


# ── Level 1: Konglish single words ─────────────────────────────────────────

def generate_level1(konglish: dict, syllable_banks: dict, count: int) -> list[dict]:
    """Single Konglish words the learner can decode and recognize."""
    all_words = []
    for cat in konglish["categories"]:
        all_words.extend(konglish["categories"][cat])

    entries = []
    used = set()
    random.shuffle(all_words)

    for word in all_words:
        if len(entries) >= count:
            break
        ko = word["ko"]
        en = word["en"]
        if ko in used:
            continue
        used.add(ko)

        syls = extract_syllables(ko)
        entry = _make_entry(ko, en, 1, syls, "konglish", syllable_banks)
        entry["hint"] = word.get("hint", "")
        entries.append(entry)

    return entries


# ── Level 2: Short native words ────────────────────────────────────────────

NATIVE_SHORT = [
    # From curriculum example_words + short_and_sweet category
    ("아이", "child"), ("오이", "cucumber"), ("우유", "milk"),
    ("개", "dog"), ("고기", "meat"), ("나비", "butterfly"),
    ("다리", "leg / bridge"), ("머리", "head / hair"), ("바다", "sea"),
    ("사자", "lion"), ("아기", "baby"), ("가구", "furniture"),
    ("나라", "country"), ("도시", "city"), ("이름", "name"),
    ("나무", "tree"), ("가수", "singer"), ("비누", "soap"),
    ("여우", "fox"), ("모자", "hat"), ("바지", "pants"),
    ("치마", "skirt"), ("구두", "shoes"), ("시계", "clock/watch"),
    ("의자", "chair"), ("침대", "bed"), ("거울", "mirror"),
    ("사과", "apple"), ("포도", "grape"), ("배", "pear / boat / stomach"),
    ("김치", "kimchi"), ("밥", "rice / meal"), ("국", "soup"),
    ("물", "water"), ("불", "fire / light"), ("산", "mountain"),
    ("강", "river"), ("꽃", "flower"), ("별", "star"),
    ("달", "moon / month"), ("해", "sun"), ("비", "rain"),
    ("눈", "eye / snow"), ("코", "nose"), ("입", "mouth"),
    ("귀", "ear"), ("손", "hand"), ("발", "foot"),
    ("집", "house"), ("문", "door"), ("책", "book"),
    ("글", "writing / letter"), ("말", "word / horse"), ("길", "road"),
    ("돈", "money"), ("일", "work / day"), ("힘", "strength"),
]


def generate_level2(syllable_banks: dict, count: int) -> list[dict]:
    """Short native Korean words — perfect for decoding practice."""
    entries = []
    used = set()
    random.shuffle(NATIVE_SHORT)

    for ko, en in NATIVE_SHORT:
        if len(entries) >= count:
            break
        if ko in used:
            continue
        used.add(ko)

        syls = extract_syllables(ko)
        entries.append(_make_entry(ko, en, 2, syls, "native", syllable_banks))

    return entries


# ── Level 3: Two-syllable combos ───────────────────────────────────────────

COMBO_TEMPLATES = [
    ("{adj} {noun}", [("큰", "big"), ("작은", "small"), ("새", "new"),
                      ("좋은", "good"), ("많은", "many"), ("그", "that")],
                     [("개", "dog"), ("집", "house"), ("책", "book"),
                      ("길", "road"), ("산", "mountain"), ("문", "door"),
                      ("별", "star"), ("꽃", "flower"), ("나무", "tree")]),
    ("{noun1} {noun2}", None, None),  # random noun pairs
]


def generate_level3(syllable_banks: dict, count: int) -> list[dict]:
    """Two-word combos: adjective+noun or noun+noun pairs."""
    adj_list = [("큰", "big"), ("작은", "small"), ("새", "new"), ("좋은", "good"),
                ("많은", "many"), ("그", "that"), ("이", "this"), ("저", "that (over there)")]
    noun_list = [("개", "dog"), ("집", "house"), ("책", "book"), ("길", "road"),
                 ("산", "mountain"), ("문", "door"), ("별", "star"), ("꽃", "flower"),
                 ("나무", "tree"), ("방", "room"), ("차", "car / tea"), ("강", "river"),
                 ("코", "nose"), ("눈", "eye / snow"), ("입", "mouth"), ("귀", "ear"),
                 ("손", "hand"), ("발", "foot"), ("배", "pear / boat"), ("밥", "rice")]

    entries = []
    used = set()
    random.shuffle(adj_list)
    random.shuffle(noun_list)

    for adj_ko, adj_en in adj_list:
        for noun_ko, noun_en in noun_list:
            if len(entries) >= count:
                break
            ko = f"{adj_ko} {noun_ko}"
            if ko in used:
                continue

            # Don't combine two words that share no semantic connection? Actually,
            # for decoding practice, random combos are fine — the point is reading.
            used.add(ko)
            en = f"{adj_en} {noun_en}"
            syls = extract_syllables(ko)
            entries.append(_make_entry(ko, en, 3, syls, "combo", syllable_banks))
        if len(entries) >= count:
            break

    return entries


# ── Level 4: Pattern drills ────────────────────────────────────────────────

DRILL_PATTERNS = [
    # Sequential consonant practice
    ("{cons} + {vowel}", lambda: [
        (f"{compose(c, 'ㅏ')} {compose(c, 'ㅓ')} {compose(c, 'ㅗ')} {compose(c, 'ㅜ')} {compose(c, 'ㅡ')} {compose(c, 'ㅣ')}",
         f"{c}+a, {c}+eo, {c}+o, {c}+u, {c}+eu, {c}+i")
        for c in 'ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ'
    ]),
    # Vowel practice with different consonants
    ("{vowel} with consonants", lambda: [
        (f"{compose('ㄱ', v)} {compose('ㄴ', v)} {compose('ㄷ', v)} {compose('ㄹ', v)} {compose('ㅁ', v)}",
         f"g{v}, n{v}, d{v}, r{v}, m{v}")
        for v in 'ㅏㅓㅗㅜㅡㅣ'
    ]),
    # The alphabet song in Hangul
    ("가나다 sequence", lambda: [
        ("가 나 다 라 마 바 사 아 자 차 카 타 파 하",
         "ga na da ra ma ba sa a ja cha ka ta pa ha")
    ]),
    # Y-vowel drills
    ("y-vowel drill", lambda: [
        (f"{compose('ㅇ', 'ㅑ')} {compose('ㅇ', 'ㅕ')} {compose('ㅇ', 'ㅛ')} {compose('ㅇ', 'ㅠ')}",
         "ya yeo yo yu")
    ]),
]


def generate_level4(syllable_banks: dict, count: int) -> list[dict]:
    """Pattern drills — systematic consonant+vowel practice."""
    entries = []

    for label, generator in DRILL_PATTERNS:
        for ko, en in generator():
            if len(entries) >= count:
                break
            syls = extract_syllables(ko)
            entry = _make_entry(ko, en, 4, syls, "drill", syllable_banks)
            entry["hint"] = label
            entries.append(entry)
        if len(entries) >= count:
            break

    return entries


# ── Level 5: Sentences and phrases ─────────────────────────────────────────
#
# Subject/verb lookup tables produce only valid Korean sentences with
# correct English subject-verb agreement. No template-mashing — every
# combination is pre-validated.

SUBJECT_TABLE = [
    ("나는",  "I"),         ("내가",  "I"),
    ("너는",  "you"),       ("네가",  "you"),
    ("우리는", "we"),       ("우리가", "we"),
    ("그는",  "he"),        ("그가",  "he"),
    ("그녀는", "she"),      ("그녀가", "she"),
]

VERB_TABLE = [
    ("가요",  {"I": "go",      "you": "go",    "we": "go",
               "he": "goes",   "she": "goes"}),
    ("와요",  {"I": "come",    "you": "come",  "we": "come",
               "he": "comes",  "she": "comes"}),
    ("봐요",  {"I": "see",     "you": "see",   "we": "see",
               "he": "sees",   "she": "sees"}),
    ("먹어요", {"I": "eat",     "you": "eat",  "we": "eat",
               "he": "eats",   "she": "eats"}),
    ("자요",  {"I": "sleep",   "you": "sleep", "we": "sleep",
               "he": "sleeps", "she": "sleeps"}),
    ("해요",  {"I": "do",      "you": "do",    "we": "do",
               "he": "does",   "she": "does"}),
    ("사요",  {"I": "buy",     "you": "buy",   "we": "buy",
               "he": "buys",   "she": "buys"}),
    ("커요",  {"I": "am big",  "you": "are big", "we": "are big",
               "he": "is big", "she": "is big"}),
    ("작아요", {"I": "am small", "you": "are small", "we": "are small",
               "he": "is small", "she": "is small"}),
]

# Adjective+noun phrases (no 다 — these are phrases, not sentences)
ADJ_NOUN_TABLE = [
    ("좋은", "good"), ("큰", "big"), ("작은", "small"), ("새", "new"),
    ("많은", "many"), ("예쁜", "pretty"),
]

NOUN_TABLE = [
    ("날", "day"), ("책", "book"), ("집", "house"), ("차", "car"),
    ("개", "dog"), ("문", "door"), ("별", "star"), ("꽃", "flower"),
    ("밥", "rice"), ("방", "room"),
]

# Copula sentences: "이것은 X예요" (This is X)
COPULA_NOUNS = [
    ("개", "a dog"), ("책", "a book"), ("문", "a door"), ("별", "a star"),
    ("꽃", "a flower"), ("집", "a house"), ("차", "a car"), ("밥", "rice"),
    ("나무", "a tree"), ("물", "water"),
]


def generate_level5(syllable_banks: dict, count: int) -> list[dict]:
    """Short sentences and phrases using validated subject/verb lookup tables."""
    entries = []
    used_korean = set()

    # 1. Subject + verb sentences (~55% of quota)
    sv_count = int(count * 0.55)
    sv_combos = []
    for subj_ko, subj_en in SUBJECT_TABLE:
        for verb_ko, verb_map in VERB_TABLE:
            if subj_en not in verb_map:
                continue
            ko = f"{subj_ko} {verb_ko}"
            if ko in used_korean:
                continue
            en = verb_map[subj_en]
            sv_combos.append((ko, en, subj_en))

    random.shuffle(sv_combos)
    for ko, en, pronoun in sv_combos:
        if len(entries) >= sv_count:
            break
        used_korean.add(ko)
        syls = extract_syllables(ko)
        # "goes" → "he goes", "come" → "I come"
        full_en = f"{pronoun} {en}"
        entries.append(_make_entry(ko, full_en, 5, syls, "sentence", syllable_banks))

    # 2. Adjective + noun phrases (~25% of quota)
    an_count = int(count * 0.25)
    an_combos = []
    for adj_ko, adj_en in ADJ_NOUN_TABLE:
        for noun_ko, noun_en in NOUN_TABLE:
            ko = f"{adj_ko} {noun_ko}"
            if ko in used_korean:
                continue
            en = f"{adj_en} {noun_en}"
            an_combos.append((ko, en))

    random.shuffle(an_combos)
    for ko, en in an_combos:
        if len(entries) >= sv_count + an_count:
            break
        used_korean.add(ko)
        syls = extract_syllables(ko)
        entries.append(_make_entry(ko, en, 5, syls, "phrase", syllable_banks))

    # 3. Copula sentences: "이것은 X예요/이에요" (This is X) — remainder of quota
    cop_combos = []
    for noun_ko, noun_en in COPULA_NOUNS:
        ko = f"이것은 {copula_polite(noun_ko)}"
        if ko in used_korean:
            continue
        en = f"this is {noun_en}"
        cop_combos.append((ko, en))

    random.shuffle(cop_combos)
    for ko, en in cop_combos:
        if len(entries) >= count:
            break
        used_korean.add(ko)
        syls = extract_syllables(ko)
        entries.append(_make_entry(ko, en, 5, syls, "sentence", syllable_banks))

    return entries


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate Hangul reading-practice dataset")
    parser.add_argument("--count", type=int, default=1000, help="Total entries to generate")
    parser.add_argument("--level", type=str, default="1,2,3,4,5",
                        help="Comma-separated levels to include (default: all)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output path (default: data/reading_practice.jsonl)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    random.seed(args.seed)

    curriculum = load_curriculum()
    konglish = load_konglish()
    syllable_banks = build_syllable_banks(curriculum)

    levels = [int(l.strip()) for l in args.level.split(",")]
    per_level = args.count // len(levels)

    all_entries = []

    if 1 in levels:
        entries = generate_level1(konglish, syllable_banks, per_level)
        all_entries.extend(entries)
        print(f"Level 1 (Konglish): {len(entries)} entries")

    if 2 in levels:
        entries = generate_level2(syllable_banks, per_level)
        all_entries.extend(entries)
        print(f"Level 2 (Native words): {len(entries)} entries")

    if 3 in levels:
        entries = generate_level3(syllable_banks, per_level)
        all_entries.extend(entries)
        print(f"Level 3 (Combos): {len(entries)} entries")

    if 4 in levels:
        entries = generate_level4(syllable_banks, per_level)
        all_entries.extend(entries)
        print(f"Level 4 (Drills): {len(entries)} entries")

    if 5 in levels:
        entries = generate_level5(syllable_banks, per_level)
        all_entries.extend(entries)
        print(f"Level 5 (Sentences/phrases): {len(entries)} entries")

    random.shuffle(all_entries)

    output_path = Path(args.output) if args.output else DATA_DIR / "reading_practice.jsonl"
    with open(output_path, 'w', encoding='utf-8') as f:
        for entry in all_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print(f"\nTotal: {len(all_entries)} entries → {output_path}")

    # Stats
    by_level = defaultdict(int)
    by_source = defaultdict(int)
    for e in all_entries:
        by_level[e["level"]] += 1
        by_source[e["source"]] += 1
    print(f"\nBy level: {dict(by_level)}")
    print(f"By source: {dict(by_source)}")

    # Sample
    print("\n--- Sample entries ---")
    for e in random.sample(all_entries, min(10, len(all_entries))):
        print(f"  L{e['level']} | {e['korean']:20s} → {e['english']}")


if __name__ == "__main__":
    main()
