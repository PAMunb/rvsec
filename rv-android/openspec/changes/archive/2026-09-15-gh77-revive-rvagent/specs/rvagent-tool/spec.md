# Delta Spec: rvagent-tool — gh77-revive-rvagent (new capability)

## Purpose

`rvagent-tool` (`modules/rvagent-tool/`) is the rv-platform plugin that wraps rv-agent as an `AbstractTool`, making it invocable as `--tools rvagent:<variant>` through rv-experiment/rv-platform. This capability spec covers the plugin contract for the **revived** rv-agent: the variant families and their hygiene rules, the deterministic-seed and teardown lifecycle, and static-data fail-fast at configure time. It mirrors the structure of the existing `aperv` capability spec (the plugin for the APE-RV jar), because the two plugins implement the same experimental-arm discipline and their variants must remain methodologically comparable.

The central policy is **explicit arms**: a variant is an experimental arm, and arms must never inherit defaults. Every frozen variant sets ALL arm-defining configuration keys explicitly, and a guard test suite enforces this mechanically. This policy exists because implicit inheritance caused a real contamination incident in the aperv plugin (arms silently inherited `frontierBoostWeight`/`activityTriggerEnabled` from defaults, invalidating a comparison). The revived rv-agent adopts the same protection from day one, together with the agent-side `pure_mode` kill-switch (see the agent delta spec, INV-AGT-43/44) so the `pure_algorithm` arm does not depend on the plugin enumerating every steering key.

Variant naming is **arm-neutral**: variants and prompt identifiers use tool-agnostic names (`v13`, `v17`, `pure_algorithm`, ...), never lineage-prefixed names. LLM arms (`llm_only`, `multimode`) are kept isolated from steering arms: no variant mixes new MOP steering flags with LLM decision-making in the same arm definition unless explicitly frozen as a named combined arm, because LLM latency contaminates steering measurements. There are no artificial limits on LLM call counts in any arm (project policy). Registration with rv-platform is unchanged and stays governed by the tools capability (INV-TOOL-12 idempotent external registration).

The revived tool is a **local-executions-only** experimental arm: it runs via `rv-experiment run --tools rvagent:<variant>` against `apks_examples/` with the platform managing the emulator lifecycle; it does not participate in scale experiments.

## Data Contracts

### Input
- `Task.config` — merged tool configuration from the platform: variant dict merged with CLI `@param=value` overrides; timeout is ALWAYS controlled by `Task.config` (gh75 `--timeouts` compatible).
- `task.static_data: StaticAnalysisData` — shared core model populated by the platform's `StaticAnalysisComponent`; consumed via `get_static_data(task)` in `rvagent_tool/tools/rvagent/config.py`.
- `seed: Optional[int]` — deterministic seed passed through to `RVAgentConfig`.

### Output
- Tool execution results per the `AbstractTool` contract (`rv_android_core/tools/abstract_tool.py:86-136`): logs, trace CSV (with `decision_source`), coverage artifacts under the task result directory.

### Side-Effects
- **[Device]**: exploration session on the platform-managed emulator (UIAutomator2); teardown (agent stop, device client release) ALWAYS runs in a `finally` block.
- **[Filesystem]**: screenshots and trace artifacts under the task result directory, capped per step.

### Error
- `ConfigurationError` — variant missing an arm-defining key, unknown variant, or invalid merged config (fail-fast at `configure`).
- Static-data validation error — present-but-invalid `task.static_data` at configure time (fail-fast; absent static data degrades gracefully per the agent spec).

## Invariants

- **INV-RVA-01**: Every frozen variant returned by `get_variants()` MUST set every arm-defining configuration key explicitly. Arms MUST NOT rely on `RVAgentConfig` defaults for any arm-defining key.
- **INV-RVA-02**: Every arm-defining key MUST have an entry in the variant→`RVAgentConfig` mapping, and the mapping MUST NOT contain keys that no variant or CLI override can set. A guard pytest MUST enforce INV-RVA-01 and INV-RVA-02 (aperv-tool pattern, `modules/aperv-tool/tests/test_aperv_tool.py`).
- **INV-RVA-03**: The `pure_algorithm` variant MUST set `pure_mode = True`; combined with agent-side INV-AGT-43, this makes the pure arm independent of key enumeration in the plugin.
- **INV-RVA-04**: LLM arms and steering arms MUST be separate variant families: `llm_only` and `multimode` MUST NOT enable MOP steering flags introduced by this change, and steering variants MUST NOT enable LLM decision-making, unless a combined arm is explicitly frozen under its own name. No variant may impose an artificial LLM call limit.
- **INV-RVA-05**: Tool teardown (agent shutdown, device client release, artifact flush) MUST execute in a `finally` block — it runs on success, on timeout, and on any exception.
- **INV-RVA-06**: Variant and prompt naming MUST be arm-neutral (tool-agnostic identifiers such as `v13`, `v17`); lineage-prefixed names MUST NOT be introduced.

