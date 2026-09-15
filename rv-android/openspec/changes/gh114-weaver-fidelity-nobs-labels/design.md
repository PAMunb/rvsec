# Design — gh114 Weaver Fidelity, Labelled Non-Observation Reports and Bounded Result Export

GitHub Issue: #114

## Context

The proposal groups three repairs that share one gate, the next campaign, and no code. They touch two repositories and eight modules, and the implementation budget is short, so this design is organised around what can be done in parallel without two workers editing the same file.

- **Weaver** (`rvsec/rvsec-android/rvsec-instrumentation-dexlib2`, Java 21, Maven). Five divergences from AspectJ (A1–A5). FR02, NFR06.
- **Specification set** (`rvsec/rvsec-mop/src/main/resources/jca_android`, 47 `.mop`; `rvsec/rvsec-core` for `Property` and helpers). Six label codes, per-element manager credit, the upstream-refusal mark, evidence keys, the RSA list. FR03, FR13.
- **Consumers** (`rv-android`): `rv-android-core` (`RvErrorLog.unique_msg`), `rv-coverage` (logcat parser), `scripts/` gates and `tests/parity/`, `data/jca_android/` records. FR11, FR13.
- **Export** (`modules/rv-platform`). One pass over tasks, one static model per APK, release of parsed state. FR14, NFR08.

Constraints carried from the discussion that produced this change:

- Nothing specific to a dataset enters `rv-android` or `rvsec`: every rule is API or weaver semantics. APKs of the corpus are used only as test and smoke inputs.
- `PredicateStore` keeps identity comparison.
- The frozen `jca` set is not edited and no impact on it is measured.
- Labels keep every reported site reported, except the per-element manager credit.
- One smoke test, at the end.
- No comparison with the ajc weaver or any other weaver is part of this change.
- #112 is archived: `BatchRunner` already accumulates counters into `counts` and `instr-cli` exits 1 with the cause on failure.

Facts the decisions rest on, all measured on the current tree (file:line in the specs of this change):

- The wrapper path never calls `PointcutMatcher`; only the inline `before` path does.
- `AndroidClassIndex` already reads superclass and interfaces but exposes only declared methods.
- dexlib2 3.0.9 `MutableMethodImplementation.addInstruction` leaves labels and debug items on the shifted original location, and `MethodLocation.getLabels()` / `getDebugItems()` are modifiable.
- `TypeResolver` has no class index.
- The `after-throwing` path already installs a handler with `InstructionInjector.installTryCatch`.
- The generated `reset()` clears only the state and category flags, not user fields.
- `__EVENTNAME` is available in `@fail` handlers.
- `ErrorSummary` identity excludes the message.
- `RvErrorLog.unique_msg` includes the whole message.
- No module under `modules/*/src` keeps a list of code families, but `scripts/gh109_nobs_channel.py` counts every non-`NOBS` family as an accusation and `scripts/gh104_message_gate.py` requires `NOBS` under `NOT_OBSERVED` branches.
- `Property.GENERATED_TRUST_MANAGERS` exists with no producer or consumer, and `test_property_append_only` forbids removal or reordering of constants.
- The predicate-graph census test pins read and write counts.

## Architecture

