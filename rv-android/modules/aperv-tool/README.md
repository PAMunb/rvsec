# aperv-tool

APE-RV tool wrapper for rv-platform integration.

## Overview

aperv-tool wraps the enhanced APE-RV binary (`ape-rv.jar`) as an `AbstractTool` plugin for the rv-platform task execution framework. APE-RV is an enhanced fork of the AOSP Monkey tool that performs model-based UI exploration using the Widget Table Graph (WTG) model with adaptive random testing. This module handles JAR deployment, strategy selection, properties injection, and execution lifecycle on Android emulators.

## Installation

```bash
# Install all rv-android modules (from project root)
uv sync
```

This module is part of the RV-Android uv workspace. All modules are installed in editable mode — source changes are reflected immediately.

## Quick Start

aperv-tool is used through rv-experiment or rv-platform, not directly:

```bash
# Via rv-experiment (recommended)
uv run rv-experiment run --tools aperv --apks-dir ./apks_examples --timeout 300

# With a specific variant
uv run rv-experiment run --tools aperv:sata_mop --apks-dir ./apks_examples

# Via rv-platform
uv run rv-platform run --tools aperv:sata --apks-dir ./apks_examples
```

## Features

- **Strategy selection**: SATA (adaptive random), BFS, DFS, and random exploration strategies
- **MOP-guided exploration**: `sata_mop` variant biases exploration toward screens with monitored operations using static analysis data
- **LLM-guided exploration**: `sata_llm` and `sata_mop_llm` variants integrate with an OpenAI-compatible LLM endpoint for decision guidance
- **JAR deployment**: Resolves `ape-rv.jar` via priority search paths and pushes to the Android device
- **Properties injection**: Generates `ape.properties` with throttle, MOP weights, and LLM configuration
- **Timeout-aware execution**: Treats timeout as expected exit behavior for exploration tools

## Variants

| Variant | Strategy | MOP Data | LLM | Description |
|---------|----------|----------|-----|-------------|
| `default` | SATA | No | No | General-purpose adaptive random exploration |
| `sata` | SATA | No | No | Same as default |
| `sata_mop` | SATA | Yes | No | MOP-guided scoring via static analysis |
| `bfs` | BFS | No | No | Breadth-first exploration |
| `random` | Random | No | No | Random exploration |
| `sata_llm` | SATA | No | Yes | SATA with LLM guidance |
| `sata_mop_llm` | SATA | Yes | Yes | SATA with MOP + LLM guidance |
| `sata_mop_llm_<variant>` | SATA | Yes | Yes | Prompt variant experiments (ape_current, ape_reasoning, compact_v1, v13, v17, visual_only) |

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `RVSEC_HOME` | Path to RVSEC installation (for JAR resolution fallback) | No |
| `TOOLS_DIR` | Alternative path for manual JAR placement | No |
| `APERV_LLM_BASE_URL` | Override LLM endpoint URL (for Docker or non-emulator setups) | No |

### JAR Resolution Priority

1. Module directory (shipped with the package)
2. `$RVSEC_HOME/ape/target/` (Maven build output)
3. `$TOOLS_DIR/aperv/` (manual placement)

### Properties (ape.properties)

Key properties written to the device:

| Property | Config Key | Default | Description |
|----------|-----------|---------|-------------|
| `ape.defaultGUIThrottle` | `throttle_ms` | `200` | Delay between UI actions (ms) |
| `ape.defaultEpsilon` | `default_epsilon` | - | SATA exploration parameter |
| `ape.mopWeightDirect` | `mop_weight_direct` | - | Weight for direct MOP matches |
| `ape.mopWeightTransitive` | `mop_weight_transitive` | - | Weight for transitive MOP matches |
| `ape.llmUrl` | `llm_url` | `http://10.0.2.2:30000/v1` | LLM endpoint (emulator host alias) |
| `ape.llmPercentage` | `llm_percentage` | - | Fraction of decisions guided by LLM |

## Dependencies

### Internal (rv-android)
- `rv-android-core` - Foundation infrastructure (AbstractTool, Command, Task, App)
- `rv-tools` - Tool registry and plugin system

### External
- Android SDK (`adb`) - Device interaction via ADB push and shell commands

## Documentation

- [Architecture](./docs/architecture.md) - Detailed architecture documentation

## Testing

```bash
# From project root
uv run pytest modules/aperv-tool/tests/ -v

# With coverage
uv run pytest modules/aperv-tool/tests/ --cov=modules/aperv-tool/src --cov-report=html
```

## License

Part of the rv-android project.
