# ADR — DEX-native instrumentation pipeline (gh52)

Status: accepted. One section per decision documented in `design.md`.

## D1 — Java Maven multi-module, not single jar

**Context**: the prototype's `DexWeaver` mixes parsing, matching, register
allocation, and DEX mutation in ~3400 LOC. Further extension would keep
piling concerns into one class and make testing a moving target.

**Decision**: decompose into 9 submodules (descriptor-reader,
pointcut-engine, advice-emitter, dex-mutator, coverage-weaver,
monitor-builder, multidex-merger, cli, validator) per single-responsibility.
Module dependency graph is a DAG rooted at descriptor-reader.

**Consequences**: independent unit tests per layer; `advice-emitter` owns
the `EmitPlan` / `RegisterRequest` value classes; `dex-mutator` consumes
them; no circular dep, no `*-api` stub module. Build-ordering is mechanical.

## D2 — Descriptor JSON, not `.aj` parsing

**Context**: weaving requires the pointcut + advice semantics. Parsing the
`.aj` output of JavaMOP is brittle (regexes over a generated template) and
fragile across JavaMOP versions.

**Decision**: patch JavaMOP to emit a JSON descriptor
(`MultiSpec_*MonitorAspect.json`) alongside the `.aj`; the weaver consumes
only JSON. Patch lives vendored in `rvsec/javamop` (see D6).

**Consequences**: the descriptor is the canonical machine contract between
monitor generation and instrumentation; `.aj` stays human-readable but is
never re-parsed.

## D3 — Coexistence + variant flag, not immediate replacement

**Context**: Layer-3 / Layer-4 validation needs paired execution of both
pipelines on the same APK.

**Decision**: Phase 4-5 keep `rv-instrumentation` (legacy ajc) and
`rv-instrumentation-dexlib2` (new) side by side; `instrumentation_variant`
selects between them. Phase 6 quarantines the legacy per P3.

**Consequences**: minimal dispatch line in `PreProcessor._instrument_apks`
+ one new config field; paired comparison becomes trivial.

## D4 — Validator as a Maven submodule, not a sidecar script

**Context**: the 6-layer validation framework must be runnable and
maintainable as software.

**Decision**: `validator/` is a Maven submodule of `rvsec-instrumentation-dexlib2`
with a CLI per layer (`Layer1..5`, `mapping`, `parity`, `inventory`).

**Consequences**: Java stays as the build system; CI gating is mechanical
(exit code + JSON report).

## D5 — Wrapper replacement for register-aliasing, not always-spill

**Context**: `after() returning(R r)` on static factories (e.g. `Cipher.getInstance`)
can cause register aliasing at injection time.

**Decision**: generate a `mop.MonitorWrappers.<name>` static method that
wraps the original call + emits the monitor event + returns the result;
rewrite the call site to invoke the wrapper. Always-spill only when no
wrapper applies.

**Consequences**: DEX size grows by the wrapper class; call-site instructions
untouched; zero `VerifyError` in the prototype's R8 APK validation.

## D6 — JavaMOP patch carried on the change branch

**Context**: the `--emit-descriptor` patch must travel with the change so
the gh52 branch is self-contained.

**Decision**: cherry-pick the patch (commit `6fca1f8a`) + follow-up mods
(`927e78c1`) onto `gh52-instr-dexlib2`; retire the legacy
`emit-descriptor` branch.

**Consequences**: merging gh52 into `modules` brings the patch with it;
future work on `modules` consumes `--emit-descriptor` transparently.

## D7 — AGP ASM API considered and deferred

**Context**: the Android Gradle Plugin's
`Instrumentation.transformClassesWith` hooks **before** R8 — it would
avoid the JVMS §4.10.1.9 round-trip for source-built APKs.

**Decision**: do NOT adopt AGP ASM as the primary path for gh52. AGP ASM
requires source access (build-time hook); the JCA-400 dataset is almost
entirely third-party binaries. Documented as a deferred complementary
sub-experiment for the F-Droid reproducible subset.

**Consequences**: dexlib2 remains the primary path; AGP ASM stays as a
future cross-validation mechanism against a ground-truth baseline.

## D8 — Java module under `rvsec-android`, Python wrapper under `rv-android/modules/`

**Context**: the monorepo has two language sub-projects under one git
root. Mixing them breaks both (uv scanning, Maven parent resolution).

**Decision**: Java aggregator at
`rvsec/rvsec-android/rvsec-instrumentation-dexlib2/` (sibling of
`rvsec-apk`, `rvsec-gator`, `rvsec-logger-logcat`); Python wrapper at
`rv-android/modules/rv-instrumentation-dexlib2/` (uv workspace member).
Different names intentionally: `rvsec-` prefix in the Maven tree, `rv-`
prefix in the uv tree, each following its neighborhood convention.

**Consequences**: disambiguation in logs / errors / docs is always by root
path, never by suffix. "Which `rv-instrumentation-dexlib2` failed?" is
never ambiguous.

## D9 — Build-time fat-jar copy into the Python wrapper's `lib/`

**Context**: the Python wrapper needs to locate the Java CLI jar without
absolute paths, env vars, or manual copy steps.

**Decision**: during `mvn package` on the `cli` module, `maven-resources-plugin:copy-resources`
copies `cli/target/instr-cli.jar` to
`${main.basedir}/rv-android/modules/rv-instrumentation-dexlib2/lib/instr-cli.jar`.
The Python wrapper's default `cli_jar_path` resolves relative to its
module install location.

**Consequences**: zero configuration in the common case; `${main.basedir}`
comes from `directory-maven-plugin` configured in `rvsec-parent`. The
`lib/*.jar` path is gitignored — the jar is a build output, never versioned.
