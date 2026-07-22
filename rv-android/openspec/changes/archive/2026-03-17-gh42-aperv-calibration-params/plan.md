# Change Plan: aperv-tool calibration parameters support

**Date**: 2026-03-17
**Track**: Quick Path
**Priority**: Normal
**GitHub Issue**: [#42](https://github.com/PAMunb/rvsec/issues/42)
**PRD Reference**: FR18 (Tool Plugin System), FR19 (Tool Configuration)
**Domains**: tools (aperv-tool)

## 1. Context

The APE-RV Java side (`Config.java`) already reads all calibratable parameters from `ape.properties` at startup via `Config.getXxx("ape.keyName", default)`. The rv-platform `@param=value` DSL also already parses and merges arbitrary parameters into the tool config (`ToolFactory` line 121: `{**variant_config, **tool_config.parameters}`).

The missing link is the Python-side `aperv-tool`: `_push_properties()` only writes `throttle_ms` and 9 LLM keys to `ape.properties`. Exploration parameters (e.g., `defaultEpsilon`, `graphStableRestartThreshold`) and MOP weights (e.g., `mopWeightDirect`) are silently dropped — even when passed via the DSL.

This change adds an explicit mapping from Python config keys to Java property keys and rewrites `_push_properties()` to use it. After this change, `aperv:sata_mop_llm@default_epsilon=0.08,mop_weight_direct=400` will generate the correct `ape.properties` entries, enabling Optuna calibration.

## 2. Scope

Single module: `modules/aperv-tool/` (2 files).

No changes needed in:
- Java `Config.java` — already reads all params from properties
- `rv-experiment` — `@param=value` DSL already works
- `rv-tools` ToolFactory — parameter merge already works
- Docker entrypoint — passes `RV_TOOLS` verbatim

## 3. File Inventory

### 3.1 `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py`

**Change A — Add `APERV_PROPERTY_MAPPING` constant (after line 69)**

New module-level constant mapping Python snake_case keys to Java camelCase `ape.*` property keys. 23 entries: 11 exploration + 3 MOP + 9 LLM (19 calibratable + 4 LLM config keys that must also be in properties):

```python
# Maps Python config key -> Java ape.properties key.
# Keys in _tool_config that appear here are written to ape.properties.
# Keys NOT here (strategy, mop_data) are Python-only and not written.
APERV_PROPERTY_MAPPING = {
    # Exploration parameters
    "default_epsilon": "ape.defaultEpsilon",
    "graph_stable_restart_threshold": "ape.graphStableRestartThreshold",
    "state_stable_restart_threshold": "ape.stateStableRestartThreshold",
    "fuzzing_rate": "ape.fuzzingRate",
    "do_fuzzing": "ape.doFuzzing",
    "throttle_for_activity_transition": "ape.throttleForActivityTransition",
    "throttle_ms": "ape.defaultGUIThrottle",
    "max_extra_priority_aliased_actions": "ape.maxExtraPriorityAliasedActions",
    "max_states_per_activity": "ape.maxStatesPerActivity",
    "trivial_activity_rank_threshold": "ape.trivialActivityRankThreshold",
    "do_back_to_trivial_activity": "ape.doBackToTrivialActivity",
    # MOP weight parameters
    "mop_weight_direct": "ape.mopWeightDirect",
    "mop_weight_transitive": "ape.mopWeightTransitive",
    "mop_weight_activity": "ape.mopWeightActivity",
    # LLM parameters
    "llm_url": "ape.llmUrl",
    "llm_on_new_state": "ape.llmOnNewState",
    "llm_on_stagnation": "ape.llmOnStagnation",
    "llm_model": "ape.llmModel",
    "llm_temperature": "ape.llmTemperature",
    "llm_top_p": "ape.llmTopP",
    "llm_top_k": "ape.llmTopK",
    "llm_timeout_ms": "ape.llmTimeoutMs",
    "llm_max_calls": "ape.llmMaxCalls",
}
```

**Change B — Update `get_variants()` LLM variants (lines 186-196)**

Move LLM defaults from `_push_properties()` hardcoded fallbacks into the variant definitions. Both `sata_llm` and `sata_mop_llm` get all 9 LLM keys explicitly:

```python
"sata_llm": {
    "strategy": "sata",
    "throttle_ms": 200,
    "llm_url": "http://10.0.2.2:30000/v1",
    "llm_on_new_state": "true",
    "llm_on_stagnation": "true",
    "llm_model": "default",
    "llm_temperature": 0.3,
    "llm_top_p": 0.6,
    "llm_top_k": 50,
    "llm_timeout_ms": 15000,
    "llm_max_calls": 200,
},
"sata_mop_llm": {
    "strategy": "sata",
    "throttle_ms": 200,
    "mop_data": "static_analysis",
    "llm_url": "http://10.0.2.2:30000/v1",
    "llm_on_new_state": "true",
    "llm_on_stagnation": "true",
    "llm_model": "default",
    "llm_temperature": 0.3,
    "llm_top_p": 0.6,
    "llm_top_k": 50,
    "llm_timeout_ms": 15000,
    "llm_max_calls": 200,
},
```

**Change C — Rewrite `_push_properties()` (lines 326-371)**

Replace the hardcoded property generation with a loop over `APERV_PROPERTY_MAPPING`:

```python
def _push_properties(self, device_serial, trace_file_path, mop_json_pushed=False):
    lines = []
    if mop_json_pushed:
        lines.append("ape.mopDataPath=/data/local/tmp/static_analysis.json")
    for python_key, java_key in APERV_PROPERTY_MAPPING.items():
        if python_key in self._tool_config:
            lines.append(f"{java_key}={self._tool_config[python_key]}")
    properties_content = "\n".join(lines) + "\n"
    # ... temp file + push (unchanged)
```

### 3.2 `modules/aperv-tool/tests/test_aperv_tool.py`

**Change D — Update existing tests**

- `TestVariants`: verify LLM variants now include all 9 LLM keys (not just `llm_url`)
- `TestPushPropertiesLlm.test_llm_properties_present_when_llm_url_set`: use full variant config (with all LLM keys) in `configure()` call

**Change E — Add new test classes**

- `test_exploration_params_written`: config with `default_epsilon=0.08` → `ape.defaultEpsilon=0.08` in output
- `test_mop_weight_params_written`: config with 3 MOP weights → all 3 appear in output
- `test_minimal_config_only_throttle`: config with only `strategy` + `throttle_ms` → only `ape.defaultGUIThrottle` in output
- `test_python_only_keys_not_written`: `strategy` and `mop_data` do NOT appear in properties
- `test_mixed_params_all_written`: config with exploration + MOP + LLM params → all mapped keys appear

## 4. Execution Order

Single group — 2 files in same module, tightly coupled. No subagent dispatch needed.

1. Edit `tool.py` (mapping → variants → push_properties)
2. Edit `test_aperv_tool.py` (update existing + add new)
3. Run tests

## 5. Acceptance Criteria

- [ ] `APERV_PROPERTY_MAPPING` has 23 entries mapping Python keys to Java `ape.*` property keys (19 calibratable + 4 LLM config)
- [ ] `_push_properties()` uses the mapping loop — no hardcoded key names
- [ ] LLM defaults are in `get_variants()` definitions, not in `_push_properties()` fallbacks
- [ ] `aperv:sata_mop_llm@default_epsilon=0.08` generates `ape.defaultEpsilon=0.08` in properties
- [ ] Python-only keys (`strategy`, `mop_data`) do NOT appear in properties
- [ ] `mopDataPath` is still conditional on `mop_json_pushed` (special case, not in mapping)
- [ ] All existing tests pass (no regression)
- [ ] New tests cover exploration, MOP, minimal, and mixed parameter generation
- [ ] `uv run pytest modules/aperv-tool/tests/ -v` passes
