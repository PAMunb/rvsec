# Agent ALFA — batch D report (MAC, MDG, KPG, SRD, SIG)

Date: 2026-08-09. Round: batch D (FINAL) of the `jca_android` adversarial audit.
Scope: CrySL conformance and formal logic (protocol §14, Agente Alfa) for
`MacSpec` (MAC), `MessageDigestSpec` (MDG), `KeyPairGeneratorSpec` (KPG),
`SecureRandomSpec` (SRD), `SignatureSpec` (SIG) against the raw
`MetaCrySL/generated/api30/` rules. Claims: `alfa_claims.csv` (59 rows; hashes §9).
All rules fixed for the round applied: D-piloto-1 (reading A), D-piloto-3
(verdicts over the effective automaton parsed from the artifacts), D-piloto-4 +
D-batchB-1 (dimension at creation, SET separate, six states, FEN on every FAIL),
D-piloto-2 tests (a) executed / (b) N/A declared for all five rules (no `part()`
in any of the five constraint sections — checked by grep), batch A/B/C standard
checks (parameterless/binding sweep, indexing tree, first-call-disjunct sweep,
post-__RESET cascade, same-call pairing).

Sequential Thinking MCP: **available and used** (4-step pre-verdict
decomposition; no chain-of-thought published — this report is the concise
scientific log).

## 0. Frozen inputs and evidence of record

- Specs and rules: all 10 sha256 re-verified byte-identical to
  `fase0/manifest_hashes.md` and `batchD/generation_manifest.md`.
- Generated artifacts: all 20 files re-hashed = generation manifest.
- Production jars (same as batch B/C judge classpath, re-hashed):
  `rv-monitor-rt-0.9.3-SNAPSHOT.jar` `0fa65fbc…`, `rvsec-core-0.9.3-SNAPSHOT.jar`
  `7b4d72aa…`, `rvsec-logger-csv-0.9.3-SNAPSHOT.jar` `6787f411…`. JDK Temurin
  25.0.3. Frozen android-30 jar `96ccfdc8…` (member matrix
  `alfa_javap_android30_batchD.txt`).
- Executed evidence (files of record under `batchD/`, alfa_-prefixed, §9):
  - `alfa_language_check.py` → `alfa_language_results.txt` — effective automata
    machine-parsed from the five `RuntimeMonitor.java` (transition arrays +
    category conditions); reference automata (reading A); α lifted to call
    classes taken from the generated aspects (merged advices reproduced;
    environment-dependent guards as call-class variants); both inclusions by
    exhaustive product BFS with smallest separating traces and walks.
    Deterministic (1 run, inputs hashed). KPG modeled without fail-reset
    (artifact `@fail` lacks `reset()`, the only one of the five).
  - `alfa_HarnessD.java` → `alfa_harnessD_rep{1,2,3}.txt` — JVM drive of the
    real compiled monitors (plus the batch B round `KeyPairSpecRuntimeMonitor`
    for the chain test), event sequences exactly as the generated advices emit
    them. 34 scenarios, 3 reps, sha256-identical (`78bb1cba…`).
  - `alfa_FoldingD.java` → `alfa_foldingD_rep{1,2,3}.txt` — D-piloto-2 test
    (a); 3 reps sha256-identical (`d7f6c478…`).
  - `alfa_mac_f3_probe.txt` — ajc (production `lib_tmp/aspectjtools.jar`) run
    over the round `MacSpecMonitorAspect.aj` + the descriptor JSON f3 advice +
    the jca-twin provenance excerpt.
- All six monitors compile standalone with javac 25.0.3 (exit 0) — **no batch-C
  `FEN-KGN-NAOCOMPILA` analogue in batch D** (positive check).
- Declared assumption (batch C precedent, carried): an object created by a
  member the raw rule does not model is UNTRACKED by the rule (rule silent,
  never accepting). Used only for Mac 2-arg/Provider `getInstance` and the
  SecureRandom 3-arg `getInstance` routes; flagged per claim.

**Effective automata (parsed, OBSERVADO_EM_ARTEFATO)** — printed verbatim at
the top of `alfa_language_results.txt`. Summary: MAC 5 states (fail=4, match=3);
MDG 5 (fail=4, match=1); KPG 5 (fail=4, match=1, **no fail-reset**); SRD 5
(fail=4, match1=2=`init`); SIG 9 (fail=8, match={4,6}). Conditions compile to
guards inside the monitor event methods (`return false` = suppression without
transition, and **without touching the category flags** — load-bearing for KPG,
§3.3).

---

## 1. MacSpec (MAC) vs Mac.cryptsl

### 1.1 Normative matrix (condensed)

