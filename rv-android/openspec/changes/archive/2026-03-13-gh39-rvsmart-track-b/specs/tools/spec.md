## Purpose

Delta spec for rvsmart exploration behavior changes in Track B (gh39). Modifies retry budget, adds sterile screen blacklist, adds forward navigation via frontier search, and includes content-description in content hash computation.

These changes target structural inefficiencies identified in the gh36 analysis: excessive retries (52.6% of actions), unparseable screen loops (19% of actions), backward-only stuck recovery, and incomplete state identity.

## ADDED Requirements

### Requirement: Sterile Screen Blacklist

The rvsmart agent SHALL track consecutive UIAutomator parse failures (null or empty root) per content hash. When `getRootInActiveWindow()` returns null, the agent SHALL attribute the failure to the **last known content hash** (the hash from the previous successful iteration), since no ScreenState can be computed without a root. When the failure count for a hash reaches the configurable `sterile_threshold` (default 3), the hash SHALL be marked as "sterile" in ContentGraph. Sterile hashes SHALL be excluded from BacktrackBfs target candidates and FrontierFinder candidates. Once marked sterile, a hash SHALL remain sterile for the duration of the run (no un-marking).

The sterile counter for a hash SHALL reset to zero when a successful parse occurs at that hash. This prevents transient failures (slow app startup, brief loading screens) from permanently blacklisting valid screens.

#### Scenario: Screen becomes sterile after 3 consecutive failures
- **WHEN** UIAutomator returns null root 3 consecutive times while the last known content hash is `a1b2c3d4`
- **THEN** `ContentGraph.isSterile("a1b2c3d4")` SHALL return true
- **AND** subsequent calls to `BacktrackBfs.findPathToUnsaturated()` SHALL skip `a1b2c3d4` as a candidate target

#### Scenario: Sterile counter resets on successful parse
- **WHEN** UIAutomator returns null root 2 times while last known hash is `a1b2c3d4`
- **AND** UIAutomator returns a valid root on the 3rd visit at the same screen
- **THEN** the sterile counter for `a1b2c3d4` SHALL reset to 0
- **AND** `ContentGraph.isSterile("a1b2c3d4")` SHALL return false

#### Scenario: No last known hash available
- **WHEN** UIAutomator returns null root on the very first iteration (no previous hash)
- **THEN** the sterile counter SHALL NOT be incremented
- **AND** existing null root recovery (handleNullRoot) SHALL proceed normally

### Requirement: Forward Navigation via Frontier Search

When StuckDetector fires Level 2 recovery and BacktrackBfs finds no unsaturated ancestor, the agent SHALL attempt forward navigation by searching for a **frontier state** — a reachable content state with `getCoverage() < frontier_coverage_threshold` (default 0.8) that is not sterile.

`FrontierFinder` SHALL perform BFS forward through `ContentNode.getTransitions()` starting from the current hash, visiting all reachable states, and returning the hash of the nearest frontier node. If no frontier exists, the search SHALL return null and recovery SHALL fall back to RESTART.

When a frontier is found but no direct navigation path is available (forward navigation requires action replay which is not yet implemented), StuckDetector SHALL return RESTART. After restart, the agent re-enters from the main activity and UCB+scorers naturally bias exploration toward the frontier (unsaturated states receive higher UCB bonus). This captures the benefit of frontier awareness without requiring explicit forward navigation.

The recovery priority order SHALL be: (1) BacktrackBfs ancestor → BACK, (2) FrontierFinder forward found → RESTART (indirect navigation via scorer bias), (3) no frontier → RESTART.

#### Scenario: Forward frontier found when all ancestors saturated
- **WHEN** the agent is stuck at hash `H1` with all ancestors having visitCount >= 5
- **AND** hash `H3` is reachable via transitions `H1 → H2 → H3`
- **AND** `H3` has coverage 0.3 (below threshold 0.8)
- **THEN** `FrontierFinder.findFrontier("H1", graph, 0.8f, sterileHashes)` SHALL return `"H3"`
- **AND** StuckDetector.recover() SHALL return RESTART (UCB bias will guide toward `H3`)

