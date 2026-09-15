# Tasks — gh114-weaver-fidelity-nobs-labels

GitHub Issue: #114

<!-- Subagent dispatch hints (subagent Gn = task group n)

     WAVE 0 — main window, serial, short: Group 1.
       It fixes the three shared contracts every parallel worker codes against:
       the AndroidClassIndex/TypeResolver API (pointcut-engine), the Property constants and the Evidence
       helper (rvsec-core), and the codes.csv `label` column with its gate check. Build the reactor once at the end.

     WAVE 1 — eleven independent subagents in parallel, one owner per file (design D14):
       G2  pointcut-engine          (PointcutMatcher, TypeResolver)                       A1 matcher, A4
       G3  advice-emitter           (WrapperEmitter, AfterEmitter)                         A1 grouping, A2 expand, A4 wiring, A5 wrapper
       G4  dex-mutator              (InstructionInjector, DexWeaver)                       A3, A2 alias, A5 ctor
       G5  rv-android scripts       (new scripts/gh114_weave_sweep.py, gh109_nobs_channel.py,
                                     experimento-gh104/scripts/gh104_gates.py)           before counts, label counts, envelope
       G6  jca_android TLS cluster  (TrustManagerFactorySpec, KeyManagerFactorySpec, SSLContextSpec)
       G7  jca_android key cluster  (SecretKeySpecSpec, SecretKeySpec, KeySpec, X509EncodedKeySpecSpec, KeyFactorySpec,
                                     SecretKeyFactorySpec, KeyAgreementSpec, KeyGeneratorSpec, SignatureSpec)
       G8  jca_android IV/random/op (IvParameterSpec, GCMParameterSpecSpec, IvChainJunction, PBEKeySpecSpec,
                                     SecureRandomSpec, CipherSpec, MacSpec)
       G9a jca_android remaining A  (AlgorithmParameterGeneratorSpec, AlgorithmParametersSpec, CertificateFactorySpec,
                                     CertPathTrustManagerParametersSpec, CipherInputStreamSpec, CipherOutputStreamSpec,
                                     DHGenParameterSpecSpec, DHParameterSpecSpec, DigestInputStreamSpec, DigestOutputStreamSpec,
                                     DSAParameterSpecSpec, ECGenParameterSpecSpec, ECParameterSpecSpec, HMACParameterSpecSpec)
       G9b jca_android remaining B  (KeyPairGeneratorSpec, KeyPairSpec, KeyStoreBuilderParametersSpec, KeyStoreSpec,
                                     MessageDigestSpec, MGF1ParameterSpecSpec, OAEPParameterSpecSpec, PBEParameterSpecSpec,
                                     PKIXBuilderParametersSpec, PKIXParametersSpec, RSAKeyGenParameterSpecSpec, SSLEngineSpec,
                                     SSLParametersSpec, TrustAnchorSpec)
       G10 rv-android-core + rv-coverage (identity_message, parser evidence fields, logcat buffer size)
       G11 rv-platform              (ResultProcessorComponent one pass, Platform release)
       Spec workers (G6–G9b) do NOT edit codes.csv, Property.java or data/jca_android records: each writes its new
       codes.csv rows to openspec/changes/gh114-weaver-fidelity-nobs-labels/fragments/codes_g<n>.csv and its
       harness traces to fragments/traces_g<n>/.
       Java workers (G2–G4) do not build the reactor and do not use `-am`: group 1 installed every module, so each
       runs `mvn -pl :<module> test` from rvsec-instrumentation-dexlib2 (JDK 21 prefix) against the installed jars of
       the others. With `-am` a worker would recompile a sibling module another worker is editing.
       The reactor build (`mvn clean install`) is run by the main window between waves.

     WAVE 2 — after WAVE 1 and one reactor build, in parallel:
       G12  cli counters and wiring  (needs G2, G3, G4)
       G13a codes, traces, harness   (tasks 13.1, 13.2, 13.5; needs G6–G9b)
       G13b records                  (task 13.3; needs G6–G9b; owns divergence/conformance records, coverage matrix,
                                      and the two Digest comment blocks)
       G13c census pins              (task 13.4; needs G6–G9b)
       G14  documentation            (needs G2–G4)
       G16a Python verification      (task 16.1; needs G10, G11; one subagent per module)
       main window: task 15.2 choice of smoke APKs (needs 5.3)
       Then main window: task 13.6 (monitor generation and all gates; needs G13a–c).

     WAVE 3 — main window, serial: G15 (build, instrument, after sweep, smoke), then 16.2–16.5.

     Critical path: 1 -> {2,3,4,6,7,8,9a,9b} -> {12,13a,13b,13c} -> 13.6 -> 15 -> 16.2.
     This change touches ~70 files across two repositories — use subagent orchestration (11 + 7 dispatches).

     Common conventions for every worker:
     - JDK: export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH
     - Reactor build (main window only): cd …/workspace-rv/rvsec && mvn clean install -DskipMopAgent -DskipTests
     - Python tests: uv run pytest <path> --import-mode=importlib -o "addopts="
     - Commit by path only: `git add -A -- <paths>` then `git commit --only -m … -- <paths>` (the index is shared
       with parallel workers; `git commit -- <paths>` alone leaves new files out). Message with refs #114, no Co-Authored-By trailer.
     - No comparison with the ajc weaver or any other weaver.
     - Nothing specific to a dataset in code, specs or comments; APKs are inputs only. P1–P4. -->

