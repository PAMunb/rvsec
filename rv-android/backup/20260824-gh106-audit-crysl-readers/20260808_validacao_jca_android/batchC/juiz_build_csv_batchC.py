#!/usr/bin/env python3
"""Builds juiz_claims_resolvidos_batchC.csv from the three agent CSVs.

Appends: resolucao_juiz, classificacao_final, severidade_final,
fenomeno_id_final, justificativa_curta. Original columns preserved.

Rules applied: D-piloto-4 (judge does not re-assign claim->dimension),
D-batchA-1 (raw weighted sums are the record), D-batchB-1 (every FAIL row
carries fenomeno_id_final; build-time assert). FEN unifications and every
overturn/harmonization are justified in juiz_sintese_batchC.md §2.

Judge evidence tags: S1..S18 = juiz_driveC_rep1.txt (J2-C, 3 reps
sha-identical d3ac5f70…); W = juiz_walk_batchC_output.txt (J1-C, 22/22);
KGNPROBE = juiz_kgn_compile_probe.txt (javac exit 1 on frozen artifact);
IDPROBE = juiz_probe_identity_alias_batchC.txt (refutation round).

REV. 2 (refutation round, 2026-08-09) — accepted objections applied:
  REF-D-01: ALFA-KGN-09, GAMA-KGN-01, BETA-SET-04 major -> critica
            (pre_registro §4 lists fail-open among the Critica triggers).
  REF-D-02: ALFA-KGN-04, GAMA-KGN-03 critica -> major-pending (alias FN trace
            not shown realizable on any measured platform — IDPROBE; the
            Android-BC probe is the named pendency; SSL half untouched).
  REF-D-03: ALFA-KST-04, GAMA-KST-05 FAIL -> INCONCLUSIVE (pre_registro §3
            bindings INCONCLUSIVE criterion: "nao determinavel por leitura +
            execucao" — the oracle semantics of declared-but-unordered events
            decides both halves; upstream grammar is syntax-only).
  REF-D-06: BETA-KGN-04 overturn justification upgraded to executed evidence
            (IDPROBE + refuter probe).
Rev. 1 asserts were (55, 73, 6) and 53 criticals; rev. 2: (55, 71, 8), 54.
"""
import csv, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------- FEN unification map (canonical id per synthesis §2.6) ----------
FEN_MAP = {
    "FEN-C-PAIRING-IMEDIATO": "FEN-C-CARRIER-SEQFAIL",
    "FEN-KGN-UNSAFE-RESIDUO": "FEN-C-CARRIER-SEQFAIL",
    "FEN-KMF-UNSAFE-RESIDUO": "FEN-C-CARRIER-SEQFAIL",
    "FEN-TMF-UNSAFE-RESIDUO": "FEN-C-CARRIER-SEQFAIL",
    "FEN-SSL-UNSAFE-RESIDUO": "FEN-C-CARRIER-SEQFAIL",
    "FEN-C-UNSAFE-2ARG": "FEN-C-GETS-INVISIVEL",
    "FEN-SSL-G2-PROVIDER-OMIT": "FEN-C-GETS-INVISIVEL",
    "FEN-KST-G2-2ARG-OMIT": "FEN-KST-G2-OMITIDA",
    "FEN-KST-GLOBAL": "FEN-KST-MONITOR-GLOBAL",
    "FEN-SSL-ENGINE-MORTO": "FEN-SSL-ENGINE-VOID",
    "FEN-SSL-ENGINE-DEAD": "FEN-SSL-ENGINE-VOID",
    "FEN-KGN-WHITELIST": "FEN-C-WHITELIST-EXTRA",
    "FEN-KGN-KEYSIZE-OMIT": "FEN-KGN-KEYSIZE-OMITIDA",
    "FEN-KGN-NOCOMPILE": "FEN-KGN-NAOCOMPILA",
}
# per-claim FEN remaps (judge assignment, D-batchB-1)
FEN_CLAIM = {
    "ALFA-SSL-05": "FEN-SSL-ENGINE-LOOP",   # cardinality unit, not the dead pointcut
    "GAMA-KST-04": "FEN-KST-G2-OMITIDA",    # the KST omission unit of the family
}

