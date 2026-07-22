#!/usr/bin/env python3
"""Reconcile tasks.json state to the logcat on disk.

A task whose identity has a non-empty `.logcat` under its container directory
already carries usable data (RVSEC-COV coverage + RVSEC MOP events), even when
the runner flagged it ERROR. Monkey runs that the container OOM-killed mid-run
still write a (partial) logcat, so their ERROR state is spurious for the purpose
of "is there data". This marks every identity that has a non-empty logcat as
COMPLETED so a resume walk skips it and runs only the identities that genuinely
lack a logcat.

The logcat, not tasks.json, is the source of truth for data completeness.

Usage:
    python3 reconcile_tasks_to_logcat.py [RESULTS_DIR] [--apply]

RESULTS_DIR defaults to ./results. Without --apply it is a dry run (reports the
count per container, writes nothing). Reconciles every results/exp_*/exp_*/tasks.json
against the logcats in its own container directory.
"""
import glob
import json
import os
import re
import sys

# <apk>.apk__<rep>__<timeout>__<tool>.logcat ; tool token keeps droidbot's variant
# (e.g. "droidbot:bfs_greedy"), matching how the runner names the file.
LOGCAT_RE = re.compile(r"^(?P<apk>.+\.apk)__(?P<rep>\d+)__(?P<to>\d+)__(?P<tool>.+)\.logcat$")


def tool_token(name, variant):
    return f"{name}:{variant}" if (name == "droidbot" and variant) else name


def main():
    apply = "--apply" in sys.argv
    positional = [a for a in sys.argv[1:] if a != "--apply"]
    results = positional[0] if positional else "results"

    total = 0
    for tasks_json in sorted(glob.glob(f"{results}/exp_*/exp_*/tasks.json")):
        container_dir = os.path.dirname(tasks_json)
        have = set()
        for f in glob.glob(f"{container_dir}/*/*.logcat"):
            if os.path.getsize(f) == 0:
                continue
            m = LOGCAT_RE.match(os.path.basename(f))
            if m:
                have.add((m["apk"], int(m["rep"]), int(m["to"]), m["tool"]))

        doc = json.load(open(tasks_json))
        changed = 0
        for t in doc["tasks"]:
            c = t["config"]
            tc = c.get("tool_config", {})
            ident = (c.get("apk_name"), c.get("repetition"), c.get("timeout"),
                     tool_token(tc.get("name"), tc.get("variant")))
            if ident in have and t.get("result", {}).get("state") != "COMPLETED":
                if apply:
                    t.setdefault("result", {})["state"] = "COMPLETED"
                changed += 1

        total += changed
        suffix = "" if apply else " (dry-run)"
        print(f"{tasks_json}: {changed} ERROR-with-logcat -> COMPLETED{suffix}")
        if apply and changed:
            json.dump(doc, open(tasks_json, "w"), indent=2)

    print(f"TOTAL: {total}{'' if apply else ' (dry-run)'}")


if __name__ == "__main__":
    main()
