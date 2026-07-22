# Tasks: gh47-aperv-sync-ape12

## 1. Remove llm_max_calls from tool.py

- [x] 1.1 Remove `"llm_max_calls": "ape.llmMaxCalls"` from `APERV_PROPERTY_MAPPING`
- [x] 1.2 Remove `"llm_max_calls": 200` from `sata_llm` variant
- [x] 1.3 Remove `"llm_max_calls": 200` from `sata_mop_llm` variant
- [x] 1.4 Remove `"llm_max_calls": 999` from dynamic `sata_mop_llm_{v}` variants

## 2. Rename prompt variants in tool.py

- [x] 2.1 Rename `"rvsmart_v13"` → `"v13"` and `"rvsmart_v17"` → `"v17"` in variant list

## 3. Update tests

- [x] 3.1 Remove `"llm_max_calls"` from `llm_keys` set and update docstring count
- [x] 3.2 Remove `assert "ape.llmMaxCalls=200" in props`

## 4. Update Docker compose files

- [x] 4.1 Rename `rvsmart_v13`/`rvsmart_v17` → `v13`/`v17` in `docker-compose.exp4-prompt-variants.yml`
- [x] 4.2 Rename `rvsmart_v13` → `v13` in `docker-compose.exp5-prompt-600s.yml`
- [x] 4.3 Rename `rvsmart_v13` → `v13` in `docker-compose.exp5-smoke.yml`

## 5. Verification

- [x] 5.1 `grep -r "llm_max_calls" modules/aperv-tool/` → zero matches
- [x] 5.2 `grep -r "llmMaxCalls" modules/aperv-tool/` → zero matches
- [x] 5.3 `grep -r "rvsmart_v" modules/aperv-tool/` → zero matches
- [x] 5.4 `grep -r "rvsmart_v1[37]" docker/` → zero matches
- [x] 5.5 `uv run pytest modules/aperv-tool/tests/ -v` → 43 passed
