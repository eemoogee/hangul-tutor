#!/usr/bin/env python3
"""
hangul_flash.py — Keyboard-first Hangul↔Roman flashcard drill.

Two directions, zero keyboard setup needed:
  Hangul→Roman:  See ㄱ, type "g"
  Roman→Hangul:  See "g", pick from numbered Hangul options (1-4)

Usage:
  python hangul_flash.py                  # Full mixed drill
  python hangul_flash.py --set consonants # Basic consonants only
  python hangul_flash.py --set vowels     # Basic vowels only
  python hangul_flash.py --lookup g       # Quick: g → ㄱ
  python hangul_flash.py --lookup ㄱ       # Quick: ㄱ → g/k
  python hangul_flash.py --direction h2r  # Hangul→Roman only
  python hangul_flash.py --direction r2h  # Roman→Hangul only
  python hangul_flash.py --hard           # All 40 jamo (incl. compounds)

Sets: consonants, vowels, basic (consonants+vowels), compounds, all
"""

import sys
import os
import random
import json
import argparse
from pathlib import Path
from collections import defaultdict

# ── Jamo database ────────────────────────────────────────────────────────

JAMO = {
    # Basic consonants
    "ㄱ": {"roman": ["g", "k"], "name": "giyeok", "set": "consonants", "confusable": ["ㅋ", "ㄲ"]},
    "ㄴ": {"roman": ["n"], "name": "nieun", "set": "consonants", "confusable": ["ㄷ"]},
    "ㄷ": {"roman": ["d", "t"], "name": "digeut", "set": "consonants", "confusable": ["ㄴ", "ㅌ", "ㄸ"]},
    "ㄹ": {"roman": ["r", "l"], "name": "rieul", "set": "consonants", "confusable": []},
    "ㅁ": {"roman": ["m"], "name": "mieum", "set": "consonants", "confusable": ["ㅂ"]},
    "ㅂ": {"roman": ["b", "p"], "name": "bieup", "set": "consonants", "confusable": ["ㅁ", "ㅍ", "ㅃ"]},
    "ㅅ": {"roman": ["s"], "name": "siot", "set": "consonants", "confusable": ["ㅆ", "ㅈ"]},
    "ㅇ": {"roman": ["ng", "silent"], "name": "ieung", "set": "consonants", "confusable": []},
    "ㅈ": {"roman": ["j"], "name": "jieut", "set": "consonants", "confusable": ["ㅅ", "ㅊ", "ㅉ"]},
    "ㅊ": {"roman": ["ch"], "name": "chieut", "set": "consonants", "confusable": ["ㅈ", "ㅉ"]},
    "ㅋ": {"roman": ["k"], "name": "kieuk", "set": "consonants", "confusable": ["ㄱ"]},
    "ㅌ": {"roman": ["t"], "name": "tieut", "set": "consonants", "confusable": ["ㄷ"]},
    "ㅍ": {"roman": ["p"], "name": "pieup", "set": "consonants", "confusable": ["ㅂ"]},
    "ㅎ": {"roman": ["h"], "name": "hieut", "set": "consonants", "confusable": []},

    # Double consonants
    "ㄲ": {"roman": ["kk"], "name": "ssanggiyeok", "set": "compounds", "confusable": ["ㄱ"]},
    "ㄸ": {"roman": ["tt"], "name": "ssangdigeut", "set": "compounds", "confusable": ["ㄷ"]},
    "ㅃ": {"roman": ["pp"], "name": "ssangbieup", "set": "compounds", "confusable": ["ㅂ"]},
    "ㅆ": {"roman": ["ss"], "name": "ssangsiot", "set": "compounds", "confusable": ["ㅅ"]},
    "ㅉ": {"roman": ["jj"], "name": "ssangjieut", "set": "compounds", "confusable": ["ㅈ", "ㅊ"]},

    # Basic vowels
    "ㅏ": {"roman": ["a"], "name": "a", "set": "vowels", "confusable": ["ㅓ", "ㅑ"]},
    "ㅑ": {"roman": ["ya"], "name": "ya", "set": "vowels", "confusable": ["ㅏ"]},
    "ㅓ": {"roman": ["eo"], "name": "eo", "set": "vowels", "confusable": ["ㅏ", "ㅕ"]},
    "ㅕ": {"roman": ["yeo"], "name": "yeo", "set": "vowels", "confusable": ["ㅓ"]},
    "ㅗ": {"roman": ["o"], "name": "o", "set": "vowels", "confusable": ["ㅜ", "ㅛ"]},
    "ㅛ": {"roman": ["yo"], "name": "yo", "set": "vowels", "confusable": ["ㅗ"]},
    "ㅜ": {"roman": ["u"], "name": "u", "set": "vowels", "confusable": ["ㅗ", "ㅠ"]},
    "ㅠ": {"roman": ["yu"], "name": "yu", "set": "vowels", "confusable": ["ㅜ"]},
    "ㅡ": {"roman": ["eu"], "name": "eu", "set": "vowels", "confusable": ["ㅣ"]},
    "ㅣ": {"roman": ["i"], "name": "i", "set": "vowels", "confusable": ["ㅡ"]},

    # Compound vowels
    "ㅐ": {"roman": ["ae"], "name": "ae", "set": "compounds", "confusable": ["ㅔ"]},
    "ㅒ": {"roman": ["yae"], "name": "yae", "set": "compounds", "confusable": ["ㅐ"]},
    "ㅔ": {"roman": ["e"], "name": "e", "set": "compounds", "confusable": ["ㅐ", "ㅖ"]},
    "ㅖ": {"roman": ["ye"], "name": "ye", "set": "compounds", "confusable": ["ㅔ"]},
    "ㅘ": {"roman": ["wa"], "name": "wa", "set": "compounds", "confusable": ["ㅝ"]},
    "ㅙ": {"roman": ["wae"], "name": "wae", "set": "compounds", "confusable": ["ㅞ"]},
    "ㅚ": {"roman": ["oe"], "name": "oe", "set": "compounds", "confusable": ["ㅟ"]},
    "ㅝ": {"roman": ["wo"], "name": "wo", "set": "compounds", "confusable": ["ㅘ"]},
    "ㅞ": {"roman": ["we"], "name": "we", "set": "compounds", "confusable": ["ㅙ"]},
    "ㅟ": {"roman": ["wi"], "name": "wi", "set": "compounds", "confusable": ["ㅚ"]},
    "ㅢ": {"roman": ["ui"], "name": "ui", "set": "compounds", "confusable": []},
}