| Clause (Mac.cryptsl) | MOP | Status | Evidence |
|---|---|---|---|
| EVENTS g1/g2 (both `getInstance(macAlg)` **1-arg**) | g1 safe / g3 unsafe (1-arg) + **g2 (String,String) with no rule counterpart**; (String,Provider) uncaptured | partially INCORRETA | ALFA-MAC-06/07 |
| EVENTS i1/i2 | i1/i2 with **extra-oracle `condition(validate(GENERATED_KEY,key))`** | INCORRETA | ALFA-MAC-04, measured |
| EVENTS u1–u4 | uArr/uByte/uBuf partition the 4 overloads | FIDELIDADE (capture) | ALFA-MAC-01, javap |
| EVENTS f1/f2/f3 | f1/f2 sound; **f3 spec-parameter unbound** | INCORRETA | ALFA-MAC-02/03 |
| ORDER `Gets, Inits, (Finals \| (Updates+, Finals))` | ere `(g3* g1\|g3* g2)(i1\|i2)((uArr\|uByte\|uBuf)*(f1\|f2\|f3))` | INCORRETA (carrier; key-gate; f3) | §1.2 |
| CONSTRAINT `macAlg in {12}` | 18-entry list (6 extra spellings, registered) | INCORRETA (extra-oracle members; Android-threat only) | ALFA-MAC-12 |
| CONSTRAINTS `offset<len`, `length(output1)>outOffset` | absent | **OMITIDA, unregistered** | ALFA-MAC-11 |
| REQUIRES `preparedHMAC[params]` | body read at i2 (null-guarded) | FIDELIDADE (read) / SET guaranteed-fire | ALFA-SET-10, measured |
| REQUIRES `!encrypted[output1,_]`, `!encrypted[output2,_]` | ENCRYPTED reads at f1/f2/f3 | FIDELIDADE (f3 live, measured; f1/f2 vacuous as in the rule) | ALFA-MAC-10 |
| ENSURES `macced[output1,inp]/[output1,pre_input]/[output2,input]` | MACED second-place projection, deferred to doFinal | FIDELIDADE + two registered residues | ALFA-MAC-08/09, §1.4 |

### 1.2 Language verdicts (product + harness)

- `L(CrySL) ⊆ α(L(MOP))`: **FAIL** — three independent shapes, all measured:
  - **Carrier** `G1u I1k` (MAC-T2: `getInstance("DES")…doFinal` →
    UnsafeAlgorithm + **3×** InvalidSequence, first paired to the same init
    call). FEN-C-CARRIER-SEQFAIL.
  - **Key gate** `G1s I1u F1` (MAC-T3: safe alg, unmarked key → i1 suppressed
    by the **extra-oracle** GENERATED_KEY condition → 2× InvalidSequence, zero
    UnsatisfiedConstraint). The raw rule has **no** generatedKey REQUIRES
    (Mac.cryptsl:78-84); the gh101 predicate register says "present" — the row
    anchors to CrySL 1.5.2, not to this audit's oracle (ALFA-SET-12). The
    spec's own sibling comments (SignatureSpec.mop:55-60) explain why reads
    must sit in bodies; these two sit in `condition(...)`. Inherited from jca.
  - **Invisible creation** `GP I1k …` (MAC-T5: a (String,Provider)-created Mac
    with safe alg and marked key → 3× InvalidSequence + UnsafeAlgorithm with
    the **empty label** "but found ." — H4 live). FEN-C-GETS-INVISIVEL.
- `α(L(MOP)) ⊆ L(CrySL)`: **FAIL** — suppression-induced FNs: `G1s I1k I1u`
  (second init with unmarked key: rule forbids a second Inits, monitor sees
  nothing). Plus the f3 channel on the AJC path (§1.3): `g1 i1 f3-call` — a
  complete rule word with the Finals unobserved.
- Acceptance: `G1s I1u F*` words are CrySL-complete and end at monitor state 0
  (key-gate route); safe captured route agrees (MAC-T1 accepting=true).

### 1.3 f3 — the unbound event (FEN-MAC-F3-UNBOUND, critical, inherited)

`MacSpec.mop:176-179` declares `f3 after(byte[] output, int outOffset)` and
uses `target(m)` without binding `m`. Three artifact-level consequences, each
verified:

1. **AJC path (measured, `alfa_mac_f3_probe.txt`)**: production ajc reports
   only `Xlint:invalidAbsoluteTypeName` ("no match for this type name: m") and
   **exits 0**; the f3 advice "has not been applied" — the pointcut can never
   match. `doFinal(byte[],int)` is zero-capture, fail-open. One more exit-0
   fail-open shape for the round's caveat list.
2. **Monitor semantics (measured, MAC-T9)**: `MacSpec_f3Event(output,outOffset)`
   dispatches on the **root** of the indexing tree
   (`MacSpecRuntimeMonitor.java:1684-1714`): one call transitioned an innocent
   second Mac's monitor to fail (InvalidSequence) *and* advanced a foreign
   monitor to its accepting state. Per-object isolation broken in both
   directions wherever any path emits f3.
3. **Descriptor (dexlib2 input)**: the JSON advice carries the malformed
   `target(m)` expression with parameters `[output, outOffset]` only — the
   dexlib2 emitter's handling is Beta's question; both possible outcomes
   (dead or broadcast) are covered by 1–2.

