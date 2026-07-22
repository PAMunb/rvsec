# ADR: Named-Binding Contract for dexlib2 Advice Emission

**Status**: Proposed (under gh56)
**Date**: 2026-05-14
**Context**: gh56-instr-binding-correctness — fix `java.lang.VerifyError` on constructor advice with `returning(...)` bindings in the dexlib2 instrumentation pipeline.
**GitHub Issue**: #56

## Context

The dexlib2 advice-emission pipeline introduced in gh52 silently emitted malformed `invoke-static` instructions whenever an advice targeted a constructor with a `returning(...)` binding. The ART verifier rejected the bytecode with `java.lang.VerifyError`, aborting the process before the monitor could observe the violation.

Empirical impact on the 2026-05-08 distributed run:
- 2.202 / 18.267 task-runs (12,1%) carried at least one `VerifyError`
- 116 / 190 distinct APKs (61,1%) were affected
- Cryptoapp smoke oracle: only **3 / 8** expected violations captured

Two compounding root causes (validated in source on 2026-05-14, see `docs/20260514_erro.md`):

1. `PointcutMatcher.buildCallMatch` treated `invoke-direct <init>` as a static invoke (`baseOffset = 0`), shifting every user-visible argument binding by one register and losing the receiver reference.
2. `MonitorInvokeBuilder.resolveBindings` hardcoded the `returning(name)` parameter to literal register `v0`, producing a type-mismatched register array at every constructor + returning site.

The bug stayed latent for ~6 months because (a) the only smoke test (`DexWeaverConstructorAdviceTest`) exercised constructor advice **without** a `returning(...)` binding, (b) `MessageDigest` was routed through `WrapperEmitter` masking the failure, and (c) the Layer 3 oracle gate was registered as diagnostic, not blocking.

This ADR captures the seven design decisions taken in gh56 to fix the bug and harden the emission pipeline against the same class of regression.

## Decisions

### D1: Bindings resolve by name across all five emitters

**Decision**: Every binding name appearing in `parameters[]`, `returning[]`, `throwing[]`, or `monitorCalls[i].args[]` resolves to a register via a single lookup table populated by `MonitorInvokeBuilder.resolveBindings`. The order of registers in the emitted `invoke-static` is dictated by the order of names in `monitorCalls[i].args[]`, not by the order of registers in the matched invoke site.

**Rationale**: gh52 ADR D13 already specified "by name", but the constructor + returning path silently regressed to ordinal-with-shift. Re-affirming "by name" as the single contract spanning all five emitters (`Before`, `After`, `AfterReturning`, `AfterThrowing`, `StaticInitialization`) makes it possible to add the cross-product unit test (`{emitter, invoke-kind, binding-kind}`) without designing a separate contract per emitter.

**Alternatives considered**:
- *Ordinal with explicit shift table per invoke kind*: rejected — the shift logic is exactly what produced bug #1; every new invoke kind would require its own shift constant and every binding kind would compound the table.
- *Type-driven resolution* (resolve by parameter type, not name): rejected because two parameters can share a type (e.g. `Cipher.update(byte[] input, int inputOffset, int inputLen, byte[] output)`).

**Concrete example** (bug shape):

For `SecretKeySpecSpec_c1` advice with expression `call(public SecretKeySpec.new(byte[], String)) && args(keyMaterial, keyAlgorithm) && returning(secretKeySpec)`:

- Matched bytecode: `invoke-direct {v4, v3, v0}, Ljavax/crypto/spec/SecretKeySpec;-><init>([B,String)V`
- `monitorCall.args = ["keyMaterial", "keyAlgorithm", "secretKeySpec"]`
- Resolution (D1):
  - `keyMaterial` → matcher's `arg00` → `v3`
  - `keyAlgorithm` → matcher's `arg01` → `v0`
  - `secretKeySpec` → returning → `targetRegister` → `v4` (the freshly-constructed instance, see D3)
- Emit: `invoke-static {v3, v0, v4}, ...->SecretKeySpecSpec_c1Event([B,String,SecretKeySpec)V`

