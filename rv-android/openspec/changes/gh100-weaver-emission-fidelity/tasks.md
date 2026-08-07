<!-- Execution notes:
     - Groups run in order. The dependency that matters is Group 4 (red evidence): no task in
       Group 5 may be integrated before Group 4 is committed. This is INV-INS-108 and it is the
       whole reason the change is shaped this way.
     - Group 1 (counters) precedes Group 5 so that register-pressure discards introduced by the
       cardinality repair are measurable rather than inferred.
     - Groups 2 and 3 must precede Group 4, because V2 runs through a validator that today shares
       the defect's premise.
     - Most files are in the sibling Java reactor ($DEXLIB2 =
       $RVSEC_HOME/rvsec/rvsec-android/rvsec-instrumentation-dexlib2). Only Group 1.5-1.7 touch
       rv-android Python modules.
     - Issue #101 depends on Group 5.2 (wrapper key) and on nothing else here. -->

## 1. Counters and observability

- [x] 1.1 Add `--results-json <path>` to the `instrument` subcommand of `InstrumentationCli` ($DEXLIB2/cli), writing the per-APK counters whether the weave succeeded or failed (D-E1)
- [x] 1.2 Log the resolved `android.jar` path at instrumentation start, so a platform-jar mismatch is diagnosable from the log alone
- [x] 1.3 Add Java unit tests: the option produces a JSON for a successful weave and for a failed one
- [x] 1.4 Re-derive the truncation census mechanically over the production descriptor `results/gh92_e2e2/monitors/MultiSpec_1MonitorAspect.json` — advices with N>1, advices truncated, events dropped — and commit the script plus its pre-repair output (D-A3)
- [x] 1.5 Pass `--results-json` from the per-APK loop in `modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py` and aggregate the per-APK JSONs into one `InstrumentationResults` with `variant="dexlib2"`, mirroring how the loop already aggregates errors
- [x] 1.6 Add Python tests: the `apk_paths` path produces `instrument_results.json`; the aggregate carries the right `success_count` / `total_count`; `_demote_silent_failures` still applies
- [x] 1.7 Run `/rv-test-run rv-instrumentation-dexlib2`
- [ ] 1.8 Verify INV-INS-105 over a real results tree: every APK processed has a results JSON (today the tree has 289 `instrument_errors.json` and zero `instrument_results.json`)

## 2. Validator independence from the emission premise

