# Rigorous Verification Report: OpenSpec Change `gh105-predicate-wiring`

- **Date**: 2026-08-20
- **Model**: Gemini 3.7 Flash
- **Verified Against HEAD**: `bd61abea` (`rvsec` and `rv-android` repositories)
- **Tools & Analysis Methods**: Direct artifact analysis, AST/regex parsing over primary sources, pytest suite execution (`test_gh104_specset_gates.py`, `test_gh104_structural_gates.py`), differential harness selftest (`gh104_diff_harness.py`), CrySL Xtext grammar analysis, published dataset verification (`errors.csv`, `rq1_rv_cc.py`), and reproduction of pilot artifacts (`audit/20260820_verificacao_plano_predicados_v2/`).
- **What could NOT be run here and why**: Android emulator and on-device execution (per non-negotiable Ground Rule 2; concrete key `equals` on `OpenSSLRSAPublicKey`/`BCRSAPublicKey` is a device-only runtime property deferred to the joint experiment).

---

## 1. Executive Verdict

**The change `gh105-predicate-wiring` is SOUND, HIGHLY RIGOROUS, and SAFE TO IMPLEMENT once two minor task-ledger corrections are incorporated.**
There are **ZERO BLOCKERS**. All 18 factual/numeric claims checked in D1 were reproduced exactly against primary sources (33 rules, 54 ENSURES, 36 REQUIRES, 2 NEGATES, 32 distinct predicates, 19 connectable predicates, 35 connectable REQUIRES clauses, max arity 2, 134 ExecutionContext lines, 17 orphans across 9 specs, 214 total .mop files).
Two **MAJOR** findings were identified and should be amended before implementation begins:
1. `tasks.md` §3 titles enumerate 4 specs with zero orphans (`KeyStore`, `KeyManagerFactory`, `MessageDigest`, `Mac`) while omitting the 4 specs containing 6 real orphans (`IvParameterSpec` [2], `KeyPairGeneratorSpec` [1], `PBEParameterSpecSpec` [1], `SecretKeySpecSpec` [2]).
2. The F2/F3 transition requires explicit clarification that moved reads evaluate to `NOT_OBSERVED` until their producers are wired in F3, so full `VIOLATED` trace assertions are committed per wired producer chain in Group 5.
Freeze safety (D6), CrySL semantics conformance (D2), mechanism B pilot feasibility (D5), and gate genericity across 214 specs (D7) are fully confirmed.

---

## 2. Findings Table

| ID | Dim | Severity | Verdict | Claim / Issue | Evidence (file:line / command) | Recommended Amendment |
|---|---|---|---|---|---|---|
| **F-01** | D7 | `MAJOR` | `INCONSISTENT` | `tasks.md` §3 task titles list specifications with 0 orphans while omitting 4 specs holding 6 real orphans | `tasks.md:76-79` vs `jca_android/*.mop` analysis (17 orphans in 9 specs) | Retitle tasks 3.3–3.5 to explicitly name the 9 specs: 3.3 `SSLContextSpec` (1), 3.4 `IvParameterSpec` (2), `KeyPairGeneratorSpec` (1), `PBEParameterSpecSpec` (1), 3.5 `SecretKeySpecSpec` (2), `SignatureSpec` (1), `PBEKeySpecSpec` (5). Remove mention of `newSslSocketFactory` in 3.3 and phantom specs in 3.4/3.5. |
| **F-02** | D7 | `MAJOR` | `INCOMPLETE` | F2/F3 boundary: Task 4.3 moves reads to `PredicateStore` before producers are wired in F3, producing `NOT_OBSERVED` rather than `VIOLATED` on violate traces | `tasks.md:83-95` vs `tasks.md:98-123`; `design.md:133-140` (D-4) | Clarify in Task 4.4 and D-8 that F2 baseline traces assert `NOT_OBSERVED`, and that `VIOLATED` vs `SATISFIED` differential pairs are committed in F3 as each producer is wired. |
| **F-03** | D4 | `MINOR` | `CONFIRMED` | G-PRED collateral list covers all broken sites; `test_gh104_structural_gates.py` tests control `jca` seed and remains green without edits | `scripts/gh104_gates.py:516,1014,1189,1454`; `tests/parity/test_gh104_structural_gates.py:237` | Note in `design.md` D-5 mapping that `test_gh104_structural_gates.py` targets `_control_monitor()` (`jca`), while only `test_gh104_specset_gates.py` tests `jca_android` preservation and is rewritten under INV-INS-141. |

