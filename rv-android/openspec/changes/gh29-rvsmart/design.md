## Context

The Python RVAgent achieves ~1 iter/s due to external communication overhead (UIAutomator2 over ADB, fixed 500ms sleep). APE achieves ~10 evt/s by running inside the emulator via `app_process`. This design describes rvsmart, a Java agent that ports the RVAgent's 5-tier DFS exploration strategy to run internally via `app_process`, targeting ~12-16 evt/s in pure_algorithm mode. The agent is standalone (no rv-android dependency at runtime) but integrates with rv-android via a new rv-tools plugin. See proposal.md and GitHub Issue #29.

Related requirements: FR18 (plugin system), FR19 (tool support), FR20 (variants), FR07 (task execution), NFR01 (modularity).

Constraints:
- Java 8 (RVSEC ecosystem standard, APE/FastBot/Monkey precedent)
- Maven build (same toolchain as rvsec-gator)
- API 29 android.jar stubs (compile-time only; ART provides runtime)
- Shell UID 2000 (no root, but `INJECT_EVENTS` permission via `app_process`)
- Timeout is the ONLY exit condition from the main loop

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Android Emulator (API 29)                                    │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ rvsmart.jar (via app_process, Shell UID 2000)          │ │
│  │                                                         │ │
│  │  Main → AgentLoop ──────────────────────────────────   │ │
│  │           │                                             │ │
│  │     ┌─────┼──────────────┬──────────────┐              │ │
│  │     │     │              │              │              │ │
│  │  device/  │        strategy/       graph/              │ │
│  │  UiCapture│        ActionSelector DynamicStateGraph  │ │
│  │  InputInj │        10 Scorers       ScreenNode         │ │
│  │  CrashInt │        PathBuffer                          │ │
│  │  AppCtrl  │        SuccessorTracker                    │ │
│  │  SysDlg   │        RewardPropagator                    │ │
│  │  Logcat   │              │                             │ │
│  │     │     │         recovery/                          │ │
│  │     │     │         StuckDetector                      │ │
│  │     │     │         BacktrackBfs                       │ │
│  │     │     │              │                             │ │
│  │     │     │          llm/ (Phase 2)                    │ │
│  │     │     │          SglangClient ──→ 10.0.2.2:30000   │ │
│  │     │     │          ToolCallParser                    │ │
│  │     │     │              │                             │ │
│  │     └─────┼──────────────┘                             │ │
│  │           │                                             │ │
│  │       output/                                           │ │
│  │       TraceWriter (stdout JSON lines)                   │ │
│  │       MetricsCollector (final JSON report)              │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  staticdata/ (optional, loaded from /data/local/tmp/)        │
│  StaticMap ← static_analysis.json (from rv-static-analysis)  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ rv-android (Python, host/container)                  │
│                                                      │
│  rv-tools/builtin/rvsmart/                           │
│  └── RVSmartTool (AbstractTool)                      │
│      1. adb push rvsmart.jar                         │
│      2. adb push static_analysis.json (optional)     │
│      3. adb push rvsmart.properties (optional)       │
│      4. adb shell CLASSPATH=... app_process ...      │
│      5. stdout → trace file (captured by Command)    │
└─────────────────────────────────────────────────────┘
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `Main` | Entry point, arg parsing, bootstrap, ServiceManager connections | CLI args | Configured AgentLoop |
| `AgentLoop` | Main while-loop, orchestrates one iteration per cycle | Config, DeviceController, Strategy | Trace output (stdout) |
| `DeviceController` | ServiceManager reflection, service connections | - | IActivityManager, IWindowManager, InputManager handles |
| `UiCapture` | AccessibilityNodeInfo BFS traversal with recycle() | Root node | `ScreenState` (items, activity, hash) |
| `InputInjector` | `InputManager.injectInputEvent()` for touch/key | `Action` | Event injected |
| `CrashInterceptor` | `ActivityController.appCrashed()` callback | System callback | Crash log entry + auto-restart |
| `SystemDialogDetector` | Detect system dialogs by package name | `ScreenState` | Dismissed or pass-through |
| `LogcatReader` | Non-blocking logcat reader for RVSEC-COV tags | Logcat stream | `List<String>` covered methods |
| `ActionSelector` | 4-tier action selection + multi-attempt. Tier 4 uses unified priority queue where widget actions (scored by 10 scorers, even saturated) and BACK/RESTART (scored by their own base scores, NOT by widget scorers) compete. BACK has dynamic decay on consecutive no-effect — self-correcting, prevents infinite loops. | Screen, Graph, StaticMap | `Action` (never null) |
| `DynamicStateGraph` | HashMap-based state graph with transitions | Visit/transition records | Visit counts, rewards, transitions |
| `StuckDetector` | Level 1 (BACK) + Level 2 (BFS to unsaturated ancestor) | Screen hash history | Recovery action |
| `StaticMap` | Loads `static_analysis.json` (nullable) | JSON file path | Reachability, windows, transitions |
| `RoutingManager` | LLM vs algorithm decision per iteration | Mode, screen, graph | Boolean (use LLM?) |
| `SglangClient` | HTTP POST to OpenAI-compatible API (Phase 2) | Messages + screenshot | LLM response |
| `TraceWriter` | Per-iteration JSON line to stdout | Iteration data | JSON line |
| `MetricsCollector` | Final metrics JSON report at timeout | Aggregated stats | JSON report |
| `RvTrack` | Structured decision logging via `[RVTRACK:<CATEGORY>]` to logcat. Same prefix convention as Python agent for tooling compatibility. 15 categories, aggregate counters. | Decision data | `Log.i("RVSMART", "[RVTRACK:...] key=value")` |
| `Config` | `java.util.Properties` loader with defaults | Properties file | Typed config values |
| `RVSmartTool` (Python) | rv-tools plugin: push, execute, capture | Task, App | Trace file |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| Bootstrap via app_process | `Main.main()` + `DeviceController.connect()` | `test_bootstrap_connects_services` |
| UI capture <10ms | `UiCapture.captureScreen()` (BFS + recycle) | `test_ui_capture_returns_valid_tree` |
| Event injection <3ms | `InputInjector.inject()` | `test_event_injection_succeeds` |
| Structural hash compat | `ScreenState.computeHash()` (SHA-256[:12]) | `test_hash_matches_python_agent` |
| Multi-attempt cycles | `AgentLoop` retry loop (MAX_RETRIES_PER_CYCLE) | `test_multi_attempt_retries_on_no_effect` |
| Crash detection | `CrashInterceptor.appCrashed()` callback | `test_crash_callback_fires_on_exception` |
| Native crash detection | `AgentLoop` null root + process gone check | `test_native_crash_detected_on_empty_ui` |
| System dialog dismiss | `SystemDialogDetector.isSystemDialog()` + `.dismiss()` | `test_system_dialog_dismissed` |
| Graceful degradation | Null checks on StaticMap, LogcatReader | `test_heuristic_mode_no_static_data` |
| Confirmed coverage | `ConfirmedCoverageScorer` + `LogcatReader` | `test_confirmed_coverage_rewards` |
| LLM hybrid (Phase 2) | `SglangClient` + `RoutingManager` + `LlmCircuitBreaker` | `test_llm_circuit_breaker_fallback` |
| Timeout-only exit | `AgentLoop` while-loop condition | `test_loop_exits_only_on_timeout` |
| INV-TOOL-02 (default variant) | `RVSmartTool.get_variants()` includes "default" | `test_rvsmart_has_default_variant` |
| INV-TOOL-06 (timeout = success) | `RVSmartTool.execute_tool_specific_logic()` | `test_timeout_is_success` |
| FR18 (registry) | `RVSmartTool` registered in BUILTIN_TOOLS | `test_rvsmart_registered_in_registry` |
| FR20 (variants) | Variants: default, mvp, fast, hybrid | `test_rvsmart_variants_resolved` |
| INV-RSM-12 (unified queue) | `ActionSelector` with BACK/RESTART as self-scored synthetic actions (not through 10 widget scorers), dynamic BACK decay | `test_selector_never_returns_null`, `test_back_decay_promotes_widget_retry`, `test_no_widgets_selects_back_then_restart`, `test_select_next_best_excludes_failed` |
| RVTRACK (structured logging) | `RvTrack` static methods, 15 categories, aggregate counters | `test_rvtrack_format`, `test_rvtrack_counters` |

