## Purpose

This delta makes each APE-RV experiment **arm** a fully explicit, self-contained configuration. Today an
`aperv` variant is a 2-3 key dictionary and the exploration behavior of a run is decided mostly by the
jar's `Config` defaults. On the `mop-fairtest` jar those defaults include RV extensions that are ON
(`frontierBoostWeight=200`, `activityTriggerEnabled=true`) and are **not** in `APERV_PROPERTY_MAPPING`, so
they leak into every arm — the non-MOP baseline is contaminated and the paired MOP/no-MOP experiment is
confounded.

An **arm-defining flag** is a flag whose value changes what an arm *is* (MOP steering, frontier boosting,
component triggering, the RV exploration extensions, or the `apePureMode` kill-switch). The contract this
delta establishes: **an arm's identity is defined entirely by its variant dictionary, never by a jar
default.** Every non-exempt variant sets every arm-defining flag explicitly; every arm-defining flag has a
mapping entry so it actually reaches `ape.properties`. A guard pytest enforces both halves so the
invariant cannot silently rot as flags are added.

The delta also decomposes the MOP arm into `sata_mop_widget` (current widget mechanism — control),
`sata_mop_activity` (isolates reach strategy A′), and `sata_mop_act_frontier` (the reach package
A′+B+E-min, where E-min is the activity-trigger launcher), adds the `ape_pure` baseline (original APE
via the kill-switch), and wires the experiment seed into the APE-RV command so paired-by-app runs are
reproducible.

> **Reconciliation note (trigger_mop_first removed).** This delta originally included `trigger_mop_first`
> as an arm-defining flag (mapped to `ape.triggerMopFirst`, set `true` in `sata_mop_act_frontier`). The
> APE-RV `mop-census-launcher` change (merged to APE-RV `master`) **deleted `Config.triggerMopFirst`** from
> the jar — the launcher is now cadence-based and census-only, with no MOP-first ordering flag. Writing
> `ape.triggerMopFirst` to a jar that no longer reads it is inert, which would violate INV-APV-13 (every
> arm-defining key must map to a property the jar honors). `trigger_mop_first` is therefore dropped from
> `ARM_DEFINING_KEYS`, `APERV_PROPERTY_MAPPING`, and every variant. E-min in `sata_mop_act_frontier` is now
> carried solely by `activity_trigger_enabled=true`. The `rv-agent` module keeps its own independent
> `trigger_mop_first` (a different tool) and is unaffected.

The `ape.*` property names for the eleven new flags are frozen by the APE-RV sibling changes
`rv-scoring-pipeline` and `mop-reach-strategies` (branch `mop-fairtest`, design
`ape-mop-fairtest/docs/20260708_arquitetura_separacao_aperv.md` §3). The values written per arm follow the
arm matrix (design §4); baseline values equal the current `Config` defaults made explicit
(`Config.java` on `mop-fairtest`: `backMenuPickCap=3`, `mopWeightDirect=500`,
`mopWeightTransitive=300`, `mopWeightOpenMenu=250`, `mopWeightWtg=200`, the guards/typed-input all `true`).

## Data Contracts

### Input
- `variant: str` — the variant name resolved by `ToolFactory` against `get_variants()`. New names:
  `ape_pure`, `sata_mop_widget`, `sata_mop_activity`, `sata_mop_act_frontier`. Source: experiment DSL.
- `seed: int` (optional) — a per-run seed supplied via the tool DSL `@seed=<n>` or `ToolConfig.parameters`,
  merged into `_tool_config` by `ToolFactory`. Source: rv-experiment paired-run configuration.

### Output
- `ape.properties` on the device — now additionally carries the arm-defining `ape.*` lines for the flags
  present in the variant dict (via the extended `APERV_PROPERTY_MAPPING`).
- The `app_process` command — additionally carries `-s <seed>` when a seed is configured.

### Side-Effects
- **[Device]**: `ape.properties` gains one line per arm-defining flag set in the variant (RV extensions,
  MOP weights, kill-switch, reach/frontier/trigger flags).

### Error
- No new exceptions. An unknown `ape.*` property (e.g. a name mismatch against the jar) is ignored by the
  jar's `Config` loader — a configured flag that the jar does not recognize is inert, not an error.

## Invariants

