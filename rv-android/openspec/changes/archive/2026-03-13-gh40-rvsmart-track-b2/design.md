# Design: gh40-rvsmart-track-b2

## Overview

Three changes to rvsmart exploration: (A) per-Activity iteration budget, (B) tarpit detection, (C) PhaseController simplification from 3 phases to 2. All three are independent at the code level but share the goal of reducing wasted iterations.

## A. Component Budget Allocation

### Approach

New class `ActivityBudgetTracker` tracks iteration spending per Activity. Each Activity gets a budget proportional to its interactive widget count (from `ScreenState.getItems()` filtered to interactive elements).

**Budget formula**: `budget = BASE_BUDGET + (widgetCount * BUDGET_PER_WIDGET)`
- `BASE_BUDGET` = 10 iterations (minimum for any Activity)
- `BUDGET_PER_WIDGET` = 3 iterations per interactive widget
- Example: Activity with 20 widgets → 10 + 60 = 70 iterations

**Lifecycle**:
1. On each iteration, `ActivityBudgetTracker.recordIteration(activityName)` increments the counter
2. `isBudgetExhausted(activityName)` returns true when iterations >= budget
3. When exhausted, AgentLoop triggers proactive backtrack (same as saturation-based, Tier 3)
4. Budget is registered on first visit: `registerActivity(activityName, widgetCount)`
5. Budget is never reset — once an Activity's budget is spent, the agent avoids it

**Integration point**: AgentLoop, after action selection (step 7), checks `activityBudgetTracker.isBudgetExhausted(activity)`. If exhausted and selected action is NOT BACK/RESTART, override with BACK or RESTART.

### Files Modified
- `strategy/ActivityBudgetTracker.java` (NEW)
- `core/AgentLoop.java` (wire tracker, check budget)
- `core/Config.java` (add `activity_base_budget`, `budget_per_widget` params)

## B. Anti-Tarpit Detection

### Approach

New class `TarpitDetector` detects when the agent is stuck in a repetitive pattern on a specific screen without making progress. Unlike PlateauDetector (global, window-based), TarpitDetector tracks per-screen-hash iteration counts since last progress.

**Detection rule**: When a screen hash accumulates `TARPIT_THRESHOLD` (default 15) consecutive iterations without any of: (a) new content state discovered, (b) new MOP coverage, (c) screen hash change — the screen is declared a tarpit.

**Recovery**: On tarpit detection:
1. Mark the screen hash as a "tarpit" (temporary blacklist, similar to sterile but for a different reason)
2. Force RESTART
3. Tarpit hashes are passed to BacktrackBfs and FrontierFinder as additional exclusions (alongside sterile hashes)

**Difference from sterile**: Sterile = UIAutomator can't parse the screen (null root). Tarpit = screen parses fine but the agent makes no progress there.

**Integration point**: AgentLoop, after learning step, calls `tarpitDetector.recordIteration(hash, hasNewState, hasNewMop)`. If tarpit detected, forces RESTART on next iteration.

### Files Modified
- `recovery/TarpitDetector.java` (NEW)
- `core/AgentLoop.java` (wire detector, check tarpit, pass tarpit hashes to recovery)
- `core/Config.java` (add `tarpit_threshold` param)
- `graph/ContentGraph.java` (add `tarpitHashes` set, `markTarpit()`, `isTarpit()`, `getTarpitHashes()`)
- `recovery/BacktrackBfs.java` (accept tarpit hashes in exclusion set)
- `recovery/StuckDetector.java` (pass combined sterile+tarpit hashes)

## C. PhaseController Simplification

### Approach

Remove Phase 2 (coverage-guided navigation) from PhaseController. The 3-phase system becomes 2-phase:
- **Phase 1**: Broad exploration (unchanged)
- **Phase 3**: Stochastic escape (unchanged, renumbered as the "escape" phase)

**Why Phase 2 is redundant**: Phase 2 navigates to the screen with the highest coverage gap via NavigationMap BFS. This is exactly what `CoverageDensityScorer` (scorer #7) does — it boosts actions on screens with untested elements. Combined with `UCBScorer` (scorer #8) providing exploration bonus, the scorer chain already achieves Phase 2's goal without explicit navigation.

**Transition change**: Phase 1 → Phase 3 when PlateauDetector signals plateau (skipping Phase 2 entirely). Phase 3 → Phase 1 when new content state is discovered (unchanged).

**ActionSelector impact**: Remove `selectPhase2()` method. Phase 2 branches in `selectAction()` dispatch to Phase 1 instead. The `findHighestGapCluster()` private method becomes dead code and is deleted.

### Files Modified
- `strategy/PhaseController.java` (remove PHASE_2 from enum, simplify transitions)
- `strategy/ActionSelector.java` (remove selectPhase2, remove findHighestGapCluster)
- `core/AgentLoop.java` (remove Phase 2 references if any)

## Dependency Order

A, B, C are independent — no shared new files. Integration wiring in AgentLoop depends on all three.

```
Group A (ActivityBudgetTracker)  ─┐
Group B (TarpitDetector)         ─┼─> Group D (AgentLoop wiring) ─> Group E (Verification)
Group C (PhaseController simpl.) ─┘
```
