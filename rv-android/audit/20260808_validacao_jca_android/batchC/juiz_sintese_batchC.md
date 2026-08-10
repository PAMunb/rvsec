# JUDGE — Batch C synthesis (KGN, KMF, TMF, SSL, KST)

Judge (LLM-as-a-Judge), round "batch C" of the `jca_android` audit · 2026-08-09.
Role: evidence synthesis — **not** a formal oracle, **not** majority vote. A
reproducible counterexample cannot be dismissed by consensus; a reading-only
claim cannot close a toolchain claim; `INCONCLUSIVE` never becomes approval.
Rules in force: `fase0/pre_registro.md` §3/§4/§6 under D-piloto-1/2/3/4,
**D-batchA-1** (raw weighted sum is the score of record) and **D-batchB-1**
(every FAIL row carries `fenomeno_id_final`, builder-asserted) — all of
`fase0/desvios.md`. Batch B carried rules honored: REF-B-01 (judge evidence
under `batchC/` with hashes), REF-B-05 (gates fail by pre-registered criteria),
REF-B-07 (routes counted, not agents), REF-B-09, REF-C-03 (G5 jar-scope
annotation), REF-C-05 (provenance table for critical phenomena).

Inputs: `batchC/generation_manifest.md` (20 artifacts, hash-verified by me),
the three agent reports and CSVs (`alfa_*` 58 claims, `beta_*` 40, `gama_*`
36 — **134 total**), the frozen specs/rules, the gh101 registers, production
sources. Claim-by-claim resolution: `batchC/juiz_claims_resolvidos_batchC.csv`
(original columns preserved; `resolucao_juiz`, `classificacao_final`,
`severidade_final`, `fenomeno_id_final`, `justificativa_curta` appended).
Mechanical re-sum: `batchC/juiz_rescore_batchC.py` (§4 is its verbatim output,
`juiz_rescore_batchC_output.txt`).

Scope of this round's verdicts: gates **G2, G3, G4, G5, G7, G9**. G6, G8 and
G10 were not executed — they can only ADD defects, never remove demonstrated
ones. G0/G1 closed in fase 0; G11–G13 are fed by, not closed by, this round.
**New this round**: the ajc capture half is CLOSED for batch C claims (Beta
measured compile-time weave with aspectjtools 1.9.25.1, the Docker version) —
G5 speaks to both weave halves; ART execution remains the G6/G10 pendency.

## 0. Evidence the judge verified or executed himself

All commands reproducible; agent files untouched; judge work in scratch
`<scratchpad>/batchC/juiz/`, decisive files copied to `batchC/juiz_*` (§7).

1. **Freeze**: `sha256sum` over the 5 `.mop`, 5 `.cryptsl` (10/10 =
   `generation_manifest.md` = `fase0/manifest_hashes.md`) and the 20 round
   artifacts (20/20 = manifest). Harness jars: rv-monitor-rt `0fa65fbc…`,
   rvsec-core `7b4d72aa…`, rvsec-logger-csv `6787f411…` (= batches A/B).
   android-30 jar `96ccfdc8…`.
2. **Sources read end-to-end** (all five `.mop`, all five api30 `.cryptsl`).
   Confirmed directly: KST declares `KeyStoreSpec(KeyStore ks)` (`.mop:21`)
   while **every one of its 7 events binds `k`** (`:30-79`) — the spec
   parameter is bound by no event; KGN `Key generatedKey;` (`:28`) with no
   `java.security.Key` import; the 17-entry `safeAlgorithms` (11 rule literals
   + 6 `HMAC-`/`HMAC/` spellings, `:22-24`); KGN g3's condition reads
   `currentAlgorithmInstance`, not the argument (`:59`); KMF/TMF `g2 =
   getInstance(String, ..) && args(alg, *)` (`KMF:43-44`); SSL `engine`
   pointcut declares `void` return (`SSL:90`) and `g2` covers
   `(String,String)` only (`:39`); SSL protocol list compared via
   `toUpperCase()` (`:33,41,56,70`); SSL rule binds Init's third argument as
   `_` and `sr` appears in **no** event (`SSLContext.cryptsl:29,52`); rule
   FORBIDDEN `getDefault() => Gets` (`:16-18`) with no spec counterpart; KST
   rule `g2: getInstance(keyStoreAlg, _)` (`KeyStore.cryptsl:47`) vs the
   spec's 1-arg reuse of the name; rule events `scE/skE1/skE2` declared,
   absent from ORDER, absent from the spec; the `@fail` bodies of KGN/KMF/
   TMF/KST removing granted ENSURES marks.
3. **Oracle-wide greps (executed)**: `generatedCipher` in **0/33** api30
   rules; **zero NEGATES in the five batch rules** (NEGATES exists only in
   SecretKey/PBEKeySpec); `SecureRandom.cryptsl` carries `ENSURES
   randomized[this] after Ins` (writer exists for the batch's readers).
4. **Artifacts**: indexing shapes verified — KGN/KMF/TMF/SSL per-object
   `MapOfMonitor` keyed on the spec parameter (`_k_`, `_k_`, `_mf_`, `_ctx_`);
   **KST is the empty-binding global
   `Tuple2<KeyStoreSpecMonitor_Set,…> KeyStoreSpec__Map`** (`:498`,
   `AbstractSynchronizedMonitor` `:221`) — Alfa's report §0 statement "KST …
   properly parameterized" is **refuted by the artifact** (report-level
   erratum; no Alfa claim row asserted it). Transition tables and
   fail/match category states machine-parsed and equal to the published ones
   (J1-C check 1–4). `reset()` clears both category flags — the
   fail-then-suppressed-sibling path is benign, confirming Beta §2's
   stale-flag analysis at code level.
5. **Production toolchain sources** (file:line before accepting a mechanism):
   `WrapperEmitter.expandCallTarget` — trailing `..` accepts every overload
   with `paramFqns.size() >= fixedPrefix` (`WrapperEmitter.java:384`),
   `args(...)` is never consulted (grep over the file: no `args()` handling),
   and a merged wrapper "fires every advice bound to the call, in descriptor
   order" (`:246-249`) — the FEN-SET-VARARGS-ARGS-IGNORED mechanism, jar-robust;
   `TypeResolver.toDescriptor` does `replace('.','/')` with **no nested-type
   handling** (`TypeResolver.java:87-107`) — produces
   `Ljava/security/KeyStore/ProtectionParameter;` where DEX wants `$` —
   the FEN-SET-NESTED-TYPE-DESCRIPTOR mechanism, jar-robust;
   production `-merge` on both generator calls
   (`runtime_verification_generator.py:211,269`) — the KGN masking route;
   `ExecutionContext.setProperty(Property, Object)`/`validate` (`:102-120`) —
   single-slot store (no home for the rule's `generatedKey[key, alg]` second
   slot; `validate(P, null)` returns true after any null write).
6. **Platform facts from extracted class bytes** (javap over `unzip`-extracted
   classes of the frozen android-30 jar): `createSSLEngine()` returns
   `SSLEngine` (both overloads) — the void pointcut can never match;
   `SSLContext.getDefault()` exists; `SSLContext.getInstance` has 3 overloads
   incl. `(String, Provider)`; `KeyStore.getInstance` 2-arg overloads exist;
   `getEntry`/`setEntry` descriptors use `KeyStore$Entry`/
   `KeyStore$ProtectionParameter`; `KeyGenerator` has exactly 3 getInstance +
   5 init overloads.
