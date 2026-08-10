# ALFA — Batch B report (CrySL conformance and formal logic)

Agent Alfa, round "batch B" of the adversarial audit of `jca_android` vs the api30
CrySL rules. Date: 2026-08-09. Specs: **CipherInputStreamSpec (CIS)**,
**CipherOutputStreamSpec (COS)**, **KeyPairSpec (KPR)**, **SecretKeySpec.mop /
target interface `javax.crypto.SecretKey` (SKY)**, **PBEKeySpecSpec (PBK)**.

Inputs: frozen `.mop`/`.cryptsl` per `batchB/generation_manifest.md`; all 20 round
artifacts re-hashed by me this session — 20/20 equal to the manifest (freeze PASS).
Oracle: the RAW api30 rules (pre-registration §1). ORDER precedence: reading A
(D-piloto-1) — **this is the first round where commas actually occur in the
audited ORDERs** (all five rules use them); reading A was applied throughout.
Language verdicts are issued over the **effective automaton including its
indexing** (D-piloto-3 + batch A juiz §6 item 1). Sequential Thinking MCP was
available and used (3 recorded steps). Standing round rules applied: indexing-tree
check (FEN-HMC-MONITOR-GLOBAL), both directions of every predicate edge,
dimension-5 (parametric/lifecycle) claims per spec, D-piloto-4 dimension-at-creation.

Epistemic labels: **PROVADO** (algorithmic check / structural proof on the
artifact), **MEDIDO** (executed command, output recorded), **OBSERVADO_EM_ARTEFATO**
(cited file:line), **INFERIDO**, **NAO_VERIFICADO**.

Companion files (all under `batchB/`, sha256):

```
23d6770ac68585b2d843b695e441d57b54bfa3c1df0248ff010e8ef8669bcdbf  alfa_automata_check.py
81c46c7ab929401216dfac1da89dbd9440fa1dc9cda288269dffd4b03fd6d538  alfa_automata_output.txt
931a6559424f90bd3fc2133c0f4313485ba07f604c095299d01a9f6ffd4dd294  alfa_AlfaDrive.java
02c0ed20c380a9b8d54a6403f188a89b1a94e48550ce2a192775a539a7de319d  alfa_drive_output.txt
b6ef1133e166c94e23271f8ccef6c9a140f7ce552ff2d61fee50bfbece3e89d6  alfa_api30_members_output.txt
```

`alfa_AlfaDrive.java` was compiled with the round-input `*RuntimeMonitor.java`
(byte-identical to the manifest hashes) against the production jars
`rvsec-core-0.9.3-SNAPSHOT.jar` (`7b4d72aa…`), `rvsec-logger-csv-0.9.3-SNAPSHOT.jar`
(`6787f411…`), `rv-monitor-rt-0.9.3-SNAPSHOT.jar` (`0fa65fbc…`) — the same three
hashes the batch A judge recorded — and run **3 times with identical output**
(pre-registered repetition policy); `alfa_drive_output.txt` is rep 1.
`alfa_api30_members_output.txt` was built from **extracted class bytes** of the
frozen android-30 jar (`96ccfdc8…`), per the batch A `javap -classpath` trap.

## 0. Batch-level structure

Unlike batch A (single-constructor rules), all five batch B rules have
**multi-event lifecycles**: repetition (`Reads+`, `Writes+`, `ge*`, `(pu*, pr*)*`),
optionality (`co?`, `d?`), a mandatory closing event (`c`, `cP`), and heavy
predicate traffic in both directions. Three structural facts dominate the batch,
all PROVADO/MEDIDO:

1. **Two specs are parameterless and therefore process-global.** `CipherInputStreamSpec()`
   (.mop:11) and `CipherOutputStreamSpec()` (.mop:11) declare no spec parameter;
   the generated monitors are one `private static final <Spec>Monitor <Spec>__Map =
   new <Spec>Monitor()` (CIS RuntimeMonitor:275, COS :309, both
   `AbstractAtomicMonitor`). Every stream in the process shares one automaton.
   This is the batch A HMC phenomenon in a worse setting: these rules have long
   lifecycles, so the **second** stream in a process — sequential, not even
   interleaved — cascades spurious violations (executed, §1/§2).
2. **KPR's constructor event binds no spec parameter.** `event c1 … returning(KeyPair kp)`
   (.mop:29) names `kp` while the spec parameter is `keyPair` (.mop:19); JavaMOP
   binds by name, so c1 lands in the **empty parameter slice** and is broadcast
   to the empty-binding monitor and every existing monitor
   (KeyPairSpecRuntimeMonitor:306, :324-354 dispatch; :380-430 clone-from-empty).
   This is the exact defect class gh101 registered and repaired for
   `PBEKeySpecSpec.f1/f2` and `TrustManagerFactorySpec.gtm1` (tasks.md:81,
   design.md:190) — present, unregistered, in KeyPairSpec. The gh101 census's own
   detector signature — `AbstractSynchronizedMonitor` instead of
   `AbstractAtomicMonitor` (design.md:190) — is visible in the round artifact
   (KeyPairSpecRuntimeMonitor:127).
