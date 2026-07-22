"""
Concatenate per-VM regenerated CSVs into the final consolidated CSVs (level 3
of the 3-level pipeline; see docs/20260514_regenerar_planilhas.md §4).

Reads:  RESULTADOS/m<i>/{summary,coverage,errors}_regen.csv  (one per VM)
Writes: RESULTADOS/{summary,coverage,errors}_regen.csv

Header-aware append (same logic as concat_vm.py). Does NOT touch the original
*_all.csv files; the final promotion is a separate step gated by verify.py.

Usage:
    uv run python scripts/regenerate_results/concat_all.py \\
        --vms m1 m2 m3 m4 \\
        --results-root /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/RESULTADOS
"""

import argparse
import os
import sys
from typing import List

CSV_NAMES = ["summary_regen.csv", "coverage_regen.csv", "errors_regen.csv"]


def concat_files(inputs: List[str], output: str) -> int:
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
                    else:
                        fout.write(line)
                        rows += 1
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vms", nargs="+", default=["m1", "m2", "m3", "m4"], help="VM directory names.")
    ap.add_argument(
        "--results-root",
        default="/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/RESULTADOS",
        help="Root that contains the per-VM directories and receives the consolidated CSVs.",
    )
    args = ap.parse_args()

    for csv_name in CSV_NAMES:
        inputs: List[str] = []
        for vm in args.vms:
            candidate = os.path.join(args.results_root, vm, csv_name)
            if os.path.isfile(candidate) and os.path.getsize(candidate) > 0:
                inputs.append(candidate)
            else:
                print(f"WARNING: missing or empty: {candidate}", file=sys.stderr)
        output = os.path.join(args.results_root, csv_name)
        if not inputs:
            print(f"ERROR: nothing to concat for {csv_name}", file=sys.stderr)
            continue
        n = concat_files(inputs, output)
        print(f"[ALL] {csv_name}: {n} rows from {len(inputs)} VMs -> {output}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
