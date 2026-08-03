# Capability: aperv (delta)

## Purpose

This delta extends the `aperv` capability with the calibration arm tier: nine named `cal_a1`…`cal_a9` variants implementing the Phase-A arm table of the LLM calibration plan (`docs/20260721_plano_calibracao_llm.md` §6), all built on the `sata_mop_act_frontier` substrate, a second explicitness guard (`LLM_ARM_KEYS`) that applies only to `cal_*`-prefixed variants and requires every LLM key to be explicit, and two new `APERV_PROPERTY_MAPPING` entries (`llm_max_tokens`, `llm_snap_tolerance_px`) that become active when the Phase-B jar exposes the corresponding Java properties.

The guard closes a known gap: INV-APV-14 enforces explicitness over `ARM_DEFINING_KEYS`, but the shared `_LLM_FLAGS` dict omits `llm_percentage` and `llm_prompt_variant` — so an LLM arm could differ from another only through a key the guard does not cover. Calibration arms differ *precisely* in LLM keys, so for them every LLM key must be part of the audited surface. Extending `ARM_DEFINING_KEYS` itself was rejected: it would retroactively invalidate the frozen gh43 exemption set (INV-APV-17) and burden non-LLM arms with irrelevant keys; a `cal_*`-scoped guard is the minimal correct enforcement.

## Invariants

- **INV-APV-26**: `LLM_ARM_KEYS` MUST be a module-level `frozenset` in `tool.py` containing every LLM configuration key consumed by the Phase-A jar: `llm_url`, `llm_on_new_state`, `llm_on_stagnation`, `llm_model`, `llm_temperature`, `llm_top_p`, `llm_top_k`, `llm_timeout_ms`, `llm_percentage`, `llm_percentage_no_substrate`, `llm_prompt_variant`. Every variant whose name starts with `cal_` MUST declare every key in `LLM_ARM_KEYS` explicitly (in addition to satisfying INV-APV-14). A key the deployed jar ignores (e.g. `llm_max_tokens` before the Phase-B jar) MUST NOT be added to `LLM_ARM_KEYS`, because requiring it would fake explicitness over a dead knob.
- **INV-APV-27**: `APERV_PROPERTY_MAPPING` MUST contain `llm_max_tokens` → `ape.llmMaxTokens` and `llm_snap_tolerance_px` → `ape.llmSnapTolerancePx`. These entries are inert for arms that do not set the keys (INV-APV-08 writes only keys present in both `_tool_config` and the mapping); the Java property names follow plan §7 and are corrected in a Phase-B iteration if the `ape`-side J1 change decides differently.
- **INV-APV-28**: Calibration arms MUST be named variants; no calibration arm SHALL be expressed as a DSL `@override` of another variant (task identity strips the `@` suffix; override-only arms collide on `(apk, tool, variant, rep, timeout)` and are silently skipped on resume).

## MODIFIED Requirements

### Requirement: ApeRVTool Variants (FR20)

`ApeRVTool` SHALL define named variants organized in five tiers: base variants, MOP-arm variants, LLM
variants, prompt experiment variants, and calibration arm variants. Every variant SHALL include a
`"strategy"` key and a `"throttle_ms"` key. The `"default"` variant SHALL use strategy `"sata"`
(INV-TOOL-02).

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

#### Calibration Arm Variants (cal_*)

Nine variants implementing the Phase-A arm table of the LLM calibration plan
(`docs/20260721_plano_calibracao_llm.md` §6, rev. 3.2). All are built on the `sata_mop_act_frontier`
arm-defining substrate (MOP on, reach package A′+B+E-min ON: `mop_data="static_analysis"`,
`mop_activity_source_components=true`, `frontier_boost_weight=200`, `mop_frontier_weight=200`,
`activity_trigger_enabled=true`, the four MOP weights explicit) plus the LLM keys, as explicit dict
literals — no builder abstraction. The frontier substrate is the algorithmic configuration that won the
cmpma multi-arm comparison (cov_mop 37.75% vs ≤35%, Friedman+Holm): whenever the router does not
delegate a step to the LLM — and on every `no_match` fallback — the arm explores in frontier mode.
`sata_mop_act_frontier` without LLM keys is exactly the ANC2 anchor arm, so the paired difference
`cal_* − ANC2` isolates the LLM contribution on the same algorithmic base.

Each `cal_*` variant declares every key in `LLM_ARM_KEYS` explicitly (INV-APV-26) in addition to the
full `ARM_DEFINING_KEYS` set (INV-APV-14). Names are tool-agnostic (`cal_*`, never a tool-name prefix).
`cal_a1` is the calibration control arm: the cmp_llm_20260721 LLM-key configuration (`v13` prompt,
`llm_percentage=0.7`, temperature 0) carried onto the frontier substrate (the cmp_llm campaign itself
ran on the widget substrate — cross-substrate anchors are re-measured in-experiment by the Phase-A
design). `cal_a2`–`cal_a9` differ from `cal_a1` only in the keys listed below.

Common explicit LLM keys (all nine arms): `llm_url="http://10.0.2.2:30000/v1"`, `llm_model="default"`
(the served model is proven per task by the `[APE-LLM-CONFIG-ACK] server_model` smoke gate),
`llm_timeout_ms=15000`, `llm_percentage_no_substrate=-1`.

