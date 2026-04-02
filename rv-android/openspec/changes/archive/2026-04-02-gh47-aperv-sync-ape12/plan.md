# Plan: Sync aperv-tool with ape#12

**Change**: gh47-aperv-sync-ape12
**Date**: 2026-04-02
**Track**: Quick Path
**Priority**: Medium
**GitHub Issue**: #47
**Affected Domains**: Tools (aperv-tool)

## Context

The `phtcosta/ape` repo (issue #12, commit e2d9f49) removed `llmMaxCalls` (artificial LLM call budget) and renamed prompt variants `rvsmart_v13` → `v13`, `rvsmart_v17` → `v17`. The updated JAR is already in the repo. The Python side still references the old names and the removed parameter.

## Scope

5 files, 2 modules (aperv-tool source + tests), 3 Docker compose files.

## File Inventory

### 1. `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py`

| Line | Current | Action |
|------|---------|--------|
| 100 | `"llm_max_calls": "ape.llmMaxCalls",` | Remove from `APERV_PROPERTY_MAPPING` |
| 231 | `"llm_max_calls": 200,` in `sata_llm` | Remove line |
| 245 | `"llm_max_calls": 200,` in `sata_mop_llm` | Remove line |
| 263 | `"llm_max_calls": 999,` in dynamic variants | Remove line |
| 268-270 | `"rvsmart_v13", ... "rvsmart_v17"` | Rename to `"v13"`, `"v17"` |

### 2. `modules/aperv-tool/tests/test_aperv_tool.py`

| Line | Current | Action |
|------|---------|--------|
| 78 | docstring "all 9 LLM config keys" | Change to "8 LLM config keys" |
| 81 | `"llm_max_calls"` in `llm_keys` set | Remove from set |
| 345 | `assert "ape.llmMaxCalls=200" in props` | Remove assertion |

### 3. `docker/docker-compose.exp4-prompt-variants.yml`

| Line | Current | Action |
|------|---------|--------|
| 5 | comment with `rvsmart_v13,rvsmart_v17` | Rename to `v13,v17` |
| 6 | comment "with 999 max calls" | Remove "with 999 max calls" |
| 17 | `sata_mop_llm_rvsmart_v13`, `sata_mop_llm_rvsmart_v17` in RV_TOOLS | Rename to `sata_mop_llm_v13`, `sata_mop_llm_v17` |

### 4. `docker/docker-compose.exp5-prompt-600s.yml`

| Line | Current | Action |
|------|---------|--------|
| 1 | comment `rvsmart_v13` | Rename to `v13` |
| 17 | `sata_mop_llm_rvsmart_v13` in RV_TOOLS | Rename to `sata_mop_llm_v13` |

### 5. `docker/docker-compose.exp5-smoke.yml`

| Line | Current | Action |
|------|---------|--------|
| 12 | `sata_mop_llm_rvsmart_v13` in RV_TOOLS | Rename to `sata_mop_llm_v13` |

## Execution Order

All edits are independent — no ordering constraints.

## Acceptance Criteria

1. `grep -r "llm_max_calls" modules/aperv-tool/` → zero matches
2. `grep -r "llmMaxCalls" modules/aperv-tool/` → zero matches
3. `grep -r "rvsmart" modules/aperv-tool/` → zero matches
4. `grep -r "rvsmart_v1[37]" docker/` → zero matches
5. `uv run pytest modules/aperv-tool/tests/ -v` → all pass
