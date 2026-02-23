# Tasks: gh27-unified-static-analysis

**Dependency order**: Group 0 (spike) → Groups 1-4 (Java) → Group 5 (Python parser) → Groups 6-7 (Python config/CLI/platform + dead code cleanup + rv-agent-validation migration) → Groups 8-9 (tests + docs, independent of each other) → Group 10 (E2E final gate)

**Java group order**: Group 1 (reachability — coverage denominator) → Group 2 (windows + WTG) → Group 3 (inputType/entries) → Group 4 (build/deploy). Reachability first because it defines the method universe; the JSON output writes sections in this priority order with flush between each, so timeout preserves the most critical data.

**Subagent orchestration**: Groups 1-4 are sequential (Java build chain). Groups 5-7 are sequential (Python dependency chain). Groups 8-9 are independent of each other but depend on 5-7. See `docs/WORKFLOW.md` Section 5.

---

## 0. Verification Spike (Pre-Implementation)

Answer the 6 Open Questions before coding to prevent wasted effort. Record answers as comments in the respective tasks below.

- [ ] 0.1 Q1: Verify `PropertyManager.v().getHintOfView(node)` exists — `grep -r "getHintOfView" $RVSEC_HOME/rvsec/rvsec-android/rvsec-gator/`. Record finding in Task 2.2
- [ ] 0.2 Q2: Verify `Scene.v().getCallGraph()` returns populated CG — create minimal GATOR test client that logs CG size. Record finding in Task 1.6
- [ ] 0.3 Q3: Verify `Configs.clientParams` propagates `-clientParam` — `grep -A 10 "clientParam" lib/gator/gator`. Record finding in Task 1.2
- [ ] 0.4 Q4: Verify apktool `@array/name` handling — `apktool d cryptoapp.apk -o /tmp/cryptoapp && grep -r "android:entries" /tmp/cryptoapp/res/layout/`. Record finding in Task 3.4
- [ ] 0.5 Q5: Verify `rvsec-mop-extractor` Soot API surface — `find $RVSEC_HOME/rvsec/rvsec-mop-extractor -name "*.java" -exec grep -h "^import soot\." {} \; | sort -u`. Record finding in Task 1.4
- [ ] 0.6 Q6: Verify JCA class resolution with rt.jar inside GATOR — **CRITICAL for reachability correctness**. Without rt.jar, JCA classes (javax.crypto.Cipher, java.security.MessageDigest) are phantom references with no active body. Soot resolves static calls (e.g., `MessageDigest.getInstance()`) but NOT instance method calls (`md.update()`, `md.digest()`) because virtual dispatch requires the class hierarchy from the active body. This breaks `reachesMop` and `directlyReachesMop` flags for instance methods.

  **Background**: REACH and GESDA both pass rt.jar via `set_soot_classpath(androidDir + ":" + rtJarPath)` + `set_prepend_classpath(true)` (see `rvsec-reachability/SootConfig.java` L69-80, `rvsec-gesda/SootConfig.java` L52-63). GATOR's `Main.java` accepts `-jre` (L59-60), includes it in `computeClasspath()` (L180: `Configs.android + ":" + Configs.jre`), but the Python launcher **never passes** `-jre`, so `Configs.jre` defaults to `""`.

  **Steps**:
  1. Modify GATOR launcher (`lib/gator/gator`): add `--jre` argparse parameter, pass as `-jre <path>` to Main.java command
  2. Create minimal test client that dumps `Scene.v().getCallGraph()` edges for `cryptoapp.apk`:
     - Run WITHOUT rt.jar: `python gator a -p cryptoapp.apk --client-jar test.jar -client TestCGClient --out /tmp/cg_no_rt.txt`
     - Run WITH rt.jar: `python gator a -p cryptoapp.apk --client-jar test.jar -client TestCGClient --out /tmp/cg_with_rt.txt --jre ~/.sdkman/candidates/java/8.0.302-open/jre/lib/rt.jar`
  3. Compare: count edges involving `javax.crypto.Cipher`, `java.security.MessageDigest`. Specifically verify:
     - `MessageDigest.getInstance()` — should appear in BOTH (static call, resolved without body)
     - `MessageDigest.update()`, `MessageDigest.digest()` — should appear only WITH rt.jar (instance calls, need active body for virtual dispatch)
     - `Cipher.init()`, `Cipher.doFinal()` — same pattern, only WITH rt.jar
  4. If confirmed: rt.jar is REQUIRED. Keep `--jre` launcher change. Update `RVStaticAnalysisConfig` to pass `rt_jar` to GATOR command (reuse existing `rt_jar` field from config.py L65-68). Update plan.md Section 6 (Parameter Passing) and Section 7.3 (config)
  5. If NOT confirmed (JCA instance methods appear even without rt.jar): document why and skip the launcher change
  6. Record findings and update all affected artifacts before proceeding to Group 1

  **Fallback (if GATOR's Soot 3.3.0 has issues with rt.jar)**: Use `android-platforms` from Sable/FlowDroid team (cloned at `/home/pedro/desenvolvimento/aplicativos/android/platforms-sable`). These are enhanced `android.jar` files that may include stubs for JCA classes. Test with `-android <sable-platform-jar>` instead of `-jre`

---

## 1. Java — RvsecAnalysisClient Core + Reachability (Coverage Denominator)

Files: `$RVSEC_HOME/rvsec/rvsec-android/rvsec-gator/client/`, `pom.xml`

Reachability comes first because it defines the method universe — the denominator for all coverage calculations. Coverage.aj logs `<class: returnType method(params)>` at runtime; the reachability section provides the static universe those signatures are matched against. The JSON output writes this section first with flush, so timeout preserves the most critical data.

- [ ] 1.1 Create `RvsecAnalysisClient.java` implementing `GUIAnalysisClient` with `run(GUIAnalysisOutput output)` entry point. Use `JsonWriter` for incremental output with flush after each section
- [ ] 1.2 Verify `Configs.clientParams` propagates `-clientParam mopDir=<path>` (Open Question 3)
- [ ] 1.3 Add JGraphT dependency (`jgrapht-core`, version managed by parent POM: 1.5.2) to `pom.xml`
- [ ] 1.4 Add `rvsec-mop-extractor` dependency with BOTH Soot exclusions (`ca.mcgill.sable:soot` AND `org.soot-oss:soot`). Verify Soot 3.3.0 compatibility (Open Question 5). Fallback: regex-based `.mop` parser
- [ ] 1.5 Add `rvsec-apk` dependency with FlowDroid/Soot exclusion
- [ ] 1.6 Verify `Scene.v().getCallGraph()` returns populated CG inside GATOR client (Open Question 2). If not, trigger with `PackManager.v().getPack("cg").apply()`
- [ ] 1.7 Implement `extractClasses(output)`: enumerate all application classes and methods from `Scene.v().getApplicationClasses()`. **D7 rule**: use `SootClass.getName()` for all class names and `SootMethod.getSignature()` for all signatures — these return JVM `$` notation for inner classes. Do NOT use `getShortName()`, `getType().toString()`, or string concatenation that could produce `.` notation
- [ ] 1.8 Implement MOP loading in two steps: (a) `loadMopSignatures(mopDir)` — load MOP spec signatures as `(className, methodName)` pairs using JavamopFacade (or regex fallback). MopFacade returns class+method ONLY, no params. (b) `resolveMopInScene(mopSignatures)` — for each MOP pair, find ALL `SootMethod` objects in `Scene.v()` where `getDeclaringClass().getName().equals(className) && getName().equals(methodName)`. This resolves overloads: if `Cipher.init` is in a MOP spec, ALL overloads (`init(int, Key)`, `init(int, Key, AlgorithmParameterSpec)`, etc.) become BFS seeds. This is consistent with MopFacade's matching behavior — the MOP monitor instruments all overloads
- [ ] 1.9 Implement `getEntryPoints()`: public/protected methods of activity classes from `output.getActivities()`
- [ ] 1.10 Implement `buildJGraph(CallGraph cg)`: convert Soot CallGraph edges to JGraphT `DefaultDirectedGraph<SootMethod, DefaultEdge>`, filtering self-loops
- [ ] 1.11 Implement reachability computation via multi-source BFS (O(V+E) total, no paths stored — boolean flags only): (a) `reachable`: multi-source BFS forward from all entry points — every visited node is reachable; (b) `reachesMop`: multi-source BFS on `EdgeReversedGraph` from all resolved MOP SootMethods (all overloads, from task 1.8b) — every visited node reaches MOP; (c) `directlyReachesMop`: scan outgoing edges of each app method, check if any callee is in the resolved MOP set (class+method match, all overloads included)
- [ ] 1.12 Implement `complementWithLifecycleCallbacks()` and `complementWithListenerCallbacks()` using GATOR's `getLifecycleHandlers()` and `getAllEventsAndTheirHandlers()`
- [ ] 1.13 Write `reachability` JSON section and flush — this is the first section written
- [ ] 1.14 Test: verify reachability data against current REACH output for `cryptoapp.apk`. Document accepted differences

## 2. Java — Windows and WTG Extraction

Files: `RvsecAnalysisClient.java`

- [ ] 2.1 Implement `extractWindows(output)` using GATOR APIs: `getActivities()`, `getActivityRoots()` + recursive `getChildren()`, `PropertyManager.v().getTextsOrTitlesOfView()`, `PropertyManager.v().getHintOfView()` — produces `windows` JSON section. **D7 rule**: window names and handler signatures must use `SootClass.getName()` / `SootMethod.getSignature()` (JVM `$` notation)
- [ ] 2.2 Verify `PropertyManager.v().getHintOfView(node)` exists (Open Question 1). If not, extract hint from decoded XML alongside inputType
- [ ] 2.3 Port WTG extraction from `RvsecWtgClient.run()` into `extractTransitions()` — produces `transitions` JSON section
- [ ] 2.4 Write `windows` section (flush), then `transitions` section (flush + close)
- [ ] 2.5 Test: run analysis client on `cryptoapp.apk`, verify window and transition data matches current GESDA + GATOR output

## 3. Java — inputType and entries Extraction

Files: `RvsecAnalysisClient.java`

- [ ] 3.1 Implement layout file resolution: find `setContentView(R.layout.X)` in Soot method bodies of each activity, resolve to layout filename
- [ ] 3.2 Implement decoded XML parsing: read `Configs.resourceLocation + "/layout/" + name + ".xml"` with Java DOM parser
- [ ] 3.3 Extract `android:inputType` attribute (string from apktool-decoded XML). Handle pipe-separated flags (e.g., `textPassword|textVisiblePassword`) — take first value
- [ ] 3.4 Verify apktool `@array/name` handling (Open Question 4). Implement `android:entries` extraction — resolve `@array/` references from `res/values/arrays.xml` if needed
- [ ] 3.5 Match XML widget data to GATOR widget nodes by comparing `android:id` resource name with `NNode.idNode.getIdName()`
- [ ] 3.6 Test: verify `inputType` and `entries` match current GESDA output for `cryptoapp.apk`

## 4. Java — Build, Deploy, and Tests

- [ ] 4.1 Add `maven-assembly-plugin` to `pom.xml` for fat JAR build (`jar-with-dependencies`, same pattern as `rvsec-reachability`). Mark `rvsec-gator-sootandroid` as `<scope>provided</scope>` (already on GATOR's classpath). Bundle JGraphT + mop-extractor (exclude BOTH `ca.mcgill.sable:soot` AND `org.soot-oss:soot`) + apk-reader (exclude FlowDroid)
- [ ] 4.2 Build: `cd $RVSEC_HOME/rvsec/rvsec-android/rvsec-gator/client && mvn clean install -DskipTests` (assembly creates fat JAR on `package`, resources-plugin copies to `rv-android/lib/analysis-client/` on `install`)
- [ ] 4.3 Verify `rvsec-analysis-client.jar` was copied to `rv-android/lib/analysis-client/` by `maven-resources-plugin` during `mvn install`
- [ ] 4.4 Update `lib/gator/teste.sh`: change `RvsecWtgClient` → `RvsecAnalysisClient`, update `client_jar` path to `lib/analysis-client/rvsec-analysis-client.jar`, add `-clientParam mopDir=...`
- [ ] 4.5 Validate `teste.sh`: run `bash lib/gator/teste.sh` on `cryptoapp.apk`, verify it produces valid analysis JSON (this validates the script itself, not just the Java tool)
- [ ] 4.6 End-to-end test: run full GATOR command from CLI on `cryptoapp.apk`, verify analysis JSON output

### 4.7 Normalization validation — Java side (D7)

Verify that the Java client writes all class names in JVM `$` notation via `SootClass.getName()`. This eliminates the GESDA/GATOR inner class notation inconsistency at the source (see `rvsec-regerar-resultados/docs/NOVO/06_normalizacao_inner_classes.md`).

- [ ] 4.7a Code review: grep `RvsecAnalysisClient.java` for all places that emit class names in JSON. Verify EVERY one uses `SootClass.getName()` or `SootMethod.getSignature()` — NOT `SootClass.getType().toString()`, NOT `SootClass.getShortName()`, NOT string concatenation. List each emit point and the API used
- [ ] 4.7b Run analysis client on `cryptoapp.apk`. Extract all `className` values from the JSON output: `jq -r '.reachability[].className' cryptoapp.apk.json | sort -u > /tmp/class_names.txt`. Verify NO class name contains a `.` between two uppercase segments (would indicate inner class in wrong notation): `grep -P '[A-Z][a-z]*\.[A-Z]' /tmp/class_names.txt` — should return 0 hits for inner classes (packages like `android.os.Bundle` are OK — they have lowercase after the dot)
- [ ] 4.7c Specific inner class check: if `cryptoapp.apk` has inner classes, verify they use `$`: `grep '\$' /tmp/class_names.txt` — should show entries like `MainActivity$1`, `SomeClass$InnerClass`, etc.
- [ ] 4.7d Cross-check with Coverage.aj format: compare a sample of signatures from the JSON with what Coverage.aj would log at runtime (`method.getDeclaringClass().getName()` format). They must match exactly — no normalization needed at matching time
- [ ] 4.7e Run analysis client on an APK known to have inner classes with complex nesting (e.g., an APK with anonymous inner classes, nested inner classes, or Parcelable CREATOR patterns). Verify all use `$` notation in JSON output

### 4.8 Java unit tests

JUnit 4.12 is available via `rvsec-gator-parent` dependencyManagement. Tests go in `rvsec-gator/client/src/test/java/`. Note: `rvsec-gator-parent/pom.xml` has `skipTests=true` by default — override with `mvn test -DskipTests=false` or remove the property for the client module.

**Test infrastructure:**

- [ ] 4.8a Add JUnit 4 `<dependency>` (scope test) to `rvsec-gator/client/pom.xml`. Create `src/test/java/br/unb/cic/gator/client/` directory and `src/test/resources/` for fixtures
- [ ] 4.8b Create test fixtures: copy `MessageDigestSpec.mop` and one additional MOP spec (e.g., `CipherSpec.mop`) to `src/test/resources/test-specs/`. Create `src/test/resources/test-layouts/activity_main.xml` with sample `android:inputType` and `android:entries` attributes

**Unit tests (no Soot/GATOR dependency — synthetic data only):**

- [ ] 4.8c `MopSignatureLoaderTest.java` — test `loadMopSignatures(mopDir)`:
  - Parse `MessageDigestSpec.mop` → expect pairs: (`java.security.MessageDigest`, `getInstance`), (`java.security.MessageDigest`, `digest`), (`java.security.MessageDigest`, `update`)
  - Parse `CipherSpec.mop` → expect pairs with `javax.crypto.Cipher`
  - Empty directory → expect empty set
  - Directory with non-.mop files → expect empty set (no crash)
- [ ] 4.8d `ReachabilityBfsTest.java` — test multi-source BFS on synthetic JGraphT `DefaultDirectedGraph`:
  - Build a graph: A→B→C→D, E→C (two entry points A, E; MOP method D). Verify: A,B,C,D,E all reachable; only C,D reachesMop (reverse BFS from D); only C directlyReachesMop (outgoing edge to D)
  - Disconnected graph: A→B, C→D (entry A, MOP D). Verify: A,B reachable but NOT reachesMop; C,D unreachable from entries
  - Self-loop: A→A. Verify no infinite loop, A is reachable
  - Empty graph → all flags false, no crash
- [ ] 4.8e `JsonOutputTest.java` — test JSON serialization structure:
  - Serialize a minimal `RvsecAnalysisClient` output (mock data). Parse result with `javax.json` or `com.google.gson`. Verify: top-level keys are `reachability`, `windows`, `transitions` in that order. Verify `reachability` array entries have fields: `className`, `methodSignature`, `reachable`, `reachesMop`, `directlyReachesMop`
  - Verify inner class names use `$` notation in output (e.g., `Outer$Inner`, not `Outer.Inner`)
  - Verify empty sections produce empty JSON arrays `[]`, not null
- [ ] 4.8f `XmlInputTypeTest.java` — test layout XML parsing:
  - Parse `test-layouts/activity_main.xml` → extract `inputType` and `entries` per widget ID
  - Pipe-separated flags (e.g., `textPassword|textVisiblePassword`) → take first value (`textPassword`)
  - `@array/items` reference → resolve from `arrays.xml` (or return raw reference if Q4 determines apktool doesn't resolve)
  - Missing `inputType` attribute → default empty string
  - Malformed XML → graceful failure (empty result, no crash)

**Integration tests (require Soot + GATOR — run via `mvn verify` with failsafe-plugin):**

- [ ] 4.8g Add `maven-failsafe-plugin` to `pom.xml` for integration tests (`*IT.java` naming convention). Configure to skip by default, run with `-DskipITs=false`
- [ ] 4.8h `RvsecAnalysisClientIT.java` — full integration test on `cryptoapp.apk`:
  - Run `RvsecAnalysisClient` via GATOR on `cryptoapp.apk` (requires `RVSEC_HOME`, `ANDROID_HOME`). Parse output JSON
  - Assert: `reachability` section non-empty (method count > 0)
  - Assert: `windows` section non-empty (at least 1 activity window)
  - Assert: `transitions` section present (can be empty for simple apps)
  - Assert: at least one method has `directlyReachesMop = true` (cryptoapp uses JCA)
  - Assert: all `className` values use `$` for inner classes (grep for `.` between uppercase segments = 0 hits)
  - Assert: JSON is valid (no truncation, all brackets closed)
- [ ] 4.8i `BaselineComparisonIT.java` — compare against 3-tool baseline:
  - Load saved baseline counts from `src/test/resources/baseline/cryptoapp_baseline.json` (window count, transition count, method count, directlyReachesMop count)
  - Run unified analysis on `cryptoapp.apk`, extract same counts
  - Assert exact match: windows, transitions, methods, directlyReachesMop
  - Assert ±10% tolerance: reachable, reachesMop (due to removing all-reachable)
- [ ] 4.8j Run unit tests: `cd $RVSEC_HOME/rvsec/rvsec-android/rvsec-gator/client && mvn test -DskipTests=false` — all unit tests must pass
- [ ] 4.8k Run integration tests: `cd $RVSEC_HOME/rvsec/rvsec-android/rvsec-gator/client && mvn verify -DskipTests=false -DskipITs=false` — all integration tests must pass (requires `cryptoapp.apk` in a known location)

## 5. Python — Constants and StaticAnalysisParser

Files: `modules/rv-android-core/src/rv_android_core/constants.py`, `modules/rv-static-analysis/src/rv_static_analysis/parser/static/static_analysis_parser.py`

- [ ] 5.1 Add `EXTENSION_STATIC_ANALYSIS = ".json"` to `rv-android-core/constants.py`. Remove old extension constants: `EXTENSION_GESDA`, `EXTENSION_GATOR` (= `".wtg"`), and `EXTENSION_REACH` from the same file
- [ ] 5.2 Rewrite `StaticAnalysisParser` in `static_analysis_parser.py`: standalone class that parses the static analysis JSON into `StaticAnalysisData`. Uses `LoggingManager` directly for logging
- [ ] 5.3 Implement `parse_file(file_path, package) -> StaticAnalysisData` — reads JSON, delegates to section parsers. Include truncated JSON recovery: on `JSONDecodeError`, find last complete `]` bracket, close with `}`, retry parse
- [ ] 5.4 Implement `_parse_classes(data, package) -> Classes` — iterates `reachability` section, applies SignatureNormalizer (INV-ANA-02), filters by code_package (INV-ANA-03)
- [ ] 5.5 Implement `_parse_windows(data, package, classes) -> Windows` — iterates `windows` section, processes widgets and listeners, maps event types
- [ ] 5.6 Implement `_parse_transitions(data, windows) -> WindowTransitionGraph` — iterates `transitions` section, resolves source/target by window ID
- [ ] 5.7 Implement per-section try/except for graceful degradation (INV-ANA-06)
- [ ] 5.8 Run `/rv-doc-code modules/rv-static-analysis/src/rv_static_analysis/parser/static/static_analysis_parser.py`

## 6. Python — Config, StaticAnalyzer, CLI, and rv-experiment Config

Files: `modules/rv-static-analysis/src/rv_static_analysis/config.py`, `modules/rv-static-analysis/src/rv_static_analysis/analysis/static/static_analysis.py`, `modules/rv-static-analysis/src/rv_static_analysis/__main__.py`, `modules/rv-experiment/src/rv_experiment/config.py`

- [ ] 6.1 Update `RVStaticAnalysisConfig`: remove `gesda_jar`, `gator_dir`, `reach_jar`. Add `analysis_client_jar`, `jvm_memory`, `analysis_timeout`
- [ ] 6.2 Update `get_tool_command('analysis', ...)` to produce GATOR command with `-client RvsecAnalysisClient -clientParam mopDir=<dir> --jre <rt_jar_path>`. Reuse existing `rt_jar` config field (config.py L65-68)
- [ ] 6.3 Update `StaticAnalyzer`: remove `_run_gesda()`, `_run_gator()`, `_run_reachability()`. Add `_run_analysis()`
- [ ] 6.4 Update `StaticAnalysisResult`: remove 3 file paths, add `analysis_file` and `timed_out`
- [ ] 6.5 Handle `RVCommandTimeoutError` in `_execute_command()` — set `result.timed_out = True`
- [ ] 6.6 Update `get_static_data()` to use `StaticAnalysisParser`. **Pre-existing bug**: current code calls `parser.parse(self.gesda_file, self.gator_file, self.reach_file, ...)` but `StaticAnalysisParser.parse()` signature is `parse(reach_file, gator_file, gesda_file, ...)` — positional args swap gesda↔reach, causing both parsers to receive the wrong file format and silently return empty data
- [ ] 6.7 Update `rv-static-analysis/__main__.py` (473 lines, CLI entry point): replace `--gesda-jar`, `--gator-dir`, `--reach-jar` args with `--analysis-client-jar`. Replace tool choices `['gesda', 'gator', 'reach']` with single analysis invocation. Update config mapping dict (`'gesda_jar'` etc. → `'analysis_client_jar'`). Update result display (`result.gesda_file/gator_file/reach_file` → `result.analysis_file`). Update module description, help text, and usage examples. Add `--jvm-memory` and `--analysis-timeout` as optional CLI args
- [ ] 6.8 Update `rv-experiment/src/rv_experiment/config.py` `get_static_analysis_config()` (~L598): resolve and provide `analysis_client_jar` path (from `lib/analysis-client/rvsec-analysis-client.jar` relative to `RVSEC_HOME` or project root), `jvm_memory` (default `"8g"`), and `analysis_timeout` (default `600`) fields to `RVStaticAnalysisConfig`. Without this, experiment mode (via `rv-experiment`) cannot find the analysis client JAR and pre-processing will fail
- [ ] 6.9 Run `/rv-doc-code modules/rv-static-analysis/src/rv_static_analysis/analysis/static/static_analysis.py`

## 7. Python — Parser Cleanup and Platform

Files: `modules/rv-static-analysis/src/rv_static_analysis/parser/static/static_analysis_parser.py`, `modules/rv-platform/src/rv_platform/components/static_analysis.py`

- [ ] 7.1 Verify `StaticAnalysisParser.parse_file()` is compatible with all callers in rv-static-analysis and rv-experiment
- [ ] 7.2 Update `read_static_analysis_files()` to use `.json` extension
- [ ] 7.3 Update rv-platform `StaticAnalysisComponent.copy_static_analysis_files()`: change extensions from `[EXTENSION_METHODS, EXTENSION_GESDA, EXTENSION_GATOR, EXTENSION_REACH]` to `[EXTENSION_METHODS, EXTENSION_STATIC_ANALYSIS]`
- [ ] 7.4 Backup old parsers to `backup/`: `gesda_parser.py`, `gator_parser.py`, `reach_parser.py` and their tests (P3)
- [ ] 7.5 Delete old parsers and test files from source tree
- [ ] 7.6 Grep all modules for dangling references: `grep -r "gesda_parser\|gator_parser\|reach_parser\|GesdaParser\|GatorParser\|ReachParser\|EXTENSION_GESDA\|EXTENSION_GATOR\|EXTENSION_REACH\|gesda_file\|gator_file\|reach_file" modules/`. Critical modules: rv-static-analysis, rv-platform, rv-experiment, rv-coverage, rv-agent, rv-agent-validation
- [ ] 7.6a Update `rv-experiment/src/rv_experiment/constants.py`: remove re-exports of `EXTENSION_GESDA` and `EXTENSION_REACH` from rv-android-core; remove local `EXTENSION_GATOR = ".gator"` (inconsistent with rv-android-core's `".wtg"`) and `EXTENSION_WTG = ".wtg"`; add `EXTENSION_STATIC_ANALYSIS` re-export. Also check `get_static_analysis_source_path()` (line 102) which constructs static analysis file paths using these extensions
- [ ] 7.6b Delete deprecated `parse_all()` from `static_analysis_parser.py` (line 152-167) — wraps the old 3-parser flow. Grep for callers first: known caller in `rv-agent-validation/experiment/runner.py`
- [ ] 7.6c Backup and delete `base_parser.py` entirely (P3). After removing GesdaParser, GatorParser, and ReachParser that inherit from `BaseStaticAnalysisParser`, the file becomes dead code — the new `StaticAnalysisParser` is standalone (uses `LoggingManager` directly, does not inherit from `BaseStaticAnalysisParser`). Includes deprecated `create_parser_factory()` (line 107-126) which also has no callers
- [ ] 7.7 Run `/rv-qa-lint-fix rv-static-analysis` — auto-fix formatting and imports after bulk changes

### 7.8 Dead code cleanup (P3)

Remove all superseded artifacts from rv-android. Backup to `backup/` before deleting.

- [ ] 7.8a Backup and delete `lib/gesda/` (superseded by analysis client — windows/widgets now extracted inside `RvsecAnalysisClient`)
- [ ] 7.8b Backup and delete `lib/reach/` (superseded by analysis client — reachability now computed inside `RvsecAnalysisClient`)
- [ ] 7.8c Delete `lib/gator/rvsec-gator-client.jar` (superseded by `lib/analysis-client/rvsec-analysis-client.jar`). Remove `/rvsec-gator-client.jar` from `lib/gator/.gitignore`
- [ ] 7.8d Delete `lib/gator/scripts/` (standalone dev scripts — `apk-guiAnalysis.sh`, `guiAnalysis.sh`, `guiAnalysisEx.sh`, `jimple.sh`, `extractClassNames.py`, `extractWidgetTypes.py`, `consts/` — never referenced by the `gator` launcher)
- [ ] 7.8e Comment out `rvsec-gesda` and `rvsec-reachability` in parent POM `$RVSEC_HOME/rvsec/rvsec-android/pom.xml` `<modules>` section (use XML comments `<!-- -->`). The modules remain in the repo but are no longer built. Commenting instead of removing preserves the ability to rebuild if needed
- [ ] 7.8f Backup and delete `RvsecWtgClient.java` from `rvsec-gator/client/src/` (superseded by `RvsecAnalysisClient`). Grep for references: `grep -r "RvsecWtgClient" $RVSEC_HOME/rvsec/rvsec-android/`
- [ ] 7.8g Grep for references to removed lib paths: `grep -r "lib/gesda\|lib/reach\|gesda_jar\|reach_jar\|rvsec-gesda\|rvsec-reach" modules/ rv-android/` — fix or remove any dangling references

### 7.9 rv-agent-validation migration (P3 — update ALL consumers)

The rv-agent-validation module has extensive references to the 3-file pattern in production code and tests. Per P3, all consumers must be updated — no adapters, no wrappers. The module assumes `.gesda`/`.wtg`/`.reach` throughout its pipeline.

**Production code:**

- [ ] 7.9a Update `modules/rv-agent-validation/src/rv_agent_validation/experiment/runner.py` (`load_static_data()`, ~L194-209): replace 3-path construction (`wtg_file`, `gesda_file`, `reach_file`) and `StaticAnalysisParser().parse(reach_file, gator_file, gesda_file, package)` with single `parse_file(json_path, package)`. Update existence check from 3 files to 1 JSON file
- [ ] 7.9b Update `modules/rv-agent-validation/src/rv_agent_validation/experiment/config.py` (`get_apps_with_static_analysis()`, ~L133-144): replace `glob("*.reach")`, `glob("*.wtg")`, `glob("*.gesda")` verification with `glob("*.json")`. Update dict keys from `reach_file`/`wtg_file`/`gesda_file` to `analysis_file`
- [ ] 7.9c Update `modules/rv-agent-validation/src/rv_agent_validation/preprocessing/instrumentation.py` (`_run_static_analysis()`, ~L338-416): replace 14+ references to 3-file pattern. Update output file paths from `.gesda`/`.wtg`/`.reach` to `.json`. Update skip-check logic, docstrings, and module-level comments. This is the largest change — the entire function assumes 3 output files
- [ ] 7.9d Update docstrings and comments in rv-agent-validation that document the 3-file architecture (module docstring in instrumentation.py lines ~25-26, function docstrings in runner.py and config.py)

**Tests:**

- [ ] 7.9e Update `modules/rv-agent-validation/tests/test_navigation_guidance.py` (~L29-38): replace `StaticAnalysisParser.parse(reach_file, gator_file, gesda_file, package)` with `parse_file(json_path, package)`
- [ ] 7.9f Update `modules/rv-agent-validation/tests/calibration/test_preprocess.py` (~L34-40, L106-162): update `_create_container_output()` helper to create `.json` instead of `.gesda`/`.wtg`/`.reach`. Update test assertions that verify existence of 3 files to verify 1 JSON file
- [ ] 7.9g Update `modules/rv-agent-validation/CLAUDE.md` — remove references to `.gesda`/`.wtg`/`.reach` file structure, document `.json` unified format

**Verification:**

- [ ] 7.9h Grep final: `grep -r "\.gesda\|\.wtg\|\.reach\|gesda_file\|gator_file\|reach_file\|GesdaParser\|ReachParser\|GatorParser" modules/rv-agent-validation/` — must return zero hits
- [ ] 7.9i Run rv-agent-validation tests: `uv run pytest modules/rv-agent-validation/tests/ -v` — all tests must pass

---

## 8. Tests

- [ ] 8.1 Create `tests/resources/cryptoapp.apk.json` test fixture from real analysis tool output
- [ ] 8.2 Create `test_static_analysis_parser.py`: well-formed JSON, empty JSON, missing sections, missing file, inner class normalization, code_package filtering, partial section failure, empty windows array, transitions referencing unknown window IDs (skip with warning), truncated JSON from timeout (valid sections parsed, missing sections return empty objects), empty MOP specs (all reachesMop = false)
- [ ] 8.3 Update `test_static_analysis_parser.py` for analysis flow
- [ ] 8.4 Update `test_static_analysis.py` (or `test_static_analyzer.py`) for single-tool pipeline
- [ ] 8.5 Update `test_config.py` for new configuration fields
- [ ] 8.6 Update `conftest.py` fixtures if needed
- [ ] 8.7 Create baseline equivalence test: compare analysis output counts (windows, transitions, methods, reachable, reachesMop, directlyReachesMop) against saved 3-tool baseline for `cryptoapp.apk`. Exact match for windows/transitions/methods/directlyReachesMop; ±10% tolerance for reachable/reachesMop

### 8.8 rv-agent test migration (P3 — update ALL consumers)

4 test files import `StaticAnalysisParser` and use the old 3-file API (`parse(reach_file, gator_file, gesda_file, package)`). Per P3, all consumers must be updated — no adapter wrappers.

- [ ] 8.8a Create `modules/rv-agent/tests/fixtures/static_analysis/cryptoapp/cryptoapp.apk.json` — unified JSON fixture generated from the existing `.reach`, `.wtg`, `.gesda` fixtures. Must contain all 3 sections (reachability, windows, transitions) with the same data
- [ ] 8.8b Update `modules/rv-agent/tests/unit/test_transition_manager.py`: change `static_data` fixture to use `StaticAnalysisParser.parse_file(json_path, package)` instead of `parse(reach_file, gator_file, gesda_file, package)`. Remove imports of old 3-file paths
- [ ] 8.8c Update `modules/rv-agent/tests/unit/test_navigation_guidance.py`: same change as 8.8b
- [ ] 8.8d Update `modules/rv-agent/tests/unit/test_rvagent_visitor.py`: same change as 8.8b
- [ ] 8.8e Update `modules/rv-agent/tests/online/test_static_analysis.py`: change file existence checks from `.reach`, `.wtg`, `.gesda` to `.json`. Update `StaticAnalysisLoader` usage if it references old extensions
- [ ] 8.8f Backup and delete old fixtures: `cryptoapp.apk.reach`, `cryptoapp.apk.wtg`, `cryptoapp.apk.gesda` from `tests/fixtures/static_analysis/cryptoapp/` (P3)
- [ ] 8.8g Run `/rv-test-run rv-agent` — all unit tests must pass

### 8.9 Final test runs

- [ ] 8.9a Run `/rv-test-run rv-static-analysis` — all tests must pass
- [ ] 8.9b Run `/rv-test-run rv-platform` — verify no breakage from extension change
- [ ] 8.9c Run `/rv-test-run rv-agent` — verify no breakage from fixture/parser migration

### 8.10 Normalization validation — Python side (D7)

Verify that `SignatureNormalizer` is a no-op on well-formed JSON (Java client already writes `$`), and that `code_package` filtering works correctly for multi-package APKs.

**SignatureNormalizer safety net tests:**

- [ ] 8.10a Create unit test `test_normalizer_is_noop_on_correct_json`: parse `cryptoapp.apk.json` test fixture through `StaticAnalysisParser.parse_file()`. Instrument or mock `SignatureNormalizer.normalize_class_name()` to count how many times it actually changes a value (input ≠ output). Assert count == 0 — the normalizer should be a no-op on correctly-generated JSON
- [ ] 8.10b Create unit test `test_normalizer_warns_on_change`: if `SignatureNormalizer` changes any class name during parsing, verify a WARNING is logged. This is the canary that detects Java client bugs — if the normalizer has to do real work, something is wrong at the source
- [ ] 8.10c Create unit test `test_normalizer_handles_legacy_dot_notation`: create a JSON fixture where class names intentionally use `.` for inner classes (simulating a buggy Java client). Verify the normalizer converts them to `$` correctly. This proves the safety net works even if the primary normalization in Java fails
- [ ] 8.10d Create unit test `test_inner_class_patterns`: verify normalization for all patterns encountered in `rvsec-regerar-resultados`:
  - `Outer$Inner` → `Outer$Inner` (already correct, no change)
  - `Outer$1` → `Outer$1` (anonymous inner, already correct)
  - `Outer$Inner$1` → `Outer$Inner$1` (nested + anonymous, already correct)
  - `Map.GameFieldPosition` → `Map$GameFieldPosition` (legacy edge case — normalizer converts)
  - `ZoomView.ZoomView` → `ZoomView.ZoomView` (Package.Class — normalizer should NOT convert, known limitation)

**code_package filtering tests (PackageDetector integration):**

- [ ] 8.10e Create unit test `test_code_package_filtering`: parse a JSON fixture containing classes from multiple packages (simulating multi-package APK like StarSlinger — `demo.*` + `exchange.*`). Pass `code_package="edu.cmu.cylab.starslinger.demo"`. Verify only classes matching the code_package are included in the result. Classes from `exchange.*` should be filtered OUT (they don't match the code_package prefix)
- [ ] 8.10f Create unit test `test_manifest_vs_code_package`: parse a JSON fixture simulating a Godot game engine APK — manifest package `ir.hsn6.trans`, but all classes in `org.godotengine.godot.*`. Pass `code_package="org.godotengine.godot"` (as `PackageDetector` would detect). Verify classes ARE included (matching code_package), not filtered out (as would happen with manifest package)
- [ ] 8.10g Verify `StaticAnalysisComponent` in rv-platform passes `app.code_package` (NOT `app.package_name`) to the parser. Grep: `grep -n "code_package\|package_name" modules/rv-platform/src/rv_platform/components/static_analysis.py` — confirm `code_package` is used for parser calls, `package_name` only for device operations

## 9. Documentation and Specs

- [ ] 9.1 Update `modules/rv-static-analysis/CLAUDE.md` — reflect analysis tool architecture
- [ ] 9.2 Update `modules/rv-android-core/CLAUDE.md` — add `EXTENSION_STATIC_ANALYSIS` to constants section
- [ ] 9.3 Run `/rv-verify rv-static-analysis` — tests + lint + type checks
- [ ] 9.4 Run `/rv-verify rv-platform` — tests + lint + type checks
- [ ] 9.5 Run `/rv-code-reviewer` — review full gh27 implementation against specs and design
- [ ] 9.6 (During `/opsx:sync`) Add end-to-end pipeline sequence diagram to `openspec/specs/analysis/spec.md` — covers the full flow from static analysis through execution to post-processing: StaticAnalyzer → analysis JSON → StaticAnalysisData → rv-agent execution → Coverage.aj → .logcat → CoverageTracker → ResultProcessor. This diagram documents unchanged components and belongs in the main spec, not the delta

## 10. E2E Validation (Final Gate)

Full rv-experiment run exercising the entire pipeline: pre-processing (instrumentation + static analysis) → execution (rv-agent + Coverage.aj logging) → post-processing (logcat parsing + coverage calculation). This is the final validation before closing gh27.

Comparison baseline: `docker/data/results/cli_experiment_20260219_095634_21537073/cryptoapp.apk/` (3-tool pipeline, 8 RVSEC-COV methods logged in 60s).

- [ ] 10.1 Run full experiment: `uv run rv-experiment run --tools rvagent:pure_algorithm --apks-dir ./apks_examples --specification-set jca --timeout 60 --name gh27_e2e_validation`
- [ ] 10.2 Verify analysis JSON created: `ls out/static/cryptoapp.apk.json` — file exists with all 3 sections (reachability, windows, transitions)
- [ ] 10.3 Verify coverage denominator > 0: check experiment log for `static_analysis_data` summary showing non-zero method count
- [ ] 10.4 Verify coverage > 0%: check `.logcat` file for `RVSEC-COV` lines — at least some methods should be logged during execution
- [ ] 10.5 Verify coverage calculation: check `*_results.json` for `method_coverage` and `mop_method_coverage` fields with non-zero values
- [ ] 10.6 Verify MOP detection: `grep "RVSEC" results/<id>/cryptoapp.apk/*.logcat` — MOP violations should appear if JCA APIs were exercised
- [ ] 10.7 Compare against baseline: coverage numbers should be comparable (±20%) to `cli_experiment_20260219` run. Document any differences
- [ ] 10.8 Verify timing improvement: `static_analysis_duration` should be less than previous 3-tool sum

### 10.9 Data Compatibility Verification (design.md "Data Compatibility Matrix")

Verify that the gh27 JSON (denominator) and runtime logcat (numerator) produce matching signatures. These checks run as part of the E2E validation using the experiment output from Task 10.1.

**M1 — Coverage signature format match (P1 vs P2):**

- [ ] 10.9a Extract a `RVSEC-COV` line from the `.logcat` file (e.g., `<com.example.Class: void method(int)>`). Find the same method in the JSON `reachable_methods` section. Verify character-for-character match including: `$` for inner classes, param types, return type, angle brackets
- [ ] 10.9b Verify inner class notation: if the APK has inner classes, confirm both the JSON and `RVSEC-COV` use `$` notation (e.g., `Outer$Inner`, not `Outer.Inner`)

**M2 — MOP flag consistency (P1 + P4):**

- [ ] 10.9c For a method that appears in a MOP spec (e.g., `MessageDigest.getInstance`), verify `directlyReachesMop = true` in the JSON for ALL overloads of that method. The MOP extractor matches by class+method only — all overloads must be flagged
- [ ] 10.9d If a `RVSEC-COV` line logs a method flagged `directlyReachesMop = true` in the JSON, confirm the method exists in a MOP spec (cross-reference with `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca/`)

**M3 — MOP error correlation (P3 vs P1):**

- [ ] 10.9e For each `RVSEC` error line in the logcat, extract class+method from the `ErrorSummary` comma-separated format (`spec,classQualifiedName,className,methodName,location,error`). Verify the class exists in the JSON's reachable classes. Note: this is approximate matching only — `StackTraceElement` format has no params/return type

### 10.10 APK-specific validation (design.md "Validation APK Candidates")

Validate the gh27 pipeline against APKs with known normalization and package detection problems from the legacy analysis (`rvsec-regerar-resultados/docs/NOVO/`). APK source: `/home/pedro/desenvolvimento/RV_ANDROID/NOVO/APKS/`.

**Inner class normalization:**

- [ ] 10.10a Run analysis on `org.secuso.privacyfriendlyludo_5.apk`. Check JSON output for inner class `Map$GameFieldPosition` (must use `$`, not `.`). If the normalizer logs any WARNING about changing class names, investigate — it means the Java client wrote `.` instead of `$`
- [ ] 10.10b Run analysis on `com.hwloc.lstopo_271.apk`. Document the `ZoomView.ZoomView` behavior — this is a KNOWN LIMITATION where the normalizer cannot distinguish `Package.Class` from `Outer.Inner`. Verify the pipeline does not crash. Record how many methods have mismatched signatures between JSON and RVSEC-COV logcat

**Package mismatch (PackageDetector integration):**

- [ ] 10.10c Run analysis on `ir.hsn6.trans_4.apk` (Godot engine). Verify: (1) `PackageDetector` returns `org.godotengine.godot` as code_package, NOT `ir.hsn6.trans`; (2) JSON contains classes from `org.godotengine.godot.*`; (3) filtering by `ir.hsn6.trans` would yield 0 methods (confirming why code_package is essential)
- [ ] 10.10d Run analysis on `org.fox.tttrss_535.apk` (typo mismatch). Verify: (1) `PackageDetector` returns `org.fox.ttrss` (2 t's), NOT `org.fox.tttrss` (3 t's from manifest); (2) JSON contains classes from `org.fox.ttrss.*`
- [ ] 10.10e Run analysis on `edu.cmu.cylab.starslinger.demo_17301504.apk` (multi-package). Verify: JSON contains classes from both `edu.cmu.cylab.starslinger.demo.*` AND `edu.cmu.cylab.starslinger.exchange.*` — both should pass the code_package prefix filter

**Rebranding:**

- [ ] 10.10f Run analysis on `com.easytarget.micopi_32.apk`. Verify `PackageDetector` detects `org.eztarget.micopi` as code_package (not `com.easytarget.micopi` from manifest). JSON must contain `org.eztarget.*` classes

**Batch validation (5 diverse APKs):**

- [ ] 10.10g Run full `rv-experiment` pipeline on 5 APKs that stress different edge cases: `cryptoapp.apk` (MOP violations), `org.secuso.privacyfriendlyludo_5.apk` (inner class), `ir.hsn6.trans_4.apk` (Godot package mismatch), `org.fox.tttrss_535.apk` (typo package mismatch), `edu.cmu.cylab.starslinger.demo_17301504.apk` (multi-package). For each: verify JSON created, coverage denominator > 0, no crashes, timing < 3-tool sum
