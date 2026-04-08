#!/usr/bin/env python3
"""Analyze RVSmart trace files for UI action distributions and exploration efficiency."""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "results"
PRODUCTIVE_ACTIONS = {"CLICK", "LONG_CLICK", "SCROLL", "SET_TEXT"}
WASTED_ACTIONS = {"SKIP", "RESTART"}


def load_all_traces():
    """Load all trace files, returning list of (apk_name, run_id, lines)."""
    traces = []
    for trace_path in sorted(DATA_DIR.rglob("*.trace")):
        apk_name = trace_path.parent.name
        run_id = trace_path.stem  # e.g. apk__1__600__rvsmart:mvp
        lines = []
        with open(trace_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        lines.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        traces.append((apk_name, run_id, lines))
    return traces


def aggregate_by_apk(traces):
    """Merge all runs per APK into a single list of iterations."""
    by_apk = defaultdict(list)
    for apk_name, _, lines in traces:
        by_apk[apk_name].extend(lines)
    return dict(by_apk)


def part1(all_lines):
    print("# Part 1: Action Distribution (Total)")
    print()
    total = len(all_lines)
    print(f"**Total actions across all traces: {total}**")
    print()

    # By action_type
    type_counts = Counter(l.get("action_type", "UNKNOWN") for l in all_lines)
    print("## Action Type Distribution")
    print()
    print("| Action Type | Count | % |")
    print("|-------------|------:|--:|")
    for at, c in type_counts.most_common():
        print(f"| {at} | {c} | {100*c/total:.1f}% |")
    print()

    # By action_source
    source_counts = Counter(l.get("action_source", "UNKNOWN") for l in all_lines)
    print("## Action Source Distribution")
    print()
    print("| Action Source | Count | % |")
    print("|--------------|------:|--:|")
    for src, c in source_counts.most_common():
        print(f"| {src} | {c} | {100*c/total:.1f}% |")
    print()

    # Productive vs wasted
    productive = sum(
        1
        for l in all_lines
        if l.get("action_source") == "algorithm"
        and l.get("action_type") in PRODUCTIVE_ACTIONS
    )
    wasted = sum(1 for l in all_lines if l.get("action_type") in WASTED_ACTIONS)
    other = total - productive - wasted
    print("## Productive vs Wasted")
    print()
    print("| Category | Count | % |")
    print(f"|----------|------:|--:|")
    print(
        f"| Productive (algorithm CLICK/LONG_CLICK/SCROLL/SET_TEXT) | {productive} | {100*productive/total:.1f}% |"
    )
    print(
        f"| Wasted (SKIP/RESTART from any source) | {wasted} | {100*wasted/total:.1f}% |"
    )
    print(f"| Other | {other} | {100*other/total:.1f}% |")
    print(f"| **Productive/Wasted ratio** | **{productive/wasted:.2f}** | |")
    print()


def part2(by_apk):
    print("# Part 2: Per-Activity Action Distribution")
    print()

    # Top 20 APKs by unique_states
    apk_unique = {}
    for apk, lines in by_apk.items():
        max_us = max((l.get("unique_states", 0) for l in lines), default=0)
        apk_unique[apk] = max_us
    top20 = sorted(apk_unique, key=apk_unique.get, reverse=True)[:20]

    for apk in top20:
        lines = by_apk[apk]
        total_iter = len(lines)
        print(f"## {apk} (unique_states={apk_unique[apk]})")
        print()

        # Group by activity
        by_activity = defaultdict(list)
        for l in lines:
            act = l.get("activity", "") or "(empty)"
            by_activity[act].append(l)

        print("| Activity | Visits | % of total | Dominant action | Unique hashes |")
        print("|----------|-------:|-----------:|-----------------|---------------:|")
        for act, act_lines in sorted(by_activity.items(), key=lambda x: -len(x[1])):
            visits = len(act_lines)
            pct = 100 * visits / total_iter
            dominant = Counter(l.get("action_type", "") for l in act_lines).most_common(
                1
            )[0][0]
            hashes = len({l.get("hash", "") for l in act_lines if l.get("hash")})
            print(f"| {act} | {visits} | {pct:.1f}% | {dominant} | {hashes} |")
        print()

    # Identify stuck activities
    print("## Activities with dominant BACK or RESTART (potential stuck)")
    print()
    print("| APK | Activity | Visits | Dominant action |")
    print("|-----|----------|-------:|-----------------|")
    for apk in top20:
        lines = by_apk[apk]
        by_activity = defaultdict(list)
        for l in lines:
            act = l.get("activity", "") or "(empty)"
            by_activity[act].append(l)
        for act, act_lines in by_activity.items():
            dominant = Counter(l.get("action_type", "") for l in act_lines).most_common(
                1
            )[0][0]
            if dominant in ("BACK", "RESTART") and len(act_lines) >= 5:
                print(f"| {apk} | {act} | {len(act_lines)} | {dominant} |")
    print()


def part3(by_apk):
    print("# Part 3: Per-Screen (hash) Analysis")
    print()

    apk_unique = {}
    for apk, lines in by_apk.items():
        max_us = max((l.get("unique_states", 0) for l in lines), default=0)
        apk_unique[apk] = max_us
    top10 = sorted(apk_unique, key=apk_unique.get, reverse=True)[:10]

    for apk in top10:
        lines = by_apk[apk]
        print(f"## {apk} (unique_states={apk_unique[apk]})")
        print()

        # Group by hash
        by_hash = defaultdict(list)
        for l in lines:
            h = l.get("hash", "") or "(empty)"
            by_hash[h].append(l)

        # Top 5 most visited
        sorted_hashes = sorted(by_hash.items(), key=lambda x: -len(x[1]))
        print("### Top 5 most-visited screens")
        print()
        print("| Hash | Visits | Activity | Dominant action | Last saturation_rate |")
        print("|------|-------:|----------|-----------------|---------------------:|")
        for h, h_lines in sorted_hashes[:5]:
            visits = len(h_lines)
            act = Counter(l.get("activity", "") for l in h_lines).most_common(1)[0][0]
            dominant = Counter(l.get("action_type", "") for l in h_lines).most_common(
                1
            )[0][0]
            last_sat = None
            for l in reversed(h_lines):
                if "saturation_rate" in l:
                    last_sat = l["saturation_rate"]
                    break
            sat_str = f"{last_sat:.2f}" if last_sat is not None else "N/A"
            print(f"| {h} | {visits} | {act} | {dominant} | {sat_str} |")
        print()

        # One-shot screens
        one_shot = sum(
            1 for h, hl in by_hash.items() if len(hl) == 1 and h != "(empty)"
        )
        print(f"**One-shot screens (visited once):** {one_shot}")
        print()

        # Screens with >20 visits
        stuck = [
            (h, len(hl)) for h, hl in by_hash.items() if len(hl) > 20 and h != "(empty)"
        ]
        if stuck:
            print(f"**Screens with >20 visits (potential stuck loops):** {len(stuck)}")
            print()
            print("| Hash | Visits |")
            print("|------|-------:|")
            for h, v in sorted(stuck, key=lambda x: -x[1]):
                print(f"| {h} | {v} |")
        else:
            print("**Screens with >20 visits:** none")
        print()


def part4(all_lines):
    print("# Part 4: Widget Class Distribution")
    print()

    wc_counts = Counter(l.get("widget_class", "") for l in all_lines)
    total = len(all_lines)
    empty_count = wc_counts.get("", 0)

    print(
        f"**Empty widget_class: {empty_count} ({100*empty_count/total:.1f}%)** — typically BACK, RESTART, SKIP actions"
    )
    print()

    print("## Overall widget_class distribution (top 15, excluding empty)")
    print()
    print("| Widget Class | Count | % |")
    print("|-------------|------:|--:|")
    for wc, c in wc_counts.most_common(16):
        if wc == "":
            continue
        print(f"| {wc} | {c} | {100*c/total:.1f}% |")
    print()

    # For CLICK actions specifically
    click_lines = [l for l in all_lines if l.get("action_type") == "CLICK"]
    click_wc = Counter(l.get("widget_class", "") for l in click_lines)
    click_total = len(click_lines)
    print(f"## Widget classes for CLICK actions (total={click_total})")
    print()
    print("| Widget Class | Count | % of CLICKs |")
    print("|-------------|------:|------------:|")
    for wc, c in click_wc.most_common(15):
        label = wc if wc else "(empty)"
        print(f"| {label} | {c} | {100*c/click_total:.1f}% |")
    print()


def part5(by_apk):
    print("# Part 5: Exploration Efficiency")
    print()

    rows = []
    for apk, lines in by_apk.items():
        if not lines:
            continue
        max_us = max((l.get("unique_states", 0) for l in lines), default=0)
        max_elapsed = max((l.get("elapsed_s", 0) for l in lines), default=0)
        total_iter = len(lines)
        productive = sum(
            1
            for l in lines
            if l.get("action_source") == "algorithm"
            and l.get("action_type") in PRODUCTIVE_ACTIONS
        )
        minutes = max_elapsed / 60 if max_elapsed > 0 else 1
        nspm = max_us / minutes
        par = productive / total_iter if total_iter > 0 else 0
        rows.append((apk, max_us, total_iter, max_elapsed, nspm, par))

    rows.sort(key=lambda x: x[4], reverse=True)

    print("## Top 10 most efficient APKs (by new_states_per_minute)")
    print()
    print(
        "| APK | unique_states | total_iters | elapsed_s | states/min | productive_ratio |"
    )
    print("|-----|------:|------:|------:|------:|------:|")
    for apk, us, ti, es, nspm, par in rows[:10]:
        print(f"| {apk} | {us} | {ti} | {es:.0f} | {nspm:.2f} | {par:.2f} |")
    print()

    print("## Bottom 10 least efficient APKs")
    print()
    print(
        "| APK | unique_states | total_iters | elapsed_s | states/min | productive_ratio |"
    )
    print("|-----|------:|------:|------:|------:|------:|")
    for apk, us, ti, es, nspm, par in rows[-10:]:
        print(f"| {apk} | {us} | {ti} | {es:.0f} | {nspm:.2f} | {par:.2f} |")
    print()


def main():
    print("Loading traces...", file=sys.stderr)
    traces = load_all_traces()
    print(f"Loaded {len(traces)} trace files", file=sys.stderr)

    all_lines = []
    for _, _, lines in traces:
        all_lines.extend(lines)
    print(f"Total iterations: {len(all_lines)}", file=sys.stderr)

    by_apk = aggregate_by_apk(traces)
    print(f"Unique APKs: {len(by_apk)}", file=sys.stderr)

    # Redirect stdout for report
    part1(all_lines)
    part2(by_apk)
    part3(by_apk)
    part4(all_lines)
    part5(by_apk)


if __name__ == "__main__":
    main()