## 1. Shared Contracts (WAVE 0, main window)

- [x] 1.1 `pointcut-engine/.../AndroidClassIndex.java`: add public `exists(String internalName)` and `methodsInHierarchy(String fqn, String name, boolean isStatic)` on top of `load`/`walkAncestors` (design D2, D4, API Design); unit tests in `AndroidClassIndexHierarchyTest` (declared hit, inherited hit via interface, unknown class → empty/false)
- [x] 1.2 `pointcut-engine/.../TypeResolver.java`: add the two-argument constructor `TypeResolver(List<String> imports, Predicate<String> classExists)`; the one-argument constructor delegates with `s -> false`; no behaviour change yet (G2 implements the fallback)
- [x] 1.3 `rvsec-core/.../Property.java`: append `REPORTED_UPSTREAM` at the end of the enum with javadoc naming producers and consumers; run `tests/parity/test_gh101_specset_gates.py::test_property_append_only`
- [x] 1.4 `rvsec-core/src/main/java/br/unb/cic/mop/eh/Evidence.java`: `suffix(Object)`, `isApplicationDefined(Object, Class<?>)`, `fingerprint(byte[])` (design D10); `EvidenceTest` covering null, `byte[]`, `TrustManager[]` with application and platform classes, any other object (empty suffix), escaping of `'`
- [x] 1.5 `rvsec-mop/src/main/resources/jca_android/codes.csv`: add the seventh column `label`; fill existing rows (`-ORDER-` → `sequence`, `-NOBS-` → `not-observed`, every other family → `violation`)
- [x] 1.6 `scripts/gh104_message_gate.py`: add checks `label-vocabulary` (INV-INS-164 closed set, family agreement) and `evidence-only-on-nobs` (INV-INS-166); make every reader of `codes.csv` in `scripts/` (`gh109_nobs_channel.py`, `gh104_message_gate.py`, `gh104_diff_harness.py`) read columns by name so the new column is transparent; add tests in `tests/parity/test_gh104_structural_gates.py`
- [x] 1.7 Create `openspec/changes/gh114-weaver-fidelity-nobs-labels/fragments/README.md` stating the fragment format (codes rows with the seven columns; one trace file per scenario) used by G6–G9b and consumed by G13a
- [x] 1.8 Reactor build (JDK 21) green; commit group 1 by path (`refs #114`)

## 2. pointcut-engine: Arity and Nested Types (WAVE 1, subagent G2)

- [x] 2.1 `PointcutMatcher.matchArgs` (`:268-306`): apply the arity rule to every `args` form (INV-INS-159) before type checks; remove the early return at `:269-271`
- [x] 2.2 Replace `PointcutMatcherArgsTypeTest.bindingOnlyArgsAlwaysMatchesRegardlessOfActualArity` and `wildcardAndRestOnlyArgsHaveNoTypeConstraint` with tests of the spec scenario "the binding form is constrained on the inline path" (delete the old ones, P3)
- [x] 2.3 `TypeResolver.toDescriptor`/`resolveFqn`: dotted name → `$` fallback from the right using `classExists` (INV-INS-162). The construction sites are wired by G3 (`WrapperEmitter`) and G12 (`BatchRunner`), design D4
- [x] 2.4 `AndroidClassIndex.toInternal` (`:223-225`): accept binary names with `$` unchanged
- [x] 2.5 `TypeResolverTest`: `nestedImportedType`, `nestedQualifiedType`, `topLevelUnchanged`, `unknownNestedKeepsCurrentDescriptor`
- [x] 2.6 `mvn -pl :pointcut-engine test` green

