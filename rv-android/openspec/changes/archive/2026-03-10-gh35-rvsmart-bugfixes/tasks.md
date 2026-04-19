# Tasks: gh35-rvsmart-bugfixes

<!-- =============================================================================
  ENVIRONMENT (required before any Maven command):
    source /etc/profile
  Sets RVSEC_HOME, ANDROID_HOME, JAVA_HOME, PATH (d8, mvn, adb).

  PATHS:
    Java source : $RVSEC_HOME/rvsec/rvsec-android/rvsmart/src/main/java/br/unb/cic/rvsmart/
    Java tests  : $RVSEC_HOME/rvsec/rvsec-android/rvsmart/src/test/java/br/unb/cic/rvsmart/
    Build root  : $RVSEC_HOME/rvsec/rvsec-android/rvsmart/
    JAR target  : $RVSEC_HOME/rv-android/modules/rvsmart-tool/src/rvsmart_tool/tools/rvsmart/rvsmart.jar
    Docker dir  : $RVSEC_HOME/rv-android/docker/
    Dockerfile  : $RVSEC_HOME/rv-android/docker/rvandroid/Dockerfile
    Backup dir  : $RVSEC_HOME/rv-android/backup/

  BUILD/TEST:
    source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test
    source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn install -DskipTests

  DOCKER:
    cd $RVSEC_HOME/rv-android/docker && docker compose -f docker-compose.yml build rvandroid
    Image: phtcosta/rvandroid:0.9.0

  TEST FRAMEWORK: JUnit 5 (Jupiter 5.10.2), Mockito 4.11.0, Maven Surefire 3.2.5
  CURRENT TESTS: 512 methods in 46 files

  SKILLS (Java): superpowers:test-driven-development, superpowers:verification-before-completion
  SKILLS (Python/rv-*): NOT used — rv-* skills are Python-only

  PARALLELISM CONSTRAINTS:
    ActionSelector.java: modified by Groups 1, 2, 3, 4, 6
    AgentLoop.java: modified by Groups 2, 3, 6
    These groups MUST be sequential to avoid edit conflicts.
    Only files with zero overlap are safe for parallel subagents.

  EXECUTION ORDER:
    Wave 1 (parallel subagents — zero file overlap):
      Subagent A: ContentNode.java (BUG-03, SAT-2) + ScreenItem.java (SAT-3)
      Subagent B: Group 5 (StaticMap, MopScorer, WtgScorer, InputValueGenerator, PromptBuilder)
      Subagent C: SystemDialogDetector.java (BUG-06) + InputInjector.java (CAP-8)
      Subagent D: CycleDetector.java (new file, BUG-02 partial)
    Wave 2 (sequential — shared ActionSelector + AgentLoop + PhaseController):
      ActionSelector.java: BUG-01 → GAP-3 → GAP-2 → GAP-1 → CAP-9/10/11
      PhaseController.java: BUG-05 → BUG-02/cycle
      AgentLoop.java: SAT-1 → BUG-02/cycle → CAP-1/4/6/8
      StuckDetector.java: BUG-04
    Wave 3: Group 7 (build + Docker + test 16 APKs)
============================================================================= -->

## 1. Critical Bug Fixes (Group A)

<!-- DISPATCH: ContentNode+ScreenItem in Wave 1 Subagent A; ActionSelector in Wave 2 -->
<!-- SKILL: superpowers:test-driven-development -->

> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

- [x] 1.1 **BUG-01**: Fix BACK permanently disabled — `strategy/ActionSelector.java`
  - Line 319: `hash` variable is `screen.getContentHash()` — identify all usages
  - Lines 325-326: Change `successorTracker.getParents(hash)` to `successorTracker.getParents(structHash)` in `selectNextBest()`
  - Lines 627-628: Same fix in `selectFromUnifiedQueue()`
  - Add `String structHash` parameter to `selectNextBest()` and `selectFromUnifiedQueue()` signatures
  - Update all call sites (lines ~306, ~611) to pass `screen.getStructHash()`
- [x] 1.2 **BUG-03**: Fix saturation returns 1.0 for empty screens — `graph/ContentNode.java`
  - Line 159-160: Change `if (totalActions == 0) return 1.0f` to `return 0.0f`
