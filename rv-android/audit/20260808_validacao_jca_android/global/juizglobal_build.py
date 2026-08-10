#!/usr/bin/env python3
"""juizglobal_build.py — GLOBAL JUDGE builder (protocol §19 items 6-7).

Generates, assert-guarded:
  1. juizglobal_set_claims_resolvidos.csv — the 30 set-phase executor claims
     (set/set_exec_claims.csv) with the global judge's four resolution columns
     appended (resolucao_juiz, classificacao_final, severidade_final,
     fenomeno_id_final).
  2. juizglobal_gates.csv — the machine-readable G0-G13 gate matrix.
  3. juizglobal_build_output.txt — every total printed here.

Asserts enforced (each anchored to a published figure the refutation round can
re-check):
  A1. The consolidated ledger (set/set_cons_ledger.csv) reproduces the
      consolidator's published totals: 558 rows = 210 PASS + 322 FAIL + 26
      INCONCLUSIVE; per-round totals equal each round's rev. 2 record;
      164 critical FAIL of record + 10 pilot derived; 50 critical-carrying
      canonical phenomena; 8 D-batchC-1 fail-open reconciliation rows;
      diagnostico pool 11 PASS / 73 FAIL / 7 INC.
  A2. Every set claim resolved FAIL carries a fenomeno_id_final (D-batchB-1).
  A3. Resolution totals of the 30 set claims: 22 FAIL / 8 PASS / 0 INC;
      severities 15 critica / 6 major / 1 minor (EXEC-SET-23 raised from the
      executor's filed major to critica by the global judge — see report §1).
  A4. Every claim ID cited in a gate row's ponteiros exists in the ledger or
      in the set-phase claims (no gate ground references a nonexistent claim).
  A5. D-batchC-1: every fail-open set claim (FEN-KGN-NAOCOMPILA) is critica.

Read-only over every prior-round and set file; writes only juizglobal_* files
in global/.
"""
import csv
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT = os.path.dirname(HERE)
SETD = os.path.join(AUDIT, "set")

OUT_LINES = []


def P(msg=""):
    print(msg)
    OUT_LINES.append(msg)


