# Design — gh114 Weaver Fidelity, Labelled Non-Observation Reports and Bounded Result Export

GitHub Issue: #114

## Context

The proposal groups three repairs that share one gate, the next campaign, and no code. They touch two repositories and eight modules, and the implementation budget is short, so this design is organised around what can be done in parallel without two workers editing the same file.

- **Weaver** (`rvsec/rvsec-android/rvsec-instrumentation-dexlib2`, Java 21, Maven). Five divergences from AspectJ (A1–A5). FR02, NFR06.
- **Specification set** (`rvsec/rvsec-mop/src/main/resources/jca_android`, 47 `.mop`; `rvsec/rvsec-core` for `Property` and helpers). Seven label codes, refused creation twins, per-element manager credit, the upstream-refusal mark, evidence keys, the RSA list. FR03, FR13.
- **Consumers** (`rv-android`): `rv-android-core` (`RvErrorLog.unique_msg`, `LogcatManager` buffer size), `rv-coverage` (logcat parser), `scripts/` gates and `tests/parity/`, `data/jca_android/` records. FR11, FR13.
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
│   eh/Evidence (fingerprint, class names, keysFor)    │   │ rv-coverage      logcat_parser              │
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
| `DexWeaver.findWrapperReplacement` | Alias a framework-subtype invoke to the most specific supertype wrapper (A2) | invoke reference | wrapper method, `wrappersAliasedToSubtype`, `wrapperAliasesUnmerged` |
| `InstructionInjector.insertBefore` | Move branch-target labels and the line-number entry to the block (A3) | method impl, index, plan | mutated impl |
| `TypeResolver.toDescriptor` | `Outer.Inner` → `Outer$Inner` (A4) | type name, imports, class lookup | descriptor |
| `WrapperEmitter.appendWrapperMethod`, `DexWeaver.applyPlan` (AFTER on ctor) | After-finally (A5) | advice group | wrapper with catch-all rethrow; ctor handler |
| `br.unb.cic.mop.eh.Evidence.keysFor` | Evidence keys for `-NOBS-` envelopes | bound object | `" vfp='…'"` or `" vcls='…'"` |
| `jca_android/*.mop` | Labels, refused creation twins, per-element credit, upstream mark, RSA | events | reports |
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
| After Advice Runs on … Exceptional Completion / INV-INS-163 | `WrapperEmitter.appendWrapperMethod` `:782-801`; `DexWeaver.applyPlan` AFTER `:925-927` via `installTryCatch`; `AfterEmitter` javadoc | `WrapperAfterFinallyShapeTest` (source shape), `DexWeaverCtorAfterFinallyTest`; monitor DEX disassembly in task 15.3 |
| Label Codes… / INV-INS-164, INV-INS-165 | `jca_android/*.mop` `@fail` handlers, `-NOBS-` branches and refused creation twins; `codes.csv` `label` | `scripts/gh104_message_gate.py` label check (`test_gh104_structural_gates.py`); `scripts/gh104_diff_harness.py` same-site comparison; harness traces of the two-argument refused route |
| Per-Element Credit of Trust-Manager Arrays | `TrustManagerFactorySpec.gtm1` `:218`, `SSLContextSpec.init` `:231-239`; `Property.GENERATED_TRUST_MANAGERS` | harness traces `tls_copied_array`, `tls_mixed_array` |
| Upstream-Refusal Mark | producer and consumer sites listed in the spec; `Property.REPORTED_UPSTREAM` | harness trace `pbe_stored_salt_chain`; census pins in `test_gh105_predicate_gates.py:1362-1395` |
| Evidence Keys / INV-INS-166 | `rvsec-core/.../eh/Evidence.java`; every `-NOBS-` `addError` | `EvidenceTest` (rvsec-core); message gate check "evidence only on NOBS" |
| RSA / INV-INS-167 | `RSAKeyGenParameterSpecSpec.mop:39`; `divergence_record.csv:376` rewritten, `:269` addendum; `conformance_record.csv` key-size row; `coverage_matrix.csv` re-emitted | harness traces `rsa_3072`, `rsa_1024`; `test_gh109_coverage_matrix` |
| Violation Report Message Envelope (modified) | envelope grammar in `NEW_SPEC_CONVENTIONS.md:175-178`, `data/jca_android/README.md` | message gate |
| Event Granularity of unique_msg (modified) / INV-CORE-25, INV-CORE-63 | `rv_android_core/domain/log.py:157-160` | `test_log.py::test_unique_msg_strips_evidence_keys`, `::test_unique_msg_without_evidence_unchanged` |
| Evidence Keys Are Parsed… / INV-ANA-72 | `logcat_parser._apply_envelope` `:462-495`; `RvErrorLog` fields | `test_logcat_parser.py::test_evidence_keys_copied`, `::test_label_code_opaque` |
| Result Generation (modified) / INV-PLT-14, INV-PLT-15 | `ResultProcessorComponent.execute` `:200-262`, `_resolve_static_data` `:294-374` | `test_result_processor.py` (`read_static_analysis_files` once per APK; six files; memory-bound test); byte-identity check against `data/results/estudo02_regen/estudo02_00/` |
| The Device Log Buffer Is Sized Before Capture / INV-CORE-64 | `rv_android_core/util/android/logcat_manager.py` `start_capture` (`:183-210`); `LOGCAT_BUFFER_SIZE` in `rv_android_core/constants.py` | `test_logcat_manager.py::test_buffer_sized_before_clear_and_capture`, `::test_sizing_failure_does_not_stop_capture` |
| A Finished Task Releases Its Parsed State / INV-PLT-38 | `platform.py:430` and `:465` | `test_platform_release.py::test_finished_task_releases_parsed_state` |