# ---------- position overturns ----------
OVERTURN = {
    "BETA-KGN-04": ("PASS", "DIVERGENCIA_EQUIVALENTE_COMPROVADA (envelope realizavel)", "-",
        "OVERTURN FAIL->PASS: g1+/g2+ words need one KeyGenerator returned by two getInstance "
        "calls; EXECUTED (REF-D-06): two getInstance calls return distinct references — judge "
        "IDPROBE and the refuter's probe agree (ALFA-KGN-11 same unit). FN unrealizable per "
        "reference identity; provider threat kept as note."),
    "GAMA-KGN-05": ("PASS", "DIVERGENCIA_EQUIVALENTE_COMPROVADA (por ordem de advice)", "-",
        "OVERTURN FAIL->PASS: equivalence holds on every realizable trace — g1-before-g3 order "
        "fixed in descriptor AND WrapperEmitter fires advices in descriptor order "
        "(WrapperEmitter.java:246-249, judge-verified); per-object indexing bars a 2nd getInstance "
        "on one monitor. Executed benign (kgn_b; judge S18a). Fragility recorded as threat, matching ALFA-KGN-08."),
    "BETA-SET-06": ("PASS", "FIDELIDADE_DEMONSTRADA (semantica do arquivo re-lida)", "-",
        "OVERTURN FAIL->PASS: data/gh101/README.md declares predicate_edges.csv the pre-repair "
        "baseline 'kept as authored' (judge re-read); rows 26/59/60/61/82/85 are that declared "
        "semantics — exactly the batch A BETA-SET-07 and batch B BETA-SET-10 resolution. THIRD "
        "recurrence: the register briefing is still missing from the round packet."),
}

# ---------- severity harmonizations (final severity; grounds in synthesis §2.3) ----------
SEV = {
    # FEN-C-CARRIER-SEQFAIL: executed FP on rule-ORDER-conformant traces (judge S1-S5, W)
    "BETA-KGN-05": "critica", "BETA-KMF-04": "critica", "BETA-TMF-04": "critica",
    "BETA-SSL-06": "critica",
    # FEN-C-DELAYED: executed FP at the rule's own optional event (S1b/S2b; batch B FEN-PBK-RESIDUO)
    "GAMA-TMF-02": "critica",
    # FEN-C-GETS-INVISIVEL: executed FP/FN (S8, S14, tmf_c; tables W)
    "GAMA-TMF-03": "critica", "GAMA-KMF-02": "critica", "GAMA-KGN-06": "critica",
    "BETA-SSL-03": "critica",
    # FEN-KST-G2-OMITIDA: executed chain FP on fully conformant program (S8)
    "BETA-KST-03": "critica", "GAMA-KST-04": "critica",
    # FEN-SSL-ENGINE-VOID: whole rule channel dead on both weave halves; FN executed in complex (S15b)
    "BETA-SSL-02": "critica",
    # FEN-SSL-ENGINE-LOOP: FN executed by the judge (S15b); §4 has no rarity carve-out
    "ALFA-SSL-05": "critica", "GAMA-SSL-05": "critica",
    # FEN-SSL-GETDEFAULT-OMITIDA: FORBIDDEN clause omitted, unregistered (pilot CIP-17 precedent)
    "GAMA-SSL-06": "critica",
    # FEN-KGN-KEYSIZE-OMITIDA: FN executed (S16/kgn_d); platform throw noted as magnitude context
    "BETA-KGN-06": "critica", "GAMA-KGN-04": "critica",
    # FEN-C-WHITELIST-EXTRA, KGN half (REF-D-02): alias FN trace not shown realizable
    # on any measured platform (after-returning events; aliases throw — IDPROBE);
    # held at major pending the Android-BC resolvability probe. SSL half stays critica.
    "ALFA-KGN-04": "major", "GAMA-KGN-03": "major",
    # FEN-KGN-NAOCOMPILA + FEN-SET-FAIL-OPEN (REF-D-01): §4 letter — fail-open is a
    # pre-registered Critica trigger; the batch A/B "major as pattern" practice was
    # never registered as a deviation and cannot be (deviations may not alter §4).
    "ALFA-KGN-09": "critica", "GAMA-KGN-01": "critica", "BETA-SET-04": "critica",
    # FEN-SET-GENERATEDKEY-2A-CASA: batch B precedent severity (latent slot loss, no executed FP/FN)
    "ALFA-KGN-07": "major", "ALFA-SET-03": "major",
    # FEN-KST-ENTRIES-OMITIDAS: FN conditional on declared oracle-reading ambiguity
    "ALFA-KST-04": "major",
}

