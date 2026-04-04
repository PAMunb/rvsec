# aperv-llm-validation - CLAUDE.md

## Overview

Offline validation module for the APE-RV LLM coordinate mapping pipeline. Tests whether Qwen3-VL can accurately ground UI element coordinates from screenshots by comparing predicted tap coordinates against UIAutomator widget bounds. Used to validate image preprocessing modes (max_edge, smart_resize, raw) and LLM parameters before deploying them in APE-RV's Java codebase.

## Quick Start

```bash
# Install (from project root)
uv sync

# Run tests (from project root)
uv run pytest modules/aperv-llm-validation/tests/ -v

# Run pre-validation (requires SGLang server)
cd modules/aperv-llm-validation
uv run python scripts/prevalidation.py \
    --screenshots-dir /home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots \
    --sglang-url http://192.168.0.36:30000/v1 \
    --output-dir results/prevalidation-qwen3vl
```

## Architecture

### Directory Structure

```
src/aperv_llm_validation/
    constants.py              # Pipeline constants (device dims, thresholds, SGLang defaults)
    data/
        models.py             # Domain models (Widget, ParsedAction, MatchResult, EvaluationResult)
        uiautomator_parser.py # UIAutomator XML -> Widget list
    pipeline/
        coordinate_normalizer.py  # Qwen [0,1000) <-> device pixel conversion
        image_processor.py        # Screenshot resize + JPEG encode (max_edge, smart_resize, raw)
        sglang_client.py          # OpenAI-compatible SGLang HTTP client with retry
    infrastructure/
        response_cache.py     # SQLite-backed LLM response cache
    evaluation/               # Evaluation engine (placeholder)
    prompts/                  # Prompt variants (placeholder)
scripts/
    prevalidation.py          # CLI: per-widget grounding test across modes x temperatures
```

### Key Components

| Component | Purpose |
|-----------|---------|
| `data/models.py` | Frozen dataclasses: `Widget`, `ParsedAction`, `MatchResult`, `EvaluationResult`, `PromptConfig`, `EvaluatorConfig` |
| `data/uiautomator_parser.py` | Parses UIAutomator XML dumps into clickable `Widget` instances, filtering by enabled + clickable + area > 0 |
| `pipeline/coordinate_normalizer.py` | Bidirectional conversion between Qwen3-VL normalized [0, 1000) space and device pixels (1080x1920) |
| `pipeline/image_processor.py` | Three resize modes: `max_edge` (longest edge <= 1000px), `smart_resize` (Qwen3-VL patch-aligned), `raw` (no resize) |
| `pipeline/sglang_client.py` | `SglangClient` wrapping OpenAI Python client with exponential backoff retry and health check |
| `infrastructure/response_cache.py` | `ResponseCache` using SQLite WAL mode, keyed by screenshot+prompt+seed+temp+resize_mode |
| `scripts/prevalidation.py` | Main CLI entry point: discovers screenshot+XML pairs, calls LLM per widget, computes bounds/center hit rates |
| `constants.py` | All numeric constants: device dimensions, coordinate ranges, matching thresholds, quality weights |

### Dependencies

- **Internal**: None (standalone module)
- **External**: `openai>=1.0.0`, `Pillow>=10.0.0`, `pydantic>=2.9.0`, `rich>=13.0.0`, `defusedxml>=0.7.0`, `scipy>=1.14.0`

## Development

### Testing

| Category | Path | Purpose |
|----------|------|---------|
| unit | `tests/test_coordinate_normalizer.py` | Qwen-to-pixel and pixel-to-Qwen conversions |
| unit | `tests/test_image_processor.py` | Resize dimension calculations, smart_resize |
| unit | `tests/test_response_cache.py` | SQLite cache get/put/stats |
| unit | `tests/test_uiautomator_parser.py` | XML parsing, widget filtering |

Test fixtures: `tests/fixtures/cryptoapp/001.uiautomator`

### Common Tasks

```bash
# Run pre-validation with specific modes
uv run python scripts/prevalidation.py \
    --screenshots-dir /path/to/screenshots \
    --modes max_edge smart_resize \
    --temperatures 0.01 0.7 \
    --max-screenshots 10

# Disable thinking mode (Qwen3.5+ models)
uv run python scripts/prevalidation.py \
    --screenshots-dir /path/to/screenshots \
    --disable-thinking

# Specify model
uv run python scripts/prevalidation.py \
    --screenshots-dir /path/to/screenshots \
    --model Qwen/Qwen3-VL-4B-Instruct
```

### Coordinate Pipeline

Two-step coordinate conversion in pre-validation:

1. **Qwen [0, 1000) -> resized image pixels**: `img_px = int((qwen / 1000) * img_dim)`
2. **Resized image pixels -> device pixels**: `dev_px = int((img_px / img_dim) * device_dim)`

This matches the Java `CoordinateNormalizer.normalize()` behavior. Device dimensions: 1080x1920 (standard Pixel emulator).

### Hit Criteria

- **Bounds hit**: predicted device pixel falls within widget's UIAutomator bounds (strict, matches APE check)
- **Center hit**: predicted device pixel within 50px Euclidean distance of widget center (matches rvsec-vision-llm benchmark)

### LLM Response Parsing

`parse_click_response()` handles three response formats from Qwen3-VL:

1. **Native tool_calls**: standard OpenAI tool calling format
2. **XML tags**: `<tool_call>{"x": N, "y": M}</tool_call>` (Qwen's common format)
3. **Inline JSON**: JSON objects embedded in content text

Includes `_fix_malformed_json()` for common Qwen quirks: missing "y" key, array format, comma-separated strings, missing leading zeros, truncated JSON.

## Key Files

| File | Purpose |
|------|---------|
| `src/aperv_llm_validation/constants.py` | All pipeline constants |
| `src/aperv_llm_validation/data/models.py` | Domain models |
| `src/aperv_llm_validation/pipeline/image_processor.py` | Image preprocessing |
| `src/aperv_llm_validation/pipeline/coordinate_normalizer.py` | Coordinate conversion |
| `src/aperv_llm_validation/infrastructure/response_cache.py` | SQLite LLM response cache |
| `scripts/prevalidation.py` | Main CLI with grounding test logic |
| `results/prevalidation-qwen3vl/000_prevalidation_results.csv` | Pre-validation output |

## Gotchas

- Screenshots directory must contain subdirectories named by app (e.g., `br.unb.cic.cryptoapp/`), each with paired `.png` and `.uiautomator` files sharing the same stem.
- The `smart_resize` mode returns `(height, width)` (height-first), matching Qwen3-VL's preprocessor convention. The image_processor handles this internally.
- Cache read is disabled in `prevalidation.py` (always calls the model). Cache write is active for crash resilience. This is intentional for experimental reproducibility.
- `ALWAYS_CLICKABLE_TYPES` includes widgets that report `clickable=false` in UIAutomator but are inherently interactive (tabs, navigation items, spinners). Without this, those widgets would be excluded from grounding tests.
- The `defusedxml` dependency is required for secure XML parsing of UIAutomator dumps (prevents XML entity attacks).