## Goals / Non-Goals

**Goals:**
- The DEX-native weaver matches, groups, inserts and completes advice as AspectJ does for the five measured cases, each proven by a before/after count or a bytecode-shape test.
- A `jca_android` report says which of seven known situations produced it, without changing which sites report (except the per-element credit), and carries evidence for triage.
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

**D2 — Resolve inherited targets by climbing the index, alias at the invoke.** `AndroidClassIndex` gains `methodsInHierarchy(owner, name, isStatic)` built on `walkAncestors`, and a public `exists(internalName)`. `expandCallTarget` falls back to it when the declared lookup is empty, and emits the wrapper with the pattern owner; when several `Owner+` patterns admit the same framework subtype, the emitter merges their advices into the subtype's wrapper. `DexWeaver.findWrapperReplacement`, on an exact miss for a framework owner, aliases the invoke to the registered wrapper of the most specific supertype with the same name and parameters, which already carries every advice whose pattern admits that supertype, and counts it in `wrappersAliasedToSubtype`. When the candidate owners are unrelated (no single most specific supertype), the invoke is left unwoven and counted in `WeaveReport.wrapperAliasesUnmerged`, which the CLI publishes beside `wrapperTargetsUnresolved`; none is expected in `jca_android`. Alternative: enumerate every framework subtype of every wrapped owner from `android.jar` up front. Rejected because it multiplies wrappers for types no APK calls and needs a reverse index `AndroidClassIndex` does not have.

**D3 — Move branch targets and the line entry after insertion, by identity snapshot.** `insertBefore` snapshots, before `insertAll`, the labels located at the call that are referenced by an `if-*`/`goto*` instruction or a switch payload of the method, and the line-number debug items located at the call. It inserts the block, lets `installGuard` create its own skip label, and moves exactly the snapshot to the first inserted instruction (the guard prefix when present), through the modifiable `getLabels()` / `getDebugItems()` sets: remove, then add. Try-range labels and local-variable debug items are not in the snapshot and stay (decision of 2026-09-15: no measured effect, and exception ranges are not touched). Known limit, unchanged by this decision: a method whose register frame grows or whose try ranges are rebuilt (an after-throwing handler, a `!holdsLock` guard, a constructor after-finally handler) loses all its line-number debug items when the weaver rebuilds it, so the line move has no effect in such a method. Alternative: insert after the call and swap instructions. Rejected because it breaks `move-result` adjacency.

