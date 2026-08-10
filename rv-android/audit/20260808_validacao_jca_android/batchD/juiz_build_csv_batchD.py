#!/usr/bin/env python3
"""Builds juiz_claims_resolvidos_batchD.csv from the three agent CSVs (123 claims).

Appends: resolucao_juiz, classificacao_final, severidade_final, fenomeno_id_final,
justificativa_curta. Original columns preserved.

Rules applied: D-piloto-4 (judge does not re-assign claim->dimension; spelling
normalization for scoring happens in the rescore script and is recorded as a
normalization, not a re-assignment), D-batchA-1 (raw weighted sums are the record),
D-batchB-1 (every FAIL row carries fenomeno_id_final; build-time assert),
D-batchC-1 (fail-open severity at pre_registro §4's letter = critica),
REF-D-02 (critical FP/FN requires a trace executable on a measured platform;
alias claims with no resolving call held at major-pending), REF-D-03 (checked:
no batch D claim depends on declared-but-unordered event placement — all events
of the five rules appear in ORDER aggregates, judge-verified).

REV. 2 (post-refutation, 2026-08-09): REF-E-01 — ALFA-SRD-08's justificativa
now scopes the false 3-arg platform sub-assertion (alfa_javap_android30_batchD.txt
is host-JDK-contaminated; declared in juiz_respostas_refutacao_batchD.md §E-01);
REF-E-03 — recorded within-phenomenon severity rationale appended to
GAMA-MAC-04/GAMA-MDG-02; REF-E-05 — ALFA-MAC-12 severidade_final is now the
machine-readable "major-pending"; REF-E-08 — BETA-SET-07 pendency marked
HOST-EXECUTABLE. Resolutions, positions, criticals (54) unchanged.

Judge evidence tags: W = juiz_walk_batchD_output.txt (J1-D, 46/46 PASS);
D1..D9 = juiz_driveD_rep1.txt (J2-D, 3 reps sha-identical e136cf4c...);
JAVAP = judge javap over unzip-extracted android-30 class bytes;
SRC = judge file:line source reads; REG = judge gh101 register reads.
"""
import csv, os

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------- FEN unification map (canonical id, synthesis §2.6) ----------
FEN_MAP = {
    "FEN-C-PAIRING-IMEDIATO": "FEN-C-CARRIER-SEQFAIL",
    "FEN-D-UNSAFE-RESIDUE": "FEN-C-CARRIER-SEQFAIL",
    "FEN-D-UNBOUND-EVENT": "FEN-MAC-F3-UNBOUND",
    "FEN-D-F3-UNBOUND": "FEN-MAC-F3-UNBOUND",
    "FEN-B-GATE-EXTRA-ORACULO": "FEN-MAC-KEYGATE-EXTRA",
    "FEN-D-COND-SUPPRESS": "FEN-MAC-KEYGATE-EXTRA",
    "FEN-D-GETINSTANCE-PROVIDER": "FEN-C-GETS-INVISIVEL",
    "FEN-C-UNSAFE-2ARG": "FEN-C-GETS-INVISIVEL",
    "FEN-D-G4-ARITY": "FEN-C-GETS-INVISIVEL",
    "FEN-D-EMPTYLABEL-LIVE": "FEN-C-EMPTY-LABEL",
    "FEN-D-SRD-NEXTBYTES": "FEN-SRD-NEXTBYTES-FP",
    "FEN-D-CTOR-SILENT": "FEN-SRD-C3-SILENT",
    "FEN-D-RANDOMIZED-WRITER": "FEN-SRD-RANDOMIZED-OVERGRANT",
    "FEN-D-WRONG-RETURN": "FEN-SIG-SIGN-VOID",
    "FEN-D-DEAD-RETURN-TYPE": "FEN-SIG-SIGN-VOID",
    "FEN-D-KPG-NPE": "FEN-KPG-NPE",
    "FEN-D-FIRST-DISJUNCT": "FEN-SET-firstcall-disjunct",
    "FEN-D-BOXING": "FEN-D-CACHE-BOXING",
    "FEN-D-MSG-SET-ERRADO": "FEN-MDG-LABEL-STALE",
    "FEN-D-REGISTER-ORACLE": "FEN-D-REGISTER-ANCHOR-DRIFT",
    "FEN-SET-FAILOPEN": "FEN-SET-FAIL-OPEN",
}
# per-claim FEN remaps (judge assignment, D-batchB-1)
FEN_CLAIM = {
    "ALFA-MAC-09": "FEN-D-S13-BYTEBUFFER",       # headline unit: the D-S13 ByteBuffer FN (Byte-cache half noted)
    "GAMA-KPG-05": "FEN-KPG-INIT2-SUPPRESSED",   # same executed unit as ALFA-KPG-04 (kpg_f = KPG-T4)
    "GAMA-SIG-04": "FEN-SIG-VERIFIED-WRONGSLOT", # same unit as ALFA-SIG-05 (wrong-object write)
}

# ---------- position overturns ----------
OVERTURN = {
    "GAMA-MDG-03": ("PASS", "DIVERGENCIA_EQUIVALENTE_COMPROVADA (por ordem de advice)", "-",
        "OVERTURN FAIL->PASS: batch C rev.2 GAMA-KGN-05 precedent applies verbatim — g1-before-g4 "
        "order is fixed in the descriptor (judge re-verified in the batch D .aj, lines 43-45) AND "
        "WrapperEmitter fires merged advices in descriptor order (WrapperEmitter.java:246-249, "
        "judge-verified in batch C); per-object creation gives every monitor a fresh '' field. "
        "Executed benign (mdg_b; judge W safe walks). Fragility recorded as threat, matching ALFA-MDG-07 (PASS)."),
    "BETA-KPG-05": ("PASS", "LIMITACAO_INEVITAVEL_DOCUMENTADA (D-S14, capability-absent registrada)", "-",
        "OVERTURN FAIL->PASS: the preparedDSA/RSA/EC non-reads are REGISTERED capability-absent "
        "omissions (predicate_edges bucket capability-absent + spec Group-5 comment; REG) — same "
        "unit as ALFA-KPG-08 (PASS) and batch C neverTypeOf precedent: registered limitation with "
        "no live witness resolves PASS/LIMITACAO and blocks total adherence, not the claim."),
}

