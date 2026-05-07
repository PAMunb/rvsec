# CLAUDE.md - rv-instrumentation-ajc

AspectJ-based APK instrumentation variant (legacy dex2jar+ajc+d8 pipeline). One of two interchangeable variants — the other is `rv-instrumentation-dexlib2`. Both implement the `Instrumenter` ABC defined in `rv-instrumentation-core`; the parent `rv-instrumentation` re-exports the public API and dispatches via `get_instrumenter()`.

## Module Overview

**Purpose**: Bridge between rv-monitor-generator artifacts and executable instrumented APKs, enabling runtime verification of Android applications.

**Package**: `rv_instrumentation_ajc`

**Entry Point**: `rv-instrumentation-ajc` CLI or programmatic via `AjcInstrumentation` class

## Architecture

### Instrumentation Pipeline

```
Original APK
    |
    v
[1.  Decompilation] ---------> DEX to JAR (dex2jar)
    |
    v
[1b. Strip desugared shims] -> Remove R8 desugar synthetic classes that break weaving
    |
    v
[1c. Quarantine classes] ---> Move VerifyError-prone library classes to side-jar
    |                          (gh50 §16/§19/§22; skipped if --no-quarantine)
    v
[2.  Monitor Integration] ---> Inject AspectJ + Java monitors from rv-monitor-generator
    |
    v
[2b. Pre-ajc frame compute] -> Run rv-frame-computer to fix stack maps before weaving
    |
    v
[3.  AspectJ Weaving] -------> Integrate monitoring pointcuts with application bytecode
    |
    v
[4.  Recompute frames] ------> Re-run rv-frame-computer post-weaving
    |
    v
[4b. Restore quarantined] ---> Re-include the side-jar contents (gh50; pairs with 1c)
    |
    v
[5.  Dependency Integration] -> Merge rv-monitor-rt, aspectjrt, rvsec-core libraries
    |
    v
[6.  Recompilation] ---------> JAR to DEX (Android d8 compiler)
    |
    v
[7.  APK Signing] -----------> Sign for deployment (jarsigner / apksigner + keystore)
    |
    v
Instrumented APK
```

**Quarantine phase** (gh50, lines 1c + 4b): library classes that the AspectJ weaver or `d8` reject (e.g. heavily-desugared Compose/Kotlin coroutine classes producing `VerifyError`) are temporarily moved to a side-jar before weaving and restored afterwards. The phase is enabled by default (`enable_quarantine=True`); disable via `--no-quarantine` for empirical comparison of recovery rate vs MOP visibility loss. Driven by `assets/weaving_excludes.yaml` glob patterns. Implemented by `__quarantine_problematic_classes()` and `__restore_quarantined_classes()` in `ajc_instrumentation.py`. dexlib2 has no quarantine equivalent.

### Core Components

| Component | File | Purpose |
|-----------|------|---------|
| `AjcInstrumentation` | `rvandroid.py` | Core instrumentation engine orchestrating the complete pipeline |
| `AjcInstrumentationConfig` | `config.py` | Configuration management with path resolution and validation |
| `Dex2jarTools` | `config.py` | Pydantic model for dex2jar tool suite paths |
| `InstrumentationResults` | `config.py` | Results model with computed success rate |
| CLI | `__main__.py` | Command-line interface for single and batch instrumentation |

### File Structure

```
modules/rv-instrumentation-ajc/
├── src/rv_instrumentation_ajc/
│   ├── __init__.py          # Public API exports
│   ├── __main__.py          # CLI entry point
│   ├── config.py            # Configuration and Pydantic models
│   └── rvandroid.py         # Main instrumentation engine
├── tests/
│   ├── conftest.py          # Test fixtures
│   └── test_config.py       # Configuration unit tests
├── assets/
│   └── keystore.jks         # Bundled development keystore
└── pyproject.toml
```

## Key Classes

### AjcInstrumentation

Main instrumentation engine that transforms APKs into monitored artifacts.

