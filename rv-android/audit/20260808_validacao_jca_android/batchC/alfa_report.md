# Agent ALFA — batch C report (KGN, KMF, TMF, SSL, KST)

Date: 2026-08-09. Round: batch C of the `jca_android` adversarial audit.
Scope: CrySL conformance and formal logic (protocol §14, Agente Alfa) for
`KeyGeneratorSpec` (KGN), `KeyManagerFactorySpec` (KMF), `TrustManagerFactorySpec`
(TMF), `SSLContextSpec` (SSL), `KeyStoreSpec` (KST) against the raw
`MetaCrySL/generated/api30/` rules. Claims: `alfa_claims.csv` (sha256
`c6ab0c2c…`). All rules fixed for the round were applied: D-piloto-1 (reading A),
D-piloto-3 (verdicts over the effective automaton parsed from the artifacts),
D-piloto-4 (dimension at creation, SET separate, six states), D-piloto-2 tests
(a) executed / (b) declared N/A, batch A/B standard checks.

Sequential Thinking MCP: **available and used** (4-step pre-verdict
decomposition; no chain-of-thought published — this report is the concise
scientific log).

## 0. Frozen inputs and evidence of record

- Specs and rules: byte-identical to `fase0/manifest_hashes.md` and
  `batchC/generation_manifest.md` (all 10 sha256 re-verified this session).
- Generated artifacts: all 20 files re-hashed = generation manifest.
- Production jars for the harness (batch B judge classpath):
  `rv-monitor-rt-0.9.3-SNAPSHOT.jar` `0fa65fbc…`, `rvsec-core-0.9.3-SNAPSHOT.jar`
  `7b4d72aa…`, `rvsec-logger-csv-0.9.3-SNAPSHOT.jar` `6787f411…`. JDK: Temurin
  25.0.3. Frozen android-30 jar `96ccfdc8…` (javap matrix
  `alfa_javap_android30.txt`).
- Executed evidence (all under `batchC/`, alfa_-prefixed, hashes in §8):
  - `alfa_language_check.py` → `alfa_language_results.txt` — effective automata
    machine-parsed from the five `RuntimeMonitor.java`; reference automata
    (reading A); α lifted to a call-class alphabet taken from the generated
    aspects; both inclusions by exhaustive product BFS with smallest separating
    traces and state walks. Deterministic (1 run, inputs hashed).
  - `alfa_HarnessC.java` → `alfa_harnessC_rep{1,2,3}.txt` — JVM drive of the
    real compiled monitors, event sequences exactly as the generated advices
    emit them (merged advices reproduced). 3 reps, sha256-identical
    (`cd4bb0f2…`).
  - `alfa_FoldingC.java` → `alfa_foldingC_rep{1,2,3}.txt` — D-piloto-2 test (a),
    3 reps sha256-identical (`abe5b3a4…`).
  - `alfa_kgn_compile_probe.txt` — measured standalone-compile failure of the
    round KGN monitor (§1.6).
- Harness deviation, declared: `KeyGeneratorSpecRuntimeMonitor.java` does not
  compile as shipped (§1.6). The behavioral harness used a copy with exactly one
  added line (`import java.security.Key;`), diff and hash recorded in the probe
  file. No file of the spec tree, rule tree, or round `gen_*` directories was
  modified.

**Effective automata (parsed, OBSERVADO_EM_ARTEFATO)** — states/init/fail/match
and per-event rows are printed verbatim at the top of
`alfa_language_results.txt`. Summary: KGN 6 states (fail=5, match=1); KMF/TMF 4
states (fail=3, match1=2) — the `.mop` `unsafeAlg` state is merged into `start`
by rv-monitor (identical rows); SSL 4 states (fail=3, match1=1); KST 6 states
(fail=5, match=1), `AbstractSynchronizedMonitor` but properly parameterized.
Conditions compile to per-monitor guards inside the event methods
(`return false` = suppression without transition) — the D-piloto-3 basis for
every language verdict below.