# ---------- severity harmonizations (final severity; grounds in synthesis §2) ----------
SEV = {
    # FEN-C-CARRIER-SEQFAIL: executed FP on rule-ORDER-conformant traces (batch C rev.2 precedent; judge W + D6)
    "BETA-MAC-06": "critica", "BETA-KPG-03": "critica",
    # FEN-MAC-KEYGATE-EXTRA: executed displaced FP on rule-conformant trace (judge D4)
    "BETA-MAC-05": "critica",
    # FEN-C-GETS-INVISIVEL: family precedent (batch C rev.2, executed FP storms / crash routes)
    "BETA-MAC-02": "critica",   # MAC: FP storm executed (MAC-T5/mac_c; W invisible-creation walk)
    "BETA-KPG-04": "critica",   # KPG: the Provider route ends in the NPE crash (judge D1)
    "BETA-SIG-02": "critica",   # SIG: FP storm executed (sig_a/SIG-T6)
    # FEN-SRD-C3-SILENT: executed FN of the rule's ONLY REQUIRES on a realizable constructor trace
    "BETA-SRD-04": "critica",
    # FEN-KPG-FAILSINK / FEN-A-STALE-FLAGS: cascade executed (kpg_b 3rd record; same records as ALFA-KPG-03)
    "GAMA-KPG-04": "critica",
    # FEN-KPG-INIT2-SUPPRESSED: executed FN+FP pair (kpg_f = KPG-T4)
    "GAMA-KPG-05": "critica",
    # FEN-SET-firstcall-disjunct: Beta EXECUTED the dexlib2 FN (DX-KPG-2) — silent FN on the production path
    "GAMA-KPG-06": "critica",
    # FEN-SRD-RANDOMIZED-OVERGRANT: aligned with ALFA-SRD-04/ALFA-SET-11 (executed grant + verified readers)
    "GAMA-SRD-03": "critica",
    # FEN-KPG-INITERROR-PLACEMENT: FP and FN both walked (judge W) and executed (judge D7a/D7b)
    "ALFA-KPG-06": "critica",
    # FEN-SRD-SEED-AFTER-END: FN executed on realizable trace (SRD-T3; judge W) — §4 letter, batch C
    # rev.2 FEN-SSL-ENGINE-LOOP precedent (no rarity carve-out)
    "ALFA-SRD-03": "critica",
    # FEN-C-EMPTY-LABEL: aligned with GAMA-SET-27 (executed H4-closure records ride with FPs)
    "ALFA-SET-14": "critica",
    # D-batchC-1: fail-open resolves at §4's letter
    "BETA-SET-04": "critica",
    # REF-D-02: MAC alias FN held at major-pending (all 6 spellings throw on measured platforms;
    # judge D5 executed the monitor-level acceptance; Android-BC probe named)
    "ALFA-MAC-12": "major-pending",
    # FEN-SIG-VERIFIED-WRONGSLOT: latent (no reader) — major per FEN-SET-GENERATEDKEY-2A-CASA precedent
    "GAMA-SIG-04": "major",
}

# classification corrections (final classification; positions unchanged)
CLS = {
    "GAMA-SIG-04": "INCORRETA (escrita no objeto errado vs verified[sign] da regra crua)",
    "GAMA-SRD-04": "LIMITACAO_INEVITAVEL_DOCUMENTADA (D-S13 cache-identity; leitura do slot-argumento literal a randomized[numB]; ambiguidade do oraculo registrada)",
}