# ---------------------------------------------------------------------------
# Global judge resolutions for the 30 set-phase claims.
# resolucao_juiz: judge's PASS/FAIL (all executor positions were re-verified —
#   the decisive dynamic evidence was re-executed byte-identically this
#   session; see juizglobal_relatorio.md §0).
# severidade_final: executor's filed severity upheld everywhere except
#   EXEC-SET-23 (major -> critica: batch C ledger precedent for
#   FEN-SSL-RANDOMIZED-EXTRA is critica and pre_registro §4's letter — an
#   executed FP on a realizable trace — applies; see report §1).
#   REF-G-04 contingency (rev. 2): the FP reading of X1 is contingent on the
#   researcher's §7-item-4 ruling on `randomized[sr]`-with-unbound-`sr`
#   (api30 SSLContext.cryptsl binds `_`); a ruling that makes X1's error
#   oracle-faithful would revisit this severity. FAIL stands either way;
#   severity does not enter the score.
# fenomeno_id_final: canonicalized to the FEN registry where an alias was
#   filed (EXEC-SET-05, EXEC-SET-12); new set-phase FENs kept as filed and
#   flagged in the report (WRAPPER-NAME-ORDER, KMF-CASCADE).
# ---------------------------------------------------------------------------
RES = {
    # id: (resolucao_juiz, severidade_final, fenomeno_id_final)
    "EXEC-SET-01": ("PASS", "n/a", ""),
    "EXEC-SET-02": ("PASS", "n/a", ""),
    "EXEC-SET-03": ("PASS", "n/a", ""),
    "EXEC-SET-04": ("PASS", "n/a", ""),
    "EXEC-SET-05": ("FAIL", "critica", "FEN-SET-FIRSTCALL-DISJUNCT"),
    "EXEC-SET-06": ("FAIL", "critica", "FEN-SET-NESTED-TYPE-DESCRIPTOR"),
    "EXEC-SET-07": ("FAIL", "critica", "FEN-SET-DECLARED-ONLY"),
    "EXEC-SET-08": ("FAIL", "critica", "FEN-SIG-SIGN-VOID"),
    "EXEC-SET-09": ("FAIL", "critica", "FEN-SSL-ENGINE-VOID"),
    "EXEC-SET-10": ("FAIL", "critica", "FEN-MAC-F3-UNBOUND"),
    "EXEC-SET-11": ("PASS", "n/a", ""),
    "EXEC-SET-12": ("FAIL", "major", "FEN-SET-VARARGS-ARGS-IGNORED"),
    "EXEC-SET-13": ("FAIL", "minor", "FEN-SET-WRAPPER-NAME-ORDER"),
    "EXEC-SET-14": ("FAIL", "critica", "FEN-KGN-NAOCOMPILA"),
    "EXEC-SET-15": ("FAIL", "critica", "FEN-KPG-NPE"),
    "EXEC-SET-16": ("FAIL", "critica", "FEN-D-RANDOMIZED-WRITER"),
    "EXEC-SET-17": ("FAIL", "major", "FEN-SET-GENERATEDKEY-2A-CASA"),
    "EXEC-SET-18": ("FAIL", "major", "FEN-D-RANDOMIZED-WRITER"),
    "EXEC-SET-19": ("FAIL", "critica", "FEN-D-KEYPAIR-EDGE"),
    "EXEC-SET-20": ("FAIL", "critica", "FEN-SIG-SIGN-VOID"),
    "EXEC-SET-21": ("FAIL", "critica", "FEN-SIG-VERIFIED-WRONGSLOT"),
    "EXEC-SET-22": ("FAIL", "major", "FEN-SET-KMF-CASCADE"),
    "EXEC-SET-23": ("FAIL", "critica", "FEN-SSL-RANDOMIZED-EXTRA"),
    "EXEC-SET-24": ("FAIL", "critica", "FEN-SET-DEDUPE"),
    "EXEC-SET-25": ("FAIL", "major", "FEN-SET-FAIL-UNKNOWN"),
    "EXEC-SET-26": ("FAIL", "critica", "FEN-SRD-NEXTBYTES-FP"),
    "EXEC-SET-27": ("PASS", "n/a", ""),
    "EXEC-SET-28": ("FAIL", "major", "FEN-SET-STATIC-JCA-DEFAULT"),
    "EXEC-SET-29": ("PASS", "n/a", ""),
    "EXEC-SET-30": ("PASS", "n/a", ""),
}

