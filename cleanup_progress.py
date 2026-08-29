"""
cleanup_progress.py — One-time cleanup for hangul-tutor's data/user_progress.json.

Removes stale invalid entries left over from an already-fixed bug in an
earlier version of the app (things like "wrong", "dh", "r/la" showing up
as if they were letters/confusion pairs). The current code already
defensively filters these out when reading, so this isn't required for
the app to work correctly — it just tidies the actual file on disk so a
manual look at it (or a tool like Hermes) doesn't get confused by the
leftovers.

Makes a timestamped backup before writing anything.

Usage:
    python cleanup_progress.py
    (run from inside your hangul-tutor project folder, or edit PROGRESS_PATH below)
"""

import json
import shutil
import time
from pathlib import Path

PROGRESS_PATH = Path("data") / "user_progress.json"

_JAMO_CHARS = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"


def looks_like_hangul(s: str) -> bool:
    if not s or len(s) != 1:
        return False
    if 0xAC00 <= ord(s) <= 0xD7A3:
        return True
    return s in _JAMO_CHARS


def main():
    if not PROGRESS_PATH.exists():
        print(f"Couldn't find {PROGRESS_PATH} — run this from your hangul-tutor project folder,")
        print("or edit PROGRESS_PATH at the top of this script to point at the right location.")
        return

    with open(PROGRESS_PATH, encoding="utf-8") as f:
        data = json.load(f)

    backup_path = PROGRESS_PATH.with_suffix(f".backup-{int(time.time())}.json")
    shutil.copy(PROGRESS_PATH, backup_path)
    print(f"Backed up to {backup_path}")

    removed_mastered = []
    mastered = data.get("mastered_letters", {})
    for key in list(mastered.keys()):
        if not looks_like_hangul(key):
            removed_mastered.append((key, mastered.pop(key)))

    removed_confusion = []
    confusion = data.get("confusion_counts", {})
    for key in list(confusion.keys()):
        parts = key.split("↔")
        if len(parts) != 2 or not all(looks_like_hangul(p) for p in parts):
            removed_confusion.append((key, confusion.pop(key)))

    if removed_mastered:
        print(f"\nRemoved {len(removed_mastered)} invalid mastered_letters entries:")
        for k, v in removed_mastered:
            print(f"   {k!r}: {v}")
    else:
        print("\nNo invalid mastered_letters entries found.")

    if removed_confusion:
        print(f"\nRemoved {len(removed_confusion)} invalid confusion_counts entries:")
        for k, v in removed_confusion:
            print(f"   {k!r}: {v}")
    else:
        print("No invalid confusion_counts entries found.")

    if removed_mastered or removed_confusion:
        with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nSaved cleaned file to {PROGRESS_PATH}")
    else:
        print("\nNothing to clean — file left untouched.")


if __name__ == "__main__":
    main()