# ---------- per-claim short justifications (FAIL confirmations + notable PASSes) ----------
J = {
 # carrier/pairing family
 "ALFA-KGN-02": "CONFIRMADO: judge S4 (2 InvalidSeq + UnsafeAlgorithm, pairing at gk1) + W walk; trace ORDER-conformant, misuse constraint-only.",
 "ALFA-KMF-02": "CONFIRMADO: judge S2 + W; same-__LOC pairing at i1; registered only partially (3b.11b names the delayed accusation, not the same-call pairing).",
 "ALFA-TMF-02": "CONFIRMADO: judge S1 executed the campaign fingerprint shape ('but found X509.').",
 "ALFA-SSL-02": "CONFIRMADO: judge S3 (UnsafeProtocol + InvalidSeq, same call).",
 "ALFA-KST-03": "CONFIRMADO: judge S5 (2 spurious of 3 records).",
 "ALFA-KGN-12": "CONFIRMADO: judge S4 records show unknown labels + list-dump message; diagnostics facet of the carrier phenomenon.",
 "BETA-KGN-05": "CONFIRMADO; severity harmonized major->critica (executed FP on conformant ORDER, judge S4; pre_registro §4).",
 "BETA-KMF-04": "CONFIRMADO; harmonized major->critica (judge S2).",
 "BETA-TMF-04": "CONFIRMADO; harmonized major->critica (judge S1); gh101 binding repair exposed the residue, provenance recorded.",
 "BETA-SSL-06": "CONFIRMADO; harmonized major->critica (judge S3).",
 "GAMA-KGN-02": "CONFIRMADO: judge S4 = kgn_a; FEN unified with FEN-C-CARRIER-SEQFAIL (same records, two names).",
 "GAMA-KMF-01": "CONFIRMADO: judge S2 = kmf_a.",
 "GAMA-TMF-01": "CONFIRMADO: judge S1 = tmf_a; same-call same-__LOC pairing proven (records differ only by type).",
 "GAMA-SSL-01": "CONFIRMADO: judge S3 = ssl_a.",
 "GAMA-KST-03": "CONFIRMADO: judge S5 = kst_b.",
 "GAMA-TMF-02": "CONFIRMADO; harmonized major->critica: S1b executed the post-__RESET FP at the rule's own gtm? on a conformant trace (batch B FEN-PBK-RESIDUO class).",
 # gets-invisivel family
 "ALFA-KGN-03": "CONFIRMADO: g2 condition-suppressed with no unsafe counterpart (spec read); creation-at-consume FP walked (W) and executed in siblings (S8/S14).",
 "ALFA-KMF-03": "CONFIRMADO: same mechanism; i1[0]=fail walked (W).",
 "ALFA-TMF-03": "CONFIRMADO: executed by Gama (tmf_c: empty-label UnsafeAlgorithm + InvalidSeq at first-event i1).",
 "ALFA-SSL-03": "CONFIRMADO: judge S14 — real getInstance(TLS, Provider) + init => 2 records on fully conformant trace, 'but found .' label.",
 "BETA-SSL-03": "CONFIRMADO; harmonized major->critica: judge S14 executed the FP; overload verified on android-30 class bytes.",
 "GAMA-SSL-02": "CONFIRMADO: judge S14 reproduces ssl_c.",
 "GAMA-TMF-03": "CONFIRMADO; harmonized ->critica (tmf_c executed; Cipher b532e439f79a repaired the identical class, unrepaired here, unregistered).",
 "GAMA-KMF-02": "CONFIRMADO; harmonized ->critica (structural twin; tables identical, W).",
 "GAMA-KGN-06": "CONFIRMADO; harmonized ->critica (gk1[0]=fail walked, W; empty-label route).",
 # KST family
 "ALFA-KST-02": "CONFIRMADO: judge S8 — 2-arg conformant creation => load FP + displaced KMF UnsatisfiedConstraint; rule g2 verified 2-arg (KeyStore.cryptsl:47).",
 "BETA-KST-03": "CONFIRMADO; harmonized major->critica (judge S8 chain FP).",
 "GAMA-KST-04": "CONFIRMADO; harmonized ->critica; FEN remapped to FEN-KST-G2-OMITIDA (the omission unit); null/stale-field marking verified (S8: validate(ks2)=false).",
 "BETA-KST-02": "CONFIRMADO: judge S6 — 5 spurious InvalidSeq on two individually conformant interleaved stores; Tuple2 global verified (W check 5).",
 "BETA-KST-08": "CONFIRMADO: judge S6 print — after load(A) neither A nor B validated (field-marking + immediate erasure compound); S8 stale-field mark.",
 "GAMA-KST-01": "CONFIRMADO: spec param ks bound by no event (spec read, lines 21 vs 30-79); artifact Tuple2 empty-binding (W); executed S6.",
 "GAMA-KST-02": "CONFIRMADO: judge S7 — A's granted mark erased by B's @fail; conformant TMF over A then FPs. Composes FEN-KST-MONITOR-GLOBAL + FEN-C-REMOVE-CASCADE.",
 "ALFA-KST-05": "CONFIRMADO: before-advice write verified in artifact (body before transition); exception path undriven, minor stands.",
 "BETA-KST-07": "CONFIRMADO: mechanism verified (gk1 body writes null key; validate(P,null)=true per ExecutionContext.setProperty/validate, judge-read).",
 # remove cascade
 "ALFA-KMF-07": "CONFIRMADO: judge S10 — granted mark of the handed-out array revoked at a later fail; SSL init(kms2) FP; zero NEGATES in the five rules (judge grep).",
 "ALFA-TMF-07": "CONFIRMADO e fechada a rota unica: judge S11 executed the TMF twin directly (was symmetry-only, confidence 0.85).",
 "ALFA-SET-06": "CONFIRMADO: S7/S10/S11 executed the pattern in three shapes; revocation semantics exists in no rule (0 NEGATES).",
 # SSL
 "ALFA-SSL-04": "CONFIRMADO: void-return pointcut vs SSLEngine return verified on android-30 class bytes (judge javap); both weave halves blind (Beta capture matrix + weave outputs conferred).",
 "BETA-SSL-02": "CONFIRMADO; harmonized major->critica: whole Engine channel unobservable; FN executed in the phenomenon complex (S15b).",
 "GAMA-SSL-03": "CONFIRMADO: same; register absence re-verified (0 hits).",
 "ALFA-SSL-05": "CONFIRMADO; FEN remapped to FEN-SSL-ENGINE-LOOP; harmonized ->critica: judge S15b executed the FN (2nd engine silent); oracle-bias note recorded (Engine? strictness), oracle stands raw.",
 "GAMA-SSL-05": "CONFIRMADO; harmonized minor->critica (same executed FN, S15b).",
 "ALFA-SSL-06": "CONFIRMADO: getDefault() exists on android-30 (judge javap); no event, no register row (0 hits); pilot CIP-17 precedent.",
 "GAMA-SSL-06": "CONFIRMADO; harmonized major->critica (same grounds).",
 "ALFA-SSL-07": "CONFIRMADO: rule binds '_' and sr is bound by no event (rule read); judge S12 executed the FP on a fully conformant trace; SecureRandom rule ENSURES randomized[this] after Ins narrows production realizability to capture gaps — noted, does not license the read vs the raw oracle; pending researcher scope reduction (batch B PBK precedent).",
 "ALFA-SSL-09": "CONFIRMADO: judge S15a executed the FN with a REAL getInstance(\"tls\") (resolves); raw literal set rejects; conformance row 19 registers the folding as aliases — registered != approved (pilot REF-04).",
 "ALFA-SSL-10": "CONFIRMADO: setProperty(P,null)/validate(P,null)=true verified at ExecutionContext source (judge-read).",
 "GAMA-SSL-04": "CONFIRMADO: judge S13 — 3 clauses violated at one init, 1 record survives (key-managers clause); ErrorSummary drops expecting (batch B mechanism, re-verified).",
 "ALFA-SET-05": "CONFIRMADO com escopo: row 63 'present' is accurate under the file's declared textual-wiring baseline semantics (README re-read); the substance stands — the dead pointcut is registered NOWHERE (omissions row 7 'terminal' framing included), an unregistered material divergence.",
 "GAMA-SET-20": "CONFIRMADO: static list carries SSLContext#createSSLEngine which no dynamic path can witness (dead pointcut judge-verified); §13 contradiction stands.",
 # KGN
 "ALFA-KGN-04": "CONFIRMADO no FAIL; severidade ->major (REF-D-02): the 6 alias spellings are outside the raw 11-literal list (INCORRETA at the constraint), but the FN's enabling trace is not realizable on any measured platform — all six throw and g1/g3 are after-returning (IDPROBE); §4's 'demonstravel em trace realizavel' unmet pending the Android-BC probe (named). Registered as carried artefact — registered != approved.",
 "GAMA-KGN-03": "CONFIRMADO no FAIL; severidade held at major (REF-D-02, rev. 1 upgrade withdrawn): same grounds as ALFA-KGN-04.",
 "ALFA-KGN-05": "CONFIRMADO: constraint transcribed nowhere; FN executed (judge S16); unregistered (0 hits).",
 "BETA-KGN-06": "CONFIRMADO; harmonized minor->critica per phenomenon; platform-throw overlap recorded as magnitude context, not a carve-out.",
 "GAMA-KGN-04": "CONFIRMADO; harmonized ->critica.",
 "ALFA-KGN-07": "CONFIRMADO; severity ->major per batch B FEN-SET-GENERATEDKEY-2A-CASA precedent: alg slot has no home in the store API (ExecutionContext.setProperty(Property,Object), judge-read); latent cross-batch FN, no executed witness this round.",
 "ALFA-SET-03": "CONFIRMADO; ->major, same grounds (writer-side confirmation of the established register).",
 "ALFA-KGN-09": "CONFIRMADO; severidade ->critica (REF-D-01): fail-open is a pre-registered §4 Critica trigger and this is a real fail-open of the round's chain — javac exit 1 on the frozen artifact while both generators exit 0 (judge probe); -merge masking verified at runtime_verification_generator.py:211,269.",
 "GAMA-KGN-01": "CONFIRMADO; severidade ->critica (REF-D-01): same grounds; three independent probes agree (Alfa, Gama, judge).",
 # accept-end / misc
 "ALFA-KMF-04": "CONFIRMADO: complete rule word ends outside match1 (W); no realizable FP/FN found — minor, table-level.",
 "ALFA-TMF-04": "CONFIRMADO: same (W).",
 "BETA-TMF-05": "CONFIRMADO: measured (ISE before return; after-returning cannot fire); platform-masked FN; register the limitation — pendency.",
 # toolchain / set
 "BETA-KMF-02": "CONFIRMADO: mechanism judge-verified at WrapperEmitter.java:334-395 (trailing-.. expansion accepts arity>=fixedPrefix; args() never consulted); table effect walked (W: g1,g2 => fail); Beta DX drives conferred; ajc disagrees => first measured ajc/dexlib2 semantic divergence.",
 "BETA-TMF-03": "CONFIRMADO: TMF twin, same mechanism and drives.",
 "BETA-SET-02": "CONFIRMADO: source mechanism verified; jar-robust (getInstance(String) exists on every platform jar).",
 "BETA-KST-04": "CONFIRMADO: TypeResolver.toDescriptor does replace('.','/') with no nested-type handling (judge-read :87-107); DEX wants $ (javap: KeyStore$Entry/$ProtectionParameter); ajc weaves, dexlib2 silently drops => silent FN + spurious fail on the sE,Stores route.",
 "BETA-SET-03": "CONFIRMADO: same mechanism, set-level.",
 "BETA-SET-04": "CONFIRMADO; severidade ->critica (REF-D-01): fail-open is a §4 Critica trigger; the property is real on the production toolchain (every probe exits 0) and the round's own artifacts realized it (FEN-KGN-NAOCOMPILA); new shape p1 (stray paren kills generation at exit 0).",
 "GAMA-SET-17": "CONFIRMADO: judge S13 executed the worst (3-clause) instance.",
 "GAMA-SET-18": "CONFIRMADO: every sequencing record in S1-S11 carries expecting=unknown (judge outputs).",
 "GAMA-SET-22": "CONFIRMADO: SecureRandomSpec unsafeInit admits all consuming events (spec fsm read by judge; register row 029a4511565f says so) while KMF/TMF/SSL carrier states admit none — the 3b.11b 'two repair philosophies' ground is factually already the case.",
 # PASS highlights
 "BETA-TMF-02": "CONFIRMADO: four-defect repair verified in spec text by judge; S18c isolation executed (tA survives tB's fail).",
 "BETA-SSL-04": "CONFIRMADO: returning(ctx) in spec :53; S3 shows observed protocol reaching the label.",
 "BETA-SSL-05": "CONFIRMADO: three readers fire (S13 1-of-3 + S12); writes verified.",
 "BETA-KST-05": "CONFIRMADO: three-key write verified in spec text; executed true by Gama (kst_d).",
 "ALFA-SET-01": "CONFIRMADO: judge S18d — full captured TLS chain clean (sr null-guarded).",
 "ALFA-SET-02": "CONFIRMADO: judge grep — generatedCipher in 0/33 api30 rules and 0/5 batch specs.",
 "ALFA-SET-04": "CONFIRMADO: SecureRandom rule ENSURES randomized[this] after Ins (judge-read) — writers exist for the batch C readers.",
 "GAMA-SET-19": "CONFIRMADO: extractor CSVs conferred; 28 rows, 0 'new'; class#method diff empty.",
 "BETA-SET-01": "CONFIRMADO: 20/20 artifact hashes = manifest (judge re-hash).",
 "ALFA-KGN-13": "CONFIRMADO: folding outputs conferred; case variants flagged by both sides for KGN (exact-contains guard).",
 "GAMA-TMF-04": "CONFIRMADO: S18c/S18d agree.",
 "GAMA-KMF-03": "CONFIRMADO: S18d agrees.",
 "GAMA-SSL-08": "CONFIRMADO: S18d agrees (sr=null path).",
 "GAMA-KST-06": "CONFIRMADO: kst_d conferred; three-key write verified.",
 "GAMA-KGN-07": "CONFIRMADO: S18a/S18b reproduce exactly (1 specific error, 0 spurious).",
}

