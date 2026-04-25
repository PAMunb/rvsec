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

## D12 — Wrapper substitution as the canonical handler for after-side aliasing (INV-INS-29)

**Context**: AFTER advice on calls that have `args()` / `target()` /
`returning()` bindings would, when emitted inline, read register state
after the matched invoke + its `move-result*` have already overwritten
those registers. Java compilers freely reuse registers, so the binding
source register frequently equals the result destination register. The
verifier observes the resulting type confusion ("register v0 has type
Reference: javax.crypto.Cipher but expected Precise Reference:
java.lang.String") and rejects the class.

**Decision**: every after-side advice that exists in the descriptor MUST
be made available as a static wrapper in `mop.MonitorWrappers` (emitted
by `WrapperEmitter` from the descriptor before weaving begins). The
`DexWeaver`'s first pass walks every `INVOKE_STATIC` instruction in
each method, looks up its `MethodReference` in a wrapper-replacements
map, and rewrites the invoke's reference to call the wrapper instead
(`InstructionInjector.replaceInvoke`, Format35c + Format3rc). The
wrapper calls the original method with the same arguments, fires every
`MultiSpec_<X>RuntimeMonitor.<event>(...)` declared by the advices that
wrapped this call, and returns the original result. The matched call's
register state is preserved exactly (the caller never sees the wrapper
internals), so no aliasing risk exists.

**Why two passes**: `replaceInstruction` is size-stable, so substitution
can iterate left-to-right safely. Inline advice (`applyPlan` insertions
for non-substituted invokes — typically `before(...)` advices) mutates
the instruction list size, so it MUST run as a separate pass iterating
right-to-left, where each insertion only shifts already-processed
indices. Mixing the passes (substitution + inline in the same loop) was
the bug that surfaced as "replaceInvoke called on non-invoke opcode:
CONST_STRING" during the smoke runs prior to this ADR landing.

**Eligibility filter**: only advices that satisfy ALL of these go to the
wrapper:
- `position == "after"` AND (`returning != null` OR expression has
  `args(...)`) — the canonical aliasing-prone shape;
- target call is static (`targetLooksStatic` reads the expression's
  modifier prefix; the parser strips it from the AST so we lex it back
  out); instance-method wrappers are deferred until D12 receives an
  AndroidClassIndex-driven extension that emits a static wrapper that
  takes the receiver as its first parameter (tracked with INV-INS-29);
- not a constructor (the new-instance result is always at register 0
  of the matched invoke, no aliasing);
- no varargs / wildcard `..` / generic `Object` in non-zero positions
  (would require `AndroidClassIndex` overload expansion to lower to a
  concrete Java signature — also deferred).
Advices that fail the filter route to the inline path (`before` is
inline-safe; non-eligible AFTER is recorded as `plansSkippedAliasing`
and skipped without emitting broken bytecode).

**Generated wrapper file**: `mop/MonitorWrappers.java`. Imports come from
the descriptor's `imports` list (filtered to drop AspectJ / MOP runtime
packages that wouldn't resolve at javac time). Each wrapper method
declares `throws Exception` (catch-all so checked exceptions like
`NoSuchAlgorithmException` propagate transparently — the call site
already handled them, the wrapper just preserves the flow). Type names
in WrapperEntry are resolved to FQNs via `TypeResolver` so the
DexWeaver's refKey lookup matches the call site's
`MethodReference.getDefiningClass()` (otherwise simple names like
"String" round-trip to "LString;" instead of "Ljava/lang/String;" and
no substitution ever happens).

**Build-side support**: `MonitorBuilder` invokes `d8` over the compiled
monitor class files PLUS every jar in `BuilderConfig.classpath` so the
runtime support classes (`com.runtimeverification.rvmonitor.java.rt.*`,
`br.unb.cic.mop.*`) get dexed alongside the generated monitor +
wrappers. Without this, the runtime monitor's parent class `RVMObject`
resolves at javac time but is missing in the merged APK at runtime,
surfacing as `ClassNotFoundException`. `rvsec-agent.jar` is the single
classpath entry (it shades `rv-monitor-rt.jar`) — passing both produced
"Type ... defined multiple times" errors at d8.

**Consequences**: codified as INV-INS-29. Cli-level smoke on cryptoapp +
3 small JCA-400 APKs goes from 882 VerifyError → 0; cov_method on
cryptoapp doubled from 26.42% → 48.11%; cov_rv_method (MOP-reachable
methods reached) jumped from 22.95% → 50.82%. The 52 plansSkippedAliasing
on the smoke run reflect instance-method advice that the current static-
only wrapper filter cannot route — INV-INS-29 follow-up will land an
instance-method wrapper extension once `AndroidClassIndex.expandSupertypes`
is ported from the prototype.

## D13 — Binding resolution by name, not by ordinal (INV-INS-30)

**Context**: the runtime monitor's event method signature follows the
`monitorCall.args` order — the names the .mop spec declares. Advices
freely mix binding clauses: a `KeyGenerator.init(int)` advice may
declare `parameters: [{type: KeyGenerator, name: k}]` and bind `k` via
`target(k)`, with `monitorCalls.args = ["k"]`. The previous
`MonitorInvokeBuilder.registersFor` walked advice parameters by ordinal
and looked up `arg00`, `arg01`, ... in `match.argBindings` — which
silently mis-bound every advice that wasn't pure `args(...)`. The
KeyGenerator advice ended up calling its event with the int key-size
register instead of the receiver, producing `VerifyError: register v2
has type Imprecise Constant: 32767 but expected Reference:
javax.crypto.KeyGenerator`.

**Decision**: build a `Map<String, Integer>` from advice-parameter NAME
to register, populated by parsing each binding clause from the
expression:
- `target(name)` → `match.targetRegister`;
- `args(n1, n2, ...)` → `match.argBindings.get("argNN")` per positional
  slot;
- `returning(name)` / `throwing(name)` → 0 (best-effort; the wrapper
  system D12 is the canonical handler — these branches are reached only
  when the wrapper filter rejected the advice and we fell back to the
  inline path, which is itself a defensive skip).
For each `monitorCall.args[i]` (the names the runtime monitor expects
in declaration order), look up the corresponding register from the map.
The same monitorCall.args order also drives `buildMethodReference`'s
parameter descriptor list, so the emitted `invoke-static` arity and
type signature align with the runtime monitor's actual method signature
emitted by rv-monitor.

**Consequences**: codified as INV-INS-30. The two fixes (D12 + D13)
land together because each masks the other: without D12, every advice
takes the inline path and D13's binding resolution surfaces as the
verifier rejecting the well-formed-but-aliasing inline event invoke;
without D13, even D12-substituted call sites that ARE wrapped still
have the inline-fallback path emitting broken events.

## D14 — Instance-method wrappers via AndroidClassIndex overload enumeration (INV-INS-31)

**Context**: D12's wrapper system (INV-INS-29) covered static-call
advices but defensively skipped instance-method advices, ambiguous-
`Object` parameter advices, and `..` varargs / `T+` supertype patterns
— anything the descriptor parser couldn't lower to a single concrete
Java signature. The cryptoapp + 3-APK smoke run reported 52
`plansSkippedAliasing` from this defensive skip. Most of those sites
are common JCA instance methods (`Cipher.doFinal`, `Cipher.init`,
`Mac.doFinal`, `MessageDigest.update`, etc.) where the descriptor's
`call(public byte[] Cipher.doFinal(byte[]))` is unambiguous on the
target side but the matched invoke is `invoke-virtual`, which the old
`targetLooksStatic` filter rejected because the wrapper would have
called `Cipher.doFinal(...)` statically and produced a runtime
`MethodNotFoundError`.

**Decision**: enumerate concrete Android API overloads via
`AndroidClassIndex.methods(declFqn, methodName, /*onlyStatic=*/false)`
(ported from prototipo's `WrapperGenerator.expandSupertypes`). For each
overload returned (carrying `paramFqns`, `returnFqn`, `isStatic()`):
- Match the parser's declared paramTypes against the overload's
  `paramFqns` with subtype-aware semantics (`T+` ⇒
  `index.isAssignableFrom(T, actual)`; `..` trailing varargs ⇒ accept
  any concrete tail; literal exact match otherwise).
- Emit one wrapper Java method per concrete overload. Static targets
  keep the original form; instance targets take the receiver as the
  first wrapper parameter (`<DeclaringFqn> recv`) and the wrapper body
  becomes `recv.<method>(p0, ...)`. Advice `target(name)` bindings map
  to `recv` and `args(n1, n2, ...)` map to `p0..pN`.
- Register the wrapper's DEX `MethodReference` with the receiver
  descriptor prepended for instance entries; keep the lookup key on
  the original (un-prepended) signature so it matches the call site's
  `getDefiningClass()#name(params)` exactly. `findWrapperReplacement`
  drops its `INVOKE_STATIC`-only filter and accepts every invoke
  opcode. `InstructionInjector.replaceInvoke` already normalizes any
  invoke kind to `INVOKE_STATIC` while preserving register operands —
  so the original receiver register at register C transparently
  becomes the wrapper's first arg.

`WrapperEmitter.generate` gains a 3-arg overload `(descriptor,
outputDir, AndroidClassIndex)` and `WrapperEntry` gains an `isStatic`
field. `BatchRunner` threads the existing `androidIndex` instance into
this call. The `hasWildcardParam` / `hasAmbiguousObjectParam` /
`targetLooksStatic` skip filters are removed from the index-driven
path — `expandCallTarget` returns concrete overloads or an empty list,
both of which the caller already handles correctly. The literal
fallback (when `androidIndex` is null) keeps the legacy filters as a
defensive backstop.

**Consequences**: codified as INV-INS-31. Wrappers can now cover
instance-method advices end-to-end, which is the dominant shape of
the JCA spec set's after-side hooks (`Cipher.doFinal`, `Mac.doFinal`,
`MessageDigest.update/digest`, `Signature.update/sign/verify`,
`KeyAgreement.doPhase`, ...). Trailing `..` varargs and `Object`
ambiguous params no longer block wrapper emission either. A side
effect of using the API index as the source of truth on `isStatic` is
that the parser's lexical heuristics (the old `targetLooksStatic`)
become unnecessary — the static / instance verdict comes from
android.jar directly. Validation: `WrapperEmitterTest` (4 cases:
static expansion, instance expansion, `..` varargs expansion, null-
index fallback) plus the smoke gate of strictly-decreasing
`plansSkippedAliasing` on cryptoapp + the 3-APK set with zero new
`VerifyError`. Smoke verification on a real emulator is captured in
task 16.x once the next aperv:sata_mop pass lands.
