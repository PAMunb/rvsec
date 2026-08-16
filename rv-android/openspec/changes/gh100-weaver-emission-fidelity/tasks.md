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
- [x] 1.4 Re-derive the truncation census mechanically over the production descriptor `results/gh92_e2e2/monitors/MultiSpec_1MonitorAspect.json` — advices with N>1, advices truncated, events dropped — and commit the script plus its pre-repair output (D-A3). This descriptor was generated from the `jca` set, and stays there deliberately: the census explains the 97,018-event dataset, which ran with `jca`. V2 (4.2, 6.2) weaves fresh monitors and uses `jca_android`, the set going forward — the two answer different questions, and neither is the other's baseline
- [x] 1.5 Pass `--results-json` from the per-APK loop in `modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py` and aggregate the per-APK JSONs into one `InstrumentationResults` with `variant="dexlib2"`, mirroring how the loop already aggregates errors
- [x] 1.6 Add Python tests: the `apk_paths` path produces `instrument_results.json`; the aggregate carries the right `success_count` / `total_count`; `_demote_silent_failures` still applies
- [x] 1.7 Run `/rv-test-run rv-instrumentation-dexlib2`
- [x] 1.8 Verify INV-INS-105 over a real results tree: every APK processed has a results JSON (today the tree has 289 `instrument_errors.json` and zero `instrument_results.json`)

## 2. Validator independence from the emission premise