- **INV-APV-13**: `APERV_PROPERTY_MAPPING` MUST contain an entry for every key in `ARM_DEFINING_KEYS`. The
  Python→Java names MUST be: `ape_pure_mode`→`ape.apePureMode`, `frontier_boost_weight`→`ape.frontierBoostWeight`,
  `activity_trigger_enabled`→`ape.activityTriggerEnabled`,
  `back_menu_pick_cap`→`ape.backMenuPickCap`, `foreign_activity_guard`→`ape.foreignActivityGuard`,
  `tree_package_guard`→`ape.treePackageGuard`, `dynamic_epsilon`→`ape.dynamicEpsilon`,
  `heuristic_input`→`ape.heuristicInput`, `fuzz_input_typed`→`ape.fuzzInputTyped`,
  `form_completion_enabled`→`ape.formCompletionEnabled`, `step_telemetry_enabled`→`ape.stepTelemetryEnabled`,
  `model_menu_enabled`→`ape.modelMenuEnabled`, `least_visited_priority_tiebreak`→`ape.leastVisitedPriorityTiebreak`,
  `tree_enhancements_enabled`→`ape.treeEnhancementsEnabled`, `activity_budget_enabled`→`ape.activityBudgetEnabled`,
  `mop_activity_source_components`→`ape.mopActivitySourceComponents`, `mop_frontier_weight`→`ape.mopFrontierWeight`,
  `llm_percentage_no_substrate`→`ape.llmPercentageNoSubstrate`. (`trigger_mop_first` was removed — the
  APE-RV jar deleted `Config.triggerMopFirst` in `mop-census-launcher`, making `ape.triggerMopFirst` inert;
  it is no longer an arm-defining key. See the Purpose note.)

- **INV-APV-14**: Every variant returned by `get_variants()` **except** the exempt ones (INV-APV-17) MUST
  set **every** key in `ARM_DEFINING_KEYS` explicitly in its dictionary. A variant MUST NOT rely on a jar
  `Config` default for any arm-defining flag.

- **INV-APV-15**: `ARM_DEFINING_KEYS` MUST be a module-level constant in `tool.py` (a `frozenset` or
  tuple), the single source of truth consumed by both the guard tests and any reviewer. Adding a new
  arm-defining flag means adding it to `ARM_DEFINING_KEYS`, to `APERV_PROPERTY_MAPPING`, and to every
  non-exempt variant — in the same commit (the guard tests fail otherwise). `mop_data` and `strategy` are
  Python-only orchestration keys and MUST NOT be in `ARM_DEFINING_KEYS`; the MOP weight keys
  (`mop_weight_direct`/`mop_weight_transitive`/`mop_weight_open_menu`/`mop_weight_wtg`) are gated by
  `mop_data` (a null `MopData` disables scoring regardless of weights) and are therefore NOT arm-defining,
  but MUST be set explicitly in the MOP arms for auditability. `max_idle_timeout_ms`
  (→ `ape.maxIdleTimeoutMs`) is likewise an arm-neutral tuning knob: it is in `APERV_PROPERTY_MAPPING` but
  NOT in `ARM_DEFINING_KEYS`, and need not be set per-variant.

- **INV-APV-16**: `get_variants()["sata_mop"]` MUST be identical to `get_variants()["sata_mop_widget"]`
  (the documented alias). Changing the widget arm MUST change the alias in lockstep (they SHOULD reference
  one shared dict).

- **INV-APV-17**: The six gh43 prompt-experiment variants (`sata_mop_llm_ape_current`,
  `sata_mop_llm_ape_reasoning`, `sata_mop_llm_compact_v1`, `sata_mop_llm_v13`, `sata_mop_llm_v17`,
  `sata_mop_llm_visual_only`) are **frozen for historical reproducibility** and are EXEMPT from INV-APV-14.
  The exemption set MUST be an explicit, named constant so the guard test enumerates it deliberately (not a
  prefix match that could silently absorb a future non-exempt `sata_mop_llm_*` arm).

