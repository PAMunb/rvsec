## Context

This change fixes two compounding defects in the dexlib2 advice-emission pipeline that together produce `java.lang.VerifyError` for every advice that targets a constructor with a `returning(...)` binding. The defects were identified in source by parallel exploration on 2026-05-14 (`docs/20260514_erro.md` in `ase-journal/docs/`) after the RQ3 anomaly in the 2026-05-08 campaign — `~0%` of detected violations originating in app code vs `33,91%` in the ICST baseline — was traced from "test generator coverage gap" to "instrumentation silently swallowed violations".

Quantified impact on the 2026-05-08 distributed run:

| Metric | Value |
|---|---|
| Total task-runs | 18.267 |
| Task-runs with at least one `VerifyError` | 2.202 (12,1%) |
| APKs with at least one affected task | 116 / 190 (61,1%) |
| Cryptoapp oracle smoke | 3 / 8 violations (oracle expects 8) |
| Specs affected (constructor-typed advice) | 12 |

The fix is structurally small (two methods rewritten, one synthetic key added to `Match.argBindings`) but the surrounding decisions are non-trivial:

1. **Binding resolution model**: do bindings resolve by ordinal (positional in `regs[]`) or by **name** (positional in `parameters[]`/`returning[]`/`monitorCalls[i].args[]`)? gh52 D13 already specified "by name" but the implementation regressed for constructors. We re-establish "by name" as the canonical contract spanning all five emitters.
2. **`move-result*` capture**: where does the synthetic `$return` key live, and who populates it? We place it in `PointcutMatcher.buildCallMatch` (single capture point, all emitters benefit) under the synthetic key `$return` in `Match.argBindings`.
3. **Constructor classification**: do we rely on opcode (`invoke-direct` to an `<init>` method) or on descriptor (`CallPC.isConstructor()`)? We require **both** to agree before capturing the receiver, because `invoke-direct` is also used for private and super-`<init>` calls outside the advice contract.
4. **Oracle gating policy**: the `cryptoapp-oracle.yaml` exists since gh52 and was the design's smoke gate, but the validator harness treats Layer 3 as diagnostic. We promote the gate to mandatory for `cryptoapp` only — not for every APK, because authoritative oracles do not exist for the other 189 APKs in the corpus.

References: FR01 (Monitor weaving), FR03 (Bytecode validity), NFR03 (Coverage fidelity), gh52 ADR D13 (Bindings by name), gh52 INV-INS-66 (inline-vs-wrapper partitioning), and `docs/20260514_erro.md` for the empirical analysis.

## Architecture

The dexlib2 instrumentation pipeline for advice emission is a three-stage data flow inside the Java multi-module Maven aggregate `rvsec-instrumentation-dexlib2`. This change touches the first two stages; the third stage (`InstructionInjector`, `RegisterShifter`, `DexWeaver`) is unaffected.

```
                                       monitors/*.json
                                              │
                                              ▼
                              ┌──────────────────────────────┐
                              │     pointcut-engine          │
                              │  PointcutMatcher.matchCall   │
                              │              │               │
                              │              ▼               │
                              │  PointcutMatcher.buildCallMatch   ◄── FIX #1 here
                              │   - constructor vs static    │
                              │   - capture targetRegister   │
                              │   - peek move-result*        │
                              │     → argBindings["$return"] │
                              └──────────┬───────────────────┘
                                         │  Match {targetRegister,
                                         │         argBindings:
                                         │           {arg00..argN, "$return"},
                                         │         isConstructor,
                                         │         matchedAgainst}
                                         ▼
                              ┌──────────────────────────────┐
                              │     advice-emitter           │
                              │  MonitorInvokeBuilder        │
                              │   .resolveBindings              ◄── FIX #2a here
                              │     - target → targetRegister│
                              │     - args   → arg00..argN   │
                              │     - returning              │
                              │         → resolveReturningRegister(match)  ◄── FIX #2b
                              │     - throwing → catch slot  │
                              │   .registersFor              │
                              │     - by name, no literal-0  │
                              │   .buildInvoke               │
                              └──────────┬───────────────────┘
                                         │  emit invoke-static …
                                         ▼
                              ┌──────────────────────────────┐
                              │     dex-mutator              │
                              │  InstructionInjector         │
                              │  RegisterShifter (INV-26)    │
                              │  DexWeaver                   │
                              └──────────────────────────────┘
```

