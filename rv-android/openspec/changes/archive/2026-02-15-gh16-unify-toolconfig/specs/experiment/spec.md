## MODIFIED Requirements

### Requirement: Experiment Configuration (FR15)

The experiment layer MUST provide a validated `ExperimentConfig` (Pydantic model) that aggregates all parameters needed for a complete experiment run. This config is built from CLI arguments or loaded from a JSON file via `--config`.

`ExperimentConfig` stores `tool_configs` as a list of `ToolConfig` objects imported from `rv_android_core.domain.task`. Each ToolConfig has `variant: str` (singular) representing one tool+variant pair. When the CLI receives a multi-variant specification like `droidbot:dfs_greedy:bfs_greedy`, the CLI parser expands it into two separate ToolConfig instances before constructing ExperimentConfig.

`ExperimentConfig.from_dict()` deserializes JSON using the current field names only. Per P3 (No Backward Compatibility), old JSON configs using `"variants": [...]` (plural list) are not supported — users must update their JSON files to use the new format with `"variant": "..."` (singular string) and one entry per tool+variant pair.

#### Scenario: CLI variant expansion at parse time

- **WHEN** the CLI receives `--tools droidbot:dfs_greedy:bfs_greedy`
- **THEN** the parser MUST create 2 ToolConfig instances: `ToolConfig(name="droidbot", variant="dfs_greedy")` and `ToolConfig(name="droidbot", variant="bfs_greedy")`
- **AND** both instances MUST be stored in `ExperimentConfig.tool_configs`

#### Scenario: JSON config auto-save on experiment run

- **WHEN** `ExperimentController.run()` is invoked
- **THEN** `save_experiment_config()` MUST be called to save the full configuration as `experiment_config.json` in the experiment results directory
- **AND** the saved JSON MUST use the unified ToolConfig format (with `variant: str`, not `variants: List[str]`)
- **AND** the saved config MUST be loadable via `rv-experiment run --config <path>`

#### Scenario: JSON config round-trip

- **WHEN** an experiment is run via CLI, producing `results/<name>/experiment_config.json`
- **AND** that JSON file is used with `rv-experiment run --config results/<name>/experiment_config.json`
- **THEN** the loaded ExperimentConfig MUST produce the same task set as the original CLI run
