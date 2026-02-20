# Tasks: gh27-unified-static-analysis

**Dependency order**: Group 0 (spike) → Groups 1-4 (Java) → Group 5 (Python parser) → Groups 6-7 (Python config/platform) → Group 8 (tests) → Group 9 (docs/specs) → Group 10 (E2E final gate)

**Java group order**: Group 1 (reachability — coverage denominator) → Group 2 (windows + WTG) → Group 3 (inputType/entries) → Group 4 (build/deploy). Reachability first because it defines the method universe; the JSON output writes sections in this priority order with flush between each, so timeout preserves the most critical data.

**Subagent orchestration**: Groups 1-4 are sequential (Java build chain). Groups 5-7 are sequential (Python dependency chain). Groups 8-9 are independent of each other but depend on 5-7. See `docs/WORKFLOW.md` Section 5.

---

## 0. Verification Spike (Pre-Implementation)

Answer the 5 Open Questions before coding to prevent wasted effort. Record answers as comments in the respective tasks below.

- [ ] 0.1 Q1: Verify `PropertyManager.v().getHintOfView(node)` exists — `grep -r "getHintOfView" $RVSEC_HOME/rvsec/rvsec-android/rvsec-gator/`. Record finding in Task 2.2
- [ ] 0.2 Q2: Verify `Scene.v().getCallGraph()` returns populated CG — create minimal GATOR test client that logs CG size. Record finding in Task 1.6
- [ ] 0.3 Q3: Verify `Configs.clientParams` propagates `-clientParam` — `grep -A 10 "clientParam" lib/gator/gator`. Record finding in Task 1.2
- [ ] 0.4 Q4: Verify apktool `@array/name` handling — `apktool d cryptoapp.apk -o /tmp/cryptoapp && grep -r "android:entries" /tmp/cryptoapp/res/layout/`. Record finding in Task 3.4
- [ ] 0.5 Q5: Verify `rvsec-mop-extractor` Soot API surface — `find $RVSEC_HOME/rvsec/rvsec-mop-extractor -name "*.java" -exec grep -h "^import soot\." {} \; | sort -u`. Record finding in Task 1.4

---

## 1. Java — RvsecUnifiedClient Core + Reachability (Coverage Denominator)

Files: `$RVSEC_HOME/rvsec/rvsec-android/rvsec-gator/client/`, `pom.xml`

Reachability comes first because it defines the method universe — the denominator for all coverage calculations. Coverage.aj logs `<class: returnType method(params)>` at runtime; the reachability section provides the static universe those signatures are matched against. The JSON output writes this section first with flush, so timeout preserves the most critical data.

- [ ] 1.1 Create `RvsecUnifiedClient.java` implementing `GUIAnalysisClient` with `run(GUIAnalysisOutput output)` entry point. Use `JsonWriter` for incremental output with flush after each section
- [ ] 1.2 Verify `Configs.clientParams` propagates `-clientParam mopDir=<path>` (Open Question 3)
- [ ] 1.3 Add JGraphT dependency (`jgrapht-core`, version managed by parent POM: 1.5.2) to `pom.xml`
- [ ] 1.4 Add `rvsec-mop-extractor` dependency with Soot exclusion. Verify Soot 3.3.0 compatibility (Open Question 5). Fallback: regex-based `.mop` parser
- [ ] 1.5 Add `rvsec-apk` dependency with FlowDroid/Soot exclusion
- [ ] 1.6 Verify `Scene.v().getCallGraph()` returns populated CG inside GATOR client (Open Question 2). If not, trigger with `PackManager.v().getPack("cg").apply()`
- [ ] 1.7 Implement `extractClasses(output)`: enumerate all application classes and methods from `Scene.v().getApplicationClasses()`
- [ ] 1.8 Implement `loadMopMethods(mopDir)`: load MOP spec signatures using JavamopFacade (or regex fallback)
- [ ] 1.9 Implement `getEntryPoints()`: public/protected methods of activity classes from `output.getActivities()`
- [ ] 1.10 Implement `buildJGraph(CallGraph cg)`: convert Soot CallGraph edges to JGraphT `DirectedGraph<SootMethod, DefaultEdge>`
- [ ] 1.11 Implement reachability computation: for each app method, compute `reachable` (path from any entry point), `reachesMop` (path to any MOP method), `directlyReachesMop` (direct edge to MOP method)
- [ ] 1.12 Implement `complementWithLifecycleCallbacks()` and `complementWithListenerCallbacks()` using GATOR's `getLifecycleHandlers()` and `getAllEventsAndTheirHandlers()`
- [ ] 1.13 Write `reachability` JSON section and flush — this is the first section written
- [ ] 1.14 Test: verify reachability data against current REACH output for `cryptoapp.apk`. Document accepted differences

## 2. Java — Windows and WTG Extraction

Files: `RvsecUnifiedClient.java`