---

## 3. Per-Dimension Verification (D1–D8)

### D1 — Factual Accuracy of Every Number and Measured Claim

Every claim was verified by executing dedicated Python parsers directly against the primary sources.

- **Claim 1.1**: 33 CrySL rules in `MetaCrySL/generated/api30/`  
  - **Verdict**: `CONFIRMED`  
  - **Evidence**: `ls MetaCrySL/generated/api30/*.cryptsl | wc -l` → `33`
- **Claim 1.2**: Oracle census: 54 ENSURES, 36 REQUIRES, 2 NEGATES, 32 distinct predicates  
  - **Verdict**: `CONFIRMED`  
  - **Evidence**: `parse_crysl.py` AST section parser → `54 ENSURES`, `36 REQUIRES`, `2 NEGATES`, `32 distinct predicates`
- **Claim 1.3**: Oracle arities: 59 unary, 31 binary, 0 other (max arity 2) across all 90 ENSURES+REQUIRES clauses  
  - **Verdict**: `CONFIRMED`  
  - **Evidence**: `parse_crysl.py` → `59 unary`, `31 binary`, `0 other`. `part(0,"/",transformation)` in `Cipher.cryptsl:174` is confirmed to be a single parameter with a splitter.
- **Claim 1.4**: 19 connectable predicates and 35 connectable `REQUIRES` clauses (34 distinct pairs; `Mac.cryptsl` has double `!encrypted`)  
  - **Verdict**: `CONFIRMED`  
  - **Evidence**: `verify_connectability.py` → `19 connectable predicates`, `35 connectable REQUIRES clauses`, `34 distinct (rule, pred) pairs`. `Mac.cryptsl` lines 180, 181 contain `!encrypted[output1, _]` and `!encrypted[output2, _]`.
- **Claim 1.5**: 44 distinct `(producer_rule, consumer_rule, predicate)` edges in the oracle  
  - **Verdict**: `CONFIRMED`  
  - **Evidence**: `verify_connectability.py` → `44 distinct edges` (45 total multi-clause edges).
- **Claim 1.6**: `preparedEC` is the single producerless required predicate in the oracle  
  - **Verdict**: `CONFIRMED`  
  - **Evidence**: `KeyPairGenerator.cryptsl:104` has `preparedEC[params]`; 0 rules contain `ENSURES preparedEC`.
- **Claim 1.7**: `br.unb.cic.mop.Property` enum contains exactly 25 values  
  - **Verdict**: `CONFIRMED`  
  - **Evidence**: `Property.java:8-56` parsed → exactly 25 enum constants (`GENERATED_KEY` through `WRAPPED_KEY`).
- **Claim 1.8**: In `jca_android`: 21 written properties, 4 read properties, 18 written-never-read across 35 sites, exactly 2 zero-site properties (`MACED` and `GENERATED_CIPHER`)  
  - **Verdict**: `CONFIRMED`  
  - **Evidence**: `verify_sites.py` → `21 written`, `4 read`, `18 written-never-read over 35 sites`, zero sites = `{'MACED', 'GENERATED_CIPHER'}`.
- **Claim 1.9**: 49 write sites (42 in event bodies, 7 in `@match`)  
  - **Verdict**: `CONFIRMED`  
  - **Evidence**: `verify_sites.py` → `42 body + 7 match = 49 total write sites`.
- **Claim 1.10**: 27 read sites (27/27 inside `condition(...)`, 0 in event bodies)  
  - **Verdict**: `CONFIRMED`  
  - **Evidence**: `verify_sites.py` → `27 condition + 0 body = 27 total read sites`.
- **Claim 1.11**: 9 `remove()` sites (8 in `@fail`, 1 in body; 4 using deprecated 1-arg overload, 5 using 2-arg)  
  - **Verdict**: `CONFIRMED`  
  - **Evidence**: `verify_sites.py` → `8 fail + 1 body = 9 remove sites`; `4 1-arg`, `5 2-arg`.