**D4 — `$` fallback driven by existence.** `TypeResolver` receives a `Predicate<String>` class-existence lookup: `AndroidClassIndex.exists` or'ed with APK class descriptors when available. `resolveFqn`/`toDescriptor` try the dotted name, then replace dots from the right with `$`. The lookup takes an internal name (`/` and `$`). It is supplied where the weaving path constructs `TypeResolver`: `WrapperEmitter.java:232`, whose `resolveFqn` (`:647-676`) then routes dotted names through the resolver, and `BatchRunner.java:182`, whose resolver `DexWeaver`, `MonitorInvokeBuilder` and `AfterThrowingEmitter` receive. When no lookup is supplied (unit tests, `BaksmaliDiffer` in the validator), behaviour is unchanged. Alternative: a capitalisation heuristic. Rejected because it guesses.

**D5 — After-finally via the existing handler machinery, verified on the bytecode.**
- **Wrapper:** `try { r = call(args); } catch (Throwable t) { <monitor calls>; throw t; } <monitor calls>; return r;`, emitted as Java source in `mop/MonitorWrappers.java` (`WrapperEmitter.java:24-25`, `:339`) and compiled with the monitor by `monitor-builder` (javac, then d8).
- **Constructor inline path:** `installTryCatch` with a handler plan that runs the monitor calls and rethrows. `DexWeaver` builds the catch-all `TryCatchSpec` the call requires. The path applies to a plain `after` on a constructor only; every constructor event of `jca_android` is `after … returning`, so it weaves nothing in that set today.
- **Verification:** `advice-emitter` tests assert the wrapper source shape (`try`, `catch (Throwable t)`, the monitor calls with the same bound arguments, `throw t`); `dex-mutator` tests disassemble the constructor site and assert the try range, the handler's monitor calls and the rethrow. The compiled wrapper is checked by disassembling the monitor DEX of a smoke APK (task 15.3). No second weaver is run.

**D6 — Labels are numbers inside families; meaning lives in `codes.csv`.** New seventh column `label`. Existing rows get `violation`, `sequence` or `not-observed`. Numbering is the next free number per file and family (`NEW_SPEC_CONVENTIONS.md:167`), so two workers on different files cannot collide. The message gate gains two checks: every row carries a vocabulary label that agrees with its family, and evidence keys appear only on `-NOBS-` sites. `gh109_nobs_channel.py` keeps classifying by family and reports label counts beside it. Alternative: new families `DFLT`, `UPST`. Rejected because every family-based reader would count them as accusations.

**D7 — Creation and reuse facts are monitor fields; the handler reads `__EVENTNAME`.**
- **Creation:** each specification with a `@fail` whose automaton starts with creation events declares `boolean creationObserved = false;`, and the bodies of those events set it to `true`. The `@fail` emits `-ORDER-01` (`creation-unobserved`) when it is false.
- **Creation event:** every constructor or static-factory event that binds the monitored parameter through `returning(...)`, whatever its condition or transition, refused and forbidden twins included (for example `CipherSpec.g3`, `SSLContextSpec.getDefault`, `PBEKeySpecSpec.f1`/`f2`). An event bound through `target(...)` is never a creation event (`DigestInputStreamSpec.on`, `KeyAgreementSpec.gs3`).
- **Refused creation twins:** a `condition(...)` that is false runs no body, so a creation call guarded only by an admitting allow-list test would leave `creationObserved` false when the value is refused, and its later failure would read `creation-unobserved` although the creation ran in woven code. Every allow-list-guarded creation therefore has a refused twin (the negated guard) for every overload it admits. The one-argument twins exist (`CipherSpec.g3`, `KeyGeneratorSpec.g3`, `KeyManagerFactorySpec.g3`, `KeyStoreSpec.g2`, `MacSpec.g3`, `MessageDigestSpec.g4`, `SecureRandomSpec.g4`/`g5`, `KeyPairGeneratorSpec.g3`/`g4`). The two-argument twin is added (decision of 2026-09-15):
  - as a new event with the file's two-argument pointcut form and the negated guard, placed beside the one-argument twin in the automaton (the Kleene prefix of the `ere`, or the `unsafeAlg` transitions of the `fsm`), in `MessageDigestSpec`, `MacSpec`, `KeyStoreSpec`, `KeyGeneratorSpec` and `KeyManagerFactorySpec`;
  - in `CipherSpec`, which is at the 17-event ceiling (INV-INS-154), by widening `g3` to `call(public static Cipher Cipher.getInstance(String, ..)) && args(transformation, ..)`, whose body only records the creation;
  - in `TrustManagerFactorySpec` and `SignatureSpec`, whose one-argument creation is unguarded, as a new event leading where the first use fails as it does without the twin (an `fsm` state with no transitions; an `ere` Kleene prefix before `(g1 | g2)`).
  A new twin records the creation facts and nothing else: it does not report and does not write the fields other events read (`KeyGeneratorSpec.g3` writes `currentAlgorithmInstance`; its two-argument twin does not). The first use of such an object fails at the same event as before, so no reported site changes; only the handler's code does.
