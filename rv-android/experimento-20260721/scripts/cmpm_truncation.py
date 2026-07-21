#!/usr/bin/env python3
"""Health/truncation report for a cmpm run (base vs v2 model comparison).

Reads every ``data/results/<name>_NN/<name>_NN/tasks.json`` for the given run
name, deduplicates by task identity ``(apk_name, tool, variant, rep, timeout)``
(resume re-runs inflate ``tasks.json`` and re-emit ERROR tasks), and reports
completion + truncation.

Why truncation is a first-class metric here: the APE-RV refinement-crash bug can
kill the process before its own timeout, and the exit-code-decoupling bug makes
that task land as ``result.state == COMPLETED`` anyway. So ``state`` alone hides
truncation. The only signal is ``execution_time_seconds`` vs the nominal
``timeout``: a healthy task runs the full APE budget plus boot/install/coverage
overhead, so its wall time exceeds ``timeout``; a truncated task falls short.

    TRUNCATED := state == COMPLETED and execution_time_seconds < timeout

SURVIVORSHIP CAVEAT: short tasks finish first. Do not trust a truncation rate
computed before ``timeout + overhead`` (~370s at 300s) has elapsed for every
slot after a launch/restart — early reads show a false "everything truncated".
The script prints how many identities are still missing versus the expected
total so an immature read is visible.

Usage:
    python3 scripts/cmpm_truncation.py cmpm_base [--expected 543] [--list]
"""
import argparse
import glob
import json
import os
import sys
from collections import Counter

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")


def identity(cfg):
    tc = cfg.get("tool_config") or {}
    return (
        cfg.get("apk_name"),
        tc.get("name"),
        tc.get("variant"),
        cfg.get("repetition"),
        cfg.get("timeout"),
    )


def load_tasks(name):
    """All task dicts across every container dir for this run name."""
    pattern = os.path.join(RESULTS_DIR, f"{name}_*", f"{name}_*", "tasks.json")
    out = []
    for path in sorted(glob.glob(pattern)):
        with open(path) as fh:
            doc = json.load(fh)
        out.extend(doc.get("tasks", []))
    return out


def dedup(tasks):
    """One record per identity. Prefer COMPLETED; among those, the fullest run
    (max execution_time) — that is the recovered/resumed success."""
    best = {}
    for t in tasks:
        key = identity(t.get("config") or {})
        res = t.get("result") or {}
        rank = (
            1 if res.get("state") == "COMPLETED" else 0,
            res.get("execution_time_seconds") or 0,
        )
        if key not in best or rank > best[key][0]:
            best[key] = (rank, t)
    return [v[1] for v in best.values()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", help="run name, e.g. cmpm_base or cmpm_v2")
    ap.add_argument("--expected", type=int, default=543,
                    help="expected distinct identities (181 APKs x 3 reps)")
    ap.add_argument("--list", action="store_true",
                    help="list every truncated task")
    args = ap.parse_args()

    raw = load_tasks(args.name)
    if not raw:
        sys.exit(f"no tasks.json found for run '{args.name}' under {RESULTS_DIR}")
    tasks = dedup(raw)

    states = Counter((t.get("result") or {}).get("state") for t in tasks)
    completed = [t for t in tasks if (t.get("result") or {}).get("state") == "COMPLETED"]

    truncated = []
    for t in completed:
        res, cfg = t["result"], t["config"]
        et, to = res.get("execution_time_seconds"), cfg.get("timeout")
        if et is not None and to is not None and et < to:
            truncated.append((cfg.get("apk_name"), cfg.get("repetition"), et, to))

    n_ident = len(tasks)
    n_done = len(completed)
    n_trunc = len(truncated)
    rate = (n_trunc / n_done * 100) if n_done else 0.0

    print(f"run              : {args.name}")
    print(f"raw task records : {len(raw)}  (pre-dedup; resume inflates)")
    print(f"distinct ident.  : {n_ident} / {args.expected} expected", end="")
    print("  <-- IMMATURE, some slots not finished" if n_ident < args.expected else "")
    print(f"states           : {dict(states)}")
    print(f"COMPLETED        : {n_done}")
    print(f"TRUNCATED        : {n_trunc}  ({rate:.1f}% of COMPLETED)  "
          f"[state==COMPLETED & exec_time < timeout]")
    if args.list and truncated:
        print("--- truncated tasks ---")
        for apk, rep, et, to in sorted(truncated, key=lambda x: x[2]):
            print(f"  {apk} rep{rep}: {et}s < {to}s")


if __name__ == "__main__":
    main()
