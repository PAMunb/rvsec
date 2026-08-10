#!/usr/bin/env python3
"""Re-sum of the pilot's descriptive score from the judge's rev. 2 claims CSV.

Weights and denominator: fase0/pre_registro.md section 6 (published before scoring).
Denominator per dimension = claims resolved by the judge (PASS+FAIL); INCONCLUSIVE
stays outside the denominator and forbids calling the score complete. No averaging
across agents.

Usage: python3 juiz_rescore.py [csv_path]   (default: juiz_claims_resolvidos.csv)
"""

import csv
import sys
from pathlib import Path

WEIGHTS = {
    "linguagem": 20,
    "captura": 20,
    "bindings": 15,
    "predicados": 15,
    "toolchain": 15,
    "diagnostico": 10,
    "reprodutibilidade": 5,
}

csv_path = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "juiz_claims_resolvidos.csv")

counts = {d: {"PASS": 0, "FAIL": 0, "INCONCLUSIVE": 0} for d in WEIGHTS}
inconclusive_ids = []
set_wide = []

with open(csv_path, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        dim = row["dimensao_score"].strip()
        res = row["resolucao"].strip()
        if dim not in counts:
            sys.exit(f"unknown dimension: {dim!r} in {row['claim_id']}")
        if res not in ("PASS", "FAIL", "INCONCLUSIVE"):
            sys.exit(f"unknown resolution: {res!r} in {row['claim_id']}")
        counts[dim][res] += 1
        if res == "INCONCLUSIVE":
            inconclusive_ids.append(row["claim_id"])
        if "-SET-" in row["claim_id"]:
            set_wide.append((row["claim_id"], res))

total = 0.0
rows = []
for dim, w in WEIGHTS.items():
    c = counts[dim]
    resolved = c["PASS"] + c["FAIL"]
    sub = w * c["PASS"] / resolved if resolved else 0.0
    total += sub
    rows.append((dim, w, resolved, c["PASS"], c["FAIL"], c["INCONCLUSIVE"], sub))

print(f"CSV: {csv_path.name}  claims: {sum(sum(c.values()) for c in counts.values())}")
print(f"{'dimension':<18}{'weight':>7}{'resolv':>7}{'PASS':>6}{'FAIL':>6}{'INC':>5}{'subscore':>10}")
for dim, w, resolved, p, fl, inc, sub in rows:
    print(f"{dim:<18}{w:>7}{resolved:>7}{p:>6}{fl:>6}{inc:>5}{sub:>10.2f}")
n_resolved = sum(r[2] for r in rows)
n_pass = sum(r[3] for r in rows)
n_fail = sum(r[4] for r in rows)
n_inc = sum(r[5] for r in rows)
print(f"{'TOTAL':<18}{100:>7}{n_resolved:>7}{n_pass:>6}{n_fail:>6}{n_inc:>5}{total:>10.2f}")
print(f"\nINCONCLUSIVE outside the denominator ({n_inc}): {', '.join(inconclusive_ids)}")

# REF-06 sensitivity: *-SET-* claims are set-wide, not about the 2 pilot specs.
sw_resolved = [c for c in set_wide if c[1] != "INCONCLUSIVE"]
print(f"\nSet-wide claims in the denominator (REF-06): {len(sw_resolved)} of {len(set_wide)} "
      f"({', '.join(i for i, _ in set_wide)})")
counts2 = {d: dict(c) for d, c in counts.items()}
with open(csv_path, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if "-SET-" in row["claim_id"]:
            counts2[row["dimensao_score"].strip()][row["resolucao"].strip()] -= 1
total2 = 0.0
for dim, w in WEIGHTS.items():
    c = counts2[dim]
    resolved = c["PASS"] + c["FAIL"]
    total2 += w * c["PASS"] / resolved if resolved else 0.0
print(f"Total without the set-wide claims: {total2:.2f} (delta {total2 - total:+.2f})")
