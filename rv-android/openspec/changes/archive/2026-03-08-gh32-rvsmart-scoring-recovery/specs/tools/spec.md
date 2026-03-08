## Purpose

This delta spec updates the rvsmart section of the tools domain specification to reflect three categories of changes introduced by gh32: (1) the scoring chain is simplified from 8 to 7 scorers by fixing two broken scorers (`MopScorer`, `WtgScorer` via `StaticMap` parser rewrite), fixing one scorer that was returning constant values due to a bug (`CoverageDensityScorer` via `UICoverageTracker` ID mismatch fix), and removing two harmful ones (`RewardScorer`, `RewardPropagator`); (2) recovery mechanisms are fixed for out-of-app situations, empty screens, effect detection, and exception handling; (3) resource management is corrected for `AccessibilityNodeInfo` recycling, `PathBuffer` divergence checking, and `UICoverageTracker` element ID consistency.

These changes restore rvsmart's static analysis guidance system to operational status — `MopScorer` and `WtgScorer` will return non-zero scores when static analysis data is available, which is the agent's central design purpose. The `RewardScorer` and its supporting `RewardPropagator` infrastructure are removed entirely because they are harmful: reward accumulates infinitely without bound or decay, eventually dominating 96.8% of total score and causing deterministic ping-pong loops between high-reward states. With functional MOP and WTG scoring, the agent no longer needs TD learning as compensation for broken scorers.

All changes are in the rvsmart Java codebase (`$RVSEC_HOME/rvsec/rvsec-android/rvsmart/`). The Python `rvsmart-tool` plugin receives one minor change (empty trace detection). No changes to the Python plugin interface, rv-platform integration, or external data formats.

## Data Contracts

### Input

- `static_analysis.json: File` — JSON file produced by `RvsecAnalysisClient` (gh27). Contains three top-level keys: `"reachability"` (JsonArray of class objects with methods), `"windows"` (JsonArray of window objects), `"transitions"` (JsonArray of {sourceId, targetId, events} objects). Pushed to device at `/data/local/tmp/static_analysis.json` by `RVSmartTool`. The `StaticMap` parser reads this file on the device.

### Output

- `trace_file: File` — stdout JSON lines from rvsmart. Each line contains iteration data including score breakdown with per-scorer contributions. Lines with `action_type="ERROR"` indicate caught exceptions in the main loop (previously silent). Lines with `action_type="SKIP"` indicate early-return iterations (null root, system dialog, OOA in-progress, etc.) with a `reason` field describing the exit cause.

### Side-Effects

- **Device (AccessibilityNodeInfo)**: `root.recycle()` called in try/finally at all `getRootInActiveWindow()` call sites. Prevents native object accumulation during execution.
- **Device (OOA Recovery)**: When out-of-app is detected, the recovery sequence now sends `input keyevent BACK` and `am force-stop <foregroundPkg>` before restarting the target app. This affects system-level state beyond the app under test.

### Error

- `RuntimeException` in `runIteration()` — now produces a trace line with `action_type="ERROR"` and the exception message, instead of being silently logged to `Log.w`. The iteration counter still increments and the agent continues.

## Invariants

- **INV-RSM-30**: `StaticMap.parseReachability()` MUST parse the `"reachability"` key as a `JsonArray` (not `JsonObject`). Each array element is a class object containing `"className"` (String, fully qualified) and `"methods"` (JsonArray). Each method object contains `"signature"` (String), `"reachable"` (boolean), `"reachesMop"` (boolean), and `"directlyReachesMop"` (boolean). Activity name matching MUST normalize trace-format names (e.g., `"uiactivitiesSplashActivity"`) to fully-qualified names (e.g., `"com.crazyhitty.chdev.ks.munch.ui.activities.SplashActivity"`) by reconstructing dots from camelCase boundaries and prepending the code package.

- **INV-RSM-31**: `StaticMap.parseTransitions()` MUST parse the `"transitions"` key as a `JsonArray`. Each array element contains `"sourceId"` (int), `"targetId"` (int), and `"events"` (JsonArray of {type, widgetClass} objects). The parser MUST build an adjacency map from window IDs to their transitions, cross-referencing window IDs with activity names from the `"windows"` section.