## Goals / Non-Goals

**Goals:**
- Port the 5-tier DFS exploration strategy from Python to Java with structural hash compatibility
- Achieve ~12-16 evt/s in pure_algorithm mode (10x improvement over Python)
- Integrate with rv-android via rv-tools plugin following existing APE tool pattern
- Support 4 graceful degradation modes based on available data (static analysis, instrumentation)
- Add multi-attempt cycles, instant crash detection, and confirmed coverage rewards
- Maintain standalone usability (JAR + adb shell, no rv-android dependency)
- All ~49 parameters configurable via `java.util.Properties` for Optuna calibration (~40 calibratable)

**Non-Goals:**
- Replacing the Python RVAgent — both coexist; rvsmart is a separate tool option
- Porting visual error detection (OpenCV) — requires image processing library inside emulator
- Porting ShortTermMemory/LongTermMemory — these are LLM context management, not needed for algorithm path
- Supporting API levels other than 29 — our emulator image is fixed at API 29
- Running on physical devices — `app_process` behavior varies across OEM ROMs
- Implementing a new exploration algorithm — this is a port of the existing Python strategy

## Decisions

### D1: Java 8 via app_process (not Kotlin, not native)

**Chosen**: Java 8 with `app_process` bootstrap.
**Alternatives considered**:
- Kotlin: Less boilerplate, null safety, but no precedent in `app_process` agents. Extra runtime (~1.5MB). Risk without practical benefit.
- C/C++ (NDK): Maximum performance but no access to Java APIs (AccessibilityNodeInfo, ActivityController). Kills productivity.
- Python inside emulator: Not feasible — Python interpreter not available on Android.