# Gate matrix (grounds abbreviated; full grounds in juizglobal_relatorio.md §2).
GATES = [
    ("G0", "PASS",
     "fase0 manifests complete; every round + set phase hash-froze inputs; freeze re-verified 23/23 this session; dirty-tree anomaly declared and shown not to touch audited bytes; D-batchD-1 admissibility held (contaminated batchD javap artifact quarantined; set-phase sweep 0 hits)",
     "fase0/manifest_hashes.md; set/set_exec_hashes.txt; EXEC-SET-30; batchD juiz_sintese §8.2#1"),
    ("G1", "PASS",
     "23/23 specs inventoried; 22 paired to 22 distinct api30 rules by content (two name traps resolved); RandomStringPassword has NO CrySL rule and is EXCLUDED by researcher decision of 2026-08-09 (formal scope reduction, registered in fase0/manifesto.md:26-30 and re-registered in this global judgment); 11 unmodelled api30 rules recorded as coverage bound",
     "fase0/inventario_pareamento.md; fase0/manifesto.md:26-30"),
    ("G2", "FAIL",
     "KeyGeneratorSpec monitor does not compile standalone while both generators exit 0 (fail-open, critica per D-batchC-1; re-verified: javac exit 1 'cannot find symbol: Key'; -merge masks it via import union from CipherSpec/KeyStoreSpec); 21/22 clean; <=17-event budget met set-wide (max SRD 15); generator ceiling closed; merge cost measured and deterministic",
     "EXEC-SET-14; EXEC-SET-01..03; batchC juiz_sintese §8.1 (KGN G2 FAIL); batchD juiz_sintese §8.1 note 3"),
    ("G3", "FAIL",
     "16/22 specs FAIL with executed separating counterexamples at the effective automaton (D-piloto-3): CIP,HMC,CIS,COS,KPR,PBK,KGN,KMF,TMF,SSL,KST,MAC,MDG,KPG,SRD,SIG; PASS: GCM,DHG,PBE,IVP,SKS,SKY; set level: canonical SecureRandom creation+nextBytes sequence FPs on the merged monitor (re-executed 3x byte-identical)",
     "round §8.1 tables (pilot/A/B/C/D); EXEC-SET-26"),
    ("G4", "FAIL",
     "18/22 specs FAIL (PASS only IVP,KMF,TMF,SIG); includes the fail-crash class FEN-KPG-NPE surviving -merge byte-for-byte (NPE to caller re-demonstrated this session, 3 reps), MAC f3 unbound target(m) broadcast, VERIFIED written on the boxed Boolean instead of the sign bytes",
     "round §8.1 tables; EXEC-SET-10; EXEC-SET-15; EXEC-SET-21"),
    ("G5", "FAIL",
     "13/22 specs FAIL; 5 canonical capture-divergence mechanism families / 6 named instances (five-vs-six resolved in report §1.2); dead pointcuts re-verified on the production dexlib2 weave over the MERGED descriptor on both frozen jars; batch A/B PASS halves are single-half evidence (batch C §8.4); android-37.0 production-default jar captures 3 post-api30 members (extra-oracle); wrapper naming jar-dependent",
     "batchC juiz_sintese §8.4; batchD juiz_sintese §5; EXEC-SET-05..13"),
    ("G6", "INCONCLUSIVE",
     "static halves executed (descriptor<->aspect<->monitor 119/119+140/140; host dexlib2 weave, 168 scenarios, both jars, re-executed byte-identically) but no round or phase drove a woven DEX on ART/device; §16 demands end-to-end DEX confirmation; unknown never becomes success",
     "EXEC-SET-04; EXEC-SET-11; batchD BETA-SET-06; batchC BETA-SET-08; batchB BETA-SET-11"),
    ("G7", "FAIL",
     "19/22 specs FAIL (PASS: PBE,IVP,MDG); set graph: 11 reader-less constants (assert re-run), 4 extra-oracle gates + 2 extra-oracle reads, guaranteed-fire PREPARED_HMAC edge, RANDOMIZED material overgrant closed writer->reader end to end (rejected randomness accepted; re-executed), KPR 1-FP-per-access toll edge, dead SIGNED/VERIFIED writers, @fail-remove revocation family with zero NEGATES in the api30 rules; only ~5 clean live edges",
     "set/set_cons_predicate_graph.csv; set_cons_report §3; EXEC-SET-16..23; EXEC-SET-29"),
    ("G8", "FAIL",
     "pre_registro §3 row 8 FAILs on observed FP/FN: the executed drives exhibit both (FPs: SRD next2, KPR toll, KMF cascade, SSL unmonitored-random; FNs: rejected-randomness acceptance, SIGNED starvation); the §11 systematic differential/mutation campaign was never executed — suite adequacy additionally INCONCLUSIVE; the drives are adjudication witnesses, not the pre-registered corpus (declared limitation). INTERPRETATION DECLARED (REF-G-03): the FAIL follows the literal FAIL cell of §3 row 8 ('FP/FN observado', no corpus qualifier); the alternative reading — INCONCLUSIVE because the pre-registered test object was never built — is acknowledged and equivalent for the READY conjunction (neither is PASS)",
     "pre_registro §3 row 8; EXEC-SET-16; EXEC-SET-19; EXEC-SET-20; EXEC-SET-26"),
    ("G9", "FAIL",
     "22/22 audited specs FAIL — the only gate failed by every unit in every round; set level: 5 of the 14 drive error records carry expecting=unknown, exactly accompanying the executed FPs; the dedupe identity (spec,type,class,method,loc — expecting excluded) drops the second of two DISTINCT violations at one site (re-executed; identity verified at ErrorDescription.java:108-139; both collectors share it)",
     "round §8.1 tables; EXEC-SET-24; EXEC-SET-25; set_cons_report §4"),
    ("G10", "INCONCLUSIVE",
     "no Android execution in any round or phase; consolidated replay battery named: G10-SRD-1, G10-KPG-1/2, G10-SIG-1, G10-MAC-1, G10-TMF-1, G10-SSL-2, G10-KST-1, G10-KGN-1, G10-IVP-1, G10-SKY-1, GAMA-KPR-06, GAMA-SET-16/21 batteries, Android-BC alias probe",
     "set_cons_report §4.2, §5 G10 row; batchC juiz_sintese §8.5; batchD juiz_sintese §8.4"),
    ("G11", "FAIL",
     "gh101 register invariance premise falsified (predicate_edges.csv:47,74-75,81 vs api30 rules — no 'present' verdict consumable without api30 anchor); false gh101-authored SRD c3 comment; unregistered inherited critical families (provenance census); gh101-introduced defects (GENCIPHER-EXTRA, SSL-RANDOMIZED-EXTRA, KPG initError placement residual); gh100 tasks open (7.4 duplicated [x]/[ ], 7.5, 7.6); repairs that held are equally on record (TMF four-defect, SSL returning(ctx), KGN i1-i5 split, D-S12, layer-2 star prefixes)",
     "batchD juiz_sintese §1#14, §3; batchC juiz_sintese §3; fase0/estado_gh100_gh101.md; set_cons_report §2, §3.1"),
    ("G12", "FAIL",
     "static path verified at source this session: rv_static_analysis/config.py:186 jar probe [33,29,28,27,26] lacks 30; :199-208 mop_dir defaults to the literal jca directory; rv_experiment/config.py get_static_analysis_config (:942-951) passes neither mop_dir nor targets_file nor android_jar — every jca_android run's static view is computed against the jca specs and never the api30 jar; open static/dynamic contradictions (FEN-SET-STATIC-DEAD-TARGETS; SKY both-views-blind); §13 unlock condition contradicted",
     "EXEC-SET-28; GAMA-SET-01; GAMA-SET-03; GAMA-SET-14"),
    ("G13", "FAIL",
     "must-close set open: 174 critical FAIL claims (164 of-record + 10 pilot derived-parsed), of which 165 link to the 50 critical-carrying canonical phenomena and 9 pilot criticals remain pilot-local without canonical FEN (pre-D-piloto-4 record; REF-G-02); the 8 D-batchC-1 reconciliation rows are counted at §4's letter IN ADDITION to the 164 of-record; plus every major family (register-anchor, dedupe/unknown, arithmetic omissions) and 26 named INCONCLUSIVE pendencies; all five refutation rounds were answered objection by objection (13/9/5/8/8) — the review PROCESS is complete, but §16's letter requires no critical/major finding OPEN after refutation",
     "set/set_cons_ledger.csv; set/set_cons_fen_registry.csv; set_cons_report §1.3, §5"),
]


