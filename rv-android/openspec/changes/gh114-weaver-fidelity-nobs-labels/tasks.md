# Tasks — gh114-weaver-fidelity-nobs-labels

GitHub Issue: #114

<!-- Subagent dispatch hints (subagent Gn = task group n)

     WAVE 0 — main window, serial, short: Group 1.
       It fixes the three shared contracts every parallel worker codes against:
       the AndroidClassIndex/TypeResolver API (pointcut-engine), the Property constants and the Evidence
       helper (rvsec-core), and the codes.csv `label` column with its gate check. Build the reactor once at the end.

     WAVE 1 — ten independent subagents in parallel, one owner per file (design D14):
       G2  pointcut-engine          (PointcutMatcher, TypeResolver)                       A1 matcher, A4
       G3  advice-emitter           (WrapperEmitter, AfterEmitter)                         A1 grouping, A2 expand, A5 wrapper
       G4  dex-mutator              (InstructionInjector, DexWeaver)                       A3, A2 alias, A5 ctor
       G5  rv-android scripts       (new scripts/gh114_weave_sweep.py)                     before counts
       G6  jca_android TLS cluster  (TrustManagerFactorySpec, KeyManagerFactorySpec, SSLContextSpec)
       G7  jca_android key cluster  (SecretKeySpecSpec, SecretKeySpec, KeySpec, X509EncodedKeySpecSpec, KeyFactorySpec,
                                     SecretKeyFactorySpec, KeyAgreementSpec, KeyGeneratorSpec, SignatureSpec)
       G8  jca_android IV/random/op (IvParameterSpec, GCMParameterSpecSpec, IvChainJunction, PBEKeySpecSpec,
                                     SecureRandomSpec, CipherSpec, MacSpec)
       G9  jca_android remaining    (every other .mop with a @fail; RSAKeyGenParameterSpecSpec)
       G10 rv-android-core + rv-coverage (identity_message, parser evidence fields)
       G11 rv-platform              (ResultProcessorComponent one pass, Platform release)
       Spec workers (G6–G9) do NOT edit codes.csv, Property.java or data/jca_android records: each writes its new
       codes.csv rows to openspec/changes/gh114-weaver-fidelity-nobs-labels/fragments/codes_g<n>.csv and its
       harness traces to fragments/traces_g<n>/.
       Java workers (G2–G4) do not run the full reactor build; they run `mvn -pl :<module> -am test` from
       rvsec-instrumentation-dexlib2 (JDK 21 prefix). The reactor build is serialised between waves.

     WAVE 2 — after WAVE 1, three subagents in parallel:
       G12 cli counters             (needs G3, G4)
       G13 spec-set closing         (needs G6–G9; single owner of codes.csv, records, census pins, gates, traces)
       G14 documentation            (needs G2–G4, G13 vocabulary)

     WAVE 3 — main window, serial: G15 (build, instrument, after sweep, smoke), G16 (verification).

     Critical path: 1 -> {3,4,6,7,8} -> {12,13} -> 15 -> 16.
     This change touches ~70 files across two repositories — use subagent orchestration (10 + 3 dispatches).

     Common conventions for every worker:
     - JDK: export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH
     - Reactor build (main window only): cd …/workspace-rv/rvsec && mvn clean install -DskipMopAgent -DskipTests
     - Python tests: uv run pytest <path> --import-mode=importlib -o "addopts="
     - Commit by path only (git commit -- <paths>), message with refs #114, no Co-Authored-By trailer.
     - No comparison with the ajc weaver or any other weaver.
     - Nothing specific to a dataset in code, specs or comments; APKs are inputs only. P1–P4. -->

## 1. Shared Contracts (WAVE 0, main window)