## 3. advice-emitter: Grouping, Inherited Targets, After-Finally Wrapper (WAVE 1, subagent G3)

- [x] 3.1 `WrapperEmitter` grouping loop (`:307-314`): exclude an arity-incompatible advice from the overload's group; `advicesExcludedByArity` counts excluded pairs (INV-INS-159)
- [x] 3.2 Replace `WrapperMergeTest.anArityIncompatibleAdviceIsCountedAndStillFires` with `anArityIncompatibleAdviceIsExcluded` (spec scenario "a one-argument call fires only the one-argument event"); keep `anAdviceWithNoArgsClauseIsNeverCounted` and `aTrailingRestIsHonouredAsAtLeast`
- [x] 3.3 `WrapperEmitter.expandCallTarget` (`:401-478`): fall back to `AndroidClassIndex.methodsInHierarchy` when the declared lookup is empty; at `:285-293` count `wrapperTargetsUnresolved` instead of a silent `continue`; add the counter to `EmitResult` (`:91`); construct `TypeResolver` at `:232` with `AndroidClassIndex::exists` and route dotted names in `resolveFqn` (`:647-676`) through it (INV-INS-162, design D4); rewrite the INV-INS-122 comments at `:74-77`, `:295-306`, `:346` to current behaviour (INV-INS-159)
- [x] 3.4 `WrapperEmitterInheritedTargetTest`: `SecretKey+.getEncoded()` resolves; unresolvable target counted
- [x] 3.5 `WrapperEmitter.appendWrapperMethod` (`:782-801`): for `after` advices without `returning`/`throwing`, emit the catch-all try block that runs the monitor calls and rethrows, then the normal-path monitor calls and return (INV-INS-163, design D5)
- [x] 3.6 `AfterEmitter.java:9-13`: javadoc states what both paths now do (P4, no history)
- [x] 3.7 `WrapperAfterFinallyShapeTest`: the generated wrapper source has `try` around the call, `catch (Throwable t)` invoking the monitor calls with the same bound arguments, `throw t`, and the normal-path calls and return (design D5; the compiled shape is checked in 15.3)
- [x] 3.8 `mvn -pl :advice-emitter test` green (no `-am`)

## 4. dex-mutator: Branch Targets, Framework Aliases, Constructor After-Finally (WAVE 1, subagent G4)

- [ ] 4.1 `InstructionInjector.insertBefore` (`:80-87`): snapshot the branch/switch-target labels and the line-number debug items at the call, insert, install the guard, move the snapshot to the first inserted instruction; try-range labels and local-variable items stay (INV-INS-161, design D3)
- [ ] 4.2 `InstructionInjectorBranchTargetTest`: `if-*` target, `goto` target, packed and sparse switch case, guarded plan at a branch target, line entry moved to the block, try range beginning at the call unchanged
- [ ] 4.3 `DexWeaver.findWrapperReplacement` (`:270-281`): on an exact miss for a framework owner, alias to registered wrappers whose owner is assignable from it; lazy merged wrapper per `(owner, name, descriptor)` (INV-INS-160)
- [ ] 4.4 `DexWeaverFrameworkSubtypeAliasTest`: `PublicKey.getEncoded()` woven with `Key+` advice; no `IllegalStateException`
- [ ] 4.5 `DexWeaver.applyPlan` AFTER on constructor (`:925-927`): use `installTryCatch` with a catch-all `TryCatchSpec` built by `DexWeaver` and a handler that runs the monitor calls and rethrows (INV-INS-163)
- [ ] 4.6 `DexWeaverCtorAfterFinallyTest`: handler shape; existing `DexWeaverNestedTryCatchTest` and `DexWeaverIfGuardedAfterThrowingTest` still green
- [ ] 4.7 `mvn -pl :dex-mutator test` green (no `-am`)

## 5. Weave Sweep Script and Before Counts (WAVE 1, subagent G5)

