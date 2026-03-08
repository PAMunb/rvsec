# RVSmart Refactoring Plan: Surpassing APE and FastBot

**Date**: 2026-03-06
**Phase**: Phase 0 — Ideation (WORKFLOW.md Section 1)
**Author**: Pedro + Claude Code
**Status**: Ideation complete, ready for track selection

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Methodology](#2-methodology)
3. [Current State Assessment](#3-current-state-assessment)
4. [Gap Analysis: rvsmart vs rvagent](#4-gap-analysis-rvsmart-vs-rvagent)
5. [Gap Analysis: rvsmart vs APE/FastBot](#5-gap-analysis-rvsmart-vs-apefastbot)
6. [Consolidated Issues from LLM Analyses](#6-consolidated-issues-from-llm-analyses)
7. [Package Detection Deep Dive](#7-package-detection-deep-dive)
8. [Refactoring Plan](#8-refactoring-plan)
9. [Expected Impact](#9-expected-impact)
10. [Risks and Mitigations](#10-risks-and-mitigations)
11. [Next Steps: Track Selection](#11-next-steps-track-selection)

---

## 1. Executive Summary

RVSmart is a Java exploration agent running via `app_process` inside the Android emulator, achieving ~14 evt/s theoretical throughput — ~10x the Python rvagent. In an E2E validation on cryptoapp, rvsmart already beats APE on all metrics (Activities 100% vs 75%, Methods 34% vs 19%, MOP 43% vs 25%). However, this was on a single, small, well-structured app.

Analysis from 5 independent LLMs, comparison with the rvagent Python codebase, study of the SOTA (APE, FastBot2, Stoat, DroidBot, Humanoid, ComboDroid, LLMDroid, VLM-Fuzz, CovAgent, TOLLER), and insights from a prior experiment regeneration project reveal that rvsmart has **critical bugs that nullify its architectural advantages** and **missing features that the Python rvagent already implements well**.

This document is the Phase 0 ideation output for the rvsmart refactoring effort. It identifies 6 phases of work, prioritized by impact, that should bring rvsmart from "beats APE on cryptoapp" to "consistently beats APE and FastBot on diverse APK sets".

**Key insight**: rvsmart's speed advantage (app_process) is its main differentiator. But speed without exploration intelligence is wasted — the agent visits the same screens faster. The priority is to fix the broken scoring/saturation system, port the rvagent memory and coverage tracking features, and then exploit the speed advantage for deeper exploration.

---

## 2. Methodology

This analysis was conducted using 6 parallel research streams:

| Stream | Source | Key Contribution |
|--------|--------|------------------|
| **rvsmart Java source** | 40 Java files in `$RVSEC_HOME/rvsec-android/rvsmart/` | Current implementation state, bug identification |
| **rvagent Python source** | `modules/rv-agent/src/rv_agent/` | Feature gap analysis, best patterns to port |
| **rvsmart-tool plugin + specs** | `modules/rvsmart-tool/`, `openspec/changes/archived/20260305-gh29-rvsmart/` | Deferred features, known limitations, E2E results |
| **External docs** | `rvsec-regerar-resultados/docs/NOVO/` (01, 02, 06, 07) | Package detection, inner class normalization, experiment methodology |
| **5 LLM analyses** | `docs/analise_{claude,codex,gemini,minimax,qwen}.md` | Independent bug and improvement identification, consensus analysis |
| **SOTA research** | APE (ICSE 2019), FastBot2 (ASE 2022), LLMDroid (FSE 2025), VLM-Fuzz, CovAgent, TOLLER | Competitive benchmarks and advanced techniques |

---

## 3. Current State Assessment

### 3.1 Architecture Strengths

RVSmart has genuine architectural advantages over all competing tools:

1. **app_process execution**: Runs inside the emulator's VM, bypassing ADB latency entirely. Theoretical throughput ~14 evt/s vs ~2 evt/s for ADB-based tools (UIAutomator2, DroidBot).
2. **AccessibilityService direct access**: Gets UI tree instantly via `getRootInActiveWindow()`, no XML serialization/deserialization overhead.
3. **Instant crash detection**: `CrashInterceptor` callback detects Java crashes and ANR immediately, no polling.
4. **MOP-aware scoring**: `MopScorer` uses static analysis data to prioritize actions that reach monitored operations (+500 direct, +300 transitive).
5. **4-tier DFS strategy**: PathBuffer (Tier 1), untested actions (Tier 2), proactive backtrack (Tier 3), unified queue (Tier 4) — a sound exploration framework.

### 3.2 E2E Validation Results (rvsmart vs APE on cryptoapp)

| Metric | rvsmart | APE | Delta |
|--------|---------|-----|-------|
| Activities | **100%** | 75% | +25pp |
| Methods | **33.9%** | 18.6% | +15.3pp |
| MOP | **42.6%** | 24.6% | +18.0pp |
| Violations | **5** | 3 | +2 |

cryptoapp is a small app (4 Activities, well-structured JCA calls). These results are encouraging but not generalizable — rvsmart's bugs become apparent on larger, more complex apps.

### 3.3 Actual vs Theoretical Performance

| Metric | Theoretical | Actual (22 APKs) | Loss |
|--------|-------------|-------------------|------|
| Throughput | 14 evt/s | 1.1-4.1 evt/s | 70-92% |
| Scroll actions | Expected > 0% | 0% | 100% |
| Out-of-app time | 0% | 27-75% (4 APKs) | Critical |
| Stuck APKs | 0 | 3 (0-2 unique states) | Critical |

**Root cause**: Operational bugs consume the speed advantage. The agent visits fewer screens per minute than slower tools because it wastes cycles on broken scoring, missing scroll, and out-of-app navigation.

---

## 4. Gap Analysis: rvsmart vs rvagent

### 4.1 UI Coverage Tracking

| Aspect | rvagent (Python) | rvsmart (Java) | Gap |
|--------|------------------|----------------|-----|
| **Element-level tracking** | `UICoverageTracker`: tracks each element by coordinate ID (`"coords:540,340"`), records interaction count, first/last timestamp | `ScreenNode.executionCounts`: tracks actions by signature (`"click@540,960"`), counts executions | Partial — rvsmart tracks actions but not element identity across visits |
| **Per-screen element sets** | `screen_elements: Dict[str, Set[str]]` maps screen_hash to registered elements | Not present — ScreenNode knows totalActions but not which elements belong to which screen | **Missing** |
| **Coverage gap computation** | `get_coverage_gap(state_hash)` returns fraction of untested elements (0.0-1.0) | Not present — `getCoverage()` exists but `totalActions` is never initialized (Codex bug) | **Broken** |
| **Component type tracking** | `element_types: Dict[str, str]` maps element_id to class name; coverage stats by type | Not present | **Missing** |
| **Test count thresholds** | UNTESTED / TESTED-1x / WELL-TESTED (3+) categories | `isActionSaturated()` with threshold=2 (default) or 4 (multi-value widgets) | Partial — simpler but functional |
| **Discovery timeline** | Chronological log of when elements were first discovered | Not present | **Missing** |
| **Coverage suggestions** | `get_exploration_suggestions()` returns untested elements per screen, prioritized | Not present | **Missing** |

**Impact**: Without per-screen element tracking and coverage gap computation, rvsmart cannot direct exploration toward under-tested screens. The CoverageDensityScorer (excluded as "redundant") would be useful if coverage data were available.

### 4.2 Memory Systems

| Aspect | rvagent (Python) | rvsmart (Java) | Gap |
|--------|------------------|----------------|-----|
| **Short-term memory** | `ShortTermMemory`: sliding window of 10 iterations per screen, clears on activity change, formats context for LLM | Not present | **Missing** |
| **Long-term memory** | `LongTermMemory`: visit_count, success_rate, state_transitions per action; guidance generation | `Learner` tracks uniqueActivities, confirmedMethods; `DynamicStateGraph` tracks visits and transitions | Partial — graph tracks visits but no action-level success patterns |
| **Agent memory** | `AgentMemoryManager`: formatted summaries for LLM (action history, exploration summary, navigation path) | Not present | **Missing** (only relevant for LLM/hybrid mode) |
| **Memory coordinator** | `MemoryCoordinator`: synchronizes updates across all 5 memory components | Not present — AgentLoop updates components individually | **Missing** |
| **Plateau detection** | `PlateauDetector`: sliding window of 10 iterations, detects no-new-state AND no-new-MOP, boosts stochastic to 0.5 | `StuckDetector`: counts consecutive unchanged hashes, triggers recovery after `stuckMaxBlocks` | Partial — stuck detection exists but no plateau-adaptive stochastic boost |

**Impact**: The rvagent's layered memory system enables informed decisions — the agent knows which screens are under-explored, which actions tend to produce transitions, and when to change strategy. RVSmart explores more blindly.

### 4.3 Out-of-App Protection

| Aspect | rvagent (Python) | rvsmart (Java) | Gap |
|--------|------------------|----------------|-----|
| **Detection** | `current_package != target_package` from `device.app_current()` | `root.getPackageName() != packageName` from AccessibilityNodeInfo | Equivalent mechanism |
| **Tolerance** | 3 actions, with immediate restart for launcher packages | `config.getOutOfAppTolerance()` (configurable), no launcher fast-path | Partial — no launcher detection |
| **System dialog whitelist** | `SYSTEM_DIALOG_PACKAGES` (android, packageinstaller, permissioncontroller) are NOT treated as external | `SystemDialogDetector.isSystemDialog()` dismisses them but at the iteration level, not in out-of-app logic | Different but functional |
| **Boundary protection** | Validates LLM click coordinates are not in status bar (top 5%) or nav bar (bottom 6%) | Not present | **Missing** (relevant for LLM/hybrid mode) |
| **Element-level package filter** | Strategy filters UI elements by `item.view["package"] != target_package`, excluding system elements | Not present — all visible elements are candidates | **Missing** |

**Impact**: RVSmart has basic out-of-app protection (added in gh29 Group 20), but lacks element-level package filtering. This means the agent can click on system notification bar elements or status bar widgets that appear within the app's foreground window, wasting actions.

### 4.4 Package Detection

| Aspect | rvagent (Python) | rvsmart (Java) | Gap |
|--------|------------------|----------------|-----|
| **Package source** | `config.package_name` (CLI argument, typically manifest package) | `--package` CLI argument | Same |
| **Code package awareness** | No explicit handling — uses manifest package for all comparisons | No explicit handling | Same gap in both |
| **UI dump package info** | Each element has `item.view["package"]` from UIAutomator XML `package` attribute | `ScreenItem.getPackageName()` from `AccessibilityNodeInfo.getPackageName()` | Both have per-element package info |

**Key insight from external docs (07_pacotes.md)**: 27.5% of F-Droid APKs have a manifest package that does NOT match the code package (e.g., Godot games: manifest=`ir.hsn6.trans`, code=`org.godotengine.godot`). Another 25.2% have code distributed across multiple packages. Both tools are vulnerable to this issue, but rvsmart can potentially detect it at runtime by observing the `package` attribute on AccessibilityNodeInfo elements — if the majority of elements have a package different from the CLI `--package`, the agent could auto-correct.

---

## 5. Gap Analysis: rvsmart vs APE/FastBot

### 5.1 APE (ICSE 2019)

| Aspect | APE | rvsmart | Advantage |
|--------|-----|---------|-----------|
| **Model abstraction** | Dynamic CEGAR: decision tree that refines/coarsens on-the-fly based on runtime feedback | Fixed hash: SHA-256 of structural attributes (class, resource_id, clickable, etc.) | APE — adapts granularity to avoid both state explosion and under-differentiation |
| **Execution model** | `app_process` (same as rvsmart) | `app_process` | Tie |
| **Throughput** | ~10 evt/s | ~14 evt/s (theoretical), ~4 evt/s (actual) | rvsmart potential, APE actual |
| **Scroll handling** | First-class action in exploration | Not generated in ActionSelector | APE |
| **Connected subgraph exhaustion** | Exhaustively explores all actions in connected subgraph before moving | 4-tier DFS with saturation threshold | APE — more methodical |
| **Cross-run model reuse** | No | No | Tie |

**Key takeaway**: APE's CEGAR abstraction is its core innovation. RVSmart uses a fixed hashing scheme — if two screens differ only in text content, they are treated as the same screen. APE would distinguish them if text is relevant to navigation. Implementing adaptive abstraction is a Phase 5 goal.

### 5.2 FastBot2 (ASE 2022)

| Aspect | FastBot2 | rvsmart | Advantage |
|--------|----------|---------|-----------|
| **Exploration** | RL with Q-values, epsilon-greedy, N-step lookahead | 4-tier DFS with scorer chain | Different philosophies |
| **Model reuse** | Persists model to `/sdcard/fastbot_*.fbm`, reloads on next run | No persistence | FastBot2 — key for CI/CD |
| **Throughput** | ~12 evt/s (Monkey-based) | ~14 evt/s (theoretical) | rvsmart potential |
| **Architecture** | Java + C++ native layer | Pure Java | FastBot2 — C++ for computation |
| **MOP awareness** | None (general-purpose) | Static analysis integration | rvsmart — unique for RV |
| **Crash detection** | No dedicated mechanism | CrashInterceptor (instant) | rvsmart |

**Key takeaway**: FastBot2's model reuse is critical for CI/CD workflows where the same app is tested repeatedly. RVSmart could persist its `DynamicStateGraph` and reward data between runs, giving each subsequent run a "warm start".

### 5.3 Advanced Techniques Worth Considering

| Technique | Tool | Relevance to rvsmart |
|-----------|------|---------------------|
| **LLM guidance on plateau** | LLMDroid (FSE 2025) | High — rvsmart already has LLM hybrid mode; could activate it specifically when plateau is detected |
| **Direct VM injection** | TOLLER (ISSTA 2021) | Low — rvsmart already runs inside the VM via app_process, achieving similar benefits |
| **Deep links for hard-to-reach activities** | Delm | Medium — could complement DFS when graph exploration stalls |
| **Cross-session model reuse** | FastBot2 | High — rvsmart's DynamicStateGraph and reward data could be serialized/deserialized |
| **Adaptive abstraction** | APE (CEGAR) | Medium — would improve state differentiation but adds significant complexity |
| **Coordinated multi-step actions** | Gemini suggestion | High — login flows, form filling require sequential action planning |

---

## 6. Consolidated Issues from LLM Analyses

Five independent LLMs analyzed rvsmart. Issues are grouped by consensus level.

### 6.1 High Consensus (3+ LLMs)

| Issue | LLMs | Impact | Phase |
|-------|-------|--------|-------|
| **Missing SCROLL/SWIPE action generation** | Claude, Codex, Gemini, MiniMax | Any app with lists/feeds is severely under-explored | P0 |
| **Speed loss from multiple UI captures per iteration** | Claude, Codex, MiniMax, Qwen | 70-92% throughput loss | P0 |
| **Scoring system deficiencies** (multiple sub-issues) | Codex, Gemini, MiniMax, Qwen | Exploration decisions are poorly informed | P2 |
| **Saturation/stuck detection broken** | Claude, Codex, MiniMax, Qwen | Agent cannot detect when a screen is fully explored | P0 |

### 6.2 Medium Consensus (2 LLMs)

| Issue | LLMs | Impact | Phase |
|-------|-------|--------|-------|
| **StaticMap JSON schema incompatibility** | Codex, Qwen | MopScorer gets no signal from static analysis | P0 |
| **RewardPropagator wiring** | Codex, Qwen | Computed values not consumed by any scorer | P0 |
| **Hardcoded "test" for SET_TEXT** | Gemini, MiniMax | Cannot pass login screens, form validations | P2 |
| **Out-of-app detection insufficient** | Claude, Qwen | Agent wastes time in wrong apps | P3 |

### 6.3 Unique but Valuable

| Issue | LLM | Impact | Phase |
|-------|-----|--------|-------|
| **BACK base score too negative (-500)** | Qwen | BACK is 13x less attractive than average CLICK; prevents voluntary backtracking | P2 |
| **Proactive backtrack threshold too low (50)** | Qwen | Tier 3 almost never activates since nearly any scored action exceeds 50 | P2 |
| **PathBuffer invalidates multi-hop routes prematurely** | Codex | Multi-step backtracking fails before reaching target | P0 |
| **"Deep actions" — coordinated multi-step sequences** | Gemini | Login flows require fill-user → fill-password → click-login sequence | P5 |
| **Gumbel-max stochastic selection** | MiniMax | Score-weighted randomness instead of uniform random | P2 |
| **Time-based stuck detection** | Qwen | Iteration-based detection is unreliable with variable iteration durations | P2 |
| **ScreenNode.totalActions never initialized** | Codex | `getSaturationRate()` always returns 1.0, breaking Tier 3 and saturation scoring | P0 |

---

## 7. Package Detection Deep Dive

### 7.1 The Problem

From the experiment regeneration project analysis (doc 07_pacotes.md):

- **27.5% of F-Droid APKs** (61 of 222) have a manifest package that does NOT match the code package. The manifest declares `ir.hsn6.trans` but all code lives in `org.godotengine.godot.*` (Godot engine games), or `org.fox.ttrss` but the manifest says `org.fox.tttrss` (typo in fork).
- **25.2% of APKs** (56 of 222) have code distributed across multiple packages. Example: `edu.cmu.cylab.starslinger.demo` (manifest) but crypto code in `edu.cmu.cylab.starslinger.exchange.*`.

### 7.2 Impact on rvsmart

RVSmart uses the `--package` CLI argument (manifest package) for out-of-app detection (`root.getPackageName() != packageName`). This comparison uses the **manifest package** because `AccessibilityNodeInfo.getPackageName()` returns the manifest package of the foreground window.

For out-of-app detection, this works correctly — if the foreground window belongs to a different app (e.g., launcher), the manifest package will differ regardless of code package. The issue is more subtle:

1. **Element-level filtering**: If rvsmart adds per-element package filtering (comparing `ScreenItem.getPackageName()` to target package), it must handle multi-package apps where UI elements from different packages coexist in the same screen.
2. **Coverage calculation**: When rv-platform matches logcat coverage entries against static analysis, the `class_name.startsWith(apk_package)` filter may miss methods in secondary packages. This is a pipeline issue, not an rvsmart issue.

### 7.3 Inner Class Normalization

From doc 06_normalizacao_inner_classes.md:

- **Soot** (static analysis) sometimes uses `.` for inner classes (Java source format)
- **AspectJ** (runtime instrumentation) uses `$` (JVM bytecode format)
- `SignatureNormalizer` converts `.` → `$` and handles 99.9985% of cases correctly
- Two edge cases: Parcelable inner classes (4 methods, negligible) and `Package.Class` where Package==Class (ZoomView case, 2 APKs excluded)

**Relevance to rvsmart**: RVSmart's `StaticMap` loads static analysis JSON and queries by action signature. If the signature format differs between runtime (what rvsmart observes) and static analysis (what the JSON contains), `MopScorer` gets false negatives. The Codex analysis flagged this as "StaticMap JSON schema incompatibility" — the actual issue may be deeper than schema: it may be a signature format mismatch.

### 7.4 Recommended Actions

1. **Out-of-app detection**: Current mechanism is correct for the manifest package case. No change needed.
2. **Element-level filtering**: When implementing per-element package filtering, use a **whitelist approach**: accept elements whose package is the target package OR whose package is empty/null. Do NOT reject elements from system packages that appear within the app's window (they may be framework components rendered by the app).
3. **StaticMap signature alignment**: Verify that the action signature format used by rvsmart (`"click@540,960"`) matches the keys in the static analysis JSON. If not, implement a normalization layer.
4. **Multi-package awareness**: For future work — detect secondary packages at runtime by observing which packages appear in AccessibilityNodeInfo elements within the app's foreground window.

---

## 8. Refactoring Plan

### Phase 0: Critical Bug Fixes

**Goal**: Fix bugs that make rvsmart fundamentally broken. These must be fixed before any optimization or feature work.

**Rationale (Codex)**: "Calibrating parameters on a broken base is counterproductive — fix structural bugs first, then calibrate."

| # | Task | File(s) | Detail | Complexity |
|---|------|---------|--------|------------|
| 0.1 | **Initialize ScreenNode.totalActions** | `ScreenNode.java`, `AgentLoop.java` | `totalActions` is never set, so `getSaturationRate()` always returns `1.0` (fully saturated), which means Tier 3 proactive backtrack always triggers and unified queue scoring is based on invalid data. Fix: set `totalActions` to the count of interactive elements on first visit in `AgentLoop.runIteration()` after `uiCapture.capture()`. | S |
| 0.2 | **Add SCROLL action generation** | `ActionSelector.java` | `generateCandidateActions()` only creates CLICK, LONG_CLICK, SET_TEXT. Add SCROLL for scrollable elements (`item.isScrollable()`). This affects all apps with lists, RecyclerView, ScrollView. Coordinates: center of scrollable container, scroll direction down by default. | S |
| 0.3 | **Fix StaticMap signature alignment** | `StaticMap.java`, `MopScorer.java` | Verify that the keys in the static analysis JSON match the format rvsmart uses for `actionSignature`. If the JSON keys use method signatures (`"onCreate(android.os.Bundle)"`) but rvsmart queries with coordinate signatures (`"click@540,960"`), MopScorer will never match. The fix requires either: (a) mapping UI elements to activities/methods via the static analysis windows/transitions data, or (b) loading the reachability data by activity name and querying per current activity. | M |
| 0.4 | **Fix PathBuffer multi-hop invalidation** | `PathBuffer.java` | PathBuffer consumes `expectedHashes` before validating that the agent is still on the planned route. If the agent diverges (e.g., due to a system dialog), the remaining path is invalidated prematurely. Fix: validate position BEFORE consuming the next hop. | S |
| 0.5 | **Wire RewardPropagator into scoring** | `AgentLoop.java`, `ActionSelector.java`, `ScreenNode.java` | RewardPropagator computes cumulative rewards per (state, action) pair and stores them in `ScreenNode.cumulativeRewards`, but no scorer reads these values. Either: (a) create a `RewardScorer` that adds cumulative reward to action scores, or (b) integrate reward as a multiplier in GradualDecayScorer. | S |
| 0.6 | **Reduce UI captures per iteration** | `AgentLoop.java` | The iteration does: initial capture → action → post-action capture → (optional) adaptive wait capture. The Claude analysis counted 3-4 captures in some iterations. Optimize: reuse the post-action capture for the next iteration's "initial" capture when the agent is not stuck. Only re-capture when necessary (crash recovery, out-of-app). | M |
| 0.7 | **Fix LLM/hybrid mode bootstrap** | `Main.java` | Codex identified that LLM components are always null because `Main.java` doesn't bootstrap them even when `--mode multimode` is passed. Fix: wire `SglangClient`, `ToolCallParser`, `PromptBuilder`, `ImageProcessor`, `ScreenshotCapture`, and `RoutingManager` creation in Main.java when mode is `multimode` or `llm_only`. | M |

**Dependencies**: None — these are independent bug fixes.
**Expected impact**: From ~4 evt/s actual to ~8-10 evt/s; MopScorer becomes functional; saturation-based backtracking starts working.

---

### Phase 1: UI Coverage Tracking & Memory

**Goal**: Port the rvagent's element-level coverage tracking and memory systems to enable coverage-driven exploration decisions.

| # | Task | File(s) | Detail | Complexity |
|---|------|---------|--------|------------|
| 1.1 | **Create UICoverageTracker** | New: `core/UICoverageTracker.java` | Port from `rv_agent/memory/ui_coverage.py`. Track: `elementsByScreen: Map<String, Set<String>>` (screen_hash → element IDs), `interactionCounts: Map<String, Integer>` (element_id → count), `elementTypes: Map<String, String>` (element_id → widget class). Element ID format: `"coords:{x},{y}"` for compatibility with rvagent hash format. | M |
| 1.2 | **Register elements on screen visit** | `AgentLoop.java` | After `uiCapture.capture()`, call `uiCoverageTracker.registerScreenElements(hash, items)` for each ScreenItem. Extract center coordinates and create element IDs. | S |
| 1.3 | **Record interactions** | `AgentLoop.java` | After action execution, call `uiCoverageTracker.recordInteraction(hash, elementId, actionType)`. For algorithm actions, use action coordinates. For LLM actions, use `findNearestElement()` with 200px proximity. | S |
| 1.4 | **Coverage gap computation** | `UICoverageTracker.java` | Implement `getCoverageGap(screenHash): float` returning fraction of untested elements (0.0 to 1.0). Used by CoverageDensityScorer and PathBuffer. | S |
| 1.5 | **Enable CoverageDensityScorer** | `ActionSelector.java`, `scorers/CoverageDensityScorer.java` | Currently excluded with comment "hardcoded count=1 makes it a constant". With UICoverageTracker providing real coverage data, this scorer becomes valuable. Modify to read coverage gap from UICoverageTracker instead of hardcoded count. Score = `coverageGap * weight` where weight is configurable. | S |
| 1.6 | **Plateau detection** | New: `strategy/PlateauDetector.java` | Port from `rv_agent/strategies/rvagent_strategy/plateau_detector.py`. Sliding window of 10 iterations tracking state discoveries and MOP discoveries. When both windows are all-false, boost stochastic probability to 0.5 (from default 0.15). Restore when new state discovered. | S |
| 1.7 | **Integrate plateau into AgentLoop** | `AgentLoop.java`, `ActionSelector.java` | Call `plateauDetector.recordIteration(isNewScreen, hasMopCoverage)` after each iteration. When plateau detected, temporarily set `stochasticProbability = 0.5` in ActionSelector. | S |

**Dependencies**: Phase 0 (totalActions must be initialized for coverage to be meaningful).
**Expected impact**: Coverage-driven exploration directs the agent toward under-tested screens. Plateau detection prevents the agent from getting stuck in deterministic loops. Estimated +3-5pp method coverage.

---

### Phase 2: Scoring & Strategy Improvements

**Goal**: Improve the quality of action selection decisions by fixing scoring parameters and adding smart behaviors.

| # | Task | File(s) | Detail | Complexity |
|---|------|---------|--------|------------|
| 2.1 | **Fix BACK base score** | `Config.java` | Change default from -500 to -100. At -500, BACK is 13x less attractive than an average CLICK (~100 from ComponentPriorityScorer), making voluntary backtracking nearly impossible. At -100, BACK becomes a reasonable alternative when no good forward actions exist. | S |
| 2.2 | **Raise proactive backtrack threshold** | `ActionSelector.java` | Change `PROACTIVE_BACKTRACK_THRESHOLD` from 50 to 150. At 50, Tier 3 almost never activates because most scored actions exceed 50. At 150, the threshold is just above a basic untested CLICK (100 from ComponentPriority), meaning Tier 3 triggers when the current screen has mostly tested actions and no MOP-reaching elements. | S |
| 2.3 | **Implement WtgScorer** | `scorers/WtgScorer.java`, `StaticMap.java` | Currently a stub returning 0. The static analysis JSON has a `transitions` section mapping `{source_activity: [{target_activity, widget_event}]}`. Parse this in StaticMap and expose `getTransitionTargets(activity)`. WtgScorer boosts actions whose widget matches a known transition that leads to an unvisited activity. Score: +200 for transition to unvisited activity, +50 for transition to under-visited activity. | M |
| 2.4 | **Smart text input** | `ActionSelector.java`, New: `strategy/InputValueGenerator.java` | Replace hardcoded `"test"` with context-aware input generation. Port concept from rvagent's `InputValueGenerator`. Strategy: for each `SET_TEXT` action, generate 3-5 variations based on widget hint/resource_id (email fields get `"test@test.com"`, password fields get `"Test1234!"`, number fields get `"42"`, generic fields get `"test"`, `""`, `"a very long text string"`). Store used inputs per element to avoid repeating. | M |
| 2.5 | **Score-weighted stochastic selection** | `ActionSelector.java` | Replace uniform random selection with softmax-weighted selection. Instead of `random.nextInt(actions.size())`, compute `p(a) = exp(score(a)/temperature) / sum(exp(scores/temperature))` and sample from this distribution. Temperature=50 gives gentle preference to higher-scored actions while maintaining exploration. | S |
| 2.6 | **Time-based stuck detection** | `recovery/StuckDetector.java` | Add a time-based threshold alongside the iteration-based one. If the agent has not discovered a new screen for 30 seconds (regardless of iteration count), trigger stuck recovery. This handles cases where slow iterations (LLM calls, long waits) make the iteration count unreliable. | S |
| 2.7 | **Increase maxRetriesPerCycle** | `Config.java` | Change default from 1 to 3. A retry costs ~250ms (throttle + capture) vs ~500ms for a full new cycle. Qwen analysis estimates retry is 30x cheaper when counting wasted cycles. More retries per cycle means fewer wasted cycles on screens where the first action had no effect. | S |

**Dependencies**: Phase 0 (saturation and scoring must be functional), Phase 1 (CoverageDensityScorer needs UICoverageTracker).
**Expected impact**: Better action selection → fewer wasted actions → more coverage per unit time. Estimated +5-8pp method coverage.

---

### Phase 3: Package Detection & Out-of-App Improvements

**Goal**: Improve robustness when dealing with diverse APKs, especially multi-package apps and apps with non-standard package structures.

| # | Task | File(s) | Detail | Complexity |
|---|------|---------|--------|------------|
| 3.1 | **Launcher fast-path** | `AgentLoop.java` | Add `LAUNCHER_PACKAGES` set (`com.android.launcher3`, `com.google.android.apps.nexuslauncher`, `com.android.launcher`). When `rootPkg` matches a launcher, skip the tolerance counter and restart immediately. The agent has no useful actions on the home screen. | S |
| 3.2 | **Element-level package filtering** | `ActionSelector.java` | In `generateCandidateActions()`, filter out elements whose `ScreenItem.getPackageName()` matches known system UI packages (`com.android.systemui`, `android`). Currently, SystemElementFilter only applies a score penalty (-5000), but the element still competes in the queue. Pre-filtering removes them entirely. Keep elements with null/empty package (framework widgets rendered by the app). | S |
| 3.3 | **Runtime package detection** | New: `core/PackageDetector.java` | Observe the `package` attribute on AccessibilityNodeInfo elements during the first N iterations. If >80% of interactive elements have a package different from the CLI `--package`, log a warning. This is diagnostic only (for the researcher to know if the package argument is wrong), not auto-corrective — auto-correction risks false positives. | S |
| 3.4 | **LLM coordinate boundary protection** | `AgentLoop.java` | When executing LLM-generated actions, validate that coordinates are not in the status bar (top 5% of screen) or navigation bar (bottom 6%). If so, substitute with BACK action. Prevents the LLM from accidentally tapping system UI elements that navigate away from the app. | S |

**Dependencies**: None — independent of other phases.
**Expected impact**: Eliminates wasted time in wrong apps and reduces interactions with system UI elements. Estimated +2-3pp method coverage on diverse APK sets.

---

### Phase 4: Speed Optimization

**Goal**: Close the gap between theoretical throughput (14 evt/s) and actual throughput.

| # | Task | File(s) | Detail | Complexity |
|---|------|---------|--------|------------|
| 4.1 | **Reduce default throttle** | `Config.java` | Change default `throttleMs` from 200ms to 50ms. Qwen analysis: throttle dominates 80% of cycle time. The rvsmart-tool plugin already sets throttle_ms=50 in variants, but if the properties file is not loaded correctly (Claude's bug), the Java default of 200ms is used. Verify properties loading and change the hardcoded default. | S |
| 4.2 | **Reduce RESTART cost** | `AgentLoop.java`, `recoverApp()` | Current: `forceStop(500ms sleep) + startApp(1500ms sleep)` = 2000ms. Reduce to: `forceStop(200ms sleep) + startApp(800ms sleep)` = 1000ms. The app_process execution model means the agent resumes immediately after the app starts — no ADB reconnection needed. | S |
| 4.3 | **Optimize adaptive wait** | `AgentLoop.java` | Current: always waits `adaptiveWaitMs` (150ms) when no effect detected. Optimize: only apply adaptive wait when the action was a CLICK on a button/link (high transition probability). Skip for SET_TEXT, SCROLL (immediate effect or no effect — no benefit from waiting). | S |
| 4.4 | **Screen state caching** | `AgentLoop.java` | After post-action capture, store the resulting `ScreenState` and reuse it as the "initial" state for the next iteration. This eliminates one full UI capture per iteration when the agent is exploring normally (no crash, no out-of-app). Only re-capture on: crash recovery, out-of-app recovery, stuck recovery. | M |
| 4.5 | **Benchmark and validate** | Test infrastructure | Run rvsmart on cryptoapp with Phase 0-4 fixes. Measure: evt/s, unique states/min, methods/min. Target: >10 evt/s sustained, matching APE's ~10 evt/s actual throughput while providing better exploration quality. | M |

**Dependencies**: Phase 0 (must fix multiple UI captures first).
**Expected impact**: From ~4 evt/s to 10-14 evt/s sustained. Higher throughput means more actions per timeout, more screens discovered, more coverage.

---

### Phase 5: Advanced Features

**Goal**: Implement techniques from SOTA tools that give rvsmart a decisive advantage.

| # | Task | File(s) | Detail | Complexity |
|---|------|---------|--------|------------|
| 5.1 | **Model persistence** | New: `output/ModelSerializer.java` | Serialize `DynamicStateGraph` (nodes, transitions, action scores, saturation) to JSON at the end of each run. On startup, if a model file exists for the same package, deserialize and resume exploration from where the previous run left off. This gives FastBot2-style cross-run knowledge reuse. Key design: use screen hashes as keys (stable across runs if app version unchanged). | L |
| 5.2 | **LLM-guided plateau recovery** | `AgentLoop.java`, `core/RoutingManager.java` | When `PlateauDetector` detects a plateau and LLM components are available, force a single LLM call to get guidance on what to explore next. The LLM sees the current screen screenshot + list of visited/unvisited activities and suggests a navigation target. This is the LLMDroid approach: use LLM only when automated exploration stalls. | M |
| 5.3 | **Coordinated action sequences** | New: `strategy/ActionSequencer.java` | Detect login/form patterns (multiple EditText fields followed by a Button) and generate coordinated sequences: fill all fields → click submit. Currently, the agent fills one field per iteration, and may click submit before filling all fields. The sequencer buffers SET_TEXT actions and executes them atomically before the CLICK. | M |
| 5.4 | **Adaptive state abstraction** | `core/ScreenState.java` | Currently, the hash includes `package` and `resource_id` which may cause over-differentiation (same screen, different ad banner) or under-differentiation (same structure, different content). Add a configurable abstraction level: Level 0 = current (all 9 attributes), Level 1 = exclude text content, Level 2 = exclude resource_id. When the graph grows too fast (>100 states in 60s), coarsen; when stuck (<3 states in 60s), refine. Inspired by APE's CEGAR. | L |
| 5.5 | **Deep link integration** | `device/AppController.java` | When the graph shows unreachable activities (from static analysis windows data), attempt to launch them directly via `am start -a android.intent.action.VIEW -d <deep_link>` or `am start -n <package>/<activity>`. Inspired by Delm. Requires parsing AndroidManifest intent-filters from static analysis data. | L |

**Dependencies**: Phase 1 (plateau detection), Phase 2 (WtgScorer for static analysis integration), Phase 4 (speed for model persistence to be meaningful).
**Expected impact**: Model persistence alone could provide +5pp method coverage on repeated runs. LLM-guided recovery targets the "30% curse" identified by CovAgent.

---

## 9. Expected Impact

### 9.1 Coverage Projections by Phase

| Phase | Method Coverage (est.) | Cumulative | Basis |
|-------|----------------------|------------|-------|
| **Baseline** (current) | 17.8% | 17.8% | 22-APK experiment average |
| **Phase 0** (bug fixes) | +5-7pp | 23-25% | Scroll adds access to list content; speed increase = more actions |
| **Phase 1** (UI coverage + memory) | +3-5pp | 26-30% | Coverage-driven exploration reduces wasted actions |
| **Phase 2** (scoring + strategy) | +5-8pp | 31-38% | Better decisions per action; smart text input opens login gates |
| **Phase 3** (package detection) | +2-3pp | 33-41% | Eliminates wasted time on wrong apps/system UI |
| **Phase 4** (speed) | +3-5pp | 36-46% | More actions per timeout = more coverage |
| **Phase 5** (advanced) | +5-10pp | 41-56% | Model reuse, LLM guidance, deep links |

### 9.2 Competitive Targets

| Tool | Method Coverage (typical) | rvsmart Target Phase |
|------|--------------------------|---------------------|
| Monkey | 12-15% | Already beaten |
| DroidBot | 14-18% | Already beaten (baseline) |
| APE | 18-22% | Phase 0-1 |
| FastBot2 | 20-25% | Phase 2 |
| Humanoid | 18-22% | Phase 1 |
| LLMDroid | 25-30% | Phase 3-4 |
| CovAgent | 35-45% | Phase 5 |

### 9.3 Claude Analysis Projection

The Claude LLM analysis estimated that with all operational bugs fixed, rvsmart could reach 25-30% method coverage (from 17.8%), surpassing APE (20.4%). The Qwen analysis projected 10-15 evt/s throughput with throttle reduction alone. These align with our Phase 0-1 targets.

---

## 10. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **StaticMap signature format mismatch is deeper than expected** | Medium | High — MopScorer remains useless | Spike: dump actual JSON keys vs rvsmart queries in a debug log; if incompatible, redesign the mapping |
| **UICoverageTracker adds too much overhead** | Low | Medium — negates speed advantage | Use lazy initialization, cap tracked elements at 2000 per screen, profile before/after |
| **Model persistence across runs produces stale data** | Medium | Medium — wrong decisions from outdated model | Version the model with app version hash; invalidate on mismatch |
| **Adaptive wait reduction causes missed transitions** | Medium | Low — some slow transitions not detected | Keep adaptive wait for CLICK actions on buttons, remove only for text/scroll |
| **Multi-repo version drift** (Java rvsmart + Python plugin) | High | High — broken interface contracts | Add version header to RVSMART_METRICS JSON; plugin validates on startup |
| **Phase 5 features add too much complexity** | Medium | Medium — maintenance burden | Each Phase 5 feature is independently toggleable via config flags |

---

## 11. Next Steps: Track Selection

This document is the Phase 0 ideation output. The refactoring effort described here is large (6 phases, ~30 tasks). Per WORKFLOW.md Section 3, track selection depends on whether the change requires **design decisions**:

**Assessment**: This effort requires design decisions (new classes, new scoring logic, memory system architecture, model persistence format). It touches multiple modules (rvsmart Java in `$RVSEC_HOME`, rvsmart-tool Python in `rv-android`). It is multi-module and architectural.

**Recommended approach**: Split into multiple GitHub Issues, each following the appropriate track:

| Phase | Track | Rationale |
|-------|-------|-----------|
| Phase 0 (bug fixes) | **Quick Path** | No design decisions — bugs with clear fixes |
| Phase 1 (UI coverage + memory) | **Full SDD** | New architecture (UICoverageTracker, PlateauDetector), design decisions needed |
| Phase 2 (scoring + strategy) | **FF SDD** | Design decisions but single module, clear requirements from LLM analyses |
| Phase 3 (package detection) | **Quick Path** | Mechanical changes, clear plan |
| Phase 4 (speed optimization) | **Quick Path** | Configuration + minor code changes |
| Phase 5 (advanced features) | **Full SDD** | Each feature is a separate architectural decision |

**Immediate next step**: Create GitHub Issues for Phase 0 and Phase 1, move to Backlog, and start Phase 0 via Quick Path. Phase 0 must be completed before any other phase begins.
