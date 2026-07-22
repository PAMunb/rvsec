"""Analyze rvsmart trace files from comparison experiment."""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

BASE = Path(
    "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android"
)
RESULTS_DIR = BASE / "data" / "results"
CSV_PATH = RESULTS_DIR / "comparacao_consolidated.csv"

ERROR_PATTERNS = [
    "NullPointer",
    "OutOfMemory",
    "ClassNotFound",
    "StackOverflow",
    "IOException",
    "TimeoutException",
    "SecurityException",
    "IllegalState",
    "IllegalArgument",
    "ArrayIndexOutOfBounds",
    "ClassCast",
    "NoSuchMethod",
    "NoSuchField",
    "UnsatisfiedLink",
    "RuntimeException",
    "Exception",
    "Error",
    "FATAL",
    "CRASH",
]


def find_traces():
    """Find all rvsmart trace files."""
    traces = []
    for cmp_dir in sorted(RESULTS_DIR.glob("cmp*")):
        for trace_file in cmp_dir.rglob("*.trace"):
            # Parse: {apk}__{rep}__{timeout}__{tool}.trace
            name = trace_file.name
            parts = name.rsplit("__", 3)
            if len(parts) == 4:
                apk = parts[0]
                rep = int(parts[1])
                traces.append({"path": trace_file, "apk": apk, "rep": rep})
    return traces


def parse_trace(path):
    """Parse a trace file into list of iteration dicts."""
    iterations = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                iterations.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return iterations


def load_csv():
    """Load consolidated CSV into dict keyed by (apk, tool, rep)."""
    import csv

    data = {}
    with open(CSV_PATH) as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["apk"], row["tool"], int(row["rep"]))
            data[key] = row
    return data


def analyze_action_distribution(traces_by_apk):
    """Area 4: Action type distribution."""
    lines = []
    lines.append("# Area 4 — Action Distribution\n")

    # Per APK: action counts averaged across reps
    apk_action_pcts = {}  # apk -> {action_type: mean_pct}
    global_counts = Counter()

    for apk, reps in sorted(traces_by_apk.items()):
        rep_distributions = []
        for iters in reps:
            counts = Counter()
            for it in iters:
                at = it.get("action_type", "UNKNOWN")
                counts[at] += 1
            total = sum(counts.values()) or 1
            pcts = {k: v / total for k, v in counts.items()}
            rep_distributions.append(pcts)
            global_counts += counts

        # Mean pcts across reps
        all_types = set()
        for d in rep_distributions:
            all_types.update(d.keys())
        mean_pcts = {}
        for t in all_types:
            mean_pcts[t] = mean([d.get(t, 0) for d in rep_distributions])
        apk_action_pcts[apk] = mean_pcts

    # Top action types overall
    total = sum(global_counts.values())
    lines.append("## Top Action Types (all APKs, all reps)\n")
    lines.append("| Action | Count | % |")
    lines.append("|--------|------:|--:|")
    for action, count in global_counts.most_common(15):
        lines.append(f"| {action} | {count} | {count*100/total:.1f}% |")

    # APKs with >50% SKIP
    lines.append("\n## APKs with >50% SKIP\n")
    skip_apks = [
        (apk, pcts.get("SKIP", 0))
        for apk, pcts in apk_action_pcts.items()
        if pcts.get("SKIP", 0) > 0.5
    ]
    skip_apks.sort(key=lambda x: -x[1])
    if skip_apks:
        lines.append("| APK | SKIP % |")
        lines.append("|-----|-------:|")
        for apk, pct in skip_apks:
            lines.append(f"| {apk} | {pct*100:.1f}% |")
    else:
        lines.append("None found.")

    # APKs with >40% BACK
    lines.append("\n## APKs with >40% BACK\n")
    back_apks = [
        (apk, pcts.get("BACK", 0))
        for apk, pcts in apk_action_pcts.items()
        if pcts.get("BACK", 0) > 0.4
    ]
    back_apks.sort(key=lambda x: -x[1])
    if back_apks:
        lines.append("| APK | BACK % |")
        lines.append("|-----|-------:|")
        for apk, pct in back_apks:
            lines.append(f"| {apk} | {pct*100:.1f}% |")
    else:
        lines.append("None found.")

    # High RESTART ratio (>15%)
    lines.append("\n## APKs with >15% RESTART\n")
    restart_apks = [
        (apk, pcts.get("RESTART", 0))
        for apk, pcts in apk_action_pcts.items()
        if pcts.get("RESTART", 0) > 0.15
    ]
    restart_apks.sort(key=lambda x: -x[1])
    if restart_apks:
        lines.append("| APK | RESTART % |")
        lines.append("|-----|----------:|")
        for apk, pct in restart_apks:
            lines.append(f"| {apk} | {pct*100:.1f}% |")
    else:
        lines.append("None found.")

    return "\n".join(lines)