- [ ] 5.1 New `scripts/gh114_weave_sweep.py <apk_dir> <descriptor.json> <out.csv>`: per APK counts of (a) wrappers of a one-parameter overload invoking an event whose advice declares more `args()` positions, (b) invokes whose owner is a framework subtype of a wrapped owner left unwoven, (c) hooked calls that are branch targets (logic of `experimento-estudo02/scripts/branch_target_hooks.py`, generalised and including switch targets), (d) `KeyStore.getEntry`/`setEntry` invokes and how many are woven; `dexdump` from `ANDROID_HOME`; totals trailer
- [ ] 5.2 `tests/scripts/test_gh114_weave_sweep.py` on a small synthetic DEX built in the test (no corpus file)
- [ ] 5.3 Run it over the instrumented APKs of the most recent `jca_android` instrumentation (directory passed on the command line) and store totals in `openspec/changes/gh114-weaver-fidelity-nobs-labels/evidence/sweep_before.csv`
- [ ] 5.4 Run `/rv-doc-code scripts/gh114_weave_sweep.py`
- [ ] 5.5 `scripts/gh109_nobs_channel.py`: report counts per `label` beside the family channel; tests
- [ ] 5.6 `experimento-gh104/scripts/gh104_gates.py`: `ENVELOPE_RE` (`:172-177`) accepts optional trailing ` vfp='…'` and ` vcls='…'` after `msg` and G5 rejects them on non-`NOBS` codes; confirm `codes.csv` is read by column name; test on synthetic envelopes with and without evidence keys

## 6. jca_android TLS Cluster (WAVE 1, subagent G6)

- [x] 6.1 `TrustManagerFactorySpec.mop`: `platform-default` code in the `NOT_OBSERVED` branch of `init` when `arg == null` (`:146-155`); `gtm1` marks every element with `GENERATED_TRUST_MANAGERS` (`:218`); `creationObserved` field and `-ORDER-01` in `@fail`; `Evidence.suffix` on every `-NOBS-` envelope
- [x] 6.2 `KeyManagerFactorySpec.mop`: `platform-default` code in the `NOT_OBSERVED` branch of `init` when `arg == null` (`:121-130`); `gkm1` unchanged; `-ORDER-01`; evidence
- [x] 6.3 `SSLContextSpec.mop` `init` (`:214-248`): per-element credit of the trust-manager array only, `platform-default` for each of the three `null`s, `application-manager` for the trust-manager array via `Evidence.isApplicationDefined`; `-ORDER-01`; evidence with trust-manager classes; update the decision comments to describe current behaviour (P4)
- [x] 6.4 Fragment `fragments/codes_g6.csv` with every new row (next free number per file and family) and traces `fragments/traces_g6/`: `tls_null_defaults`, `tls_copied_array`, `tls_mixed_array`, `tmf_init_before_getinstance`

## 7. jca_android Key-Material Cluster (WAVE 1, subagent G7)

- [ ] 7.1 `SecretKeySpecSpec.mop` `c1`/`c2`: `upstream-refused` and `random-key-material` codes in the `NOT_OBSERVED` branches (`:116-120`, `:182-186`) with the precedence of the spec; mark the constructed spec `REPORTED_UPSTREAM` whenever the site reports; `-ORDER-01`; evidence
- [ ] 7.2 `SecretKeySpec.mop` `e1` and `KeySpec.mop` `ge1`: mark the returned clone `REPORTED_UPSTREAM` when the key carries the mark
- [ ] 7.3 `X509EncodedKeySpecSpec.mop`, `KeyFactorySpec.mop` (`genPublic`, `genPrivate`), `SecretKeyFactorySpec.mop` (`gen`), `KeyAgreementSpec.mop` (`dophase`, `gs1`, `gs2`), `SignatureSpec.mop` (`i4`): consumer `upstream-refused` codes and producer marks (value or origin reports only) as listed in the spec; `-ORDER-01` in each `@fail` of these files and of `KeyGeneratorSpec.mop`, which gets no upstream mark; evidence on every `-NOBS-`
- [ ] 7.4 Fragment `fragments/codes_g7.csv` and traces `fragments/traces_g7/`: `random_bytes_as_key`, `ecdh_remote_peer_chain`, `keypair_generated_getpublic`

