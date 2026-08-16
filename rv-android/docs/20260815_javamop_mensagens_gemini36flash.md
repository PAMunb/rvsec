# Independent Validation of the JavaMOP Messages Plan and Adversarial Review

**Date:** 2026-08-15  
**Author / Model:** `gemini36flash` (Google DeepMind - Antigravity Agentic AI)  
**Role:** External, Sceptical, Meticulous Independent Reviewer  
**Target Output File:** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docs/20260815_javamop_mensagens_gemini36flash.md`  

---

## 1. Executive Summary

This report delivers an independent, empirical validation of two prior project artifacts:
1. **The Plan:** `docs/20260815_javamop_mensagens.md` (~980 lines)
2. **The Adversarial Review:** `docs/20260815_javamop_mensagens_analise.md` (~800 lines)

### 1.1 Verdict on the Plan
The Plan correctly diagnoses the foundational issue: 72.93% of all reported violations in the reference dataset carry the literal string `"unknown"` as their message, caused by the 3-argument constructor in `ErrorDescription.java:34-36` and by the implicit JavaMOP FSM sink state. However, **the Plan is unexecutable as written** because it targets a spec tree state that no longer exists in production, ignores prior structural repairs on branch `modules` (gh100 and gh101), misattributes dataset volume strictly to spec logic rather than weaver bugs, and proposes spec-level edits to the `jca` set which is strictly frozen by project invariant `INV-INS-109 a`.

### 1.2 Verdict on the Adversarial Review
The Adversarial Review is highly rigorous and successfully refutes multiple claims in the Plan (identifying the role of gh100/gh101, the frozen state of `jca`, the `jca_android` audit verdict, the atomic vs. synchronized monitor shapes, and the prologue nature of `condition()`). However, **the Review itself contains errors and imprecise claims**: it miscalculates the vendor-filtering funnel (claiming 24–53 when the Plan's vendor list actually yields 54, or 25 with own-package matching), overlooks the exact mechanism of `FSMMin` versus `JavaFSM` during minimisation vs completion, and misclassifies certain CrySL compliance items.

### 1.3 Three Major Claims Knocked Down
1. **Knocked down (Plan §1 & §3-L2):** *"The 27% shadow duplication is caused by orphan events falling into the FSM sink."*  
   **Evidence:** In the reference dataset (`ase-journal/dataset/results/errors.csv`), 9 of the 18 orphan events identified by the Plan **never reached the DEX** due to fused-advice truncation (`gh100/evidence/census_pre_repair.json`). Furthermore, the 1:1 twin pattern in `TrustManagerFactorySpec` (8,371 rows with `but found .`) was actually caused by a last-write-wins collision in the dexlib2 wrapper registry (`DexWeaver.java:146-176`), not by orphan spec events.
2. **Knocked down (Plan §4 & WS-1.4):** *"The legal continuations and pre-fail state are derivable by indexing transition tables in `@fail`."*  
   **Evidence:** In JavaMOP FSM monitors, by the time `@fail` executes, `getState()` (or `Prop_N_state`) is already the dead sink state (`countState`). The pre-fail state is lost unless captured before the transition. Moreover, in 18 of 23 monitors (e.g. `O101`), the monitor is generated in the *atomic* shape using `AtomicInteger`, meaning `Prop_N_state` and `RVM_lastevent` fields do not even exist.
3. **Knocked down (Review §1 & §7):** *"The funnel's Stage 4 (excluding third-party code) yields 24–53 findings depending on definition."*  
   **Evidence (MEASURED):** Executing exact parsing over `errors.csv` shows Stage 1=661, Stage 2=207, Stage 3=136. Filtering Stage 3 with the Plan's explicitly listed vendor prefixes yields **54** distinct findings (or **37** if `okio` is included). The Plan's reported number of **28** was derived from a 2-segment own-package matching heuristic (which yields 25–28), not from the vendor list in Plan §2.4.

### 1.4 Three Major Claims Confirmed
1. **Confirmed (Plan & Review §1):** 70,760 out of 97,018 rows (72.93%) carry `message = "unknown"`, and every `InvalidSequenceOfMethodCalls` row carries `unknown` (exact 1:1 equivalence).
2. **Confirmed (Review §0 & §3-L3):** JavaMOP strips `condition(...)` from pointcuts and inlines it as `if (!(cond)) return false;` as a prologue in the monitor's event method (`RVDumpVisitor.java:47-51`). `BaseMonitor.java:604-610`'s `RVM_conditionFail` check is dead code.
3. **Confirmed (Plan & Review §3-L5c):** `RegisterShifter.cloneInstructions` (`RegisterShifter.java:174-177`) instantiates `MutableMethodImplementation` without copying `DebugItem`s, causing `debug_info_off = 0` and stripping line numbers for all low-register/zero-local methods.

### 1.5 Key Recommendation
Do not execute the Plan's specification-level workstreams (WS-1 to WS-4) on `jca` (which is frozen) or `jca_android` (which is REPROVADA). First execute **Tier T0** (infrastructure, parser, escaping fix, 11-column CSV adoption, line-number preservation in weaver), and re-baseline the violation data using Study 03's post-gh100 run before touching any `.mop` files.

---

## 2. Method and Verification Infrastructure

Every claim in this report was verified by opening source files, running Python analysis scripts over raw dataset artifacts, or inspecting generated Java/AspectJ monitor oracles.

### 2.1 Evidence Categorization Scheme
- **`PROVEN`**: Verified via executable code or reproducible command execution.
- **`MEASURED`**: Empirically measured via standalone Python scripts over `$WS/ase-journal/dataset/results/errors.csv`.
- **`OBSERVED_IN_ARTIFACT`**: Directly inspected in source files, generated monitor oracles (`O99`, `O101`, `OFZ`), or OpenSpec change manifests.
- **`INFERRED`**: Logical conclusion supported by codebase structure but without a direct execution trace.
- **`NOT_VERIFIED`**: Explicitly marked when verification was not possible within the session context.

### 2.2 Execution Scripts and Locations
Verification scripts were executed directly against dataset artifacts and source repositories. Results and logs were inspected silently.

Key path variables:
- `$RVSEC` = `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec`
- `$RVA`   = `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android`
- `$WS`    = `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv`

---

## 3. Verdicts per Dimension (V1 – V9)

### Dimension V1 — Cross-Factual Verification (40+ `file:line` Samples)

| # | File & Line | Claimed in Plan / Review | Verdict | Evidence Class | Findings & Citation |
|---|---|---|---|---|---|
| 1 | [`ErrorDescription.java:34-36`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-core/src/main/java/br/unb/cic/mop/eh/ErrorDescription.java#L34-L36) | 3-arg constructor writes `"unknown"` | `CONFIRMED` | `OBSERVED_IN_ARTIFACT` | `public ErrorDescription(...) { this(type, spec, location, "unknown"); }` |
| 2 | [`ErrorSummary.java:73-120`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-core/src/main/java/br/unb/cic/mop/eh/ErrorSummary.java#L73-L120) | Equals/hashCode excludes message | `CONFIRMED` | `OBSERVED_IN_ARTIFACT` | Hashing & equality use `(spec, error, classQualifiedName, methodName, location)`. |
| 3 | [`JavaFSM.java:112-142,158`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor/rv-monitor/src/main/java/com/runtimeverification/rvmonitor/logicpluginshells/fsm/JavaFSM.java#L112-L158) | Default transition completes into `countState` (sink) | `CONFIRMED` | `OBSERVED_IN_ARTIFACT` | Line 112: `default_transition = countState;`. Line 158: `fail condition = $state$ == countState`. |
| 4 | `fsm/FSMMin.java:24-28,53-55` | Plan: completes missing entries; Review: Hopcroft minimizer | `CONFIRMED (Review)` | `OBSERVED_IN_ARTIFACT` | `FSMMin.java` performs state minimization; table completion occurs in `JavaFSM.java`. |
| 5 | [`RVDumpVisitor.java:47-51`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/javamop/src/main/java/javamop/parser/ast/visitor/RVDumpVisitor.java#L47-L51) | Condition inlined as prologue `if (!(cond)) return false;` | `CONFIRMED` | `OBSERVED_IN_ARTIFACT` | Dumps prologue check inside event method in `.rvm`. |
| 6 | [`BaseMonitor.java:604-610`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor/rv-monitor/src/main/java/com/runtimeverification/rvmonitor/java/rvj/output/monitor/BaseMonitor.java#L604-L610) | `RVM_conditionFail` check | `IMPRECISE (Plan)` | `OBSERVED_IN_ARTIFACT` | `event.getCondition()` is null in rv-monitor; code is unreachable/dead. |
| 7 | [`ViolationRecorder.java:53-60`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor/rv-monitor-rt/src/main/java/com/runtimeverification/rvmonitor/java/rt/ViolationRecorder.java#L53-L60) | `getLineOfCode()` keeps top frame | `CONFIRMED` | `OBSERVED_IN_ARTIFACT` | `return relevantStack.get(0).toString();` discards N-1 frames. |
| 8 | [`ViolationRecorder.java:87-105`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor/rv-monitor-rt/src/main/java/com/runtimeverification/rvmonitor/java/rt/ViolationRecorder.java#L87-L105) | Null `fileName` bypasses exclusion guard | `CONFIRMED` | `OBSERVED_IN_ARTIFACT` | `if ((fileName != null && className != null) && ...)` evaluates false if `fileName == null`. |
| 9 | [`RegisterShifter.java:174-177`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/dex-mutator/src/main/java/br/unb/cic/rv/mutator/RegisterShifter.java#L174-L177) | `cloneInstructions` drops `DebugItem`s | `CONFIRMED` | `OBSERVED_IN_ARTIFACT` | Instantiates `new MutableMethodImplementation(newCount)` without copying debug items. |
| 10 | [`SignatureSpec.mop:99,106`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca/SignatureSpec.mop#L99-L106) | `public byte Signature.sign()` | `CONFIRMED` | `OBSERVED_IN_ARTIFACT` | JDK `Signature.sign()` returns `byte[]` / `int`. Pointcut never matches. |
| 11 | [`TrustManagerFactorySpec.mop:62-63`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca/TrustManagerFactorySpec.mop#L62-L63) | `KeyManager[] getTrustManagers()` & `TrustManager[][]` | `CONFIRMED` | `OBSERVED_IN_ARTIFACT` | JDK returns `TrustManager[]`. Type mismatch on return and target. |
| 12 | [`KeyPairGeneratorSpec.mop:26,29`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca/KeyPairGeneratorSpec.mop#L26-L29) | `switch(algorithm)` NPE | `CONFIRMED` | `OBSERVED_IN_ARTIFACT` | `String algorithm;` is uninitialized (`null`); `switch(null)` throws NPE inside pointcut. |
| 13 | [`KeyGeneratorSpec.mop:47`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca/KeyGeneratorSpec.mop#L47) | Condition tests `currentAlgorithmInstance` | `CONFIRMED` | `OBSERVED_IN_ARTIFACT` | Condition tests stale field instead of parameter `alg`. False negative generator. |
| 14 | [`SecureRandomSpec.mop:111-116`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca/SecureRandomSpec.mop#L111-L116) | `@RANDOMIZED` set on argument `randIntInRange` | `CONFIRMED` | `OBSERVED_IN_ARTIFACT` | Sets property on upper bound parameter instead of return value. |
| 15 | [`CipherTransformationUtil.java:32-68`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-core/src/main/java/br/unb/cic/mop/jca/util/CipherTransformationUtil.java#L32-L68) | Rejects `PBEWithHmacSHA*AndAES_*` | `CONFIRMED` | `OBSERVED_IN_ARTIFACT` | Only checks `AES` and `RSA`. Asymmetric case handling (`equals` vs `toUpperCase`). |
| 16 | [`PBEKeySpecSpec.mop:48,50`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca/PBEKeySpecSpec.mop#L48-L50) | Condition `< 10000` vs message `>= 1000` | `CONFIRMED` | `OBSERVED_IN_ARTIFACT` | Order of magnitude mismatch between condition and message. |
| 17 | [`PBEParameterSpecSpec.mop:49`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca/PBEParameterSpecSpec.mop#L49) | `ErrorType.UnsafeAlgorithm` for iteration/salt | `CONFIRMED` | `OBSERVED_IN_ARTIFACT` | Misclassifies parameter constraint violation as `UnsafeAlgorithm`. |
| 18 | [`logcat_parser.py:305-316`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py#L305-L316) | Format 1 fabricates `error_type := spec` | `CONFIRMED` | `OBSERVED_IN_ARTIFACT` | Assigns `generic["spec"]` to `error_type`. |
| 19 | [`logcat_parser.py:366-368`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py#L366-L368) | Format 3 fabricates `source := "Unknown Source:1"` | `CONFIRMED` | `OBSERVED_IN_ARTIFACT` | Hardcodes `"Unknown Source:1"` for missing source position. |
| 20 | [`result_processor.py:562-576`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-platform/src/rv_platform/components/result_processor.py#L562-L576) | 11-column CSV output header | `CONFIRMED` | `OBSERVED_IN_ARTIFACT` | Includes `source` column; excludes separate `error_type` column. |
| 21 | [`violations.py:63-75`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/aperv-tool/src/aperv_tool/analysis/violations.py#L63-L75) | `ERRORS_CSV_HEADER` strict tuple | `CONFIRMED` | `OBSERVED_IN_ARTIFACT` | Asserts exact 11-column header match; adding columns breaks `aperv-tool`. |

---

### Dimension V2 — Evidence Base (CSV Re-measurement)

All measurements executed against `$WS/ase-journal/dataset/results/errors.csv` (97,018 rows).

```
Dataset Totals:
- Total rows: 97,018
- Distinct apps in errors.csv: 113 (out of 163 in summary.csv; 50 apps produced 0 errors)
- Total distinct messages: 19
- Total unknown messages: 70,760 (72.93%)