def main():
    # ---- A1: re-verify the consolidated ledger totals -----------------------
    with open(os.path.join(SETD, "set_cons_ledger.csv"), newline="",
              encoding="utf-8") as fh:
        ledger = list(csv.DictReader(fh))
    assert len(ledger) == 558, len(ledger)
    c = Counter(r["resolution"] for r in ledger)
    assert c["PASS"] == 210 and c["FAIL"] == 322 and c["INCONCLUSIVE"] == 26, c
    per_round = {
        "pilot": (72, 30, 34, 8), "batchA": (96, 46, 48, 2),
        "batchB": (133, 40, 88, 5), "batchC": (134, 55, 71, 8),
        "batchD": (123, 39, 81, 3),
    }
    for rnd, (tot, pas, fail, inc) in per_round.items():
        rows = [r for r in ledger if r["round"] == rnd]
        cc = Counter(r["resolution"] for r in rows)
        assert (len(rows), cc["PASS"], cc["FAIL"], cc["INCONCLUSIVE"]) == \
            (tot, pas, fail, inc), (rnd, cc)
    crit_rec = [r for r in ledger if r["resolution"] == "FAIL"
                and r["severity_resolved"] == "critica"
                and r["severity_kind"] == "of-record"]
    crit_der = [r for r in ledger if r["resolution"] == "FAIL"
                and r["severity_resolved"] == "critica"
                and r["severity_kind"] == "derived-parsed"]
    assert len(crit_rec) == 164 and len(crit_der) == 10, \
        (len(crit_rec), len(crit_der))
    crit_fens = {r["fen_canonical"] for r in ledger
                 if r["resolution"] == "FAIL"
                 and r["severity_resolved"] == "critica" and r["fen_canonical"]}
    assert len(crit_fens) == 50, len(crit_fens)
    s4 = [r for r in ledger if r["severity_s4_letter"]
          and r["severity_s4_letter"] != r["severity_resolved"]]
    assert len(s4) == 8, len(s4)
    diag = Counter(r["resolution"] for r in ledger
                   if r["dimension"] == "diagnostico")
    assert (diag["PASS"], diag["FAIL"], diag["INCONCLUSIVE"]) == (11, 73, 7), diag
    P("A1 ledger asserts PASS: 558 rows = 210/322/26; per-round figures match "
      "every rev. 2 record; criticals 164 of-record + 10 derived over 50 "
      "phenomena; 8 D-batchC-1 reconciliation rows; diagnostico 11/73/7.")

    # ---- resolved set claims CSV -------------------------------------------
    with open(os.path.join(SETD, "set_exec_claims.csv"), newline="",
              encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        claims = list(reader)
        cols = reader.fieldnames
    assert len(claims) == 30, len(claims)
    out_cols = cols + ["resolucao_juiz", "classificacao_final",
                       "severidade_final", "fenomeno_id_final"]
    resolved = []
    for r in claims:
        cid = r["id"]
        res, sev, fen = RES[cid]
        row = dict(r)
        row["resolucao_juiz"] = res
        # classificacao_final: the executor's six-state label is upheld for all
        # 30 claims (every decisive evidence re-verified; see report §0-§1).
        row["classificacao_final"] = r["classificacao"]
        row["severidade_final"] = sev
        row["fenomeno_id_final"] = fen
        resolved.append(row)

    # A2: D-batchB-1 — every FAIL carries a phenomenon
    for row in resolved:
        if row["resolucao_juiz"] == "FAIL":
            assert row["fenomeno_id_final"], row["id"]
    P("A2 D-batchB-1 assert PASS: every FAIL set claim carries "
      "fenomeno_id_final.")

    # A3: resolution totals
    rc = Counter(r["resolucao_juiz"] for r in resolved)
    sc = Counter(r["severidade_final"] for r in resolved
                 if r["resolucao_juiz"] == "FAIL")
    assert rc["FAIL"] == 22 and rc["PASS"] == 8 and rc.get("INCONCLUSIVE", 0) == 0, rc
    assert sc["critica"] == 15 and sc["major"] == 6 and sc["minor"] == 1, sc
    P(f"A3 resolution asserts PASS: 30 = 22 FAIL / 8 PASS / 0 INCONCLUSIVE; "
      f"severities 15 critica / 6 major / 1 minor "
      f"(EXEC-SET-23 raised major->critica by the global judge).")

    # A5: fail-open family at critica (D-batchC-1)
    for row in resolved:
        if row["fenomeno_id_final"] == "FEN-KGN-NAOCOMPILA":
            assert row["severidade_final"] == "critica", row["id"]
    P("A5 D-batchC-1 assert PASS: fail-open set claims resolved at critica.")

    # per-phenomenon counts (D-piloto-4 rule 3)
    fen_counts = Counter(r["fenomeno_id_final"] for r in resolved
                         if r["resolucao_juiz"] == "FAIL")
    P(f"\nSet-phase FAIL claims by phenomenon ({len(fen_counts)} phenomena over "
      f"{sum(fen_counts.values())} claims):")
    for fen, n in sorted(fen_counts.items()):
        P(f"  {fen}: {n}")

    # descriptive set-phase score (pre_registro §6 weights; D-batchA-1 raw sum)
    WEIGHTS = {"linguagem_formal": 20, "captura_eventos": 20,
               "bindings_clausulas": 15, "predicados_composicao": 15,
               "toolchain_android": 15, "diagnostico": 10,
               "reprodutibilidade": 5}
    P("\nDescriptive SET-phase score (pre-registered weights; raw weighted sum "
      "per D-batchA-1; denominator = claims resolved by the global judge; "
      "0 INCONCLUSIVE -> COMPLETE; all 7 dimensions carry claims -> no "
      "unattainable weight):")
    total = 0.0
    for dim, w in WEIGHTS.items():
        rows = [r for r in resolved if r["dimensao"] == dim]
        n = len(rows)
        p = sum(1 for r in rows if r["resolucao_juiz"] == "PASS")
        sub = w * p / n if n else 0.0
        total += sub
        P(f"  {dim}: weight {w}, resolved {n}, PASS {p}, subscore {sub:.2f}")
    P(f"  TOTAL (raw weighted sum): {total:.2f} / 100")
    P("  MANDATORY LABELS: descriptive score != probability of correction != "
      "verdict; never rounded to 100; no score opens a gate; COMPLETE "
      "(0 INCONCLUSIVE).")
    assert abs(total - 15.45) < 0.01, total

    # ---- A4: gate ground pointers reference existing claims -----------------
    # Hardened per REF-G-01 (rev. 2): round-qualified pointers of the form
    # "batch<X> CLAIM-ID" are checked as (round, claim_id) PAIRS against the
    # ledger, not just token existence; unqualified round-claim IDs are checked
    # for existence anywhere (declared scope: existence-only).
    ledger_ids = {r["claim_id"] for r in ledger}
    ledger_pairs = {(r["round"], r["claim_id"]) for r in ledger}
    set_ids = {r["id"] for r in resolved}
    known = ledger_ids | set_ids
    import re
    for gate, res, ground, ptr in GATES:
        text = ground + "; " + ptr
        for rnd, tok in re.findall(r"\b(pilot|batch[A-D])\s+"
                                   r"([A-Z]+-[A-Z]{2,4}-\d+)\b", text):
            if (rnd, tok) not in ledger_pairs:
                raise AssertionError(
                    f"{gate}: round-qualified pointer ({rnd}, {tok}) not in ledger")
        for tok in re.findall(r"\b(?:EXEC-SET-\d+|[A-Z]+-[A-Z]{2,4}-\d+"
                              r"|BETA-SET-\d+|GAMA-SET-\d+|ALFA-SET-\d+)\b",
                              text):
            if tok not in known:
                raise AssertionError(f"{gate}: pointer {tok} not a known claim")
    P("\nA4 gate-pointer assert PASS (rev. 2, REF-G-01-hardened): every "
      "round-qualified pointer resolves as a (round, claim) pair in the "
      "ledger; every unqualified claim ID exists in the ledger or the "
      "set-phase claims.")

    # ---- A6 (rev. 2, REF-G-01): G6's intended referents are INCONCLUSIVE ----
    g6_expected = [("batchD", "BETA-SET-06"), ("batchC", "BETA-SET-08"),
                   ("batchB", "BETA-SET-11")]
    by_pair = {(r["round"], r["claim_id"]): r["resolution"] for r in ledger}
    for pair in g6_expected:
        assert by_pair.get(pair) == "INCONCLUSIVE", (pair, by_pair.get(pair))
    P("A6 assert PASS: G6's cited referents (batchD BETA-SET-06, batchC "
      "BETA-SET-08, batchB BETA-SET-11) are each INCONCLUSIVE in their round "
      "of record (same-named claims in other rounds are distinct claims).")

    # ---- write outputs ------------------------------------------------------
    with open(os.path.join(HERE, "juizglobal_set_claims_resolvidos.csv"), "w",
              newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=out_cols)
        w.writeheader()
        w.writerows(resolved)
    with open(os.path.join(HERE, "juizglobal_gates.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["gate", "resultado", "fundamento_curto", "ponteiros"])
        w.writerows(GATES)
    gate_res = Counter(g[1] for g in GATES)
    P(f"\nGate matrix written: {dict(gate_res)} "
      f"(PASS: G0,G1; INCONCLUSIVE: G6,G10; FAIL: the other 10).")
    P("\nSET VERDICT (pre_registro §7 conjunction): NOT READY. Failing "
      "members: (1) 23/23 APROVADA -> 0/22 audited approved (22 REPROVADA; 1 "
      "researcher-excluded); (2) all gates PASS -> 10 FAIL + 2 INCONCLUSIVE; "
      "(3) no OMITIDA/INCORRETA/INCONCLUSIVA clause -> hundreds INCORRETA/"
      "OMITIDA + 26 INCONCLUSIVE; (4) no open counterexample -> executed "
      "counterexamples open. Member (5) reproducible evidence is the only one "
      "satisfied.")
    with open(os.path.join(HERE, "juizglobal_build_output.txt"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(OUT_LINES) + "\n")


if __name__ == "__main__":
    main()
