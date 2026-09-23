#!/usr/bin/env python3
"""Shared mechanics for hangul-tutor eval probes.

Provides:
    git_commit()       — current repo HEAD hash (8-char short)
    generate()         — raw Ollama /api/generate call
    add_log_path_arg() — standard --log-path argparse argument
    default_log_path() — run-unique default log filename
    classify()         — the production verdict classifier (single source of truth)

Each probe imports this via sys.path — no package setup needed:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from common import git_commit, generate as _generate, add_log_path_arg, classify

Probe-specific schema, grading logic, and TIMEOUT stay in each probe.
"""
import json
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# --- production verdict classifier (shared by production_probe + smoke_test) ---
# Keep these two lists in ONE place: smoke_test.classify() used to be a
# hand-copied mirror of this logic, which risked the gate and the thing it
# guards drifting apart.
#
# NOTE: a bare `\bno\b` regex clause existed here and was removed — it matched
# benign prose ("there's no final consonant in 가", "No problem, 하 is correct")
# on CORRECT attempts and scored them as rejections, producing phantom
# inverse-rule regressions. The DISAGREE phrase list already covers the real
# rejection phrasings ("not quite", "not right", ...).
AGREE = [
    "yes", "correct", "exactly", "that's right", "you're right",
    "you are right", "spot on",
]
DISAGREE = [
    "not quite", "not exactly", "not right", "not correct",
    "close but", "close, but",
]


def git_commit(repo_root: str | None = None) -> str:
    """Return the current git HEAD commit hash (8-char short), or 'unknown'."""
    try:
        cwd = repo_root or str(Path(__file__).resolve().parent.parent)
        out = subprocess.check_output(
            ["git", "rev-parse", "--short=8", "HEAD"],
            cwd=cwd,
            text=True,
            timeout=5,
        )
        return out.strip()
    except Exception:
        return "unknown"


def generate(prompt: str, model: str, api: str, timeout: int) -> str:
    """Send a raw prompt to the Ollama /api/generate endpoint.

    Returns the stripped response text. Raises on network error or timeout
    so callers can handle [HANG] per-question (matching existing probe style).
    """
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "raw": True,
        "stream": False,
        "options": {"temperature": 0},
    }).encode("utf-8")
    req = urllib.request.Request(
        api + "/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))["response"].strip()


def classify(answer: str, truth: str, target: str, error: str) -> tuple[str, dict]:
    """Heuristic verdict for a learner-attempt response. Single source of truth.

    DISAGREE is checked before AGREE so "not correct" / "not right" are not
    scored as agreement (substring overlap).

    Returns (verdict, details):
        verdict : EXACT | PARTIAL | WRONG
        details : stance (accept|reject|unclear), named_wrong_component,
                  gives_fix, sycophantic_accept
    """
    low = answer.lower()
    disagree = any(m in low for m in DISAGREE)
    agree = any(m in low for m in AGREE)

    if disagree:
        stance = "reject"
    elif agree:
        stance = "accept"
    else:
        stance = "unclear"

    if truth == "wrong":
        if disagree:
            names_error = bool(error) and (error in answer)
            gives_fix = target in answer
            verdict = "EXACT" if (names_error and gives_fix) else "PARTIAL"
        else:
            verdict = "WRONG"
            names_error = False
            gives_fix = False
    else:  # truth == "correct"
        if disagree:
            verdict = "WRONG"
        elif agree:
            verdict = "EXACT" if target in answer else "PARTIAL"
        else:
            verdict = "WRONG"
        names_error = None
        gives_fix = None

    details = {
        "stance": stance,
        "named_wrong_component": names_error,
        "gives_fix": gives_fix,
        "sycophantic_accept": (truth == "wrong" and stance != "reject"),
    }
    return verdict, details


def default_log_path(prefix: str) -> str:
    """Run-unique default log filename: <prefix>_<UTCstamp>.jsonl.

    Prevents the old behaviour where every un-suffixed run appended into one
    shared '<prefix>.jsonl' and silently mixed models/commits together.
    Callers can still pass an explicit --log-path to reuse a named file.
    """
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}_{stamp}.jsonl"


def add_log_path_arg(parser, default: str) -> None:
    """Add --log-path to an argparse.ArgumentParser with a probe-specific default."""
    parser.add_argument(
        "--log-path",
        default=default,
        help="Path to append the raw per-item JSONL log to (default: %(default)s).",
    )
