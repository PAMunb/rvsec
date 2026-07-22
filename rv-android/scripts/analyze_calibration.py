#!/usr/bin/env python3
"""Analyze APE-RV calibration progress vs baselines.

Produces a markdown report comparing the best Optuna trials against baseline
tools on the same APK subset. Uses the same scoring methodology as the
calibration objective (trimmed mean 10%, score = 50% MOP + 50% method).

Report sections:
    1. Optuna state (complete/running/failed trial counts)
    2. Top-N trials with detailed coverage metrics
    3. Comparison against baseline tools (ape, fastbot, monkey, etc.)
    4. Per-APK violation details for the best trial
    5. Parameter range analysis (detects ceiling/floor effects)
    6. Best trial parameter values with position in search range
    7. Convergence tracking (score improvement over rounds)

Key functions:
    - ``load_optuna_trials``: Reads trial data from Optuna's SQLite DB.
    - ``compute_trial_metrics``: Scores a trial using trimmed-mean methodology.
    - ``load_baselines``: Loads and scores baseline tools from consolidated CSV.
    - ``analyze_ranges``: Detects if top trials cluster at parameter boundaries.
    - ``generate_report``: Assembles the full markdown report.

Usage:
    # Default: aperv_precal_macro vs exp3_consolidated baselines
    uv run python scripts/analyze_calibration.py

    # Custom paths:
    uv run python scripts/analyze_calibration.py \\
        --study-dir results/aperv_precal_macro \\
        --baseline-csv data/results/exp3_consolidated.csv \\
        --filter-file data/apks/aperv_precal_30.txt \\
        --top-n 10

    # Save report to file:
    uv run python scripts/analyze_calibration.py -o results/aperv_precal_macro/report.md
"""

import argparse
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import trim_mean

# Must match aperv_objective.py so analysis scores are consistent with calibration
TRIM_PROPORTION = 0.1
MOP_WEIGHT = 0.50
METHOD_WEIGHT = 0.50

ROOT = Path(__file__).resolve().parent.parent

# Column name mappings: the two CSV formats use different column names for the
# same metrics. These dicts provide a uniform interface so the analysis code
# can use semantic keys ("method", "mop") regardless of source format.

# Baseline CSV column mapping (unified format from consolidate_exp*.py)
BASELINE_COLS = {
    "method": "method_coverage",
    "mop": "mop_coverage",
    "activity": "activity_coverage",
    "errors": "total_errors",
}

# Calibration summary.csv column mapping (rv-platform ResultProcessor format)
TRIAL_COLS = {
    "method": "cov_method",
    "mop": "cov_rv_method",  # "rv_method" = RV-instrumented methods reached
    "activity": "cov_act",
    "errors": "errors",
}