- [x] 1.3 **SAT-3**: Fix `isInteractive()` excludes longClickable — `core/ScreenItem.java`
  - Line 83-85: Add `|| longClickable` to `isInteractive()` return expression
- [x] 1.4 **Tests**: Add to existing test files (~4 tests):
  - `strategy/ActionSelectorTest.java`: verify `selectNextBest()` uses structHash for `getParents()` and BACK action appears when parent exists at structural level (~2 tests)
  - `graph/ContentNodeTest.java`: verify `getSaturationRate()` returns 0.0f when totalActions==0 (~1 test)
  - `core/ScreenItemTest.java`: verify `isInteractive()` returns true for longClickable-only items (~1 test)
- [x] 1.5 Run `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test` — all tests must pass

## 2. Cycle Detection & Recovery (Group B) — depends on Group 1

<!-- DISPATCH: CycleDetector (new file) in Wave 1 Subagent D; rest in Wave 2 -->
<!-- SKILL: superpowers:test-driven-development -->

> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

- [x] 2.1 **BUG-02**: Implement cycle detector — new file `recovery/CycleDetector.java`
  - Ring buffer of last 10 structHashes
  - Method `recordHash(String structHash)` + `isCycleDetected()` detecting period-2 to period-4 patterns
  - In `core/AgentLoop.java` main loop (around line 456-474), before action selection: call `cycleDetector.recordHash(structHash)` and if cycle detected, force RESTART or navigate to different cluster
- [x] 2.2 **BUG-02 (Phase)**: Prevent Phase 1 reset on cycle — `strategy/PhaseController.java`
  - In `onNewContentState()` (line 83-85): accept `boolean isCycleDetected` parameter. If cycle detected AND same structHash cluster, skip Phase 1 reset
- [x] 2.3 **BUG-04**: Improve stuck recovery — `recovery/StuckDetector.java`
  - Line 79-92: When BFS finds no unsaturated ancestor, before RESTART:
    - Try NavigationMap replay to nearest unsaturated structural cluster
    - Add `NavigationMap` as constructor dependency
    - Track RESTART-to-same-screen cycles: after 3 consecutive RESTARTs landing on same structHash, switch to exhaustive interaction mode (try all coordinates, different scroll directions)
- [x] 2.4 **GAP-1**: Wire `isClusterForced()` into ActionSelector — `strategy/ActionSelector.java` + `strategy/PhaseController.java`
  - Add `PhaseController` reference to `ActionSelector` (constructor injection or method parameter)
  - At top of `selectPhase1()` (line 214): if `phaseController.isClusterForced(structHash)`, delegate to `selectPhase2()` behavior (skip current cluster)
- [x] 2.5 **Tests**: Create + update test files (~10 tests):
  - Create `recovery/CycleDetectorTest.java`: period-2 detection, period-3 detection, period-4 detection, no false positive on non-repeating sequence, ring buffer overflow (>10 entries), reset after cycle break (~6 tests)
  - `strategy/PhaseControllerTest.java`: verify Phase 1 skip when cycle detected with same structHash (~2 tests)
  - `recovery/StuckDetectorTest.java`: verify NavigationMap replay attempted before RESTART; verify exhaustive mode after 3 RESTARTs to same screen (~2 tests)
- [x] 2.6 Run `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

## 3. Saturation & Tracking Fixes (Group C)

<!-- DISPATCH: ContentNode in Wave 1 Subagent A; AgentLoop+ActionSelector in Wave 2 -->
<!-- SKILL: superpowers:test-driven-development -->

> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

- [x] 3.1 **SAT-1**: Move `recordAction()` to after execution — `core/AgentLoop.java`
  - Line 477: Move `graph.recordAction(hash, action.signature(), action.getWidgetClass())` to AFTER `executeAction()` (after line 481)
  - Wrap execute+record in try-finally: record in `finally` block to preserve crash safety while ensuring failed injections don't inflate count
- [x] 3.2 **SAT-2 + GAP-4**: Factor success rate into saturation — `graph/ContentNode.java`
  - Line 143-153 (`isActionSaturated`): Change threshold logic:
    - 0 successes after N executions: saturate at `threshold / 2` (faster — action is likely ineffective)
    - >50% success rate: saturate at `threshold * 1.5` (slower — action is productive)
    - Otherwise: keep default threshold
  - Requires accessing success count — add `getSuccessCount(String signature)` method using `successCounts` map
- [x] 3.3 **GAP-3**: Improve failure filter — `strategy/ActionSelector.java`
  - Lines 224-237: Replace hardcoded `< 3` threshold with adaptive logic:
    - Use `getFailureCount()` (line 679-686) but fix rounding issue in success reconstruction
    - Threshold scales with iteration count: `min(3, max(1, totalIterations / 500))`
    - Or: only filter actions with 3+ consecutive failures (not cumulative)
- [x] 3.4 **Tests**: Add to existing test files (~5 tests):
  - `graph/ContentNodeTest.java`: verify adaptive threshold — 0 successes saturates at threshold/2, >50% success rate at threshold*1.5, default threshold otherwise (~3 tests)
  - `strategy/ActionSelectorTest.java`: verify adaptive failure filter — actions not filtered prematurely at low iteration count (~2 tests)
- [x] 3.5 Run `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