Provenance: the jca twin has the byte-same shape under the name f2
(`jca/MacSpec.mop:76-79`) — inherited, in both sets, never caught.

### 1.4 The `!macced[_, plainText]` transcription (§8 adversarial target) — closed

The projection design is **faithful** (ALFA-MAC-08, measured): MACED is the
second place of the two-place `macced`, marks are deferred to the doFinal that
actually produces the MAC (MAC-T1), `@fail` drops unfinalized inputs without
marking, f2 marks its direct input, and the only reader
(CipherSpec.mop:95-106) quantifies with the first place anonymous, so the
one-place projection is exact. The two residues are real, registered, and now
**measured**: data fed through a `ByteBuffer` is never marked (MAC-T6 — the
D-S13 FN), and a MACed byte marks the canonical cached `Byte`
(MAC-T7 — over-marking; inert today: the only MACED reader takes `byte[]`,
which can never be identity-equal to a `Byte`). Classification
LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA (still blocks total-adherence claims).

### 1.5 Lifecycle, folding, provenance

Per-object isolation holds for the 10 bound events (measured across
scenarios); f3 is the sole breach. Folding: no folding in the guard
(exact `contains`); the 6 extra `HMAC-*`/`HMAC/*` spellings are unresolvable on
the host JDK (probe) — Android-provider FN threat declared, batch C KGN-alias
status. Provenance: key-gate conditions, g2 extra capture, Provider hole,
carrier shape, f3 shape, arithmetic-constraint omission — all inherited from
jca (twin diff); the update/doFinal splits, MACED/pendingInputs machinery,
preparedHMAC and !encrypted reads, 2-arg GENERATED_MAC remove — gh101.

---

## 2. MessageDigestSpec (MDG) vs MessageDigest.cryptsl

### 2.1 Normative matrix

| Clause | MOP | Status | Evidence |
|---|---|---|---|
| EVENTS g1/g2 (`getInstance(alg)`, `(alg,_)`) | g1 + g2/g3 split over the two 2-arg overloads — **the only batch D spec capturing (String,Provider)** | FIDELIDADE (safe half) / INCORRETA (no unsafe counterparts for 2-arg) | ALFA-MDG-01/04 |
| EVENTS u1–u4 | fused `update(..)` (covers ByteBuffer = rule u4) | FIDELIDADE | ALFA-MDG-01 |
| EVENTS d1/d2/d3, DWOU=d2 | 1:1 | FIDELIDADE | ALFA-MDG-01 |
| (no reset event in the rule) | reset event **removed** by gh101 (D-S12) | FIDELIDADE_DEMONSTRADA | ALFA-MDG-06, §2.3 |
| ORDER `Gets, (DWOU \| (Updates+, Digests))+` | ere `(g4* g1\|g4* g2\|g4* g3)(d2\|(update+(d1\|d2\|d3)))+` | FIDELIDADE on captured-safe routes (incl. reuse); INCORRETA on unsafe refinement | §2.2 |
| CONSTRAINT `digestAlg in {6}` | 9 entries + `toUpperCase` folding | **INCORRETA — 6 measured FN witnesses** | ALFA-MDG-05 |
| CONSTRAINTS `pre_len>pre_off`, `len>off` | absent | **OMITIDA, unregistered** | ALFA-MDG-08 |
| ENSURES `digested[out,_]/[out,inbytearr]` | DIGESTED single slot, no reader (registered terminal); @fail does **not** revoke (faithful: zero NEGATES) | LIMITAÇÃO documented | ALFA-MDG-09 |

### 2.2 Language verdicts

- `L(CrySL) ⊆ α(L(MOP))`: **FAIL** — carrier `G1u U` (MDG-T3: UnsafeAlgorithm
  + 2× InvalidSequence) and invisible unsafe-2-arg `G2u U` (MDG-T4:
  **"but found ."** + 2× InvalidSequence). Product walks in
  `alfa_language_results.txt`.
- `α(L(MOP)) ⊆ L(MOP CrySL)`: **PASS** — the only spec of the five with no
  silent-deviation witness (the fused update keeps every rule event
  observable; d1-without-update fails both oracles — consistent).
- Safe-path acceptance and reuse cycles agree (MDG-T1/T2/T5 all 0 errors,
  match states aligned) — recorded as fidelity the falsification attempt could
  not break.

### 2.3 The reset removal (§8 adversarial target, D-S12) — closed as fidelity

The raw api30 rule declares getInstance/update/digest and **no reset**
(MessageDigest.cryptsl:27-55). The jca twin declared a reset event
(`jca/MessageDigestSpec.mop:73-76`) that its own ere never placed → all-fail
row → every legitimate `reset()` call produced an InvalidSequence FP.
gh101 removed the event (divergence_record `ff425611fcba`); the removal aligns
the spec with the raw oracle exactly. Adversarial closure: I searched for a
trace where reset-blindness separates spec from rule — none exists, both
automata ignore the call; the divergence is oracle-vs-reality (the real
`reset()` clears digest state that neither side tracks), recorded as an oracle
blind spot, not a spec defect. FIDELIDADE_DEMONSTRADA, gh101-introduced.

