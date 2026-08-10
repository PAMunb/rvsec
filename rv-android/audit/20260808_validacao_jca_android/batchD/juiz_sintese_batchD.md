# JUDGE — Batch D synthesis (MAC, MDG, KPG, SRD, SIG) — FINAL batch

Judge (LLM-as-a-Judge), round "batch D" of the `jca_android` audit · 2026-08-09.
Role: evidence synthesis — **not** a formal oracle, **not** majority vote. A
reproducible counterexample cannot be dismissed by consensus; a reading-only
claim cannot close a toolchain claim; `INCONCLUSIVE` never becomes approval.
Rules in force: `fase0/pre_registro.md` §3/§4/§6 under D-piloto-1/2/3/4,
D-batchA-1 (raw weighted sum is the score of record), D-batchB-1 (every FAIL
row carries `fenomeno_id_final`, builder-asserted), and **D-batchC-1**
(fail-open severity at §4's letter = crítica) — all of `fase0/desvios.md`.
Batch C is **CLOSED (rev. 2)**; its four binding consistency rulings are
applied here: D-batchC-1, **REF-D-02** (critical FP/FN requires a trace
executable on a measured platform; alias claims without a resolving call held
at major-pending), **REF-D-03** (declared-but-unordered event placement is
INCONCLUSIVE — checked: **no batch D claim depends on that choice**, §2.8),
**REF-D-04** (the SecureRandomSpec instances of both measured ajc×dexlib2
divergence mechanisms — confirmed by my own grep, §0.6). Batch B carried rules
honored: REF-B-01 (judge evidence under `batchD/` with hashes), REF-B-05
(gates fail by pre-registered criteria), REF-B-07 (routes counted, not
agents), REF-B-09, REF-C-03 (G5 jar-scope annotation), REF-C-05 (provenance
table for critical phenomena).

Inputs: `batchD/generation_manifest.md` (20 artifacts, hash-verified by me),
the three agent reports and CSVs (`alfa_*` 59 claims, `beta_*` 30, `gama_*`
34 — **123 total**), the frozen specs/rules, the gh101 registers, production
sources, platform class bytes. Claim-by-claim resolution:
`batchD/juiz_claims_resolvidos_batchD.csv` (original columns preserved;
`resolucao_juiz`, `classificacao_final`, `severidade_final`,
`fenomeno_id_final`, `justificativa_curta` appended). Mechanical re-sum:
`batchD/juiz_rescore_batchD.py` (§4 is its verbatim output,
`juiz_rescore_batchD_output.txt`).

Scope of this round's verdicts: gates **G2, G3, G4, G5, G7, G9**. G6, G8 and
G10 were not executed — they can only ADD defects, never remove demonstrated
ones. G0/G1 closed in fase 0; G11–G13 are fed by, not closed by, this round.
The ajc capture half is closed for batch D claims (Beta compile-time weave
with aspectjtools 1.9.25.1, the Docker version; Gama's independent ajc probe
on the MAC aspect); the production dexlib2 half is closed by Beta's executed
weave over the frozen android-30 jar; ART execution remains the G6/G10
pendency.

## 0. Evidence the judge verified or executed himself

All commands reproducible; agent files untouched (one parse-time repair of a
malformed CSV row, documented in the builder — the file itself unmodified);
judge work in scratch `<scratchpad>/batchD/juiz/`, decisive files copied to
`batchD/juiz_*` (§7).

1. **Freeze**: `sha256sum` over the 5 `.mop` + 5 `.cryptsl` (10/10 =
   `generation_manifest.md` = `fase0/manifest_hashes.md`) and the 20 round
   artifacts (20/20 = manifest). Harness jars re-hashed: rv-monitor-rt
   `0fa65fbc…`, rvsec-core `7b4d72aa…`, rvsec-logger-csv `6787f411…`;
   android-30 jar `96ccfdc8…`.
2. **Sources read end-to-end with the decisive lines confirmed**:
   - `Mac.cryptsl`: REQUIRES = {`preparedHMAC[params]`, `!encrypted[output1,_]`,
     `!encrypted[output2,_]`} — **no generatedKey clause**; `g1`/`g2` are
     byte-duplicate 1-arg `getInstance(macAlg)` (oracle-authoring anomaly,
     recorded); arithmetic constraints `offset < len`,
     `length(output1) > outOffset` present (`:73-75`), untranslated.
   - `MacSpec.mop:176-179`: `event f3 after(byte[] output, int outOffset)`
     uses `target(m)` with **`m` bound by no formal**; `i1`/`i2` gate on
     `condition(validate(GENERATED_KEY, key))` (`:75,94`) while the spec's own
     i2 comment states reads must sit in bodies to avoid exactly the
     suppression-FP shape.
   - `SecureRandomSpec.mop:169-177`: the `end` state block lists
     genSeed/setSeed1-3/next1/next3/ints and **omits `next2`** (the `init` and
     `unsafeInit` blocks both have it); `c3`'s body is `sr = r;` **only**
     (`:42-47`) while the gh101 comment (`:136-139`) claims "c3, g4 and
     setSeed3 … Each reports in its own body" — **comment/code divergence
     confirmed**. `SecureRandom.cryptsl`: ORDER `Ins, Seeds?, Ends*`; REQUIRES
     `randomized[seed]`; ENSURES includes `randomized[numB]` of `ne =
     next(numB)`.
   - `KeyPairGeneratorSpec.mop`: `String algorithm;` uninitialized (`:26`);
     `validate(int)` opens `switch(algorithm)` (`:28-35`); `initError`
     pointcut covers `initialize(int)` only (`:113-120`); `gen` is the
     disjunctive `(call(generateKeyPair()) || call(genKeyPair()))` (`:123`);
     ere `(g3* g1 | g3* g2) initError* (init1|…|init4) initError* gen`; `@fail`
     has **no `__RESET`**.
   - `SignatureSpec.mop:119-131`: `s1`/`s2` declare `call(public byte
     Signature.sign(...))`; `v1`/`v2` mark VERIFIED over the boxed boolean
     return.
   - `MessageDigestSpec.mop`: 9-entry list incl. 3 no-hyphen aliases +
     `.toUpperCase()` folding in the guards; `g4`'s condition tests the
     monitor **field** (`currentAlgorithmInstance`), not the argument; the raw
     rule's constraint is 6 literals **including MD5/SHA-1/SHA-224** (so both
     are SAFE under api30 — the oracle-shift warning); rule declares **no
     reset** and the spec has **no reset event** (D-S12 removal verified at
     both ends); `pre_len > pre_off`, `len > off` present in the rule,
     untranslated.
3. **`__RESET` census (executed)**: grep over the five frozen monitors —
   `this.reset();` present in MAC/MDG/SRD/SIG `@fail`, **absent only from
   KPG** (0 vs 1); same at spec level. KPG's fail state is absorbing.
4. **MAC f3 dispatch (artifact)**: `MacSpec_f3Event(byte[],int)`
   (`MacSpecRuntimeMonitor.java:1684`) sets `matchedEntry = MacSpec__Map`
   (the process-global root), FindOrCreates an anonymous monitor when none
   exists, and fires `event_f3` on the **whole monitor set** — broadcast.
5. **Platform member facts** (javap over `unzip`-extracted classes of the
   frozen android-30 jar — never `-classpath`): `Signature`: `public final
   byte[] sign()`, `public final int sign(byte[],int,int)` — **no `byte
   sign()` member exists**; `SecureRandom`: `nextInt`/`ints` **not declared**
   (inherited from `java.util.Random`), `protected final int next(int)`
   (uncallable by apps); `Mac`/`KeyPairGenerator`/`Signature` all declare
   `getInstance(String, Provider)`; `Mac.doFinal(byte[],int)` is void;
   `KeyPairGenerator` declares both `genKeyPair()` and `generateKeyPair()`;
   `MessageDigest` declares `reset()` and `clone()`.
6. **REF-D-04 confirmation grep (executed)**: `SecureRandomSpec.mop` g2 =
   `getInstance(String, ..) && args(alg, *)` (`:62-63`) and g4 =
   `getInstance(String, ..) && args(alg)` exact-1 (`:76-77`) — both varargs
   `args()`-narrowing instances, as batch C rev. 2 flagged; KPG carries the
   round's `|| call(` disjunct (`:123`). **New cross-round finding from the
   same grep**: the first-disjunct mechanism also occurs textually in
   **batch B** specs — `CipherInputStreamSpec.mop:28` (`read() ||
   read(byte[])`) and `CipherOutputStreamSpec.mop:27` (`write(int) ||
   write(byte[])`). The batch C REF-D-04 sweep covered the two
   batch-C-measured mechanisms (varargs; nested-type), not this one — routed
   to the global phase (§6.7), closed rounds not reopened.
7. **gh101 registers read**: `predicate_edges.csv:47` (`MacSpec … REQUIRES
   generatedKey … present`), `:74-75` (`randomized[randInt]/[randIntInRange]
   present`), `:81` (`verified … present`); `data/gh101/README.md:148-153`
   **declares the file anchored to CrySL 1.5.2** with the premise that
   "`ORDER`, `REQUIRES`, `ENSURES` and `NEGATES` describe API semantics and do
   not vary" — a premise **falsified by the batch D rules themselves** (api30
   Mac has no generatedKey; api30 SecureRandom's `ne` is the protected
   `next(int)`; api30 Signature says `verified[sign]`). Absence greps re-run:
   `next2` (only inventory rows), `byte Signature`, `target(m)`,
   `switch(algorithm)`, `Provider)` — 0 hits each in `data/gh101/`.
   `divergence_record` rows `ff425611fcba` (reset removal), `151e53aa8e1f`
   (initError), `029a4511565f` (unsafeInit) located and read.