# ---------- per-claim short justifications ----------
J = {
 # === MAC ===
 "ALFA-MAC-01": "CONFIRMADO: JAVAP re-derived the 4-update/3-getInstance/2-init/3-doFinal partition from extracted bytes; safe walk W (match at f1).",
 "ALFA-MAC-02": "CONFIRMADO: SRC MacSpec.mop:176-179 — f3 declares (byte[] output, int outOffset) and uses target(m) with m unbound; ajc probes by Beta AND Gama (independent, exit 0 + Xlint invalidAbsoluteTypeName) + descriptor JSON carries the malformed expression. Fail-open shape at critica per D-batchC-1.",
 "ALFA-MAC-03": "CONFIRMADO: judge D9 EXECUTED the broadcast — one f3Event advanced foreign mX to accepting (isInAcceptingState false->true) and accused innocent mY (1 InvalidSeq); dispatch on MacSpec__Map root verified in artifact (W).",
 "ALFA-MAC-04": "CONFIRMADO: SRC Mac.cryptsl REQUIRES = {preparedHMAC, !encrypted x2} — NO generatedKey (judge read); judge D4 executed the displaced FP (i1 suppressed, doFinal -> InvalidSeq, zero specific); the spec's own i2 comment names the trap (SRC).",
 "ALFA-MAC-05": "CONFIRMADO: judge W walked the carrier (g3 i1 uArr f1: fails at 1,2,3 on a rule-ORDER-conformant trace); D6 executed the sibling MDG shape; SRD counter-design (D3) proves avoidability.",
 "ALFA-MAC-06": "CONFIRMADO: SRC Mac.cryptsl:33-37 — g1=g2 are byte-duplicate 1-arg getInstance (oracle anomaly recorded); the spec's (String,String) capture tracks and marks objects the raw rule never tracks; major stands (no direct executed FP).",
 "ALFA-MAC-07": "CONFIRMADO: JAVAP getInstance(String,Provider) exists on android-30; judge W walked the born-at-i1 FP storm (fails at 0,1,2); Beta capture matrix mac_gi2p NEITHER (conferred).",
 "ALFA-MAC-08": "CONFIRMADO: SRC MacSpec deferred-marking design + CipherSpec reader anonymous first place; §8 target closed as faithful projection with the two D-S13 residues filed separately.",
 "ALFA-MAC-09": "CONFIRMADO: measured residues (MAC-T6 ByteBuffer FN; MAC-T7 Byte-cache over-mark, inert: only MACED reader takes byte[]); FEN remapped to FEN-D-S13-BYTEBUFFER (registered D-S13 unit).",
 "ALFA-MAC-10": "CONFIRMADO: monitor-level read live at f3 (MAC-T10); end-to-end deadness via f3 filed under FEN-MAC-F3-UNBOUND, not double-counted.",
 "ALFA-MAC-11": "CONFIRMADO: SRC Mac.cryptsl:73-75 declares offset<len and length(output1)>outOffset; no translation in the spec (judge grep); 0-hit register greps re-run (REG).",
 "ALFA-MAC-12": "CONFIRMADO com ajuste REF-D-02: minor->major-pending. Judge D5 EXECUTED the monitor-level FN (g1 accepts 'HMAC-SHA256', acceptance granted, 0 errors — raw 12-literal list rejects it), but the enabling getInstance throws on every measured platform (folding probe); Android-BC probe named. Same standard as batch C rev.2 KGN aliases.",
 "ALFA-MAC-13": "CONFIRMADO: per-object isolation on bound events verified in D9 setup (mX/mY independent until f3); the sole breach is the unbound f3 (filed).",
 "BETA-MAC-01": "CONFIRMADO: both halves measured by Beta (ajc dead / dexlib2 broadcast via global root, DX-MAC-anon/bcast); judge D9 independently executed the broadcast at monitor level; halves DISAGREE — dimension-7 instance #2 for the audit.",
 "BETA-MAC-02": "CONFIRMADO; harmonized major->critica (FEN-C-GETS-INVISIVEL family, batch C rev.2): Provider-created Mac invisible on BOTH halves (capture matrix conferred), consequence executed as born-at-consume FP storm (W; MAC-T5).",
 "BETA-MAC-03": "CONFIRMADO: registered D-S13 limitation with measured witness (MAC-T6) — FAIL/LIMITACAO stands (witness measured; registration blocks only the unregistered aggravation).",
 "BETA-MAC-04": "CONFIRMADO: now MEASURED (Alfa MAC-T7 executed the Byte-cache over-mark; Beta had it INFERIDO); inert today (no byte-typed MACED reader, judge grep conferred).",
 "BETA-MAC-05": "CONFIRMADO; harmonized major->critica: judge D4 executed the exact displaced FP on a rule-conformant trace; same phenomenon as ALFA-MAC-04/GAMA-MAC-02 (FEN-MAC-KEYGATE-EXTRA).",
 "BETA-MAC-06": "CONFIRMADO; harmonized major->critica (FEN-C-CARRIER-SEQFAIL, batch C rev.2 harmonization of the same Beta residue class).",
 "GAMA-MAC-01": "CONFIRMADO: mac_a executed the same-call pairing at one __LOC; judge W carrier walk agrees; historical 31-both/0-only-specific cells consistent.",
 "GAMA-MAC-02": "CONFIRMADO: judge D4 reproduces mac_b (displaced InvalidSeq, no specific); rule REQUIRES verified by judge (SRC); oracle-anchor divergence (1.5.2 states generatedKey) recorded, api30 governs.",
 "GAMA-MAC-03": "CONFIRMADO: Gama's own ajc probe (exit 0 + Xlint) + Beta's independent probe agree; judge D9 executed the broadcast; critica per D-batchC-1 (fail-open) and per the executed FP.",
 "GAMA-MAC-04": "CONFIRMADO: mac_c executed 'but found .' + InvalidSeq; JAVAP Provider overload exists with no event; historical tink-site consistency recorded, attribution deferred (G10-MAC-1). Severity held at filed major (rev.2, REF-E-03): the per-spec empty-label rows are the diagnostic-degradation facet (§4 'diagnóstico inatribuível' = major); the phenomenon's criticality is carried by the census/SIG rows whose executed records ride with FPs on conformant traces.",
 "GAMA-MAC-05": "CONFIRMADO: mac_e/mac_b conferred; judge D5 additionally shows the i1 path marking and accepting with a marked key (0 errors).",
 "GAMA-MAC-06": "CONFIRMADO com escopo: README declares predicate_edges.csv anchored to CrySL 1.5.2 (judge re-read :148-149) — the row is accurate under its declared anchor (no batch C BETA-SET-06 repeat); the confirmed substance is that the file's OWN premise ('REQUIRES/ENSURES do not vary' across anchors) is falsified by this very row (api30 Mac lacks the clause, judge SRC), and no row-level marking flags anchor-divergent rows — the drift sustains the extra-oracle gate against register-based review.",
 # === MDG ===
 "ALFA-MDG-01": "CONFIRMADO: JAVAP partition re-derived; the ONLY batch D spec capturing (String,Provider); Beta capture matrix mdg_gi2p both halves (conferred).",
 "ALFA-MDG-02": "CONFIRMADO: judge W safe-reuse walk (g1 update d1 update d1 -> match) and d1-without-update fails both oracles; product results accepted after walk verification.",
 "ALFA-MDG-03": "CONFIRMADO: judge D6 executed the carrier (UnsafeAlgorithm + InvalidSeq pair at EACH consuming site, 3 sites = 6 records); W walk agrees.",
 "ALFA-MDG-04": "CONFIRMADO: g2/g3 conditions are safe-only with no unsafe twin and g4 is 1-arg (SRC); born-at-update FP + empty label executed (MDG-T4/mdg_a).",
 "ALFA-MDG-05": "CONFIRMADO: crítica stands under REF-D-02 — the 6 witnesses ('sha-256','md5','sha256','SHA256','SHA384','SHA512') RESOLVE on the measured host JDK (folding probe, 3 reps), so the FN trace is realizable; raw 6-literal list verified (SRC MessageDigest.cryptsl:63).",
 "ALFA-MDG-06": "CONFIRMADO: §8 target closed — judge verified NO reset in the api30 rule and NO reset event in the spec (SRC/grep); jca twin declared it outside its ere (all-fail row); removal = fidelity to the raw oracle; oracle blind spot recorded.",
 "ALFA-MDG-07": "CONFIRMADO: same grounds as the GAMA-MDG-03 overturn (advice order judge-verified in the .aj; WrapperEmitter descriptor-order from batch C); fragility recorded.",
 "ALFA-MDG-08": "CONFIRMADO: SRC MessageDigest.cryptsl:65-67 (pre_len>pre_off, len>off); no translation; 0-hit register greps (REG).",
 "ALFA-MDG-09": "CONFIRMADO: DIGESTED registered terminal (predicate_omissions conferred); non-revoking @fail faithful (zero NEGATES); consequence-free — PASS/LIMITACAO.",
 "ALFA-MDG-10": "CONFIRMADO: judge D6 output carries the literal 'expecting one of {SHA-256, SHA-384, SHA-512}' against the 9-entry enforced list — message misstates the enforced oracle.",
 "ALFA-MDG-11": "CONFIRMADO: table-level acceptance divergence; accepting-store reader-less (REG); minor stands.",
 "BETA-MDG-01": "CONFIRMADO: capture faithful end to end on BOTH halves (matrix conferred; ByteBuffer + Provider covered; reset unmodelled per D-S12). Scope: capture dimension only — composes with Alfa's language/constraint FAILs (different dimensions, no conflict).",
 "BETA-MDG-02": "CONFIRMADO: merged g1->g4 order benign (judge re-verified order in .aj); folding acceptance of lowercase safe alg is the FN side of ALFA-MDG-05 — the capture PASS here is order/binding only.",
 "GAMA-MDG-01": "CONFIRMADO: judge D6 reproduces mdg_c exactly (pair per distinct consuming site); historical 2780/2871 both-cells consistent; __RESET re-arm verified in walk.",
 "GAMA-MDG-02": "CONFIRMADO: mdg_a executed; clone() route noted (no event in rule either — recorded, not a defect vs raw oracle); guava site-shape consistency recorded, attribution deferred. Severity held at filed major (rev.2, REF-E-03): same rationale as GAMA-MAC-04 — diagnostic-degradation facet, family criticality carried by the census/SIG rows.",
 "GAMA-MDG-04": "CONFIRMADO: judge D6 output shows the wrong-set message literally; unified FEN-MDG-LABEL-STALE.",
 "GAMA-MDG-05": "CONFIRMADO: MD5/SHA-1 are SAFE under the api30 rule (judge SRC) and mdg_b shows current silence on MD5 — any future drop is oracle change; warning stands as filed.",
 # === KPG ===
 "ALFA-KPG-01": "CONFIRMADO: JAVAP 4-initialize/3-getInstance/genKeyPair+generateKeyPair re-derived; dexlib2 disjunct caveat correctly flagged and now MEASURED by Beta (KPG-02).",
 "ALFA-KPG-02": "CONFIRMADO: judge D1 EXECUTED the NPE from BOTH init1Event and initErrorEvent to the caller on an unseen generator; switch(algorithm) on uninitialized field verified (SRC .mop:26-35); no try/catch in dispatch (SRC artifact). Classified spec-INCORRETA (fail-crash), not toolchain: the switch is spec-authored code; monitor-creation-at-first-event is standard parametric semantics.",
 "ALFA-KPG-03": "CONFIRMADO: judge verified KPG is the ONLY batch D monitor without this.reset() in @fail (0 vs 1 in the other four, W); cascade walked (W fail-sink walk) and executed (D7a follow-on records; kpg_b).",
 "ALFA-KPG-04": "CONFIRMADO: initError pointcut covers initialize(int) only (SRC .mop:113-120); kpg_f/KPG-T4 executed the FN+FP pair; the 1-arg route reports correctly (D7a InvalidKeySize).",
 "ALFA-KPG-05": "CONFIRMADO: carrier + H2 confirmed for the pilot's named KPG; sticky-category amplification filed under FEN-KPG-FAILSINK/FEN-A-STALE-FLAGS.",
 "ALFA-KPG-06": "CONFIRMADO; harmonized major->critica: judge D7a executed the FP (bad-size-then-gen: InvalidSeq at gen on an ORDER-complete trace — i3 with bad size IS an Inits) and D7b executed the FN (bad-then-corrected accepted + GENERATED_KEY_PAIR granted while the rule's single-Inits is violated); both directions also walked (W). The gh101 register does not record the gen-unreachability consequence (REG).",
 "ALFA-KPG-07": "CONFIRMADO: JAVAP (String,Provider) exists; rule g2=(alg,_) covers it (SRC); consequence is the D1 crash — critica.",
 "ALFA-KPG-08": "CONFIRMADO: preparedDH read faithful (kpg_d conferred); preparedDSA/RSA/EC registered capability-absent (REG) — PASS/LIMITACAO, blocks total adherence.",
 "ALFA-KPG-09": "CONFIRMADO: writer-only constant verified (REG + grep); alg-slot loss consequence-free; extra-oracle remove inert for the same reason.",
 "ALFA-KPG-10": "CONFIRMADO: CHAIN-T1 measured mark delivery + one KeyPairSpec FP per pair access (batch B REPROVADA shape re-measured from the writer side); no starvation. SET-level consequence recorded in synthesis §6 (claim unit stays KPG per id convention).",
 "ALFA-KPG-11": "CONFIRMADO: literal sets verified against the rule (SRC validate(): RSA{2048,4096}, DSA/DH 2048, EC 256 = the rule's implications).",
 "BETA-KPG-01": "CONFIRMADO com escopo: judge D7b reproduced the correction route exactly (InvalidKeySize only, then accepting — no spurious InvalidSeq). The PASS is SCOPED to that route: D7a shows bad-size-then-generate still draws the delayed spurious InvalidSeq (ALFA-KPG-06/GAMA-KPG-03) — no conflict, complementary routes on one table (W).",
 "BETA-KPG-02": "CONFIRMADO: production WrapperEmitter.findFirstCall mechanism (source-verified in batch C, :507-524) + EXECUTED weave (kpg_genkp UNTOUCHED, plansSkippedAliasing=1) + DX-KPG-2 drive (mark never granted); ajc captures both — halves DISAGREE (dimension-7 instance #3).",
 "BETA-KPG-03": "CONFIRMADO; harmonized major->critica (carrier family; EC exposure gh101-introduced by the CrySL-aligned safe list — provenance recorded).",
 "BETA-KPG-04": "CONFIRMADO; harmonized major->critica: on KPG the Provider route's consequence is the executed NPE crash (judge D1), not a mere FN.",
 "GAMA-KPG-01": "CONFIRMADO: judge D1 executed the NPE 3x deterministic from both event methods; reachable via the conformant Provider route (JAVAP); unregistered (REG 0 hits); fail-crash outranks fail-open.",
 "GAMA-KPG-02": "CONFIRMADO: same evidence; Cipher-repaired class (b532e439f79a) unrepaired here with a crash consequence.",
 "GAMA-KPG-03": "CONFIRMADO: both forms executed (kpg_a immediate; kpg_b delayed = judge D7a); the gh101 initError repair CONVERTED the immediate pairing into the delayed one — it did not remove it; jca twin had initError absent from its ere (REG).",
 "GAMA-KPG-04": "CONFIRMADO; harmonized major->critica: absorbing-fail cascade executed (kpg_b 3rd record; judge W fail-sink walk shows one accusation per event forever) + the batch A stale-flags phenomenon first instantiated (artifact :441-456/:1039-1045, SRC).",
 "GAMA-KPG-05": "CONFIRMADO; harmonized major->critica; FEN remapped to FEN-KPG-INIT2-SUPPRESSED (same executed unit as ALFA-KPG-04: kpg_f = KPG-T4).",
 "GAMA-KPG-06": "CONFIRMADO; harmonized major->critica: the pendency Gama named (dexlib2 half) was EXECUTED by Beta (DX-KPG-2, silent FN) — the register-based claim is now measurement-backed.",
 "GAMA-KPG-07": "CONFIRMADO: kpg_d conferred; judge D7b confirms GENERATED_KEY_PAIR write + accepting; terminal-by-registered-design verified (REG).",
 # === SRD ===
 "ALFA-SRD-01": "CONFIRMADO: judge verified the end-block omission in the SPEC TEXT (SecureRandomSpec.mop:169-177: genSeed/setSeed1-3/next1/next3/ints, no next2) AND the effective row next2={4,1,3,4,4} (W), AND executed the FP (D2: 2 false InvalidSeq on nextBytes calls 2-3 of a canonical trace); jca twin end block also omits next2 (inherited, campaign-long); unregistered (REG 0 hits beyond inventory rows). The batch headline.",
 "ALFA-SRD-02": "CONFIRMADO: c3 body is 'sr = r;' only (SRC :42-47) while the gh101 comment (:136-139) claims 'Each reports in its own body' — comment/code divergence in a gh101-authored hunk, judge-read; FN executed (SRD-T4: zero reports on the rule's only REQUIRES violated).",
 "ALFA-SRD-03": "CONFIRMADO; harmonized major->critica: FN executed on a realizable trace (SRD-T3; judge W: c1 nB setSeed1 silent while Seeds? strictly precedes Ends*); §4's letter + batch C rev.2 FEN-SSL-ENGINE-LOOP precedent (executed cardinality/position FN = critica; no rarity carve-out). Oracle-bias note (re-seeding arguably benign) recorded, oracle stands raw.",
 "ALFA-SRD-04": "CONFIRMADO: judge D3 executed the overgrant (RANDOMIZED[bytes-from-unsafe-instance]=true while RANDOMIZED[sr]=false); downstream reader list verified by grep; CipherSpec's coupled GENERATED_CIPHER write shows the alternative was known.",
 "ALFA-SRD-05": "CONFIRMADO: judge D3 shows the object-level mark correctly withheld from unsafe instances; conformant-path writer characterization stands (D2 setup: c1-created instance marked).",
 "ALFA-SRD-06": "CONFIRMADO: rule ne is the protected next(int) (JAVAP: 'protected final int next(int)') — uncallable by apps; nextInt/ints are not declared SecureRandom members (JAVAP) and have no rule counterpart; boxed-Integer cache marks measured (SRD-T8/srd_d); register endorsement anchored to 1.5.2 (FEN-D-REGISTER-ANCHOR-DRIFT).",
 "ALFA-SRD-07": "CONFIRMADO: judge D3 executed the no-pairing design (exactly 1 UnsafeAlgorithm, 0 InvalidSeq) — the round's proof that the carrier-FP family is a design choice; GAMA-SET-22 confirmed from the SRD side.",
 "ALFA-SRD-08": "CONFIRMADO com escopo (rev.2, REF-E-01): g4 args(alg) is 1-arg only (SRC :76-78, judge REF-D-04 grep); born-at-consume FP without the specific accusation executed (SRD-T6/srd_c) — the operative mechanism. SCOPE NOTE: the evidencia_primaria sub-assertion that getInstance(String,SecureRandomParameters[,String|Provider]) exist on android-30 is FALSE — alfa_javap_android30_batchD.txt is host-JDK output (JDK-fallback trap; the type is absent from the frozen jar, judge- and refuter-verified from extracted bytes); the 3-arg untracked-route surface is host-JDK-only and VACUOUS on the frozen android-30 platform. Resolution and severity rest on the unsafe-2-arg half only.",
 "ALFA-SRD-09": "CONFIRMADO: only init accepting (match1 alias, SRC :189); accepting-store reader-less; minor table-level.",
 "ALFA-SRD-10": "CONFIRMADO: SHA1PRNG literal identical both sides; all 15 events bind r (W parse).",
 "BETA-SRD-01": "CONFIRMADO: FEN-SET-VARARGS-ARGS-IGNORED recurrence — mechanism judge-verified at source in batch C (args() never consulted); judge REF-D-04 grep confirms g2 args(alg,*) under (String,..) in THIS spec (:62-63); Beta EXECUTED the FP (DX-SRD-1: legal 1-arg getInstance('SHA1PRNG') -> InvalidSeq on the dexlib2 path, 3 reps); ajc honors args — halves DISAGREE. Critical FP on the correct call, toolchain, jar-robust.",
 "BETA-SRD-02": "CONFIRMADO: g4 arity FN on ajc executed (SRD-d1 silent); dexlib2 catches by the same over-expansion that makes SRD-01 wrong (halves disagree in the OPPOSITE direction on the unsafe leg); FEN remapped to FEN-C-GETS-INVISIVEL (unsafe-2-arg capture-blindness unit, with the divergence nuance recorded).",
 "BETA-SRD-03": "CONFIRMADO: declared-only AndroidClassIndex verified by JAVAP (nextInt/ints not declared on SecureRandom) + executed weave (UNTOUCHED) + DX-SRD-2 (no RANDOMIZED writes on the device path); nextBytes/generateSeed survive (DX-SRD-2b).",
 "BETA-SRD-04": "CONFIRMADO; harmonized major->critica: same unit as ALFA-SRD-02 (executed FN of the rule's only REQUIRES via the constructor; setSeed3 asymmetry proves the design was available).",
 "BETA-SRD-05": "CONFIRMADO: boxing store residues measured (bound-not-return; cache-boundary loss); D-S13 family, minor stands.",
 "BETA-SRD-06": "CONFIRMADO com escopo: writer EXISTS and fires on the ajc path (judge D2/D3 confirm writes) — the PASS is existence/binding only and composes with the overgrant FAIL (conditionality) and the dexlib2 deadness of next3/ints (BETA-SRD-03).",
 "GAMA-SRD-01": "CONFIRMADO: judge D2 reproduces srd_a exactly (2 false InvalidSeq, calls 2-3); control srd_a2 isolates the row; spec-text + table + execution all judge-verified. Minimal separating trace c1 nB nB walked (W).",
 "GAMA-SRD-03": "CONFIRMADO; harmonized major->critica: judge D3 executed the unsafeInit-path grant; body-before-handleEvent fail-path grant executed (srd_a b2=true); every downstream randomized[] REQUIRES satisfiable by non-conformant randomness — the set-wide FN feed that decides pilot/A/B residuals (synthesis §6).",
 "GAMA-SRD-04": "CONFIRMADO com reclassificacao: the argument-slot marking is LITERAL to the raw rule's randomized[numB] (SRC — oracle's own oddity: ne is protected); the cache-identity half is the D-S13 family -> classificacao_final LIMITACAO_INEVITAVEL_DOCUMENTADA; the extra-alphabet unit lives in ALFA-SRD-06 (INCORRETA) — units composed, no conflict.",
 "GAMA-SRD-05": "CONFIRMADO: srd_e/srd_b conferred; judge D3 reproduces the g4 specific-alone report; registered unsafeInit philosophy works as registered (its overgrant side is filed separately).",
 "GAMA-SRD-06": "CONFIRMADO: unsafe 2-arg matches nothing on ajc (g2 safe-gated, g4 1-arg — judge REF-D-04 grep); displaced FP + no UnsafeAlgorithm executed (srd_c); safe-side Provider coverage is the batch's only one (contrast recorded).",
 # === SIG ===
 "ALFA-SIG-01": "CONFIRMADO: JAVAP from extracted bytes — 'public final byte[] sign()' / 'public final int sign(byte[],int,int)'; no 'byte sign()' member exists, so both pointcuts are dead (SRC .mop:120,127); consequence walked (W: complete conformant sign flow never accepts) and executed (SIG-T1/T3; Beta both-halves NEITHER, conferred); internal returning(byte[])-vs-byte inconsistency accepted silently by generators — fail-open note (D-batchC-1 reinforces critica).",
 "ALFA-SIG-02": "CONFIRMADO: judge W walked the carrier (g3 i4 update v1: fails at 1,2,3 on rule-ORDER-conformant trace); SIG-T5 executed.",
 "ALFA-SIG-03": "CONFIRMADO: JAVAP Provider overload exists; rule g2=(alg,_) covers it; FP storm + empty label executed (SIG-T6/sig_a).",
 "ALFA-SIG-04": "CONFIRMADO: body reads on i1/i2/i4 exactly as the rule states (SRC); SIG-T4 executed (1 specific, 0 spurious) — the G9-clean design MacSpec i1/i2 lacks.",
 "ALFA-SIG-05": "CONFIRMADO: judge D8 EXECUTED the wrong-slot write (VERIFIED[Boolean.TRUE]=true, VERIFIED[signBytes]=false); raw rule says verified[sign] (SRC Signature.cryptsl:93); no reader (REG) — major latent.",
 "ALFA-SIG-06": "CONFIRMADO: verify-branch skeleton faithful (judge W safe verify walk to match); divergences route through the dead Signs channel and carriers (filed).",
 "ALFA-SIG-07": "CONFIRMADO: 20-literal set equality; raw-oracle permissiveness (DSS, MD5withRSA) recorded per pre_registro §1.",
 "ALFA-SIG-08": "CONFIRMADO: 12 events bind s; per-object isolation verified in D8/D9 setups.",
 "BETA-SIG-01": "CONFIRMADO: both halves measured dead (sig_sign0/sign3 NEITHER, conferred; no wrapper emitted); drives executed the FN (SIGNED never written; accepting never reached) and the FP (re-initSign after unobserved sign -> InvalidSeq); JAVAP re-derived by judge.",
 "BETA-SIG-02": "CONFIRMADO; harmonized major->critica (FEN-C-GETS-INVISIVEL family: the omission's executed consequence is the sig_a/SIG-T6 FP storm on conformant traces).",
 "BETA-SIG-03": "CONFIRMADO: verify branch faithful both halves + two-object isolation (SIG-d, 3 reps); scope: the sign half is dead (BETA-SIG-01).",
 "BETA-SIG-04": "CONFIRMADO: reader present, bound to the right object (SRC :69,107); writers cross-spec (KeyPairSpec/KeyStoreSpec — batch B context bounds end-to-end value; ALFA-KPG-10 measured the FP toll on the generateKeyPair route).",
 "GAMA-SIG-01": "CONFIRMADO: same member facts re-derived by judge (JAVAP); sig_b executed the acceptance loss; 'sign-misuse unreportable today' verified by W (platform-view walk never reaches s1).",
 "GAMA-SIG-02": "CONFIRMADO: sig_a executed (3 records, 3 types, 1 __LOC — all survive dedupe); H4 closure for SIG; historical single-site (spongycastle checkSignature) consistency recorded, attribution deferred (G10-SIG-1).",
 "GAMA-SIG-03": "CONFIRMADO: JAVAP + rule read; the dominant historical empty-label site uses provider-parameterized creation — consistency, not causation (deferred).",
 "GAMA-SIG-04": "CONFIRMADO com reclassificacao INCORRETA e harmonizacao minor->major: same unit as ALFA-SIG-05 (judge D8 executed); 'equivalent-in-effect while terminal' is absence-of-reader, not semantic equivalence — the rule marks the sign bytes; latent -> major per the FEN-SET-GENERATEDKEY-2A-CASA precedent.",
 "GAMA-SIG-05": "CONFIRMADO: sig_e/sig_d conferred; g3 repair holds at the getInstance line (no immediate accusation).",
 # === SET ===
 "ALFA-SET-10": "CONFIRMADO: MAC-T8 executed the guaranteed-fire read; writer-side unwritability is batch A's closed record (HMC); faithful reader x unwritable writer = composition FAIL — the set-level guaranteed FP on every parameterized Mac.init.",
 "ALFA-SET-11": "CONFIRMADO: judge D3 executed the decisive split — material marks granted from unsafe instances (true) vs object mark withheld (false); the object/material split DECIDES pilot/A/B residuals (synthesis §6: object-level reads sound; material-level reads unsound).",
 "ALFA-SET-12": "CONFIRMADO com escopo (paralelo a GAMA-MAC-06): rows accurate under the file's DECLARED 1.5.2 anchor (README :148-149, judge re-read — not a batch C BETA-SET-06 repeat); the confirmed defect is the falsified invariance premise + absence of row-level anchor marking for the >=3 rows that diverge between anchors (Mac generatedKey; SecureRandom randInt/randIntInRange; Signature verified) — all three verified against the raw rules by the judge (SRC).",
 "ALFA-SET-13": "CONFIRMADO: pairing census 4/5 executed (judge D6 for MDG; W walks for MAC/KPG/SIG carriers; D3 executes the SRD counter-design) — the strongest evidence yet that the family is INCORRETA, not an inevitable limitation.",
 "ALFA-SET-14": "CONFIRMADO; harmonized major->critica (aligned with GAMA-SET-27, same executed records): H4 empty-label mechanism live in MAC/MDG/SIG via creation-at-consume; KPG crashes instead (D1).",
 "ALFA-SET-15": "CONFIRMADO: judge re-verified the full freeze chain (10/10 specs+rules; 20/20 artifacts; jar hashes; W monitors compile — no KGN-NAOCOMPILA analogue).",
 "BETA-SET-01": "CONFIRMADO: regeneration determinism + coenable EXACT n*(2^n-1) on 5/5 — arithmetic re-verified by judge (22517/2040/4599/49140/491505).",
 "BETA-SET-02": "CONFIRMADO: SRD stress point measured (491505 sets, 24.08 MB string, 12.57 s / 1.61 GB, 3 reps); 17-event extrapolation 2228207 sets re-computed by judge — CLOSES the fase0 gap 'teto do gerador sem output bruto' (recorded in synthesis §6).",
 "BETA-SET-03": "CONFIRMADO: descriptor<->aspect 1:1 (programmatic); all five monitors compile standalone (judge re-compiled, exit 0) — no batch C KGN masking shape.",
 "BETA-SET-04": "CONFIRMADO; harmonized major->critica per D-batchC-1 (fail-open at §4's letter): P1/P3 silently drop the monitor at exit 0; P2 accepts an unknown symbol; a pipeline gated on exit codes catches none.",
 "BETA-SET-05": "CONFIRMADO: per-object indexing on bound events verified (judge D9 setup isolation; W dispatch checks); the sole global-root breach is the unbound MAC f3 (filed).",
 "GAMA-SET-23": "CONFIRMADO: 6 statically-listed rows are dynamically dead/deformed (sign x2 judge-JAVAP; f3 judge-executed broadcast; nextInt x2/ints JAVAP-absent from declared members + declared-only index) — static view over-promises; batch C SET-20 breach class, now including two RANDOMIZED writers.",
 "GAMA-SET-24": "CONFIRMADO: extractor diff = exactly MessageDigest#reset (the removed event) at the GATOR key; literal-jca default re-verified current (config.py:199-207); near-vacuous otherwise for batch D.",
 "GAMA-SET-26": "CONFIRMADO: dedupe collapse controls re-executed on batch D artifacts (mdg_e vs mdg_c); judge D6 shows same-call pairs surviving because types differ; per-site amplification / per-line masking stands.",
 "GAMA-SET-27": "CONFIRMADO: H4 closed — live mechanism executed in exactly the three pilot-named classes (mac_c/mdg_a/sig_a; judge W invisible-creation walk); task 8.1's zero-post-GH100 measurement covered only the weaver route; per-line historical attribution stays deferred.",
 "GAMA-SET-28": "CONFIRMADO: freeze chain independently re-verified by judge (hashes §0/§7).",
}