- [x] 2.1 Fix `BaksmaliDiffer.java:216` to attribute a woven artefact using all of `monitorCalls`, not `get(0)`
- [x] 2.2 Extend the emitter fixtures to build an advice with N=3 monitor calls: `EmitPlanShapeTest:74`, `StaticInitializationEmitterSignatureTest:143-154`, `AfterThrowingEmitterTest:60/77/105/121`
- [x] 2.3 Add the contract test for INV-INS-106: no validator or emitter source reads `getMonitorCalls().get(0)`
- [x] 2.4 Run the `$DEXLIB2` validator and emitter test suites; they must pass with the new fixtures against the **unrepaired** weaver except where the fixture asserts cardinality (those are Group 4's red evidence)

## 3. Derived oracles

- [x] 3.1 Add the provenance block to the oracle YAML schema and make `OracleLoader` require it: hand-validated, or derived-from-an-independent-weaver with source path, source content hash and derivation script name (INV-INS-107)
- [x] 3.2 Make `OracleLoader` reject an oracle whose provenance names the implementation under test, with a message naming the circularity
- [x] 3.3 Write the L3-b derivation script over `out/run_jca_compare_consolidated/events_fair.csv` (55,169 paired ajc × dexlib2 events, 8 APKs under both variants) and commit the derived oracle with its provenance block
- [x] 3.4 Decide and record the L3-c provenance filter — which control-group records enter the oracle and why (D-O2) — then write the derivation script over the JVM `-javaagent` control-group results and commit the derived oracle
- [x] 3.5 Add the `LIMITATIONS.md` entry for the unwritten multidex profile
- [x] 3.6 Add Java unit tests for `OracleLoader`: admission with each provenance class, rejection of a circular oracle, rejection below `MINIMUM_ORACLES`
- [x] 3.7 Confirm `MINIMUM_ORACLES = 3` is now satisfiable without lowering the threshold

## 3b. Oracle granularity and comparator fidelity — runs before Group 4

<!-- Numbered 3b rather than renumbering: the handoff, the commits and issue #100's
     acceptance criteria already cite "4.3", "5.3" and "6.2" by number.
     Tasks 3.3 and 3.4 delivered oracles keyed on (spec, errorType), pooled into one
     file per profile, against a comparator that reads a line format nothing emits.
     Group 3 stays checked off as the record of what was built; this group corrects it. -->

- [x] 3b.1 Teach `TraceComparator.parseObserved` the collector's line (`ErrorCollector.java:37`): padded `RVSEC   :` tag, seven fields `spec,classQualifiedName,className,methodName,location,errorType,expecting`, fields 6+ rejoined. `ObservedEvent` gains the qualified class, the short class and the method. Agree with `rv-android`'s `logcat_parser.py:319`, which is the reference implementation (INV-INS-117)
- [x] 3b.2 Make `matched` and `countFalsePositives` honour an oracle event's `location`, accepting a match against either the qualified or the short class form, and falling back to `(spec, errorType)` only when the oracle declares no location (INV-INS-116). **Add the test that fails without it first**: `MessageDigestSpec` at `jh.h.c` versus `okio.ByteString.digest$okio` must score one FN and one FP, not one TP
- [x] 3b.3 Rewrite the five `TraceComparatorTest` fixtures against the collector's format. They currently declare `location: { class: C, method: m }` and feed `[SpecX] ErrA: detail one`; keeping them would preserve the invented shape the whole group exists to remove
- [x] 3b.4 Add the parsing tests from a **verbatim recorded line** (`data/results/cmp163_00/…/app.eduroam.geteduroam_2685.apk__1__300__aperv:mop_on_llm_off.logcat`, 2026-08-06): padded tag accepted, `expecting one of PKIX,SunX509 but found .` survives the rejoin intact, both class forms readable
- [x] 3b.5 Make the comparison consult the admission rule (D-O6): `TraceComparator.compare` lists the oracle directory itself and `run_phase5_validators.sh` never invokes the `oracles` subcommand, so a circular oracle is scored by the gate written to exclude it. Rejections carry into the report
- [x] 3b.6 Rewrite `scripts/derive_l3b_oracle.py`: key on `(apk, class, method, spec)`; apply the frame-form repair with the producer's rule (`ErrorDescription.FRAME_SUFFIX`) and assert 2,476 rows repaired with zero residue; **do not** substitute `data-analysis/repair_frame_keys.py`, which repairs 0 of them here (D-O3); declare the repair in the provenance block
- [x] 3b.7 Rewrite `scripts/derive_l3c_oracle.py` on the same key. Its sources arrive already repaired (0 frame-form rows), so the repair is a guard there, not a transformation — a non-zero count means the upstream defect reappeared and the run must abort rather than silently repair
- [x] 3b.8 Emit one oracle per APK, named `<apkBaseName>-oracle.yaml` per `TraceComparator.resolveOracleForApk`, each with its trace pair under `validator/traces/<apkBaseName>/`, written in the collector's format (D-O5). Delete the two pooled files — they resolve for no APK in batch mode
- [x] 3b.9 Re-run both derivations and record the counts: L3-b `ajc=13, dexlib2=17, both=12, only-ajc=1, only-dexlib2=5` over 8 paired APKs; L3-c the `app_producao` set over 12 apps, with the three `UnsatisfiedConstraint` specs named
- [x] 3b.10 Confirm `MINIMUM_ORACLES = 3` still holds against the per-APK set, and that `OracleLoaderTest`'s assertion against the real `oracles/` directory still passes
- [x] 3b.11 Run the `$DEXLIB2` validator suite; record the surefire counts rather than trusting a quiet `mvn -q`

## 4. Red evidence — barrier, nothing in Group 5 may be integrated before this is committed

- [x] 4.1 Run V0 against the **pre-repair** weaver: an advice with N monitor calls emits N invokes in descriptor order. It must fail. Commit the failing output as an artefact of this change — `EmissionCardinalityTest`, 4 of 5 assertions fail; `evidence/v0_red_emission_cardinality.txt`
- [x] 4.2 Run V2 against the **pre-repair** weaver: weave one APK with the `jca_android` set, baksmali it, count the `invoke-static` for the 9 events. They must be absent. Commit the failing output — `scripts/v2_woven_dex_events.py`, verdict FAIL; `evidence/v2_red_cryptoapp.{json,txt}`. `cryptoapp` reaches 2 of the 9; the other 7 belong to advices that wove nowhere in this APK and are reported `n/a` rather than counted as absent (see `evidence/v2_pinned_inputs.md`)
- [x] 4.3 Freeze the descriptor and the generated monitor sources that V2 weaves with, before it runs: record the sha256 of the descriptor and of each generated monitor source in the red-evidence artefact, and reuse exactly those inputs for the green run in 6.2. The `.mop` specification sets these monitors are generated from are being edited in parallel by issue #101; if they move between the red run and the green one, the two runs stop being comparable and INV-INS-108 proves nothing. Task 1.4's descriptor (`results/gh92_e2e2/monitors/MultiSpec_1MonitorAspect.json`) is committed and already insulated — V2 is the run that needs the pin — `evidence/v2_pinned_inputs.md`. The pinned set is `results/gh99_jca_android_monitors/monitors/`, generated 2026-08-06 before any of issue #101's 2026-08-07 edits, so the pin cost nothing
- [x] 4.4 Record in this file which commit carries the red evidence, so the repair commits can reference it (INV-INS-108) — **`e29c3694`** ("test(gh100): record V0 and V2 failing against the unrepaired weaver"). Filled in by the first repair commit, since the hash does not exist until the red evidence is committed
- [x] 4.5 Confirm that neither V0 nor V2 passes before the repair — a test that passes here is rejected as evidence and must be replaced — confirmed. The one V0 assertion that does pass, `unfusedAdviceStillEmitsExactlyOneInvoke`, is the negative control and is not offered as evidence for the repair

## 5. Emission repairs

- [x] 5.1 Make the inline path iterate `monitorCalls` in descriptor order: `EmitContext:51-52`, `MonitorInvokeBuilder:238-241` (reached from `:50`, `:136`, `:217`), `StaticInitializationEmitter:145-148`, `AfterThrowingEmitter:72` (D-A1, D-A2) — `primaryMonitorCall`/`primaryCall` are gone; `EmitContext.monitorCalls()` returns the list. `AfterThrowingEmitter` computes the throwing operand index **per call**, so `TryCatchSpec` carries a `List<Integer>` parallel to `toInsert` and `InstructionInjector` rewrites each invoke's own slot — fused calls can put the exception in different positions, and one index applied to all of them would rewrite an unrelated register. `StaticInitializationEmitter` emits the `ClassSignature` materialisation once and one invoke per event
- [x] 5.2 Add the inline/wrapper parity assertion: for the same advice, both plans emit the same monitor calls in the same order, with `WrapperEmitter:637` as the reference — `EmissionParityTest`
- [x] 5.3 ~~Widen the wrapper registry key at `DexWeaver:145` so distinct advices produce distinct keys~~ and guard the write at `:159` to fail loud on a rebinding (D-B1). **Issue #101 depends on this task** — **the key could not be widened**: it is the call site's own `MethodReference`, the only identity a call site carries, so any added component is one the lookup cannot supply. Repaired instead by **merging**: `WrapperEmitter` now emits one wrapper per original call whose body fires every advice bound to it, which makes the registry single-valued by construction. Measured on the production descriptor before the merge: 96 wrappers over 84 distinct keys, 10 keys bound more than once, **12 wrappers silently discarded**, `SecureRandom.getInstance(String)` bound three times. The fail-loud guard is in place and is now an assertion that the emitter and the registry agree. Confirmed with the user on 2026-08-07 and folded into `design.md` D-B1
- [x] 5.4 Check whether the widened key changes generated wrapper method names in a way that affects `BaksmaliDiffer` string matching; if it does, handle the Layer-1 normalisation gap here rather than leaving it to Layer 1 — **it does, and the gap was already there**. The merge shifts the emitter's `_<n>` overload numbering, and `specOfInvoke` looked names up **exactly** despite its javadoc claiming a prefix form. `buildWrapperToSpec` now keys on the base name and unions the specs of every advice over it; `specOfInvoke` tries the exact name first and then strips a trailing `_<digits>`. The descriptor-only derivation never saw the android.jar overloads the emitter numbers, so reproducing that count was never possible
- [x] 5.5 Make `parseCommonPointcut` raise `UnsupportedAspectConstructError` instead of matching everything — it returned `null` on a parse failure, which drops the class-level exclusions (`BaseAspect.notwithin()`, `!within(...RVMObject+)`) that appear in no advice's own expression, weaving every site they exist to exclude
- [x] 5.6 Add Java unit tests for the wrapper key collision and the fail-closed parse — `WrapperMergeTest` (3), `WrapperRegistryGuardTest` (3), and `DexWeaverDegradationTest.malformedCommonPointcutFailsTheWeave`, which **inverts** an existing test that asserted the fail-open behaviour the delta spec now forbids
- [x] 5.7 Run the full `$DEXLIB2` test suite — green: descriptor-reader 15 · pointcut-engine 157 · advice-emitter 95 · dex-mutator 86 · validator 59 · cli 7 · grammar-tests 16/3/7 · 0 failures

## 6. Green evidence and gates

- [x] 6.1 Re-run V0: it must pass, with descriptor order asserted, not just the call set — 5/5, against 4 failures in the red run; the source scan passes too. `evidence/green_deltas.md`
- [x] 6.2 Re-run V2 over the `jca_android` descriptor and monitor sources pinned in 4.3: the 9 events must appear as `invoke-static` in the woven DEX — verdict **PASS** over the same pinned bytes. Of the 9, `cryptoapp` reaches 2: `IvParameterSpecSpec_c3Event` ×0→×4 and `SecretKeySpecSpec_c3Event` ×0→×5, each now matching its kept sibling's count exactly. The other 7 stay `n/a` in both runs — their advices matched no site in this APK, so it is silent about them either way. `evidence/v2_green_cryptoapp.{json,txt}`
- [x] 6.3 Re-run the census script from 1.4 and record the post-repair counts against the pre-repair baseline — `INLINE PATH ITERATES`, truncation sites 3→0, **events dropped 9→0**, error emitters 8→0, with the descriptor and its routing unchanged (115 advices, 17 fused, 10 wrapper / 7 inline). `evidence/census_post_repair.json`
- [x] 6.4 Read the weaver counters for sites discarded under register pressure after the repair, and record the delta. An increase is reported explicitly; if it is systematic, open a follow-up issue rather than absorbing it — **`plansSkippedHighRegister` 0 → 0: no increase, no follow-up issue**. `matchesApplied` and `wrappersSubstituted` are unchanged (32, 74); `wrappersGenerated` falls 96→84, which is the wrapper merge removing exactly the 12 entries the registry used to overwrite. This is a statement about `cryptoapp`, not the corpus — the counter now reaches the Python layer (INV-INS-105) so the next corpus run answers it without being asked
- [x] 6.5 Execute L3-b against its derived oracles and record the verdict
- [x] 6.6 Execute L3-c against its derived oracles and record the verdict — this is the only regime where `UnsatisfiedConstraint` is observable, so it is the gate that speaks to the erased category
- [x] 6.7 State in the recorded verdicts that the runtime arm (L3-a) did not run and that V0/V2 prove emission and arrival in the woven DEX, not arrival in logcat
- [x] 6.8 State in the recorded verdicts that they are **characterization, not certification**: both sides of each derived oracle are frozen pre-repair recordings, so neither can flip green when the repair lands, and a certifying verdict would need a fresh `dexlib2` run (L3-a or V4), neither of which is in scope

## 7. Integration and verification

- [x] 7.1 Build the sibling reactor from its root and confirm the updated jar lands in `rv-android/lib/` — `mvn -q install -DskipTests -DskipMopAgent=true`, 12m12s, exit 0 (the ~4 min in the handoff was optimistic). `modules/rv-instrumentation-dexlib2/lib/instr-cli.jar` sha256 `f8a6a49c…`; `lib/frame-computer/rv-frame-computer.jar` also refreshed
- [x] 7.2 Add the Python integration test for the end-to-end counters path — `test_every_processed_apk_carries_counters_even_when_one_fails`: a mixed batch where one APK weaves and one fails, asserting both reach the merged results JSON with counters intact. That is INV-INS-105's actual claim ("successful or not"), and the gap group 1's tests left — a run whose failures dropped out of the merge would report a register-pressure increase concentrated in them as no increase at all. 36 passed
- [x] 7.3 Run `/rv-qa-lint-fix rv-instrumentation-dexlib2` — `src/` was already clean (autoflake, isort, black: no changes). The skill's scope is `src/` only; `black` was run over `tests/` separately, reformatting the test added in 7.2. Three pre-existing E501s remain in `src/config.py:73,78` and `dexlib_instrumentation.py:88`, all inside description/message strings and none introduced here
- [x] 7.4 Run `/rv-verify rv-instrumentation-dexlib2` — tests PASS (25 in-module, 36 with `rv-instrumentation-core`), security PASS (bandit's 2 expected `subprocess` findings), complexity PASS (avg CC 3.6 A, min MI 48.12 A), types SKIPPED (mypy not configured for this module). Lint FAIL on the three pre-existing E501s above; the format failures it reported were the 7.2 test and are fixed. `instrument_apks` is flagged long (226 lines, CC 6, linear) — pre-existing, not touched by this change
- [ ] 7.5 Invoke `/rv-code-reviewer` via the Skill tool
- [ ] 7.6 Run `/rv-docs-sync rv-instrumentation-dexlib2` if module docs need updating
- [x] 7.7 Notify issue #101 that task 5.3 has landed, since its empirical verification of the two hot specs is blocked on it
