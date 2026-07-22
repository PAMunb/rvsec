#!/usr/bin/env python3
"""
Analyze remaining validation areas (10, 13, 14, 15) for the rvsmart comparison experiment.
"""

import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev

import scipy.stats as stats

BASE = Path(
    "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android"
)
DATA = BASE / "data"
RESULTS = DATA / "results"
APKS_DIR = DATA / "apks"
CONTAINERS = [f"cmp{i:02d}" for i in range(1, 7)]

WTG_ZERO_APKS = {
    "byrne.utilities.hashpass_2.apk",
    "com.example.root.analyticaltranslator_6.apk",
    "com.github.mobile_1900.apk",
    "com.googlecode.gtalksms_69.apk",
    "com.maxfierke.sandwichroulette_2.apk",
    "com.orpheusdroid.sqliteviewer_1.apk",
    "com.ruesga.android.wallpapers.photophase_1036.apk",
    "com.soumikshah.investmenttracker_3.apk",
    "com.vwp.owmap_136.apk",
    "de.determapp.android_8.apk",
    "de.kodejak.hashr_13.apk",
    "digital.selfdefense.lucia_20001.apk",
    "fr.s13d.photobackup_33.apk",
    "github.vatsal.easyweatherdemo_11.apk",
    "io.gresse.hugo.anecdote_23.apk",
    "jp.co.kayo.android.localplayer_2071400330.apk",
    "net.jjc1138.android.scrobbler_7.apk",
    "uk.org.boddie.android.weatherforecast_166.apk",
}


def load_all_tasks():
    """Load all tasks from all containers, returns list of (container, task) tuples."""
    all_tasks = []
    for ctr in CONTAINERS:
        path = RESULTS / ctr / ctr / "tasks.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        for t in data["tasks"]:
            all_tasks.append((ctr, t))
    return all_tasks


def find_logcat_files():
    """Find all rvsmart logcat files across containers."""
    files = []
    for ctr in CONTAINERS:
        ctr_dir = RESULTS / ctr / ctr
        if not ctr_dir.exists():
            continue
        for apk_dir in sorted(ctr_dir.iterdir()):
            if not apk_dir.is_dir():
                continue
            for f in sorted(apk_dir.iterdir()):
                if f.name.endswith(".logcat"):
                    # Parse: {apk}__{rep}__{timeout}__{tool}.logcat
                    parts = f.stem.split("__")
                    if len(parts) >= 3:
                        apk = parts[0]
                        rep = int(parts[1])
                        files.append((apk, rep, ctr, f))
    return files


def find_trace_files():
    """Find all rvsmart trace files across containers."""
    files = []
    for ctr in CONTAINERS:
        ctr_dir = RESULTS / ctr / ctr
        if not ctr_dir.exists():
            continue
        for apk_dir in sorted(ctr_dir.iterdir()):
            if not apk_dir.is_dir():
                continue
            for f in sorted(apk_dir.iterdir()):
                if f.name.endswith(".trace"):
                    parts = f.stem.split("__")
                    if len(parts) >= 3:
                        apk = parts[0]
                        rep = int(parts[1])
                        files.append((apk, rep, ctr, f))
    return files