- [ ] 1.1 `pointcut-engine/.../AndroidClassIndex.java`: add public `exists(String internalName)` and `methodsInHierarchy(String fqn, String name, boolean isStatic)` on top of `load`/`walkAncestors` (design D2, D4, API Design); unit tests in `AndroidClassIndexHierarchyTest` (declared hit, inherited hit via interface, unknown class → empty/false)
- [ ] 1.2 `pointcut-engine/.../TypeResolver.java`: add the two-argument constructor `TypeResolver(List<String> imports, Predicate<String> classExists)`; the one-argument constructor delegates with `s -> false`; no behaviour change yet (G2 implements the fallback)
- [ ] 1.3 `rvsec-core/.../Property.java`: append `REPORTED_UPSTREAM` at the end of the enum with javadoc naming producers and consumers; run `tests/parity/test_gh101_specset_gates.py::test_property_append_only`
- [ ] 1.4 `rvsec-core/src/main/java/br/unb/cic/mop/eh/Evidence.java`: `suffix(Object)`, `isApplicationDefined(Object, Class<?>)`, `fingerprint(byte[])` (design D10); `EvidenceTest` covering null, `byte[]`, `TrustManager[]` with application and platform classes, any other object (empty suffix), escaping of `'`
- [ ] 1.5 `rvsec-mop/src/main/resources/jca_android/codes.csv`: add the seventh column `label`; fill existing rows (`-ORDER-` → `sequence`, `-NOBS-` → `not-observed`, every other family → `violation`)
- [ ] 1.6 `scripts/gh104_message_gate.py`: add checks `label-vocabulary` (INV-INS-164 closed set, family agreement) and `evidence-only-on-nobs` (INV-INS-166); make every reader of `codes.csv` in `scripts/` (`gh109_nobs_channel.py`, `gh104_message_gate.py`, `gh104_diff_harness.py`) read columns by name so the new column is transparent; add tests in `tests/parity/test_gh104_structural_gates.py`
- [ ] 1.7 Create `openspec/changes/gh114-weaver-fidelity-nobs-labels/fragments/README.md` stating the fragment format (codes rows with the seven columns; one trace file per scenario) used by G5–G5 and consumed by G5
- [ ] 1.8 Reactor build (JDK 21) green; commit group 1 by path (`refs #114`)

## 2. pointcut-engine: Arity and Nested Types (WAVE 1, subagent G2)

- [ ] 2.1 `PointcutMatcher.matchArgs` (`:268-306`): apply the arity rule to every `args` form (INV-INS-159) before type checks; remove the early return at `:269-271`
- [ ] 2.2 Replace `PointcutMatcherArgsTypeTest.bindingOnlyArgsAlwaysMatchesRegardlessOfActualArity` and `wildcardAndRestOnlyArgsHaveNoTypeConstraint` with tests of the spec scenario "the binding form is constrained on the inline path" (delete the old ones, P3)
- [ ] 2.3 `TypeResolver.toDescriptor`/`resolveFqn`: dotted name → `$` fallback from the right using `classExists` (INV-INS-162); wire `AndroidClassIndex::exists` where `TypeResolver` is constructed in the weaving path (`DexWeaver`, `WrapperEmitter`, `MonitorInvokeBuilder`, `AfterThrowingEmitter` callers)
- [ ] 2.4 `AndroidClassIndex.toInternal` (`:223-225`): accept binary names with `$` unchanged
- [ ] 2.5 `TypeResolverTest`: `nestedImportedType`, `nestedQualifiedType`, `topLevelUnchanged`, `unknownNestedKeepsCurrentDescriptor`
- [ ] 2.6 `mvn -pl :pointcut-engine test` green

## 3. advice-emitter: Grouping, Inherited Targets, After-Finally Wrapper (WAVE 1, subagent G3)