INC_J = {
 "BETA-SET-07": "MANTIDO INCONCLUSIVE: android-37.0 production-default jar re-measurement pending (REF-C-03 carried).",
 "BETA-SET-08": "MANTIDO INCONCLUSIVE: ART/device + exceptional-return advice semantics (G6/G10). The ajc half is now measured for batch C claims; ART remains the unexecuted half. NOTE: after FEN-SET-VARARGS-ARGS-IGNORED the two halves measurably DISAGREE pre-ART — the pendency is now which half the device realizes, not whether they agree.",
 "GAMA-TMF-05": "MANTIDO INCONCLUSIVE: historical attribution deferred to replay battery G10-TMF-1; current-artifact half executed (S1).",
 "GAMA-SSL-07": "MANTIDO INCONCLUSIVE: replay G10-SSL-2.",
 "GAMA-KST-07": "MANTIDO INCONCLUSIVE: replay G10-KST-1.",
 "GAMA-SET-21": "MANTIDO INCONCLUSIVE: KGN/KMF historical zero-emission decomposition; zero != conformance.",
}

# REF-D-03: FAIL -> INCONCLUSIVE (oracle semantics of declared-but-unordered events)
REV2_INC = {
    "ALFA-KST-04":
        "REV.2 FAIL->INCONCLUSIVE (REF-D-03): under reading (a) the silence at scE/skE1/skE2 is an FN "
        "and the store record displaced; under reading (b) the raw oracle itself flags the projected "
        "trace at store — correctly placed, no FN, and the omission matches the oracle's indifference. "
        "The upstream Xtext grammar is syntax-only and does not fix the semantics; §3 bindings "
        "INCONCLUSIVE criterion applies ('nao determinavel por leitura + execucao'). Executed facts "
        "stand on the record (S9a accusation at store; silence at the Entries calls); resolution "
        "awaits the named oracle-semantics pendency. INCONCLUSIVE is not approval.",
    "GAMA-KST-05":
        "REV.2 FAIL->INCONCLUSIVE (REF-D-03): same grounds as ALFA-KST-04; the register-absence half "
        "is moot under reading (b) (nothing to register) and revives under reading (a).",
}