- **Refused creation:** the specifications with a refused creation — the twins above and the forbidden creations that report `FORB` (`PBEKeySpecSpec.f1`/`f2`, `SSLContextSpec.getDefault`) — declare `boolean creationRefused = false;`, set to `true` in those bodies. The `@fail` emits the `creation-refused` code when it holds. An ordering failure of such an object is the consequence of the refusal the specification already reported, or of a value it refuses: in the evidence campaign 16,429 report lines (11.7 %) were `-ORDER-00` failures sharing the misuse with a value code, and in `MessageDigestSpec`, `MacSpec` and `CipherSpec` every such failure was the cascade of a refused `getInstance`. In `KeyStoreSpec` the type is accused only at `getKey`, so a refused store never read by `getKey` has the `creation-refused` report as its only report.
- **Reuse:** `CipherSpec` and `MacSpec` also declare `operationFinished` (set in final-operation bodies) and `reuseObserved` (set in `@fail` when the failing event is an init event and `operationFinished` holds). The `@fail` emits `-ORDER-02` (`reuse-after-final`) when `reuseObserved` holds.
- **Precedence in `@fail`:** `creation-unobserved`, then `creation-refused`, then `reuse-after-final`, then `sequence`. A refused creation sets `creationObserved` as well, so the first test separates the two creation labels.
- **Survival:** `reset()` does not clear user fields, so all these facts survive a failure, and every label persists on the monitor.
- **Unreachable handlers:** in the fifteen specifications whose automaton is a single construction (`ere : c1`, `c1 | c2`, …) `@fail` cannot fire; their `-ORDER-` rows are unreachable and exist for the bijection between sites and `codes.csv` rows. None of them has a refused creation.
- **Alternative rejected:** the JavaMOP `creation` modifier, which changes when monitors are created and therefore what is reported.

**D8 — One appended property for refusal; direct producers mark on value or origin reports.** `Property.REPORTED_UPSTREAM` is appended at the end of the enum.
- **Producers:** each direct producer site (constructed specs, factory products, the `KeyAgreement` secret) sets a local `boolean reported` whenever it calls `addError` with a value or origin code for the object it produces, and calls `ensure(REPORTED_UPSTREAM, product)` when `reported` holds. `-ORDER-` reports never mark.
- **Consumers:** in the `NOT_OBSERVED` branch, a consumer checks `validateAny(REPORTED_UPSTREAM, bound) == SATISFIED` before choosing the code.
- **Not marking:** `SecureRandomSpec` and `KeyGeneratorSpec` (decision of 2026-09-15); the `RANDOMIZED` readers keep `not-observed`.
- **Bridges:** `KeySpec.ge1` and `SecretKeySpec.e1` mark the returned clone when the key is marked.
- **Lists are not closed:** the producers and consumers are the ones the specification names (decision of 2026-09-15). Other producers that report on their product do not mark, and other `-NOBS-` sites keep `not-observed`. Two cases are kept outside the lists on purpose: `MacSpec.i2`, whose key read is the same as `i1`'s, is not a consumer, and `PBEKeySpecSpec.f1`/`f2`, which report `FORB` on the spec they construct, do not mark it.
- **Label selection reads:** `SecretKeySpecSpec.c1`/`c2` read `validate(RANDOMIZED, keyMaterial)` only to choose `random-key-material`; whether they report is still decided by `PREPARED_KEY_MATERIAL`. `SecretKeySpec.crysl` does not require `randomized`, and the predicate-graph row of that read carries this reason.