## 4. Phase & Dialog Fixes (Group D)

<!-- DISPATCH: SystemDialogDetector in Wave 1 Subagent C; PhaseController+ActionSelector in Wave 2 -->
<!-- SKILL: superpowers:test-driven-development -->

> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

- [x] 4.1 **BUG-05**: Limit Preference screen trapping — `strategy/PhaseController.java`
  - In `onNewContentState()`: accept activity name parameter
  - Detect preference/settings activities: check if activity name contains "Preference", "Setting", "Config", "About" (case-insensitive)
  - For preference activities: limit Phase 1 re-entries to 5 (vs 20 for normal activities in `isClusterForced`)
  - Update `core/AgentLoop.java` call site to pass activity name
- [x] 4.2 **BUG-06**: Expand system dialog detection — `device/SystemDialogDetector.java`
  - Lines 25-30: Add to SYSTEM_PACKAGES set:
    - `"com.android.permissioncontroller"`
    - `"com.google.android.permissioncontroller"`
    - `"com.android.systemui"` (for dialog-type overlays)
    - `"com.samsung.android.packageinstaller"` (Samsung devices)
    - `"com.android.providers.downloads.ui"`
    - `"com.google.android.gms"` (Google Play Services dialogs)
- [x] 4.3 **GAP-2**: Add random exploration in Phase 3 — `strategy/ActionSelector.java`
  - In `selectPhase3()` (lines 298-308): with 10% probability, query NavigationMap for a random outgoing edge from current structHash to a less-visited cluster
  - If edge found, return the corresponding action instead of stochastic widget selection
  - Requires NavigationMap reference (add as dependency)
- [x] 4.4 **Tests**: Add to existing test files (~5 tests):
  - `strategy/PhaseControllerTest.java`: verify preference activity detected by name patterns ("Preference", "Setting", "Config", "About"); verify re-entry limit is 5 for preferences vs 20 for normal (~2 tests)
  - `device/SystemDialogDetectorTest.java`: verify all 6 new packages detected as system dialogs (~2 tests)
  - `strategy/ActionSelectorTest.java`: verify Phase 3 random exploration triggers with NavigationMap edge (~1 test)
