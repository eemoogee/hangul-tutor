"""PROBE — how many pool syllables per lesson are bare CV vs batchim?

WHEN TO RUN: before briefing or building any mode that must distinguish
bare-CV syllables from batchim ones (e.g. decompose_syllable, build_syllable),
or any time a `if jong: return self._spell_question(lesson)` guard is added and
you need to know how often it will fire instead of the real mode.

WHY IT MATTERS: a guard that rejects batchim is only safe if lessons still have
bare-CV items left. Measured 2026-09: 102/136 pool syllables are bare CV (75%),
lessons 2-9 are 100% bare CV (so the new mode is fully usable there), but
lessons 10-11 are 100% batchim (22 syllables, zero bare CV) — so a guard makes
the mode correctly ABSENT in those two lessons rather than degraded.

READ-ONLY: instantiates HangulQuiz and inspects curriculum + _decompose_syllable.
Touches nothing on disk.

RUN:  python scripts/_probe_pool_cv_vs_batchim.py   (from the repo root)
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hangul_quiz_engine import HangulQuiz

q = HangulQuiz()

print(f"{'id':>3} {'lesson title':<34} {'pool':>5} {'bare CV':>8} {'batchim':>8}  {'%batchim':>8}")
print("-" * 78)
rows = []
for lesson in q.curriculum["lessons"]:
    pool = lesson.get("practice_syllables") or lesson.get("example_syllables")
    if not pool:
        continue
    bare = b = 0
    for s in pool:
        cho, jung, jong = q._decompose_syllable(s)
        if not cho and not jung:
            continue          # bare jamo, not a composed block
        if jong:
            b += 1
        else:
            bare += 1
    tot = bare + b
    pct = (b / tot * 100) if tot else 0
    rows.append((lesson["id"], lesson.get("title", "")[:33], len(pool), bare, b, pct))
    print(f"{lesson['id']:>3} {lesson.get('title','')[:33]:<34} {len(pool):>5} {bare:>8} {b:>8}  {pct:>7.1f}%")

print("-" * 78)
tb = sum(r[3] for r in rows); tt = sum(r[4] for r in rows)
print(f"TOTAL composed-block syllables in all pools: {tb+tt}")
print(f"  bare CV (usable by decompose): {tb}  ({tb/(tb+tt)*100:.1f}%)")
print(f"  batchim (-> falls back to spell): {tt}  ({tt/(tb+tt)*100:.1f}%)")
print()
print("Lessons that would be 100% fallback (every pool item has batchim):")
hits = [r for r in rows if r[3] == 0]
if hits:
    for r in hits:
        print(f"  lesson {r[0]}: {r[1]}  (pool={r[2]})")
else:
    print("  (none)")
print()
print("Lessons with ZERO bare-CV items but pool present: "
      f"{sum(1 for r in rows if r[3]==0)}/{len(rows)}")