- [ ] 3.1 `WrapperEmitter` grouping loop (`:307-314`): exclude an arity-incompatible advice from the overload's group; `advicesExcludedByArity` counts excluded pairs (INV-INS-159)
- [ ] 3.2 Replace `WrapperMergeTest.anArityIncompatibleAdviceIsCountedAndStillFires` with `anArityIncompatibleAdviceIsExcluded` (spec scenario "a one-argument call fires only the one-argument event"); keep `anAdviceWithNoArgsClauseIsNeverCounted` and `aTrailingRestIsHonouredAsAtLeast`
- [ ] 3.3 `WrapperEmitter.expandCallTarget` (`:401-478`): fall back to `AndroidClassIndex.methodsInHierarchy` when the declared lookup is empty; at `:285-293` count `wrapperTargetsUnresolved` instead of a silent `continue`; add the counter to `EmitResult` (`:91`)
- [ ] 3.4 `WrapperEmitterInheritedTargetTest`: `SecretKey+.getEncoded()` resolves; unresolvable target counted
- [ ] 3.5 `WrapperEmitter.appendWrapperMethod` (`:782-801`): for `after` advices without `returning`/`throwing`, emit the catch-all try block that runs the monitor calls and rethrows, then the normal-path monitor calls and return (INV-INS-163, design D5)
- [ ] 3.6 `AfterEmitter.java:9-13`: javadoc states what both paths now do (P4, no history)
- [ ] 3.7 `WrapperAfterFinallyShapeTest`: baksmali of a generated wrapper shows the try range around the invoke, the handler invoking the monitor calls with the same bound arguments and `throw` of the caught register (spec scenario "the woven wrapper carries the handler")
- [ ] 3.8 `mvn -pl :advice-emitter -am test` green

## 4. dex-mutator: Branch Targets, Framework Aliases, Constructor After-Finally (WAVE 1, subagent G4)

- [ ] 4.1 `InstructionInjector.insertBefore` (`:80-87`): snapshot the branch/switch-target labels and the line-number debug items at the call, insert, install the guard, move the snapshot to the first inserted instruction; try-range labels and local-variable items stay (INV-INS-161, design D3)
- [ ] 4.2 `InstructionInjectorBranchTargetTest`: `if-*` target, `goto` target, packed and sparse switch case, guarded plan at a branch target, line entry moved to the block, try range beginning at the call unchanged
- [ ] 4.3 `DexWeaver.findWrapperReplacement` (`:270-281`): on an exact miss for a framework owner, alias to registered wrappers whose owner is assignable from it; lazy merged wrapper per `(owner, name, descriptor)` (INV-INS-160)
- [ ] 4.4 `DexWeaverFrameworkSubtypeAliasTest`: `PublicKey.getEncoded()` woven with `Key+` advice; no `IllegalStateException`
- [ ] 4.5 `DexWeaver.applyPlan` AFTER on constructor (`:925-927`): use `installTryCatch` with a handler that runs the monitor calls and rethrows (INV-INS-163)
- [ ] 4.6 `DexWeaverCtorAfterFinallyTest`: handler shape; existing `DexWeaverNestedTryCatchTest` and `DexWeaverIfGuardedAfterThrowingTest` still green
- [ ] 4.7 `mvn -pl :dex-mutator -am test` green

## 5. Weave Sweep Script and Before Counts (WAVE 1, subagent G5)

- [ ] 5.1 New `scripts/gh114_weave_sweep.py <apk_dir> <descriptor.json> <out.csv>`: per APK counts of (a) wrappers of a one-parameter overload invoking an event whose advice declares more `args()` positions, (b) invokes whose owner is a framework subtype of a wrapped owner left unwoven, (c) hooked calls that are branch targets (logic of `experimento-estudo02/scripts/branch_target_hooks.py`, generalised and including switch targets), (d) `KeyStore.getEntry`/`setEntry` invokes and how many are woven; `dexdump` from `ANDROID_HOME`; totals trailer
- [ ] 5.2 `tests/scripts/test_gh114_weave_sweep.py` on a small synthetic DEX built in the test (no corpus file)
- [ ] 5.3 Run it over the instrumented APKs of the most recent `jca_android` instrumentation (directory passed on the command line) and store totals in `openspec/changes/gh114-weaver-fidelity-nobs-labels/evidence/sweep_before.csv`
- [ ] 5.4 Run `/rv-doc-code scripts/gh114_weave_sweep.py`

## 6. jca_android TLS Cluster (WAVE 1, subagent G6)

