# Delta Spec: agent — gh77-revive-rvagent

## Purpose

This delta revives rv-agent as a local-only experimental arm and ports the exploration concepts that evolved in APE-RV (branch `mop-fairtest`) onto rv-agent's existing ranking and strategy layers. The port preserves the current default behavior of every touched component: all new steering capabilities ship behind flags whose defaults are off/0, so a run with an unchanged configuration behaves exactly as before this change.

Two structural ideas organize the delta. First, the composite action ranking becomes a **config-assembled scoring pipeline**: scorers are instantiated in exactly one place (`ScoringPipeline.from_config`), each scorer declares its own enablement (`is_enabled(config)`), the assembled composition is logged at startup for arm auditability, and a **pure-arm kill-switch** (`pure_mode`) forces every registered steering flag off so the `pure_algorithm` arm is provably free of MOP steering ("MOP" always means *monitored operations*, never security). Second, MOP-reach knowledge expands from widget/method reachability to **component-level reachability**: `StaticAnalysisData.components` (already present in the shared core model, currently ignored by rv-agent) feeds an `activity_has_mop` predicate that powers a new frontier scorer, MOP-first launch ordering, and plateau-escape component triggering.

Concept taxonomy (flag names, weight semantics, `decision_source` values) is mirrored 1:1 with APE-RV so traces and analyses are directly comparable between the two tools; any divergence must be documented here.

## Data Contracts

### Input
- `StaticAnalysisData.components: Components` — component catalog (activities with `reachesTarget`, services, receivers, providers) produced by the rv-platform static-analysis pipeline; consumed read-only (source: `task.static_data`, `rv_platform/components/static_analysis.py:109-142`).
- `RVAgentConfig` new fields (Pydantic, `modules/rv-agent/src/rv_agent/config/agent_config.py`): `pure_mode: bool = False`, `mop_frontier_weight: float = 0.0`, `mop_activity_source_components: bool = False`, `trigger_mop_first: bool = False`, `component_trigger_enabled: bool = False`, `component_percentage: float = 0.05`, `state_mop_density_enabled: bool = False`, `form_completion_enabled: bool = False`, `seed: Optional[int] = None`, plus guard/cap fields (`foreign_activity_guard`, `back_menu_pick_cap`, `mop_target_pick_cap`, `idle_timeout_cap`, `dynamic_epsilon`, `activity_budget_enabled`).

### Output
- Trace CSV row per decision with `decision_source: str` — provenance value from the shared taxonomy (`mop`, `wtg`, `menu`, `form`, `coverage`, `component_trigger`, `llm`, `base`), precedence MOP > WTG > Menu > Form > Coverage (destination: `metrics/exporter.py` consumers; same taxonomy as the aperv `.trace`).
- Startup audit line `[RV-ARCH] scorers=[...] flags={...}` (destination: run log, arm auditability).

### Side-Effects
- **[Device]**: component triggering dispatches `am start-service` / `am broadcast` intents through the rv-uiautomator `DeviceInterface` (never `am start` for activities — those go through the normal launcher).
- **[Log]**: `pure_mode` logs every flag key it forced off.

### Error
- `ConfigurationError` — arm-defining flag not registered with the kill-switch registry at pipeline assembly (fail-fast).
- Static-data validation error — `StaticAnalysisData` missing/invalid required fields at load time (fail-fast; no silent degraded run).

## Invariants