def analyze_plateau_stochastic(traces_by_apk):
    """Area 6: Plateau/Stochastic/Recovery."""
    lines = []
    lines.append("# Area 6 — Plateau / Stochastic / Recovery\n")

    apk_stats = {}
    for apk, reps in sorted(traces_by_apk.items()):
        rep_stochastic_pcts = []
        rep_saturation = []
        rep_max_consec = []

        for iters in reps:
            if not iters:
                continue
            # Stochastic %
            scored = [it for it in iters if "scores" in it]
            if scored:
                stoch_count = sum(
                    1 for it in scored if it["scores"].get("stochastic", False)
                )
                rep_stochastic_pcts.append(stoch_count / len(scored))

            # Saturation at end
            last_with_sat = None
            for it in reversed(iters):
                if "saturation_rate" in it:
                    last_with_sat = it
                    break
            if last_with_sat:
                rep_saturation.append(last_with_sat["saturation_rate"])

            # Max consecutive same hash
            max_consec = 1
            cur_consec = 1
            prev_hash = None
            for it in iters:
                h = it.get("hash", "")
                if h and h == prev_hash:
                    cur_consec += 1
                    max_consec = max(max_consec, cur_consec)
                else:
                    cur_consec = 1
                prev_hash = h
            rep_max_consec.append(max_consec)

        apk_stats[apk] = {
            "stochastic_pct": mean(rep_stochastic_pcts) if rep_stochastic_pcts else 0,
            "saturation": mean(rep_saturation) if rep_saturation else 0,
            "max_consec_hash": mean(rep_max_consec) if rep_max_consec else 0,
        }

    # Overall summary
    all_stoch = [s["stochastic_pct"] for s in apk_stats.values()]
    all_sat = [s["saturation"] for s in apk_stats.values()]
    lines.append("## Overall Summary\n")
    lines.append(f"- Mean stochastic %: {mean(all_stoch)*100:.1f}%")
    lines.append(f"- Median stochastic %: {median(all_stoch)*100:.1f}%")
    lines.append(f"- Mean final saturation: {mean(all_sat):.3f}")
    lines.append(f"- Median final saturation: {median(all_sat):.3f}")

    # APKs with >50% stochastic
    lines.append("\n## APKs with >50% Stochastic (algorithm falling back to random)\n")
    high_stoch = [
        (apk, s["stochastic_pct"])
        for apk, s in apk_stats.items()
        if s["stochastic_pct"] > 0.5
    ]
    high_stoch.sort(key=lambda x: -x[1])
    if high_stoch:
        lines.append(f"Count: {len(high_stoch)}\n")
        lines.append("| APK | Stochastic % | Saturation | Max Consec Hash |")
        lines.append("|-----|-------------:|-----------:|----------------:|")
        for apk, pct in high_stoch:
            s = apk_stats[apk]
            lines.append(
                f"| {apk} | {pct*100:.1f}% | {s['saturation']:.3f} | {s['max_consec_hash']:.0f} |"
            )
    else:
        lines.append("None found.")

    # Saturation near 1.0 (>0.8)
    lines.append("\n## APKs with High Saturation (>0.8 — fully explored)\n")
    high_sat = [
        (apk, s["saturation"]) for apk, s in apk_stats.items() if s["saturation"] > 0.8
    ]
    high_sat.sort(key=lambda x: -x[1])
    if high_sat:
        lines.append(f"Count: {len(high_sat)}\n")
        lines.append("| APK | Saturation |")
        lines.append("|-----|-----------:|")
        for apk, sat in high_sat[:20]:
            lines.append(f"| {apk} | {sat:.3f} |")
        if len(high_sat) > 20:
            lines.append(f"| ... ({len(high_sat)-20} more) | |")
    else:
        lines.append("None found.")

    # Saturation near 0 (<0.1)
    lines.append("\n## APKs with Low Saturation (<0.1 — barely explored)\n")
    low_sat = [
        (apk, s["saturation"]) for apk, s in apk_stats.items() if s["saturation"] < 0.1
    ]
    low_sat.sort(key=lambda x: x[1])
    if low_sat:
        lines.append(f"Count: {len(low_sat)}\n")
        lines.append("| APK | Saturation | Stochastic % |")
        lines.append("|-----|-----------:|-------------:|")
        for apk, sat in low_sat[:20]:
            s = apk_stats[apk]
            lines.append(f"| {apk} | {sat:.3f} | {s['stochastic_pct']*100:.1f}% |")
        if len(low_sat) > 20:
            lines.append(f"| ... ({len(low_sat)-20} more) | | |")
    else:
        lines.append("None found.")

    return "\n".join(lines)