## 8. jca_android IV, Random and Operation Cluster (WAVE 1, subagent G8)

- [ ] 8.1 `IvParameterSpec.mop`, `GCMParameterSpecSpec.mop`, `PBEKeySpecSpec.mop`: producer marks on value or origin reports (their `RANDOMIZED` reads keep `not-observed`); `-ORDER-01`; evidence
- [ ] 8.2 `IvChainJunction.mop` `use`: `upstream-refused` for `PREPARED_IV`/`PREPARED_GCM` reads; evidence on every `-NOBS-` (no `@fail` in this file)
- [ ] 8.3 `SecureRandomSpec.mop`: `-ORDER-01` and evidence only (no upstream mark, no consumer label)
- [ ] 8.4 `CipherSpec.mop` and `MacSpec.mop`: `upstream-refused` in `i2`/`i1`; `operationFinished` set in final-operation bodies, `reuseObserved`, `-ORDER-02` (`reuse-after-final`) and `-ORDER-01` in `@fail` with the handler precedence of the spec; update `CipherSpec.mop:414-418` and `MacSpec.mop:423-434` comments to current behaviour
- [ ] 8.5 Fragment `fragments/codes_g8.csv` and traces `fragments/traces_g8/`: `pbe_stored_salt_chain`, `gcm_decrypt_received_nonce`, `cipher_reinit_after_dofinal`, `mac_reinit_after_dofinal`

## 9. jca_android Remaining Specifications and RSA (WAVE 1, subagents G9a and G9b)

- [x] 9.1 G9a, the fourteen files listed for G9a in the dispatch hints: `creationObserved` field set by its creation events and `-ORDER-01` in `@fail` (creation events as defined in design D7, refused twins included, `target`-bound events excluded); `Evidence.suffix` on every `-NOBS-` envelope
- [x] 9.2 G9a: fragment `fragments/codes_g9a.csv` (no traces)
- [x] 9.3 G9b, the fourteen files listed for G9b: the same as 9.1 (`SSLEngineSpec` has no creation event and gets no `-ORDER-01`)
- [x] 9.4 G9b: `RSAKeyGenParameterSpecSpec.mop:33-39`: `keySizes = Arrays.asList(2048, 3072, 4096)`; comment names both expert clauses, NIST SP 800-57 Part 1 and D-20.4, current behaviour only
- [x] 9.5 G9b: fragment `fragments/codes_g9b.csv` and traces `fragments/traces_g9b/`: `rsa_3072`, `rsa_1024`, `digest_clone_update`

## 10. Record Identity and Parser Evidence Fields (WAVE 1, subagent G10)

- [x] 10.1 `modules/rv-android-core/src/rv_android_core/domain/log.py`: `identity_message` computed field (anchored trailing `vfp`/`vcls`, escape-aware), `unique_msg` uses it; `value_fingerprint` and `value_class` fields excluded from equality (INV-CORE-25, INV-CORE-63)
- [x] 10.2 Tests in `modules/rv-android-core/tests/`: evidence stripped; message without evidence byte-identical key; `vfp=` inside a quoted `msg` not stripped
- [x] 10.3 `modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py` `_apply_envelope` (`:462-495`): copy `vfp`/`vcls` (INV-ANA-72)
- [x] 10.4 Tests in `modules/rv-coverage/tests/`: the three scenarios of the analysis spec
- [x] 10.5 `modules/rv-android-core/src/rv_android_core/constants.py`: `LOGCAT_BUFFER_SIZE = "16M"`; `util/android/logcat_manager.py` `start_capture` (`:183-210`): run `adb -s <serial> logcat -G <size>` before the clear and the capture, INFO with serial and size on success, WARNING on failure, capture continues (INV-CORE-64, design D15)
- [x] 10.6 Tests in `modules/rv-android-core/tests/`: command order `-G`, `-c`, capture with the capture command byte-identical to INV-CORE-37; sizing failure logs WARNING and capture starts
- [x] 10.7 Run `/rv-test-run rv-android-core` and `/rv-test-run rv-coverage`

## 11. Bounded Result Export (WAVE 1, subagent G11)