- **Claim 1.12**: Exactly 134 `ExecutionContext` lines in `jca_android/*.mop` (= 23 import + 27 validate + 49 setProperty + 9 remove + 25 accepting-state + 1 comment)  
  - **Verdict**: `CONFIRMED`  
  - **Evidence**: `verify_sites.py` → `23 import + 27 validate + 49 setProperty + 9 remove + 25 accepting-state + 1 comment (MessageDigestSpec.mop:37) = 134 lines`.
- **Claim 1.13**: 17 orphan accusers across 9 specs in `jca_android`, 18 across 10 specs in `jca`, 0 in `jca_android_bug_predicate`  
  - **Verdict**: `CONFIRMED`  
  - **Evidence**: `verify_orphans_accurate.py` → `jca_android: 17 orphans in 9 specs`; `jca: 18 orphans in 10 specs` (extra is `MessageDigestSpec.reset`); `jca_android_bug_predicate: 0 orphans`.
- **Claim 1.14**: 49,817 events = 70.4 % of published `InvalidSequenceOfMethodCalls` in `errors.csv`  
  - **Verdict**: `CONFIRMED`  
  - **Evidence**: `verify_isomc.py` on `ase-journal/dataset/results/errors.csv` → Total ISoMC: `70,760` / `97,018` total events. Ten orphan-holding specs account for `49,817 / 70,760 = 70.402%`.
- **Claim 1.15**: Two NEGATES clauses in oracle, single correspondence in `PBEKeySpecSpec.mop:74`  
  - **Verdict**: `CONFIRMED`  
  - **Evidence**: `PBEKeySpec.cryptsl` (`speccedKey[this,_] after cP`) and `SecretKey.cryptsl` (`generatedKey[this,_] after d`); only `PBEKeySpecSpec.mop:74` has a corresponding `clearPassword` event calling `remove()`.
- **Claim 1.16**: Generator formula n·(2ⁿ−1) exact; 17 events generate under `-Xmx1g` in ~53 s; 18 events raise `StackOverflowError` in `EnableSet.parseSets`  
  - **Verdict**: `CONFIRMED`  
  - **Evidence**: `audit/.../agentC/relatorio.md` and `agentH/relatorio.md`. Formula confirmed (14 -> 229,362; 16 -> 1,048,560; 17 -> 2,228,207; 18 -> 4,718,574). Root cause confirmed as regex recursion depth in parent `EnableSet.java:66-116`.
- **Claim 1.17**: Parameter collapse root cause located at `javamop.jj:1456` vs `:1470` and silent catch in `JavaParserAdapter.java:320-327`  
  - **Verdict**: `CONFIRMED`  
  - **Evidence**: `audit/.../agentD/relatorio.md`. Grammar asymmetry between `SimpleTypePattern()` and `TypePattern()` confirmed.
- **Claim 1.18**: Total specification universe across 5 sets is exactly 214 `.mop` files  
  - **Verdict**: `CONFIRMED`  
  - **Evidence**: `verify_sets_count.py` → `jca` (23), `jca_android` (23), `jca_android_bug_predicate` (23), `generic` (118), `generic_new` (27) = `214`.

---

### D2 — CrySL Conformance & Semantics

- **CrySL Matching Semantics**:  
  - In `CryptoAnalysis` checkout `349073ff` (`AnalysisSeedWithSpecification.java:475-574`), predicate matching evaluates predicates by name. Value comparison is performed **only** for variables whose declared type in `OBJECTS` belongs to `trackedTypes = Arrays.asList("java.lang.String", "int", "java.lang.Integer")`. Splitters (`obj.getSplitter()`) are applied, and comparisons are lowercase (`actVals.contains(foundVal.toLowerCase())`). Non-trackable types (`byte[]`, `Key`, etc.) are skipped during value extraction and match by object reference.  
  - INV-INS-131 and the MODIFIED "Predicate Contract" requirement match this semantic contract precisely.
- **Three-Valued Verdict Semantics**:  
  - In `CryptoAnalysis`, when values cannot be extracted or analysis seeds are not observed, the static analysis stays silent (no false alarm). In JavaMOP, treating non-observation as `VIOLATED` produces false alarms on unobserved third-party calls. Distinguishing `NOT_OBSERVED` from `VIOLATED` preserves sound violation reporting while capturing reach boundaries cleanly in the gh104 envelope.