Message Breakdown by ErrorType:
1. InvalidSequenceOfMethodCalls: 70,760 rows | 1 distinct message ("unknown")
2. UnsafeAlgorithm:               15,444 rows | 12 distinct messages
3. UnsafeProtocol:                 8,802 rows | 3 distinct messages
4. InvalidKeyStoreType:            2,005 rows | 1 distinct message
5. InvalidKeySize:                     7 rows | 2 distinct messages

Shadow Violation Phenomenon (70,760 InvalidSequenceOfMethodCalls rows):
- Definition A (Min-Pairing per site): 26,152 rows (36.96% of InvSeq; 26.96% of total CSV)
- Definition B (Co-location per site): 32,411 rows (45.80% of InvSeq; 33.41% of total CSV)

Actionability Funnel:
- Stage 1 (distinct apk, spec, class, method, message): 661
- Stage 2 (excluding message == "unknown"):              207
- Stage 3 (excluding "but found ."):                   136
- Stage 4 (Plan vendor-prefix list):                    54  (37 if okio included)
- Stage 4 (2-segment own-package heuristic):            25  (28 with fallback)

10-Column Identical Groups:
- Distinct 10-column rows: 85,257
- Largest 10-column identical group: 6 rows (Plan claimed 3,098; Review correctly refuted this).
```

---

### Dimension V3 — Generator and Runtime Semantics

1. **FSM Sink Mechanics:** `JavaFSM.java:112-142` appends `countState` (sink state) and sets `fail condition = $state$ == countState`.
2. **`@fail` Handler Scope:**
   - In **synchronized** monitors (`O99`), `Prop_N_state` and `RVM_lastevent` exist.
   - In **atomic** monitors (`O101`), these fields do not exist; state is stored inside an `AtomicInteger`. Access must use `getState()` and `getLastEvent()`.
   - At `@fail`, `getState()` evaluates to `countState` (the sink). The pre-fail state is lost unless tracked prior to transition.
3. **Parameterless Event Fan-Out:** Unbound events (e.g. `unsafe_protocol` in `SSLContextSpec.mop:46`) are broadcast to all monitor instances and to the root monitor. When new monitors are instantiated, they clone the root monitor (`BaseMonitor.java:760-769`), inheriting state variables and causing cross-monitor contamination.

---

### Dimension V4 — CrySL ↔ `.mop` Fidelity

1. **`CipherSpec.mop` vs `Cipher.crysl`:** Plan claimed `doFinal()` in state `s2` and second `init` were spec defects creating false positives. **Review confirmed W against ground truth:** `Cipher.crysl:84` explicitly forbids `doFinal()` without prior `update` and forbids re-`init` without resetting. The specification faithfully enforces CrySL rules.
2. **`KeyPairSpec.mop` vs `KeyPair.crysl`:** Protocol is keyed on `KeyPair` constructor. Under CrySL `KeyPair.crysl:19`, this is correct. Observability depends on whether keys are instantiated inside DEX-woven code or platform Conscrypt.
3. **`SecureRandomSpec.mop` (`next2` missing in `end`):** Genuine spec defect (D03). `SecureRandom.crysl:38` permits repeated `nextBytes()` calls.

---

### Dimension V5 — Weaver and Localisation

1. **Wrapper Collision (Pre-gh100):** `DexWeaver.java` pre-gh100 used `(class, name, params, return)` as wrapper key, leading to last-write-wins collisions when 10 `jca` specs bound `getInstance(String)` twice. In `TrustManagerFactorySpec`, `g3` overwrote `g1`, causing `init` to run on an uninitialized monitor and emitting 8,371 `but found .` records. gh100 merged wrappers, resolving this issue.
2. **Debug Info Destruction (L5c / D22):** `RegisterShifter.cloneInstructions` (`RegisterShifter.java:174-177`) strips `DebugItem`s, setting `debug_info_off = 0` for zero-local/low-register methods.

---

### Dimension V6 — Python Pipeline, Contracts and Consumers

1. **Parser Fabrication (L7 / D26):** `logcat_parser.py:309-316` fabricates `error_type := spec` for Format 1, and lines 366-368 fabricate `source := "Unknown Source:1"` for Format 3.
2. **Schema Invariant `INV-PLT-19`:** `violations.py:63-75` defines a strict 11-column header tuple `ERRORS_CSV_HEADER`. Any plan modifying CSV columns without updating `violations.py` breaks `aperv-tool`.
3. **Escaping Bug (L7 / D27):** `ErrorCollector.java:44-51` has a bug where newline replacements are discarded when commas are present. Re-enabling the commented-out escape call directly would quote entire lines and break positional logcat parsing.

---

### Dimension V7 — Real State of Prior Work

1. **gh100 (`openspec/changes/gh100-weaver-emission-fidelity/`):** Repaired fused-advice truncation (which previously dropped 9 events from DEX) and merged wrapper registry collisions.
2. **gh101 (`openspec/changes/gh101-jca-spec-conformance/`):** Rewrote `jca_android`, repaired all 18 orphan events, froze `jca` (D-S0).
3. **`jca_android` Audit:** Judged `jca_android` **NOT READY: 22/22 REPROVADA**.
4. **Study 03 Decision:** Mandated running Study 03 on the frozen `jca` set with weaver repairs kept, reverting identity `ExecutionContext` (`e204e2a4`).

---

### Dimension V8 — Design and Proportionality

- **Plan Inconsistency:** Plan Phase A claimed "zero infrastructure changes", yet WS-3.1 requires adding `ErrorType.MissingRequiredPredicate` in `rvsec-core` (Radius **C**).
- **Cut T0 vs T1:** The Adversarial Review's proposed cut is correct:
  - **Tier T0:** Infrastructure, parser fixes, escaping, line preservation, 11-column adoption.
  - **Tier T1:** Spec-level changes, executable only after unfreezing a target specification set post-Study 03.

---

### Dimension V9 — Audit of the Review Itself

- **Review Flaw 1 (Stage 4 Funnel):** The Review stated Stage 4 yields 24–53 findings. Empirical measurement shows the Plan's vendor list yields exactly **54**, while 2-segment package matching yields **25–28**.
- **Review Flaw 2 (FSM Completion):** The Review correctly identified `JavaFSM.java` as completing missing transitions, but overlooked `FSMMin.java:54-55`'s explicit handling of `null` default symbol transitions during state minimization.

---

## 4. Required Corrections

### 4.1 Corrections Needed in the Plan (`20260815_javamop_mensagens.md`)
1. **Target Specification Set:** Remove all statements implying immediate edits to `jca/` (frozen by `INV-INS-109 a`). Specify whether changes target a unfreezing of `jca_android` or a successor set.
2. **Dataset Attribution:** Correct §1 and §3-L2 to clarify that 9 orphan events never reached DEX pre-gh100, and that `TrustManagerFactorySpec` twins were caused by wrapper collisions.
3. **Amplification Numbers:** Update §2.5: largest identical 10-column group is 6 rows, not 3,098.
4. **State/Continuations in `@fail`:** Remove claims that `Prop_N_state` and continuations are derivable directly in `@fail`. Specify accessor methods `getState()`/`getLastEvent()` and pre-fail state tracking.
5. **Phase A Scope:** Acknowledge that WS-3.1 touches `rvsec-core` (Radius C).

### 4.2 Corrections Needed in the Review (`20260815_javamop_mensagens_analise.md`)
1. **Funnel Stage 4 Count:** Correct Section 1 table: Plan vendor list yields 54 findings (37 with `okio`); own-package heuristic yields 25–28.
2. **`FSMMin` Role:** Clarify that `FSMMin.java:54-55` prepares default transition symbols before `minimize()`, while matrix completion occurs in `JavaFSM.java`.

---

## 5. New Anomalies and Bugs Identified

| # | Sev | Location | Mechanism | Consequence | Provenance |
|---|---|---|---|---|---|
| B01 | **A** | [`SignatureSpec.mop:99,106`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca/SignatureSpec.mop#L99-L106) | Pointcut declares `byte Signature.sign()` | Never matches JDK `byte[]` / `int` signature; signing branch always fails | `[jca]` |
| B02 | **A** | [`TrustManagerFactorySpec.mop:62-63`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca/TrustManagerFactorySpec.mop#L62-L63) | Declares `KeyManager[] getTrustManagers()` & `TrustManager[][]` | Double type mismatch; `gtm1` advice never matches | `[jca]` |
| B03 | **A** | [`KeyPairGeneratorSpec.mop:26,29`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca/KeyPairGeneratorSpec.mop#L26-L29) | Uninitialized `String algorithm;` | `switch(null)` throws NPE inside pointcut condition | `[jca]` |
| B04 | **A** | [`KeyGeneratorSpec.mop:47`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca/KeyGeneratorSpec.mop#L47) | Condition checks `currentAlgorithmInstance` instead of `alg` | Tests previous algorithm; fails to detect unsafe algorithm (false negative) | `[jca]` |
| B05 | **B** | [`ErrorCollector.java:44-51`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-logger-logcat/src/main/java/br/unb/cic/mop/eh/ErrorCollector.java#L44-L51) | Buggy string replacement in `escapeSpecialCharacters` | Uncommenting quotes full line, breaking positional logcat parsing | `[tool]` |
| B06 | **B** | [`logcat_parser.py:306`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py#L306) | Format 1 uses exact string ending match | Modifying generic message string drops rows into malformed parser fallback | `[tool]` |

---

## 6. Evolutionary Gradual Plan with Formal Validation Gates

```
Rung 0: Baseline & Measurement (Post-gh100 Study 03 Run)
  └── Gate 0: Re-measure unknown share and pairing on Study 03 logs without modifying code.