- **INV-AGT-42**: The scoring pipeline MUST be assembled in exactly one place (`ScoringPipeline.from_config`), and the assembled composition (scorer names and effective flag values) MUST be logged at startup as a single `[RV-ARCH]` line.
- **INV-AGT-43**: When `pure_mode` is True, every flag registered as an RV steering flag MUST be forced to its off/0 value before assembly, and each forced key MUST be logged. Every arm-defining configuration field MUST be registered with the kill-switch; a completeness test MUST fail when a new arm-defining field is added without registration.
- **INV-AGT-44**: With all RV steering flags off (equivalently, `pure_mode=True`), action selection MUST be equivalent to the documented base policy — same ranking for the same fixture and seed (parity, mirror of APE-RV INV-ARCH-01).
- **INV-AGT-45**: When `mop_activity_source_components` is True, `activity_has_mop(activity)` MUST return True for every activity listed in `StaticAnalysisData.components.activities` with `reachesTarget=True`, in addition to the pre-existing widget/method reachability source.
- **INV-AGT-46**: `MopFrontierScorer` MUST add `mop_frontier_weight` only when the action's resolved target activity both satisfies `activity_has_mop` AND has no node in the dynamic state graph (unvisited). The boost is additive with, and independent of, the generic frontier boost.
- **INV-AGT-47**: When `trigger_mop_first` is True, the activity launch queue MUST order activities with `reachesTarget=True` before all others; ordering among equals is otherwise unchanged.
- **INV-AGT-48**: Component triggering MUST fire only when the plateau detector signals stagnation, MUST dispatch only non-activity components (services, receivers/broadcasts), and MUST respect the `component_percentage` cadence.
- **INV-AGT-49**: Static analysis data MUST be validated fail-fast at load; a run MUST NOT proceed silently with partially valid static data.
- **INV-AGT-50**: DIALOG-type windows MUST be re-keyed to their host activity via WTG edges before any MOP predicate or navigation lookup uses the window key.
- **INV-AGT-51**: Exploration guards and caps (foreign-activity/package guards, BACK/MENU consecutive-pick cap, MOP-target revisit cap, idle-timeout cap, per-activity action budget) MUST filter candidates before ranking, and each guard rejection MUST be counted in telemetry.
- **INV-AGT-52**: Every executed decision MUST carry exactly one `decision_source` value from the shared taxonomy with precedence MOP > WTG > Menu > Form > Coverage; the taxonomy MUST be value-identical to the aperv `.trace` taxonomy.
- **INV-AGT-53**: With `seed` set, two runs on the same APK, fixture, and configuration MUST produce identical action sequences up to device nondeterminism; all stochastic choices MUST draw from the seeded RNG.

## MODIFIED Requirements

### Requirement: Composite Action Ranking (FR27)

The strategy MUST rank available actions using a composite scoring system assembled by `ScoringPipeline.from_config(config)` — the single assembly point for scorers. Each scorer implements the `Scorer` abstract base class with a `score(action, context) -> float` method and an `is_enabled(config) -> bool` gate; disabled scorers are not instantiated into the pipeline. At startup the pipeline MUST log its composition as `[RV-ARCH] scorers=[...] flags={...}` so the active arm is auditable from the run log. Scores are summed by `ActionRanker` to determine final ranking.

When `pure_mode` is True (the `pure_algorithm` arm kill-switch), all registered RV steering flags are forced off/0 before assembly and the pipeline degenerates to the documented base policy: base-policy scorers (`ComponentPriorityScorer`, `SystemElementFilter`, `SaturationScorer`, `VisitationPenaltyScorer`, `GradualDecayScorer`, `StrengthScorer`, `CoverageDensityScorer`) remain active; MOP/WTG steering scorers are excluded.

The scorer list includes the previously registered scorers plus `GradualDecayScorer` and `CoverageDensityScorer`. `GradualDecayScorer` provides smoother priority transitions using exponential decay: `base_score * decay_rate^visits` where `base_score` = 200 and `decay_rate` = 0.7. This replaces the binary untested/tested split with a gradual signal — actions visited once still have value (200 * 0.7 = 140), twice (200 * 0.49 = 98), and so on.

`CoverageDensityScorer` provides cross-screen coverage guidance using learned transition data. While all other scorers operate on the CURRENT screen, CoverageDensityScorer answers the question "which of these actions leads to the most interesting DESTINATION?" by querying `SuccessorTracker` for action destinations and `UICoverageTracker` for destination coverage. This addresses the "small island" problem: when MOP methods represent 1-5% of app code, broad UI coverage increases the probability of reaching monitored operations, including those not mapped by static analysis. The scorer is always active (not gated on `StaticAnalysisData`), creating a dual guidance architecture where MOP targeting provides directed precision and coverage provides broad probabilistic exploration.

Three scorers ported from APE-RV branch `mop-fairtest` join the pipeline, all flag-gated and off by default:

- `MopFrontierScorer` (`mop_frontier_weight`, default 0.0 = disabled): adds the weight when the action's resolved target activity satisfies `activity_has_mop` AND is unvisited in the dynamic state graph. Additive with the generic frontier boost; the interaction of the two weights requires a local calibration smoke before cross-tool comparison.
- `StateMopDensityScorer` (`state_mop_density_enabled`): boosts by the density of MOP-flagged widgets in the target state, counting only widgets flagged by static analysis (port of INV-MOP-24 semantics).
- `FormCompletionScorer` (`form_completion_enabled`): prefers filling empty text inputs before submit actions, using a convergent filled-form predicate based on actual widget text; while the form has not converged, submit-type actions on that form are excluded from the boost.

**Default weights:**

| Scorer | Default | Rationale |
|--------|---------|-----------|
| `MopScorer` (direct) | 500 | MOP-direct actions are the primary exploration target; they MUST rank above all other scorers (deferred in Tier 2 when untested inputs exist — INV-AGT-39) |
| `MopScorer` (transitive) | 300 | MOP-transitive actions MUST outweigh WTG navigation to prevent the agent from preferring new screens over MOP paths (deferred in Tier 2 when untested inputs exist — INV-AGT-39) |
| `WtgScorer` | 150 | WTG provides a support role for screen discovery, not a primary driver |
| `SaturationScorer` | 100 | Incentivizes exploration of unsaturated states |
| `ComponentPriorityScorer` | 50/40 | Unchanged |
| `StrengthScorer` | 50 | Base score; incorporates cumulative reward from N-step propagation |
| `GradualDecayScorer` | 200 * 0.7^visits | Smooth decay across visits |
| `CoverageDensityScorer` | 200 * coverage_gap | Always active; cross-screen coverage guidance using learned transitions |
| `MopFrontierScorer` | `mop_frontier_weight` = 0.0 (disabled) | Frontier boost restricted to MOP-reaching unvisited activities; calibrate locally before use |
| `StateMopDensityScorer` | disabled | Density of MOP-flagged widgets in target state |
| `FormCompletionScorer` | disabled | Fill-before-submit with convergent predicate |
| `SystemElementFilter` | -5000 | Unchanged |
| `VisitationPenaltyScorer` | -15 | Repulsion from over-visited states |

**StrengthScorer with Cumulative Reward**: The `StrengthScorer` MUST incorporate cumulative reward data from N-step reward propagation (see N-Step Reward Propagation requirement). The scorer reads `action_cumulative_reward` from the `ScreenNode` and adds it to the existing success-rate-based score. This means actions that historically led to MOP-reaching sequences accumulate higher scores over time.

Action selection supports two modes: deterministic (always selects highest-scored action) and stochastic (Gumbel-max sampling with configurable temperature). The selection mode is chosen probabilistically based on `stochastic_probability` (default 0.15 — 15% stochastic, 85% deterministic). All stochastic draws MUST use the seeded RNG when `seed` is set (INV-AGT-53).

#### Scenario: Pipeline Assembly Audit Log

- **WHEN** `ScoringPipeline.from_config(config)` runs with `mop_frontier_weight = 250.0` and `form_completion_enabled = False`
- **THEN** the startup log MUST contain exactly one `[RV-ARCH]` line
- **AND** the line MUST list `MopFrontierScorer` among the assembled scorers and `mop_frontier_weight=250.0` among the flags
- **AND** `FormCompletionScorer` MUST NOT appear in the assembled scorer list

#### Scenario: Pure-Arm Kill-Switch Forces Steering Off

- **WHEN** `pure_mode = True` and the config also sets `mop_frontier_weight = 250.0` and `trigger_mop_first = True`
- **THEN** the pipeline MUST force `mop_frontier_weight` to 0.0 and `trigger_mop_first` to False before assembly
- **AND** the log MUST list both forced keys
- **AND** the resulting ranking on any fixture MUST equal the base-policy ranking (INV-AGT-44)

#### Scenario: Unregistered Arm-Defining Flag Fails Fast

- **WHEN** a new arm-defining config field `new_steering_weight` exists but is not registered with the kill-switch registry
- **THEN** `ScoringPipeline.from_config` MUST raise `ConfigurationError` at assembly
- **AND** the registry completeness test MUST fail until the field is registered