- [ ] 2.1 Implement `extractWindows(output)` using GATOR APIs: `getActivities()`, `getActivityRoots()` + recursive `getChildren()`, `PropertyManager.v().getTextsOrTitlesOfView()`, `PropertyManager.v().getHintOfView()` — produces `windows` JSON section
- [ ] 2.2 Verify `PropertyManager.v().getHintOfView(node)` exists (Open Question 1). If not, extract hint from decoded XML alongside inputType
- [ ] 2.3 Port WTG extraction from `RvsecWtgClient.run()` into `extractTransitions()` — produces `transitions` JSON section
- [ ] 2.4 Write `windows` section (flush), then `transitions` section (flush + close)
- [ ] 2.5 Test: run unified client on `cryptoapp.apk`, verify window and transition data matches current GESDA + GATOR output

## 3. Java — inputType and entries Extraction

Files: `RvsecUnifiedClient.java`

- [ ] 3.1 Implement layout file resolution: find `setContentView(R.layout.X)` in Soot method bodies of each activity, resolve to layout filename
- [ ] 3.2 Implement decoded XML parsing: read `Configs.resourceLocation + "/layout/" + name + ".xml"` with Java DOM parser
- [ ] 3.3 Extract `android:inputType` attribute (string from apktool-decoded XML). Handle pipe-separated flags (e.g., `textPassword|textVisiblePassword`) — take first value
- [ ] 3.4 Verify apktool `@array/name` handling (Open Question 4). Implement `android:entries` extraction — resolve `@array/` references from `res/values/arrays.xml` if needed
- [ ] 3.5 Match XML widget data to GATOR widget nodes by comparing `android:id` resource name with `NNode.idNode.getIdName()`
- [ ] 3.6 Test: verify `inputType` and `entries` match current GESDA output for `cryptoapp.apk`

## 4. Java — Build and Deploy

- [ ] 4.1 Add `maven-shade-plugin` to `pom.xml` for fat JAR build (bundle JGraphT + mop-extractor + apk-reader, exclude Soot)
- [ ] 4.2 Build: `cd $RVSEC_HOME/rvsec/rvsec-android/rvsec-gator/client && mvn package -DskipTests`
- [ ] 4.3 Create `rv-android/lib/unified/` directory and copy `rvsec-unified-client.jar`
- [ ] 4.4 End-to-end test: run full GATOR command from CLI on `cryptoapp.apk`, verify unified JSON output

## 5. Python — Constants and UnifiedParser

Files: `modules/rv-android-core/src/rv_android_core/constants.py`, `modules/rv-static-analysis/src/rv_static_analysis/parser/static/unified_parser.py`

- [ ] 5.1 Add `EXTENSION_UNIFIED = ".json"` to `rv-android-core/constants.py`
- [ ] 5.2 Create `UnifiedParser` class extending `BaseStaticAnalysisParser`
- [ ] 5.3 Implement `parse_file(file_path, package) -> StaticAnalysisData` — reads JSON, delegates to section parsers
- [ ] 5.4 Implement `_parse_classes(data, package) -> Classes` — iterates `reachability` section, applies SignatureNormalizer (INV-ANA-02), filters by code_package (INV-ANA-03)
- [ ] 5.5 Implement `_parse_windows(data, package, classes) -> Windows` — iterates `windows` section, processes widgets and listeners, maps event types
- [ ] 5.6 Implement `_parse_transitions(data, windows) -> WindowTransitionGraph` — iterates `transitions` section, resolves source/target by window ID
- [ ] 5.7 Implement per-section try/except for graceful degradation (INV-ANA-06)
- [ ] 5.8 Run `/rv-doc-code modules/rv-static-analysis/src/rv_static_analysis/parser/static/unified_parser.py`

## 6. Python — Config and StaticAnalyzer

Files: `modules/rv-static-analysis/src/rv_static_analysis/config.py`, `modules/rv-static-analysis/src/rv_static_analysis/analysis/static/static_analysis.py`

- [ ] 6.1 Update `RVStaticAnalysisConfig`: remove `gesda_jar`, `gator_dir`, `reach_jar`. Add `unified_jar`, `jvm_memory`, `unified_timeout`
- [ ] 6.2 Update `get_tool_command('unified', ...)` to produce GATOR command with `-client RvsecUnifiedClient -clientParam mopDir=<dir>`
- [ ] 6.3 Update `StaticAnalyzer`: remove `_run_gesda()`, `_run_gator()`, `_run_reachability()`. Add `_run_unified()`
- [ ] 6.4 Update `StaticAnalysisResult`: remove 3 file paths, add `unified_file` and `timed_out`
- [ ] 6.5 Handle `RVCommandTimeoutError` in `_execute_command()` — set `result.timed_out = True`
- [ ] 6.6 Update `get_static_data()` to use `UnifiedParser` instead of three separate parsers
- [ ] 6.7 Run `/rv-doc-code modules/rv-static-analysis/src/rv_static_analysis/analysis/static/static_analysis.py`

## 7. Python — StaticAnalysisParser Facade and Platform

Files: `modules/rv-static-analysis/src/rv_static_analysis/parser/static/static_analysis_parser.py`, `modules/rv-platform/src/rv_platform/components/static_analysis.py`

