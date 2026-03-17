## 1. Implementation: tool.py

- [ ] 1.1 Add `sata_llm` and `sata_mop_llm` variants to `get_variants()` (ref: plan.md File Inventory #1)
- [ ] 1.2 Add `APERV_LLM_BASE_URL` env var override in `configure()`, after strategy validation and config copy (ref: plan.md File Inventory #2)
- [ ] 1.3 Extend `_push_properties()` to write 9 `ape.llm*` keys when `llm_url` is present in config (ref: plan.md File Inventory #3)

## 2. Tests: test_aperv_tool.py

- [ ] 2.1 Update `TestVariants.test_exactly_five_variants` to expect 7 variants
- [ ] 2.2 Add `test_sata_llm_has_llm_url_no_mop_data`
- [ ] 2.3 Add `test_sata_mop_llm_has_both_llm_url_and_mop_data`
- [ ] 2.4 Add `test_llm_variants_use_sata_strategy`
- [ ] 2.5 Add `test_env_var_overrides_llm_url` in `TestConfigure`
- [ ] 2.6 Add `test_env_var_ignored_without_llm_url` in `TestConfigure`
- [ ] 2.7 Add `TestPushPropertiesLlm` class with tests for LLM properties content (present when llm_url set, absent when not)

## 3. Verification

- [ ] 3.1 Run `uv run pytest modules/aperv-tool/tests/ -v` — all tests pass
- [ ] 3.2 Verify acceptance criteria from plan.md are met