def load_optuna_trials(study_dir: Path) -> tuple[list[dict], dict, dict, dict]:
    """Load completed trials and parameter data from Optuna's SQLite DB.

    Reads directly from the SQLite database instead of using the Optuna API
    to avoid importing optuna (heavy dependency) in an analysis-only script.

    Args:
        study_dir: Path to the calibration output directory containing
            ``optuna_study.db``.

    Returns:
        Tuple of:
            - trials: List of ``{"number": int, "score": float}`` dicts,
              sorted by score descending (best first).
            - states: Dict mapping state name to count (e.g. ``{"COMPLETE": 80}``).
            - param_data: Nested dict ``{trial_number: {param_name: value}}``.
            - distributions: Dict ``{param_name: distribution_json_dict}`` for
              range analysis.

    Raises:
        SystemExit: If the Optuna DB file does not exist.
    """
    db_path = study_dir / "optuna_study.db"
    if not db_path.exists():
        sys.exit(f"Optuna DB not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()

    # Study state
    c.execute("SELECT state, COUNT(*) FROM trials GROUP BY state")
    states = dict(c.fetchall())

    # Completed trials with scores, sorted best-first for top-N selection
    c.execute("""
        SELECT t.number, tv.value
        FROM trials t
        JOIN trial_values tv ON t.trial_id = tv.trial_id
        WHERE t.state = 'COMPLETE'
        ORDER BY tv.value DESC
    """)
    trials = [{"number": num, "score": score} for num, score in c.fetchall()]

    c.execute("SELECT COUNT(*) FROM trials")
    total_in_db = c.fetchone()[0]

    # Load params for all completed trials (for range analysis).
    # Optuna stores categorical values as integer indices into the choices list,
    # so we need distribution_json to decode back to the actual string value.
    c.execute("""
        SELECT t.number, tp.param_name, tp.param_value, tp.distribution_json
        FROM trials t
        JOIN trial_params tp ON t.trial_id = tp.trial_id
        WHERE t.state = 'COMPLETE'
    """)
    import json

    param_data = defaultdict(dict)
    distributions = {}
    for num, name, val, dist_json in c.fetchall():
        dist = json.loads(dist_json)
        distributions[name] = dist
        if dist["name"] == "CategoricalDistribution":
            # Decode index back to the original string choice
            choices = dist["attributes"]["choices"]
            param_data[num][name] = choices[int(float(val))]
        else:
            param_data[num][name] = float(val)

    conn.close()

    return trials, states, param_data, distributions


def load_trial_summary(study_dir: Path, trial_num: int) -> pd.DataFrame | None:
    """Load summary.csv for a single trial.

    The double-nested path matches the Docker volume mount layout used by
    ``calibration_orchestrator.py``: outer dir is the mount target, inner dir
    is created by rv-experiment using ``RV_EXPERIMENT_NAME=trial_N``.

    Args:
        study_dir: Base calibration output directory.
        trial_num: Optuna trial number.

    Returns:
        DataFrame with per-APK results, or None if summary.csv is missing
        (trial failed or container was killed before writing results).
    """
    p = study_dir / f"trial_{trial_num}" / f"trial_{trial_num}" / "summary.csv"
    if not p.exists():
        return None
    return pd.read_csv(p)


def compute_trial_metrics(df: pd.DataFrame) -> dict:
    """Compute trimmed-mean metrics for a trial's summary.csv.

    Uses the same scoring formula as ``aperv_objective.compute_score`` to
    ensure analysis scores match the values Optuna saw during calibration.

    Args:
        df: DataFrame loaded from a trial's summary.csv.

    Returns:
        Dict with keys: ``method``, ``mop``, ``activity`` (trimmed means),
        ``score`` (weighted composite), ``errors_sum``, ``errors_mean``,
        ``n_apks_with_errors``, ``n_apks``.
    """
    method = trim_mean(df[TRIAL_COLS["method"]].values, TRIM_PROPORTION)
    mop = trim_mean(df[TRIAL_COLS["mop"]].values, TRIM_PROPORTION)
    activity = trim_mean(df[TRIAL_COLS["activity"]].values, TRIM_PROPORTION)
    errors_sum = df[TRIAL_COLS["errors"]].sum()
    errors_mean = df[TRIAL_COLS["errors"]].mean()
    n_apks_with_errors = (df[TRIAL_COLS["errors"]] > 0).sum()
    score = MOP_WEIGHT * mop + METHOD_WEIGHT * method
    return {
        "method": method,
        "mop": mop,
        "activity": activity,
        "score": score,
        "errors_sum": errors_sum,
        "errors_mean": errors_mean,
        "n_apks_with_errors": n_apks_with_errors,
        "n_apks": len(df),
    }


def load_baselines(csv_path: Path, filter_apks: set[str]) -> dict[str, dict]:
    """Load baseline tools, filter to APK subset, and compute trimmed-mean metrics.

    The baseline CSV comes from ``consolidate_exp*.py`` scripts and contains
    results from multiple tools with multiple repetitions per APK. To make
    comparisons fair with calibration trials (which run each APK once), we
    first average repetitions per APK, then apply trimmed mean across APKs.

    Args:
        csv_path: Path to the consolidated baseline CSV.
        filter_apks: Set of APK names to include (must match the calibration
            subset to ensure apples-to-apples comparison).

    Returns:
        Dict mapping tool name to a metrics dict with the same structure as
        ``compute_trial_metrics`` output, plus ``n_reps``.
    """
    df = pd.read_csv(csv_path)
    df = df[df["apk"].isin(filter_apks)].copy()

    results = {}
    for tool, gdf in df.groupby("tool"):
        # Average reps per APK first to avoid biasing tools with more reps
        apk_means = (
            gdf.groupby("apk")
            .agg(
                {
                    BASELINE_COLS["method"]: "mean",
                    BASELINE_COLS["mop"]: "mean",
                    BASELINE_COLS["activity"]: "mean",
                    BASELINE_COLS["errors"]: "sum",  # sum errors across reps per APK
                }
            )
            .reset_index()
        )

        # Errors: total across all APKs and reps
        errors_total = gdf[BASELINE_COLS["errors"]].sum()
        errors_per_apk_mean = gdf.groupby("apk")[BASELINE_COLS["errors"]].sum().mean()
        n_apks_with_errors = (
            gdf.groupby("apk")[BASELINE_COLS["errors"]].sum() > 0
        ).sum()

        # Assumes uniform rep count across APKs (enforced by experiment design)
        n_reps = int(gdf.groupby("apk").size().iloc[0])
        n_apks = len(apk_means)

        # Trimmed mean for robustness, matching calibration objective methodology
        method = trim_mean(apk_means[BASELINE_COLS["method"]].values, TRIM_PROPORTION)
        mop = trim_mean(apk_means[BASELINE_COLS["mop"]].values, TRIM_PROPORTION)
        activity = trim_mean(
            apk_means[BASELINE_COLS["activity"]].values, TRIM_PROPORTION
        )
        score = MOP_WEIGHT * mop + METHOD_WEIGHT * method

        results[tool] = {
            "method": method,
            "mop": mop,
            "activity": activity,
            "score": score,
            "errors_sum": errors_total,
            "errors_mean": errors_per_apk_mean,
            "n_apks_with_errors": n_apks_with_errors,
            "n_apks": n_apks,
            "n_reps": n_reps,
        }

    return results


def analyze_ranges(
    param_data: dict, distributions: dict, top_n_trials: list[int]
) -> list[dict]:
    """Analyze parameter ranges vs observed values in top trials.

    Detects ceiling/floor effects: if the best trials cluster near a
    parameter boundary, the search range may need to be expanded. This is
    critical for iterating on the parameter space definition -- a ceiling
    warning means Optuna "wants" to go higher but is constrained.

    Args:
        param_data: Nested dict ``{trial_number: {param_name: value}}``.
        distributions: Dict ``{param_name: distribution_json_dict}`` from Optuna.
        top_n_trials: List of trial numbers for the top-N trials (best first).

    Returns:
        List of dicts, one per parameter. Numeric params include ``top_avg``,
        ``top_pos_pct`` (position as % of range), and ``warning`` (non-empty
        if ceiling/floor detected). Categorical params include value counts.
    """
    top_set = set(top_n_trials)
    results = []

    for name, dist in sorted(distributions.items()):
        attrs = dist.get("attributes", {})

        all_vals = [
            param_data[t].get(name) for t in param_data if name in param_data[t]
        ]
        top_vals = [
            param_data[t].get(name)
            for t in param_data
            if t in top_set and name in param_data[t]
        ]

        entry = {"name": name, "dist_type": dist["name"]}

        if dist["name"] == "CategoricalDistribution":
            from collections import Counter

            entry["choices"] = attrs["choices"]
            entry["all_counts"] = dict(Counter(all_vals))
            entry["top_counts"] = dict(Counter(top_vals))
        else:
            low = attrs["low"]
            high = attrs["high"]
            numeric_top = [v for v in top_vals if isinstance(v, (int, float))]
            numeric_all = [v for v in all_vals if isinstance(v, (int, float))]

            entry["low"] = low
            entry["high"] = high
            entry["step"] = attrs.get("step")
            entry["log"] = attrs.get("log", False)

            if numeric_top:
                avg = np.mean(numeric_top)
                entry["top_avg"] = avg
                entry["top_min"] = min(numeric_top)
                entry["top_max"] = max(numeric_top)
                # Position as percentage of range: 0% = at floor, 100% = at ceiling
                entry["top_pos_pct"] = (
                    (avg - low) / (high - low) * 100 if high > low else 0
                )
            if numeric_all:
                entry["all_min"] = min(numeric_all)
                entry["all_max"] = max(numeric_all)

            # Ceiling/floor warnings: if the best trials are near a boundary,
            # Optuna may be constrained and the range should be expanded
            warn = ""
            if numeric_top:
                pos = entry["top_pos_pct"]
                if pos >= 90:
                    warn = "!! TOP AVG AT CEILING"
                elif pos <= 10:
                    warn = "!! TOP AVG AT FLOOR"
                # Also check the single best trial specifically
                best_val = param_data[top_n_trials[0]].get(name)
                if isinstance(best_val, (int, float)):
                    best_pos = (best_val - low) / (high - low) * 100
                    if best_pos >= 95:
                        warn = "!! BEST AT CEILING"
                    elif best_pos <= 5:
                        warn = "!! BEST AT FLOOR"
            entry["warning"] = warn

        results.append(entry)

    return results


def generate_report(
    study_dir: Path,
    trials: list[dict],
    states: dict,
    param_data: dict,
    distributions: dict,
    baselines: dict[str, dict],
    top_n: int,
    target_trials: int,
) -> str:
    """Generate a comprehensive markdown report for calibration analysis.

    Assembles 7 report sections comparing calibration trials against baselines,
    analyzing parameter convergence, and detecting range boundary issues.

    Args:
        study_dir: Path to the calibration output directory.
        trials: List of ``{"number", "score"}`` dicts, sorted best-first.
        states: Dict mapping trial state names to counts.
        param_data: Nested dict ``{trial_number: {param_name: value}}``.
        distributions: Dict ``{param_name: distribution_json_dict}``.
        baselines: Dict ``{tool_name: metrics_dict}`` from ``load_baselines``.
        top_n: Number of top trials to display in detail.
        target_trials: Target trial count for progress percentage.

    Returns:
        Complete markdown report as a string.
    """
    lines = []
    w = lines.append

    w(f"# Calibration Report: {study_dir.name}\n")
    w(f"**Generated**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n")

    # --- 1. Optuna State ---
    w("## 1. Optuna State\n")
    complete = states.get("COMPLETE", 0)
    running = states.get("RUNNING", 0)
    fail = states.get("FAIL", 0)
    total = complete + running + fail
    pct = complete / target_trials * 100 if target_trials else 0
    w("| Metric | Value |")
    w(f"|--------|-------|")
    w(f"| Complete | {complete} |")
    w(f"| Running | {running} |")
    w(f"| Failed | {fail} |")
    w(f"| Target | {target_trials} |")
    w(f"| Progress | {pct:.1f}% |")
    w("")

    # --- 2. Top-N Trials ---
    w(f"## 2. Top {top_n} Trials\n")
    w("| # | Score | Method% | MOP% | Activity% | Errors | APKs w/err |")
    w(f"|---|-------|---------|------|-----------|--------|------------|")

    top_trials_metrics = []
    for t in trials[:top_n]:
        df = load_trial_summary(study_dir, t["number"])
        if df is None:
            continue
        m = compute_trial_metrics(df)
        m["number"] = t["number"]
        top_trials_metrics.append(m)
        w(
            f"| {t['number']:>3} | {m['score']:.2f} | {m['method']:.2f} | {m['mop']:.2f} "
            f"| {m['activity']:.2f} | {m['errors_sum']:.0f} | {m['n_apks_with_errors']}/{m['n_apks']} |"
        )
    w("")

    # Score distribution
    scores = [t["score"] for t in trials]
    w("**Score distribution**:")
    w(
        f"best={scores[0]:.2f}, median={np.median(scores):.2f}, "
        f"worst={scores[-1]:.2f}, mean={np.mean(scores):.2f}, std={np.std(scores):.2f}\n"
    )

    # --- 3. Comparison with Baselines ---
    w("## 3. Comparison with Baselines\n")
    w("All metrics use trimmed mean (10% cut) on the same APK subset.\n")
    w("| Tool | Method% | MOP% | Activity% | Score | Errors | APKs w/err | Reps |")
    w(f"|------|---------|------|-----------|-------|--------|------------|------|")

    for tool in sorted(baselines.keys()):
        b = baselines[tool]
        w(
            f"| `{tool}` | {b['method']:.2f} | {b['mop']:.2f} | {b['activity']:.2f} "
            f"| {b['score']:.2f} | {b['errors_sum']:.0f} | {b['n_apks_with_errors']}/{b['n_apks']} "
            f"| {b['n_reps']} |"
        )

    # Add best calibrated and top-3 avg
    if top_trials_metrics:
        best = top_trials_metrics[0]
        w(
            f"| **CALIBRATED #{best['number']}** | **{best['method']:.2f}** | **{best['mop']:.2f}** "
            f"| **{best['activity']:.2f}** | **{best['score']:.2f}** | **{best['errors_sum']:.0f}** "
            f"| **{best['n_apks_with_errors']}/{best['n_apks']}** | 1 |"
        )

        if len(top_trials_metrics) >= 3:
            top3 = top_trials_metrics[:3]
            avg_m = np.mean([t["method"] for t in top3])
            avg_mop = np.mean([t["mop"] for t in top3])
            avg_act = np.mean([t["activity"] for t in top3])
            avg_score = np.mean([t["score"] for t in top3])
            avg_err = np.mean([t["errors_sum"] for t in top3])
            avg_apks_err = np.mean([t["n_apks_with_errors"] for t in top3])
            w(
                f"| **CALIBRATED top-3 avg** | **{avg_m:.2f}** | **{avg_mop:.2f}** "
                f"| **{avg_act:.2f}** | **{avg_score:.2f}** | **{avg_err:.0f}** "
                f"| **{avg_apks_err:.0f}/{top3[0]['n_apks']}** | 1 |"
            )
    w("")

    # Delta vs baselines
    if top_trials_metrics and baselines:
        best = top_trials_metrics[0]
        w("### Deltas vs baselines\n")
        w("| Baseline | Δ Method | Δ MOP | Δ Score | Δ Errors |")
        w(f"|----------|----------|-------|---------|----------|")
        for tool in sorted(baselines.keys()):
            b = baselines[tool]
            dm = best["method"] - b["method"]
            dmop = best["mop"] - b["mop"]
            ds = best["score"] - b["score"]
            de = best["errors_sum"] - b["errors_sum"]
            sign_m = "+" if dm >= 0 else ""
            sign_mop = "+" if dmop >= 0 else ""
            sign_s = "+" if ds >= 0 else ""
            sign_e = "+" if de >= 0 else ""
            w(
                f"| `{tool}` | {sign_m}{dm:.2f}pp | {sign_mop}{dmop:.2f}pp "
                f"| {sign_s}{ds:.2f} | {sign_e}{de:.0f} |"
            )
        w("")

    # --- 4. Per-APK Comparison (best trial vs best baseline) ---
    if top_trials_metrics:
        best_num = top_trials_metrics[0]["number"]
        best_df = load_trial_summary(study_dir, best_num)
        if best_df is not None:
            w("## 4. Per-APK Violations (best trial)\n")
            err_df = best_df[best_df[TRIAL_COLS["errors"]] > 0].sort_values(
                TRIAL_COLS["errors"], ascending=False
            )
            if len(err_df) > 0:
                w("| APK | Method% | MOP% | Violations |")
                w(f"|-----|---------|------|------------|")
                for _, row in err_df.iterrows():
                    apk_short = row["apk"][:50]
                    w(
                        f"| {apk_short} | {row[TRIAL_COLS['method']]:.1f} "
                        f"| {row[TRIAL_COLS['mop']]:.1f} | {int(row[TRIAL_COLS['errors']])} |"
                    )
                w(
                    f"\n**{len(err_df)}/{len(best_df)} APKs** detected violations "
                    f"(total: {int(best_df[TRIAL_COLS['errors']].sum())})\n"
                )
            else:
                w("No violations detected.\n")

    # --- 5. Range Analysis ---
    if top_trials_metrics:
        top_nums = [t["number"] for t in top_trials_metrics[:top_n]]
        range_results = analyze_ranges(param_data, distributions, top_nums)

        w("## 5. Parameter Range Analysis\n")
        w(f"| Parameter | Range | Top{top_n} avg | Pos% | Warning |")
        w("|-----------|-------|----------|------|---------|")

        for r in range_results:
            if r["dist_type"] == "CategoricalDistribution":
                w(
                    f"| `{r['name']}` | {r['choices']} | all:{r['all_counts']} "
                    f"| — | top:{r['top_counts']} |"
                )
            else:
                low, high = r["low"], r["high"]
                if "top_avg" in r:
                    avg = r["top_avg"]
                    pos = r["top_pos_pct"]
                    if isinstance(low, float) and low < 1:
                        w(
                            f"| `{r['name']}` | [{low:.3f}, {high:.3f}] "
                            f"| {avg:.4f} | {pos:.0f}% | {r['warning']} |"
                        )
                    else:
                        w(
                            f"| `{r['name']}` | [{low:.0f}, {high:.0f}] "
                            f"| {avg:.1f} | {pos:.0f}% | {r['warning']} |"
                        )
                else:
                    w(f"| `{r['name']}` | [{low}, {high}] | N/A (conditional) | — | |")
        w("")

    # --- 6. Best Trial Params ---
    if top_trials_metrics:
        best_num = top_trials_metrics[0]["number"]
        w(f"## 6. Best Trial #{best_num} Parameters\n")
        w("| Parameter | Value | Position in range |")
        w(f"|-----------|-------|-------------------|")
        params = param_data.get(best_num, {})
        for name in sorted(params.keys()):
            val = params[name]
            dist = distributions.get(name, {})
            if dist.get("name") == "CategoricalDistribution":
                w(f"| `{name}` | {val} | — |")
            else:
                attrs = dist.get("attributes", {})
                low = attrs.get("low", 0)
                high = attrs.get("high", 1)
                if isinstance(val, (int, float)) and high > low:
                    pos = (val - low) / (high - low) * 100
                    if isinstance(low, float) and low < 1:
                        w(f"| `{name}` | {val:.6f} | {pos:.0f}% |")
                    else:
                        w(f"| `{name}` | {val:.0f} | {pos:.0f}% |")
                else:
                    w(f"| `{name}` | {val} | — |")
        w("")

    # --- 7. Convergence ---
    w("## 7. Convergence by Round\n")
    trials_by_num = sorted(trials, key=lambda t: t["number"])
    w("| Round | Trials | Best in round | Best overall | Improved? |")
    w(f"|-------|--------|---------------|-------------|-----------|")

    round_size = 10  # default containers per round
    best_so_far = -float("inf")
    for i in range(0, len(trials_by_num), round_size):
        chunk = trials_by_num[i : i + round_size]
        round_n = i // round_size + 1
        round_best = max(t["score"] for t in chunk)
        improved = ""
        if round_best > best_so_far:
            best_so_far = round_best
            improved = "← NEW BEST"
        w(
            f"| {round_n} | {chunk[0]['number']}-{chunk[-1]['number']} "
            f"| {round_best:.2f} | {best_so_far:.2f} | {improved} |"
        )
    w("")

    return "\n".join(lines)


def main() -> None:
    """Parse arguments, load data, and generate the calibration report."""
    parser = argparse.ArgumentParser(
        description="Analyze APE-RV calibration progress vs baselines.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--study-dir",
        type=Path,
        default=ROOT / "results" / "aperv_precal_macro",
        help="Path to calibration output directory (default: results/aperv_precal_macro)",
    )
    parser.add_argument(
        "--baseline-csv",
        type=Path,
        default=ROOT / "data" / "results" / "exp3_consolidated.csv",
        help="Path to consolidated baseline CSV (default: data/results/exp3_consolidated.csv)",
    )
    parser.add_argument(
        "--filter-file",
        type=Path,
        default=ROOT / "data" / "apks" / "aperv_precal_30.txt",
        help="APK filter file (default: data/apks/aperv_precal_30.txt)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Number of top trials to show (default: 10)",
    )
    parser.add_argument(
        "--target-trials",
        type=int,
        default=130,
        help="Target number of trials for progress percentage (default: 130)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Write report to file instead of stdout",
    )
    args = parser.parse_args()

    # Load filter APKs
    filter_apks = set()
    with open(args.filter_file) as f:
        for line in f:
            if line.strip():
                filter_apks.add(line.strip())

    # Load Optuna data
    trials, states, param_data, distributions = load_optuna_trials(args.study_dir)

    if not trials:
        sys.exit("No completed trials found.")

    # Load baselines
    baselines = load_baselines(args.baseline_csv, filter_apks)

    # Generate report
    report = generate_report(
        study_dir=args.study_dir,
        trials=trials,
        states=states,
        param_data=param_data,
        distributions=distributions,
        baselines=baselines,
        top_n=args.top_n,
        target_trials=args.target_trials,
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
