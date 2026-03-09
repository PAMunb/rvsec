## Purpose

This delta spec documents the behavioral changes to the rvsmart Java agent's exploration algorithm. The `RVSmartTool` Python wrapper contract (registration, execution, health check, trace capture, metrics extraction) remains unchanged — only the internal exploration algorithm within the rvsmart JAR changes.

The redesign replaces three internal mechanisms: (1) single structural hash with dual hash (content-aware + structural), (2) BACK-dependent backtracking with structural navigation graph replay, (3) 4-tier action selection with 3-phase continuous exploration. These changes affect what the agent does inside the emulator during execution, but not how rv-platform invokes or monitors it.

The trace output format (`RVTRACK:` lines) and metrics JSON (`RVSMART_METRICS:`) remain compatible. New fields MAY be added to the metrics JSON (e.g., `content_states_explored`, `structural_clusters`, `phase_transitions`) but existing fields SHALL be preserved.

## MODIFIED Requirements

### Requirement: RVSmartTool Metrics Extraction

After execution completes (timeout or otherwise), `RVSmartTool` SHALL extract the final metrics report from the trace file and write it to a separate file. The extraction logic searches for the last line starting with `RVSMART_METRICS:` in the trace file, parses the JSON payload, and writes it to `rvsmart_metrics.json` alongside the trace file in the task output directory.

The metrics JSON payload SHALL include the following fields nested within existing sections (in addition to existing fields preserved from gh30-gh32):

Within the `exploration` section (alongside `unique_states`, `unique_hashes`):
- `content_states`: integer — number of distinct content-hash states explored
- `structural_clusters`: integer — number of distinct structural-hash clusters
- `nav_map_edges`: integer — number of recorded structural navigation transitions
- `phase_distribution`: object — `{"phase1": N, "phase2": N, "phase3": N}` counting iterations spent in each phase

Within the `decisions` section (alongside `forced_backs`):
- `backtrack_replays`: integer — number of times RESTART+replay was used (BACK failure recovery)

Counter wiring in AgentLoop:
- `content_states`: read from `ContentGraph.size()` at metrics finalization
- `structural_clusters`: read from `StructuralGraph.size()` at metrics finalization
- `nav_map_edges`: read from `NavigationMap.size()` at metrics finalization
- `phase_distribution`: incremented in `AgentLoop.runIteration()` after `PhaseController.currentPhase()` returns
- `backtrack_replays`: incremented in `BacktrackStrategy` each time replay path is executed

#### Scenario: Metrics JSON includes dual hash and phase data

- **WHEN** rvsmart completes execution with the redesigned algorithm
- **THEN** `RVSmartTool` SHALL extract `RVSMART_METRICS:` JSON from trace file
- **AND** the JSON SHALL contain `content_states` as an integer >= 1
- **AND** the JSON SHALL contain `structural_clusters` as an integer >= 1
- **AND** the JSON SHALL contain `phase_distribution` with keys `phase1`, `phase2`, `phase3`
- **AND** the JSON SHALL contain `backtrack_replays` as an integer >= 0

#### Scenario: Backward-compatible metrics fields preserved

- **WHEN** rvsmart completes execution
- **THEN** `RVSMART_METRICS:` JSON SHALL still contain all fields from gh30-gh32 metrics format (iterations, unique_screens, mop_hits, ooa_count, restart_count, avg_cycle_ms, etc.)
- **AND** `RVSmartTool` Python extraction logic SHALL require no changes

## Invariants

- **INV-TOOL-TRACE-01**: The rvsmart trace file format (`RVTRACK:` lines) SHALL remain parseable by existing post-processing scripts. New trace line types MAY be added with distinct prefixes but existing prefixes SHALL preserve their format.
- **INV-TOOL-METRICS-01**: The `RVSMART_METRICS:` JSON SHALL be a strict superset of the gh32 metrics schema — no existing fields removed, only new fields added.
