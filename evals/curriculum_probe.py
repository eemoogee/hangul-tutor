#!/usr/bin/env python3
"""Structured Hangul curriculum probe (20 questions).

Measures factual knowledge coverage across five areas: consonants, vowels,
batchim, syllable structure, romanization. Serves the target
model in NON-thinking mode via a raw empty-think-block prompt, so results
reflect knowledge rather than the Qwen3 chain-of-thought bug.

Usage:
    python evals/curriculum_probe.py
    python evals/curriculum_probe.py --log-path curriculum_probe_raw_v12_rank32.jsonl

Config (env, optional):
    HANGUL_MODEL   Ollama model name (default: hf.co/eemoogee/hangul-expert-qwen3-8b)
    OLLAMA_API     Ollama base URL  (default: http://localhost:11434)

Each entry prints: area, question, EXPECTED, think-bleed flag, raw answer.
Grade manually against EXPECTED — auto-classification is intentionally absent
here to preserve raw evidence for later re-analysis. Baseline results in
evals/README.md.

Per-item JSONL record (appended to --log-path):
    timestamp, model, git_commit, item_id, area, question, expected,
    think_bleed, raw_response, response_time_s
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import add_log_path_arg, default_log_path, generate as _generate, git_commit

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
    return _generate(prompt, MODEL, API, TIMEOUT)


def main(log_path: str | None = None) -> None:
    if log_path is None:
        log_path = default_log_path("curriculum_probe_raw")
    commit = git_commit()
    with open(log_path, "a", encoding="utf-8") as logf:
        for i, (area, q, expected) in enumerate(PROBE, 1):
            ans = ""
            bleed = False
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

            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "model": MODEL,
                "git_commit": commit,
                "item_id": i,
                "area": area,
                "question": q,
                "expected": expected,
                "think_bleed": bleed,
                "raw_response": ans,
                "response_time_s": dt,
            }
            logf.write(json.dumps(record, ensure_ascii=False) + "\n")
            print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_log_path_arg(parser, default_log_path("curriculum_probe_raw"))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(log_path=args.log_path)