### 2.4 Constraints — the folding FNs (measured)

The guard folds case (`.toUpperCase`) and carries 3 no-hyphen aliases; the
probe measured **six** host-resolvable strings that are spec-safe and
raw-violating: `sha-256`, `md5`, `sha256`, `SHA256`, `SHA384`, `SHA512`
(`alfa_foldingD_rep1.txt`). The register records the aliases as spelling
variants; the raw oracle governs (pre_registro §1) — INCORRETA, critical FN
family (FEN-C-WHITELIST-EXTRA). The diagnostic label naming
"{SHA-256, SHA-384, SHA-512}" against a 9-entry guard is filed as a separate
minor (ALFA-MDG-10).

---

## 3. KeyPairGeneratorSpec (KPG) vs KeyPairGenerator.cryptsl

### 3.1 Normative matrix

| Clause | MOP | Status | Evidence |
|---|---|---|---|
| EVENTS g1/g2 | g1/g3 (1-arg) + g2 (String,String) safe-only; (String,Provider) — a rule-covered Gets — uncaptured | INCORRETA | ALFA-KPG-07 |
| EVENTS i1–i4 | init3/init4/init1/init2, 1:1, bound; **conditions call `validate()` = `switch(algorithm)`** | FIDELIDADE (capture) / **INCORRETA (NPE)** | ALFA-KPG-01/02 |
| EVENTS k1/k2 | merged `gen` (2 call disjuncts — dexlib2 caveat flagged) | FIDELIDADE (AJC capture) | ALFA-KPG-01 |
| ORDER `Gets, Inits, Generators` | ere with `initError*` inserted | INCORRETA both directions | ALFA-KPG-06, §3.2 |
| CONSTRAINT base list + keySize implications | anchored lists; validate() = the rule's implications | FIDELIDADE (literals) | ALFA-KPG-11 |
| REQUIRES preparedDH (implication) | body reads at init3/init4 | FIDELIDADE | ALFA-KPG-08 |
| REQUIRES preparedDSA/RSA/EC | unread — registered capability-absent (D-S14) | LIMITAÇÃO documented | ALFA-KPG-08 |
| ENSURES `generatedKeypair[kp, alg]` | GENERATED_KEY_PAIR[kp] — alg slot dropped; writer-only (registered) | LIMITAÇÃO documented | ALFA-KPG-09, §3.4 |

### 3.2 Language verdicts