**D9 — Per-element credit of trust-manager arrays through the existing element property.** `GENERATED_TRUST_MANAGERS` (existing, unused) marks trust-manager elements. `SSLContextSpec.init` credits the trust-manager array when the array is marked, or when the array read answers `NOT_OBSERVED` and the array is non-empty and every element is marked; a `VIOLATED` answer is never upgraded (no site withdraws `GENERATED_TRUST_MANAGER`, so the distinction does not arise on any program today). Key managers are out (decision of 2026-09-15). For `application-manager` the test is `element.getClass().getClassLoader() != TrustManager.class.getClassLoader()`, computed by `Evidence.isApplicationDefined(Object, Class<?>)`. This works whether the platform reports the boot loader as `null` or as `BootClassLoader`, because both sides come from the same runtime.

**D10 — Evidence helper in `rvsec-core`.** `Evidence.keysFor(Object bound)` returns `" vfp='sha256:<16hex>'"` for a `byte[]`, `" vcls='<classes>'"` for a `TrustManager[]` (comma-joined element classes in array order), and `""` for anything else, `null` included (decision of 2026-09-15). Values pass through the specification's `q()` escaping rules: at most 512 characters, `'` escaped, and no `:::` (class names cannot contain it). Every `-NOBS-` envelope appends `Evidence.keysFor(bound)` after `msg`. The name is not `suffix`, which is a reserved token of the JavaMOP grammar (a specification modifier): a `.mop` that calls a method of that name does not parse. Alternative: compute the fingerprint in Python from logged bytes. Rejected because logging key material is worse than logging a truncated hash.

**D11 — Identity strips only trailing evidence.** `RvErrorLog.identity_message` removes a trailing ` vfp='…'` and ` vcls='…'` with a regex anchored at the end of the message that honours `\'` escapes. `unique_msg` uses it. `message` is unchanged, and so is the `errors.csv` header (INV-PLT-19, INV-CAN-25).

**D12 — Task-major export, taken from the proven offline regenerator.** `execute()` orders completed tasks by `(apk, tool, rep, timeout)`, writes headers through the existing `_generate_*_csv([])` calls, and loops tasks:
1. resolve the model through a one-entry `{apk: StaticAnalysisData}` cache;
2. set `task.static_data`;
3. run the four row writers and `_extract_task_data`;
4. release `task.repository` and `task.static_data`.

`performance.csv` runs after the loop. `_write_task_coverage_data` and `_write_task_summary_data` keep storing the reconstructed repository on the task during that task, so the other writers of the same task reuse it. The release happens after the last writer. `Platform` releases both fields right after `update_task` (`platform.py:430`, `:465`). Alternative: stream `results.json`. Deferred, because the measured bound already fits.

**D13 — RSA follows the sibling list; the existing wart row is rewritten.** Edit `keySizes`. `divergence_record.csv:376` is already the `oracle-wart` row for the two RSA clauses and today records that neither is edited; it is rewritten in place to record the alignment, with task `gh109:6.3;gh114:9.4` (no second row: the recorder does not detect two conflicting rows). Row `:269`, which says 1024 stays in the list, gains an addendum. `conformance_record.csv` gains a key-size row (`:123` covers the exponent only), and `coverage_matrix.csv` is re-emitted with `scripts/gh109_coverage_matrix.py --emit` because it copies row 376's summary. G-CONF checks only that a backing row of the right kind exists, so the behaviour is checked by the harness traces `rsa_3072` and `rsa_1024`.