- [x] 4.5 Run `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

## 5. Static Analysis Enrichment (Group E)

<!-- DISPATCH: subagent — ALL 5 files are independent of other groups (zero file overlap).
     Safe for Wave 1 parallel (Subagent B). -->
<!-- SKILL: superpowers:test-driven-development -->

> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

- [x] 5.1 **SA-1 + SA-2**: Enrich StaticMap parsing — `staticdata/StaticMap.java`
  - Parse `windows[].widgets[]` array: extract `idName`, `type`, `listeners[].handler`, `listeners[].eventType`, `inputType`, `hint`
  - Cross-reference `listeners[].handler` with `reachability[].methods[]` to build per-widget MOP flags
  - Store in new map: `Map<String, Map<String, WidgetStaticData>> activityWidgets` (activity -> resourceId -> data)
  - Parse `transitions[].events[]`: extract `widgetId`, `widgetClass`, `handler`
  - Store in new map: `Map<String, Map<String, String>> widgetTransitions` (activity -> widgetResourceId -> targetActivity)
  - Create `WidgetStaticData` record/class: `resourceId`, `type`, `directMop`, `transitiveMop`, `inputType`, `hint`, `targetActivity`
- [x] 5.2 **SA-1**: Widget-level MOP scoring — `strategy/scorers/MopScorer.java`
  - Accept `StaticMap` enriched data
  - For each candidate action, match screen item's `resourceId` to `WidgetStaticData`
  - Widget with `directMop=true` handler: +500 (unchanged)
  - Widget with `transitiveMop=true` handler: +300 (unchanged)
  - Widget on MOP-reachable activity but without MOP handler: +100 (reduced from +500/+300)
  - Unmatched widgets (no resourceId match): fall back to activity-level scoring
- [x] 5.3 **SA-2**: Widget-level WTG targeting — `strategy/scorers/WtgScorer.java`
  - Accept widget-to-transition data from StaticMap
  - For CLICK/LONG_CLICK: match action's resourceId to `widgetTransitions`
  - Widget that directly triggers transition to unvisited activity: +300 (targeted boost)
  - Other CLICK/LONG_CLICK on same screen: +50 (reduced from +200)
  - Unmatched widgets: fall back to activity-level scoring
- [x] 5.4 **SA-3**: Static inputType fallback — `strategy/InputValueGenerator.java`
  - Accept `StaticMap` reference
  - When runtime `inputType == 0` (unset), look up `WidgetStaticData.inputType` by matching `resourceId`
  - Use static inputType for value generation heuristics
- [x] 5.5 **SA-4**: Handler-level LLM hints — `llm/PromptBuilder.java`
  - In V17 navigation hint section (line 236-239): when `WidgetStaticData` is available for an element, append handler info (e.g., "[triggers Cipher.init()]")
  - Accept `StaticMap` or `PromptContext` enrichment with per-widget MOP handlers
- [x] 5.6 **Tests**: Add to existing test files (~12 tests):
  - `staticdata/StaticMapTest.java`: verify widget-level parsing — idName, listeners, inputType, hint extracted; MOP cross-reference built correctly; transition events parsed into widgetTransitions map (~4 tests)
  - `strategy/scorers/MopScorerTest.java`: verify widget-level scoring — directMop widget gets +500, transitiveMop +300, same-activity-no-handler +100, unmatched falls back to activity-level (~3 tests)
  - `strategy/scorers/WtgScorerTest.java`: verify widget-level targeting — direct transition widget gets +300, same-screen widget +50, unmatched falls back to activity-level (~3 tests)
  - `strategy/InputValueGeneratorTest.java`: verify static inputType fallback when runtime inputType==0 and resourceId matches static data (~2 tests)
- [x] 5.7 Run `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

## 6. APE Capabilities — Low Risk (Group F) — Wave 2

<!-- DISPATCH: InputInjector in Wave 1 Subagent C; AgentLoop+ActionSelector in Wave 2 (after Groups 1-4) -->
<!-- SKILL: superpowers:test-driven-development -->

> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

- [x] 6.1 **CAP-1**: KEYCODE_MENU injection — `core/AgentLoop.java`
  - **THE dominant root cause**: affects ALL 7 worst apps in the comparison. Per-app evidence:
    - **episodes_12** (-33.65pp): 5 OptionsMenus, 4/8 activities only reachable via menu. "Add Show" is collapsed SearchView in OptionsMenu. The -33pp gap is NOT ViewPager — rvsmart never reaches ShowActivity where ViewPager lives.
    - **sandwichroulette_2** (-25.05pp): Legacy SDK 10 app, NO action bar. ALL 6 activities launched ONLY from KEYCODE_MENU. Zero navigation without menu.
    - **eduroamcat_59** (-25.96pp): 7 OptionsMenu items ALL `showAsAction="never"`. Gap is method coverage from menu handlers triggering crypto code paths.
    - **simpledilbert_40** (-20.90pp): 7 OptionsMenu items defined ONLY programmatically (no XML). Zero menu XML files — all created in Java code.
    - **insteadlauncher_80601** (-26.13pp): Overflow menu items trigger deeper code paths. Context menu on RecyclerView items.
    - **imagepipe_45** (-22.61pp): About/Licence screens in overflow menu. Image editing tools require loaded image first.
    - **fdroidclassic_1110** (-18.45pp): SearchView collapsed in toolbar, overflow menus in app detail screens.
  - Implementation:
    - In main iteration loop, after action selection but before execution:
    - With 2% probability (configurable via `Config.menuFuzzRate`, default 0.02), inject `KEYCODE_MENU` instead of selected action
    - Use `inputInjector.pressKeyCode(KeyEvent.KEYCODE_MENU)` (or equivalent `uiAutomation.injectInputEvent`)
    - After injection, re-capture UI tree — OptionsMenu items will appear as clickable elements in accessibility tree
    - Track menu injection count in trace for analysis
