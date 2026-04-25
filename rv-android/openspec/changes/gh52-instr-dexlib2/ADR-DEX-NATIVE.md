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

## D10 — Calling-convention-safe scratch register allocation (shift+bump)

**Context**: every advice / coverage emission needs at least one scratch
register at a low slot (Format35c invokes pack 5 register references into
4-bit fields each, so `v0..v15` is the legal range). The natural-looking
shortcut is `bumpRegisterCount(+N)` to grow the frame, then use the new
high-end slot as scratch — every other DEX instrumentation tutorial does
this. It does not work on Android.

**The trap**: Android DEX places method **parameters in the highest
`paramRegisterCount` slots**. Growing `registerCount` from `M` to `M+N`
shifts the parameter window from `r[M-paramRegs..M-1]` to
`r[M+N-paramRegs..M+N-1]` *implicitly* — the runtime initializes
parameters at the new positions. But the bytecode still references them
at the old positions, which are now uninitialized locals. Result on the
verifier: `java.lang.VerifyError: tried to get class from non-reference
register vN (type=Undefined)` on the first instruction that touches a
parameter — which is essentially every instrumented method that has
parameters.

We hit this in the gh52 cryptoapp + 3-APK smoke run on Apr 25: every
coverage-instrumented method failed boot with VerifyError on
`MainActivity.<init>`, `MainActivity.a(int)`, etc. The pre-existing
`coverage-weaver.CoverageWeaver` (and `dex-mutator.RegisterAllocator`)
both used the naive `bumpRegisterCount` shortcut.

**Decision**: standardize on `RegisterShifter.spillLowRegisters(mut,
count)` for any code path that needs to add scratch slots. Strategy:
walk every existing instruction and rewrite each register reference
`r → r + count` (via `shiftExpanding(threshold=0, delta=count,
scratchReg=0)`, which widens 4-bit slots to `/from16` forms when needed),
then call `bumpRegisterCount(+count)`. After both steps, registers
`0..count-1` are free for the caller and parameters end up at
`regCount - paramRegs..regCount - 1` — matching where the runtime
initializes them after the bump. When the method already has free
locals (`localCount >= count`), no shift/bump is needed; the caller
uses the existing low locals as scratch (the cheap path).

The strategy is ported verbatim from
`prototipo-dexlib2/dex-weaver/CoverageWeaver.spillOneLocal`. The
prototype validated it end-to-end on the same APKs that gh52's naive
implementation broke.

**Alternatives considered**:
- *Always grow at top + use high-end scratch (the original gh52
  shortcut)*: silently violates the calling convention. Rejected — see
  the cryptoapp regression above.
- *Insert `move-from16` instructions at method entry to copy parameters
  from the new high positions back to the old low positions before the
  original bytecode runs*: works in theory but trades shift complexity
  for prologue complexity, and breaks debug line numbers / try-catch
  ranges that point at instruction 0. The shift approach keeps
  instruction count-relative offsets stable.
- *Scope to `coverage-weaver` only and leave `dex-mutator.RegisterAllocator`
  unchanged*: the JCA descriptor's advice all declare
  `RegisterRequest.NONE`, so `RegisterAllocator` is currently
  unexercised — this is technically safe today, but a future advice
  with `if(...)` guards (the only emitter that requests scratch) would
  re-trigger the regression silently. Tracked as a follow-up under
  INV-INS-26 in `tasks.md` §5.4 rather than fixed eagerly because the
  refactor to add `Method` to the allocator's signature touches every
  advice emitter and is best validated by an actual scratch-using
  emitter test.

**Consequences**: codified as INV-INS-26. CoverageWeaver: free-locals
fast path or shift+bump spill. RegisterAllocator: documented residual
risk + follow-up task. Cli-level smoke against cryptoapp installs +
boots without VerifyError; future emitters that need scratch must use
`spillLowRegisters` (or its allocator analogue once the follow-up
lands), never `bumpRegisterCount` alone.

## D11 — `move-result*` aware advice insertion (INV-INS-27)

**Context**: the gh52 cryptoapp smoke run on Apr 25 surfaced a second
class of advice-side bug, distinct from the register allocation issue.
`AfterReturningEmitter` was matched against the internal call inside
`androidx.core.util.Preconditions.checkArgument(boolean, Object)`. The
matched method's bytecode at the call site was:

```
[3] invoke-static  Lsome/Format;->format(...)Ljava/lang/String;
[4] move-result-object v1
```

`InstructionInjector.insertAfter(idx=3, plan)` faithfully inserted the
monitor's `invoke-static` at index 4 — between the matched invoke and
its `move-result-object`. Result:

```
[3] invoke-static  Lsome/Format;->format(...)Ljava/lang/String;
[4] invoke-static  Lmop/MultiSpec_1RuntimeMonitor;->event(...)V  ← NEW
[5] move-result-object v1                                        ← now reads V (void!)
```

The DEX `move-result*` family is **only valid as the immediate successor
of an invoke that returns a value**. Inserting any non-`move-result`
instruction in between makes the move-result read from the wrong
invoke's pseudo-result. When the new invoke returns void (every monitor
event method returns V by MOP convention), the verifier rejects the
class with `type Undefined unexpected`.

**Decision**: `InstructionInjector.insertAfter(idx, plan)` and any other
AFTER-style insertion path MUST detect when `instructions[idx]` is an
invoke followed by `move-result*` and shift the insertion point past
the move-result (`idx + 2` instead of `idx + 1`). This applies whether
the move-result is consumed (a real `v = call()` site) or unconsumed
(some compilers emit `move-result-object` even when discarded). The
emitter API stays unchanged; the fix lives entirely in the executor.

**Alternatives considered**:
- *Have the matcher excludes call sites whose result is consumed*: too
  conservative — it would lose every `AfterReturning` advice that
  targets a method whose result the user code actually uses, which is
  almost all of them.
- *Have the emitter inspect the next instruction*: would force every
  emitter to know about `move-result*`, duplicating logic. The injector
  is the right home — it already has the instruction stream context.

**Consequences**: codified as INV-INS-27. Required test:
`advice-emitter/src/test/MoveResultGuardTest` with synthetic matched
calls followed by move-result-object / move-result-wide / move-result.
Required smoke: cryptoapp's Preconditions.checkArgument advice landing
must produce a verifying class (currently the dominant failure mode).
Tracked alongside D10 in tasks.md §5.4 — both fixes land together,
because exercising INV-INS-27 in isolation requires the allocator's
shift to be in place to keep paramRegs intact.
