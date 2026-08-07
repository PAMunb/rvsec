# Design — Weaver Emission Fidelity and the Layer-3 Gate

GitHub Issue: #100

## Context

The proposal establishes three problems: the inline emission path truncates fused advices, the wrapper registry overwrites colliding keys, and the validation layer that would detect both shares the first defect's premise. This document settles how each is repaired, in what order, and what evidence is admissible.

Most of the code lives in the sibling Java reactor (`$RVSEC_HOME/rvsec/rvsec-android/rvsec-instrumentation-dexlib2`), built from the root `rvsec` reactor and delivered into `rv-android/lib/` through the `main.basedir` mechanism. The only part inside this repository is the consumer of the weaver counters: `modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py` and the `InstrumentationResults` model in `modules/rv-instrumentation-core/src/rv_instrumentation_core/results.py`.

Two constraints shape the design and neither is negotiable. First, no emulator may be started, stopped or managed by hand, which is what removed the runtime arm of Layer 3 from scope and forced the acceptance criterion onto the Java side. Second, the acceptance tests must be observed failing before the repair — the defect being repaired survived fifteen months precisely because a discriminating instrument was replaced by an aggregate one, and a test first seen green proves nothing about whether it discriminates.

Relevant requirements: FR02 (APK instrumentation with monitors), NFR07 (correctness of the runtime verification pipeline).

## Architecture

