#!/usr/bin/env python3
"""Mechanical re-sum for batch C (reads juiz_claims_resolvidos_batchC.csv).

D-piloto-4: per-spec scores over that spec's resolved claims only; SET scored
separately; dimension as filed by the creating agent (judge never re-assigns).
D-batchA-1: the RAW WEIGHTED SUM is the score of record; unattainable weight
stated; attainable-% only as a labeled derived reading.
D-batchB-1: per-phenomenon table generated from fenomeno_id_final only;
build assert guarantees no FAIL row lacks a phenomenon.
Denominator per dimension = PASS+FAIL resolved; INCONCLUSIVE outside (and the
unit's score is INCOMPLETE). Score != probability != verdict; never rounded to
100; no score opens a gate.
"""
import csv, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
W = {"linguagem_formal": 20, "captura_eventos": 20, "bindings_clausulas": 15,
     "predicados_composicao": 15, "toolchain_android": 15, "diagnostico": 10,
     "reprodutibilidade": 5}

rows = list(csv.DictReader(open(os.path.join(HERE, "juiz_claims_resolvidos_batchC.csv"),
                                newline="", encoding="utf-8")))
assert len(rows) == 134

def unit(cid):
    part = cid.split("-")[1]
    return "SET" if part == "SET" else part

units = defaultdict(lambda: defaultdict(lambda: {"P": 0, "F": 0, "I": 0}))
for r in rows:
    u, d, res = unit(r["id"]), r["dimensao"], r["resolucao_juiz"]
    assert d in W, (r["id"], d)
    units[u][d]["P" if res == "PASS" else "F" if res == "FAIL" else "I"] += 1

def score(u):
    tot, det, inc, missing = 0.0, [], 0, 0
    for d, w in W.items():
        c = units[u].get(d)
        if not c or (c["P"] + c["F"]) == 0:
            i = c["I"] if c else 0
            inc += i
            missing += w
            det.append(f"{d.split('_')[0][:4]} --/{w}" + (f" +{i}INC" if i else ""))
            continue
        den = c["P"] + c["F"]
        s = w * c["P"] / den
        tot += s
        inc += c["I"]
        det.append(f"{d.split('_')[0][:4]} {s:.2f} ({c['P']}/{den}" + (f" +{c['I']}INC" if c["I"] else "") + ")")
    return tot, det, inc, missing

print("== Per-unit raw weighted sums (of record, D-batchA-1) ==")
order = ["KGN", "KMF", "TMF", "SSL", "KST", "SET"]
for u in order:
    tot, det, inc, missing = score(u)
    status = "INCOMPLETE" if inc else "COMPLETE"
    line = f"{u}: RAW {tot:.2f}  [{'; '.join(det)}]  {status}"
    if inc:
        line += f" ({inc} INCONCLUSIVE outside denominator)"
    if missing:
        line += f"  unattainable weight {missing}"
        line += f"  derived reading (labeled, NOT the record): {tot:.2f}/{100-missing} = {100*tot/(100-missing):.2f}%"
    print(line)

# batch aggregate (context only; spec claims, SET excluded)
agg = defaultdict(lambda: {"P": 0, "F": 0, "I": 0})
for r in rows:
    if unit(r["id"]) == "SET":
        continue
    res = r["resolucao_juiz"]
    agg[r["dimensao"]]["P" if res == "PASS" else "F" if res == "FAIL" else "I"] += 1
tot, det, inc = 0.0, [], 0
for d, w in W.items():
    c = agg[d]
    den = c["P"] + c["F"]
    inc += c["I"]
    s = w * c["P"] / den if den else 0.0
    tot += s
    det.append(f"{d.split('_')[0][:4]} {s:.2f} ({c['P']}/{den}" + (f" +{c['I']}INC" if c["I"] else "") + ")")
n_spec = sum(1 for r in rows if unit(r["id"]) != "SET")
print(f"\n== Batch-C aggregate (context only; {n_spec} spec claims, SET excluded) ==")
print(f"AGG: RAW {tot:.2f}  [{'; '.join(det)}]  " + ("INCOMPLETE" if inc else "COMPLETE") + f" ({inc} INC)")

# resolution totals
n = defaultdict(int)
for r in rows:
    n[r["resolucao_juiz"]] += 1
print(f"\nResolutions: {n['PASS']} PASS / {n['FAIL']} FAIL / {n['INCONCLUSIVE']} INCONCLUSIVE (134 total)")

# per-phenomenon (fenomeno_id_final, FAIL rows only — D-batchB-1)
fen = defaultdict(lambda: {"claims": [], "crit": 0})
for r in rows:
    if r["resolucao_juiz"] != "FAIL":
        continue
    fid = r["fenomeno_id_final"]
    assert fid, r["id"]
    fen[fid]["claims"].append(r["id"])
    if r["severidade_final"].startswith("crit"):
        fen[fid]["crit"] += 1
print(f"\n== Per-phenomenon FAIL counts (fenomeno_id_final; {len(fen)} phenomena) ==")
for fid in sorted(fen, key=lambda k: (-len(fen[k]["claims"]), k)):
    d = fen[fid]
    print(f"{fid}: {len(d['claims'])} FAIL ({d['crit']} critical) <- {', '.join(sorted(d['claims']))}")

n_crit = sum(1 for r in rows if r["resolucao_juiz"] == "FAIL" and r["severidade_final"].startswith("crit"))
n_crit_fen = sum(1 for f in fen.values() if f["crit"])
print(f"\ncritical FAIL claims: {n_crit}; phenomena with >=1 critical FAIL: {n_crit_fen}")