- `L(CrySL) ⊆ α(L(MOP))`: **FAIL** — carrier `G1u I3good` (KPG-T6, pilot
  **H2 confirmed for KPG** with an executed trace: UnsafeAlgorithm +
  InvalidSequence on the same initialize call, plus §3.3's amplification);
  `G1s I3bad GEN` (KPG-T3: InvalidKeySize correctly alone at the init, then a
  **spurious InvalidSequence at gen** — the rule's `i3` with a bad size is
  still an Inits, so `Gets, Inits, Generators` is ORDER-complete);
  `G1s I4bad GEN` (KPG-T4, §3.5).
- `α(L(MOP)) ⊆ L(CrySL)`: **FAIL** — `G1s I3bad I3good GEN` (KPG-T7: bad size,
  corrected size, generate → monitor **accepts with match** while the rule's
  single-Inits ORDER is violated). The initError placement diverges in both
  directions (ALFA-KPG-06); the gh101 register row for it does not record the
  gen-unreachability consequence.
- Acceptance: `G1s I3bad GEN` CrySL-complete, monitor in fail (product row).

### 3.3 The fail sink and the sticky category (FEN-KPG-FAILSINK, critical)

KPG's `@fail` is the only one of the five without `__RESET`
(`KeyPairGeneratorSpecRuntimeMonitor.java:471-477`). Two measured
consequences: (a) every event after a first violation fails again (KPG-T2:
one InvalidSequence per subsequent event, plus a re-executed
`remove(GENERATED_KEY_PAIR, kp)`); (b) **the category flag is sticky through
suppressed events**: a guard that returns false leaves `Category_fail` as the
previous event set it (`Prop_1_event_initError`:441-445 returns before
touching the flags) and the dispatch checks the flag unconditionally
(`event_initError`), so even a *suppressed* event re-fires the fail handler —
measured in KPG-T6, where the suppressed initError emitted its own
InvalidSequence. Inherited (jca `@fail` identical).

### 3.4 NPE on invisible creation (FEN-KPG-NPE, critical)

`validate(keySize)` opens with `switch(algorithm)`; `algorithm` is null on any
monitor born without a captured creation. Measured (KPG-T5): `initialize(2048)`
on such a monitor throws `NullPointerException` **to the caller** from
`KeyPairGeneratorSpecMonitor.validate` (`KeyPairGeneratorSpecRuntimeMonitor.java:262`);
no try/catch exists anywhere in the dispatch chain or the advice. Reachable
routes: unsafe 2-arg `getInstance`, and — decisively — **any**
`getInstance(String, Provider)`, a safe, rule-conformant Gets (rule g2 =
`getInstance(alg,_)`; member on android-30). In a woven APK the app's own
`initialize()` call site would throw (that final step INFERIDO; the
monitor-level propagation MEDIDO). A crash on conformant usage outranks an FP.
Inherited (jca validate has the same null hole).

### 3.5 initialize(int, SecureRandom) with a bad size (critical FP+FN pair)

`initError`'s pointcut covers `initialize(int)` only; `init2`'s condition
suppresses the 2-arg call with an invalid size. Measured (KPG-T4):
`g1(RSA); initialize(1024, sr); generateKeyPair()` → **zero InvalidKeySize**
(FN of the specific error) and a spurious InvalidSequence at gen (FP). The
same misuse through the 1-arg overload is reported correctly.

### 3.6 The generatedKeyPair edge, end to end (round-mandated)

Writer measured (KPG-T1); the constant is writer-only in the whole set
(predicate_omissions row; grep: zero readers) and single-slot — the second-slot
question of FEN-SET-GENERATEDKEY-2A-CASA closes as **consequence-free here**
(no reader needs the alg). The semantic route to SignatureSpec runs through
KeyPairSpec's gpu/gpr marks, and CHAIN-T1 measured it end to end: KPG accepts;
`realKp.getPrivate()` births the KeyPairSpec monitor at gpr (its creation
event is the constructor, which generateKeyPair-produced pairs never execute
in app code) → **one InvalidSequence FP from KeyPairSpec** — the batch B
REPROVADA shape re-measured from the writer side — but the
GENERATED_PRIVATE_KEY mark **is** delivered and SignatureSpec.initSign raises
nothing. The edge works at the cost of one FP per pair-access route; no
starvation.

---

## 4. SecureRandomSpec (SRD) vs SecureRandom.cryptsl

### 4.1 Normative matrix

| Clause | MOP | Status | Evidence |
|---|---|---|---|
| EVENTS c1/c2 | c1; c2/c3 split on the RANDOMIZED read — **c3 reports nothing** | INCORRETA (silent FN) | ALFA-SRD-02 |
| EVENTS g1/g2/gI | g1/g2 (g2 covers all safe 2-arg overloads)/g3; g4 unsafe **1-arg only** | partially INCORRETA | ALFA-SRD-08 |
| EVENT gS | genSeed, marks return | FIDELIDADE | ALFA-SRD-05 |
| EVENTS s1/s2 | setSeed2/3 split (setSeed3 **does** report) + setSeed1 | FIDELIDADE (capture) | artifact |
| EVENT ne (`next(numB)` — protected) | next1/next3/ints capture `nextInt(int)`/`nextInt()`/`ints(..)` — extra-alphabet | INCORRETA | ALFA-SRD-06 |
| EVENT nB | next2 — **missing from the `end` state** | **INCORRETA — the batch headline FP** | ALFA-SRD-01 |
| ORDER `Ins, Seeds?, Ends*` | fsm start/init/unsafeInit/end | INCORRETA both directions | §4.2 |
| CONSTRAINT `randAlg in {SHA1PRNG}` | identical | FIDELIDADE | ALFA-SRD-10 |
| REQUIRES `randomized[seed]` | conditions at c2/c3, setSeed2/3 | read faithful; c3 reporting absent | ALFA-SRD-02 |
| ENSURES randomized[this]/[genSeed]/[next]/[numB] | §4.4 | mixed | ALFA-SRD-04/05/06 |

### 4.2 Language verdicts

- `L(CrySL) ⊆ α(L(MOP))`: **FAIL — the strongest FP of the batch.** The `end`
  state lists every consumer except `next2` (SecureRandomSpec.mop:169-177;
  effective row `next2 = {4,1,3,4,4}`). Measured: a second `nextBytes`
  (SRD-T1), `nextBytes` after `setSeed` (SRD-T7 — `new SecureRandom();
  setSeed(seed); nextBytes(out)`, the canonical seeded usage), `nextBytes`
  after `nextInt` (SRD-T8) — each a false InvalidSequence on a trace the raw
  `Ends*` accepts. The jca twin's `end` block is identical minus setSeed3 —
  **inherited, live in both sets, never caught**. Also invisible unsafe-2-arg
  (SRD-T6, FP without the specific accusation).
- `α(L(MOP)) ⊆ L(CrySL)`: **FAIL** — Seeds-after-Ends over-acceptance
  (SRD-T3: `c1 nB setSeed1` silent; product witnesses `C1 GS S1` …): the
  setSeed rows loop at `end`, the rule places `Seeds?` strictly before
  `Ends*`. And c3's silence (SRD-T4: the rule's only REQUIRES violated, zero
  reports on the whole trace — the gh101 comment "each reports in its own
  body" is **false for c3**, a comment/code divergence in a gh101-authored
  hunk).
- Acceptance: only `init` is accepting (match1); CrySL-complete words ending
  in `end`/`unsafeInit` are non-match — inert (accepting store has no
  readers), FEN-C-ACCEPT-END.