- [ ] 6.1 `TrustManagerFactorySpec.mop`: `platform-default` code in the `NOT_OBSERVED` branch of `init` when `arg == null` (`:146-155`); `gtm1` marks every element with `GENERATED_TRUST_MANAGERS` (`:218`); `creationObserved` field and `-ORDER-01` in `@fail`; `Evidence.suffix` on every `-NOBS-` envelope
- [ ] 6.2 `KeyManagerFactorySpec.mop`: `platform-default` code in the `NOT_OBSERVED` branch of `init` when `arg == null` (`:121-130`); `gkm1` unchanged; `-ORDER-01`; evidence
- [ ] 6.3 `SSLContextSpec.mop` `init` (`:214-248`): per-element credit of the trust-manager array only, `platform-default` for each of the three `null`s, `application-manager` for the trust-manager array via `Evidence.isApplicationDefined`; `-ORDER-01`; evidence with trust-manager classes; update the decision comments to describe current behaviour (P4)
- [ ] 6.4 Fragment `fragments/codes_g6.csv` with every new row (next free number per file and family) and traces `fragments/traces_g6/`: `tls_null_defaults`, `tls_copied_array`, `tls_mixed_array`, `tmf_init_before_getinstance`

## 7. jca_android Key-Material Cluster (WAVE 1, subagent G7)

- [ ] 7.1 `SecretKeySpecSpec.mop` `c1`/`c2`: `upstream-refused` and `random-key-material` codes in the `NOT_OBSERVED` branches (`:116-120`, `:182-186`) with the precedence of the spec; mark the constructed spec `REPORTED_UPSTREAM` whenever the site reports; `-ORDER-01`; evidence
- [ ] 7.2 `SecretKeySpec.mop` `e1` and `KeySpec.mop` `ge1`: mark the returned clone `REPORTED_UPSTREAM` when the key carries the mark
- [ ] 7.3 `X509EncodedKeySpecSpec.mop`, `KeyFactorySpec.mop` (`genPublic`, `genPrivate`), `SecretKeyFactorySpec.mop` (`gen`), `KeyAgreementSpec.mop` (`dophase`, `gs1`, `gs2`), `SignatureSpec.mop` (`i4`): consumer `upstream-refused` codes and producer marks (value or origin reports only) as listed in the spec; `-ORDER-01` in each `@fail` of these files and of `KeyGeneratorSpec.mop`, which gets no upstream mark; evidence on every `-NOBS-`
- [ ] 7.4 Fragment `fragments/codes_g7.csv` and traces `fragments/traces_g7/`: `random_bytes_as_key`, `ecdh_remote_peer_chain`, `keypair_generated_getpublic`

## 8. jca_android IV, Random and Operation Cluster (WAVE 1, subagent G8)

- [ ] 8.1 `IvParameterSpec.mop`, `GCMParameterSpecSpec.mop`, `PBEKeySpecSpec.mop`: producer marks on value or origin reports (their `RANDOMIZED` reads keep `not-observed`); `-ORDER-01`; evidence
- [ ] 8.2 `IvChainJunction.mop` `use`: `upstream-refused` for `PREPARED_IV`/`PREPARED_GCM` reads (no `@fail` in this file)
- [ ] 8.3 `SecureRandomSpec.mop`: `-ORDER-01` and evidence only (no upstream mark, no consumer label)
- [ ] 8.4 `CipherSpec.mop` and `MacSpec.mop`: `upstream-refused` in `i2`/`i1`; `operationFinished` set in final-operation bodies, `reuseObserved`, `-ORDER-02` (`reuse-after-final`) and `-ORDER-01` in `@fail` with the handler precedence of the spec; update `CipherSpec.mop:414-418` and `MacSpec.mop:423-434` comments to current behaviour
- [ ] 8.5 Fragment `fragments/codes_g8.csv` and traces `fragments/traces_g8/`: `pbe_stored_salt_chain`, `gcm_decrypt_received_nonce`, `cipher_reinit_after_dofinal`, `mac_reinit_after_dofinal`

## 9. jca_android Remaining Specifications and RSA (WAVE 1, subagent G9)

- [ ] 9.1 Every `.mop` of `jca_android` with a `@fail` not owned by G6–G8: `creationObserved` field set by its creation events and `-ORDER-01` in `@fail` (list from `grep -l '@fail'` minus the G5–G5 files; `SSLEngineSpec` has no creation event and gets none)
- [ ] 9.2 `RSAKeyGenParameterSpecSpec.mop:33-39`: `keySizes = Arrays.asList(2048, 3072, 4096)`; comment names both expert clauses, NIST SP 800-57 Part 1 and D-20.4, current behaviour only
- [ ] 9.3 Fragment `fragments/codes_g9.csv` and traces `fragments/traces_g9/`: `rsa_3072`, `rsa_1024`, `digest_clone_update`