INC_J = {
 "BETA-SET-06": "MANTIDO INCONCLUSIVE: ART/device execution (G6/G10). Note carried from batch C rev.2: with FEN-MAC-F3-UNBOUND, FEN-SET-firstcall-disjunct and FEN-SET-VARARGS on SRD, the two halves measurably DISAGREE pre-ART in batch D too — the pendency is which semantics the device realizes.",
 "BETA-SET-07": "MANTIDO INCONCLUSIVE: android-37.0 production-default jar (REF-C-03 carried); all batch D member matching is android-30-pinned. HOST-EXECUTABLE (rev.2, REF-E-08): the discriminating measurement — production dexlib2 weave over the android-37.0 jar on the frozen host toolchain — needs no device/emulator; routed to the set-level phase actionable list, unlike the ART pendencies.",
 "GAMA-SRD-02": "MANTIDO INCONCLUSIVE: H-SRD-1 (the 12,400 historical SRD lines as the SRD-01 FP) is a site-profile consistency argument; causal attribution requires the named replay G10-SRD-1. The current-artifact mechanism itself is judge-executed (D2) — only the historical attribution stays open.",
}

def main():
    rows_out, total = [], 0
    for fname in ("alfa_claims.csv", "beta_claims.csv", "gama_claims.csv"):
        with open(os.path.join(HERE, fname), newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f, restkey="_extra"):
                # Parse-time repair (agent file untouched): ALFA-SRD-08 carries an
                # unquoted comma inside "args(alg,*)" in contraevidencia_procurada,
                # shifting the last four fields right by one. Shift them back.
                if r.get("_extra"):
                    assert r["id"] == "ALFA-SRD-08" and r["_extra"] == ["0.9"], r["id"]
                    r["contraevidencia_procurada"] += "," + r["ameaca_validade"]
                    r["ameaca_validade"] = r["impacto_fp_fn"]
                    r["impacto_fp_fn"] = r["severidade"]
                    r["severidade"] = r["confianca"]
                    r["confianca"] = r["_extra"][0]
                r.pop("_extra", None)
                total += 1
                cid = r["id"]
                pos = r["posicao"].strip()
                if cid in OVERTURN:
                    res, cls_f, sev_f, just = OVERTURN[cid]
                elif pos == "INCONCLUSIVE":
                    res, cls_f, sev_f = "INCONCLUSIVE", r["classificacao"], r.get("severidade", "n/a")
                    just = INC_J[cid]
                else:
                    res = pos
                    cls_f = CLS.get(cid, r["classificacao"])
                    sev_f = SEV.get(cid, r.get("severidade", ""))
                    just = J.get(cid,
                        "CONFIRMADO: evidencia primaria conferida pelo juiz; sem contraevidencia."
                        if pos == "PASS" else
                        "CONFIRMADO: evidencia primaria conferida pelo juiz (fontes/artefatos/execucao).")
                fen_filed = r.get("fenomeno_id", "").strip()
                fen_f = FEN_CLAIM.get(cid, FEN_MAP.get(fen_filed, fen_filed))
                if res == "FAIL":
                    assert fen_f, f"D-batchB-1 violation: FAIL row {cid} without fenomeno_id_final"
                out = dict(r)
                out["resolucao_juiz"] = res
                out["classificacao_final"] = cls_f
                out["severidade_final"] = sev_f
                out["fenomeno_id_final"] = fen_f if res == "FAIL" else (fen_f or "")
                out["justificativa_curta"] = just
                rows_out.append(out)

    assert total == 123, f"expected 123 claims, got {total}"
    n_pass = sum(1 for r in rows_out if r["resolucao_juiz"] == "PASS")
    n_fail = sum(1 for r in rows_out if r["resolucao_juiz"] == "FAIL")
    n_inc = sum(1 for r in rows_out if r["resolucao_juiz"] == "INCONCLUSIVE")
    assert (n_pass, n_fail, n_inc) == (39, 81, 3), (n_pass, n_fail, n_inc)

    cols = list(rows_out[0].keys())
    outp = os.path.join(HERE, "juiz_claims_resolvidos_batchD.csv")
    with open(outp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r in rows_out:
            w.writerow(r)
    print(f"wrote {outp}: {total} rows = {n_pass} PASS / {n_fail} FAIL / {n_inc} INCONCLUSIVE")
    n_crit = sum(1 for r in rows_out if r["resolucao_juiz"] == "FAIL"
                 and r["severidade_final"].lower().startswith(("crit", "crít")))
    print(f"critical FAIL claims: {n_crit}")

if __name__ == "__main__":
    main()
