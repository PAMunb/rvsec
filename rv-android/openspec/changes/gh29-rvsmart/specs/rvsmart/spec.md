# Specification: rvsmart Java Agent

## Purpose

rvsmart is a Java-based Android exploration agent that runs inside the Android emulator via `app_process`, achieving ~12-16 events/second in pure algorithm mode — approximately 10x the throughput of the Python RVAgent. It implements the same 5-tier DFS-based exploration strategy as the Python agent but uses internal Android APIs (`AccessibilityNodeInfo`, `InputManager`, `ActivityController`) instead of external UIAutomator2 over ADB.

The agent is packaged as a standalone fat JAR (`rvsmart.jar`) with zero dependency on rv-android Python code at runtime. It lives in `$RVSEC_HOME/rvsec-android/rvsmart/`, built with Maven (Java 8), compiled against android.jar API 29 stubs. At runtime, `app_process` bootstraps an ART VM with the JAR on the classpath, executing `br.unb.cic.rvsmart.Main` with Shell UID 2000 (`INJECT_EVENTS` permission, no root required).

rvsmart operates in four degradation modes depending on what data is available. The base algorithm is always the same; additional data sources add scoring layers without changing the core loop. When static analysis data (`static_analysis.json` from rv-static-analysis) is provided, MopScorer and WtgScorer activate to prioritize monitored-operation-reaching actions. When running on instrumented APKs (AspectJ-weaved by rv-instrumentation), a LogcatReader drains `RVSEC-COV` tags in real time, feeding a ConfirmedCoverageScorer with ground-truth reward signal. Without either data source, rvsmart operates as a heuristic explorer using component priority, gradual decay, and stuck detection — still functional, still DFS-driven, still achieving 12-16 evt/s.

Running inside the emulator enables algorithmic improvements impossible from the outside: multi-attempt cycles (retry no-effect actions within the same iteration at ~8ms cost instead of wasting a full ~700ms iteration), instant crash detection via `ActivityController.appCrashed()` callback (instead of 1-2 iterations of indirect detection), system dialog dismissal in the same cycle (instead of wasting iterations interacting with crash/permission dialogs), and direct app restart via `IActivityManager.forceStopPackage()` (~50-100ms instead of ~1-2s via ADB shell).

LLM integration (Phase 2) adds a hybrid mode where `RoutingManager` decides per iteration whether to use the algorithm path (~1-5ms) or the LLM path (~1.5-3s via SGLang). The LLM is reached from inside the emulator via `http://10.0.2.2:30000/v1` (host loopback) through a socat bridge to the sglang container. `LlmCircuitBreaker` handles network failures: 3 consecutive failures trigger a 60-second cooldown with automatic fallback to the algorithm path.

## Data Contracts

### Input
- `--package <string>` — Target app package name (required). Passed via CLI. Example: `br.unb.cic.cryptoapp`.
- `--timeout <int>` — Execution timeout in seconds (required). The ONLY exit condition from the main loop.
- `--health-check` — Validate ServiceManager connections and exit with code 0/1 (optional). Used by RVSmartTool for fast failure detection.
- `--static-data <path>` — Path to `static_analysis.json` on device filesystem (optional). When absent, MopScorer and WtgScorer return 0.
- `--config <path>` — Path to `rvsmart.properties` on device filesystem (optional). When absent, internal defaults used for all ~49 parameters.
- `--mode <enum>` — Execution mode: `pure_algorithm` (default), `multimode`, `llm_only`.
- `--seed <int>` — Random seed for reproducibility (optional).

### Output
- **Stdout (JSON lines)**: One JSON line per iteration with: `iteration`, `timestamp_ms`, `hash`, `activity`, `action_type`, `action_source`, `action_had_effect`, `retries`, `unique_states`, `elapsed_s`.
- **Stdout (final report)**: Last line prefixed with `RVSMART_METRICS:` containing a JSON object with sections: `metadata`, `exploration`, `decisions`, `ui_coverage`, `confirmed_coverage`, `llm`.
- **Logcat**: Standard Android logcat entries via `android.util.Log` (tag: `RVSMART`).

### Side-Effects
- **[Android System]**: Injects touch/key events into the target app via `InputManager`.
- **[Android System]**: May force-stop and restart the target app on crash or stuck recovery.
- **[Android System]**: Dismisses system dialogs (crash, permission, battery optimization).
- **[Network]**: In multimode/llm_only, makes HTTP POST requests to SGLang API.

### Error
- **Bootstrap failure**: If reflection fails to connect to ServiceManager services → stderr message + exit code 1.
- **Runtime crash of agent itself**: Uncaught exception → stack trace to stderr + exit code 1. (Crashes of the target app are handled gracefully via CrashInterceptor.)

### Examples

**Input (CLI)**:
```
CLASSPATH=/data/local/tmp/rvsmart.jar /system/bin/app_process /data/local/tmp/ \
  br.unb.cic.rvsmart.Main --package br.unb.cic.cryptoapp --timeout 60 \
  --static-data /data/local/tmp/static_analysis.json --mode pure_algorithm --seed 42
```

**Output (iteration line)**:
```json
{"iteration":42,"timestamp_ms":15230,"hash":"a1b2c3d4e5f6","activity":"MainActivity","action_type":"CLICK","action_source":"algorithm","action_had_effect":true,"retries":0,"unique_states":12,"elapsed_s":15.2}
```

**Output (final metrics, last line)**:
```
RVSMART_METRICS:{"metadata":{"tool":"rvsmart","package":"br.unb.cic.cryptoapp","mode":"pure_algorithm","timeout":60,"version":"1.0.0"},"exploration":{"iterations":4200,"execution_time_s":60.0,"unique_states":28,"total_transitions":4180,"throughput_evt_per_s":14.2},"decisions":{"total_actions":4200,"algorithm_actions":4200,"llm_actions":0,"multi_attempt_retries":312,"forced_backs":45,"crashes":2,"system_dialogs":3},"ui_coverage":{"unique_activities":5,"unique_hashes":28,"widgets_discovered":142,"widgets_interacted":98,"coverage_ratio":0.69},"confirmed_coverage":{"enabled":true,"unique_methods":12,"total_events":47,"mop_methods_reached":8},"llm":{"total_calls":0,"tokens_in":0,"tokens_out":0,"total_time_s":0,"circuit_breaker_trips":0}}
```