#### Scenario: MOP Prioritization with Updated Weights

- **WHEN** action A has `directly_reaches_target = True` and action B has `reaches_target = False`
- **THEN** `MopScorer` MUST assign +500 to A and 0 to B (default config)
- **AND** action A MUST rank higher than B (all other scores being equal)

#### Scenario: MOP-Transitive Outweighs WTG

- **WHEN** action A has `reaches_target = True` (transitive) and action B is WTG-guided to an unvisited screen
- **THEN** `MopScorer` MUST assign +300 to A
- **AND** `WtgScorer` MUST assign +150 to B
- **AND** action A MUST rank higher than B (all other scores being equal)

#### Scenario: MopFrontierScorer Conditions

- **WHEN** `mop_frontier_weight = 250.0`, action A resolves to activity "SettingsActivity" with `activity_has_mop("SettingsActivity") = True` and no node in the dynamic state graph
- **AND** action B resolves to activity "AboutActivity" with `activity_has_mop("AboutActivity") = False`
- **AND** action C resolves to "SettingsActivity" after it has been visited (node exists in the graph)
- **THEN** `MopFrontierScorer` MUST assign +250.0 to A and 0 to B and 0 to C

#### Scenario: StateMopDensityScorer Counts Only Flagged Widgets

- **WHEN** `state_mop_density_enabled = True` and the target state has 10 widgets of which 4 are flagged as MOP-reaching by static analysis
- **THEN** `StateMopDensityScorer` MUST compute density 0.4 from the 4 flagged widgets only
- **AND** unflagged widgets MUST NOT contribute to the density

#### Scenario: FormCompletionScorer Excludes Submit Until Converged

- **WHEN** `form_completion_enabled = True` and the current screen has 2 empty `EditText` fields and 1 submit `Button`
- **THEN** `FormCompletionScorer` MUST boost the fill actions on the empty fields
- **AND** the submit action MUST receive no form boost while the filled-form predicate has not converged
- **AND** after both fields contain real text, the submit action MUST become boost-eligible

#### Scenario: WTG-Guided Navigation Scoring

- **WHEN** `TransitionManager` indicates that action A leads to an unvisited screen
- **THEN** `WtgScorer` MUST assign +150 to that action (default config)

#### Scenario: GradualDecayScorer Behavior

- **WHEN** action A targets an element visited 0 times and action B targets an element visited 3 times
- **THEN** `GradualDecayScorer` MUST assign 200 to A (200 * 0.7^0)
- **AND** `GradualDecayScorer` MUST assign approximately 68.6 to B (200 * 0.7^3)

#### Scenario: Reward-Enhanced Strength Scoring

- **WHEN** action A in state S has `action_cumulative_reward` = 3.2 (from prior MOP-reaching sequences)
- **AND** action A has `success_rate` = 0.8
- **AND** `reward_score_weight` = 1.0 (default)
- **THEN** `StrengthScorer` MUST compute base score as 50 * 0.8 = 40
- **AND** MUST add the weighted cumulative reward: 40 + 1.0 * 3.2 = 43.2

#### Scenario: Stochastic Selection with Reduced Probability

- **WHEN** `stochastic_probability` = 0.15 and the seeded RNG returns a value < 0.15
- **THEN** `ActionRanker.select_stochastic()` MUST be used with `stochastic_temperature`
- **AND** the selection MUST use Gumbel-max sampling (adding Gumbel noise to log-scores) drawn from the seeded RNG

#### Scenario: Component Priority

- **WHEN** action A targets a `Button` widget and action B targets a `TextView`
- **THEN** `ComponentPriorityScorer` MUST assign +50 to A (high priority) and 0 to B (not in priority list)

#### Scenario: CoverageDensityScorer with Known Destination

- **WHEN** action A leads to a known destination screen (via SuccessorTracker) with 15 total elements and 12 untested elements (coverage_gap = 0.8)
- **AND** `coverage_density_weight` = 200
- **THEN** `CoverageDensityScorer` MUST assign 200 * 0.8 = 160 to action A

