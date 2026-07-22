# CLAUDE.md - rvsec-core

## Purpose
Shared runtime types for all monitored-operations code. **Zero dependencies** (root of the dependency tree). Used both by JSE-side code (`rvsec-agent`) and by the classes/handlers generated from `.mop` specs at compile time — it is the base library the generated monitor code links against.

## Role in pipeline
Every generated JavaMOP monitor (`event`/`@fail`/`@match` bodies) calls into `ExecutionContext` and the `eh.*` error types defined here.

## Key components (verified paths)
- `src/main/java/br/unb/cic/mop/Property.java` — enum of monitored properties (`ENCRYPTED`, `DIGESTED`, `RANDOMIZED`, `SIGNED`, `WRAPPED_KEY`, `PREPARED_GCM`, etc.).
- `src/main/java/br/unb/cic/mop/ExecutionContext.java` — singleton (`instance()`); `setProperty`/`validate`/`remove` model CrySL-style ensures/requires; `setObjectAsInAcceptingState`/`isInAcceptingState` track FSM acceptance; `reset()` clears state.
- `src/main/java/br/unb/cic/mop/eh/{ErrorType,ErrorDescription,ErrorSummary}.java` — violation classification and reporting types. `ErrorDescription.equals()` compares only the derived `ErrorSummary`, but `hashCode()` also mixes in `expecting` — an equals/hashCode contract violation (see `rvsec-logger-csv` gotchas for its effect on dedup).
- `src/main/java/br/unb/cic/mop/jca/util/CipherTransformationUtil.java` — helper used by `jca/CipherSpec.mop` (`isValid(transformation)` condition).
- `src/main/java/org/aspectj/lang/{Signature.java,ClassSignature.java}` — **shim**: a minimal `Signature` interface + single `ClassSignature` implementation, standing in for the real AspectJ runtime type. Lets the **dexlib2** weaver hand a `Signature` to generated `*staticinitEvent(Signature)` monitor methods without pulling `aspectjrt` onto Android. Only `getDeclaringType()` is exercised by generated monitor code (`Class k = sig.getDeclaringType()`); the weaver emits `new ClassSignature(T.class)` at the matched type's `<clinit>`.

## Relationships
⟶ all other Java modules (`rvsec-agent`, `rvsec-logger-csv`, `rvsec-logger-logcat` in `rvsec-android`) declare `rvsec-core` as a dependency; generated monitor code (`mop/*RuntimeMonitor.java`) references its types directly.

## Build
`mvn clean install` — plain library jar, no external dependencies.

## Gotchas / README corrections
- ⚠ README claims a **"Logger interface" implemented by csv/logcat — no such interface exists** in this module or anywhere in the repo. Each logger module (`rvsec-logger-csv`, `rvsec-android/rvsec-logger-logcat`) independently defines its **own** `br.unb.cic.mop.eh.ErrorCollector` class (same fully-qualified name, no shared interface/superclass). Selection is **by classpath** — csv OR logcat jar is on the classpath, never both — not polymorphism.