**Round-standard checks (batch B §6):** parameterless-spec sweep — none of the
five is parameterless; every event of every spec binds the spec parameter
(returning or target). `AbstractSynchronizedMonitor` appears only in KST, with a
real parameter and per-object indexing tree. First-call-disjunct sweep: **no
`||` remains in any call() pointcut of the five** (the jca twins had them in
KGN/KMF/TMF `init`; gh101's 1:1 event split removed them — on the dexlib2
production path this also removes the batch B first-disjunct hazard for these
specs). Interface-target sweep: all five target concrete classes. Mandatory
successors after carrier states: listed and — as batch B §6 item 5 predicted —
they are the top critical phenomenon of the batch (§6, FEN-C-CARRIER-SEQFAIL).

---

## 1. KeyGeneratorSpec (KGN) vs KeyGenerator.cryptsl

### 1.1 Normative matrix (condensed; one row per rule clause)

| Clause (KeyGenerator.cryptsl) | MOP translation | Status | Evidence |
|---|---|---|---|
| EVENTS g1/g2 (`getInstance(alg)`, `(alg,_)`) | g1/g2 safe + g3 unsafe (1-arg only); g2 covers both 2-arg overloads via `Object+` | split, partially INCORRETA | ALFA-KGN-03: 2-arg unsafe has no counterpart → invisible |
| EVENTS i1–i5 (5 init overloads) | i1–i5 transcribed 1:1, all bound | FIDELIDADE_DEMONSTRADA | ALFA-KGN-01; javap: exactly 5 overloads on android-30 |
| EVENTS gk (`key = generateKey()`) | gk1 after-returning SecretKey | FIDELIDADE_DEMONSTRADA | artifact + harness |
| ORDER `Gets, Inits?, gk` | `ere:(g3* g1+ \| g3* g2+)(((i1..i5) gk1)\|gk1)` | INCORRETA on the unsafe refinement | §1.2 |
| CONSTRAINT `alg in {11}` | 17-entry `safeAlgorithms` | INCORRETA (6 extra-oracle aliases) | ALFA-KGN-04 |
| CONSTRAINT `alg in {AES} => keySize in {128,192,256}` | absent | **OMITIDA, unregistered** | ALFA-KGN-05, FN measured |
| REQUIRES `randomized[ranGen]` | body read at i2/i4/i5 | FIDELIDADE_DEMONSTRADA | ALFA-KGN-06, measured |
| ENSURES `generatedKey[key, alg]` | `setProperty(GENERATED_KEY, key)` — alg slot dropped | INCORRETA | ALFA-KGN-07 / FEN-SET-GENERATEDKEY-2A-CASA (writer side confirmed) |

### 1.2 α and language verdicts (PROVADO over the product; MEDIDO in harness)

α is a call-class relation (one Java call ↦ 0..2 MOP events), materialized from
`KeyGeneratorSpecMonitorAspect.aj:66-72`: **g1 and g3 share one advice, g1Event
before g3Event**. Call classes and emissions are in `alfa_language_check.py`
(`CALLS('KGN')`), including the guard interplay: for a safe 1-arg getInstance,
g1's body sets `currentAlgorithmInstance` before g3's guard reads it, so g3 is
suppressed — no double-fire (harness KGN-T1: 0 errors). The g3 guard written
over the monitor field instead of the argument is therefore
DIVERGÊNCIA_EQUIVALENTE_COMPROVADA **by advice order only** (ALFA-KGN-08 flags
the fragility).

- `L(CrySL) ⊆ α(L(MOP))`: **FAIL**. Smallest separating trace `G1u I1`
  (getInstance(unsafe); init): rule-conformant ORDER, monitor fails at i1 and
  again at the following gk1 after `__RESET`. Walk in
  `alfa_language_results.txt`; measured in KGN-T2 (`getInstance("DES")` →
  2× InvalidSequenceOfMethodCalls + UnsafeAlgorithm). Also `G2u I1` (2-arg
  unsafe suppressed) — measured in KGN-T3, including the empty
  `but found .` label. FEN-C-CARRIER-SEQFAIL / FEN-C-GETS-INVISIVEL.
