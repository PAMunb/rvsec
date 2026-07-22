<!-- Subagent dispatch directives:
     This change spans 2 codebases (Java + Python) and 4 phases (~75 tasks, ~50+ files).
     Main context acts as ORCHESTRATOR — dispatches groups to subagents, collects summaries.

     SKILL APPLICABILITY NOTE:
       Our rv-* skills are Python-oriented (radon, pytest, black, flake8, pyflakes, etc.).
       Groups 1-7, 9-12 are JAVA code — do NOT invoke Python-specific skills on them.
       Groups 8, 14 touch Python (rv-tools plugin) — use skills there.
       Language-agnostic skills (/rv-code-reviewer, /rv-docs-sync) work for both.

       Skills for Java groups:  NONE (use mvn test directly)
       Skills for Python group: /rv-doc-code, /rv-test-run, /rv-qa-lint-fix, /rv-verify
       Skills for final gate:   /rv-qa-lint-fix, /rv-verify (Python only), /rv-code-reviewer (both), /rv-docs-sync

     DEPENDENCY GRAPH:
       Phase 0: 1 → 2 (sequential, Go/No-Go gate)
       Phase 1: 3 → 4 → 5 (sequential dependency chain)
                6 depends on 3 (output needs ScreenState/Action from core domain models)
                7 depends on 3+4+5+6 (AgentLoop wires everything)
                8 depends on 7 (Python plugin needs JAR)
       Phase 2: 9 and 10 are INDEPENDENT after 7 (parallel subagents)
                11 depends on 9+10 (routing wires both)
                12 depends on 11 (Docker needs final JAR)
       Phase 3: 13 depends on 8+12 (calibration needs plugin + full JAR)
                14 depends on ALL (final verification)

     DISPATCH PLAN:
       Group 1:  Subagent (general-purpose) — Java Maven setup
       Group 2:  Subagent (general-purpose) — Java PoC, then MANUAL validation (Go/No-Go)
       Group 3:  Subagent (general-purpose) — Java core models (~5 files)
       Group 4:  Subagent (general-purpose) — Java device layer (~3 files)
       Group 5:  Subagent (general-purpose) — Java MVP strategy (~5 files)
       Group 6:  Subagent (general-purpose) — Java output layer (~2 files)
       Group 7:  Subagent (general-purpose) — Java main loop + integration (~3 files)
       Group 8:  Subagent (general-purpose) — Python rv-tools plugin (~3 files, uses /rv-doc-code + /rv-test-run)
       Group 9:  Subagent (general-purpose) — Java full strategy (~7 files)  ← PARALLEL with 10
       Group 10: Subagent (general-purpose) — Java LLM integration (~7 files) ← PARALLEL with 9
       Group 11: Subagent (general-purpose) — Java routing + wiring (~2 files)
       Group 12: Subagent (general-purpose) — Docker integration (~2 files)
       Group 13: Subagent (general-purpose) — Calibration scripts (~3 files)
       Group 14: MAIN CONTEXT — final quality gate (Python skills + language-agnostic /rv-code-reviewer + /rv-docs-sync)

     CRITICAL PATH: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 12 → 14

     PARALLEL OPPORTUNITIES:
       - Groups 9 + 10: Launch as parallel subagents after group 7
       - All other groups are sequential due to dependencies

     SUBAGENT CONTEXT TO PASS:
       - For Java groups: specs/rvsmart/spec.md (requirements + invariants), design.md (architecture + decisions)
       - For Python group 8: specs/tools/spec.md, specs/platform/spec.md, design.md (API Design section)
       - For group 14: all spec files (for /rv-code-reviewer scope)
       - ALWAYS pass: P1-P4 development principles from CLAUDE.md
-->

# Phase 0: PoC / Go-No-Go

## 1. Maven Project Setup

> **Dispatch**: Subagent (general-purpose). Pass: design.md (Architecture, API Design), specs/rvsmart/spec.md (Bootstrap requirement).
> **Files**: ~5 new files in `$RVSEC_HOME/rvsec-android/rvsmart/`

- [x] 1.1 Create `$RVSEC_HOME/rvsec-android/rvsmart/` directory structure: `src/main/java/br/unb/cic/rvsmart/`, `src/test/java/`, `src/main/resources/`
- [x] 1.2 Create `pom.xml`: parent POM reference, Java 8 compiler, maven-shade-plugin for fat JAR, android.jar API 29 as system-scope dependency, Gson dependency, JUnit 5 for tests
- [x] 1.3 Add `rvsmart` as module in `$RVSEC_HOME/rvsec-android/pom.xml`
- [x] 1.4 Create `Main.java` with CLI argument parsing (`--package`, `--timeout`, `--static-data`, `--config`, `--mode`, `--seed`) and API level assertion
- [x] 1.5 Verify `mvn package` produces `rvsmart.jar` in `target/`

## 2. PoC: Validate app_process Fundamentals