**D14 — Waves and ownership.** One owner per file. `codes.csv`, `divergence_record.csv`, `conformance_record.csv`, `predicate_graph.csv` and the census pins belong to the closing group of the specification wave (`NEW_SPEC_CONVENTIONS.md:198-207`). Specification workers emit codes in their `.mop` files and hand the new rows to the closing task as a fragment file each.

The divergence-record gate (`scripts/gh104_divergence_record.py`, run by `tests/parity/test_gh104_specset_gates.py:77-91`) keys every changed hunk of a seeded `.mop` by its content, so every label, evidence or mark edit in the 22 seeded files invalidates the row of the hunk it lands in. The closing group updates the record once, after the last `.mop` edit: `--refresh` lists the live hunks, a small script carries each previous reason to the new key of the same file and appends the gh114 reason, and `--check` runs with `RVSEC_HOME` set (without it the test skips instead of failing). Only existing kinds are used: `message` for label codes, evidence keys and handler fields, `predicate-store` for the upstream mark and the per-element credit. Workers do not write divergence rows.

**D15 — Size the device log buffer before each capture.** `start_capture` runs `adb -s <serial> logcat -G 16M`, then the existing `logcat -c`, then the unchanged capture command. Measured on the campaign image: 2 MiB per buffer, 46 s of history, `logd` already pruning the application's entries after one minute. A separate command keeps INV-CORE-37 byte-identical; running it on every capture covers a rebooted device. A failure logs a WARNING and the capture proceeds. Alternative: fewer coverage lines at start-up. Rejected because it changes what coverage records.

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
    public static String keysFor(Object bound);                      // "" | " vfp='sha256:…'" (byte[]) | " vcls='…'" (TrustManager[])
    public static boolean isApplicationDefined(Object element, Class<?> platformType);
    static String fingerprint(byte[] bytes);                         // "sha256:" + 16 lower-case hex
}
```
No checked exceptions. `MessageDigest.getInstance("SHA-256")` failure yields `""`.

### `RvErrorLog.identity_message -> str` (computed field, `rv_android_core/domain/log.py`)
Post: INV-CORE-63. `unique_msg` uses it.

### `RvErrorLog.value_fingerprint: str = ""`, `RvErrorLog.value_class: str = ""`
Pydantic fields with default `""`, excluded from `__eq__` and `__hash__` (identity stays `unique_msg`), and excluded from `to_dict()`: the values are already inside `message`, so `results.json` keeps its keys and the byte-identity check of D12 holds.

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
| `logcat -G` fails | `LogcatManager.start_capture` | WARNING with serial and size | Capture proceeds with the device's default buffer |
| Static JSON absent for an APK | `_resolve_static_data` | Empty model for the APK, tasks counted unresolved once each | Coverage cells empty (INV-PLT-35) |
| Writer exception for one task | row writers | `write_errors` count, ERROR log (INV-PLT-32) | Continue with next writer and task |

## Risks / Trade-offs

- [A1 removes events a specification relied on implicitly] → The sweep compares per-wrapper event lists before and after and must show differences only in arity pairs; the differential harness replays all traces.
- [A3 moving the line entry changes the `source` of `before` reports, which is part of the device dedupe identity] → Declared as a discontinuity against earlier campaigns; the per-misuse count is unaffected.
- [A5 changes automaton state after throwing calls, and G-2/G-ORDER expectations may shift] → The record rows whose reason assumed the skipped advice are rewritten (task 13.3) and the gates rerun. Event bodies also run on a throwing call, so their predicate writes and staged values happen there too.
- [Creation facts in multi-parameter monitors: JavaMOP copies monitors when a binding is extended, and a copied `creationObserved` may come from a partial monitor] → Harness traces with two-parameter specifications (`KeyStoreSpec`, `SSLContextSpec`) assert the label. Where a copy is wrong the specification keeps `-ORDER-00`, recorded as a gate allowlist row.
- [Upstream mark on objects that are later legitimately re-produced] → The mark only relabels a `NOT_OBSERVED` answer. It never turns `SATISFIED` into a report, because `validate` runs first.
- [Evidence of the first report per identity per process only] → Documented. Triage compares across processes and installations, not within one.
- [Truncated hash of key material in logcat] → 64-bit prefix of SHA-256, accepted by the researcher. It identifies equality, not the key.
- [Per-element credit accepts an array whose elements came from a factory initialised with an attacker-chosen `KeyStore`] → `TrustManagerFactory.init` still reports on the store. The credit concerns the array, not the factory's input.
- [Byte identity with the offline regenerator depends on identical task ordering and `PYTHONHASHSEED`] → Order by the same key and fix the seed in the check. Row content, not order, is the contract where the seed matters (INV-PLT-19).
- [Parallel `.mop` workers colliding on shared records] → D14 ownership: fragments in, one closing task.
- [An analysis that discounts `creation-refused` loses a refused `KeyStore` never read by `getKey`, whose type is accused nowhere else] → Stated in D7 and in the label's `codes.csv` description; the label says the creation was refused, which is itself the accusation.
- [A refused twin adds a monitor call on a creation call already wrapped by its admitted sibling] → The twin's body only assigns two fields; the call is on the same wrapper, so no new wrapper is generated.
- [Readers of `unique_msg` outside this change] → `scripts/rv_oracle_common.py:114-117` and `modules/aperv-tool/.../violations.py:448-468` read its seventh part, which no longer carries the evidence keys; no count they compute moves. Noted, not edited.
- [Pre-existing defect outside this change] → `TaskStorage.get_pending_tasks()` uses a `TaskState.ARCHIVED` that does not exist; nothing calls it and a skipped test hides it. Noted, not edited.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (Java) | A1 matcher and grouping, A2 hierarchy and alias, A3 label moves, A4 resolution, A5 wrapper and ctor handler shapes, `Evidence` | JUnit in `pointcut-engine`, `advice-emitter`, `dex-mutator`, `rvsec-core` | ~30 |
| Harness (Python + Java) | Labels keep the same reporting sites; label codes per situation; refused two-argument creation; per-element credit; upstream chain; RSA | `scripts/gh104_diff_harness.py` with new traces in `data/gh104/traces`; `TraceRunner` accepts `trustmanagers(...)` (a fresh `TrustManager[]` of bound names) and `applicationtrustmanager` (a manager of an application class) so a mixed array replays. The trace grammar has no byte-array literal, so the stable fingerprint of constant key material is covered by `EvidenceTest` instead of a trace | ~15 new traces |
| Gates (pytest) | codes.csv label column, evidence only on NOBS, G-CONF with RSA wart, census pins, set size 47 | `tests/parity/test_gh104_structural_gates.py`, `test_gh105_predicate_gates.py`, `test_gh109_nobs_channel.py` | existing + ~4 |
| Unit (Python) | `identity_message`, parser evidence fields, export one-pass, release | pytest `--import-mode=importlib -o "addopts="` in `rv-android-core`, `rv-coverage`, `rv-platform` | ~12 |
| Static sweep | A1–A4 before (existing instrumented APKs) and after (APKs instrumented for the smoke) | `scripts/gh114_weave_sweep.py <apk_dir> <descriptor> <out.csv>` | 4 totals |
| Regeneration | Export byte identity on one container (the `timestamp` column of `performance.csv`, which records when the file was generated, excluded) | `rv-platform run --process-results` against a copy of `estudo02_00` with `PYTHONHASHSEED=0` | 1 |
| Smoke (end) | Full pipeline with `jca_android`, dexlib2, a handful of APKs, one short tool run; labels and evidence present in `errors.csv`; export completes | `uv run rv-experiment run …` (platform manages the emulator) | 1 |

## Open Questions

- **The APK set for the smoke.** Criteria: at least one APK that reaches `SSLContext.init` through a TLS client, one with embedded BouncyCastle, one with a `Cipher.init` that is a branch target in the sweep, one with `KeyStore.getEntry`. The choice is made in task 15.2 from the before-sweep, not by name in this design.
- **Whether G-2/G-ORDER allowlist rows move after A5 and D7.** This is measured in the gates task, and each moved row gets a reason.