- `α(L(MOP)) ⊆ L(CrySL)`: **PASS** on the realizable envelope (no silent
  deviation). Formal event-level only: `g1 g1 gk1`, `g3 g2 gk1` accepted by the
  effective automaton but outside L(CrySL) — every such word needs one object
  returned by two getInstance calls; unrealizable by reference identity
  (ALFA-KGN-11).
- Acceptance sets agree (ere ends at gk1 = match; rule accepts after gk).

### 1.3 Constraints, predicates, graph

`randomized` read: faithful (rule binds ranGen at i2/i4/i5; guarded null skip is
a minor residue). `GENERATED_KEY` writer: single slot — the algorithm slot the
rule's ENSURES carries (and `Cipher.cryptsl`'s
`generatedKey[key, part(0,"/",transformation)]` needs) does not exist anywhere
in the store API (`ExecutionContext.java:104-111`). @fail removes are correctly
two-argument and self-scoped.

### 1.4 Lifecycle / parametric (dimension 5, mandatory)

Monitor per KeyGenerator (weak-ref map, identity); all 9 events bind `k`;
interleaved safe/unsafe instances isolated (harness KGN-T6, measured);
`terminateInternal` handles GC of the only parameter. PASS (ALFA-KGN-10).

### 1.5 Folding / part()

Folding (test a, executed): guard is exact-`contains`; JCA resolves
case-insensitively; case variants ("aes", "hmacsha256") are flagged by both the
spec and the raw literal constraint — categories consistent (ALFA-KGN-13). The
6 alias spellings are the divergence: spec-safe, raw-violating; unresolvable on
host JDK, resolvable on Android BC — FN threat declared (ALFA-KGN-04).
part() (test b): **N/A — declared**; no `part()` in this rule's constraints.

### 1.6 Generability finding (measured)

The round artifact `KeyGeneratorSpecRuntimeMonitor.java` (hash = manifest) does
**not compile standalone**: `KeyGeneratorSpec.mop:28` declares `Key generatedKey;`
with no `java.security.Key` import; javamop and rv-monitor exited 0 over it —
one more fail-open shape for the round's caveat list. The other four monitors
compile unmodified. Production merged-agent builds may mask this via another
spec's import — NAO_VERIFICADO, flagged (ALFA-KGN-09, major).

### 1.7 Provenance

Inherited from `jca` (twin diffed): g3-condition shape, ere carrier shape
(carrier-successor FP), missing 2-arg unsafe counterpart, missing keySize
constraint, missing Key import, HMAC alias spellings. gh101-introduced: the
i1–i5 split (correct), the randomized reads (correct), the widened 11-literal
base list (gh99 derivation; registered).

---

## 2. KeyManagerFactorySpec (KMF) vs KeyManagerFactory.cryptsl

### 2.1 Normative matrix

| Clause | MOP | Status | Evidence |
|---|---|---|---|
| EVENTS g1/g2 | g1/g3 (1-arg safe/unsafe), g2 `(String,..)&&args(alg,*)` covers both 2-arg overloads | partially INCORRETA (no 2-arg unsafe) | ALFA-KMF-03 |
| EVENTS i1/i2 | 1:1 split, both bound | FIDELIDADE_DEMONSTRADA | ALFA-KMF-01 |
| EVENTS gkm | gkm1 after-returning KeyManager[] | FIDELIDADE_DEMONSTRADA | artifact |
| ORDER `Gets, Init, gkm?` | fsm start/unsafeAlg/waitingInit/final | INCORRETA on unsafe refinement + accepting set | §2.2 |
| CONSTRAINT `neverTypeOf(password,String)` | absent, registered out of scope | LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA | ALFA-KMF-08 |
| CONSTRAINT `algo in {PKIX}` | identical list | FIDELIDADE_DEMONSTRADA | ALFA-KMF-09 |
| REQUIRES `generatedKeyStore[keyStore]` | body read at i1 | FIDELIDADE_DEMONSTRADA | ALFA-KMF-05, both directions measured |
| REQUIRES `generatedManagerFactoryParameters` — **not in the api30 rule** | n/a | n/a | rule carries no such REQUIRES; the register's D-S14 note concerns CrySL 1.5.2, not this oracle |
| ENSURES `generatedKeyManager[this]/[kms]` | one constant, two writes | FIDELIDADE_DEMONSTRADA | ALFA-KMF-06 |