## 10. Record Identity and Parser Evidence Fields (WAVE 1, subagent G10)

- [ ] 10.1 `modules/rv-android-core/src/rv_android_core/domain/log.py`: `identity_message` computed field (anchored trailing `vfp`/`vcls`, escape-aware), `unique_msg` uses it; `value_fingerprint` and `value_class` fields excluded from equality (INV-CORE-25, INV-CORE-63)
- [ ] 10.2 Tests in `modules/rv-android-core/tests/`: evidence stripped; message without evidence byte-identical key; `vfp=` inside a quoted `msg` not stripped
- [ ] 10.3 `modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py` `_apply_envelope` (`:462-495`): copy `vfp`/`vcls` (INV-ANA-72)
- [ ] 10.4 Tests in `modules/rv-coverage/tests/`: the three scenarios of the analysis spec
- [ ] 10.5 Run `/rv-test-run rv-android-core` and `/rv-test-run rv-coverage`

## 11. Bounded Result Export (WAVE 1, subagent G11)

- [ ] 11.1 `modules/rv-platform/src/rv_platform/components/result_processor.py` `execute()` (`:200-262`): order completed tasks by `(apk, tool, rep, timeout)`, headers once, one task-major pass over the four row writers and `_extract_task_data`, release after the last writer, `performance.csv` after the loop (design D12)
- [ ] 11.2 `_resolve_static_data` (`:294-374`): one-entry per-APK cache; `read_static_analysis_files` once per APK; unresolved tasks recorded once each (INV-PLT-15)
- [ ] 11.3 `modules/rv-platform/src/rv_platform/platform.py` `:430` and `:465`: release `task.repository` and `task.static_data` after `update_task` (INV-PLT-38)
- [ ] 11.4 Update `test_result_processor.py` call-count assertions to once per APK; add the memory-bound scenario test (600 synthetic tasks) and `test_platform_release.py`
- [ ] 11.5 Byte-identity check: copy one container's `tasks.json`, logcats and static JSONs to a scratch results dir, run `uv run rv-platform run --process-results <dir>` with `PYTHONHASHSEED=0`, compare the six files with `data/results/estudo02_regen/estudo02_00/`; record the result in `evidence/export_identity.txt`
- [ ] 11.6 Run `/rv-test-run rv-platform`

## 12. CLI Counters (WAVE 2, subagent G12; needs 3 and 4)

- [ ] 12.1 `cli/.../BatchRunner.java`: publish `wrapperTargetsUnresolved` (from `EmitResult`) in the counts map beside `wrappersGenerated`
- [ ] 12.2 `ResultsJsonReportingTest`: `wrapperTargetsUnresolved` present; `advicesExcludedByArity` semantics test updated
- [ ] 12.3 `modules/rv-instrumentation-dexlib2` (Python) parser of `instrument_results.json` and its tests accept the new key (`tests/test_dexlib_instrumentation.py:901-958` pattern)
- [ ] 12.4 `mvn -pl :cli -am test` green; `/rv-test-run rv-instrumentation-dexlib2`

## 13. Specification-Set Closing (WAVE 2, subagent G13; needs 6–9)