**Rationale**: APE, FastBot, and Monkey all use Java via `app_process`. The approach is battle-tested. RVSEC already uses Java (rvsec-gator). Future advisees can maintain it.

### D2: AccessibilityNodeInfo for UI capture (not UiAutomation, not uiautomator dump)

**Chosen**: `AccessibilityNodeInfo` via `ServiceManager.getService("accessibility")` + reflection.
**Alternatives considered**:
- `UiAutomation` via Instrumentation: Public API, stable, but requires InstrumentationRunner setup, slower.
- `uiautomator dump`: ~200-500ms per dump + XML parse. Unacceptable throughput.
- Accessibility Service (installed APK): Requires manual permission, incompatible with `app_process` model.

**Rationale**: Direct access, <10ms latency, same data as UIAutomator. APE (`GUITree`) and FastBot use the same approach.

### D3: InputManager.injectInputEvent() for event injection

**Chosen**: `InputManager.injectInputEvent()` via reflection.
**Alternatives**: `adb shell input tap` (~50ms overhead per command, 50x slower), `Instrumentation.sendPointerSync()` (not available via `app_process`), minitouch (extra binary, socket protocol, no clear benefit).

**Rationale**: <1ms latency, programmatic, no process fork. Standard for `app_process` agents (APE, FastBot, Monkey).

### D4: Gson for JSON (not org.json)

**Chosen**: Gson. **Alternative**: org.json (both viable). **Rationale**: Gson already in RVSEC ecosystem (RvsecAnalysisClient uses Gson). Sorted key serialization for deterministic structural hash via `TreeMap<String, Object>` — Gson serializes TreeMap keys in natural order, producing deterministic JSON without custom TypeAdapters. Golden test: hardcoded ScreenItems → expected SHA-256[:12] must match Python agent reference.

### D5: java.util.Properties for configuration (not YAML, not JSON config)

**Chosen**: `java.util.Properties` loaded from `--config rvsmart.properties`.
**Rationale**: Zero dependency, trivially parseable, key=value format maps directly to Optuna's parameter space. Optuna generates `.properties` files as part of the calibration loop.

### D6: Socat bridge for LLM networking (not adb reverse)

**Chosen**: `socat TCP-LISTEN:30000,bind=127.0.0.1,fork TCP:sglang:30000` in container entrypoint. Java agent connects to `http://10.0.2.2:30000/v1`. Bind to localhost only to avoid exposing the port to all container interfaces.
**Alternative**: `adb reverse tcp:30000 tcp:30000` — Java agent uses `http://localhost:30000/v1`.
**Rationale**: Socat is more explicit, no dependency on `adb reverse` state which can be lost on emulator restart. Both work; socat is the default, `adb reverse` documented as alternative.

### D7: Built-in tool (not external like rvagent)

**Chosen**: `RVSmartTool` as built-in tool in `rv-tools/builtin/rvsmart/`.
**Alternative**: External tool registered via `_register_external_tools()` like `RVAgentTool`.
**Rationale**: rvsmart is a JAR-based tool like APE — it pushes a JAR and runs via `adb shell`. This is the same pattern as all built-in tools. No separate Python module needed (unlike rvagent which wraps a full LangGraph application). The JAR is self-contained.

### D8: Phased delivery (PoC → MVP → Full → Calibration)

