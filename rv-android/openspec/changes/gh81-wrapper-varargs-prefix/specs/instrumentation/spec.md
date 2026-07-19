# Delta Spec: instrumentation — trailing-varargs fixed-prefix fidelity in wrapper expansion

## Purpose

The dexlib2 DEX-native instrumentation pipeline wraps `after`-side advices through static wrapper methods (`mop.MonitorWrappers`) instead of inlining them, because the returning value and argument registers can alias at the call site. To emit a wrapper, `WrapperEmitter.expandCallTarget` (module `rvsec-instrumentation-dexlib2/advice-emitter`) must resolve the advice's `call(...)` pointcut into the concrete android.jar overloads it can legally match: each matched overload becomes one wrapper, and the dex-mutator rewrites matching call sites to route through it. Every overload admitted here directly determines which application invocations feed monitor events — an over-broad match set silently reports events for API calls the MOP specification never asked to observe.

AspectJ-style pointcuts express "these leading parameters, then anything" with a trailing `..`, as in `call(public static SecureRandom SecureRandom.getInstance(String, ..))`. The pointcut parser (`PointcutExpressionParser.splitParams`) represents this by stripping the trailing `..` from the parameter list and setting the `CallPC.varargs` flag: `paramSpecs` holds exactly the fixed positional head (`[String]` in the example), and `varargs=true` marks the open tail. A `..` appearing in a non-trailing position (`(String, .., int)`) is a different construct — "any number of parameters HERE, then these" — which has no finite lowering to concrete Java signatures and is rejected wholesale by the expansion.

This delta pins the fidelity contract between those two components: overload expansion MUST treat the entire parsed head as fixed. Every fixed parameter — including the last one — must match the candidate overload's leading parameters before the candidate is wrapped. The requirement exists because the two representations were historically conflated: expansion assumed the `..` was still the last element of the head and subtracted one from the prefix length, leaving the final fixed parameter unverified, so `call(public byte[] Cipher.doFinal(byte[], ..))` also wrapped the zero-argument `doFinal()`.

## Data Contracts

### Input
- `ct: CallPC` — parsed `call(...)` pointcut: `paramSpecs` (fixed positional head, trailing `..` already stripped by the parser), `varargs: boolean` (true iff the source ended the list with `..`), plus return type, declaring type, and method name.
- `index: AndroidClassIndex` — android.jar overload index; `methods(classFqn, name, onlyStatic)` returns the class's own declared overloads.

### Output
- `List<ConcreteCall>` — the concrete overloads the pointcut matches; each becomes one wrapper method. Empty when the class or method is absent from the index, or when the pointcut contains a non-trailing `..`.

### Side-Effects
- **[Wrapper source]**: each returned overload materializes as a static method in `mop/MonitorWrappers.java`; the dex-mutator rewrites matching call sites to `invoke-static` through it.

### Error
- (none — unmatchable or unsupported pointcuts yield an empty list, and the caller falls back or skips)

## Invariants

- **INV-INS-103**: For a `call(...)` pointcut with trailing varargs, `CallPC.paramSpecs` is exactly the fixed positional head and `CallPC.varargs` is the sole varargs signal. Overload expansion MUST verify all `paramSpecs.size()` fixed parameters positionally against a candidate overload's leading parameters and MUST reject candidates with fewer parameters than the fixed head. A `".."` descriptor inside `paramSpecs` is necessarily a non-trailing `..` and MUST cause the whole pointcut to be rejected (empty expansion).

## ADDED Requirements

### Requirement: Trailing-Varargs Fixed-Prefix Fidelity in Wrapper Overload Expansion

When resolving a `call(...)` pointcut with trailing varargs (`CallPC.varargs == true`) against the android.jar overload index, `WrapperEmitter.expandCallTarget` MUST treat the entire `paramSpecs` list as the fixed parameter prefix: a candidate overload is admitted only if it has at least `paramSpecs.size()` parameters AND every fixed parameter (including the last) matches the candidate's parameter at the same position under the pointcut's type-pattern rules (exact FQN, subtype `+`, primitives, arrays). Candidate overloads with fewer parameters than the fixed prefix, or whose leading parameters do not all match, MUST be rejected.

The parser's representation is authoritative: `PointcutExpressionParser.splitParams` strips a trailing `..` from the head and sets the varargs flag, so expansion MUST NOT assume a `".."` element remains in `paramSpecs`. Any `".."` descriptor actually present in `paramSpecs` is a non-trailing `..` and MUST cause the expansion to return an empty list (no finite lowering exists).

An empty fixed head (`(..)`) MUST keep its match-anything semantics: every declared overload of the named method is admitted, subject only to the return-type pattern.

#### Scenario: Last fixed parameter filters overloads under trailing varargs

- **WHEN** an `after returning` advice carries `call(public byte[] Cipher.doFinal(byte[], ..))` and the android.jar index declares `javax.crypto.Cipher` overloads `doFinal()`, `doFinal(byte[])`, and `doFinal(byte[], int, int)`
- **THEN** `expandCallTarget` MUST return exactly 2 concrete calls — `doFinal(byte[])` and `doFinal(byte[], int, int)` — because both start with the fixed `byte[]` parameter
- **AND** the zero-arg `doFinal()` MUST NOT be returned (it has fewer parameters than the fixed prefix)
- **AND** every returned overload's first parameter MUST be `byte[]`

#### Scenario: Empty fixed head keeps match-anything semantics

- **WHEN** an `after returning` advice carries `call(public static * Cipher.getInstance(..))` and the index declares 3 static `getInstance` overloads
- **THEN** `expandCallTarget` MUST return all 3 overloads (fixed prefix length 0 constrains nothing)

#### Scenario: Non-trailing wildcard is rejected wholesale

- **WHEN** an advice carries `call(public static Cipher Cipher.getInstance(String, .., int))` — the `..` is followed by `int`, so the parser keeps `".."` as a `ParamSpec` in the head and `varargs` stays false
- **THEN** `expandCallTarget` MUST return an empty list
- **AND** no wrapper MUST be emitted for that advice
