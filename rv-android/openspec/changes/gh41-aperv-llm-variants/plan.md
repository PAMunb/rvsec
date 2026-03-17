# Plan: aperv-tool LLM variants and properties generation

**Date**: 2026-03-17
**Track**: Quick Path
**Priority**: Normal
**GitHub Issue**: #41
**Affected Domains**: Tools (aperv-tool)

---

## Context

The APE-RV Java side (phtcosta/ape#6, `gh6-aperv-llm-integration`) adds LLM integration to the exploration loop with 2 routing modes (new-state and stagnation) and 9 config keys with `ape.` prefix. The rv-android `aperv-tool` must register new LLM variants and generate `ape.properties` with the correct LLM config keys so that `rv-experiment` / `rv-platform` can run APE-RV with LLM guidance.

The implementation follows the established pattern from `rvsmart-tool`, which already supports LLM variants with env var overrides and properties generation. No design decisions are needed — all design was done in the gh6 change on the APE side.

Reference: `docs/20260317_aperv_llm_rvandroid.md` (Phase 0 ideation).

---

## Scope

Two files are affected, both in `modules/aperv-tool/`:

| File | Change |
|------|--------|
| `src/aperv_tool/tools/aperv/tool.py` | Add 2 variants to `get_variants()`, add env var override in `configure()`, extend `_push_properties()` with LLM keys |
| `tests/test_aperv_tool.py` | Add tests for 7-variant set, LLM variant structure, env var override, properties LLM content |

---

## File Inventory

### tool.py (`modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py`)

**1. `get_variants()` (lines 152-186)**: Add 2 new entries to the returned dict:

```python
"sata_llm": {
    "strategy": "sata",
    "throttle_ms": 200,
    "llm_url": "http://10.0.2.2:30000/v1",
},
"sata_mop_llm": {
    "strategy": "sata",
    "throttle_ms": 200,
    "mop_data": "static_analysis",
    "llm_url": "http://10.0.2.2:30000/v1",
},
```

**2. `configure()` (lines 188-213)**: After the existing strategy validation, add env var override for LLM URL (following rvsmart-tool pattern at rvsmart tool.py lines 177-180):

```python
llm_url_override = os.environ.get("APERV_LLM_BASE_URL")
if llm_url_override and "llm_url" in self._tool_config:
    self._tool_config["llm_url"] = llm_url_override
```

**3. `_push_properties()` (lines 310-342)**: After the existing throttle and mop lines, add LLM config keys when `llm_url` is present in config. The 9 keys map directly from the gh6 `Config.java` defaults:

| Config Key | Python config key | Default |
|-----------|-------------------|---------|
| `ape.llmUrl` | `llm_url` | (from variant) |
| `ape.llmOnNewState` | `llm_on_new_state` | true |
| `ape.llmOnStagnation` | `llm_on_stagnation` | true |
| `ape.llmModel` | `llm_model` | "default" |
| `ape.llmTemperature` | `llm_temperature` | 0.3 |
| `ape.llmTopP` | `llm_top_p` | 0.6 |
| `ape.llmTopK` | `llm_top_k` | 50 |
| `ape.llmTimeoutMs` | `llm_timeout_ms` | 15000 |
| `ape.llmMaxCalls` | `llm_max_calls` | 200 |

### test_aperv_tool.py (`modules/aperv-tool/tests/test_aperv_tool.py`)

**4. `TestVariants`**: Update `test_exactly_five_variants` → `test_exactly_seven_variants`. Add tests:
- `test_sata_llm_has_llm_url_no_mop_data` — verify `llm_url` present, `mop_data` absent
- `test_sata_mop_llm_has_both_llm_url_and_mop_data` — verify both keys present
- `test_llm_variants_use_sata_strategy` — both use `strategy: "sata"`

**5. `TestConfigure`**: Add tests:
- `test_env_var_overrides_llm_url` — set `APERV_LLM_BASE_URL`, verify override applied
- `test_env_var_ignored_without_llm_url` — set env var but configure without `llm_url`, verify no effect

**6. New `TestPushPropertiesLlm` class**: Test `_push_properties()` LLM content generation. Mock file push, verify properties content includes all 9 `ape.llm*` keys for LLM config, and does NOT include them for non-LLM config.

---

## Execution Order

Single group — both files are in the same module and changes are tightly coupled:

1. Edit `tool.py` (variants → configure → properties)
2. Edit `test_aperv_tool.py` (update existing + add new tests)
3. Run tests

No subagent dispatch needed (2 files, <150 LOC).

---

## Acceptance Criteria

- [ ] `ApeRVTool.get_variants()` returns exactly 7 variants: default, sata, sata_mop, bfs, random, sata_llm, sata_mop_llm
- [ ] `sata_llm` config has `strategy=sata`, `llm_url`, no `mop_data`
- [ ] `sata_mop_llm` config has `strategy=sata`, `llm_url`, `mop_data=static_analysis`
- [ ] `configure()` applies `APERV_LLM_BASE_URL` env var override when `llm_url` is in config
- [ ] `configure()` ignores `APERV_LLM_BASE_URL` when `llm_url` is NOT in config
- [ ] `_push_properties()` writes all 9 `ape.llm*` keys when `llm_url` is present
- [ ] `_push_properties()` does NOT write any `ape.llm*` keys for non-LLM variants
- [ ] All existing tests pass unchanged (no regression)
- [ ] New tests cover variant structure, env var override, and properties content
- [ ] `uv run pytest modules/aperv-tool/tests/ -v` passes