#### Scenario: No frontier available
- **WHEN** the agent is stuck at hash `H1`
- **AND** all reachable states (ancestors and forward) have coverage >= 0.8 or are sterile
- **THEN** `FrontierFinder.findFrontier()` SHALL return null
- **AND** StuckDetector.recover() SHALL return RESTART

#### Scenario: Sterile states excluded from frontier search
- **WHEN** hash `H2` is marked sterile in ContentGraph
- **AND** `H2` is reachable from current hash via transitions
- **THEN** `FrontierFinder.findFrontier()` SHALL NOT return `H2`
- **AND** BFS SHALL continue past `H2` to search deeper nodes

## MODIFIED Requirements

### Requirement: Retry Budget

The rvsmart retry loop (INV-RSM-07) SHALL use `max_retries_per_cycle` (default changed from 3 to **1**) as the maximum number of alternative actions tried when the primary action has no effect.

Additionally, when the current screen's saturation rate (`ContentNode.getSaturationRate()`) is greater than or equal to `retry_saturation_threshold` (default 0.8), retries SHALL be skipped entirely (effective retry count = 0). This prevents wasting iterations on screens where most widget actions have already been sufficiently explored.

#### Scenario: Retries limited to 1 on unsaturated screen
- **WHEN** the primary action on a screen with saturation 0.3 has no effect
- **THEN** the agent SHALL try at most 1 alternative action
- **AND** if the alternative also has no effect, the agent SHALL proceed to the next iteration

#### Scenario: Retries skipped on saturated screen
- **WHEN** the primary action on a screen with saturation 0.9 has no effect
- **AND** `retry_saturation_threshold` is 0.8
- **THEN** the agent SHALL NOT attempt any retry actions
- **AND** the agent SHALL proceed directly to the next iteration

### Requirement: Content Hash Computation

The content hash computed by `ScreenState.computeContentHash()` SHALL include a truncated `contentDescription` (≤50 chars) for interactive non-EditText widgets, in addition to the existing fields (className, resourceID, text, enabled, checkable).

The content signature format SHALL be: `className|resourceId|text|contentDesc|enabled|checkable`.

Content-description inclusion follows the same rules as text inclusion: excluded for EditText widgets (user input) and excluded for non-interactive widgets (dynamic output). This ensures accessibility-described widgets (e.g., ImageButtons with content-description but no text) produce distinct content hashes.

#### Scenario: ImageButton with content-description produces distinct hash
- **WHEN** two ImageButton widgets have the same className, resourceId, no text
- **AND** one has contentDescription "Settings" and the other has contentDescription "Profile"
- **THEN** `computeContentHash()` SHALL produce different hashes for screens containing these widgets

#### Scenario: Non-interactive widget content-description excluded
- **WHEN** an output-only TextView has contentDescription "Current balance: $42.50"
- **THEN** the contentDescription SHALL NOT be included in the content signature
- **AND** changing the balance SHALL NOT produce a different content hash

### Requirement: Scoring Chain (spec debt from gh37)

The rvsmart scoring chain SHALL consist of exactly **8** scorers: `MopScorer`, `WtgScorer`, `GradualDecayScorer`, `SystemElementFilter`, `ComponentPriorityScorer`, `ConfirmedCoverageScorer`, `CoverageDensityScorer`, `UCBScorer`. This updates INV-RSM-32 from 7 to 8 scorers (UCBScorer added by gh37).

## Invariants

- **INV-RSM-44**: Sterile hashes SHALL be excluded from both BacktrackBfs ancestor candidates and FrontierFinder forward candidates. A sterile hash SHALL never be returned as a navigation target.
- **INV-RSM-45**: The retry loop SHALL execute 0 retries when `ContentNode.getSaturationRate() >= retry_saturation_threshold`, regardless of `max_retries_per_cycle`.
- **INV-RSM-46**: `FrontierFinder.findFrontier()` SHALL return the nearest (shortest BFS path) frontier state, not an arbitrary one. BFS guarantees shortest-path property.
- **INV-RSM-47**: The content signature for interactive non-EditText widgets SHALL include both `text` and `contentDescription`, each truncated to 50 chars independently.