Pre-fix the emit was `{v4, v3, v0}` — every slot type-mismatched → `VerifyError`.

### D2: `$return` synthetic key lives in `Match.argBindings`

**Decision**: `PointcutMatcher.buildCallMatch` peeks at `instructions[invokeIndex + 1]` and, if the opcode is `MOVE_RESULT`, `MOVE_RESULT_OBJECT`, or `MOVE_RESULT_WIDE`, stores the destination register under the synthetic key `$return` in `Match.argBindings`. The peek is skipped for constructors (`<init>` returns `void` — no `move-result*` follows).

**Rationale**: `Match.argBindings` already exists and is consumed by `resolveBindings`. Adding one synthetic key keeps the type contract uniform (`Map<String, Integer>`). The alternative — a separate `Optional<Integer> returnRegister` field on `Match` — would force every consumer to check both locations, complicating the named-binding lookup.

**Alternative considered**: indexing `$return` as `argN+1` (where N is the parameter count). Rejected because the existing `argNN` keys are positional in the user-parameter list and conflating "return value" with "extra positional arg" misleads test authors.

**Concrete example**: for advice `call(public KeyGenerator.generateKey()) && target(generator) && returning(secretKey)` matched on `invoke-virtual {v2}` followed by `move-result-object v5`:

- `Match.argBindings = { "$return" : 5 }`
- `resolveBindings` resolves `secretKey` → 5 → emitted invoke places `v5` at the position matching the monitor signature.

For `MOVE_RESULT_WIDE` (long/double), the destination register pair occupies `(vN, vN+1)`; the synthetic key stores the low register `vN`. Wide-pair contiguity is preserved by `RegisterShifter` (INV-INS-26).

### D3: Constructor identification requires both opcode and descriptor agreement

**Decision**: `buildCallMatch` sets `match.isConstructor = true` only when both `cp.isConstructor() == true` AND the matched invoke's `MethodReference.name.equals("<init>")`. The descriptor predicate alone is necessary; the opcode predicate alone is insufficient because `invoke-direct` is also used for private method calls and `super.<init>` chaining outside the advice contract.

**Rationale**: bug #1 had a subtle false-friend in proposed Fix #1 — removing `cp.isConstructor()` from `treatAsZeroOffset` without preserving the descriptor predicate would have left private `invoke-direct` calls with a captured receiver they were not asking for. The two-predicate gate is defence in depth.