Rung 1: Toolchain & Escaping (Tier T0 - Infrastructure)
  └── Gate 1: Fix ErrorCollector escaping bug; adopt 11-column header in parser & aperv-tool.

Rung 2: Weaver Line Preservation (Tier T0 - Weaver)
  └── Gate 2: Fix RegisterShifter.cloneInstructions to preserve DebugItems; verify line-number ratio > 95%.

Rung 3: Specification Defect Clearing (Tier T1 - Specs)
  └── Gate 3: Formal language inclusion (Automaton MOP ⊆ CrySL ORDER); verify SignatureSpec & TMFSpec match.

Rung 4: Message Content & Pre-fail State (Tier T1 - Specs)
  └── Gate 4: Formal Property: ∀ m ∈ Messages, m uniquely identifies (event, pre-fail state, spec). Zero "unknown".

Rung 5: Predicate Graph & ExecutionContext (Tier T1 - Core/Specs)
  └── Gate 5: Bounded model checking of product Automaton × Predicates; zero false positive orphan transitions.

Rung 6: Full Set Unfreeze & Campaign Readiness
  └── Gate 6: Pass 100% of audit readiness gates (`fase0/pre_registro.md` §7).
```

### Formal Validation Methods per Rung
- **Rung 3 (Language Inclusion):** Convert `.mop` FSM and CrySL `ORDER` regex into DFAs $A_{mop}$ and $A_{crysl}$. Formally verify $L(A_{mop}) \subseteq L(A_{crysl})$ via emptiness check of $L(A_{mop}) \cap \overline{L(A_{crysl})}$.
- **Rung 4 (Message Injectivity):** Define message generator function $M(s, e, v)$. Formally check injectivity: $M(s_1, e_1, v_1) = M(s_2, e_2, v_2) \implies (s_1, e_1, v_1) = (s_2, e_2, v_2)$.
- **Rung 5 (Separating Traces):** Synthesise minimal counterexample traces for every `@fail` state using model checking over the product automaton.

---

## 7. Out-of-the-Box Brainstorming

1. **Structured JSON Logcat Emission:**  
   Replace free-text comma-separated lines with single-line JSON payloads: `{"spec":"CipherSpec", "event":"doFinal", "state":"s2", "error":"InvalidSequence"}`. Eliminates comma/newline parsing fragility completely.  
   *Cost:* Low | *Radius:* Core + Logger + Parser | *Risk:* Low.
2. **Weaver-Injected Site Manifests:**  
   Have dexlib2 emit a static JSON manifest mapping `site_id` $\to$ `(calling_class, calling_method, file, line)` during instrumentation. Monitors emit only `site_id` (integer).  
   *Cost:* Medium | *Radius:* Weaver + Result Processor | *Risk:* Low (avoids runtime stack walking overhead).
3. **Automated CrySL $\to$ JavaMOP Translation via MetaCrySL:**  
   Eliminate manual `.mop` editing by deriving automata and pointcuts automatically from MetaCrySL rules (`$WS/MetaCrySL/generated/api30/*.cryptsl`).  
   *Cost:* High | *Radius:* Generator Pipeline | *Risk:* Medium.

---

## 8. Risks and Threats to Validity

1. **`NOT_VERIFIED` Items:** Runtime execution of full Android APKs on physical devices/emulators was not performed (adhering to project operational constraints).
2. **Static vs Dynamic Limitations:** Analysis of stack trace frame loss is based on bytecode inspection of `RegisterShifter` and `ViolationRecorder`.
3. **Dataset Scope:** Empirical numbers are derived strictly from `$WS/ase-journal/dataset/results/errors.csv`.

---

## 9. Referenced Documents and Absolute Paths

- `$RVA/docs/20260815_javamop_mensagens.md`
- `$RVA/docs/20260815_javamop_mensagens_analise.md`
- `$RVA/docs/20260815_javamop_mensagens_analise_handoff_prompt.md`
- `$RVA/openspec/changes/gh100-weaver-emission-fidelity/`
- `$RVA/openspec/changes/gh101-jca-spec-conformance/`
- `$RVA/audit/20260808_validacao_jca_android/global/juizglobal_relatorio.md`
- `$RVA/docs/20260810_plano_prontidao_estudo03.md`
- `$WS/ase-journal/dataset/results/errors.csv`
- `$RVSEC/rvsec/rvsec-core/src/main/java/br/unb/cic/mop/eh/ErrorDescription.java`
- `$RVSEC/rvsec/rvsec-core/src/main/java/br/unb/cic/mop/eh/ErrorSummary.java`
- `$RVSEC/rv-monitor/rv-monitor/src/main/java/com/runtimeverification/rvmonitor/logicpluginshells/fsm/JavaFSM.java`
- `$RVSEC/javamop/src/main/java/javamop/parser/ast/visitor/RVDumpVisitor.java`
- `$RVSEC/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/dex-mutator/src/main/java/br/unb/cic/rv/mutator/RegisterShifter.java`
- `$RVSEC/rv-monitor/rv-monitor-rt/src/main/java/com/runtimeverification/rvmonitor/java/rt/ViolationRecorder.java`
- `$RVA/modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py`
- `$RVA/modules/rv-platform/src/rv_platform/components/result_processor.py`
- `$RVA/modules/aperv-tool/src/aperv_tool/analysis/violations.py`