### 4.3 What the falsification could NOT break

The gh101 task-3b repair **works as designed** for the violating branches'
diagnosis: `getInstance("NativePRNG"); nextBytes; setSeed` produces exactly
one UnsafeAlgorithm and **zero** InvalidSequence (SRD-T5) — the measured
counterexample proving the carrier FPs of MAC/MDG/KPG/SIG (and batch C) are a
design choice, not a necessity. setSeed3 reports its constraint properly.
Object-level marks are constraint-coupled (§4.4).

### 4.4 RANDOMIZED writer semantics (round-mandated characterization)

The whole set consumes what SRD writes; the measured characterization
(ALFA-SET-11) splits cleanly by object kind:

- **SecureRandom objects**: marked at `match1 = init`, i.e. at the five
  conformant creation events only — c3/g4-created instances are correctly
  never marked (SRD-T2/T4/T5). `randomized[this] after Ins` is implemented
  with the rule's constraint coupling. Downstream reads over SecureRandom
  objects (CipherSpec ranGen, KeyGeneratorSpec random, SSLContextSpec random)
  rest on a sound producer.
- **Material (byte[]/int/IntStream)**: `next2`/`genSeed`/`next1`/`next3`/`ints`
  bodies write **in any monitor state** — bytes produced by a
  violating-constructor instance (SRD-T4) or an unsafe-algorithm instance
  (SRD-T5) are marked RANDOMIZED. CrySL grants ENSURES only to conformant
  instances; every downstream material reader (Iv/GCM/PBE/SKS/PBK/c2/setSeed2)
  can be satisfied by rejected usage — a set-wide FN feed
  (FEN-SRD-RANDOMIZED-OVERGRANT, critical). CipherSpec's own
  GENERATED_CIPHER write-inside-condition shows the coupled alternative was
  known to gh101.
- **Extra-alphabet writes**: the rule's `ne` is the **protected**
  `next(int)` (javap), uncallable by apps; the spec's nextInt/ints events have
  no rule counterpart, and next1/next3 mark **boxed Integers**
  (`RANDOMIZED[Integer.valueOf(16)]=true` measured, SRD-T8 — cache makes the
  mark process-global). No int-typed reader exists today (grep) — inert
  pollution, registered in part by the predicate_edges "inexpressible" row;
  but the register also lists `randomized[randInt]/[randIntInRange]` as
  "present", legitimizing writes the raw rule does not state (ALFA-SET-12).

---

## 5. SignatureSpec (SIG) vs Signature.cryptsl

### 5.1 Normative matrix

| Clause | MOP | Status | Evidence |
|---|---|---|---|
| EVENTS g1/g2 | g1/g3 + g2 (String,String) safe-only; (String,Provider) uncaptured | INCORRETA | ALFA-SIG-03 |
| EVENTS i1/i2/i3/i4 | 1:1, bound, **reads in bodies (no suppression)** | FIDELIDADE | ALFA-SIG-04 |
| EVENTS u1–u4 | fused `update(..)`, binds nothing | FIDELIDADE (capture; slot loss inert) | ALFA-SIG-08 |
| EVENTS s1/s2 (Signs) | pointcuts declare return `byte`; real: `byte[] sign()` / `int sign(byte[],int,int)` | **INCORRETA — zero-capture** | ALFA-SIG-01 |
| EVENTS v1/v2 | 1:1 | FIDELIDADE (capture) | javap |
| ORDER `Gets, ((IS+,(U+,S+)+)+ \| (IV+,(U*,V+)+)+)` | same skeleton + g3* carrier | branch structure FIDELIDADE; carrier + dead Signs INCORRETA | §5.2 |
| CONSTRAINT `alg in {20}` | identical 20, no folding | FIDELIDADE | ALFA-SIG-07 |
| REQUIRES generatedPrivkey/Pubkey | body reads i1/i2/i4; i3 read-free (rule-faithful) | FIDELIDADE | ALFA-SIG-04 |
| ENSURES `signed[out,·] after Signs` | SIGNED written in the dead s1/s2; terminal (registered) | INCORRETA-but-inert | ALFA-SIG-01 |
| ENSURES `verified[sign]` | VERIFIED over the **boxed boolean return** | INCORRETA (wrong object) | ALFA-SIG-05 |

### 5.2 Language verdicts

- `L(CrySL) ⊆ α(L(MOP))`: **FAIL** — carrier `G1u IV4` (SIG-T5: UnsafeAlgorithm
  + 3× InvalidSequence) and invisible-creation `GP IS1/IV4` (SIG-T6: **safe**
  algorithm through a Provider → "but found ." + 3× InvalidSequence).
- `α(L(MOP)) ⊆ L(CrySL)`: **FAIL** — every `… SGN` word is silent
  (zero-capture): `G1s IS1 SGN` (sign-without-update, a rule violation —
  SIG-T3, 0 errors) and the complete conformant `G1s IS1 U SGN` never reaches
  acceptance and never writes SIGNED (SIG-T1). Static ground truth:
  `alfa_javap_android30_batchD.txt` lines for `sign()`. The internal
  inconsistency (`returning(byte[] output)` beside a `byte`-typed pointcut)
  was accepted silently by the generators — fail-open note. Inherited (jca
  twin identical).
