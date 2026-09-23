#!/usr/bin/env python3
"""Aggregate probe JSONL logs into a machine-readable run manifest.

Reads any number of probe log files (production / curriculum / pedagogy)
and emits one summary row per logical run plus a per-item breakdown. This
replaces hand-typing baselines into evals/README.md -- the JSONL is the
source of truth; this renders it.

Run identity is keyed on the **file**, because the file suffix is the real
run label (`_v12_rank32`, `_v11_3epoch`, ...). Within a file, rows are
further grouped by (model, git_commit) so a file that genuinely mixed two
models still reports separately. Model/commit are carried as attributes.

Rationale: the default model name is identical across many runs, and the
oldest logs predate the `model`/`git_commit` fields entirely -- so keying
on (model, commit) silently merged distinct runs. Keying on file does not.

The three probes have different schemas, so this script auto-detects the
probe type from the record fields:

    production_probe : classifier_verdict, stance, sycophantic_accept ...
    curriculum_probe : area, expected (no classifier_verdict -> manual grade)
    pedagogy_probe   : tone_markers, timed_out, turn

Usage:
    python evals/summarize.py                       # auto-discover, text
    python evals/summarize.py --format md           # markdown table
    python evals/summarize.py --format json --out manifest.json
    python evals/summarize.py --detail v12_rank32   # per-item detail
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

PROBE_PREFIXES = ("production_probe_raw", "curriculum_probe_raw", "pedagogy_probe_raw")


def detect_probe(rec: dict) -> str:
    """Best-effort probe-type detection from a single record."""
    if "classifier_verdict" in rec:
        return "production"
    if "tone_markers" in rec or "timed_out" in rec:
        return "pedagogy"
    if "area" in rec and "expected" in rec:
        return "curriculum"
    return "unknown"


def model_commit(rec: dict) -> str:
    """Model/commit label for a record; older logs lack these fields."""
    model = rec.get("model") or "<unknown-model>"
    commit = rec.get("git_commit") or "<no-commit>"
    return f"{model} @ {commit}"


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def summarize_production(records: list[dict]) -> dict:
    """Verdict counts + regression counters for one production run."""
    s = {
        "records": len(records),
        "EXACT": 0,
        "PARTIAL": 0,
        "WRONG": 0,
        "sycophantic_accept": 0,
        "inverse_rule": 0,
        "unstable_items": 0,
        "hangs": 0,
        "think_bleed": 0,
    }
    by_item: dict[int, dict[int, str]] = defaultdict(dict)
    times: list[float] = []
    for r in records:
        v = r.get("classifier_verdict", "UNKNOWN")
        if v in s:
            s[v] += 1
        if r.get("attempt_type") == "correct" and v == "WRONG":
            s["inverse_rule"] += 1
        if r.get("sycophantic_accept"):
            s["sycophantic_accept"] += 1
        if r.get("think_bleed"):
            s["think_bleed"] += 1
        if not r.get("model_raw_response"):
            s["hangs"] += 1
        if r.get("response_time_s"):
            times.append(r["response_time_s"])
        iid, rn = r.get("item_id"), r.get("run_number")
        if iid is not None and rn is not None:
            by_item[iid][rn] = v
    for runs in by_item.values():
        if len(runs) > 1 and len(set(runs.values())) > 1:
            s["unstable_items"] += 1
    s["mean_time_s"] = round(_mean(times), 1)
    return s


def summarize_curriculum(records: list[dict]) -> dict:
    """Curriculum is manually graded; report coverage + flags only."""
    return {
        "records": len(records),
        "items": len({r.get("item_id") for r in records}),
        "think_bleed": sum(1 for r in records if r.get("think_bleed")),
        "hangs": sum(1 for r in records if not r.get("raw_response")),
        "mean_time_s": round(_mean([r["response_time_s"] for r in records if r.get("response_time_s")]), 1),
    }


def summarize_pedagogy(records: list[dict]) -> dict:
    return {
        "records": len(records),
        "hangs": sum(1 for r in records if r.get("timed_out")),
        "think_bleed": sum(1 for r in records if r.get("think_bleed")),
        "mean_time_s": round(_mean([r["response_time_s"] for r in records if r.get("response_time_s")]), 1),
    }


def load(path: Path) -> list[dict]:
    out = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def collect(paths: list[Path]) -> list[dict]:
    """Return a list of run entries, one per (file, model/commit) group.

    File is the primary key (matches the run-suffix convention); rows are
    split further by model/commit inside a file so a mixed file still
    reports its models separately rather than silently averaging them.
    """
    runs: list[dict] = []
    for p in paths:
        recs = load(p)
        if not recs:
            continue
        probe = detect_probe(recs[0])
        grouped: dict[str, list[dict]] = defaultdict(list)
        for r in recs:
            grouped[model_commit(r)].append(r)
        for mc, rs in grouped.items():
            runs.append({
                "probe": probe,
                "file": p.name,
                "model_commit": mc,
                "records": rs,
                "timestamp_min": min((r.get("timestamp", "") for r in rs), default=""),
                "timestamp_max": max((r.get("timestamp", "") for r in rs), default=""),
            })
    return runs


def summarize(entry: dict) -> dict:
    probe = entry["probe"]
    if probe == "production":
        return summarize_production(entry["records"])
    if probe == "curriculum":
        return summarize_curriculum(entry["records"])
    if probe == "pedagogy":
        return summarize_pedagogy(entry["records"])
    return {"records": len(entry["records"])}


def render_table(runs: list[dict], fmt: str) -> str:
    if fmt == "json":
        manifest = [
            {
                "probe": e["probe"],
                "file": e["file"],
                "model_commit": e["model_commit"],
                "first_ts": e["timestamp_min"],
                "last_ts": e["timestamp_max"],
                "summary": summarize(e),
            }
            for e in runs
        ]
        manifest.sort(key=lambda m: (m["probe"], m["last_ts"]))
        return json.dumps(manifest, ensure_ascii=False, indent=2)

    if fmt == "md":
        lines = ["| Probe | Run file | Model @ commit | Recs | EXACT | PARTIAL | WRONG | Syco | Inverse | Unstable | Hangs | mean s |",
                 "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for e in runs:
            s = summarize(e)
            if e["probe"] == "production":
                lines.append(
                    f"| production | {e['file']} | {e['model_commit']} | {s['records']} | "
                    f"{s['EXACT']} | {s['PARTIAL']} | {s['WRONG']} | {s['sycophantic_accept']} | "
                    f"{s['inverse_rule']} | {s['unstable_items']} | {s['hangs']} | {s['mean_time_s']} |"
                )
            else:
                lines.append(
                    f"| {e['probe']} | {e['file']} | {e['model_commit']} | {s['records']} | "
                    f"- | - | - | - | - | - | {s.get('hangs', 0)} | {s.get('mean_time_s', '-')} |"
                )
        return "\n".join(lines)

    lines = []
    for e in runs:
        s = summarize(e)
        lines.append("=" * 78)
        lines.append(f"{e['probe']} :: {e['file']}   [{e['model_commit']}]")
        lines.append(f"  window: {e['timestamp_min']} .. {e['timestamp_max']}")
        for k, v in s.items():
            lines.append(f"  {k:22s} = {v}")
    return "\n".join(lines)


def render_detail(runs: list[dict], needle: str) -> str:
    lines = []
    for e in runs:
        if needle.lower() not in e["file"].lower() and needle.lower() not in e["model_commit"].lower():
            continue
        lines.append("=" * 78)
        lines.append(f"{e['probe']} :: {e['file']}   [{e['model_commit']}]")
        for r in sorted(e["records"], key=lambda r: (r.get("item_id", 0), r.get("run_number", 0), r.get("tag", ""))):
            v = r.get("classifier_verdict", "-")
            stance = r.get("stance", "-")
            q = r.get("question", "")
            ans = (r.get("model_raw_response") or r.get("raw_response") or "").replace("\n", " ")
            lines.append(f"  [{r.get('item_id','-')}.{r.get('run_number','-')}] {r.get('tag',''):14s} "
                         f"{v:8s} stance={stance:8s} {q}")
            lines.append(f"        -> {ans[:160]}")
    return "\n".join(lines) if lines else f"(no run matching {needle!r})"


def default_paths() -> list[Path]:
    found: list[Path] = []
    for prefix in PROBE_PREFIXES:
        found.extend(Path(p) for p in sorted(glob.glob(f"{prefix}*.jsonl")))
        found.extend(Path(p) for p in sorted(glob.glob(f"evals/{prefix}*.jsonl")))
    seen, out = set(), []
    for p in found:
        if p.name not in seen:
            seen.add(p.name)
            out.append(p)
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("paths", nargs="*", help="Probe JSONL files (default: auto-discover *_probe_raw*.jsonl)")
    p.add_argument("--format", choices=["text", "md", "json"], default="text")
    p.add_argument("--out", help="Write output to this file instead of stdout")
    p.add_argument("--detail", metavar="NEEDLE", help="Print per-item detail for runs matching NEEDLE")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    paths = [Path(p) for p in args.paths] if args.paths else default_paths()
    if not paths:
        print("No probe logs found.", file=sys.stderr)
        sys.exit(1)
    runs = collect(paths)
    out = render_detail(runs, args.detail) if args.detail else render_table(runs, args.format)
    if args.out:
        Path(args.out).write_text(out + "\n", encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(out)


if __name__ == "__main__":
    main()
