# Change Plan: gh35-rvsmart-bugfixes

**Date**: 2026-03-10
**Track**: Quick Path
**Priority**: High
**GitHub Issue**: [#35](https://github.com/PAMunb/rvsec/issues/35)
**PRD Reference**: FR18-FR20 (Tools)
**Domains**: tools (rvsmart Java agent)

## 1. Context

Deep trace analysis of the comparison experiment (100 APKs, 600s, 3 reps) revealed 17 issues in rvsmart's exploration algorithm that collectively explain the -4.39pp method coverage gap vs APE (p<0.001). The most critical: BACK is never executed (0/251k actions) due to a hash mismatch, 24.5% of iterations are wasted on ping-pong cycles, and static analysis data is parsed at activity-level when widget-level data is available.

All changes are in the rvsmart Java agent codebase at `$RVSEC_HOME/rvsec/rvsec-android/rvsmart/`. No Python changes. Build system: Maven (`pom.xml`). Test framework: JUnit 5 (Jupiter 5.10.2) + Mockito 4.11.0. Current test count: 512 methods in 46 files.

**Environment prerequisite**: `source /etc/profile` (sets `$RVSEC_HOME`, `JAVA_HOME`, `ANDROID_HOME`, `PATH`).

## 2. Scope

All paths relative to `$RVSEC_HOME/rvsec/rvsec-android/rvsmart/src/main/java/br/unb/cic/rvsmart/`. Tests under `$RVSEC_HOME/rvsec/rvsec-android/rvsmart/src/test/java/br/unb/cic/rvsmart/`.

**Group A — Critical Bug Fixes (BUG-01, BUG-03, SAT-3)**: Minimal line changes, highest ROI.
**Group B — Cycle Detection & Recovery (BUG-02, BUG-04, GAP-1)**: New cycle detector, improved stuck recovery.
**Group C — Saturation & Tracking (SAT-1, SAT-2, GAP-3, GAP-4)**: Fix action recording order and threshold logic.
**Group D — Phase & Dialog Fixes (BUG-05, BUG-06, GAP-2)**: Preference trapping, system dialog detection, random exploration.
**Group E — Static Analysis Enrichment (SA-1 to SA-4)**: Parse widget-level data from JSON, wire into scorers.
**Group F — APE Capabilities (KEYCODE_MENU, scroll gesture, widget gaps)**: KEYCODE_MENU injection, stronger scroll gestures, actions for missed widget types.
**Group G — Verification**: Build, Docker image, test on 16 worst APKs.

## 3. File Inventory

### Group A — Critical Bug Fixes

| File | Action | Detail |
|------|--------|--------|
| `strategy/ActionSelector.java:325-326` | Edit | BUG-01a: Change `getParents(hash)` to `getParents(structHash)` in `selectNextBest()`. Add `structHash` parameter. |
| `strategy/ActionSelector.java:627-628` | Edit | BUG-01b: Same fix in `selectFromUnifiedQueue()`. Pass structHash from caller. |
| `strategy/ActionSelector.java:306,611` | Edit | BUG-01: Update callers to pass `screen.getStructHash()` where contentHash was used. |
| `graph/ContentNode.java:159-160` | Edit | BUG-03: Change `if (totalActions == 0) return 1.0f` to `return 0.0f`. |
| `core/ScreenItem.java:83-85` | Edit | SAT-3: Add `|| longClickable` to `isInteractive()`. |

### Group B — Cycle Detection & Recovery

| File | Action | Detail |
|------|--------|--------|
| `core/AgentLoop.java:456-474` | Edit | BUG-02: Add cycle detector before action selection. Ring buffer of last 10 structHashes. Detect period-2 to period-4 patterns. When detected, force navigation to different cluster or RESTART. |
| `strategy/PhaseController.java:83-85` | Edit | BUG-02: In `onNewContentState()`, skip Phase 1 reset if cycle detected (same structHash oscillation). |
| `recovery/StuckDetector.java:79-92` | Edit | BUG-04: When BFS finds no unsaturated ancestor, try NavigationMap replay to known-unsaturated cluster before falling back to RESTART. Add NavigationMap dependency. |
| `strategy/ActionSelector.java:214-260` | Edit | GAP-1: At top of `selectPhase1()`, check `phaseController.isClusterForced(structHash)` — if true, delegate to Phase 2 behavior. Add PhaseController reference. |

### Group C — Saturation & Tracking

| File | Action | Detail |
|------|--------|--------|
| `core/AgentLoop.java:477,481` | Edit | SAT-1: Move `graph.recordAction()` to after `executeAction()`. Keep crash safety via try-finally. |
| `graph/ContentNode.java:143-153` | Edit | SAT-2 + GAP-4: Factor success rate into saturation. Action with 0 successes saturates at threshold/2. Action with >50% success rate gets threshold×1.5. |
| `strategy/ActionSelector.java:224-237` | Edit | GAP-3: Replace hardcoded 3-failure filter with time-decayed count. Failures older than N iterations count as 0.5. |

### Group D — Phase & Dialog Fixes

| File | Action | Detail |
|------|--------|--------|
| `strategy/PhaseController.java:83-85` | Edit | BUG-05: In `onNewContentState()`, detect Preference/Settings activities (check activity name) and skip phase reset or limit re-entries to 5. |
| `device/SystemDialogDetector.java:25-30` | Edit | BUG-06: Add packages: `com.android.permissioncontroller`, `com.google.android.permissioncontroller`, `com.android.systemui`, `com.samsung.android.packageinstaller`, `com.android.providers.downloads.ui`. |
| `strategy/ActionSelector.java:298-308` | Edit | GAP-2: In `selectPhase3()`, with 10% probability use NavigationMap random outgoing edge instead of pure stochastic widget selection. |

### Group E — Static Analysis Enrichment

| File | Action | Detail |
|------|--------|--------|
| `staticdata/StaticMap.java:81-154` | Edit | SA-1+SA-2: Parse `windows[].widgets[].listeners[].handler` and cross-reference with `reachability[].methods[].directlyReachesMop`. Store per-widget MOP flags. Parse `transitions[].events[].widgetId/widgetClass`. Store widget-to-transition mapping. Parse `windows[].widgets[].inputType` and `hint`. |
| `strategy/scorers/MopScorer.java:30-38` | Edit | SA-1: Use widget-level MOP data. Match screen items to static widgets by resourceId. Widget with direct MOP handler gets +500, others on same activity get +100 (reduced from +500). |
| `strategy/scorers/WtgScorer.java:49-61` | Edit | SA-2: Use widget-to-transition data. Boost specific widget that triggers transition to unvisited activity (+300), not all clicks equally. |
| `strategy/InputValueGenerator.java` | Edit | SA-3: When runtime inputType is 0, fall back to static inputType from StaticMap. |
| `llm/PromptBuilder.java:236-239` | Edit | SA-4: Enrich navigation hints with handler method names when available (e.g., "triggers Cipher.init()"). |

### Group G — Verification

| File | Action | Detail |
|------|--------|--------|
| `$RVSEC_HOME/rvsec/rvsec-android/rvsmart/pom.xml` | Build | `mvn install -DskipTests` — fat JAR + copy to rvsmart-tool |
| `$RVSEC_HOME/rv-android/docker/rvandroid/Dockerfile` | Build | `docker compose -f docker-compose.yml build rvandroid` → `phtcosta/rvandroid:0.9.0` |
| `$RVSEC_HOME/rv-android/docker/docker-compose.test-gh35.yml` | Create | 8 containers × 2 APKs, 600s, 3 reps, rvsmart:mvp + SGLang |

## 4. Execution Order

**Parallelism constraint**: ActionSelector.java is modified by Groups A, B, C, D, F. AgentLoop.java by Groups B, C, F. These MUST be sequential. Only files with zero overlap can run in truly parallel subagents.

```
WAVE 1 (parallel subagents — zero file overlap):
  Subagent 1: ContentNode.java (BUG-03, SAT-2) + ScreenItem.java (SAT-3) — 2 files
  Subagent 2: Group E (StaticMap, MopScorer, WtgScorer, InputValueGenerator, PromptBuilder) — 5 files
  Subagent 3: SystemDialogDetector.java (BUG-06) + InputInjector.java (CAP-8) — 2 files
  Subagent 4: CycleDetector.java (new file, BUG-02 partial) — 1 file

WAVE 2 (sequential — shared ActionSelector.java, AgentLoop.java, PhaseController.java):
  ActionSelector.java: BUG-01 → GAP-3 → GAP-2 → GAP-1 → CAP-9/10/11
  PhaseController.java: BUG-05 → BUG-02/cycle
  AgentLoop.java: SAT-1 → BUG-02/cycle → CAP-1/4/6/8
  StuckDetector.java: BUG-04

WAVE 3 (after all code):
  Group G (verification) — build JAR, Docker image, test 16 APKs
```

### Group F — APE Capabilities

| File | Action | Detail |
|------|--------|--------|
| `core/AgentLoop.java` | Edit | CAP-1: Inject KEYCODE_MENU with 2% probability. THE dominant root cause of the coverage gap — all 7 worst apps have activities/features reachable ONLY via OptionsMenu (see per-app evidence in tasks.md). |
| `core/AgentLoop.java` | Edit | CAP-4: Retry capture up to 3× when <3 interactive elements. |
| `core/AgentLoop.java` | Edit | CAP-6: Force RESTART at 200 iterations without new state. |
| `core/AgentLoop.java:801-815` | Edit | CAP-8: Fix scroll gesture too weak. Current: 300px in 50ms. APE uses ~540px in 200ms. Increase displacement to half-screen-width, duration to 200ms. |
| `device/InputInjector.java:36` | Edit | CAP-8: Change `SWIPE_STEP_DELAY_MS = 5` to `20` for scroll gestures. |
| `strategy/ActionSelector.java` | Edit | CAP-9: Generate CLICK at center for focusable-but-not-clickable widgets (SeekBar, RatingBar). These are focusable but NOT clickable by default — rvsmart generates 0 actions for them. |
| `strategy/ActionSelector.java` | Edit | CAP-10: Generate SCROLL_DOWN for SwipeRefreshLayout (not clickable/scrollable, needs swipe-down gesture at top of bounds). |
| `strategy/ActionSelector.java` | Edit | CAP-11: Generate edge swipe from left for DrawerLayout (not clickable/scrollable, needs edge swipe to open navigation drawer). |

## 5. Acceptance Criteria

- [ ] BACK action executed in >50% of APKs (currently 1/100)
- [ ] No APKs with 100% RESTART rate due to saturation bug
- [ ] Ping-pong cycles broken within 10 iterations
- [ ] MopScorer uses widget-level data (not activity-level)
- [ ] WtgScorer targets specific widgets for transitions
- [ ] KEYCODE_MENU triggers OptionsMenu in ≥2 APKs (critical: sandwichroulette, episodes)
- [ ] KEYCODE_MENU reaches previously-unreachable activities in apps with menu-only navigation
- [ ] Trivial state refresh recovers ≥3 APKs from 0-states
- [ ] Scroll gestures traverse ViewPager/RecyclerView (displacement >= half-screen-width, duration 200ms)
- [ ] SeekBar/RatingBar receive CLICK actions (focusable widgets no longer ignored)
- [ ] SwipeRefreshLayout triggers refresh via swipe-down gesture
- [ ] DrawerLayout opens via edge swipe from left
- [ ] Docker image built and tested on 16 worst APKs (2 per container)
- [ ] Method coverage gap vs APE reduced by ≥3pp on test set

## 6. Clarifications

### ViewPager is NOT a scroll-generation blindspot

Initial hypothesis was that rvsmart fails to generate SCROLL for ViewPager. This is **wrong** — ViewPager reports `isScrollable()==true` in the accessibility tree, and rvsmart correctly generates SCROLL left/right for scrollable elements. The actual problem is that the scroll gesture is too weak (300px/50ms vs APE's ~540px/200ms), causing swipes to not register. Fixed by CAP-8.

### KEYCODE_MENU is the dominant root cause for the 7 worst apps

The -33.65pp gap in episodes_12 is NOT caused by ViewPager (the app has one, but it's in ShowActivity which is never reached). The real cause: "Add Show" is behind a collapsed SearchView in the OptionsMenu, and 4/8 activities are only reachable via menu items. Same pattern in all 7 worst apps — activities/features behind OptionsMenu that rvsmart never opens.

### APE's patchGUITree() click propagation

APE propagates `clickable=true` from parent containers to child widgets (e.g., LinearLayout with onClick → children get clickable). This gives finer-grained exploration. rvsmart only clicks the container center. Noted as future enhancement (not in current scope).

### Saturation pre-recording confirmed

`recordAction()` IS called before `executeAction()` at AgentLoop.java:477. SAT-1 fix moves it to after execution.