- [ ] 11.1 `modules/rv-platform/src/rv_platform/components/result_processor.py` `execute()` (`:200-262`): order completed tasks by `(apk, tool, rep, timeout)`, headers once, one task-major pass over the four row writers and `_extract_task_data`, release after the last writer, `performance.csv` after the loop (design D12)
- [ ] 11.2 `_resolve_static_data` (`:294-374`): one-entry per-APK cache; `read_static_analysis_files` once per APK; unresolved tasks recorded once each (INV-PLT-15)
- [ ] 11.3 `modules/rv-platform/src/rv_platform/platform.py` `:430` and `:465`: release `task.repository` and `task.static_data` after `update_task` (INV-PLT-38)
- [ ] 11.4 Update `test_result_processor.py` call-count assertions to once per APK; add the memory-bound scenario test (600 synthetic tasks) and `test_platform_release.py`
- [ ] 11.5 Byte-identity check: copy one container's `tasks.json`, logcats and static JSONs to a scratch results dir, run `uv run rv-platform run --process-results <dir>` with `PYTHONHASHSEED=0`, compare the six files with `data/results/estudo02_regen/estudo02_00/`; record the result in `evidence/export_identity.txt`
- [ ] 11.6 Run `/rv-test-run rv-platform`

## 12. CLI Counters and Resolver Wiring (WAVE 2, subagent G12; needs 2, 3 and 4)

- [ ] 12.1 `cli/.../BatchRunner.java`: construct `TypeResolver` at `:182` with `AndroidClassIndex::exists` (design D4); publish `wrapperTargetsUnresolved` (from `EmitResult`) in the counts map beside `wrappersGenerated`; rewrite the INV-INS-122 comment at `:223-229` to current behaviour
- [ ] 12.2 `ResultsJsonReportingTest`: `wrapperTargetsUnresolved` present; `advicesExcludedByArity` semantics test updated
- [ ] 12.3 `modules/rv-instrumentation-dexlib2` (Python) parser of `instrument_results.json` and its tests accept the new key (`tests/test_dexlib_instrumentation.py:901-958` pattern)
- [ ] 12.4 `mvn -pl :cli -am test` green; `/rv-test-run rv-instrumentation-dexlib2`

## 13. Specification-Set Closing (WAVE 2, subagents G13a, G13b, G13c; needs 6–9b; 13.6 in the main window after all three)

- [ ] 13.1 G13a: Merge `fragments/codes_g6.csv` … `codes_g9b.csv` into `jca_android/codes.csv` in file order; verify numbering is the next free per file and family
- [ ] 13.2 G13a: Move `fragments/traces_*` into `data/gh104/traces/` and add their expectations to the harness baseline; pin label `sequence` on the existing traces `CipherSpec-unsafe`, `MessageDigestSpec-md5`, `SSLContextSpec-getdefault-engine`, `PBEKeySpecSpec-forbidden-then-clear`, `KeyGeneratorSpec-unsafe` (design D7)
- [ ] 13.3 G13b: Records (design D13, D14), after the last `.mop` edit:
  - `.mop` comment blocks `DigestInputStreamSpec.mop:75-89`, `DigestOutputStreamSpec.mop:76-88` rewritten for after-finally (G13b edits them after G9a, first, so the refresh below sees them)
  - `divergence_record.csv`: run `scripts/gh104_divergence_record.py --refresh`, carry each previous reason to the new key of the same file and append the gh114 reason (kinds `message` and `predicate-store` only); rewrite `:376` in place for the RSA alignment (both clauses, NIST SP 800-57 Part 1, D-20.4, task `gh109:6.3;gh114:9.4`); addendum on `:269`; close `:45`, `:46` as repaired by gh114; rewrite `:105`, `:106` for after-finally
  - `conformance_record.csv`: new RSA key-size row; rewrite `:116`, `:117`, `:119`, `:120` (advice kind is plain `after`; guards stay `deferred-constant`, platform refuses the call) and amend `:118`, `:121` (`len < 0` on a throwing call)
  - re-emit `coverage_matrix.csv` with `scripts/gh109_coverage_matrix.py --emit`
  - `RVSEC_HOME=… uv run python scripts/gh104_divergence_record.py --check` exits 0