## ADDED Requirements

### Requirement: Variant Families with Explicit Arm-Defining Keys (FR20)

`RVAgentTool.get_variants()` MUST return frozen variants organized in two families: steering arms (at minimum `pure_algorithm`; additional steering arms are frozen after the local calibration smoke) and LLM arms (`llm_only`, `multimode`). Each variant dict MUST set every arm-defining key explicitly — arm-defining keys are those whose value distinguishes experimental arms: `pure_mode`, all MOP steering flags/weights (`mop_frontier_weight`, `mop_activity_source_components`, `trigger_mop_first`, `component_trigger_enabled`, `state_mop_density_enabled`, `form_completion_enabled`, guards/caps), and LLM routing keys (mode, proportions, prompt version). Defaults in `get_variants()` follow the L2 pattern: URL/path/model defaults live in the variant dicts, `configure()` reads the merged dict, and no `os.environ` access happens at the tool layer.

#### Scenario: pure_algorithm Sets the Kill-Switch

- **WHEN** `get_variants()["pure_algorithm"]` is inspected
- **THEN** it MUST contain `pure_mode: True`
- **AND** it MUST contain an explicit off/0 value for every MOP steering key (e.g., `mop_frontier_weight: 0.0`, `trigger_mop_first: False`)

#### Scenario: Guard Test Rejects Incomplete Variant

- **WHEN** a developer adds arm-defining key `state_mop_density_enabled` to the mapping but omits it from the `multimode` variant
- **THEN** the guard pytest (every variant sets every arm-defining key) MUST fail
- **AND** the failure message MUST name the variant and the missing key

#### Scenario: Guard Test Rejects Unmapped Key

- **WHEN** a variant sets a key `mop_frontier_weight` that has no entry in the variant→`RVAgentConfig` mapping
- **THEN** the mapping-completeness guard test MUST fail

#### Scenario: LLM and Steering Arms Are Isolated

- **WHEN** `get_variants()["llm_only"]` and `get_variants()["multimode"]` are inspected
- **THEN** every MOP steering flag introduced by gh77 MUST be explicitly off/0 in both
- **AND** no variant MUST contain an LLM call-count limit key

### Requirement: Deterministic Seed and Teardown Lifecycle (FR19)

The tool MUST accept a `seed` parameter (via variant or CLI `@seed=N` override) and pass it through to `RVAgentConfig.seed` unchanged. The tool's execute path MUST perform teardown in a `finally` block: stopping the agent session, releasing the UIAutomator2 device client, and flushing trace/metric artifacts happen regardless of success, timeout, or exception. Timeout remains controlled exclusively by `Task.config` (the tool never overrides it).

#### Scenario: Seed Pass-Through

- **WHEN** the tool is invoked as `rvagent:pure_algorithm@seed=42`
- **THEN** the `RVAgentConfig` handed to rv-agent MUST have `seed = 42`

#### Scenario: Teardown Runs on Exception

- **WHEN** `execute_tool_specific_logic` raises midway through an exploration session
- **THEN** the agent session MUST still be stopped and the device client released
- **AND** partial trace artifacts MUST still be flushed to the task result directory

### Requirement: Static Data Fail-Fast at Configure (FR19)

When `task.static_data` is present, the tool MUST validate it at configure time (before the exploration session starts) and abort the task with an explicit error naming the invalid field when validation fails. When `task.static_data` is absent, the tool MUST proceed in the degraded no-guidance mode defined by the agent capability. This mirrors the agent-side INV-AGT-49 at the plugin boundary so a misconfigured pre-processing pipeline is caught before any device time is spent.

#### Scenario: Invalid Static Data Aborts Before Session

- **WHEN** `task.static_data` is present but its `wtg` field is structurally invalid
- **THEN** `configure` MUST raise a validation error naming `wtg`
- **AND** no emulator interaction MUST occur for this task

#### Scenario: Absent Static Data Proceeds Degraded

- **WHEN** `task.static_data` is None
- **THEN** the tool MUST start the session with WTG guidance disabled