#### Scenario: CoverageDensityScorer with Unknown Destination

- **WHEN** action B has never been executed (destination unknown to SuccessorTracker)
- **AND** `coverage_density_weight` = 200
- **THEN** `CoverageDensityScorer` MUST assign 200 * 0.5 = 100 to action B (exploration bonus)

#### Scenario: CoverageDensityScorer Synergy with MopScorer

- **WHEN** action A leads to a MOP-rich screen with high coverage gap (coverage_gap = 0.8)
- **AND** `MopScorer` assigns +500 to action A (directly_reaches_target = True)
- **AND** `CoverageDensityScorer` assigns +160 to action A (200 * 0.8)
- **THEN** the combined score for action A MUST include both contributions (+660 from these two scorers)
- **AND** action A MUST rank higher than an action B with only MopScorer +500 but CoverageDensityScorer +20 (well-covered destination, coverage_gap = 0.1)

### Requirement: WTG-Guided Navigation (FR30)

rv-agent MUST use the Window Transition Graph (from GATOR static analysis) to guide exploration when `StaticAnalysisData` is available. The integration operates through three components:

1. `TransitionManager`: Integrates WTG data with `DynamicStateGraph`, mapping static window IDs to runtime activities. Provides path planning capability for the `PathBuffer` via `plan_path_to_mop_activity()`, and exposes the `activity_has_mop(activity)` predicate used by frontier scoring, launch ordering, and component triggering.
2. `NavigationGuidance`: Provides unified navigation context to both LLM and algorithm. Enriches LLM prompts with MOP-specific hints when static analysis data is available.
3. `WtgScorer`: Gives priority scores to actions that WTG indicates lead to unvisited screens.

**Component-Sourced MOP Activities (A′)**: When `mop_activity_source_components` is True, `TransitionManager` MUST additionally source MOP activities from `StaticAnalysisData.components.activities[].reachesTarget` — an activity is MOP-reaching when it appears there with `reachesTarget=True`, in addition to the pre-existing widget/method reachability source. This predicate is the shared basis for `MopFrontierScorer`, MOP-first launch ordering, and component triggering. (In APE-RV this raised the fraction of apps with at least one MOP activity from 17.8% to 83.6%.)

**DIALOG Window Re-Keying**: Before any MOP predicate or navigation lookup uses a window key, `TransitionManager` MUST re-key DIALOG-type windows to their host activity by following WTG edges (port of the APE-RV parser-fidelity change, INV-MOP-25 semantics). Without the re-key, MOP flags attached to dialog windows are invisible to activity-level predicates.

**Path Planning via BFS**: The `TransitionManager` MUST provide a `plan_path_to_mop_activity()` method that performs BFS on the WTG from the current activity to find the nearest Activity containing MOP methods. The BFS MUST use MOP density weighting: edge priority toward a target Activity is weighted by `target_methods_in_target / total_methods_in_target`. Activities with higher MOP density are preferred targets. The `mop_nav_weight` parameter (default 2.0) controls the influence of MOP density relative to path length.

**Saturation-Aware Path Preference**: When multiple BFS paths of equal MOP density exist, the `TransitionManager` MUST prefer paths through less-saturated states. This combines directed MOP navigation with opportunistic exploration of under-tested intermediate screens.

**MOP-Specific LLM Guidance**: When static analysis data is available and the execution mode includes LLM iterations (multimode or llm_only), `NavigationGuidance` MUST enrich the LLM prompt with MOP-specific context. This includes which interactive elements on the current screen lead to monitored API calls, and path descriptions toward MOP-rich Activities (e.g., "Button 'Configure Encryption' directly calls Cipher.getInstance"). This is formatted via `format_for_llm()` and passed as navigation hints.

When static data is not available, all three components gracefully degrade: `NavigationGuidance.is_enabled` returns False, `WtgScorer` returns 0 for all actions, `TransitionManager` provides empty guidance, and `plan_path_to_mop_activity()` returns None. Absence of static data is distinct from invalid static data: absence degrades gracefully, invalidity fails fast at load (INV-AGT-49).

#### Scenario: WTG Guidance Available