Phase 0 validates `app_process` fundamentals before investing in the full agent. Phase 1 delivers a functional agent with core capabilities. Phase 2 adds full algorithm parity + LLM. Phase 3 validates with calibration and benchmarks. Go/No-Go gate after Phase 0 — if fundamentals fail on our emulator image, reassess before investing 35+ dev-days.

## API Design

### Java Agent CLI

```
CLASSPATH=/data/local/tmp/rvsmart.jar \
  /system/bin/app_process /data/local/tmp/ \
  br.unb.cic.rvsmart.Main \
  --package <package_name> \
  --timeout <seconds> \
  [--static-data /data/local/tmp/static_analysis.json] \
  [--config /data/local/tmp/rvsmart.properties] \
  [--mode pure_algorithm|multimode|llm_only] \
  [--seed <int>]
```

**Preconditions**: Emulator running, target APK installed, JAR pushed to `/data/local/tmp/`.
**Postconditions**: Stdout contains JSON lines (trace) + final JSON report. Exit code 0.
**Error behavior**: Bootstrap failure → stderr message + exit code 1. Runtime crash → logged, agent restarts app and continues.

### RVSmartTool (Python plugin)

```python
class RVSmartTool(AbstractTool):
    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="rvsmart",
        description="Java agent running inside emulator via app_process",
        url="https://github.com/PAMunb/rvsec",
        version="1.0.0",
        process_pattern="br.unb.cic.rvsmart"
    )

    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "default": {"mode": "pure_algorithm", "throttle_ms": 50},
            "mvp": {"mode": "pure_algorithm", "throttle_ms": 50},
            "fast": {"mode": "pure_algorithm", "throttle_ms": 30},
            "hybrid": {"mode": "multimode", "llm_url": "http://10.0.2.2:30000/v1"},
        }

    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        # 1. Push JAR to device
        # 2. Push static_analysis.json (if available)
        # 3. Push config.properties (if available)
        # 4. Build adb shell CLASSPATH=... app_process ... command
        # 5. Execute with stdout → trace file
```

**Preconditions**: `rvsmart.jar` available (resolved via JarResolver). Emulator running (managed by rv-platform).
**Postconditions**: Trace file written. `rvsmart_metrics.json` written alongside trace (extracted from `RVSMART_METRICS:` line). `RVToolTimeoutError` raised on timeout (expected, handled by platform as success).
**Health check**: Before full execution, `RVSmartTool` runs a quick `adb shell CLASSPATH=... app_process ... --health-check` that validates ServiceManager connections and exits with code 0/1. If health check fails, the tool logs a clear error and skips execution (faster feedback than waiting for bootstrap timeout).

### Trace Output Format

Per-iteration JSON line (stdout):
```json
{"iteration":42,"timestamp_ms":15230,"hash":"a1b2c3d4e5f6","activity":"MainActivity",
 "action_type":"CLICK","action_source":"algorithm","action_had_effect":true,
 "retries":0,"unique_states":12,"elapsed_s":15.2}
```

Final metrics JSON (last stdout line, prefixed with `RVSMART_METRICS:`):
```json
{"metadata":{...},"exploration":{...},"decisions":{...},"ui_coverage":{...},
 "confirmed_coverage":{...},"llm":{...}}
```

The `RVSMART_METRICS:` prefix allows rv-tools plugin to extract the final report from the trace file without ambiguity.

## Data Flow

```
1. rv-tools pushes files to emulator:
   rvsmart.jar → /data/local/tmp/rvsmart.jar
   static_analysis.json → /data/local/tmp/static_analysis.json (optional)
   rvsmart.properties → /data/local/tmp/rvsmart.properties (optional)

2. rv-tools executes via adb shell:
   adb shell CLASSPATH=... /system/bin/app_process ... Main --package X --timeout T

3. Inside emulator, rvsmart main loop:
   UiCapture → ScreenState → DynamicStateGraph.recordVisit()
                            → SystemDialogDetector.check()
                            → LogcatReader.drainCoverageTags()
                            → RoutingManager.shouldUseLlm()
                               ├─ algorithm: ActionSelector.selectAction()
                               └─ llm: SglangClient.generate() → ToolCallParser → CoordinateNormalizer
                            → InputInjector.inject(action)
                            → UiCapture (verify) → actionHadEffect?
                               └─ no: multi-attempt retry (up to MAX_RETRIES_PER_CYCLE)
                            → Learner.update() (reward propagation, stuck detection)
                            → TraceWriter.writeLine() (stdout)

4. At timeout:
   MetricsCollector.writeFinalReport() → stdout (RVSMART_METRICS: prefix)

5. rv-tools captures stdout → trace file
   rv-platform ResultProcessorComponent reads trace file for results

6. After execution, rv-tools plugin post-processing:
   RVSmartTool.extract_metrics() → search trace file for last RVSMART_METRICS: line
   → parse JSON → write rvsmart_metrics.json alongside trace file
   → standard coverage_metrics populated by CoverageComponent from logcat (unchanged)
```

