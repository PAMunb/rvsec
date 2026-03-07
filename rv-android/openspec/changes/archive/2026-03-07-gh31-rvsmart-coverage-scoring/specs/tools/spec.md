## Purpose

This delta spec extends the rvsmart section of the tools domain specification to document new behavioral contracts introduced by gh31: element-level UI coverage tracking, plateau detection, context-aware text input, WTG-based scoring with multi-hop BFS, saturation-based proactive backtrack, and scoring parameter tuning. These components make rvsmart's exploration decisions informed by per-screen coverage data and static analysis transitions — capabilities that the Python rvagent already implements and that APE and FastBot achieve through their own mechanisms (CEGAR abstraction and Q-value learning, respectively).

All changes are in the rvsmart Java codebase (`$RVSEC_HOME/rvsec/rvsec-android/rvsmart/`). The rvsmart-tool Python plugin is not modified. The additions below supplement the existing rvsmart specification added by gh29 — they do not replace any existing invariants or scenarios.

## Invariants

- **INV-RSM-20**: `UICoverageTracker` MUST track elements per screen using hybrid IDs: `"res:{resource_id}"` when the element has a non-empty `resourceId`, otherwise `"coords:{centerX},{centerY}"`. This avoids coordinate collision for overlapping widgets (e.g., Button containing ImageView) while handling elements without resource IDs. Each element MUST be associated with exactly one screen hash. The tracker MUST NOT duplicate element registrations across visits to the same screen — re-visiting a screen updates interaction counts but does not re-register already-known elements.

- **INV-RSM-21**: `UICoverageTracker.getCoverageGap(screenHash)` MUST return a value between 0.0 (all elements tested at least once) and 1.0 (no elements tested). If the screen hash is unknown, it MUST return 1.0 (fully unexplored). The value MUST be consistent with the actual interaction count: an element with interactionCount > 0 MUST be counted as tested.

- **INV-RSM-22**: `PlateauDetector` MUST use a sliding window of exactly 10 iterations. A plateau is detected WHEN the window contains zero new-state events AND zero new-MOP-coverage events. The plateau state MUST be cleared immediately when either a new state or new MOP coverage is observed.

- **INV-RSM-23**: During a detected plateau, `ActionSelector` MUST use a stochastic probability of 0.5 (instead of the default 0.15). When the plateau clears, the stochastic probability MUST revert to the configured default. The boost MUST NOT persist beyond one iteration after plateau clearance.

- **INV-RSM-24**: `InputValueGenerator` MUST select input values based on the widget's `hint`, `resource_id`, or `inputType` attributes. It MUST NOT use the same input value twice for the same element within a single exploration run. If all generated values have been used, it MUST cycle back to the first value.

- **INV-RSM-25**: `WtgScorer` MUST read the `transitions` section of the static analysis JSON (loaded by `StaticMap`). It MUST perform BFS of depth 3 on the transitions graph with diminishing boost: +200 for 1-hop transitions to unvisited activities, +100 for 2-hop transitions to unvisited activities, +50 for 3-hop transitions to unvisited activities or any-hop transitions to under-visited activities (visitCount < 3). If no static analysis data is available, `WtgScorer` MUST return 0 for all actions. `WtgScorer` MUST return 0 for SCROLL, BACK, RESTART, and SET_TEXT actions — WTG transitions only describe widget-triggered navigation.

- **INV-RSM-26**: Launcher packages (`com.android.launcher3`, `com.google.android.apps.nexuslauncher`, `com.android.launcher`) MUST trigger immediate app restart in the out-of-app handler, bypassing the tolerance counter. The tolerance counter MUST only apply to non-launcher external packages.

- **INV-RSM-27**: `ActionSelector.generateCandidateActions()` MUST exclude elements whose `packageName` matches `com.android.systemui`. Elements with null or empty `packageName` MUST NOT be excluded (they are framework widgets rendered by the app).

- **INV-RSM-28**: `ActionSelector` MUST trigger proactive backtrack (Tier 3) when `screenNode.getSaturationRate() >= 0.8`. The score-based threshold (`PROACTIVE_BACKTRACK_THRESHOLD`) SHALL NOT be used as the backtrack trigger. This is self-calibrating: it depends only on how many actions have been tried on the current screen, not on scorer weights.