## Invariants

- **INV-RSM-01**: The main loop SHALL exit ONLY when elapsed time exceeds the configured timeout. No other exit condition (saturation, error count, empty action list) SHALL terminate the loop.
- **INV-RSM-02**: Every `AccessibilityNodeInfo` obtained via `getChild()` MUST be recycled via `node.recycle()` in a finally block. Failure to recycle causes Binder reference leaks leading to OOM within minutes at 14 evt/s.
- **INV-RSM-03**: The structural hash algorithm MUST produce identical output to the Python agent's `compute_screen_hash_from_description()` (in `dynamic_state_graph.py`) for the same UI tree. Same fields (class, resource_id, package, clickable, scrollable, checkable, enabled, long_clickable, editable), same ordering (primary sort by resource_id with empty string replaced by `"zzz"` for sort-to-end, secondary sort by class — matching the Python `sort(key=lambda x: (x["resource_id"] or "zzz", x["class"]))`), same JSON canonicalization: Gson with `GsonBuilder().create()` on a `TreeMap<String, Object>` to guarantee sorted keys, compact format with no spaces after separators (equivalent to Python `separators=(",", ":")`) — NOT `setPrettyPrinting()`, NOT custom TypeAdapter. The JSON structure is `{"activity":"<name>","items":[...]}` with `sort_keys=True` at top level. Output format: SHA-256[:12] hex string. Unit tests MUST include a golden test: given a concrete input (hardcoded list of ScreenItems), assert the exact hash output matches a reference value computed by the Python agent.
- **INV-RSM-04**: When `--static-data` is not provided, `StaticMap` SHALL be null and all scorers that depend on static data (MopScorer, WtgScorer) SHALL return 0. The agent MUST continue to function in heuristic mode.
- **INV-RSM-05**: When `LogcatReader` has no `RVSEC-COV` data (original APK or logcat unavailable), `ConfirmedCoverageScorer` SHALL return 0. The agent MUST continue using MopScorer estimates or heuristic scoring.
- **INV-RSM-06**: `CrashInterceptor.appCrashed()` callback MUST immediately mark the preceding action as crash-causing and initiate app restart. The agent MUST NOT attempt to execute additional actions before the restart completes.
- **INV-RSM-07**: Multi-attempt retries within a cycle MUST NOT exceed `MAX_RETRIES_PER_CYCLE`. Actions with ≥3 consecutive failures on the same screen MUST be skipped by `selectNextBest()`.
- **INV-RSM-08**: The `execute` and `learn` phases MUST be action-source-agnostic. The same code path handles actions from both algorithm and LLM origins. The `source` field is metadata only.
- **INV-RSM-09**: `LlmCircuitBreaker` MUST trip after 3 consecutive LLM failures and remain open for 60 seconds. During the open period, `RoutingManager.shouldUseLlm()` MUST return false regardless of mode/strategy.
- **INV-RSM-10**: The `RVSMART_METRICS:` prefix on the final stdout line MUST be present to allow unambiguous extraction of the metrics report from the trace file.
- **INV-RSM-11**: BFS traversal of the UI tree MUST cap at `MAX_ITEMS` (default 2000) nodes to prevent unbounded memory consumption on pathological UI trees. The 2000 limit is based on empirical observation: typical Android screens have 30-200 nodes; complex apps (e.g., RecyclerView with nested layouts) can reach 500-1500; 2000 provides headroom while keeping memory footprint bounded (~2000 × ~200 bytes/node ≈ 400KB). When the cap is reached, nodes SHALL be prioritized by: (1) interactive widgets (clickable, scrollable, checkable, editable) over non-interactive, (2) shallower depth over deeper depth. This ensures that actionable UI elements are retained even in deeply nested layouts.
- **INV-RSM-12**: The candidate action list MUST NEVER be empty. BACK and RESTART are synthetic actions injected into the Tier 4 unified queue alongside widget actions, using their own base scores (NOT scored by the 10 widget scorers — see Ten Weighted Scorers section). Saturated widget actions remain in the list with reduced scores (via GradualDecayScorer) — they are deprioritized, never removed. System elements receive a -5000 penalty but stay in the list. `ActionSelector.selectAction()` MUST NEVER return null. When all widget scores fall below BACK's score, BACK wins naturally. When consecutive BACKs fail to change state, BACK's effective score decreases dynamically (`back_score -= back_decay_per_repeat`, default 200 per consecutive no-effect BACK), making saturated widget actions and eventually RESTART more attractive. This self-correcting mechanism prevents BACK/RESTART infinite loops without special-case escape logic.
- **INV-RSM-13**: `HeapMonitor` MUST check `Runtime.freeMemory()` every 100 iterations and increase `throttle_ms` by 50% when free memory falls below 10% of max heap (critical threshold). Warning threshold at 20%. If pressure persists for 3 consecutive checks, reduce `MAX_ITEMS` cap to 1000 temporarily. This prevents OOM on long runs with large UI trees.

## ADDED Requirements

### Requirement: Bootstrap via app_process

