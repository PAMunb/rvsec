#!/usr/bin/env python3
"""JUDGE batch B — mechanical re-sum of the descriptive scores.

Reads batchB/juiz_claims_resolvidos_batchB.csv and computes, under the
pre-registered weights (fase0/pre_registro.md par.6) and the D-piloto-4 /
D-batchA-1 rules (fase0/desvios.md):
  - per-spec scores over that spec's resolved claims only (INCONCLUSIVE out);
  - a separate SET score (claims whose id contains -SET-);
  - the batch aggregate (context only, SET excluded);
  - per-dimension detail and unattainable weight (D-batchA-1: the raw weighted
    sum is the score of record; attainable-% printed only as a labeled derived
    reading);
  - per-phenomenon resolution counts. rev. 2 (REF-C-02): the counts read the
    judge column `fenomeno_id_final` (agent fenomeno_id where filed, judge
    backfill for the 7 FAIL rows the agents left blank), so the block now
    carries the full phenomenon assignment machine-readably; it falls back to
    the agent column for any row without the judge column.

The published tables in juiz_sintese_batchB.md par.4/par.8 must match this output.
"""
import csv, os
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "juiz_claims_resolvidos_batchB.csv")

WEIGHTS = {
    "linguagem_formal": 20.0, "captura_eventos": 20.0, "bindings_clausulas": 15.0,
    "predicados_composicao": 15.0, "toolchain_android": 15.0, "diagnostico": 10.0,
    "reprodutibilidade": 5.0,
}
SPECS = {"CIS": "CipherInputStreamSpec", "COS": "CipherOutputStreamSpec",
         "KPR": "KeyPairSpec", "SKY": "SecretKeySpec(SecretKey)", "PBK": "PBEKeySpecSpec"}

rows = list(csv.DictReader(open(CSV, newline="", encoding="utf-8")))
assert len(rows) == 133, len(rows)

def unit_of(cid):
    part = cid.split("-")[1]
    return "SET" if part == "SET" else part

def score(unit_rows, label):
    by_dim = defaultdict(lambda: {"PASS": 0, "FAIL": 0, "INC": 0})
    for r in unit_rows:
        d = r["dimensao"].strip()
        assert d in WEIGHTS, (r["id"], d)
        res = r["resolucao_juiz"]
        by_dim[d]["PASS" if res == "PASS" else "FAIL" if res == "FAIL" else "INC"] += 1
    raw, attainable, cells = 0.0, 0.0, []
    n_inc = sum(v["INC"] for v in by_dim.values())
    for dim, w in WEIGHTS.items():
        c = by_dim.get(dim)
        if not c or (c["PASS"] + c["FAIL"]) == 0:
            extra = f" (+{c['INC']} INC)" if c and c["INC"] else ""
            cells.append(f"{dim.split('_')[0][:4]} —{extra}")
            continue
        s = w * c["PASS"] / (c["PASS"] + c["FAIL"])
        raw += s; attainable += w
        inc = f" +{c['INC']}INC" if c["INC"] else ""
        cells.append(f"{dim.split('_')[0][:4]} {s:.2f} ({c['PASS']}/{c['PASS']+c['FAIL']}{inc})")
    unattain = 100.0 - attainable
    complete = "COMPLETE" if n_inc == 0 else f"INCOMPLETE ({n_inc} INCONCLUSIVE outside denominator)"
    print(f"{label}: raw = {raw:.2f} / 100 pre-registered weight"
          + (f"; unattainable weight = {unattain:.0f}" if unattain else "")
          + (f"; derived reading (labeled, not the record): {raw:.2f}/{attainable:.0f} = {100*raw/attainable:.2f}%" if unattain else "")
          + f"; {complete}")
    print("   " + " | ".join(cells))
    return raw

print("== Per-spec scores (that spec's resolved claims only; D-piloto-4) ==")
for ab, name in SPECS.items():
    score([r for r in rows if unit_of(r["id"]) == ab], f"{ab} {name}")

print("\n== SET score (separate; D-piloto-4 item 2) ==")
set_rows = [r for r in rows if unit_of(r["id"]) == "SET"]
score(set_rows, "SET")

print("\n== Batch-B aggregate (context only; spec claims, SET excluded) ==")
spec_rows = [r for r in rows if unit_of(r["id"]) != "SET"]
score(spec_rows, "AGGREGATE")

print("\n== Resolution totals ==")
c = Counter(r["resolucao_juiz"] for r in rows)
crit = [r["id"] for r in rows if r["resolucao_juiz"] == "FAIL" and r["severidade_final"] == "critica"]
print(f"133 claims = {c['PASS']} PASS + {c['FAIL']} FAIL + {c['INCONCLUSIVE']} INCONCLUSIVE; "
      f"critical FAILs: {len(crit)}")