- [ ] 7.1 Update `StaticAnalysisParser` facade: replace three parser instances with `UnifiedParser`. Add `parse_unified()` method
- [ ] 7.2 Update `read_static_analysis_files()` to use `.json` extension
- [ ] 7.3 Update rv-platform `StaticAnalysisComponent.copy_static_analysis_files()`: change extensions from `[EXTENSION_METHODS, EXTENSION_GESDA, EXTENSION_GATOR, EXTENSION_REACH]` to `[EXTENSION_METHODS, EXTENSION_UNIFIED]`
- [ ] 7.4 Backup old parsers to `backup/`: `gesda_parser.py`, `gator_parser.py`, `reach_parser.py` and their tests (P3)
- [ ] 7.5 Delete old parsers and test files from source tree
- [ ] 7.6 Grep all modules for dangling references: `grep -r "gesda_parser\|gator_parser\|reach_parser\|GesdaParser\|GatorParser\|ReachParser\|EXTENSION_GESDA\|EXTENSION_GATOR\|EXTENSION_REACH\|gesda_file\|gator_file\|reach_file" modules/`. Critical modules: rv-static-analysis, rv-platform, rv-experiment, rv-coverage, rv-agent
- [ ] 7.7 Run `/rv-qa-lint-fix rv-static-analysis` — auto-fix formatting and imports after bulk changes

## 8. Tests

- [ ] 8.1 Create `tests/resources/cryptoapp.apk.json` test fixture from real unified tool output
- [ ] 8.2 Create `test_unified_parser.py`: well-formed JSON, empty JSON, missing sections, missing file, inner class normalization, code_package filtering, partial section failure, empty windows array, transitions referencing unknown window IDs (skip with warning), truncated JSON from timeout (valid sections parsed, missing sections return empty objects)
- [ ] 8.3 Update `test_static_analysis_parser.py` for unified flow
- [ ] 8.4 Update `test_static_analysis.py` (or `test_static_analyzer.py`) for single-tool pipeline
- [ ] 8.5 Update `test_config.py` for new configuration fields
- [ ] 8.6 Update `conftest.py` fixtures if needed
- [ ] 8.7 Create baseline equivalence test: compare unified output counts (windows, transitions, methods, reachable, reachesMop, directlyReachesMop) against saved 3-tool baseline for `cryptoapp.apk`. Exact match for windows/transitions/methods/directlyReachesMop; ±10% tolerance for reachable/reachesMop
- [ ] 8.8 Run `/rv-test-run rv-static-analysis` — all tests must pass
- [ ] 8.9 Run `/rv-test-run rv-platform` — verify no breakage from extension change

## 9. Documentation and Specs

- [ ] 9.1 Update `modules/rv-static-analysis/CLAUDE.md` — reflect unified tool architecture
- [ ] 9.2 Update `modules/rv-android-core/CLAUDE.md` — add `EXTENSION_UNIFIED` to constants section
- [ ] 9.3 Run `/rv-verify rv-static-analysis` — tests + lint + type checks
- [ ] 9.4 Run `/rv-verify rv-platform` — tests + lint + type checks
- [ ] 9.5 Run `/rv-code-reviewer` — review full gh27 implementation against specs and design
- [ ] 9.6 (During `/opsx:sync`) Add end-to-end pipeline sequence diagram to `openspec/specs/analysis/spec.md` — covers the full flow from static analysis through execution to post-processing: StaticAnalyzer → unified JSON → StaticAnalysisData → rv-agent execution → Coverage.aj → .logcat → CoverageTracker → ResultProcessor. This diagram documents unchanged components and belongs in the main spec, not the delta

## 10. E2E Validation (Final Gate)

Full rv-experiment run exercising the entire pipeline: pre-processing (instrumentation + unified static analysis) → execution (rv-agent + Coverage.aj logging) → post-processing (logcat parsing + coverage calculation). This is the final validation before closing gh27.

Comparison baseline: `docker/data/results/cli_experiment_20260219_095634_21537073/cryptoapp.apk/` (3-tool pipeline, 8 RVSEC-COV methods logged in 60s).

- [ ] 10.1 Run full experiment: `uv run rv-experiment run --tools rvagent:pure_algorithm --apks-dir ./apks_examples --specification-set jca --timeout 60 --name gh27_e2e_validation`
- [ ] 10.2 Verify unified JSON created: `ls out/static/cryptoapp.apk.json` — file exists with all 3 sections (reachability, windows, transitions)
- [ ] 10.3 Verify coverage denominator > 0: check experiment log for `static_analysis_data` summary showing non-zero method count
- [ ] 10.4 Verify coverage > 0%: check `.logcat` file for `RVSEC-COV` lines — at least some methods should be logged during execution
- [ ] 10.5 Verify coverage calculation: check `*_results.json` for `method_coverage` and `mop_method_coverage` fields with non-zero values
- [ ] 10.6 Verify MOP detection: `grep "RVSEC" results/<id>/cryptoapp.apk/*.logcat` — MOP violations should appear if JCA APIs were exercised
- [ ] 10.7 Compare against baseline: coverage numbers should be comparable (±20%) to `cli_experiment_20260219` run. Document any differences
- [ ] 10.8 Verify timing improvement: `static_analysis_duration` should be less than previous 3-tool sum