def analyze_score_breakdown(traces_by_apk, csv_data):
    """Area 7: Score breakdown."""
    lines = []
    lines.append("# Area 7 — Score Breakdown\n")

    scorer_keys = [
        "coverage",
        "component",
        "mop",
        "wtg",
        "decay",
        "confirmed",
        "system",
    ]

    # Per APK: mean scores across all iterations and reps
    apk_mean_scores = {}
    for apk, reps in sorted(traces_by_apk.items()):
        all_scores = {k: [] for k in scorer_keys}
        all_totals = []
        for iters in reps:
            for it in iters:
                if "scores" in it:
                    s = it["scores"]
                    for k in scorer_keys:
                        if k in s:
                            all_scores[k].append(s[k])
                    if "total" in s:
                        all_totals.append(s["total"])
        apk_mean_scores[apk] = {k: mean(v) if v else 0 for k, v in all_scores.items()}
        apk_mean_scores[apk]["total"] = mean(all_totals) if all_totals else 0

    # Overall mean per scorer
    lines.append("## Mean Score per Scorer (across all APKs)\n")
    lines.append("| Scorer | Mean | Median |")
    lines.append("|--------|-----:|-------:|")
    for k in ["total"] + scorer_keys:
        vals = [s[k] for s in apk_mean_scores.values()]
        lines.append(f"| {k} | {mean(vals):.1f} | {median(vals):.1f} |")

    # APKs where WTG is always 0
    lines.append("\n## APKs with WTG Score Always 0\n")
    wtg_zero = []
    for apk, reps in traces_by_apk.items():
        all_wtg = []
        for iters in reps:
            for it in iters:
                if "scores" in it and "wtg" in it["scores"]:
                    all_wtg.append(it["scores"]["wtg"])
        if all_wtg and max(all_wtg) == 0:
            wtg_zero.append(apk)
    wtg_zero.sort()
    lines.append(f"Count: {len(wtg_zero)} / {len(traces_by_apk)}\n")
    if wtg_zero:
        for apk in wtg_zero:
            lines.append(f"- {apk}")

    # Correlation: total score vs method_coverage
    lines.append("\n## Correlation: Mean Total Score vs Method Coverage\n")
    pairs = []
    for apk in apk_mean_scores:
        # Get mean method_coverage from CSV
        coverages = []
        for rep in range(1, 4):
            key = (apk, "rvsmart:mvp", rep)
            if key in csv_data:
                mc = csv_data[key].get("method_coverage", "")
                if mc:
                    try:
                        coverages.append(float(mc))
                    except ValueError:
                        pass
        if coverages:
            pairs.append((apk, apk_mean_scores[apk]["total"], mean(coverages)))

    if pairs:
        scores = [p[1] for p in pairs]
        covs = [p[2] for p in pairs]
        n = len(pairs)
        mean_s = mean(scores)
        mean_c = mean(covs)
        cov_sc = sum((s - mean_s) * (c - mean_c) for s, c in zip(scores, covs)) / n
        std_s = (sum((s - mean_s) ** 2 for s in scores) / n) ** 0.5
        std_c = (sum((c - mean_c) ** 2 for c in covs) / n) ** 0.5
        if std_s > 0 and std_c > 0:
            corr = cov_sc / (std_s * std_c)
            lines.append(f"Pearson correlation (n={n}): **{corr:.3f}**")
        else:
            lines.append("Cannot compute correlation (zero variance).")

        # Top/bottom 5 by score
        pairs.sort(key=lambda x: -x[1])
        lines.append("\n### Top 5 by Mean Total Score\n")
        lines.append("| APK | Mean Score | Method Cov |")
        lines.append("|-----|----------:|-----------:|")
        for apk, sc, cov in pairs[:5]:
            lines.append(f"| {apk} | {sc:.0f} | {cov:.1f}% |")

        lines.append("\n### Bottom 5 by Mean Total Score\n")
        lines.append("| APK | Mean Score | Method Cov |")
        lines.append("|-----|----------:|-----------:|")
        for apk, sc, cov in pairs[-5:]:
            lines.append(f"| {apk} | {sc:.0f} | {cov:.1f}% |")

    return "\n".join(lines)


