# Weaver Fidelity, Labelled Non-Observation Reports and Bounded Result Export

GitHub Issue: #114

## Why

A complete campaign with the `jca_android` set and the DEX-native weaver (11 tools × 163 APKs × 3 repetitions × 3 budgets) was read report by report (`experimento-estudo02/docs/20260915_reanalise_acusacoes.md`, summarised in `20260915_relatorio_executivo.md`, Appendix A). Of its 27,068 per-run misuses, 23.2 % are what the CrySL rules forbid; 64.3 % are correct code the monitor cannot observe, reported under the `-NOBS-` family and counted as misuse; about 3 % are produced by defects of the weaver itself. The same campaign's final export was killed by the kernel for memory in all ten containers, and its tables exist only because they were regenerated offline.

Three things follow, and all three are properties of the tool rather than of that corpus. First, the weaver diverges from AspectJ semantics in five measured places, fabricating reports in some and losing them in others. Second, the `-NOBS-` family says "not observed" for situations that are structurally different — a `null` that requests the platform default, a fresh array around a factory-issued trust manager, an object whose origin was already refused upstream, an object whose creation happened outside woven code — so no analysis can separate them without reading each application's source. Third, the result export holds every task's parsed logcat and static model in memory at once and cannot finish a campaign of realistic size. Every rule this change introduces is a statement about the JCA/Android API or about the weaver; none refers to an application, a library or a dataset, and the change must hold for any set of APKs.

This is the gate before the next campaign. It builds on #112 (archived): `instr-cli` exits 1 and keeps the cause when a weave fails, which is what makes a DEX broken by the instruction-insertion repairs visible while they are verified.

## What Changes

**Weaver (`rvsec-instrumentation-dexlib2`), each repair counted before and after over the instrumented APKs:**

- **A1 — positional arity is enforced.** An untyped `args(...)` clause currently matches a call of any arity, so `getInstance(String)` also fires the two-argument event, and three specifications (`TrustManagerFactory`, `KeyManagerFactory`, `SecureRandom`) report invalid sequences for correct code. The measurement INV-INS-122 introduced (`advicesExcludedByArity`) becomes the filter it was designed to judge. **BREAKING** for reported counts: removes artefactual `-ORDER-` reports.
- **A2 — inherited methods on framework subtypes are woven.** A call whose owner is a framework subtype that inherits the matched method without redeclaring it (`SecretKey.getEncoded()`) gets no wrapper, and the drop is silent. Resolution climbs the framework type hierarchy, and every dropped wrapper is counted in the results JSON.
- **A3 — a before-hook is not bypassed by a branch.** Instructions inserted before a matched call leave the labels that target the call on the original instruction, so control arriving by a branch skips the monitor. Branch and switch targets, and the line-number entry of the call, are moved to the first inserted instruction; exception ranges are not touched; the `if(...)` guard, which relies on the current behaviour, keeps working.
- **A4 — nested types resolve.** `KeyStore.ProtectionParameter` is resolved as a package, so `KeyStore.getEntry`/`setEntry` are never woven.
- **A5 — `after` runs when the call throws.** The inline and wrapper paths skip an `after` advice when the matched call throws; AspectJ runs it (`after` = after-finally), and `AfterEmitter`'s own contract promises it. Both paths gain the handler-and-rethrow shape the `after-throwing` path already builds. **BREAKING** for reported counts: adds reports on throwing calls in 58 of the 202 events of `jca_android`.

**Specification set `jca_android` — labels, not verdicts.** No new code family is introduced: every label is a new numbered code inside the `-NOBS-` or `-ORDER-` family, described by a new `label` column of `codes.csv`, so every consumer that separates not-observed from accusation keeps working. With one exception stated below, no reported site stops being reported; only the code changes, so that an analysis can tell a violation from a limit of observation. The exception is the per-element trust-manager credit, which accepts an array whose every element a factory issued. `PredicateStore` keeps comparing bound objects by identity.

- `null` passed where the API documents it as "use the platform default" (`TrustManagerFactory.init`, `KeyManagerFactory.init`, the three arguments of `SSLContext.init`) gets its own code within the `-NOBS-` family.
- A trust-manager array is credited per element: `SSLContext.init` accepts the array when **every** element was issued by a `TrustManagerFactory`; an element whose class was defined by the application's class loader gets its own code.
- An object whose producer already refused it (value or origin) is reported downstream as "refused upstream", not as not observed.
- The first event a monitor observes, when it is not a creation event of the specification, gets its own `-ORDER-` code.
- An ordering failure of an object whose observed creation the specification refused — an algorithm, transformation or type outside the allow-list, or a forbidden constructor — gets its own `-ORDER-` code. Such a failure is the consequence of the refusal already reported, not a wrong order. Every creation guarded by an allow-list gets a refused twin for every overload, so a refused creation in woven code is always observed.
- A second `init` on a `Cipher` or `Mac` after its operation finished gets its own `-ORDER-` code.
- Key material that was observed to be random, where the rule requires prepared key material, gets its own code.
- A `-NOBS-` report over a byte array carries a fingerprint of the bytes (truncated hash), and one over a trust-manager array carries the element classes. No verdict depends on either.
- **BREAKING** for any consumer that enumerates codes: new codes and new fields in the report.