### LLM Path Data Flow (Phase 2)

```
AgentLoop (LLM iteration):
  RoutingManager.shouldUseLlm() → true
    → ScreenshotCapture.capture() (SurfaceControl ~20ms; fallback: adb exec-out screencap ~150ms if UID 2000 lacks permission)
    → ImageProcessor.compress(screenshot) (PNG→JPEG quality 80, resize 1000px)
    → PromptBuilder.build(screenshot_b64, screen_items, navigation_hint)
    → SglangClient.generate(messages) via HTTP POST to 10.0.2.2:30000/v1
       ├─ success: ToolCallParser.parse(response) → action_type + normalized_coords
       │           → CoordinateNormalizer.denormalize(qwen_coords, display_size) → device_pixels
       │           → Action(type, x, y, source="llm")
       ├─ network error: LlmCircuitBreaker.recordFailure()
       │                 → 3 consecutive → trip (skip LLM for 60s)
       │                 → fallback: ActionSelector.selectAction() (algorithm path)
       └─ parse error: log warning → fallback to algorithm action
```

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| Reflection failure at bootstrap | `DeviceController.connect()` — API not found | Log error, exit code 1 | PoC validates all reflection targets; bootstrap is Go/No-Go gate |
| UI tree empty (null root) | `UiCapture` — possible native crash or ANR | Check if app process alive via `getRunningTasks()` | If gone: log native crash, force-stop + restart. If alive: wait one cycle (ANR). |
| App crash (Java exception) | `CrashInterceptor.appCrashed()` callback | Log crash with stack trace, mark action as crash-causing | `forceStopPackage()` + `startActivity()` (~50-100ms) |
| `RVToolTimeoutError` | `AbstractTool.execute()` wraps `RVCommandTimeoutError` | Expected behavior — tool ran for configured duration | Platform returns `True` (success). Results collected. |
| LLM network failure | `SglangClient` — connection refused, timeout | `LlmCircuitBreaker`: 3 consecutive failures → skip LLM for 60s | Auto-reset after cooldown. Fallback to algorithm path. |
| LLM parse failure | `ToolCallParser` — invalid response format | Log warning, fall back to algorithm action for this iteration | No retry — LLM call is expensive. Algorithm handles it. |
| OOM (heap pressure) | `HeapMonitor` — `Runtime.freeMemory()` below threshold (warning: <20% heap, critical: <10% heap). Check interval: every 100 iterations. | Critical: increase throttle_ms by 50%, log warning | Adaptive: if pressure persists for 3 consecutive checks, reduce MAX_ITEMS cap to 1000 temporarily |
| Static analysis missing | `StaticMap` — file not provided or parse failure | MopScorer and WtgScorer return 0 | Graceful degradation to heuristic mode. Log info. |
| Multi-attempt exhaustion | All actions on screen have ≥3 consecutive failures | StuckDetector escalation (BACK or RESTART) | Tier 4 unified queue: BACK wins by score, then StuckDetector Level 2 BFS to unsaturated ancestor |
| Saturated/low-value screen (INV-RSM-12) | All widget actions saturated, system elements only, or no interactive widgets | Unified priority queue: BACK and RESTART are synthetic actions competing by score alongside widget actions. Saturated actions stay in queue with low scores. | BACK score decays with consecutive no-effect repeats (`-200/repeat`), naturally promoting saturated widget re-execution or RESTART. Self-correcting, no special-case logic. |

## Risks / Trade-offs

**[Reflection API breakage across API levels]** → Mitigation: API level assertion at bootstrap (`Build.VERSION.SDK_INT != 29` → warn). Target only API 29. PoC validates all reflection targets before investing in full implementation.

**[OOM from unrecycled AccessibilityNodeInfo]** → Mitigation: BFS traversal with `node.recycle()` in try/finally block. MAX_ITEMS cap (2000). HeapMonitor with adaptive throttle on memory pressure.