3. **Extra-oracle predicate gates recur.** The api30 CIS/COS rules have **no
   REQUIRES section** and the api30 Cipher rule ensures only `encrypted[…]`
   (Cipher.cryptsl:187-193) — `generatedCipher` **does not exist in the api30
   oracle**; the api30 SecretKey rule has **no REQUIRES** — the `GENERATED_KEY`
   gate on `e1` is extra; the api30 PBEKeySpec rule requires `randomized[salt]`
   **only** — the `randomized[password]` conjunct is extra. Per the fixed round
   rule (batch A precedent FEN-DHG-SUPRESSAO / FEN-SKS-WHITELIST), extra-oracle
   conditions are INCORRETA vs the raw oracle; registration ≠ approval.

Method for the language dimension: `alfa_automata_check.py` does **exact product
reachability** (no depth bound) over (reference state, effective state) with
concrete letters that carry the CrySL projection, the MOP projection (including
suppression = no event, verified in the monitors' prologues), a raw-oracle
per-call error tag, and the body-error flag; a step where oracle emission ≠
monitor emission is a counterexample; shortest witnesses via BFS with full state
walks. `__RESET` in `@fail` is modeled as reset-to-initial (handler source).
End-of-trace (incomplete operation) is reported separately. Multi-instance models
implement the verified dispatch semantics (global static monitor; empty-slice
broadcast + clone).

## 1. CipherInputStreamSpec ↔ CipherInputStream.cryptsl

### Scientific log
- **Question**: rule `ORDER Constructs, Reads+, c` with `Constructs := c1|c2`,
  `CONSTRAINTS len > off`, `ENSURES cipheredInputStream[is, ciph]`, **no
  REQUIRES**. Does the translation preserve it per instance?
- **Hypothesis to falsify**: "the automaton shape `c1 (r1|r2)+ cl1` is the rule".
- **Discriminating tests**: indexing-tree check; product check; two-stream drive;
  register absence search.
- **Evidence**: spec has **no parameter** → static global monitor
  (RuntimeMonitor:275, OBSERVADO). Drive CIS-a: first legal stream, 0 errors;
  **CIS-b: second legal stream → 3 spurious `InvalidSequenceOfMethodCalls`
  (c1, r1, cl1 each fail + `__RESET` cascade), 3 identical reps — MEDIDO**.
  Product check: FP witness `[ctor2_unmarked]` (extra-oracle body check), FN
  witness `[ctor2_marked, ctor1_subclass]`; constraint witness
  `[ctor2_marked, read3_lenLEoff]` silent (PROVADO, alfa_automata_output.txt).
  Drive CIS-c: ctor with unmarked cipher → 1 `UnsatisfiedConstraint` where the
  raw oracle is silent (MEDIDO).
- **Result**: hypothesis falsified on four independent axes (below).
- **Uncertainty**: weaving/device (G6/G10) outside scope; the 1-arg-ctor FN needs
  a user subclass to realize (the ctor is `protected` in android-30 — MEDIDO from
  class bytes).
- **Decision**: file ALFA-CIS-01..08.

### Normative matrix
| Clause (api30) | MOP translation | Effective artifact | Status |
|---|---|---|---|
| OBJECTS is/ciph/b/off/len | c1 binds (is,ciph); r2 binds (arr,offset,len) | aspect binds | FIDELIDADE (binding side) |
| EVENT c1: `CipherInputStream(is)` (protected ctor, present in android-30) | **no event** | — | **OMITIDA** (ALFA-CIS-03, major, unregistered): a subclass-constructed stream is invisible; its first read then fires a spurious fail (product witness) |
| EVENT c2: `CipherInputStream(is, ciph)` | c1, plain `after` + `args` | `c1={3,4,4,4,4}` | FIDELIDADE at member level |
| EVENTS r1/r2/r3, `Reads` | r1 fuses read()/read(byte[]); r2 = 3-arg | `r1=r2={4,1,4,1,4}` | FIDELIDADE_DEMONSTRADA (fusion faithful: no clause distinguishes r1O/r2O; ALFA-CIS-08) |
| EVENT c: close() | cl1 | `cl1={4,2,4,4,4}` | FIDELIDADE |
| ORDER `Constructs, Reads+, c` | `ere : c1 (r1|r2)+ cl1` | **one static monitor for all instances** | **INCORRETA** (ALFA-CIS-01, critical): per-instance language broken; executed 3-FP cascade on the second legal stream |
| CONSTRAINTS `len > off` | **not transcribed** (r2 body empty, .mop:30-32) | no check anywhere | **OMITIDA** (ALFA-CIS-04, major, unregistered — searched data/gh101/*.csv and the change tree, 0 hits for "len > off"). Oracle-bias note: the raw constraint itself is odd (the real JDK contract is offset/len envelope, not `len > off`); recorded, not corrected |
| *(no REQUIRES in the rule)* | body check `validate(GENERATED_CIPHER, ciph)` + `UnsatisfiedConstraint` (.mop:22-25) | body emits before transition | **INCORRETA** (ALFA-CIS-02, critical): extra-oracle; executed FP (CIS-c). Registered in divergence_record.csv:2 — but the register says "Closes the rule's REQUIRES generatedCipher[ciph]" and **the api30 rule contains no REQUIRES at all**; `generatedCipher` exists in no api30 rule (grep over all 33) — an upstream-1.5.2 anchor import; registered ≠ approved |
| ENSURES `cipheredInputStream[is, ciph]` | not written (no Property constant) | — | LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA (ALFA-CIS-05, PASS): registered predicate-no-constant omission (predicate_omissions.csv:19); no consumer in any api30 rule (grep). Still blocks any total-adherence claim. Note: the pair `[is, ciph]` would also not fit the unary store (ExecutionContext.java:102-120) |
| *(diagnostics)* | `@fail` = 2-arg `ErrorDescription` (.mop:39) | every sequencing violation reports `expecting=unknown` (MEDIDO in drive) | **INCORRETA** (ALFA-CIS-06, major): G9 criterion "nenhum unknown" fails on the spec's only sequencing channel |
| *(end of trace)* | never-closed stream: no signal | product: ref states {0,1,2} non-accepting, silent | OMITIDA minor (ALFA-CIS-07): CrySL incomplete operation unreported; no end-of-trace channel exists in this translation approach; unregistered |

### α and binding profile
| Java call | CrySL event | MOP event | Notes |
|---|---|---|---|
| `new CipherInputStream(is, ciph)` | c2 | c1 | is/ciph by `args`; **no object bound to any monitor index** (parameterless spec) — the property object of the rule (the stream) is not represented |
| `new CipherInputStream(is)` (subclass) | c1 | — | α undefined: omission |
| `read()` / `read(byte[])` | r1 / r2 | r1 | fusion, faithful |
| `read(byte[],int,int)` | r3 | r2 | constraint components bound but unused |
| `close()` | c | cl1 | |

α is total on public-API calls but **the monitor identity plane is collapsed**:
all instances map to one automaton — the α-level root cause of ALFA-CIS-01.

## 2. CipherOutputStreamSpec ↔ CipherOutputStream.cryptsl

### Scientific log
- **Question**: same family as CIS plus one alphabet question: the spec declares
  `fl` (flush) inside the loop `(w1|w2|fl)+` while the rule's alphabet has **no
  flush event**.
- **Hypothesis to falsify**: "fl is harmless because flush is oracle-invisible".
- **Discriminating test**: two named product witnesses + executed drive COS-a/COS-b.
- **Evidence**: table `fl={4,1,1,4,4}` — fl **alone advances the loop** (state
  2→1), and from the accepting state 3 → 4 (fail). Drive COS-a
  `[construct, flush, close]` → **0 errors** while the oracle rejects (`Writes+`
  unmet at close): executed FN. Drive COS-b `[construct, write, close, flush]` →
  the flush-after-close step alone emits a spurious
  `InvalidSequenceOfMethodCalls`: executed FP. 3 identical reps. Register search:
  0 hits for "flush" anywhere in data/gh101 or the change tree.
- **Result**: hypothesis falsified in both directions — an event **outside the
  rule's alphabet both accepts what the oracle rejects and rejects what the
  oracle accepts**. Cleanest pure-language counterexample of the batch.
- **Decision**: ALFA-COS-02 critical, plus the CIS-family claims (global monitor
  executed as COS-b cascade: 3 spurious errors on the second legal stream).

### Normative matrix (differences from CIS only)
| Clause (api30) | MOP translation | Status |
|---|---|---|
| EVENTS w1(int)/w2(byte[])/w3(3-arg), `Writes` | w1 fuses write(int)/write(byte[]); w2 = 3-arg | FIDELIDADE (fusion faithful) |
| *(flush not in the rule)* | event `fl` inside `(w1|w2|fl)+` (.mop:32,36) | **INCORRETA** (ALFA-COS-02, critical, unregistered): FN `c1 fl cl` (executed, 0 errors); FP `c1 w1 cl fl` (executed, spurious fail). Under α (flush ⟼ ε) both inclusions fail — walks in alfa_automata_output.txt |
| ORDER / indexing | parameterless → global static monitor (RuntimeMonitor:309) | **INCORRETA** (ALFA-COS-01, critical, executed cascade) |
| EVENT c1 1-arg (protected) | omitted | **OMITIDA** (ALFA-COS-04, major) |
| CONSTRAINTS `len > off` | not transcribed | **OMITIDA** (ALFA-COS-05, major) |
| *(no REQUIRES)* | GENERATED_CIPHER body check | **INCORRETA** (ALFA-COS-03, critical; same phenomenon as CIS — FEN-SET-GENCIPHER-EXTRA) |
| ENSURES `cipheredOutputStream[os, ciph]` | not written; registered (predicate_omissions.csv:20) | LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA (ALFA-COS-06, PASS) |
| diagnostics / end-of-trace | `@fail` 2-arg → `expecting=unknown`; no end-of-trace channel | INCORRETA major (ALFA-COS-07) / OMITIDA minor (ALFA-COS-08) |

## 3. KeyPairSpec ↔ KeyPair.cryptsl

### Scientific log
- **Question**: `ORDER co?, (pu*, pr*)*` — the constructor is **optional**
  (a KeyPair usually comes from `KeyPairGenerator.generateKeyPair()`), and under
  reading A `(pu*, pr*)*` = `(pu|pr)*`. REQUIRES generatedPrivkey/generatedPubkey
  on the ctor args; ENSURES generatedKeypair[this,_] after co, generatedPubkey[retPub]
  after pu, generatedPrivkey[retPriv] after pr.
- **Hypotheses to falsify**: (H1) "`ere: c1 (gpu|gpr)*` accepts the same
  per-instance language"; (H2) "the monitor is per-object on keyPair".
- **Evidence**: H1 — table `gpu={2,1,2}`: gpu from the initial state → state 2 =
  fail; product witness `[getPublic]`; **drive KPR-a: a real
  `KeyPairGenerator`-obtained pair, `getPublic()` first → 1 spurious
  `InvalidSequenceOfMethodCalls` (MEDIDO, 3 reps)**. H2 — c1's `returning` names
  `kp`, not the spec parameter `keyPair` (.mop:19 vs :29); the dispatch goes
  through the empty-binding `Tuple2` and broadcasts to the whole monitor set
  (RuntimeMonitor:306, :324-354); monitors for bound objects are **cloned from
  the empty-binding monitor** (:380-430). **Drive KPR-b: two legal constructions
  → spurious fail at the second c1; then `kp1.getPublic()` → another spurious
  fail (contaminated clone). 2 FPs on a fully legal two-object trace (MEDIDO)**.
  Register search: the empty-slice defect class is registered for PBK f1/f2 and
  TMF gtm1 (tasks.md:81, design.md:190) — **no row for KeyPairSpec.c1** in
  conformance_record, divergence_record, predicate_omissions, tasks, design,
  proposal; the census signature `AbstractSynchronizedMonitor` is present in the
  artifact (:127).
- **Result**: both hypotheses falsified, each with an executed counterexample.
  The dominant real-world usage (generator-obtained pairs) fires a spurious
  violation on its **first** getter.
- **Uncertainty**: none structural; the `@match`-marks-wrong-object effect after
  broadcasts is OBSERVADO in code (monitor field copied by clone) but not driven.
- **Decision**: ALFA-KPR-01/02/06 critical; 03/05 PASS; 04 minor; 07 major; 08
  register gap.

### Normative matrix
| Clause (api30) | MOP translation | Effective artifact | Status |
|---|---|---|---|
| OBJECTS consPriv/consPub/retPriv/retPub | c1 args + gpu/gpr returning | aspect binds | FIDELIDADE (positions/types) |
| EVENT co (ctor) | c1 — `returning(KeyPair kp)` binds **no spec parameter** | empty-slice broadcast + clone (:306,:324-430); `AbstractSynchronizedMonitor` (:127) | **INCORRETA** (ALFA-KPR-02, critical, executed KPR-b, unregistered) |
| ORDER `co?, (pu*, pr*)*` | `ere: c1 (gpu|gpr)*` — **co made mandatory** | `gpu[0]=2` (fail) | **INCORRETA** (ALFA-KPR-01, critical, executed KPR-a, unregistered). `(pu*, pr*)*` ≡ `(pu|pr)*` under reading A: PROVADO equivalent (ALFA-KPR-05, PASS) |
| REQUIRES generatedPrivkey[consPriv], generatedPubkey[consPub] | body reads GENERATED_PRIVATE_KEY / GENERATED_PUBLIC_KEY, report-not-suppress (.mop:32-39) | correct constants/objects; writers gpu/gpr + KeyStoreSpec:77-78 | FIDELIDADE on the non-null path (ALFA-KPR-03, PASS); **null-guarded**: `new KeyPair(null, null)` silently passes where the raw oracle's predicates are unsatisfiable → FN, INCORRETA minor (ALFA-KPR-04) |
| ENSURES generatedKeypair[this,_] after co | `setProperty(GENERATED_KEY_PAIR, kp)` in c1 body | unary write = faithful projection of `[this,_]`; no reader in oracle or set (registered, predicate_omissions.csv:3) | FIDELIDADE / registered write-no-read. Written even when REQUIRES failed — oracle grants no predicate on a violated object (CryptoAnalysis semantics, INFERIDO) — impact nil today (no reader); noted inside ALFA-KPR-03 |
| ENSURES generatedPubkey[retPub] after pu / generatedPrivkey[retPriv] after pr | gpu/gpr bodies write the correct constants on the returned keys (.mop:47,:58) | readers: CipherSpec:157-158,178-179,199-200; SignatureSpec:69,83,107 | FIDELIDADE_DEMONSTRADA (the gh101 wrong-constant repair holds in the frozen bytes). The body still executes on the spurious-fail path, so the predicate plane survives the automaton FPs |
| *(lifecycle, dim-5)* | two instances share c1 events; clones inherit empty-monitor state | executed contamination (KPR-b) | **INCORRETA** (ALFA-KPR-06, critical) |
| *(diagnostics)* | `@fail` 2-arg (.mop:64) → `expecting=unknown` on every spurious and every real sequencing report; `@match` marks `keyPair` monitor field that a clone may have copied from another instance | MEDIDO / OBSERVADO | **INCORRETA** (ALFA-KPR-07, major) |

Cosmetic (no claim): the comment at .mop:50-54 narrates the pre-gh101 wrong-constant
defect in a way that reads as current state — P4 friction; the code at :58 is correct.

## 4. SecretKeySpec.mop (target interface `javax.crypto.SecretKey`) ↔ SecretKey.cryptsl

### Scientific log
- **Question**: rule `ORDER ge*, d?`, **no REQUIRES, no CONSTRAINTS**; ENSURES
  `preparedKeyMaterial[keyMaterial] after ge`; NEGATES `generatedKey[this,_]
  after d`. The spec gates e1 with `validate(GENERATED_KEY, secretKey)` and has
  **no `@fail` handler and an empty `@match`**.
- **Hypotheses to falsify**: (H1) "`e1* (d|epsilon)` = `ge*, d?` in the effective
  automaton"; (H2) "the gate is a faithful reading of some rule clause";
  (H3) "ORDER violations are reported".
- **Evidence**: H1 — tables `e1={0,2,2}`, `d={1,2,2}`, accepting {0,1}
  (match = nextstate∈{0,1}): dual inclusion PROVADO including the epsilon
  alternative (initial state accepting). H2 — the api30 rule has **no REQUIRES
  section** (SecretKey.cryptsl:1-31); the gate is a suppression prologue
  (`return false` before `handleEvent`, RuntimeMonitor:127-133). **Drive: an
  unmarked key's `getEncoded` is suppressed and `RANDOMIZED` (the registered
  surrogate for `preparedKeyMaterial`) is NOT written (`validate=false`,
  MEDIDO)** — the oracle unconditionally ensures `preparedKeyMaterial` after ge,
  and the downstream reader `SecretKeySpecSpec.c1` (REQUIRES
  preparedKeyMaterial, carried as RANDOMIZED) then accuses legal key material:
  the FEN-DHG-SUPRESSAO shape on a cross-spec edge. Realizable sources of
  unmarked keys inside the modeled world: `SecretKeyFactory.generateSecret`
  (unmodelled — no GENERATED_KEY writer), KeyStore keys (KeyStoreSpec writes
  only GENERATED_PRIVATE/PUBLIC_KEY), any key whose producer spec suppressed its
  own mark (batch A SKS criticals cascade here). H3 — the spec has no `@fail`;
  state 2 carries **no category** (only `Category_match` exists,
  RuntimeMonitor:88): **drive: `destroy; getEncoded; destroy` → 0 errors on two
  realizable oracle violations (MEDIDO, 3 reps)**. The ge-after-d violation is
  doubly unreachable: even with a handler, d removes GENERATED_KEY (.mop:41), so
  the gate suppresses the post-destroy e1 and no transition occurs at all.
- **Register search**: divergence_record.csv:83 registers the d event + `(d |
  epsilon)` and asserts "a second d or a getEncoded after d **fails**" — the row
  does not record that the spec has **no `@fail` handler** (the "fail" is
  unobservable) nor that the gate makes the ge-after-d transition unreachable.
  No register row covers the gate itself (searched conformance_record,
  divergence_record, predicate_omissions, the change tree; predicate_inventory
  rows 99/101 list the read/remove mechanically, without conformance judgment).
- **Result**: language PASS; the spec cannot report anything, ever (its only
  outputs are predicate writes), and its gate starves the oracle's
  `preparedKeyMaterial` edge.
- **Uncertainty**: the α-composition with `SecretKeySpecSpec` (same runtime
  object, two monitors) is coherent on the predicate plane (SKS writes
  GENERATED_KEY at `@match`; SKY's gate reads it; d removes it — the NEGATES
  edge is honored across specs, correct per-instance scope). Whether
  `call(SecretKey.getEncoded())` matches a call whose static receiver type is
  the implementing class (`SecretKeySpec`) is a capture question → Beta;
  filed INCONCLUSIVE (ALFA-SKY-07) because the α consequence is trace-splitting
  by static type.
- **Decision**: ALFA-SKY-01/05 PASS; 02/03/04 critical; 06 minor; 07 INCONCLUSIVE.

### Normative matrix
| Clause (api30) | MOP translation | Effective artifact | Status |
|---|---|---|---|
| OBJECTS key/keyMaterial | e1 target + returning | aspect binds | FIDELIDADE |
| EVENT ge | e1 **gated by extra-oracle `GENERATED_KEY`** | suppression prologue :127-133 | **INCORRETA** (ALFA-SKY-02, critical, unregistered): oracle has no REQUIRES; suppressed ge withholds the ENSURES → executed starvation, downstream FP feed |
| EVENT d | d, per-object, `remove(GENERATED_KEY, secretKey)` | :148-152 | FIDELIDADE (NEGATES `[this,_]` scope correct — per-instance remove) |
| ORDER `ge*, d?` | `ere: e1* (d | epsilon)` | accepting {0,1}; dual inclusion | FIDELIDADE_DEMONSTRADA (ALFA-SKY-01, PASS) |
| ENSURES `preparedKeyMaterial[keyMaterial] after ge` | `setProperty(RANDOMIZED, key)` | registered surrogate (predicate_edges.csv:64 "present-surrogate") | **INCORRETA** (ALFA-SKY-04, critical, FEN-SKS-SURROGATE writer side): RANDOMIZED aliases two distinct oracle predicates — SecureRandom output and key material become indistinguishable to every reader (e.g., `getEncoded` bytes satisfy PBK's `randomized[salt]`); registered ≠ approved, no equivalence proof on file |
| NEGATES `generatedKey[this,_] after d` | remove per-object | correct | FIDELIDADE (part of ALFA-SKY-05, PASS) |
| *(violation reporting)* | no `@fail`, empty `@match` | state 2 categoryless | **OMITIDA** (ALFA-SKY-03, critical): both realizable ORDER violations silent — executed 0-errors proof; distinguished from batch A's dead-`@fail` minor precedent because here violating traces EXIST and there is no live channel at all |

## 5. PBEKeySpecSpec ↔ PBEKeySpec.cryptsl

### Scientific log
- **Question**: rule `ORDER c1, cP` (clearPassword **mandatory**), FORBIDDEN
  `PBEKeySpec(char[]) => c1` and `PBEKeySpec(char[],byte[],int) => c1`,
  CONSTRAINTS `iterationCount >= 10000` and `neverTypeOf(password, String)`,
  REQUIRES `randomized[salt]` **only**, ENSURES `speccedKey[this, keylength]`,
  NEGATES `speccedKey[this,_] after cP`.
- **Hypotheses to falsify**: (H1) "the layer-2 carrier prefix
  `(f1|f2|err1|err2|err3)* c1 c2` is language-equivalent modulo α"; (H2) "the
  guard set equals the rule's clause set"; (H3) "FORBIDDEN `=> c1` is honored".
- **Evidence**: H1 — on the valid path, dual inclusion PROVADO; but the rule has
  a **mandatory event after the constructor**, so the batch A carrier argument
  ("no subsequent mandatory event") does not transfer: a violating or forbidden
  construction leaves the automaton at state 0 and the object's **legal**
  `clearPassword()` then hits `c2[0]=3` (fail). **Drive PBK-a (iter=500,
  everything else conforming): 1 correct `UnsatisfiedConstraint` + 1 spurious
  `InvalidSequenceOfMethodCalls` at the legal cP (MEDIDO, 3 reps)** — the exact
  "residue displacing the accusation to the next call" the protocol §8 names
  (D-S10 class). (ALFA-PBK-03, critical.)
  H2 — c1's condition and err2 demand `RANDOMIZED(password)` (.mop:43,:61); the
  rule requires `randomized[salt]` only. **Drive PBK-b (iter=10000, salt
  randomized, user-typed password — the ordinary legal use): 1
  `UnsatisfiedConstraint` ("first argument should have been randomized") + 1
  spurious sequence violation at cP + `SPECCED_KEY` withheld
  (`validate=false`) although the oracle grants `speccedKey` (MEDIDO)**.
  Unregistered as a divergence — conformance_record.csv:18 documents
  RandomStringPassword as a *mitigation* ("a password derived from SecureRandom
  is not accused"), which concedes the accusation exists; the raw oracle never
  licenses it. (ALFA-PBK-02, critical.)
  H3 — FORBIDDEN maps the two ctors **to c1** for typestate continuation; the
  spec's f1/f2 loop at 0 instead. **Drive PBK-c: `new PBEKeySpec(pwd)` then
  `clearPassword()` → 2 errors** where the oracle produces exactly one
  ForbiddenMethodError with a legal cP; both MOP reports carry the category
  `InvalidSequenceOfMethodCalls` (`ErrorType` has no forbidden-method value).
  (ALFA-PBK-04 major; category part in ALFA-PBK-07.)
- **Other clauses**: guards partition exactly (c1 = ¬err1∧¬err2∧¬err3;
  overlapping err co-firing is by design and documented, .mop:80-87);
  `speccedKey[this, keylength]` written **unary** — second slot dropped
  (FEN-SET-GENERATEDKEY-2A-CASA family), register slot-blind
  (predicate_edges.csv:55 "present" with no slot note); MOP-side reader absent
  (SecretKeyFactory unmodelled — registered, predicate_omissions.csv:10);
  NEGATES via per-object `remove(SPECCED_KEY, s)` — correct scope;
  `neverTypeOf(password, String)` untranslated — registered as outside dynamic
  expressibility (data/gh101/README.md:697) and genuinely unobservable at the
  join point (the argument is already `char[]`): LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA;
  err1 message says "**>= 1000**" while the guard tests **10000** (.mop:42 vs
  :55) — the identical 10× defect batch A measured in PBEParameterSpecSpec
  (FEN-PBE-MSG family). End-of-trace: cP is mandatory; a never-cleared spec is
  an oracle incomplete-operation, silent here.
- **Decision**: ALFA-PBK-01/06/08/10 PASS; 02/03 critical; 04/05/07 major; 09 minor.

### Normative matrix
| Clause (api30) | MOP translation | Effective artifact | Status |
|---|---|---|---|
| OBJECTS password/salt/iterationCount/keylength | bound by position in all 7 events; every event binds `s` | per-object `MapOfMonitor` (:491) | FIDELIDADE (ALFA-PBK-08, PASS, incl. dim-5 isolation) |
| FORBIDDEN 1-arg/3-arg `=> c1` | f1/f2 report in body, loop at 0 | `f1=f2={0,3,3,3}` | **INCORRETA** (ALFA-PBK-04, major): mapping not honored → legal cP spuriously fails (executed PBK-c); category not forbidden-flavored |
| EVENT c1 (4-arg) | c1 + carriers err1/err2/err3 | `c1={1,3,3,3}`, err loops | valid path FIDELIDADE (ALFA-PBK-01, PASS); **residue INCORRETA** (ALFA-PBK-03, critical, executed PBK-a) |
| EVENT cP | c2, target(s), removes SPECCED_KEY | `c2={3,2,3,3}` | FIDELIDADE for the event; the `c2[0]=3` cell is the residue's trigger |
| CONSTRAINT `iterationCount >= 10000` | exact in c1/err1 | prologues | FIDELIDADE (values); message off by 10× (ALFA-PBK-07) |
| CONSTRAINT `neverTypeOf(password, String)` | not translated; registered README:697 | — | LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA (ALFA-PBK-06, PASS) |
| REQUIRES `randomized[salt]` | read in c1/err3, correct constant/object | writers SecureRandomSpec | FIDELIDADE (ALFA-PBK-10, PASS) |
| *(no requires on password)* | **extra** `RANDOMIZED(password)` in c1/err2 | executed FP + ENSURES starvation | **INCORRETA** (ALFA-PBK-02, critical, unregistered) |
| ENSURES `speccedKey[this, keylength]` | unary SPECCED_KEY in c1 body | binary slot impossible (ExecutionContext unary) | **OMITIDA** second slot (ALFA-PBK-05, major; FEN-SET-GENERATEDKEY-2A-CASA); reader-side omission registered |
| NEGATES `speccedKey[this,_] after cP` | per-object remove | correct scope | FIDELIDADE (in ALFA-PBK-10) |
| *(end of trace)* | cP mandatory, no channel | — | OMITIDA minor (ALFA-PBK-09) |

## 6. Set-level findings (ALFA-SET-*)

| ID | Finding | Position |
|---|---|---|
| ALFA-SET-05 | Generator silently accepts a parametric spec whose event binds **no** spec parameter (KPR c1: name mismatch `kp`/`keyPair`) and a monitor variable shadowing the spec parameter name (`KeyPair keyPair = null`, .mop:21 vs :19) — exit 0, no warning (generation_manifest). Same silent-acceptance family as batch A BETA-SET-02 | FAIL major |
| ALFA-SET-06 | The `generatedCipher` subsystem (CipherSpec writes; CIS/COS read) implements a predicate that exists in **no api30 rule** — an upstream-CrySL-1.5.2 import into the derived set. gh101 registered the addition (design.md:294-296, tasks.md:146, divergence_record.csv:2-3,8) and its own text concedes anchor-dependence ("the anchor bears only on `generatedCipher`"), but the register misstates the api30 oracle ("Closes the rule's REQUIRES") and no researcher scope reduction is on file | FAIL major |
| ALFA-SET-07 | Parameterless specs silently generate a single static process-global monitor (CIS/COS). The gh101 empty-slice census keyed on `AbstractSynchronizedMonitor` (design.md:190) is **blind** to this shape — parameterless specs generate `AbstractAtomicMonitor` (artifact-verified) — and blind in the other direction too: KPR generated the Synchronized signature and no register row exists. Both lint gaps are one grep each | FAIL major |
| ALFA-SET-08 | Every live `@fail` in the batch uses the 2-arg `ErrorDescription` → `expecting=unknown` on all sequencing reports of CIS/COS/KPR/PBK (executed in all four); SKY has no channel at all. Set-wide pattern of the batch A GAMA-IVP-02 defect class | FAIL major |

## 7. D-piloto-2 standardized tests — applicability declaration (mandatory)

- **(a) folding × case-insensitive `getInstance`**: **N/A for all five specs** —
  none declares a `getInstance` event and neither the five rules nor the five
  specs carry any algorithm-string constraint (the only `alg` binding, KPR's
  none / SKY's none, is not constrained).
- **(b) `part()` over an absent component**: **N/A literally for all five** — no
  api30 rule in the batch uses `part()` (grep). The analogous absent-component
  situation — CIS/COS `CONSTRAINTS len > off` naming components bound only at
  the 3-arg read/write — does not even reach the absent-component question,
  because the constraint is not transcribed at any event (ALFA-CIS-04 /
  ALFA-COS-05): the defect is omission, not projection.

## 8. Summary of positions

45 claims in `alfa_claims.csv`: **11 PASS, 33 FAIL, 1 INCONCLUSIVE**.
FAIL severities: **13 critical** — ALFA-CIS-01/02, ALFA-COS-01/02/03,
ALFA-KPR-01/02/06, ALFA-SKY-02/03/04, ALFA-PBK-02/03 — 15 major, 5 minor.
Every critical claim is anchored either in the executed drive
(`alfa_drive_output.txt`, 3 identical reps) or in the exact product check
(`alfa_automata_output.txt`), or both.

Critical phenomena for the judge (10): FEN-CIS-MONITOR-GLOBAL,
FEN-COS-MONITOR-GLOBAL (family of batch A FEN-HMC-MONITOR-GLOBAL, now with
executed multi-instance cascades), FEN-SET-GENCIPHER-EXTRA (CIS+COS+set),
FEN-COS-FLUSH (alphabet superset: FN and FP executed), FEN-KPR-CO-OPCIONAL
(dominant real-world KeyPair usage spuriously accused), FEN-KPR-C1-SLICE-VAZIO
(unregistered recurrence of the gh101-repaired defect class, executed
contamination), FEN-SKY-GATE-SUPRESSAO (extra-oracle gate starving the
`preparedKeyMaterial` edge), FEN-SKY-SEM-CANAL (spec structurally unable to
report any violation), FEN-SKS-SURROGATE (writer side; joins batch A),
FEN-PBK-SENHA-EXTRA (every ordinary user-password construction accused),
FEN-PBK-RESIDUO (protocol §8's D-S10 residue class, executed).

Cross-cutting for the judge: (i) batch B refutes the batch A working assumption
that layer-2 carrier prefixes are benign — they are benign **only when no
mandatory event follows**; PBK's `cP` turns the residue into an executed FP
class; (ii) the two register-described defect classes gh101 repaired elsewhere
(empty-slice binding; all-fail events) have an unregistered live instance (KPR
c1) and an unregistered inverse blind spot (parameterless global monitors);
(iii) the predicate plane and the automaton plane fail independently: KPR's
predicate writes survive its automaton FPs, while SKY's automaton is correct and
its predicate plane is starved — per the semantic model, both planes must hold.