## ADDED Requirements

### Requirement: Element-Level UI Coverage Tracking (FR18, NFR01)

RVSmart SHALL track UI element coverage at the per-screen, per-element level through `UICoverageTracker`. When the agent visits a screen, all interactive elements from the `UiCapture` result SHALL be registered with the tracker using hybrid IDs: `"res:{resource_id}"` when the element has a non-empty `resourceId`, otherwise `"coords:{centerX},{centerY}"`. After each action execution, the tracker SHALL record the interaction by incrementing the count for the targeted element.

The tracker provides two key capabilities to the exploration strategy:

1. **Coverage gap computation**: `getCoverageGap(screenHash)` returns the fraction of untested elements on a given screen, enabling `CoverageDensityScorer` to direct exploration toward screens with many untested elements. A screen with 20 elements where 5 have been tested has a coverage gap of 0.75.

2. **Element type tracking**: Each element's widget class (Button, EditText, ImageView, etc.) is recorded alongside its hybrid ID. This enables future per-type coverage statistics without a separate tracking mechanism.

The tracker is integrated into `AgentLoop`: elements are registered after `UiCapture.capture()`, and interactions are recorded after action execution. The tracker is NOT accessible from outside the agent — it is an internal decision-making component.

#### Scenario: Elements registered on first screen visit

- **WHEN** `AgentLoop` visits a screen with hash `"abc123def456"` for the first time
- **AND** `UiCapture.capture()` returns 15 interactive elements (8 Buttons, 4 EditTexts, 2 ImageViews, 1 CheckBox)
- **THEN** `UICoverageTracker.registerScreenElements("abc123def456", items)` SHALL register 15 elements
- **AND** each element SHALL have a hybrid ID: `"res:{resource_id}"` when resourceId is non-empty, otherwise `"coords:{centerX},{centerY}"`
- **AND** `getCoverageGap("abc123def456")` SHALL return 1.0 (no elements tested)

#### Scenario: Coverage gap decreases after interactions

- **WHEN** the agent has visited screen `"abc123def456"` which has 10 registered elements
- **AND** 3 elements have been interacted with (interactionCount > 0)
- **THEN** `getCoverageGap("abc123def456")` SHALL return 0.7

#### Scenario: Re-visiting a screen does not duplicate elements

- **WHEN** the agent visits screen `"abc123def456"` for the 3rd time
- **AND** the screen has the same 15 elements as the first visit
- **THEN** the element count for that screen SHALL remain 15 (not 45)
- **AND** interaction counts from previous visits SHALL be preserved

#### Scenario: CoverageDensityScorer uses real coverage data

- **WHEN** `CoverageDensityScorer.score(action, context)` is called
- **AND** `context.coverageGap` for the current screen is 0.8 (80% untested)
- **THEN** the scorer SHALL return `0.8 * weight` (where weight is configurable, default 100)
- **AND** actions on screens with lower coverage gap SHALL receive lower scores from this scorer

### Requirement: Plateau Detection and Adaptive Stochastic Boost (FR18, NFR01)

RVSmart SHALL detect exploration plateaus using a `PlateauDetector` with a sliding window of 10 iterations. A plateau occurs when the agent discovers no new screens AND triggers no new MOP coverage for 10 consecutive iterations — indicating the agent is stuck in a local optimum where deterministic action selection cycles through the same states.

When a plateau is detected, `ActionSelector` SHALL temporarily increase the stochastic selection probability from the configured default (0.15) to 0.5. This means 50% of actions during a plateau are selected with score-weighted randomness instead of the top-scored action, dramatically increasing the chance of escaping the local optimum. The probability reverts to the default as soon as a new state or new MOP coverage is observed.

The plateau detector is integrated into `AgentLoop`: after each iteration, the loop calls `plateauDetector.recordIteration(isNewState, hasNewMopCoverage)`. The detected plateau state is passed to `ActionSelector` via the scoring context.

#### Scenario: Plateau detected after 10 iterations without progress

- **WHEN** the agent completes 10 consecutive iterations
- **AND** none of those iterations discovered a new screen (all `afterHash` values were already in `DynamicStateGraph`)
- **AND** none of those iterations produced new MOP coverage from logcat
- **THEN** `PlateauDetector.isPlateauDetected()` SHALL return `true`
- **AND** `ActionSelector` SHALL use stochastic probability 0.5