```
                     rvsec (Java)                                          rv-android (Python)
┌──────────────────────────────────────────────────────┐   ┌─────────────────────────────────────────────┐
│ rvsec-core                                           │   │ rv-android-core  RvErrorLog.unique_msg      │
│   Property (+REPORTED_UPSTREAM)                      │   │   (identity_message strips vfp/vcls)        │
│   eh/Evidence (fingerprint, class names, suffix)     │   │ rv-coverage      logcat_parser              │
│          ▲                                           │   │   (vfp→value_fingerprint, vcls→value_class) │
│ rvsec-mop/jca_android/*.mop  ──generate──► monitor   │   │ rv-platform      ResultProcessorComponent   │
│   labels, marks, evidence, RSA; codes.csv (+label)   │   │   one pass, per-APK model, release          │
│          │ descriptor (.json)                        │   │ Platform  release on task finish            │
│          ▼                                           │   │ scripts/ gates (label column, census)       │
│ rvsec-instrumentation-dexlib2                        │   │ scripts/gh114_weave_sweep.py (A1–A4 counts) │
│   pointcut-engine  PointcutMatcher (A1)              │   │ data/jca_android records (RSA wart, A5)     │
│                    TypeResolver, AndroidClassIndex (A2 API, A4) │                                        │
│   advice-emitter   WrapperEmitter (A1 group, A2 expand, A5 wrapper) │                                     │
│   dex-mutator      InstructionInjector (A3), DexWeaver (A2 alias, A5 ctor) │                             │
│   cli              BatchRunner counters             │   └─────────────────────────────────────────────┘
└──────────────────────────────────────────────────────┘
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `PointcutMatcher.matchArgs` | Arity of every `args` form (A1, inline path) | `ArgsPC`, call parameter types | `Optional<Match>` |
| `WrapperEmitter` grouping loop | Exclude arity-incompatible advices per overload (A1, wrapper path) | advices, concrete overloads | wrapper groups, `advicesExcludedByArity` |
| `AndroidClassIndex.exists`, `.methodsInHierarchy` | Class existence (A4) and inherited-method lookup (A2) | internal name, method name | `boolean`, `List<MethodInfo>` |
| `WrapperEmitter.expandCallTarget` | Resolve inherited targets; count unresolved (A2) | pattern owner, name | `ConcreteCall`s, `wrapperTargetsUnresolved` |
| `DexWeaver.findWrapperReplacement` | Alias a wrapper to a framework subtype at the invoke (A2) | invoke reference | wrapper method |
| `InstructionInjector.insertBefore` | Move branch-target labels and the line-number entry to the block (A3) | method impl, index, plan | mutated impl |
| `TypeResolver.toDescriptor` | `Outer.Inner` → `Outer$Inner` (A4) | type name, imports, class lookup | descriptor |
| `WrapperEmitter.appendWrapperMethod`, `DexWeaver.applyPlan` (AFTER on ctor) | After-finally (A5) | advice group | wrapper with catch-all rethrow; ctor handler |
| `br.unb.cic.mop.eh.Evidence` | Evidence keys for `-NOBS-` envelopes | bound object | `" vfp='…'"` or `" vcls='…'"` |
| `jca_android/*.mop` | Labels, per-element credit, upstream mark, RSA | events | reports |
| `RvErrorLog.unique_msg` | Identity without evidence keys | record | key |
| `logcat_parser._apply_envelope` | Copy evidence keys to fields | envelope dict | record |
| `ResultProcessorComponent.execute` | One pass, per-APK model, release | completed tasks | six files |
| `Platform` (after `update_task`) | Release parsed state of a finished task | task | task with `None` fields |
| `scripts/gh114_weave_sweep.py` | Before/after counts for A1–A4 over any directory of instrumented APKs | APK dir, descriptor | CSV + totals |

## Mapping: Spec → Implementation → Test

| Requirement / Invariant | Implementation | Test |
|---|---|---|
| Positional Arity Is Enforced… / INV-INS-159 | `PointcutMatcher.matchArgs`; `WrapperEmitter` grouping `:307-314`, `argsArityCompatible` `:368-375` | `PointcutMatcherArgsTypeTest` (replaced binding-form tests), `WrapperMergeTest.anArityIncompatibleAdviceIsExcluded`, `ResultsJsonReportingTest` counter; sweep `arity_pairs_fired == 0` |
| Methods Inherited by Framework Subtypes… / INV-INS-160 | `AndroidClassIndex.methodsInHierarchy`; `WrapperEmitter.expandCallTarget`, `:285-293`; `DexWeaver.findWrapperReplacement` `:270-281` | `WrapperEmitterInheritedTargetTest`, `DexWeaverFrameworkSubtypeAliasTest`; sweep `framework_subtype_unwoven == 0` |
| Inserted Before-Block Not Bypassed / INV-INS-161 | `InstructionInjector.insertBefore` `:80-87` (+ helper `moveLocatedItems`) | `InstructionInjectorBranchTargetTest` (if, goto, packed/sparse switch, guard, line entry moved, try range unchanged); sweep `branch_target_hooks == 0` |
| Nested Types Resolve / INV-INS-162 | `TypeResolver.toDescriptor` `:87-107`, `resolveFqn` `:110-130`; `WrapperEmitter.resolveFqn` `:647-676`; `AndroidClassIndex.toInternal` `:223-225` | `TypeResolverTest.nestedImportedType`, `.nestedQualifiedType`, `.topLevelUnchanged`; sweep `keystore_entry_woven > 0` where the call exists |
| After Advice Runs on … Exceptional Completion / INV-INS-163 | `WrapperEmitter.appendWrapperMethod` `:782-801`; `DexWeaver.applyPlan` AFTER `:925-927` via `installTryCatch`; `AfterEmitter` javadoc | `WrapperAfterFinallyShapeTest`, `DexWeaverCtorAfterFinallyTest` |
| Label Codes… / INV-INS-164, INV-INS-165 | `jca_android/*.mop` `@fail` handlers and `-NOBS-` branches; `codes.csv` `label` | `scripts/gh104_message_gate.py` label check (`test_gh104_structural_gates.py`); `scripts/gh104_diff_harness.py` same-site comparison |
| Per-Element Credit of Trust-Manager Arrays | `TrustManagerFactorySpec.gtm1` `:218`, `SSLContextSpec.init` `:231-239`; `Property.GENERATED_TRUST_MANAGERS` | harness traces `tls_copied_array`, `tls_mixed_array` |
| Upstream-Refusal Mark | producer and consumer sites listed in the spec; `Property.REPORTED_UPSTREAM` | harness trace `pbe_stored_salt_chain`; census pins in `test_gh105_predicate_gates.py:1362-1395` |
| Evidence Keys / INV-INS-166 | `rvsec-core/.../eh/Evidence.java`; every `-NOBS-` `addError` | `EvidenceTest` (rvsec-core); message gate check "evidence only on NOBS" |
| RSA / INV-INS-167 | `RSAKeyGenParameterSpecSpec.mop:39`; `divergence_record.csv` row; `conformance_record.csv` | G-CONF in `test_gh104_structural_gates.py:488-501`; harness trace `rsa_3072`, `rsa_1024` |
| Violation Report Message Envelope (modified) | envelope grammar in `NEW_SPEC_CONVENTIONS.md:175-178`, `data/jca_android/README.md` | message gate |
| Event Granularity of unique_msg (modified) / INV-CORE-25, INV-CORE-63 | `rv_android_core/domain/log.py:157-160` | `test_log.py::test_unique_msg_strips_evidence_keys`, `::test_unique_msg_without_evidence_unchanged` |
| Evidence Keys Are Parsed… / INV-ANA-72 | `logcat_parser._apply_envelope` `:462-495`; `RvErrorLog` fields | `test_logcat_parser.py::test_evidence_keys_copied`, `::test_label_code_opaque` |
| Result Generation (modified) / INV-PLT-14, INV-PLT-15 | `ResultProcessorComponent.execute` `:200-262`, `_resolve_static_data` `:294-374` | `test_result_processor.py` (`read_static_analysis_files` once per APK; six files; memory-bound test); byte-identity check against `data/results/estudo02_regen/estudo02_00/` |
| A Finished Task Releases Its Parsed State / INV-PLT-38 | `platform.py:430` and `:465` | `test_platform_release.py::test_finished_task_releases_parsed_state` |

## Goals / Non-Goals

**Goals:**
- The DEX-native weaver matches, groups, inserts and completes advice as AspectJ does for the five measured cases, each proven by a before/after count or a bytecode-shape test.
- A `jca_android` report says which of six known situations produced it, without changing which sites report (except the per-element credit), and carries evidence for triage.
- A campaign export finishes within bounded memory with unchanged tables.
- All work splits into waves of independent subagent groups with one owner per file.

**Non-Goals:**
- Any change to `jca`, to `PredicateStore` comparison, to the expert rules, or to value lists other than RSA.
- Producers for `Certificate.getPublicKey`, `Cipher.unwrap`, `ECPublicKeySpec`.
- A per-site verdict catalogue, or any classification of evidence values.
- Streaming `results.json`.
- Re-running the evidence campaign, or updating experiment-local scripts under `experimento-*/`, with one exception: `experimento-gh104/scripts/gh104_gates.py` is the message gate run over any new campaign, and its G5 envelope pattern is adjusted to accept the evidence keys (decision of 2026-09-15). It is not moved to `scripts/`.

## Decisions

**D1 — Enforce arity at both weaving paths, keep the counter's name.** The arity rule goes into `PointcutMatcher.matchArgs` for all forms, and the wrapper grouping loop drops an incompatible advice for that overload. Two places, because the wrapper path does not call the matcher. Alternative: route wrapper grouping through the matcher. Rejected because the grouping works on expanded overloads and the matcher on a woven invoke; unifying them is a refactor this change does not need. `advicesExcludedByArity` keeps its name, so the Python parser (`rv-instrumentation-dexlib2`) and the phase-5 validators keep reading it.

**D2 — Resolve inherited targets by climbing the index, alias at the invoke.** `AndroidClassIndex` gains `methodsInHierarchy(owner, name, isStatic)` built on `walkAncestors`, and a public `exists(internalName)`. `expandCallTarget` falls back to it when the declared lookup is empty, and emits the wrapper with the pattern owner. `DexWeaver.findWrapperReplacement`, on an exact miss for a framework owner, looks for registered wrappers with the same name and parameters whose owner is assignable from the invoke's owner. It then registers one merged wrapper for that owner, carrying every matching advice, created lazily once per `(owner, name, descriptor)`. Alternative: enumerate every framework subtype of every wrapped owner from `android.jar` up front. Rejected because it multiplies wrappers for types no APK calls and needs a reverse index `AndroidClassIndex` does not have.

**D3 — Move branch targets and the line entry after insertion, by identity snapshot.** `insertBefore` snapshots, before `insertAll`, the labels located at the call that are referenced by an `if-*`/`goto*` instruction or a switch payload of the method, and the line-number debug items located at the call. It inserts the block, lets `installGuard` create its own skip label, and moves exactly the snapshot to the first inserted instruction (the guard prefix when present), through the modifiable `getLabels()` / `getDebugItems()` sets: remove, then add. Try-range labels and local-variable debug items are not in the snapshot and stay (decision of 2026-09-15: no measured effect, and exception ranges are not touched). Alternative: insert after the call and swap instructions. Rejected because it breaks `move-result` adjacency.

**D4 — `$` fallback driven by existence.** `TypeResolver` receives a `Predicate<String>` class-existence lookup: `AndroidClassIndex.exists` or'ed with APK class descriptors when available. `resolveFqn`/`toDescriptor` try the dotted name, then replace dots from the right with `$`. When no lookup is supplied (unit tests, validator), behaviour is unchanged. Alternative: a capitalisation heuristic. Rejected because it guesses.

**D5 — After-finally via the existing handler machinery, verified on the bytecode.**
- **Wrapper:** `try { r = call(args); } catch (Throwable t) { <monitor calls>; throw t; } <monitor calls>; return r;`, emitted as dexlib2 instructions with a catch-all try block around the invoke.
- **Constructor inline path:** `installTryCatch` with a handler plan that runs the monitor calls and rethrows.
- **Verification:** unit tests disassemble the generated wrapper and constructor site and assert the try range around the invoke, the handler's monitor calls with the same bound arguments, and the rethrow. No second weaver is run.

**D6 — Labels are numbers inside families; meaning lives in `codes.csv`.** New seventh column `label`. Existing rows get `violation`, `sequence` or `not-observed`. Numbering is the next free number per file and family (`NEW_SPEC_CONVENTIONS.md:167`), so two workers on different files cannot collide. The message gate gains two checks: every row carries a vocabulary label that agrees with its family, and evidence keys appear only on `-NOBS-` sites. `gh109_nobs_channel.py` keeps classifying by family and reports label counts beside it. Alternative: new families `DFLT`, `UPST`. Rejected because every family-based reader would count them as accusations.

**D7 — Creation and reuse facts are monitor fields; the handler reads `__EVENTNAME`.**
- **Creation:** each specification with a `@fail` whose automaton starts with creation events declares `boolean creationObserved = false;`, and the bodies of those events set it to `true`. The `@fail` emits `-ORDER-01` (`creation-unobserved`) when it is false.
- **Reuse:** `CipherSpec` and `MacSpec` also declare `operationFinished` (set in final-operation bodies) and `reuseObserved` (set in `@fail` when the failing event is an init event and `operationFinished` holds). The `@fail` emits `-ORDER-02` (`reuse-after-final`) when `reuseObserved` holds.
- **Survival:** `reset()` does not clear user fields, so both facts survive a failure.
- **Alternative rejected:** the JavaMOP `creation` modifier, which changes when monitors are created and therefore what is reported.

**D8 — One appended property for refusal; direct producers mark on value or origin reports.** `Property.REPORTED_UPSTREAM` is appended at the end of the enum.
- **Producers:** each direct producer site (constructed specs, factory products, the `KeyAgreement` secret) sets a local `boolean reported` whenever it calls `addError` with a value or origin code for the object it produces, and calls `ensure(REPORTED_UPSTREAM, product)` when `reported` holds. `-ORDER-` reports never mark.
- **Consumers:** in the `NOT_OBSERVED` branch, a consumer checks `validateAny(REPORTED_UPSTREAM, bound) == SATISFIED` before choosing the code.
- **Not marking:** `SecureRandomSpec` and `KeyGeneratorSpec` (decision of 2026-09-15); the `RANDOMIZED` readers keep `not-observed`.
- **Bridges:** `KeySpec.ge1` and `SecretKeySpec.e1` mark the returned clone when the key is marked.

**D9 — Per-element credit of trust-manager arrays through the existing element property.** `GENERATED_TRUST_MANAGERS` (existing, unused) marks trust-manager elements. `SSLContextSpec.init` credits the trust-manager array when the array is marked, or when it is non-empty and every element is marked. Key managers are out (decision of 2026-09-15). For `application-manager` the test is `element.getClass().getClassLoader() != TrustManager.class.getClassLoader()`, computed by `Evidence.isApplicationDefined(Object, Class<?>)`. This works whether the platform reports the boot loader as `null` or as `BootClassLoader`, because both sides come from the same runtime.

**D10 — Evidence helper in `rvsec-core`.** `Evidence.suffix(Object bound)` returns `" vfp='sha256:<16hex>'"` for a `byte[]`, `" vcls='<classes>'"` for a `TrustManager[]` (comma-joined element classes in array order), and `""` for anything else, `null` included (decision of 2026-09-15). Values pass through the specification's `q()` escaping rules: at most 512 characters, `'` escaped, and no `:::` (class names cannot contain it). Every `-NOBS-` envelope appends `Evidence.suffix(bound)` after `msg`. Alternative: compute the fingerprint in Python from logged bytes. Rejected because logging key material is worse than logging a truncated hash.