**Specification set `jca_android` — one value clause.** `RSAKeyGenParameterSpec.crysl:15` admits `{1024, 2048, 4096}` while its sibling `KeyPairGenerator.crysl:29` admits `{2048, 3072, 4096}`. The specification transcribes the sibling list, recorded as an `oracle-wart` row under the D-20.4 precedent; the pinned rule is not edited. **BREAKING** for reported counts: 3072 stops being reported and 1024 starts.

**Consumers of report codes.** The logcat parser and the campaign consolidation recognise the new codes and the evidence keys; the evidence keys stay in the record's message but are excluded from its identity.

**Result export (`rv-platform`).** `ResultProcessorComponent` writes all output files in one pass over tasks ordered by APK, keeps one static model at a time, and releases each task's repository and static model after its rows are written; the platform releases both when a task finishes during the run. Files, columns and row content are unchanged.

**Logcat capture (`rv-android-core`).** The capture reads the device's log ring buffer through `adb logcat` while the application runs. On the campaign's emulator image each buffer is 2 MiB and `logd` was already pruning entries of the application's process 60 s into a short run (measured 2026-09-15 on `phtcosta/rvandroid:0.9.3`, API 30). In the evidence campaign whole blocks of the application's lines are missing at process start-up, when coverage lines arrive by the hundred per second: at the okhttp `platformTrustManager` site 26 of 3,889 runs lost reports that the same event body emits unconditionally. `LogcatManager` sets the ring buffer to 16 MiB before every capture.

**Out of scope, deliberately:** the frozen `jca` set (no change and no impact measurement); any per-site verdict catalogue (it is specific to a dataset); value lists of the expert oracle other than the RSA clause; producers the oracle does not have (`Certificate.getPublicKey`, `Cipher.unwrap`, `ECPublicKeySpec`); re-running the campaign used as evidence.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `instrumentation`: arity enforcement replaces the measure-only contract of INV-INS-122; weaving of methods inherited by framework subtypes and a published drop counter; branch-target preservation for inserted before-hooks; nested-type resolution in pointcut signatures; after-finally semantics for `after` advice on both weaving paths.
- `instrumentation` (continued): the label codes of the successor set within the `-NOBS-` and `-ORDER-` families, the per-element manager credit, the upstream-refusal mark, the evidence keys appended to non-observation envelopes, and the RSA key-size transcription with its `oracle-wart` row. The `conformance` capability (the MOP–CrySL comparison component) is not touched: it does not read report codes.
- `core`: the identity of a violation record (`unique_msg`, INV-CORE-25) excludes the evidence keys, so a fingerprint that differs per run does not multiply unique counts; `LogcatManager` sizes the device log ring buffer before capture (INV-CORE-64).
- `analysis`: the logcat parser accepts the new code families and report fields.
- `platform`: `ResultProcessorComponent` processes tasks one at a time with a per-APK static model (INV-PLT-14, INV-PLT-15), and completed tasks release their repository and static model.

## Impact

**Sibling Java reactor** (`rvsec/`):

| Module | What changes |
|---|---|
| `rvsec-instrumentation-dexlib2/pointcut-engine` | arity check; nested-type resolution (`PointcutMatcher`, `TypeResolver`) |
| `rvsec-instrumentation-dexlib2/advice-emitter` | wrapper grouping and drop counter (`WrapperEmitter`); `AfterEmitter` after-finally |
| `rvsec-instrumentation-dexlib2/dex-mutator` | branch-target and line-entry retargeting (`InstructionInjector`); framework-subtype owners (`DexWeaver`, `AndroidClassIndex`) |
| `rvsec-instrumentation-dexlib2/cli` | new counters in the results JSON |
| `rvsec-mop` (`jca_android/`) | label codes, refused creation twins, per-element credit, upstream-refusal mark, evidence keys, RSA list, `codes.csv` (new `label` column) |
| `rvsec-core` | new `Property` entries and the fingerprint helper used by the specifications |

**`rv-android`**: `rv-coverage` (logcat parser), `rv-platform` (`ResultProcessorComponent`, task release), campaign consolidation, `rv-android-core` (`RvErrorLog.unique_msg`, `LogcatManager` buffer size), `data/jca_android/` records (`conformance_record.csv`, `divergence_record.csv`) and the structural and message gates under `scripts/` and `tests/parity/`.

**Requirements**: FR02 (instrumentation), FR03 (specification sets), FR11 (logcat parsing), FR13 (violation detection), FR14 (result generation), NFR06 (observability), NFR08 (reproducibility).

**Verification without a campaign**: static sweeps over the instrumented APKs for A1–A4, bytecode-shape unit tests of the woven handler for A5, the specification trace harness (`scripts/gh104_diff_harness.py`, which replays monitor event traces) for the labels (same set of reported sites and events before and after), byte-for-byte regeneration of one reference container for the export, and a single end-to-end smoke test at the end.
