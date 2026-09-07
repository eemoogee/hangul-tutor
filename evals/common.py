#!/usr/bin/env python3
"""Shared mechanics for hangul-tutor eval probes.

Provides:
    git_commit()       — current repo HEAD hash (8-char short)
    generate()         — raw Ollama /api/generate call
    add_log_path_arg() — standard --log-path argparse argument

Each probe imports this via sys.path — no package setup needed:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from common import git_commit, generate as _generate, add_log_path_arg

Probe-specific schema, grading logic, and TIMEOUT stay in each probe.
"""
import json
import subprocess
import urllib.request
from pathlib import Path


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


def add_log_path_arg(parser, default: str) -> None:
    """Add --log-path to an argparse.ArgumentParser with a probe-specific default."""
    parser.add_argument(
        "--log-path",
        default=default,
        help="Path to append the raw per-item JSONL log to (default: %(default)s).",
    )