8. **J1-D — walk test (executed)**: `juiz_walk_batchD.py` hash-asserts the
   five frozen monitors, machine-parses transition tables + fail/match
   category states, verifies them against the agents' published tables
   (11+8+9+15+12 event rows all equal), checks the structural facts (§0.3/0.4)
   and walks 21 decisive traces with CrySL-ORDER status labeled (reading A):
   **46/46 checks PASS** (`juiz_walk_batchD_output.txt`). This includes the
   round-mandated independent product verification on **two specs both
   directions**: SRD (`c1 nB nB` FP direction; `c1 nB s1` FN direction — both
   confirmed) and KPG (`g1 initError gen` FP direction — ORDER-complete,
   monitor fails; `g1 initError init1 gen` FN direction — single-Inits
   violated, monitor match) — Alfa's product results confirmed where walked;
   plus MAC/MDG/SIG carrier, key-gate, invisible-creation, safe-path and
   sign-truncation walks.
9. **J2-D — independent end-to-end drive (executed, 3 byte-identical reps,
   sha `e136cf4c…`)**: `juiz_JuizDriveD.java` compiles the five frozen
   monitors against the production jars (javac exit 0 — no batch-C
   KGN-NAOCOMPILA analogue, verified) and drives the generated static event
   methods in the verified merged-advice order with real JDK objects:
   - **D1**: `initialize(int)` as first event on an unseen KeyPairGenerator ⇒
     `java.lang.NullPointerException` thrown **to the caller** from BOTH
     `init1Event` and `initErrorEvent` — the fail-crash executed.
   - **D2**: `new SecureRandom(); nextBytes ×3` ⇒ InvalidSequenceOfMethodCalls
     at calls 2 and 3 (`expecting=unknown`) — the batch headline FP on the
     canonical trace.
   - **D3**: unsafe `getInstance("NativePRNG")` (g1-then-g4) + consumers ⇒
     **exactly 1 UnsafeAlgorithm, 0 InvalidSeq** (the no-pairing
     counter-design) AND `RANDOMIZED[bytes-from-unsafe-instance]=true` while
     `RANDOMIZED[sr]=false` — the overgrant and the object/material split in
     one run.
   - **D4**: safe alg + unmarked key ⇒ i1 suppressed, doFinal accused
     (1 InvalidSeq, 0 specific) — the extra-oracle key gate FP.
   - **D5**: `g1("HMAC-SHA256")` + marked key + full path ⇒ **0 errors +
     acceptance** on an algorithm the raw 12-literal list rejects — the
     monitor-level alias FN (REF-D-02 keeps it major-pending: the enabling
     call throws on measured platforms).
   - **D6**: MDG unsafe carrier ⇒ UnsafeAlgorithm + InvalidSeq **pair at each
     of 3 distinct consuming sites** (6 records), message literally
     `expecting one of {SHA-256, SHA-384, SHA-512}` against the 9-entry
     enforced list.
   - **D7a/D7b**: KPG bad-size-then-generate ⇒ InvalidKeySize then spurious
     InvalidSeq at gen (delayed pairing); bad-then-corrected-then-generate ⇒
     InvalidKeySize only + **accepting + GENERATED_KEY_PAIR granted** — the FP
     and FN faces of initError placement, plus the exact reconciliation of
     Beta's PASS with Gama's delayed pairing (§2.3).
   - **D8**: `VERIFIED[Boolean.TRUE]=true`, `VERIFIED[signBytes]=false` — the
     wrong-slot write executed.
   - **D9**: one `MacSpec_f3Event` with no Mac argument ⇒ foreign monitor mX
     advanced to **accepting** (`isInAcceptingState` false→true without any
     doFinal) and innocent mY accused (1 InvalidSeq) — the broadcast executed
     in both directions.
10. **G2 arithmetic re-verified**: coenable[fail] = n·(2ⁿ−1) exact for all
    five (22 517 / 2 040 / 4 599 / 49 140 / 491 505) and the 17-event
    extrapolation 17·131 071 = 2 228 207 — Beta's `beta_coenable_summary.txt`
    conferred (SRD 12.57 s / 1.61 GB, 3 reps; RuntimeMonitor byte-identical).
11. **Beta weave measurements conferred**: `beta_capture_matrix.txt` —
    `sig_sign0`/`sig_sign3` NEITHER (dead both halves); `mac_gi2p`/`kpg_gi2p`/
    `sig_gi2p` NEITHER; `mdg_gi2p`/`srd_gi2p` both halves; `kpg_genkp`
    ajc-only (dex FN); `srd_nextint0`/`ints*` ajc-only; `srd_gi1` fires g1+g4
    on ajc and is WRAPPED on dexlib2. `beta_probes_summary.txt` (P1/P2/P3 all
    exit 0) conferred.

Epistemic labels: **fato medido** (my execution this session), **observado em
artefato** (cited file:line), **inferido**, **histórico** (pre-repair
errors.csv — hypothesis generator only).

## 1. Conflict / convergence matrix

Routes counted, not agents. Full per-claim record in the CSV.