```
                    JavaMOP descriptor (115 advices, 17 with N>1 monitorCalls)
                                    |
                          descriptor-reader
                                    |
                          +---------+---------+
                          |                   |
                   pointcut-engine       advice-emitter
                  (fail-closed parse)   (emission cardinality)
                          |                   |
                          +---------+---------+
                                    |
                              dex-mutator
                          (wrapper registry guard,
                           register pressure)
                                    |
                     +--------------+--------------+
                     |                             |
                    cli                        validator
        (--results-json on instrument)   (BaksmaliDiffer, OracleLoader,
                     |                    TraceComparator, derived oracles)
                     |
        rv-instrumentation-dexlib2 (Python)
        _parse_results_json -> InstrumentationResults
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `EmitContext` / `MonitorInvokeBuilder` | Build the invoke sequence for an advice | `AdviceSpec` with `monitorCalls: List` | N invoke instructions, descriptor order |
| `StaticInitializationEmitter` / `AfterThrowingEmitter` | Emit at their respective join points | same | same |
| `WrapperEmitter` | Wrapper path; already iterates correctly | same | reference behaviour |
| `DexWeaver` | Wrapper registry | advice + computed key | registry binding, guarded |
| `parseCommonPointcut` | Parse a pointcut expression | expression text | matcher, or raise |
| `InstrumentationCli` | CLI surface for `instrument` and `batch` | APK path, options | woven APK + results JSON |
| `BaksmaliDiffer` | Layer-1 static hook attribution | woven DEX + descriptor | hook comparison |
| `OracleLoader` | Load and admit oracle YAMLs | `validator/oracles/*.yaml` | oracle set, or rejection |
| `TraceComparator` | Layer-3 event-set comparison | oracle + two variants' traces | F1 / κ report |
| `dexlib_instrumentation.py` | Python driver of the CLI | APK paths, results dir | `InstrumentationResults` |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| Emission Cardinality for Fused Advices | `EmitContext:51-52`, `MonitorInvokeBuilder:238-241`, `StaticInitializationEmitter:145-148`, `AfterThrowingEmitter:72` | V0: `EmitPlanShapeTest`, `StaticInitializationEmitterSignatureTest`, `AfterThrowingEmitterTest` with an N=3 fixture |
| INV-INS-104 (N calls → N invokes, every path) | same, plus `WrapperEmitter:637` as reference | parity assertion: inline plan and wrapper plan emit the same call set |
| Wrapper Registry Key Uniqueness | `DexWeaver:145` (key), `:159` (write), guard idiom at `:208` | unit test with two advices colliding on the key |
| Fail-Closed Pointcut Parsing | `parseCommonPointcut` | unit test: unparseable expression raises, does not match |
| Instrumentation Result Reporting | `InstrumentationCli:129-137`, `dexlib_instrumentation.py:245-252`, `_parse_results_json:494` | integration: production path produces `instrument_results.json` |
| INV-INS-105 (results JSON always written) | same | assertion over a results tree: every APK has a results JSON |
| Validator Independence | `BaksmaliDiffer:216` | Layer-1 run over a DEX woven from an N>1 advice |
| INV-INS-106 (no validator reads `get(0)`) | same | grep-style contract test over the validator sources |
| INV-INS-107 (derived-oracle provenance) | `OracleLoader`, oracle YAML provenance block | loader rejects an oracle whose source is the implementation under test |
| Pre-Fix Red Evidence / INV-INS-108 | process, enforced in `tasks.md` | the committed red output of V0 and V2 |
| V2 (9 events in the woven DEX) | end-to-end over one APK | baksmali the woven DEX, count `invoke-static` for the 9 events |

## Goals / Non-Goals

**Goals:**

- Every emission path emits every monitor call an advice carries.
- The production instrumentation path reports its counters to the Python layer.
- Layer 3 has three admissible oracles and executes to a recorded verdict for L3-b and L3-c.
- The repair is proved by evidence that was observed failing first.

**Non-Goals:**

- L3-a, the runtime per-APK arm. It needs a UI driver inside the platform's emulator session, i.e. a new tool plugin in `rv-android`. Out of scope by decision.
- V4, re-executing the corpus to quantify how many real violations the defect erased. The cheap targets are known (`photok`, `aegis`, `org.cry.otp` have executed-but-silent sites), but this is a separate question.
- Repairing the specification-side defects. Those are issue #101.
- Any change to the JavaMOP fusion stage. The root cause of fusion producing N>1 advices is upstream (`EventManager.java:91` requires `advice.retVal.equals(event.getRetVal())` while `MOPParameter.equals` compares type *and* name), but the weaver must handle N>1 correctly regardless of why it occurs.

## Decisions

### D-E1 — counters reach Python by extending `instrument`, not by unifying on `batch`

`--results-json` exists only on `batch`. Two ways to close the gap: force production onto `batch`, or add the option to `instrument`.

Forcing `batch` loses the explicit APK subset. The Python driver takes `apk_paths` precisely to honour a strict subset, and its own comment records why: the Java `batch` path globs the directory, so a subset can only be respected by per-APK invocation or by staging a symlink farm. Unifying on `batch` would trade a real capability for an implementation convenience.

**Decision: extend the `instrument` subcommand with `--results-json`**, writing one results JSON per APK, and aggregate on the Python side where the per-APK loop already aggregates errors. This preserves `apk_paths` semantics, keeps the existing `batch` behaviour untouched, and makes INV-INS-105 checkable on both paths.

### D-A1 — repair truncation by iterating, not by inlining the wrapper path

The wrapper path at `WrapperEmitter:637` already iterates and is the reference behaviour. Two options: make the inline path iterate, or route everything through the wrapper path.

Routing everything through wrappers would change bytecode shape for every currently-inline site, which is a far larger blast radius than the defect. **Decision: make the inline path iterate**, and add a parity assertion that for the same advice the inline plan and the wrapper plan produce the same set of monitor calls in the same order. The parity assertion is the cheap guard against the two paths drifting again.

### D-A2 — order is part of the contract

`monitorCalls` is a list, and the descriptor's order is the order the monitor expects. **Decision: descriptor order is normative**, asserted in V0, not merely the set of calls. A set-only assertion would let a future refactor reorder emissions silently.

### D-A3 — count before fixing

The census (7 advices, 9 events) was derived from the production descriptor by inspection. **Decision: re-derive it mechanically as a task inside this change, before the repair**, so the post-repair count has a pre-repair baseline computed by the same code rather than by a different method. This is one script and it doubles as part of the V2 evidence.

### D-B1 — the wrapper key is disambiguated, and collision fails loud until it is

The key at `DexWeaver:145` collides for distinct advices. Two options: widen the key so distinct advices produce distinct keys, or keep the key and guard the write.

**Decision: widen the key, and additionally guard the write to fail loud** when a key would be rebound to a different advice. Guarding alone (the `containsKey` idiom at `:208`) would silently drop the second advice's wrapper instead of silently overwriting the first — a different wrong answer. Widening fixes the cause; the guard turns any residual collision into a build failure rather than a data defect.

### D-O1 — the oracle minimum is met by provenance, not by lowering the threshold

`MINIMUM_ORACLES = 3` against two files, one an empty template. Lowering the threshold would be a policy concession with no argument behind it. Writing a third multidex oracle by hand was mandated in April 2026 and never happened.

**Decision: keep the minimum at three and satisfy it with derived oracles** — L3-b from the paired `ajc` × `dexlib2` events, L3-c from the JVM `-javaagent` control group. Both derive from an independent weaver, which is what makes them non-circular; the delta spec makes provenance an admission criterion so that a circular oracle is rejected by the loader rather than by reviewer vigilance. The multidex profile's absence goes to `LIMITATIONS.md`.

### D-O2 — the L3-c provenance filter is stated in the YAML

The control group's records span more than the sites of interest. Which records enter the oracle is a decision that determines what the gate can conclude. **Decision: the filter is expressed as a named, scripted selection over the source CSV, recorded in the oracle's provenance block together with the source file's content hash**, so the oracle can be re-derived and audited without re-reading this document.

## API Design

### `InstrumentationCli instrument <apk> [--results-json <path>]`

- **Precondition**: `apk` exists; the parent directory of `--results-json` exists.
- **Postcondition**: the woven APK is written to the results directory; a results JSON describing this APK's counters is written to `--results-json` regardless of success or failure.
- **Error**: an unparseable pointcut raises `UnsupportedAspectConstructError`; a wrapper key rebinding to a different advice fails the weave. Both are reported in the results JSON before the non-zero exit.

### `_parse_results_json(path: Path) -> InstrumentationResults`

Unchanged in signature. The per-APK loop in `dexlib_instrumentation.py` aggregates the per-APK JSONs into a single `InstrumentationResults` with `variant="dexlib2"`, mirroring how it already aggregates errors. `success_count`, `total_count` and `errors` keep their meaning; the existing `_demote_silent_failures` cross-check continues to apply, since a results JSON claiming success is still not proof that the APK landed.

### `OracleLoader.load(dir: Path) -> List<Oracle>`

- **Precondition**: at least `MINIMUM_ORACLES` YAMLs present.
- **Postcondition**: every returned oracle carries a provenance block; derived oracles carry source path, source content hash and derivation script name.
- **Error**: an oracle whose provenance names the implementation under test is rejected with a message naming the circularity.

## Data Flow

Repair path: descriptor → `advice-emitter` produces an emission plan carrying all N monitor calls → `dex-mutator` splices N invokes, applying register-pressure handling → counters accumulate → `cli` writes the results JSON → Python parses it into `InstrumentationResults` → platform result processing.

Evidence path: the production descriptor and a woven APK → the census script produces the pre-repair count of truncated advices and dropped events → V0 and V2 run red against pre-repair code and their output is committed → the repair lands → V0 and V2 run green → the same census script produces the post-repair count → L3-b and L3-c run against their derived oracles and their verdicts are recorded.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `UnsupportedAspectConstructError` | `parseCommonPointcut` on an unrecognised expression | Fail the weave, name expression and aspect | Extend the parser deliberately, in its own change |
| Wrapper key rebinding | `DexWeaver` registry write | Fail loud | Widen the key for the colliding shape |
| Register-pressure discard after cardinality repair | `dex-mutator` | Count and report; do not silently drop | Reported in the change; a discard that turns out to be systematic becomes its own issue |
| Missing results JSON | Python driver | Treat as instrumentation failure for that APK | Investigate the CLI invocation, not the parser |
| Circular oracle | `OracleLoader` | Reject with a message naming the circularity | Re-derive from an independent weaver's recording |

## Risks / Trade-offs

- [The acceptance criterion is weaker than the one it replaces] → V0 and V2 prove emission and arrival in the woven DEX, not arrival in logcat. Stated in the delta spec as a condition on how any Layer-3 verdict is reported, so the weaker claim is not read as the stronger one.
- [Derived oracles are a novel provenance class and invite reviewer scrutiny] → the non-circularity argument is written into the requirement, the source is content-addressed, and the derivation is scripted and re-runnable.
- [Cardinality repair may trigger register-pressure discards] → counters land before the repair (D-E1 before D-A1 in the task order) precisely so this is measurable rather than inferred.
- [The change spans two repositories] → the Java work is delivered as a jar into `rv-android/lib/` by the reactor; the Python side is two files. Task groups are ordered so the Python side integrates after the CLI option exists.
- [`get(0)` may exist in sites not yet enumerated] → INV-INS-106 is enforced by a contract test over the validator and emitter sources rather than by the five known line numbers.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (Java) | Emission cardinality on every path; inline/wrapper parity; wrapper key collision; fail-closed parse | Existing emitter test suites, extended with an N=3 fixture | ~10 tests |
| Unit (Java) | `OracleLoader` provenance admission and rejection | Synthetic oracle YAMLs | ~4 tests |
| Contract (Java) | No validator or emitter source reads `getMonitorCalls().get(0)` | Source scan test | 1 test |
| Integration (Java) | V2 — the 9 events appear as `invoke-static` in the woven DEX | Weave one APK, baksmali, count | 1 gate |
| Integration (Python) | The production path produces and parses a results JSON | `rv-instrumentation-dexlib2` tests | ~3 tests |
| Gate | L3-b and L3-c executed to a recorded verdict | `ValidationCli layer3` against derived oracles | 2 runs |

Python tests run with `--import-mode=importlib -o "addopts="`, per the CI contract.

## Open Questions

- Whether the widened wrapper key (D-B1) changes the generated wrapper method names in a way that affects `BaksmaliDiffer`'s string matching. To be checked when the key shape is chosen; if it does, the Layer-1 normalisation gap documented in May 2026 is touched and must be handled in the same task group.
- Whether the L3-c filter should include control-group records whose site does not exist in the Android build. The conservative choice is to exclude them and say so in the provenance block; the decision is recorded when the derivation script is written.
- Whether the post-repair count of register-pressure discards is small enough to absorb or large enough to become its own issue. Answerable only after D-A3's baseline exists.