- **INV-RSM-32**: The rvsmart scoring chain MUST consist of exactly 7 scorers: `MopScorer`, `WtgScorer`, `GradualDecayScorer`, `SystemElementFilter`, `ComponentPriorityScorer`, `ConfirmedCoverageScorer`, `CoverageDensityScorer`. The `RewardScorer` and `RewardPropagator` classes MUST NOT exist in the codebase — they are deleted per P3 (no backward compatibility). `CoverageDensityScorer` (re-enabled by gh31) becomes functional once the `UICoverageTracker` ID mismatch is fixed (INV-RSM-39).

- **INV-RSM-33**: When out-of-app is detected with `consecutiveOoaAfterRestart >= MAX_CONSECUTIVE_OOA_AFTER_RESTART`, the recovery sequence MUST: (1) send `input keyevent BACK` via `adb shell`, (2) if still out-of-app, call `am force-stop <foregroundPackage>`, (3) then `forceStop(targetPackage)` and `startApp(targetPackage)`. The `foregroundPackage` MUST be obtained from `root.getPackageName()` at OOA detection time.

- **INV-RSM-34**: When `ActionSelector.generateCandidateActions()` produces 0 interactive candidates AND the current screen has no parent in `SuccessorTracker`, the agent MUST `Thread.sleep(2000)` and recapture the screen before falling back to RESTART. This allows splash screen auto-transitions (Handler/Timer-based) to complete. If the recapture still produces 0 candidates, RESTART is the correct fallback.

- **INV-RSM-35**: When `action.type == SET_TEXT`, the `hadEffect` variable MUST be set to `true` unconditionally after action execution. The structural hash excludes text content by design (to avoid state explosion from dynamic content), so SET_TEXT never changes the hash — but it always changes the UI content. This prevents the stuck detector from counting SET_TEXT as "no progress" and triggering premature RESTART during form filling.

- **INV-RSM-36**: When `runIteration()` throws an exception caught by the `run()` method's catch block, the agent MUST write a trace line with `action_type="ERROR"` and the exception message to stdout before continuing to the next iteration. Additionally, all 6 early-return paths in `runIteration()` — (1) crash-at-start, (2) null root from `getRootInActiveWindow()`, (3) system dialog dismiss, (4) post-action crash, (5) post-action native crash, (6) OOA tolerance-not-exceeded — MUST write a trace line with `action_type="SKIP"` and a `reason` field describing the exit cause. This ensures that all iteration outcomes are visible in the `.trace` file even when running via `app_process` (where `Log.w` output is not captured by the Python plugin).

- **INV-RSM-37**: Every `AccessibilityNodeInfo` obtained via `getRootInActiveWindow()` MUST be recycled via `root.recycle()` in a `finally` block. This applies to all 4 call sites in `AgentLoop`: (1) initial capture at iteration start, (2) post-action capture, (3) adaptive wait recapture, (4) OOA detection capture. Failure to recycle causes native object accumulation (~4000 objects per 300s run) that can trigger OOM in long-running sessions.

- **INV-RSM-38**: `PathBuffer.invalidateIfDiverged(currentHash)` MUST compare `currentHash` against `expectedHashes[currentIndex]` (the hash at the current position in the planned path), NOT against `expectedHashes[currentIndex + 1]` or any other offset. An off-by-one error causes all multi-hop BFS recovery paths to fail on the first hop.

- **INV-RSM-39**: `UICoverageTracker` MUST use the same element ID scheme for both `registerScreenElements()` and `recordInteraction()`. If registration uses `"res:{resource_id}"` for elements with resource IDs, then `recordInteraction()` MUST also receive `"res:{resource_id}"` (not `"coords:{x},{y}"`). Mismatched ID schemes cause the tracker to never match registered elements with their interactions, making `getCoverageGap()` always return the maximum value.

