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

- [ ] 1.1 Create `$RVSEC_HOME/rvsec-android/rvsmart/` directory structure: `src/main/java/br/unb/cic/rvsmart/`, `src/test/java/`, `src/main/resources/`
- [ ] 1.2 Create `pom.xml`: parent POM reference, Java 8 compiler, maven-shade-plugin for fat JAR, android.jar API 29 as system-scope dependency, Gson dependency, JUnit 5 for tests
- [ ] 1.3 Add `rvsmart` as module in `$RVSEC_HOME/rvsec-android/pom.xml`
- [ ] 1.4 Create `Main.java` with CLI argument parsing (`--package`, `--timeout`, `--static-data`, `--config`, `--mode`, `--seed`) and API level assertion
- [ ] 1.5 Verify `mvn package` produces `rvsmart.jar` in `target/`

## 2. PoC: Validate app_process Fundamentals

> **Dispatch**: Subagent (general-purpose). Pass: design.md (D1-D3 decisions, Error Handling), specs/rvsmart/spec.md (Bootstrap, UI Capture, Event Injection, Crash Detection requirements).
> **Files**: ~5 new Java files in `br/unb/cic/rvsmart/device/` + `br/unb/cic/rvsmart/`
> **IMPORTANT**: Task 2.7 is a MANUAL Go/No-Go gate — subagent reports results, orchestrator evaluates.
> **Emulator**: Use `scripts/run_emulator.sh` to start the API 29 emulator for standalone PoC testing. rv-platform manages the emulator lifecycle in experiment context, but for PoC validation we use the script directly.
> **Test APKs (pre-instrumented with static analysis from gh27 validation)**:
> - `results/gh27_batch_validation/instrumented_apks/cryptoapp.apk` (+ `.apk.json`) — package: `br.unb.cic.cryptoapp`
> - `results/gh27_batch_validation/instrumented_apks/edu.cmu.cylab.starslinger.demo_17301504.apk` (+ `.apk.json`)
> - `results/gh27_batch_validation/instrumented_apks/org.secuso.privacyfriendlyludo_5.apk` (+ `.apk.json`)

