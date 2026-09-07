#!/usr/bin/env python3
"""Pedagogical-behavior probe (10 questions across 5 dimensions).

Measures whether TUTORING behavior survived fine-tuning, not just factual
recall: correction handling, mnemonic/memory aids, explanation depth (why),
follow-up/context retention (two-turn), and encouragement/learner tone.

Serving format matches curriculum_probe.py (raw empty-think-block, temp 0).
Multi-turn questions (7, 8) embed turn-1's assistant answer as conversation
history — no think block on history turns, empty think block only on the
generation turn (matching Modelfile.nothink semantics).

Usage:
    python evals/pedagogy_probe.py
    python evals/pedagogy_probe.py --log-path pedagogy_probe_raw_v12_rank32.jsonl

Config (env, optional):
    HANGUL_MODEL / OLLAMA_API  (same as curriculum_probe.py)

Output per question: tag, elapsed, think-bleed, length, tone-marker scan, raw
answer. A hang/timeout prints [HANG] and the run continues (per-question
try/except) — important because OOD multi-turn inputs can loop forever.

Per-item JSONL record (appended to --log-path):
    timestamp, model, git_commit, tag, turn, question,
    turn1_question, turn1_response,   <- null for single-turn / turn-1 items
    think_bleed, tone_markers, raw_response, response_time_s, timed_out

    Two-turn items produce two flat records (turn=1, turn=2). The turn-2
    record carries turn1_question and turn1_response so the full conversation
    is self-contained in that record alone.

Baseline results are recorded in evals/README.md.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import add_log_path_arg, generate as _generate, git_commit

MODEL = os.environ.get("HANGUL_MODEL", "hf.co/eemoogee/hangul-expert-qwen3-8b")
API = os.environ.get("OLLAMA_API", "http://localhost:11434")
TIMEOUT = 100

TONE_MARKERS = [
    "actually", "don't worry", "great question", "think of it this way",
    "you're doing", "you are doing", "normal", "easy", "correct", "exactly",
    "remember", "good news", "not wrong", "right on", "that's right",
    "you've got", "hang in", "keep going", "don't be", "it's okay", "it is okay",
]


def generate(prompt: str) -> str:
    return _generate(prompt, MODEL, API, TIMEOUT)


def ask(question: str) -> str:
    return generate(
        "<|im_start|>user\n"
        f"{question}<|im_end|>\n"
        "<|im_start|>assistant\n"
        "<think>\n\n</think>\n\n"
    )


def ask_followup(q1: str, a1: str, q2: str) -> str:
    return generate(
        "<|im_start|>user\n"
        f"{q1}<|im_end|>\n"
        "<|im_start|>assistant\n"
        f"{a1}<|im_end|>\n"
        "<|im_start|>user\n"
        f"{q2}<|im_end|>\n"
        "<|im_start|>assistant\n"
        "<think>\n\n</think>\n\n"
    )


def markers(text: str) -> list[str]:
    low = text.lower()
    return [m for m in TONE_MARKERS if m in low]


def emit(tag: str, question: str, answer: str, dt: float) -> None:
    bleed = "<think>" in answer or " response" in answer
    found = markers(answer)
    marker_str = ", ".join(found) if found else "(none)"
    print("=" * 78)
    print(f"[{tag}]  ({dt:.0f}s)  think-bleed={bleed}  len={len(answer)} chars")
    print(f"Q: {question}")
    print(f"markers: {marker_str}")
    print("-" * 78)
    print(answer)
    print()


def run(
    tag: str,
    question: str,
    gen,
    logf,
    commit: str,
    *,
    turn: int = 1,
    turn1_question: str | None = None,
    turn1_response: str | None = None,
) -> str:
    """Run one generation with per-question try/except. Writes one JSONL record.

    Returns the answer string ('' on hang/timeout).

    For two-turn sequences:
      Turn 1: call with default turn=1; turn1_question/turn1_response stay None.
      Turn 2: call with turn=2, turn1_question=q1, turn1_response=a1 so the
              record is self-contained (full context preserved).
    """
    ans = ""
    bleed = False
    timed_out = False
    t0 = time.time()
    try:
        ans = gen()
        dt = time.time() - t0
        bleed = "<think>" in ans or " response" in ans
        emit(tag, question, ans, dt)
    except Exception as e:
        dt = time.time() - t0
        timed_out = True
        print("=" * 78)
        print(f"[{tag}]  [HANG/TIMEOUT after {dt:.0f}s]  {type(e).__name__}")
        print(f"Q: {question}")
        print()

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "git_commit": commit,
        "tag": tag,
        "turn": turn,
        "question": question,
        "turn1_question": turn1_question,
        "turn1_response": turn1_response,
        "think_bleed": bleed,
        "tone_markers": markers(ans),
        "raw_response": ans,
        "response_time_s": dt,
        "timed_out": timed_out,
    }
    logf.write(json.dumps(record, ensure_ascii=False) + "\n")
    return ans


def main(log_path: str = "pedagogy_probe_raw.jsonl") -> None:
    commit = git_commit()
    with open(log_path, "a", encoding="utf-8") as logf:

        # --- correction / mnemonic / why (single-turn) ---
        for tag, q in [
            ("correction-1", "I've been studying Hangul and I think ㅐ sounds like the 'a' in 'father.' Am I right?"),
            ("correction-2", "My teacher said batchim can make any of its 24 consonant sounds. Is that correct?"),
            ("mnemonic-1", "I keep mixing up ㄱ and ㄴ. Can you help me remember which is which?"),
            ("mnemonic-2", "What's a good way to remember that ㅡ sounds like 'eu' and not 'oo'?"),
            ("why-1", "Why does batchim only produce 7 sounds even though there are more consonants?"),
            ("why-2", "Why does ㄹ sometimes sound like 'r' and sometimes like 'l'?"),
        ]:
            run(tag, q, lambda q=q: ask(q), logf, commit)

        # --- follow-up / context retention (two-turn) ---
        q1 = "What is batchim?"
        a1 = run("followup-1a", q1, lambda: ask(q1), logf, commit)
        q2 = "Can you give me an example word where batchim changes the pronunciation?"
        run(
            "followup-1b", q2,
            lambda: ask_followup(q1, a1, q2),
            logf, commit,
            turn=2, turn1_question=q1, turn1_response=a1,
        )

        q1 = "How many basic vowels are there in Korean?"
        a1 = run("followup-2a", q1, lambda: ask(q1), logf, commit)
        q2 = "Which ones do beginners usually find hardest?"
        run(
            "followup-2b", q2,
            lambda: ask_followup(q1, a1, q2),
            logf, commit,
            turn=2, turn1_question=q1, turn1_response=a1,
        )

        # --- encouragement / learner tone (single-turn) ---
        for tag, q in [
            ("encourage-1", "I've been studying Hangul for a week and I still can't read syllable blocks. Am I doing something wrong?"),
            ("encourage-2", "This is really hard. Is Hangul actually as easy as people say?"),
        ]:
            run(tag, q, lambda q=q: ask(q), logf, commit)

    print("DONE")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_log_path_arg(parser, "pedagogy_probe_raw.jsonl")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(log_path=args.log_path)