- **INV-RSM-40**: `ScreenNode.totalActions` MUST be updated on every visit to the screen via `Math.max(existingTotal, currentCount)`. If the first visit to a screen captures 0 elements (transient UI state during activity transition), `totalActions` MUST NOT be permanently locked to 0 — subsequent visits with more elements MUST update the count. A permanent 0 causes `getSaturationRate()` to return 1.0, triggering premature proactive backtracking.

- **INV-RSM-41**: `UICoverageTracker.recordInteraction(screenHash, elementId)` MUST use `screenHash` to scope interactions by screen. The interaction counts map MUST use a composite key `screenHash + "|" + elementId` so that interactions recorded on screen A do not count toward coverage of elements on screen B that happen to share the same element ID (e.g., same resource ID used in different activities). Without screen scoping, `getCoverageGap()` reports inaccurate coverage that contaminates cross-screen exploration decisions.

- **INV-RSM-42**: `AgentLoop` MUST use the return value of `HeapMonitor.check()` as the actual sleep duration between iterations, instead of always sleeping `config.getThrottleMs()`. When heap pressure is normal, `check()` returns the configured throttle value (no behavior change). When heap pressure is high, `check()` returns a larger value that MUST actually delay the next iteration — this adaptive throttle was effectively dead code because the caller ignored the return value.

## MODIFIED Requirements

### Requirement: RVSmartTool Execution Contract

`RVSmartTool.execute_tool_specific_logic(task, app)` SHALL:
1. Resolve `rvsmart.jar` path via `JarResolver` (search paths in priority order: (a) `$RVSEC_HOME/rvsec/rvsec-android/rvsmart/target/rvsmart.jar` — development Maven build, (b) `$TOOLS_DIR/rvsmart/rvsmart.jar` — manual placement, (c) `/opt/rv-android/tools/rvsmart/rvsmart.jar` — Docker image). First match wins.
2. Push `rvsmart.jar` to `/data/local/tmp/rvsmart.jar` via `adb push`.
3. If `task.static_data` is available and has a `json_path`, push the JSON to `/data/local/tmp/static_analysis.json`.
4. If configuration parameters require a properties file, generate `rvsmart.properties` and push to `/data/local/tmp/`.
5. Build the `adb shell` command: `adb -s <device_serial> shell CLASSPATH=/data/local/tmp/rvsmart.jar /system/bin/app_process /data/local/tmp/ br.unb.cic.rvsmart.Main --package <package_name> --timeout <timeout> [--static-data ...] [--config ...] [--mode ...]`.
6. Execute via `self._execute_and_check_command()` with stdout and stderr directed to `task.result.trace_file`.
7. After execution, check if trace file is empty (0 bytes). If empty, log a warning indicating the agent produced no output (possible silent hang or crash).

Before full execution, `RVSmartTool` SHALL run a health check: `adb shell CLASSPATH=... app_process ... --health-check`. This validates ServiceManager connections and performs one UI capture to verify AccessibilityNodeInfo reflection, then exits with code 0 (success) or 1 (failure). If the health check fails, the tool SHALL log an error with the health check output and raise an exception.

Timeout behavior follows the standard `AbstractTool` contract: `RVCommandTimeoutError` is converted to `RVToolTimeoutError` by the base class. This is expected behavior (INV-TOOL-06).

#### Scenario: Health check passes
- **WHEN** `--health-check` exits with code 0
- **THEN** `RVSmartTool` SHALL proceed with full execution

#### Scenario: Health check fails
- **WHEN** `--health-check` exits with code 1
- **THEN** `RVSmartTool` SHALL log "rvsmart health check failed: <stderr output>"
- **AND** `RVSmartTool` SHALL NOT proceed with full execution
- **AND** the task SHALL be marked as failed with a clear error message

#### Scenario: Execution with static analysis data
- **WHEN** `execute_tool_specific_logic(task, app)` is called with `task.static_data.json_path = "/results/exp1/instrumented_apks/cryptoapp/static_analysis.json"`
- **THEN** rvsmart.jar SHALL be pushed to `/data/local/tmp/rvsmart.jar`
- **AND** static_analysis.json SHALL be pushed to `/data/local/tmp/static_analysis.json`
- **AND** the adb shell command SHALL include `--static-data /data/local/tmp/static_analysis.json`
- **AND** `StaticMap` SHALL parse the JSON correctly as JsonArrays (INV-RSM-30, INV-RSM-31)
- **AND** `MopScorer` SHALL return non-zero scores for actions on screens whose methods have `directlyReachesMop=true`
- **AND** `WtgScorer` SHALL return non-zero scores for actions matching known transitions to unvisited activities

