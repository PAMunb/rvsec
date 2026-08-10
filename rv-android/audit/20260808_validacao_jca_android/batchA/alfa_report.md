# ALFA — Batch A report (CrySL conformance and formal logic)

Agent Alfa, round "batch A" of the adversarial audit of `jca_android` vs the api30
CrySL rules. Date: 2026-08-09. Specs: **DHGenParameterSpecSpec (DHG)**,
**HMACParameterSpecSpec (HMC)**, **PBEParameterSpecSpec (PBE)**,
**IvParameterSpec.mop / spec `IvParameterSpecSpec` (IVP)**, **SecretKeySpecSpec (SKS)**.

Inputs: frozen `.mop`/`.cryptsl` per `batchA/generation_manifest.md` (hashes verified
there); effective automata parsed from the generated `*RuntimeMonitor.java` of the
round's common input (D-piloto-3). Oracle: the RAW api30 rules (pre-registration §1).
ORDER precedence: reading A (D-piloto-1) — no comma occurs in these five ORDERs, so
the precedence question is moot for this batch. Sequential Thinking MCP was available
and used (3 steps); the concise scientific log is published per spec below.

Epistemic labels used throughout: **PROVADO** (algorithmic check or structural proof
on the artifact), **MEDIDO** (executed command with recorded output), **OBSERVADO_EM_ARTEFATO**
(cited file:line), **INFERIDO** (deduction without execution), **NAO_VERIFICADO**.

Companion files (all under `batchA/`): `alfa_claims.csv` (34 claims),
`alfa_automata_check.py` + `alfa_automata_output.txt`,
`alfa_paren_check.py` + `alfa_paren_check_output.txt`,
`alfa_JvmHarness.java` + `alfa_jvm_harness_output.txt`,
`alfa_api30_members_output.txt`.

## 0. Batch-level structure shared by all five specs

All five rules are **single-constructor rules**: `ORDER` is one event or a two-way
alternative `Cons := cA | cB`, every event is a constructor observed `after ...
returning`, and the monitor is parametric on the **returned object**. Two structural
consequences, used repeatedly below, both PROVADO:

1. **Every realizable per-instance trace has length exactly 1.** An object is
   constructed once; all events of a monitor bind the same returned object. Hence in
   the effective tables (`{1,2,2}` conforming, `{0,2,2}` violating): the transitions
   out of states 1 and 2 are vacuous, and `@fail` — reachable only from state ≥ 1 —
   is **dead code in all five monitors**. Positive corollary: these five specs cannot
   emit a spurious `InvalidSequenceOfMethodCalls` (claim ALFA-SET-04, PASS). Threat:
   this holds at monitor level; a weaver that double-fires an advice would make
   `fail` reachable (G6/G10, outside my scope).
2. **REQUIRES/CONSTRAINTS are enforced by `condition(...)` prologues that
   suppress the event when false** (`return false` before `handleEvent` — semantic
   model §5(c)). Fidelity therefore hinges on whether every suppressible misuse has a
   **violating-carrier event** that reports in its own body. This is where the batch
   splits: IVP has full carriers, SKS has carriers testing the wrong predicate set,
   PBE has a carrier for one of two constructors, DHG has none.

The generator-mechanism phenomenon from the pilot (stale category flags → handler
re-execution on a suppressed event; BETA-CIP-06/GAMA-CIP-08) is **confirmed in these
artifacts** (wrapper discards the event's boolean and then tests monitor flags,
`gen_IvParameterSpec/...RuntimeMonitor.java:410-417`; each 2-carrier advice calls the
conforming event then the violating event, aspect `:41-43`). In all five specs the
re-executed handler is `@match` with idempotent bodies (`setProperty` /
`setObjectAsInAcceptingState` over identity sets), so the impact here is zero —
ALFA-SET-01, FAIL major as a set-wide latent pattern, benign in batch A.

## 1. DHGenParameterSpecSpec ↔ DHGenParameterSpec.cryptsl

### Scientific log
- **Question**: does the translation preserve a rule that has *no* CONSTRAINTS, no
  REQUIRES, ORDER `c1`, ENSURES `preparedDH[this]`?
- **Hypothesis to falsify**: "trivial spec, trivially faithful".
- **Discriminating test**: diff the guard set of the `.mop` against the clause set of
  the rule; walk the suppressed branch end-to-end through the predicate graph.
