#!/usr/bin/env python3
"""set_cons_build.py — SET-phase consolidation builder (protocol §19.5, analytical half).

Regenerates, from the five CLOSED per-round resolved CSVs (rev. 2 where a rev. 2
exists), the consolidated claim ledger (set_cons_ledger.csv), the unified FEN
registry (set_cons_fen_registry.csv) and the set-level predicate graph
(set_cons_predicate_graph.csv), plus every total printed to stdout
(captured as set_cons_build_output.txt). Assert-guarded against the published
rev. 2 figures of each round. Read-only over all inputs.

Column normalization (documented mapping, pilot → later-round schema):
  pilot juiz_claims_resolvidos.csv (rev. 2) has columns
    claim_id, resolucao, classificacao, dimensao_score, evidencia_decisiva, pendencia
  mapped as: claim_id->id; resolucao->resolucao_juiz; classificacao->classificacao_final
  (six-state token = text before the first '('); severity: the pilot record does NOT
  carry a machine severity column — it is PARSED here from the classificacao free text
  (first occurrence of critica|crítica|major|minor inside the field) and is therefore a
  DERIVED reading, labeled as such, never a figure of record.
  dimensao_score values map: linguagem->linguagem_formal, captura->captura_eventos,
  bindings->bindings_clausulas, predicados->predicados_composicao,
  toolchain->toolchain_android, diagnostico/reprodutibilidade unchanged.
  The pilot pre-dates the FEN discipline (D-piloto-4 was fixed after it): pilot rows
  carry no fenomeno_id. Eight pilot claims are joined to canonical FENs here ONLY where
  a later closed round's record explicitly joins them (list PILOT_FEN below, each with
  its source); all other pilot rows keep an empty fen_canonical.

batchA has fenomeno_id (agent-filed; the fenomeno_id_final column only exists from
batch B rev. 2 onward per D-batchB-1); batchB/C/D use fenomeno_id_final.

Severity normalization: 'crítica'->'critica'; '-', 'n/a', '' -> 'none'.
'major-pending' kept verbatim (REF-E-05 machine record).

D-batchC-1 reconciliation column (severidade_s4_letter): fail-open family claims
resolved below critica in pilot/batchA/batchB get 'critica(D-batchC-1)' in that column;
their round severity of record is NOT rewritten (closed rounds stay closed). Membership
list FAILOPEN_S4 below, with the consolidator's selection rule stated in the report §1.
"""
import csv, hashlib, os, re, sys, collections

AUDIT = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))  # audit root
SETD = os.path.join(AUDIT, "set")
SPECS_DIR = ("/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/"
             "rvsec/rvsec/rvsec-mop/src/main/resources/jca_android")

SOURCES = [
    ("pilot",  os.path.join(AUDIT, "pilot",  "juiz_claims_resolvidos.csv")),
    ("batchA", os.path.join(AUDIT, "batchA", "juiz_claims_resolvidos_batchA.csv")),
    ("batchB", os.path.join(AUDIT, "batchB", "juiz_claims_resolvidos_batchB.csv")),
    ("batchC", os.path.join(AUDIT, "batchC", "juiz_claims_resolvidos_batchC.csv")),
    ("batchD", os.path.join(AUDIT, "batchD", "juiz_claims_resolvidos_batchD.csv")),
]

# Published rev. 2 figures (source: each round's juiz_sintese §8 / §3):
PUBLISHED = {  # round: (total, PASS, FAIL, INCONCLUSIVE, critical_FAIL, critical_FEN_groups)
    "pilot":  (72, 30, 34, 8, None, None),   # pilot record carries no machine severity
    "batchA": (96, 46, 48, 2, 18, 7),
    "batchB": (133, 40, 88, 5, 38, 12),
    "batchC": (134, 55, 71, 8, 54, 17),
    "batchD": (123, 39, 81, 3, 54, 21),
}

DIM_MAP = {
    # pilot
    "linguagem": "linguagem_formal", "captura": "captura_eventos",
    "bindings": "bindings_clausulas", "predicados": "predicados_composicao",
    "toolchain": "toolchain_android",
    # batch D accented variants (judge §2.7: spelling normalization only)
    "captura de eventos": "captura_eventos",
    "equivalência paramétrica/ciclo de vida": "bindings_clausulas",  # D §2.7 pendency
    "predicados/composição": "predicados_composicao",
    "linguagem formal": "linguagem_formal",
    "bindings/cláusulas": "bindings_clausulas",
    "diagnóstico": "diagnostico",
}

SPEC_CODE = {  # claim-id token -> spec unit
    "CIP": "CipherSpec", "GCM": "GCMParameterSpecSpec",
    "DHG": "DHGenParameterSpecSpec", "HMC": "HMACParameterSpecSpec",
    "PBE": "PBEParameterSpecSpec", "IVP": "IvParameterSpecSpec",
    "SKS": "SecretKeySpecSpec", "CIS": "CipherInputStreamSpec",
    "COS": "CipherOutputStreamSpec", "KPR": "KeyPairSpec",
    "SKY": "SecretKeySpec(SecretKey)", "PBK": "PBEKeySpecSpec",
    "KGN": "KeyGeneratorSpec", "KMF": "KeyManagerFactorySpec",
    "TMF": "TrustManagerFactorySpec", "SSL": "SSLContextSpec",
    "KST": "KeyStoreSpec", "MAC": "MacSpec", "MDG": "MessageDigestSpec",
    "KPG": "KeyPairGeneratorSpec", "SRD": "SecureRandomSpec",
    "SIG": "SignatureSpec", "SET": "SET",
}

# ---------------------------------------------------------------------------
# FEN canonicalization.
# batchB aliases are VERBATIM the judge's own unification map
# (batchB/juiz_rescore_batchB.py:90-117, rev. 2). batchA aliases reproduce the
# batch A judge's §3 phenomenon table (juiz_sintese_batchA.md:187-197), verified
# below by asserting 7 critical FEN groups over exactly 18 critical claims.
# Cross-round merges reproduce batch D §2.6 + §6 and batch C §8.4 declarations.
ALIAS = {
    # --- batch A -> §3 canonicals
    "FEN-DHG-supressao-condition": "FEN-DHG-SUPRESSAO",
    "FEN-DHG-condicao-extra": "FEN-DHG-SUPRESSAO",
    "FEN-DHG-SUPRESSAO-CONFORME": "FEN-DHG-SUPRESSAO",
    "FEN-HMC-linguagem": "FEN-HMC-MONITOR-GLOBAL",
    "FEN-HMC-lifecycle": "FEN-HMC-MONITOR-GLOBAL",
    "FEN-HMC-monitor-global": "FEN-HMC-MONITOR-GLOBAL",
    "FEN-HMC-classe-ausente": "FEN-HMC-CLASSE-AUSENTE",
    "FEN-HMC-classe-ausente-api30": "FEN-HMC-CLASSE-AUSENTE",
    "FEN-PBE-supressao-c2": "FEN-PBE-C2-GAP",
    "FEN-SKS-whitelist-extra": "FEN-SKS-WHITELIST",
    "FEN-SKS-whitelist-extra-oraculo": "FEN-SKS-WHITELIST",
    "FEN-SKS-surrogate-preparedkeymaterial": "FEN-SKS-SURROGATE",
    "FEN-SKS-requires-4arg": "FEN-SKS-REQUIRES-4ARG",
    "FEN-SKS-requires-c2": "FEN-SKS-REQUIRES-4ARG",
    "FEN-SKS-C2-RANDOMIZED-DROP": "FEN-SKS-REQUIRES-4ARG",
    "FEN-SET-generatedkey-2a-casa": "FEN-SET-GENERATEDKEY-2A-CASA",
    "FEN-SET-STALE-FLAGS": "FEN-A-STALE-FLAGS",   # batch D §3 names the canonical
    "FEN-SET-failopen-parser": "FEN-SET-FAIL-OPEN",
    "FEN-SET-failopen-simbolo": "FEN-SET-FAIL-OPEN",
    "FEN-SET-PARSER-FAILOPEN": "FEN-SET-FAIL-OPEN",
    "FEN-SET-exit0-erro": "FEN-SET-FAIL-OPEN",
    "FEN-SET-parenteses-tolerados": "FEN-SET-FAIL-OPEN",
    "FEN-SET-flags-obsoletas": "FEN-SET-FLAGS-OBSOLETAS",
    "FEN-SET-fail-morto": "FEN-SET-FAIL-MORTO",
    "FEN-BATCHA-fail-morto": "FEN-SET-FAIL-MORTO",  # claim-level remap of ALFA-SET-04 below
    "FEN-PBE-msg-1000": "FEN-PBE-MSG-1000",
    "FEN-PBE-errortype": "FEN-PBE-MSG-1000",  # batch A §3 counts the 4-claim FEN-PBE-MSG group
    "FEN-IVP-UNKNOWN-EXPECTING": "FEN-IVP-UNKNOWN",
    # --- batch B (judge's own map, juiz_rescore_batchB.py:90-117)
    "FEN-CIS-MONITOR-GLOBAL": "FEN-STREAMS-MONITOR-GLOBAL",
    "FEN-COS-MONITOR-GLOBAL": "FEN-STREAMS-MONITOR-GLOBAL",
    "FEN-STREAMS-monitor-global": "FEN-STREAMS-MONITOR-GLOBAL",
    "FEN-SET-MONITOR-GLOBAL-SEM-PARAMETRO": "FEN-STREAMS-MONITOR-GLOBAL",
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
    "FEN-SET-failopen": "FEN-SET-FAIL-OPEN",  # cross-round: C/D canonical FEN-SET-FAIL-OPEN
    "FEN-SET-JCA-DIR-DEFAULT": "FEN-SET-STATIC-JCA-DEFAULT",
}
# claim-level remaps (batch A judge's §3: ALFA-SET-04 is counted inside the HMC
# monitor-global phenomenon — "BETA-HMC-03; overturned ALFA-HMC-01/05, ALFA-SET-04")
CLAIM_FEN = {
    ("batchA", "ALFA-SET-04"): "FEN-HMC-MONITOR-GLOBAL",
}
# Pilot joins — ONLY where a later closed round's record explicitly joins the claim
# or names the identical mechanism as the same family (source cited per entry):
PILOT_FEN = {
    "ALFA-CIP-07": ("FEN-SET-GENERATEDKEY-2A-CASA", "batchA juiz_sintese §3: 'joins pilot ALFA-CIP-07'"),
    "GAMA-GCM-01": ("FEN-SET-FAIL-OPEN", "fail-open de símbolo; same family as batchA FEN-SET-failopen-simbolo; D-batchC-1"),
    "BETA-SET-04": ("FEN-SET-FAIL-OPEN", "exit 0 com erro; D-batchC-1 family"),
    "GAMA-CIP-04": ("FEN-SET-DEDUPE", "batchB/C/D FEN-SET-DEDUPE same mechanism (dedupe colide cláusulas)"),
    "GAMA-CIP-01": ("FEN-SET-FAIL-UNKNOWN", "todo @fail = unknown; batchB FEN-SET-FAIL-UNKNOWN same mechanism"),
    "BETA-CIP-06": ("FEN-SET-FLAGS-OBSOLETAS", "batchA FEN-SET-flags-obsoletas names the pilot pair"),
    "GAMA-CIP-08": ("FEN-SET-FLAGS-OBSOLETAS", "idem"),
    "GAMA-SET-01": ("FEN-SET-STATIC-JCA-DEFAULT", "static path literal jca / no api30; batchB FEN-SET-JCA-DIR-DEFAULT, batchD FEN-SET-STATIC-JCA-DEFAULT"),
    "GAMA-SET-03": ("FEN-SET-STATIC-JCA-DEFAULT", "idem"),
}