**Concrete examples**:
- `invoke-direct {v0, v1}, LFoo;-><init>([B)V` with `cp.isConstructor()==true` → `match.isConstructor=true`, `targetRegister=v0`
- `invoke-direct {v0}, LFoo;->privateMethod()V` with `cp.isConstructor()==false` → `match.isConstructor=false`, `targetRegister=v0` via virtual fallback path
- `super.<init>` chain (`invoke-direct {v0, v1}, LObject;-><init>()V` inside user constructor body) with `cp.isConstructor()==false` (descriptor targets user-class `<init>`, not Object's) → `match.isConstructor=false`, no receiver-capture under constructor semantics

**Alternative considered**: trust only `cp.isConstructor()`. Acceptable for the smoke, but a future emitter that consumes `Match.targetRegister` directly (e.g. for a `target(this)` binding on a private-method advice) would be at risk. The two-predicate gate is documented in INV-INS-70.

### D4: Layer 3 oracle gate is mandatory only for `cryptoapp`

**Decision**: `--mandatory` (on the `layer3` subcommand of `ValidationCli`) is passed exclusively when `cryptoapp.apk` appears in the dex result set. Other APKs continue to run Layer 3 in diagnostic mode. The orchestrator (`run_phase5_validators.sh`) detects `cryptoapp` in the result directory and adds the flag conditionally.

**Rationale**: authoritative ground-truth oracles exist for `cryptoapp.apk` (8 events, hardcoded by the cryptoapp authors). The other APKs in the corpus have no authoritative oracle — promoting Layer 3 to mandatory for them would force the gate to either accept any non-empty trace (false positives) or fail every run (false negatives). The bug we are blocking only manifested in cryptoapp because that is the only smoke we ran with a constructor-heavy oracle.

**Implementation**: at the script level, `HAS_CRYPTOAPP` is set by `find "$DEX_DIR/instrumented_apks" -name 'cryptoapp*.apk'`. When true, `--mandatory` is appended to the `layer3 --batch` invocation.

**Pivotal events**: of the 8 cryptoapp oracle events, only **#7 `KeyPair.<init>`** and **#8 `SecretKeySpec.<init>`** exercise the constructor-advice path that gh56 fixes. The other 6 events are captured today via `WrapperEmitter` and do NOT exercise the bug. The implementation logs pass/fail status of the two pivotal events separately so operators can distinguish a binding regression (pivotal events fail) from a wrapper regression (non-pivotal events fail).

**Alternative considered**: extend the oracle inventory to 20-30 APKs. Out of scope — requires manual ground-truth derivation per APK.

### D5: `DexWeaver.WeaveReport.plansSkippedUnresolvedBinding` is observable, not silent

**Decision**: when `resolveBindings` cannot resolve a binding name to a register, `MonitorInvokeBuilder.buildInvoke` throws the marker `UnresolvedBindingException`. `DexWeaver` catches it at the per-advice emission funnel, logs the site (advice name + binding name + class + insn index), increments `WeaveReport.plansSkippedUnresolvedBinding`, and continues weaving the rest of the APK. The advice is skipped at that site — no malformed `invoke-static` is emitted with `v0` substituted for the unresolved name.

**Rationale**: silent emission of malformed invokes was the cause of the six-month latency. An observable counter surfaces every future regression in `instrument_results.json` immediately. The counter is the canonical regression trip-wire for any future instrumentation run.

**Alternatives considered**:
- *Return `null` from `buildInvoke` and require every emitter to null-check*: rejected — five emitters, five null-checks, easy to miss one.
- *Throw an unchecked exception that's NOT caught*: rejected — some skips are legitimate (e.g. `returning(unused)` on a method whose return is discarded; the rest of the APK should still be instrumented).

The chosen pattern (marker exception caught at one funnel point) mirrors the existing `HighRegisterNonContiguous` exception (INV-INS-69).

**Concrete observation**: `instrument_results.json` now includes `"plansSkippedUnresolvedBinding": <count>`. The script `run_phase5_validators.sh` fails fast when this counter is non-zero on cryptoapp runs (gh56 INV-INS-71).

### D6: Mandatory gate signals through the existing `Report(passed=false)` contract, not a new exit code

**Decision**: When `layer3 --mandatory` detects a deviation, the subcommand builds `Report(passed=false)` and calls `emitAndExit(parent, report)`. The existing `Report.exitCode()` (`validator/Report.java:44-46`) maps that to exit `1`. The runner aggregator (`scripts/run_phase5_validators.sh`) already treats `rc==1` as `GATES_FAILED`; any other non-zero rc is classified as diagnostic. No new exit code is introduced.

**Rationale**: an earlier draft of this design proposed exit code `2` for "mandatory gate failure" to distinguish it from `1` (malformed input). That conflicted with the actual `Report.exitCode()` contract — `Report` is the universal validator response object and changing its surface for one subcommand fragments the contract. The runner script also does not treat `rc==2` as failure — it logs diagnostic and continues. Routing through `Report(passed=false)` reuses the existing aggregator semantics without modification.

**Alternative considered**: tri-state `Report` (`PASS`/`FAIL`/`MANDATORY_FAIL`) with exit codes `0/1/2`. Rejected because:
1. The semantic distinction `MANDATORY_FAIL` vs `FAIL` collapses to "gate failed" from the operator's perspective — both block the build.
2. The runner script's exit-code aggregator treats anything beyond `1` as diagnostic; emitting `rc==2` would silently downgrade real failures to advisory.
3. Tri-state ripples to every layer's Report construction (layer1..layer5 each need a `--mandatory` analogue) — speculative complexity for a single use case.

### D7: Instruction-stream propagation through `Context`, typed as `List<? extends Instruction>`

**Decision**: `PointcutMatcher.match(...)` (the public API) gains a `List<? extends Instruction> instructions` parameter; `Context` gains a matching field; `buildCallMatch` reads the list from `Context` to peek `idx+1` for `move-result*` (D2 / INV-INS-72). The list is typed as `List<? extends Instruction>` — the `org.jf.dexlib2.iface.Instruction` interface — not `List<BuilderInstruction>`.

**Rationale**: an earlier draft typed the parameter as `List<BuilderInstruction>` (from the `dexlib2-builder` module). That would couple `pointcut-engine` to `dexlib2-builder`, which is a build-only dependency in the current Maven graph — the matcher operates exclusively on the read-side `iface.Instruction` abstraction. Keeping the type as `List<? extends Instruction>` preserves the module layering. Concrete callers (in `dex-mutator`) pass either the immutable instruction list of a `Method` or an in-flight `MutableMethodImplementation.getInstructions()` — both satisfy the wildcard.

The `?` (extends) bound is needed because the caller may hold a `List<BuilderInstruction>` (which extends `Instruction`), and we want to accept it without forcing the caller to copy/cast.

**Alternative considered**: stash the list on `Context` only and keep `match()`'s API unchanged by adding a `match(pe, classDef, method, instructions)` overload. Rejected — every existing caller of `match()` already has the instruction list available (it iterates over instructions to call `match` per index), so requiring the parameter at the public API site is honest about the data dependency.

**Caller impact**: `PointcutMatcher.match` is the only public method whose signature changed. Single call site (`DexWeaver.java:329`) was updated to pass the existing `instructions` list. No external module other than `dex-mutator` and the test fixture `EmitterTestFixtures.java` was touched.

## Consequences

**Positive**:
- ART verifier accepts every instrumented APK in the cryptoapp smoke (post-fix; pre-fix only 3/8 oracle events were captured because 5 were lost to `VerifyError`).
- The named-binding contract is enforced at unit-test level via `DexWeaverConstructorAdviceTest` (SecretKeySpec + IvParameterSpec cases asserting register-to-type correspondence).
- `plansSkippedUnresolvedBinding` counter surfaces future regressions immediately; the script fails fast when it's non-zero on cryptoapp runs.

**Negative / accepted residuals**:
- Cross-APK ecosystem validation beyond cryptoapp is out of scope for gh56 (separate experiment). A binding-related `VerifyError` family unique to other APKs could theoretically slip past the smoke; the counter trip-wire mitigates this.
- The `Match.isConstructor` field duplicates information derivable from `matchedAgainst instanceof CallPC && ((CallPC) matchedAgainst).isConstructor()`. The duplication is justified because `MonitorInvokeBuilder` is the only consumer and the `instanceof` downcast would re-introduce a `pointcut-engine` import in the emitter module — the field's purpose is layering, not new information.

**Neutral**:
- `Match` constructor signature changed (added `boolean isConstructor` param). Callers updated in the same change: `PointcutMatcher.buildCallMatch`, `PointcutMatcher.mergeBindings`, `Match.empty(pe)`, `EmitterTestFixtures` (test).
- `WeaveReport` record gained one component (`plansSkippedUnresolvedBinding`); consumer `BatchRunner.java` was updated in the same change to surface the new field in `instrument_results.json`.

## References

- `docs/20260514_erro.md` — empirical analysis of the bug (root cause § 3, patch § 5).
- gh52 ADR D13 (Bindings by name) — the contract this ADR re-affirms.
- INV-INS-66 (inline-vs-wrapper partitioning) — the precondition for inline-AFTER on constructor invokes.
- INV-INS-26 (RegisterShifter) — wide-register pair contiguity invariant referenced by D2.
- INV-INS-69 (HighRegisterNonContiguous) — marker-exception pattern reused by D5.
- INV-INS-70..73 — the four invariants introduced by gh56.