**[LLM latency dominates in multimode]** → Trade-off accepted. In multimode, LLM inference (~1.5-3s) dominates regardless of Java speed. Mitigation: default `llm_probability=0.05` (5%), much lower than Python agent (algorithm iterations are now 10x more productive). `new_screen_only` routing strategy likely optimal. Calibration via Optuna will find the sweet spot.

**[Widget matching accuracy (static→runtime)]** → Same challenge as Python agent. resource-id matching ~60-75%. No mitigation beyond what Python already does — this is inherent to the approach.

**[Structural hash divergence between Python and Java]** → Mitigation: Same algorithm, same fields, same JSON canonicalization (Gson sorted keys), same SHA-256[:12]. Unit test validates hash equivalence for reference UI trees.

**[Socat bridge failure in Docker]** → Mitigation: LlmCircuitBreaker auto-falls back to algorithm. socat healthcheck in entrypoint. Only affects LLM mode — pure_algorithm unaffected.

**[android.jar stubs vs ART runtime mismatch]** → android.jar API 29 stubs are compile-time only — ART provides the actual classes at runtime. If code references a class/method present in the stubs but missing from the actual ART runtime (e.g., hidden API restrictions tightened in newer emulator builds), the result is `NoClassDefFoundError` or `NoSuchMethodError` at runtime, not at compile time. Mitigation: PoC Phase 0 validates all reflection targets and all directly-used Android APIs. Use only public API + reflection for internal APIs (ServiceManager, InputManager). The `--health-check` mode catches these failures fast.

**[Multi-repo version drift]** → rvsmart Java (rvsec repo) and RVSmartTool Python (rv-android repo) share two interface contracts: (1) `RVSMART_METRICS:` JSON schema, (2) `static_analysis.json` input format. Breaking changes require coordinated PRs. Merge order: Java first (produces JAR), Python second (references JAR). Docker build includes JAR from `$RVSEC_HOME`. Mitigation: version string in `RVSMART_METRICS` metadata + RVSmartTool logs JAR version at startup.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (Java) | Structural hash, scorers, graph operations, config parsing, action selection | JUnit 5, mock Android APIs | ~40 tests |
| Unit (Python) | RVSmartTool variant resolution, command building, trace parsing | pytest, mock Command | ~15 tests |
| Integration (Java) | Full AgentLoop with mock DeviceController | JUnit 5 with service mocks | ~10 tests |
| Integration (Python) | RVSmartTool registration, factory resolution | pytest with registry | ~5 tests |
| Equivalence | Same static_analysis.json, compare structural hashes | Python vs Java hash comparison script | ~5 tests |
| E2E | rvsmart on cryptoapp via rv-experiment | `rv-experiment run --tools rvsmart:mvp` | ~3 scenarios |

**Hash equivalence tests** are critical: the Python agent produces reference hashes for known UI states; the Java agent must produce identical hashes. This is tested at the unit level (same canonical JSON → same SHA-256[:12]) and at the integration level (same screen → same hash).

## Resolved Questions

1. **JAR distribution** (RESOLVED): `JarResolver` searches in priority order: (1) `$RVSEC_HOME/rvsec-android/rvsmart/target/rvsmart.jar` (development — Maven build output), (2) `$TOOLS_DIR/rvsmart/rvsmart.jar` (manual placement), (3) `/opt/rv-android/tools/rvsmart/rvsmart.jar` (Docker image). Development uses (1); Docker image `COPY` from `$RVSEC_HOME` at build time uses (3). No need for (a) built-in alongside ape.jar — rvsmart is in a separate repo.

2. **Metrics contract** (RESOLVED): `RVSmartTool` extracts the `RVSMART_METRICS:` line from the trace file after execution and writes it to `rvsmart_metrics.json` alongside the trace file. No changes to `TaskResult` model or `ResultProcessorComponent`. Standard `coverage_metrics` (method_coverage, activities_coverage) are populated by rv-platform's `CoverageComponent` from logcat — same pipeline as all other tools. rvsmart-specific metrics (throughput, multi-attempt stats, LLM stats) are available in the separate JSON file for Optuna calibration and post-analysis scripts. This avoids coupling rvsmart's metrics schema to `TaskResult`.

3. **Parent POM integration** (RESOLVED): rvsmart is added as a module in `$RVSEC_HOME/rvsec-android/pom.xml`. `android.jar` API 29 stubs are provided as a system-scope dependency pointing to `$ANDROID_HOME/platforms/android-29/android.jar` — same approach as APE uses. `mvn package` in the rvsmart directory produces the fat JAR via maven-shade-plugin.