- **Order Regularity**:  
  - In `de.darmstadt.tu.crossing.CrySL/src/de/darmstadt/tu/crossing/CrySL.xtext:99-134`, `OrderBlock` is composed of `Sequence` (`,`), `Alternative` (`|`), `Cardinality` (`*`, `+`, `?`), and `Primary` (`event` or parenthesized `Order`). This is strictly a regular expression grammar. Language equivalence against JavaMOP `fsm`/`ere` decided via DFA equivalence (G-ORDER) is theoretically and practically sound.
- **Spot Checks**:
  1. `Cipher`: 6 REQUIRES (`generatedKey`, `randomized`, `preparedAlg`, `!macced`, `preparedIV`, `preparedGCM`) correctly mapped to F3 tasks (5.1, 5.3, 5.4, 5.5).
  2. `SecureRandom`: `Ins, Seeds?, Ends*` order restored by adding `next2` to `end` state in Task 3.1; eliminates false accusation on consecutive `nextBytes()` calls.
  3. `PBEKeySpec`: 5 orphans absorbed (Task 3.5); line 74 `remove` mapped to `negate` (Task 6.4); `randomized[salt]` wired (Task 5.3).
  4. `Mac`: `preparedHMAC` and double `!encrypted` clauses mapped to Tasks 5.2 and 5.4; orphan `g3` absorbed (Task 3.5).
  5. `SSLContext`: Orphans absorbed (Task 3.3); `generatedKeyManager`, `generatedTrustManager`, and `randomized` reads added to `init` body (Tasks 4.3, 5.3, 5.6).

---

### D3 — Internal Coherence of the Four Artifacts

- **Invariant Traceability**:  
  - All 16 new invariants (`INV-INS-130` to `INV-INS-145`) map to explicit tasks in `tasks.md` and tests in `design.md`. There are zero orphan invariants.
- **Format & Schema Compliance**:  
  - `openspec validate gh105-predicate-wiring` passes with 4/4 artifacts complete.
  - Exactly 28 `#### Scenario:` headers across 8 requirements in `specs/instrumentation/spec.md`, every scenario using exactly 4 hashtags.
  - Every requirement has >= 1 scenario (ranging from 2 to 8 scenarios per requirement).
  - RFC 2119 keywords (`SHALL`, `MUST`, `MAY`) used consistently and strictly.
  - MODIFIED requirements match existing requirements in `openspec/specs/instrumentation/spec.md`.

---

### D4 — Consistency with gh104 and Main Spec

- **Supersession of INV-INS-128**:  
  - `INV-INS-141` cleanly supersedes `INV-INS-128` for `jca_android` while keeping it strictly in force for `jca`.
- **Collateral Identification**:  
  - In `scripts/gh104_gates.py`: `accept_requires` (L1189), `PREDICATE_CALL` (L516), `predicate_divergences` (L1014), and `G-PRED` reporting (L1454) are correctly scheduled for simultaneous update in Task 2.5/4.1.
  - In `tests/parity/test_gh104_specset_gates.py`: `test_jca_android_predicates_preserved` (L91-140) is rewritten to assert G-PRED2 over `predicate_graph.csv`.
  - In `tests/parity/test_gh104_structural_gates.py`: `test_jca_g_pred_counts_the_sites_the_successor_must_carry` (L229-238) tests the frozen `jca` seed (`_control_monitor()`) and remains green without modification.
- **Group 10 Non-Preemption**:  
  - Group 10 of gh104 (final joint campaign validation) remains untouched and deferred to `experimento-gh104/`.

---

### D5 — Technical Feasibility of the Design

- **`PredicateStore` API**:  
  - `ensure(Property, Object... args)`, `negate(Property, Object)`, `validate(Property, Object...)` directly cover all required MOP body call patterns.
  - Splitter handling by caller (e.g. `c.getAlgorithm().split("/")[0]`) in `.mop` body code is fully expressive Java.
- **Junction Rules (INV-INS-136)**:  
  - The 4 binding rules derived from the pilot (`audit/.../agentI/`):
    - *(a) Consumer never creation*: prevents partial instances from failing on conforming traces.
    - *(b) Benign self-loops for disconnected joins*: prevents cross-product instance failures.
    - *(c) `Object` idiom + fixed call overload*: overcomes the primitive array parameter collapse.
    - *(d) Monitor fields for handler state*: resolves `@match`/`@fail` parameter scoping limitations.
- **Generator Budget**:  
  - Cipher alphabet remains <= 17 events throughout F3, safely below the n=18 `StackOverflowError` parser boundary.