rvsmart SHALL bootstrap by connecting to Android system services via `ServiceManager.getService()` using reflection. The bootstrap sequence is: (1) parse CLI arguments, (2) assert API level (warn if `Build.VERSION.SDK_INT != 29`), (3) connect to `ActivityManagerService`, `WindowManagerService`, and `InputManager` via ServiceManager, (4) register `ActivityController` for crash/ANR interception, (5) load `static_analysis.json` if provided (otherwise null), (6) load `config.properties` if provided (otherwise defaults), (7) start `LogcatReader` daemon thread (uses `ConcurrentLinkedQueue<String>` for thread-safe producer-consumer between the reader thread and the main loop's `drainCoverageTags()` call), (8) start target app via `IActivityManager.startActivity()` (validates that `forceStopPackage()` and `startActivity()` work with Shell UID 2000 during PoC), (9) enter main loop.

If any ServiceManager connection fails, the agent SHALL log the error to stderr and exit with code 1. This is the Go/No-Go gate — if fundamental APIs are not accessible on the target emulator image, the agent cannot function.

#### Scenario: Successful bootstrap on API 29 emulator
- **WHEN** rvsmart.jar is executed via `app_process` on an API 29 emulator with `--package br.unb.cic.cryptoapp --timeout 60`
- **THEN** Main SHALL connect to ActivityManagerService, WindowManagerService, and InputManager
- **AND** CrashInterceptor SHALL register ActivityController callback
- **AND** the target app SHALL be launched via `IActivityManager.startActivity()`
- **AND** the main loop SHALL begin execution

#### Scenario: Bootstrap with static analysis data
- **WHEN** rvsmart is started with `--static-data /data/local/tmp/static_analysis.json`
- **THEN** StaticMap SHALL load and parse the JSON file
- **AND** MopScorer and WtgScorer SHALL be activated with the loaded data

#### Scenario: Bootstrap without static analysis data
- **WHEN** rvsmart is started without `--static-data`
- **THEN** StaticMap SHALL be null
- **AND** MopScorer and WtgScorer SHALL return 0 for all actions
- **AND** the agent SHALL operate in heuristic mode

#### Scenario: Bootstrap failure on unsupported API level
- **WHEN** `ServiceManager.getService("activity")` returns null or reflection fails
- **THEN** Main SHALL log "Bootstrap failed: cannot connect to ActivityManagerService" to stderr
- **AND** Main SHALL exit with code 1

### Requirement: UI Capture via AccessibilityNodeInfo

rvsmart SHALL capture the current UI state by obtaining the root `AccessibilityNodeInfo` node and traversing the tree via BFS. Each node is parsed into a `ScreenItem` with the following field mapping from `AccessibilityNodeInfo` methods:

| ScreenItem field | AccessibilityNodeInfo method | Hash field? | Notes |
|---|---|---|---|
| `className` | `getClassName()` | Yes (`class`) | Simple class name (e.g., `Button`), stripped from fully-qualified |
| `resourceId` | `getViewIdResourceName()` | Yes (`resource_id`) | Format varies: `package:id/name` or `id/name`. Normalize by taking substring after last `/` if no `:`, or keep full string. Must match Python agent's `resource_id` field from UIAutomator2 XML. Validated in PoC Task 2.8. |
| `text` | `getText()` | No | Used for SET_TEXT, not in hash |
| `contentDescription` | `getContentDescription()` | No | |
| `bounds` | `getBoundsInScreen(Rect)` | No | Used for click coordinates |
| `package` | `getPackageName()` | Yes | Used by SystemElementFilter |
| `clickable` | `isClickable()` | Yes | |
| `scrollable` | `isScrollable()` | Yes | |
| `checkable` | `isCheckable()` | Yes | |
| `enabled` | `isEnabled()` | Yes | |
| `longClickable` | `isLongClickable()` | Yes (`long_clickable`) | |
| `editable` | `isEditable()` | Yes | |
| `parentIndex` | BFS traversal index of parent | No | For tree reconstruction |

The traversal MUST recycle every node after extraction (INV-RSM-02) and MUST cap at `MAX_ITEMS` nodes (INV-RSM-11).

The resulting `ScreenState` contains the list of `ScreenItem` objects, the current Activity name (from `IActivityManager.getRunningTasks(1)`), and a structural hash computed per INV-RSM-03.

#### Scenario: Normal UI capture
- **WHEN** the target app displays a screen with 45 UI elements
- **THEN** `UiCapture.captureScreen()` SHALL return a `ScreenState` with 45 items
- **AND** each `AccessibilityNodeInfo` SHALL be recycled after parsing
- **AND** the structural hash SHALL match the Python agent's hash for the same UI tree
- **AND** latency SHALL be <10ms

#### Scenario: UI capture on pathological UI tree
- **WHEN** the UI tree contains more than 2000 nodes
- **THEN** `UiCapture` SHALL traverse all nodes via BFS but retain only the top 2000 by priority (interactive widgets first, then by shallower depth)
- **AND** remaining nodes SHALL be discarded with a log warning including the total node count

#### Scenario: UI capture returns null root
- **WHEN** `getRootInActiveWindow()` returns null
- **THEN** the agent SHALL check if the target app process is alive via `getRunningTasks()`
- **AND** if the app process is gone, the agent SHALL log a native crash and restart the app
- **AND** if the app process is alive, the agent SHALL wait one cycle (possible ANR)

### Requirement: Event Injection via InputManager

rvsmart SHALL inject touch and key events using `InputManager.injectInputEvent()` via reflection. Supported action types: CLICK, LONG_CLICK, SET_TEXT, SCROLL, SWIPE, BACK, KEY_EVENT, RESTART. Each action carries device pixel coordinates (x, y), optional text (for SET_TEXT), and a source field ("algorithm" or "llm") that is metadata only — the injection path is identical regardless of source (INV-RSM-08).

#### Scenario: Click injection
- **WHEN** the strategy selects a CLICK action at coordinates (540, 960) on a 1080x1920 display
- **THEN** `InputInjector` SHALL create a `MotionEvent` (ACTION_DOWN + ACTION_UP) at (540, 960)
- **AND** `InputManager.injectInputEvent()` SHALL be called with `INJECT_INPUT_EVENT_MODE_ASYNC`
- **AND** latency SHALL be <3ms

#### Scenario: SET_TEXT injection
- **WHEN** the strategy selects a SET_TEXT action with text "test@email.com" on an editable field
- **THEN** `InputInjector` SHALL focus the target field (CLICK), clear existing text, then inject key events for each character

### Requirement: Main Loop and Multi-Attempt Cycles

The main loop SHALL execute iterations until the configured timeout expires (INV-RSM-01). Each iteration follows the sequence: capture UI → update graph → check system dialog → drain logcat coverage → decide route (algorithm or LLM) → pre-mark action → execute → verify effect → multi-attempt if no effect → learn → throttle.

When an action has no effect (screen hash unchanged, same activity, same focused resource), the agent SHALL retry with the next best action from the strategy, up to `MAX_RETRIES_PER_CYCLE` times. This multi-attempt mechanism only applies to algorithm actions — LLM actions are expensive and SHALL NOT be retried. Actions with ≥3 consecutive failures on the same screen SHALL be skipped by `selectNextBest()` (INV-RSM-07).

`selectNextBest()` is a method on `ActionSelector` that returns the next-highest-scoring action from the current Tier 4 unified queue, excluding: (a) the action that just failed, and (b) actions with ≥3 consecutive failures on the current screen. It does NOT re-evaluate tiers — it operates within the already-computed Tier 4 ranked list. If the ranked list is exhausted within the cycle, the multi-attempt loop ends.

The `actionHadEffect` check uses a compound criterion: hash change OR activity change OR focused resource change. This catches SET_TEXT effects (text excluded from hash for EditText) and activity transitions that preserve widget structure.

#### Scenario: Normal iteration with effective action
- **WHEN** the agent is on screen with hash "a1b2c3" and selects a CLICK action
- **THEN** the action SHALL be pre-marked in the graph
- **AND** `InputInjector.inject()` SHALL execute the action
- **AND** post-execution UI capture SHALL detect hash "d4e5f6" (different)
- **AND** `Learner.update()` SHALL record the transition with `actionHadEffect=true`

#### Scenario: Multi-attempt on no-effect action
- **WHEN** an algorithm action has no effect (same hash, same activity, same focus)
- **THEN** the agent SHALL call `strategy.selectNextBest()` for an alternative action
- **AND** the alternative SHALL be executed and verified in the same cycle
- **AND** this SHALL repeat up to `MAX_RETRIES_PER_CYCLE` (default 3) times
- **AND** each no-effect action SHALL be recorded via `graph.recordActionFailure()`

#### Scenario: Multi-attempt exhaustion
- **WHEN** all `MAX_RETRIES_PER_CYCLE` retries produce no effect
- **THEN** the agent SHALL proceed to the learn phase with `actionHadEffect=false`
- **AND** StuckDetector SHALL evaluate whether escalation (BACK or RESTART) is needed

#### Scenario: LLM action not retried
- **WHEN** an LLM-sourced action has no effect
- **THEN** the agent SHALL NOT retry with multi-attempt
- **AND** the agent SHALL proceed directly to the learn phase

### Requirement: Tiered Action Selection (4 Tiers)

rvsmart SHALL implement a tiered action selection based on the Python RVAgentStrategy's 5-tier design, with one key improvement: **BACK and RESTART are synthetic actions in the same priority queue as widget actions in Tier 4** (INV-RSM-12), eliminating the need for a separate Tier 5 fallback. The candidate list is NEVER empty — saturated actions remain with reduced scores, system elements remain with heavy penalty, and BACK/RESTART always participate in Tier 4 scoring.

The class is named `ActionSelector` (not `ActionSelector`) because the implementation uses 4 tiers. The Python agent's `RVAgentStrategy` uses 5 tiers; rvsmart's redesign merges Tiers 4+5 into a unified queue.

| Tier | Name | Condition | Action |
|------|------|-----------|--------|
| 1 | PathBuffer | Buffer non-empty | Dispense one buffered action |
| 2 | Untested Actions | Has untested actions on current screen | Select untested action |
| 3 | Proactive Backtrack | Saturation ≥ threshold (default 0.8) | Plan BACK sequence via BFS to unsaturated ancestor |
| 4 | Unified Queue | All tested (including saturated), or no path found in Tier 3 | Select action with highest score from unified queue (widgets + BACK + RESTART) |

**Unified priority queue (Tier 4)**: All candidate actions — widget actions (even saturated), BACK (synthetic), and RESTART (synthetic) — compete in a single sorted list. Widget actions and synthetic actions use DIFFERENT scoring paths:
- **Widget actions**: scored by the 10 scorers. Saturated actions get low scores from GradualDecayScorer (decays to 0 after min_visits) and VisitationPenaltyScorer, but remain in the queue.
- **BACK** (synthetic): uses ONLY its own base score `back_base_score` (default -100, configurable). Does NOT pass through the 10 widget scorers. Decreases by `back_decay_per_repeat` (default 200) for each consecutive no-effect BACK on the same screen.
- **RESTART** (synthetic): uses ONLY its own base score `restart_base_score` (default -500, configurable). Does NOT pass through the 10 widget scorers. RESTART is the least attractive option but always available.

This design ensures: (1) the list is never empty, (2) consecutive BACKs self-correct because BACK's score drops while widget scores stay stable, (3) RESTART is reached only when BACK has been exhausted, (4) all parameters are calibratable by Optuna.

Tier 4 uses score aggregation as sum of all scorer outputs (for widget actions) or base score (for synthetic actions). With probability `stochastic_probability` (default 0.15), the selection ignores scores and picks a random action from the queue — this matches the Python agent's stochastic selection mechanism (simple random threshold, not Gumbel-max). Deterministic selection picks the highest-scoring action.

#### Scenario: Tier 2 selects untested action
- **WHEN** the agent visits a screen with 8 clickable widgets, 3 already tested
- **THEN** ActionSelector SHALL select one of the 5 untested widgets
- **AND** the selected action SHALL be pre-marked before execution

#### Scenario: Tier 3 proactive backtrack
- **WHEN** the current screen has saturation ≥ 0.8 (80% of actions tested)
- **THEN** ActionSelector SHALL use BacktrackBfs to find an unsaturated ancestor
- **AND** a BACK sequence SHALL be buffered in PathBuffer
- **AND** Tier 1 SHALL dispense the first BACK action

#### Scenario: Tier 4 scored selection with saturated actions
- **WHEN** all widget actions on the current screen are tested (some saturated)
- **THEN** ActionSelector SHALL include all widget actions (even saturated), BACK, and RESTART in the unified queue
- **AND** aggregate scores from all 10 scorers SHALL be computed for widget actions
- **AND** BACK and RESTART SHALL use their base scores (adjusted for consecutive repeats)
- **AND** the action with the highest score SHALL be selected (with Gumbel-max noise if enabled)

#### Scenario: All widgets are system elements — BACK wins naturally (INV-RSM-12)
- **WHEN** all widget actions on the screen are system elements (score -5000 each)
- **THEN** BACK (base score -100) SHALL outscore all widget actions
- **AND** BACK SHALL be selected as the highest-scoring action
- **AND** RVTRACK:SELECT SHALL log tier=4 action=BACK reason=system_elements_only

#### Scenario: Consecutive BACKs self-correct (INV-RSM-12)
- **WHEN** BACK has been selected 3 consecutive times on the same screen with no state change
- **THEN** BACK's effective score SHALL be `back_base_score - (3 × back_decay_per_repeat)` = -100 - 600 = -700
- **AND** saturated widget actions (score ~-50 from decay + penalty) SHALL now outscore BACK
- **AND** the agent SHALL re-execute a saturated widget action instead of looping BACK
- **AND** RVTRACK:STRATEGY SHALL log reason=back_decay_widget_retry

#### Scenario: No interactive widgets on screen (INV-RSM-12)
- **WHEN** the UI tree has zero clickable, scrollable, checkable, or editable elements
- **THEN** the unified queue SHALL contain only BACK and RESTART
- **AND** BACK (score -100) SHALL outscore RESTART (score -500)
- **AND** if consecutive BACKs decay BACK below RESTART, RESTART SHALL be selected
- **AND** RVTRACK:STRATEGY SHALL log reason=no_widgets_restart

#### Scenario: Saturated with no path plan — scored selection continues (INV-RSM-12)
- **WHEN** Tier 3 fires (saturation >= threshold) but BacktrackBfs finds no unsaturated ancestor
- **THEN** ActionSelector SHALL fall through to Tier 4 (unified queue)
- **AND** saturated widget actions, BACK, and RESTART SHALL compete by score
- **AND** the highest-scoring candidate SHALL be selected
- **AND** RVTRACK:STRATEGY SHALL log tier=4 reason=saturated_no_path_scored

### Requirement: Ten Weighted Scorers

rvsmart SHALL implement 10 scorers, each returning an integer score for a candidate action. Scorers are grouped by data dependency:

**Always active (7 scorers):**
- `GradualDecayScorer`: `base × decay_rate^visits` (0 after min_visits). Defaults: base=200.0, rate=0.7, min_visits=5.
- `CoverageDensityScorer`: `weight × coverage_gap` (gap in [0.0, 1.0]; 0.5 for unknown destinations). Default weight=200.0.
- `SaturationScorer`: `bonus × (1.0 - saturation)`. Default bonus=100.0.
- `ComponentPriorityScorer`: scores based on Android widget class name (simple class name, not fully qualified). Two priority levels:
  - **High priority** (+50.0): Button, ImageButton, MaterialButton, FloatingActionButton, ExtendedFloatingActionButton, EditText, AutoCompleteTextView, MultiAutoCompleteTextView, TextInputEditText, Spinner, AppCompatSpinner, DrawerLayout, Tab, TabLayout, TabView, ActionBar$Tab, TabItem, BottomNavigationItemView, NavigationBarItemView, NavigationBarView, NavigationRailView, ActionMenuItemView, MenuItemView, OverflowMenuButton, Chip, LinearLayout.
  - **Medium priority** (+40.0): CheckBox, MaterialCheckBox, AppCompatCheckBox, Switch, SwitchCompat, SwitchMaterial, ToggleButton, AppCompatToggleButton, RadioButton, MaterialRadioButton, AppCompatRadioButton, SeekBar, AppCompatSeekBar, Slider, RangeSlider, RatingBar, ViewPager, RecyclerView, CheckedTextView, AppCompatCheckedTextView.
  - All other components: 0.0.
  - ComponentPriorityScorer applies ONLY to widget actions. BACK/RESTART synthetic actions do NOT pass through this scorer (see synthetic action scoring below).
- `StrengthScorer`: `weight × success_rate + reward_weight × cumulative_reward`. Default weight=50.0, reward_weight=1.0. Untested actions get success_rate=0.5.
- `SystemElementFilter`: -5000.0 for system UI elements (package `com.android.systemui` only — status bar, navigation bar). The `android` package is NOT penalized because system dialogs (permissions, crash alerts) from the `android` package are part of app flow and handled by `SystemDialogDetector` instead. Fixed value, not configurable.
- `VisitationPenaltyScorer`: `-factor × log(1 + visits)`. Default factor=15.0.

**Require static analysis (2 scorers, return 0 when StaticMap is null):**
- `MopScorer`: +500.0 for direct MOP-reaching (`directly_reaches_mop`), +300.0 for transitive MOP-reaching (`reaches_mop`). These are the production defaults — the Java implementation MUST use 500.0/300.0 as hardcoded defaults (matching the Python agent's config defaults in `agent_config.py`, not the lower class-level fallbacks).
- `WtgScorer`: +150.0 for WTG-guided transitions to unvisited screens. Same note: use 150.0 as Java default (Python config default).

**Requires logcat data (1 scorer, new for rvsmart — not present in Python agent, returns 0 when LogcatReader has no data):**
- `ConfirmedCoverageScorer`: +500 if action directly triggered new coverage (logcat RVSEC-COV tag within 2s of action execution), +200 if action's screen historically led to coverage events. This scorer is unique to rvsmart — the Python agent does not have real-time logcat access. The 9 other scorers are ported from the Python agent's `ActionRanker`.

**Synthetic action scoring (BACK and RESTART):**

BACK and RESTART are synthetic actions that do NOT pass through the 10 widget scorers above. They use only their own base scores, avoiding unintended interactions (e.g., ComponentPriorityScorer assigning +30 to BACK, or SystemElementFilter penalizing RESTART). In the Python agent, BACK/RESTART do pass through ComponentPriorityScorer (scores +30/+20) because they are in Tier 5 as a separate fallback. In rvsmart's unified Tier 4 queue, synthetic actions compete directly with widget actions, so their scores must be self-contained and independent of widget scorers.

- `BACK`: base score `back_base_score` (default -100). Decays by `back_decay_per_repeat` (default 200) for each consecutive no-effect BACK on the same screen hash. Resets when the screen hash changes (i.e., BACK had effect and navigated to a different screen, or a widget action changed the screen). If BACK navigates away and then the agent returns to the same screen, the decay counter for that screen hash is preserved (not reset). This makes BACK progressively less attractive when looping, naturally promoting re-execution of saturated widget actions.
- `RESTART`: base score `restart_base_score` (default -500). Static — always least attractive. Selected only when all widget actions and BACK have lower effective scores (extreme edge case).

All scorer weights and synthetic action scores are configurable via `rvsmart.properties` and calibratable by Optuna.

#### Scenario: Heuristic mode scoring (no static data, no logcat)
- **WHEN** StaticMap is null and LogcatReader has no RVSEC-COV data
- **THEN** MopScorer, WtgScorer, and ConfirmedCoverageScorer SHALL return 0
- **AND** the remaining 7 scorers SHALL produce non-zero scores
- **AND** action selection SHALL function using only heuristic scores

#### Scenario: Full mode scoring
- **WHEN** StaticMap is loaded and LogcatReader has RVSEC-COV data
- **THEN** all 10 scorers SHALL produce scores
- **AND** MopScorer SHALL return +500 for actions that directly reach a MOP method

### Requirement: Crash Detection and Recovery

rvsmart SHALL detect app crashes via two mechanisms:

1. **Java crash callback**: `ActivityController.appCrashed()` fires immediately with the exception and stack trace. The agent marks the preceding action as crash-causing, logs the crash info, and restarts the app via `IActivityManager.forceStopPackage()` + `startActivity()` (INV-RSM-06).

2. **Native crash detection**: At the start of each cycle, if `getRootInActiveWindow()` returns null, the agent checks `IActivityManager.getRunningTasks()`. If the target app process is gone, it is treated as a native crash (SIGSEGV, SIGABRT, OOM-killed). The agent logs the event, restarts the app, and continues.

#### Scenario: Java crash detection and recovery
- **WHEN** the target app throws an uncaught exception
- **THEN** `CrashInterceptor.appCrashed()` SHALL fire with the exception
- **AND** the preceding action SHALL be marked as crash-causing in the graph
- **AND** the app SHALL be restarted via forceStopPackage + startActivity (~50-100ms)
- **AND** the agent SHALL continue from the next iteration

#### Scenario: Native crash detection
- **WHEN** the UI tree root is null and `getRunningTasks()` shows the target app is gone
- **THEN** the agent SHALL log "Native crash detected: app process gone"
- **AND** the app SHALL be restarted
- **AND** the agent SHALL continue from the next iteration

### Requirement: System Dialog Handling

rvsmart SHALL detect and dismiss system dialogs (crash dialog, permission requests, battery optimization) at the start of each cycle, before action selection. Detection is by package name: `android`, `com.android.packageinstaller`, `com.google.android.packageinstaller`, `com.android.settings`. Dismissal clicks the appropriate button (OK, Allow, Deny depending on dialog type) and re-captures the UI in the same cycle. Zero iterations wasted.

#### Scenario: Crash dialog dismissal
- **WHEN** the current screen is a system dialog from package `android` with text "has stopped"
- **THEN** `SystemDialogDetector.isSystemDialog()` SHALL return true
- **AND** `SystemDialogDetector.dismiss()` SHALL click the "OK" button
- **AND** the agent SHALL re-capture the UI and continue the iteration

### Requirement: Stuck Detection and Recovery

rvsmart SHALL implement two-level stuck detection:

- **Level 1**: If the screen hash remains unchanged for `stuck_max_blocks` consecutive iterations (default 10), force a BACK action.
- **Level 2**: If Level 1 does not resolve the stuck state, use BFS on the `back_successors` graph to find the nearest unsaturated ancestor. If no unsaturated ancestor is found within `max_backtrack_hops`, force a RESTART via `IActivityManager.forceStopPackage()` + `startActivity()`.

#### Scenario: Level 1 stuck recovery
- **WHEN** the screen hash has been "a1b2c3" for 10 consecutive iterations
- **THEN** StuckDetector SHALL trigger Level 1 recovery
- **AND** the agent SHALL execute a BACK action

#### Scenario: Level 2 stuck recovery with restart
- **WHEN** Level 1 BACK does not change the screen AND BFS finds no unsaturated ancestor within 8 hops
- **THEN** StuckDetector SHALL trigger Level 2 recovery
- **AND** the agent SHALL restart the app via forceStopPackage + startActivity

### Requirement: Heap Monitoring and OOM Prevention

`HeapMonitor` SHALL monitor `Runtime.freeMemory()` every 100 iterations to prevent OOM crashes during long exploration runs. Two thresholds are defined: warning (freeMemory < 20% of max heap) and critical (freeMemory < 10% of max heap).

At the critical threshold, `HeapMonitor` increases `throttle_ms` by 50% to reduce allocation pressure. If memory pressure persists for 3 consecutive checks (300 iterations), `MAX_ITEMS` cap is temporarily reduced to 1000 to limit UI tree memory footprint. When free memory recovers above 20%, throttle and MAX_ITEMS return to their configured values.

#### Scenario: OOM prevention at critical threshold
- **WHEN** `Runtime.freeMemory()` falls below 10% of `Runtime.maxMemory()`
- **THEN** `HeapMonitor` SHALL increase `throttle_ms` by 50%
- **AND** log warning "Memory pressure detected: freeMemory=Xmb (Y%), increasing throttle to Zms"

#### Scenario: Sustained memory pressure
- **WHEN** free memory remains below 10% for 3 consecutive HeapMonitor checks (300 iterations)
- **THEN** `HeapMonitor` SHALL reduce `MAX_ITEMS` cap from 2000 to 1000
- **AND** log warning "Sustained memory pressure: reducing MAX_ITEMS to 1000"

#### Scenario: Memory recovery
- **WHEN** free memory recovers above 20% of `Runtime.maxMemory()`
- **THEN** `HeapMonitor` SHALL restore `throttle_ms` and `MAX_ITEMS` to their configured values
- **AND** log info "Memory pressure resolved, restoring defaults"

### Requirement: Routing Manager (LLM Hybrid)

In `multimode` or `llm_only` mode, `RoutingManager` SHALL decide per iteration whether to use the algorithm path or the LLM path. Three strategies are supported:

- `probabilistic` (default): Random threshold against `llm_probability` (default 0.05, configurable, calibratable). The conservative 5% default reflects that algorithm iterations are 10x faster — even at 5%, the LLM provides guidance on ~1 in 20 iterations without bottlenecking throughput. Optuna calibration will find the optimal value.
- `new_screen_only`: LLM only on first visit to a screen (`visitCount <= 1`).
- `stuck_only`: LLM only when StuckDetector fires.

In `pure_algorithm` mode, `shouldUseLlm()` always returns false. In `llm_only` mode, it always returns true (except when LlmCircuitBreaker is open).

The LLM path captures a screenshot via `SurfaceControl.screenshot()` (~20ms if available with Shell UID 2000). If `SurfaceControl` is not accessible (PoC Task 2.7 validates this), the fallback is `adb exec-out screencap -p` piped from the host via a helper thread (~100-200ms, acceptable because LLM inference dominates at ~1.5-3s). The screenshot is compressed to JPEG quality 80, resized to 1000px longest edge, sent with the UI element list to SGLang, the tool call response is parsed, and Qwen3-VL [0,1000) coordinates are denormalized to device pixels.

#### Scenario: Probabilistic routing in multimode
- **WHEN** mode is `multimode`, strategy is `probabilistic`, llm_probability is 0.05 (default)
- **THEN** ~5% of iterations SHALL use the LLM path
- **AND** ~95% SHALL use the algorithm path

#### Scenario: LLM circuit breaker trips
- **WHEN** 3 consecutive LLM calls fail (network error, timeout, or parse failure)
- **THEN** LlmCircuitBreaker SHALL open
- **AND** `shouldUseLlm()` SHALL return false for 60 seconds
- **AND** the agent SHALL fall back to algorithm path during the cooldown

### Requirement: Configurable Parameters via Properties

rvsmart SHALL load all configurable parameters from a `java.util.Properties` file specified via `--config`. When the file is absent, internal defaults SHALL be used. The file format is standard Java Properties (key=value, `#` comments).

Parameters are grouped into: execution (4: timeout, throttle_ms, max_retries_per_cycle, seed), routing (2: mode, llm_probability), scorer weights (13: mop_direct_score, mop_transitive_score, wtg_guided_score, gradual_decay_base, gradual_decay_rate, gradual_decay_min_visits, coverage_density_weight, saturation_bonus, component_high_priority, component_medium_priority, strength_weight, reward_score_weight, visitation_penalty_factor), synthetic actions (3: back_base_score, restart_base_score, back_decay_per_repeat), stochastic selection (2: stochastic_probability, stochastic_temperature), reward propagation (4: reward_gamma, reward_propagation_n, reward_mop_weight, max_cumulative_factor), successor tracker (3: max_re_enables, multi_value_saturation_threshold, ui_coverage_threshold), path buffer (4: path_buffer_strategy_priority, max_backtrack_hops, coverage_path_weight, mop_path_weight), stuck detection (3: stuck_max_blocks, max_backtrack_failures, backtrack_saturation_threshold), MOP navigation (3: mop_nav_weight, mop_max_input_variations, confirmed_coverage_window_s), LLM inference (7: llm_base_url, llm_model, llm_temperature, llm_top_p, llm_top_k, llm_max_tokens, llm_timeout_s), logcat (1: logcat_buffer_size). Total: ~49 parameters, ~40 calibratable by Optuna (excluding fixed infrastructure params like llm_base_url, llm_model, timeout, seed, mode).

#### Scenario: Custom scorer weights via config
- **WHEN** rvsmart.properties contains `mop_direct_score=800.0` and `gradual_decay_base=150.0`
- **THEN** MopScorer SHALL use 800.0 for direct MOP-reaching (instead of default 500.0)
- **AND** GradualDecayScorer SHALL use 150.0 as base (instead of default 200.0)

#### Scenario: Default parameters when no config file
- **WHEN** rvsmart is started without `--config`
- **THEN** all parameters SHALL use their internal defaults
- **AND** the agent SHALL function with the default configuration

### Requirement: Structured Decision Logging (RVTRACK)

rvsmart SHALL implement structured decision logging using the same `[RVTRACK:<CATEGORY>]` prefix convention as the Python RVAgent. This enables automated verification scripts, calibration analysis, and post-mortem debugging using the same tooling. Logs are written to Android logcat via `android.util.Log.i("RVSMART", message)`.

Categories (matching Python agent where applicable):

| Category | Description | Key Fields |
|----------|-------------|------------|
| PARSE | UI capture result | iter, activity, elements, hash, capture_ms |
| ROUTE | LLM/algorithm routing decision | iter, mode, path, reason |
| RANK | Top-N actions with scores | iter, top (top-5 action signatures with scores) |
| SELECT | Final action selection | iter, tier, action, coords, score |
| EXEC | Action executed | iter, action, coords, source, inject_ms |
| STATE | State/activity change | iter, changed, from_hash, to_hash, from_activity, to_activity |
| LEARN | Post-action learning | iter, reward, stuck_level, had_effect |
| STRATEGY | Tier selection reasoning | iter, tier, reason, untested_count, saturation |
| BACKTRACK | Backtrack events | iter, level, from_state, to_state, hops |
| REWARD | Reward propagation | iter, type, value, steps, gamma |
| COVERAGE | Confirmed coverage event | iter, method, source (logcat) |
| LLM | LLM call metrics | iter, tokens_in, tokens_out, time_ms, success |
| STUCK | Stuck detection/recovery | iter, level, hash, consecutive, action |
| CRASH | App crash detected | iter, type (java/native), action, restart_ms |
| OOM | Memory pressure event | iter, free_pct, throttle_ms, max_items |

Format: `[RVTRACK:<CATEGORY>] key1=value1 key2=value2 ...`

Aggregate counters SHALL be maintained for experiment-level metrics (same set as Python agent where applicable): backtrack_count, restart_count, multi_attempt_retries, system_dialogs_dismissed, crash_recoveries, stuck_level1_count, stuck_level2_count, circuit_breaker_trips, ooom_throttle_events. These counters are included in the `RVSMART_METRICS:` final report.

#### Scenario: Filtering RVTRACK logs from logcat
- **WHEN** an experiment completes with rvsmart
- **THEN** `adb logcat -s RVSMART | grep "RVTRACK:SELECT"` SHALL show all action selections
- **AND** `adb logcat -s RVSMART | grep "RVTRACK:"` SHALL show all tracked decisions
- **AND** automated scripts SHALL parse key=value pairs for metric extraction

#### Scenario: RVTRACK aggregate counters in final report
- **WHEN** the timeout expires
- **THEN** the `RVSMART_METRICS:` report SHALL include aggregate counters
- **AND** counter values SHALL match the count of corresponding RVTRACK log lines

### Requirement: Trace Output and Final Metrics Report

rvsmart SHALL write per-iteration trace data as JSON lines to stdout, captured by the rv-tools plugin into the task trace file. At timeout, rvsmart SHALL write a final metrics report as the last stdout line, prefixed with `RVSMART_METRICS:` (INV-RSM-10).

The metrics report contains 6 sections: `metadata` (tool, package, mode, timeout, timestamp), `exploration` (iterations, execution time, unique states, total transitions, throughput), `decisions` (total actions, LLM/algorithm counts, multi-attempt retries, forced backs, crashes, system dialogs), `ui_coverage` (unique activities, unique hashes, widgets discovered/interacted, coverage ratio), `confirmed_coverage` (enabled flag, unique methods, total events, MOP methods reached), `llm` (total calls, tokens in/out, total time, circuit breaker trips).

#### Scenario: Trace output during execution
- **WHEN** the agent completes iteration 42 at elapsed time 15.2s
- **THEN** stdout SHALL contain a JSON line: `{"iteration":42,"timestamp_ms":15230,"hash":"a1b2c3d4e5f6","activity":"MainActivity","action_type":"CLICK","action_source":"algorithm","action_had_effect":true,"retries":0,"unique_states":12,"elapsed_s":15.2}`

#### Scenario: Final metrics report at timeout
- **WHEN** the configured timeout expires after 4200 iterations
- **THEN** the last stdout line SHALL be prefixed with `RVSMART_METRICS:`
- **AND** the JSON payload SHALL contain all 6 sections with aggregated statistics

### Requirement: Reward Propagation

rvsmart SHALL implement N-step temporal difference reward propagation, matching the Python agent's `RewardPropagator`. When an action produces a meaningful outcome (new activity, new state, MOP coverage), a reward is propagated backward through the last N actions (default N=5) with discount factor gamma (default 0.8).

Reward types: `mop_reached` (5.0), `new_activity` (2.0), `new_state` (1.0), `form_fill` (0.0), `same_state` (-0.1). Cumulative reward per action is clamped at ±(`max_cumulative_factor` × `reward_mop_weight`).

When ConfirmedCoverageScorer detects actual coverage via logcat, `RewardPropagator.propagateConfirmedCoverage()` SHALL propagate a `mop_reached` reward for the coverage-triggering action and its predecessors.

#### Scenario: Reward propagation on new activity discovery
- **WHEN** an action causes a transition from MainActivity to SettingsActivity (new activity)
- **THEN** RewardPropagator SHALL assign reward 2.0 to the current action
- **AND** reward SHALL propagate backward: action[-1] gets 2.0×0.8=1.6, action[-2] gets 2.0×0.64=1.28, etc.

### Requirement: Successor Tracker

rvsmart SHALL implement the SuccessorTracker to solve the "combobox problem" — when navigating BACK from a child state reveals untested elements on the parent, the parent action that led to the child SHALL be re-enabled for re-execution. The tracker records `back_successors` (which screens are reachable by pressing BACK from the current screen) for BFS navigation planning.

Re-enablement is limited to `max_re_enables` (default 6) per action. Multi-value widgets (spinners, dropdowns) saturate after `multi_value_saturation_threshold` (default 4) executions.

#### Scenario: Parent re-enablement after BACK
- **WHEN** the agent presses BACK from ChildScreen to ParentScreen
- **AND** ParentScreen now shows an untested widget (coverage < `ui_coverage_threshold`)
- **THEN** SuccessorTracker SHALL re-enable the parent action that led to ChildScreen
- **AND** Tier 2 (untested actions) SHALL pick up the re-enabled action

### Requirement: Dynamic State Graph

rvsmart SHALL maintain a `DynamicStateGraph` using `HashMap<String, ScreenNode>` where keys are structural hashes. Each `ScreenNode` stores: visit count, executed actions (with success/failure counts), cumulative reward, and transitions to other states.

The graph supports: `recordVisit()`, `recordTransition()`, `recordAction()`, `recordActionFailure()`, `getVisitCount()`, `getSaturation()`. Actions are pre-marked before execution (crash safety — if the app crashes during execution, the graph still records that the action was attempted).

#### Scenario: Pre-mark for crash safety
- **WHEN** the strategy selects an action on screen "a1b2c3"
- **THEN** `graph.recordAction("a1b2c3", action.signature())` SHALL be called BEFORE execution
- **AND** if the app crashes during execution, the graph SHALL still contain the action record