- **WHEN** `StaticAnalysisData` with WTG is provided
- **THEN** `NavigationGuidance.is_enabled` MUST return True
- **AND** `get_context()` MUST return an `ExplorationContext` with `has_guidance = True`

#### Scenario: WTG Guidance Unavailable

- **WHEN** `StaticAnalysisData` is None
- **THEN** `NavigationGuidance.is_enabled` MUST return False
- **AND** `get_context()` MUST return an `ExplorationContext` with `has_guidance = False`
- **AND** `format_for_llm()` MUST return an empty string
- **AND** `plan_path_to_mop_activity()` MUST return None

#### Scenario: Component-Sourced MOP Activity (A′)

- **WHEN** `mop_activity_source_components = True` and `StaticAnalysisData.components.activities` contains `{"name": "com.app.CryptoActivity", "reachesTarget": true}`
- **AND** no widget/method reachability entry exists for "com.app.CryptoActivity"
- **THEN** `activity_has_mop("com.app.CryptoActivity")` MUST return True
- **AND** with `mop_activity_source_components = False` the same call MUST return False (pre-existing source only)

#### Scenario: DIALOG Window Re-Keyed to Host Activity

- **WHEN** the WTG contains a DIALOG window "ConfirmDialog" with an edge from activity "MainActivity", and static analysis flags "ConfirmDialog" as MOP-reaching
- **THEN** `TransitionManager` MUST re-key "ConfirmDialog" to "MainActivity"
- **AND** `activity_has_mop("MainActivity")` MUST return True

#### Scenario: LLM Navigation Hint with MOP Context

- **WHEN** WTG guidance is available and there are unvisited screens reachable from the current activity
- **AND** the current screen contains elements that directly reach MOP methods
- **THEN** `format_for_llm()` MUST return a non-empty string starting with "Navigation guidance:"
- **AND** the string MUST list up to 3 unvisited screens and priority targets
- **AND** the string MUST include MOP-specific descriptions for elements that reach monitored API calls (e.g., "Button 'Security Settings' leads to Cipher.getInstance via 2 steps")
- **AND** the MOP context MUST be formatted for inclusion in `prompts/v17.py` (the MOP navigation prompt template)

#### Scenario: Algorithm WTG Scoring

- **WHEN** WTG indicates action A leads to an unvisited screen
- **THEN** `WtgScorer` MUST assign `wtg_guided_score` (default 150.0) to action A

#### Scenario: BFS Path Planning to MOP Activity

- **WHEN** `plan_path_to_mop_activity()` is called from the current activity "MainActivity"
- **AND** the WTG contains a path: MainActivity -> SettingsActivity -> SecurityActivity
- **AND** SecurityActivity contains 5 MOP methods out of 20 total methods (density = 0.25)
- **AND** another path exists: MainActivity -> AboutActivity with 1 MOP method out of 10 (density = 0.1)
- **THEN** the method MUST return the path to SecurityActivity (higher MOP density)
- **AND** the path MUST be a list of transition actions: [action_to_settings, action_to_security]

#### Scenario: MOP Density Weighting in BFS

- **WHEN** BFS finds two candidate MOP Activities at the same graph distance (2 hops each)
- **AND** Activity A has MOP density 0.3 (6 MOP methods / 20 total)
- **AND** Activity B has MOP density 0.1 (2 MOP methods / 20 total)
- **AND** `mop_nav_weight` is 2.0
- **THEN** the BFS MUST prefer the path to Activity A
- **AND** the effective priority for A MUST be higher by a factor proportional to `(0.3 / 0.1) * mop_nav_weight`

#### Scenario: Saturation-Aware Path Selection

- **WHEN** two BFS paths of equal MOP density lead to the same target Activity
- **AND** path 1 traverses through a state with saturation rate 0.9
- **AND** path 2 traverses through a state with saturation rate 0.3
- **THEN** the BFS MUST prefer path 2 (less-saturated intermediate states)

## ADDED Requirements

### Requirement: MOP-First Activity Launch Ordering with Dose Control

