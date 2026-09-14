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
| Wrapper Registry Key Uniqueness | `WrapperEmitter` merges the advices bound to one call into one wrapper; `DexWeaver:145` (key), `:159` (write, fail-loud guard) | `WrapperMergeTest` (3), `WrapperRegistryGuardTest` (3) |
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

### D-B1 — the wrapper key cannot be widened, so the emitter merges instead

The key at `DexWeaver:145` collides for distinct advices. Two options were on the table: widen the key so distinct advices produce distinct keys, or keep the key and guard the write.

**Neither is available.** The key is `origClassDesc#method(params)return` — the call site's own `MethodReference`, which is the only identity a call site carries. Any component added to it is a component the lookup cannot supply, because at substitution time the weaver has the invoke and nothing else; so there is nothing to widen the key *with*. And guarding alone would abort the weave on the real production descriptor, which has 10 keys bound more than once.

**Decision, confirmed with the user on 2026-08-07: `WrapperEmitter` merges.** One wrapper is emitted per original call, and its body fires the monitor calls of every advice bound to that call. The registry becomes single-valued by construction — there is no second binding left to disambiguate — and the fail-loud guard stays, demoted from being the repair to being the assertion that emitter and registry still agree about what counts as the same call.

Measured on the production descriptor **before** the merge: 96 wrappers over 84 distinct keys, 10 keys bound more than once, **12 wrappers silently discarded**; `SecureRandom.getInstance(String)` alone was bound three times. After it: `wrappersGenerated` 96 → 84, `wrappersSubstituted` unchanged at 74 — no call site lost its wrapper.

This satisfies the delta spec, which requires the weaver to *either* disambiguate the key or fail loud, never to bind the second advice's wrapper to the first advice's site. Merging removes the second binding rather than telling the two apart, which meets the requirement by making its precondition unreachable.

### D-O1 — the oracle minimum is met by provenance, not by lowering the threshold

`MINIMUM_ORACLES = 3` against two files, one an empty template. Lowering the threshold would be a policy concession with no argument behind it. Writing a third multidex oracle by hand was mandated in April 2026 and never happened.

**Decision: keep the minimum at three and satisfy it with derived oracles** — L3-b from the paired `ajc` × `dexlib2` events, L3-c from the JVM `-javaagent` control group. Both derive from an independent weaver, which is what makes them non-circular; the delta spec makes provenance an admission criterion so that a circular oracle is rejected by the loader rather than by reviewer vigilance. The multidex profile's absence goes to `LIMITATIONS.md`.

### D-O2 — the L3-c provenance filter is stated in the YAML

The control group's records span more than the sites of interest. Which records enter the oracle is a decision that determines what the gate can conclude. **Decision: the filter is expressed as a named, scripted selection over the source CSV, recorded in the oracle's provenance block together with the source file's content hash**, so the oracle can be re-derived and audited without re-reading this document.

The open question this left — whether records whose site cannot exist in a shipped APK should enter — is answered: **they do not**. `categoria_unit_tests.csv` classifies each `(apk, spec, class, method)` tuple, and only `app_producao` is admitted; the excluded `lib` tuples are `*Test` classes that no Android build contains. Admitting them would let the oracle demand events from sites the APK does not have, which is a false negative manufactured by the oracle rather than observed in the pipeline. The filter keeps 138 of 298 control rows, over 12 apps.

### D-O3 — the unit of analysis is the article's, not the comparator's

The first derivation keyed the oracles on `(spec, errorType)`, reasoning that `TraceComparator.matched` is existential and ignores `location`, and that R8 renames classes between variants so matching on them would measure the minifier.

**Decision: key on `(apk, class, method, spec)`** — the unique-misuse unit defined at `results-rq1.tex:41` and implemented at `data-analysis/repair_summary_outcome.py:53` and `analyze_intersection_rv_cc.py:39`. Both halves of the earlier argument fail. An argument from what a validator currently does cannot set the unit of analysis: if the comparator ignores location, that is the comparator diverging from the article, and the fix belongs to the comparator (D-O4). And the strings that looked like divergent minification — `okio.ByteString.digest$okio(r8-map-id-…:17)` appearing as both class and method — were not R8 at all; they were the frame-form defect, 2,476 rows of `events_fair.csv` where the summarizer's fallback copied a whole stack frame into both columns.

The correction is not cosmetic. At `(spec, errorType)` the paired record shows 8 categories reported only by `dexlib2`; at the article's key it shows 5 unique misuses, and the difference is not rounding — two of the eight were the same misuse counted twice because the line number had entered the key. The repaired figures are `ajc = 13`, `dexlib2 = 17`, `both = 12`, `only-ajc = 1`, `only-dexlib2 = 5`.

The frame-form repair itself uses the producer's rule (`ErrorDescription.FRAME_SUFFIX`), **not** the article's `repair_frame_keys.py`. The two agree on the article's own sheets and disagree here: the article's rule requires the stripped group to look like `File.ext:NN`, and the campaign's frames are `(Unknown Source:1)` and `(r8-map-id-…:17)`, which have no dot and, in the first case, a space. It repairs 0 of the 2,476 rows. The producer's rule repairs all 2,476 with zero residue, because it is deliberately unrestricted about everything except the trailing `:<digits>` and the absence of nested parentheses.

