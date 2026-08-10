#!/usr/bin/env python3
"""Mechanical re-sum for batch D (reads juiz_claims_resolvidos_batchD.csv).

D-piloto-4: per-spec scores over that spec's resolved claims only; SET scored
separately; dimension as filed by the creating agent — the judge never
re-assigns. Spelling NORMALIZATION only: the three agents filed the same seven
pre-registered dimensions under different spellings (accents, spaces, slashes);
each spelling maps 1:1 onto a pre-registered dimension. One recorded exception
(pendency, not re-assignment): Alfa filed 3 claims under the semantic-model
label "equivalência paramétrica/ciclo de vida", which is not a §6 score
dimension; their decisive evidence measures parameter-to-object binding, the §3
"Binding/cláusula" row, so they are scored under bindings_clausulas and the
assignment question is recorded as a D-piloto-4 pendency (synthesis §2.7).

D-batchA-1: the RAW WEIGHTED SUM is the score of record; unattainable weight
stated; attainable-% only as a labeled derived reading.
D-batchB-1: per-phenomenon table from fenomeno_id_final only; build assert
guarantees no FAIL row lacks one. Denominator per dimension = PASS+FAIL
resolved; INCONCLUSIVE outside (unit INCOMPLETE). Score != probability !=
verdict; never rounded to 100; no score opens a gate.
"""
import csv, os, unicodedata
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
W = {"linguagem_formal": 20, "captura_eventos": 20, "bindings_clausulas": 15,
     "predicados_composicao": 15, "toolchain_android": 15, "diagnostico": 10,
     "reprodutibilidade": 5}

def ascii_fold(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().strip().lower()

DIM_NORM = {
    "captura de eventos": "captura_eventos",
    "captura": "captura_eventos",
    "captura_eventos": "captura_eventos",
    "linguagem formal": "linguagem_formal",
    "linguagem_formal": "linguagem_formal",
    "predicados/composicao": "predicados_composicao",
    "predicados_composicao": "predicados_composicao",
    "bindings/clausulas": "bindings_clausulas",
    "bindings_clausulas": "bindings_clausulas",
    "diagnostico": "diagnostico",
    "toolchain_android": "toolchain_android",
    "reprodutibilidade": "reprodutibilidade",
    # recorded D-piloto-4 pendency (see docstring): 3 Alfa claims
    "equivalencia parametrica/ciclo de vida": "bindings_clausulas",
}

rows = list(csv.DictReader(open(os.path.join(HERE, "juiz_claims_resolvidos_batchD.csv"),
                                newline="", encoding="utf-8")))
assert len(rows) == 123

def unit(cid):
    part = cid.split("-")[1]
    return "SET" if part == "SET" else part

def dim(r):
    d = DIM_NORM[ascii_fold(r["dimensao"])]
    assert d in W
    return d

units = defaultdict(lambda: defaultdict(lambda: {"P": 0, "F": 0, "I": 0}))
for r in rows:
    u, d, res = unit(r["id"]), dim(r), r["resolucao_juiz"]
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
for u in ["MAC", "MDG", "KPG", "SRD", "SIG", "SET"]:
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
    agg[dim(r)]["P" if res == "PASS" else "F" if res == "FAIL" else "I"] += 1
# rev. 2 (REF-E-07): empty dimensions are excluded and their weight stated,
# matching the per-unit D-batchA-1 presentation.
tot, det, inc, agg_missing = 0.0, [], 0, 0
for d, w in W.items():
    c = agg[d]
    den = c["P"] + c["F"]
    inc += c["I"]
    if den == 0:
        agg_missing += w
        det.append(f"{d.split('_')[0][:4]} --/{w}" + (f" +{c['I']}INC" if c["I"] else ""))
        continue
    s = w * c["P"] / den
    tot += s
    det.append(f"{d.split('_')[0][:4]} {s:.2f} ({c['P']}/{den}" + (f" +{c['I']}INC" if c["I"] else "") + ")")
n_spec = sum(1 for r in rows if unit(r["id"]) != "SET")
print(f"\n== Batch-D aggregate (context only; {n_spec} spec claims, SET excluded) ==")
line = f"AGG: RAW {tot:.2f}  [{'; '.join(det)}]  " + ("INCOMPLETE" if inc else "COMPLETE") + f" ({inc} INC)"
if agg_missing:
    line += (f"  unattainable weight {agg_missing}"
             f"  derived reading (labeled, NOT the record): {tot:.2f}/{100-agg_missing} = {100*tot/(100-agg_missing):.2f}%")
print(line)

n = defaultdict(int)
for r in rows:
    n[r["resolucao_juiz"]] += 1
print(f"\nResolutions: {n['PASS']} PASS / {n['FAIL']} FAIL / {n['INCONCLUSIVE']} INCONCLUSIVE (123 total)")

def is_crit(sev):
    return ascii_fold(sev).startswith("crit")

fen = defaultdict(lambda: {"claims": [], "crit": 0})
for r in rows:
    if r["resolucao_juiz"] != "FAIL":
        continue
    fid = r["fenomeno_id_final"]
    assert fid, r["id"]
    fen[fid]["claims"].append(r["id"])
    if is_crit(r["severidade_final"]):
        fen[fid]["crit"] += 1
print(f"\n== Per-phenomenon FAIL counts (fenomeno_id_final; {len(fen)} phenomena) ==")
for fid in sorted(fen, key=lambda k: (-len(fen[k]["claims"]), k)):
    d = fen[fid]
    print(f"{fid}: {len(d['claims'])} FAIL ({d['crit']} critical) <- {', '.join(sorted(d['claims']))}")

n_crit = sum(1 for r in rows if r["resolucao_juiz"] == "FAIL" and is_crit(r["severidade_final"]))
n_crit_fen = sum(1 for f in fen.values() if f["crit"])
print(f"\ncritical FAIL claims: {n_crit}; phenomena with >=1 critical FAIL: {n_crit_fen}")