def analyze_errors(trace_files):
    """Area 9: Trace errors."""
    lines = []
    lines.append("# Area 9 — Trace Errors\n")

    error_re = re.compile("|".join(ERROR_PATTERNS), re.IGNORECASE)
    apk_errors = defaultdict(list)

    for tf in trace_files:
        apk = tf["apk"]
        try:
            text = tf["path"].read_text()
        except Exception:
            continue
        # Search for error patterns in raw text (some traces may have error fields)
        found = set()
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                # Check for error/exception fields
                for key in ("error", "exception", "error_message", "crash"):
                    if key in obj and obj[key]:
                        found.add(str(obj[key])[:100])
            except json.JSONDecodeError:
                # Non-JSON line — might be an error/stack trace
                if error_re.search(line):
                    found.add(line[:100])

        if found:
            apk_errors[apk].extend(found)

    lines.append(f"APKs with errors in traces: {len(apk_errors)}\n")
    if apk_errors:
        # Sort by error count
        sorted_apks = sorted(apk_errors.items(), key=lambda x: -len(x[1]))
        lines.append("| APK | Error Count | Sample |")
        lines.append("|-----|------------:|--------|")
        for apk, errors in sorted_apks[:30]:
            sample = errors[0][:60].replace("|", "/")
            lines.append(f"| {apk} | {len(errors)} | {sample} |")
    else:
        lines.append("No errors found in trace files.")

    return "\n".join(lines)


def analyze_timing(traces_by_apk, csv_data):
    """Area 6 timing: compare trace elapsed_s vs task duration_s."""
    lines = []
    lines.append("# Area 6b — Timing Investigation\n")
    lines.append(
        "Comparing trace elapsed_s (last iteration) vs tasks.json duration_s.\n"
    )

    discrepancies = []
    for apk, reps in sorted(traces_by_apk.items()):
        for rep_idx, iters in enumerate(reps):
            if not iters:
                continue
            # Last iteration elapsed_s
            last_elapsed = None
            for it in reversed(iters):
                if "elapsed_s" in it:
                    last_elapsed = it["elapsed_s"]
                    break
            if last_elapsed is None:
                continue

            # CSV duration
            key = (apk, "rvsmart:mvp", rep_idx + 1)
            if key not in csv_data:
                continue
            try:
                task_duration = float(csv_data[key]["duration_s"])
            except (ValueError, KeyError):
                continue

            diff = task_duration - last_elapsed
            discrepancies.append((apk, rep_idx + 1, last_elapsed, task_duration, diff))

    if not discrepancies:
        lines.append("No data to compare.")
        return "\n".join(lines)

    diffs = [d[4] for d in discrepancies]
    lines.append(f"Total comparisons: {len(discrepancies)}")
    lines.append(f"Mean overhead (task_duration - trace_elapsed): {mean(diffs):.1f}s")
    lines.append(f"Median overhead: {median(diffs):.1f}s")
    lines.append(f"Max overhead: {max(diffs):.1f}s")
    lines.append(f"Min overhead: {min(diffs):.1f}s")

    # Tasks >660s
    over_660 = [d for d in discrepancies if d[3] > 660]
    lines.append(f"\n## Tasks with duration >660s: {len(over_660)}\n")
    if over_660:
        lines.append(
            "| APK | Rep | Trace Elapsed (s) | Task Duration (s) | Overhead (s) |"
        )
        lines.append(
            "|-----|----:|-----------------:|-----------------:|-------------:|"
        )
        over_660.sort(key=lambda x: -x[4])
        for apk, rep, elapsed, dur, diff in over_660[:30]:
            lines.append(f"| {apk} | {rep} | {elapsed:.1f} | {dur:.0f} | {diff:.1f} |")
        if len(over_660) > 30:
            lines.append(f"| ... ({len(over_660)-30} more) | | | | |")

    # Distribution of overheads
    lines.append("\n## Overhead Distribution (all tasks)\n")
    buckets = [0, 10, 30, 60, 120, 300, 600, float("in")]
    labels = ["0-10s", "10-30s", "30-60s", "60-120s", "120-300s", "300-600s", ">600s"]
    for i, label in enumerate(labels):
        count = sum(1 for d in diffs if buckets[i] <= d < buckets[i + 1])
        if count:
            lines.append(f"- {label}: {count}")

    return "\n".join(lines)