- [ ] 2.1 Implement `DeviceController.java`: connect to ActivityManagerService, WindowManagerService, InputManager via `ServiceManager.getService()` + reflection
- [ ] 2.2 Implement `UiCapture.java`: AccessibilityNodeInfo BFS traversal with `node.recycle()` in try/finally, MAX_ITEMS cap (2000) with priority-based retention (interactive widgets first, shallower depth second) per INV-RSM-11. Return `List<ScreenItem>`
- [ ] 2.3 Implement `InputInjector.java`: `InputManager.injectInputEvent()` via reflection for MotionEvent (CLICK, LONG_CLICK, SWIPE) and KeyEvent (BACK, KEY_EVENT)
- [ ] 2.4 Implement `AppController.java`: `IActivityManager.getRunningTasks(1)` for current Activity, `forceStopPackage()` + `startActivity()` for app lifecycle
- [ ] 2.5 Implement `CrashInterceptor.java`: register `ActivityController` callback for `appCrashed()` / `appEarlyNotResponding()` / `appNotResponding()`
- [ ] 2.6 Create PoC test harness in Main: bootstrap → capture UI → inject click → detect crash → print results to stdout. Use `scripts/run_emulator.sh` to start the emulator, install a test APK from `results/gh27_batch_validation/instrumented_apks/`, then run the harness via `adb shell CLASSPATH=... app_process ...`
- [ ] 2.7 Validate `SurfaceControl.screenshot()` with Shell UID 2000: test whether `SurfaceControl.screenshot(display)` works from `app_process` context. Shell UID 2000 may lack `CAPTURE_SCREEN` permission — if so, document alternative approaches (e.g., `adb exec-out screencap -p` piped to stdin, or `/dev/graphics/fb0`). This is critical for Phase 2 LLM screenshot capture.
- [ ] 2.8 Validate `AccessibilityNodeInfo.getViewIdResourceName()` format: verify whether it returns `package:id/name` or `id/name` and compare with UIAutomator2 XML `resource-id` attribute format. Document the format and ensure `ScreenState.computeHash()` normalizes it to match the Python agent's format (INV-RSM-03).
- [ ] 2.9 Validate PoC on API 29 emulator: UI capture success rate >99% across 1000 captures, event injection success rate >99%, crash callback fires on forced crash. **Go/No-Go gate**: if any fundamental fails, document findings and reassess. Document results in GitHub issue (#29) using this template:

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

- [ ] 3.1 Implement `core/ScreenState.java`: items list, activity name, structural hash. `computeHash()` MUST match Python agent output (INV-RSM-03): same fields, same ordering (resource_id then class), Gson sorted keys, SHA-256[:12]
- [ ] 3.2 Implement `core/Action.java`: type enum (CLICK, LONG_CLICK, SET_TEXT, SCROLL, SWIPE, BACK, KEY_EVENT, RESTART), x/y device pixels, text (nullable), source ("algorithm"/"llm"), `signature()` method
- [ ] 3.3 Implement `core/Config.java`: load from `java.util.Properties` file with typed getters and defaults for all ~48 parameters (see spec Parameters section for complete list)
- [ ] 3.4 Implement `graph/ScreenNode.java`: visitCount, executedActions map (ActionSignature → count), failedActions map, cumulativeReward, transitions set
- [ ] 3.5 Implement `graph/DynamicStateGraph.java`: `LinkedHashMap<String, ScreenNode>` (insertion-ordered for deterministic BFS with --seed), methods: `recordVisit()`, `recordTransition()`, `recordAction()`, `recordActionFailure()`, `getVisitCount()`, `getSaturation()`
- [ ] 3.6 Add JUnit tests: structural hash equivalence with Python reference hashes (golden test: hardcoded ScreenItems → exact expected hash), Config default loading, DynamicStateGraph operations. Include at least 3 reference hashes computed by the Python agent from real `uiautomator dump` captures of cryptoapp screens (not just synthetic trees). Document how to generate new reference hashes using the Python agent (for future maintenance).
- [ ] 3.7 Run `mvn test` — verify all unit tests pass
- [ ] 3.8 Run `/rv-code-reviewer` (Java scope: `$RVSEC_HOME/rvsec-android/rvsmart/src/main/java/br/unb/cic/rvsmart/core/`, `graph/`)

## 4. Device Interaction Layer

> **Dispatch**: Subagent (general-purpose). Pass: specs/rvsmart/spec.md (System Dialog Handling, Confirmed Coverage via logcat), design.md (Key Components: SystemDialogDetector, LogcatReader, HeapMonitor).
> **Files**: ~3 new Java files in `device/` + tests

- [ ] 4.1 Implement `device/SystemDialogDetector.java`: detect system dialogs by package name (`android`, `com.android.packageinstaller`, etc.), dismiss by clicking OK/Allow/Deny
- [ ] 4.2 Implement `device/LogcatReader.java`: non-blocking thread that reads logcat for `RVSEC-COV` tags, `drainCoverageTags()` returns accumulated list and clears buffer
- [ ] 4.3 Implement `device/HeapMonitor.java`: periodic `Runtime.freeMemory()` check, increases throttle_ms when below threshold
- [ ] 4.4 Add JUnit tests: SystemDialogDetector package matching, LogcatReader tag parsing, HeapMonitor threshold logic
- [ ] 4.5 Run `mvn test`

## 5. MVP Strategy (3-Tier Selection)

> **Dispatch**: Subagent (general-purpose). Pass: specs/rvsmart/spec.md (Tiered Action Selection, Scorers, Stuck Detection, Graceful Degradation INV-RSM-04), design.md (ActionSelector, StaticMap).
> **Files**: ~5 new Java files in `strategy/`, `recovery/`, `staticdata/` + tests

- [ ] 5.1 Implement `strategy/scorers/Scorer.java` interface: `int score(Action candidate, ScreenState screen, DynamicStateGraph graph, StaticMap staticMap)`
- [ ] 5.2 Implement 3 MVP scorers: `MopScorer.java` (returns 0 when StaticMap null), `GradualDecayScorer.java`, `SystemElementFilter.java`
- [ ] 5.3 Implement `strategy/ActionSelector.java` with 3-tier MVP subset: Tier 2 (untested), Tier 4 (unified queue with 3 scorers + BACK/RESTART synthetic actions per INV-RSM-12). Tiers 1 and 3 stubbed for Phase 2. **Important**: The unified queue design (INV-RSM-12) MUST be implemented from Phase 1 — do not implement a separate Tier 5 BACK fallback that would need refactoring later. The synthetic action scoring (BACK=-100, RESTART=-500, BACK decay) is part of the MVP.
- [ ] 5.4 Implement `recovery/StuckDetector.java`: Level 1 only (hash unchanged for N iterations → BACK)
- [ ] 5.5 Implement `staticdata/StaticMap.java`: load `static_analysis.json` via Gson, nullable. `getReachabilityInfo()`, `getWindowInfo()`, `getTransitionInfo()`
- [ ] 5.6 Add JUnit tests: scorer outputs for known inputs, ActionSelector tier selection logic, StuckDetector triggering, StaticMap null handling. **Critical (INV-RSM-12)**: test unified priority queue — (a) never returns null, (b) all-system-element screen: BACK wins by score, (c) consecutive BACKs: BACK score decays, saturated widget action eventually wins, (d) zero widgets: BACK selected first, then RESTART after BACK decay exhaustion. Test BACK/RESTART synthetic scoring with configurable base scores.
- [ ] 5.7 Run `mvn test`

## 6. Output Layer

> **Dispatch**: Subagent (general-purpose). Pass: specs/rvsmart/spec.md (Trace Output INV-RSM-10, RVTRACK, MetricsCollector), design.md (Trace Output Format).
> **Files**: ~3 new Java files in `output/` + tests

- [ ] 6.1 Implement `output/TraceWriter.java`: write JSON line to stdout per iteration (fields: iteration, timestamp_ms, hash, activity, action_type, action_source, action_had_effect, retries, unique_states, elapsed_s)
- [ ] 6.2 Implement `output/MetricsCollector.java`: accumulate stats across iterations, `writeFinalReport()` writes `RVSMART_METRICS:` prefixed JSON to stdout at timeout. Include aggregate counters from RvTrack.
- [ ] 6.3 Implement `output/RvTrack.java`: structured decision logging via `Log.i("RVSMART", "[RVTRACK:<CATEGORY>] key=value")`. 15 categories matching Python agent convention (PARSE, ROUTE, RANK, SELECT, EXEC, STATE, LEARN, STRATEGY, BACKTRACK, REWARD, COVERAGE, LLM, STUCK, CRASH, OOM). Maintain aggregate counters (backtrack_count, restart_count, multi_attempt_retries, etc.). Static methods for each category (e.g., `RvTrack.select(iter, tier, action, coords, score)`).
- [ ] 6.4 Add JUnit tests: TraceWriter JSON format, MetricsCollector aggregation with counters, RVSMART_METRICS prefix presence (INV-RSM-10), RvTrack message format and counter accumulation
- [ ] 6.5 Run `mvn test`

## 7. Main Loop (AgentLoop)

> **Dispatch**: Subagent (general-purpose). Pass: specs/rvsmart/spec.md (Main Loop INV-RSM-01, Multi-Attempt INV-RSM-07, Crash Detection, Learner INV-RSM-08), design.md (Data Flow, AgentLoop component).
> **Files**: ~3 new Java files in `core/` + update `Main.java` + tests
> **NOTE**: This group wires all Phase 1 components together. Subagent needs awareness of all prior groups' APIs.

- [ ] 7.1 Implement `core/AgentLoop.java`: main while-loop with timeout-only exit (INV-RSM-01). Sequence: captureUi → updateGraph → checkSystemDialog → drainLogcatCoverage → selectAction → preMarkAction → execute → verifyEffect → multiAttempt → learn → throttle
- [ ] 7.2 Implement `core/Learner.java`: post-action processing — reward assignment (new_activity=2.0, new_state=1.0, same_state=-0.1), stuck detection update, graph update. Source-agnostic (INV-RSM-08).
- [ ] 7.3 Implement multi-attempt logic inside AgentLoop: compound `actionHadEffect` check (hash OR activity OR focus change), retry with `selectNextBest()` up to MAX_RETRIES_PER_CYCLE, skip actions with ≥3 consecutive failures (INV-RSM-07)
- [ ] 7.4 Implement native crash detection in AgentLoop: null root → check getRunningTasks() → restart if gone
- [ ] 7.5 Wire Main.java to bootstrap DeviceController + build AgentLoop + run
- [ ] 7.6 Add JUnit tests: AgentLoop timeout exit, multi-attempt retry logic, native crash detection flow, Learner reward assignment. **Critical (INV-RSM-12)**: test that AgentLoop never receives null from ActionSelector. Verify BACK decay resets on state change. Wire RvTrack logging into all decision points (strategy tier, backtrack, reward, state change).
- [ ] 7.7 Run `mvn test`
- [ ] 7.8 Build fat JAR: `mvn package -DskipTests` and verify `rvsmart.jar` size (~500KB-1MB)
- [ ] 7.9 Implement `--health-check` mode in Main: bootstrap ServiceManager connections only, print status, exit 0/1. Used by RVSmartTool for fast failure detection.

## 8. rv-tools Plugin (Python)

> **Dispatch**: Subagent (general-purpose). Pass: specs/tools/spec.md (full), specs/platform/spec.md (full), design.md (RVSmartTool API, Trace Output Format). Also pass: `modules/rv-tools/src/rv_tools/builtin/ape/tool.py` as reference pattern.
> **Files**: ~3 new Python files in `modules/rv-tools/src/rv_tools/builtin/rvsmart/` + tests
> **Skills**: This group uses `/rv-doc-code` and `/rv-test-run` — the subagent MUST invoke these skills.

- [ ] 8.1 Create `modules/rv-tools/src/rv_tools/builtin/rvsmart/__init__.py` and `tool.py`: `RVSmartTool` extending `AbstractTool` with TOOL_SPEC, 4 variants (default, mvp, fast, hybrid), `configure()`, `execute_tool_specific_logic()`
- [ ] 8.2 Implement JAR resolution via `JarResolver` (search priority: (1) `$RVSEC_HOME/rvsec-android/rvsmart/target/rvsmart.jar`, (2) `$TOOLS_DIR/rvsmart/rvsmart.jar`, (3) `/opt/rv-android/tools/rvsmart/rvsmart.jar`)
- [ ] 8.3 Implement `execute_tool_specific_logic()`: adb push JAR + optional static data + optional config → build `Command` with `adb shell CLASSPATH=... /system/bin/app_process ...` → execute with stdout to trace file
- [ ] 8.4 Implement metrics extraction: search trace file for last `RVSMART_METRICS:` line, parse JSON, write to `rvsmart_metrics.json` alongside trace file. When metrics line is missing (agent crashed), write default metrics JSON with zeroed values and `"status":"metrics_unavailable"`. Standard `coverage_metrics` are populated by rv-platform's CoverageComponent from logcat (no changes needed).
- [ ] 8.4.1 Implement health check: before full execution, run `adb shell CLASSPATH=... app_process ... --health-check`. If exit code 1, log error and raise with clear message (faster than waiting for bootstrap timeout).
- [ ] 8.5 Register `RVSmartTool` in `BUILTIN_TOOLS` list in `rv_tools/__init__.py`
- [ ] 8.6 Add pytest tests: tool registration, variant resolution, command building, metrics extraction from sample trace file
- [ ] 8.7 Run `/rv-doc-code modules/rv-tools/src/rv_tools/builtin/rvsmart/tool.py`
- [ ] 8.8 Run `/rv-test-run rv-tools`

# Phase 2: Full Algorithm + LLM Hybrid

## 9. Complete Strategy (4-Tier + All Scorers)

> **Dispatch**: Subagent (general-purpose). **PARALLEL with Group 10**. Pass: specs/rvsmart/spec.md (Ten Scorers, Successor Tracker, Reward Propagation, Stuck Detection Level 2), design.md (ActionSelector, PathBuffer, SuccessorTracker, RewardPropagator, BacktrackBfs).
> **Files**: ~7 new Java files in `strategy/`, `recovery/` + tests

- [ ] 9.1 Implement remaining 7 scorers: `WtgScorer.java`, `CoverageDensityScorer.java`, `SaturationScorer.java`, `ComponentPriorityScorer.java`, `StrengthScorer.java`, `VisitationPenaltyScorer.java`, `ConfirmedCoverageScorer.java`
- [ ] 9.2 Implement `strategy/SuccessorTracker.java`: back_successors recording, parent re-enablement (max_re_enables=6), multi-value widget saturation (threshold=4)
- [ ] 9.3 Implement `strategy/PathBuffer.java`: store BACK sequences, one action per iteration, eager invalidation on divergence. 3 strategies: backtrack, MOP, coverage.
- [ ] 9.4 Implement `strategy/RewardPropagator.java`: N-step TD (N=5, gamma=0.8), `propagateConfirmedCoverage()` for logcat-confirmed rewards
- [ ] 9.5 Implement `recovery/BacktrackBfs.java`: BFS on back_successors for Level 2 stuck recovery
- [ ] 9.6 Complete ActionSelector: activate Tier 1 (PathBuffer) and Tier 3 (proactive backtrack with saturation threshold)
- [ ] 9.7 Update StuckDetector: add Level 2 (BFS to unsaturated ancestor → RESTART if not found)
- [ ] 9.8 Add JUnit tests: all 7 new scorers, SuccessorTracker re-enablement, PathBuffer dispensing + invalidation, RewardPropagator N-step propagation, BacktrackBfs pathfinding
- [ ] 9.9 Run `mvn test`
- [ ] 9.10 Run `/rv-code-reviewer` (Java scope: `strategy/`, `recovery/`)

## 10. LLM Integration (Java)

> **Dispatch**: Subagent (general-purpose). **PARALLEL with Group 9**. Pass: specs/rvsmart/spec.md (Routing Manager, LLM Circuit Breaker INV-RSM-09, Coordinate Normalization), design.md (D6 Socat decision, SglangClient, ToolCallParser, PromptBuilder, ImageProcessor, CoordinateNormalizer, ScreenshotCapture).
> **Files**: ~7 new Java files in `llm/` + tests

- [ ] 10.1 Implement `llm/SglangClient.java`: HTTP POST to OpenAI-compatible API (`java.net.HttpURLConnection`), request/response JSON via Gson, configurable base_url/model/temperature/top_p/top_k/max_tokens/timeout
- [ ] 10.2 Implement `llm/LlmCircuitBreaker.java`: 3 consecutive failures → open for 60s → auto-reset (INV-RSM-09)
- [ ] 10.3 Implement `llm/ToolCallParser.java`: parse tool calls from LLM response (native tool_calls field → XML fallback → JSON fallback), extract action type + coordinates + text
- [ ] 10.4 Implement `llm/PromptBuilder.java`: build messages array with screenshot (base64) + UI element list + navigation hint
- [ ] 10.5 Implement `llm/ImageProcessor.java`: compress screenshot PNG→JPEG quality 80, resize to 1000px longest edge
- [ ] 10.6 Implement `llm/CoordinateNormalizer.java`: Qwen3-VL [0,1000) → device pixels using DisplayMetrics
- [ ] 10.7 Implement `llm/ScreenshotCapture.java`: capture via SurfaceControl (~20ms)
- [ ] 10.8 Add JUnit tests: SglangClient request format, LlmCircuitBreaker state transitions, ToolCallParser for native/XML/JSON formats, CoordinateNormalizer conversion, ImageProcessor resize dimensions
- [ ] 10.9 Run `mvn test`
- [ ] 10.10 Run `/rv-code-reviewer` (Java scope: `llm/`)

## 11. Routing and Integration

> **Dispatch**: Subagent (general-purpose). Depends on groups 9 + 10. Pass: specs/rvsmart/spec.md (Routing Manager modes/strategies), design.md (Data Flow, RoutingManager).
> **Files**: ~2 new Java files + updates to AgentLoop + tests

- [ ] 11.1 Implement `core/RoutingManager.java`: 3 modes (PURE_ALGORITHM, MULTIMODE, LLM_ONLY), 3 strategies (probabilistic, new_screen_only, stuck_only), circuit breaker check
- [ ] 11.2 Wire LLM path into AgentLoop: RoutingManager decision → ScreenshotCapture → ImageProcessor → PromptBuilder → SglangClient → ToolCallParser → CoordinateNormalizer → Action
- [ ] 11.3 Wire ConfirmedCoverageScorer into ActionSelector (active when LogcatReader has data)
- [ ] 11.4 Wire RewardPropagator.propagateConfirmedCoverage() into AgentLoop logcat drain step
- [ ] 11.5 Add JUnit tests: RoutingManager mode/strategy combinations, LLM path action production (mocked SglangClient)
- [ ] 11.6 Run `mvn test`
- [ ] 11.7 Build final fat JAR: `mvn package`

## 12. Docker Integration

> **Dispatch**: Subagent (general-purpose). Pass: design.md (D6 Socat decision), specs/rvsmart/spec.md (LLM hybrid mode).
> **Files**: ~2 files in `docker/`

- [ ] 12.1 Add socat bridge command to `docker/docker-entrypoint.sh`: `socat TCP-LISTEN:30000,bind=127.0.0.1,fork,reuseaddr TCP:sglang:30000 &` (conditional on hybrid mode). Bind to localhost only — binding to 0.0.0.0 exposes the LLM port to all container network interfaces unnecessarily.
- [ ] 12.2 Update `docker/docker-compose.yml` (or create variant): add sglang service with GPU reservation, health check, rvandroid depends_on sglang
- [ ] 12.3 Ensure `rvsmart.jar` is included in Docker image build (copy from `$RVSEC_HOME/rvsec-android/rvsmart/target/`)
- [ ] 12.4 Test Docker build succeeds with rvsmart.jar included

# Phase 3: Calibration & Validation

## 13. Calibration and Equivalence Testing

> **Dispatch**: Subagent (general-purpose). Depends on groups 8 + 12. Pass: specs/rvsmart/spec.md (INV-RSM-03 hash compatibility, INV-RSM-10 metrics format), design.md (Testing Strategy: Equivalence layer).
> **Files**: ~3 new Python scripts

- [ ] 13.1 Create hash equivalence test script (Python): capture real UI trees from cryptoapp + at least 4 third-party apps (starslinger, privacyfriendlyludo, and 2+ additional) via `uiautomator dump` → compute hash with Python agent algorithm → compute hash with rvsmart (via subprocess on emulator or extracted logic) → assert equality (INV-RSM-03). Corpus requirement: ≥20 screens from 5+ distinct apps, including edge cases: (a) screen with all-null text/contentDescription, (b) screen with emoji/Unicode in text, (c) RecyclerView with 500+ nodes (tests MAX_ITEMS cap), (d) screen with deeply nested fragments overlay. Use real UI dumps, not synthetic trees — real dumps expose format differences (resource_id, special characters, deep nesting) that synthetic trees miss.
- [ ] 13.2 Create Optuna integration script (Python): generate `rvsmart.properties` files from Optuna trial parameters → push to emulator → run rvsmart → parse `rvsmart_metrics.json` → return objective value. **Objective function**: `maximize: throughput_evt_per_s × (unique_states / elapsed_s)`, subject to: `memory_peak < 80% heap`, `crash_rate < 1%`. Multi-objective with Pareto front if needed.
- [ ] 13.3 Test all 4 operational modes using pre-instrumented APKs from `results/gh27_batch_validation/instrumented_apks/`: full (instrumented APK + `.apk.json`), MOP-directed (`.apk.json` only), coverage-aware (instrumented APK only), heuristic (original APK, neither). Use `scripts/run_emulator.sh` for standalone emulator. Test on cryptoapp + at least 1 third-party APK (starslinger or privacyfriendlyludo).
- [ ] 13.4 E2E validation via rv-platform: `rv-experiment run --tools rvsmart:mvp --apks-dir results/gh27_batch_validation/instrumented_apks/ --timeout 60 --skip-monitors --skip-instrument --skip-static` — verify trace file, metrics JSON, coverage results. Use instrumented APKs directory directly (skip flags because APKs are already pre-processed).

# Final Verification

## 14. Quality Gate

> **Dispatch**: MAIN CONTEXT executes this group directly. Skills have `context: fork` — they run as isolated subagents, keeping main context clean. This is the standard Full SDD quality gate (WORKFLOW.md Section 9).
> **NOTE**: Python-specific skills (/rv-qa-lint-fix, /rv-verify) target the rv-tools module only. Language-agnostic skills (/rv-code-reviewer, /rv-docs-sync) cover both Java and Python code.

- [ ] 14.1 Run `source /etc/profile && cd $RVSEC_HOME/rvsec-android/rvsmart && mvn test` — all Java tests pass (via Bash in main context)
- [ ] 14.2 Run `/rv-qa-lint-fix rv-tools` — auto-fix formatting and imports in Python plugin code
- [ ] 14.3 Run `/rv-verify rv-tools` — tests + lint + type checks for Python rv-tools module
- [ ] 14.4 Invoke `/rv-code-reviewer` via Skill tool — review scope: rvsmart Java implementation (`$RVSEC_HOME/rvsec-android/rvsmart/`) + RVSmartTool Python plugin (`modules/rv-tools/src/rv_tools/builtin/rvsmart/`). This skill is language-agnostic and reviews both codebases.
- [ ] 14.5 Run `/rv-docs-sync` — update CLAUDE.md with rvsmart tool documentation (language-agnostic)