- **INV-APV-18**: When a `seed` is present in `_tool_config`, `_build_main_command` MUST append `-s <seed>`
  to the `app_process` argument vector (after `--ape <strategy>`). When no seed is configured, the command
  MUST NOT include `-s` (preserving the current non-deterministic default). The seed value is passed
  verbatim as a string. The `mop-fairtest` jar honors this seed (it parses `-s SEED` and seeds both
  `Monkey.mRandom` and APE's `RandomHelper`, INV-EXPL-14); this invariant closes the rv-android-side gap
  that previously dropped the seed.

- **INV-APV-19**: Introducing a new arm-defining APE-RV flag into `aperv-tool` MUST, in the same commit,
  (a) add the Python key to `ARM_DEFINING_KEYS`, (b) add its `APERV_PROPERTY_MAPPING` entry, and (c) set it
  explicitly in every non-exempt variant. INV-APV-13 and INV-APV-14 are the executable enforcement of this
  policy.

## MODIFIED Requirements

### Requirement: ApeRVTool Variants (FR20)

`ApeRVTool` SHALL define named variants organized in four tiers: base variants, MOP-arm variants, LLM
variants, and prompt experiment variants. Every variant SHALL include a `"strategy"` key and a
`"throttle_ms"` key. The `"default"` variant SHALL use strategy `"sata"` (INV-TOOL-02).

Every variant **except** the exempt prompt-experiment variants (INV-APV-17) SHALL set every key in
`ARM_DEFINING_KEYS` explicitly (INV-APV-14) so the arm's behavior is defined by the variant dictionary and
never by a jar `Config` default. Baseline arms (`default`/`sata`, `bfs`, `random`) SHALL set the RV
exploration flags to the current jar defaults made explicit (`back_menu_pick_cap=3`,
`foreign_activity_guard=true`, `tree_package_guard=true`, `dynamic_epsilon=true`,
`heuristic_input=true`, `fuzz_input_typed=true`, `form_completion_enabled=true`, `step_telemetry_enabled=true`,
`model_menu_enabled=true`, `least_visited_priority_tiebreak=true`, `tree_enhancements_enabled=true`,
`activity_budget_enabled=true`, `llm_percentage_no_substrate=-1`) and the MOP/reach/frontier flags
OFF (`ape_pure_mode=false`, `frontier_boost_weight=0`, `activity_trigger_enabled=false`,
`mop_activity_source_components=false`, `mop_frontier_weight=0`).

#### Base Variants

| Variant | strategy | mop_data | ape_pure_mode | RV exploration flags | frontier_boost_weight | activity_trigger_enabled | Notes |
|---------|----------|----------|---------------|----------------------|-----------------------|--------------------------|-------|
| `default` | `"sata"` | -- | `false` | ON (defaults explicit) | `0` | `false` | Alias for sata |
| `sata` | `"sata"` | -- | `false` | ON (defaults explicit) | `0` | `false` | aperv baseline, RV exploration ON, MOP off |
| `bfs` | `"bfs"` | -- | `false` | ON (defaults explicit) | `0` | `false` | Breadth-first baseline |
| `random` | `"random"` | -- | `false` | ON (defaults explicit) | `0` | `false` | Priority-weighted random baseline |
| `ape_pure` | `"sata"` | -- | `true` | **OFF (all explicit)** | `0` | `false` | Original APE via kill-switch; every RV flag off/0 |

`ape_pure` SHALL set `ape_pure_mode=true` **and** set every other arm-defining flag to its off/zero value
explicitly (defense-in-depth: the jar kill-switch forces RV off, and the explicit offs keep the guard test
uniform and the arm auditable without trusting the kill-switch). `ape_pure` SHALL NOT set `mop_data`.

#### MOP-Arm Variants

The MOP arms decompose the reach mechanism. All set `mop_data="static_analysis"` and the four MOP weights
explicitly (`mop_weight_direct=500`, `mop_weight_transitive=300`, `mop_weight_open_menu=250`,
`mop_weight_wtg=200`) and keep the full RV exploration baseline ON.

| Variant | mop_activity_source_components (A′) | frontier_boost_weight | mop_frontier_weight (B) | activity_trigger_enabled (E-min) | Notes |
|---------|-------------------------------------|-----------------------|-------------------------|----------------------------------|-------|
| `sata_mop_widget` | `false` | `0` | `0` | `false` | Current widget mechanism (MOP control) |
| `sata_mop_activity` | `true` | `0` | `0` | `false` | Isolates strategy A′ |
| `sata_mop_act_frontier` | `true` | `200` | `200` | `true` | Reach package A′+B+E-min |
| `sata_mop` | — alias of `sata_mop_widget` (identical dict, INV-APV-16) — | | | | Back-compat name |

The `mop_frontier_weight=200` value for `sata_mop_act_frontier` is a calibration starting point (design
§4: "≈200, calibrate in smoke"); calibration smokes use the DSL override
(`aperv:sata_mop_act_frontier@mop_frontier_weight=400`) and do not require a new variant.

#### LLM Variants

LLM variants add LLM-guided action selection. `llm_url` uses `http://10.0.2.2:30000/v1` (emulator host
loopback), overridable via `APERV_LLM_BASE_URL`. They set the full arm-defining set explicitly:
`sata_llm` on the `sata` baseline (MOP off), `sata_mop_llm` on the `sata_mop_widget` substrate (MOP on).

| Variant | mop_data | Arm-defining baseline | Notes |
|---------|----------|-----------------------|-------|
| `sata_llm` | -- | `sata` (MOP off) | SATA + LLM |
| `sata_mop_llm` | `"static_analysis"` | `sata_mop_widget` (MOP on) | SATA + MOP + LLM (round-2 base) |

LLM variants also include sampling parameters: `llm_model="default"`, `llm_temperature=0.3`,
`llm_top_p=0.6`, `llm_top_k=50`, `llm_timeout_ms=15000`.

#### Prompt Experiment Variants (FROZEN / EXEMPT — INV-APV-17)

Six variants for controlled prompt ablation (gh43). All use SATA + MOP + LLM with `llm_percentage=0.7` and
differ only in `llm_prompt_variant`. They are **frozen exactly as authored** and are EXEMPT from the
arm-defining explicitness policy (INV-APV-14) to preserve historical reproducibility.

| Variant | llm_prompt_variant |
|---------|--------------------|
| `sata_mop_llm_ape_current` | `ape_current` |
| `sata_mop_llm_ape_reasoning` | `ape_reasoning` |
| `sata_mop_llm_compact_v1` | `compact_v1` |
| `sata_mop_llm_v13` | `v13` |
| `sata_mop_llm_v17` | `v17` |
| `sata_mop_llm_visual_only` | `visual_only` |

#### Scenario: Baseline sata arm disables RV steering explicitly
- **WHEN** `get_variants()["sata"]` is read
- **THEN** it SHALL contain `frontier_boost_weight == 0` and `activity_trigger_enabled == False` explicitly
- **AND** it SHALL contain every key in `ARM_DEFINING_KEYS`
- **AND** it SHALL NOT contain a `mop_data` key

#### Scenario: ape_pure arm sets the kill-switch and every RV flag off
- **WHEN** `get_variants()["ape_pure"]` is read
- **THEN** `ape_pure_mode` SHALL be `True`
- **AND** every other key in `ARM_DEFINING_KEYS` SHALL be present with its off/zero value (e.g. `dynamic_epsilon == False`, `form_completion_enabled == False`, `model_menu_enabled == False`, `tree_enhancements_enabled == False`)
- **AND** `mop_data` SHALL NOT be present

#### Scenario: sata_mop_widget is the MOP control arm
- **WHEN** `get_variants()["sata_mop_widget"]` is read
- **THEN** `mop_data` SHALL equal `"static_analysis"`
- **AND** `mop_weight_direct == 500`, `mop_weight_transitive == 300`, `mop_weight_open_menu == 250`, `mop_weight_wtg == 200`
- **AND** `mop_activity_source_components == False`, `frontier_boost_weight == 0`, `mop_frontier_weight == 0`, `activity_trigger_enabled == False`
- **AND** `trigger_mop_first` SHALL NOT be present (removed — jar deleted the property)

#### Scenario: sata_mop_activity isolates strategy A′
- **WHEN** `get_variants()["sata_mop_activity"]` is read
- **THEN** it SHALL differ from `sata_mop_widget` only by `mop_activity_source_components == True`
- **AND** all other arm-defining keys SHALL equal the `sata_mop_widget` values

#### Scenario: sata_mop_act_frontier enables the reach package
- **WHEN** `get_variants()["sata_mop_act_frontier"]` is read
- **THEN** `mop_activity_source_components == True`, `frontier_boost_weight == 200`, `mop_frontier_weight == 200`, `activity_trigger_enabled == True`
- **AND** `mop_data` SHALL equal `"static_analysis"`
- **AND** `trigger_mop_first` SHALL NOT be present (E-min is carried by `activity_trigger_enabled` alone)

#### Scenario: sata_mop is an alias of sata_mop_widget
- **WHEN** `get_variants()["sata_mop"]` and `get_variants()["sata_mop_widget"]` are compared
- **THEN** the two dictionaries SHALL be equal (INV-APV-16)

#### Scenario: Every non-exempt variant sets every arm-defining key (guard)
- **WHEN** `get_variants()` is iterated over every variant whose name is NOT in the exempt set (the six `sata_mop_llm_<prompt>` variants)
- **THEN** each such variant SHALL contain every key in `ARM_DEFINING_KEYS`
- **AND** a variant missing any arm-defining key SHALL fail the guard test with a message naming the variant and the missing keys

#### Scenario: Creating tool with a new MOP arm variant
- **WHEN** `ToolFactory.create_tool(ToolConfig(name="aperv", variant="sata_mop_act_frontier"))` is called
- **THEN** the factory SHALL return a configured `ApeRVTool` instance
- **AND** `tool._tool_config["mop_data"]` SHALL be `"static_analysis"`
- **AND** `tool._tool_config["activity_trigger_enabled"]` SHALL be `True`

---

### Requirement: ape.properties Generation

`ApeRVTool._push_properties()` SHALL generate an `ape.properties` file from `_tool_config` using
`APERV_PROPERTY_MAPPING` and push it to `/data/local/tmp/ape.properties` on the device. Only keys present
in both `_tool_config` and `APERV_PROPERTY_MAPPING` are written; Python-only keys (`strategy`, `mop_data`,
`seed`) have no mapping entry and are excluded automatically.

`APERV_PROPERTY_MAPPING` SHALL contain an entry for every arm-defining key (INV-APV-13), so that a flag set
in a variant dictionary actually reaches the device. The mapping translates Python config keys to Java
property names:

| Python Key | Java Property | Category |
|------------|--------------|----------|
| `throttle_ms` | `ape.defaultGUIThrottle` | Exploration |
| `default_epsilon` | `ape.defaultEpsilon` | Exploration |
| `graph_stable_restart_threshold` | `ape.graphStableRestartThreshold` | Exploration |
| `state_stable_restart_threshold` | `ape.stateStableRestartThreshold` | Exploration |
| `fuzzing_rate` | `ape.fuzzingRate` | Exploration |
| `do_fuzzing` | `ape.doFuzzing` | Exploration |
| `throttle_for_activity_transition` | `ape.throttleForActivityTransition` | Exploration |
| `max_extra_priority_aliased_actions` | `ape.maxExtraPriorityAliasedActions` | Exploration |
| `max_states_per_activity` | `ape.maxStatesPerActivity` | Exploration |
| `trivial_activity_rank_threshold` | `ape.trivialActivityRankThreshold` | Exploration |
| `do_back_to_trivial_activity` | `ape.doBackToTrivialActivity` | Exploration |
| `back_menu_pick_cap` | `ape.backMenuPickCap` | RV exploration (arm-defining) |
| `max_idle_timeout_ms` | `ape.maxIdleTimeoutMs` | arm-neutral (global tuning knob) |
| `foreign_activity_guard` | `ape.foreignActivityGuard` | RV exploration (arm-defining) |
| `tree_package_guard` | `ape.treePackageGuard` | RV exploration (arm-defining) |
| `dynamic_epsilon` | `ape.dynamicEpsilon` | RV exploration (arm-defining) |
| `heuristic_input` | `ape.heuristicInput` | RV exploration (arm-defining) |
| `fuzz_input_typed` | `ape.fuzzInputTyped` | RV exploration (arm-defining) |
| `form_completion_enabled` | `ape.formCompletionEnabled` | RV exploration (arm-defining) |
| `step_telemetry_enabled` | `ape.stepTelemetryEnabled` | RV exploration (arm-defining) |
| `model_menu_enabled` | `ape.modelMenuEnabled` | RV exploration (arm-defining) |
| `least_visited_priority_tiebreak` | `ape.leastVisitedPriorityTiebreak` | RV exploration (arm-defining) |
| `tree_enhancements_enabled` | `ape.treeEnhancementsEnabled` | RV exploration (arm-defining) |
| `activity_budget_enabled` | `ape.activityBudgetEnabled` | RV exploration (arm-defining) |
| `ape_pure_mode` | `ape.apePureMode` | Kill-switch (arm-defining) |
| `mop_weight_direct` | `ape.mopWeightDirect` | MOP |
| `mop_weight_transitive` | `ape.mopWeightTransitive` | MOP |
| `mop_weight_activity` | `ape.mopWeightActivity` | MOP (inert; back-compat) |
| `mop_weight_open_menu` | `ape.mopWeightOpenMenu` | MOP |
| `mop_weight_wtg` | `ape.mopWeightWtg` | MOP |
| `mop_activity_source_components` | `ape.mopActivitySourceComponents` | MOP reach A′ (arm-defining) |
| `mop_frontier_weight` | `ape.mopFrontierWeight` | MOP reach B (arm-defining) |
| `frontier_boost_weight` | `ape.frontierBoostWeight` | Frontier (arm-defining) |
| `activity_trigger_enabled` | `ape.activityTriggerEnabled` | Component triggering / MOP reach E-min (arm-defining) |
| `component_percentage` | `ape.componentPercentage` | Component triggering |
| `mop_target_pick_cap` | `ape.mopTargetPickCap` | MOP |
| `coverage_boost_weight` | `ape.coverageBoostWeight` | Coverage |
| `llm_url` | `ape.llmUrl` | LLM |
| `llm_on_new_state` | `ape.llmOnNewState` | LLM |
| `llm_on_stagnation` | `ape.llmOnStagnation` | LLM |
| `llm_model` | `ape.llmModel` | LLM |
| `llm_temperature` | `ape.llmTemperature` | LLM |
| `llm_top_p` | `ape.llmTopP` | LLM |
| `llm_top_k` | `ape.llmTopK` | LLM |
| `llm_timeout_ms` | `ape.llmTimeoutMs` | LLM |
| `llm_percentage` | `ape.llmPercentage` | LLM |
| `llm_percentage_no_substrate` | `ape.llmPercentageNoSubstrate` | LLM seam F′ (arm-defining) |
| `llm_prompt_variant` | `ape.llmPromptVariant` | LLM |

When `mop_json_pushed` is True, the properties file SHALL also include
`ape.mopDataPath=/data/local/tmp/static_analysis.json` (hardcoded device path matching the push
destination). An `ape.*` key the jar does not recognize is ignored by the jar's `Config` loader (a
name-mismatch is inert, not an error).

