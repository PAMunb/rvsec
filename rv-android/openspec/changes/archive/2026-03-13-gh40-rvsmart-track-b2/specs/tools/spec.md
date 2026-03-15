## Purpose

Delta spec for remaining Track B improvements (gh40). Adds per-Activity iteration budget, anti-tarpit detection, and simplifies PhaseController from 3 phases to 2.

## ADDED Requirements

### Requirement: Per-Activity Iteration Budget

The rvsmart agent SHALL allocate an iteration budget to each Activity based on its interactive widget count. The budget formula SHALL be: `budget = activity_base_budget + (widgetCount * budget_per_widget)`, where `activity_base_budget` (default 10) and `budget_per_widget` (default 3) are configurable parameters.

`ActivityBudgetTracker` SHALL register an Activity's budget on first visit using the count of interactive elements from the current ScreenState. On each iteration, the tracker SHALL increment the iteration counter for the current Activity. When the counter reaches the budget, `isBudgetExhausted()` SHALL return true.

When the budget is exhausted and the selected action is a widget action (not BACK or RESTART), AgentLoop SHALL override the action with BACK (if parent exists) or RESTART. This prevents the agent from spending excessive time on Activities with few interactive widgets while under-exploring complex Activities.

The budget is permanent per run — once exhausted, an Activity remains exhausted. This is intentional: the agent should distribute its limited time across Activities rather than revisiting exhausted ones.

#### Scenario: Budget allocated proportional to widget count
- **WHEN** the agent first visits an Activity with 20 interactive widgets
- **AND** `activity_base_budget` is 10 and `budget_per_widget` is 3
- **THEN** the Activity SHALL receive a budget of 70 iterations (10 + 20×3)

#### Scenario: Budget exhaustion triggers backtrack
- **WHEN** the agent has spent 70 iterations on an Activity with budget 70
- **AND** the selected action is CLICK at (540, 960)
- **THEN** the agent SHALL override the action with BACK or RESTART
- **AND** subsequent visits to this Activity SHALL also be overridden

#### Scenario: BACK and RESTART are not overridden
- **WHEN** the budget for the current Activity is exhausted
- **AND** the selected action is BACK
- **THEN** the action SHALL NOT be overridden (BACK is already leaving the Activity)

### Requirement: Anti-Tarpit Detection

The rvsmart agent SHALL detect "tarpit" screens — screens where the agent accumulates many iterations without making progress. A screen hash SHALL be declared a tarpit when it accumulates `tarpit_threshold` (default 15) consecutive iterations without: (a) discovering a new content state, (b) gaining new MOP coverage, or (c) the screen hash changing.

`TarpitDetector` SHALL track per-screen-hash iteration counts since last progress event. When a tarpit is detected, the agent SHALL mark the hash in ContentGraph and force RESTART. Tarpit hashes SHALL be excluded from BacktrackBfs and FrontierFinder candidate targets alongside sterile hashes.

The tarpit counter for a hash SHALL reset when progress is observed at that hash. A tarpit is a "soft" blacklist — unlike sterile hashes (which indicate UIAutomator failure), tarpit hashes indicate algorithmic futility. Both result in the same exclusion behavior.

#### Scenario: Tarpit detected after 15 no-progress iterations
- **WHEN** the agent spends 15 consecutive iterations on screen hash `abc123`
- **AND** no new content state is discovered and no new MOP coverage is gained
- **THEN** `TarpitDetector.isTarpit("abc123")` SHALL return true
- **AND** the agent SHALL force RESTART on the next iteration

#### Scenario: Tarpit counter resets on progress
- **WHEN** the agent has spent 10 iterations on hash `abc123` without progress
- **AND** on the 11th iteration, a new content state is discovered
- **THEN** the tarpit counter for `abc123` SHALL reset to 0

#### Scenario: Tarpit hashes excluded from navigation targets
- **WHEN** hash `abc123` is marked as tarpit
- **THEN** `BacktrackBfs.findPathToUnsaturated()` SHALL skip `abc123` as a candidate
- **AND** `FrontierFinder.findFrontier()` SHALL skip `abc123` as a candidate

## MODIFIED Requirements

### Requirement: Scoring Chain Composition

The rvsmart exploration phases SHALL be simplified from 3 phases to 2:

- **Phase 1** (Broad exploration): unchanged — DFS with untested action preference, scorer chain, cluster navigation fallback
- **Phase 3** (Stochastic escape): unchanged — softmax-weighted stochastic selection with boosted probability

**Phase 2 (Coverage-guided navigation) is removed.** Its behavior is redundant with `CoverageDensityScorer` (directs to screens with untested elements) and `UCBScorer` (exploration bonus for under-visited states). The scorer chain achieves Phase 2's goal without explicit NavigationMap BFS navigation.

The transition becomes: Phase 1 → Phase 3 when PlateauDetector signals plateau. Phase 3 → Phase 1 when new content state is discovered.

`ActionSelector.selectPhase2()` and `findHighestGapCluster()` SHALL be removed. `PhaseController.Phase` enum SHALL contain only `PHASE_1` and `PHASE_3`.

#### Scenario: Phase transition skips Phase 2
- **WHEN** PlateauDetector signals plateau (10 consecutive no-progress iterations)
- **AND** current phase is Phase 1
- **THEN** PhaseController SHALL transition directly to Phase 3
- **AND** Phase 2 SHALL NOT be entered

## Invariants

- **INV-RSM-48**: `ActivityBudgetTracker.isBudgetExhausted()` SHALL return true only after the iteration count reaches the computed budget. Budget computation MUST use `activity_base_budget + (widgetCount * budget_per_widget)`.
- **INV-RSM-49**: `TarpitDetector` SHALL reset the per-hash counter when any progress event occurs (new state, new MOP, hash change). A tarpit SHALL only be declared after `tarpit_threshold` truly consecutive no-progress iterations.
- **INV-RSM-50**: After PhaseController simplification, the `Phase` enum SHALL contain exactly 2 values: `PHASE_1` and `PHASE_3`. No code SHALL reference `PHASE_2`.