When `trigger_mop_first` is True, the exploration strategy MUST order the activity launch queue so that activities satisfying `activity_has_mop` (i.e., `reachesTarget=True` via the A′ predicate) are launched before all other activities; relative order within each group is unchanged. The launch policy MUST additionally support **dose control**: a configurable launch cadence, a per-run launch cap, and a **denylist** of activities whose launch failed (a denylisted activity is never re-launched in the same run). Activities are launched through the normal launcher; launch ordering never uses component-trigger intents.

#### Scenario: MOP-First Queue Ordering

- **WHEN** `trigger_mop_first = True` and the launch queue contains ["AboutActivity", "CryptoActivity", "HelpActivity"] where only "CryptoActivity" has `reachesTarget = True`
- **THEN** the effective launch order MUST be ["CryptoActivity", "AboutActivity", "HelpActivity"]
- **AND** with `trigger_mop_first = False` the original order MUST be preserved

#### Scenario: Failed Launch Enters Denylist

- **WHEN** launching "CryptoActivity" fails (activity does not reach foreground)
- **THEN** "CryptoActivity" MUST be added to the launch denylist
- **AND** subsequent launch selections in the same run MUST NOT pick "CryptoActivity"

#### Scenario: Per-Run Launch Cap

- **WHEN** the per-run launch cap is 5 and 5 direct launches have already been dispatched
- **THEN** the launch policy MUST NOT dispatch further direct launches in this run
- **AND** normal UI-driven exploration MUST continue unaffected

### Requirement: Component Triggering as Stagnation Escape

When `component_trigger_enabled` is True and the plateau detector signals exploration stagnation, the agent MUST escape by directly triggering MOP-reaching **non-activity** components from `StaticAnalysisData.components`: services via `am start-service` and receivers via `am broadcast` (using the broadcast catalog), dispatched through the rv-uiautomator `DeviceInterface` with the target package name. Activities MUST NOT be dispatched by the trigger mechanism — they are covered by the launch policy. Triggering MUST respect the `component_percentage` cadence (default 0.05) and each dispatch MUST be attributed in the decision trace with `decision_source = "component_trigger"`.

#### Scenario: Trigger Fires Only on Plateau

- **WHEN** `component_trigger_enabled = True` and `PlateauDetector` has NOT signaled stagnation
- **THEN** no component trigger MUST be dispatched
- **AND** when the detector signals stagnation, the next trigger opportunity MAY dispatch one MOP-reaching service or broadcast

#### Scenario: Activities Excluded from Triggering

- **WHEN** stagnation is signaled and `StaticAnalysisData.components` lists a MOP-reaching activity, a MOP-reaching service, and a MOP-reaching receiver
- **THEN** the trigger candidate set MUST contain only the service and the receiver

#### Scenario: Dispatch Failure Is Contained

- **WHEN** `am start-service` for service "com.app.SyncService" returns a failure
- **THEN** the agent MUST log the failure, add the component to the trigger denylist, and continue exploration
- **AND** the run MUST NOT abort

### Requirement: Static Analysis Data Fail-Fast

Static analysis data MUST be validated when loaded: required fields (`classes`, `windows`, `wtg`, `components`) are checked for structural validity, and validation failure MUST abort the run with an explicit error message identifying the invalid field. A run MUST NOT proceed silently with structurally invalid static data. Absence of static data entirely remains a supported degraded mode (WTG guidance disabled) — fail-fast applies only to present-but-invalid data.

#### Scenario: Invalid Components Field Aborts

- **WHEN** `task.static_data` is present but `components` is structurally invalid (e.g., activities entries missing the `name` field)
- **THEN** the load MUST raise a validation error naming `components`
- **AND** no exploration step MUST execute

#### Scenario: Absent Static Data Degrades Gracefully

- **WHEN** `task.static_data` is None
- **THEN** the run MUST proceed with WTG guidance disabled (existing degraded mode)

### Requirement: Exploration Guards and Caps

The strategy MUST support the following guards and caps, each individually configurable and off by default, applied as candidate filters before ranking and as policy in the LangGraph `execute`/`validation` nodes. Every guard/cap rejection MUST increment a per-guard telemetry counter.