# ── Terminal styling ─────────────────────────────────────────────────────

# Enable ANSI on Windows
if sys.platform == "win32":
    os.system("")

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
RESET = "\033[0m"
CLEAR = "\033[2J\033[H"


def green(s):
    return f"{GREEN}{s}{RESET}"


def red(s):
    return f"{RED}{s}{RESET}"


def yellow(s):
    return f"{YELLOW}{s}{RESET}"


def cyan(s):
    return f"{CYAN}{s}{RESET}"


def dim(s):
    return f"{DIM}{s}{RESET}"


def bold(s):
    return f"{BOLD}{s}{RESET}"


# ── Progress persistence ───────────────────────────────────────

PROGRESS_PATH = Path(__file__).parent / "data" / "flash_progress.json"


def load_progress():
    if PROGRESS_PATH.exists():
        with open(PROGRESS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {
        "correct": {},
        "wrong": {},
        "confusion_counts": {},
        "total_rounds": 0,
        "best_streak": 0,
    }


def save_progress(progress):
    PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


# ── Distractor selection ─────────────────────────────────────────────────


def pick_distractors(target, pool, confusion_counts, n=3):
    """Pick N distractors, favoring confused pairs and same-set jamo."""
    candidates = [j for j in pool if j != target]
    target_info = JAMO[target]

    # Prefer confusable pairs that the user has actually confused
    confused = []
    for c in target_info.get("confusable", []):
        pair_key = "|".join(sorted([target, c]))
        if confusion_counts.get(pair_key, 0) >= 2 and c in candidates:
            confused.append(c)

    # Fill from same set, then any
    same_set = [j for j in candidates if JAMO[j]["set"] == target_info["set"] and j not in confused]
    other = [j for j in candidates if j not in same_set and j not in confused]

    chosen = confused[:]
    random.shuffle(same_set)
    random.shuffle(other)

    chosen += same_set
    chosen += other

    return chosen[:n]


# ── Game loop ────────────────────────────────────────────────────────────


def play(jamo_pool, direction=None, progress=None):
    """
    Interactive flashcard drill.

    direction: "h2r" (hangul→roman), "r2h" (roman→hangul), or None (mixed)
    progress: dict from load_progress() — modified in place
    """
    if progress is None:
        progress = load_progress()
    pool = list(jamo_pool)
    if not pool:
        print(red("No jamo in selected set. Try --hard or --set basic."))
        return

    streak = 0
    session_correct = 0
    session_total = 0

    print(CLEAR)
    print(bold("╔══════════════════════════════════════╗"))
    print(bold("║      Hangul Flashcard Drill          ║"))
    print(bold("╠══════════════════════════════════════╣"))
    print(bold("║") + "  Type 'q' to quit, 's' for stats  " + bold("║"))
    print(bold("╚══════════════════════════════════════╝"))
    print()

    if direction:
        mode_label = "Hangul→Roman" if direction == "h2r" else "Roman→Hangul"
        print(dim(f"Direction: {mode_label}  |  Pool: {len(pool)} jamo"))
    else:
        print(dim(f"Direction: mixed  |  Pool: {len(pool)} jamo"))
    print()

    while True:
        # Decide direction
        if direction:
            d = direction
        else:
            d = random.choice(["h2r", "r2h"])

        # Pick target jamo — weighted toward confused/wrong items
        weights = []
        for j in pool:
            w = 1.0
            w += progress["wrong"].get(j, 0) * 1.5
            # Boost if part of a confused pair
            for pair_key, count in progress.get("confusion_counts", {}).items():
                if j in pair_key.split("|"):
                    w += count * 0.5
            weights.append(max(w, 0.5))
        target = random.choices(pool, weights=weights, k=1)[0]

        info = JAMO[target]

        if d == "h2r":
            correct = _ask_h2r(target, info, progress)
        else:
            correct = _ask_r2h(target, info, pool, progress.get("confusion_counts", {}), progress)

        if correct is None:
            # Non-answer (stats, etc.) — re-ask same question
            continue

        session_total += 1

        if correct:
            session_correct += 1
            streak += 1
            progress["correct"][target] = progress["correct"].get(target, 0) + 1

            # Reduce wrong weight on consecutive correct
            if streak >= 3:
                progress["wrong"][target] = max(0, progress["wrong"].get(target, 0) - 1)

            print(f"  {green('✓')}  Streak: {bold(str(streak))}")
        else:
            streak = 0
            progress["wrong"][target] = progress["wrong"].get(target, 0) + 1
            print(f"  {red('✗')}  Correct: {green('/'.join(info['roman']))}")
            print()

        if streak > progress.get("best_streak", 0):
            progress["best_streak"] = streak

        progress["total_rounds"] = progress.get("total_rounds", 0) + 1

        # Save every 10 rounds
        if progress["total_rounds"] % 10 == 0:
            save_progress(progress)

        # Check for quit/stats commands at the prompt
        print()


def _ask_h2r(target, info, progress):
    """Hangul→Roman: show Hangul, accept any valid romanization."""
    # Build prompt
    print(f"  {bold(target)}  ({dim(info['name'])})")
    print(f"  Romanization: ", end="")
    sys.stdout.flush()

    try:
        answer = input().strip()
    except KeyboardInterrupt:
        print()
        raise SystemExit(0)
    except EOFError:
        print()
        return False

    if answer.lower() == "q":
        raise SystemExit(0)
    if answer.lower() == "s":
        _show_stats(progress)
        return None

    valid = [r.lower() for r in info["roman"]]
    return answer.lower() in valid


def _ask_r2h(target, info, pool, confusion_counts, progress):
    """Roman→Hangul: show romanization, user picks from numbered Hangul options."""
    roman_display = "/".join(info["roman"])

    # Pick 3 distractors
    distractors = pick_distractors(target, pool, confusion_counts, n=3)
    if len(distractors) < 3:
        # Pad from full JAMO
        all_others = [j for j in JAMO if j != target and j not in distractors]
        random.shuffle(all_others)
        distractors += all_others[: 3 - len(distractors)]

    choices = [target] + distractors
    random.shuffle(choices)
    correct_idx = choices.index(target) + 1

    # Build display
    print(f"  {bold(roman_display)}  →  which Hangul?")
    print()
    for i, j in enumerate(choices, 1):
        label = JAMO[j]["name"]
        print(f"  {bold(str(i))}) {j}  {dim(f'({label})')}")
    print()
    print(f"  Pick 1-{len(choices)}: ", end="")
    sys.stdout.flush()

    try:
        answer = input().strip()
    except KeyboardInterrupt:
        print()
        raise SystemExit(0)
    except EOFError:
        print()
        return False

    if answer.lower() == "q":
        raise SystemExit(0)
    if answer.lower() == "s":
        _show_stats(progress)
        return None

    try:
        pick = int(answer)
    except ValueError:
        return False

    if pick == correct_idx:
        return True

    # Track confusion
    if 1 <= pick <= len(choices) and pick != correct_idx:
        chosen_jamo = choices[pick - 1]
        pair_key = "|".join(sorted([target, chosen_jamo]))
        progress.setdefault("confusion_counts", {})
        progress["confusion_counts"][pair_key] = progress["confusion_counts"].get(pair_key, 0) + 1

    return False


_stats_last_shown = None


def _show_stats(progress):
    """Show session stats without interrupting the game flow."""
    total = sum(progress["correct"].values()) + sum(progress["wrong"].values())
    rank = _get_rank(progress)

    print()
    print(dim("  ── Session Stats ──"))
    print(f"  Total answered: {total}")
    print(f"  Best streak:    {progress.get('best_streak', 0)}")
    print(f"  Rank:           {rank}")
    if progress.get("confusion_counts"):
        worst = sorted(progress["confusion_counts"].items(), key=lambda x: -x[1])[:3]
        print(f"  Top confusions: ", end="")
        parts = []
        for pair, count in worst:
            a, b = pair.split("|")
            parts.append(f"{a}↔{b} ({count}×)")
        print(", ".join(parts))
    print()


def _get_rank(progress):
    """Novice → Master based on accuracy and volume."""
    correct = sum(progress["correct"].values())
    wrong = sum(progress["wrong"].values())
    total = correct + wrong
    if total < 10:
        return dim("Novice")
    pct = correct / total if total > 0 else 0
    if pct >= 0.95 and total >= 100:
        return bold(green("Master"))
    elif pct >= 0.85:
        return green("Advanced")
    elif pct >= 0.70:
        return yellow("Intermediate")
    else:
        return "Beginner"


# ── Lookup mode ──────────────────────────────────────────────────────────


def lookup(query):
    """Quick one-shot lookup: Hangul→roman or roman→Hangul."""
    # Check if query is a Hangul character
    if query in JAMO:
        info = JAMO[query]
        rom = "/".join(info["roman"])
        print(f"{bold(query)} → {green(rom)}  ({info['name']})")
        return

    # Search by romanization
    query_lower = query.lower()
    matches = []
    for j, info in JAMO.items():
        if query_lower in [r.lower() for r in info["roman"]]:
            matches.append((j, info))

    if matches:
        for j, info in matches:
            rom = "/".join(info["roman"])
            print(f"{bold(query_lower)} → {green(j)}  ({rom}, {info['name']})")
    else:
        # Partial match
        partials = []
        for j, info in JAMO.items():
            for r in info["roman"]:
                if query_lower in r.lower():
                    partials.append((j, "/".join(info["roman"]), info["name"]))
        if partials:
            print(dim(f"No exact match for '{query}'. Similar:"))
            for j, rom, name in partials:
                print(f"  {green(j)} = {rom}  ({name})")
        else:
            print(red(f"No match for '{query}'"))


# ── Main ──────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Hangul↔Roman flashcard drill — no Hangul keyboard needed"
    )
    parser.add_argument(
        "--set",
        default="basic",
        choices=["consonants", "vowels", "basic", "compounds", "all"],
        help="Jamo set to drill (default: basic = consonants + vowels)",
    )
    parser.add_argument(
        "--direction",
        choices=["h2r", "r2h"],
        help="Lock to one direction (default: random mix)",
    )
    parser.add_argument(
        "--hard",
        action="store_true",
        help="Include all 40 jamo including compound consonants/vowels",
    )
    parser.add_argument(
        "--lookup",
        metavar="CHAR",
        help="Quick lookup: --lookup g → shows hangul, --lookup ㄱ → shows roman",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show lifetime stats and exit",
    )
    args = parser.parse_args()

    # Lookup mode (no game)
    if args.lookup:
        lookup(args.lookup)
        return

    # Stats mode
    if args.stats:
        progress = load_progress()
        correct = sum(progress["correct"].values())
        wrong = sum(progress["wrong"].values())
        total = correct + wrong
        accuracy = (correct / total * 100) if total > 0 else 0
        rank = _get_rank(progress)

        print(f"Total: {total}  |  Correct: {green(str(correct))}  |  Wrong: {red(str(wrong))}  |  {accuracy:.1f}%")
        print(f"Best streak: {progress.get('best_streak', 0)}  |  Rank: {rank}")
        if progress.get("confusion_counts"):
            print("\nConfusion pairs:")
            for pair, count in sorted(progress["confusion_counts"].items(), key=lambda x: -x[1])[:10]:
                a, b = pair.split("|")
                print(f"  {a} ↔ {b}: {count}×")
        return

    # Build pool
    set_map = {
        "consonants": [j for j, i in JAMO.items() if i["set"] == "consonants"],
        "vowels": [j for j, i in JAMO.items() if i["set"] == "vowels"],
        "basic": [
            j for j, i in JAMO.items() if i["set"] in ("consonants", "vowels")
        ],
        "compounds": [j for j, i in JAMO.items() if i["set"] == "compounds"],
        "all": list(JAMO.keys()),
    }

    if args.hard:
        pool = set_map["all"]
    else:
        pool = set_map[args.set]

    progress = load_progress()
    try:
        play(pool, direction=args.direction, progress=progress)
    except SystemExit:
        save_progress(progress)

        correct = sum(progress["correct"].values())
        wrong = sum(progress["wrong"].values())
        total = correct + wrong
        accuracy = (correct / total * 100) if total > 0 else 0
        print(f"\n{dim('Session saved.')}  {green(str(correct))} correct / {red(str(wrong))} wrong = {accuracy:.0f}%")
        print(f"Best streak ever: {progress.get('best_streak', 0)}")


if __name__ == "__main__":
    main()