# D-batchC-1 §4-letter reconciliation: fail-open family FAIL claims in pilot/A/B
# resolved below critica. Selection rule: FEN family == FEN-SET-FAIL-OPEN after
# canonicalization (i.e. the judges' own fail-open naming), plus the two pilot
# claims joined above. Family-adjacent phenomena NOT counted (documented in the
# report §1): FEN-SET-GERADOR-SILENCIO (silent generator acceptance censuses),
# FEN-SET-FAIL-MORTO (dead @fail code), silent-acceptance census claims.
FAILOPEN_ROUNDS = {"pilot", "batchA", "batchB"}

SIX_STATES = ["FIDELIDADE_DEMONSTRADA", "DIVERGENCIA_EQUIVALENTE_COMPROVADA",
              "LIMITACAO_INEVITAVEL_DOCUMENTADA", "OMITIDA", "INCORRETA", "INCONCLUSIVA"]

def norm_sev(s):
    s = (s or "").strip()
    s = s.replace("crítica", "critica")
    if s in ("", "-", "n/a", "none"): return "none"
    return s

def pilot_sev(classificacao, resol):
    if resol != "FAIL": return "none"
    m = re.search(r"cr[ií]tica|major|minor", classificacao)
    return norm_sev(m.group(0)) if m else "none"

def pilot_state(classificacao):
    tok = re.split(r"[\(\[]", classificacao)[0].strip()
    # normalize accents already absent in the CSV; keep the leading token
    return tok

def spec_of(claim_id):
    m = re.match(r"^(ALFA|BETA|GAMA)-([A-Z]{3})-", claim_id)
    return SPEC_CODE.get(m.group(2), m.group(2)) if m else claim_id

def canon(fen):
    fen = (fen or "").strip()
    return ALIAS.get(fen, fen)