- **Foreign-activity guard** (`foreign_activity_guard`): when the foreground activity does not belong to the target package, the agent escapes (BACK or relaunch) instead of interacting.
- **Foreign-tree guard**: UI trees whose root package is not the target package are discarded.
- **BACK/MENU pick cap** (`back_menu_pick_cap`): at most N consecutive BACK/MENU selections; when the cap is hit, BACK/MENU candidates are filtered out of the next ranking round.
- **MOP-target revisit cap** (`mop_target_pick_cap`): a MOP-reaching target already picked N times stops receiving MOP boosts.
- **Idle-timeout cap** (`idle_timeout_cap`): bounded wait on idle screens.
- **Dynamic epsilon** (`dynamic_epsilon`): exploration epsilon adapts to stagnation.
- **Per-activity action budget** (`activity_budget_enabled`): an activity that consumed its action budget is deprioritized until the frontier changes.

#### Scenario: Foreign Activity Escape

- **WHEN** `foreign_activity_guard = True` and the foreground activity belongs to package "com.android.settings" while the target package is "br.unb.cic.cryptoapp"
- **THEN** the agent MUST NOT rank or execute widget actions on the foreign screen
- **AND** the agent MUST execute an escape action (BACK or target relaunch)
- **AND** the foreign-guard telemetry counter MUST increment

#### Scenario: Consecutive BACK Cap

- **WHEN** `back_menu_pick_cap = 3` and the last 3 executed decisions were BACK selections
- **THEN** BACK and MENU candidates MUST be filtered from the next ranking round
- **AND** the filter MUST lift after one non-BACK/MENU decision executes

#### Scenario: MOP Revisit Cap Stops Boost

- **WHEN** `mop_target_pick_cap = 4` and MOP-reaching widget W has been picked 4 times
- **THEN** `MopScorer` MUST assign 0 to further actions on W
- **AND** base-policy scorers MUST continue to score W normally

### Requirement: Decision Source Telemetry

Every executed decision MUST be attributed with exactly one `decision_source` value written to the per-step trace CSV by `metrics/exporter.py`. The taxonomy and precedence are identical to the aperv `.trace` field so traces from both tools can be compared row-for-row: precedence MOP > WTG > Menu > Form > Coverage, plus `component_trigger` for stagnation-escape dispatches, `llm` for LLM-decided actions, and `base` when no steering source applied. Per-step telemetry MUST include step timing (`clock=` wall-clock attribution) and, in LLM modes, screenshot-failure counters.

#### Scenario: MOP Precedence in Attribution

- **WHEN** a decision received both a MOP boost (+500) and a WTG boost (+150)
- **THEN** the trace row MUST record `decision_source = "mop"` (highest precedence)

#### Scenario: Pure Arm Attribution

- **WHEN** `pure_mode = True` and a decision is executed
- **THEN** the trace row MUST record `decision_source = "base"` (no steering source may appear)

### Requirement: Deterministic Seed

The agent MUST accept a `seed` configuration value and thread it through every stochastic choice (stochastic selection mode, Gumbel-max sampling, epsilon draws, tie-breaking). With `seed` set, two runs on the same APK, fixtures, and configuration MUST produce identical action sequences up to device nondeterminism. Seeding is a precondition for seed-paired comparisons between arms.

#### Scenario: Same Seed, Same Sequence

- **WHEN** two offline ranking simulations run on the same fixture with `seed = 42`
- **THEN** both MUST produce the identical ranked action sequence

#### Scenario: Unset Seed Preserves Current Behavior

- **WHEN** `seed` is None
- **THEN** stochastic choices MUST behave as before this change (non-reproducible)

### Requirement: Typed Input Generation

Text input generation MUST infer the expected input type using containment matching within ±2 hierarchy levels of the input widget and token-based keyword matching (port of fair-test F: INV-MOP-23 and INV-INP-05 semantics), and generate a value of the matching type. WebView actionability thresholds MUST be computed over actionable nodes only. Per-step artifact production (screenshots, dumps) MUST be capped.

#### Scenario: Typed Value from Nearby Label

- **WHEN** an empty `EditText` has a sibling label "Email address" within 2 hierarchy levels
- **THEN** the generated input MUST be a syntactically valid email value
- **AND** keyword matching MUST operate on tokens (matching "email" in "Email address"), not on substring containment across unrelated words
