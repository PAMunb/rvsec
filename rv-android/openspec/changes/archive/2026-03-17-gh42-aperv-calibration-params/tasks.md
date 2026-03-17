## 1. Implementation: tool.py

- [x] 1.1 Add `APERV_PROPERTY_MAPPING` constant after line 69 with 23 entries (19 calibratable + 4 LLM config) (ref: plan.md Change A)
- [x] 1.2 Update `sata_llm` and `sata_mop_llm` variants in `get_variants()` to include all 9 LLM defaults explicitly (ref: plan.md Change B)
- [x] 1.3 Rewrite `_push_properties()` to use mapping loop instead of hardcoded keys (ref: plan.md Change C)

## 2. Tests: test_aperv_tool.py

- [x] 2.1 Update `TestVariants` to verify LLM variants include all 9 LLM keys
- [x] 2.2 Update `TestPushPropertiesLlm` to use full variant config with all LLM keys
- [x] 2.3 Add `test_exploration_params_written` — `default_epsilon=0.08` → `ape.defaultEpsilon=0.08`
- [x] 2.4 Add `test_mop_weight_params_written` — 3 MOP weights appear in properties
- [x] 2.5 Add `test_minimal_config_only_throttle` — only `ape.defaultGUIThrottle` when minimal config
- [x] 2.6 Add `test_python_only_keys_not_written` — `strategy`, `mop_data` not in properties
- [x] 2.7 Add `test_mixed_params_all_written` — exploration + MOP + LLM all appear

## 3. Verification

- [x] 3.1 Run `uv run pytest modules/aperv-tool/tests/ -v` — all tests pass
- [x] 3.2 Verify acceptance criteria from plan.md are met