7. **gh101 registers read**: `frozen_set_debt.md:220-250` (task 3b.11b) —
   the carrier residue is **registered as a deliberately kept residue**
   ("the accusation moves from the violating call to the next one"), with two
   D-S9 grounds; it does **not** register the same-call pairing with the
   specific error, and no researcher scope reduction is on file. One of its
   two grounds — "an absorbing state … would leave the set with two repair
   philosophies" — is **factually already the case**: `SecureRandomSpec`'s
   `unsafeInit` admits ALL consuming events (spec fsm `:148-186`; its own
   register row `029a4511565f` says so) while KMF/TMF `unsafeAlg` and SSL
   `unsafeProtocol` admit none (GAMA-SET-22 verified). `divergence_record.csv`
   row `b532e439f79a` — the **Cipher-only** repair of exactly the
   unsafe-2-arg capture class live in KGN/KMF/TMF/SSL/KST.
   `predicate_edges.csv:63` marks the SSL `generatedSSLEngine` edge `present`
   — accurate under the file's declared **pre-repair textual-wiring baseline**
   (`README.md`, re-read: "kept as authored"), while the dead pointcut that
   makes the writer unreachable is registered **nowhere** (incl.
   `predicate_omissions.csv:7`'s "terminal" framing). `conformance_record.csv`
   row 19 registers the SSL case-folding as aliases; row `53b2fdc6652b`
   registers the KGN HMAC spellings as carried artefacts — registered ≠
   approved (batch A/B precedent).
8. **J1-C — walk test (executed)**: `juiz_walk_batchC.py` hash-asserts the
   five frozen monitors, machine-parses their tables, verifies them against
   the agents' published tables, checks the indexing shapes, and walks 15
   decisive traces with each trace's CrySL-ORDER status labeled: **22/22
   checks PASS** (`juiz_walk_batchC_output.txt`).
9. **J2-C — independent end-to-end drive (executed, 3 byte-identical reps,
   sha `d3ac5f70…`)**: `juiz_JuizDriveC.java` compiles the five round
   monitors (KGN via the documented 1-line-import scratch copy — probe file)
   against the production jars and drives the generated static event methods
   in descriptor advice order with real JDK objects, 18 scenarios:
   - **S1–S5 (all five specs)**: constraint-only misuse on a rule-ORDER-
     conformant trace ⇒ the specific error (UnsafeAlgorithm/UnsafeProtocol/
     InvalidKeyStoreType) **and** a spurious `InvalidSequenceOfMethodCalls
     (expecting=unknown)` on the **same call, same `__LOC`** (records differ
     only by type — surviving dedupe jointly), plus the post-`__RESET` delayed
     FP at the rule's own optional event (S1b/S2b). TMF executed with the
     campaign string "X509" ("but found X509.").
   - **S6**: two individually conformant interleaved KeyStores ⇒ **5 spurious
     InvalidSeq** on the global monitor; after `load(A)` **neither** A nor B
     validates (field-marking + immediate-erasure compound).
   - **S7**: A's granted `GENERATED_KEY_STORE` erased by B's `@fail` (shared
     field) ⇒ fully conformant TMF over A gets `UnsatisfiedConstraint`.
   - **S8**: real `KeyStore.getInstance("PKCS12", provider)` (rule-conformant
     g2, no spec event) ⇒ spurious InvalidSeq at load + displaced
     `UnsatisfiedConstraint` in conformant KMF; `validate(ks2)=false` (stale
     field marked instead).
   - **S9**: `load,[setKeyEntry unobserved],store` ⇒ accusation displaced to
     store; captured `se1` control clean.
   - **S10/S11**: 2nd getKeyManagers/getTrustManagers (genuine ORDER
     violation) ⇒ `@fail` revokes the just-handed-out array's granted ENSURES
     (rules carry **zero NEGATES**) ⇒ chained `UnsatisfiedConstraint` at SSL
     init — executed for **both** KMF and TMF (closes ALFA-TMF-07's
     symmetry-only route); the 2-arg remove's per-object precision confirmed
     (kms1/tms1 survive).
   - **S12**: fully conformant SSL init with fresh `SecureRandom` ⇒ 1
     `UnsatisfiedConstraint` — the extra-oracle randomized read FP.
   - **S13**: three REQUIRES violated at one init ⇒ **1 record** survives
     dedupe (key-managers clause).
   - **S14**: real `SSLContext.getInstance("TLS", provider)` + init (fully
     conformant) ⇒ empty-label `UnsafeProtocol ("but found .")` + InvalidSeq.
   - **S15**: real `SSLContext.getInstance("tls")` resolves; spec accepts
     (toUpperCase), raw literal set rejects ⇒ 0 records = executed FN; 2nd
     `createSSLEngine` ⇒ 0 records = executed Engine? cardinality FN.
   - **S16/S17**: KGN AES `init(64)` and `getInstance("HMAC-SHA256")` ⇒ 0
     records = executed FNs (keySize implication; raw 11-literal list).
   - **S18 (positives)**: KGN conformant lifecycle → match + GENERATED_KEY
     marked; KGN i2 with unmarked SecureRandom → exactly 1 specific error, 0
     spurious; TMF two-factory isolation (tA survives tB's fail); full
     captured KST→KMF→TMF→SSL chain with sr=null → 0 records.
10. **KGN compile probe (executed)**: `javac` on the **frozen** artifact →
    exit 1, `cannot find symbol: class Key` (`juiz_kgn_compile_probe.txt`);
    agrees with Alfa's and Gama's independent probes; generators exited 0
    (fail-open); `-merge` masking verified at source (§0.5).
11. **Beta weave measurements conferred**: `beta_capture_matrix.txt` (ajc
    `-showWeaveInfo`) and `beta_weave_all.out`/`beta_dexdrive_run1.out` —
    SSL engine 0 join points on BOTH paths; KMF/TMF 1-arg wrapper fires
    g1,g3,g2 on dexlib2 while ajc suppresses g2 (`args(alg,*)` honored);
    KST getEntry/setEntry UNTOUCHED on dexlib2, woven by ajc — matching the
    source mechanisms of §0.5 and my table-level walk (J1-C check "g1,g2 ⇒
    fail").

Epistemic labels: **fato medido** (my execution this session), **observado em
artefato** (cited file:line), **inferido**, **histórico** (pre-repair
errors.csv — hypothesis generator only).

## 1. Conflict / convergence matrix

Routes counted, not agents. Full per-claim record in the CSV.

| # | Phenomenon / Claims | Alfa | Beta | Gama | Conflict | Discriminating test | Resolution | Residual |
|---|---|---|---|---|---|---|---|---|
| 1 | **FEN-C-CARRIER-SEQFAIL** (unified with Gama's FEN-C-PAIRING-IMEDIATO and Beta's four `*-UNSAFE-RESIDUO`) — carrier state + mandatory successor ⇒ specific error + spurious InvalidSeq on the SAME call of a rule-ORDER-conformant trace — 15 FAIL claims, 5 specs | FAIL crit ×5 (+1 diag major) | FAIL major ×4 | FAIL crit ×5 | Names + severity only — **same records** (verified: one mechanism, one set of executed records per spec) | Judge S1–S5 + J1-C walks; register 3b.11b read | **One phenomenon.** FAIL — INCORRETA critical (4 Beta claims harmonized → critical). Partially registered (3b.11b registers the delayed accusation, NOT the same-call pairing; no researcher scope reduction). One D-S9 ground factually false (§0.7) | G10 replay battery (historical attribution only) |
| 2 | **FEN-C-DELAYED** — post-`__RESET` FP at the rule's own optional event — GAMA-TMF-02 | (folded into #1 counts) | — | FAIL major | Unit split vs #1 | S1b/S2b executed by judge | FAIL — INCORRETA critical (harmonized; batch B FEN-PBK-RESIDUO class, executed on conformant trace). Kept as its own phenomenon (distinct repair point: reset semantics) | — |
| 3 | **FEN-C-GETS-INVISIVEL** (unified with FEN-C-UNSAFE-2ARG, FEN-SSL-G2-PROVIDER-OMIT) — getInstance with zero events: 2-arg unsafe suppressed without counterpart (KGN/KMF/TMF), SSL safe `(String,Provider)` uncaptured — 9 FAIL | FAIL crit ×4 | FAIL major (SSL) | FAIL crit/major ×4 | Severity | Judge S14 (real Provider-overload call, 2 records on conformant trace) + tmf_c conferred + tables walked | FAIL — INCORRETA/OMITIDA critical ×9 (4 harmonized). The **Cipher-repaired class** (b532e439f79a) live in 4+ specs, unregistered | Android-provider variants |
| 4 | **FEN-KST-G2-OMITIDA** — rule's entire 2-arg Gets alternative untranslated (name reused for unsafe-type 1-arg) | FAIL crit | FAIL major | FAIL major | Severity | Judge S8 executed the chain FP on a fully conformant program | FAIL — OMITIDA critical ×3 (2 harmonized); GAMA-KST-04 remapped to this FEN (its omission unit) | — |
| 5 | **FEN-KST-MONITOR-GLOBAL** (≡ FEN-KST-GLOBAL) + **FEN-KST-ERASURE** — spec param `ks` never bound ⇒ process-global broadcast; wrong-object marking; cross-object ENSURES erasure | (report erratum: called it "properly parameterized"; no claim) | FAIL crit ×2 | FAIL crit ×2 | Alfa's report text vs artifact | Judge J1-C check 5 (Tuple2, no MapOfMonitor) + S6/S7 executed | FAIL — INCORRETA critical ×3 (+ erasure critical). **New sub-shape for the standing check: parameter declared, never bound** — invisible to the census signature. Alfa erratum recorded (§2.5) | Device replay G10-KST-1 |
| 6 | **FEN-SET-VARARGS-ARGS-IGNORED** — dexlib2 expands `(String, ..)` onto the 1-arg overload and ignores `args(alg, *)`; ajc honors it ⇒ **first measured ajc×dexlib2 semantic divergence**; spurious InvalidSeq on every correct 1-arg `getInstance("PKIX")` on the dexlib2 path | — | FAIL crit ×3 | — | Single lane | Mechanism judge-verified at `WrapperEmitter.java:334-395`; table effect walked (J1-C); Beta DX drives conferred | FAIL — INCORRETA critical (toolchain), jar-robust. G5 dexlib2 half fails for KMF/TMF; dimension-7 implication in §5 preamble | ART half (which semantics the device realizes) |
| 7 | **FEN-SET-NESTED-TYPE-DESCRIPTOR** — `toDescriptor` slash-mangles nested types ⇒ KST getEntry/setEntry silently unwoven on dexlib2, woven by ajc | — | FAIL crit ×2 | — | Single lane | Source verified (`TypeResolver.java:87-107`) + javap `$` descriptors + Beta TR probe conferred | FAIL — INCORRETA critical (toolchain), jar-robust; silent FN + spurious fail on the `sE, Stores` route | ART half |
| 8 | **FEN-SSL-ENGINE-VOID** (≡ MORTO ≡ DEAD) — void-return pointcut can never match ⇒ whole Engine channel dead on BOTH weave halves; `generatedSSLEngine` writer unreachable; static list still carries the member (GAMA-SET-20) | FAIL crit (+SET-05 major) | FAIL major | FAIL crit (+SET-20 major) | Severity | Judge javap (return `SSLEngine`); Beta both-halves weave conferred; S15b executed the FN in the complex | FAIL — INCORRETA critical ×3 + register-absence major (ALFA-SET-05 confirmed **with scope**: edges:63 is accurate under the file's baseline semantics; the dead pointcut is registered nowhere) + §13 contradiction major | — |
| 9 | **FEN-SSL-ENGINE-LOOP** — `engine` loops at end vs rule `Engine?` — ALFA-SSL-05 (major) × GAMA-SSL-05 (minor) | FAIL major | — | FAIL minor | Severity | **Judge S15b executed the FN** (2nd engine silent) | FAIL — INCORRETA critical ×2 (both harmonized: §4 has no rarity carve-out; FN executed). Oracle-bias note recorded (Engine? strictness vs real apps) — bias registered, oracle stands raw. ALFA-SSL-05's FEN remapped here (cardinality unit ≠ dead-pointcut unit) | — |
| 10 | **FEN-SSL-GETDEFAULT-OMITIDA** — FORBIDDEN clause untranslated, unregistered | FAIL crit | — | FAIL major | Severity | Judge javap (member exists); 0-hit register greps | FAIL — OMITIDA critical ×2 (harmonized; pilot CIP-17 precedent: FORBIDDEN omitted with no register = critical) | — |
| 11 | **FEN-SSL-RANDOMIZED-EXTRA** — spec enforces RANDOMIZED on the argument the rule binds `_` (sr bound by no event) — gh101-introduced | FAIL crit | — | — | Single route | Rule read by judge; **S12 executed the FP** on a fully conformant trace | FAIL — INCORRETA critical. Production realizability narrowed (SecureRandom rule ENSURES randomized[this] after Ins — §0.3) but not removed (capture gaps, unmonitored sources); pending researcher scope reduction (batch B PBK precedent) | Researcher countersignature |
| 12 | **FEN-C-WHITELIST-EXTRA** — KGN 6 alias spellings; SSL case-folded acceptance — vs raw literal sets | FAIL crit ×2 | — | FAIL major | Severity; register status | Judge S15a (real `getInstance("tls")` accepted silently) + S17; conformance rows 19/`53b2fdc6…` read | FAIL — INCORRETA critical ×3 (GAMA-KGN-03 harmonized). Pilot REF-04 rule: under the raw oracle folding/alias acceptance is FAIL; registered ≠ approved | KGN alias resolvability on Android BC (declared) |
| 13 | **FEN-KGN-KEYSIZE-OMITIDA** — `alg=AES ⇒ keySize∈{128,192,256}` transcribed nowhere | FAIL crit | FAIL minor | FAIL major | Severity | Judge S16 executed the FN | FAIL — OMITIDA critical ×3 (2 harmonized; §4 letter: FN executed on realizable trace; the platform's own InvalidParameterException recorded as magnitude context, not a carve-out) | — |
| 14 | **FEN-C-REMOVE-CASCADE** — `@fail` revokes granted ENSURES; zero NEGATES in the five rules; chain FP into SSL | FAIL crit ×3 | (2-arg remove precision PASS claims) | (KST instance via #5) | Beta PASS vs Alfa FAIL — **no conflict, units compose**: per-object *precision* of the 2-arg remove is real (S10/S11/S18c: sibling marks survive) AND the *revocation semantics itself* is extra-oracle (S10b/S11b chain FP) | Judge S10/S11 executed both halves; 0-NEGATES grep | FAIL — INCORRETA critical ×3; ALFA-TMF-07's symmetry route closed by direct execution (S11) | Which arm a real app exercises (G10) |
| 15 | **FEN-KGN-NAOCOMPILA** (≡ NOCOMPILE) — frozen artifact does not compile standalone; generators exit 0 | FAIL major (toolchain) | — | FAIL major (reprodutibilidade) | Dimension assignment only (D-piloto-4 pendency, recorded) | **Judge probe executed** (exit 1, same symbol); `-merge` masking source-verified | FAIL — INCORRETA major ×2; new fail-open shape (generation clean, artifact non-compilable); G2-decisive for KGN | Per-spec production build (G10-KGN-1) |
| 16 | **FEN-SET-GENERATEDKEY-2A-CASA** — `generatedKey[key, alg]` second slot has no home in the store API (writer side) | FAIL crit ×2 | — | — | Cross-batch severity consistency | `ExecutionContext.setProperty(Property,Object)` judge-read | FAIL — INCORRETA **major** ×2 (harmonized ↓ to the batch B severity of the same phenomenon: latent, no executed witness; cross-batch FN candidate for G11) | Cipher-side reader test (other batch) |
| 17 | **FEN-KST-ENTRIES-OMITIDAS** — scE/skE1/skE2 declared by the rule, unobserved | FAIL crit | — | FAIL major | Severity; oracle reading | Judge S9 (displaced accusation executed; control clean) | FAIL — OMITIDA **major** ×2 (ALFA-KST-04 harmonized ↓): the FN half depends on the CogniCrypt semantics of declared-but-unordered events — a NEW named oracle-semantics pendency; the displaced-accusation half holds under either reading | Oracle semantics resolution |
| 18 | **FEN-SET-DEDUPE** — 3 clauses, 1 record (worst instance) | — | — | FAIL major ×2 | Single lane | **Judge S13 executed** (1 of 3 survives) | FAIL — INCORRETA major; batch B mechanism re-verified | Survivor order under dexlib2 |
| 19 | **FEN-SET-FAIL-UNKNOWN** + FEN-C-ACCEPT-END + FEN-C-NULL-POLLUTION + FEN-KST-LOAD-TIMING + FEN-KST-NULL-KEY-MARK + FEN-TMF-GTM-INVISIVEL + FEN-SET-FAIL-OPEN | FAIL minor/major | FAIL minor/major | FAIL major | None | S1–S11 outputs (unknown everywhere); J1-C accept-end walk; ExecutionContext null semantics read; Beta probes conferred (new p1 shape: stray paren kills generation at exit 0) | FAIL as filed (details in CSV) | — |
| 20 | **FEN-SET-DESIGN-SPLIT** — GAMA-SET-22: "two repair philosophies" D-S9 ground already false | — | — | FAIL major | Single route | **Judge verified** SecureRandomSpec fsm + register row (§0.7) | FAIL — INCORRETA major (register-internal false ground; feeds the FEN-C-CARRIER-SEQFAIL disposition) | — |
| 21 | **Overturned claims** — BETA-KGN-04 (Gets repetition), GAMA-KGN-05 (g3 state-read condition), BETA-SET-06 (edges staleness) | (KGN-11 PASS; KGN-08 PASS) | FAIL→ | FAIL→ | Real conflicts | Fresh-instance JCA semantics; descriptor-order verified both paths; README baseline re-read | **3 overturns FAIL→PASS** (§2.1) — no counterexample existed in any of the three | — |
| 22 | **Positive closures** — TMF four-defect repair + g3 row; SSL returning(ctx) + 3 predicate reads; KST three-key write; TLS chain on captured path; 23-spec merge compiles clean; generation determinism; KGN multi-overload capture (`Object+` exact-arity discriminator) | PASS | PASS | PASS | None | S18 + S3 + spec text + Beta merge/weave conferred | PASS — FIDELIDADE_DEMONSTRADA. Note: the merged-set compile PASS is exactly what masks FEN-KGN-NAOCOMPILA (standalone) — both recorded | — |

## 2. Detailed resolutions

### 2.1 Overturned positions (judge-verified evidence, none by vote)

| Claim | From → To | Why |
|---|---|---|
| BETA-KGN-04 | FAIL → **PASS** (DIVERGÊNCIA_EQUIVALENTE_COMPROVADA) | The permissive words (`g1 g1 gk1`) require one KeyGenerator returned by two `getInstance` calls; the JCA factory constructs a fresh instance per call — unrealizable by reference identity on the per-object monitor. Same unit as ALFA-KGN-11 (PASS). Beta's own row already classified it DIVERGÊNCIA_EQUIVALENTE; the FAIL position was inconsistent with its classification. Provider threat retained as note. |
| GAMA-KGN-05 | FAIL → **PASS** (DIVERGÊNCIA_EQUIVALENTE_COMPROVADA) | g3's state-read condition is equivalent on every realizable trace: g1-before-g3 order is fixed in the descriptor AND `WrapperEmitter` fires merged advices in descriptor order (judge-verified, `WrapperEmitter.java:246-249`) — Gama's named residual threat ("dexlib2 order could differ") is closed by source. Executed benign twice (kgn_b, S18a). Fragility stays a recorded threat, aligned with ALFA-KGN-08. |
| BETA-SET-06 | FAIL → **PASS** | `predicate_edges.csv` is the declared pre-repair baseline "kept as authored" (README re-read by me) — the rows Beta cites are that semantics. **Third recurrence** of the same misreading (batch A BETA-SET-07, batch B BETA-SET-10): the one-paragraph register briefing recommended twice is still missing from the round packet. |

### 2.2 Severity harmonizations (21 decisions: 18 up, 3 down; severity does not enter the score)

Upward, per executed evidence within the phenomenon (§4 criteria, batch B
practice — no rarity carve-outs): BETA-KGN-05, BETA-KMF-04, BETA-TMF-04,
BETA-SSL-06 (carrier, → critical); GAMA-TMF-02 (delayed, → critical);
GAMA-TMF-03, GAMA-KMF-02, GAMA-KGN-06, BETA-SSL-03 (gets-invisível, →
critical); BETA-KST-03, GAMA-KST-04 (KST g2, → critical); BETA-SSL-02
(engine dead, → critical); ALFA-SSL-05, GAMA-SSL-05 (engine loop, → critical
— FN executed by me, S15b); GAMA-SSL-06 (getDefault, → critical);
BETA-KGN-06, GAMA-KGN-04 (keySize, → critical); GAMA-KGN-03 (whitelist, →
critical).

Downward, with grounds: ALFA-KGN-07 and ALFA-SET-03 (generatedKey second
slot) critical → **major** — cross-batch consistency with batch B's
resolution of the SAME phenomenon (latent slot loss, no executed FP/FN this
round; the realizable cross-batch FN via Cipher's reader is recorded as a
G11 candidate); ALFA-KST-04 (Entries) critical → **major** — the FN half
rests on an unresolved oracle-semantics question (declared-but-unordered
events), now a named pendency; the executed halves (silence + displaced
accusation, S9) hold under either reading.

### 2.3 Single-route claims and how they were closed

FEN-SET-VARARGS-ARGS-IGNORED and FEN-SET-NESTED-TYPE-DESCRIPTOR (Beta lane):
mechanisms verified at source by me (§0.5), platform facts re-derived from
class bytes (§0.6), Beta's weave/drive outputs conferred (§0.11), table-level
effect independently walked (J1-C). ALFA-SSL-07 (randomized extra): rule
text verified, FP executed by me (S12), production-writer nuance added
(§0.3). ALFA-TMF-07 (remove cascade by symmetry, confidence 0.85): executed
directly (S11). GAMA-SET-22: SecureRandomSpec fsm + register row verified by
me. GAMA-SET-20: dead-member static listing verified via the dead pointcut +
extractor CSVs conferred. FEN-KGN-NAOCOMPILA: third independent compile
probe executed by me.

### 2.4 Dimension-assignment pendencies (D-piloto-4 — recorded, not re-assigned)

- FEN-C-CARRIER-SEQFAIL: Alfa under `linguagem_formal` (+1 `diagnostico`),
  Beta and Gama under `diagnostico`.
- FEN-KGN-NAOCOMPILA: Alfa under `toolchain_android`, Gama under
  `reprodutibilidade`.
- FEN-C-GETS-INVISIVEL: Alfa/Beta/Gama all `captura_eventos` (no pendency).
- FEN-KST-ENTRIES-OMITIDAS: Alfa `captura_eventos`, Gama `bindings_clausulas`.
The per-phenomenon table (§4) is the corrective lens.

### 2.5 Agent-report errata (no claim rows affected)

Alfa report §0 states KST is "AbstractSynchronizedMonitor but properly
parameterized" and §5.3 "7/7 events bind `k`" — `k` is not the spec
parameter (`ks`); the artifact is the empty-binding global Tuple2 (J1-C
check 5). Alfa filed no lifecycle claim for KST, so no resolution changes;
Alfa's KST language claims stay PASS/FAIL **as scoped** (single-object
traces). Recorded because the batch B standing check ("verify the parameter
is bound by every event") was executed incompletely by one of three agents —
and the check itself again proved decisive.

### 2.6 FEN unification (register of record for this round)

Canonical ← merged aliases: **FEN-C-CARRIER-SEQFAIL** ← FEN-C-PAIRING-IMEDIATO,
FEN-{KGN,KMF,TMF,SSL}-UNSAFE-RESIDUO (same mechanism, same executed records:
decided by comparing the record sets of S1–S5 with both agents' scenario
tables — they are the same events, same calls, same types);
**FEN-C-GETS-INVISIVEL** ← FEN-C-UNSAFE-2ARG, FEN-SSL-G2-PROVIDER-OMIT;
**FEN-KST-G2-OMITIDA** ← FEN-KST-G2-2ARG-OMIT (+ GAMA-KST-04 remap);
**FEN-KST-MONITOR-GLOBAL** ← FEN-KST-GLOBAL; **FEN-SSL-ENGINE-VOID** ←
FEN-SSL-ENGINE-MORTO, FEN-SSL-ENGINE-DEAD; **FEN-C-WHITELIST-EXTRA** ←
FEN-KGN-WHITELIST; **FEN-KGN-KEYSIZE-OMITIDA** ← FEN-KGN-KEYSIZE-OMIT;
**FEN-KGN-NAOCOMPILA** ← FEN-KGN-NOCOMPILE. Claim-level remaps:
ALFA-SSL-05 → FEN-SSL-ENGINE-LOOP (cardinality unit); GAMA-KST-04 →
FEN-KST-G2-OMITIDA. FEN-C-DELAYED and FEN-KST-ERASURE kept distinct
(different repair points; composition noted). Per-phenomenon counts are
generated from `fenomeno_id_final` only (D-batchB-1).

### 2.7 Pilot-hypothesis update (recorded per round instructions)

**H2 is refuted in immediate form for the whole batch**: the current
artifacts pair the specific error with a spurious `@fail` on the same call
in all five specs (S1–S5) — the pairing batch B saw return in delayed form
at PBK's `cP` never left in immediate form here. The historical TMF
fingerprint (4,599/4,602 cells with both; two literals only) is *consistent*
with this mechanism — Gama's stratification re-derives it — but causal
attribution for the pre-repair lines stays deferred to the named replay
battery (GAMA-TMF-05/SSL-07/KST-07, INCONCLUSIVE). **H4 update**: the
empty-label route is alive in the current artifacts (creation-at-consume:
S14 executed "but found ."); the weaver attribution of the historical
zero-post-GH100 measurement is unchallenged.

## 3. Consolidated classification

**Resolution totals**: 134 claims → **55 PASS, 73 FAIL, 6 INCONCLUSIVE**;
**53 critical FAIL claims across 15 critical phenomena** (27 FEN groups
total after unification — verbatim table in `juiz_rescore_batchC_output.txt`).
Position changes: 3 FAIL→PASS (§2.1), 0 PASS→FAIL; 21 severity
harmonization decisions — 18 up, 3 down (§2.2). No counterexample was dismissed; no
resolution used agent counting.

**Critical phenomena (15) with provenance** (REF-C-05 discipline; every
entry checked against the `jca` twins and the gh101 registers this session;
provenance routes G11/G13 accountability and excuses nothing — the oracle is
the api30 rule):

| FEN | Specs | State | Provenance |
|---|---|---|---|
| FEN-C-CARRIER-SEQFAIL | KGN KMF TMF SSL KST | INCORRETA — executed FP on conformant ORDER ×5 (S1–S5) | jca-inherited shapes; TMF/SSL form reshaped by gh101 (carrier states), FP retained; **partially registered** (3b.11b: delayed accusation yes, same-call pairing no; D-S9 ground "two philosophies" factually false — GAMA-SET-22) |
| FEN-C-DELAYED | TMF (pattern: all) | INCORRETA — executed (S1b/S2b) | structural (reset semantics), inherited |
| FEN-C-GETS-INVISIVEL | KGN KMF TMF SSL | INCORRETA — executed FP/FN (S14, tmf_c) | jca-inherited; the Cipher twin was repaired by gh101 (b532e439f79a), these were not; unregistered |
| FEN-KST-G2-OMITIDA | KST | OMITIDA — executed chain FP (S8) | jca-inherited, unregistered |
| FEN-KST-MONITOR-GLOBAL | KST | INCORRETA — executed (S6): 5 spurious + wrong-object identity | jca-inherited (twin binds `k` too); **new sub-shape**: parameter declared, never bound — census-invisible |
| FEN-KST-ERASURE | KST (chains into KMF/TMF/SSL) | INCORRETA — executed (S7) | composition (global monitor × remove semantics), inherited mechanism |
| FEN-C-REMOVE-CASCADE | KMF TMF (pattern KGN/KST) | INCORRETA — executed chain FP (S10/S11); zero NEGATES | revocation semantics inherited; the 2-arg remove *form* is gh101 (replacing the worse whole-set remove — precision verified) |
| FEN-SSL-ENGINE-VOID | SSL | INCORRETA — both weave halves dead (measured); writer unreachable | jca-inherited byte-for-byte, registered nowhere |
| FEN-SSL-ENGINE-LOOP | SSL | INCORRETA — executed FN (S15b) | jca-inherited |
| FEN-SSL-GETDEFAULT-OMITIDA | SSL | OMITIDA — FORBIDDEN clause, no register | jca-inherited |
| FEN-SSL-RANDOMIZED-EXTRA | SSL | INCORRETA — executed FP (S12); rule binds `_` | **gh101-introduced** (task 3.2 read) |
| FEN-C-WHITELIST-EXTRA | KGN SSL | INCORRETA — executed FNs (S15a, S17) | aliases/folding jca-inherited; base lists gh99; registered as aliases/artefacts — registered ≠ approved |
| FEN-KGN-KEYSIZE-OMITIDA | KGN | OMITIDA — executed FN (S16) | jca-inherited, unregistered |
| FEN-SET-VARARGS-ARGS-IGNORED | KMF TMF (set) | INCORRETA toolchain — measured; ajc×dexlib2 disagree | toolchain (dexlib2), outside both spec sets |
| FEN-SET-NESTED-TYPE-DESCRIPTOR | KST (set) | INCORRETA toolchain — measured | toolchain (dexlib2) |

**Major (non-critical) phenomena**: FEN-KGN-NAOCOMPILA (G2-decisive,
jca-inherited missing import, fail-open, unregistered);
FEN-SET-GENERATEDKEY-2A-CASA (writer side, batch B severity kept);
FEN-KST-ENTRIES-OMITIDAS (oracle-reading pendency named);
FEN-SET-DEDUPE (3-clause worst case executed); FEN-SET-FAIL-UNKNOWN (every
sequencing record of the batch `expecting=unknown` — executed throughout
S1–S11); FEN-SET-DESIGN-SPLIT (register-internal false ground);
FEN-SET-FAIL-OPEN (new p1 shape: stray paren now kills generation at exit
0); ALFA-SET-05's register-absence half; GAMA-SET-20 (§13 static/dynamic
contradiction).

**Minor**: FEN-C-ACCEPT-END (complete rule words end outside match —
table-level, no realizable FP/FN found), FEN-C-NULL-POLLUTION,
FEN-KST-LOAD-TIMING, FEN-KST-NULL-KEY-MARK, FEN-TMF-GTM-INVISIVEL
(platform-masked FN — register the limitation).

**DIVERGÊNCIA_EQUIVALENTE_COMPROVADA (PASS)**: ALFA-KGN-08/GAMA-KGN-05 (g3
state-read, by advice order — both paths), ALFA-KGN-11/BETA-KGN-04 (Gets
repetition, unrealizable), ALFA-KST-07 (outer `+` re-entry), ALFA-TMF-06
(two-constant ENSURES split, reader-side correct).

**LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA (PASS, blocks total adherence)**:
neverTypeOf ×4 (KMF, KST ×3 — registered D-S14 class).

**FIDELIDADE_DEMONSTRADA highlights**: TMF four-defect repair + unsafeAlg
row (executed pre-repair reconstruction pF1 conferred); SSL
`returning(ctx)` repair + three REQUIRES readers; KST three-key write; KGN
i1–i5 split (language-preserving) + multi-overload capture with `Object+`
(the exact-arity discriminator against the KMF/TMF `..` defect); full
captured TLS chain (S18d); PKIX/KeyStore whitelists literal-identical;
generation determinism (20/20 byte-identical regeneration); 23-spec merged
monitor compiles clean (which is also the KGN masking route — both facts
recorded).

**INCONCLUSIVE (6, outside every denominator, named pendencies)**:
BETA-SET-07 (android-37.0 production-default jar), BETA-SET-08 (ART/device;
note updated — the halves now measurably disagree pre-ART, the open
question is which semantics the device realizes), GAMA-TMF-05/GAMA-SSL-07/
GAMA-KST-07 (historical attribution — replay battery), GAMA-SET-21
(KGN/KMF historical zero-emission).

## 4. Descriptive scores (pre-registered weights; verbatim from `juiz_rescore_batchC.py`)

Raw weighted sum is the score of record (D-batchA-1); per-spec over that
spec's resolved claims only; SET separate; dimension as filed;
INCONCLUSIVE outside the denominator.

| Unit | ling(20) | capt(20) | bind(15) | pred(15) | tool(15) | diag(10) | repr(5) | **Raw (of record)** | Status |
|---|---|---|---|---|---|---|---|---|---|
| KGN | 15.00 (3/4) | 10.00 (2/4) | 7.50 (5/10) | 11.25 (3/4) | 7.50 (1/2) | 0.00 (0/3) | 0.00 (0/1) | **51.25** | COMPLETE |
| KMF | 6.67 (1/3) | 0.00 (0/3) | 15.00 (4/4) | 12.00 (4/5) | 15.00 (1/1) | 0.00 (0/2) | — (unattainable 5) | **48.67** | COMPLETE |
| TMF | 6.67 (1/3) | 0.00 (0/3) | 15.00 (2/2) | 11.25 (3/4) | 15.00 (1/1) | 0.00 (0/4 +1INC) | — (5) | **47.92** | INCOMPLETE (1 INC) |
| SSL | 8.00 (2/5) | 0.00 (0/7) | 7.50 (2/4) | 9.00 (3/5) | 15.00 (1/1) | 0.00 (0/3 +1INC) | — (5) | **39.50** | INCOMPLETE (1 INC) |
| KST | 15.00 (3/4) | 0.00 (0/5) | 4.29 (2/7) | 9.00 (3/5) | 15.00 (1/1) | 0.00 (0/1 +1INC) | — (5) | **43.29** | INCOMPLETE (1 INC) |

**SET score** (separate): pred 8.33 (5/9), tool 3.75 (1/4 +1INC), diag 0.00
(0/3 +1INC), repr 5.00 (1/1 +1INC) → **raw 17.08**; unattainable weight 55
(no ling/capt/bind SET claims); labeled derived reading 17.08/45 = 37.96%;
INCOMPLETE (3 INC).

**Batch-C aggregate** (context only; 114 spec claims, SET excluded): ling
10.53 (10/19), capt 1.82 (2/22), bind 8.33 (15/27), pred 10.43 (16/23), tool
12.50 (5/6), diag 0.00 (0/13 +3INC), repr 0.00 (0/1) → **raw 43.61**;
INCOMPLETE (3 INC).

**Mandatory labels**: descriptive score ≠ probability of correction ≠
verdict; never rounded to 100; no score opens a gate; TMF/SSL/KST, SET and
the aggregate are INCOMPLETE. Context readings: (i) `diagnostico` is **0
across all six units** — the same-call pairing, unknown-expecting and dedupe
collapse leave no live diagnostics dimension untouched; (ii) `captura` is
near-zero everywhere except KGN — batch C's factory specs concentrate their
defects at the getInstance/engine capture plane; (iii) claim counts
overstate convergence (FEN-C-CARRIER-SEQFAIL alone carries 15 claims) — use
the per-phenomenon table; (iv) the KMF/TMF/SSL/KST bindings and predicate
sub-scores reflect the gh101 repairs that DID hold (S18), coexisting with
the gate-deciding criticals.

## 5. Per-spec verdicts (covered scope: G2, G3, G4, G5, G7, G9)

**Operative gate rule** (REF-B-05): a gate fails when its pre-registered
criteria (`pre_registro.md` §3, protocol §16) are met; a critical
INCORRETA/OMITIDA inside the gate is one sufficient trigger, not the only
one.

**G5 scope decision (both halves, with REF-C-03 jar annotation)**: this
round G5 evidence covers BOTH weave halves — Beta's ajc 1.9.25.1
compile-time weave (the Docker AspectJ version) and the production dexlib2
pipeline over the frozen android-30 jar — plus the spec-level event-domain
analysis. **G5 FAILs are jar-robust** (void-return mismatch, trailing-`..`
over-expansion with args() ignored, nested-type descriptor mangling, and
spec-text event omissions are jar-independent mechanisms, judge-verified at
source); **G5 member-matching PASS halves (KGN capture; the clean sub-rows
of KMF/TMF/SSL/KST) are pinned to android-30** and carry the production
default-jar divergence (android-37.0 host / android-36 Docker, BETA-SET-07)
as a named pendency. **Dimension-7 note (first for the audit)**: ajc and
dexlib2 now measurably DISAGREE on KMF/TMF g2 semantics — observational
equivalence between the two production weaving paths is not merely
unverified, it is refuted at the static level; only ART execution (G6/G10)
can determine which semantics the device realizes.

### KeyGeneratorSpec — **REPROVADA** (covered scope)

| Gate | Result | Grounds |
|---|---|---|
| G2 | **FAIL** | the round artifact does not compile standalone (javac exit 1 — Alfa, Gama and judge probes); javamop/rv-monitor exit 0 — fail-open; production masked only by `-merge` import union (source-verified). Budget itself fine (9 events, 1.08 s / 111 MB) |
| G3 | **FAIL** | carrier FP executed: rule-ORDER-conformant unsafe-algorithm trace draws 2 spurious InvalidSeq (S4, J1-C) — critical |
| G4 | **FAIL** | 6 extra-oracle alias spellings accepted (FN executed, S17) — critical; `alg=AES ⇒ keySize` transcribed nowhere (FN executed, S16) — critical, unregistered |
| G5 | **FAIL** | rule g2's unsafe domain has zero MOP events (suppressed with no counterpart) — expected-event zero-fire, critical; member capture itself exhaustive on both weave halves (BETA-KGN-02 PASS, android-30-pinned) |
| G7 | **FAIL** | ENSURES `generatedKey[key, alg]` half-realized — the alg slot has no home in the store API (major, judge-verified); extra-oracle revocation pattern present (`@fail` removes GENERATED_KEY; zero NEGATES) |
| G9 | **FAIL** | same-call pairing (S4b); every sequencing record `expecting=unknown`; whitelist dumped into the message text |

### KeyManagerFactorySpec — **REPROVADA** (covered scope)

| Gate | Result | Grounds |
|---|---|---|
| G2 | PASS | clean deterministic generation measured (BETA-KMF-01) |
| G3 | **FAIL** | carrier FP executed (S2) — critical; complete rule words end outside match1 (minor, table-level) |
| G4 | PASS | PKIX whitelist literal-identical; parametric binding correct per-object; neverTypeOf registered (LIMITAÇÃO — blocks total adherence, not this gate) |
| G5 | **FAIL** | production dexlib2 fires g2 on every correct 1-arg `getInstance("PKIX")` → spurious InvalidSeq (FEN-SET-VARARGS-ARGS-IGNORED, jar-robust, ajc disagrees) — critical; 2-arg unsafe getInstance invisible (critical) |
| G7 | **FAIL** | `@fail` revokes the granted `generatedKeyManager[kms]` ENSURES — zero NEGATES in the rule — chained FP into SSL executed (S10) — critical; generatedKeyStore read and two-constant writes themselves faithful (PASS claims) |
| G9 | **FAIL** | same-call pairing + delayed residue (S2); `unknown` on every sequencing record |

### TrustManagerFactorySpec — **REPROVADA** (covered scope)

| Gate | Result | Grounds |
|---|---|---|
| G2 | PASS | clean generation measured |
| G3 | **FAIL** | carrier FP executed with the campaign's own "X509" shape (S1) — critical |
| G4 | PASS | binding repair (gtm1 four-defect fix) verified in the frozen artifact; whitelist identical |
| G5 | **FAIL** | same two criticals as KMF (varargs FP jar-robust; 2-arg unsafe invisible) |
| G7 | **FAIL** | remove cascade executed directly (S11) — critical; 2-arg remove precision itself verified (S18c) |
| G9 | **FAIL** | pairing + delayed residue + `unknown` (S1) |

### SSLContextSpec — **REPROVADA** (covered scope)

| Gate | Result | Grounds |
|---|---|---|
| G2 | PASS | clean generation measured |
| G3 | **FAIL** | carrier FP executed (S3) — critical; `engine*` vs rule `Engine?` — FN executed (S15b) — critical |
| G4 | **FAIL** | case-folded whitelist accepts what the raw literal set rejects — FN executed with a real resolvable call (S15a) — critical; registered as aliases, no scope reduction on file |
| G5 | **FAIL** | Engine channel dead on BOTH weave halves (void-return pointcut, jar-robust) — critical; `(String, Provider)` overload uncaptured → conformant creation accused (S14) — critical |
| G7 | **FAIL** | extra-oracle RANDOMIZED read on the argument the rule binds `_` — FP executed (S12) — critical, gh101-introduced; `generatedSSLEngine` writer unreachable and the fact registered nowhere (major); null-pollution residue (minor); the three predicate reads themselves work (PASS claims) |
| G9 | **FAIL** | 3 violated clauses → 1 record (S13); empty "but found ." labels live (S14); `unknown` everywhere |

### KeyStoreSpec — **REPROVADA** (covered scope)

| Gate | Result | Grounds |
|---|---|---|
| G2 | PASS | clean generation measured |
| G3 | **FAIL** | process-global monitor: two individually conformant interleaved stores draw 5 spurious InvalidSeq (S6) — critical; carrier FP (S5) — critical |
| G4 | **FAIL** | spec parameter `ks` bound by no event — wrong-object marking executed (S6/S8) — critical; before-advice ENSURES timing (minor); Entries omission (major, oracle-reading pendency) |
| G5 | **FAIL** | rule's 2-arg Gets alternative has no pointcut — chain FP executed (S8) — critical; getEntry/setEntry silently unwoven on production dexlib2 (nested-type descriptor, jar-robust, ajc disagrees) — critical; scE/skE1/skE2 unobserved |
| G7 | **FAIL** | cross-object ENSURES erasure through the shared field — conformant TMF over A accused after B's fail (S7) — critical; null-key marking (minor); three-key write repair itself holds (PASS) |
| G9 | **FAIL** | pairing (S5); displaced accusations (S8/S9); `unknown` on every sequencing record |

**Batch verdict line**: **5/5 REPROVADA in the covered scope** — every
gate-deciding defect anchored in evidence the judge executed (J1-C, J2-C,
compile probe) or verified at source/register/platform bytes, over the
frozen artifacts. Per protocol §16 the set cannot move toward `READY` from
this batch. Cumulative across the audit: **17/17 audited specs REPROVADA**
in their covered scopes (pilot 2, batch A 5, batch B 5, batch C 5).

## 6. Observations routed to batch D (already generated — no gate changes)

Batch D's inputs are frozen (`batchD/generation_manifest.md`), so these are
addressed to the batch D **reviewers and judge**, not to its generator:

1. **Unbound-parameter sub-shape is now standard**: the indexing check must
   verify (a) a parameter is declared, (b) every event binds *that*
   parameter — KST passed (a) and failed (b) while carrying
   `AbstractSynchronizedMonitor`, defeating both the batch B census
   signature and one agent's reading. One grep per spec for the declared
   parameter name vs the names actually bound in events.
2. **Carrier/pairing sweep first**: FEN-C-CARRIER-SEQFAIL is now a
   13-spec-registered residue (3b.11b) with an executed same-call pairing in
   every batch C spec. For each batch D spec: list carrier states/prefixes
   and the mandatory successor, and pre-file the pairing test. The D-S9
   register's "two philosophies" ground is factually false (GAMA-SET-22) —
   cite it, do not re-derive it.
3. **Unsafe-2-arg (Cipher-repaired) class**: grep every batch D spec for
   1-arg-only unsafe/invalid events vs rules whose Gets has a 2-arg
   alternative; the repair exists in the set (b532e439f79a) and is absent
   from at least 5 specs.
4. **dexlib2 sweeps**: (a) any `call(... , ..)` with `args(...)` narrowing
   loses the narrowing on the production path (WrapperEmitter never reads
   args()); (b) any nested-type parameter (`Outer.Inner`) in a pointcut is
   silently unweavable on dexlib2 (`toDescriptor` slash-mangling). Both
   jar-robust, judge-verified; pre-file capture claims accordingly.
5. **Return-type mismatch check**: SSL's void-vs-SSLEngine joins TMF's
   repaired gtm1 as the second instance of the class — javap every pointcut
   return type against extracted class bytes before filing capture PASSes.
6. **Register briefing STILL missing**: BETA-SET-06 is the third
   consecutive-round misreading of `predicate_edges.csv` baseline semantics.
   Put the one-paragraph briefing (batch A §6 item 5) in the batch D packet.
7. **Judge standing tests generalize**: the walk+drive pair (J1/J2) again
   closed every table-level and JVM-level conflict without an emulator; the
   two-object drive decided the KST global-monitor family; the real-call
   drive (S14/S15a with real platform objects) decided capture-omission FPs
   and folding FNs — keep all three for batch D.
8. **Oracle-semantics pendencies for the researcher** (pre_registro §7 —
   explicit scope reduction or repair, never silent): the extra-oracle
   family now adds SSL's RANDOMIZED-on-`_` read; the folding/alias family
   (KGN/SSL) awaits a decision; new ambiguity class: declared-but-unordered
   rule events (KST Entries); rule-authoring defect recorded: SSL binds
   `sr` in no event.

## 7. Files (judge outputs of record, sha256)

```
459e544459a1840bbd18b9dd608d3d90806cb43b5ea795c5afff88ff31b74e9b  juiz_JuizDriveC.java
d3ac5f70b8cafa254114507531cb0d37d3697e2c54c893df2fa3cc11d95e0681  juiz_driveC_rep1.txt (= rep2 = rep3)
6b45a5bafe1095e66cc05846c887a7244f1c0b610ba7f86a7ebf0e55637c62f8  juiz_walk_batchC.py
e91a19f1a0415845a9fae68b4add647c72a840f70268162e42fc113af66eaaca  juiz_walk_batchC_output.txt
974f74f7e8ec948cacaae320b3f96895c600d53d0641fca483011e70dc39c5fd  juiz_kgn_compile_probe.txt
b2ac0a81b35e57e12185e9bf1f204d37ef2c22fd962b8037fe9796739af7878f  juiz_build_csv_batchC.py
510497cfe7ea6a27a31f23807cf33e30755e5ece417af16bf650165d111f9d73  juiz_claims_resolvidos_batchC.csv
1f6537570e8b9554f16fbc9a03f6ee76a8e928184bcd3dc93466833035a368ad  juiz_rescore_batchC.py
5d92f1ac3bcdd895966ee6a339ebc821cba867b6415014d0d06ddec89a4e9924  juiz_rescore_batchC_output.txt
```

- J2-C reps 2–3 are sha256-identical to rep 1 (repetition policy satisfied).
  Compile: monitors byte-identical to the manifest except the documented
  1-line KGN import patch (patched copy sha `685f7dae…`, diff recorded in
  the probe file); classpath = the three production jars (§0.1); run 3×
  from clean scratch working dirs.
- `juiz_walk_batchC.py` hash-asserts its inputs; set `BATCHC_GEN` to the
  directory containing the round `gen_<Spec>/out` artifacts to reproduce.
- Agent primary files consulted: all `batchC/alfa_*`, `beta_*`, `gama_*`;
  `generation_manifest.md`; frozen specs/rules; `data/gh101/*`; production
  sources cited at file:line throughout.

*Next step per protocol §15: adversarial refutation round against this
synthesis; the judge's decision becomes final only after answering each
objection. The must-close set for G13 from this round: 53 critical claims
(15 phenomena, provenance table §3) and every major finding, including the
register-absence family, FEN-KGN-NAOCOMPILA, FEN-SET-GENERATEDKEY-2A-CASA,
FEN-KST-ENTRIES-OMITIDAS (with its oracle-semantics pendency) and the §13
static/dynamic contradiction (GAMA-SET-20).*

## 8. Final decision after the refutation round

2026-08-09. Issued after responding to each of the 8 objections of the
independent reviewer (`refutacao_parecer_batchC.md`), as protocol §15
requires — responses in `juiz_respostas_refutacao_batchC.md` (outcomes: **8
accepted — 4 material (REF-D-01..04, three changing the resolved record), 4
minor**). The reviewer independently re-executed J1-C (22/22,
byte-identical), J2-C (sha `d3ac5f70…` = mine), the KGN compile probe (exit
1, same symbol), the builder and the rescore (byte-identical), and reported
no objection reaching verdicts, gates or scores of record except the
KST/aggregate denominators; the adjudication is nonetheless mine, objection
by objection, each re-verified before acting (including my own new probe,
`juiz_probe_identity_alias_batchC.txt`). Sections 1–7 above are the first
synthesis (rev. 1) and remain as record; **where wording or numbers diverge,
this section prevails** — the basis is rev. 2 of
`juiz_claims_resolvidos_batchC.csv`.

### 8.1 Final per-spec verdicts and gates

Operative gate rule unchanged (REF-B-05): gates fail on their pre-registered
criteria; a critical INCORRETA/OMITIDA is one sufficient trigger among them.

| Spec | G2 | G3 | G4 | G5 | G7 | G9 | Verdict (covered scope) |
|---|---|---|---|---|---|---|---|
| KeyGeneratorSpec | FAIL ² | FAIL | FAIL | FAIL ¹ | FAIL | FAIL | **REPROVADA** |
| KeyManagerFactorySpec | PASS | FAIL | PASS | FAIL ¹ | FAIL | FAIL | **REPROVADA** |
| TrustManagerFactorySpec | PASS | FAIL | PASS | FAIL ¹ | FAIL | FAIL | **REPROVADA** |
| SSLContextSpec | PASS | FAIL | FAIL | FAIL ¹ | FAIL | FAIL | **REPROVADA** |
| KeyStoreSpec | PASS | FAIL | FAIL | FAIL ¹ | FAIL | FAIL | **REPROVADA** |

¹ G5 annotation unchanged from §5 (both weave halves measured this round;
FAILs jar-robust, member-matching PASS halves android-30-pinned;
android-37.0 default-jar pendency carried). ² **G2 interpretation declared
(REF-D-05)**: "geração limpa" is read to include the generated artifact's
standalone compilability — a monitor javac rejects is a relevant error of
the generation output that the generators failed to surface (exit 0); pilot
GCM is distinguishable (its degenerate artifact compiled). KGN's verdict is
independent of this reading (G3/G4/G5/G7/G9 all FAIL).

Rev. 2 gate-ground adjustments (no outcome changes): KGN G4's grounds are
the keySize omission (critical — strengthened by the reviewer's observation
that `i1` is a before-event, so the FN fires before the platform's own
exception) and the folding family, with the KGN-alias half now held at
major-pending (REF-D-02) — the gate already failed on the keySize critical
alone; KST G4/G5 grounds are restated without the Entries claims (now
INCONCLUSIVE, REF-D-03) — both gates FAIL on the independent criticals
(unbound `ks`, 2-arg Gets omission, nested-type unweaving), as the reviewer
verified.

**Batch verdict line (final)**: 5/5 REPROVADA in the covered scope
(G2/G3/G4/G5/G7/G9); per protocol §16 the set cannot move toward `READY`
from this batch. Cumulative across the audit: **17/17 audited specs
REPROVADA** in their covered scopes.

### 8.2 Corrections of record absorbed from the refutation (rev. 1 → rev. 2)

| # | Change | Origin |
|---|---|---|
| 1 | **ALFA-KGN-09, GAMA-KGN-01, BETA-SET-04: major → crítica** — §4's letter pre-registers fail-open as a Crítica trigger; the batch-A "major as pattern" practice was never registered and cannot be registered without altering §4. Cross-batch ledger inconsistency (batch B's fail-open family at major) **declared and routed to G13** with a PROPOSED deviation text (§8.6) | REF-D-01 (accepted, material) |
| 2 | **ALFA-KGN-04: crítica → major; GAMA-KGN-03: rev. 1 upgrade withdrawn (major)** — the alias FN's enabling trace is not realizable on any measured platform (all six spellings throw; g1/g3 are after-returning — executed by the reviewer and by me, `juiz_probe_identity_alias_batchC.txt`); §4's "demonstrável em trace realizável" unmet pending the Android-BC probe. FAIL/INCORRETA stand; SSL folding half (ALFA-SSL-09) untouched at crítica (real resolving call, S15a) | REF-D-02 (accepted, material) |
| 3 | **ALFA-KST-04, GAMA-KST-05: FAIL → INCONCLUSIVE** — under reading (b) of declared-but-unordered events the raw oracle itself flags the projected trace at store (correctly placed; no FN, no displacement); the upstream Xtext grammar is syntax-only and cannot fix the semantics; §3's bindings INCONCLUSIVE criterion applies. Executed facts stay on record; oracle-semantics resolution is the named pendency; INCONCLUSIVE is not approval | REF-D-03 (accepted, material) |
| 4 | BETA-KGN-04 overturn justification upgraded from inferred API semantics to **executed evidence** (distinct references on repeated getInstance — reviewer's probe + mine) | REF-D-06 (accepted) |
| 5 | §2.6 unification ground reworded: *identical record structure at the pairing call (specific error + InvalidSeq, same call, same `__LOC`); traces differ in the mandatory-successor leg* (Gama's kgn_a = 2 records without `i1`; Beta/judge = 3 with it) | REF-D-07 (accepted) |
| 6 | REF-B-09 dimension-5 route declaration added (§8.4) | REF-D-08 (accepted) |

**Rev. 2 resolution totals**: 134 = **55 PASS / 71 FAIL / 8 INCONCLUSIVE**;
**54 critical FAIL claims; 17 phenomena with ≥1 critical FAIL; 26 FEN groups
with FAILs** (rev. 1's provisional figures were 73/6, 53, 15, 27). All
figures machine-generated by the rev. 2 builder + rescore.

### 8.3 Final scores (rev. 2 CSV; verbatim from `juiz_rescore_batchC.py` re-run)

| Unit | Raw weighted sum (of record) | Notes |
|---|---|---|
| KGN | **51.25** | COMPLETE |
| KMF | **48.67** | COMPLETE; unattainable weight 5 (no repr claims); labeled derived reading 51.23% |
| TMF | **47.92** | INCOMPLETE — 1 INC; unattainable 5 |
| SSL | **39.50** | INCOMPLETE — 1 INC; unattainable 5 |
| KST | **44.00** (was 43.29) | INCOMPLETE — 3 INC (REF-D-03 moved 2 claims out of the denominators); unattainable 5 |
| SET (separate, D-piloto-4) | **17.08** | INCOMPLETE — 3 INC; unattainable weight 55; labeled derived reading 37.96% |
| Batch-C aggregate (context) | **44.02** (was 43.61) | 114 spec claims, SET excluded; INCOMPLETE — 5 INC |

**Mandatory labels**: descriptive score ≠ probability of correction ≠
verdict; never rounded to 100; no score opens a gate; TMF/SSL/KST, SET and
the aggregate are INCOMPLETE; `diagnostico` is 0.00 across all six units;
severity changes do not move scores — only REF-D-03's denominator change
does.

### 8.4 Declarations owed and made (REF-D-04, REF-D-07, REF-D-08)

**Cross-round G5 threat (REF-D-04)**: batch C proves the two production
weave halves can disagree (varargs/args() ignored; nested-type descriptors).
Judge-executed sweep over the 18 non-batch-C `jca_android` specs: the two
demonstrated mechanisms occur in **no batch A or batch B spec** (CipherSpec's
trailing-`..` events use the non-narrowing `args(x, ..)` form — no
divergence); they occur concretely in **SecureRandomSpec (batch D)**: g2
`args(alg, *)` (`:62-63`) and g4 `args(alg)` exact-1 (`:76-78`) under
`(String, ..)` calls — both will diverge ajc×dexlib2. Standing consequence:
batch A's production-matcher partition PASSes and batch B's KPR/PBK
dexlib2-half G5 PASSes contain neither known mechanism but are hereby
declared **single-half evidence, not equivalence evidence** — routed to the
global judgment phase together with the android-37.0 default-jar pendency.
Closed rounds are not reopened. The SecureRandomSpec instances are flagged
to the batch D reviewers (inputs already frozen; this flags reviewers, not
the generator).

**Dimension-5 route coverage (REF-D-08, per REF-B-09)**: KST — multi-route
(Beta ×2 executed, Gama ×2 executed, judge S6/S7); KGN/KMF/TMF/SSL — Beta's
per-object lifecycle rows plus executed isolation scenarios (kgn_b, S18c,
SSL-e conferred), two routes, no contradiction; Alfa filed no KST lifecycle
claim and its report's KST dimension-5 statements were wrong (erratum §2.5)
— the executed routes alone carried that resolution.

**FEN-C-CARRIER-SEQFAIL unification ground (REF-D-07, final wording)**:
identical record structure at the pairing call; traces differ in the
mandatory-successor leg.

### 8.5 Open pendencies (named)

- **Android-BC alias resolvability** (REF-D-02): decides whether
  ALFA-KGN-04/GAMA-KGN-03 return to crítica in the global phase. A JVM+
  Android-provider probe or device run (G10) suffices.
- **Oracle semantics of declared-but-unordered events** (REF-D-03): decides
  ALFA-KST-04/GAMA-KST-05 (INCONCLUSIVE) — requires the CogniCrypt/
  CryptoAnalysis typestate construction verified at source, or a researcher
  ruling on the oracle reading.
- **BETA-SET-07** (android-37.0 production-default jar) and **BETA-SET-08**
  (ART/device; the halves now measurably disagree pre-ART — the open
  question is which semantics the device realizes). G6/G10.
- **GAMA-TMF-05 / GAMA-SSL-07 / GAMA-KST-07** (historical attribution —
  replay battery G10-TMF-1/SSL-2/KST-1), **GAMA-SET-21** (KGN/KMF
  historical zero-emission), **G10-KGN-1** (per-spec production build).
- **Researcher countersignature** (pre_registro §7): no scope reduction is
  on file for the extra-oracle family (SSL RANDOMIZED-on-`_`, folding/alias
  whitelists, revocation-without-NEGATES, carrier-residue D-S9 disposition —
  whose "two philosophies" ground is factually false, GAMA-SET-22).
- **G13 must-close set from this round**: the 54 critical claims (17
  phenomena, provenance §3), every major finding (including
  FEN-SET-GENERATEDKEY-2A-CASA, ALFA-SET-05's register-absence half,
  GAMA-SET-20, FEN-SET-DEDUPE/FAIL-UNKNOWN/DESIGN-SPLIT), the cross-round
  G5 declaration (§8.4), and the fail-open severity-ledger reconciliation
  (§8.2 item 1).

### 8.6 PROPOSED deviation text (for the researcher/orchestrator; NOT registered by the judge — nothing was written to `fase0/`)

> **D-batchC-1 (PROPOSED — fail-open severity follows §4's letter; ledger
> reconciliation)**: "Fail-open findings (generator or pipeline defects
> masked by exit 0, including artifacts that do not compile standalone) are
> resolved at severity *crítica* per `pre_registro.md` §4, from batch C
> onward. The batch A/B records that resolved fail-open pattern claims at
> *major* stand as those rounds' records; the G13 consolidation counts the
> phenomenon family at §4's letter. Origin: REF-D-01, batch C refutation
> round."

### 8.7 Files of record for the round (rev. 2 hashes)

```
e25fea4c683032d7ee8a52e117ae6c96d4eb065a518d7d3618bbeb51f7120b9e  juiz_claims_resolvidos_batchC.csv   (rev. 2)
b830b66cf2c330626ac4bd31560961ad4617ad7d8c343939668500b79684de75  juiz_build_csv_batchC.py            (rev. 2)
1f6537570e8b9554f16fbc9a03f6ee76a8e928184bcd3dc93466833035a368ad  juiz_rescore_batchC.py              (unchanged logic; re-run)
40f5dcbaa5b36b09188715f63f27bfdd6b97be3ac4ea1eebe1f606f8d6b88910  juiz_rescore_batchC_output.txt      (rev. 2)
da64eddb595bb19bdf80838db0bf2d5bd48503ef294acddddc9511467055810f  juiz_probe_identity_alias_batchC.txt (new, refutation round)
c2864eaf2b130815efd0a3c396a54871c6e08a72dd627c491826705aebfa5b41  juiz_respostas_refutacao_batchC.md  (new)
459e544459a1840bbd18b9dd608d3d90806cb43b5ea795c5afff88ff31b74e9b  juiz_JuizDriveC.java                (unchanged)
d3ac5f70b8cafa254114507531cb0d37d3697e2c54c893df2fa3cc11d95e0681  juiz_driveC_rep1.txt (= rep2 = rep3, unchanged)
6b45a5bafe1095e66cc05846c887a7244f1c0b610ba7f86a7ebf0e55637c62f8  juiz_walk_batchC.py                 (unchanged)
e91a19f1a0415845a9fae68b4add647c72a840f70268162e42fc113af66eaaca  juiz_walk_batchC_output.txt         (unchanged)
974f74f7e8ec948cacaae320b3f96895c600d53d0641fca483011e70dc39c5fd  juiz_kgn_compile_probe.txt          (unchanged)
```

Rev. 1 hashes of the two revised files remain in §7; rev. 1's rescore output
figures are preserved verbatim in `refutacao_rescore_rerun.txt`.

### 8.8 Decision

**Batch C is closed** with **KeyGeneratorSpec, KeyManagerFactorySpec,
TrustManagerFactorySpec, SSLContextSpec and KeyStoreSpec all REPROVADA in
the covered scope (G2, G3, G4, G5, G7, G9)** — five specs, **17 critical
phenomena, 54 critical claims** (rev. 2), every gate-deciding defect
anchored in evidence executed by the judge (J1-C, J2-C, compile probe,
identity/alias probe) or judge-verified at source/register/platform bytes,
independently re-executed by the refutation reviewer (walk, drive, probe,
builder and rescore all byte-identical). All eight refutation objections
were accepted and remediated; three moved the resolved record (severity
ledger and two INCONCLUSIVE conversions), none moved a verdict, a gate, or
a score other than the REF-D-03 denominators. Per protocol §16 the set
cannot move toward `READY`; per pre_registro §7 no divergence was silently
accepted. Observations for batch D (§6) stand as delivered, augmented by
the concrete SecureRandomSpec varargs instances of §8.4.
