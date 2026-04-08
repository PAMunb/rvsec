"""Area 8 — Internal Metrics Consistency for rvsmart traces."""

import csv
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

BASE = Path(
    "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/data/results"
)
CSV_PATH = BASE / "comparacao_consolidated.csv"

# Load consolidated CSV (rvsmart only)
csv_lookup = {}  # (apk, rep) -> row
with open(CSV_PATH) as f:
    for row in csv.DictReader(f):
        if row["tool"] == "rvsmart:mvp":
            key = (row["apk"], int(row["rep"]))
            csv_lookup[key] = row

# Find all trace files
trace_files = sorted(BASE.glob("cmp*/cmp*/*/*.trace"))
# Filter rvsmart only
trace_files = [t for t in trace_files if "rvsmart" in t.name]

print("# Area 8 — Internal Metrics Consistency\n")
print(f"**Trace files found**: {len(trace_files)}  ")
print(f"**CSV rvsmart entries**: {len(csv_lookup)}\n")

# Parse all traces
records = []  # list of dicts with parsed info
for tf in trace_files:
    # Extract apk and rep from filename: {apk}__{rep}__600__rvsmart:mvp.trace
    m = re.match(r"(.+?)__(\d+)__600__rvsmart:mvp\.trace", tf.name)
    if not m:
        continue
    apk = m.group(1)
    rep = int(m.group(2))

    lines = []
    with open(tf) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                lines.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    if not lines:
        continue

    records.append(
        {
            "apk": apk,
            "rep": rep,
            "path": tf,
            "lines": lines,
            "csv_row": csv_lookup.get((apk, rep)),
        }
    )

print(f"**Parsed trace records**: {len(records)}\n")

# ---- CHECK 1: Iteration count ----
print("## Check 1: Iteration Count (lines vs last iteration field)\n")
c1_pass, c1_fail = [], []
c1_diffs = []
for r in records:
    n_lines = len(r["lines"])
    last_iter = r["lines"][-1].get("iteration", -1)
    expected_lines = last_iter + 1  # 0-indexed
    diff = n_lines - expected_lines
    c1_diffs.append(diff)
    if diff != 0:
        c1_fail.append((r["apk"], r["rep"], n_lines, expected_lines, diff))
    else:
        c1_pass.append((r["apk"], r["rep"]))

print(f"- **Pass**: {len(c1_pass)} | **Fail**: {len(c1_fail)}")
if c1_fail:
    print("\n| APK | Rep | Lines | Expected | Diff |")
    print(f"|-----|-----|-------|----------|------|")
    for apk, rep, nl, exp, d in c1_fail[:20]:
        print(f"| {apk} | {rep} | {nl} | {exp} | {d:+d} |")
    if len(c1_fail) > 20:
        print("| ... | ... | ... | ... | ... |")
        print(f"\n*({len(c1_fail)} total failures)*")
if c1_diffs:
    print(
        f"\n**Diff stats**: mean={statistics.mean(c1_diffs):.2f}, std={statistics.stdev(c1_diffs) if len(c1_diffs)>1 else 0:.2f}\n"
    )

# ---- CHECK 2: Unique states ----
print("## Check 2: Unique States (distinct hashes vs max unique_states)\n")
c2_pass, c2_fail = [], []
c2_diffs = []
for r in records:
    distinct_hashes = len(
        set(l.get("hash", "") for l in r["lines"] if l.get("hash", ""))
    )
    max_us = max((l.get("unique_states", 0) for l in r["lines"]), default=0)
    diff = distinct_hashes - max_us
    c2_diffs.append(diff)
    if diff != 0:
        c2_fail.append((r["apk"], r["rep"], distinct_hashes, max_us, diff))
    else:
        c2_pass.append((r["apk"], r["rep"]))

print(f"- **Pass**: {len(c2_pass)} | **Fail**: {len(c2_fail)}")
if c2_fail:
    print("\n| APK | Rep | Distinct Hashes | Max unique_states | Diff |")
    print(f"|-----|-----|-----------------|-------------------|------|")
    for apk, rep, dh, mus, d in c2_fail[:30]:
        print(f"| {apk} | {rep} | {dh} | {mus} | {d:+d} |")
    if len(c2_fail) > 30:
        print(f"\n*({len(c2_fail)} total failures)*")
if c2_diffs:
    print(
        f"\n**Diff stats**: mean={statistics.mean(c2_diffs):.2f}, std={statistics.stdev(c2_diffs) if len(c2_diffs)>1 else 0:.2f}\n"
    )

# ---- CHECK 3: Execution time ----
print("## Check 3: Execution Time (trace elapsed_s vs CSV duration_s)\n")
c3_pass, c3_fail = [], []
c3_overheads = []
c3_no_csv = 0
for r in records:
    if not r["csv_row"]:
        c3_no_csv += 1
        continue
    trace_elapsed = r["lines"][-1].get("elapsed_s", 0)
    csv_duration = float(r["csv_row"]["duration_s"])
    overhead = csv_duration - trace_elapsed
    c3_overheads.append(overhead)
    if overhead > 100 or overhead < 30:
        c3_fail.append((r["apk"], r["rep"], trace_elapsed, csv_duration, overhead))
    else:
        c3_pass.append((r["apk"], r["rep"]))