#### Scenario: Arm-defining flags appear in properties for a baseline arm
- **WHEN** `_push_properties()` is called for the `sata` variant
- **THEN** the generated properties file SHALL contain `ape.frontierBoostWeight=0`
- **AND** it SHALL contain `ape.activityTriggerEnabled=false`
- **AND** it SHALL contain `ape.dynamicEpsilon=true`
- **AND** it SHALL NOT contain `ape.mopDataPath`

#### Scenario: Kill-switch flag appears in properties for ape_pure
- **WHEN** `_push_properties()` is called for the `ape_pure` variant
- **THEN** the generated properties file SHALL contain `ape.apePureMode=true`
- **AND** it SHALL contain `ape.frontierBoostWeight=0` and `ape.activityTriggerEnabled=false`

#### Scenario: Reach-package flags appear in properties for sata_mop_act_frontier
- **WHEN** `_push_properties()` is called for `sata_mop_act_frontier` with `mop_json_pushed=True`
- **THEN** the properties file SHALL contain `ape.mopActivitySourceComponents=true`
- **AND** it SHALL contain `ape.mopFrontierWeight=200` and `ape.activityTriggerEnabled=true`
- **AND** it SHALL contain `ape.mopDataPath=/data/local/tmp/static_analysis.json`
- **AND** it SHALL NOT contain `ape.triggerMopFirst` (property removed)