def load_consolidated_csv():
    """Load the consolidated CSV."""
    rows = []
    with open(RESULTS / "comparacao_consolidated.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


# ============================================================
# AREA 10: Logcat Analysis
# ============================================================
def area_10():
    lines = []
    lines.append("# Area 10 — Logcat Analysis (RVSEC-COV Events)\n")

    logcat_files = find_logcat_files()
    lines.append(f"Total logcat files found: {len(logcat_files)}\n")

    # Per APK: count RVSEC-COV events, distinct methods, errors
    apk_cov_counts = defaultdict(list)  # apk -> [count per rep]
    apk_methods = defaultdict(list)  # apk -> [set of methods per rep]
    apk_errors = defaultdict(list)  # apk -> [count per rep]
    error_examples = []

    for apk, rep, ctr, path in logcat_files:
        try:
            content = path.read_text(errors="replace")
        except Exception:
            continue

        cov_count = 0
        methods = set()
        err_count = 0

        for line in content.splitlines():
            if "RVSEC-COV" in line:
                cov_count += 1
                # Extract method signature: everything between < and >
                m = re.search(r"<([^>]+)>", line)
                if m:
                    methods.add(m.group(1))
            # Error patterns (exclude RVSEC-COV lines)
            elif re.search(r"(Exception|Error|FATAL)", line, re.IGNORECASE):
                err_count += 1
                if len(error_examples) < 10:
                    error_examples.append((apk, rep, line.strip()[:200]))

        apk_cov_counts[apk].append(cov_count)
        apk_methods[apk].append(methods)
        apk_errors[apk].append(err_count)

    # Summary table
    lines.append("## RVSEC-COV Events per APK\n")
    lines.append(
        "| APK | Reps | Avg COV Events | Avg Distinct Methods | Min/Max Events |"
    )
    lines.append(
        "|-----|------|----------------|---------------------|----------------|"
    )

    total_cov = 0
    total_methods_all = set()
    apk_list = sorted(apk_cov_counts.keys())
    for apk in apk_list:
        counts = apk_cov_counts[apk]
        method_sets = apk_methods[apk]
        avg_count = mean(counts)
        avg_methods = mean([len(ms) for ms in method_sets])
        total_cov += sum(counts)
        for ms in method_sets:
            total_methods_all.update(f"{apk}::{m}" for m in ms)
        lines.append(
            f"| {apk[:50]} | {len(counts)} | {avg_count:.1f} | {avg_methods:.1f} | {min(counts)}/{max(counts)} |"
        )

    lines.append(f"\n**Total RVSEC-COV events across all files**: {total_cov}")
    lines.append(f"**Total unique APK×method combinations**: {len(total_methods_all)}")
    lines.append(f"**APKs with logcat data**: {len(apk_list)}")

    # APKs with zero coverage events
    zero_cov = [apk for apk in apk_list if all(c == 0 for c in apk_cov_counts[apk])]
    lines.append(f"\n**APKs with zero RVSEC-COV events in all reps**: {len(zero_cov)}")
    if zero_cov:
        for apk in zero_cov:
            lines.append(f"  - {apk}")

    # Error analysis
    lines.append("\n## Error/Exception Lines in Logcat\n")
    apks_with_errors = [
        (apk, apk_errors[apk])
        for apk in apk_list
        if any(e > 0 for e in apk_errors[apk])
    ]
    lines.append(
        f"APKs with error/exception lines: {len(apks_with_errors)} / {len(apk_list)}"
    )

    if apks_with_errors:
        lines.append("\n| APK | Avg Error Lines | Max |")
        lines.append("|-----|----------------|-----|")
        for apk, errs in sorted(apks_with_errors, key=lambda x: -max(x[1]))[:20]:
            lines.append(f"| {apk[:50]} | {mean(errs):.0f} | {max(errs)} |")

    if error_examples:
        lines.append("\n### Sample Error Lines (first 10)\n")
        for apk, rep, line in error_examples:
            lines.append(f"- **{apk}** rep{rep}: `{line[:150]}`")

    lines.append("")
    return "\n".join(lines)


# ============================================================
# AREA 13: Static Analysis Utilization
# ============================================================
def area_13():
    lines = []
    lines.append("# Area 13 — Static Analysis Utilization\n")

    trace_files = find_trace_files()

    # Group traces by APK
    apk_traces = defaultdict(list)
    for apk, rep, ctr, path in trace_files:
        apk_traces[apk].append((rep, path))

    # Load SA data for each APK
    sa_data = {}
    for sa_file in sorted(APKS_DIR.glob("*.json")):
        apk_name = sa_file.stem  # e.g., byrne.utilities.hashpass_2.apk
        # The stem includes .apk, so the apk name IS the stem
        try:
            sa = json.loads(sa_file.read_text())
            activities = [
                w["name"] for w in sa.get("windows", []) if w.get("type") == "ACTIVITY"
            ]
            transitions = sa.get("transitions", [])
            real_transitions = [
                t
                for t in transitions
                if not all(
                    e["type"].startswith("implicit_") for e in t.get("events", [])
                )
            ]
            classes = sa.get("reachability", [])
            total_methods = sum(len(c.get("methods", [])) for c in classes)
            sa_data[apk_name] = {
                "activities": activities,
                "n_activities": len(activities),
                "n_transitions": len(transitions),
                "n_real_transitions": len(real_transitions),
                "n_classes": len(classes),
                "n_methods": total_methods,
            }
        except Exception as e:
            pass

    lines.append(f"SA JSONs loaded: {len(sa_data)}\n")

    # Extract activities visited and unique_states from traces
    apk_trace_stats = {}  # apk -> {activities_visited, unique_states, max_wtg_score}
    for apk in sorted(apk_traces.keys()):
        all_activities = set()
        all_unique_states = []
        max_wtg = 0
        for rep, path in apk_traces[apk]:
            try:
                activities_this_rep = set()
                max_us = 0
                for line in path.read_text(errors="replace").splitlines():
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    act = entry.get("activity", "")
                    if act:
                        activities_this_rep.add(act)
                        all_activities.add(act)
                    us = entry.get("unique_states", 0)
                    if us > max_us:
                        max_us = us
                    scores = entry.get("scores", {})
                    wtg = scores.get("wtg", 0)
                    if wtg > max_wtg:
                        max_wtg = wtg
                all_unique_states.append(max_us)
            except Exception:
                continue
        apk_trace_stats[apk] = {
            "activities_visited": all_activities,
            "avg_unique_states": mean(all_unique_states) if all_unique_states else 0,
            "max_wtg_score": max_wtg,
        }

    # Utilization table
    lines.append("## Activity Utilization Ratios\n")
    lines.append(
        "| APK | SA Activities | Visited | Ratio | SA Transitions | Real Trans | Unique States | WTG Score |"
    )
    lines.append(
        "|-----|-------------|---------|-------|---------------|------------|--------------|-----------|"
    )

    ratios = []
    for apk in sorted(sa_data.keys()):
        sa = sa_data[apk]
        ts = apk_trace_stats.get(apk, {})
        visited = ts.get("activities_visited", set())
        n_visited = len(visited)
        n_sa = sa["n_activities"]
        ratio = n_visited / n_sa if n_sa > 0 else 0
        ratios.append(ratio)
        avg_us = ts.get("avg_unique_states", 0)
        max_wtg = ts.get("max_wtg_score", 0)
        lines.append(
            f"| {apk[:45]} | {n_sa} | {n_visited} | {ratio:.2f} | {sa['n_transitions']} | {sa['n_real_transitions']} | {avg_us:.1f} | {max_wtg} |"
        )

    if ratios:
        lines.append(f"\n**Mean activity utilization ratio**: {mean(ratios):.3f}")
        lines.append(f"**Median**: {sorted(ratios)[len(ratios)//2]:.3f}")

    # WTG=0 APKs analysis
    lines.append("\n## WTG Score = 0 APKs: SA Transition Analysis\n")
    lines.append(
        "| APK | SA Activities | SA Transitions | Real Transitions | Has Usable Transitions? |"
    )
    lines.append(
        "|-----|-------------|---------------|-----------------|------------------------|"
    )

    has_trans_but_unused = 0
    no_trans_expected = 0
    for apk in sorted(WTG_ZERO_APKS):
        sa = sa_data.get(apk)
        if not sa:
            lines.append(f"| {apk[:45]} | ? | ? | ? | NO SA JSON |")
            continue
        real_t = sa["n_real_transitions"]
        has_usable = "YES — BUG (unused)" if real_t > 0 else "NO — expected"
        if real_t > 0:
            has_trans_but_unused += 1
        else:
            no_trans_expected += 1
        lines.append(
            f"| {apk[:45]} | {sa['n_activities']} | {sa['n_transitions']} | {real_t} | {has_usable} |"
        )

    lines.append(
        f"\n**WTG=0 APKs with usable transitions in SA (bug)**: {has_trans_but_unused}"
    )
    lines.append(
        f"**WTG=0 APKs with no real transitions (expected)**: {no_trans_expected}"
    )

    # Correlation: more SA data -> better coverage?
    lines.append("\n## Correlation: SA Data Volume vs Coverage\n")
    csv_rows = load_consolidated_csv()
    apk_avg_cov = defaultdict(list)
    for row in csv_rows:
        if row["tool"] == "rvsmart:mvp":
            try:
                apk_avg_cov[row["apk"]].append(float(row["method_coverage"]))
            except (ValueError, KeyError):
                pass

    x_transitions = []
    y_coverage = []
    x_methods = []
    for apk in sa_data:
        if apk in apk_avg_cov:
            avg_cov = mean(apk_avg_cov[apk])
            x_transitions.append(sa_data[apk]["n_real_transitions"])
            x_methods.append(sa_data[apk]["n_methods"])
            y_coverage.append(avg_cov)

    if len(x_transitions) > 5:
        r_trans, p_trans = stats.spearmanr(x_transitions, y_coverage)
        r_methods, p_methods = stats.spearmanr(x_methods, y_coverage)
        lines.append(
            f"- **Spearman(real_transitions, method_coverage)**: r={r_trans:.3f}, p={p_trans:.4f}"
        )
        lines.append(
            f"- **Spearman(total_methods_in_SA, method_coverage)**: r={r_methods:.3f}, p={p_methods:.4f}"
        )
        lines.append(f"- N={len(x_transitions)} APKs with both SA and coverage data")
    else:
        lines.append("Insufficient data for correlation analysis.")

    lines.append("")
    return "\n".join(lines)


# ============================================================
# AREA 14: Execution Order and Contamination
# ============================================================
def area_14():
    lines = []
    lines.append("# Area 14 — Execution Order and Contamination\n")

    all_tasks = load_all_tasks()

    # Execution order per container
    lines.append("## Execution Order per Container\n")
    container_tasks = defaultdict(list)
    for ctr, task in all_tasks:
        container_tasks[ctr].append(task)

    for ctr in sorted(container_tasks.keys()):
        tasks = container_tasks[ctr]
        # Sort by start_time
        tasks_sorted = sorted(tasks, key=lambda t: t["result"].get("start_time", ""))
        lines.append(f"\n### {ctr} ({len(tasks_sorted)} tasks)\n")
        lines.append("| # | APK | Rep | Duration | Method Coverage |")
        lines.append("|---|-----|-----|----------|----------------|")
        for i, t in enumerate(tasks_sorted):
            apk = t["config"]["apk_name"]
            rep = t["config"]["repetition"]
            dur = t["result"].get("execution_time_seconds", 0)
            cov = t["result"].get("coverage_metrics", {}).get("method_coverage", 0)
            lines.append(f"| {i+1} | {apk[:40]} | {rep} | {dur}s | {cov:.1f}% |")

    # Rep1 vs Rep2 vs Rep3 comparison
    lines.append("\n## Rep-to-Rep Coverage Comparison\n")

    apk_rep_cov = defaultdict(
        lambda: defaultdict(list)
    )  # apk -> rep -> [coverage values]
    for ctr, task in all_tasks:
        apk = task["config"]["apk_name"]
        rep = task["config"]["repetition"]
        cov = task["result"].get("coverage_metrics", {}).get("method_coverage", 0)
        apk_rep_cov[apk][rep].append(cov)

    # For paired comparison, take mean across containers for each rep
    rep1_vals = []
    rep2_vals = []
    rep3_vals = []
    diff_apks = []

    lines.append("| APK | Rep1 Cov | Rep2 Cov | Rep3 Cov | Max Diff |")
    lines.append("|-----|----------|----------|----------|----------|")

    for apk in sorted(apk_rep_cov.keys()):
        reps = apk_rep_cov[apk]
        r1 = mean(reps.get(1, [0])) if reps.get(1) else None
        r2 = mean(reps.get(2, [0])) if reps.get(2) else None
        r3 = mean(reps.get(3, [0])) if reps.get(3) else None
        vals = [v for v in [r1, r2, r3] if v is not None]
        max_diff = max(vals) - min(vals) if len(vals) > 1 else 0

        if r1 is not None:
            rep1_vals.append(r1)
        if r2 is not None:
            rep2_vals.append(r2)
        if r3 is not None:
            rep3_vals.append(r3)

        if max_diff > 0:
            diff_apks.append((apk, max_diff))

        r1s = f"{r1:.1f}" if r1 is not None else "—"
        r2s = f"{r2:.1f}" if r2 is not None else "—"
        r3s = f"{r3:.1f}" if r3 is not None else "—"
        lines.append(f"| {apk[:45]} | {r1s} | {r2s} | {r3s} | {max_diff:.1f} |")

    # Statistical tests
    lines.append("\n## Statistical Tests\n")

    n = min(len(rep1_vals), len(rep2_vals), len(rep3_vals))
    if n > 5:
        # Friedman test (non-parametric repeated measures)
        stat_f, p_f = stats.friedmanchisquare(
            rep1_vals[:n], rep2_vals[:n], rep3_vals[:n]
        )
        lines.append(
            f"**Friedman test** (rep1 vs rep2 vs rep3): chi2={stat_f:.3f}, p={p_f:.4f}"
        )

        # Wilcoxon signed-rank for pairwise
        stat_12, p_12 = stats.wilcoxon(rep1_vals[:n], rep2_vals[:n])
        stat_13, p_13 = stats.wilcoxon(rep1_vals[:n], rep3_vals[:n])
        stat_23, p_23 = stats.wilcoxon(rep2_vals[:n], rep3_vals[:n])
        lines.append(f"**Wilcoxon rep1 vs rep2**: W={stat_12:.1f}, p={p_12:.4f}")
        lines.append(f"**Wilcoxon rep1 vs rep3**: W={stat_13:.1f}, p={p_13:.4f}")
        lines.append(f"**Wilcoxon rep2 vs rep3**: W={stat_23:.1f}, p={p_23:.4f}")
        lines.append(f"N={n} APKs used in paired tests")

    lines.append(
        f"\n**Mean coverage**: Rep1={mean(rep1_vals):.2f}, Rep2={mean(rep2_vals):.2f}, Rep3={mean(rep3_vals):.2f}"
    )

    # APKs with differences
    diff_apks.sort(key=lambda x: -x[1])
    lines.append(
        f"\n**APKs with non-zero coverage difference across reps**: {len(diff_apks)}"
    )
    if diff_apks:
        lines.append("\nTop 10 largest differences:")
        for apk, diff in diff_apks[:10]:
            lines.append(f"  - {apk}: {diff:.1f}pp")

    # Cross-APK contamination check
    lines.append("\n## Cross-APK Contamination Check\n")
    lines.append("Checking if APK N+1's rep1 is anomalous compared to its rep2/rep3.\n")

    anomalous = []
    for ctr in sorted(container_tasks.keys()):
        tasks = sorted(
            container_tasks[ctr], key=lambda t: t["result"].get("start_time", "")
        )
        # Group by APK in execution order
        apk_order = []
        current_apk = None
        for t in tasks:
            apk = t["config"]["apk_name"]
            if apk != current_apk:
                apk_order.append(apk)
                current_apk = apk

        for i, apk in enumerate(apk_order):
            if i == 0:
                continue  # skip first APK, nothing before it
            reps = apk_rep_cov[apk]
            r1 = mean(reps.get(1, [0])) if reps.get(1) else None
            r2 = mean(reps.get(2, [0])) if reps.get(2) else None
            r3 = mean(reps.get(3, [0])) if reps.get(3) else None
            if r1 is not None and r2 is not None and r3 is not None:
                later_mean = (r2 + r3) / 2
                diff = abs(r1 - later_mean)
                if diff > 5:  # 5pp threshold
                    anomalous.append((ctr, apk, r1, r2, r3, diff))

    if anomalous:
        lines.append(
            f"Found {len(anomalous)} APKs where rep1 differs by >5pp from mean(rep2,rep3):"
        )
        for ctr, apk, r1, r2, r3, diff in anomalous[:15]:
            lines.append(
                f"  - [{ctr}] {apk}: rep1={r1:.1f}, rep2={r2:.1f}, rep3={r3:.1f} (diff={diff:.1f}pp)"
            )
    else:
        lines.append(
            "No APKs found with rep1 anomaly >5pp — no evidence of cross-APK contamination."
        )

    # Check for pm clear / uninstall in traces
    lines.append("\n## App Data Clearing Between Reps\n")
    lines.append(
        "The platform uninstalls/reinstalls the APK between reps (standard rv-platform behavior)."
    )
    lines.append(
        "Trace files don't contain platform-level operations — only rvsmart's own actions."
    )

    lines.append("")
    return "\n".join(lines)


# ============================================================
# AREA 15: Exit Conditions
# ============================================================
def area_15():
    lines = []
    lines.append("# Area 15 — Exit Conditions\n")

    all_tasks = load_all_tasks()
    csv_rows = load_consolidated_csv()

    TIMEOUT = 600
    NEAR_TIMEOUT_LOW = 590
    NEAR_TIMEOUT_HIGH = 660

    # Classify each task
    classifications = defaultdict(int)
    early_exits = []
    errors = []

    lines.append("## RVSmart Task Classification\n")

    for ctr, task in all_tasks:
        state = task["result"].get("state", "UNKNOWN")
        dur = task["result"].get("execution_time_seconds", 0)
        apk = task["config"]["apk_name"]
        rep = task["config"]["repetition"]
        err = task["result"].get("error_message")

        if state == "ERROR" or (state != "COMPLETED"):
            classifications["ERROR"] += 1
            errors.append((ctr, apk, rep, dur, state, err))
        elif NEAR_TIMEOUT_LOW <= dur <= NEAR_TIMEOUT_HIGH:
            classifications["TIMEOUT (normal)"] += 1
        elif dur < NEAR_TIMEOUT_LOW:
            classifications["EARLY_EXIT"] += 1
            early_exits.append((ctr, apk, rep, dur, state))
        else:
            classifications["LATE_FINISH"] += 1

    total = sum(classifications.values())
    lines.append("| Classification | Count | % |")
    lines.append("|---------------|-------|---|")
    for cls in ["TIMEOUT (normal)", "EARLY_EXIT", "ERROR", "LATE_FINISH"]:
        count = classifications.get(cls, 0)
        pct = 100 * count / total if total > 0 else 0
        lines.append(f"| {cls} | {count} | {pct:.1f}% |")
    lines.append(f"| **Total** | **{total}** | **100%** |")

    # Early exits detail
    if early_exits:
        lines.append(f"\n## Early Exits ({len(early_exits)} tasks)\n")
        lines.append("| Container | APK | Rep | Duration (s) | Status |")
        lines.append("|-----------|-----|-----|-------------|--------|")
        for ctr, apk, rep, dur, state in sorted(early_exits, key=lambda x: x[3]):
            lines.append(f"| {ctr} | {apk[:40]} | {rep} | {dur} | {state} |")

        # Check last iterations of trace for early exits
        lines.append("\n### Last Trace Entries for Early Exits\n")
        trace_files = find_trace_files()
        trace_map = {(apk, rep, ctr): path for apk, rep, ctr, path in trace_files}

        for ctr, apk, rep, dur, state in early_exits[:10]:
            key = (apk, rep, ctr)
            if key in trace_map:
                try:
                    trace_lines = (
                        trace_map[key].read_text(errors="replace").strip().splitlines()
                    )
                    if trace_lines:
                        last = json.loads(trace_lines[-1])
                        last_iter = last.get("iteration", "?")
                        last_elapsed = last.get("elapsed_s", "?")
                        last_action = last.get("action_type", "?")
                        last_activity = last.get("activity", "?")
                        lines.append(
                            f"- **{apk[:35]}** rep{rep} [{ctr}]: last_iter={last_iter}, "
                            f"elapsed={last_elapsed}s, action={last_action}, activity={last_activity}"
                        )
                except Exception:
                    pass

    # Errors detail
    if errors:
        lines.append(f"\n## Errors ({len(errors)} tasks)\n")
        lines.append("| Container | APK | Rep | Duration | State | Error |")
        lines.append("|-----------|-----|-----|----------|-------|-------|")
        for ctr, apk, rep, dur, state, err in errors:
            err_short = (err or "—")[:80]
            lines.append(
                f"| {ctr} | {apk[:35]} | {rep} | {dur}s | {state} | {err_short} |"
            )

    # Duration distribution
    lines.append("\n## Duration Distribution (RVSmart)\n")
    rvsmart_durations = [
        task["result"].get("execution_time_seconds", 0) for _, task in all_tasks
    ]
    if rvsmart_durations:
        lines.append(f"- Mean: {mean(rvsmart_durations):.1f}s")
        lines.append(
            f"- Std: {stdev(rvsmart_durations):.1f}s"
            if len(rvsmart_durations) > 1
            else ""
        )
        lines.append(
            f"- Min: {min(rvsmart_durations)}s, Max: {max(rvsmart_durations)}s"
        )
        lines.append(
            f"- Median: {sorted(rvsmart_durations)[len(rvsmart_durations)//2]}s"
        )

    # Compare with ape/fastbot from consolidated CSV
    lines.append("\n## Comparison with APE and Fastbot Duration Patterns\n")

    tool_durations = defaultdict(list)
    for row in csv_rows:
        try:
            tool_durations[row["tool"]].append(float(row["duration_s"]))
        except (ValueError, KeyError):
            pass

    lines.append(
        "| Tool | N | Mean Duration | Std | Min | Max | Median | Near-Timeout (590-660s) % |"
    )
    lines.append(
        "|------|---|---------------|-----|-----|-----|--------|--------------------------|"
    )
    for tool in sorted(tool_durations.keys()):
        durs = tool_durations[tool]
        n = len(durs)
        m = mean(durs)
        s = stdev(durs) if n > 1 else 0
        med = sorted(durs)[n // 2]
        near_to = sum(1 for d in durs if NEAR_TIMEOUT_LOW <= d <= NEAR_TIMEOUT_HIGH)
        pct_to = 100 * near_to / n if n > 0 else 0
        lines.append(
            f"| {tool} | {n} | {m:.1f} | {s:.1f} | {min(durs):.0f} | {max(durs):.0f} | {med:.0f} | {pct_to:.1f}% |"
        )

    lines.append("")
    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================
def main():
    report = []
    report.append("# RVSmart Comparison — Remaining Validation Areas\n")
    report.append(f"Generated from data in `{DATA}`\n")

    print("Analyzing Area 10 (Logcat)...")
    report.append(area_10())

    print("Analyzing Area 13 (Static Analysis Utilization)...")
    report.append(area_13())

    print("Analyzing Area 14 (Execution Order and Contamination)...")
    report.append(area_14())

    print("Analyzing Area 15 (Exit Conditions)...")
    report.append(area_15())

    output = "\n---\n\n".join(report)
    out_path = DATA / "results" / "report_remaining_areas.md"
    out_path.write_text(output)
    print(f"\nReport written to: {out_path}")
    print("\n" + "=" * 80)
    print(output)


if __name__ == "__main__":
    main()