```python
from rv_instrumentation_ajc import AjcInstrumentation, AjcInstrumentationConfig

config = AjcInstrumentationConfig(
    monitor_output_dir="/path/to/monitors",
    android_jar_path="/path/to/android.jar",
    instrumented_dir="/output"
)

instrumentation = AjcInstrumentation(config)
results = instrumentation.instrument_apks(
    apks_dir="/path/to/apks",
    results_dir="/output",
    force_instrumentation=False
)
```

**Key Methods**:
- `instrument_apks()`: Batch instrumentation with error tracking
- `instrument()`: Single APK instrumentation pipeline
- `prepare_instrumentation()`: Environment setup and Maven dependency resolution
- `check_if_instrumented()`: Verify APK was actually modified

### AjcInstrumentationConfig

Configuration management with priority-based path resolution:

1. Individual explicit paths (highest priority)
2. Explicit `rvsec_root` parameter
3. `RVSEC_HOME` environment variable
4. Working directory defaults

**Required Fields**:
- `monitor_output_dir`: Directory with generated monitor artifacts (*.aj, *.java)
- `android_jar_path`: Android SDK android.jar for classpath
- `android_platforms_dir`: Android SDK platforms directory
- `dex2jar_home`: Directory containing dex2jar tools
- `keystore_file`: Keystore for APK signing (defaults to bundled keystore)

## Dependencies

### Module Dependencies

- **rv-android-core**: App domain model, ErrorHandler, LoggingManager, utils
- **pydantic**: Configuration validation and data models

### External Tool Dependencies

| Tool | Purpose | Configuration |
|------|---------|---------------|
| dex2jar | DEX to JAR conversion | `dex2jar_home` |
| ajc (AspectJ) | Monitor weaving | System PATH |
| d8 | JAR to DEX compilation | Android SDK (ANDROID_HOME) |
| jarsigner | APK signing | Java (JAVA_HOME) |
| Maven | Dependency resolution | System PATH |
| zip | APK manipulation | System PATH |

### Required Libraries (via Maven)

- `rv-monitor-rt.jar`: RV-Monitor runtime
- `rvsec-core.jar`: RVSEC core functionality
- `rvsec-logger-logcat.jar`: Android logcat integration
- `aspectjrt.jar`: AspectJ runtime

## CLI Usage

### Single APK Instrumentation

```bash
# Basic usage
rv-instrumentation-ajc instrument --apk /path/to/app.apk --output /output

# With custom monitors and force re-instrumentation
rv-instrumentation-ajc instrument \
    --apk /path/to/app.apk \
    --monitor-dir /custom/monitors \
    --output /output \
    --force \
    --summary
```

### Batch Instrumentation

```bash
# Instrument all APKs in directory
rv-instrumentation-ajc batch \
    --apks-dir /path/to/apks \
    --output /output \
    --verbose \
    --summary
```

### Configuration Validation

```bash
# Validate configuration without running instrumentation
rv-instrumentation-ajc instrument --apk /path/to/app.apk --output /tmp --dry-run
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--rvsec-root` | RVSEC installation root directory |
| `--monitor-dir` | Monitor artifacts directory |
| `--android-jar` | Android SDK android.jar path |
| `--android-platforms-dir` | Android SDK platforms directory |
| `--keystore` | Keystore file (optional, uses bundled) |
| `--keystore-password` | Keystore password (default: "password") |
| `--dex2jar-home` | dex2jar tools directory |
| `--output` | Output directory for instrumented APKs |
| `--force` | Force re-instrumentation |
| `--no-quarantine` | Disable the `assets/weaving_excludes.yaml` quarantine + restore step (gh50 §21). Default behavior is enabled — passing this flag bypasses both `__quarantine_problematic_classes` and `__restore_quarantined_classes` so library classes that normally crash ajc/d8 are woven inline. Empirical use only: comparing recovery rate vs MOP visibility loss across datasets. |
| `--verbose, -v` | Enable verbose logging |
| `--summary` | Display instrumentation summary |
| `--dry-run` | Validate configuration only |

## Development

### Running Tests

```bash
cd modules/rv-instrumentation-ajc

# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest --cov=src -v
```

### Test Structure

