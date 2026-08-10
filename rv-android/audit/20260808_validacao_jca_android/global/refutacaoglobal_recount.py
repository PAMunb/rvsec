#!/usr/bin/env python3
"""refutacaoglobal_recount.py — independent recount by the GLOBAL REFUTATION
reviewer (no reuse of juizglobal_build.py logic; own queries over the record).

Recounts, from the raw CSVs of record:
  R1. Ledger totals, per-round totals, criticals of-record/derived, critical
      FEN groups, D-batchC-1 reconciliation rows, diagnostico pool.
  R2. Criticals WITHOUT canonical FEN (the REF-G-02(a) figure).
  R3. FAIL ledger rows without fen_canonical, by round (D-batchB-1 scope check).
  R4. The 30 set-claim resolution and severity tallies from
      juizglobal_set_claims_resolvidos.csv (not from the builder's RES table).
  R5. The 15.45 set-phase score re-derived from the resolved CSV.
  R6. Gate per-spec tallies (G2..G9) re-derived from the five rounds' §8.1
      verdict tables, transcribed manually below from the synthesis files.
  R7. FEN registry row count.
Prints everything; asserts only where the record publishes an exact figure.
"""
import csv
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT = os.path.dirname(HERE)


def main():
    led = list(csv.DictReader(open(os.path.join(AUDIT, "set", "set_cons_ledger.csv"),
                                   encoding="utf-8")))
    print("R1. ledger rows:", len(led), Counter(r["resolution"] for r in led))
    assert len(led) == 558
    for rnd, exp in [("pilot", (72, 30, 34, 8)), ("batchA", (96, 46, 48, 2)),
                     ("batchB", (133, 40, 88, 5)), ("batchC", (134, 55, 71, 8)),
                     ("batchD", (123, 39, 81, 3))]:
        rows = [r for r in led if r["round"] == rnd]
        c = Counter(r["resolution"] for r in rows)
        got = (len(rows), c["PASS"], c["FAIL"], c["INCONCLUSIVE"])
        print("   ", rnd, got)
        assert got == exp, (rnd, got, exp)
    crit = [r for r in led if r["resolution"] == "FAIL"
            and r["severity_resolved"] == "critica"]
    rec = [r for r in crit if r["severity_kind"] == "of-record"]
    der = [r for r in crit if r["severity_kind"] == "derived-parsed"]
    fens = {r["fen_canonical"] for r in crit if r["fen_canonical"]}
    s4 = [r for r in led if r["severity_s4_letter"]
          and r["severity_s4_letter"] != r["severity_resolved"]]
    diag = Counter(r["resolution"] for r in led if r["dimension"] == "diagnostico")
    print("    criticals: of-record", len(rec), "derived", len(der),
          "| critical FEN groups", len(fens), "| s4-letter rows", len(s4),
          "| diagnostico", dict(diag))
    assert (len(rec), len(der), len(fens), len(s4)) == (164, 10, 50, 8)
    assert (diag["PASS"], diag["FAIL"], diag["INCONCLUSIVE"]) == (11, 73, 7)

    nofen_crit = [r for r in crit if not r["fen_canonical"]]
    print("R2. criticals WITHOUT canonical FEN:", len(nofen_crit),
          sorted(r["claim_id"] for r in nofen_crit))

    nofen_fail = Counter(r["round"] for r in led
                         if r["resolution"] == "FAIL" and not r["fen_canonical"])
    print("R3. FAIL rows without fen_canonical by round:", dict(nofen_fail),
          "(D-batchB-1 adopted from batch C onward; batch B retrofitted --",
          "pilot/batchA gaps are within the deviation's registered scope)")

    res = list(csv.DictReader(open(os.path.join(
        HERE, "juizglobal_set_claims_resolvidos.csv"), encoding="utf-8")))
    rc = Counter(r["resolucao_juiz"] for r in res)
    sc = Counter(r["severidade_final"] for r in res
                 if r["resolucao_juiz"] == "FAIL")
    fenc = Counter(r["fenomeno_id_final"] for r in res
                   if r["resolucao_juiz"] == "FAIL")
    print("R4. set claims:", dict(rc), "| severities:", dict(sc),
          "| phenomena over FAILs:", len(fenc), "/", sum(fenc.values()))
    assert (rc["FAIL"], rc["PASS"], rc.get("INCONCLUSIVE", 0)) == (22, 8, 0)
    assert (sc["critica"], sc["major"], sc["minor"]) == (15, 6, 1)
    assert (len(fenc), sum(fenc.values())) == (20, 22)

    W = {"linguagem_formal": 20, "captura_eventos": 20, "bindings_clausulas": 15,
         "predicados_composicao": 15, "toolchain_android": 15, "diagnostico": 10,
         "reprodutibilidade": 5}
    tot = 0.0
    for d, w in W.items():
        rows = [r for r in res if r["dimensao"] == d]
        p = sum(1 for r in rows if r["resolucao_juiz"] == "PASS")
        tot += w * p / len(rows) if rows else 0.0
    print(f"R5. set-phase raw weighted sum re-derived: {tot:.2f}")
    assert abs(tot - 15.45) < 0.01

    # R6: per-spec gate verdicts transcribed from the five §8.1 tables
    # (pilot/juiz_sintese.md §8.1; batchA/B/C/D juiz_sintese_batch*.md §8.1).
    T = {  # spec: (G2, G3, G4, G5, G7, G9)  P=PASS F=FAIL
        "CIP": "PFFPFF", "GCM": "PPFPFF",
        "DHG": "PPFPFF", "HMC": "PFFPFF", "PBE": "PPFPPF", "IVP": "PPPPPF",
        "SKS": "PPFPFF",
        "CIS": "PFFFFF", "COS": "PFFFFF", "KPR": "PFFPFF", "SKY": "PPFFFF",
        "PBK": "PFFPFF",
        "KGN": "FFFFFF", "KMF": "PFPFFF", "TMF": "PFPFFF", "SSL": "PFFFFF",
        "KST": "PFFFFF",
        "MAC": "PFFFFF", "MDG": "PFFFPF", "KPG": "PFFFFF", "SRD": "PFFFFF",
        "SIG": "PFPFFF",
    }
    assert len(T) == 22
    names = ["G2", "G3", "G4", "G5", "G7", "G9"]
    for i, g in enumerate(names):
        fails = sorted(s for s, v in T.items() if v[i] == "F")
        print(f"R6. {g}: {len(fails)}/22 FAIL -> {','.join(fails)}")
    assert sum(1 for v in T.values() if v[0] == "F") == 1     # G2: KGN only
    assert sum(1 for v in T.values() if v[1] == "F") == 16    # G3
    assert sum(1 for v in T.values() if v[2] == "F") == 18    # G4
    assert sum(1 for v in T.values() if v[3] == "F") == 13    # G5
    assert sum(1 for v in T.values() if v[4] == "F") == 19    # G7
    assert sum(1 for v in T.values() if v[5] == "F") == 22    # G9

    reg = list(csv.DictReader(open(os.path.join(
        AUDIT, "set", "set_cons_fen_registry.csv"), encoding="utf-8")))
    print("R7. FEN registry rows:", len(reg))
    assert len(reg) == 119

    print("\nALL REFUTATION RECOUNTS MATCH THE RECORD.")


if __name__ == "__main__":
    main()