- [x] 6.2 **CAP-4**: Trivial state refresh — `core/AgentLoop.java`
  - After `UiCapture.capture(root)` (around line 392-395), if interactive element count < 3:
    - Wait 1000ms, re-capture (up to 3 retries)
    - If element count increases, use the new capture
    - Log retry count in trace
  - Addresses 9 APKs with 0 unique_states caused by splash/loading screens
- [x] 6.3 **CAP-6**: Periodic restart without stuck — `core/AgentLoop.java`
  - Add counter `iterationsSinceNewState` (reset on each new contentHash discovery)
  - When `iterationsSinceNewState >= 200` (configurable via `Config.periodicRestartThreshold`):
    - Force RESTART
    - Reset counter
    - Log as `"periodic_restart"` in trace
  - Distinct from StuckDetector: fires on monotonic exploration plateau, not on consecutive same-hash
- [x] 6.4 **CAP-8**: Fix scroll gesture too weak — `core/AgentLoop.java` + `device/InputInjector.java`
  - Current scroll displacement: 300px in 50ms. APE uses ~540px (to screen edge) in 200ms. rvsmart's short/fast swipe doesn't register on many widgets (ViewPager, RecyclerView with snap).
  - `core/AgentLoop.java` lines 801-815: increase scroll displacement from 300px to half-screen-width (query display metrics). This ensures gesture covers enough distance to trigger page changes in ViewPager and snap-scrolling RecyclerViews.
  - `device/InputInjector.java` line 36: change `SWIPE_STEP_DELAY_MS = 5` to `20`. This slows down the gesture from 50ms to 200ms total, matching APE's timing and giving the system enough time to register the swipe.
  - Note: rvsmart DOES generate SCROLL left/right for scrollable elements (ViewPager reports `isScrollable()==true`). The problem is gesture strength, not action generation.
- [x] 6.5 **CAP-9**: Generate actions for focusable-but-not-clickable widgets — `strategy/ActionSelector.java`
  - Affected widgets (from layout analysis of 100 test apps):
    - **SeekBar**: 93 layouts. `focusable=true`, `clickable=false` by default. rvsmart generates 0 actions. Fix: generate CLICK at widget center (positions the thumb).
    - **RatingBar**: 24 layouts. `focusable=true`, `clickable=false` by default. Fix: generate CLICK at center.
  - In action generation logic: when a widget is focusable but not clickable AND its class is SeekBar or RatingBar (or subclass), generate a CLICK action at the widget's center coordinates.
  - This recovers interactions with volume controls, brightness sliders, star ratings, etc.
- [x] 6.6 **CAP-10**: Generate swipe-down for SwipeRefreshLayout — `strategy/ActionSelector.java`
  - SwipeRefreshLayout: 115 layouts in test apps. Not clickable, not scrollable in accessibility tree. Needs swipe-down gesture to trigger refresh.
  - In action generation logic: when a widget's class is SwipeRefreshLayout (or subclass), generate a SCROLL_DOWN action at the top of the widget bounds.
  - This triggers pull-to-refresh, which can load new content and reveal new screens.
- [x] 6.7 **CAP-11**: Generate edge swipe for DrawerLayout — `strategy/ActionSelector.java`
  - DrawerLayout: 116 layouts in test apps. Not clickable, not scrollable. Needs edge swipe from left screen edge to open navigation drawer.
  - In action generation logic: when a widget's class is DrawerLayout (or subclass), generate a SWIPE action from the left edge of the screen (x=0 or x=10) to the center (x=screen_width/2), at vertical center of the widget.
  - This opens the navigation drawer, revealing menu items that may lead to unexplored activities.
  - Note: WebView (61 layouts) is NOT addressed — internal HTML content is not exposed through accessibility tree. Marked as known limitation.