- [ ] 13.4 G13c: `tests/parity/test_gh105_predicate_gates.py:1362-1395`: restate the census pins with the new `REPORTED_UPSTREAM` and `GENERATED_TRUST_MANAGERS` sites; update `data/jca_android/predicate_graph.csv`
- [ ] 13.5 G13a, after 13.1–13.2: Run the specification trace harness (`scripts/gh104_diff_harness.py`, which replays monitor event traces against two snapshots of the specification set; no weaver involved) over all traces: same `(spec, event, class, method, location)` sets before and after except the trust-manager per-element credit traces; store the report in `evidence/labels_same_sites.txt`
- [ ] 13.6 Main window, after 13.1–13.5: Generate the monitor for `jca_android` (`uv run rv-monitor-generator generate --specs-dir …/jca_android --output <scratch>`) and run all gates: `uv run pytest tests/parity --import-mode=importlib -o "addopts="`; every moved G-2/G-ORDER allowlist row carries a reason

## 14. Documentation (WAVE 2, subagent G14; needs 2–4)

- [ ] 14.1 `data/jca_android/NEW_SPEC_CONVENTIONS.md` (envelope grammar with evidence keys, `label` column, numbering of label codes, precedence) and `data/jca_android/README.md` (codes table count, labels)
- [ ] 14.2 `rvsec-instrumentation-dexlib2/architecture.md` (`:176` INV-INS-122 → INV-INS-159; A2, A3, A5 behaviour; new counters) and `modules/rv-instrumentation-dexlib2/docs/architecture.md` (`:30`, `:316`), `modules/rv-instrumentation-dexlib2/CLAUDE.md` (`:111`)
- [ ] 14.3 `modules/rv-platform` docs/CLAUDE.md where result processing is described (one pass, release)

## 15. Build, Instrument, Measure and Smoke (WAVE 3, main window)

- [ ] 15.1 Reactor build (JDK 21) green, then `mvn test` for `rvsec-instrumentation-dexlib2` and `rvsec-core` without `-DskipTests`
- [ ] 15.2 In WAVE 2 (needs 5.3): choose the smoke APKs from `evidence/sweep_before.csv` by the design criteria (TLS client reaching `SSLContext.init`, embedded BouncyCastle, a hooked `Cipher.init` that is a branch target, a `KeyStore.getEntry` call). In WAVE 3, after 15.1: instrument them through the production path with `jca_android`
- [ ] 15.3 Run `scripts/gh114_weave_sweep.py` on the newly instrumented APKs; `evidence/sweep_after.csv` shows (a)=0, (b)=0, (c)=0 and (d) woven where the call exists; disassemble the monitor DEX of one smoke APK and confirm the after-finally handler in the `KeyAgreement.doPhase` or `SSLContext.init` wrapper (INV-INS-163); commit both sweeps
- [ ] 15.4 Smoke: `uv run rv-experiment run --tools ape --specification-set jca_android --apks-dir <smoke apks> --timeouts <budget chosen by the researcher> --name gh114_smoke` (the platform manages the emulator); confirm export completes, `errors.csv` has label codes, `vfp` on `-NOBS-` rows over byte arrays and `vcls` on trust-manager rows, `summary.csv` `mop_errors_unique` unaffected by evidence; the platform log shows the `logcat -G 16M` sizing for every task with no WARNING; record in `evidence/smoke.md`

## 16. Verification

- [ ] 16.1 WAVE 2, subagents G16a (one per module, needs G10, G11): `/rv-qa-lint-fix` then `/rv-verify` for `rv-android-core`, `rv-coverage`, `rv-platform`
- [ ] 16.2 WAVE 3, after G12: `/rv-qa-lint-fix rv-instrumentation-dexlib2` then `/rv-verify rv-instrumentation-dexlib2`
- [ ] 16.3 Invoke `/rv-code-reviewer` via Skill tool
- [ ] 16.4 Run `/opsx:verify gh114-weaver-fidelity-nobs-labels`
- [ ] 16.5 Archive note: the `## Invariants` sections of the four delta specs (INV-INS-159..167, INV-CORE-25 restated and INV-CORE-63, INV-ANA-72, INV-PLT-14/15 restated and INV-PLT-38) are synced by hand into the base specs at archive; the REMOVED arity requirement also removes INV-INS-122 from the base, and the base `## Data Contracts` line for `advicesExcludedByArity` (`openspec/specs/instrumentation/spec.md:248`) is re-anchored to INV-INS-159 by hand; the MODIFIED `The Java SE Specification Set Is Frozen` is synced by the skill