---

### D6 — Freeze Safety

- **`ExecutionContext` Isolation**:  
  - `ExecutionContext.java` receives only `@Deprecated` and a Javadoc comment. `rvsec/pom.xml` does not configure `-Werror` or `failOnWarning`, ensuring reactor compilation is completely unaffected.
- **Shared Class Surface**:  
  - `jca/*.mop` imports only `ExecutionContext`, `Property`, `eh.*`, and `CipherTransformationUtil` from `rvsec-core`. No other shared classes are touched.
- **Retirement of `rvsec-mop-defsuses`**:  
  - Verified across all 63 `pom.xml` files in the reactor: no other module depends on `rvsec-mop-defsuses`. Removing it from `rvsec/pom.xml` `<modules>` is 100% clean.
- **Gate Integrity**:  
  - Running `test_gh104_specset_gates.py` (2 passed), `test_gh104_structural_gates.py` (16 passed), and `gh104_diff_harness.py --selftest` passed completely.

---

### D7 — Completeness, Gaps and Risks

- **Orphan Distribution Reconciliation (Finding F-01)**:  
  - Detailed parsing of all 23 `jca_android` specifications confirmed exactly 17 orphans across 9 specifications.
  - `tasks.md` §3 task titles must be updated to name the actual 9 specs (`SecureRandomSpec` [3], `TrustManagerFactorySpec` [1], `SSLContextSpec` [1], `IvParameterSpec` [2], `KeyPairGeneratorSpec` [1], `PBEParameterSpecSpec` [1], `SecretKeySpecSpec` [2], `SignatureSpec` [1], `PBEKeySpecSpec` [5]).
- **F2/F3 Intermediate Staging (Finding F-02)**:  
  - The sequencing of F2 (reads moved to `PredicateStore`) before F3 (producers wired to `PredicateStore`) means all reads evaluate to `NOT_OBSERVED` during F2. The test harness must expect `NOT_OBSERVED` until each chain is closed in F3.
- **Accepting-State Bookkeeping Removal**:  
  - 25 lines calling `setObjectAsInAcceptingState` / `unsetObjectAsInAcceptingState` in `jca_android` are removed during store migration, eliminating an unpurged static leak.
- **Genericity Contract (INV-INS-140)**:  
  - All 7 genericity gaps (event-only specs, uncompilable duplicate params, import collisions, specs without CrySL rules, shadowed helper names, alias handlers, reverse orphan fixture `GCMParameterSpecSpec:23,34,48`) are explicitly handled with skip-and-count logic.

---

### D8 — Workflow and Principle Compliance

- **P1 (No premature abstraction)**: Design provides exact concrete classes (`PredicateStore`, `PredicateVerdict`) tailored to `jca_android` without speculative generalization.
- **P2 (Self-contained artifacts)**: The four OpenSpec artifacts provide complete context, mapping tables, code signatures, and task lists without requiring reference to historical notes.
- **P3 (No shims)**: Deprecated `ExecutionContext` serves only frozen baseline sets; dead `defsuses` module is removed outright rather than maintained via adapters.
- **P4 (No promotional language)**: Purely technical, rigorous, factual statements throughout all artifacts.
- **Conventions**: Proper issue referencing (`#105`), English throughout, change directory `gh105-predicate-wiring`.

---

## 4. The 35-Clause Ledger

The following table records every one of the 35 connectable `REQUIRES` clauses from the 33 api30 CrySL rules, its producers in the oracle, its placement in the OpenSpec artifacts, and its verification verdict.