### D-O4 — the comparator reads the producer's format and matches on location

`TraceComparator.RVSEC_LINE` matches `[Spec] EType: msg`. `ErrorCollector.java:37` emits seven comma-separated fields under a padded `RVSEC   :` tag. Nothing in the pipeline emits the bracketed shape — not the collector, and not `ErrorDescription.toString()`, whose ` at ` separator the pattern's mandatory `:` or `-` rejects. The pattern came from `drive_cryptoapp.py:89-94`, whose comment *asserts* the format, and the Java javadoc names that script as its authority.

**Decision: teach the comparator the producer's format and match on `location`, in this change.** Three options were weighed. Leaving both alone keeps the change small but ships two oracles that only run against traces written in an invented shape — Layer 3 stays inert while looking executable, which is worse than the honest N/A it had before. Matching on location without fixing the parser is impossible: the bracketed shape carries no class or method to match against. Fixing the parser without matching on location wastes the class and method the real line already supplies, and leaves the gate weaker than the oracle, which INV-INS-116 forbids.

Two details are forced by the data rather than chosen. The oracle's `location.class` must match against field 1 **or** field 2, because the line carries the class both fully qualified and short, and the two admissible provenances use different forms — `cryptoapp` names `MessageDigestUtil`, a derived oracle names `okhttp3.internal.platform.Platform`. And an oracle event that declares no location keeps matching on `(spec, errorType)` alone, so under-specification stays available deliberately and never happens by accident.

The measured effect: `MessageDigestSpec` is reported once by `ajc` at `jh.h.c` in `gizz.tapes.foss_63` and once by `dexlib2` at `okio.ByteString.digest$okio` in `com.wirelessalien.android.moviedb_33`. Today those score as one agreement. With location, they become one false negative and one false positive, which is what they are.

This breaks all five `TraceComparatorTest` cases, which declare `location: { class: C, method: m }` in the oracle and feed `[SpecX] ErrA: detail one` as the trace. They are rewritten against the collector's format, which is the point: the fixtures were the last thing keeping the invented shape alive.

### D-O5 — one oracle per APK, because `apk` is the one key element the line does not carry

The first derivation wrote a single pooled oracle per profile. **Decision: one oracle file per APK**, named `<apkBaseName>-oracle.yaml`.

The reason is not tidiness. Of the article's four key elements, the violation line supplies class, method and specification, and never the APK — the APK is recoverable only from the oracle's identity or the result-tree filename. `TraceComparator.resolveOracleForApk` already implements exactly that mapping for batch mode, and `cryptoapp-oracle.yaml` already obeys it; the pooled files do not, so in batch mode they resolve for no APK at all. They do work in analyze mode, where `compare` pairs `apkSubsetDir/<oracleName>/` by oracle name — which is why the defect was not noticed. A pooled oracle also lets one app dominate a profile's verdict: on the paired record a single app contributes 1,708 of the events.

### D-O6 — admission is enforced where the comparison happens

`OracleLoader` implements INV-INS-107, but `TraceComparator.compare` lists the oracle directory itself (`TraceComparator.java:96-101`) and `run_phase5_validators.sh` runs `layer1, layer2, layer5, layer3_batch, layer4` without ever invoking the `oracles` subcommand. Admission is therefore reachable only by an operator who chooses to run it.

**Decision: the comparison consults the admission rule.** An oracle rejected for circularity or missing attribution does not contribute to a verdict, and its rejection is carried into the report rather than dropped. Group 3 built the rule; without this it guards a door nobody walks through.

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

Evidence path: the production descriptor and a woven APK → the census script produces the pre-repair count of truncated advices and dropped events → V0 and V2 run red against pre-repair code and their output is committed → the repair lands → V0 and V2 run green → the same census script produces the post-repair count → L3-b and L3-c run against their derived oracles and their verdicts are recorded as characterization.

Layer-3 trace path: `ErrorCollector` writes seven fields under the `RVSEC` tag → logcat records them with a padded tag → `parseObserved` reads spec, error type, both class forms, method and the rejoined message → `matched` compares them against each oracle event's `(spec, errorType, location)` → per-spec F1 and κ. The derived oracles reconstruct their trace pair in the same collector format, so a recording and a reconstruction enter through one code path and a fixture cannot drift away from the producer without the recording drifting too.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `UnsupportedAspectConstructError` | `parseCommonPointcut` on an unrecognised expression | Fail the weave, name expression and aspect | Extend the parser deliberately, in its own change |
| Wrapper key rebinding | `DexWeaver` registry write | Fail loud | Fix the emitter: one wrapper per original call. The key is the call site's own `MethodReference` and cannot be widened (D-B1) |
| Register-pressure discard after cardinality repair | `dex-mutator` | Count and report; do not silently drop | Reported in the change; a discard that turns out to be systematic becomes its own issue |
| Missing results JSON | Python driver | Treat as instrumentation failure for that APK | Investigate the CLI invocation, not the parser |
| Circular oracle | `OracleLoader` | Reject with a message naming the circularity | Re-derive from an independent weaver's recording |