- Verify path: faithful and measured (SIG-T2 accepts; SIG-T7's
  verify-after-initSign flagged by both oracles; updates optional before
  verify, mandatory before sign — preserved).
- VERIFIED wrong slot measured (SIG-T2): `VERIFIED[Boolean.TRUE]=true`,
  `VERIFIED[signBytes]=false` — the rule marks the signature bytes; the store
  gets the process-global cached Boolean. No reader exists (registered
  terminal) — contained.

---

## 6. Batch-level phenomena (FEN registry for batch D)

| FEN | What | Specs | Provenance | Measured? |
|---|---|---|---|---|
| FEN-MAC-F3-UNBOUND | event without the spec parameter: AJC silently never matches (exit 0) / monitor broadcasts to all instances | MAC | inherited (jca f2) | yes (ajc probe; MAC-T9) |
| FEN-MAC-KEYGATE-EXTRA | extra-oracle GENERATED_KEY read as suppressing condition → sequence-FP machine + lost accusation | MAC | inherited | yes (MAC-T3) |
| FEN-SRD-NEXTBYTES-FP | `next2` missing from `end` → InvalidSequence on 2nd nextBytes / nextBytes-after-setSeed / after-nextInt | SRD | inherited | yes (SRD-T1/T7/T8) |
| FEN-SRD-C3-SILENT | violating constructor branch reports nothing, ever; gh101 comment claims otherwise | SRD | body inherited; comment gh101 | yes (SRD-T4) |
| FEN-SRD-SEED-AFTER-END | Seeds admitted after Ends → over-acceptance FN | SRD | inherited | yes (SRD-T3) |
| FEN-SRD-RANDOMIZED-OVERGRANT | material marks granted from violating/unsafe instances → set-wide FN feed | SRD (+SET) | inherited | yes (SRD-T4/T5) |
| FEN-SRD-EXTRA-ALPHABET | nextInt/ints extra-alphabet events; boxed-Integer marks (cache) | SRD | inherited | yes (SRD-T8) |
| FEN-KPG-NPE | switch(null) in condition → NPE thrown to the app on invisible creation (incl. safe Provider route) | KPG | inherited | yes (KPG-T5) |
| FEN-KPG-FAILSINK | @fail without reset → per-event cascade + sticky category re-fires on suppressed events | KPG | inherited | yes (KPG-T2/T6) |
| FEN-KPG-INIT2-SUPPRESSED | bad keySize via initialize(int,SecureRandom): no InvalidKeySize + spurious InvalidSequence | KPG | inherited | yes (KPG-T4) |
| FEN-KPG-INITERROR-PLACEMENT | initError neither advances (FP at gen) nor counts as Inits (FN on multi-init) | KPG | gh101 form | yes (KPG-T3/T7) |
| FEN-SIG-SIGN-VOID | `byte`-typed sign pointcuts can never match → Signs channel dead (FEN-SSL-ENGINE-VOID family) | SIG | inherited | yes (javap + SIG-T1/T3) |
| FEN-SIG-VERIFIED-WRONGSLOT | verified[sign] marked on the boxed return Boolean | SIG | inherited | yes (SIG-T2) |
| FEN-C-CARRIER-SEQFAIL | carrier FP + G9 pairing | MAC, MDG, KPG (H2 confirmed), SIG — **not SRD** | inherited | yes (T2/T3/T6/T5 resp.) |
| FEN-C-GETS-INVISIVEL | invisible creations → FP storms / NPE / lost accusations | all five | inherited | yes |
| FEN-D-EMPTYLABEL-LIVE | H4 "but found ." live mechanism (born-invisible monitors) | MAC, MDG, SIG (KPG crashes instead) | inherited | yes (MAC-T5, MDG-T4, SIG-T6) |
| FEN-C-WHITELIST-EXTRA | MDG folding+aliases (6 measured FN); MAC 6 alias spellings (Android threat) | MDG, MAC | inherited (gh99-registered variants) | yes (folding probe) |
| FEN-D-ARITH-OMITIDA | arithmetic constraints untranslated and unregistered | MAC, MDG | inherited | artifact + register search |
| FEN-D-PREPAREDHMAC-GUARANTEED-FIRE | faithful Mac read × unwritable writer (batch A) = guaranteed FP | MAC/SET | gh101 read; writer batch A | yes (MAC-T8) |
| FEN-D-KEYPAIR-EDGE | generateKeyPair route: mark delivered + one KeyPairSpec FP per pair access | KPG/SET | inherited (KeyPairSpec c1) | yes (CHAIN-T1) |
| FEN-D-REGISTER-ANCHOR-DRIFT | predicate_edges rows anchored to 1.5.2 contradict the raw oracle ("present" for extra-oracle edges) | SET | gh101 registers | artifact |
| FEN-C-ACCEPT-END | CrySL-complete words end outside match | MDG, SRD, SIG (via carriers), MAC (key-gate) | inherited | product tables |