def analyze_ui_coverage(traces_by_apk):
    """Area 5: UI coverage from traces."""
    lines = []
    lines.append("# Area 5 — UI Coverage (from traces)\n")

    apk_stats = {}
    for apk, reps in sorted(traces_by_apk.items()):
        rep_max_states = []
        rep_activities = []
        for iters in reps:
            max_states = 0
            activities = set()
            for it in iters:
                us = it.get("unique_states", 0)
                if us > max_states:
                    max_states = us
                act = it.get("activity", "")
                if act:
                    activities.add(act)
            rep_max_states.append(max_states)
            rep_activities.append(len(activities))
        apk_stats[apk] = {
            "max_states": mean(rep_max_states) if rep_max_states else 0,
            "activities": mean(rep_activities) if rep_activities else 0,
        }

    all_states = [s["max_states"] for s in apk_stats.values()]
    all_acts = [s["activities"] for s in apk_stats.values()]
    lines.append("## Overall Summary\n")
    lines.append(f"- Mean unique states: {mean(all_states):.1f}")
    lines.append(f"- Median unique states: {median(all_states):.1f}")
    lines.append(f"- Mean activities visited: {mean(all_acts):.1f}")
    lines.append(f"- Median activities visited: {median(all_acts):.1f}")

    # APKs with only 1 unique state
    lines.append("\n## APKs with Only 1 Unique State (stuck on one screen)\n")
    stuck = [
        (apk, s["max_states"], s["activities"])
        for apk, s in apk_stats.items()
        if s["max_states"] <= 1
    ]
    stuck.sort(key=lambda x: x[1])
    if stuck:
        lines.append(f"Count: {len(stuck)}\n")
        lines.append("| APK | Max States | Activities |")
        lines.append("|-----|-----------:|-----------:|")
        for apk, st, act in stuck:
            lines.append(f"| {apk} | {st:.1f} | {act:.1f} |")
    else:
        lines.append("None found.")

    # Top 10 by unique states
    lines.append("\n## Top 10 by Unique States\n")
    top = sorted(apk_stats.items(), key=lambda x: -x[1]["max_states"])[:10]
    lines.append("| APK | Max States | Activities |")
    lines.append("|-----|-----------:|-----------:|")
    for apk, s in top:
        lines.append(f"| {apk} | {s['max_states']:.1f} | {s['activities']:.1f} |")

    return "\n".join(lines)


def main():
    print("Scanning for trace files...")
    trace_files = find_traces()
    print(f"Found {len(trace_files)} trace files")

    # Group by APK, maintaining rep order
    apk_reps = defaultdict(dict)  # apk -> {rep: [iters]}
    for tf in trace_files:
        apk_reps[tf["apk"]][tf["rep"]] = tf["path"]

    # Parse all traces, grouped as apk -> [rep1_iters, rep2_iters, ...]
    print("Parsing trace files...")
    traces_by_apk = {}
    for apk in sorted(apk_reps):
        reps_data = []
        for rep in sorted(apk_reps[apk]):
            iters = parse_trace(apk_reps[apk][rep])
            reps_data.append(iters)
        traces_by_apk[apk] = reps_data

    print(f"Parsed traces for {len(traces_by_apk)} APKs")

    csv_data = load_csv()
    print(f"Loaded CSV with {len(csv_data)} rows")

    report_parts = []
    report_parts.append("# RVSmart Trace Analysis Report\n")
    report_parts.append(
        f"Trace files: {len(trace_files)} | APKs: {len(traces_by_apk)}\n"
    )

    print("Analyzing action distribution...")
    report_parts.append(analyze_action_distribution(traces_by_apk))

    print("Analyzing plateau/stochastic...")
    report_parts.append("\n---\n")
    report_parts.append(analyze_plateau_stochastic(traces_by_apk))

    print("Analyzing score breakdown...")
    report_parts.append("\n---\n")
    report_parts.append(analyze_score_breakdown(traces_by_apk, csv_data))

    print("Analyzing errors...")
    report_parts.append("\n---\n")
    report_parts.append(analyze_errors(trace_files))

    print("Analyzing timing...")
    report_parts.append("\n---\n")
    report_parts.append(analyze_timing(traces_by_apk, csv_data))

    print("Analyzing UI coverage...")
    report_parts.append("\n---\n")
    report_parts.append(analyze_ui_coverage(traces_by_apk))

    report = "\n".join(report_parts)
    print("\n" + "=" * 80)
    print(report)


if __name__ == "__main__":
    main()