- [ ] 2.1 Fix `BaksmaliDiffer.java:216` to attribute a woven artefact using all of `monitorCalls`, not `get(0)`
- [ ] 2.2 Extend the emitter fixtures to build an advice with N=3 monitor calls: `EmitPlanShapeTest:74`, `StaticInitializationEmitterSignatureTest:143-154`, `AfterThrowingEmitterTest:60/77/105/121`
- [ ] 2.3 Add the contract test for INV-INS-106: no validator or emitter source reads `getMonitorCalls().get(0)`
- [ ] 2.4 Run the `$DEXLIB2` validator and emitter test suites; they must pass with the new fixtures against the **unrepaired** weaver except where the fixture asserts cardinality (those are Group 4's red evidence)

## 3. Derived oracles

- [ ] 3.1 Add the provenance block to the oracle YAML schema and make `OracleLoader` require it: hand-validated, or derived-from-an-independent-weaver with source path, source content hash and derivation script name (INV-INS-107)
- [ ] 3.2 Make `OracleLoader` reject an oracle whose provenance names the implementation under test, with a message naming the circularity
- [ ] 3.3 Write the L3-b derivation script over `out/run_jca_compare_consolidated/events_fair.csv` (55,169 paired ajc × dexlib2 events, 8 APKs under both variants) and commit the derived oracle with its provenance block
- [ ] 3.4 Decide and record the L3-c provenance filter — which control-group records enter the oracle and why (D-O2) — then write the derivation script over the JVM `-javaagent` control-group results and commit the derived oracle
- [ ] 3.5 Add the `LIMITATIONS.md` entry for the unwritten multidex profile
- [ ] 3.6 Add Java unit tests for `OracleLoader`: admission with each provenance class, rejection of a circular oracle, rejection below `MINIMUM_ORACLES`
- [ ] 3.7 Confirm `MINIMUM_ORACLES = 3` is now satisfiable without lowering the threshold

## 4. Red evidence — barrier, nothing in Group 5 may be integrated before this is committed

- [ ] 4.1 Run V0 against the **pre-repair** weaver: an advice with N monitor calls emits N invokes in descriptor order. It must fail. Commit the failing output as an artefact of this change
- [ ] 4.2 Run V2 against the **pre-repair** weaver: weave one APK with the JCA set, baksmali it, count the `invoke-static` for the 9 events. They must be absent. Commit the failing output
- [ ] 4.3 Freeze the descriptor and the generated monitor sources that V2 weaves with, before it runs: record the sha256 of the descriptor and of each generated monitor source in the red-evidence artefact, and reuse exactly those inputs for the green run in 6.2. The `.mop` specification sets these monitors are generated from are being edited in parallel by issue #101; if they move between the red run and the green one, the two runs stop being comparable and INV-INS-108 proves nothing. Task 1.4's descriptor (`results/gh92_e2e2/monitors/MultiSpec_1MonitorAspect.json`) is committed and already insulated — V2 is the run that needs the pin
- [ ] 4.4 Record in this file which commit carries the red evidence, so the repair commits can reference it (INV-INS-108)
- [ ] 4.5 Confirm that neither V0 nor V2 passes before the repair — a test that passes here is rejected as evidence and must be replaced

## 5. Emission repairs

- [ ] 5.1 Make the inline path iterate `monitorCalls` in descriptor order: `EmitContext:51-52`, `MonitorInvokeBuilder:238-241` (reached from `:50`, `:136`, `:217`), `StaticInitializationEmitter:145-148`, `AfterThrowingEmitter:72` (D-A1, D-A2)
- [ ] 5.2 Add the inline/wrapper parity assertion: for the same advice, both plans emit the same monitor calls in the same order, with `WrapperEmitter:637` as the reference
- [ ] 5.3 Widen the wrapper registry key at `DexWeaver:145` so distinct advices produce distinct keys, and guard the write at `:159` to fail loud on a rebinding (D-B1). **Issue #101 depends on this task**
- [ ] 5.4 Check whether the widened key changes generated wrapper method names in a way that affects `BaksmaliDiffer` string matching; if it does, handle the Layer-1 normalisation gap here rather than leaving it to Layer 1
- [ ] 5.5 Make `parseCommonPointcut` raise `UnsupportedAspectConstructError` instead of matching everything
- [ ] 5.6 Add Java unit tests for the wrapper key collision and the fail-closed parse
- [ ] 5.7 Run the full `$DEXLIB2` test suite

## 6. Green evidence and gates

- [ ] 6.1 Re-run V0: it must pass, with descriptor order asserted, not just the call set
- [ ] 6.2 Re-run V2 over the descriptor and monitor sources pinned in 4.3: the 9 events must appear as `invoke-static` in the woven DEX
- [ ] 6.3 Re-run the census script from 1.4 and record the post-repair counts against the pre-repair baseline
- [ ] 6.4 Read the weaver counters for sites discarded under register pressure after the repair, and record the delta. An increase is reported explicitly; if it is systematic, open a follow-up issue rather than absorbing it
- [ ] 6.5 Execute L3-b against its derived oracle and record the verdict
- [ ] 6.6 Execute L3-c against its derived oracle and record the verdict — this is the only regime where `UnsatisfiedConstraint` is observable, so it is the gate that speaks to the erased category
- [ ] 6.7 State in the recorded verdicts that the runtime arm (L3-a) did not run and that V0/V2 prove emission and arrival in the woven DEX, not arrival in logcat

## 7. Integration and verification

- [ ] 7.1 Build the sibling reactor from its root and confirm the updated jar lands in `rv-android/lib/`
- [ ] 7.2 Add the Python integration test for the end-to-end counters path
- [ ] 7.3 Run `/rv-qa-lint-fix rv-instrumentation-dexlib2`
- [ ] 7.4 Run `/rv-verify rv-instrumentation-dexlib2`
- [ ] 7.5 Invoke `/rv-code-reviewer` via the Skill tool
- [ ] 7.6 Run `/rv-docs-sync rv-instrumentation-dexlib2` if module docs need updating
- [ ] 7.7 Notify issue #101 that task 5.3 has landed, since its empirical verification of the two hot specs is blocked on it