#### Scenario: Python-only keys are still excluded
- **WHEN** `_push_properties()` is called for a variant whose `_tool_config` contains `strategy`, `mop_data`, and `seed`
- **THEN** the properties file SHALL NOT contain `strategy`, `mop_data`, or `seed`

---

## ADDED Requirements

### Requirement: Arm-Defining Flag Completeness (FR20)

`aperv-tool` SHALL declare a module-level constant `ARM_DEFINING_KEYS` in `tool.py` enumerating every
Python config key whose value defines an experiment arm (INV-APV-15). A guard test suite SHALL enforce two
properties so an arm's identity can never silently fall back to a jar default:

1. **Mapping completeness (INV-APV-13)**: every key in `ARM_DEFINING_KEYS` has an entry in
   `APERV_PROPERTY_MAPPING`.
2. **Variant explicitness (INV-APV-14)**: every variant returned by `get_variants()`, except the exempt
   gh43 prompt-experiment variants (INV-APV-17), sets every key in `ARM_DEFINING_KEYS` explicitly.

The exempt set SHALL be an explicit named constant (not a prefix match), so a future non-exempt
`sata_mop_llm_*` arm is not silently absorbed (INV-APV-17). Introducing a new arm-defining flag SHALL
require updating `ARM_DEFINING_KEYS`, `APERV_PROPERTY_MAPPING`, and every non-exempt variant in the same
commit (INV-APV-19) — the guard tests are the executable enforcement.

