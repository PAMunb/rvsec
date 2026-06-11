"""
Regenerate summary_regen.csv, coverage_regen.csv, and errors_regen.csv for one
container of experiment 2026-05-08, reusing the official rv-android parser.

Why this exists: the consolidated CSVs in RESULTADOS/ were produced without
static_data. `_reconstruct_repository_from_logcat()` called
`parse_logcat_file(file)` without the second argument, so LogcatRepository had
no denominators and could not mark MOP methods. Coverage degenerated. Errors
appear correct (RVSEC violations are self-contained in the logcat).

What it does: for every `.logcat` file under a container directory
(`RESULTADOS/m<i>/results/exp_<j>/exp_<j>/`):
  1. Parse the filename `<apk>__<rep>__<timeout>__<tool>.logcat`.
  2. Load StaticAnalysisData from the matching JSON in APKS_FINAL_JCA_DEXLIB
     (cached per APK).
     Passes `package=""` to the parser: GATOR upstream already filtered classes
     by the real code_package via PackageDetector, and the JSON's `package`
     field is the manifest_package (which can diverge, e.g. app.dumdum vs.
     io.nekohasekai.sagernet). See docs/20260514_regenerar_planilhas.md §9.
  3. Call `parse_logcat_file(logcat_path, static_data)`.
  4. Emit rows matching the official `result_processor.py` schemas:
       - summary_regen.csv:  apk,rep,timeout,tool,cov_act,cov_method,cov_rv_method,errors
       - coverage_regen.csv: apk,rep,timeout,tool,time,class,method,signature,
                             cov_class,cov_act,cov_method,cov_rv_method
       - errors_regen.csv:   apk,rep,timeout,tool,time,spec,class,method,message,unique_msg

Constraint: does NOT modify rv-android. Only consumes public APIs
(`parse_logcat_file`, `StaticAnalysisParser.parse_file`, `LogcatRepository`).

Usage:
    uv run python scripts/regenerate_results/regenerate_container.py \\
        /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/RESULTADOS/m1/results/exp_00/exp_00 \\
        --workers 8 \\
        --static-dir /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB

Output: three `*_regen.csv` files written inside container_dir, plus a stats
line on stdout.
"""

import argparse
import csv
import logging
import os
import re
import sys
from datetime import datetime
from functools import lru_cache
from multiprocessing import Pool
from typing import Dict, List, Optional, Tuple

from rv_coverage.parser.log.logcat_parser import parse_logcat_file
from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser

# Silence verbose parser logs. The logcat_parser WARNING-level messages are
# from a pre-existing parser limitation: Android logcat truncates lines at
# ~4076 bytes, and the official Soot-signature regex needs the trailing `)>`,
# so very long constructor signatures (e.g. databinding _init_ with 100+
# params) fail to parse. We cannot fix this without modifying rv-android, and
# the impact is negligible (<0.1% of RVSEC-COV lines per logcat).
logging.getLogger("rv_static_analysis.parser.static.static_analysis_parser").setLevel(logging.ERROR)
logging.getLogger("rv_android_core.util.repository_initializer").setLevel(logging.ERROR)
logging.getLogger("rv_coverage.parser.log.logcat_parser").setLevel(logging.ERROR)

# Filename convention. Tool may contain `:` (e.g. droidbot:dfs_greedy).
LOGCAT_NAME_RE = re.compile(r"^(?P<apk>.+\.apk)__(?P<rep>\d+)__(?P<timeout>\d+)__(?P<tool>.+)\.logcat$")

# Exact headers from result_processor.py.
# Summary schema combines the old experiment columns
# (ase-journal/dataset/results/backup/summary/) with both error counters that
# LogcatRepository exposes: total (every RVSEC line, with duplicates) and unique
# (deduplicated by unique_msg = class:::method:::spec:::error_type:::message).
# CoverageMetrics.to_dict() returns both as `total_errors` and `unique_errors`.
SUMMARY_HEADER = [
    "apk", "rep", "timeout", "tool",
    "cov_act", "cov_class", "cov_method",
    "cov_reachable", "cov_reaches_target", "cov_directly_reaches_target",
    "mop_errors_total", "mop_errors_unique",
]
COVERAGE_HEADER = [
    "apk", "rep", "timeout", "tool", "time", "class", "method", "signature",
    "cov_class", "cov_act", "cov_method", "cov_rv_method",
]
ERRORS_HEADER = ["apk", "rep", "timeout", "tool", "time", "spec", "class", "method", "message", "unique_msg"]


def parse_logcat_filename(filename: str) -> Optional[Tuple[str, int, int, str]]:
    """Return (apk, rep, timeout, tool), or None if the filename does not match."""
    m = LOGCAT_NAME_RE.match(filename)
    if not m:
        return None
    return m["apk"], int(m["rep"]), int(m["timeout"]), m["tool"]


# Per-APK static_data cache. Each worker has its own (per-process) cache. Size 256
# easily holds the ~12 APKs per container and amortizes JSON parsing across reps/timeouts.
@lru_cache(maxsize=256)
def load_static_data(json_path: str):
    """Load StaticAnalysisData from JSON with package='' (see module docstring)."""
    if not os.path.isfile(json_path):
        return None
    parser = StaticAnalysisParser()
    return parser.parse_file(json_path, "")