- **Evidence**: `.mop:24` carries `condition(exponentSize < primeSize)` — a
  constraint that exists in **no** section of the api30 rule and in no
  MetaCrySL-generated variant (`grep exponentSize` over `MetaCrySL/generated/**`:
  only OBJECTS/EVENTS lines). Harness T4: `new DHGenParameterSpec(1024,1024)` and
  `(512,1024)` return normally (MEDIDO).
- **Result**: hypothesis falsified — the spec is *stricter* than its oracle and the
  excess is enforced by **silent suppression** (no carrier, no report, no monitor,
  no `PREPARED_DH`). Downstream, `KeyPairGeneratorSpec.mop:96-99,107-110` reads
  `PREPARED_DH` under the rule's implication `alg in {"DH"} => preparedDH[params]`
  (KeyPairGenerator.cryptsl REQUIRES) and reports `UnsatisfiedConstraint` — an
  **end-to-end false positive on a trace the oracle accepts** (PROVADO structurally).
- **Uncertainty**: the FP chain is not device-executed; DH `KeyPairGenerator`
  availability on API 30 is INFERIDO.
- **Decision**: file ALFA-DHG-02/03/05 (critical/critical/major) + register-accuracy
  claim ALFA-DHG-06.

### Normative matrix
| Clause (api30) | MOP translation | Effective artifact | Status |
|---|---|---|---|
| OBJECTS `int primeSize`, `int exponentSize` | bound by `args(primeSize, exponentSize)` (.mop:23) | advice binds both (aspect :39-41) | FIDELIDADE_DEMONSTRADA |
| EVENT `c1: DHGenParameterSpec(primeSize, exponentSize)` | event c1, `after ... returning(s)`, ctor `(int,int)` — matches the only public ctor in android-30 jar (alfa_api30_members_output.txt) | `c1={1,2,2}` | FIDELIDADE (capture side INFERIDO — Beta's harness owns the matcher) |
| ORDER `c1` | `ere : c1` | dual inclusion PROVADO (alfa_automata_output.txt) | FIDELIDADE_DEMONSTRADA |
| *(no CONSTRAINTS section)* | **extra** `condition(exponentSize < primeSize)` suppressing c1 | `return false` before `handleEvent` (monitor :110-118) | **INCORRETA** (ALFA-DHG-02, critical, unregistered) |
| ENSURES `preparedDH[this]` | `setProperty(PREPARED_DH, spec)` in `@match` (.mop:36) | handler :135-137 | **INCORRETA** on the suppressed path (ALFA-DHG-03, critical); faithful on the satisfying path |
| *(no REQUIRES / NEGATES)* | none | — | FIDELIDADE (trivially) |

### α and binding profile
| Java call | CrySL event | MOP event | Discriminant | Bindings |
|---|---|---|---|---|
| `new DHGenParameterSpec(int,int)` returns normally, `exponentSize < primeSize` | c1 | c1 | condition true | primeSize/exponentSize by position; `s` via `returning`; property object = `s` |
| same call, `exponentSize >= primeSize` | c1 (oracle: valid, ENSURES fires) | **no event** (suppressed) | condition false | — |

α is **not total** on oracle-valid calls — that is the defect, not a fusion issue.

### Verdict inputs
Language: PASS. Bindings/constraints: FAIL (critical). Predicates: FAIL (critical).
Lifecycle: PASS (ALFA-DHG-04). Diagnosis: FAIL (major — displaced, misleading
accusation at the KeyPairGeneratorSpec site; the message asserts no monitored
DHGenParameterSpec sequence happened, which in the FP trace is false). Register
accuracy: FAIL minor (conformance_record's reason describes a constraint the derived
rule does not contain). Note: DHG is byte-identical to the frozen `jca` copy (known
anomaly 2), so every finding here is inherited by `jca` as well; the gh101 all-fail
census could not have caught it (c1 *is* in the ere — the defect class is
suppression-without-carrier, which no gh101 register covers).

## 2. HMACParameterSpecSpec ↔ HMACParameterSpec.cryptsl

### Scientific log
- **Question**: constraint-free single-event rule; anything to falsify?
- **Hypothesis to falsify**: "the spec is observable on the platform it targets".
- **Discriminating test**: membership of `javax.xml.crypto.dsig.spec.HMACParameterSpec`
  in the frozen android-30 jar, decided by the jar's entry table (`unzip -l`), not by
  `javap` — because `javap -classpath` **silently falls back to the host JDK's
  modules** for classes missing from the classpath; this fallback was itself caught
  during measurement and is documented in `alfa_api30_members_output.txt`.
- **Evidence**: 0 entries under `javax/xml/crypto` in android-30.jar
  (sha256 `96ccfdc8...`, = frozen manifest). MEDIDO.
- **Result**: hypothesis falsified. The api30 oracle — an availability profile —
  contains a rule for a class API 30 does not publish. The translation is faithful;
  the spec is vacuous for platform-API usage: the pointcut cannot match, and
  `PREPARED_HMAC` is never written on-platform (its reader `MacSpec.mop:99` then
  treats *any* non-null `params` as unprepared — faithful to the Mac rule, but the
  entire producer side is unreachable).
- **Uncertainty**: an app bundling its own copy of the class could still be woven
  (INFERIDO; rare).
- **Decision**: ALFA-HMC-02 FAIL major (LIMITACAO_INEVITAVEL_DOCUMENTADA — documented
  here) + set claim ALFA-SET-03 (oracle-generator defect).

### Normative matrix
| Clause (api30) | MOP translation | Effective artifact | Status |
|---|---|---|---|
| OBJECTS `int outputLength` | not bound (`after()` with no args, .mop:21) | — | FIDELIDADE (anonymous projection; no dependent clause in the api30 rule) |
| EVENT `c1: HMACParameterSpec(outputLength)` | event `c`, ctor `(int)` | `c={1,2,2}` | FIDELIDADE at spec level; **vacuous on platform** (ALFA-HMC-02) |
| ORDER `c1` | `ere : c` | dual inclusion PROVADO | FIDELIDADE_DEMONSTRADA |
| ENSURES `preparedHMAC[this]` | `setProperty(PREPARED_HMAC, spec)` in `@match` (.mop:35) | handler present; reader `MacSpec.mop:99`; edge registered `present` (predicate_edges.csv:21) | FIDELIDADE (edge); unreachable on-platform |

α: identity (one call ↔ one event, no condition — the only batch-A event with **no**
suppression path). Binding profile: `s` via `returning`; property object = `s`.
Lifecycle: PASS. No diagnosis surface needed (nothing the rule can accuse).

## 3. PBEParameterSpecSpec ↔ PBEParameterSpec.cryptsl

### Scientific log
- **Question**: rule with real CONSTRAINT (`iterationCount >= 10000`) and REQUIRES
  (`randomized[salt]`) over `Cons := c1 | c2`; are both enforced on both constructors,
  and does every violating construction report?
- **Hypothesis to falsify**: "the layer-2 repair (`c3*` prefix) closed the violating
  branch".
- **Discriminating test**: enumerate carriers per constructor arity in the generated
  aspect; realizability harness for the 3-arg misuse.
- **Evidence**: the 2-arg advice calls `c1Event` then `c3Event`; the 3-arg advice
  calls **only** `c2Event` (`PBEParameterSpecSpecMonitorAspect.aj:49-52`). `c3` is
  declared over the 2-arg ctor only (.mop:42-51). Harness T3b:
  `new PBEParameterSpec(salt, 100, ivSpec)` returns normally (MEDIDO).
- **Result**: hypothesis falsified for the 3-arg constructor. A realizable oracle
  misuse (`iterationCount < 10000`, or unrandomized salt, via the 3-arg ctor — the
  ctor is in android-30.jar) produces **no event, no report, no monitor**: terminal
  FN, silent, and **unregistered** (searched: divergence_record.csv — the PBE row
  covers only the c3 repair; predicate_omissions.csv; conformance_record.csv;
  frozen_set_debt.md; proposal.md:39, design.md:168, tasks.md group 3b — all list
  `PBEParameterSpecSpec.c3` only). The 2-arg side is faithful: c1/c3 partition the
  join point exactly (guards are exact complements) and c3 reports.
- **Uncertainty**: corpus frequency of the 3-arg ctor not measured; the FN is
  structural regardless.
- **Decision**: ALFA-PBE-03 FAIL critical; plus two minor diagnostic defects.

### Normative matrix
| Clause (api30) | MOP translation | Effective artifact | Status |
|---|---|---|---|
| OBJECTS salt / iterationCount / paramSpec | bound by position in c1/c2/c3; paramSpec bound in c2, unused (rule also has no clause on it) | aspect binds all | FIDELIDADE_DEMONSTRADA |
| EVENTS c1 (2-arg), c2 (3-arg), `Cons := c1|c2` | c1, c2 conforming; c3 = violating carrier of c1 only | tables c1/c2=`{1,2,2}`, c3=`{0,2,2}` | c1/c2 FIDELIDADE; **carrier for c2 OMITTED** (ALFA-PBE-03, INCORRETA, critical) |
| ORDER `Cons` | `ere : c3* (c1 | c2)` | dual inclusion PROVADO modulo α | DIVERGENCIA_EQUIVALENTE_COMPROVADA (registered, divergence_record hunk 49b892006688) |
| CONSTRAINT `iterationCount >= 10000` | transcribed exactly in c1 and c2 (.mop:26,36) | prologues in monitor | FIDELIDADE (values) — mechanics INCORRETA on the 3-arg violating path (suppression) |
| REQUIRES `randomized[salt]` | `validate(RANDOMIZED, salt)` in c1/c2; ¬ in c3 | correct constant/object; writers in SecureRandomSpec | FIDELIDADE on 2-arg; suppressed on 3-arg (same phenomenon) |
| ENSURES `preparedPBE[this]` | `PREPARED_PBE` in `@match` | write present; **no reader in the set and no consumer in the api30 rules** (grep) — registered (predicate_omissions.csv, PREPARED_PBE row) | FIDELIDADE / registered write-no-read mirroring the oracle |

### α
| Java call | condition | CrySL | MOP |
|---|---|---|---|
| 2-arg ctor, constraint∧requires hold | c1 (valid) | c1 → match | |
| 2-arg ctor, violated | c1 (ConstraintError/RequiredPredicateError) | c3 → own-body report, state 0 | |
| 3-arg ctor, hold | c2 (valid) | c2 → match | |
| 3-arg ctor, violated | c2 (error) | **nothing** — α undefined (defect) | |

### Diagnostics (two measured defects)
1. c3's message says "expecting at least **1000** iterations" while the guard checks
   **10000** (.mop:46 vs :50) — ALFA-PBE-04, minor.
2. c3 uses `ErrorType.UnsafeAlgorithm` where IVP/SKS use `UnsatisfiedConstraint` for
   the identical shape — category inconsistency breaks per-category stratification of
   `errors.csv` — ALFA-PBE-05, minor. (Shared vocabulary note: `ErrorType` has no
   RequiredPredicate category at all; all three specs fold REQUIRES violations into
   constraint-flavored categories. Reported as a note, not a claim, since the enum is
   a set-level vocabulary choice.)
3. Cosmetic: the .mop javadoc header (line 11) says "GCMParameterSpec".

Lifecycle: PASS (ALFA-PBE-07).

## 4. IvParameterSpec.mop (`IvParameterSpecSpec`) ↔ IvParameterSpec.cryptsl

### Scientific log
- **Question**: REQUIRES `randomized[iv]`, no CONSTRAINTS, `Cons := cons1|cons2`; the
  MOP adds envelope conjuncts to c2 (`offset>=0 && len>=0 && iv.length>=offset+len`)
  that are not in the rule, and c4's guard is only `!randomized` — is there a silent
  gap (`randomized ∧ ¬envelope`) or an over-restriction?
- **Hypothesis to falsify**: "the extra conjuncts change the accepted set".
- **Discriminating test**: JVM harness of the constructor's throwing envelope
  (events are `after returning`; a throwing ctor fires nothing).
- **Evidence**: T1a-T1d — `IvParameterSpec(byte[],int,int)` throws exactly when
  `offset<0` (AIOOBE), `len<0` (AIOOBE), or `iv.length<offset+len` (IAE); valid
  arguments return normally (MEDIDO, host JDK).
- **Result**: hypothesis falsified in the benign direction: at the after-returning
  join point the extra conjuncts are **vacuously true**, so c2 fires iff
  `randomized(iv)`, c4 iff `¬randomized(iv)` — total, disjoint, no silent gap, no
  over-restriction. DIVERGENCIA_EQUIVALENTE_COMPROVADA (ALFA-IVP-02). The int
  overflow corner (`offset+len` wrapping) requires arrays beyond JVM limits and a
  ctor that would throw first — unrealizable.
- **Uncertainty**: proven on host JDK (Temurin 25); ART/libcore implements the same
  documented contract but was not executed here (android.jar is a stub jar — this is
  precisely why the harness is the only executable route without a device). Declared
  as threat, PASS maintained at confidence 0.8.
- **Decision**: all four IVP claims PASS. This is the one batch-A spec with a
  complete, correctly-predicated carrier structure.

### Normative matrix
| Clause (api30) | MOP translation | Effective artifact | Status |
|---|---|---|---|
| OBJECTS iv/offset/len | bound by position | aspect binds | FIDELIDADE_DEMONSTRADA |
| EVENTS cons1/cons2, `Cons` | c1/c2 conforming + c3/c4 violating carriers | c1/c2=`{1,2,2}`, c3/c4=`{0,2,2}` | FIDELIDADE (carriers registered, divergence_record hunk f4fe01f5b82c) |
| ORDER `Cons` | `ere : (c3|c4)* (c1|c2)` | dual inclusion PROVADO modulo α | DIVERGENCIA_EQUIVALENTE_COMPROVADA |
| *(no CONSTRAINTS)* | envelope conjuncts on c2 | vacuous at join point (T1) | DIVERGENCIA_EQUIVALENTE_COMPROVADA (ALFA-IVP-02) |
| REQUIRES `randomized[iv]` | `validate(RANDOMIZED, iv)` in all 4 guards, correct object | writers SecureRandomSpec.mop:106-133 | FIDELIDADE_DEMONSTRADA |
| ENSURES `preparedIV[this]` | `PREPARED_IV` in `@match`; reader CipherSpec.mop:84 | edges registered present | FIDELIDADE_DEMONSTRADA |

Violating-path diagnosis: c3/c4 report `UnsatisfiedConstraint` at the construction
site, and the missing `PREPARED_IV` reproduces at the Cipher reader — a **double
accusation that mirrors CrySL** (the IvParameterSpec rule's RequiredPredicateError
plus the Cipher rule's unsatisfied `preparedIV`), so it is faithful, not noise.
Lifecycle: PASS (ALFA-IVP-04).

## 5. SecretKeySpecSpec ↔ SecretKeySpec.cryptsl

### Scientific log
- **Question**: rule with CONSTRAINT `length(keyMaterial) >= off + len`, REQUIRES
  `preparedKeyMaterial[keyMaterial]`, ENSURES `speccedKey[this,_]` and
  `generatedKey[this,alg]`. The .mop adds an algorithm whitelist, reads `RANDOMIZED`,
  and its c1 header carries a visually unbalanced parenthesis. Four independent
  falsification routes.
- **Tests/evidence/results**:
  1. **Whitelist** (.mop:19-20, guards c1-c4): the api30 rule has **no** constraint
     on `alg` (sole CONSTRAINT is the length clause). Registered in
     conformance_record.csv as "declared hand translation" with "the derived rule
     imposes no membership constraint at all". Realizable FP:
     `new SecretKeySpec(randomizedBytes, "DESede")` → c3 reports
     `UnsatisfiedConstraint`; the raw oracle accepts and ensures both predicates.
     Registered ≠ approved (semantic model §7) → ALFA-SKS-02 FAIL critical.
     D-piloto-2 test (a), adapted (no `getInstance` event exists; the whitelist is
     the only algorithm-string constraint in the batch): T5a/T5b MEDIDO — JCA
     accepts lower-case key algorithms downstream (`Mac.init` with alg
     "hmacsha256"; AES cipher with alg "aes"), so the `toUpperCase` folding is
     behavior-consistent with the platform and does not alter the verdict.
  2. **Predicate surrogate**: the REQUIRES reads `Property.RANDOMIZED`
     (.mop:29) — registered as "present-surrogate / carried as Property.RANDOMIZED"
     (predicate_edges.csv:66; README.md:162 "borrowed constant"); there is no
     `PREPARED_KEY_MATERIAL` constant (Property.java). The surrogate is **not
     equivalent**: the oracle's producers are `SecretKey.getEncoded`/`Key.getEncoded`
     only (SecretKey.cryptsl:25, Key.cryptsl:23), while `RANDOMIZED` is produced by
     SecureRandomSpec (nextBytes et al.) and RandomStringPassword. Realizable FN
     against the raw oracle: SecureRandom-derived key material passes c1 and earns
     `GENERATED_KEY` where the oracle demands `preparedKeyMaterial`. (Declared oracle
     bias: what the oracle flags here is good practice; recorded, not corrected.)
     → ALFA-SKS-03 FAIL critical.
  3. **4-arg path**: c2's guard is `whitelist ∧ length-ok`, c4's is its exact
     complement — **neither reads RANDOMIZED at all** (.mop:37,54; .rvm:20-27,36-43),
     while the 2-arg path does. Realizable FN: `new SecretKeySpec(nonRandomBytes, 0,
     16, "AES")` → c2 → match → `GENERATED_KEY` + `SPECCED_KEY` written; downstream
     Cipher/Mac readers are poisoned. Unregistered (searched: predicate_edges.csv:66
     marks the REQUIRES "present" without noting it covers only c1/c3 — the
     inventory rows 102-103 list reads in c1/c3 only; divergence_record hunk
     f0ffa75b48bc describes c4 without noting the missing predicate;
     predicate_omissions.csv; tasks/design/proposal). → ALFA-SKS-04 FAIL critical.
  4. **generatedKey second slot**: `@match` writes `GENERATED_KEY` unary (.mop:81);
     the rule ensures `generatedKey[this, alg]`; `ExecutionContext` has no second
     slot (ExecutionContext.java:102-120) and readers (CipherSpec.mop:156/177/198,
     MacSpec.mop:75/94) validate without the algorithm → wrong-algorithm key
     accepted downstream. Same phenomenon the pilot proved on the reader side
     (ALFA-CIP-07); write side here; still unregistered (predicate_edges.csv:68 says
     "present", argument `this`, no slot note — the exact register gap the pilot
     judge named in §6 item 5). → ALFA-SKS-05 FAIL critical (OMITIDA),
     `FEN-SET-generatedkey-2a-casa`.
  5. **Length constraint**: transcribed exactly on c2; on c1 the components
     `off`/`len` do not exist → unevaluable, not enforced — consistent with the
     absent-component reading (test (b) is literally N/A: no `part()` in any batch-A
     rule); and the constructor itself throws whenever the constraint would fail
     (T2a-T2c), making c4's length disjunct dead at the join point. → ALFA-SKS-07
     PASS. (Diagnostic note: c4's message names the length case that can never be
     its trigger.)
  6. **Syntax**: c1's pointcut has balance −1 (one stray `)` at .mop:30) — measured
     by `alfa_paren_check.py`; the generator absorbed it silently (exit 0, artifacts
     balanced, semantics intact in `.rvm:13`). Toolchain fail-open → ALFA-SET-02.
  7. **speccedKey[this,_]**: written in `@match`, anonymous second slot → unary
     write is a faithful projection; no reader because SecretKeyFactory is
     unmodelled; registered twice (predicate_omissions.csv SPECCED_KEY;
     divergence_record hunk 644c9b978750) → ALFA-SKS-06 PASS
     (LIMITACAO_INEVITAVEL_DOCUMENTADA — still blocks "total adherence").
- **Uncertainty**: FN/FP traces are structural + harness-realizable, not
  device-executed; ART envelope threat as in IVP.
- **Decision**: language PASS; four critical FAILs; lifecycle PASS — note that
  `SecretKeySpec` is the batch's maximum-risk type for identity (value-based
  `equals`/`hashCode`, confirmed by javap), and the identity-keyed store
  (`ExecutionContext.java:18-27,52-54`) matches the JavaMOP index exactly —
  ALFA-SKS-08 PASS.

### Normative matrix
| Clause (api30) | MOP translation | Effective artifact | Status |
|---|---|---|---|
| OBJECTS alg/keyMaterial/len/off | bound by position in c1-c4 | aspect binds | FIDELIDADE_DEMONSTRADA |
| EVENTS c1 (2-arg), c2 (4-arg), `Cons` | conforming c1/c2 + carriers c3/c4 | tables `{1,2,2}`/`{0,2,2}` | carriers: DIVERGENCIA_EQUIVALENTE (registered); **c2/c4 predicate content INCORRETA** (ALFA-SKS-04) |
| ORDER `Cons` | `ere : (c3|c4)* (c1|c2)` | dual inclusion PROVADO modulo α | DIVERGENCIA_EQUIVALENTE_COMPROVADA |
| CONSTRAINT `length(keyMaterial) >= off + len` | exact on c2; unevaluable on c1; API-enforced | T2 harness | FIDELIDADE_DEMONSTRADA (ALFA-SKS-07) |
| *(no alg constraint)* | **extra** whitelist + toUpperCase folding | c3 reports on non-listed alg | **INCORRETA** (ALFA-SKS-02, critical, registered-not-approved) |
| REQUIRES `preparedKeyMaterial[keyMaterial]` | `RANDOMIZED` surrogate, c1/c3 only | 4-arg path reads nothing | **INCORRETA ×2** (ALFA-SKS-03 surrogate; ALFA-SKS-04 4-arg gap; both critical) |
| ENSURES `speccedKey[this,_]` | `SPECCED_KEY` unary in `@match` | registered write-no-read | LIMITACAO_INEVITAVEL_DOCUMENTADA (ALFA-SKS-06) |
| ENSURES `generatedKey[this,alg]` | `GENERATED_KEY` unary in `@match` | second slot dropped, readers pair-blind | **OMITIDA** (ALFA-SKS-05, critical, unregistered) |

## 6. Set-level findings (ALFA-SET-*)

| ID | Finding | Position |
|---|---|---|
| ALFA-SET-01 | Stale-category-flags handler re-execution on suppressed events, confirmed in batch A artifacts; benign here (idempotent `@match` bodies), latent set-wide (`FEN-SET-flags-obsoletas`, = pilot BETA-CIP-06/GAMA-CIP-08) | FAIL major |
| ALFA-SET-02 | JavaMOP parser fail-open: unbalanced `)` in SecretKeySpecSpec.mop absorbed silently, exit 0, artifacts semantically intact (`FEN-SET-failopen-parser`, kin of pilot GAMA-GCM-01) | FAIL major |
| ALFA-SET-03 | The api30 availability profile emits a rule (HMACParameterSpec) for a class absent from the API-30 platform jar — the oracle violates its own premise; registered as oracle bias, does not impugn the translation | FAIL major |
| ALFA-SET-04 | No spurious `InvalidSequenceOfMethodCalls` is emittable from any batch-A spec (`@fail` unreachable per instance, PROVADO from the tables); dead-handler hygiene noted; contingent on no weaver double-fire (G6/G10 pending) | PASS |

## 7. D-piloto-2 standardized tests — applicability declaration (mandatory)

- **(a) folding × case-insensitive `getInstance`**: none of the five specs has a
  `getInstance` event. The only algorithm-string constraint in the batch is SKS's
  (extra-oracle) whitelist — the test was **applied in adapted form** there
  (harness T5, MEDIDO): JCA consumes SecretKeySpec algorithms case-insensitively, so
  the `toUpperCase` folding is behavior-consistent; verdict of ALFA-SKS-02 is
  unaffected (the whitelist itself is the defect). **N/A for DHG, HMC, PBE, IVP**:
  no algorithm-string constraint exists in either the rule or the spec.
- **(b) `part()` over an absent component**: **N/A literally for all five** — no
  api30 rule in the batch uses `part()`. The analogous situation (a constraint
  naming components absent from one event: SKS `length(keyMaterial) >= off+len` vs
  the 2-arg ctor) was adjudicated under the same principle in ALFA-SKS-07
  (unevaluable ⇒ not enforced; additionally API-enforced by construction).

## 8. Summary of positions

34 claims: **19 PASS, 15 FAIL, 0 INCONCLUSIVE**. FAIL severities: 7 critical
(ALFA-DHG-02, ALFA-DHG-03, ALFA-PBE-03, ALFA-SKS-02, ALFA-SKS-03, ALFA-SKS-04,
ALFA-SKS-05), 5 major, 3 minor. Per-spec outlook from Alfa's dimensions alone
(verdicts belong to the judge): IVP clean; HMC faithful-but-vacuous-on-platform
(oracle anomaly); DHG, PBE, SKS each carry at least one demonstrable, realizable
FP/FN — under pre_registro §4 these block APROVADA for those three specs.

Cross-cutting for the judge: (i) the batch's dominant defect class is
**suppression-without-carrier / carrier-with-wrong-predicate** — a class invisible
to gh101's all-fail census and only partially visible to its predicate registers;
(ii) three of the seven criticals are *registered* divergences
(SKS whitelist, SKS surrogate) — registration exists but equivalence was never
demonstrated, and no researcher scope reduction is on file; (iii) `alfa_claims.csv`
column `fenomeno_id` links the two pilot-shared phenomena
(`FEN-SET-generatedkey-2a-casa`, `FEN-SET-flags-obsoletas`).