**D11 — Identity strips only trailing evidence.** `RvErrorLog.identity_message` removes a trailing ` vfp='…'` and ` vcls='…'` with a regex anchored at the end of the message that honours `\'` escapes. `unique_msg` uses it. `message` is unchanged, and so is the `errors.csv` header (INV-PLT-19, INV-CAN-25).

**D12 — Task-major export, taken from the proven offline regenerator.** `execute()` orders completed tasks by `(apk, tool, rep, timeout)`, writes headers through the existing `_generate_*_csv([])` calls, and loops tasks:
1. resolve the model through a one-entry `{apk: StaticAnalysisData}` cache;
2. set `task.static_data`;
3. run the four row writers and `_extract_task_data`;
4. release `task.repository` and `task.static_data`.

`performance.csv` runs after the loop. `_write_task_coverage_data` and `_write_task_summary_data` keep storing the reconstructed repository on the task during that task, so the other writers of the same task reuse it. The release happens after the last writer. `Platform` releases both fields right after `update_task` (`platform.py:430`, `:465`). Alternative: stream `results.json`. Deferred, because the measured bound already fits.

**D13 — RSA follows the sibling list with a wart row.** Edit `keySizes` and add the `divergence_record.csv` row (kind `oracle-wart`, task `gh114:9.2`) and the `conformance_record.csv` row update. If G-CONF compares the list literally against `RSAKeyGenParameterSpec.crysl:15`, the wart row is its warrant, exactly as for D-20.4.

