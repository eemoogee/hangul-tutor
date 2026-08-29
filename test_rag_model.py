#!/usr/bin/env python3
"""RAG + model integration test.

Feeds the RAG-augmented prompt through the fine-tuned ``hangul-expert`` model
for a set of representative questions and prints the injected facts alongside
each model answer, plus a no-RAG baseline for the batchim question (the model's
known weak spot). Confirms the injected facts actually change the answers.

Usage:
    python test_rag_model.py

Requires a running Ollama server and the ``hangul-expert`` model.
"""
import json
import urllib.request

from rag_facts import build_augmented_prompt, get_relevant_facts

MODEL = "hangul-expert"
QUESTIONS = [
    "What is batchim?",
    "How do Korean syllable blocks work?",
    "What sound does ㅎ make?",
    "What is the difference between ㄱ and ㅋ?",
    "Is ㅏ a consonant or a vowel?",
    "What does ㅇ do at the start of a syllable?",
]


def generate(prompt: str, raw: bool = True) -> str:
    """Send a raw prompt to the local Ollama model and return its reply."""
    payload = json.dumps(
        {"model": MODEL, "prompt": prompt, "raw": raw, "stream": False}
    ).encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))["response"].strip()


def main() -> None:
    for q in QUESTIONS:
        facts = get_relevant_facts(q)
        print("=" * 72)
        print(f"Q: {q}")
        print(f"INJECTED ({len(facts)} facts):")
        for f in facts:
            print(f"    {f}")
        print(f"RAG ANSWER: {generate(build_augmented_prompt(q))}")
        print()

    print("=" * 72)
    print("BASELINE (no RAG) — What is batchim?")
    base_prompt = (
        "<|im_start|>system\nYou are a Hangul tutor.<|im_end|>\n"
        "<|im_start|>user\nWhat is batchim?<|im_end|>\n"
        "<|im_start|>assistant\n"
    )
    print(f"NO-RAG ANSWER: {generate(base_prompt)}")


if __name__ == "__main__":
    main()
