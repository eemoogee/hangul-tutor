#!/usr/bin/env python3
"""Smoke test for the RAG fact lookup system.

Prints the augmented prompt build_augmented_prompt() produces for six
representative questions, so fact retrieval and prompt injection can be
inspected directly.
"""
from rag_facts import build_augmented_prompt

QUESTIONS = [
    "What is batchim?",
    "How do Korean syllable blocks work?",
    "What sound does ㅎ make?",
    "What is the difference between ㄱ and ㅋ?",
    "Is ㅏ a consonant or a vowel?",
    "What does ㅇ do at the start of a syllable?",
]


def main():
    for i, q in enumerate(QUESTIONS, 1):
        print("=" * 70)
        print(f"Q{i}: {q}")
        print("=" * 70)
        print(build_augmented_prompt(q))
        print()


if __name__ == "__main__":
    main()