**D14 — Waves and ownership.** One owner per file. `Property.java`, `codes.csv`, `divergence_record.csv`, `conformance_record.csv`, `predicate_graph.csv` and the census pins belong to the closing group of the specification wave (`NEW_SPEC_CONVENTIONS.md:198-207`). Specification workers emit codes in their `.mop` files and hand the new rows to the closing task as a fragment file each.

## API Design

### `AndroidClassIndex.exists(String internalName) -> boolean`
Pre: `internalName` uses `/` and `$`. Post: `true` iff `android.jar` has the class; cached. No exception for a malformed name (returns `false`).

### `AndroidClassIndex.methodsInHierarchy(String fqn, String name, boolean isStatic) -> List<MethodInfo>`
Post: declared methods of `fqn` if any, otherwise the first ancestor (superclass chain, then interfaces breadth-first) that declares `name`; empty when none. Never throws for an unknown class.

### `TypeResolver(List<String> imports, Predicate<String> classExists)`
Post: `toDescriptor("KeyStore.ProtectionParameter")` with `java.security.KeyStore` importable returns `Ljava/security/KeyStore$ProtectionParameter;`. The existing one-argument constructor delegates with `s -> false` (current behaviour).

### `InstructionInjector.insertBefore(MutableMethodImplementation impl, int index, EmitPlan plan)`
Post: INV-INS-161. The guard skip label stays at the call. Throws `IllegalArgumentException` for a non-BEFORE plan (unchanged).