def main():
    out = []
    P = out.append
    ledger = []
    for rnd, path in SOURCES:
        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        for r in rows:
            if rnd == "pilot":
                cid = r["claim_id"]; resol = r["resolucao"]
                state = pilot_state(r["classificacao"])
                sev = pilot_sev(r["classificacao"], resol)
                dim = DIM_MAP.get(r["dimensao_score"], r["dimensao_score"])
                fen_src = ""
                fen_can, join_src = PILOT_FEN.get(cid, ("", ""))
                sev_kind = "derived-parsed"  # pilot severity is not a column of record
            else:
                cid = r["id"]; resol = r["resolucao_juiz"]
                state = r["classificacao_final"]
                sev = norm_sev(r["severidade_final"])
                dim = DIM_MAP.get(r["dimensao"], r["dimensao"])
                fen_src = (r.get("fenomeno_id_final") or r.get("fenomeno_id") or "").strip()
                fen_can = CLAIM_FEN.get((rnd, cid)) or canon(fen_src)
                join_src = ""
                sev_kind = "of-record"
            sev_s4 = sev
            if (rnd in FAILOPEN_ROUNDS and resol == "FAIL"
                    and fen_can == "FEN-SET-FAIL-OPEN" and sev not in ("critica",)):
                sev_s4 = "critica(D-batchC-1)"
            ledger.append({
                "round": rnd, "claim_id": cid, "spec": spec_of(cid), "dimension": dim,
                "resolution": resol, "classification": state,
                "severity_resolved": sev, "severity_kind": sev_kind,
                "severity_s4_letter": sev_s4,
                "fen_source": fen_src, "fen_canonical": fen_can,
                "pilot_join_source": join_src,
            })

    # ------------------------------------------------------------------ totals
    P("== set_cons_build — consolidated ledger totals ==")
    grand = collections.Counter()
    for rnd, _ in SOURCES:
        rows = [r for r in ledger if r["round"] == rnd]
        c = collections.Counter(r["resolution"] for r in rows)
        tot, pas, fail, inc, crit_pub, fen_pub = PUBLISHED[rnd]
        assert len(rows) == tot, (rnd, len(rows), tot)
        assert c["PASS"] == pas and c["FAIL"] == fail and c["INCONCLUSIVE"] == inc, (rnd, c)
        crit = [r for r in rows if r["resolution"] == "FAIL" and r["severity_resolved"] == "critica"]
        fens = {r["fen_canonical"] for r in crit if r["fen_canonical"]}
        line = (f"{rnd:7s} total={len(rows):3d} PASS={c['PASS']:3d} FAIL={c['FAIL']:3d} "
                f"INC={c['INCONCLUSIVE']:2d} critFAIL={len(crit):3d} critFEN={len(fens):2d}")
        if crit_pub is not None:
            assert len(crit) == crit_pub, (rnd, len(crit), crit_pub)
            assert len(fens) == fen_pub, (rnd, sorted(fens), fen_pub)
            line += "  (== published rev.2 figures)"
        else:
            line += "  (pilot critFAIL is a DERIVED parse — pilot record has no severity column)"
        P(line)
        grand.update(c)
    P(f"OVERALL total={len(ledger)} PASS={grand['PASS']} FAIL={grand['FAIL']} "
      f"INC={grand['INCONCLUSIVE']}")
    assert len(ledger) == 558 and grand["PASS"] == 210 and grand["FAIL"] == 322 \
        and grand["INCONCLUSIVE"] == 26

    crit_all = [r for r in ledger if r["resolution"] == "FAIL" and r["severity_resolved"] == "critica"]
    pilot_crit = [r for r in crit_all if r["round"] == "pilot"]
    P(f"critical FAIL claims: of-record (A+B+C+D) = {len(crit_all)-len(pilot_crit)} "
      f"(18+38+54+54=164); pilot derived-parsed = {len(pilot_crit)} "
      f"-> overall derived = {len(crit_all)}")
    s4 = [r for r in ledger if r["severity_s4_letter"].endswith("(D-batchC-1)")]
    P(f"D-batchC-1 reconciliation column set on {len(s4)} pilot/A/B fail-open claims: "
      + ", ".join(f"{r['round']}:{r['claim_id']}(was {r['severity_resolved']})" for r in s4))

    # per-dimension totals (context only; scores of record live in each round)
    P("\nper-dimension resolution counts (all rounds pooled; context only, not a score):")
    for dim in sorted({r["dimension"] for r in ledger}):
        rows = [r for r in ledger if r["dimension"] == dim]
        c = collections.Counter(r["resolution"] for r in rows)
        P(f"  {dim:24s} n={len(rows):3d} PASS={c['PASS']:3d} FAIL={c['FAIL']:3d} INC={c['INCONCLUSIVE']:2d}")

    # ------------------------------------------------------------ FEN registry
    fen_rows = collections.defaultdict(lambda: {"rounds": set(), "specs": set(),
                                                "claims": [], "fail": 0, "crit": 0})
    for r in ledger:
        f = r["fen_canonical"]
        if not f: continue
        d = fen_rows[f]
        d["rounds"].add(r["round"]); d["specs"].add(r["spec"]); d["claims"].append(r["claim_id"])
        if r["resolution"] == "FAIL":
            d["fail"] += 1
            if r["severity_resolved"] == "critica": d["crit"] += 1

    curated = CURATED  # defined below
    reg_path = os.path.join(SETD, "set_cons_fen_registry.csv")
    with open(reg_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL)
        w.writerow(["fen_canonical", "family", "aliases", "rounds", "specs",
                    "claims_total", "claims_fail", "claims_critical",
                    "provenance", "executed_evidence", "open_pendencies", "notes"])
        for f in sorted(fen_rows, key=lambda x: (-fen_rows[x]["crit"], -fen_rows[x]["fail"], x)):
            d = fen_rows[f]
            aliases = sorted(a for a, c in ALIAS.items() if c == f)
            cur = curated.get(f, {})
            w.writerow([f, cur.get("family", ""), "; ".join(aliases),
                        " ".join(sorted(d["rounds"])), " ".join(sorted(d["specs"])),
                        len(d["claims"]), d["fail"], d["crit"],
                        cur.get("prov", "not curated at set level (see round record)"),
                        cur.get("evid", ""), cur.get("pend", ""), cur.get("note", "")])
    P(f"\nFEN registry: {len(fen_rows)} phenomena with claim linkage "
      f"({sum(1 for f in fen_rows if fen_rows[f]['crit'])} with >=1 critical FAIL claim) "
      f"-> {os.path.basename(reg_path)}")
    P("NOTE: pilot claims enter the registry only via the 9 documented joins; the pilot's "
      "other phenomena remain in the pilot record without FEN ids (pre-D-piloto-4).")

    # ------------------------------------------------------- ledger CSV output
    led_path = os.path.join(SETD, "set_cons_ledger.csv")
    with open(led_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ledger[0].keys()), quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r in ledger: w.writerow(r)
    P(f"ledger: {len(ledger)} rows -> {os.path.basename(led_path)}")

    # ------------------------------------------------ predicate graph (G7 half)
    pat_ev = re.compile(r"^\s*(?:creation\s+)?event\s+([A-Za-z0-9_]+)")
    pat_hd = re.compile(r"^\s*@(match\w*|fail)")
    pat_ere = re.compile(r"^\s*ere\s*:")
    pat_op = re.compile(r"(setProperty|validate|remove)\s*\(\s*Property\.([A-Z_]+)\s*,\s*([A-Za-z0-9_\.]+)")
    sites = []
    for fn in sorted(os.listdir(SPECS_DIR)):
        if not fn.endswith(".mop"): continue
        lines = open(os.path.join(SPECS_DIR, fn), encoding="utf-8", errors="replace").read().splitlines()
        ctx, seen_event, after_ere = "helper", False, False
        for i, l in enumerate(lines, 1):
            m = pat_ev.match(l)
            if m: ctx, seen_event = f"event {m.group(1)}", True
            if pat_ere.match(l): after_ere = True
            mh = pat_hd.match(l)
            if mh and after_ere: ctx = f"@{mh.group(1)}"
            for m2 in pat_op.finditer(l):
                op, const, arg = m2.groups()
                opk = {"setProperty": "write", "validate": "read", "remove": "remove"}[op]
                sites.append({"file": fn, "line": i, "context": ctx if seen_event or ctx == "helper" else "helper",
                              "op": opk, "constant": const, "argument": arg})
    graph_path = os.path.join(SETD, "set_cons_predicate_graph.csv")
    ann = GRAPH_ANN
    with open(graph_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL)
        w.writerow(["constant", "spec_file", "line", "context", "op", "argument",
                    "arg_kind", "api30_status", "liveness", "adjudication"])
        for s in sorted(sites, key=lambda x: (x["constant"], x["file"], x["line"])):
            key = (s["file"], s["line"])
            a = ann.get(key, ann.get((s["file"], s["constant"], s["op"]), {}))
            w.writerow([s["constant"], s["file"], s["line"], s["context"], s["op"],
                        s["argument"], a.get("kind", ""), a.get("api30", ""),
                        a.get("live", ""), a.get("adj", "")])
    n_const = len({s["constant"] for s in sites})
    P(f"\npredicate graph: {len(sites)} Property sites over {n_const} constants "
      f"-> {os.path.basename(graph_path)}")
    # graph-level asserts (facts verified in this session against the frozen specs)
    consts = collections.defaultdict(lambda: {"write": 0, "read": 0, "remove": 0})
    for s in sites: consts[s["constant"]][s["op"]] += 1
    for c in ("SIGNED", "VERIFIED", "DIGESTED", "WRAPPED_KEY", "PREPARED_PBE",
              "SPECCED_KEY", "GENERATED_MAC", "GENERATE_SSL_CONTEXT", "GENERATE_SSL_ENGINE",
              "GENERATED_KEY_PAIR", "GENERATED_TRUST_MANAGER"):
        assert consts[c]["read"] == 0, (c, consts[c])  # writer-side constants with no reader
    assert consts["GENERATED_CIPHER"]["read"] == 2 and consts["GENERATED_CIPHER"]["write"] == 3
    assert consts["PREPARED_HMAC"]["write"] == 1 and consts["PREPARED_HMAC"]["read"] == 1
    P("graph asserts: 11 reader-less constants confirmed; GENERATED_CIPHER 3w/2r; "
      "PREPARED_HMAC 1w/1r (guaranteed-fire pair) — all against the frozen specs")
    P("\nwriter/reader/remove counts per constant:")
    for c in sorted(consts):
        d = consts[c]
        P(f"  {c:26s} writes={d['write']:2d} reads={d['read']:2d} removes={d['remove']:2d}")
    text = "\n".join(out)
    print(text)
    with open(os.path.join(SETD, "set_cons_build_output.txt"), "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    return 0

# ---------------------------------------------------------------------------
# Curated FEN metadata (set-level consolidation; every entry cites its round
# record — file pointers are relative to the audit root).
def _c(family, prov, evid, pend="", note=""):
    return {"family": family, "prov": prov, "evid": evid, "pend": pend, "note": note}

CURATED = {
    # ---- cross-round critical families
    "FEN-C-GETS-INVISIVEL": _c("capture-omission (getInstance domains)",
        "jca-inherited; Cipher twin repaired by gh101 (b532e439f79a), MAC/KPG/SIG (+ batch C KGN/KMF/TMF/SSL) not; unregistered",
        "batchC juiz_sintese §3 (S14, tmf_c); batchD juiz_sintese §1#1 (JAVAP, W walks, D1 crash route, capture matrix)",
        "Android replay G10-{MAC,KPG,SIG}-1", "critical in 8 specs, major in SRD (halves disagree on the unsafe half)"),
    "FEN-C-CARRIER-SEQFAIL": _c("pairing (specific error + spurious InvalidSeq, same call)",
        "jca-inherited shapes; KPG/TMF/SSL forms reshaped by gh101 (immediate->delayed conversion in KPG); partially registered (3b.11b)",
        "batchC S1-S5; batchD D6 executed, W carrier walks x4; D3 executed the SRD counter-design (zero pairing)",
        "G10 replay (historical attribution only)",
        "H2 CLOSED: immediate in MAC/MDG/KPG/SIG + batch C 5; delayed in KPG/TMF; SRD decouples by design"),
    "FEN-C-EMPTY-LABEL": _c("diagnostics (empty 'but found .' label)",
        "jca-inherited mechanism; live in MAC/MDG/SIG via creation-at-consume (task 8.1 covered only the weaver route)",
        "batchD MAC-T5/mdg_a/sig_a conferred; W invisible-creation walk; H4 CLOSED live",
        "per-line historical attribution deferred (G10)", ""),
    "FEN-MAC-F3-UNBOUND": _c("unbound target() / weave-half divergence",
        "jca-inherited (twin f2 header byte-same incl. unbound target(m); bodies differ), unregistered",
        "batchD D9 executed broadcast both directions; two independent ajc probes (dead at exit 0); RuntimeMonitor:1684 broadcast dispatch",
        "ART half (which semantics the device realizes)", "fail-open at §4 letter (D-batchC-1)"),
    "FEN-MAC-KEYGATE-EXTRA": _c("extra-oracle condition gate (suppression)",
        "jca-inherited; register row 'present' is 1.5.2-anchored (falsified premise, FEN-D-REGISTER-ANCHOR-DRIFT)",
        "batchD D4 executed the displaced FP; raw Mac.cryptsl REQUIRES has no generatedKey clause (judge-read)",
        "1.5.2-vs-api30 anchor decision (researcher countersignature)", ""),
    "FEN-SIG-SIGN-VOID": _c("dead pointcut (wrong return type)",
        "jca-inherited, unregistered; generator fail-open note (D-batchC-1)",
        "batchD judge javap over extracted bytes; W sign-truncation walk; Beta capture matrix NEITHER on both halves",
        "", "third instance of the dead-return-type class (batch C TMF gtm1, SSL engine)"),
    "FEN-SRD-NEXTBYTES-FP": _c("automaton omission (next2 missing from end state)",
        "jca-inherited (twin end block identical minus setSeed3), unregistered, live both campaigns",
        "batchD D2 executed (canonical trace FP); spec text SecureRandomSpec.mop:169-177 + effective table + W minimal trace",
        "H-SRD-1 attribution -> G10-SRD-1", "the batch D headline FP"),
    "FEN-SRD-C3-SILENT": _c("silent violating branch + false register comment",
        "body jca-inherited; false gh101 comment (:136-139) gh101-authored — comment/code divergence judge-confirmed",
        "batchD judge source read (c3 body 'sr = r;' only); D3/J1-D",
        "", ""),
    "FEN-SRD-SEED-AFTER-END": _c("over-acceptance FN", "jca-inherited",
        "batchD W walk (FN executed on realizable trace)", "", ""),
    "FEN-SRD-RANDOMIZED-OVERGRANT": _c("predicate overgrant (material marks)",
        "jca-inherited (body-write shape)",
        "batchD D3 executed the object/material split (RANDOMIZED[material]=true from unsafe instance; RANDOMIZED[sr]=false)",
        "CrySL predicate-semantics footnote (declared)",
        "set-level consequence: material-level randomized[] reads unsound; object-level sound (decides pilot/A/B residuals)"),
    "FEN-KPG-NPE": _c("fail-crash (spec-authored switch on uninitialized field)",
        "jca-inherited (twin mechanism-identical: switch on creation-initialized field; twin has extra literal cases), unregistered",
        "batchD D1 executed: NPE to caller from init1Event and initErrorEvent; §2.4 classification (G4, G5 enabling route)",
        "woven-APK replay G10-KPG-1", "the audit's first fail-crash class"),
    "FEN-KPG-FAILSINK": _c("absorbing fail state (only spec without __RESET)",
        "jca-inherited (@fail identical)", "batchD __RESET census + executed cascade", "", ""),
    "FEN-A-STALE-FLAGS": _c("generated-code shape (stale category flags re-fire)",
        "generated-code shape; cross-round batch A phenomenon, first instantiated in KPG (batch D)",
        "batchD executed (suppressed-event re-fire); batchA FEN-SET-STALE-FLAGS record", "", ""),
    "FEN-KPG-INIT2-SUPPRESSED": _c("missing channel (bad keySize via initialize(int,SecureRandom))",
        "jca-inherited, unregistered", "batchD executed FN+FP pair", "", ""),
    "FEN-KPG-INITERROR-PLACEMENT": _c("repair residual (immediate->delayed conversion)",
        "gh101 form (repair residual); gen-unreachability consequence unregistered",
        "batchD D7a (FP at gen) + D7b (accepted double-Inits FN + GENERATED_KEY_PAIR granted)",
        "", "Beta PASS stands scoped to the correction route (§2.3)"),
    "FEN-SET-FIRSTCALL-DISJUNCT": _c("toolchain: dexlib2 first-call disjunct drop",
        "toolchain (WrapperEmitter.findFirstCall), jar-robust; also textually present in batch B CIS(:28)/COS(:27) — routed to global phase (batchD §6.7), batch B not reopened",
        "batchB source-verified + measured; batchD DX-KPG-2 executed (genKeyPair unwoven)",
        "ART half; CIS/COS dexlib2 half re-measure (host-executable)", ""),
    "FEN-SET-VARARGS-ARGS-IGNORED": _c("toolchain: dexlib2 ignores args() narrowing under trailing ..",
        "toolchain (dexlib2), outside both spec sets, jar-robust",
        "batchC measured (KMF/TMF); batchD DX-SRD-1 executed FP on the correct call; REF-D-04 sweep",
        "ART half", "SRD g2/g4 instances confirmed (halves disagree in opposite directions on one spec)"),
    "FEN-SET-NESTED-TYPE-DESCRIPTOR": _c("toolchain: nested-type descriptor unweaving",
        "toolchain (dexlib2)", "batchC measured (KST)", "ART half", ""),
    "FEN-SET-DECLARED-ONLY": _c("toolchain: declared-only member index (inherited members unwoven)",
        "toolchain (dexlib2)", "batchD measured (SRD next3/ints dead on device path)", "ART half", ""),
    "FEN-SET-FAIL-OPEN": _c("fail-open (exit 0 masking generator/pipeline defects)",
        "toolchain (generators); shapes: parser tolerance (pilot/A), symbol fail-open (pilot GCM), exit-0-with-error, stray paren (C p1), non-compiling artifact (KGN), probes P1/P2/P3 (D)",
        "pilot GAMA-GCM-01/BETA-SET-04; batchA parser/symbol claims; batchC KGN compile probe (exit 1 vs generator exit 0); batchD P1/P2/P3 all exit 0",
        "gate the pipeline on artifact inspection, not exit codes (batchD §6.4)",
        "D-batchC-1: counted at §4's letter (critica) at set level; pilot/A/B round records stand at their resolved severities"),
    "FEN-STREAMS-MONITOR-GLOBAL": _c("monitor-global (parameterless spec)",
        "jca-inherited (jca CIS/COS also parameterless); batch A HMC family, now parameterless",
        "batchB J2a/J2c executed FP cascade on every 2nd legal stream", "", ""),
    "FEN-SET-GENCIPHER-EXTRA": _c("extra-oracle predicate (gh101-introduced)",
        "gh101-introduced (task 5.1, registered with the misstated api30 oracle); no api30 rule REQUIRES generatedCipher",
        "batchB J2b executed FP; api30 CipherInputStream.cryptsl has ENSURES cipheredInputStream only (judge/consolidator-verified)",
        "researcher scope reduction or removal", ""),
    "FEN-COS-FLUSH": _c("event outside the rule's alphabet",
        "jca-inherited (jca:19,23)", "batchB J2c executed FN and FP", "", ""),
    "FEN-KPR-CO-OPCIONAL": _c("ORDER divergence (co? made mandatory)",
        "jca-inherited (jca:41 same ere), unregistered",
        "batchB J2d executed FP on the canonical JCA route; H-KPR-1 historical link (668 lines) INCONCLUSIVE pending replay",
        "H-KPR-1 replay battery (GAMA-KPR-06)", "the 1-FP-per-pair-access toll edge (KPG->KeyPairSpec->SIG delivery)"),
    "FEN-KPR-C1-SLICE-VAZIO": _c("empty-slice broadcast (unbound returning)",
        "jca-inherited (jca:23 same unbound returning); the gh101-repaired defect class, live and unregistered",
        "batchB J2e executed cross-instance contamination", "", ""),
    "FEN-SKY-GATE-SUPRESSAO": _c("extra-oracle condition gate (suppression)",
        "jca-inherited (jca/SecretKeySpec.mop:25 same gate)",
        "batchB J2g executed ENSURES starvation", "researcher scope reduction", ""),
    "FEN-SKY-SEM-CANAL": _c("missing diagnostic channel",
        "jca-inherited (twin also channel-less)",
        "batchB J2g executed: two realizable violations, zero records", "", ""),
    "FEN-SKS-SURROGATE": _c("surrogate constant without equivalence proof",
        "constant predates the change (registered surrogate preparedKeyMaterial->RANDOMIZED)",
        "batchA ALFA-SKS-03 (reader side); batchB writer side (SKY)", "researcher scope reduction", ""),
    "FEN-PBK-SENHA-EXTRA": _c("extra-oracle requirement (randomized[password])",
        "jca-inherited (jca:38,56), unregistered",
        "batchB J2h executed FP on the canonical PBE use + ENSURES starvation", "", ""),
    "FEN-PBK-RESIDUO": _c("pairing (delayed residue, D-S10 class)",
        "structural (conditions gate transitions in both sets); delayed form exposed by the gh101 star-prefix repair",
        "batchB J2h executed spurious fail at the rule's own mandatory cP", "", ""),
    "FEN-SKY-ZERO-CAPTURA": _c("toolchain: whole spec inert on production dexlib2",
        "toolchain (dexlib2, interface-with-no-declared-methods)",
        "batchB measured on the production pipeline; three mechanisms judge-verified",
        "ajc half INCONCLUSIVE (ALFA-SKY-07)", ""),
    "FEN-C-REMOVE-CASCADE": _c("extra-oracle revocation (@fail removes; zero NEGATES in rules)",
        "revocation semantics inherited; 2-arg remove form is gh101 (replacing whole-set remove — precision verified)",
        "batchC S10/S11 executed chain FP (KMF/TMF; pattern KGN/KST)", "researcher scope reduction", ""),
    "FEN-KST-MONITOR-GLOBAL": _c("monitor-global (parameter declared, never bound)",
        "jca-inherited (twin binds k too); new sub-shape: census-invisible",
        "batchC S6 executed: 5 spurious + wrong-object identity", "", ""),
    "FEN-KST-ERASURE": _c("composition (global monitor x remove semantics)",
        "composition, inherited mechanism (chains into KMF/TMF/SSL)",
        "batchC S7 executed", "", ""),
    "FEN-KST-G2-OMITIDA": _c("capture-omission", "jca-inherited, unregistered",
        "batchC S8 executed chain FP", "", ""),
    "FEN-SSL-ENGINE-VOID": _c("dead events (both weave halves)",
        "jca-inherited byte-for-byte, registered nowhere",
        "batchC measured both halves dead; GENERATE_SSL_ENGINE writer unreachable", "", ""),
    "FEN-SSL-ENGINE-LOOP": _c("over-acceptance FN", "jca-inherited",
        "batchC S15b executed FN", "", ""),
    "FEN-SSL-GETDEFAULT-OMITIDA": _c("FORBIDDEN clause omitted", "jca-inherited",
        "batchC record (no register)", "", ""),
    "FEN-SSL-RANDOMIZED-EXTRA": _c("extra-oracle read (rule binds _)",
        "gh101-introduced (task 3.2 read)",
        "batchC S12 executed FP; api30 SSLContext.cryptsl Init binds third arg as _ and REQUIRES randomized[sr] with sr unbound (oracle oddity)",
        "researcher scope reduction", ""),
    "FEN-C-WHITELIST-EXTRA": _c("whitelist folding/aliases vs raw literal sets",
        "aliases/folding jca-inherited; base lists gh99; registered as aliases/variants — registered != approved",
        "batchC S15a/S17 executed FNs; batchD MDG 6 resolvable FN witnesses (critical) + MAC monitor-level FN executed D5 (major-pending)",
        "Android-BC probe (decides MAC/KGN return to critica)", ""),
    "FEN-KGN-KEYSIZE-OMITIDA": _c("constraint omission", "jca-inherited, unregistered",
        "batchC S16 executed FN", "", ""),
    "FEN-KGN-NAOCOMPILA": _c("fail-open (artifact does not compile standalone)",
        "jca-inherited missing import, fail-open, unregistered",
        "batchC compile probe (javac exit 1; generators exit 0); masked by the 23-spec merge route",
        "", "critica per D-batchC-1 (REF-D-01)"),
    "FEN-C-DELAYED": _c("pairing (delayed via reset semantics)", "structural, inherited",
        "batchC S1b/S2b executed", "", ""),
    "FEN-D-PREPAREDHMAC-GUARANTEED-FIRE": _c("guaranteed-fire predicate edge",
        "composition: faithful batch D read (MacSpec.mop:99) x batch A unwritable writer (HMC platform-vacuous on android-30)",
        "batchD MAC-T8 executed (every parameterized Mac.init FPs)",
        "", "set-level edge; blocks G7 at set level"),
    "FEN-D-KEYPAIR-EDGE": _c("FP-toll delivery edge (KPG->KeyPairSpec->SIG)",
        "inherited (KeyPairSpec c1 — batch B REPROVADA shape, writer side)",
        "batchD CHAIN-T1 executed: private-key mark delivered at 1 KeyPairSpec FP per pair access (no starvation)",
        "", ""),
    "FEN-SIG-VERIFIED-WRONGSLOT": _c("wrong-slot predicate write",
        "jca-inherited; rule says verified[sign]",
        "batchD D8 executed (VERIFIED[Boolean.TRUE]=true; VERIFIED[signBytes]=false)",
        "reader-appearance watch", "latent (no reader in the set) — major per GENERATEDKEY-2A-CASA precedent"),
    "FEN-D-REGISTER-ANCHOR-DRIFT": _c("register anchor (1.5.2 invariance premise falsified)",
        "gh101 register premise ('REQUIRES/ENSURES do not vary') falsified by >=3 api30 rows: Mac generatedKey; SecureRandom randInt/randIntInRange; Signature verified",
        "batchD judge re-read README:148-153 + row checks against raw rules",
        "researcher: anchor column or api30 re-derivation", "the set phase must not consume 'present' verdicts without an anchor check"),
    "FEN-SET-GENERATEDKEY-2A-CASA": _c("second predicate slot dropped (unary store)",
        "unregistered; store unary, readers pair-blind",
        "pilot ALFA-CIP-07; batchA ALFA-SKS-05; batchB PBK speccedKey slot; batchC writer side",
        "", "cross-round family: generatedKey[key, alg]-style second slots"),
    "FEN-DHG-SUPRESSAO": _c("extra-oracle condition (suppression) + downstream FP",
        "unregistered (extra condition exponentSize<primeSize)",
        "batchA J2 executed FP chain into KeyPairGeneratorSpec (preparedDH denied on the suppressed path)",
        "", ""),
    "FEN-HMC-MONITOR-GLOBAL": _c("monitor-global (spec parameter never bound)",
        "predates gh101 (HMC byte-identical to frozen jca copy)",
        "batchA J3 executed FP on legal trace (JVM harness; realizable wherever the class exists)",
        "", "platform absence does not excuse: app-bundled JSR-105 on Android"),
    "FEN-HMC-CLASSE-AUSENTE": _c("oracle bias (rule models class android-30 does not publish)",
        "oracle-inherited (api30 generation models availability, not recommendation)",
        "batchA ALFA-HMC-02/BETA-HMC-02; oracle-bias register created by the round",
        "researcher countersignature of the register (REF-B-08)", ""),
    "FEN-PBE-C2-GAP": _c("missing violating carrier (terminal FN)",
        "jca-inherited, unregistered",
        "batchA executed terminal FN (3-arg ctor misuse totally silent)", "", ""),
    "FEN-SKS-WHITELIST": _c("extra-oracle whitelist",
        "registered != approved; no scope reduction on file",
        "batchA executed FP against the raw oracle", "researcher scope reduction", ""),
    "FEN-SKS-REQUIRES-4ARG": _c("REQUIRES dropped on a whole path (predicate laundering)",
        "unregistered", "batchA executed FN + predicate laundering", "", ""),
    "FEN-SET-DEDUPE": _c("diagnostics (dedupe collides clauses / masks multiplicity)",
        "pipeline (ErrorCollector/dedupe key)",
        "pilot GAMA-CIP-04; batchB J2f; batchC 3-clause worst case executed; batchD re-executed (per-site amplification / per-line masking)",
        "", ""),
    "FEN-SET-FAIL-UNKNOWN": _c("diagnostics (expecting=unknown on every sequencing record)",
        "generator (@fail handlers built without expected-set)",
        "pilot GAMA-CIP-01; batchB executed throughout; batchC S1-S11; batchD everywhere",
        "", "G9-decisive in every round"),
    "FEN-SET-STATIC-JCA-DEFAULT": _c("static path resolves jca/no api30 silently",
        "pipeline (static analysis wiring)",
        "pilot GAMA-SET-01/03; batchB FEN-SET-JCA-DIR-DEFAULT; batchD FEN-SET-STATIC-JCA-DEFAULT",
        "G12: verify nominal jca_android resolves to the right directory", ""),
    "FEN-SET-FLAGS-OBSOLETAS": _c("toolchain flags obsolete", "toolchain",
        "pilot BETA-CIP-06/GAMA-CIP-08; batchA x3", "", ""),
    "FEN-SET-STATIC-DEAD-TARGETS": _c("static/dynamic contradiction (6 static-listed dynamically-dead rows)",
        "pipeline", "batchD measured", "G12 must-close", ""),
    "FEN-MDG-LABEL-STALE": _c("diagnostics (message names 3-entry set while enforcing 9)",
        "spec (label built from a stale set)", "batchD D6 output literal", "", ""),
    "FEN-D-ARITH-OMITIDA": _c("arithmetic constraints untranslated",
        "unregistered (MAC offset<len, length(output1)>outOffset; MDG pre_len>pre_off, len>off)",
        "batchD source reads (rule :73-75 vs spec)", "", ""),
    "FEN-SRD-EXTRA-ALPHABET": _c("extra-oracle events occupy automaton positions",
        "jca-inherited (nextInt/ints as events; api30 ne is protected next(int), uncallable)",
        "batchD ALFA-SRD-06; boxed-Integer cache marks (D-S13 family)",
        "researcher: protected-ne unimplementability countersignature", ""),
    "FEN-D-S13-BYTEBUFFER": _c("registered limitation with measured witness",
        "registered (D-S13)", "batchD measured ByteBuffer FN", "", "FAIL/LIMITAÇÃO per §2.1 rule"),
    "FEN-D-CACHE-BOXING": _c("boxed-primitive cache marks", "registered (D-S13 family)",
        "batchD measured", "", ""),
    "FEN-C-ACCEPT-END": _c("complete rule words end outside match (table-level)",
        "structural", "batchC/batchD table-level; no realizable FP/FN found", "", "minor"),
    "FEN-IVP-UNKNOWN": _c("diagnostics (unknown on the only violation channel)",
        "generator", "batchA GAMA-IVP-02 (judge-verified)", "", "G9-decisive for IVP"),
    "FEN-PBE-MSG-1000": _c("diagnostics (false '1000' message, off by 10x; miscategorized)",
        "jca-inherited", "batchA GAMA-PBE-02 + batchB measured twin", "", ""),
    "FEN-KPR-MATCH-NULL": _c("@match marks null (generator-mechanism half)",
        "generator shape", "batchB executed", "", ""),
    "FEN-SET-CTOR-INVISIVEL-ESTATICA": _c("static path blind to constructors",
        "pipeline", "batchA GAMA-SET-09; batchB GAMA claim", "G12", ""),
    "FEN-SET-TIPO-ESTATICO": _c("unregistered scope reduction (static type filter)",
        "pipeline", "batchB record", "G12", ""),
    "FEN-SET-GERADOR-SILENCIO": _c("silent generator acceptances (census blind spots)",
        "toolchain (generators)", "batchB BETA-SET-05/06 + ALFA-SET-05/07",
        "", "family-adjacent to FEN-SET-FAIL-OPEN; NOT counted in the D-batchC-1 reconciliation (documented)"),
    "FEN-SET-FAIL-MORTO": _c("dead @fail handlers", "spec/generator",
        "pilot GCM (@fail unreachable); batchA x4+ALFA-SET-04 (HMC)", "",
        "distinct from fail-open (dead code, not masked failure)"),
    "FEN-TMF-GTM-INVISIVEL": _c("platform-masked FN", "platform", "batchC record (register the limitation)", "", "minor"),
    "FEN-KST-ENTRIES-OMITIDAS": _c("oracle-reading pendency", "oracle semantics of declared-but-unordered events",
        "batchC REF-D-03: ALFA-KST-04/GAMA-KST-05 INCONCLUSIVE", "CogniCrypt typestate construction at source, or researcher ruling", ""),
    "FEN-SET-DESIGN-SPLIT": _c("register-internal false ground",
        "gh101 register ('two philosophies' ground factually false — GAMA-SET-22)",
        "batchC record", "", ""),
    "FEN-MAC-G2-EXTRA": _c("extra-oracle 2-arg capture (oracle's own g1=g2 anomaly)",
        "oracle-authoring anomaly (byte-duplicate 1-arg Gets)",
        "batchD record", "researcher countersignature (Mac g1=g2)", ""),
    "FEN-SET-STATIC-JCA-DEFAULT ": _c("", "", ""),  # guard against trailing-space typos
}
GRAPH_ANN = {}  # populated below (per (file,constant,op) unless a per-line entry exists)

def _g(kind, api30, live, adj):
    return {"kind": kind, "api30": api30, "live": live, "adj": adj}

GRAPH_ANN.update({
    # ---- GENERATED_CIPHER
    ("CipherInputStreamSpec.mop", "GENERATED_CIPHER", "read"): _g(
        "object(Cipher)", "extra-oracle (api30 CipherInputStream.cryptsl has no REQUIRES; ENSURES cipheredInputStream only)",
        "live (body-report)", "FEN-SET-GENCIPHER-EXTRA critical, executed J2b (batchB); gh101-introduced"),
    ("CipherOutputStreamSpec.mop", "GENERATED_CIPHER", "read"): _g(
        "object(Cipher)", "extra-oracle (same)", "live", "FEN-SET-GENCIPHER-EXTRA critical (batchB)"),
    ("CipherSpec.mop", "GENERATED_CIPHER", "write"): _g(
        "object(Cipher)", "extra-oracle predicate (no api30 rule names generatedCipher); write itself conditional on key-mark disjunction",
        "live", "feeds the CIS/COS gate; pilot ALFA-CIP-20 (extra-oráculo, minor) + batchB FEN-SET-GENCIPHER-EXTRA"),
    # ---- RANDOMIZED readers
    ("CipherSpec.mop", 64): _g("object(SecureRandom)", "rule-grounded (Cipher REQUIRES randomized[random])",
        "live (body-report, helper)", "sound side of the D3 split (object-level); pilot G7 'randomized fiel'"),
    ("KeyGeneratorSpec.mop", 34): _g("object(SecureRandom)", "rule-grounded (KeyGenerator REQUIRES randomized[random])",
        "live (helper validate)", "sound side of the D3 split"),
    ("SSLContextSpec.mop", 82): _g("object(SecureRandom)",
        "extra-oracle vs api30 (SSLContext.cryptsl Init binds 3rd arg as _; REQUIRES randomized[sr] with sr unbound — oracle oddity)",
        "live (body-report)", "FEN-SSL-RANDOMIZED-EXTRA critical, executed S12 (batchC); gh101-introduced"),
    ("IvParameterSpec.mop", "RANDOMIZED", "read"): _g("material(byte[] iv)",
        "rule-grounded (IvParameterSpec REQUIRES randomized[iv])",
        "live (condition-split c1/c2 safe vs c3/c4 violating)",
        "unsound producer side (FEN-SRD-RANDOMIZED-OVERGRANT, D3): satisfiable by rejected randomness — FN direction; batchA bounds equivalence PASS unaffected"),
    ("GCMParameterSpecSpec.mop", "RANDOMIZED", "read"): _g("material(byte[] src)",
        "rule-grounded (GCMParameterSpec REQUIRES randomized[src])",
        "live (suppression mechanics INCORRETA — pilot ALFA-GCM-03/04)",
        "pilot critical (suppressed report) + overgrant FN direction (D3)"),
    ("PBEParameterSpecSpec.mop", "RANDOMIZED", "read"): _g("material(byte[] salt)",
        "rule-grounded (REQUIRES randomized[salt])", "live; c2-gap: 3-arg ctor has no violating carrier",
        "FEN-PBE-C2-GAP critical (batchA) + overgrant FN direction (D3)"),
    ("PBEKeySpecSpec.mop", 43): _g("material(char[] password)",
        "extra-oracle (rule REQUIRES randomized[salt] only)", "live (c1 body + err2 condition)",
        "FEN-PBK-SENHA-EXTRA critical, executed J2h (batchB)"),
    ("PBEKeySpecSpec.mop", 61): _g("material(char[] password)", "extra-oracle (same)", "live (condition-gate)",
        "FEN-PBK-SENHA-EXTRA"),
    ("PBEKeySpecSpec.mop", 44): _g("material(byte[] salt)", "rule-grounded", "live",
        "randomized[salt] read + NEGATES scope correct (ALFA-PBK-10 PASS); overgrant FN direction (D3)"),
    ("PBEKeySpecSpec.mop", 69): _g("material(byte[] salt)", "rule-grounded", "live (condition-gate)", "see :44"),
    ("SecretKeySpecSpec.mop", "RANDOMIZED", "read"): _g("material(byte[] keyMaterial)",
        "surrogate (preparedKeyMaterial carried as RANDOMIZED; no equivalence proof)",
        "live", "FEN-SKS-SURROGATE critical (batchA reader side; batchB writer side); overgrant FN direction (D3)"),
    ("SecureRandomSpec.mop", "RANDOMIZED", "read"): _g("material(byte[] seed)",
        "rule-grounded (REQUIRES randomized[seed]); randomized[lSeed] inexpressible (registered)",
        "live (condition-splits)", "material side of the split; setSeed2/c2 instances"),
    ("RandomStringPassword.mop", "RANDOMIZED", "read"): _g("material(String/char[] taint chain)",
        "no oracle (spec has no CrySL counterpart; researcher-excluded from audit scope)",
        "live", "propagation chain only"),
    # ---- RANDOMIZED writers
    ("SecureRandomSpec.mop", 106): _g("material(byte[] seed)", "rule-grounded (ENSURES randomized[genSeed])",
        "live", "unconditional — overgrant family (D3)"),
    ("SecureRandomSpec.mop", 114): _g("material(int randIntInRange)",
        "register row 'present' is 1.5.2-anchored; api30 ne is protected next(int) — anchor drift",
        "live", "FEN-D-REGISTER-ANCHOR-DRIFT + FEN-SRD-EXTRA-ALPHABET; Integer-cache marks (FEN-D-CACHE-BOXING)"),
    ("SecureRandomSpec.mop", 121): _g("material(byte[] bytes)", "rule-grounded (ENSURES randomized of nB)",
        "live", "FEN-SRD-RANDOMIZED-OVERGRANT critical: mark granted from violating/unsafe instances (D3)"),
    ("SecureRandomSpec.mop", 127): _g("material(int randInt)", "extra-alphabet (see :114)", "live",
        "FEN-SRD-EXTRA-ALPHABET; cache marks"),
    ("SecureRandomSpec.mop", 133): _g("material(IntStream)", "extra-alphabet", "dead on device path (declared-only)",
        "FEN-SET-DECLARED-ONLY (batchD)"),
    ("SecureRandomSpec.mop", 198): _g("object(SecureRandom sr)", "rule-grounded (ENSURES randomized[this])",
        "live (@match1 — constraint-coupled)", "sound object-level writer (batchD PASS half; decides pilot/A/B residuals)"),
    ("SecretKeySpec.mop", 26): _g("material(byte[] key)",
        "surrogate write (ENSURES preparedKeyMaterial carried as RANDOMIZED)",
        "starved (gated by extra-oracle GENERATED_KEY condition at :25)",
        "FEN-SKY-GATE-SUPRESSAO critical, executed J2g (batchB)"),
    ("RandomStringPassword.mop", "RANDOMIZED", "write"): _g("material(String/char[])",
        "no oracle", "live", "taint propagation"),
    # ---- GENERATED_KEY
    ("KeyGeneratorSpec.mop", 114): _g("object(SecretKey)", "rule-grounded (ENSURES generatedKey[key]); second CrySL slot dropped (store unary)",
        "live", "FEN-SET-GENERATEDKEY-2A-CASA family"),
    ("KeyGeneratorSpec.mop", 124): _g("object(SecretKey)", "extra-oracle revocation (rule has zero NEGATES)",
        "live (@fail)", "FEN-C-REMOVE-CASCADE pattern (batchC)"),
    ("SecretKeySpecSpec.mop", 81): _g("object(SecretKeySpec)", "rule-grounded (ENSURES generatedKey[this]); second slot dropped",
        "live", "FEN-SET-GENERATEDKEY-2A-CASA (ALFA-SKS-05, batchA)"),
    ("KeyStoreSpec.mop", 71): _g("object(Key)", "rule-grounded (three-key write — batchC FIDELIDADE highlight)",
        "live", "gk1 body"),
    ("CipherSpec.mop", "GENERATED_KEY", "read"): _g("object(Key)", "rule-grounded (REQUIRES generatedKey[key])",
        "live (init4 disjunct under condition — pilot suppression INCORRETA)",
        "pilot ALFA-CIP-08 critical (condition suppression); second-slot omission ALFA-CIP-07"),
    ("MacSpec.mop", "GENERATED_KEY", "read"): _g("object(Key)",
        "extra-oracle (api30 Mac.cryptsl REQUIRES has no generatedKey clause — judge-read)",
        "live (condition-gate — suppressing)", "FEN-MAC-KEYGATE-EXTRA critical, executed D4 (batchD)"),
    ("SecretKeySpec.mop", 25): _g("object(SecretKey)", "extra-oracle (SecretKey rule has no REQUIRES)",
        "live (condition-gate)", "FEN-SKY-GATE-SUPRESSAO critical (batchB)"),
    ("SecretKeySpec.mop", 41): _g("object(SecretKey)", "rule-grounded (NEGATES generatedKey[this], per-object)",
        "live (d event body)", "batchB PASS (SKY NEGATES per-object)"),
    ("KeyStoreSpec.mop", 86): _g("object(Key)", "extra-oracle revocation (@fail; rule has zero NEGATES)",
        "live (@fail)", "FEN-C-REMOVE-CASCADE pattern + FEN-KST-ERASURE composition (S7)"),
    # ---- GENERATED_PUBLIC/PRIVATE
    ("KeyPairSpec.mop", 47): _g("object(PublicKey)", "rule-grounded (ENSURES generatedPubkey[retPublicKey])",
        "live", "wrong-constant of the baseline (:38 GENERATED_PUBLIC_KEY over private key) REPAIRED in the frozen spec (:58 writes GENERATED_PRIVATE_KEY) — baseline drift example"),
    ("KeyPairSpec.mop", 58): _g("object(PrivateKey)", "rule-grounded", "live",
        "delivery costs 1 KeyPairSpec FP per pair access (FEN-D-KEYPAIR-EDGE, CHAIN-T1)"),
    ("KeyPairSpec.mop", 32): _g("object(PublicKey)", "rule-grounded (REQUIRES generatedPubkey)", "live (null-guarded, minor FN)",
        "empty-slice broadcast context (FEN-KPR-C1-SLICE-VAZIO)"),
    ("KeyPairSpec.mop", 36): _g("object(PrivateKey)", "rule-grounded", "live (null-guarded)", "same"),
    ("SignatureSpec.mop", "GENERATED_PRIVATE_KEY", "read"): _g("object(PrivateKey)",
        "rule-grounded (REQUIRES generatedPrivkey[privateKey])", "live (body-report — the G9-clean design)",
        "batchD SIG G4 PASS (SIG-T4: 1 specific, 0 spurious)"),
    ("SignatureSpec.mop", "GENERATED_PUBLIC_KEY", "read"): _g("object(PublicKey)", "rule-grounded", "live", "same"),
    ("KeyStoreSpec.mop", 77): _g("object(Key)", "rule-grounded", "live", "three-key write"),
    ("KeyStoreSpec.mop", 78): _g("object(Key)", "rule-grounded", "live", "three-key write"),
    ("KeyStoreSpec.mop", 87): _g("object(Key)", "extra-oracle revocation", "live (@fail)", "FEN-KST-ERASURE"),
    ("KeyStoreSpec.mop", 88): _g("object(Key)", "extra-oracle revocation", "live (@fail)", "FEN-KST-ERASURE"),
    ("CipherSpec.mop", "GENERATED_PUBLIC_KEY", "read"): _g("object(Key)", "rule-grounded (key-kind union)", "live", "init disjunction"),
    ("CipherSpec.mop", "GENERATED_PRIVATE_KEY", "read"): _g("object(Key)", "rule-grounded", "live", "init disjunction"),
    # ---- KEY_PAIR / STORE / MANAGERS
    ("KeyPairGeneratorSpec.mop", 126): _g("object(KeyPair)", "rule-grounded (ENSURES generatedKeypair[keyPair])",
        "writer-only (no reader in set; terminal by design, registered)", "batchD ALFA-KPG-09 LIMITAÇÃO PASS; D7b delivery measured"),
    ("KeyPairGeneratorSpec.mop", 139): _g("object(KeyPair)", "extra-oracle revocation", "inert (writer-only constant)", "batchD G7 note"),
    ("KeyPairSpec.mop", 41): _g("object(KeyPair)", "rule-grounded (ENSURES generatedKeypair[this])", "writer-only", "baseline said missing — repaired"),
    ("KeyStoreSpec.mop", 48): _g("object(KeyStore)", "rule-grounded (ENSURES generatedKeyStore[this])", "live", "read by KMF:76/TMF:79"),
    ("KeyStoreSpec.mop", 89): _g("object(KeyStore)", "extra-oracle revocation", "live (@fail)", "FEN-KST-ERASURE chain into KMF/TMF/SSL"),
    ("KeyManagerFactorySpec.mop", 76): _g("object(KeyStore)", "rule-grounded (REQUIRES generatedKeyStore[keyStore])", "live", "chain FP when KST erases (S10/S11)"),
    ("TrustManagerFactorySpec.mop", 79): _g("object(KeyStore)", "rule-grounded", "live", "same"),
    ("KeyManagerFactorySpec.mop", "GENERATED_KEY_MANAGERS", "write"): _g("object(KMF/KeyManager)",
        "rule-grounded (ENSURES generatedKeyManager[this] + generatedKeyManagers[keyManager])", "live", "read by SSL:74"),
    ("KeyManagerFactorySpec.mop", "GENERATED_KEY_MANAGERS", "remove"): _g("object", "extra-oracle revocation",
        "live (@fail)", "FEN-C-REMOVE-CASCADE executed S10 (batchC)"),
    ("SSLContextSpec.mop", 74): _g("object(KeyManager[])", "rule-grounded (REQUIRES generatedKeyManager[kms])", "live", ""),
    ("SSLContextSpec.mop", 78): _g("object(TrustManager[])", "rule-grounded (REQUIRES generatedTrustManager[tms])",
        "live", "reader-side correct (ALFA-TMF-06 PASS)"),
    ("TrustManagerFactorySpec.mop", 83): _g("object(TMF)", "rule-grounded (ENSURES generatedTrustManager[this]) under a two-constant split",
        "writer-no-reader (singular constant; SSL reads the plural)", "ALFA-TMF-06 DIVERGÊNCIA PASS; singular is dead-write"),
    ("TrustManagerFactorySpec.mop", 94): _g("object(TMF)", "same", "writer-no-reader", "same"),
    ("TrustManagerFactorySpec.mop", 109): _g("object(TrustManager)", "rule-grounded (ENSURES generatedTrustManagers[trustManager])",
        "live (read by SSL:78); gtm1 platform-masked FN (minor)", "FEN-TMF-GTM-INVISIVEL; baseline wrong-constant row (:65 GENERATED_KEY_MANAGERS) REPAIRED — baseline drift example"),
    ("TrustManagerFactorySpec.mop", "GENERATED_TRUST_MANAGER", "remove"): _g("object", "extra-oracle revocation", "live (@fail)", "FEN-C-REMOVE-CASCADE executed S11"),
    ("TrustManagerFactorySpec.mop", "GENERATED_TRUST_MANAGERS", "remove"): _g("object", "extra-oracle revocation", "live (@fail)", "same"),
    # ---- SSL outputs
    ("SSLContextSpec.mop", 86): _g("object(SSLContext)", "rule-grounded (ENSURES generatedSSLContext[this] after Init)",
        "writer-only (terminal in both anchors, registered)", ""),
    ("SSLContextSpec.mop", 92): _g("object(SSLEngine)", "rule-grounded (ENSURES generatedSSLEngine[eng])",
        "DEAD write — engine events dead on both weave halves", "FEN-SSL-ENGINE-VOID critical (batchC)"),
    # ---- MAC family
    ("MacSpec.mop", 99): _g("object(AlgorithmParameterSpec)", "rule-grounded (REQUIRES preparedHMAC[params])",
        "guaranteed-fire (writer platform-vacuous on android-30)",
        "FEN-D-PREPAREDHMAC-GUARANTEED-FIRE critical, executed MAC-T8 (batchD)"),
    ("HMACParameterSpecSpec.mop", 35): _g("object(HMACParameterSpec)", "rule-grounded (ENSURES preparedHMAC[this])",
        "unwritable on android-30 (class not published; monitor-global defect besides)",
        "FEN-HMC-CLASSE-AUSENTE (oracle bias) + FEN-HMC-MONITOR-GLOBAL (batchA)"),
    ("MacSpec.mop", "MACED", "write"): _g("material(input slices + direct doFinal input)",
        "rule-grounded (macced[_, D] second place; deferred marking at doFinal — faithful design)",
        "live (helper markAsMaced, called from doFinal events)", "batchD PASS highlight (!macced projection)"),
    ("CipherSpec.mop", 102): _g("material(plainText)", "rule-grounded (REQUIRES !macced[_])", "live (negated read)", ""),
    ("MacSpec.mop", "GENERATED_MAC", "write"): _g("material(byte[] output)",
        "rule-grounded (ENSURES macced[output])", "writer-no-reader (no spec reads GENERATED_MAC)",
        "D-S13 residues measured/registered (batchD G7 row)"),
    ("MacSpec.mop", 195): _g("material", "extra-oracle revocation", "live (@fail)", ""),
    ("MacSpec.mop", "ENCRYPTED", "read"): _g("material(byte[] output)", "rule-grounded (REQUIRES !encrypted[output1/2,_])",
        "live (negated reads in f1/f2/f3 bodies)", "second slot of encrypted[_,_] dropped (unary store)"),
    ("CipherSpec.mop", "ENCRYPTED", "write"): _g("material(byte[]/ByteBuffer ciphertext)",
        "rule-grounded (ENSURES encrypted[...])", "live (read by MacSpec)",
        "projection registered (pilot ALFA-CIP-19: 2nd-slot FN latent)"),
    ("CipherSpec.mop", 238): _g("material(byte[] wrappedKeyBytes)", "rule-grounded (ENSURES wrappedKey)",
        "writer-no-reader (dead effect)", "pilot ALFA-CIP-21 LIMITAÇÃO (registered)"),
    # ---- prepared* params
    ("DHGenParameterSpecSpec.mop", 36): _g("object(DHGenParameterSpec)", "rule-grounded (ENSURES preparedDH[this])",
        "write suppressed on the extra-oracle condition path", "FEN-DHG-SUPRESSAO critical (batchA J2: downstream KPG FP)"),
    ("KeyPairGeneratorSpec.mop", 96): _g("object(AlgorithmParameterSpec)", "rule-grounded (REQUIRES preparedDH[params])",
        "live (body-report)", "downstream FP when DHG suppresses (J2); preparedRSA/DSA/EC capability-absent (registered, D-S14)"),
    ("KeyPairGeneratorSpec.mop", 107): _g("object", "rule-grounded", "live", "same"),
    ("IvParameterSpec.mop", 74): _g("object(IvParameterSpec)", "rule-grounded (ENSURES preparedIV[this])", "live (@match)", "read by CipherSpec:84"),
    ("CipherSpec.mop", 84): _g("object(AlgorithmParameterSpec)", "rule-grounded (REQUIRES preparedIV[paramSpec])", "live", ""),
    ("GCMParameterSpecSpec.mop", 56): _g("object(GCMParameterSpec)", "rule-grounded (ENSURES preparedGCM[this])", "live (@match)", "read by CipherSpec:89"),
    ("CipherSpec.mop", 89): _g("object", "rule-grounded (REQUIRES preparedGCM[paramSpec])", "live", ""),
    ("PBEParameterSpecSpec.mop", 66): _g("object(PBEParameterSpec)", "rule-grounded (ENSURES preparedPBE[this])",
        "writer-no-reader (registered LIMITAÇÃO — blocks total adherence)", "batchA G7 PASS with LIMITAÇÃO"),
    # ---- SPECCED_KEY / SIGNED / VERIFIED / DIGESTED
    ("PBEKeySpecSpec.mop", 47): _g("object(PBEKeySpec)", "rule-grounded (ENSURES speccedKey[this, keylength]); second slot OMITIDA (major)",
        "writer-no-reader (registered)", "FEN-SET-GENERATEDKEY-2A-CASA family (batchB)"),
    ("PBEKeySpecSpec.mop", 77): _g("object(PBEKeySpec)", "rule-grounded (NEGATES speccedKey[this], per-object)", "live (c2 body)", "batchB PASS"),
    ("SecretKeySpecSpec.mop", 82): _g("object(SecretKeySpec)", "rule-grounded (ENSURES speccedKey[this])",
        "writer-no-reader (registered)", ""),
    ("SignatureSpec.mop", 122): _g("material(byte[] output)", "rule-grounded (ENSURES signed[out,...] — second slot dropped besides)",
        "DEAD — event s1 can never match (byte-typed sign pointcut vs byte[] member); no reader either",
        "FEN-SIG-SIGN-VOID critical (batchD, javap + capture matrix)"),
    ("SignatureSpec.mop", 130): _g("material", "rule-grounded", "DEAD (same; int member)", "FEN-SIG-SIGN-VOID"),
    ("SignatureSpec.mop", 137): _g("WRONG OBJECT (boxed Boolean return; rule says verified[sign] = the signature bytes)",
        "rule-grounded predicate, wrong slot", "latent (no reader in set)",
        "FEN-SIG-VERIFIED-WRONGSLOT major, executed D8 (batchD)"),
    ("SignatureSpec.mop", 145): _g("WRONG OBJECT (same)", "same", "latent", "FEN-SIG-VERIFIED-WRONGSLOT"),
    ("MessageDigestSpec.mop", "DIGESTED", "write"): _g("material(byte[] out)", "rule-grounded (ENSURES digested[output])",
        "writer-only (terminal in both anchors, registered deliberate)", "batchD ALFA-MDG-09 LIMITAÇÃO PASS"),
})

if __name__ == "__main__":
    sys.exit(main())