def canonical_fen(claim_id, fen, pos):
    if claim_id in FEN_CLAIM:
        return FEN_CLAIM[claim_id]
    return FEN_MAP.get(fen, fen)

def main():
    rows_out = []
    total = 0
    for fname in ("alfa_claims.csv", "beta_claims.csv", "gama_claims.csv"):
        with open(os.path.join(HERE, fname), newline="", encoding="utf-8") as f:
            rdr = csv.DictReader(f)
            for r in rdr:
                total += 1
                cid = r["id"]
                pos = r["posicao"].strip()
                if cid in OVERTURN:
                    np, ncls, nsev, just = OVERTURN[cid]
                    res, cls_f, sev_f = np, ncls, nsev
                elif cid in REV2_INC:
                    res, cls_f, sev_f = "INCONCLUSIVE", "INCONCLUSIVA (pendente semantica do oraculo)", "n/a"
                    just = REV2_INC[cid]
                elif pos == "INCONCLUSIVE":
                    res, cls_f, sev_f = "INCONCLUSIVE", r["classificacao"], r.get("severidade", "n/a")
                    just = INC_J.get(cid, "MANTIDO INCONCLUSIVE: pendencia nomeada no relatorio do agente.")
                else:
                    res = pos  # CONFIRMADO at the filed position
                    cls_f = r["classificacao"]
                    sev_f = SEV.get(cid, r.get("severidade", ""))
                    just = J.get(cid,
                        "CONFIRMADO: evidencia primaria conferida pelo juiz; sem contraevidencia."
                        if pos == "PASS" else
                        "CONFIRMADO: evidencia primaria conferida pelo juiz (fontes/artefatos/execucao).")
                fen_f = canonical_fen(cid, r.get("fenomeno_id", "").strip(), res)
                if res == "FAIL":
                    assert fen_f, f"D-batchB-1 violation: FAIL row {cid} without fenomeno_id_final"
                if cid in REV2_INC:
                    fen_f = fen_f or "FEN-KST-ENTRIES-OMITIDAS"  # kept for traceability on INC rows
                out = dict(r)
                out["resolucao_juiz"] = res
                out["classificacao_final"] = cls_f
                out["severidade_final"] = sev_f
                out["fenomeno_id_final"] = fen_f if res == "FAIL" else (fen_f or "")
                out["justificativa_curta"] = just
                rows_out.append(out)

    assert total == 134, f"expected 134 claims, got {total}"
    n_pass = sum(1 for r in rows_out if r["resolucao_juiz"] == "PASS")
    n_fail = sum(1 for r in rows_out if r["resolucao_juiz"] == "FAIL")
    n_inc = sum(1 for r in rows_out if r["resolucao_juiz"] == "INCONCLUSIVE")
    assert (n_pass, n_fail, n_inc) == (55, 71, 8), (n_pass, n_fail, n_inc)

    cols = list(rows_out[0].keys())
    outp = os.path.join(HERE, "juiz_claims_resolvidos_batchC.csv")
    with open(outp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r in rows_out:
            w.writerow(r)
    print(f"wrote {outp}: {total} rows = {n_pass} PASS / {n_fail} FAIL / {n_inc} INCONCLUSIVE")
    n_crit = sum(1 for r in rows_out if r["resolucao_juiz"] == "FAIL" and r["severidade_final"].startswith("crit"))
    print(f"critical FAIL claims: {n_crit}")

if __name__ == "__main__":
    main()