- [x] 6.8 **Tests**: Add to existing test files (~9 tests):
  - `core/AgentLoopTest.java`: verify KEYCODE_MENU injected at configured rate — mock random to force injection, verify `pressKeyCode(KEYCODE_MENU)` called (~2 tests); verify state refresh retries when <3 interactive elements (~1 test); verify periodic restart after `periodicRestartThreshold` iterations without new state (~1 test); verify scroll displacement uses half-screen-width instead of 300px (~1 test)
  - `strategy/ActionSelectorTest.java`: verify CLICK generated for focusable-but-not-clickable SeekBar and RatingBar widgets (~2 tests); verify SCROLL_DOWN generated for SwipeRefreshLayout at top of bounds (~1 test); verify edge swipe generated for DrawerLayout from left edge to center (~1 test)
- [x] 6.9 Run `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

### 6b. Always-Clickable Widget Alignment (CAP-12) — post-Wave 2

<!-- Discovered during implementation: rv-screen-parser has ALWAYS_CLICKABLE_TYPES (19 widget types)
     and a Spinner special case that rvsmart does not cover. The most impactful gap is Spinner,
     which explicitly reports clickable=false in UIAutomator dumps. Tab/BottomNav components
     usually report clickable=true so risk is lower, but added as safety net. -->

- [x] 6b.1 **CAP-12**: Force CLICK for always-clickable widget types — `strategy/ActionSelector.java`
  - Align with rv-screen-parser's `ALWAYS_CLICKABLE_TYPES` and Spinner special case
  - Add constant set `ALWAYS_CLICKABLE_WIDGETS` with types that may report `clickable=false` in UIAutomator:
    - **Spinner**, **AppCompatSpinner** — highest priority, explicitly documented as `clickable=false`
    - **TabLayout**, **TabView**, **ActionBar$Tab** — tab navigation
    - **BottomNavigationItemView**, **NavigationBarItemView** — bottom navigation
    - **Chip** — Material chip component
    - **FloatingActionButton** — FAB (may be focusable-only in some configurations)
  - In `generateCandidateActions()` special widget section: when widget class (simple name) is in `ALWAYS_CLICKABLE_WIDGETS` AND widget is not already clickable, generate CLICK at center
  - Distinct from CAP-9 (SeekBar/RatingBar are focusable-only; these are navigation/selection widgets)
- [x] 6b.2 **Tests**: Add to `strategy/ActionSelectorTest.java` (~3 tests):
  - Verify CLICK generated for Spinner with `clickable=false` (~1 test)
  - Verify CLICK generated for TabView with `clickable=false` (~1 test)
  - Verify no duplicate CLICK when widget already reports `clickable=true` (~1 test)
- [x] 6b.3 Run `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

### 6c. BACK Execution Fixes — post-experiment validation

<!-- Discovered in gh35 experiment: BACK actions are generated and ranked (BUG-01 fix works)
     but never executed due to two issues found in trace analysis (forced_backs=0 in all 16 APKs). -->

- [x] 6c.1 **BUG-01b**: Exempt BACK and RESTART from failure filter — `strategy/ActionSelector.java`
  - Line ~391-394: The filter `getFailureCount(node, a.signature()) < getFailureThreshold(...)` removes BACK after 3 executions without screen change
  - BACK on stuck screens (modals, overlays) counts as "failure" even though it's a valid recovery action
  - Fix: exempt `Action.Type.BACK` and `Action.Type.RESTART` from the failure filter — these system actions must always remain available as candidates
  - BACK score already decays via `backDecayCountPerHash` (line ~401-403), so over-BACK is already handled by scoring, not filtering
- [x] 6c.2 **BUG-01c**: Wire `recordForcedBack()` — `core/AgentLoop.java` + `output/MetricsCollector.java`
  - `MetricsCollector.recordForcedBack()` exists but is never called anywhere (dead code)
  - Wire it in `AgentLoop.java`: call `metricsCollector.recordForcedBack()` when a BACK action is executed (inside `executeAction()` switch case for BACK, or after execution when `action.getType() == BACK`)
  - This enables trace analysis to verify BACK is actually firing
