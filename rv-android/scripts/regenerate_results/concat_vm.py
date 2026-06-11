"""
Concatenate per-container regenerated CSVs into per-VM CSVs (level 2 of the
3-level pipeline; see docs/20260514_regenerar_planilhas.md §4).

For each VM dir (RESULTADOS/m<i>/), reads
    results/exp_<j>/exp_<j>/{summary,coverage,errors}_regen.csv  (4 containers)
and writes
    m<i>/{summary,coverage,errors}_regen.csv

Header-aware append: the header from the first non-empty container CSV is kept;
headers of the others are skipped. If a container is missing its CSVs, it is
reported on stderr and skipped (the per-VM file is still produced from whatever
is available).

Usage:
    uv run python scripts/regenerate_results/concat_vm.py m1 m2 m3 m4 \\
        --results-root /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/RESULTADOS
"""

import argparse
import os
import sys
from typing import List

CSV_NAMES = ["summary_regen.csv", "coverage_regen.csv", "errors_regen.csv"]


def find_container_csvs(vm_dir: str, csv_name: str) -> List[str]:
    """Return sorted list of container-level CSV paths for one CSV kind."""
    results_dir = os.path.join(vm_dir, "results")
    if not os.path.isdir(results_dir):
        return []
    out = []
    for entry in sorted(os.listdir(results_dir)):
        outer = os.path.join(results_dir, entry)
        if not os.path.isdir(outer):
            continue
        # rv-android container layout duplicates the dir name: results/exp_00/exp_00/
        inner = os.path.join(outer, entry)
        candidate = os.path.join(inner, csv_name)
        if os.path.isfile(candidate):
            out.append(candidate)
    return out


def concat_files(inputs: List[str], output: str) -> int:
    """Append `inputs` into `output`, keeping only the first header. Returns row count (excluding header)."""
    rows = 0
    header_written = False
    with open(output, "w", encoding="utf-8") as fout:
        for src in inputs:
            with open(src, "r", encoding="utf-8") as fin:
                first = True
                for line in fin:
                    if first:
                        first = False
                        if not header_written:
                            fout.write(line)
                            header_written = True
                        # else: skip header
                    else:
                        fout.write(line)
                        rows += 1
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("vms", nargs="+", help="VM directory names (e.g. m1 m2 m3 m4).")
    ap.add_argument(
        "--results-root",
        default="/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/RESULTADOS",
        help="Root that contains the per-VM directories.",
    )
    args = ap.parse_args()

    rc = 0
    for vm in args.vms:
        vm_dir = os.path.join(args.results_root, vm)
        if not os.path.isdir(vm_dir):
            print(f"ERROR: vm dir does not exist: {vm_dir}", file=sys.stderr)
            rc = 2
            continue
        for csv_name in CSV_NAMES:
            inputs = find_container_csvs(vm_dir, csv_name)
            output = os.path.join(vm_dir, csv_name)
            if not inputs:
                print(f"WARNING: no {csv_name} found under {vm_dir}/results/*/", file=sys.stderr)
                # Still write an empty file with no header — caller decides what to do.
                open(output, "w", encoding="utf-8").close()
                continue
            n = concat_files(inputs, output)
            print(f"[{vm}] {csv_name}: {n} rows from {len(inputs)} containers -> {output}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