def process_logcat(args: Tuple[str, str]) -> Optional[Dict]:
    """Process one logcat. Returns a dict with row lists, or None on bad filename."""
    logcat_path, static_dir = args
    filename = os.path.basename(logcat_path)
    parsed = parse_logcat_filename(filename)
    if not parsed:
        return None
    apk, rep, timeout, tool = parsed

    json_path = os.path.join(static_dir, f"{apk}.json")
    static_data = load_static_data(json_path)

    repo = parse_logcat_file(logcat_path, static_data)

    # ---- compute t0 (task start proxy) ----
    # tool_execution_start_time is runtime-only state (set by CoverageTracker on
    # tool start); it is not persisted in the .logcat. When reparsing offline,
    # we approximate it as the earliest RVSEC/RVSEC-COV timestamp in the file.
    # This biases `time` toward "seconds since first instrumented event" rather
    # than "seconds since adb shell am start", but the delta is < 1s in
    # practice (instrumentation classes load very early in app startup).
    raw_method_calls = repo.get_method_calls()
    raw_errors = repo.get_errors()

    t0: Optional[datetime] = None
    for call in raw_method_calls:
        fca = call.get("first_called_at")
        if fca:
            ts = datetime.fromisoformat(fca)
            if t0 is None or ts < t0:
                t0 = ts
    for err in raw_errors:
        # RvErrorLog.to_dict() emits time_occurred as milliseconds since epoch.
        tms = err.get("time_occurred")
        if tms:
            ts = datetime.fromtimestamp(tms / 1000.0)
            if t0 is None or ts < t0:
                t0 = ts

    def seconds_since_t0(iso_or_ms) -> int:
        if t0 is None or iso_or_ms is None:
            return 0
        if isinstance(iso_or_ms, str):
            ts = datetime.fromisoformat(iso_or_ms)
        else:
            ts = datetime.fromtimestamp(iso_or_ms / 1000.0)
        delta = (ts - t0).total_seconds()
        return max(0, int(delta))

    # ---- summary (one row) ----
    # CoverageMetrics.to_dict() provides every coverage breakdown the old
    # experiment summary used, plus both error counters. See SUMMARY_HEADER.
    metrics = repo.calculate_metrics()
    metrics_dict = metrics.to_dict()
    summary_row = [
        apk, rep, timeout, tool,
        round(metrics_dict.get("activity_coverage", 0) or 0, 2),
        round(metrics_dict.get("class_coverage", 0) or 0, 2),
        round(metrics_dict.get("method_coverage", 0) or 0, 2),
        round(metrics_dict.get("reachable_method_coverage", 0) or 0, 2),
        round(metrics_dict.get("mop_method_coverage", 0) or 0, 2),
        round(metrics_dict.get("direct_mop_method_coverage", 0) or 0, 2),
        metrics_dict.get("total_errors", 0) or 0,
        metrics_dict.get("unique_errors", 0) or 0,
    ]

    # ---- coverage (N rows, one per unique called method, chronological) ----
    # Replicates result_processor._write_task_coverage_data exactly: iterate
    # repository.get_method_calls() (already deduplicated and sorted by first-call
    # time), keep cumulative sets, and compute progressive cov_* values.
    coverage_rows: List[List] = []
    if static_data is not None:
        total_methods = len(repo.get_static_methods())
        total_activities = len(repo.get_static_activities())
        total_mop = len(repo.get_target_methods()) or 1  # avoid div-by-zero, matches result_processor
        # total_classes do MESMO denominador que o summary usa (CoverageMetrics.class_coverage
        # = called_classes / total_classes). Assim a última linha progressiva de cov_class bate
        # exatamente com summary.cov_class. Ver rv_android_core.domain.coverage:427.
        total_classes = metrics_dict.get("total_classes", 0) or 0

        called_methods: set = set()
        called_activities: set = set()
        called_mop: set = set()
        called_classes: set = set()

        # Resort by absolute first_called_at (since time_since_task_start is 0
        # for all calls in offline reparse, the original sort by `time` is
        # undefined). Falling back to `first_called_at` puts entries in true
        # chronological order; ties keep insertion order from get_method_calls().
        ordered_calls = sorted(
            raw_method_calls,
            key=lambda c: c.get("first_called_at") or "",
        )

        for call in ordered_calls:
            signature = call.get("signature", "")
            called_methods.add(signature)
            activity = call.get("activity")
            if activity:
                called_activities.add(activity)
            if call.get("is_mop_method", False):
                called_mop.add(signature)
            class_name = call.get("class_name")
            if class_name:
                called_classes.add(class_name)

            method_cov = (len(called_methods) / total_methods * 100) if total_methods > 0 else 0
            activity_cov = (len(called_activities) / total_activities * 100) if total_activities > 0 else 0
            mop_cov = (len(called_mop) / total_mop * 100) if total_mop > 0 else 0
            class_cov = (len(called_classes) / total_classes * 100) if total_classes > 0 else 0

            coverage_rows.append([
                apk, rep, timeout, tool,
                seconds_since_t0(call.get("first_called_at")),
                call.get("class_name", ""),
                call.get("method_name", ""),
                signature,
                round(class_cov, 2),     # cov_class — cobertura de classe progressiva real
                round(activity_cov, 2),  # cov_act
                round(method_cov, 2),    # cov_method
                round(mop_cov, 2),       # cov_rv_method
            ])
    # If static_data is missing (APK without JSON), coverage_rows stays empty and
    # we record a warning. We do not emit degenerate rows (the original consolidated
    # CSV already did that).

    # ---- errors (N rows, one per RVSEC violation) ----
    # Sort by absolute timestamp (time_occurred ms). Falls back to insertion
    # order when time_occurred is missing, matching get_errors() behavior.
    ordered_errors = sorted(raw_errors, key=lambda e: e.get("time_occurred") or 0)

    errors_rows: List[List] = []
    for err in ordered_errors:
        class_full = err.get("class_full_name", "")
        method_n = err.get("method", "")
        spec = err.get("spec", "")
        err_type = err.get("error_type", "")
        msg = err.get("message", "")
        unique = err.get("unique_msg") or f"{class_full}:::{method_n}:::{spec}:::{err_type}:::{msg}"
        t = seconds_since_t0(err.get("time_occurred"))
        errors_rows.append([apk, rep, timeout, tool, t, spec, class_full, method_n, msg, unique])

    return {
        "logcat": filename,
        "apk": apk,
        "summary": summary_row,
        "coverage": coverage_rows,
        "errors": errors_rows,
        "missing_static": static_data is None,
    }