- [x] 6c.3 **Tests**: Add to existing test files (~3 tests):
  - `strategy/ActionSelectorTest.java`: verify BACK not filtered by failure threshold — create node with BACK at 5 failures, confirm BACK still in candidates from `selectNextBest()` (~1 test)
  - `strategy/ActionSelectorTest.java`: verify RESTART not filtered by failure threshold (~1 test)
  - `strategy/ActionSelectorTest.java`: verify regular widget action IS filtered at failure threshold (~1 test)
- [x] 6c.4 Run `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

## 7. Verification (Group G) — Wave 3, after all groups

<!-- DISPATCH: orchestrator runs directly (sequential, after all groups complete) -->
<!-- SKILL: superpowers:verification-before-completion -->

- [x] 7.1 Build and deploy JAR:
  ```
  source /etc/profile
  cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart
  mvn install -DskipTests
  ```
  The `install` phase triggers maven-resources-plugin which copies the fat JAR to `$RVSEC_HOME/rv-android/modules/rvsmart-tool/src/rvsmart_tool/tools/rvsmart/rvsmart.jar`. Verify file exists and is recent.
- [x] 7.2 Run all unit tests:
  ```
  source /etc/profile
  cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart
  mvn test
  ```
  All tests must pass (512 existing + ~45 new ≈ 557 tests). Fix failures before proceeding.
- [x] 7.3 Rebuild Docker image:
  ```
  cd $RVSEC_HOME/rv-android/docker
  docker compose -f docker-compose.yml build rvandroid
  ```
  Image: `phtcosta/rvandroid:0.9.0`. Verify with `docker images | grep rvandroid`.
- [x] 7.4 Create `docker/docker-compose.test-gh35.yml`:
  - 8 services (`gh35_00` through `gh35_07`), each running 2 APKs
  - Base: extends rvandroid service from `docker-compose.rvsmart.yml`
  - Volumes: `../data/apks:/data/apks:ro`, `../data/results/gh35_XX:/results`
  - Environment: `TOOL=rvsmart:mvp`, `TIMEOUT=600`, `REPS=3`, `BATCH_FILE=/data/apks/gh35_batch_XX.txt`
  - Depends on: `sglang` service (from `docker-compose.rvsmart.yml`)
  - Resource limits: `cpus: 3`, `mem_limit: 12g` per container
- [x] 7.5 Create 8 batch files `data/apks/gh35_batch_00.txt` through `gh35_batch_07.txt`.
  Format: one APK filename per line (without path), 2 APKs per file.
  ```
  # gh35_batch_00.txt
  episodes_12.apk
  insteadlauncher_80601.apk
  ```
  Full list (16 worst vs APE):
  - Batch 00: episodes_12, insteadlauncher_80601
  - Batch 01: eduroamcat_59, sandwichroulette_2
  - Batch 02: imagepipe_45, sqliteviewer_1
  - Batch 03: simpledilbert_40, towercollector_2140302
  - Batch 04: fdroidclassic_1110, subsonic_59
  - Batch 05: mupen64plusae_246, gilga_11
  - Batch 06: quicknote_241, mosmetro_77
  - Batch 07: dashchan_1043, ultrasonic_129
- [x] 7.6 Run experiment:
  ```
  cd $RVSEC_HOME/rv-android
  docker compose -f docker/docker-compose.test-gh35.yml up -d
  watch -n 60 bash scripts/monitor_comparacao.sh data/results
  ```
- [ ] 7.7 Analyze results: compare method_cov, activity_cov, violations vs cmp01-cmp08 baseline
- [ ] 7.8 Verify BACK usage > 0 in majority of APKs (currently 1/100)
- [ ] 7.9 Verify no 100% RESTART APKs due to BUG-03
- [ ] 7.10 Verify cycle detection triggers in previously-affected APKs
- [ ] 7.11 Verify KEYCODE_MENU triggers OptionsMenu discovery in ≥2 APKs
- [ ] 7.12 Verify KEYCODE_MENU opens menus in sandwichroulette_2 (ALL 6 activities require menu — zero navigation without it)
- [ ] 7.13 Verify KEYCODE_MENU reaches "Add Show" in episodes_12 (collapsed SearchView in OptionsMenu)
- [ ] 7.14 Verify scroll gestures traverse ViewPager pages (displacement >= half-screen-width)
- [ ] 7.15 Verify SeekBar/RatingBar receive CLICK actions in apps with those widgets
- [ ] 7.16 Update `docs/20260310_comparacao_resultados.md` with gh35 results
