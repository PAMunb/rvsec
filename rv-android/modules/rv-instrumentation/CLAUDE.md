# CLAUDE.md - rv-instrumentation

APK instrumentation module for runtime verification monitor weaving. Transforms standard Android APKs into monitored operations-enabled artifacts through a sophisticated pipeline including decompilation, monitor integration, AspectJ weaving, recompilation, and signing.

## Module Overview

**Purpose**: Bridge between rv-monitor-generator artifacts and executable instrumented APKs, enabling runtime verification of Android applications.

**Package**: `rv_instrumentation`

**Entry Point**: `rv-instrumentation` CLI or programmatic via `RVInstrumentation` class

## Architecture

### Instrumentation Pipeline

```
Original APK
    |
    v
[1. Decompilation] -----> DEX to JAR (dex2jar)
    |
    v
[2. Monitor Integration] --> Inject AspectJ + Java monitors from rv-monitor-generator
    |
    v
[3. AspectJ Weaving] ----> Integrate monitoring pointcuts with application bytecode
    |
    v
[4. Dependency Integration] --> Merge rv-monitor-rt, aspectjrt, rvsec-core libraries
    |
    v
[5. Recompilation] ------> JAR to DEX (Android d8 compiler)
    |
    v
[6. APK Signing] --------> Sign for deployment (jarsigner + keystore)
    |
    v
Instrumented APK
```

### Core Components

| Component | File | Purpose |
|-----------|------|---------|
| `RVInstrumentation` | `rvandroid.py` | Core instrumentation engine orchestrating the complete pipeline |
| `RVInstrumentationConfig` | `config.py` | Configuration management with path resolution and validation |
| `Dex2jarTools` | `config.py` | Pydantic model for dex2jar tool suite paths |
| `InstrumentationResults` | `config.py` | Results model with computed success rate |
| CLI | `__main__.py` | Command-line interface for single and batch instrumentation |

### File Structure

```
modules/rv-instrumentation/
├── src/rv_instrumentation/
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

### RVInstrumentation

Main instrumentation engine that transforms APKs into monitored artifacts.

```python
from rv_instrumentation import RVInstrumentation, RVInstrumentationConfig

config = RVInstrumentationConfig(
    monitor_output_dir="/path/to/monitors",
    android_jar_path="/path/to/android.jar",
    instrumented_dir="/output"
)

instrumentation = RVInstrumentation(config)
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

### RVInstrumentationConfig

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
rv-instrumentation instrument --apk /path/to/app.apk --output /output

# With custom monitors and force re-instrumentation
rv-instrumentation instrument \
    --apk /path/to/app.apk \
    --monitor-dir /custom/monitors \
    --output /output \
    --force \
    --summary
```

### Batch Instrumentation

```bash
# Instrument all APKs in directory
rv-instrumentation batch \
    --apks-dir /path/to/apks \
    --output /output \
    --verbose \
    --summary
```

### Configuration Validation

```bash
# Validate configuration without running instrumentation
rv-instrumentation instrument --apk /path/to/app.apk --output /tmp --dry-run
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
| `--verbose, -v` | Enable verbose logging |
| `--summary` | Display instrumentation summary |
| `--dry-run` | Validate configuration only |

## Development

### Running Tests

```bash
cd modules/rv-instrumentation

# Run all tests
poetry run pytest tests/ -v

# Run with coverage
poetry run pytest --cov=src -v
```

### Test Structure

- `tests/test_config.py`: Configuration and Pydantic model tests
- `tests/conftest.py`: Shared fixtures (temp_workspace, mock_tools_directory, etc.)

### Adding New Tests

```python
from rv_instrumentation import RVInstrumentationConfig
from unittest.mock import patch, MagicMock

def test_new_feature(temp_workspace):
    # Use temp_workspace fixture for isolated testing
    with patch('rv_instrumentation.config.LoggingManager') as mock_logging:
        mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
        # Test implementation
```

## Configuration Examples

### Minimal Configuration (Environment-based)

```python
# Requires RVSEC_HOME and ANDROID_HOME environment variables
config = RVInstrumentationConfig()
```

### Explicit Configuration

```python
config = RVInstrumentationConfig(
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
rv-instrumentation batch --monitor-dir /monitors --apks-dir /apks --output /instrumented
```

### With rv-experiment

The module integrates with experiment orchestration:

```python
from rv_instrumentation import RVInstrumentation, RVInstrumentationConfig

# Called by ExperimentController during pre-processing phase
config = RVInstrumentationConfig(monitor_output_dir=experiment_config.monitor_dir)
instrumentation = RVInstrumentation(config)
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