print("\n== Per-phenomenon counts (D-piloto-4 item 3; unified FEN groups) ==")
FEN_UNIFY = {
    "FEN-CIS-MONITOR-GLOBAL": "FEN-STREAMS-MONITOR-GLOBAL",
    "FEN-COS-MONITOR-GLOBAL": "FEN-STREAMS-MONITOR-GLOBAL",
    "FEN-STREAMS-monitor-global": "FEN-STREAMS-MONITOR-GLOBAL",
    "FEN-COS-flush-alfabeto": "FEN-COS-FLUSH", "FEN-COS-FLUSH-ALFABETO": "FEN-COS-FLUSH",
    "FEN-KPR-co-obrigatorio": "FEN-KPR-CO-OPCIONAL",
    "FEN-KPR-c1-sem-binding": "FEN-KPR-C1-SLICE-VAZIO",
    "FEN-KPR-C1-FATIA-VAZIA": "FEN-KPR-C1-SLICE-VAZIO",
    "FEN-KPR-var-sombreada": "FEN-KPR-MATCH-NULL",
    "FEN-SKY-condicao-extra": "FEN-SKY-GATE-SUPRESSAO",
    "FEN-SKY-ENSURES-CONDICIONADO": "FEN-SKY-GATE-SUPRESSAO",
    "FEN-SKY-VIOLACAO-SILENCIOSA": "FEN-SKY-SEM-CANAL",
    "FEN-SET-escritas-sem-estado": "FEN-SKY-SEM-CANAL",
    "FEN-SKY-zero-captura": "FEN-SKY-ZERO-CAPTURA",
    "FEN-PBK-password-extra": "FEN-PBK-SENHA-EXTRA",
    "FEN-PBK-PASSWORD-RANDOMIZED": "FEN-PBK-SENHA-EXTRA",
    "FEN-PBK-CP-FAIL-ESPURIO": "FEN-PBK-RESIDUO",
    "FEN-SET-firstcall-disjunct": "FEN-SET-FIRSTCALL-DISJUNCT",
    "FEN-SET-mensagem-fator10": "FEN-PBE-MSG-1000", "FEN-PBE-MSG": "FEN-PBE-MSG-1000",
    "FEN-SET-UNKNOWN-EXPECTING": "FEN-SET-FAIL-UNKNOWN",
    "FEN-SET-DEDUPE-EXPECTING": "FEN-SET-DEDUPE", "FEN-SET-dedupe-resumo": "FEN-SET-DEDUPE",
    "FEN-PBK-ERR-DEDUPE-COLAPSO": "FEN-SET-DEDUPE",
    "FEN-CIS-CTOR-1ARG": "FEN-CIS-CTOR1-OMITIDA",
    "FEN-CIS-CONSTRAINT-OMITIDA": "FEN-CIS-LENOFF",
    "FEN-PBK-FORBIDDEN-UNKNOWN": "FEN-PBK-FORBIDDEN-MAP",
    "FEN-SET-tipo-estatico": "FEN-SET-TIPO-ESTATICO",
    "FEN-SET-failopen": "FEN-SET-FAILOPEN",
    "FEN-SET-GERADOR-SILENCIO": "FEN-SET-GERADOR-SILENCIO",
    "FEN-SET-MONITOR-GLOBAL-SEM-PARAMETRO": "FEN-STREAMS-MONITOR-GLOBAL",
}
def fen_of(r):
    f = (r.get("fenomeno_id_final") or r.get("fenomeno_id") or "").strip()
    return FEN_UNIFY.get(f, f)

fen = defaultdict(Counter)
for r in rows:
    f = fen_of(r)
    if not f:
        continue
    fen[f][r["resolucao_juiz"]] += 1
unlinked_fail = [r["id"] for r in rows if r["resolucao_juiz"] == "FAIL" and not fen_of(r)]
print(f"  (FAIL rows without phenomenon linkage: {len(unlinked_fail)}"
      + (f" — {unlinked_fail})" if unlinked_fail else ")"))
for f in sorted(fen, key=lambda x: (-sum(fen[x].values()), x)):
    cc = fen[f]
    sev = {r["severidade_final"] for r in rows if fen_of(r) == f and r["resolucao_juiz"] == "FAIL"}
    print(f"  {f}: {sum(cc.values())} claims ({dict(cc)})" + (f" max-sev={'critica' if 'critica' in sev else 'major' if 'major' in sev else 'minor'}" if sev else ""))
n_crit_fen = sum(1 for f in fen
                 if any(r["severidade_final"] == "critica" for r in rows
                        if fen_of(r) == f and r["resolucao_juiz"] == "FAIL"))
n_crit_claims = sum(1 for r in rows if r["resolucao_juiz"] == "FAIL" and r["severidade_final"] == "critica")
print(f"  => critical FAIL claims: {n_crit_claims}; phenomena with >=1 critical FAIL: {n_crit_fen}")
