# Design: Fix WrapperEmitter trailing-varargs fixed-prefix over-matching

**GitHub Issue**: [#81](https://github.com/PAMunb/rvsec/issues/81)

## Context

The dexlib2 engine (gh52) wraps `after`-side advices via static wrappers in `mop.MonitorWrappers` to avoid DEX register aliasing between the returning value and argument registers. `WrapperEmitter.expandCallTarget` resolves each advice's `call(...)` pointcut into concrete android.jar overloads (via `AndroidClassIndex`); each overload becomes one wrapper. The production path always supplies a real index (`cli/BatchRunner` constructs `AndroidClassIndex(cfg.androidJar())` and passes it to `WrapperEmitter.generate`), so the index-driven expansion is the production behavior.

Two components disagree about how a trailing `..` is represented:

- `PointcutExpressionParser.splitParams` strips a trailing `..` from the parameter list and sets `CallPC.varargs = true`. `paramSpecs` is exactly the fixed positional head (`(String, ..)` → head `[String]`, varargs true). A non-trailing `..` (`(String, .., int)`) is kept as a `ParamSpec` with descriptor `".."`.
- `expandCallTarget` assumes the `..` is still the last element of `specs` and computes `fixedPrefix = specs.size() - 1` for trailing varargs, then clamps negative values to 0.

Because the parser already removed the `..`, the `- 1` drops a real fixed parameter: the matching loop iterates `i < fixedPrefix` and never verifies the last fixed parameter, and the arity floor (`m.paramFqns.size() < fixedPrefix`) under-counts by one. `call(public byte[] Cipher.doFinal(byte[], ..))` therefore matches 3 fixture overloads including the zero-arg `doFinal()` instead of the correct 2. The same method also contains a dead branch (`if (i == specs.size() - 1) hasTrailingVarargs = true;` inside the specs loop) that can only fire for input the parser never produces.

Related requirement: FR02 (APK Instrumentation with Monitors). Corpus severity: latent — see proposal.

## Architecture

No structural change. The fix is confined to one method in one class of the `advice-emitter` Maven submodule:

```
descriptor JSON ──▶ PointcutExpressionParser ──▶ CallPC {paramSpecs=head, varargs} 
                                                     │
                                                     ▼
BatchRunner ──▶ WrapperEmitter.generate ──▶ expandCallTarget(ct, resolver, index)   ◀── fix here
                                                     │
                                                     ▼
                                            List<ConcreteCall> ──▶ wrapper methods in mop.MonitorWrappers
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `WrapperEmitter.expandCallTarget` | Resolve a `call(...)` pointcut to concrete android.jar overloads | `CallPC`, `TypeResolver`, `AndroidClassIndex` | `List<ConcreteCall>` |
| `PointcutExpressionParser.splitParams` | Split a param list into fixed head + varargs flag (unchanged, authoritative) | param-list text | `CallPC.ParamList` |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| Trailing-Varargs Fixed-Prefix Fidelity (delta spec) | `WrapperEmitter.expandCallTarget` — `fixedPrefix = specs.size()` | `WrapperEmitterTest.indexExpansionAppliesTrailingVarargsPrefixFilter` |
| INV-INS-103 (parser head is authoritative; `".."` in specs → reject) | same method — `".."` `ParamSpec` returns empty list | `WrapperEmitterTest.literalFallbackSkipsMidListWildcardParam` + index-path middle-`..` test |
| Empty head `(..)` match-anything unchanged | same method — `fixedPrefix = 0` naturally | `WrapperEmitterTest.expandsVarargsViaIndex` |

## Goals / Non-Goals

**Goals:**
- Every fixed parameter of a trailing-varargs pointcut (including the last) is verified against candidate overloads.
- Dead dual-representation code removed; `ct.varargs()` is the single varargs signal (P3).
- Regression test committed with the fix; existing suite stays green.

**Non-Goals:**
- No parser changes — re-inserting a trailing `..` into `paramSpecs` would ripple into `PointcutMatcher` and every other `pointcut-engine` consumer.
- No change to `literalFallback` (the index-less path already vetoes varargs).
- No change to `before`-advice inline emission (`BeforeEmitter` path does not use `expandCallTarget`).
- D1 (descriptor-reader missing-field validation), D2 (DexWeaver skip-WARN discriminator), and the deprecated `hasAmbiguousObjectParam(WrapperEntry)` dead code are tracked separately and stay out of this change.

## Decisions

**D-1: Fix in `expandCallTarget`, not the parser (Option B of the investigation).** The parser's representation (head + flag) is clean and consumed correctly by `PointcutMatcher`; only `expandCallTarget` misreads it. Changing the parser would have a much larger blast radius. Alternative rejected: normalizing `paramSpecs` to re-include the trailing `..`.

**D-2: Delete the dead branch instead of keeping it defensively.** The branch `if (i == specs.size() - 1) hasTrailingVarargs = true;` is unreachable for parser input (the parser never leaves a trailing `..` in the head; the only sequence that could reach it is the degenerate `(.., ..)`, which no corpus spec uses and which users should write as `(..)`). Keeping it would preserve the dual-representation trap that caused the bug (P3: no dead code). After the fix, any `".."` descriptor found in `specs` returns the empty list (unsupported non-trailing wildcard).

**D-3: Drop the `< 0` clamp.** With `fixedPrefix = specs.size()` the value is never negative (`(..)` gives 0). The clamp only existed to patch the `- 1` underflow.

## API Design

### `expandCallTarget(CallPC ct, TypeResolver resolver, AndroidClassIndex index, boolean instanceAllowed) → List<ConcreteCall>`

Signature unchanged. Contract after the fix:

- **Precondition**: `ct.paramSpecs()` is the parser-produced fixed head; `ct.varargs()` is the trailing-varargs flag.
- **Postcondition (trailing varargs)**: returns exactly the overloads with `paramCount >= specs.size()` whose first `specs.size()` parameters all match the corresponding `ParamSpec` patterns (and whose return type matches, when specified).
- **Postcondition (non-varargs)**: unchanged — exact arity plus full positional match.
- **Rejection**: any `".."` descriptor inside `specs` (non-trailing wildcard) returns an empty list.

## Data Flow

`descriptor JSON → CallPC (head, varargs) → expandCallTarget filters index.methods(declFqn, name) by fixed prefix + return pattern → ConcreteCall list → one wrapper method each → dex-mutator rewrites call sites`.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| (none new) | — | Unmatchable/unsupported pointcuts yield an empty list | Caller falls back (`literalFallback`) or skips the advice |

## Risks / Trade-offs

- [Match sets shrink for future discriminating pointcuts] → intended: that is the bug being fixed. Corpus scan confirms the four existing `after`-side `getInstance(String, ..)` cases are unaffected (all overloads `String`-first).
- [Degenerate `(.., ..)` pointcut changes behavior from match-all to rejected] → acceptable: no corpus spec uses it, semantically it should be written `(..)`, and rejecting is safer than silently matching everything.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (JUnit 5) | Fixed-prefix filter under trailing varargs (`doFinal(byte[], ..)` → 2 overloads, not 3) | ASM in-memory android fixture jar (existing `buildFixture`) | 1 new (already written, RED) |
| Unit (existing) | Empty head `(..)` (3 overloads), middle-`..` rejection, literal fallback paths, corpus-shaped `getInstance` cases | existing `WrapperEmitterTest` suite | must stay green |
| Suite | Full `advice-emitter` module | `mvn -pl advice-emitter -am test` | all green |

## Open Questions

(none — investigation complete; see `docs/handoff_dexlib2_wrapperemitter_varargs_overmatch.md` for the full evidence trail)