print(
    f"- **Pass** (30-100s overhead): {len(c3_pass)} | **Fail**: {len(c3_fail)} | **No CSV match**: {c3_no_csv}"
)
if c3_fail:
    print("\n| APK | Rep | Trace elapsed_s | CSV duration_s | Overhead |")
    print(f"|-----|-----|-----------------|----------------|----------|")
    for apk, rep, te, cd, oh in sorted(c3_fail, key=lambda x: x[4])[:30]:
        print(f"| {apk} | {rep} | {te:.1f} | {cd:.0f} | {oh:.1f}s |")
    if len(c3_fail) > 30:
        print(f"\n*({len(c3_fail)} total failures)*")
if c3_overheads:
    print(
        f"\n**Overhead stats**: mean={statistics.mean(c3_overheads):.1f}s, std={statistics.stdev(c3_overheads) if len(c3_overheads)>1 else 0:.1f}s, "
        f"min={min(c3_overheads):.1f}s, max={max(c3_overheads):.1f}s\n"
    )

# ---- CHECK 4: Activity coverage ----
print("## Check 4: Activity Coverage (trace activities vs CSV activity_coverage)\n")
c4_details = []
for r in records:
    if not r["csv_row"]:
        continue
    trace_activities = set()
    for l in r["lines"]:
        act = l.get("activity", "")
        if act:
            trace_activities.add(act)
    csv_act_cov = float(r["csv_row"]["activity_coverage"])
    c4_details.append((r["apk"], r["rep"], len(trace_activities), csv_act_cov))

# Group by comparison: trace count vs csv percentage (can't directly compare, but report both)
print(
    "**Note**: Trace gives absolute count of distinct activities visited; CSV gives % coverage from logcat.\n"
)
print(f"| APK | Rep | Trace Activities | CSV activity_coverage% |")
print(f"|-----|-----|-----------------|----------------------|")
# Show cases where trace has few activities but CSV shows high coverage or vice versa
# Sort by trace activity count descending
c4_sorted = sorted(c4_details, key=lambda x: (-x[2], x[3]))
for apk, rep, ta, ca in c4_sorted[:15]:
    print(f"| {apk} | {rep} | {ta} | {ca:.1f}% |")
print("| ... | ... | ... | ... |")

# Summary stats
ta_vals = [x[2] for x in c4_details]
ca_vals = [x[3] for x in c4_details]
print(
    f"\n**Trace activities**: mean={statistics.mean(ta_vals):.1f}, std={statistics.stdev(ta_vals):.1f}, range=[{min(ta_vals)}, {max(ta_vals)}]"
)
print(
    f"**CSV activity_coverage%**: mean={statistics.mean(ca_vals):.1f}%, std={statistics.stdev(ca_vals):.1f}%, range=[{min(ca_vals):.1f}%, {max(ca_vals):.1f}%]\n"
)

# Correlation hint: cases where trace shows 1 activity but CSV > 50%
anomalies_4 = [(a, r, t, c) for a, r, t, c in c4_details if t <= 2 and c > 50]
if anomalies_4:
    print(
        f"**Anomalies** (<=2 trace activities but >50% CSV coverage): {len(anomalies_4)}"
    )
    for apk, rep, ta, ca in anomalies_4[:10]:
        print(f"  - {apk} rep{rep}: {ta} trace activities, {ca:.1f}% CSV coverage")
anomalies_4b = [(a, r, t, c) for a, r, t, c in c4_details if t >= 10 and c < 30]
if anomalies_4b:
    print(
        f"\n**Anomalies** (>=10 trace activities but <30% CSV coverage): {len(anomalies_4b)}"
    )
    for apk, rep, ta, ca in anomalies_4b[:10]:
        print(f"  - {apk} rep{rep}: {ta} trace activities, {ca:.1f}% CSV coverage")
print()

# ---- CHECK 5: Action type consistency ----
print("## Check 5: Action Type Consistency (action count vs iteration count)\n")
c5_pass, c5_fail = [], []
action_type_totals = defaultdict(int)
for r in records:
    n_lines = len(r["lines"])
    action_count = sum(1 for l in r["lines"] if "action_type" in l)
    for l in r["lines"]:
        at = l.get("action_type", "UNKNOWN")
        action_type_totals[at] += 1
    if action_count != n_lines:
        c5_fail.append((r["apk"], r["rep"], n_lines, action_count))
    else:
        c5_pass.append((r["apk"], r["rep"]))

print(f"- **Pass**: {len(c5_pass)} | **Fail**: {len(c5_fail)}")
if c5_fail:
    print("\n| APK | Rep | Lines | Actions |")
    print(f"|-----|-----|-------|---------|")
    for apk, rep, nl, ac in c5_fail[:20]:
        print(f"| {apk} | {rep} | {nl} | {ac} |")

print("\n**Action type distribution** (all traces combined):\n")
for at, count in sorted(action_type_totals.items(), key=lambda x: -x[1]):
    print(f"- {at}: {count:,}")

print(f"\n**Total actions**: {sum(action_type_totals.values()):,}")
print(
    f"\n---\n*Generated from {len(records)} trace files across {len(set(r['apk'] for r in records))} APKs*"
)