### `br.unb.cic.mop.eh.Evidence`
```java
public final class Evidence {
    public static String suffix(Object bound);                       // "" | " vfp='sha256:…'" (byte[]) | " vcls='…'" (TrustManager[])
    public static boolean isApplicationDefined(Object element, Class<?> platformType);
    static String fingerprint(byte[] bytes);                         // "sha256:" + 16 lower-case hex
}
```
No checked exceptions. `MessageDigest.getInstance("SHA-256")` failure yields `""`.

### `RvErrorLog.identity_message -> str` (computed field, `rv_android_core/domain/log.py`)
Post: INV-CORE-63. `unique_msg` uses it.

### `RvErrorLog.value_fingerprint: str = ""`, `RvErrorLog.value_class: str = ""`
Pydantic fields with default `""`, excluded from `__eq__` and `__hash__` (identity stays `unique_msg`), and included in `to_dict()`.

### `ResultProcessorComponent.execute() -> None`
Post: INV-PLT-14, INV-PLT-15, INV-PLT-38. Rows follow the ordered task list.

## Data Flow

1. `.mop` → monitor generator → `MultiSpec_1MonitorAspect.json` and monitor sources → DEX-native weaver (A1–A5) → instrumented APK and `instrument_results.json` (counters).
2. On device: an event reaches the monitor, the body reads the store, and a label and evidence are selected → `ErrorCollector` (dedupe by `ErrorSummary`) → logcat `RVSEC` line.
3. `rv-coverage` parser → `RvErrorLog` (`code`, `event`, `value_fingerprint`, `value_class`, `message`) → `unique_msg` (without evidence).
4. `rv-platform`: task finishes → state released → at the end, `ResultProcessorComponent` makes one pass → `errors.csv` (message carries the evidence) and the other five files.
5. Analysis (outside `rv-android`) joins `errors.csv.code` with `codes.csv.label`.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `IllegalStateException` (wrapper rebind) | `DexWeaver.registerWrapper` | Unchanged for genuine rebinds; framework aliases use a separate lazy registration keyed by the invoke owner | Fail the weave with phase and cause (#112) |
| Unresolvable wrapper target | `expandCallTarget` | Count `wrapperTargetsUnresolved`, no wrapper | Visible in `instrument_results.json` |
| DEX write failure after A3/A5 insertion | `DexPool.writeTo` | `phase=dex_write`, exit 1 | Inspect the named DEX; the sweep lists the method |
| `NoSuchAlgorithmException` in `Evidence` | `MessageDigest.getInstance` | Omit `vfp` | None needed |
| Malformed evidence value | parser | Existing truncation and forbidden-char counters | Record kept |
| Static JSON absent for an APK | `_resolve_static_data` | Empty model for the APK, tasks counted unresolved once each | Coverage cells empty (INV-PLT-35) |
| Writer exception for one task | row writers | `write_errors` count, ERROR log (INV-PLT-32) | Continue with next writer and task |

## Risks / Trade-offs

- [A1 removes events a specification relied on implicitly] → The sweep compares per-wrapper event lists before and after and must show differences only in arity pairs; the differential harness replays all traces.
- [A3 moving the line entry changes the `source` of `before` reports, which is part of the device dedupe identity] → Declared as a discontinuity against earlier campaigns; the per-misuse count is unaffected.
- [A5 changes automaton state after throwing calls, and G-2/G-ORDER expectations may shift] → `conformance_record.csv` window reasons are rewritten and the gates rerun.
- [Creation facts in multi-parameter monitors: JavaMOP copies monitors when a binding is extended, and a copied `creationObserved` may come from a partial monitor] → Harness traces with two-parameter specifications (`KeyStoreSpec`, `SSLContextSpec`) assert the label. Where a copy is wrong the specification keeps `-ORDER-00`, recorded as a gate allowlist row.
- [Upstream mark on objects that are later legitimately re-produced] → The mark only relabels a `NOT_OBSERVED` answer. It never turns `SATISFIED` into a report, because `validate` runs first.
- [Evidence of the first report per identity per process only] → Documented. Triage compares across processes and installations, not within one.
- [Truncated hash of key material in logcat] → 64-bit prefix of SHA-256, accepted by the researcher. It identifies equality, not the key.
- [Per-element credit accepts an array whose elements came from a factory initialised with an attacker-chosen `KeyStore`] → `TrustManagerFactory.init` still reports on the store. The credit concerns the array, not the factory's input.
- [Byte identity with the offline regenerator depends on identical task ordering and `PYTHONHASHSEED`] → Order by the same key and fix the seed in the check. Row content, not order, is the contract where the seed matters (INV-PLT-19).
- [Parallel `.mop` workers colliding on shared records] → D14 ownership: fragments in, one closing task.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (Java) | A1 matcher and grouping, A2 hierarchy and alias, A3 label moves, A4 resolution, A5 wrapper and ctor handler shapes, `Evidence` | JUnit in `pointcut-engine`, `advice-emitter`, `dex-mutator`, `rvsec-core` | ~30 |
| Harness (Python + Java) | Labels keep the same reporting sites; label codes per situation; per-element credit; upstream chain; RSA | `scripts/gh104_diff_harness.py` with new traces in `data/gh104/traces` | ~12 new traces |
| Gates (pytest) | codes.csv label column, evidence only on NOBS, G-CONF with RSA wart, census pins, set size 47 | `tests/parity/test_gh104_structural_gates.py`, `test_gh105_predicate_gates.py`, `test_gh109_nobs_channel.py` | existing + ~4 |
| Unit (Python) | `identity_message`, parser evidence fields, export one-pass, release | pytest `--import-mode=importlib -o "addopts="` in `rv-android-core`, `rv-coverage`, `rv-platform` | ~12 |
| Static sweep | A1–A4 before (existing instrumented APKs) and after (APKs instrumented for the smoke) | `scripts/gh114_weave_sweep.py <apk_dir> <descriptor> <out.csv>` | 4 totals |
| Regeneration | Export byte identity on one container | `rv-platform run --process-results` against a copy of `estudo02_00` with `PYTHONHASHSEED=0` | 1 |
| Smoke (end) | Full pipeline with `jca_android`, dexlib2, a handful of APKs, one short tool run; labels and evidence present in `errors.csv`; export completes | `uv run rv-experiment run …` (platform manages the emulator) | 1 |

## Open Questions

- **The APK set for the smoke.** Criteria: at least one APK that reaches `SSLContext.init` through a TLS client, one with embedded BouncyCastle, one with a `Cipher.init` that is a branch target in the sweep, one with `KeyStore.getEntry`. The choice is made in task 15.2 from the before-sweep, not by name in this design.
- **Whether G-2/G-ORDER allowlist rows move after A5 and D7.** This is measured in the gates task, and each moved row gets a reason.