#### Scenario: Execution without static analysis data
- **WHEN** `task.static_data` is None
- **THEN** the adb shell command SHALL NOT include `--static-data`
- **AND** rvsmart SHALL operate in heuristic mode (MopScorer/WtgScorer return 0 — no static data to read)

#### Scenario: Timeout after configured duration
- **WHEN** the tool executes for the configured timeout (e.g., 300 seconds)
- **THEN** `RVCommandTimeoutError` SHALL be raised by the Command
- **AND** `AbstractTool.execute()` SHALL convert it to `RVToolTimeoutError`
- **AND** rv-platform SHALL treat this as success (INV-PLT-04)

#### Scenario: Empty trace file detected
- **WHEN** execution completes and the trace file exists but has 0 bytes
- **THEN** `RVSmartTool` SHALL log a warning "rvsmart produced empty trace file — possible silent hang or startup crash"
- **AND** execution SHALL NOT be marked as failure (the agent ran for the full timeout)

## ADDED Requirements

### Requirement: StaticMap JSON Parser Compatibility (FR18, FR19)

`StaticMap` SHALL correctly parse the JSON format produced by `RvsecAnalysisClient` (gh27). The JSON file contains three top-level keys, all of which are `JsonArray` values (not `JsonObject`). The parser was originally written expecting `JsonObject` values, causing `getAsJsonObject()` to return `null` silently — this made MopScorer and WtgScorer return 0 for all actions since gh29.

The parser MUST handle three aspects correctly:

1. **Format**: Read `"reachability"` and `"transitions"` as `JsonArray` via `getAsJsonArray()`.
2. **Activity name normalization**: Trace-format activity names (e.g., `"uiactivitiesSplashActivity"` — dots stripped from relative path) MUST be normalized to match fully-qualified names in the JSON (e.g., `"com.crazyhitty.chdev.ks.munch.ui.activities.SplashActivity"`). The normalization reconstructs the fully-qualified name by prepending the code package and re-inserting dots at camelCase boundaries.
3. **Transitions data model**: The `"transitions"` section uses `{sourceId, targetId, events}` objects referencing window IDs from the `"windows"` section. The parser MUST cross-reference window IDs with activity names to build the activity-to-transitions adjacency map that `WtgScorer` reads.

#### Scenario: Reachability parsed from JsonArray
- **WHEN** `StaticMap` loads a JSON file where `"reachability"` is a JsonArray with 50 class entries
- **AND** class `"com.example.app.MainActivity"` has method `"<com.example.app.MainActivity: void onClick(View)>"` with `directlyReachesMop=true`
- **THEN** `getMopMethodsForActivity("MainActivity")` SHALL return a non-empty set containing that method signature
- **AND** `MopScorer.score()` SHALL return a positive value for CLICK actions on that activity's screen

#### Scenario: Transitions parsed from JsonArray
- **WHEN** `StaticMap` loads a JSON file where `"transitions"` is a JsonArray with `{sourceId: 1, targetId: 2, events: [{type: "implicit_launch_event"}]}`
- **AND** the `"windows"` section maps windowId=1 to `"com.example.app.MainActivity"` and windowId=2 to `"com.example.app.SettingsActivity"`
- **THEN** `getTransitions("MainActivity")` SHALL return transitions containing a path to `"SettingsActivity"`
- **AND** `WtgScorer.score()` SHALL return +200 for CLICK actions that match this transition when `"SettingsActivity"` is unvisited

#### Scenario: Activity name normalization
- **WHEN** the trace reports activity `"uiactivitiesSplashActivity"` and the code package is `"com.crazyhitty.chdev.ks.munch"`
- **THEN** `StaticMap` SHALL normalize the name to match against `"com.crazyhitty.chdev.ks.munch.ui.activities.SplashActivity"` in the JSON
- **AND** MOP and WTG queries for that activity SHALL return correct results

