#!/usr/bin/env python3
"""Pedagogical-behavior probe (10 questions across 5 dimensions).

Measures whether TUTORING behavior survived fine-tuning, not just factual
recall: correction handling, mnemonic/memory aids, explanation depth (why),
follow-up/context retention (two-turn), and encouragement/learner tone.

Serving format matches curriculum_probe.py (raw empty-think-block, temp 0).
Multi-turn questions (7, 8) embed turn-1's assistant answer as conversation
history — no think block on history turns, empty think block only on the
generation turn (matching Modelfile.nothink semantics).

Config (env, optional):
    HANGUL_MODEL / OLLAMA_API  (same as curriculum_probe.py)

Output per question: tag, elapsed, think-bleed, length, tone-marker scan, raw
answer. A hang/timeout prints [HANG] and the run continues (per-question
try/except) — important because OOD multi-turn inputs can loop forever.

Baseline results are recorded in evals/README.md.
"""
import json
import os
import time
import urllib.request

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
    payload = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "raw": True,
        "stream": False,
        "options": {"temperature": 0},
    }).encode("utf-8")
    req = urllib.request.Request(
        API, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))["response"].strip()


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


def markers(text: str) -> str:
    low = text.lower()
    found = [m for m in TONE_MARKERS if m in low]
    return ", ".join(found) if found else "(none)"


def emit(tag: str, question: str, answer: str, dt: float) -> None:
    bleed = "<think>" in answer or " response" in answer
    print("=" * 78)
    print(f"[{tag}]  ({dt:.0f}s)  think-bleed={bleed}  len={len(answer)} chars")
    print(f"Q: {question}")
    print(f"markers: {markers(answer)}")
    print("-" * 78)
    print(answer)
    print()


def run(tag: str, question: str, gen) -> str:
    """Run one generation with per-question try/except. Returns answer ('' on hang)."""
    t0 = time.time()
    try:
        ans = gen()
        emit(tag, question, ans, time.time() - t0)
        return ans
    except Exception as e:
        print("=" * 78)
        print(f"[{tag}]  [HANG/TIMEOUT after {time.time()-t0:.0f}s]  {type(e).__name__}")
        print(f"Q: {question}")
        print()
        return ""


def main() -> None:
    # --- correction / mnemonic / why (single-turn) ---
    for tag, q in [
        ("correction-1", "I've been studying Hangul and I think ㅐ sounds like the 'a' in 'father.' Am I right?"),
        ("correction-2", "My teacher said batchim can make any of its 24 consonant sounds. Is that correct?"),
        ("mnemonic-1", "I keep mixing up ㄱ and ㄴ. Can you help me remember which is which?"),
        ("mnemonic-2", "What's a good way to remember that ㅡ sounds like 'eu' and not 'oo'?"),
        ("why-1", "Why does batchim only produce 7 sounds even though there are more consonants?"),
        ("why-2", "Why does ㄹ sometimes sound like 'r' and sometimes like 'l'?"),
    ]:
        run(tag, q, lambda q=q: ask(q))

    # --- follow-up / context retention (two-turn) ---
    q1 = "What is batchim?"
    a1 = run("followup-1a", q1, lambda: ask(q1))
    q2 = "Can you give me an example word where batchim changes the pronunciation?"
    run("followup-1b", q2, lambda: ask_followup(q1, a1, q2))

    q1 = "How many basic vowels are there in Korean?"
    a1 = run("followup-2a", q1, lambda: ask(q1))
    q2 = "Which ones do beginners usually find hardest?"
    run("followup-2b", q2, lambda: ask_followup(q1, a1, q2))

    # --- encouragement / learner tone (single-turn) ---
    for tag, q in [
        ("encourage-1", "I've been studying Hangul for a week and I still can't read syllable blocks. Am I doing something wrong?"),
        ("encourage-2", "This is really hard. Is Hangul actually as easy as people say?"),
    ]:
        run(tag, q, lambda q=q: ask(q))

    print("DONE")


if __name__ == "__main__":
    main()
