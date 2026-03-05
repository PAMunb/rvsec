## Why

The current RVAgent (Python) achieves ~1 iter/s in pure_algorithm mode, limited by external overhead: UIAutomator2 over ADB (~200ms per UI capture) and inter-iteration sleep (500ms fixed). Competing tools like APE achieve ~10 evt/s by running inside the Android emulator via `app_process`. This 10x throughput gap limits the number of actions per time budget and reduces overall coverage in time-constrained experiments. Beyond raw speed, running externally prevents algorithmic improvements that require sub-millisecond feedback — multi-attempt cycles (retry no-effect actions in the same iteration), instant crash detection via `ActivityController` callback, and real-time coverage rewards from logcat. GitHub Issue: #29.

**Baseline**: Emulador API 29 (x86_64, 4GB RAM), cryptoapp.apk, timeout 60s, host: AMD Ryzen 7 2700U, 32GB RAM. All throughput targets measured against this baseline.

## What Changes

- **New Java agent (rvsmart)**: Standalone executable JAR (`rvsmart.jar`) that runs inside the Android emulator via `app_process`. Implements a 4-tier DFS-based exploration strategy derived from the Python RVAgent's 5-tier design (BACK/RESTART consolidated into a unified Tier 4 queue, eliminating the separate Tier 5 fallback) using internal Android APIs (`AccessibilityNodeInfo`, `InputManager`, `ActivityController`, `IActivityManager`) instead of external UIAutomator2. Located at `$RVSEC_HOME/rvsec-android/rvsmart/`, built with Maven, same ecosystem as rvsec-gator.
- **New rv-tools plugin**: `RVSmartTool` extending `AbstractTool` — pushes JAR + optional static analysis data to emulator, executes via `adb shell CLASSPATH=... /system/bin/app_process`, captures stdout trace. Registers as built-in tool with variants (`mvp`, `fast`, `hybrid`).
- **Graceful degradation**: 4 operational modes depending on available data — full (static analysis + instrumented APK), MOP-directed (static analysis only), coverage-aware (instrumented APK only), heuristic (neither). All modes use the same core algorithm; additional data sources add scoring layers.
- **LLM hybrid mode (Phase 2)**: Optional SGLang integration via HTTP from inside emulator (`10.0.2.2` → socat bridge → sglang container). `RoutingManager` selects between algorithm and LLM paths per iteration. `LlmCircuitBreaker` handles network failures with automatic fallback.
- **Confirmed coverage rewards**: Real-time logcat reading for `RVSEC-COV` tags feeds a new `ConfirmedCoverageScorer` (new scorer for rvsmart, not present in the Python agent) — ground-truth reward signal instead of static proxy estimates from `MopScorer`.
- **Structural hash compatibility**: Same algorithm as Python agent (same fields, same JSON canonicalization, same SHA-256[:12]) for direct comparability of state graphs between Java and Python runs.

## Capabilities

### New Capabilities

- `rvsmart`: The rvsmart Java agent — architecture, bootstrap via `app_process`, main loop, internal components (device interaction, strategy, graph, recovery, LLM, output), configurable parameters (~48 via `Properties`, ~39 calibratable), operational modes, and the rv-tools plugin integration. This is a new standalone system within the RVSEC ecosystem that does not modify existing rv-agent behavior.

### Modified Capabilities

- `tools`: New built-in tool registration (`RVSmartTool`) with variants and factory integration. Adds a new tool class following the existing `AbstractTool` contract (FR18, FR19, FR20). No changes to the registry/factory patterns themselves — only a new consumer of the existing extension points. Delta spec needed to document the new tool's `ToolSpec`, variants, and execution contract.
- `platform`: No behavioral changes to the platform itself — no code changes required. The platform already supports any tool conforming to `AbstractTool`. The delta spec documents the integration contract between rvsmart's trace output and the existing result processing pipeline (trace file compatibility, metrics extraction, resume identity). This is pure documentation of how the existing pipeline consumes rvsmart output, not a specification of new platform behavior.

## Impact

**New module** (outside rv-android uv workspace):
- `rvsec-android/rvsmart/` — Java 8, Maven, compiles against android.jar API 29 stubs. Produces `rvsmart.jar` via maven-shade-plugin. Zero runtime dependency on rv-android Python code.