| Variant | Hypothesis | llm_prompt_variant | llm_percentage | llm_temperature | llm_top_p | llm_top_k | llm_on_new_state | llm_on_stagnation |
|---------|------------|--------------------|----------------|-----------------|-----------|-----------|------------------|-------------------|
| `cal_a1` | control | `v13` | `0.7` | `0` | `0.6` | `50` | `true` | `true` |
| `cal_a2` | H1 | `v13` | `0.3` | `0` | `0.6` | `50` | `true` | `true` |
| `cal_a3` | H1 (stagnation-only) | `v13` | `0` | `0` | `0.6` | `50` | `false` | `true` |
| `cal_a4` | H1 (new-state+stagnation) | `v13` | `0` | `0` | `0.6` | `50` | `true` | `true` |
| `cal_a5` | H3 (vendor bundle) | `v13` | `0.3` | `0.7` | `0.8` | `20` | `true` | `true` |
| `cal_a6` | H3 (temperature isolated) | `v13` | `0.3` | `0.7` | `0.6` | `50` | `true` | `true` |
| `cal_a7` | H3 (AutoDroid point) | `v13` | `0.3` | `0.25` | `0.6` | `50` | `true` | `true` |
| `cal_a8` | H2 (short extreme) | `visual_only` | `0.3` | `0` | `0.6` | `50` | `true` | `true` |
| `cal_a9` | H2 (long extreme) | `v17` | `0.3` | `0` | `0.6` | `50` | `true` | `true` |

Phase-B arms (`cal_b*`) are not pre-defined: they depend on Phase-A survivors and are added to
`get_variants()` under the same `LLM_ARM_KEYS` guard when Phase B is designed, deployed via the
calibration-control snapshot+bind-mount mechanism without an image rebuild.

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

#### Scenario: cal_a1 is the LLM control configuration on the frontier substrate
- **WHEN** `get_variants()["cal_a1"]` is read
- **THEN** `llm_prompt_variant == "v13"`, `llm_percentage == 0.7`, `llm_temperature == 0`, `llm_top_p == 0.6`, `llm_top_k == 50`, `llm_on_new_state == True`, `llm_on_stagnation == True`
- **AND** `mop_data` SHALL equal `"static_analysis"` and the arm-defining substrate SHALL equal the `sata_mop_act_frontier` values (`mop_activity_source_components == True`, `frontier_boost_weight == 200`, `mop_frontier_weight == 200`, `activity_trigger_enabled == True`)

#### Scenario: Every cal_* arm falls back to frontier mode when the LLM does not act
- **WHEN** `get_variants()` is iterated over every variant whose name starts with `cal_`
- **THEN** each SHALL contain the `sata_mop_act_frontier` substrate values (`mop_activity_source_components == True`, `frontier_boost_weight == 200`, `mop_frontier_weight == 200`, `activity_trigger_enabled == True`, `mop_data == "static_analysis"`)
- **AND** no `cal_*` arm SHALL carry the `sata_mop_widget` substrate (`frontier_boost_weight == 0`)

#### Scenario: cal_a3 is the stagnation-only routing regime
- **WHEN** `get_variants()["cal_a3"]` is read
- **THEN** `llm_on_new_state == False`, `llm_on_stagnation == True`, `llm_percentage == 0`
- **AND** all other `LLM_ARM_KEYS` values SHALL equal the `cal_a1` values

#### Scenario: cal_a6 vs cal_a5 isolates top_p/top_k from temperature
- **WHEN** `get_variants()["cal_a5"]` and `get_variants()["cal_a6"]` are compared
- **THEN** they SHALL differ only in `llm_top_p` (`0.8` vs `0.6`) and `llm_top_k` (`20` vs `50`)
- **AND** both SHALL have `llm_temperature == 0.7` and `llm_percentage == 0.3`

#### Scenario: Every cal_* variant declares every LLM key (LLM_ARM_KEYS guard)
- **WHEN** `get_variants()` is iterated over every variant whose name starts with `cal_`
- **THEN** each SHALL contain every key in `LLM_ARM_KEYS`
- **AND** a `cal_*` variant missing any LLM key SHALL fail the guard test with a message naming the variant and the missing keys

## ADDED Requirements

### Requirement: Calibration Property Mappings (FR20, NFR05)

`APERV_PROPERTY_MAPPING` SHALL contain the entries `llm_max_tokens` → `ape.llmMaxTokens` and
`llm_snap_tolerance_px` → `ape.llmSnapTolerancePx` (INV-APV-27). These keys are NOT members of
`LLM_ARM_KEYS` and NOT set by any `cal_a*` arm: the Phase-A jar hardcodes `max_tokens=1024` and the
snapping tolerance, so a variant setting them would declare configuration the deployed binary ignores.
The mapping entries exist so that Phase-B arms can set the keys the moment the Phase-B jar (J1/J4
changes in the `ape` repo) exposes the properties, with no further `aperv-tool` change.

#### Scenario: New mappings are present but unused by Phase-A arms
- **WHEN** `APERV_PROPERTY_MAPPING` is read
- **THEN** it SHALL map `llm_max_tokens` to `"ape.llmMaxTokens"` and `llm_snap_tolerance_px` to `"ape.llmSnapTolerancePx"`
- **AND** no `cal_a*` variant SHALL contain either key
- **AND** `ape.properties` generation for a `cal_a*` arm SHALL NOT emit `ape.llmMaxTokens` or `ape.llmSnapTolerancePx` (INV-APV-08: only keys present in both `_tool_config` and the mapping are written)
