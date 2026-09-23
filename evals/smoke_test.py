#!/usr/bin/env python3
"""
Smoke-test eval — fast harness check to run after every Kaggle retrain.

Purpose: catch harness-level failures (wrong endpoint, broken classifier,
wrong model loaded, think-bleed regression) BEFORE trusting a full eval
sweep. NOT a quality measurement — 5 items, single run each, binary
PASS / WARN / ABORT output.

Five items:
  1. endpoint-sanity   — confirms /api/generate is reachable and returning text
  2. letter-fact-ㄱ    — romanization; WRONG = catastrophic or wrong model loaded
  3. batchim-trigger   — "What is 받침?"; core B3+ training target
  4. aspirated-tense   — ㄱ vs ㅋ distinction; B4 training layer
  5. classifier-check  — validates classify() on canned strings, no Ollama call
                         (uses common.classify — the single source of truth)

Exit codes:
    0   PASS  — all items passed
    1   ABORT — harness failure (endpoint down, or classifier broken);
                do NOT trust eval results
    2   WARN  — one or more model items failed; proceed with caution

Config (env, optional):
    HANGUL_MODEL   Ollama model name (default: hf.co/eemoogee/hangul-expert-qwen3-8b)
    OLLAMA_API     Ollama base URL   (default: http://localhost:11434)

Run:
    python evals/smoke_test.py
    HANGUL_MODEL=hf.co/eemoogee/hangul-expert-qwen3-8b python evals/smoke_test.py
"""

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

MODEL   = os.environ.get("HANGUL_MODEL", "hf.co/eemoogee/hangul-expert-qwen3-8b")
API     = os.environ.get("OLLAMA_API",   "http://localhost:11434")
TIMEOUT = 60  # shorter than production_probe.py (100s) — a hang here is itself a signal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import classify  # noqa: E402  (single source of truth)