The five emitters (`BeforeEmitter`, `AfterEmitter`, `AfterReturningEmitter`, `AfterThrowingEmitter`, `StaticInitializationEmitter`) all funnel through `MonitorInvokeBuilder.buildInvoke`, so a single fix at the funnel propagates correctly. `WrapperEmitter` is **out of band** — it produces a wrapper method that calls the original API and the monitor, sidestepping the inline-emission path entirely. Its correctness for `MessageDigest` does not exercise the buggy code path, which is why the bug stayed latent in the cryptoapp smoke for six months.

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `PointcutMatcher.buildCallMatch` | Match an invoke site against a `CallPC`, capture registers and (new) `$return` | `(CallPC, MethodReference, int[] regs, boolean isStaticInvoke, List<? extends Instruction> insns, int idx)` | `Match { targetRegister, argBindings, isConstructor, matchedAgainst }` |
| `MonitorInvokeBuilder.resolveBindings` | Map binding names (`target`/`args`/`returning`/`throwing`) to registers via `Match` | `(AdviceDescriptor advice, Match match)` | `Map<String, Integer>` (binding name → register) |
| `MonitorInvokeBuilder.resolveReturningRegister` (NEW) | Choose between `targetRegister` (constructor) and `argBindings["$return"]` (non-constructor) | `(Match match)` | `Integer` or `null` (unresolved) |
| `MonitorInvokeBuilder.registersFor` | Build the register array for an `invoke-static` from `monitorCall.args[]` and the binding map | `(List<String> argNames, Map<String, Integer> nameToReg)` | `int[]` (no literal-zero fallback) |
| `DexWeaver.WeaveReport.plansSkippedUnresolvedBinding` (NEW record component) | Observe unresolved bindings rather than emit malformed invokes. `WeaveReport` is a nested `record` inside `DexWeaver.java`; this change adds one component to the record, not a new class. | — | `int` counter, surfaced in `instrument_results.json` |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| INV-INS-70 (constructor offset; `match.isConstructor` set when both `cp.isConstructor()` AND `mr.getName().equals("<init>")` agree, D3) | `PointcutMatcher.buildCallMatch` lines 175-202 — split predicate `treatAsZeroOffset = isStaticInvoke` only; populate `Match.isConstructor` per D3 two-predicate gate | `PointcutMatcherConstructorTest.constructor_offset_captures_receiver` (plus D3-guard cases: private direct, super-`<init>`, descriptor-disagree) |
| INV-INS-71 (returning register, no literal-0) | `MonitorInvokeBuilder.resolveBindings` lines 141-194 — delete `putIfAbsent(..., 0)`, call `resolveReturningRegister` | `MonitorInvokeBindingTest.returning_no_literal_zero` |
| INV-INS-72 (`$return` peek) | `PointcutMatcher.buildCallMatch` new block — inspect `insns[idx+1]` for `MOVE_RESULT*` and record destination | `PointcutMatcherConstructorTest.move_result_object_captured_as_dollar_return` |
| INV-INS-73 (cryptoapp oracle mandatory) | `ValidationCli` `layer3` subcommand new `--mandatory` option; `run_phase5_validators.sh` appends it when `cryptoapp` is in the result set | `Layer3MandatoryTest.cryptoapp_deviation_fails_gate` |
| Named-Binding Contract (req) | `MonitorInvokeBuilder.{resolveBindings, registersFor}` + `DexWeaver.WeaveReport.plansSkippedUnresolvedBinding` | `MonitorInvokeBindingTest.cross_product_5x3x4` |
| Cryptoapp smoke gate (acceptance criterion) | `scripts/run_phase5_validators.sh` orchestrator | Manual run: `cryptoapp.apk` ape 300s → 8/8 oracle total + 2/2 on pivotal events (#7 `KeyPair.<init>`, #8 `SecretKeySpec.<init>`), 0 VerifyError, `plansSkippedUnresolvedBinding == 0` |

## Goals / Non-Goals

**Goals**

- ART verifier MUST accept every instrumented APK in the cryptoapp smoke (zero `VerifyError` after fix).
- Cryptoapp oracle captures **8 / 8** expected violations (up from 3 / 8), with **2 / 2** on the pivotal events (`#7 KeyPair.<init>`, `#8 SecretKeySpec.<init>`) as a separate sub-criterion.
- A sampled re-run of the **stratified 9 APKs** (top-3 + median-3 + tail-3 by `VerifyError` count) from the 2026-05-08 campaign shows zero `VerifyError`, with paired pre-vs-post event/coverage delta ≥ 0 per APK.
- The named-binding contract is documented as four invariants (INV-INS-70..73) in the instrumentation spec.
- Cryptoapp Layer 3 oracle becomes a blocking gate, observable via non-zero exit when the trace deviates.
- Fix surface: two methods rewritten (`buildCallMatch`, `resolveBindings`), one new helper (`resolveReturningRegister`), one synthetic key (`$return`), one new boolean field on `Match` (`isConstructor`), one CLI flag (`--mandatory`), one record component (`plansSkippedUnresolvedBinding`). Public API touched: `PointcutMatcher.match` (D7). No structural refactor.

**Non-Goals**

- Overload enumeration in `expandCallTarget` (`Mac.update([B)V`, `SSLContext.init`, …). Deferred to `gh<N+1>-instr-pointcut-completeness`.
- Kotlin `suspend` / CPS state-machine detection (INV-INS-61 residual). Deferred.
- `Format35c` for registers `>v15` (INV-INS-32 residual). Orthogonal mechanic — register escalation, not binding resolution. Deferred.
- `InheritanceResolver` Phase 2 expansion for custom Cipher subclasses (`wrappersAliasedToSubtype` residual). Deferred.
- Building a centralised `rv-validator` Python module or `.github/workflows/` CI pipeline for the oracle gate. The change extends the existing bash orchestrator only.
- Re-running the full 2026-05-08 campaign (190 APKs × 11 tools × 3 timeouts × 3 reps). Documented as a separate decision in `RISKS.md`.
- Touching the AJC variant. AJC has its own structural defects (gh54 R8/Compose residuals) and uses a completely different emission path.

## Decisions

### D1: Bindings resolve by name across all emitters

**Decision**: Every binding name appearing in `parameters[]`, `returning[]`, `throwing[]`, or `monitorCalls[i].args[]` resolves to a register via a single lookup table populated by `resolveBindings`. The order of registers in the emitted `invoke-static` is dictated by the order of names in `monitorCalls[i].args[]`, not by the order of registers in the matched invoke site.

**Rationale**: gh52 ADR D13 already specified "by name", but the constructor + returning path silently regressed to ordinal-with-shift. Re-affirming "by name" as the single contract spanning all five emitters makes it possible to add the cross-product unit test (`{emitter, invoke-kind, binding-kind}`) without designing a separate contract per emitter.

**Alternatives considered**:

- *Ordinal with explicit shift table per invoke kind*: rejected because the shift logic is exactly what produced bug #1 — every new invoke kind would require its own shift constant and every binding kind would compound the table.
- *Type-driven resolution* (resolve by parameter type, not name): rejected because two parameters can share a type (e.g. `Cipher.update(byte[] input, int inputOffset, int inputLen, byte[] output)`).

### D2: `$return` synthetic key lives in `Match.argBindings`

**Decision**: `PointcutMatcher.buildCallMatch` peeks at `insns[idx+1]` and, if the opcode is `MOVE_RESULT`, `MOVE_RESULT_OBJECT`, or `MOVE_RESULT_WIDE`, stores the destination register under the synthetic key `$return` in `Match.argBindings`. The peek is skipped for constructors (no `move-result*` is emitted for `<init>`).

**Rationale**: `Match.argBindings` already exists and is consumed by `resolveBindings`. Adding one synthetic key keeps the type contract uniform (`Map<String, Integer>`). The alternative — a separate `Optional<Integer> returnRegister` field on `Match` — would force every consumer to check both locations, complicating the named-binding lookup.

**Alternative considered**: making `$return` part of `argBindings` indexed as `argN+1` (where N is the parameter count). Rejected because the existing `argNN` keys are positional in the user-parameter list and conflating "return value" with "extra positional arg" misleads test authors.

### D3: Constructor identification requires both opcode and descriptor agreement

**Decision**: `buildCallMatch` captures `targetRegister = regs[0]` only when `cp.isConstructor() == true` AND the matched invoke is `invoke-direct` to an `<init>` method. The descriptor predicate alone is necessary; the opcode predicate alone is insufficient because `invoke-direct` is also used for private method calls and super-`<init>` chaining outside the advice contract.

**Rationale**: bug #1 had a subtle false-friend in proposed Fix #1 — removing `cp.isConstructor()` from `treatAsZeroOffset` without preserving the descriptor predicate would have left private `invoke-direct` calls with a captured receiver they were not asking for. The two-predicate gate is defence in depth.

**Alternative**: trust only `cp.isConstructor()`. Acceptable for the smoke, but a future emitter that consumes `Match.targetRegister` directly (e.g. for a `target(this)` binding on a private-method advice) would be at risk. The two-predicate gate is documented in the constructor invariant.

### D4: Layer 3 oracle gate is mandatory only for `cryptoapp`

**Decision**: `--mandatory` (on the `layer3` subcommand) is passed to `ValidationCli` exclusively when `cryptoapp.apk` appears in the result set. Other APKs continue to run Layer 3 in diagnostic mode. The orchestrator (`run_phase5_validators.sh`) detects `cryptoapp` in the result directory and adds the flag conditionally.

**Rationale**: authoritative ground-truth oracles exist for `cryptoapp.apk` (8 events, hardcoded by the cryptoapp authors) and `hateitorrateit-oracle.yaml` (secondary). The other 189 APKs in the corpus have no authoritative oracle — promoting Layer 3 to mandatory for them would force the gate to either accept any non-empty trace (false positives) or fail every run (false negatives). The bug we are blocking only manifested in cryptoapp because that is the only smoke we ran with a constructor-heavy oracle.

**Alternative considered**: extend the oracle inventory to 20-30 APKs (Layer 4 sampling). Out of scope here — it requires manual ground-truth derivation. Documented in `RISKS.md` as a future follow-up.

### D5: `DexWeaver.WeaveReport.plansSkippedUnresolvedBinding` is observable, not silent

**Decision**: when `resolveBindings` cannot resolve a binding name to a register, the emitter logs a `WARN` and increments `DexWeaver.WeaveReport.plansSkippedUnresolvedBinding`. The advice is skipped at that site — no malformed `invoke-static` is emitted with `v0` substituted for the unresolved name.

**Rationale**: silent emission of malformed invokes was the cause of the six-month latency. An observable counter surfaces every future regression in `instrument_results.json` immediately.

**Alternative**: throw an exception. Rejected because some skips are legitimate (e.g. an advice declares `returning(unused)` but the original code discards the return value, so no `move-result*` exists — the advice cannot fire at that site, but the rest of the APK should still be instrumented).

### D6: Mandatory gate signals through the existing `Report(passed=false)` contract, not a new exit code

**Decision**: When `layer3 --mandatory` detects a deviation, the subcommand builds `Report(passed=false)` and calls `emitAndExit(parent, report)`. The existing `Report.exitCode()` (`validator/Report.java:44-46`) maps that to exit `1`. The runner aggregator (`scripts/run_phase5_validators.sh:73-85`) already treats `rc==1` as `GATES_FAILED`; any other non-zero rc is classified as diagnostic. No new exit code is introduced.

**Rationale**: an earlier draft of this design proposed exit code `2` for "mandatory gate failure" to distinguish it from `1` (malformed input). That conflicted with the actual `Report.exitCode()` contract — `Report` is the universal validator response object and changing its surface for one subcommand fragments the contract. The runner script also does not treat `rc==2` as failure — it logs diagnostic and continues. Routing through `Report(passed=false)` reuses the existing aggregator semantics without modification.

**Alternative considered**: extend `Report` with a tri-state (`PASS`/`FAIL`/`MANDATORY_FAIL`) and update `exitCode()` to emit `0`/`1`/`2`. Rejected because:
1. The semantic distinction `MANDATORY_FAIL` vs `FAIL` collapses to "gate failed" from the operator's perspective — both block the build.
2. The runner script's exit-code aggregator (`GATES_FAILED` if any `rc==1`, otherwise `GATES_DIAGNOSTIC`) treats anything beyond `1` as diagnostic; emitting `rc==2` would silently downgrade real failures to advisory.
3. Tri-state ripples to every layer's Report construction (layer1..layer5 each need a `--mandatory` analogue) — speculative complexity for a single use case.

### D7: Instruction-stream propagation through `Context`, typed as `List<? extends Instruction>`

**Decision**: `PointcutMatcher.match(...)` (the public API at `PointcutMatcher.java:63-68`) gains a `List<? extends Instruction> instructions` parameter; `Context` (`PointcutMatcher.java:321-336`) gains a matching field; `buildCallMatch` reads the list from `Context` to peek `idx+1` for `move-result*`. The list is typed as `List<? extends Instruction>` — the `org.jf.dexlib2.iface.Instruction` interface — not `List<BuilderInstruction>`.

**Rationale**: an earlier draft typed the parameter as `List<BuilderInstruction>` (from the `dexlib2-builder` module). That would couple `pointcut-engine` to `dexlib2-builder`, which is a build-only dependency in the current Maven graph — the matcher operates exclusively on the read-side `iface.Instruction` abstraction. Keeping the type as `List<? extends Instruction>` preserves the module layering. Concrete callers (in `dex-mutator` / `advice-emitter`) pass either the immutable instruction list of a `Method` or an in-flight `MutableMethodImplementation.getInstructions()` — both satisfy the wildcard.

The `?` (extends) bound is needed because the caller may hold a `List<BuilderInstruction>` (which extends `Instruction`), and we want to accept it without forcing the caller to copy/cast.

**Alternative considered**: stash the list on `Context` only and keep `match()`'s API unchanged by adding a `match(pe, classDef, method, instructions)` overload. Rejected — every existing caller of `match()` already has the instruction list available (it iterates over instructions to call `match` per index), so requiring the parameter at the public API site is honest about the data dependency. The overload would be syntactic sugar with no semantic benefit.

**Impact on callers**: every call site of `PointcutMatcher.match(...)` (grep `\\.match\\(` across `dex-mutator`, `advice-emitter`, and any test fixture) must be updated to pass `instructions`. Compilation surface is bounded — `PointcutMatcher.match` is the only public method touched.

## API Design

### `Match` (existing, extended documentation)

```
final class Match {
    final int targetRegister;            // -1 for static; regs[0] for constructor/virtual
    final Map<String, Integer> argBindings;
    //   keys: "arg00".."argNN"            → positional user parameters (regs[baseOffset + i])
    //         "$return"                   → destination of trailing move-result*
    //                                       (absent for constructors and for invokes
    //                                        whose return is discarded by the caller)
    final boolean isConstructor;         // NEW: load-bearing predicate consumed by
                                         // resolveReturningRegister. Set to true only
                                         // when both CallPC.isConstructor() and the
                                         // <init> opcode/method-name predicate agree
                                         // (defence-in-depth, D3).
    final PointcutExpression matchedAgainst;  // existing: debugging/audit reference
}
```

### `PointcutMatcher.match` (extended public API — see D7)

```
Optional<Match> match(
    PointcutExpression pe,
    ClassDef classDef,
    Method method,
    Instruction instruction,
    int instructionIndex,
    int totalInstructions,
    List<? extends Instruction> instructions    // NEW (D7) — for move-result* peek
);
```

`Context` (`PointcutMatcher.java:321-336`) gains a matching `final List<? extends Instruction> instructions` field, populated by the constructor. All existing fields preserved.

### `PointcutMatcher.buildCallMatch` (rewrite)

```
Match buildCallMatch(
    CallPC cp,
    MethodReference mr,
    int[] regs,
    boolean isStaticInvoke,
    List<? extends Instruction> instructions,
    int invokeIndex
);
```

**Preconditions**: `cp != null`, `mr != null`, `regs != null`, `instructions != null`, `0 <= invokeIndex < instructions.size()`.

**Postconditions**:

- If `cp.isConstructor() && !isStaticInvoke`, then `Match.targetRegister == regs[0]`, `baseOffset` for arguments is `1`, and `argBindings` does not contain `"$return"`.
- If `isStaticInvoke`, then `Match.targetRegister == -1`, `baseOffset` for arguments is `0`.
- Otherwise (virtual instance), `Match.targetRegister == regs[0]`, `baseOffset` is `1`.
- If `!cp.isConstructor()` and `invokeIndex + 1 < instructions.size()` and `instructions[invokeIndex+1].opcode ∈ {MOVE_RESULT, MOVE_RESULT_OBJECT, MOVE_RESULT_WIDE}`, then `argBindings.get("$return") == instructions[invokeIndex+1].registerA`.

**Errors**: throws `IllegalArgumentException` if `regs.length < baseOffset + parameterCount` (i.e. malformed invoke).

### `MonitorInvokeBuilder.resolveReturningRegister` (new)

```
static Integer resolveReturningRegister(Match match);
```

**Returns**:

- `match.targetRegister` when `match.isConstructor == true && match.targetRegister >= 0`.
- `match.argBindings.get("$return")` otherwise (may be `null`).

(`Match.isConstructor` is the new boolean field added in task 1.2; reading the constructor predicate through this field — rather than via an `instanceof CallPC` downcast on `matchedAgainst` — keeps `MonitorInvokeBuilder` from depending on `pointcut-engine` descriptor types. Trade-off: the field duplicates information derivable from `matchedAgainst instanceof CallPC && ((CallPC) matchedAgainst).isConstructor()`. The duplication is justified because `MonitorInvokeBuilder` is the only consumer and the `instanceof` downcast would re-introduce a `pointcut-engine` import in the emitter module — the field's purpose is layering, not new information.)

**Caller contract**: `resolveBindings` substitutes the returned value into the bindings map only when non-null. If null, the binding is left unresolved and the emitter follows the unresolved-binding policy (D5).

### `ValidationCli` (extended — `layer3` subcommand)

`ValidationCli` uses picocli with subcommands (`inventory`, `mapping`, `parity`, `oracles`, `preflight`, `layer1`..`layer5`, …). The change extends the existing `layer3` subcommand only. The flag works in **both modes** (`analyze` and `--batch`) — see `tasks.md` task 4.2 for the rationale and per-mode behaviour.

```
ValidationCli layer3 [analyze|--batch options...] [--mandatory]
  --mandatory   When set, any deviation from the oracle in either analyze or
                batch mode produces Report(passed=false), which the existing
                Report.exitCode() maps to exit 1. Without this flag (default),
                Layer 3 remains diagnostic (warnings only, Report(passed=true),
                exit 0 even on deviation).
```

Exit codes: `0` success / diagnostic-only deviation; `1` mandatory-gate deviation OR malformed input / I/O error (existing semantics — see `Report.exitCode()` at `validator/Report.java:44-46`). No new exit code is introduced (see D6).

### `scripts/run_phase5_validators.sh` (extended)

The orchestrator detects whether any APK in the dex result directory matches `cryptoapp*`. If yes, it appends `--mandatory` to the `layer3 --batch` subcommand invocation at `scripts/run_phase5_validators.sh:114`. The script also propagates the existing `ValidationCli` exit code via the `run_layer` aggregator (`rc==1 → GATES_FAILED`). No new exit-code plumbing is needed.

The hardcoded paths to `rvsec-gh52-instr-dexlib2` (`THRESHOLDS` default at L41, `REPO_ROOT` at L43, `VALIDATOR_DIR` at L44) are replaced with derivation from the script's own location, with env-var overrides (`RVSEC_REPO_ROOT`, `RVSEC_VALIDATOR_DIR`) for operators who maintain side-by-side clones. See task 4.3.

In addition, the script gains a `jq`-based `plansSkippedUnresolvedBinding` guard for cryptoapp runs (task 4.3) — replacing the manual `cat instrument_results.json` check originally proposed as task 5.5.

## Data Flow

```
Pointcut JSON descriptor (monitors/*.json)
      │
      │  CallPC { isConstructor, returnType, parameters[], … }
      ▼
PointcutMatcher.matchCall(insn, descriptor)
      │
      │  iterates DEX instructions, locates invoke matches
      ▼
PointcutMatcher.buildCallMatch(cp, mr, regs, isStatic, insns, idx)
      │
      │  Match { targetRegister, argBindings{"arg00"…,"$return"}, isConstructor, matchedAgainst }
      ▼
For each AdviceDescriptor matching the site:
      │
      ▼
MonitorInvokeBuilder.resolveBindings(advice, match)
      │
      │  Map<String,Integer> { target:r0, arg00:r3, arg01:r0, returning_name:r4, "$return":r5, … }
      ▼
MonitorInvokeBuilder.registersFor(monitorCall.args[], nameToReg)
      │
      │  int[] regs       (by name, no literal-0 fallback)
      ▼
MonitorInvokeBuilder.buildInvoke(targetMethod, regs)
      │
      │  emit-invoke-static {r3, r0, r4} → MultiSpec_1RuntimeMonitor.<event>
      ▼
InstructionInjector.insertAfter(insns, idx, [newInsn])
      │
      │  (move-result* handling already correct — INV-INS-27)
      ▼
DexWeaver.weaveAdvice(…)
      │
      ▼
Final classes.dex
```

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `IllegalArgumentException` from `buildCallMatch` | Malformed invoke (regs too short) | Throw with site location; emitter skips the site | None (skip & log; do not abort APK weaving) |
| `null` from `resolveReturningRegister` for an advice declaring `returning` | No `move-result*` after non-constructor invoke | Log `WARN`; increment `plansSkippedUnresolvedBinding`; skip advice at this site | Site contributes no event; other sites unaffected |
| `null` for an `args(name)` binding | Matcher did not locate parameter | Same as above (unresolved-binding policy D5) | Same |
| `ValidationCli` exits `1` (`Report(passed=false)`) on cryptoapp deviation with `--mandatory` | Layer 3 oracle mismatch (mandatory gate triggered, see D6) | Orchestrator's `run_layer` aggregator classifies `rc==1` as `GATES_FAILED` and exits non-zero; CI / smoke run visibly fails | Investigate trace, fix bug, re-run |

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|---|---|---|
| Fix #1 introduces a regression for non-constructor `invoke-direct` calls (private methods, super-`<init>`) | New `VerifyError` family in the wild | Constructor predicate is gated by `cp.isConstructor()` (D3); add parametrized test cases for private-direct and super-direct invokes confirming `targetRegister` behaviour |
| Fix #2 changes resolution semantics for advice that previously "worked" by coincidence on `v0` | Previously-silent successes may now be `plansSkippedUnresolvedBinding` warnings | Acceptable — the prior "success" was emitting a `v0` value at the return slot, which had no defined semantics. The new warning surfaces a previously hidden defect. Document expected `WARN` count delta after fix in validation report. |
| Cryptoapp oracle gate triggers false positives if `ape` exploration fails to reach all 8 violation sites within timeout | Smoke gate blocks builds without a real bug | Use 300s timeout (gh52 baseline) and `ape:sata_mop` (deterministic for cryptoapp); document deterministic re-runs in `RISKS.md`. If `ape` regresses on cryptoapp, the gate signals a different real problem (`ape` regression). |
| Re-running the stratified 9-APK sample (top-3 + median-3 + tail-3) from 2026-05-08 reveals a new `VerifyError` family not covered by Fix #1+#2 | Scope creep | Triage: if the new family is binding-related, expand this change; if orthogonal (e.g. Format35c >v15), file as gh<N+1> and ship gh56 with the documented residual count. The tail-3 stratum is specifically chosen to surface tail patterns (R8-obfuscated `<init>`, Tink/Okio internals, `args(name)` unresolved) absent from a pure top-10 selection. |
| Full campaign re-run cost (85 h GCP) | Schedule risk for ASE journal | Decision documented in `RISKS.md`. Default: re-run only the affected slice (~6 h GCP for 9 APKs). Full re-run is a separate go/no-go after the slice confirms zero `VerifyError` AND non-negative event/coverage delta. |
| `MonitorInvokeBindingTest` type-matching is circular — fixture re-uses builder logic to derive "expected type per register" | Internal-consistency test passes while the bug remains (this is the vector through which gh52 missed the bug) | Test fixture MUST declare a hand-written `Map<Integer, String> expectedTypeByRegister` per scenario, sourced from the bytecode test input (which is also hand-written), NOT from any helper that re-parses the monitor signature with the same logic the builder uses. See `tasks.md:3.2` and `spec.md` Named-Binding Contract. |
| Cryptoapp oracle 8/8 binary gate fails for non-bug reasons (wrapper regression, Ape determinism) | False positive blocks build with no real binding bug | Document the two pivotal events (`#7 KeyPair.<init>`, `#8 SecretKeySpec.<init>`) explicitly in `spec.md`; require 2/2 on those events as a separate sub-criterion alongside 8/8 totals. If the 6/8 wrapper-derived events fail but the 2 pivotal events pass, the failure is not a binding regression — escalate to wrapper investigation, not a gh56 revert. |
| `IvParameterSpec.<init>` documented as affected in `docs/20260514_erro.md:§2.4` but absent from oracle and tests | Silent regression on a known affected class | Add `IvParameterSpec.<init>` case to `DexWeaverConstructorAdviceTest` (task 3.4). Oracle YAML is invariant under this change; the test case provides the regression seal at unit level. |

## Testing Strategy

| Layer | What to test | How | Count |
|---|---|---|---|
| Unit (Java) | `buildCallMatch` offset and `$return` capture | JUnit5 `@ParameterizedTest` in `PointcutMatcherConstructorTest` | 8 cases: constructor (no MR), virtual (MR-object), virtual (no MR), static (MR-wide for long/double), static (no MR), private invoke-direct non-`<init>` (D3 guard), `super.<init>` chain, descriptor-disagree edge (D3 defence-in-depth) |
| Unit (Java) | `resolveBindings` cross-product | JUnit5 `@ParameterizedTest` in `MonitorInvokeBindingTest` covering `{Before, After, AfterReturning, AfterThrowing, StaticInit} × {constructor, virtual, static} × {args, target, returning, throwing}` validating register-to-type correspondence against an independent fixture type table | ~24 cases (only valid combinations; invalid combinations enumerated up-front, e.g. `StaticInit × constructor`, `Before × returning`, `AfterReturning × throwing`). Plus 2 additional cases: `args(name)` unresolved + counter increment; `returning(name)` with high-register `>v15` forcing `Format35c → 3rc` escalation. |
| Unit (Java) | `DexWeaverConstructorAdviceTest` extension | Add `SecretKeySpec.<init>` + `returning(spec)` and `IvParameterSpec.<init>` cases; assert emitted `invoke-static` registers vs monitor signature | +2 cases |
| Unit (Java) | `ValidationCli layer3 --mandatory` option | New `Layer3MandatoryTest` | 3 cases (deviation fails with exit `1`, full match passes with exit `0`, no oracle stays diagnostic with exit `0`) |
| Integration (smoke) | Cryptoapp end-to-end | Run `rv-experiment run --tools ape --timeout 300 --instrumentation-variant dexlib2 --specification-set jca --apks-dir apks_examples`; validate trace via `run_phase5_validators.sh` (the orchestrator auto-appends `--mandatory` to the `layer3 --batch` subcommand when cryptoapp is in the result set; also fails fast via `jq` guard if `plansSkippedUnresolvedBinding > 0`) | 8 / 8 oracle total + 2 / 2 on pivotal events (`#7 KeyPair.<init>`, `#8 SecretKeySpec.<init>`); 0 `VerifyError`; `plansSkippedUnresolvedBinding == 0` |
| Integration (sample) | Stratified 9 APKs from 2026-05-08 (top-3 + median-3 + tail-3 by `VerifyError` count) | Same command, restricted APK set, single timeout / repetition, paired with pre-fix baseline run | 0 `VerifyError` in all 9; event-count delta ≥ 0 per APK; coverage delta ≥ 0 per APK |
| Regression (full) | All existing Java unit tests | `mvn test` at aggregator level | Unchanged pass count |
| Regression (Python) | `rv-instrumentation-dexlib2` wrapper tests | `uv run pytest modules/rv-instrumentation-dexlib2/tests/` | 16 existing tests pass unchanged |

## Open Questions

- *Should the `$return` synthetic key be visible to user-authored advice expressions* (e.g. `returning($return)`)? Answer: no — the synthetic key is private to the matcher / resolver. User-authored expressions use named bindings only. The synthetic key is plumbing.
- *Does the cryptoapp oracle gate need a tolerance for non-determinism in `ape` exploration*? Answer: no — `ape:sata_mop` is the deterministic mode (gh52 INV-INS-67). If a regression breaks determinism, that is a separate bug and the oracle gate failure is the right signal.
- *Should we re-run the full 2026-05-08 campaign*? Decision deferred to `RISKS.md`; default is the affected slice unless the slice surfaces a new failure family.
