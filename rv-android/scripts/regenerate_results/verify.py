"""
Rigorously verify the regenerated CSVs against the raw .logcat files.

Checks performed (see docs/20260514_regenerar_planilhas.md §8):
  C1 errors strict 1:1: for each (apk,rep,timeout,tool), count of "RVSEC:"
     lines in the .logcat must equal the count of rows in errors_regen.csv.
  C2 coverage upper bound: rows in coverage_regen.csv for the tuple must be
     <= count of "RVSEC-COV:" lines in the .logcat (deduplicated).
  C3 summary <-> coverage coherence: cov_act, cov_method, cov_rv_method on the
     summary row must equal the last chronological row of coverage_regen.csv
     (within +-0.01) for the same tuple.
  C4 sanity: number of summary rows == number of .logcat files discovered.
  C5 errors parity vs original errors_all.csv (optional, --compare-errors):
     row count delta and per-tuple delta.

Outputs:
  verification_report.md  (next to the consolidated CSVs)
  exit code 0 if all checks pass, 1 otherwise.

Usage:
    # Verify one container (smoke):
    uv run python scripts/regenerate_results/verify.py --container \\
        /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/RESULTADOS/m1/results/exp_00/exp_00

    # Verify the full consolidated output:
    uv run python scripts/regenerate_results/verify.py --full \\
        --results-root /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/RESULTADOS
"""

import argparse
import csv
import os
import re
import sys
from collections import defaultdict
from multiprocessing import Pool
from typing import Dict, List, Optional, Tuple

LOGCAT_NAME_RE = re.compile(r"^(?P<apk>.+\.apk)__(?P<rep>\d+)__(?P<timeout>\d+)__(?P<tool>.+)\.logcat$")

# Tag patterns emitted by RVSEC instrumentation. The logcat parser keys off the
# tag column (col 6 of "threadtime" format), but our verifier only needs counts,
# so a substring scan is enough and is ~10x faster than re-parsing the whole file.
RE_RVSEC_ERR = re.compile(r"\bRVSEC\s*:")
RE_RVSEC_COV = re.compile(r"\bRVSEC-COV\s*:")

Tuple4 = Tuple[str, str, str, str]  # (apk, rep, timeout, tool) as strings to ease CSV joining


def parse_logcat_name(filename: str) -> Optional[Tuple4]:
    m = LOGCAT_NAME_RE.match(filename)
    if not m:
        return None
    return m["apk"], m["rep"], m["timeout"], m["tool"]


def count_logcat_tags(path: str) -> Tuple[int, int]:
    """Return (rvsec_err_count, rvsec_cov_count) for one logcat file."""
    err = cov = 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if RE_RVSEC_ERR.search(line):
                err += 1
            elif RE_RVSEC_COV.search(line):
                cov += 1
    return err, cov


def discover_logcats(root: str) -> List[str]:
    out = []
    for r, _, files in os.walk(root):
        for f in files:
            if f.endswith(".logcat"):
                out.append(os.path.join(r, f))
    return sorted(out)


def _count_worker(path: str) -> Tuple[Optional[Tuple4], int, int]:
    key = parse_logcat_name(os.path.basename(path))
    err, cov = count_logcat_tags(path)
    return key, err, cov


def collect_logcat_counts(root: str, workers: int) -> Dict[Tuple4, Tuple[int, int]]:
    """Walk root, count tags per logcat. Returns {(apk,rep,timeout,tool): (err,cov)}."""
    logcats = discover_logcats(root)
    counts: Dict[Tuple4, Tuple[int, int]] = {}
    with Pool(processes=workers) as pool:
        for key, err, cov in pool.imap_unordered(_count_worker, logcats, chunksize=8):
            if key is None:
                continue
            # Same tuple could appear in multiple containers only if a logcat
            # was duplicated — not expected, but we sum defensively.
            prev_err, prev_cov = counts.get(key, (0, 0))
            counts[key] = (prev_err + err, prev_cov + cov)
    return counts


