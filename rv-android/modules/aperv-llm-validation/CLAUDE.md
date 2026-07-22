# aperv-llm-validation - CLAUDE.md

## Overview

**Temporary** offline validation module for the APE-RV LLM coordinate-mapping pipeline. Tests whether Qwen3-VL can ground UI element coordinates from screenshots by comparing predicted tap coordinates against UIAutomator widget bounds. Used to validate image preprocessing modes (`max_edge`, `smart_resize`, `raw`) and LLM parameters before they land in APE-RV's Java code. Exclude from production/release lists.

```bash
# Pre-validation (requires SGLang server); uv sync/pytest form is in the top-level module CLAUDE.md
uv run python scripts/prevalidation.py \
    --screenshots-dir /path/to/screenshots \
    --sglang-url http://192.168.0.36:30000/v1 \
    --output-dir results/prevalidation-qwen3vl
```

CLI flags include `--modes`, `--temperatures`, `--max-screenshots`, `--disable-thinking`, `--model`.

## Files

| File | Purpose |
|------|---------|
| `src/aperv_llm_validation/constants.py` | Device dims, coordinate ranges, matching thresholds, quality weights, SGLang defaults |
| `src/aperv_llm_validation/data/models.py` | Frozen dataclasses: `Widget`, `ParsedAction`, `MatchResult`, `EvaluationResult`, `PromptConfig`, `EvaluatorConfig` |
| `src/aperv_llm_validation/data/uiautomator_parser.py` | UIAutomator XML → clickable `Widget` list (filters enabled + clickable + area > 0) |
| `src/aperv_llm_validation/pipeline/coordinate_normalizer.py` | Qwen [0,1000) ↔ device-pixel conversion |
| `src/aperv_llm_validation/pipeline/image_processor.py` | Resize modes `max_edge` / `smart_resize` / `raw` + JPEG encode |
| `src/aperv_llm_validation/pipeline/sglang_client.py` | `SglangClient`: OpenAI client + exponential-backoff retry + health check |
| `src/aperv_llm_validation/infrastructure/response_cache.py` | `ResponseCache`: SQLite WAL, keyed by screenshot+prompt+seed+temp+resize_mode |
| `scripts/prevalidation.py` | CLI: discovers screenshot+XML pairs, calls LLM per widget, computes bounds/center hit rates |

`evaluation/` and `prompts/` are placeholders. Tests: `tests/test_{coordinate_normalizer,image_processor,response_cache,uiautomator_parser}.py`; fixture `tests/fixtures/cryptoapp/`. Output: `results/prevalidation-qwen3vl/000_prevalidation_results.csv`.

Dependencies: standalone module, no internal deps. External: `openai`, `Pillow`, `pydantic`, `rich`, `defusedxml`, `scipy`.

## Coordinate Pipeline

Two-step conversion in pre-validation:
1. **Qwen [0,1000) → resized-image px**: `img_px = int((qwen / 1000) * img_dim)`
2. **Resized-image px → device px**: `dev_px = int((img_px / img_dim) * device_dim)`

Matches the Java `CoordinateNormalizer.normalize()` behavior. Device dimensions: 1080x1920 (standard Pixel emulator).

## Hit Criteria

- **Bounds hit**: predicted device pixel falls within the widget's UIAutomator bounds (strict, matches APE check).
- **Center hit**: predicted device pixel within 50px Euclidean distance of widget center (matches rvsec-vision-llm benchmark).

`parse_click_response()` handles three Qwen3-VL response formats: native `tool_calls`, `<tool_call>{...}</tool_call>` XML tags, and inline JSON (with `_fix_malformed_json()` for common Qwen quirks).

## Gotchas

- Screenshots dir must contain per-app subdirectories (e.g. `br.unb.cic.cryptoapp/`), each with paired `.png` + `.uiautomator` files sharing the same stem.
- `smart_resize` returns `(height, width)` (height-first), matching Qwen3-VL's preprocessor convention; `image_processor` handles this internally.
- Cache **read** is disabled in `prevalidation.py` (always calls the model); cache **write** stays active for crash resilience — intentional for experimental reproducibility.
- `ALWAYS_CLICKABLE_TYPES` re-includes inherently interactive widgets that report `clickable=false` in UIAutomator (tabs, nav items, spinners).
- `defusedxml` is required for secure UIAutomator-XML parsing (prevents XML entity attacks).