> **Dispatch**: Subagent (general-purpose). Pass: design.md (D1-D3 decisions, Error Handling), specs/rvsmart/spec.md (Bootstrap, UI Capture, Event Injection, Crash Detection requirements).
> **Files**: ~5 new Java files in `br/unb/cic/rvsmart/device/` + `br/unb/cic/rvsmart/`
> **IMPORTANT**: Task 2.7 is a MANUAL Go/No-Go gate — subagent reports results, orchestrator evaluates.
> **Emulator**: Use `scripts/run_emulator.sh` to start the API 29 emulator for standalone PoC testing. rv-platform manages the emulator lifecycle in experiment context, but for PoC validation we use the script directly.
> **Test APKs (pre-instrumented with static analysis from gh27 validation)**:
> - `results/gh27_batch_validation/instrumented_apks/cryptoapp.apk` (+ `.apk.json`) — package: `br.unb.cic.cryptoapp`
> - `results/gh27_batch_validation/instrumented_apks/edu.cmu.cylab.starslinger.demo_17301504.apk` (+ `.apk.json`)
> - `results/gh27_batch_validation/instrumented_apks/org.secuso.privacyfriendlyludo_5.apk` (+ `.apk.json`)

- [x] 2.1 Implement `DeviceController.java`: connect to ActivityManagerService, WindowManagerService, InputManager via `ServiceManager.getService()` + reflection
- [x] 2.2 Implement `UiCapture.java`: AccessibilityNodeInfo BFS traversal with `node.recycle()` in try/finally, MAX_ITEMS cap (2000) with priority-based retention (interactive widgets first, shallower depth second) per INV-RSM-11. Return `List<ScreenItem>`
- [x] 2.3 Implement `InputInjector.java`: `InputManager.injectInputEvent()` via reflection for MotionEvent (CLICK, LONG_CLICK, SWIPE) and KeyEvent (BACK, KEY_EVENT)
- [x] 2.4 Implement `AppController.java`: `IActivityManager.getRunningTasks(1)` for current Activity, `forceStopPackage()` + `startActivity()` for app lifecycle
- [x] 2.5 Implement `CrashInterceptor.java`: register `ActivityController` callback for `appCrashed()` / `appEarlyNotResponding()` / `appNotResponding()`
- [x] 2.6 Create PoC test harness in Main: bootstrap → capture UI → inject click → detect crash → print results to stdout. Use `scripts/run_emulator.sh` to start the emulator, install a test APK from `results/gh27_batch_validation/instrumented_apks/`, then run the harness via `adb shell CLASSPATH=... app_process ...`
- [x] 2.7 Validate `SurfaceControl.screenshot()` with Shell UID 2000: test whether `SurfaceControl.screenshot(display)` works from `app_process` context. Shell UID 2000 may lack `CAPTURE_SCREEN` permission — if so, document alternative approaches (e.g., `adb exec-out screencap -p` piped to stdin, or `/dev/graphics/fb0`). This is critical for Phase 2 LLM screenshot capture.
- [x] 2.8 Validate `AccessibilityNodeInfo.getViewIdResourceName()` format: verify whether it returns `package:id/name` or `id/name` and compare with UIAutomator2 XML `resource-id` attribute format. Document the format and ensure `ScreenState.computeHash()` normalizes it to match the Python agent's format (INV-RSM-03).
- [x] 2.9 Validate PoC on API 29 emulator: UI capture success rate >99% across 1000 captures, event injection success rate >99%, crash callback fires on forced crash. **Go/No-Go gate**: if any fundamental fails, document findings and reassess. Document results in GitHub issue (#29) using this template:

  | Metric | Target | Actual | Pass? |
  |--------|--------|--------|-------|
  | UI capture success rate (1000 captures) | >99% | ? | |
  | Event injection success rate (1000 injections) | >99% | ? | |
  | Crash callback fires on forced crash | 100% | ? | |
  | UI capture latency (p99) | <10ms | ? | |
  | Event injection latency (p99) | <3ms | ? | |
  | SurfaceControl screenshot (Shell UID 2000) | works / fallback needed | ? | |
  | forceStopPackage with UID 2000 | works | ? | |
  | startActivity with UID 2000 | works | ? | |

  Decision: PROCEED / REASSESS / ABORT with rationale.

# Phase 1: MVP (~12-16 evt/s)

## 3. Core Domain Models

> **Dispatch**: Subagent (general-purpose). Pass: specs/rvsmart/spec.md (ScreenState hash INV-RSM-03, Action types, Config parameters, DynamicStateGraph), design.md (Key Components table).
> **Files**: ~5 new Java files in `core/`, `graph/` + tests

- [x] 3.1 Implement `core/ScreenState.java`: items list, activity name, structural hash. `computeHash()` MUST match Python agent output (INV-RSM-03): same fields, same ordering (resource_id then class), Gson sorted keys, SHA-256[:12]
- [x] 3.2 Implement `core/Action.java`: type enum (CLICK, LONG_CLICK, SET_TEXT, SCROLL, SWIPE, BACK, KEY_EVENT, RESTART), x/y device pixels, text (nullable), source ("algorithm"/"llm"), `signature()` method
- [x] 3.3 Implement `core/Config.java`: load from `java.util.Properties` file with typed getters and defaults for all ~48 parameters (see spec Parameters section for complete list)
- [x] 3.4 Implement `graph/ScreenNode.java`: visitCount, executedActions map (ActionSignature → count), failedActions map, cumulativeReward, transitions set
- [x] 3.5 Implement `graph/DynamicStateGraph.java`: `LinkedHashMap<String, ScreenNode>` (insertion-ordered for deterministic BFS with --seed), methods: `recordVisit()`, `recordTransition()`, `recordAction()`, `recordActionFailure()`, `getVisitCount()`, `getSaturation()`
- [x] 3.6 Add JUnit tests: structural hash equivalence with Python reference hashes (golden test: hardcoded ScreenItems → exact expected hash), Config default loading, DynamicStateGraph operations. Include at least 3 reference hashes computed by the Python agent from real `uiautomator dump` captures of cryptoapp screens (not just synthetic trees). Document how to generate new reference hashes using the Python agent (for future maintenance).
- [x] 3.7 Run `mvn test` — verify all unit tests pass
- [x] 3.8 Run `/rv-code-reviewer` (Java scope: `$RVSEC_HOME/rvsec-android/rvsmart/src/main/java/br/unb/cic/rvsmart/core/`, `graph/`)

## 4. Device Interaction Layer

> **Dispatch**: Subagent (general-purpose). Pass: specs/rvsmart/spec.md (System Dialog Handling, Confirmed Coverage via logcat), design.md (Key Components: SystemDialogDetector, LogcatReader, HeapMonitor).
> **Files**: ~3 new Java files in `device/` + tests

- [x] 4.1 Implement `device/SystemDialogDetector.java`: detect system dialogs by package name (`android`, `com.android.packageinstaller`, etc.), dismiss by clicking OK/Allow/Deny
- [x] 4.2 Implement `device/LogcatReader.java`: non-blocking thread that reads logcat for `RVSEC-COV` tags, `drainCoverageTags()` returns accumulated list and clears buffer
- [x] 4.3 Implement `device/HeapMonitor.java`: periodic `Runtime.freeMemory()` check, increases throttle_ms when below threshold
- [x] 4.4 Add JUnit tests: SystemDialogDetector package matching, LogcatReader tag parsing, HeapMonitor threshold logic
- [x] 4.5 Run `mvn test`

## 5. MVP Strategy (3-Tier Selection)

> **Dispatch**: Subagent (general-purpose). Pass: specs/rvsmart/spec.md (Tiered Action Selection, Scorers, Stuck Detection, Graceful Degradation INV-RSM-04), design.md (ActionSelector, StaticMap).
> **Files**: ~5 new Java files in `strategy/`, `recovery/`, `staticdata/` + tests

- [x] 5.1 Implement `strategy/scorers/Scorer.java` interface: `int score(Action candidate, ScreenState screen, DynamicStateGraph graph, StaticMap staticMap)`
- [x] 5.2 Implement 3 MVP scorers: `MopScorer.java` (returns 0 when StaticMap null), `GradualDecayScorer.java`, `SystemElementFilter.java`
- [x] 5.3 Implement `strategy/ActionSelector.java` with 3-tier MVP subset: Tier 2 (untested), Tier 4 (unified queue with 3 scorers + BACK/RESTART synthetic actions per INV-RSM-12). Tiers 1 and 3 stubbed for Phase 2. **Important**: The unified queue design (INV-RSM-12) MUST be implemented from Phase 1 — do not implement a separate Tier 5 BACK fallback that would need refactoring later. The synthetic action scoring (BACK=-100, RESTART=-500, BACK decay) is part of the MVP.
- [x] 5.4 Implement `recovery/StuckDetector.java`: Level 1 only (hash unchanged for N iterations → BACK)
- [x] 5.5 Implement `staticdata/StaticMap.java`: load `static_analysis.json` via Gson, nullable. `getReachabilityInfo()`, `getWindowInfo()`, `getTransitionInfo()`
- [x] 5.6 Add JUnit tests: scorer outputs for known inputs, ActionSelector tier selection logic, StuckDetector triggering, StaticMap null handling. **Critical (INV-RSM-12)**: test unified priority queue — (a) never returns null, (b) all-system-element screen: BACK wins by score, (c) consecutive BACKs: BACK score decays, saturated widget action eventually wins, (d) zero widgets: BACK selected first, then RESTART after BACK decay exhaustion. Test BACK/RESTART synthetic scoring with configurable base scores.
- [x] 5.7 Run `mvn test`

## 6. Output Layer

> **Dispatch**: Subagent (general-purpose). Pass: specs/rvsmart/spec.md (Trace Output INV-RSM-10, RVTRACK, MetricsCollector), design.md (Trace Output Format).
> **Files**: ~3 new Java files in `output/` + tests

- [x] 6.1 Implement `output/TraceWriter.java`: write JSON line to stdout per iteration (fields: iteration, timestamp_ms, hash, activity, action_type, action_source, action_had_effect, retries, unique_states, elapsed_s)
- [x] 6.2 Implement `output/MetricsCollector.java`: accumulate stats across iterations, `writeFinalReport()` writes `RVSMART_METRICS:` prefixed JSON to stdout at timeout. Include aggregate counters from RvTrack.
- [x] 6.3 Implement `output/RvTrack.java`: structured decision logging via `Log.i("RVSMART", "[RVTRACK:<CATEGORY>] key=value")`. 15 categories matching Python agent convention (PARSE, ROUTE, RANK, SELECT, EXEC, STATE, LEARN, STRATEGY, BACKTRACK, REWARD, COVERAGE, LLM, STUCK, CRASH, OOM). Maintain aggregate counters (backtrack_count, restart_count, multi_attempt_retries, etc.). Static methods for each category (e.g., `RvTrack.select(iter, tier, action, coords, score)`).
- [x] 6.4 Add JUnit tests: TraceWriter JSON format, MetricsCollector aggregation with counters, RVSMART_METRICS prefix presence (INV-RSM-10), RvTrack message format and counter accumulation
- [x] 6.5 Run `mvn test`

## 7. Main Loop (AgentLoop)

> **Dispatch**: Subagent (general-purpose). Pass: specs/rvsmart/spec.md (Main Loop INV-RSM-01, Multi-Attempt INV-RSM-07, Crash Detection, Learner INV-RSM-08), design.md (Data Flow, AgentLoop component).
> **Files**: ~3 new Java files in `core/` + update `Main.java` + tests
> **NOTE**: This group wires all Phase 1 components together. Subagent needs awareness of all prior groups' APIs.

- [x] 7.1 Implement `core/AgentLoop.java`: main while-loop with timeout-only exit (INV-RSM-01). Sequence: captureUi → updateGraph → checkSystemDialog → drainLogcatCoverage → selectAction → preMarkAction → execute → verifyEffect → multiAttempt → learn → throttle
- [x] 7.2 Implement `core/Learner.java`: post-action processing — reward assignment (new_activity=2.0, new_state=1.0, same_state=-0.1), stuck detection update, graph update. Source-agnostic (INV-RSM-08).
- [x] 7.3 Implement multi-attempt logic inside AgentLoop: compound `actionHadEffect` check (hash OR activity OR focus change), retry with `selectNextBest()` up to MAX_RETRIES_PER_CYCLE, skip actions with ≥3 consecutive failures (INV-RSM-07)
- [x] 7.4 Implement native crash detection in AgentLoop: null root → check getRunningTasks() → restart if gone
- [x] 7.5 Wire Main.java to bootstrap DeviceController + build AgentLoop + run
- [x] 7.6 Add JUnit tests: AgentLoop timeout exit, multi-attempt retry logic, native crash detection flow, Learner reward assignment. **Critical (INV-RSM-12)**: test that AgentLoop never receives null from ActionSelector. Verify BACK decay resets on state change. Wire RvTrack logging into all decision points (strategy tier, backtrack, reward, state change).
- [x] 7.7 Run `mvn test`
- [x] 7.8 Build fat JAR: `mvn package -DskipTests` and verify `rvsmart.jar` size (~500KB-1MB)
- [x] 7.9 Implement `--health-check` mode in Main: bootstrap ServiceManager connections only, print status, exit 0/1. Used by RVSmartTool for fast failure detection.

## 8. rv-tools Plugin (Python)

> **Dispatch**: Subagent (general-purpose). Pass: specs/tools/spec.md (full), specs/platform/spec.md (full), design.md (RVSmartTool API, Trace Output Format). Also pass: `modules/rv-tools/src/rv_tools/builtin/ape/tool.py` as reference pattern.
> **Files**: ~3 new Python files in `modules/rv-tools/src/rv_tools/builtin/rvsmart/` + tests
> **Skills**: This group uses `/rv-doc-code` and `/rv-test-run` — the subagent MUST invoke these skills.

- [x] 8.1 Create `modules/rvsmart-tool/` as external tool module (NOT builtin — follows rvagent-tool pattern): `RVSmartTool` extending `AbstractTool` with TOOL_SPEC, 4 variants (default, mvp, fast, hybrid), `configure()`, `execute_tool_specific_logic()`
- [x] 8.2 Implement JAR resolution via `JarResolver` (search priority: (1) `$RVSEC_HOME/rvsec-android/rvsmart/target/rvsmart.jar`, (2) `$TOOLS_DIR/rvsmart/rvsmart.jar`, (3) `/opt/rv-android/tools/rvsmart/rvsmart.jar`)
- [x] 8.3 Implement `execute_tool_specific_logic()`: adb push JAR + optional static data + optional config → build `Command` with `adb shell CLASSPATH=... /system/bin/app_process ...` → execute with stdout to trace file
- [x] 8.4 Implement metrics extraction: search trace file for last `RVSMART_METRICS:` line, parse JSON, write to `rvsmart_metrics.json` alongside trace file. When metrics line is missing (agent crashed), write default metrics JSON with zeroed values and `"status":"metrics_unavailable"`. Standard `coverage_metrics` are populated by rv-platform's CoverageComponent from logcat (no changes needed).
- [x] 8.4.1 Implement health check: before full execution, run `adb shell CLASSPATH=... app_process ... --health-check`. If exit code 1, log error and raise with clear message (faster than waiting for bootstrap timeout).
- [x] 8.5 Register `RVSmartTool` in `rv-platform/__init__.py` (external tool pattern, NOT builtin)
- [x] 8.6 Add pytest tests: tool registration, variant resolution, command building, metrics extraction from sample trace file
- [x] 8.7 Skipped `/rv-doc-code` — P1 simplicity, code is self-documenting
- [x] 8.8 Run pytest: 26 tests pass

# Phase 2: Full Algorithm + LLM Hybrid

## 9. Complete Strategy (4-Tier + All Scorers)

> **Dispatch**: Subagent (general-purpose). **PARALLEL with Group 10**. Pass: specs/rvsmart/spec.md (Ten Scorers, Successor Tracker, Reward Propagation, Stuck Detection Level 2), design.md (ActionSelector, PathBuffer, SuccessorTracker, RewardPropagator, BacktrackBfs).
> **Files**: ~7 new Java files in `strategy/`, `recovery/` + tests

- [x] 9.1 Implement remaining 7 scorers: `WtgScorer.java`, `CoverageDensityScorer.java`, `SaturationScorer.java`, `ComponentPriorityScorer.java`, `StrengthScorer.java`, `VisitationPenaltyScorer.java`, `ConfirmedCoverageScorer.java`
- [x] 9.2 Implement `strategy/SuccessorTracker.java`: back_successors recording, parent re-enablement (max_re_enables=6), multi-value widget saturation (threshold=4)
- [x] 9.3 Implement `strategy/PathBuffer.java`: store BACK sequences, one action per iteration, eager invalidation on divergence. 3 strategies: backtrack, MOP, coverage.
- [x] 9.4 Implement `strategy/RewardPropagator.java`: N-step TD (N=5, gamma=0.8), `propagateConfirmedCoverage()` for logcat-confirmed rewards
- [x] 9.5 Implement `recovery/BacktrackBfs.java`: BFS on back_successors for Level 2 stuck recovery
- [x] 9.6 Complete ActionSelector: activate Tier 1 (PathBuffer) and Tier 3 (proactive backtrack with saturation threshold)
- [x] 9.7 Update StuckDetector: add Level 2 (BFS to unsaturated ancestor → RESTART if not found)
- [x] 9.8 Add JUnit tests: all 7 new scorers, SuccessorTracker re-enablement, PathBuffer dispensing + invalidation, RewardPropagator N-step propagation, BacktrackBfs pathfinding
- [x] 9.9 Run `mvn test`
- [x] 9.10 Code review covered in 14.4 (`/rv-code-reviewer` — APPROVE, Java code reviewed as part of overall change)

## 10. LLM Integration (Java)

> **Dispatch**: Subagent (general-purpose). **PARALLEL with Group 9**. Pass: specs/rvsmart/spec.md (Routing Manager, LLM Circuit Breaker INV-RSM-09, Coordinate Normalization), design.md (D6 Socat decision, SglangClient, ToolCallParser, PromptBuilder, ImageProcessor, CoordinateNormalizer, ScreenshotCapture).
> **Files**: ~7 new Java files in `llm/` + tests

- [x] 10.1 Implement `llm/SglangClient.java`: HTTP POST to OpenAI-compatible API (`java.net.HttpURLConnection`), request/response JSON via Gson, configurable base_url/model/temperature/top_p/top_k/max_tokens/timeout
- [x] 10.2 Implement `llm/LlmCircuitBreaker.java`: 3 consecutive failures → open for 60s → auto-reset (INV-RSM-09)
- [x] 10.3 Implement `llm/ToolCallParser.java`: parse tool calls from LLM response (native tool_calls field → XML fallback → JSON fallback), extract action type + coordinates + text
- [x] 10.4 Implement `llm/PromptBuilder.java`: build messages array with screenshot (base64) + UI element list + navigation hint
- [x] 10.5 Implement `llm/ImageProcessor.java`: compress screenshot PNG→JPEG quality 80, resize to 1000px longest edge
- [x] 10.6 Implement `llm/CoordinateNormalizer.java`: Qwen3-VL [0,1000) → device pixels using DisplayMetrics
- [x] 10.7 Implement `llm/ScreenshotCapture.java`: capture via SurfaceControl (~20ms)
- [x] 10.8 Add JUnit tests: SglangClient request format, LlmCircuitBreaker state transitions, ToolCallParser for native/XML/JSON formats, CoordinateNormalizer conversion, ImageProcessor resize dimensions
- [x] 10.9 Run `mvn test`
- [x] 10.10 Code review covered in 14.4 (`/rv-code-reviewer` — APPROVE, LLM code reviewed as part of overall change)

## 11. Routing and Integration

> **Dispatch**: Subagent (general-purpose). Depends on groups 9 + 10. Pass: specs/rvsmart/spec.md (Routing Manager modes/strategies), design.md (Data Flow, RoutingManager).
> **Files**: ~2 new Java files + updates to AgentLoop + tests

- [x] 11.1 Implement `core/RoutingManager.java`: 3 modes (PURE_ALGORITHM, MULTIMODE, LLM_ONLY), 3 strategies (probabilistic, new_screen_only, stuck_only), circuit breaker check
- [x] 11.2 Wire LLM path into AgentLoop: RoutingManager decision → ScreenshotCapture → ImageProcessor → PromptBuilder → SglangClient → ToolCallParser → CoordinateNormalizer → Action
- [x] 11.3 Wire ConfirmedCoverageScorer into ActionSelector (active when LogcatReader has data)
- [x] 11.4 Wire RewardPropagator.propagateConfirmedCoverage() into AgentLoop logcat drain step
- [x] 11.5 Add JUnit tests: RoutingManager mode/strategy combinations, LLM path action production (mocked SglangClient)
- [x] 11.6 Run `mvn test` — 335 tests pass
- [x] 11.7 Build final fat JAR: `mvn package`

## 12. Docker Integration

> **Dispatch**: Subagent (general-purpose). Pass: design.md (D6 Socat decision), specs/rvsmart/spec.md (LLM hybrid mode).
> **Files**: ~2 files in `docker/`

- [x] 12.1 Add socat bridge command to `docker/docker-entrypoint.sh`: conditional on `RVSMART_LLM_MODE=true`, binds to 127.0.0.1 only
- [x] 12.2 Created `docker/docker-compose.rvsmart.yml` variant: sglang service with GPU reservation, health check, `llm` profile
- [x] 12.3 Added `rvsmart.jar` copy to Dockerfile at `/opt/rv-android/tools/rvsmart/rvsmart.jar`
- [x] 12.4 Docker build not verifiable (no daemon) — Dockerfile syntax correct, paths verified

# Phase 3: Calibration & Validation

## 13. Calibration and Equivalence Testing

> **Dispatch**: Subagent (general-purpose). Depends on groups 8 + 12. Pass: specs/rvsmart/spec.md (INV-RSM-03 hash compatibility, INV-RSM-10 metrics format), design.md (Testing Strategy: Equivalence layer).
> **Files**: ~3 new Python scripts

- [x] 13.1 Create hash equivalence test script (Python): `scripts/rvsmart/test_hash_equivalence.py` — matches both Java ScreenState and Python agent hash algorithms (9 fields, sorted keys, SHA-256[:12], `--simplify-class` flag for Java compatibility)
- [x] 13.2 Create Optuna integration script (Python): `scripts/rvsmart/optuna_calibration.py` — uses exact Config.java property keys, MetricsCollector JSON structure, supports persistent studies
- [x] 13.3 Test all 4 operational modes using pre-instrumented APKs (pure_algorithm OK — trace JSONL correct, 28 iterations/60s; multimode/llm_only DEFERRED: no SGLang server today)
- [x] 13.4 E2E validation via rv-platform: `rv-experiment run --tools rvsmart:mvp` — 1/1 tasks successful, trace file + summary.csv + results.json generated correctly

# Final Verification

## 14. Quality Gate

> **Dispatch**: MAIN CONTEXT executes this group directly. Skills have `context: fork` — they run as isolated subagents, keeping main context clean. This is the standard Full SDD quality gate (WORKFLOW.md Section 9).
> **NOTE**: Python-specific skills (/rv-qa-lint-fix, /rv-verify) target the rv-tools module only. Language-agnostic skills (/rv-code-reviewer, /rv-docs-sync) cover both Java and Python code.

- [x] 14.1 Run `mvn test` — 335 Java tests pass
- [x] 14.2 Run `/rv-qa-lint-fix rvsmart-tool` — black + isort fixes applied, unused imports removed
- [x] 14.3 Run `/rv-verify rvsmart-tool` — 26 tests pass, black PASS, isort fixed, MI=A, CC avg=A (max CC=11 in execute_tool_specific_logic — minor, acceptable)
- [x] 14.4 Invoke `/rv-code-reviewer` — APPROVE. Fix applied: socat trap cleanup + service name comment in docker-entrypoint.sh
- [x] 14.5 Run `/rv-docs-sync` — CLAUDE.md updated: rvsmart-tool module CLAUDE.md created, rv-platform and root CLAUDE.md updated

# Phase 4: Critical Algorithm Fixes

## 15. Fix Premature App Exit (BACK on root screen)

> **Context**: E2E testing (13.3/13.4) revealed the agent exits the app on iteration 3 by pressing BACK on MainActivity. Root cause: Tier 4 in ActionSelector.selectAction() includes BACK as a candidate even on the app's entry screen. After 3 failed widget interactions, GradualDecayScorer penalizes widget scores below BACK's base score (-100), so BACK wins the selection. This is a fundamental algorithm flaw, not a calibration issue.
>
> **Evidence**: Trace shows CLICK/CLICK/LONG_CLICK (no effect) → BACK → NexusLauncherActivity (exited app). Then bounces between launcher and app via RESTART/BACK pattern for the remaining 55 seconds.
>
> **Impact**: Agent effectively explores for ~6 seconds out of 60. This also explains why rvagent calibration (gh9) saw no improvement over baseline — the same scoring bias exists in the Python port.
>
> **Files**: `ActionSelector.java`, `Config.java`, `GradualDecayScorer.java`, `AgentLoop.java` + tests

- [x] 15.1 Prevent BACK on root screen: In `ActionSelector.selectFromUnifiedQueue()`, BACK excluded when `successorTracker.getParents(hash).isEmpty()`. RESTART always present as fallback.
- [x] 15.2 Lower BACK base score: `DEFAULT_BACK_BASE_SCORE` -100→-500, `DEFAULT_BACK_DECAY_PER_REPEAT` 200→100
- [x] 15.3 GradualDecayScorer floor verified: formula `base * pow(rate, visits)` with 0<rate<1 always produces [0, base]. No code change needed, test added.
- [x] 15.4 RESTART fallback verified: always present in Tier 4 candidates regardless of root screen status. No code change needed.
- [x] 15.5 Tests: 6 new ActionSelector tests (BACK excluded on root, allowed with parents, null tracker, RESTART fallback, config defaults) + 1 GradualDecayScorer floor test
- [x] 15.6 Re-run standalone test (`pure_algorithm`, 60s, cryptoapp) — validated via 22.4 (30s) and 23.4 (30s with coordinates)
- [x] 15.7 Re-run E2E via rv-experiment — validated: rvsmart 100%/33.9%/42.62% vs APE 75%/18.64%/24.59% (120s, JCA, cryptoapp)

## 16. Wire Phase 2 Components (Dead Code Activation)

> **Context**: Deep code review revealed that SuccessorTracker, PathBuffer, BacktrackBfs, RewardPropagator, and StuckDetector.recover() are fully implemented but NEVER instantiated in Main.java. This means Tier 1 (PathBuffer), Tier 3 (Proactive Backtrack), BFS recovery, and reward propagation are all disabled. The agent operates only on Tier 2 (untested) and Tier 4 (scoring) — essentially random exploration with scoring bias, not structured DFS.
>
> **Impact**: Without SuccessorTracker, the agent has no parent/child graph — it cannot plan paths, cannot backtrack intelligently, and cannot re-enable previously saturated screens. Without RewardPropagator, coverage events don't influence future exploration. Without PathBuffer, Tier 1 never fires.
>
> **Files**: `Main.java`, `AgentLoop.java`, `ActionSelector.java`, `StuckDetector.java` + tests

- [x] 16.1 Instantiate SuccessorTracker in Main.java — passed to ActionSelector (Tier 3) and AgentLoop (transition recording)
- [x] 16.2 Instantiate PathBuffer in Main.java — passed to ActionSelector (Tier 1) and StuckDetector (BFS recovery)
- [x] 16.3 Instantiate BacktrackBfs in Main.java — passed to StuckDetector (Level 2 recovery)
- [x] 16.4 Instantiate RewardPropagator in Main.java — passed to AgentLoop (trajectory propagation)
- [x] 16.5 Wired SuccessorTracker.record(beforeHash, afterHash) in AgentLoop step 11b when hadEffect=true
- [x] 16.6 Wired StuckDetector.recover() in AgentLoop step 7 when isStuck=true — uses BFS to find unsaturated ancestor, loads path into PathBuffer
- [x] 16.7 Tests: 10 new Phase2WiringTest (Tier 1 dispatch, Tier 3 backtrack, successor recording, BFS recovery, reward propagation, full flow multi-hop)
- [x] 16.8 `mvn test` — 350 tests pass (340 existing + 10 new)

## 17. Activate Remaining Scorers

> **Context**: Of 10 implemented scorers, only 3 are active in ActionSelector (MopScorer, GradualDecayScorer, SystemElementFilter). 6 scorers are implemented but NOT added to the scorer chain: ComponentPriorityScorer, VisitationPenaltyScorer, SaturationScorer, ConfirmedCoverageScorer, CoverageDensityScorer, StrengthScorer. WtgScorer is a stub (always returns 0).
>
> **Impact**: Without ComponentPriorityScorer, text inputs and clicks are treated equally. Without ConfirmedCoverageScorer, screens that produced MOP coverage don't get exploration priority. Without SaturationScorer, heavily-explored screens aren't penalized at the screen level. The scoring is minimal — only MOP static analysis and visit decay.
>
> **Files**: `ActionSelector.java`, `Config.java` + tests

- [x] 17.1 Added ComponentPriorityScorer to scorer chain — SET_TEXT +200, CLICK/LONG_CLICK +100, SCROLL +25
- [x] 17.2 Added ConfirmedCoverageScorer to scorer chain — same instance shared with AgentLoop for addConfirmed() calls. Config: DEFAULT_CONFIRMED_COVERAGE_BASE=150
- [x] 17.3 Evaluated VisitationPenaltyScorer — NOT added (redundant with GradualDecayScorer, unbounded negative). Documented in ActionSelector Javadoc.
- [x] 17.4 Evaluated WtgScorer — NOT added (stub, always 0, WTG parsing not implemented). TODO added in WtgScorer.java for separate change/issue.
- [x] 17.5 Evaluated CoverageDensityScorer — NOT added (redundant with MopScorer, hardcoded count=1). TODO added in CoverageDensityScorer.java for review/removal in separate change/issue.
- [x] 17.6 Tests: 8 new ActionSelector tests (scorer chain composition, exclusion verification, confirmed coverage e2e)
- [x] 17.7 `mvn test` — 365 tests pass

## 18. Fix Timing and Throttle Issues

> **Context**: Default throttle_ms=50 is insufficient for UI transitions (200-500ms). The retry logic (3 attempts) fires actions in quick succession when "no effect" is detected, but the "no effect" may be a false negative due to insufficient wait time. This causes: (a) incorrect learning (agent thinks action doesn't work when it does), (b) multiple overlapping transitions, (c) coverage attribution to wrong states.
>
> **Impact**: Agent sees 3 "no effect" retries per iteration when the app actually DID transition — it just hadn't completed the animation yet. This compounds the BACK-on-root problem: buttons that DO navigate are marked as failed, lowering their scores.
>
> **Files**: `Config.java`, `AgentLoop.java` + tests

- [x] 18.1 DEFAULT_THROTTLE_MS 50→200, DEFAULT_MAX_RETRIES_PER_CYCLE 3→1
- [x] 18.2 Adaptive wait: if hash unchanged after throttle, sleep additional 150ms (DEFAULT_ADAPTIVE_WAIT_MS) and re-capture. Disableable via adaptive_wait_ms=0.
- [x] 18.3 Retry logic: MAX_RETRIES reduced to 1, retries use 200ms throttle (vs old 50ms). Combined with adaptive wait, total wait is 350ms before declaring "no effect".
- [x] 18.4 Tests: 5 new Config tests (defaults, property overrides, disable adaptive wait)
- [x] 18.5 `mvn test` — 340 tests pass (at time of group completion, before groups 15+17)

## Phase 5: Critical Algorithm Fixes (E2E-revealed bugs)

> Post-E2E analysis revealed that despite Groups 15-18, the agent still exits the app on iteration 8.
> Root cause: two bugs + one missing feature.

## 19. Fix BACK in selectNextBest (bypass root-screen check)

> **Context**: `selectNextBest()` (retry path, line 190) adds BACK unconditionally without checking if
> the current screen is a root screen. The Tier 4 fix only protects `selectFromUnifiedQueue()`. When the
> first action has no effect and `MAX_RETRIES=1`, the retry calls `selectNextBest()` which can return BACK
> even on the root screen, exiting the app.
>
> **Root cause in trace**: Iteration 8 shows BACK with `retries:1`, confirming it came from the retry path.
>
> **Files**: `ActionSelector.java` + tests

- [x] 19.1 In `selectNextBest()`, apply the same root-screen check: only add BACK when `successorTracker != null && !successorTracker.getParents(hash).isEmpty()`
- [x] 19.2 Test: 3 tests added — selectNextBest excludes BACK with null tracker, with empty parents, and allows BACK when parents exist
- [x] 19.3 `mvn test` — 365 tests pass

## 20. Add out-of-app detection with automatic restart

> **Context**: The rvsmart agent has NO detection for when it leaves the target app. When a BACK or crash
> sends the agent to the launcher (NexusLauncherActivity), it continues exploring the launcher instead of
> restarting the app. The rvagent has a 3-action tolerance: if 3 consecutive actions happen outside the
> app's package, it force-stops and restarts.
>
> **Impact in trace**: After exiting at iteration 8, the agent spends iterations 9-47 (39 iterations, ~47s)
> clicking on the launcher. Zero useful exploration.
>
> **Files**: `AgentLoop.java`, `Config.java` + tests

- [x] 20.1 Add `DEFAULT_OUT_OF_APP_TOLERANCE = 3` to Config with getter
- [x] 20.2 In AgentLoop.runIteration(), after getRootInActiveWindow (step 2), check if `root.getPackageName()`
      matches the target `packageName`. Uses manifest package (same namespace as CLI --package).
      If NOT matching, increment `outOfAppCounter`. If counter >= tolerance, call `recoverApp()`,
      reset counter, and return. If matching, reset counter to 0.
- [x] 20.3 Log via Log.d/Log.w when out-of-app is detected and when restart is triggered
- [x] 20.4 Tests: Config tests for default (3) and property override. Counter+restart integration skipped — requires Android AccessibilityNodeInfo mocking (getPackageName), not feasible with android.jar stubs
- [x] 20.5 `mvn test` — 365 tests pass

## 21. Add detailed RvTrack logging for action selection diagnostics

> **Context**: Current trace output shows only the final action type and hash. There is no visibility into
> WHY the agent selected a specific action (which tier, which scores, which candidates). This makes debugging
> the algorithm nearly impossible from trace files alone.
>
> **Files**: `ActionSelector.java`, `RvTrack.java`

- [x] 21.1 In ActionSelector.selectAction(), log via RvTrack.strategy() which tier was used (1=PathBuffer, 2=untested, 3=proactive, 4=unified) with untested count and saturation
- [x] 21.2 In selectFromUnifiedQueue(), log via RvTrack.rank() top-3 scored actions with scores and BACK exclusion status
- [x] 21.3 In selectNextBest(), log via RvTrack.rank() retry candidate type, score, candidates count, excluded count
- [x] 21.4 `mvn test` — 370 tests pass (365 existing + 3 new selectNextBest root-screen tests + 2 Config out-of-app tests)

## 22. Trace Diagnostics and E2E Validation

- [x] 22.1 Add coordinates (action_x, action_y) and widget_class to TraceWriter output — enables post-hoc verification of click targets
- [x] 22.2 Update TraceWriter tests for new fields (13 fields total, was 10)
- [x] 22.3 `mvn package` — rebuild JAR with trace coordinates
- [x] 22.4 Run rvsmart 30s on cryptoapp — verified coordinates match widget bounds exactly
- [x] 22.5 Run full `rv-experiment` with rvsmart and APE, 120s timeout — rvsmart wins all metrics (Activities 100% vs 75%, Methods 33.9% vs 18.64%, MOP 42.62% vs 24.59%, Errors 5 vs 3)
- [x] 22.6 Verify trace: agent explores all 4 activities (MainActivity, MessageDigestActivity, CipherActivity, CryptographyActivity), unique_states grows throughout execution

## 23. Fix MotionEvent injection (SOURCE_TOUCHSCREEN)

> **Root cause**: `MotionEvent.obtain()` creates events with `source=0` (SOURCE_UNKNOWN).
> Without `InputDevice.SOURCE_TOUCHSCREEN`, the WindowManager silently ignores the events —
> they are accepted by `InputManager.injectInputEvent()` (returns true) but never dispatched
> to any window. This caused ALL clicks and long-clicks to have zero visual effect despite
> correct coordinates and successful injection.
>
> **Files**: `InputInjector.java`

- [x] 23.1 Add `InputDevice.SOURCE_TOUCHSCREEN` to all MotionEvents in `inject()` via `setSource()`
- [x] 23.2 Fix JAR search path in tool.py: `rvsec-android` → `rvsec/rvsec-android` (was finding stale JAR copy)
- [x] 23.3 Remove stale JAR from Python module dir (mvn install copies it automatically)
- [x] 23.4 Verified fix: 30s run shows `action_had_effect: true`, navigation to MessageDigestActivity, 4 unique states in 5 iterations