def load_csv_rows(path: str) -> List[Dict[str, str]]:
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def group_by_tuple(rows: List[Dict[str, str]]) -> Dict[Tuple4, List[Dict[str, str]]]:
    out: Dict[Tuple4, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = (row["apk"], row["rep"], row["timeout"], row["tool"])
        out[key].append(row)
    return out


def verify(
    logcat_root: str,
    summary_csv: str,
    coverage_csv: str,
    errors_csv: str,
    report_path: str,
    original_errors_csv: Optional[str] = None,
    workers: int = 8,
) -> int:
    print(f"Walking logcats under {logcat_root} ...", flush=True)
    logcat_counts = collect_logcat_counts(logcat_root, workers)
    print(f"  {len(logcat_counts)} unique tuples from logcats", flush=True)

    print(f"Loading {summary_csv} ...", flush=True)
    summary_rows = load_csv_rows(summary_csv)
    summary_by = group_by_tuple(summary_rows)
    print(f"  {len(summary_rows)} summary rows  ({len(summary_by)} unique tuples)")

    print(f"Loading {coverage_csv} ...", flush=True)
    coverage_rows = load_csv_rows(coverage_csv)
    coverage_by = group_by_tuple(coverage_rows)
    print(f"  {len(coverage_rows)} coverage rows  ({len(coverage_by)} unique tuples)")

    print(f"Loading {errors_csv} ...", flush=True)
    errors_rows = load_csv_rows(errors_csv)
    errors_by = group_by_tuple(errors_rows)
    print(f"  {len(errors_rows)} error rows  ({len(errors_by)} unique tuples)")

    # ---- check C1: errors strict 1:1 ----
    c1_failures: List[str] = []
    for key, (raw_err, _raw_cov) in logcat_counts.items():
        regen_err = len(errors_by.get(key, []))
        if regen_err != raw_err:
            c1_failures.append(f"  {key}: logcat={raw_err} regen={regen_err} (delta={regen_err - raw_err})")

    # ---- check C2: coverage upper bound ----
    c2_failures: List[str] = []
    for key, (_raw_err, raw_cov) in logcat_counts.items():
        regen_cov = len(coverage_by.get(key, []))
        if regen_cov > raw_cov:
            c2_failures.append(f"  {key}: logcat_cov={raw_cov} regen_cov_rows={regen_cov}")

    # ---- check C3: summary <-> last coverage row coherence ----
    c3_failures: List[str] = []
    for key, rows in summary_by.items():
        if len(rows) != 1:
            c3_failures.append(f"  {key}: summary has {len(rows)} rows (expected 1)")
            continue
        s = rows[0]
        cov_rows = coverage_by.get(key, [])
        # Map summary column -> coverage_regen.csv column.
        # Note: coverage_regen.csv keeps the trimmed schema from result_processor.py
        # (cov_class duplicates cov_method, cov_rv_method is mop). The summary
        # uses the full old-experiment names; we cross-check the three that have
        # a direct counterpart in coverage_regen.csv.
        summary_to_coverage = [
            ("cov_act", "cov_act"),
            ("cov_method", "cov_method"),
            ("cov_reaches_target", "cov_rv_method"),
        ]
        if not cov_rows:
            # No coverage rows means either no RVSEC-COV in the logcat or the APK
            # had no static_data. summary cov_* must be 0 in that case.
            for s_col, _ in summary_to_coverage:
                if float(s.get(s_col, "0") or 0) != 0:
                    c3_failures.append(f"  {key}: {s_col}={s[s_col]} but coverage_rows=0")
            continue
        last = cov_rows[-1]  # CSV order preserved; chronological per regenerate_container.py
        for s_col, c_col in summary_to_coverage:
            sv = float(s.get(s_col, "0") or 0)
            cv = float(last.get(c_col, "0") or 0)
            if abs(sv - cv) > 0.01:
                c3_failures.append(f"  {key}: summary.{s_col}={sv} vs last_coverage.{c_col}={cv} (delta={sv - cv:.4f})")

    # ---- check C4: sanity (summary rows == discovered logcats) ----
    c4_ok = len(summary_rows) == len(logcat_counts)
    c4_msg = f"summary_rows={len(summary_rows)} logcat_files={len(logcat_counts)}"

    # ---- check C5: errors parity vs original (optional) ----
    c5_lines: List[str] = []
    if original_errors_csv and os.path.isfile(original_errors_csv):
        orig_rows = load_csv_rows(original_errors_csv)
        orig_by = group_by_tuple(orig_rows)
        delta = len(errors_rows) - len(orig_rows)
        c5_lines.append(f"original rows: {len(orig_rows)}  regen rows: {len(errors_rows)}  delta: {delta}")
        common = set(orig_by) & set(errors_by)
        differ = sum(1 for k in common if len(orig_by[k]) != len(errors_by[k]))
        only_orig = set(orig_by) - set(errors_by)
        only_regen = set(errors_by) - set(orig_by)
        c5_lines.append(f"tuples differing: {differ}  only_orig: {len(only_orig)}  only_regen: {len(only_regen)}")

    # ---- write report ----
    def status(ok: bool) -> str:
        return "PASS" if ok else "FAIL"

    c1_ok = not c1_failures
    c2_ok = not c2_failures
    c3_ok = not c3_failures

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Verification report\n\n")
        f.write(f"- logcat_root: `{logcat_root}`\n")
        f.write(f"- summary:  `{summary_csv}`  ({len(summary_rows)} rows)\n")
        f.write(f"- coverage: `{coverage_csv}` ({len(coverage_rows)} rows)\n")
        f.write(f"- errors:   `{errors_csv}`   ({len(errors_rows)} rows)\n\n")

        f.write(f"## C1 errors strict 1:1 vs `.logcat` -- {status(c1_ok)}\n")
        f.write(f"failures: {len(c1_failures)}\n")
        if c1_failures:
            f.write("```\n" + "\n".join(c1_failures[:50]) + ("\n... (truncated)" if len(c1_failures) > 50 else "") + "\n```\n")
        f.write("\n")

        f.write(f"## C2 coverage rows <= RVSEC-COV count -- {status(c2_ok)}\n")
        f.write(f"failures: {len(c2_failures)}\n")
        if c2_failures:
            f.write("```\n" + "\n".join(c2_failures[:50]) + ("\n... (truncated)" if len(c2_failures) > 50 else "") + "\n```\n")
        f.write("\n")

        f.write(f"## C3 summary <-> coverage last row coherence -- {status(c3_ok)}\n")
        f.write(f"failures: {len(c3_failures)}\n")
        if c3_failures:
            f.write("```\n" + "\n".join(c3_failures[:50]) + ("\n... (truncated)" if len(c3_failures) > 50 else "") + "\n```\n")
        f.write("\n")

        f.write(f"## C4 sanity (summary rows == logcat files) -- {status(c4_ok)}\n")
        f.write(f"{c4_msg}\n\n")

        if c5_lines:
            f.write("## C5 errors parity vs original\n")
            for line in c5_lines:
                f.write(f"- {line}\n")

    print(f"Report written: {report_path}", flush=True)
    all_ok = c1_ok and c2_ok and c3_ok and c4_ok
    print(f"Overall: {status(all_ok)}", flush=True)
    return 0 if all_ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--container", help="Verify a single container_dir against its container-level *_regen.csv.")
    g.add_argument("--full", action="store_true", help="Verify the consolidated CSVs against all .logcat files.")
    ap.add_argument(
        "--results-root",
        default="/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/RESULTADOS",
        help="Root used in --full mode.",
    )
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--compare-errors", action="store_true",
                    help="In --full mode, also run C5 against original errors_all.csv.")
    args = ap.parse_args()

    if args.container:
        d = os.path.abspath(args.container)
        return verify(
            logcat_root=d,
            summary_csv=os.path.join(d, "summary_regen.csv"),
            coverage_csv=os.path.join(d, "coverage_regen.csv"),
            errors_csv=os.path.join(d, "errors_regen.csv"),
            report_path=os.path.join(d, "verification_report.md"),
            workers=args.workers,
        )

    root = os.path.abspath(args.results_root)
    return verify(
        logcat_root=root,
        summary_csv=os.path.join(root, "summary_regen.csv"),
        coverage_csv=os.path.join(root, "coverage_regen.csv"),
        errors_csv=os.path.join(root, "errors_regen.csv"),
        report_path=os.path.join(root, "verification_report.md"),
        original_errors_csv=os.path.join(root, "errors_all.csv") if args.compare_errors else None,
        workers=args.workers,
    )


if __name__ == "__main__":
    sys.exit(main())
