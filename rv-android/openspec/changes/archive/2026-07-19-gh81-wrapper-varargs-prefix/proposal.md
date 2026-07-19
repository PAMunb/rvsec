# Proposal: Fix WrapperEmitter trailing-varargs fixed-prefix over-matching

**GitHub Issue**: [#81](https://github.com/PAMunb/rvsec/issues/81)
**Track**: Fast-Forward SDD
**Date**: 2026-07-19

## Why

`WrapperEmitter.expandCallTarget` (dexlib2 DEX-native engine, `advice-emitter` submodule) over-matches android.jar overloads for `call(...)` pointcuts that end with trailing varargs `..`: it computes the fixed-parameter prefix as `specs.size() - 1`, but the pointcut parser has already stripped the trailing `..` out of `paramSpecs` (it becomes the `CallPC.varargs` flag), so the subtraction drops a real fixed parameter. The last fixed parameter of the pointcut is never verified against candidate overloads, and spurious overloads get wrapped — `call(public byte[] Cipher.doFinal(byte[], ..))` matches the zero-arg `doFinal()` (3 overloads instead of the correct 2). The bug is reproduced by the failing regression test `WrapperEmitterTest.indexExpansionAppliesTrailingVarargsPrefixFilter` (`expected: <2> but was: <3>`).

Severity today is **latent**: a full scan of the MOP spec corpus (`jca`, `generic`, `generic_new`) shows the only `after`-side trailing-varargs pointcuts with a non-empty fixed prefix are four `getInstance(String, ..)` events (SecureRandomSpec g2/g4, KeyManagerFactorySpec g2, TrustManagerFactorySpec g2), and every `getInstance` overload of those three classes is `String`-first — the dropped check happens not to change the match set. The discriminating cases (`Cipher.init(int, Key, ..)` vs `init(int, Certificate, ..)`) are `before` advices, which use the inline emitter path and are never wrapped. But any future `after` advice whose trailing-varargs prefix discriminates between overloads would silently feed the monitor wrong events — a correctness landmine in the production path (`BatchRunner` always supplies a real `AndroidClassIndex`, so the buggy index path is the production path).

## What Changes

- Fix the `fixedPrefix` arithmetic in `WrapperEmitter.expandCallTarget`: for trailing-varargs pointcuts the parser guarantees `paramSpecs` is exactly the fixed head, so the correct prefix length is `specs.size()` (no `- 1`, no `< 0` clamp).
- Delete the dead dual-representation handling inside `expandCallTarget`: the branch that sets `hasTrailingVarargs = true` when a `".."` `ParamSpec` is the last element of `specs` is unreachable for parser-produced input (the parser never leaves a trailing `..` in the head). Any `".."` inside `specs` is necessarily a middle `..` → unsupported → return empty list. `hasTrailingVarargs = ct.varargs()` becomes the single source of truth (P3: dead code deleted, not kept).
- Commit the regression test `indexExpansionAppliesTrailingVarargsPrefixFilter` (already written, currently RED) together with the fix.
- Add a spec scenario capturing **trailing-varargs prefix fidelity** to the instrumentation capability; reconcile the wrapper-generation invariant wording (INV-INS-66/68) in the module-local `architecture.md`.
- The parser (`PointcutExpressionParser`) is **not** changed — its representation is correct and authoritative.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `instrumentation`: the "DEX-Native APK Instrumentation Pipeline" requirement gains a scenario constraining wrapper overload expansion under trailing varargs — WHEN a `call(...)` pointcut ends with `..` and has a non-empty fixed parameter prefix, THEN every fixed parameter (including the last) must match the candidate overload's leading parameters, AND candidates with fewer parameters than the prefix or with non-matching leading parameters are rejected.

## Impact

- **Modules**: Java-side only — `rvsec-instrumentation-dexlib2/advice-emitter` (`WrapperEmitter.java` + `WrapperEmitterTest.java`). No Python module changes; the Python wrapper `rv-instrumentation-dexlib2` consumes the jar unchanged.
- **Requirements**: FR02 (APK Instrumentation with Monitors) — wrapper expansion feeds the monitor events for `after`-side advices; over-matching would corrupt monitored-operation streams.
- **Behavioral impact on the current corpus**: none — the four `after`-side `getInstance(String, ..)` events keep their match sets (all overloads are `String`-first); `(..)` empty-prefix and middle-`..` behavior unchanged. The fix removes spurious wrappers only for pointcuts whose last fixed parameter discriminates between overloads (none in the corpus today).
- **Docs**: module-local `architecture.md` invariant text (INV-INS-66/68) updated to state the prefix-fidelity rule.