#### Scenario: Plateau clears on new state discovery

- **WHEN** `PlateauDetector.isPlateauDetected()` returns `true`
- **AND** the agent discovers a new screen (hash not in `DynamicStateGraph`)
- **THEN** `PlateauDetector.isPlateauDetected()` SHALL return `false` on the next call
- **AND** `ActionSelector` SHALL revert to the configured stochastic probability (default 0.15)

#### Scenario: No plateau when progress is ongoing

- **WHEN** the agent discovers at least one new screen within any 10-iteration window
- **THEN** `PlateauDetector.isPlateauDetected()` SHALL return `false`

### Requirement: Context-Aware Text Input Generation (FR18)

RVSmart SHALL generate context-appropriate text input values using `InputValueGenerator` instead of the hardcoded string `"test"`. The generator SHALL examine the target widget's `hint`, `resource_id`, and `inputType` attributes to determine the appropriate input category, then select a value from a pre-defined list for that category.

Input categories and their value lists:

| Category | Detection Heuristic | Values |
|----------|-------------------|--------|
| Email | hint/resource_id contains "email" or "mail" | `"test@test.com"`, `"user@example.org"`, `"a@b.c"` |
| Password | hint/resource_id contains "password" or "pass" | `"Test1234!"`, `"password123"`, `"Aa1!aaaa"` |
| Number | inputType is `TYPE_CLASS_NUMBER` or hint contains "number", "amount", "age" | `"42"`, `"0"`, `"999"` |
| Phone | inputType is `TYPE_CLASS_PHONE` or hint contains "phone", "tel" | `"+5561999999999"`, `"123456789"` |
| URL | hint/resource_id contains "url" or "website" | `"https://example.com"`, `"http://test.org"` |
| Generic | No pattern matched | `"test"`, `""`, `"a very long text string for testing"`, `"12345"` |

The generator tracks which values have been used for each element (by hybrid ID) and rotates through the list to maximize input diversity.

#### Scenario: Email field detected by hint

- **WHEN** `InputValueGenerator.generateInput(item)` is called
- **AND** `item.getHint()` returns `"Enter your email"`
- **THEN** the generator SHALL return a value from the Email category (e.g., `"test@test.com"`)
- **AND** the value SHALL NOT be one already used for this element in this run

#### Scenario: Password field detected by resource ID

- **WHEN** `InputValueGenerator.generateInput(item)` is called
- **AND** `item.getResourceId()` returns `"com.example:id/password_input"`
- **THEN** the generator SHALL return a value from the Password category

#### Scenario: Generic fallback when no pattern matches

- **WHEN** `InputValueGenerator.generateInput(item)` is called
- **AND** `item.getHint()` is null, `item.getResourceId()` is `"com.example:id/field1"`, `item.getInputType()` is 0
- **THEN** the generator SHALL return a value from the Generic category

#### Scenario: Value rotation for repeated interactions

- **WHEN** the agent interacts with the same EditText element 4 times
- **AND** the element is categorized as Generic (4 values available)
- **THEN** the first 4 interactions SHALL use 4 different values
- **AND** the 5th interaction SHALL cycle back to the first value

### Requirement: WTG-Based Transition Scoring (FR18, NFR01)

`WtgScorer` SHALL use the `transitions` section of the static analysis JSON to boost actions that correspond to known window transitions leading to unvisited or under-visited activities. This enables the agent to prioritize actions that are statically known to navigate to unexplored parts of the application.

The `transitions` section of the JSON maps source activities to lists of `{target_activity, widget_event}` objects. `StaticMap` (fixed in gh30 task 0.3 to support activity-based queries) SHALL expose `getTransitions(activityName)` returning the list of known transitions from the given activity.

For each candidate CLICK or LONG_CLICK action, `WtgScorer` performs BFS of depth 3 on the transitions graph, matching the action's widget resource ID and event type (click, long_click) against known transitions. The score uses diminishing boost based on BFS hop depth:

- +200 if the action's widget matches a 1-hop transition to an unvisited activity (visit count 0)
- +100 if the action's widget matches a 1-hop transition to an activity that is 2-hops away from an unvisited activity
- +50 if the action's widget matches a 1-hop transition to an activity that is 3-hops away from an unvisited activity, OR any-hop transition to an under-visited activity (visit count < 3)
- 0 if no transition match found, no static data, or action type is SCROLL/BACK/RESTART/SET_TEXT

BFS tracks visited nodes to handle cycles in the transitions graph.

#### Scenario: 1-hop to unvisited activity (+200)

- **WHEN** `WtgScorer.score(action, context)` is called
- **AND** `context.currentActivity` is `"com.example.MainActivity"`
- **AND** `StaticMap.getTransitions("com.example.MainActivity")` returns `[{target: "com.example.SettingsActivity", widget: "btn_settings", event: "click"}]`
- **AND** the action's target widget has resource_id `"com.example:id/btn_settings"` and type CLICK
- **AND** `"com.example.SettingsActivity"` has visit count 0 in the graph
- **THEN** `WtgScorer` SHALL return 200

#### Scenario: 2-hop to unvisited activity (+100)

- **WHEN** `WtgScorer.score(action, context)` is called
- **AND** `context.currentActivity` is `"com.example.MainActivity"`
- **AND** the action's widget matches a transition to `"com.example.SettingsActivity"` (1-hop, already visited)
- **AND** `StaticMap.getTransitions("com.example.SettingsActivity")` contains a transition to `"com.example.DetailActivity"` (2-hop from current)
- **AND** `"com.example.DetailActivity"` has visit count 0 in the graph
- **THEN** `WtgScorer` SHALL return 100

#### Scenario: Under-visited activity (+50)

- **WHEN** the same conditions as the 1-hop scenario apply, but `"com.example.SettingsActivity"` has visit count 2 (under-visited, < 3)
- **THEN** `WtgScorer` SHALL return 50

#### Scenario: No static analysis data available

- **WHEN** `WtgScorer.score(action, context)` is called
- **AND** `StaticMap` has no data (rvsmart running in heuristic mode)
- **THEN** `WtgScorer` SHALL return 0

#### Scenario: Non-widget actions return 0

- **WHEN** `WtgScorer.score(action, context)` is called
- **AND** the action type is SCROLL, BACK, RESTART, or SET_TEXT
- **THEN** `WtgScorer` SHALL return 0 (WTG transitions only describe widget-triggered navigation)

### Requirement: Scoring Parameter Tuning (FR18)

RVSmart SHALL use updated default scoring parameters that improve action selection quality based on analysis from 5 independent LLMs and comparison with APE/FastBot behavior.

Changes from gh29 defaults:

| Parameter | Old Value | New Value | Rationale |
|-----------|-----------|-----------|-----------|
| BACK base score | -500 | -100 | At -500, BACK is 13x less attractive than average CLICK (~100), preventing voluntary backtracking |
| Proactive backtrack trigger | Score-based (`bestScore < 50`) | Saturation-based (`getSaturationRate() >= 0.8`) | Score-based threshold is fragile — adding/removing scorers shifts score range, requiring re-tuning. Saturation is self-calibrating: depends only on how many actions have been tried on the current screen |
| Stochastic selection | Uniform random | Softmax-weighted (temperature=50) | Uniform ignores scores entirely; softmax prefers higher-scored actions while maintaining exploration |
| maxRetriesPerCycle | 1 | 3 | Retry costs ~250ms vs ~500ms for a new cycle; more retries reduces wasted cycles |

The softmax-weighted stochastic selection computes `p(a) = exp(score(a) / temperature) / sum(exp(scores / temperature))` and samples from this distribution. Temperature=50 gives gentle preference to higher-scored actions. When all scores are equal, softmax degenerates to uniform random (same behavior as before).

#### Scenario: BACK action is selectable when forward options are poor

- **WHEN** the current screen has 5 candidate actions
- **AND** 4 CLICK actions have scores of 80, 70, 60, 50 (all tested, low priority)
- **AND** 1 BACK action has score -100 + context bonuses
- **THEN** BACK SHALL be selectable via stochastic selection with non-negligible probability
- **AND** BACK SHALL NOT be the top-scored action unless forward options score below -100

#### Scenario: Saturation-based proactive backtrack activates

