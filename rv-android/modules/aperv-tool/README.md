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
uv run rv-experiment run --tools aperv --apks-dir ./apks_examples --timeouts 300

# With a specific variant
uv run rv-experiment run --tools aperv:sata_mop --apks-dir ./apks_examples

# Via rv-platform
uv run rv-platform run --tools aperv:sata --apks-dir ./apks_examples
```

## Features

- **Strategy selection**: SATA (adaptive random) and random exploration — the two agent types the APE-RV binary implements
- **MOP-guided exploration**: `sata_mop` biases exploration toward screens where monitored operations are reachable, using a compact artifact derived from static analysis
- **LLM-guided exploration**: `sata_llm`, `sata_mop_llm` and `mop_on_llm_70` integrate with an OpenAI-compatible LLM endpoint for decision guidance
- **JAR deployment**: Resolves `ape-rv.jar` via priority search paths and pushes to the Android device
- **Properties injection**: Generates `ape.properties` naming the arm's jar preset plus its override deltas
- **Timeout-aware execution**: Treats timeout as expected exit behavior for exploration tools, and checks the converse — a run that returned early without timing out did not explore its budget, so it fails instead of reporting success. The exit code is not consulted: APE-RV exits non-zero when the application under test crashes, which is data the run exists to collect

## Variants

An arm is a **jar preset name plus a dict of override deltas**. The preset (`aperv`, `mop`, `llm`, `llm_mop`) is resolved inside `ape-rv.jar`, which owns what it contains; this module owns the experimental matrix — which arms exist, their frozen names, and how each differs from its preset. Eight names carry seven configurations (`default` is bound to the same object as `sata`).

| Variant | Preset | MOP artifact | Overrides |
|---------|--------|--------------|-----------|
| `default` | `aperv` | No | _(none)_ — alias of `sata` |
| `sata` | `aperv` | No | _(none)_ — adaptive random baseline |
| `sata_mop` | `mop` | Yes | _(none)_ — MOP-guided scoring |
| `sata_llm` | `llm` | No | `llm_url` |
| `sata_mop_llm` | `llm_mop` | Yes | `llm_url` |
| `mop_on_llm_off` | `mop` | Yes | Reach package (activity source components, frontier weights, activity trigger) — E3 reference arm |
| `mop_off_llm_off` | `mop` | Yes | Reach package minus the frontier weight and trigger, plus the four MOP weights at `0` — E3 control arm |
| `mop_on_llm_70` | `llm_mop` | Yes | Reach package plus the calibrated LLM dose (`v13`, 70%, temperature `0`) and `llm_snap_tolerance_px=150` — E3 LLM arm |

MOP-off means the artifact is still pushed and the scoring weights are zeroed, never an omitted document: omitting it would kill the generic WTG and frontier navigation as collateral, turning the contrast into "full substrate versus almost none" instead of "MOP guidance on versus off".

Arms retired by the preset migration can no longer be launched; results recorded under those names are frozen artifacts and remain readable. The list with each retirement's reason is `tests/migration/retirements.py`.

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

The generated file states the arm and nothing more. For `sata_mop_llm`, whose only override is the server URL, it is exactly three lines:

```properties
ape.preset=llm_mop                                  # always first
ape.mopDataPath=/data/local/tmp/mop-artifact.json   # only when the MOP artifact was pushed
ape.llmUrl=http://10.0.2.2:30000/v1                 # one line per override delta
```

Everything a preset supplies — throttle, epsilon, MOP weights, LLM model and timeouts — is resolved inside the jar and is never restated here, so `sata_mop` ships a two-line file. Override keys are translated to `ape.*` names through `APERV_PROPERTY_MAPPING`; the emission walks the mapping rather than the override dict, so two runs of the same arm produce byte-identical properties. The eight top-level keys in `APERV_ORCHESTRATION_KEYS` (`preset`, `overrides`, `strategy`, `mop_data`, `seed`, and the three device-addressing keys `device_port` / `device_serial` / `device_id`) are Python orchestration and never reach the device; any other unmapped key raises `ConfigurationError` before a device is touched.

The jar must postdate the preset mechanism. An older build treats `ape.preset` as an unknown key and ignores it, and since the file no longer carries what the preset would have supplied, the run silently executes on jar defaults while the results directory still carries the arm's name.

An experiment can add a delta without a new variant using the tool DSL, e.g. `--tools aperv:sata_mop@default_epsilon=0.1`.

### Corpus provenance

`corpus_basis` records which application list a run was drawn from, as `<corpus-id>:<sha256>` (e.g. `subset40:b60903ad…d48d4`). It is provenance the caller supplies, not a digest the tool computes: aperv-tool does not own the corpus list and does not read a campaign's filesystem layout to hash it. `configure()` validates the shape before any device interaction, the key is omitted entirely when unstated, and the jar echoes it into the trace's opening record without reading it back — so it changes no behaviour and makes a recorded run answer "which corpus?" from its own artifacts. Usually set through the DSL: `--tools aperv:mop_on_llm_off@corpus_basis=subset40:<sha256>`.

## Offline analysis

`aperv_tool.analysis` holds read-only utilities over artifacts a run already produced — no device, no adb, and nothing in the execution path: `trace_ndjson` (native reader of the stage-4 NDJSON trace), `coverage_dump` (the jar's `UICOV` / `UICOV-ACT` dump) and `clock_logcat_join` (placing `RVSEC` violation lines on the exploration timeline). They live in the tool package because the thesis experiment consumes them, not only a calibration campaign.

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