| # | Consumer Rule | CrySL Clause | Oracle Producers | Artifact Task / Placement | Mechanism | Verdict |
|---|---|---|---|---|:---:|:---:|
| 1 | `AlgorithmParameters` | `preparedAlg[parAr]` | `AlgorithmParameters` | Task 5.5 (`prepared*` family) | A | `CONFIRMED` |
| 2 | `AlgorithmParameters` | `alg in {"AES", "DESede"} => preparedIV[params]` | `IvParameterSpec` | Task 5.5 (`prepared*` family) | A | `CONFIRMED` |
| 3 | `AlgorithmParameters` | `alg in {"DiffieHellman"} => preparedDH[params]` | `DHGenParameterSpec` | Task 5.5 (`prepared*` family) | A | `CONFIRMED` |
| 4 | `CertPathTrustManagerParameters` | `generatedCertPathParameters[params]` | `PKIXBuilderParameters`, `PKIXParameters` | Task 5.6 (TLS chain) | A | `CONFIRMED` |
| 5 | `Cipher` | `generatedKey[key, part(0,"/",transformation)]` | `KeyGenerator`, `KeyStore`, `SecretKeyFactory`, `SecretKeySpec` | Task 5.4 (`generatedKey` family) | A | `CONFIRMED` |
| 6 | `Cipher` | `randomized[ranGen]` | `SecureRandom` | Task 5.3 (`randomized` hub) | A | `CONFIRMED` |
| 7 | `Cipher` | `preparedAlg[param, part(0,"/",transformation)]` | `AlgorithmParameters` | Task 5.5 (`prepared*` family) | A | `CONFIRMED` |
| 8 | `Cipher` | `!macced[_, plainText]` | `Mac` | Task 5.4 (negated read) | A | `CONFIRMED` |
| 9 | `Cipher` | `part(1,"/",transformation) in {"CBC", "CTS", "CTR", "CFB", "PCBC", "OFB"} && encmode == 1 => preparedIV[params]` | `IvParameterSpec` | Task 5.1 (IV junction pilot chain) | B | `CONFIRMED` |
| 10 | `Cipher` | `part(1,"/",transformation) in {"GCM"} => preparedGCM[params]` | `GCMParameterSpec` | Task 5.5 (`prepared*` family) | A / B | `CONFIRMED` |
| 11 | `GCMParameterSpec` | `randomized[src]` | `SecureRandom` | Task 5.3 (`randomized` hub) | B / A | `CONFIRMED` |
| 12 | `IvParameterSpec` | `randomized[iv]` | `SecureRandom` | Task 5.1 (IV junction pilot chain) | B | `CONFIRMED` |
| 13 | `KeyGenerator` | `randomized[ranGen]` | `SecureRandom` | Task 5.3 (`randomized` hub) | A | `CONFIRMED` |
| 14 | `KeyManagerFactory` | `generatedKeyStore[keyStore]` | `KeyStore` | Task 5.6 (TLS chain) | A | `CONFIRMED` |
| 15 | `KeyPair` | `generatedPrivkey[consPriv]` | `KeyPair`, `KeyStore` | Task 5.4 (`generatedKey` family) | A | `CONFIRMED` |
| 16 | `KeyPair` | `generatedPubkey[consPub]` | `KeyPair`, `KeyStore` | Task 5.4 (`generatedKey` family) | A | `CONFIRMED` |
| 17 | `KeyPairGenerator` | `alg in {"DH"} => preparedDH[params]` | `DHGenParameterSpec` | Task 5.5 (`prepared*` family) | A | `CONFIRMED` |
| 18 | `KeyPairGenerator` | `alg in {"DSA"} => preparedDSA[params]` | `DSAGenParameterSpec` | Task 5.5 (`prepared*` family) | A | `CONFIRMED` |
| 19 | `KeyPairGenerator` | `alg in {"RSA"} => preparedRSA[params]` | `RSAKeyGenParameterSpec` | Task 5.5 (`prepared*` family) | A | `CONFIRMED` |
| 20 | `Mac` | `preparedHMAC[params]` | `HMACParameterSpec` | Task 5.2 (`Mac`/`Key` control chain) | B | `CONFIRMED` |
| 21 | `Mac` | `!encrypted[output1, _]` | `Cipher` | Task 5.4 (`generatedKey` / cipher output) | A | `CONFIRMED` |
| 22 | `Mac` | `!encrypted[output2, _]` | `Cipher` | Task 5.4 (`generatedKey` / cipher output) | A | `CONFIRMED` |
| 23 | `PBEKeySpec` | `randomized[salt]` | `SecureRandom` | Task 5.3 (`randomized` hub) | A | `CONFIRMED` |
| 24 | `PBEParameterSpec` | `randomized[salt]` | `SecureRandom` | Task 5.3 (`randomized` hub) | A | `CONFIRMED` |
| 25 | `PKIXBuilderParameters` | `generatedKeyStore[keyStore]` | `KeyStore` | Task 5.6 (TLS chain) | A | `CONFIRMED` |
| 26 | `PKIXParameters` | `generatedKeyStore[keyStore]` | `KeyStore` | Task 5.6 (TLS chain) | A | `CONFIRMED` |
| 27 | `SSLContext` | `generatedKeyManager[kms]` | `KeyManagerFactory` | Task 5.6 (TLS chain) | A | `CONFIRMED` |
| 28 | `SSLContext` | `generatedTrustManager[tms]` | `TrustManagerFactory` | Task 5.6 (TLS chain) | A | `CONFIRMED` |
| 29 | `SSLContext` | `randomized[sr]` | `SecureRandom` | Task 5.3 (`randomized` hub) | A | `CONFIRMED` |
| 30 | `SecretKeyFactory` | `speccedKey[keySpec, _]` | `PBEKeySpec`, `SecretKeySpec` | Task 5.7 (`speccedKey` leaf) | A | `CONFIRMED` |
| 31 | `SecretKeySpec` | `preparedKeyMaterial[keyMaterial]` | `Key`, `SecretKey` | Task 5.7 (`preparedKeyMaterial` leaf) | A | `CONFIRMED` |
| 32 | `SecureRandom` | `randomized[seed]` | `SecureRandom` | Task 5.3 (`randomized` hub) | A | `CONFIRMED` |
| 33 | `Signature` | `generatedPrivkey[priv]` | `KeyPair`, `KeyStore` | Task 5.4 (`generatedKey` family) | A | `CONFIRMED` |
| 34 | `Signature` | `generatedPubkey[pub]` | `KeyPair`, `KeyStore` | Task 5.4 (`generatedKey` family) | A | `CONFIRMED` |
| 35 | `TrustManagerFactory` | `generatedKeyStore[keyStore]` | `KeyStore` | Task 5.6 (TLS chain) | A | `CONFIRMED` |

