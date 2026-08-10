#!/usr/bin/env python3
"""Mechanical re-sum of the batch-A descriptive scores from the judge's consolidated
claims CSV (juiz_claims_resolvidos_batchA.csv).

Rules (fase0/pre_registro.md section 6 + fase0/desvios.md D-piloto-4):
- Weights: linguagem_formal 20, captura_eventos 20, bindings_clausulas 15,
  predicados_composicao 15, toolchain_android 15, diagnostico 10, reprodutibilidade 5.
- Denominator per dimension = claims RESOLVED by the judge (PASS+FAIL);
  INCONCLUSIVE stays outside the denominator and forbids calling a score complete.
- Per-spec scores use only that spec's claims; SET claims (id contains "-SET-")
  are scored in a separate set score, never mixed into per-spec denominators.
- A batch aggregate over the 5 specs' claims (SET excluded) is reported for context.
- Dimension of each claim = the `dimensao` column assigned by the agent at creation
  (D-piloto-4 item 1: the judge does not re-assign).
- Labels: descriptive score != probability of correction != verdict; never rounded
  to 100; never opens a gate.

Usage: python3 juiz_rescore_batchA.py [csv_path]
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

WEIGHTS = {
    "linguagem_formal": 20,
    "captura_eventos": 20,
    "bindings_clausulas": 15,
    "predicados_composicao": 15,
    "toolchain_android": 15,
    "diagnostico": 10,
    "reprodutibilidade": 5,
}

SPECS = ("DHG", "HMC", "PBE", "IVP", "SKS")

csv_path = Path(sys.argv[1] if len(sys.argv) > 1
                else Path(__file__).parent / "juiz_claims_resolvidos_batchA.csv")

def unit_of(claim_id):
    if "-SET-" in claim_id:
        return "SET"
    for s in SPECS:
        if f"-{s}-" in claim_id:
            return s
    sys.exit(f"cannot map claim to a unit: {claim_id}")

# unit -> dim -> {PASS, FAIL, INCONCLUSIVE}
counts = defaultdict(lambda: defaultdict(lambda: {"PASS": 0, "FAIL": 0, "INCONCLUSIVE": 0}))
inconclusive_ids = []
n_claims = 0

with open(csv_path, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        n_claims += 1
        dim = row["dimensao"].strip()
        res = row["resolucao_juiz"].strip()
        if dim not in WEIGHTS:
            sys.exit(f"unknown dimension {dim!r} in {row['id']}")
        if res not in ("PASS", "FAIL", "INCONCLUSIVE"):
            sys.exit(f"unknown resolution {res!r} in {row['id']}")
        counts[unit_of(row["id"])][dim][res] += 1
        if res == "INCONCLUSIVE":
            inconclusive_ids.append(row["id"])

def table(unit_counts, label):
    print(f"\n== {label} ==")
    print(f"{'dimension':<24}{'weight':>7}{'resolv':>7}{'PASS':>6}{'FAIL':>6}{'INC':>5}{'subscore':>10}")
    raw, attainable = 0.0, 0
    tp = tf = ti = tr = 0
    for dim, w in WEIGHTS.items():
        c = unit_counts.get(dim, {"PASS": 0, "FAIL": 0, "INCONCLUSIVE": 0})
        resolved = c["PASS"] + c["FAIL"]
        if resolved == 0 and c["INCONCLUSIVE"] == 0:
            print(f"{dim:<24}{w:>7}{'-':>7}{'-':>6}{'-':>6}{'-':>5}{'(no claims)':>12}")
            continue
        sub = w * c["PASS"] / resolved if resolved else 0.0
        if resolved:
            raw += sub
            attainable += w
        tp += c["PASS"]; tf += c["FAIL"]; ti += c["INCONCLUSIVE"]; tr += resolved
        print(f"{dim:<24}{w:>7}{resolved:>7}{c['PASS']:>6}{c['FAIL']:>6}{c['INCONCLUSIVE']:>5}{sub:>10.2f}")
    norm = 100.0 * raw / attainable if attainable else 0.0
    print(f"{'TOTAL':<24}{attainable:>7}{tr:>7}{tp:>6}{tf:>6}{ti:>5}{raw:>10.2f}")
    print(f"  PRIMARY (pre-registered presentation): raw weighted sum {raw:.2f}; "
          + ("all 7 dimensions carry claims"
             if attainable == 100 else
             f"dimensions with no claims leave {100 - attainable} weight points unattainable this round"))
    if attainable != 100:
        # REF-B-02: normalization over attainable weight is an UNREGISTERED convention;
        # printed only as a derived reading, pending the PROPOSED deviation D-batchA-1.
        print(f"  derived reading (unregistered, see REF-B-02/D-batchA-1 PROPOSED): "
              f"{raw:.2f}/{attainable} = {norm:.2f}%")
    if ti:
        print(f"  score INCOMPLETE: {ti} INCONCLUSIVE outside the denominator")
    return raw, attainable, norm

# per-spec
for s in SPECS:
    table(counts[s], f"spec {s} (per-spec score, SET claims excluded)")

# SET score
table(counts["SET"], "SET claims (separate set score, D-piloto-4 item 2)")

# batch aggregate over the 5 specs' claims
agg = defaultdict(lambda: {"PASS": 0, "FAIL": 0, "INCONCLUSIVE": 0})
for s in SPECS:
    for dim, c in counts[s].items():
        for k in c:
            agg[dim][k] += c[k]
table(agg, "BATCH-A AGGREGATE over the 5 specs' claims (context only; SET excluded)")

print(f"\nclaims total: {n_claims}")
print(f"INCONCLUSIVE outside all denominators ({len(inconclusive_ids)}): "
      + ", ".join(inconclusive_ids))
print("\nLabels (mandatory): descriptive score != probability of correction != verdict;"
      "\nnever rounded to 100; a score never opens a gate; scores with INCONCLUSIVE"
      "\nclaims outside the denominator are INCOMPLETE.")