- **WHEN** `screenNode.getSaturationRate()` returns 0.85 (85% of actions tried)
- **AND** the saturation threshold is 0.8
- **THEN** Tier 3 (proactive backtrack) SHALL activate because 0.85 >= 0.8
- **AND** the agent SHALL attempt to backtrack to a screen with lower saturation and untested actions

#### Scenario: Softmax-weighted selection preserves exploration

- **WHEN** stochastic selection triggers (15% probability, or 50% during plateau)
- **AND** candidate actions have scores [300, 200, 100, 50]
- **THEN** the selection SHALL use softmax with temperature=50
- **AND** the action with score 300 SHALL have the highest selection probability
- **AND** the action with score 50 SHALL have non-zero selection probability

### Requirement: Time-Based Stuck Detection (FR18)

RVSmart SHALL detect stuck states using both iteration count and wall-clock time. The existing `StuckDetector` uses consecutive unchanged screen hashes to detect stuck states. This change adds a secondary time-based trigger: if no new screen has been discovered for 30 seconds of wall-clock time (regardless of iteration count), the agent SHALL trigger stuck recovery.

Time-based detection addresses a gap in the current design where slow iterations (LLM calls, long adaptive waits) reduce the iteration count but not the actual time spent stuck. An agent stuck for 30 seconds in LLM mode may have only completed 3 iterations (below the iteration threshold) while an agent in pure_algorithm mode would have completed 30+ iterations.

#### Scenario: Time-based stuck detection triggers

- **WHEN** the agent has been executing for 30 seconds since the last new screen discovery
- **AND** the iteration-based stuck detector has NOT triggered (fewer than `stuckMaxBlocks` consecutive unchanged hashes)
- **THEN** the time-based stuck detection SHALL trigger recovery
- **AND** the recovery mechanism SHALL be the same as iteration-based stuck recovery

#### Scenario: Time-based threshold resets on new screen

- **WHEN** the agent discovers a new screen (hash not previously in `DynamicStateGraph`)
- **THEN** the time-based stuck timer SHALL reset to 0

### Requirement: Element-Level Package Filtering (FR18)

> **Note**: Launcher fast-path (INV-RSM-26) is implemented by gh30-rvsmart-bugs-speed. PackageDetector was dropped — superseded by `--code-package` passed from rv-android's `App.code_package` (gh30 task 0.3). A Java-side diagnostic detector is unnecessary since the researcher already knows the code_package from the Python side.

`ActionSelector.generateCandidateActions()` SHALL pre-filter elements whose `packageName` matches `com.android.systemui`. These are system UI elements (notification bar, status bar widgets) that appear within the app's foreground window but do not belong to the app under test. Elements with null or empty `packageName` SHALL NOT be filtered — they are framework widgets rendered by the app and may be interactive.

#### Scenario: System UI elements excluded from candidates

- **WHEN** `generateCandidateActions()` processes elements on a screen
- **AND** 2 elements have `packageName == "com.android.systemui"` (notification icons)
- **AND** 12 elements have `packageName == "com.example.app"` (app widgets)
- **AND** 3 elements have `packageName == null` (framework widgets)
- **THEN** the candidate list SHALL contain 15 actions (12 + 3), not 17
- **AND** the 2 system UI elements SHALL be excluded before scoring

### Requirement: LLM Coordinate Boundary Protection (FR18)

When executing LLM-generated actions in hybrid/multimode, `AgentLoop` SHALL validate that click coordinates are not in the status bar (top 5% of screen height) or navigation bar (bottom 6% of screen height). If the coordinates fall in these regions, the action SHALL be replaced with a BACK action. This prevents the LLM from accidentally tapping system UI elements that navigate away from the app.

#### Scenario: LLM tap in status bar rejected

- **WHEN** the agent executes an LLM-generated CLICK action
- **AND** the click y-coordinate is 40 (screen height 1920, top 5% = y < 96)
- **THEN** the CLICK SHALL be replaced with a BACK action
- **AND** RVTRACK SHALL log `llm_boundary_reject` with the original coordinates

#### Scenario: LLM tap in app area accepted

- **WHEN** the agent executes an LLM-generated CLICK action
- **AND** the click y-coordinate is 960 (middle of screen)
- **THEN** the CLICK SHALL be executed as-is