def discover_logcats(container_dir: str) -> List[str]:
    """Return absolute paths of every *.logcat under container_dir."""
    out = []
    for root, _, files in os.walk(container_dir):
        for f in files:
            if f.endswith(".logcat"):
                out.append(os.path.join(root, f))
    return sorted(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("container_dir", help="Path to one container (e.g. RESULTADOS/m1/results/exp_00/exp_00)")
    ap.add_argument(
        "--static-dir",
        default="/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB",
        help="Directory holding the static analysis JSONs (one per APK).",
    )
    ap.add_argument("--workers", type=int, default=8, help="Worker count for the internal pool.")
    ap.add_argument("--limit", type=int, default=0, help="Process only the first N logcats (debug).")
    args = ap.parse_args()

    container_dir = os.path.abspath(args.container_dir)
    if not os.path.isdir(container_dir):
        print(f"ERROR: container_dir does not exist: {container_dir}", file=sys.stderr)
        return 2
    if not os.path.isdir(args.static_dir):
        print(f"ERROR: static-dir does not exist: {args.static_dir}", file=sys.stderr)
        return 2

    logcats = discover_logcats(container_dir)
    if args.limit > 0:
        logcats = logcats[: args.limit]
    if not logcats:
        print(f"WARNING: no .logcat files found in {container_dir}", file=sys.stderr)
        return 1

    print(f"[{container_dir}] discovered {len(logcats)} logcats, workers={args.workers}", flush=True)

    summary_path = os.path.join(container_dir, "summary_regen.csv")
    coverage_path = os.path.join(container_dir, "coverage_regen.csv")
    errors_path = os.path.join(container_dir, "errors_regen.csv")

    n_processed = 0
    n_missing_static = 0
    n_unparseable_name = 0
    n_cov_rows = 0
    n_err_rows = 0
    missing_static_apks: set = set()

    with open(summary_path, "w", newline="", encoding="utf-8") as fs, \
         open(coverage_path, "w", newline="", encoding="utf-8") as fc, \
         open(errors_path, "w", newline="", encoding="utf-8") as fe:
        ws = csv.writer(fs); ws.writerow(SUMMARY_HEADER)
        wc = csv.writer(fc); wc.writerow(COVERAGE_HEADER)
        we = csv.writer(fe); we.writerow(ERRORS_HEADER)

        # Each pool worker has its own @lru_cache of static_data (per-process).
        # Acceptable: each container has ~12 unique APKs, so a worker reloads at
        # most 12 JSONs over its lifetime.
        pool_args = [(lp, args.static_dir) for lp in logcats]
        with Pool(processes=args.workers) as pool:
            for result in pool.imap_unordered(process_logcat, pool_args, chunksize=8):
                if result is None:
                    n_unparseable_name += 1
                    continue
                ws.writerow(result["summary"])
                wc.writerows(result["coverage"])
                we.writerows(result["errors"])
                n_processed += 1
                n_cov_rows += len(result["coverage"])
                n_err_rows += len(result["errors"])
                if result["missing_static"]:
                    n_missing_static += 1
                    missing_static_apks.add(result["apk"])

    print(
        f"[{container_dir}] OK  logcats={n_processed}  cov_rows={n_cov_rows}  "
        f"err_rows={n_err_rows}  missing_static={n_missing_static}"
        f"  unparseable_names={n_unparseable_name}",
        flush=True,
    )
    if missing_static_apks:
        print(f"  APKs without static JSON ({len(missing_static_apks)}): {sorted(missing_static_apks)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