## Risks / Trade-offs

- [The acceptance criterion is weaker than the one it replaces] → V0 and V2 prove emission and arrival in the woven DEX, not arrival in logcat. Stated in the delta spec as a condition on how any Layer-3 verdict is reported, so the weaker claim is not read as the stronger one.
- [Derived oracles are a novel provenance class and invite reviewer scrutiny] → the non-circularity argument is written into the requirement, the source is content-addressed, and the derivation is scripted and re-runnable.
- [Cardinality repair may trigger register-pressure discards] → counters land before the repair (D-E1 before D-A1 in the task order) precisely so this is measurable rather than inferred.
- [The change spans two repositories] → the Java work is delivered as a jar into `rv-android/lib/` by the reactor; the Python side is two files. Task groups are ordered so the Python side integrates after the CLI option exists.
- [`get(0)` may exist in sites not yet enumerated] → INV-INS-106 is enforced by a contract test over the validator and emitter sources rather than by the five known line numbers.
- [The specification sets these monitors derive from are being edited in parallel by issue #101] → the descriptor and monitor sources used for the red evidence are content-addressed and pinned, and the green run reuses them; drift between the two runs would void INV-INS-108.
- [A parser can be wrong for fifteen months while every test around it passes] → `RVSEC_LINE` was written in `drive_cryptoapp.py` from a comment asserting the format, copied into `TraceComparator` with the Python script cited as its authority, and then surrounded by fixtures written to fit it. Nothing in the loop ever touched the producer. Every artefact agreed with every other artefact and all of them disagreed with `ErrorCollector`. INV-INS-117 exists to make the producer the authority; the scenario that enforces it rejects "another parser agrees" as justification, because that is precisely the argument that held here.
- [Making the comparator stricter can turn a passing gate red for reasons unrelated to the weaver] → matching on location is additive only where the oracle declares it, and a derived oracle declares it by construction. The `cryptoapp` oracle already declares it and already claims it is matched, so no oracle is made stricter than its own text. What changes is that the claim becomes true.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (Java) | Emission cardinality on every path; inline/wrapper parity; wrapper key collision; fail-closed parse | Existing emitter test suites, extended with an N=3 fixture | ~10 tests |
| Unit (Java) | `OracleLoader` provenance admission and rejection | Synthetic oracle YAMLs | ~4 tests |
| Unit (Java) | `parseObserved` reads the collector's seven-field line: padded tag, rejoined `expecting`, both class forms | Fixtures copied verbatim from a recorded logcat | ~4 tests |
| Unit (Java) | `matched` / `countFalsePositives` honour `location`, and ignore it when the oracle omits it | Rewritten `TraceComparatorTest` fixtures | ~5 tests |
| Unit (Java) | An inadmissible oracle does not contribute to a verdict | Circular oracle in the comparison directory | ~2 tests |
| Unit (Python) | The frame-form repair on the L3-b source: 2,476 rows repaired, zero residue | Derivation script self-check | ~2 tests |
| Contract (Java) | No validator or emitter source reads `getMonitorCalls().get(0)` | Source scan test | 1 test |
| Integration (Java) | V2 — the 9 events appear as `invoke-static` in the woven DEX | Weave one APK, baksmali, count | 1 gate |
| Integration (Python) | The production path produces and parses a results JSON | `rv-instrumentation-dexlib2` tests | ~3 tests |
| Gate | L3-b and L3-c executed to a recorded verdict | `ValidationCli layer3` against derived oracles | 2 runs |

Python tests run with `--import-mode=importlib -o "addopts="`, per the CI contract.

## Open Questions

- ~~Whether the widened wrapper key (D-B1) changes the generated wrapper method names in a way that affects `BaksmaliDiffer`'s string matching.~~ **Answered in D-B1 and task 5.4**: the key was never widened, but the merge does move the names, and the Layer-1 gap was already open before it. `specOfInvoke` looked wrapper names up **exactly**, while its own javadoc claimed it registered a prefix form — it never did. Reproducing the emitter's `_<n>` overload numbering from the descriptor alone was never possible either, because the descriptor does not carry the `android.jar` overloads the emitter numbers over. `buildWrapperToSpec` now keys on the base name `<fqClass>_<method>` and unions the specs of every advice over it; `specOfInvoke` tries the exact name first, then strips a trailing `_<digits>`.
- ~~Whether the L3-c filter should include control-group records whose site does not exist in the Android build.~~ **Answered in D-O2**: excluded, via the `app_producao` classification, which keeps 138 of 298 control rows over 12 apps. The excluded tuples are `*Test` classes no APK contains.
- Whether the derived oracles should carry `expected_message_substring`. The recorded `expecting` text is generated by the specification and names the offending parameter, so it discriminates two misuses of one method — but it is also the field most likely to change when a `.mop` set is edited, and issue #101 is editing those sets in parallel. Left null in the derived oracles for now; revisit if a verdict turns out to hinge on a distinction only the message carries.
- Whether the post-repair count of register-pressure discards is small enough to absorb or large enough to become its own issue. Answerable only after D-A3's baseline exists.