- [ ] 13.1 Merge `fragments/codes_g6..g9.csv` into `jca_android/codes.csv` in file order; verify numbering is the next free per file and family
- [ ] 13.2 Move `fragments/traces_*` into `data/gh104/traces/` and add their expectations to the harness baseline
- [ ] 13.3 `data/jca_android/divergence_record.csv`: `oracle-wart` row for the RSA list (both clauses, NIST SP 800-57 Part 1, D-20.4, task `gh114:9.2`); `conformance_record.csv`: RSA row and the window-clause reasons of the 58 `after` events rewritten for after-finally semantics
- [ ] 13.4 `tests/parity/test_gh105_predicate_gates.py:1362-1395`: restate the census pins with the new `REPORTED_UPSTREAM` and `GENERATED_TRUST_MANAGERS` sites; update `data/jca_android/predicate_graph.csv`
- [ ] 13.5 `scripts/gh109_nobs_channel.py`: report counts per `label` beside the family channel; tests
- [ ] 13.6 `experimento-gh104/scripts/gh104_gates.py`: `ENVELOPE_RE` (`:172-177`) accepts optional trailing ` vfp='…'` and ` vcls='…'` after `msg` and G5 rejects them on non-`NOBS` codes; confirm `codes.csv` is read by column name; run it over a harness output that carries evidence keys
- [ ] 13.7 Generate the monitor for `jca_android` (`uv run rv-monitor-generator generate --specs-dir …/jca_android --output <scratch>`) and run all gates: `uv run pytest tests/parity --import-mode=importlib -o "addopts="`; every moved G-2/G-ORDER allowlist row carries a reason
- [ ] 13.8 Run the specification trace harness (`scripts/gh104_diff_harness.py`, which replays monitor event traces against two snapshots of the specification set; no weaver involved) over all traces: same `(spec, event, class, method, location)` sets before and after except the trust-manager per-element credit traces; store the report in `evidence/labels_same_sites.txt`

## 14. Documentation (WAVE 2, subagent G14)

- [ ] 14.1 `data/jca_android/NEW_SPEC_CONVENTIONS.md` (envelope grammar with evidence keys, `label` column, numbering of label codes, precedence) and `data/jca_android/README.md` (codes table count, labels)
- [ ] 14.2 `rvsec-instrumentation-dexlib2/architecture.md` (`:176` INV-INS-122 → INV-INS-159; A2, A3, A5 behaviour; new counters) and `modules/rv-instrumentation-dexlib2/docs/architecture.md` (`:30`, `:316`), `modules/rv-instrumentation-dexlib2/CLAUDE.md` (`:111`)
- [ ] 14.3 `modules/rv-platform` docs/CLAUDE.md where result processing is described (one pass, release)

## 15. Build, Instrument, Measure and Smoke (WAVE 3, main window)

- [ ] 15.1 Reactor build (JDK 21) green, then `mvn test` for `rvsec-instrumentation-dexlib2` and `rvsec-core` without `-DskipTests`
- [ ] 15.2 Choose the smoke APKs from `evidence/sweep_before.csv` by the design criteria (TLS client reaching `SSLContext.init`, embedded BouncyCastle, a hooked `Cipher.init` that is a branch target, a `KeyStore.getEntry` call); instrument them through the production path with `jca_android`
- [ ] 15.3 Run `scripts/gh114_weave_sweep.py` on the newly instrumented APKs; `evidence/sweep_after.csv` shows (a)=0, (b)=0, (c)=0 and (d) woven where the call exists; commit both sweeps
- [ ] 15.4 Smoke: `uv run rv-experiment run --tools ape --specification-set jca_android --apks-dir <smoke apks> --timeouts <budget chosen by the researcher> --name gh114_smoke` (the platform manages the emulator); confirm export completes, `errors.csv` has label codes, `vfp` on `-NOBS-` rows over byte arrays and `vcls` on trust-manager rows, `summary.csv` `mop_errors_unique` unaffected by evidence; record in `evidence/smoke.md`

## 16. Verification

- [ ] 16.1 Run `/rv-qa-lint-fix rv-android-core`, `/rv-qa-lint-fix rv-coverage`, `/rv-qa-lint-fix rv-platform`, `/rv-qa-lint-fix rv-instrumentation-dexlib2`
- [ ] 16.2 Run `/rv-verify rv-android-core`, `/rv-verify rv-coverage`, `/rv-verify rv-platform`, `/rv-verify rv-instrumentation-dexlib2`
- [ ] 16.3 Invoke `/rv-code-reviewer` via Skill tool
- [ ] 16.4 Run `/opsx:verify gh114-weaver-fidelity-nobs-labels`
- [ ] 16.5 Archive note: the `## Invariants` sections of the four delta specs (INV-INS-159..167, INV-CORE-25 restated and INV-CORE-63, INV-ANA-72, INV-PLT-14/15 restated and INV-PLT-38) are synced by hand into the base specs at archive; the REMOVED arity requirement also removes INV-INS-122 from the base