### Requirement: Scoring Chain Composition (FR18, NFR01)

The rvsmart scoring chain SHALL consist of exactly 7 additive scorers, each contributing an independent score component that is summed to produce the total action score:

| # | Scorer | Contribution | Status |
|---|--------|-------------|--------|
| 1 | `MopScorer` | Boost for actions on screens with methods that reach monitored operations | Functional (requires StaticMap fix) |
| 2 | `WtgScorer` | Boost for actions matching static WTG transitions to unvisited activities (+200/+100/+50 by hop distance) | Functional (requires StaticMap fix) |
| 3 | `GradualDecayScorer` | 200→0 decay over 5 visits to penalize revisitation | Unchanged |
| 4 | `SystemElementFilter` | -5000 for system UI elements to prevent interaction | Unchanged |
| 5 | `ComponentPriorityScorer` | SET_TEXT=200, CLICK=100, SCROLL=25 to prioritize high-value action types | Unchanged |
| 6 | `ConfirmedCoverageScorer` | 150/(1+revisits) to boost screens with confirmed MOP coverage, decaying on revisits | Unchanged (decay added by gh31) |
| 7 | `CoverageDensityScorer` | coverageGap * weight (default 100) to direct exploration toward screens with untested elements | Functional (requires UICoverageTracker ID fix — INV-RSM-39; re-enabled by gh31) |

The following are REMOVED (P3 — complete deletion, backup to `backup/`):

- `RewardScorer` — accumulated rewards infinitely without bound, eventually dominating 96.8% of total score. The `maxCumulativeFactor` config field was defined but never enforced. The `reset()` method existed but was never called. With functional MOP and WTG scorers, the agent has real static analysis guidance and no longer needs reward accumulation.
- `RewardPropagator` — infrastructure supporting `RewardScorer`. Computed N-step TD returns and propagated confirmed coverage rewards, but all values were consumed only by the removed `RewardScorer`.

#### Scenario: Scoring with functional MOP and WTG data
- **WHEN** static analysis data is loaded and `MopScorer` has MOP method data for the current activity
- **AND** `WtgScorer` has transition data showing a 1-hop path to an unvisited activity via a CLICK action
- **THEN** the CLICK action's total score SHALL include: mop > 0, wtg = 200, decay (visit-dependent), component = 100, confirmed (coverage-dependent), system = 0
- **AND** the RewardScorer component SHALL NOT appear in the score breakdown

#### Scenario: Scoring without static analysis data
- **WHEN** no static analysis data is available (`StaticMap.isLoaded() == false`)
- **THEN** `MopScorer` SHALL return 0 for all actions
- **AND** `WtgScorer` SHALL return 0 for all actions
- **AND** scoring falls back to the 4 non-static scorers (GradualDecay, SystemElement, ComponentPriority, ConfirmedCoverage)

### Requirement: OOA Multi-Stage Recovery (FR19, NFR04)

When out-of-app is detected (foreground package differs from target package), and `consecutiveOoaAfterRestart` reaches `MAX_CONSECUTIVE_OOA_AFTER_RESTART`, the agent SHALL execute a multi-stage recovery sequence instead of the current single-stage `forceStop(target) + startApp(target)`:

1. Send `input keyevent BACK` via `adb shell` to dismiss modal activities (e.g., SoundPicker, Chrome FirstRun)
2. Wait 500ms and re-check foreground package
3. If still out-of-app, call `am force-stop <foregroundPackage>` to close the blocking app
4. Then proceed with the standard `forceStop(targetPackage) + startApp(targetPackage)`

The foreground package is already available at OOA detection time (`root.getPackageName()`) and is passed to `RvTrack.ooa()` — it just needs to also be used for `forceStop`.

