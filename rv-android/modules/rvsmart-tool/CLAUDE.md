# CLAUDE.md - rvsmart-tool

## Purpose

rvsmart-tool wraps the RVSmart Java exploration agent as an AbstractTool for execution within the rv-platform task execution framework. RVSmart is a Java-based tool that runs inside the Android emulator via `app_process`, performing algorithmic (DFS, random) or hybrid LLM-guided UI exploration to trigger monitored operations for runtime verification. This module handles JAR resolution, device deployment via ADB, configuration and static data push, health checks, command construction, and metrics extraction from trace output.

## Architecture

### Key Patterns and Design Decisions

- **AbstractTool Implementation**: RVSmartTool implements the rv-tools AbstractTool interface with `configure()` and `execute_tool_specific_logic()` lifecycle methods
- **External Tool Registration**: Registered via rv-platform `__init__.py` on import (not a built-in rv-tools tool)
- **JAR Resolution**: Uses JarResolver with `os.path.dirname(__file__)` as first search path (same pattern as APE/FastBot). JAR copied by Maven `install` phase via `maven-resources-plugin`. Fallbacks: `$RVSEC_HOME/rvsec-android/rvsmart/target`, `$TOOLS_DIR/rvsmart`
- **Device-Side Execution**: Runs Java code on the Android device via `adb shell app_process`, not on the host
- **Metrics Extraction**: Parses `RVSMART_METRICS:` prefix from trace file stdout to extract JSON metrics

### Execution Flow

1. `configure()` stores variant configuration (mode, throttle, LLM URL)
2. `execute_tool_specific_logic()` resolves JAR via JarResolver
3. Pushes `rvsmart.jar` to `/data/local/tmp/rvsmart.jar` on device
4. Optionally pushes `static_analysis.json` to device (from platform StaticAnalysisComponent)
5. Optionally generates and pushes `rvsmart.properties` from tool config
6. Runs `--health-check` command to verify JAR is functional
7. Executes main exploration command via `adb shell app_process`
8. Captures stdout/stderr to trace file
9. Extracts metrics from trace file and writes `rvsmart_metrics.json`

### Key Components

| Component | Purpose |
|-----------|---------|
| `RVSmartTool` | AbstractTool implementation - JAR deployment, command execution, metrics extraction |
| `TOOL_SPEC` | ToolSpec with name="rvsmart", process_pattern="br.unb.cic.rvsmart" |

### Variants

| Variant | Mode | Description |
|---------|------|-------------|
| `default` | pure_algorithm | Algorithmic exploration, 50ms throttle |
| `mvp` | pure_algorithm | Same as default (minimum viable product) |
| `fast` | pure_algorithm | Algorithmic exploration, 30ms throttle |
| `hybrid` | multimode | LLM-guided exploration via `http://10.0.2.2:30000/v1` |

## Directory Structure

```
src/rvsmart_tool/
    __init__.py              # Module exports (RVSmartTool)
    tools/
        __init__.py
        rvsmart/
            __init__.py
            tool.py          # RVSmartTool implementation
```

## Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `tools/rvsmart/tool.py` | RVSmartTool - JAR deployment, execution, metrics extraction | 559 |

## Dependencies

### Internal (rv-android modules)

- **rv-android-core**: Command, App, Task, AbstractTool, ToolSpec, ErrorHandler, JarResolver, LoggingManager
- **rv-tools**: ToolRegistry (for registration via rv-platform)

### External

- **pydantic** (>=2.9.0): Configuration validation

## Testing

```bash
cd modules/rvsmart-tool

# Run all tests
PYTHONPATH=../rv-android-core/src:../rv-tools/src:src uv run pytest tests/ -v
```

### Test Structure

```
tests/
    __init__.py
    test_rvsmart_tool.py     # Tool spec, variants, configure, metrics, JAR paths, commands
```

### Test Coverage

- `TestToolSpec`: Verifies tool name, version, process pattern, URL
- `TestVariants`: Validates all 4 variants (default, mvp, fast, hybrid)
- `TestConfigure`: Configuration storage, empty config, defensive copy
- `TestMetricsExtraction`: Valid metrics parsing, missing metrics fallback
- `TestJarSearchPaths`: Environment-based path resolution
- `TestBuildCommand`: Command construction with/without static data, mode, config

## Common Tasks

### Run RVSmart via rv-experiment

```bash
# Algorithmic exploration (default variant)
uv run rv-experiment run --tools rvsmart --apks-dir ./apks_examples --timeout 300

# Fast variant
uv run rv-experiment run --tools rvsmart:fast --apks-dir ./apks_examples --timeout 300

# Hybrid LLM mode (requires SGLang server accessible from emulator)
uv run rv-experiment run --tools rvsmart:hybrid --apks-dir ./apks_examples --timeout 300
```

### Run RVSmart via rv-platform

```bash
uv run rv-platform run --tools rvsmart --apks-dir ./apks_examples
uv run rv-platform run --tools rvsmart:hybrid --apks-dir ./apks_examples --timeout 600
```

## Important Notes

- **JAR Prerequisite**: RVSmart Java project must be built with `mvn install` (not just `mvn package`). The `install` phase copies the JAR to the Python tool module directory via `maven-resources-plugin`. The JAR is `.gitignore`d as a build artifact
- **Device Execution**: RVSmart runs inside the emulator via `app_process`, not on the host machine
- **Timeout Handling**: Timeout is controlled by `Task.config`, not by variant configuration. Timeout expiration is expected behavior for exploration tools
- **Hybrid Mode**: The `hybrid` variant uses `http://10.0.2.2:30000/v1` which maps to the host's `localhost:30000` from inside the emulator. In Docker, a socat bridge forwards port 30000 to the `sglang` service
- **Static Analysis Data**: Optionally receives static analysis data from the platform's StaticAnalysisComponent and pushes it to the device for informed exploration
- **Metrics Output**: Writes `rvsmart_metrics.json` in the task results directory, extracted from `RVSMART_METRICS:` lines in trace output

## Development Notes

This module is part of the RV-Android uv workspace. All modules are installed in **editable mode** via the root `pyproject.toml`.

**Key points:**
- Run `uv sync` from the project root to install all modules
- Source code changes are reflected immediately (no reinstall needed)
- Only reinstall if `pyproject.toml` dependencies change

```bash
# From project root
uv sync             # Install/update all modules (also removes unused packages)
```