# ---------------------------------------------------------------------------
# Ollama interface — identical to production_probe.py
# ---------------------------------------------------------------------------
def generate(prompt: str) -> str:
    payload = json.dumps({
        "model":   MODEL,
        "prompt":  prompt,
        "raw":     True,
        "stream":  False,
        "options": {"temperature": 0},
    }).encode("utf-8")
    req = urllib.request.Request(
        API + "/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))["response"].strip()


def ask(question: str) -> str:
    """Wrap a question in the plain ChatML + empty think-block serving format."""
    return generate(
        "<|im_start|>user\n"
        f"{question}<|im_end|>\n"
        "<|im_start|>assistant\n"
        "<think>\n\n</think>\n\n"
    )


# ---------------------------------------------------------------------------
# Individual item checks
# ---------------------------------------------------------------------------
def check_endpoint() -> tuple[str, str]:
    """Item 1: endpoint sanity — confirms /api/generate returns text.

    ABORT if unreachable or empty. WARN if think-bleed detected (Modelfile
    may not be loaded). Any non-empty response otherwise = PASS.
    """
    t0 = time.time()
    try:
        ans = ask("What sound does the letter ㅏ make?")
        dt  = time.time() - t0
        if not ans or len(ans) < 5:
            return "ABORT", f"response too short: {ans!r}"
        if "<think>" in ans:
            return "WARN", f"{dt:.1f}s — think-bleed detected (check Modelfile.nothink)"
        return "PASS", f"{dt:.1f}s"
    except Exception as e:
        return "ABORT", f"{type(e).__name__}: {e}"


def check_letter_fact() -> tuple[str, str]:
    """Item 2: ㄱ romanization — known correctly since v8.

    WARN (not ABORT) so a regression here shows up without halting — the
    classifier check (item 5) is the true abort gate.
    """
    t0 = time.time()
    try:
        ans = ask("What is the romanization of ㄱ?")
        dt  = time.time() - t0
        low = ans.lower()
        ok  = "g" in low or "k" in low   # ㄱ = g (initial) / k (final/isolated)
        return ("PASS" if ok else "WARN"), f"{dt:.1f}s"
    except Exception as e:
        return "WARN", f"{type(e).__name__}: {e}"


def check_batchim() -> tuple[str, str]:
    """Item 3: 받침 trigger — core B3+ training target."""
    t0 = time.time()
    try:
        ans = ask("What is 받침?")
        dt  = time.time() - t0
        low = ans.lower()
        ok  = "final consonant" in low or "받침" in ans or "batchim" in low
        return ("PASS" if ok else "WARN"), f"{dt:.1f}s"
    except Exception as e:
        return "WARN", f"{type(e).__name__}: {e}"


def check_aspirated() -> tuple[str, str]:
    """Item 4: ㄱ vs ㅋ distinction — B4 training layer."""
    t0 = time.time()
    try:
        ans = ask("What is the difference between ㄱ and ㅋ?")
        dt  = time.time() - t0
        low = ans.lower()
        ok  = any(kw in low for kw in ("aspir", "breath", "stronger", "puff", "more air"))
        return ("PASS" if ok else "WARN"), f"{dt:.1f}s"
    except Exception as e:
        return "WARN", f"{type(e).__name__}: {e}"


def check_classifier() -> tuple[str, str]:
    """Item 5: classifier self-check — NO Ollama call.

    Runs classify() against two canned strings to verify the AGREE/DISAGREE
    lists haven't drifted into false-positive/negative territory. This is the
    class of bug that made v10/v11 inverse counts untrustworthy ('almost'
    false-positive, etc.). ABORT if either canned check fails.
    """
    # Correct attempt — model confirms and names the target → should be EXACT
    v1, _ = classify(
        "Yes — 하 is correct.",
        truth="correct", target="하", error="",
    )
    if v1 != "EXACT":
        return "ABORT", f"correct-attempt canned string scored {v1} (expected EXACT)"

    # Wrong attempt — model rejects and names the error → should be EXACT
    v2, _ = classify(
        "Not quite — you used ㅓ instead of ㅏ. The correct syllable is 하.",
        truth="wrong", target="하", error="ㅓ",
    )
    if v2 != "EXACT":
        return "ABORT", f"wrong-attempt canned string scored {v2} (expected EXACT)"

    return "PASS", "no model call"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
ITEMS: list[tuple[str, object]] = [
    ("endpoint-sanity",  check_endpoint),
    ("letter-fact-ㄱ",   check_letter_fact),
    ("batchim-trigger",  check_batchim),
    ("aspirated-tense",  check_aspirated),
    ("classifier-check", check_classifier),
]

MARKER = {"PASS": "✓", "WARN": "!", "ABORT": "✗"}


def main() -> None:
    print(f"smoke_test.py — model={MODEL}  api={API}")
    print("=" * 64)

    aborts = 0
    warns  = 0

    for i, (tag, fn) in enumerate(ITEMS, 1):
        status, note = fn()
        m = MARKER.get(status, "?")
        print(f"  [{i}/{len(ITEMS)}] {tag:<22}  {m} {status:<6}  {note}")

        if status == "ABORT":
            aborts += 1
            print(f"\n  Stopping — item {i} is an ABORT gate.")
            break
        if status == "WARN":
            warns += 1

    print("=" * 64)
    if aborts:
        print("SMOKE TEST: ABORT")
        print("  Harness failure — do NOT trust eval results from this run.")
        print("  Fix the issue above before running the full eval suite.")
        sys.exit(1)
    elif warns:
        print(f"SMOKE TEST: WARN  ({warns} warning(s))")
        print("  Proceed with caution; inspect raw answers before calling results stable.")
        sys.exit(2)
    else:
        print("SMOKE TEST: PASS")
        print("  Endpoint up, classifier OK, model responding on expected targets.")
        sys.exit(0)


if __name__ == "__main__":
    main()