#### Scenario: Modal activity blocking recovery (SoundPicker)
- **WHEN** the agent detects OOA with foreground package `"com.google.android.soundpicker"` for 3 consecutive attempts
- **THEN** the agent SHALL send `input keyevent BACK`
- **AND** if the foreground is still `"com.google.android.soundpicker"` after 500ms
- **THEN** the agent SHALL call `am force-stop com.google.android.soundpicker`
- **AND** then `forceStop(targetPackage)` and `startApp(targetPackage)`

#### Scenario: BACK dismisses the blocking activity
- **WHEN** the agent sends `input keyevent BACK` and the foreground returns to the target package
- **THEN** the agent SHALL NOT call `forceStop` on either package
- **AND** `consecutiveOoaAfterRestart` SHALL reset to 0

### Requirement: Empty Screen Wait Strategy (FR19, NFR01)

When `ActionSelector.generateCandidateActions()` produces 0 interactive candidates (no clickable, scrollable, or editable elements), and the current screen has no parent in the `SuccessorTracker` graph (indicating the agent cannot backtrack), the agent SHALL wait for a potential auto-transition before resorting to RESTART.

Many Android apps use splash screens that auto-transition to the main activity after 2-3 seconds via `Handler.postDelayed()`. Without waiting, the agent's RESTART (~1.2s cycle) relaunches the app before the transition completes, creating an infinite loop of splash screen restarts. In the blippex experiment, this caused 93.6% of iterations to be wasted on RESTART in the SplashActivity.

#### Scenario: Splash screen auto-transition
- **WHEN** the agent captures a screen with 0 interactive elements and no parents in the graph
- **THEN** the agent SHALL `Thread.sleep(2000)` and recapture the screen via `UiCapture.capture()`
- **AND** if the recaptured screen has interactive elements, the agent SHALL proceed with normal action selection
- **AND** if the recaptured screen still has 0 elements, the agent SHALL fall back to RESTART

### Requirement: Exception Visibility in Trace Output (FR19, NFR04)

When `runIteration()` throws an exception caught by the `run()` method's catch block, the agent SHALL write a trace line to stdout with `action_type="ERROR"` and the exception message. This ensures that failures are visible in the `.trace` file, which is the primary diagnostic artifact for rvsmart executions.

RVSmart runs via `app_process` as UID 2000 (shell user) without access to the device's logcat buffer. The current `Log.w(TAG, ...)` call in the catch block writes to logcat, which is not captured by the Python plugin's stdout redirection. Errors are silently lost.

#### Scenario: Exception produces trace line
- **WHEN** `runIteration()` throws `NullPointerException` at iteration 42
- **THEN** the agent SHALL write to stdout: `{"iteration":42, "action_type":"ERROR", "error":"NullPointerException: <message>", ...}`
- **AND** the agent SHALL continue to iteration 43

#### Scenario: Early return produces SKIP trace line
- **WHEN** `getRootInActiveWindow()` returns `null` at iteration 15
- **THEN** the agent SHALL write to stdout: `{"iteration":15, "action_type":"SKIP", "reason":"null_root", ...}`
- **AND** the agent SHALL continue to iteration 16

## REMOVED Requirements

### RewardScorer and RewardPropagator

**Reason**: `RewardScorer` accumulates rewards infinitely via `RewardPropagator.propagate()` called every iteration. The `accumulatedRewards` map grows without bound — after 1000 iterations in the munch experiment, the top 2 screen hashes had reward values of ~14000, dominating 96.8% of the total score. This made all other scorers irrelevant and caused deterministic ping-pong loops between high-reward states.

The `maxCumulativeFactor` configuration constant (value 3.0) was defined in `Config.java` but never enforced — no code reads it. The `RewardPropagator.reset()` method exists but is never called from `recoverApp()`, `handleOoaRestart()`, or `executeAction(RESTART)`. The rewards persist across app restarts, permanently reinforcing the bias toward previously visited screens.

With `MopScorer` and `WtgScorer` restored to operational status (via the StaticMap parser fix), the agent has real static analysis guidance. The RewardScorer was a compensation mechanism for broken static analysis scorers — that compensation is no longer needed and is actively harmful.

**Deleted files**: `strategy/RewardPropagator.java`, `strategy/scorers/RewardScorer.java`, and their associated test files. Backed up to `backup/` per P3.
