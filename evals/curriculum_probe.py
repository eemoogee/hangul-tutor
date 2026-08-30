#!/usr/bin/env python3
"""Structured Hangul curriculum probe (22 questions).

Measures factual knowledge coverage across six areas: consonants, vowels,
batchim, syllable structure, stroke order, romanization. Serves the target
model in NON-thinking mode via a raw empty-think-block prompt, so results
reflect knowledge rather than the Qwen3 chain-of-thought bug.

Usage:
    python evals/curriculum_probe.py

Config (env, optional):
    HANGUL_MODEL   Ollama model name (default: hf.co/eemoogee/hangul-expert-qwen3-8b)
    OLLAMA_API     Ollama base URL  (default: http://localhost:11434)

Each entry prints: area, question, EXPECTED, think-bleed flag, raw answer.
Grade manually against EXPECTED. Baseline results are recorded in evals/README.md.
"""
import json
import os
import time
import urllib.request

MODEL = os.environ.get("HANGUL_MODEL", "hf.co/eemoogee/hangul-expert-qwen3-8b")
API = os.environ.get("OLLAMA_API", "http://localhost:11434")
TIMEOUT = 150

# (area, question, expected)
PROBE = [
    ("consonant", "What sound does ㄱ make?", "soft g or k (g in 'go' / k in 'skate')"),
    ("consonant", "What sound does ㄷ make?", "'d' sound"),
    ("consonant", "What sound does ㅂ make?", "'b' sound"),
    ("consonant", "What is the romanization of ㅅ?", "'s'"),
    ("consonant", "What sound does ㄲ make?", "tensed/strong 'kk' (double ㄱ)"),
    ("consonant", "What sound does ㅆ make?", "tensed/strong 'ss' (double ㅅ)"),
    ("vowel", "What sound does ㅓ make?", "'eo' sound"),
    ("vowel", "What sound does ㅗ make?", "'oh/o' sound"),
    ("vowel", "What sound does ㅜ make?", "'oo/u' sound"),
    ("vowel", "What is the romanization of ㅡ?", "'eu'"),
    ("vowel", "What sound does ㅐ make?", "'ae' sound (compound vowel)"),
    ("vowel", "What sound does ㅘ make?", "'wa' sound (compound vowel)"),
    ("batchim", "What is batchim?", "optional final consonant at bottom of syllable"),
    ("batchim", "What is 받침?", "final consonant (batchim)"),
    ("batchim", "What sound does ㄱ make when it is a batchim at the end of a syllable?", "unreleased 'k' (7-sound rule)"),
    ("batchim", "How many distinct sounds can a batchim represent?", "7 representative sounds"),
    ("syllable", "What are the parts of a Korean syllable block?", "initial consonant + vowel + optional final consonant (batchim)"),
    ("syllable", "How are Korean syllables written?", "written in blocks"),
    ("stroke", "What is the stroke order for writing the letter ㄱ?", "single stroke, top-to-bottom then left-to-right"),
    ("stroke", "What is the stroke order for writing the letter ㅁ?", "4 strokes, box shape"),
    ("romanization", "What is the romanization of ㄹ?", "'r' or 'l'"),
    ("romanization", "What is the romanization of the syllable 한?", "'han'"),
]


def ask(question: str) -> str:
    prompt = (
        "<|im_start|>user\n"
        f"{question}<|im_end|>\n"
        "<|im_start|>assistant\n"
        "<think>\n\n</think>\n\n"
    )
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


def main() -> None:
    for i, (area, q, expected) in enumerate(PROBE, 1):
        t0 = time.time()
        try:
            ans = ask(q)
            dt = time.time() - t0
            bleed = "<think>" in ans or " response" in ans
            print(f"### [{i}/{len(PROBE)}] {area.upper()} :: {q}  [{dt:.0f}s]")
            print(f"    EXPECTED: {expected}")
            print(f"    THINK-BLEED: {bleed}")
            print(f"    ANSWER: {ans!r}")
        except Exception as e:
            dt = time.time() - t0
            print(f"### [{i}/{len(PROBE)}] {area.upper()} :: {q}  [ERROR after {dt:.0f}s]")
            print(f"    EXPECTED: {expected}")
            print(f"    {type(e).__name__}: {e}")
        print()


if __name__ == "__main__":
    main()