`mop_data` and `strategy` are Python-only orchestration keys and SHALL NOT be members of
`ARM_DEFINING_KEYS`. The four MOP weight keys are gated by `mop_data` (a null `MopData` disables scoring
regardless of weight) and SHALL NOT be members of `ARM_DEFINING_KEYS`, but SHALL be set explicitly in the
MOP arms for auditability.

#### Scenario: Every arm-defining key is mapped
- **WHEN** the guard test iterates `ARM_DEFINING_KEYS`
- **THEN** every key SHALL be present in `APERV_PROPERTY_MAPPING`
- **AND** a key absent from the mapping SHALL fail the test naming the offending key

#### Scenario: Every non-exempt variant is explicit
- **WHEN** the guard test iterates `get_variants()` excluding the six named gh43 prompt-experiment variants
- **THEN** each remaining variant SHALL contain every key in `ARM_DEFINING_KEYS`
- **AND** the failure message SHALL name the variant and the missing arm-defining keys

#### Scenario: Exempt variants are skipped deliberately
- **WHEN** the guard test computes the exempt set
- **THEN** it SHALL be the explicit constant naming exactly the six `sata_mop_llm_<prompt>` variants
- **AND** the six exempt variants SHALL NOT be required to set `ARM_DEFINING_KEYS`

