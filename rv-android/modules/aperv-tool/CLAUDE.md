# aperv-tool - CLAUDE.md

## Overview

rv-platform plugin that wraps the APE-RV binary (`ape-rv.jar`) as an `AbstractTool`. APE-RV is an enhanced fork of the AOSP Monkey tool that performs model-based UI exploration using the Widget Table Graph (WTG) model. The tool manages JAR deployment, properties injection, and command execution on the Android emulator via `app_process`.

## Quick Start

```bash
# Install (from project root)
uv sync

# Run tests (from project root)
uv run pytest modules/aperv-tool/tests/ -v

# Use via rv-experiment
uv run rv-experiment run --tools aperv:sata --apks-dir ./apks_examples --timeout 300
uv run rv-experiment run --tools aperv:sata_mop --specification-set jca  # MOP-guided
uv run rv-experiment run --tools aperv:sata_llm --apks-dir ./apks_examples  # LLM-guided
```

## Architecture

### Directory Structure

```
src/aperv_tool/
    tools/
        aperv/
            __init__.py
            tool.py                 # ApeRVTool (AbstractTool implementation)
            ape-rv.jar              # APE-RV binary (gitignored; built from ape source at Docker image build)
            system-broadcast.json   # Broadcast intent catalog for component triggering
            .gitignore              # Ignores ape-rv.jar
```

### Key Components

| Component | Purpose |
|-----------|---------|
| `tools/aperv/tool.py` | `ApeRVTool` class: JAR resolution, device push, properties generation, command building, execution |
| `tools/aperv/ape-rv.jar` | APE-RV binary pushed to `/data/local/tmp/ape-rv.jar` on the emulator |
| `tools/aperv/system-broadcast.json` | Catalog of system broadcast intents for component triggering |

### Dependencies

- **Internal**: `rv-android-core` (AbstractTool, ToolSpec, Command, ErrorHandler, JarResolver, domain models)
- **External**: `rv-tools` (plugin registration)

## Development

### Testing

| Category | Path | Purpose |
|----------|------|---------|
| unit | `tests/test_aperv_tool.py` | Tool spec, variants, configure validation, JAR search paths, command building, constants, empty trace detection, properties generation (LLM keys, calibration params) |

### Variants

13 named variants across 4 categories:

| Variant | Strategy | MOP Data | LLM | Notes |
|---------|----------|----------|-----|-------|
| `default` | sata | no | no | Adaptive random (best general-purpose) |
| `sata` | sata | no | no | Same as default |
| `sata_mop` | sata | yes | no | MOP-guided via static analysis JSON |
| `bfs` | bfs | no | no | Breadth-first exploration |
| `random` | random | no | no | Pure random |
| `sata_llm` | sata | no | yes | LLM guidance via SGLang |
| `sata_mop_llm` | sata | yes | yes | MOP + LLM combined |
| `sata_mop_llm_*` | sata | yes | yes | 6 prompt variant experiments (ape_current, ape_reasoning, compact_v1, v13, v17, visual_only) |

All variants use `throttle_ms: 200`. The `dfs` strategy has no named variant but is accessible via parameter override.

### Configuration Flow

1. `configure(config)` validates strategy eagerly (catches typos before device interaction)
2. `execute_tool_specific_logic(task, app)`:
   - Resolves `ape-rv.jar` via priority search (module dir > `$RVSEC_HOME/ape/target/` > `$TOOLS_DIR/aperv/`)
   - Pushes JAR to `/data/local/tmp/ape-rv.jar`
   - Pushes `system-broadcast.json` to `/data/local/tmp/` (optional)
   - For MOP variants: pushes static analysis JSON to `/data/local/tmp/static_analysis.json`
   - Generates and pushes `ape.properties` with exploration parameters
   - Builds and executes `adb shell CLASSPATH=... app_process` command

### Properties Mapping

`APERV_PROPERTY_MAPPING` translates Python config keys to Java `ape.properties` keys. Keys not in the mapping (e.g., `strategy`, `mop_data`) are Python-only and not written to properties.

### Key Design Decisions

- **Working directory `/system/bin`**: APE-RV requires system-level resource resolution; `/data/local/tmp/` causes `ClassNotFoundException` on some API levels
- **Shared process_pattern**: `com.android.commands.monkey` is shared with the builtin ape tool; they must not run concurrently on the same device
- **Timeout as expected exit**: exploration tools run until time limit; `RVCommandTimeoutError` is re-raised as `RVToolTimeoutError` (completed run, not failure)
- **Non-zero exit is normal**: APE-RV exits non-zero when it detects app crashes during exploration
- **LLM URL override**: `APERV_LLM_BASE_URL` env var overrides `llm_url` for Docker/non-emulator setups (emulator uses `10.0.2.2` for host loopback)

## Key Files

| File | Purpose |
|------|---------|
| `src/aperv_tool/tools/aperv/tool.py` | Main tool class (290+ lines) with all execution logic |
| `tests/test_aperv_tool.py` | Comprehensive tests (480+ lines) |
| `pyproject.toml` | Package metadata (no entry point -- manual registration) |
| `docs/architecture.md` | Architecture documentation |

## Gotchas

- `ape-rv.jar` is gitignored (never committed). The Docker image builds it from source at image-build time: `docker/rvandroid/Dockerfile` clones `https://github.com/phtcosta/ape.git`, runs `mvn package`, and copies `target/ape-rv.jar` into this directory (priority-1 resolution path). For standalone (non-Docker) runs, build it from the APE-RV Java project or place it here manually; without it, `_resolve_jar_path()` raises `RVToolExecutionError`.
- The `+15s` grace period on the command timeout gives APE-RV time to flush its WTG model. Without this buffer, the process is killed before writing final output.
- Empty trace file (0 bytes) indicates a silent startup crash. This is logged as a warning, not an error, because coverage may still be captured via logcat.
- Static analysis JSON for MOP variants must exist at `<task.results_dir>/<apk_name>.json`. If missing, the tool degrades gracefully (runs without MOP data).