- `tests/test_config.py`: Configuration and Pydantic model tests
- `tests/conftest.py`: Shared fixtures (temp_workspace, mock_tools_directory, etc.)

### Adding New Tests

```python
from rv_instrumentation_ajc import AjcInstrumentationConfig
from unittest.mock import patch, MagicMock

def test_new_feature(temp_workspace):
    # Use temp_workspace fixture for isolated testing
    with patch('rv_instrumentation_ajc.config.LoggingManager') as mock_logging:
        mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
        # Test implementation
```

## Configuration Examples

### Minimal Configuration (Environment-based)

```python
# Requires RVSEC_HOME and ANDROID_HOME environment variables
config = AjcInstrumentationConfig()
```

### Explicit Configuration

```python
config = AjcInstrumentationConfig(
    rvsec_root="/path/to/rvsec",
    monitor_output_dir="/path/to/monitors",
    android_jar_path="/path/to/android-sdk/platforms/android-29/android.jar",
    android_platforms_dir="/path/to/android-sdk/platforms",
    keystore_file="/path/to/keystore.jks",
    keystore_password="password",
    working_dir="/workspace",
    instrumented_dir="/output/instrumented",
    dex2jar_home="/path/to/dex2jar"
)
```

### Configuration Summary

```python
# Get detailed configuration for debugging
summary = config.get_configuration_summary()
print(summary.model_dump())
# {
#     'android_integration': {'android_jar_path': '...', 'android_platforms_dir': '...'},
#     'instrumentation_paths': {'working_dir': '...', 'instrumented_dir': '...', ...},
#     'monitor_artifacts': {'aspectj_count': 5, 'java_count': 5},
#     'validation_status': 'Validated'
# }
```

## Error Handling

### Error Types

- `ConfigurationError`: Invalid paths, missing tools, permission issues
- `CommandException`: External tool execution failures with tool name and error code
- `InstrumentationError`: Pipeline phase failures

### Error Reports

Failed instrumentations generate `instrument_errors.json`:

```json
{
  "app_name.apk": {
    "code": -1,
    "tool": "dex2jar",
    "message": "Tool execution failed",
    "phase": "decompilation"
  }
}
```

### Results Tracking

```python
results = instrumentation.instrument_apks(apks_dir, output_dir)
print(f"Success rate: {results.success_rate}%")
print(f"Failed: {len(results.errors)}")
for apk_name, error in results.errors.items():
    print(f"  {apk_name}: {error.phase} - {error.message}")
```

## Integration Points

### With rv-monitor-generator

```bash
# 1. Generate monitors from MOP specifications
rv-monitor-generator generate --specs-dir $RVSEC_HOME/specs/jca --output /monitors

# 2. Instrument APKs with generated monitors
rv-instrumentation-ajc batch --monitor-dir /monitors --apks-dir /apks --output /instrumented
```

### With rv-experiment

The module integrates with experiment orchestration:

```python
from rv_instrumentation_ajc import AjcInstrumentation, AjcInstrumentationConfig

# Called by ExperimentController during pre-processing phase
config = AjcInstrumentationConfig(monitor_output_dir=experiment_config.monitor_dir)
instrumentation = AjcInstrumentation(config)
instrumentation.instrument_apks(apks_dir, results_dir)
```

## Important Notes

### Monitor Artifacts

The module expects monitor artifacts generated by rv-monitor-generator:
- AspectJ files (*.aj): Weaving specifications with pointcuts
- Java files (*.java): Monitor class implementations

### Keystore

A bundled development keystore is included at `assets/keystore.jks` with password "password". For production use, provide a custom keystore.

### Android SDK Version

Default target is `android-29`. Future enhancement will support dynamic SDK selection based on APK target SDK.

### Instrumentation Verification

After instrumentation, the module verifies the APK was actually modified by comparing file hashes. If hashes match the original, instrumentation is considered failed.

### Temporary Directories

The module creates and cleans up temporary directories:
- `tmp_dir`: Intermediate processing files
- `lib_tmp_dir`: Extracted library dependencies
- `rvm_tmp_dir`: Runtime verification monitor processing

These are cleaned up after each APK to prevent disk space issues during batch processing.


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