#### Scenario: mop_data and strategy are not arm-defining keys
- **WHEN** the guard test inspects `ARM_DEFINING_KEYS`
- **THEN** it SHALL NOT contain `mop_data` or `strategy`

---

### Requirement: Seed Propagation to APE-RV (FR18, FR19)

`ApeRVTool._build_main_command()` SHALL append `-s <seed>` to the `app_process` argument vector when a
`seed` key is present in `_tool_config` (INV-APV-18). The seed reaches `_tool_config` via the tool DSL
(`aperv:<variant>@seed=<n>`) or `ToolConfig.parameters`, merged by `ToolFactory`. When no seed is
configured, the command SHALL NOT include `-s`, preserving the current default where the jar self-seeds
non-deterministically.

The `mop-fairtest` APE-RV jar already honors a passed seed: `Monkey` parses `-s SEED`
(`Monkey.java:886-887`), and when `mSeed != 0` it seeds both `Monkey.mRandom` and APE's `RandomHelper`
(`Monkey.java:731`, `RandomHelper.seed(mSeed)`, INV-EXPL-14) — so a fixed seed makes a run reproducible.
The rv-android-side gap (the command never emitting `-s`) is what this requirement closes; no jar change
is required.

#### Scenario: Seed configured is passed as -s
- **WHEN** `_build_main_command(app, "emulator-5554", 60)` is called with `_tool_config` containing `seed=42`
- **THEN** the command argument vector SHALL contain `-s` immediately followed by `"42"`
- **AND** the `-s 42` pair SHALL appear after `--ape <strategy>`

#### Scenario: No seed configured omits -s
- **WHEN** `_build_main_command(app, "emulator-5554", 60)` is called with `_tool_config` containing no `seed` key
- **THEN** the command argument vector SHALL NOT contain `-s`

#### Scenario: Seed is not written to ape.properties
- **WHEN** `_push_properties()` is called for a variant whose `_tool_config` contains `seed=42`
- **THEN** the generated properties file SHALL NOT contain a `seed` line (it is a CLI-only, Python-only key)