**Modified rv-android modules**:
- **rv-tools**: New `RVSmartTool` class in `builtin/rvsmart/`. Extends `AbstractTool`, implements `execute_tool_specific_logic()` (adb push + adb shell app_process). New variants: `mvp` (pure_algorithm, throttle 50ms), `fast` (pure_algorithm, throttle 30ms), `hybrid` (multimode with LLM). Follows existing patterns from APE/DroidBot tools.
- **rv-platform**: No code changes required. Platform already handles any `AbstractTool` via `ToolFactory` + `TaskExecutor` component pipeline. The `ResultProcessorComponent` already reads tool output from task results. rvsmart's trace format is designed to be compatible with existing result processing. A delta spec documents the integration contract (trace file compatibility, metrics extraction, resume identity) — this is documentation of existing behavior, not new platform code.
- **rv-experiment**: No code changes required. Experiment orchestration (pre-processing → execution → post-processing) works unchanged. rvsmart APKs go through the same instrumentation + static analysis pipeline. CLI already supports `--tools rvsmart:mvp`.

**Docker integration**:
- socat bridge in `docker-entrypoint.sh` for LLM mode (container localhost:30000 → sglang service:30000)
- `docker-compose.yml` update for sglang service dependency when using hybrid mode

**Cross-module dependencies**:
- rvsmart reads `static_analysis.json` produced by rv-static-analysis (same format as Python agent)
- rvsmart reads `RVSEC-COV` logcat tags produced by rv-instrumentation's AspectJ weaving (same tags as Python agent)
- rv-tools plugin uses `Command` class from rv-android-core for adb operations

**Metrics contract**: rvsmart writes a final JSON report prefixed with `RVSMART_METRICS:` to stdout. `RVSmartTool` extracts it and writes to `rvsmart_metrics.json` alongside the trace file. Standard `coverage_metrics` (method_coverage, activities_coverage, etc.) are populated by rv-platform's `CoverageComponent` from logcat — same as all other tools. rvsmart-specific metrics (throughput, multi-attempt retries, LLM stats) live in the separate JSON file for Optuna calibration and post-processing. No changes to `TaskResult` model or `ResultProcessorComponent`.

**Multi-repo protocol**: rvsmart Java code lives in `$RVSEC_HOME/rvsec-android/rvsmart/` (external repo). The rv-tools Python plugin lives in `rv-android`. Coordination: (1) Java code is merged first in rvsec repo, producing `rvsmart.jar`, (2) Python plugin is merged in rv-android referencing the JAR, (3) Docker image build includes the JAR from `$RVSEC_HOME`. Version compatibility: the `RVSMART_METRICS:` JSON schema and the `static_analysis.json` input format are the interface contracts. Breaking changes require coordinated PRs in both repos.

**Related requirements**: FR18 (plugin system), FR19 (external tool support), FR20 (variant system), FR07 (task execution), NFR01 (modularity), NFR03 (testability).

**Phased delivery**:
- Phase 0 (PoC): Validate `app_process` fundamentals — bootstrap, UI capture, event injection, crash callback
- Phase 1 (MVP): 3-tier selection, multi-attempt, crash detection, system dialogs, rv-tools plugin, ~12-16 evt/s
- Phase 2 (Full): 4-tier selection with all 10 scorers, LLM hybrid, confirmed coverage, all 4 operational modes
- Phase 3 (Calibration): Optuna integration, equivalence tests, benchmark vs APE/FastBot/rvagent-python

## Acceptance Criteria

- [ ] Phase 0: `app_process` bootstrap succeeds, UI capture success rate >99% (1000 captures), event injection >99%, crash callback fires on forced crash
- [ ] Phase 1: rvsmart achieves ≥12 evt/s in pure_algorithm mode (baseline: cryptoapp, 60s, API 29)
- [ ] Phase 1: Structural hash produces identical output to Python agent for same UI (3 reference screens from real uiautomator dumps)
- [ ] Phase 1: rv-tools plugin resolves JAR, pushes, executes, captures trace file
- [ ] Phase 1: TraceWriter output + `RVSMART_METRICS:` report extracted correctly
- [ ] Phase 2: All 4 operational modes produce non-zero coverage on cryptoapp in 60s
- [ ] Phase 2: multimode at 5% LLM achieves ≥10 evt/s on cryptoapp (throughput degradation ≤20% vs pure_algorithm)
- [ ] Phase 2: LLM circuit breaker trips after 3 consecutive failures, auto-resets after 60s
- [ ] Phase 2: Node recycling validated — unit test with mock UI tree confirms all AccessibilityNodeInfo refs are recycled in try/finally (INV-RSM-02)
- [ ] Phase 2: No OutOfMemoryError during 1000 continuous iterations on cryptoapp (INV-RSM-13 validated by HeapMonitor)
- [ ] Phase 3: Hash equivalence: 0 divergences across ≥20 reference screens from 5+ apps (including edge cases: null fields, emoji/Unicode, deep nesting, RecyclerView with 500+ nodes)
- [ ] Phase 3: Optuna calibration integration functional with objective function
- [ ] Phase 3: rvsmart coverage ≥80% of APE coverage on same APKs (N≥5 APKs, paired comparison)
- [ ] All code follows P1-P4 principles