## 7. Verdict shape (Alfa's covered dimensions)

Every one of the five specs carries at least one **critical FAIL with an
executed, realizable counterexample**, so under pre_registro §4 none can be
APROVADA in the dimensions I cover:

- **MAC**: f3 unbound (dead or broadcasting), extra-oracle key gate (FP+FN,
  measured), carrier FP, invisible-creation FP with empty labels, unregistered
  arithmetic omissions.
- **MDG**: carrier FP, invisible-creation FP + empty label, 6 measured folding
  FNs. (Best language core of the batch otherwise.)
- **KPG**: NPE crash on conformant Provider usage, fail-sink with sticky
  category, init2 FP+FN pair, initError placement divergent both directions,
  H2 confirmed.
- **SRD**: nextBytes FP on ubiquitous conformant usage, c3 silent FN,
  Seeds-after-Ends FN, material-mark over-granting feeding the whole set.
- **SIG**: dead Signs channel (silent FN + acceptance loss), carrier FP,
  invisible-creation FP storm, VERIFIED wrong slot.

Positive results the falsification attempt could NOT break (recorded):
MDG safe-path cycle fidelity incl. reuse and the Provider capture; the D-S12
reset removal (fidelity vs the raw oracle); Mac's macced projection design and
deferred marking; SIG's body-read repair (G9-clean at the read site) and exact
20-literal list; KPG's literal constraint fidelity and the measured
generatedKeyPair chain delivery; SRD's constraint-coupled object-level
RANDOMIZED writer and the unsafeInit no-pairing design — the batch's proof
that the carrier-FP family is avoidable.

§8 adversarial targets, all closed with executed/artifact evidence:
`MessageDigest.reset` removal → FIDELIDADE (ALFA-MDG-06);
`!macced[_, plainText]` transcription → faithful projection + two measured
registered residues (ALFA-MAC-08/09); D-S13 ByteBuffer FN and Byte-cache
over-marking → both measured (MAC-T6/T7), Integer analogue measured on SRD
(SRD-T8).

INCONCLUSIVE hygiene: no claim converts absence of evidence into safety.
Declared pendencies: dexlib2 handling of the malformed f3 descriptor and of
the gen/nextInt inherited-member captures (Beta); the KPG NPE final
crash-in-APK step (monitor-level propagation measured, advice propagation
inferred); Android-provider resolvability of the MAC alias spellings; the
untracked-object CrySL reading (assumption declared per claim).

## 8. Claim counts

59 claims (MAC 13, MDG 11, KPG 11, SRD 10, SIG 8, SET 6): 21 PASS, 38 FAIL,
0 INCONCLUSIVE; every FAIL carries a `fenomeno_id` (D-batchB-1 checked
programmatically). Criticals (23): ALFA-MAC-02/03/04/05/07,
ALFA-MDG-03/04/05, ALFA-KPG-02/03/04/05/07/10, ALFA-SRD-01/02/04,
ALFA-SIG-01/02/03, ALFA-SET-10/11/13. (SET rows scored separately per
D-piloto-4.)

## 9. File hashes (sha256, files of record in `batchD/`)

```
0b86e9fe0d39f4f96d3e55daed5980ec1373b962d24db42a895fa7ab365365da  alfa_claims.csv
88ca9d4a391b41d7dcf513cff2a8ee045f2849977000a7b93c4911ddd116f4bc  alfa_language_check.py
ed7737a6071eb364429b527c52664166422fe967983fcaef304d40c86c91980e  alfa_language_results.txt
c16252614209a7a0eecea261beceb818787c4937c19ea50e44e8849e67c185cf  alfa_HarnessD.java
78bb1cbaa78ba20ebb6c10ca607040ef8dbb8ba75920ed7154ccff24c981cc85  alfa_harnessD_rep1.txt (= rep2 = rep3)
f98f9cce7f8ce8a50e847743e70073668b2d872dc78625064a4d7ca5a001444d  alfa_FoldingD.java
d7f6c4781f9ec33a7c93b2b20e31194f265a47c263b124aeff44a96c0438f08a  alfa_foldingD_rep1.txt (= rep2 = rep3)
a369a9235171a3de59b7eb68b5ae7cddb646f7d1cb9a6d6ae3c8e3e53876cb3b  alfa_mac_f3_probe.txt
4644fdab9a7e724a5c9c4fcaf0451d6acfffc624eb1885af8a2432cf2f238939  alfa_javap_android30_batchD.txt
```
(Duplicated in `alfa_hashes.txt` beside this report.)

Commands and working directories: generation per `batchD/generation_manifest.md`
(not re-run); analysis and harness run from the session scratch
(`scratchpad/batchD/alfa/`), inputs identified by hashes. No spec, rule, or
production file was modified; no JavaMOP/RV-Monitor execution over the spec
tree; no emulator touched; no batchD beta_/gama_ file read.
