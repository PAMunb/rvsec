# Weaver Emission Fidelity and the Layer-3 Gate

GitHub Issue: #100

## Why

The DEX-native weaver silently corrupts what RVSEC reports. An advice fused from N events emits only the first monitor call, so 7 advices are truncated and 9 events never reach the DEX: **8 of them error emitters** — 7 raising `UnsatisfiedConstraint`, one `UnsafeAlgorithm` — and the ninth a state transition whose loss suppresses a later violation instead of an immediate one. The measurable consequence is that `ErrorType.UnsatisfiedConstraint` has 8 `addError` sites in the `jca` specification set and **zero** occurrences across 97,018 recorded events, while the AspectJ control group reports 43 for the same category. A second defect, a wrapper-registry collision, works in the opposite direction and fabricates violations; a third makes an unparsed pointcut match everything.

None of this was caught, and the reason is structural rather than accidental. Layer 3 of the pre-registered validation framework (`docs/20260423_plano_validacao.md`) compares event *sets* between the `ajc` and `dexlib2` variants against a hand-validated oracle, and event #8 of its canonical oracle is precisely one of the nine the truncation erases — the gate was designed correctly in April 2026, before the defect existed as a hypothesis. In May 2026 it was declared N/A and substituted by an aggregate coverage metric (`cov_rv_method`), which **cannot** observe this defect by construction: the truncation removes additional monitor calls from an already-woven site, so method coverage is identical with and without it. A discriminating instrument was replaced by a non-discriminating one, and the cost surfaced fifteen months later as an entire error category missing from the dataset.

The weaver also reports nothing. `--results-json` exists only on the `batch` subcommand while production instruments through `instrument`, which is why the tree holds 289 `instrument_errors.json` files and zero `instrument_results.json`. Without counters there is no way to observe the side effects of repairing emission.

## What Changes

- **Emission fidelity.** An advice with N `monitorCalls` emits N invokes, in descriptor order, on the inline path as well as the wrapper path. Today `getMonitorCalls().get(0)` truncates at `EmitContext.java:51-52`, `MonitorInvokeBuilder.java:238-241` (used at `:50`, `:136`, `:217`), `StaticInitializationEmitter.java:145-148` and `AfterThrowingEmitter.java:72`.
- **Wrapper collision.** The wrapper registry stops overwriting an existing key (`DexWeaver.java:145` and `:159`); the guard that resolves it already exists in the same file at `:208`.
- **Fail-closed pointcut parsing.** `parseCommonPointcut` raises instead of matching everything when it cannot parse.
- **Weaver counters reach Python.** The production single-APK path emits its results JSON, and `rv-instrumentation-dexlib2` parses it into `InstrumentationResults`. The resolved `android.jar` is logged.
- **The validation layer stops sharing the defect's premise.** `BaksmaliDiffer.java:216` no longer assumes a single monitor call, and the four test fixtures that build advices through `get(0)` (`EmitPlanShapeTest:74`, `StaticInitializationEmitterSignatureTest:143-154`, `AfterThrowingEmitterTest:60/77/105/121`) exercise an advice with N>1.
- **Layer 3 becomes executable with derived oracles.** The oracle minimum is satisfied by oracles derived from existing AspectJ executions rather than by hand-written YAML: **L3-b** from the 55,169 paired `ajc` × `dexlib2` events in `out/run_jca_compare_consolidated/events_fair.csv`, and **L3-c** from the JVM `-javaagent` control group, the only regime where `UnsatisfiedConstraint` is observable at all. Both are executed and their verdicts recorded.
- **The acceptance evidence is ordered.** V0 (an advice with N `monitorCalls` emits N invokes) and V2 (the nine events appear as `invoke-static` in the woven DEX) are executed and **recorded failing against the pre-fix code** before any emission fix is integrated.

**Out of scope, deliberately:** L3-a, the strict per-APK instrument, stays parked. It requires a deterministic UI driver running inside a booted emulator, reachable only as a new `AbstractTool` plugin in `rv-android`; that front was decided against on 2026-08-06. The acceptance criterion therefore lives on the Java side and proves emission rather than arrival in logcat.

## Capabilities

### New Capabilities

None. This change repairs behaviour that the `instrumentation` capability already claims.

### Modified Capabilities

- `instrumentation`: three requirement areas change.
  - **Monitor emission for fused advices** — the current `Named-Binding Contract for dexlib2 Advice Emission` and `JavaMOP Descriptor Format and Emission` requirements do not state that an advice carrying N monitor calls must emit N invokes on every emission path. The delta makes emission cardinality an explicit contract with an invariant, on both the inline and wrapper paths.
  - **Instrumentation result reporting** — the pipeline currently has no requirement that the production single-APK path report its counters. The delta states that the production path emits a results JSON consumed by the Python layer.
  - **Ground-truth oracle diversity and the Layer-3 gate** — `Ground-Truth Oracle Diversity for Equivalence Claims` mandates three hand-validated oracle APKs committed before execution, of which one (multidex from JCA-400) was never written; `Cryptoapp Oracle Layer 3 Mandatory Gate` assumes a runtime trace obtained through a driver. The delta admits oracles **derived from executions of the independent AspectJ weaver**, states the provenance rule that keeps them non-circular, and records that the runtime arm (L3-a) is out of scope with the substituted Java-side criterion named.

## Impact

**Sibling Java reactor** (`$RVSEC_HOME/rvsec/rvsec-android/rvsec-instrumentation-dexlib2`), which is where most of the work is:

| Submodule | What changes |
|---|---|
| `advice-emitter` | `EmitContext`, `MonitorInvokeBuilder`, `StaticInitializationEmitter`, `AfterThrowingEmitter` — emission cardinality |
| `dex-mutator` | `DexWeaver` — wrapper registry guard |
| `pointcut-engine` | `parseCommonPointcut` — fail closed |
| `cli` | `InstrumentationCli` — results JSON on the production path |
| `validator` | `BaksmaliDiffer`, `OracleLoader`, oracle derivation, L3-b and L3-c execution |

**`rv-android` Python modules**: `rv-instrumentation-dexlib2` (`dexlib_instrumentation.py`, `_parse_results_json`) and `rv-instrumentation-core` (`InstrumentationResults`). This is the only part of the change inside this repository, and it is deliberate scope — it is the consumer side of the counters, not new platform machinery.

**Requirements**: FR02 (APK instrumentation with monitors), FR03 (specification set support, indirectly — the erased category belongs to the JCA set), NFR07 (correctness of the runtime verification pipeline). To be confirmed line by line against `docs/PRD.md` during the specs phase.

**Downstream**: issue #101 (JCA specification authoring, `isValid`, predicate graph) depends on the wrapper-collision fix for the empirical verification of two of its specs, and on nothing else in this change. Every other part of #101 is independent and can proceed in parallel.

**Data already on disk, no re-execution needed**: `out/run_jca_compare_consolidated/events_fair.csv` (55,169 paired events, 8 APKs under both variants) and the AspectJ unit-test control group results. The corpus re-execution that would quantify how many real violations the defect erased (V4) is not part of this change.