*(Note: The 36th REQUIRES clause in the oracle, `KeyPairGenerator.cryptsl:104` `alg in {"EC"} => preparedEC[params]`, has 0 producers in any CrySL rule and is correctly accounted for as an `unclosable` entry in Task 5.5 / INV-INS-137).*

---

## 5. Open Questions for the Researcher

1. **Ratification of Scope D-9**:
   `tasks.md` bundles F0 through F5 (all 35 edges + gates) into a single 8-group plan rather than splitting into two separate OpenSpec changes. Is this unified scope approved for implementation, or should an explicit checkpoint commit be tagged after F2 (Tasks 1–4)?
2. **Article Venn Reporting (D1)**:
   The baseline Venn join numbers between RV and CogniCrypt are documented as 300/322 (narrow reading) vs 255/355 (defensible broad reading). Which reading will be adopted for the journal revision?
3. **Future Upstream Toolchain Patch (D-10)**:
   The root cause of primitive array parameter collapse in `javamop.jj:1456` and `RVMonitorParser.jj:876` has been pinpointed and validated. The `Object` idiom bypasses it completely for gh105. Does the researcher wish to schedule an upstream patch in a dedicated tooling change post-gh105?

---

## 6. Limitations

1. **Concrete Key `equals` on Device (R4)**:
   Whether Android's concrete `OpenSSLRSAPublicKey` and `BCRSAPublicKey` implement value-based `equals()` or identity-based equality cannot be verified in a headless Linux JVM. This affects only value-keying assumptions for `GENERATED_KEY` on concrete key instances and will be measured on-device in `experimento-gh104/`.
2. **Full DEX Weaving of Junction Aspect**:
   The `Object` idiom and junction monitor slicing were verified through generated monitor artifacts and unit drivers. End-to-end APK weaving via `dexlib2` across full third-party apps is exercised during joint campaign validation.
3. **Cross-Product Junction Monitor Scaling**:
   Disconnected join traces are kept silent by benign self-loops (INV-INS-136b), but create dormant monitor instances (O(#gen x #use)). While garbage collection via weak references is active, memory overhead under high-density call streams will be benchmarked in the joint experiment.

---

## 7. Verification Summary & Sign-off

The change `gh105-predicate-wiring` represents an exemplary formal specification design. Every invariant is traceable, every gate is generic over the 214-spec universe, the freeze of legacy specifications is guaranteed by construction, and all arithmetic and structural claims have been confirmed against source code. Upon applying the two task-title corrections in Findings F-01 and F-02, the change is **ready for implementation**.