### 2.2 Language verdicts

- `L(CrySL) ⊆ α(L(MOP))`: **FAIL** — `G1u I1` (measured KMF-T1:
  `getInstance("SunX509")` → UnsafeAlgorithm + 2× InvalidSequence) and `G2u I1`
  (suppressed 2-arg). FEN-C-CARRIER-SEQFAIL / FEN-C-GETS-INVISIVEL.
- `α(L(MOP)) ⊆ L(CrySL)`: PASS realizable; formal-only `g3 g1 i1` (two Gets
  under α) unrealizable per object.
- **Acceptance set diverges** (FEN-C-ACCEPT-END): `g1 i1 gkm1` is
  CrySL-complete but ends in state 0 (non-match) — `gkm1` row `{3,3,0,3}`.
  Measured KMF-T2: no error, and the accepting mark persists only because gkm1
  fires no handler. No realizable FP/FN found from this; minor, table-level
  (ALFA-KMF-04). Note the second `getKeyManagers()` is flagged — that is
  **consistent** with the raw `gkm?` (at most one) — but see 2.3.

### 2.3 Predicate graph — the remove cascade (measured)

CHAIN-T3: after a granted `generatedKeyManager[kms]` (gkm#1), a second
getKeyManagers drives the monitor to fail and `@fail` removes the mark from the
already-handed-out array; a later `SSLContext.init(kms,…)` then reports
UnsatisfiedConstraint. The five rules contain **zero NEGATES** (grep) — the
revocation semantics is invented by the translation. FP lands on the innocent
downstream spec. Critical (ALFA-KMF-07 / ALFA-SET-06, FEN-C-REMOVE-CASCADE).
Compounding: any *spurious* fail (FEN-C-CARRIER-SEQFAIL) also triggers the
removes, so one carrier FP can cascade into chain FPs.

### 2.4 Lifecycle, folding, part(), provenance

Parametric: all 6 events bind `k`; per-object monitor. Folding: PKIX variants
("pkix", "Pkix") resolve on JDK and are rejected by both spec and raw literal —
consistent; "SunX509"/"NewSunX509" resolve (carrier realizability). part(): N/A
— declared. Provenance: carrier shape, missing 2-arg unsafe, accepting-set end
inherited from `jca`; i1/i2 split + generatedKeyStore read + two-argument
removes + `keyManagers` field are gh101 (the 2-arg remove replaced the strictly
worse jca whole-set `remove(Property)`).

---

## 3. TrustManagerFactorySpec (TMF) vs TrustManagerFactory.cryptsl

Isomorphic to KMF (tables byte-equal shape; verified separately). Deltas:

- **gtm1 four-defect repair verified in the round artifact** (binding `mf`,
  return `TrustManager[]`, pointcut return type, constant
  `GENERATED_TRUST_MANAGERS`) — jca twin carries all four defects
  (`jca/TrustManagerFactorySpec.mop:62-65`); PASS (ALFA-TMF-01).
- Carrier FP measured with the campaign's own shape: `getInstance("X509")` —
  the string behind the 8,371 historical UnsafeAlgorithm events
  (`data/gh101/frozen_set_debt.md:90-91,172`) — now also produces 2 spurious
  InvalidSequence (TMF-T1, measured; ALFA-TMF-02, critical). In `jca` the same
  usage produced an *immediate* InvalidSequence at getInstance (all-fail g3
  row, `frozen_set_debt.md:84`): gh101's unsafeAlg state moved the accusation
  from getInstance to init but did not remove it. Provenance:
  inherited-in-substance, form changed by gh101.
- ENSURES split over two constants: factory mark `GENERATED_TRUST_MANAGER` is
  reader-less and registered (`predicate_omissions.csv:5`); the consumed array
  route is correct (CHAIN-T1). PASS-with-note (ALFA-TMF-06).
- Remove cascade: same code shape as the measured KMF path; filed by symmetry
  (ALFA-TMF-07, confidence 0.85).
- Acceptance-set end divergence: same as KMF (ALFA-TMF-04).
- part(): N/A — declared. neverTypeOf: not present in this rule.

---

## 4. SSLContextSpec (SSL) vs SSLContext.cryptsl

### 4.1 Normative matrix

| Clause | MOP | Status | Evidence |
|---|---|---|---|
| FORBIDDEN `getDefault() => Gets` | **absent** | **OMITIDA, unregistered** | ALFA-SSL-06; member exists on android-30 (javap) |
| EVENTS g1/g2 | g1/unsafe_protocol (1-arg), g2 `(String,String)` only | INCORRETA: `(String,Provider)` overload uncaptured | ALFA-SSL-03 |
| EVENT Init `init(kms,tms,_)` | init binds km/tm/random, plain `after` | FIDELIDADE (capture) | artifact |
| EVENTS se1/se2 (Engine) | `call(public void SSLContext.createSSLEngine(..))` | **INCORRETA: pointcut can never match** (returns SSLEngine) | ALFA-SSL-04, FEN-SSL-ENGINE-VOID |
| ORDER `Gets, Init, Engine?` | fsm; `engine` loops at end | INCORRETA (carrier FP; engine* vs Engine?; both masked/compounded by zero-capture) | §4.2 |
| CONSTRAINT `protocol in {7 literals}` | folded `toUpperCase` list | INCORRETA (case-folded superset) | ALFA-SSL-09, 5 measured FN witnesses |
| REQUIRES `generatedKeyManager[kms]`, `generatedTrustManager[tms]` | body reads on bound arrays | FIDELIDADE_DEMONSTRADA | ALFA-SSL-08, measured both directions |
| REQUIRES `randomized[sr]` — **sr bound by no event** (Init's 3rd arg is `_`) | read enforced on the argument | **INCORRETA (extra-oracle)** | ALFA-SSL-07, measured FP |
| ENSURES `generatedSSLContext[this]` | write at init (terminal, registered) | FIDELIDADE + null-pollution residue | ALFA-SSL-10 |
| ENSURES `generatedSSLEngine[eng]` | write inside the dead engine event | INCORRETA (never establishable) | ALFA-SSL-04, measured `validate=false` after real createSSLEngine |

### 4.2 Language verdicts

- `L(CrySL) ⊆ α(L(MOP))`: **FAIL** — `G1u INIT` (measured SSL-T1:
  UnsafeProtocol + spurious InvalidSequence), `G2u INIT`, and — unique to SSL —
  `G2sP INIT`: a **safe** protocol through `getInstance(String, Provider)` is
  invisible (pointcut matches `(String,String)` only) and init FPs. KGN
  (`Object+`) and KMF/TMF (`(String,..)`) cover this overload; SSL does not.
- `α(L(MOP)) ⊆ L(CrySL)`: **FAIL** — every `… ENG` word is silent
  (zero-capture). Robust witness free of exception-path caveats:
  `G1s INIT ENG ENG` — the second createSSLEngine violates the raw `Engine?`
  and nothing fires. (The shorter `G1s ENG` witness carries a realizability
  caveat: pre-init createSSLEngine throws ISE, and the event is after-returning
  — the call still occurs, the monitor still says nothing.)
- Acceptance-set divergences on unsafe-path words (minor; FEN-C-ACCEPT-END).

### 4.3 The randomized extra-oracle read (measured)

`SSLContext.cryptsl:29` binds the third init argument as `_`; `sr` (line 52's
`randomized[sr]`) is bound by **no event** — as written, the raw rule cannot
attach the requirement to any runtime object. The spec enforces it on the
argument: CHAIN-T1 (fully monitored KST→KMF→TMF chain, fresh `SecureRandom`)
yields exactly one UnsatisfiedConstraint — a measured FP against the raw
oracle. Plausible intent-repair; but the audit oracle is the raw rule, and the
precedent (batch B PBK `RANDOMIZED(password)`, FEN family) classifies
extra-oracle predicate reads as INCORRETA pending explicit researcher scope
reduction — none is on file (batch B §8.4). gh101-introduced (jca init read
nothing). ALFA-SSL-07, critical, confidence 0.8 (CogniCrypt unbound-REQUIRES
semantics inferred from the rule text, declared).

### 4.4 Lifecycle, folding, part(), provenance

Parametric: 5/5 events bind ctx (unsafe_protocol returning(ctx) is the gh101
repair; jca's empty-slice shape verified in the twin). Folding: **5 measured FN
witnesses vs the raw literal set** ("tls", "tlsv1.2", "TLSV1.2", "default",
"DEFAULT" all resolve and are spec-safe); "SSLv3"/"DTLS" resolve on JDK — the
carrier FP of §4.2 is realizable today. part(): N/A — declared. Provenance:
engine void-pointcut, getDefault omission, folding, Provider-overload hole all
inherited from `jca` byte-for-byte (twin grep §evidence); the three predicate
reads and the unsafeProtocol state are gh101.

---

## 5. KeyStoreSpec (KST) vs KeyStore.cryptsl

### 5.1 Normative matrix

| Clause | MOP | Status | Evidence |
|---|---|---|---|
| EVENTS g1/g2 | g1/g2 = safe/unsafe **1-arg only**; CrySL g2 `(keyStoreAlg,_)` has **no pointcut** | **OMITIDA** | ALFA-KST-02, FP cascade measured |
| EVENTS l1/l2 (Loads) | fused `load(..)` before | FIDELIDADE (capture; android-30 has exactly 2 overloads) | javap |
| EVENTS s1/s2 (Stores) | fused `store(..)` | FIDELIDADE | javap |
| EVENTS gE/sE | ge1/se1, bound | FIDELIDADE | artifact |
| EVENTS scE/skE1/skE2 (Entries) | **absent** | **OMITIDA** | ALFA-KST-04, silent FN measured |
| EVENT gk | gk1 after-returning Key | FIDELIDADE | artifact |
| ORDER `Gets, Loads, ((gE?, gk) \| (sE, Stores))*` | ere `(g2* g1 load (((ge1 gk1)\|gk1)\|(se1 store))*)+` | INCORRETA on unsafe/2-arg refinement; cycles faithful | §5.2 |
| CONSTRAINTS neverTypeOf ×3 | absent, registered | LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA | ALFA-KST-08 |
| CONSTRAINT `keyStoreAlg in {5}` | identical list | FIDELIDADE_DEMONSTRADA | ALFA-KST-09 |
| ENSURES `generatedKeyStore[this] after Loads` | written by **before**-advice | INCORRETA (timing: granted on entry, survives throwing load) | ALFA-KST-05, minor |
| ENSURES `generatedKey[key,_]/generatedPrivkey/generatedPubkey` | three writes + three removes | FIDELIDADE_DEMONSTRADA (gh101 repair, measured) | ALFA-KST-06 |

### 5.2 Language verdicts

- `L(CrySL) ⊆ α(L(MOP))`: **FAIL** — three shapes: `G1u LOAD` (measured
  KST-T2, `getInstance("JKS")` → 2× InvalidSequence + InvalidKeyStoreType);
  `G2s LOAD` / `G2u LOAD` — **any** 2-arg getInstance usage, safe included, FPs
  at load (measured CHAIN-T2) and starves `generatedKeyStore`, producing a
  second FP inside KMF/TMF (`UnsatisfiedConstraint`) on a fully
  rule-conformant program. This is the strongest chain counterexample of the
  batch.
- `α(L(MOP)) ⊆ L(CrySL)`: **FAIL** — `G1s SCE` etc.: setCertificateEntry /
  setKeyEntry are declared rule events with no ORDER transition; their
  occurrence is a misuse under the typestate reading of CrySL (assumption
  declared in ALFA-KST-04) and the monitor is silent (measured KST-T3, 0
  errors).
- Store-position consistency: `g1 load store` is flagged by both oracles
  (measured KST-T4) — recorded as fidelity, not defect.
- Formal-only: outer `+`/`g2*` re-entry words unrealizable per object;
  threat noted for `KeyStore.getInstance(File,…)`/`KeyStore.Builder` creation
  paths (android-30 members, javap) where **both** oracles are blind but the
  monitor additionally FPs at load.

### 5.3 Lifecycle, folding, part(), provenance

Parametric: 7/7 events bind `k`. Folding: "pkcs12"/"Pkcs12" resolve on JDK,
rejected by both sides — consistent; "BKS"/"AndroidKeyStore" unresolvable on
host JDK (declared; Android-side pending). part(): N/A — declared. Provenance:
2-arg omission, Entries omission, carrier shape, before-timing all inherited
from `jca`; the three-key predicate writes/removes and the Android type list
are gh101.

---

## 6. Batch-level phenomena (FEN registry for batch C)

| FEN | What | Specs | Provenance | Measured? |
|---|---|---|---|---|
| FEN-C-CARRIER-SEQFAIL | unsafe-carrier state + mandatory successor ⇒ 1–2 spurious InvalidSequence on rule-conformant ORDER, plus G9 breach (spurious @fail beside the specific error) | KGN, KMF, TMF, SSL, KST | inherited (`jca` same shapes; TMF/SSL form reshaped by gh101, FP retained) | yes (KGN-T2, KMF-T1, TMF-T1, SSL-T1, KST-T2) |
| FEN-C-GETS-INVISIVEL | getInstance call with zero MOP events (condition-suppressed with no counterpart, or overload uncaptured) ⇒ monitor born at first instance event ⇒ sequence FP + predicate starvation | KGN, KMF, TMF, SSL (incl. safe `(String,Provider)`), KST (via G2 omission) | inherited | yes (KGN-T3, CHAIN-T2) |
| FEN-KST-G2-OMITIDA | entire CrySL Gets alternative untranslated | KST | inherited | yes (CHAIN-T2) |
| FEN-KST-ENTRIES-OMITIDAS | declared events scE/skE1/skE2 unobserved ⇒ silent FN | KST | inherited | yes (KST-T3) |
| FEN-SSL-ENGINE-VOID | void-return pointcut can never match createSSLEngine ⇒ Engine channel zero-capture, generatedSSLEngine unestablishable; register row overstates the edge | SSL (+ SET register claim) | inherited | yes (SSL-T2; ajc weave pending, G6) |
| FEN-SSL-GETDEFAULT-OMITIDA | FORBIDDEN clause untranslated | SSL | inherited | artifact-complete |
| FEN-SSL-RANDOMIZED-EXTRA | randomized enforced on the rule's anonymous `_` argument (sr unbound) | SSL | gh101-introduced | yes (CHAIN-T1) |
| FEN-C-WHITELIST-EXTRA | extra-oracle whitelist members / case-folded acceptance | KGN (6 aliases), SSL (folding) | inherited (aliases/folding predate gh101; base lists gh99) | yes (folding harness; KGN aliases Android-only threat) |
| FEN-KGN-KEYSIZE-OMITIDA | implication constraint dropped, unregistered | KGN | inherited | yes (KGN-T5) |
| FEN-C-REMOVE-CASCADE | @fail revokes granted ENSURES; zero NEGATES in the five rules; poisons downstream reads; compounds with carrier FPs | KMF, TMF (pattern also KGN/KST self-scoped) | gh101 form (2-arg removes) replacing worse jca whole-set removes; revocation semantics itself inherited | yes (CHAIN-T3) |
| FEN-C-ACCEPT-END | CrySL-complete words end outside the match category (gkm1/gtm1→start; SSL unsafe-path) | KMF, TMF, SSL | inherited | yes (KMF-T2, table walks) |
| FEN-C-NULL-POLLUTION | setProperty(P, null) on paths where the guard field was never assigned; validate(P,null)=true | SSL (measured); KST transient | inherited | yes (SSL-T1) |
| FEN-KGN-NAOCOMPILA | round monitor uncompilable standalone (missing import), generators exit 0 | KGN | inherited | yes (compile probe) |
| FEN-KST-LOAD-TIMING | `generatedKeyStore[this] after Loads` granted by before-advice (on entry, survives a throwing load) | KST | inherited | artifact-complete (exception path not driven) |

## 7. Verdict shape (Alfa's covered dimensions)

Every one of the five specs carries at least one **critical FAIL with an
executed, realizable counterexample** in the language or capture dimension, so
under pre_registro §4 none can be APROVADA in the dimensions I cover:

- KGN: carrier FP + suppressed-Gets FP (measured), keySize FN (measured),
  extra-oracle aliases, generatedKey slot loss, uncompilable artifact.
- KMF: carrier FP (measured), suppressed 2-arg Gets, remove cascade (measured).
- TMF: carrier FP on the historical campaign string (measured), same family.
- SSL: Engine zero-capture (measured), getDefault OMITIDA, extra-oracle
  randomized FP (measured), Provider-overload hole, folding FNs (measured).
- KST: 2-arg Gets OMITIDA with measured chain-FP cascade, Entries FN
  (measured), carrier FP (measured).

INCONCLUSIVE hygiene: no claim converts absence of evidence into safety; the
declared pendencies are the ajc/woven half of FEN-SSL-ENGINE-VOID (G6), the
Android-provider realizability of the KGN alias FN, the CogniCrypt semantics of
unbound REQUIRES (ALFA-SSL-07) and of declared-but-unordered events
(ALFA-KST-04) — both used with the assumption stated in the claim row, not
resolved by fiat.

Positive results the falsification attempt could NOT break (recorded as
fidelity): the i-event splits of KGN/KMF/TMF (language-preserving, measured);
the TMF gtm1 four-defect repair; the KST three-key predicate repair; the
KST→KMF/TMF→SSL predicate chain on captured safe paths (single extra-oracle
randomized report aside); parameter binding and per-object isolation in all
five; PKIX/KeyStore whitelists literal-identical to the raw sets.

## 8. File hashes (sha256, files of record in `batchC/`)

```
c6ab0c2c4daeb1077faf3b229b173996c75a280d0d295440caf4c8e9be1461ca  alfa_claims.csv
bbf096dcd74343853ce6638160191271c33d879c8d12aa67f130108fe8c7a18f  alfa_language_check.py
ecab08e5779bb980f77b4ba8c73d0fe6bd5104ecc2db1d1f389743339149e5c3  alfa_language_results.txt
24e3ce6dc4475deaf69ba55f998837b42d0f2cec80eab2c35705f83317f3a132  alfa_HarnessC.java
cd4bb0f22d59c651a799529dcb393efb75a135c75b42c66b41339c69b71babdc  alfa_harnessC_rep1.txt (= rep2 = rep3)
d4758e8f752e7e8e427e17543d9f6c9a554f896dce5cbd4469ee842bd2664424  alfa_FoldingC.java
abe5b3a46b0e1e97da53d6232420aaab4072ec439ec60a761a7abd6aab5c7d96  alfa_foldingC_rep1.txt (= rep2 = rep3)
de949c4bd30bb4bd07c03af506b5ced5a6e3e42a7620242ac72928ad813ea24b  alfa_javap_android30.txt
7a6487bb32e9bf370862a816d49d58a27dd53d65006ce960a8353da607f32987  alfa_kgn_compile_probe.txt
```

Commands and working directories: generation per `batchC/generation_manifest.md`
(not re-run); analysis and harness run from the session scratch
(`scratchpad/batchC/alfa/`), inputs identified by the hashes above and by the
frozen manifests. No spec, rule, or production file was modified; no JavaMOP or
RV-Monitor execution over the spec tree; no emulator touched.