| # | Phenomenon / claims | Alfa | Beta | Gama | Conflict | Discriminating test | Resolution | Residual |
|---|---|---|---|---|---|---|---|---|
| 1 | **FEN-C-GETS-INVISIVEL** (← FEN-D-GETINSTANCE-PROVIDER, FEN-C-UNSAFE-2ARG, FEN-D-G4-ARITY) — getInstance domains with zero/suppressed events: `(String,Provider)` invisible in MAC/KPG/SIG; unsafe 2-arg invisible in MAC/MDG/KPG/SIG/SRD — 12 FAIL | FAIL crit ×4 + major (SRD) | FAIL major→crit ×3 + SRD major ×2 | FAIL crit ×2 + major (SRD) | Severity; classification INCORRETA vs OMITIDA | Judge JAVAP (members exist); W invisible-creation walks; D1 (KPG route = crash); capture matrix conferred | FAIL — INCORRETA/OMITIDA; critical in MAC/MDG/KPG/SIG (executed FP storm / crash), major in SRD (safe side is the batch's only Provider-covered one; only the unsafe half is blind, halves disagreeing in opposite directions on it). Cipher-repaired class (`b532e439f79a`) unrepaired in 3 specs, unregistered | Android replay G10-{MAC,KPG,SIG}-1 |
| 2 | **FEN-C-CARRIER-SEQFAIL** (← FEN-C-PAIRING-IMEDIATO, FEN-D-UNSAFE-RESIDUE) — carrier state + mandatory successor ⇒ specific error + spurious InvalidSeq, same call — 10 FAIL, 4 specs (NOT SRD) | FAIL crit ×4 + SET census | FAIL major→crit ×2 | FAIL crit ×3 | Names + severity only — same records | Judge W carrier walks ×4; D6 executed (MDG); D3 executed the SRD **counter-design** (zero pairing) | FAIL — INCORRETA critical ×10. H2 **closed**: immediate form in MAC/MDG/KPG/SIG, delayed in KPG; SRD decouples by design — the strongest proof yet that the family is a design choice, not a limitation (3b.11b's kept-residue framing further weakened) | G10 replay (historical attribution only) |
| 3 | **FEN-SRD-NEXTBYTES-FP** (← FEN-D-SRD-NEXTBYTES) — `next2` missing from `end` ⇒ FP on 2nd+ nextBytes, nextBytes-after-setSeed, after-nextInt | FAIL crit | — | FAIL crit + INC (historical) | None | Judge: spec text (`:169-177`) + effective row + **D2 executed** + W minimal trace | FAIL — INCORRETA critical. jca-inherited (twin `end` block identical minus setSeed3), live both campaigns, unregistered. **The batch headline FP** — canonical conformant usage | H-SRD-1 attribution → G10-SRD-1 |
| 4 | **FEN-KPG-NPE** (← FEN-D-KPG-NPE) — `switch(null)` in validate ⇒ NPE to the app on initialize(int) after invisible creation (incl. the safe Provider route) | FAIL crit | (route via KPG-04) | FAIL crit | None on mechanism; classification question (spec vs toolchain) | **Judge D1 executed the NPE from both event methods**; SRC (uninitialized field, no try/catch anywhere in dispatch); JAVAP (Provider route conformant) | FAIL — INCORRETA **(spec)**, critical, the audit's first **fail-crash** class (§2.4): the switch is spec-authored code; monitor-creation-at-first-event is standard parametric semantics; no toolchain component converts it. Placed under G4 with G5 as enabling route (§5 preamble) | Woven-APK replay G10-KPG-1 |
| 5 | **FEN-SIG-SIGN-VOID** (← FEN-D-WRONG-RETURN, FEN-D-DEAD-RETURN-TYPE) — `byte`-typed sign pointcuts can never match; Signs channel dead on BOTH halves | FAIL crit | FAIL crit | FAIL crit | None | Judge JAVAP re-derivation; W sign-truncation walk (never accepts); Beta NEITHER rows + drives conferred | FAIL — INCORRETA critical ×3. jca-inherited, unregistered; the internal `returning(byte[])`-beside-`byte` inconsistency silently accepted by generators (fail-open note, D-batchC-1). Third instance of the dead-return-type class (TMF gtm1, SSL engine) | — |
| 6 | **FEN-MAC-F3-UNBOUND** (← FEN-D-UNBOUND-EVENT, FEN-D-F3-UNBOUND) — `target(m)` unbound: ajc silently dead (exit 0 + Xlint) / dexlib2-and-monitor broadcast via global root — halves DISAGREE | FAIL crit ×2 | FAIL crit | FAIL crit | None (two agents ran ajc independently, same result) | Judge SRC (no `m` formal; descriptor); artifact dispatch (§0.4); **D9 executed the broadcast both directions** | FAIL — INCORRETA critical ×4; fail-open at §4's letter (D-batchC-1); per-object isolation broken in both directions wherever f3 is emitted; jca-inherited (twin f2), unregistered | ART half |
| 7 | **FEN-MAC-KEYGATE-EXTRA** (← FEN-B-GATE-EXTRA-ORACULO, FEN-D-COND-SUPPRESS) — extra-oracle GENERATED_KEY read as suppressing condition | FAIL crit | FAIL major→crit | FAIL crit | Severity | Judge SRC (raw REQUIRES has no such clause); **D4 executed the displaced FP** | FAIL — INCORRETA critical ×3. jca-inherited; the register row asserting the clause "present" is the 1.5.2 anchor (see #14); the spec's own sibling comment names the trap | 1.5.2-anchor decision (researcher) |
| 8 | **FEN-SRD-C3-SILENT** (← FEN-D-CTOR-SILENT) + false gh101 comment | FAIL crit | FAIL major→crit (OMITIDA) | (PASS on the g4 side only) | Severity; Beta OMITIDA vs Alfa INCORRETA | Judge SRC: c3 body `sr = r;` only; comment `:136-139` claims it reports — **comment/code divergence confirmed by me** | FAIL — critical ×2 (classifications compose: the branch exists and is silent = INCORRETA; the diagnosis channel is missing = OMITIDA facet). Gama's PASS (GAMA-SRD-05) is the g4/setSeed3 side — no conflict | — |
| 9 | **FEN-SRD-RANDOMIZED-OVERGRANT** (← FEN-D-RANDOMIZED-WRITER) — material marks granted from violating/unsafe instances | FAIL crit ×2 | (writer-exists PASS, scoped) | FAIL major→crit | Beta PASS vs others FAIL — **no conflict, units compose**: existence/binding of the writer is real (D2/D3 confirm writes) AND its unconditionality is extra-oracle | **Judge D3 executed the decisive split** (material true / object false) | FAIL — INCORRETA critical ×3. **Set-level consequence declared (§6.1)**: object-level RANDOMIZED reads are sound (constraint-coupled at creation); material-level (byte[]/int) reads are unsound — this decides the pilot/A/B residual uncertainty along exactly that split | CrySL predicate-semantics footnote (declared) |
| 10 | **FEN-KPG-INITERROR-PLACEMENT** + **FEN-KPG-INIT2-SUPPRESSED** + **FEN-KPG-FAILSINK** / **FEN-A-STALE-FLAGS** — the KPG complex | FAIL crit/major ×3 | KPG-01 PASS (correction route) | FAIL crit/major ×3 | Beta PASS vs Alfa/Gama FAIL on initError | **Judge D7a/D7b executed BOTH routes on one table**; W walks both inclusions; __RESET census | Resolved as complementary routes (§2.3): the gh101 `initError*` repair holds on the correction route (Beta's PASS stands, scoped) and **converted the immediate pairing into a delayed one** (bad-size-then-gen FP; multi-init FN) — placement INCORRETA critical; fail-sink cascade + stale-category critical (executed); init2 suppression critical (FN+FP executed) | Register lacks the gen-unreachability consequence |
| 11 | **FEN-C-EMPTY-LABEL** (← FEN-D-EMPTYLABEL-LIVE) — H4 "but found ." live | FAIL major→crit | — | FAIL crit ×3 + major | Severity | mac_c/mdg_a/sig_a conferred; judge W invisible-creation walk; D1 shows KPG crashes instead | FAIL — critical; **H4 closed**: live mechanism in exactly the three pilot-named classes via creation-at-consume; task 8.1's zero-post-GH100 measurement covered only the weaver route; per-line historical attribution deferred | G10-SIG-1/G10-MAC-1 |
| 12 | **FEN-SET-firstcall-disjunct** (← FEN-D-FIRST-DISJUNCT) — dexlib2 drops `genKeyPair()`; **FEN-SET-VARARGS-ARGS-IGNORED** on SRD g2; **FEN-SET-DECLARED-ONLY** on next3/ints | — | FAIL crit ×2 + major | FAIL major→crit | Gama register-based vs Beta executed | Beta EXECUTED all three on the production path (DX drives, 3 reps); judge REF-D-04 grep + JAVAP declared-members check; mechanisms source-verified in batch C | FAIL — INCORRETA toolchain, jar-robust. **Dimension-7 status: the two production weave halves now disagree on FIVE measured mechanisms** (varargs g2; g4 arity — opposite directions on one spec; first-disjunct; declared-only; f3 dead-vs-broadcast) | ART half; global-phase G5 declaration (§6.7) |
| 13 | **FEN-C-WHITELIST-EXTRA** — MDG folding (6 resolvable FN witnesses) vs MAC 6 alias spellings (none resolvable) | FAIL crit (MDG) + minor (MAC) | — | — | Internal severity split | Folding probe conferred (witnesses resolve on host JDK); **judge D5 executed the MAC monitor-level FN** | FAIL — MDG critical (REF-D-02 satisfied: realizable enabling calls); MAC **major-pending** (REF-D-02: all six spellings throw on measured platforms; monitor-level FN executed by me; Android-BC probe named — exactly the batch C rev. 2 KGN-alias line) | Android-BC probe |
| 14 | **FEN-D-REGISTER-ANCHOR-DRIFT** (← FEN-D-REGISTER-ORACLE) — register rows contradicting the raw api30 oracle | FAIL major | — | FAIL major | Whether a declared anchor absolves the rows (batch C BETA-SET-06 shape?) | **Judge re-read README `:148-153`**: the file IS declared 1.5.2-anchored — rows accurate under their declared semantics (no BETA-SET-06 repeat); but the declaration's premise ("REQUIRES/ENSURES do not vary") is **falsified by ≥3 batch D rows**, judge-verified against the raw rules | FAIL — INCORRETA major ×2, **confirmed with scope**: the defect is the falsified invariance premise + no row-level anchor marking, which sustains the extra-oracle gate (#7) against register-based review | Researcher: anchor column or api30 re-derivation |
| 15 | **FEN-SIG-VERIFIED-WRONGSLOT** — VERIFIED on the boxed Boolean | FAIL major | — | FAIL minor (DIVERGÊNCIA_EQUIVALENTE) | Classification + severity | **Judge D8 executed** (TRUE marked; bytes not); raw rule read (`verified[sign]`) | FAIL — INCORRETA major ×2 (Gama reclassified: absence-of-reader is not semantic equivalence; latent → major per the FEN-SET-GENERATEDKEY-2A-CASA precedent) | Reader-appearance watch |
| 16 | **MDG tension** — Beta "the clean spec" vs Alfa language/constraint FAILs | FAIL crit ×3 | PASS ×2 | FAIL crit/major | Apparent | Dimensions compared claim-by-claim | **No conflict — compose**: Beta measured capture (both halves faithful, the only Provider-capturing spec, D-S12 correct) and safe-path drives; Alfa/Gama measured language/constraints vs the raw oracle (carrier FP, invisible unsafe-2-arg, folding FNs). MDG is simultaneously the batch's best capture plane and a REPROVADA vs the raw oracle | — |
| 17 | **SRD position across agents** — "decouples" (Gama) vs "avoidability proven" (Alfa) | PASS (SRD-07) | — | PASS (SRD-05) | None | Judge D3 | Same fact, two roles: the unsafeInit sink eliminates pairing (executed, 1 specific error, 0 spurious) AND trades it for silent admission (c3 silence, Seeds-after-Ends FN) — the "two repair philosophies" (GAMA-SET-22) both measured inside one spec. Used as the INCORRETA ground for #2, and as the FN ground for #8/#3 — no double-counting: different traces | — |
| 18 | **Overturned claims** — GAMA-MDG-03 (g4 field-condition), BETA-KPG-05 (prepared* unread) | (MDG-07 PASS; KPG-08 PASS) | FAIL→ | FAIL→ | Real conflicts | Advice order re-verified in the batch D `.aj` by judge (+ batch C WrapperEmitter source); registers re-read | **2 overturns FAIL→PASS** (§2.1) — no counterexample existed in either | — |
| 19 | **Positive closures** — §8 targets and repairs that held | PASS | PASS | PASS | None | D3/D5/D7b/D8 + W safe walks + conferred agent runs | PASS — FIDELIDADE: D-S12 reset removal (fidelity to the raw oracle, both ends verified); `!macced` projection design + deferred marking; D-S13 residues measured and registered; SIG body reads (G9-clean); SIG 20-literal set; KPG literal constraints + preparedDH; SRD constraint-coupled object writer + no-pairing design; MDG capture plane; generation determinism 20/20; all five monitors compile standalone | — |

## 2. Detailed resolutions

### 2.1 Overturned positions (judge-verified evidence, none by vote)

| Claim | From → To | Why |
|---|---|---|
| GAMA-MDG-03 | FAIL → **PASS** (DIVERGÊNCIA_EQUIVALENTE_COMPROVADA) | Batch C rev. 2 GAMA-KGN-05 precedent applies verbatim: g1-before-g4 merged-advice order is fixed in the descriptor (judge re-verified in the batch D `.aj:43-45`) AND `WrapperEmitter` fires merged advices in descriptor order (`WrapperEmitter.java:246-249`, judge-verified at source in batch C); per-object creation gives every monitor a fresh `""` field. Executed benign (mdg_b; my safe walks). Fragility recorded as a threat, aligned with ALFA-MDG-07 (PASS). |
| BETA-KPG-05 | FAIL → **PASS** (LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA) | The preparedDSA/RSA/EC non-reads are **registered** capability-absent omissions (predicate_edges capability-absent bucket + the spec's Group-5 comment). Same unit as ALFA-KPG-08 (PASS); batch C neverTypeOf precedent: a registered limitation with no live witness resolves PASS/LIMITAÇÃO — it blocks total adherence, not the claim. |

Resolution rule made explicit for the record (consistent with batch C):
registered limitations **without** a live measured witness resolve
PASS/LIMITAÇÃO; registered limitations **with** a measured witness (D-S13
ByteBuffer FN, Byte/Integer-cache marks) stay FAIL/LIMITAÇÃO — the witness is
a real divergence vs the raw oracle; registration removes only the
"unregistered" aggravation.

### 2.2 Severity harmonizations (17 decisions: 15 up, 2 capped by precedent; severity does not move scores)

Upward, per executed evidence within the phenomenon (§4's letter; batch C
rev. 2 practice): BETA-MAC-02, BETA-KPG-04, BETA-SIG-02 (gets-invisível →
critical; on KPG the route ends in the executed crash); BETA-MAC-05
(key gate → critical, judge D4); BETA-MAC-06, BETA-KPG-03 (carrier →
critical); BETA-SRD-04 (c3 silence → critical, executed FN of the rule's only
REQUIRES); GAMA-KPG-04 (fail-sink cascade + stale flags → critical, executed);
GAMA-KPG-05 (init2 suppression → critical, executed FN+FP); GAMA-KPG-06
(first-disjunct → critical — Beta executed the dexlib2 FN Gama had left as a
named pendency); GAMA-SRD-03 (overgrant → critical, aligned with
ALFA-SRD-04/SET-11); ALFA-KPG-06 (initError placement → critical — I executed
both directions, D7a/D7b); ALFA-SRD-03 (Seeds-after-Ends → critical — FN
executed on a realizable trace; batch C rev. 2 FEN-SSL-ENGINE-LOOP precedent,
no rarity carve-outs); ALFA-SET-14 (empty label → critical, aligned with
GAMA-SET-27); BETA-SET-04 (fail-open probes → critical, **D-batchC-1**).

Capped by binding precedent: ALFA-MAC-12 minor → **major-pending** (REF-D-02:
the six MAC alias spellings throw on every measured platform; my D5 executed
the monitor-level FN; the Android-BC probe decides a return to crítica in the
global phase — the exact batch C rev. 2 KGN-alias disposition). GAMA-SIG-04
minor → **major** with reclassification to INCORRETA (§2.5): latent wrong-slot
write, FEN-SET-GENERATEDKEY-2A-CASA severity precedent.

### 2.3 The KPG initError reconciliation (Beta PASS × Alfa/Gama FAIL — routes)

Beta's KPG-01 (PASS) and Gama's kpg_b / Alfa's KPG-T3 (FAIL) measure
**different routes over one transition table**, both re-executed by me on the
frozen monitor: `initError` loops in the pre-init state (row `{4,4,2,3,4}`),
so bad-size → corrected-size → generate reaches match with no spurious record
(D7b — the repair is real on the correction route), while bad-size → generate
**without** correction fails at `gen` (row `gen[2]=4`; D7a) although
`Gets, Inits, Generators` is ORDER-complete (the rule's i3 with a bad size is
still an Inits; the size is a CONSTRAINT). And bad-then-corrected is TWO
Inits — a rule ORDER violation the monitor **accepts and rewards with
GENERATED_KEY_PAIR** (D7b, FN). Verdict: the gh101 repair **converted** the
immediate pairing into a delayed FP and opened an FN — Gama's formulation is
adopted; Beta's PASS stands scoped to the correction route.

### 2.4 The KPG NPE — classification and gate placement (round-mandated)

Classification: **INCORRETA (spec defect), severity crítica, new failure
class: fail-crash.** Grounds, each judge-verified: the `switch(algorithm)` is
**spec-authored** Java (`KeyPairGeneratorSpec.mop:28-35`) over a field only
creation events initialize; a monitor born at a consuming event is standard
RV-Monitor parametric semantics (FindOrCreate — same machinery in all five
specs, only KPG dereferences an uninitialized field inside a condition); no
generated or runtime component adds a catch (dispatch chain read; D1 shows
the exception escaping the static event method to the caller). It is
therefore not a toolchain defect — the toolchain faithfully executes the
spec's own code — though the generated code's *absence of any handler* is
recorded as an aggravating toolchain-shape note for G6. Gate placement under
§16: **G4** (Cláusulas/bindings — the §3 bindings row's "condition
inalcançável" criterion extended a fortiori: the condition does not merely
fail to bind, its evaluation crashes the caller on rule-conformant input),
with **G5** as the enabling route (the `(String,Provider)` capture omission
creates the unseen-creation state) and a **G9** note (a crash annihilates all
subsequent diagnostics from the process). A crash on conformant usage
outranks an FP; the woven-frame step remains INFERIDO (no catch exists —
G10-KPG-1 named).

### 2.5 Classification corrections (positions unchanged)

- GAMA-SIG-04 → INCORRETA: "equivalent-in-effect while terminal" is absence
  of a reader, not semantic equivalence; the raw rule marks the sign bytes.
- GAMA-SRD-04 → LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA: the argument-slot marking
  is literal to the raw rule's `randomized[numB]` (the oracle's own oddity —
  `ne` is protected and uncallable); the cache-identity half is the
  registered D-S13 family. The extra-alphabet unit (nextInt/ints as events)
  stays INCORRETA in ALFA-SRD-06 — units composed, no conflict.

### 2.6 FEN unification (register of record for this round)

Canonical ← merged aliases: **FEN-C-CARRIER-SEQFAIL** ← FEN-C-PAIRING-IMEDIATO,
FEN-D-UNSAFE-RESIDUE; **FEN-MAC-F3-UNBOUND** ← FEN-D-UNBOUND-EVENT,
FEN-D-F3-UNBOUND; **FEN-MAC-KEYGATE-EXTRA** ← FEN-B-GATE-EXTRA-ORACULO,
FEN-D-COND-SUPPRESS; **FEN-C-GETS-INVISIVEL** ← FEN-D-GETINSTANCE-PROVIDER,
FEN-C-UNSAFE-2ARG, FEN-D-G4-ARITY; **FEN-C-EMPTY-LABEL** ←
FEN-D-EMPTYLABEL-LIVE; **FEN-SRD-NEXTBYTES-FP** ← FEN-D-SRD-NEXTBYTES;
**FEN-SRD-C3-SILENT** ← FEN-D-CTOR-SILENT; **FEN-SRD-RANDOMIZED-OVERGRANT** ←
FEN-D-RANDOMIZED-WRITER; **FEN-SIG-SIGN-VOID** ← FEN-D-WRONG-RETURN,
FEN-D-DEAD-RETURN-TYPE; **FEN-KPG-NPE** ← FEN-D-KPG-NPE;
**FEN-SET-firstcall-disjunct** ← FEN-D-FIRST-DISJUNCT; **FEN-D-CACHE-BOXING**
← FEN-D-BOXING; **FEN-MDG-LABEL-STALE** ← FEN-D-MSG-SET-ERRADO;
**FEN-D-REGISTER-ANCHOR-DRIFT** ← FEN-D-REGISTER-ORACLE; **FEN-SET-FAIL-OPEN**
← FEN-SET-FAILOPEN. Claim-level remaps: ALFA-MAC-09 → FEN-D-S13-BYTEBUFFER;
GAMA-KPG-05 → FEN-KPG-INIT2-SUPPRESSED; GAMA-SIG-04 →
FEN-SIG-VERIFIED-WRONGSLOT. Kept distinct (different repair points):
FEN-KPG-FAILSINK vs FEN-A-STALE-FLAGS (absorbing state vs stale category
flags — both executed in the KPG drives, composition noted);
FEN-KPG-INITERROR-PLACEMENT vs FEN-C-CARRIER-SEQFAIL (delayed vs immediate;
GAMA-KPG-03 spans both, filed under the carrier canonical, the delayed half
cross-referenced). Per-phenomenon counts are generated from
`fenomeno_id_final` only (D-batchB-1).

### 2.7 Dimension-assignment pendencies (D-piloto-4 — recorded, not re-assigned)

- Alfa filed 3 claims (MAC-03, MAC-13, SIG-08) under the semantic-model label
  "equivalência paramétrica/ciclo de vida", which is not a §6 score
  dimension; scored under `bindings_clausulas` (their decisive evidence
  measures parameter-to-object binding — the §3 bindings row) with the
  assignment recorded here as a pendency, not corrected ex post.
- FEN-MAC-F3-UNBOUND spans four filed dimensions (captura/bindings/
  toolchain/equivalência) — the per-phenomenon table is the corrective lens.
- FEN-SET-firstcall-disjunct: Beta `captura_eventos` × Gama
  `toolchain_android`; FEN-SET-VARARGS: Beta `captura_eventos` here vs batch
  C's `toolchain_android` — same phenomenon, different filed dimensions
  across rounds; recorded.

### 2.8 REF-D-03 check (executed)

Declared-but-unordered events: none in batch D — every event of the five
api30 rules appears in ORDER through its aggregate (Mac: Finals ∋ f3; MDG:
DWOU = d2; KPG/SIG: all aggregates ordered; SRD: Ins/Seeds/Ends cover
c1/c2/g1/g2/gI/s1/s2/gS/ne/nB — grep over the EVENTS/ORDER sections). No
batch D claim depends on the reading choice REF-D-03 rules INCONCLUSIVE.

### 2.9 D-piloto-2 tests

(a) folding×JCA executed (Alfa probe, 3 reps; conferred; MDG witnesses
decide #13); (b) `part()` N/A — no `part()` in any of the five rules'
constraint sections (Alfa grep, spot-checked by me).

## 3. Consolidated classification

**Resolution totals**: 123 claims → **39 PASS, 81 FAIL, 3 INCONCLUSIVE**;
**54 critical FAIL claims across 21 critical phenomena** (34 FEN groups with
FAILs — verbatim table in `juiz_rescore_batchD_output.txt`). Position
changes: 2 FAIL→PASS (§2.1), 0 PASS→FAIL; 17 severity decisions (§2.2); 2
classification corrections (§2.5). No counterexample was dismissed; no
resolution used agent counting.

**Critical phenomena (21) with provenance** (REF-C-05; every entry checked
against the `jca` twins and the gh101 registers this session; provenance
routes G11/G13 accountability and excuses nothing — the oracle is the api30
rule):

| FEN | Specs | State | Provenance |
|---|---|---|---|
| FEN-C-GETS-INVISIVEL | MAC MDG KPG SIG (crit) SRD (major) | INCORRETA/OMITIDA — FP storms / crash route / FNs executed | jca-inherited; Cipher-repaired class (`b532e439f79a`) unrepaired in MAC/KPG/SIG; unregistered |
| FEN-C-CARRIER-SEQFAIL | MAC MDG KPG SIG (not SRD) | INCORRETA — executed same-call pairing ×4 + delayed (KPG) | jca-inherited shapes; KPG form reshaped by gh101 (immediate→delayed conversion); partially registered (3b.11b) |
| FEN-C-EMPTY-LABEL | MAC MDG SIG (KPG crashes; SRD label-free) | INCORRETA — "but found ." executed in all three | jca-inherited mechanism; H4 closed live |
| FEN-MAC-F3-UNBOUND | MAC | INCORRETA — ajc dead at exit 0 (fail-open) / broadcast executed (D9) | jca-inherited (twin f2 byte-same), unregistered |
| FEN-MAC-KEYGATE-EXTRA | MAC | INCORRETA — displaced FP executed (D4); specific channel silenced | jca-inherited; register row anchored to 1.5.2 |
| FEN-SIG-SIGN-VOID | SIG | INCORRETA — dead on both weave halves (measured); acceptance + SIGNED unreachable | jca-inherited, unregistered; generator fail-open note |
| FEN-SRD-NEXTBYTES-FP | SRD | INCORRETA — FP on canonical usage executed (D2) | jca-inherited (twin end block), unregistered, live both campaigns |
| FEN-SRD-C3-SILENT | SRD | INCORRETA — FN executed; gh101 comment claims the opposite | body jca-inherited; false comment gh101-authored |
| FEN-SRD-SEED-AFTER-END | SRD | INCORRETA — FN executed (walked) | jca-inherited |
| FEN-SRD-RANDOMIZED-OVERGRANT | SRD (+SET) | INCORRETA — grant from unsafe instance executed (D3) | jca-inherited (body-write shape) |
| FEN-KPG-NPE | KPG | INCORRETA (spec) — **fail-crash**, executed (D1) | jca-inherited (twin validate identical), unregistered |
| FEN-KPG-FAILSINK | KPG | INCORRETA — absorbing-fail cascade executed | jca-inherited (@fail identical) |
| FEN-A-STALE-FLAGS | KPG (generator shape) | INCORRETA — suppressed-event re-fire executed | generated-code shape (cross-round batch A phenomenon, first instantiated) |
| FEN-KPG-INIT2-SUPPRESSED | KPG | INCORRETA — FN+FP pair executed | jca-inherited, unregistered |
| FEN-KPG-INITERROR-PLACEMENT | KPG | INCORRETA — FP (D7a) and FN (D7b) executed | gh101 form (repair residual); consequence unregistered |
| FEN-SET-firstcall-disjunct | KPG (set) | INCORRETA toolchain — executed FN (DX-KPG-2); halves disagree | toolchain (WrapperEmitter.findFirstCall), jar-robust; also textually present in batch B CIS/COS (§6.7) |
| FEN-SET-VARARGS-ARGS-IGNORED | SRD (set) | INCORRETA toolchain — executed FP on the correct call (DX-SRD-1); halves disagree | toolchain (recurrence from batch C), jar-robust |
| FEN-C-WHITELIST-EXTRA | MDG (crit); MAC (major-pending) | INCORRETA — 6 resolvable FN witnesses (MDG); monitor-level FN executed, realizability pending (MAC) | jca-inherited folding/aliases; gh99/gh101-registered as variants — registered ≠ approved |
| FEN-D-PREPAREDHMAC-GUARANTEED-FIRE | MAC/SET | INCORRETA — guaranteed-fire composition executed (MAC-T8) | gh101 read (faithful) × batch A unwritable writer |
| FEN-D-KEYPAIR-EDGE | KPG/SET | INCORRETA — mark delivered at 1 FP per pair access, executed (CHAIN-T1) | inherited (KeyPairSpec c1 — batch B REPROVADA shape, writer side) |
| FEN-SET-FAIL-OPEN | SET | INCORRETA — P1/P2/P3 all exit 0 (crítica per D-batchC-1) | toolchain (generators) |

**Major (non-critical) phenomena**: FEN-D-REGISTER-ANCHOR-DRIFT (falsified
invariance premise; no row-level anchor marking); FEN-SIG-VERIFIED-WRONGSLOT
(executed wrong-slot write, latent); FEN-MAC-G2-EXTRA (extra-oracle 2-arg
capture; oracle's own g1=g2 anomaly recorded); FEN-D-ARITH-OMITIDA (MAC+MDG
arithmetic constraints untranslated, unregistered); FEN-SRD-EXTRA-ALPHABET
(nextInt/ints extra-oracle events; boxed-Integer cache marks);
FEN-SET-DECLARED-ONLY (next3/ints dead on the device path);
FEN-SET-STATIC-DEAD-TARGETS (6 statically-listed dynamically-dead rows);
FEN-SET-DEDUPE (per-site amplification / per-line masking re-executed);
FEN-D-S13-BYTEBUFFER (measured, registered). **Minor**: FEN-D-CACHE-BOXING,
FEN-MDG-LABEL-STALE, FEN-C-ACCEPT-END, FEN-SET-STATIC-JCA-DEFAULT.

**DIVERGÊNCIA_EQUIVALENTE_COMPROVADA (PASS)**: ALFA-MDG-07 / GAMA-MDG-03
(g4 field-condition, by descriptor advice order — both paths, fragility
recorded). **LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA**: PASS — ALFA-MDG-09
(DIGESTED terminal), ALFA-KPG-08/BETA-KPG-05 (prepared* capability-absent,
D-S14), ALFA-KPG-09 (GENERATED_KEY_PAIR writer-only); FAIL (measured
witnesses) — ALFA-MAC-09/BETA-MAC-03 (ByteBuffer FN), BETA-MAC-04/
BETA-SRD-05/GAMA-SRD-04 (cache boxing).

**FIDELIDADE_DEMONSTRADA highlights** (what the falsification could not
break, all conferred or re-executed): the D-S12 `reset` removal (fidelity to
the raw oracle at both ends — §8 adversarial target closed); Mac's `!macced`
projection design with deferred marking (§8 target closed); SIG's body-read
repair (1 specific, 0 spurious — the design MacSpec i1/i2 lacks) and exact
20-literal list; KPG's literal constraint sets + preparedDH read + measured
generatedKeyPair chain delivery; SRD's constraint-coupled object-level
RANDOMIZED writer and the no-pairing unsafeInit design (D3); MDG's capture
plane (both halves, ByteBuffer + Provider); generation determinism (19/19
byte-identical regeneration); five-of-five standalone monitor compilation.

**INCONCLUSIVE (3, outside every denominator, named pendencies)**:
BETA-SET-06 (ART/device — the halves now disagree on five measured
mechanisms pre-ART; the pendency is which semantics the device realizes),
BETA-SET-07 (android-37.0 production-default jar), GAMA-SRD-02 (H-SRD-1
historical attribution → G10-SRD-1; the current-artifact mechanism itself is
judge-executed).

## 4. Descriptive scores (pre-registered weights; verbatim from `juiz_rescore_batchD.py`)

Raw weighted sum is the score of record (D-batchA-1); per-spec over that
spec's resolved claims only; SET separate; dimension as filed (spelling
normalization only, §2.7); INCONCLUSIVE outside the denominator.

| Unit | ling(20) | capt(20) | bind(15) | pred(15) | tool(15) | diag(10) | repr(5) | **Raw (of record)** | Status |
|---|---|---|---|---|---|---|---|---|---|
| MAC | 0.00 (0/2) | 4.00 (1/5) | 4.29 (2/7) | 4.29 (2/7) | 0.00 (0/1) | 0.00 (0/3) | — (unattainable 5) | **12.57** | COMPLETE |
| MDG | 8.00 (2/5) | 13.33 (2/3) | 9.00 (3/5) | 15.00 (1/1) | — (15) | 2.50 (1/4) | — (5) | **47.83** | COMPLETE |
| KPG | 5.00 (1/4) | 4.00 (1/5) | 3.75 (1/4) | 12.00 (4/5) | 0.00 (0/3) | 0.00 (0/2) | — (5) | **24.75** | COMPLETE |
| SRD | 4.00 (1/5) | 0.00 (0/6) | 5.00 (1/3) | 7.50 (3/6) | — (15) | 0.00 (0/1 +1INC) | — (5) | **16.50** | INCOMPLETE (1 INC) |
| SIG | 6.67 (1/3) | 0.00 (0/5) | 15.00 (4/4) | 7.50 (2/4) | — (15) | 0.00 (0/1) | — (5) | **29.17** | COMPLETE |

**SET score** (separate): pred 3.75 (1/4), tool 0.00 (0/2 +2INC), diag 0.00
(0/5), repr 5.00 (5/5) → **raw 8.75**; unattainable weight 55; labeled
derived reading 8.75/45 = 19.44%; INCOMPLETE (2 INC).

**Batch-D aggregate** (context only; 105 spec claims, SET excluded): ling
5.26 (5/19), capt 3.33 (4/24), bind 7.17 (11/23), pred 7.83 (12/23), tool
0.00 (0/4), diag 0.91 (1/11 +1INC), repr 0.00 (0/0) → **raw 24.51**;
INCOMPLETE (1 INC).

**Mandatory labels**: descriptive score ≠ probability of correction ≠
verdict; never rounded to 100; no score opens a gate; SRD, SET and the
aggregate are INCOMPLETE. Context readings: (i) **MAC 12.57 is the lowest
unit score of the audit to date** — every dimension with a live defect,
`ling` 0/2; (ii) `diagnostico` is near-zero across all six units for the
fourth consecutive round (pairing, unknown-expecting, empty labels, dedupe);
(iii) MDG's 47.83 coexists with REPROVADA — its capture/predicate planes are
clean while its constraint plane carries measured FNs (composition, §1 #16);
(iv) claim counts overstate convergence (FEN-C-GETS-INVISIVEL alone carries
12 claims) — use the per-phenomenon table.

## 5. Per-spec verdicts (covered scope: G2, G3, G4, G5, G7, G9)

**Operative gate rule** (REF-B-05): a gate fails when its pre-registered
criteria (`pre_registro.md` §3, protocol §16) are met; a critical
INCORRETA/OMITIDA inside the gate is one sufficient trigger, not the only one.

**G5 scope (both halves, REF-C-03 annotations)**: batch D G5 evidence covers
BOTH weave halves (Beta ajc 1.9.25.1 + production dexlib2 over frozen
android-30; Gama's independent ajc probe; judge javap and conferred
matrices). **G5 FAILs are jar-robust** (unbound `target(m)`; `byte`-typed
sign pointcuts vs `byte[]`/`int` members; varargs `args()` ignored;
first-disjunct drop; declared-only member index — all jar-independent
mechanisms). **Member-matching PASS halves are android-30-pinned**
(BETA-SET-07 pendency). **Dimension-7 status**: the two production weave
halves now measurably disagree on **five** mechanisms across the audit
(batch C: varargs, nested-type; batch D: f3 dead-vs-broadcast, first-disjunct,
declared-only, plus SRD g4-arity disagreeing in the opposite direction on the
same spec) — only ART execution (G6/G10) can determine which semantics the
device realizes.

### MacSpec — **REPROVADA** (covered scope)

| Gate | Result | Grounds |
|---|---|---|
| G2 | PASS | clean deterministic generation (0.46+1.65 s; 11 events; coenable exact) |
| G3 | **FAIL** | carrier FP executed on rule-ORDER-conformant trace (W; MAC-T2) — critical; key-gate makes conformant traces fail (D4); complete rule words through f3 unobservable on the ajc path (FN) |
| G4 | **FAIL** | extra-oracle GENERATED_KEY suppressing condition (D4, critical); two arithmetic constraints OMITIDA, unregistered (major); 6 alias spellings (major-pending, REF-D-02) |
| G5 | **FAIL** | f3 dead on ajc at exit 0 / broadcast on dexlib2 — halves disagree, both wrong (critical, D9 + two independent ajc probes, D-batchC-1); `(String,Provider)` and unsafe 2-arg getInstance invisible (critical) |
| G7 | **FAIL** | PREPARED_HMAC guaranteed-fire edge (faithful read × batch-A-unwritable writer — set-level guaranteed FP, MAC-T8, critical); key-gate is an extra-oracle predicate read (critical); MACED D-S13 residues measured (registered); the `!macced` projection design itself faithful (PASS half recorded) |
| G9 | **FAIL** | same-call pairing (critical); empty "but found ." labels live (MAC-T5); every sequencing record `expecting=unknown`; displaced accusations (D4) |

### MessageDigestSpec — **REPROVADA** (covered scope)

| Gate | Result | Grounds |
|---|---|---|
| G2 | PASS | clean generation (8 events) |
| G3 | **FAIL** | carrier FP executed (D6) — critical; invisible unsafe-2-arg route (MDG-T4) — critical; safe-path core incl. reuse cycles faithful (PASS half recorded; the batch's only direction-2 language PASS) |
| G4 | **FAIL** | case-folded 9-entry guard vs raw 6-literal set — **6 FN witnesses resolvable on the measured platform** (critical, REF-D-02 satisfied); arithmetic constraints OMITIDA, unregistered (major) |
| G5 | **FAIL** | the rule's unsafe 2-arg/Provider domain has zero events (conditions safe-only, g4 1-arg) — expected-event zero-fire with no counterpart (critical); member capture itself exhaustive on both halves incl. ByteBuffer and Provider (PASS half, android-30-pinned — best capture plane of the batch) |
| G7 | PASS | DIGESTED terminal registered (LIMITAÇÃO — blocks total adherence, not the gate); non-revoking @fail faithful (zero NEGATES); no extra-oracle reads; no writer defect |
| G9 | **FAIL** | pairing cascade per consuming site (D6, 2 780/2 871 historical cells consistent); message names a 3-entry set while enforcing 9 (D6 output literal); empty label live (mdg_a); `unknown` everywhere |

### KeyPairGeneratorSpec — **REPROVADA** (covered scope)

| Gate | Result | Grounds |
|---|---|---|
| G2 | PASS | clean generation; compiles standalone (judge-verified) |
| G3 | **FAIL** | initError placement diverges in both directions — FP at gen (D7a) and accepted double-Inits FN (D7b) — critical; carrier + H2 confirmed for the pilot's named KPG (critical); absorbing fail state (only spec without `__RESET`) cascades (critical) |
| G4 | **FAIL** | **FEN-KPG-NPE: condition evaluation throws NPE to the caller on rule-conformant input** (D1, critical — fail-crash class, placement per §2.4); bad keySize via `initialize(int,SecureRandom)` has no InvalidKeySize channel — FN+FP pair executed (critical); literal constraint sets themselves faithful (PASS recorded) |
| G5 | **FAIL** | `(String,Provider)` — a rule-conformant Gets — invisible, and it is the NPE trigger route (critical); `genKeyPair()` silently unwoven on production dexlib2 (first-disjunct, executed DX-KPG-2, critical, halves disagree); unsafe 2-arg invisible |
| G7 | **FAIL** | the only route from KPG's ENSURES to Signature costs 1 KeyPairSpec FP per pair access (CHAIN-T1, critical — batch B shape re-measured from the writer side; mark delivery itself works, no starvation); extra-oracle `@fail` remove present but inert (writer-only constant); preparedDH read + GENERATED_KEY_PAIR write faithful (PASS halves) |
| G9 | **FAIL** | immediate AND delayed pairing (kpg_a, D7a); stale-category re-fire on suppressed events (executed); `unknown` on every sequencing record; the NPE annihilates diagnostics on its route |

### SecureRandomSpec — **REPROVADA** (covered scope)

| Gate | Result | Grounds |
|---|---|---|
| G2 | PASS | **the round's stress point, measured and closed**: 15 events, coenable[fail] = 491 505 = 15·(2¹⁵−1) exact, 24.08 MB string, 12.57 s / 1.61 GB, 3 reps, byte-identical output — closes the fase0 "generator ceiling without raw output" gap; ≤ 17 |
| G3 | **FAIL** | `next2` missing from `end` ⇒ FP on the most common conformant usage patterns (D2 executed; spec-text + table + walk all judge-verified) — the batch headline, critical, inherited, unregistered; Seeds-after-Ends over-acceptance FN (walked, critical); extra-alphabet events occupy automaton positions |
| G4 | **FAIL** | c3 violating branch silent — the rule's ONLY REQUIRES violated with zero reports, and the gh101 comment claims otherwise (comment/code divergence judge-confirmed) — critical; boxed-Integer cache marks (D-S13 family) |
| G5 | **FAIL** | dexlib2 fires g2 on every legal 1-arg `getInstance("SHA1PRNG")` ⇒ FP on the correct call (varargs, executed, critical, jar-robust — REF-D-04 instance confirmed); unsafe 2-arg invisible on ajc (g4 arity) while dexlib2 catches it by the same bug — halves disagree in **opposite directions on one spec**; next3/ints dead on the device path (declared-only) |
| G7 | **FAIL** | RANDOMIZED material marks granted from violating/unsafe instances — set-wide FN feed (D3 executed, critical); object-level writer constraint-coupled and sound (PASS half — the split that decides pilot/A/B residuals, §6.1) |
| G9 | **FAIL** | 12 400 historical lines 100% `unknown`/InvalidSeq with the site profile matching the next2 FP (H-SRD-1, INC pending replay); displaced accusations on unsafe-2-arg routes; no pairing (the one clean G9 sub-item, recorded) |

### SignatureSpec — **REPROVADA** (covered scope)

| Gate | Result | Grounds |
|---|---|---|
| G2 | PASS | clean generation (12 events) |
| G3 | **FAIL** | the entire sign branch can never accept — conformant signing never reaches match and sign-position misuse is silent (W platform-view walk; critical); carrier FP executed (critical) |
| G4 | PASS | i1/i2/i4 reads in bodies exactly as the rule states (SIG-T4: 1 specific, 0 spurious — the G9-clean design); 20-literal set exact; update binding loss inert and registered |
| G5 | **FAIL** | `sign()`/`sign(byte[],int,int)` pointcuts declare return `byte` vs real `byte[]`/`int` — dead on BOTH halves (judge javap; capture matrix NEITHER; critical, jar-robust, D-batchC-1 fail-open note); `(String,Provider)` invisible (critical); verify branch captured faithfully (PASS half, android-30-pinned) |
| G7 | **FAIL** | SIGNED writer sits in dead events — unreachable, while the register lists the edge "present" (critical claim ALFA-SIG-01 covers the predicate loss; registered "terminal" bounds composition impact); VERIFIED written on the boxed Boolean instead of the rule's sign bytes (D8 executed, major, latent); generatedPrivkey/Pubkey reads faithful (PASS half) |
| G9 | **FAIL** | three records, three types, one `__LOC` on a single conformant call (sig_a); empty label live; re-initSign after unobserved sign ⇒ spurious InvalidSeq; `unknown` everywhere |

**Batch verdict line**: **5/5 REPROVADA in the covered scope** — every
gate-deciding defect anchored in evidence the judge executed (J1-D 46/46,
J2-D D1–D9, javap, source and register reads) or verified at source over the
frozen artifacts. Per protocol §16 the set cannot move toward `READY` from
this batch. Cumulative across the audit: **22/22 audited specs REPROVADA**
in their covered scopes (pilot 2, batch A 5, batch B 5, batch C 5, batch D
5). All 20 non-pilot specs of the round plan are now covered
(RandomStringPassword excluded by researcher decision).

## 6. Observations for the SET-level phase (protocol §19.5 — the next step)

The per-spec rounds are complete. The set-level phase (predicate composition,
`-merge` generation, descriptor, weaving, historical consolidation) inherits:

1. **Predicate-composition ledger (the RANDOMIZED split is the key)**:
   object-level RANDOMIZED reads (over SecureRandom objects) rest on a sound,
   constraint-coupled producer; material-level reads (byte[]/int — Iv, GCM,
   PBE, SecretKeySpec, PBEKeySpec, KeyGenerator, SSL, Cipher, c2/setSeed2)
   are satisfiable by rejected randomness (executed) — pilot/A/B downstream
   verdicts that consumed material marks carry a confirmed FN direction;
   those over objects do not. Second producer: SecretKeySpec.mop:26 (batch B
   scope, noted). Other edges: PREPARED_HMAC = guaranteed-fire (faithful
   batch D read × batch A unwritable writer — every parameterized `Mac.init`
   FPs); KPG→KeyPairSpec→SIG delivers the private-key mark at 1 KeyPairSpec
   FP per pair access (no starvation — the batch B REPROVADA shape measured
   from the writer side); dead writers: SIGNED (unreachable events),
   VERIFIED (wrong slot), DIGESTED/GENERATED_KEY_PAIR (terminal by design);
   extra-oracle reads to sweep set-wide: MAC GENERATED_KEY gate (+ batch C
   SSL RANDOMIZED read).
2. **Register anchor**: `predicate_edges.csv` is declared 1.5.2-anchored and
   its invariance premise is falsified by ≥3 measured rows (Mac generatedKey;
   SecureRandom randInt/randIntInRange; Signature verified). The set phase
   must not consume "present" verdicts without an anchor check; an api30
   re-derivation or a row-level anchor column is the repair.
3. **`-merge` generation and budget**: full 23-spec merge measured (javamop
   0.70 s / 174.8 MB; rv-monitor 28.08 s / 1.74 GB; per-spec `.rvm`
   byte-identical to merge outputs). SRD dominates (24.08 MB coenable
   string); the 17-event ceiling now has a measured basis (n·2ⁿ saturation,
   extrapolation re-computed) — the fase0 gap "teto do gerador sem output
   bruto" is CLOSED. Method note for replication: with `-merge`, javamop
   writes `<Spec>.rvm` beside the spec, not into `-d out`.
4. **Descriptor lint list for the set phase** (all measured this audit):
   unbound `target(x)` in an advice expression (MAC f3 → ajc-dead/broadcast);
   `call(...)` disjunctions (first-disjunct drop); `args()` narrowing under
   trailing `..` (ignored); inherited members vs declared-only index
   (next3/ints); nested types (batch C); return-type mismatches (javap every
   pointcut). Every one is silent at exit 0 — gate the pipeline on artifact
   inspection, not exit codes (D-batchC-1).
5. **Fail-crash sweep (new class)**: KPG's `switch(null)` is the audit's
   first crash-to-app defect. The set phase must sweep all 23 specs for
   spec-authored helpers that dereference/switch on creation-initialized
   fields reachable from conditions of consuming events (candidates: every
   `validate()`-style helper; any field read inside `condition(...)`).
6. **Historical consolidation inputs**: H2 CLOSED (immediate 4/5 + delayed
   KPG; SRD decouples by design); H4 CLOSED live (MAC/MDG/SIG
   creation-at-consume; task 8.1 covered only the weaver route); H5 → H-SRD-1
   (the 12 400 SRD lines' site profile matches the next2 FP, not the all-fail
   account; INC pending replay); MDG oracle-shift warning (5 891/6 048
   historical UnsafeAlgorithm lines are MD5/SHA-1 — SAFE under api30: any
   future drop is oracle change, not repair). Consolidated replay battery:
   G10-SRD-1, G10-KPG-1 (NPE crash), G10-KPG-2 (genKeyPair weave), G10-SIG-1,
   G10-MAC-1 + batch C's battery.
7. **Cross-round G5 declaration (carried from batch C rev. 2, extended)**:
   batch A/B G5 PASS halves remain **single-half evidence, not equivalence
   evidence**. Extension from my REF-D-04 grep: the first-disjunct mechanism
   — now *measured* in batch D (KPG) — occurs textually in batch B's
   `CipherInputStreamSpec.mop:28` and `CipherOutputStreamSpec.mop:27`
   (`read()`/`write` overload disjunctions); their dexlib2 halves are
   therefore suspect in the same class. Closed rounds are not reopened; the
   global phase adjudicates, together with the android-37.0 default-jar
   pendency and the ART half (which of the five divergent mechanisms'
   semantics the device realizes).
8. **Oracle-authoring anomalies for the researcher** (explicit scope
   reduction or oracle repair, never silent): Mac g1=g2 byte-duplicate 1-arg
   Gets (the Provider overload is arguably intended — the anomaly feeds
   FEN-C-GETS-INVISIVEL's MAC reading); SecureRandom `ne` = protected
   `next(int)` (uncallable — makes `randomized[numB]` unimplementable as
   written); the folding/alias family decision (MDG critical now; MAC and
   batch C KGN pending the Android-BC probe); the 1.5.2-vs-api30 anchor
   decision (#2); reset()/clone() oracle blind spots (real state changes both
   oracles ignore — recorded, out of scope).
9. **G13 must-close set from this round**: 54 critical claims (21 phenomena,
   §3), every major including the register-anchor family, the arithmetic
   omissions, FEN-SET-STATIC-DEAD-TARGETS' static/dynamic contradiction, and
   the three INCONCLUSIVEs' named pendencies.

## 7. Files (judge outputs of record, sha256)

```
see juiz_hashes_batchD.txt (generated beside this file) for the sha256 list:
juiz_sintese_batchD.md, juiz_claims_resolvidos_batchD.csv,
juiz_build_csv_batchD.py, juiz_rescore_batchD.py, juiz_rescore_batchD_output.txt,
juiz_walk_batchD.py, juiz_walk_batchD_output.txt,
juiz_JuizDriveD.java, juiz_driveD_rep1.txt (= rep2 = rep3, sha e136cf4c…)
```

- J2-D reps 2–3 are sha256-identical to rep 1 (repetition policy satisfied).
  Compile: the five monitors byte-identical to the manifest (no patches
  needed — all compile standalone); classpath = rv-monitor-rt `0fa65fbc…`,
  rvsec-core `7b4d72aa…`, rvsec-logger-csv `6787f411…`; run 3× from clean
  scratch working dirs.
- `juiz_walk_batchD.py` hash-asserts its inputs; set `BATCHD_GEN` to the
  directory containing the round `gen_<Spec>/out` artifacts to reproduce.
- One agent-CSV anomaly, handled without touching the file: `alfa_claims.csv`
  row ALFA-SRD-08 carries an unquoted comma inside `args(alg,*)` in
  `contraevidencia_procurada`, shifting its last four fields; the builder
  repairs the shift at parse time (assert-guarded) and the repair is
  documented in `juiz_build_csv_batchD.py`.
- Agent primary files consulted: all `batchD/alfa_*`, `beta_*`, `gama_*`;
  `generation_manifest.md`; frozen specs/rules; `data/gh101/*`; production
  sources and platform class bytes cited at file:line throughout; batch C
  rev. 2 record (closed) for binding precedents.

*Next step per protocol §15: adversarial refutation round against this
synthesis; the judge's decision becomes final only after answering each
objection. After that, protocol §19.5-6: the set-level verification phase
(§6 above) and the global judgment.*

## 8. Final decision after the refutation round

2026-08-09. Issued after responding to each of the 8 objections of the
independent reviewer (`refutacao_parecer_batchD.md`), as protocol §15
requires — responses in `juiz_respostas_refutacao_batchD.md` (outcomes: **8
accepted — 1 material (REF-E-01), 7 minor; 2 record-text/marker changes, 0
resolution/score/gate/verdict changes**). The reviewer independently
re-executed the builder (byte-identical CSV incl. the assert-guarded
ALFA-SRD-08 parse repair), the rescore (byte-identical; every sum re-derived
by hand), J1-D (46/46, byte-identical) and J2-D (independent recompile of the
five frozen monitors, output sha `e136cf4c…` = all three published reps), and
reported no objection reaching any verdict, gate, score or the
critical-phenomena inventory. The adjudication is nonetheless mine, objection
by objection, each re-verified before acting (including my own re-execution
of the REF-E-01 trap probe). Sections 1–7 above are the first synthesis
(rev. 1) and remain as record; **where wording or numbers diverge, this
section prevails** — the basis is rev. 2 of
`juiz_claims_resolvidos_batchD.csv`.

### 8.1 Final per-spec verdicts and gates (unchanged from §5)

| Spec | G2 | G3 | G4 | G5 | G7 | G9 | Verdict (covered scope) |
|---|---|---|---|---|---|---|---|
| MacSpec | PASS | FAIL | FAIL | FAIL ¹ | FAIL | FAIL | **REPROVADA** |
| MessageDigestSpec | PASS | FAIL | FAIL | FAIL ¹ | PASS | FAIL | **REPROVADA** |
| KeyPairGeneratorSpec | PASS | FAIL | FAIL ² | FAIL ¹ | FAIL | FAIL | **REPROVADA** |
| SecureRandomSpec | PASS ³ | FAIL | FAIL | FAIL ¹ | FAIL | FAIL | **REPROVADA** |
| SignatureSpec | PASS | FAIL | PASS | FAIL ¹ | FAIL | FAIL | **REPROVADA** |

¹ G5 annotation unchanged (§5 preamble): both weave halves measured this
round; FAILs jar-robust; member-matching PASS halves android-30-pinned; the
two halves measurably disagree on five mechanisms — which semantics the
device realizes is the ART pendency (G6/G10).
² G4 carries FEN-KPG-NPE under the declared a-fortiori extension of the
pre-registered "condition inalcançável" criterion (§2.4), with G5 as the
enabling route — the placement survived refutation (parecer §2.6).
³ G2 PASS records the measured generator-ceiling closure (SRD 15 events,
491 505 coenable sets, 12.57 s / 1.61 GB — the fase0 gap is closed).

**Batch verdict line (final)**: 5/5 REPROVADA in the covered scope
(G2/G3/G4/G5/G7/G9); per protocol §16 the set cannot move toward `READY`
from this batch. **Per-spec adjudication of the audit is COMPLETE: 22/22
audited specs REPROVADA in their covered scopes** (pilot 2, batch A 5,
batch B 5, batch C 5, batch D 5; RandomStringPassword excluded by researcher
decision, `fase0/manifesto.md`).

### 8.2 Corrections of record absorbed from the refutation (rev. 1 → rev. 2)

| # | Change | Origin |
|---|---|---|
| 1 | **`alfa_javap_android30_batchD.txt` declared host-JDK-contaminated** (JDK-fallback trap; 6 `SecureRandomParameters` hits vs 0 in the frozen jar; `sun.security.*` internals; trap reproduced by refuter and by me) — **unusable as android-30 evidence**. ALFA-SRD-08's 3-arg sub-assertion scoped FALSE/vacuous-on-android-30 in the rev. 2 CSV; resolution and severity stand on the independent g4-arity mechanism + executed FP. Blast radius checked: every other member fact citing the file was independently re-derived from extracted bytes (judge §0.5 + refuter). Judge-process correction adopted: trap-marker grep over agent javap artifacts before consumption (routed to the set-level phase checklist) | REF-E-01 (accepted, material) |
| 2 | §1 #11 Gama cell corrected to **crítica ×2 (GAMA-SET-27, GAMA-SIG-02) + major ×2 (GAMA-MAC-04, GAMA-MDG-02)**; per-phenomenon figures were already correct | REF-E-02 (accepted) |
| 3 | FEN-C-EMPTY-LABEL severity asymmetry rationale recorded (census/SIG rows crítica per executed FP companions; per-spec MAC/MDG rows major per §4 "diagnóstico inatribuível", held as filed) — rev. 2 justificativas + this section | REF-E-03 (accepted) |
| 4 | Generation-determinism figure unified: **20/20** artifacts byte-identical (primary evidence `beta_hashes.txt` regeneration section, re-counted by me; Beta's prose "19/19" is a report-level slip with no claim row attached; §3's "19/19" is corrected hereby) | REF-E-04 (accepted) |
| 5 | ALFA-MAC-12 `severidade_final` = **`major-pending`** machine-recorded in the rev. 2 CSV (Android-BC probe decides a return to crítica in the global phase) | REF-E-05 (accepted) |
| 6 | Provenance wordings scoped to mechanism: FEN-KPG-NPE "twin **mechanism-identical** (switch on creation-initialized field; twin has extra literal cases)"; FEN-MAC-F3-UNBOUND "twin f2 **header byte-same** (incl. unbound `target(m)`); bodies differ" | REF-E-06 (accepted) |
| 7 | Aggregate line now excludes empty dimensions and states unattainable weight (rescore rev. 2): AGG RAW 24.51, repr --/5, **unattainable weight 5**, labeled derived reading 25.80% | REF-E-07 (accepted) |
| 8 | BETA-SET-07 marked **HOST-EXECUTABLE** in the rev. 2 CSV and in §8.4's pendency list (production dexlib2 weave over the android-37.0 jar needs no device) | REF-E-08 (accepted) |

**Rev. 2 resolution totals (unchanged)**: 123 = **39 PASS / 81 FAIL / 3
INCONCLUSIVE**; **54 critical FAIL claims; 21 phenomena with ≥1 critical
FAIL; 34 FEN groups with FAILs**; 2 overturns FAIL→PASS; 0 PASS→FAIL; 17
severity decisions; all machine-generated by the rev. 2 builder + rescore and
independently recounted by the refuter.

### 8.3 Final scores (rev. 2 CSV; verbatim from `juiz_rescore_batchD.py` re-run)

| Unit | Raw weighted sum (of record) | Notes |
|---|---|---|
| MAC | **12.57** | COMPLETE; unattainable weight 5; labeled derived reading 13.23% — the audit's lowest unit score |
| MDG | **47.83** | COMPLETE; unattainable weight 20; derived 59.79% |
| KPG | **24.75** | COMPLETE; unattainable weight 5; derived 26.05% |
| SRD | **16.50** | INCOMPLETE — 1 INC; unattainable weight 20; derived 20.62% |
| SIG | **29.17** | COMPLETE; unattainable weight 20; derived 36.46% |
| SET (separate, D-piloto-4) | **8.75** | INCOMPLETE — 2 INC; unattainable weight 55; derived 19.44% |
| Batch-D aggregate (context) | **24.51** | 105 spec claims, SET excluded; INCOMPLETE — 1 INC; unattainable weight 5; derived 25.80% |

**Mandatory labels**: descriptive score ≠ probability of correction ≠
verdict; never rounded to 100; no score opens a gate; SRD, SET and the
aggregate are INCOMPLETE; severity changes (incl. `major-pending`) move no
score — rev. 2 sums are numerically identical to rev. 1, only the aggregate's
presentation changed (REF-E-07).

### 8.4 Open pendencies (named; final for the per-spec phase)

- **ART/device half** (BETA-SET-06, INCONCLUSIVE): the two production weave
  halves disagree on five measured mechanisms — which the device realizes is
  the open question (G6/G10 replay battery: G10-SRD-1, G10-KPG-1, G10-KPG-2,
  G10-SIG-1, G10-MAC-1 + batch C battery).
- **android-37.0 production-default jar** (BETA-SET-07, INCONCLUSIVE) —
  **HOST-EXECUTABLE** (REF-E-08): production dexlib2 weave over the
  android-37.0 jar on the frozen host toolchain; no emulator required; goes
  to the set-level phase's actionable list.
- **H-SRD-1 historical attribution** (GAMA-SRD-02, INCONCLUSIVE): device
  replay G10-SRD-1 decides whether the 12 400 historical SRD lines are the
  next2 FP.
- **Android-BC alias resolvability** (ALFA-MAC-12 `major-pending` + batch C
  KGN line): a JVM+provider probe or device run decides the return to
  crítica.
- **Researcher countersignature items** (pre_registro §7 — explicit scope
  reduction or repair, never silent): 1.5.2-vs-api30 register anchor (the
  falsified invariance premise, ≥3 rows); Mac g1=g2 duplicate-Gets oracle
  anomaly; SecureRandom protected-`ne` unimplementability; folding/alias
  family decision; reset()/clone() oracle blind spots.

### 8.5 Closing note — per-spec adjudication COMPLETE; hand-off to the set-level phase (§19.5)

With this decision the per-spec adversarial adjudication of the audit is
**COMPLETE: 22/22 specs REPROVADA in their covered scopes**, every batch
closed through refutation. The set-level/global phase opens with these routed
items (detail in §6):

1. **Cross-round single-half G5 declaration** (batch C rev. 2, extended by
   this round): batch A/B dexlib2-half G5 PASSes are single-half evidence;
   the batch-D-measured first-disjunct mechanism occurs textually in batch
   B's CIS (`:28`) and COS (`:27`) — adjudicate there, without reopening
   closed rounds.
2. **RANDOMIZED set-level consequence**: object-level reads sound;
   material-level reads unsound (executed split) — re-read every downstream
   randomized[] verdict of pilot/A/B under that split.
3. **Predicate-graph rebuild against api30 anchors** (register anchor drift)
   + the guaranteed-fire PREPARED_HMAC edge + the KPG→KeyPairSpec→SIG
   1-FP-per-access edge + dead writers (SIGNED, VERIFIED) + extra-oracle
   reads sweep (MAC GENERATED_KEY, batch C SSL RANDOMIZED).
4. **Ledger reconciliation under D-batchC-1**: count the fail-open family at
   §4's letter across batches A/B records (declared, not rewritten), per the
   batch C routing.
5. **Descriptor lint list + fail-crash sweep** (all 23 specs) and the
   `-merge` budget record (ceiling closed).
6. **Evidence-hygiene rule from REF-E-01**: trap-marker grep over any javap
   artifact before consumption in the set/global phases.

**PROPOSED deviation text (for `fase0/desvios.md`, orchestrator to
formalize — marked PROPOSED, not written by the judge)**: "D-batchD-1 —
platform-member evidence admissibility: a javap artifact is admissible as
platform evidence only if produced over class files extracted from the frozen
jar; artifacts bearing host-trap markers (types or members absent from the
frozen jar, e.g. `SecureRandomParameters`, `sun.security.*`,
`jdk.internal.*`) are inadmissible, and every agent javap artifact is swept
for those markers before the judge consumes it. Origin: REF-E-01 (batch D
refutation, accepted material). Changes no criteria, weights or gates —
fixes an evidence-admissibility rule the pre-registration did not cover."

*The set-level phase (§19.5 item 5) and the global judgment (item 7) are the
next steps; per-spec correction proposals (item 8) come only after them.*
