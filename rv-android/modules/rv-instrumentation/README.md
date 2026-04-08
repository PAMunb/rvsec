# RV-Instrumentation Module

APK instrumentation for runtime verification monitor weaving.

## Overview

The RV-Instrumentation module transforms standard Android APKs into runtime verification-enabled artifacts. It integrates generated monitor artifacts from rv-monitor-generator with Android applications through a pipeline of decompilation, monitor integration, AspectJ weaving, recompilation, and signing.

### Key Features

- **Instrumentation Pipeline**: APK transformation with decompilation (dex2jar), monitor integration, AspectJ weaving, recompilation (d8), and signing stages
- **Monitor Integration**: Integrates rv-monitor-generator artifacts (AspectJ aspects and Java monitor classes) for both JCA and generic specification sets
- **Configuration System**: Priority-based path resolution with RVSEC_HOME auto-discovery and explicit overrides
- **Batch Processing**: Batch instrumentation with error tracking per APK
- **Error Handling**: Error tracking with rv-android-core infrastructure, JSON error reports for failed APKs
- **CLI Interface**: Command-line interface with validation, dry-run mode, and summary output

## Architecture

### Instrumentation Pipeline

1. **APK Decompilation**: DEX to JAR conversion using dex2jar toolchain
2. **Monitor Integration**: Injection of generated AspectJ and Java monitor artifacts
3. **AspectJ Weaving**: Integration of monitoring pointcuts with application bytecode
4. **Dependency Integration**: Merge runtime verification support libraries
5. **Recompilation**: JAR to DEX conversion using Android d8 compiler
6. **APK Signing**: Create deployment-ready instrumented APK

### Core Components

- **RVInstrumentation** (`rvandroid.py`): Core instrumentation engine orchestrating the complete pipeline (decompilation, monitor integration, weaving, recompilation, signing)
- **RVInstrumentationConfig** (`config.py`): Configuration management with priority-based path resolution and validation
- **Dex2jarTools** (`config.py`): Pydantic model for dex2jar tool suite paths
- **InstrumentationResults** (`config.py`): Results model with computed success rate

### Integration Points

- **rv-android-core**: Uses App domain model, ErrorHandler, LoggingManager, and configuration utilities
- **rv-monitor-generator**: Integrates generated monitor artifacts (*.aj and *.java files)
- **rv-experiment**: Called by ExperimentController during the pre-processing phase
- **Android Toolchain**: dex2jar, AspectJ compiler (ajc), Android d8, jarsigner

## Installation

```bash
# Install dependencies
cd modules/rv-instrumentation
uv sync

# Install in development mode with pip
pip install -e .
```

## Configuration

The module uses a priority-based configuration system:

1. **Individual parameters** (highest priority)
2. **Explicit rvsec_root parameter**
3. **RVSEC_HOME environment variable**
4. **Error if no valid source**

### Required Dependencies

- Android SDK (ANDROID_HOME environment variable)
- JavaMOP and RV-Monitor tools
- Generated monitor artifacts from rv-monitor-generator
- dex2jar toolchain
- AspectJ compiler (ajc)

**Note:** The module includes a bundled development keystore for APK signing. For production use, provide your own keystore via configuration.

## Keystore Configuration

The module includes a bundled development keystore (`assets/keystore.jks`) with password `"password"` for convenient development and testing. This keystore allows instrumented APKs to be installed on development devices and emulators.

### Using Custom Keystore

For production or specific signing requirements, provide your own keystore:

```bash
# Via CLI
rv-instrumentation instrument \
    --apk /path/to/app.apk \
    --keystore /path/to/your/keystore.jks \
    --keystore-password yourpassword \
    --output /output

# Via configuration
config = RVInstrumentationConfig(
    keystore_file="/path/to/your/keystore.jks",
    keystore_password="yourpassword"
)
```

### Creating a Custom Keystore

```bash
# Generate new keystore for development
keytool -genkey -keystore my-keystore.jks -alias server \
    -keyalg RSA -keysize 2048 -validity 10000

# Use with rv-instrumentation
rv-instrumentation instrument \
    --apk app.apk \
    --keystore my-keystore.jks \
    --keystore-password mypassword \
    --output /instrumented
```

## Usage

### Command Line Interface

#### Single APK Instrumentation

```bash
# Basic instrumentation using environment configuration
rv-instrumentation instrument --apk /path/to/app.apk --output /output/instrumented

# Force re-instrumentation with custom monitor directory
rv-instrumentation instrument \
    --apk /path/to/app.apk \
    --monitor-dir /custom/monitors \
    --output /output/instrumented \
    --force \
    --summary
```

#### Batch APK Instrumentation

```bash
# Batch instrument all APKs in directory
rv-instrumentation batch --apks-dir /path/to/apks --output /output/instrumented

# Batch with verbose output and summary
rv-instrumentation batch \
    --apks-dir /path/to/apks \
    --output /output/instrumented \
    --verbose \
    --summary
```

#### Configuration Validation

```bash
# Validate configuration without performing instrumentation
rv-instrumentation instrument --apk /path/to/app.apk --output /tmp --dry-run
```

#### Custom Configuration

```bash
# Using custom RVSEC installation
rv-instrumentation batch \
    --rvsec-root /custom/rvsec \
    --apks-dir /path/to/apks \
    --output /output/instrumented

# Complete custom configuration
rv-instrumentation instrument \
    --apk /path/to/app.apk \
    --monitor-dir /custom/monitors \
    --android-jar /custom/android.jar \
    --keystore /custom/keystore.jks \
    --keystore-password mypassword \
    --dex2jar-home /custom/dex2jar \
    --output /output/instrumented
```

### Programmatic Interface

```python
from rv_instrumentation import RVInstrumentation, RVInstrumentationConfig

# Create configuration
config = RVInstrumentationConfig(
    rvsec_root="/path/to/rvsec",
    monitor_output_dir="/path/to/monitors",
    instrumented_dir="/output/instrumented"
)

# Initialize instrumentation engine
instrumentation = RVInstrumentation(config)

# Instrument APKs
results = instrumentation.instrument_apks(
    apks_dir="/path/to/apks",
    results_dir="/output/instrumented",
    force_instrumentation=False
)

# Check results
print(f"Success rate: {results.success_rate}%")
if results.errors:
    print(f"Failed: {len(results.errors)} APKs")
```

## CLI Options

### Commands

- `instrument`: Instrument a single APK
- `batch`: Batch instrument multiple APKs

### Configuration Options

- `--rvsec-root`: RVSEC installation root directory
- `--monitor-dir`: Directory containing generated monitor artifacts
- `--android-jar`: Path to Android SDK android.jar
- `--android-platforms-dir`: Android SDK platforms directory
- `--keystore`: Keystore file for APK signing (optional, uses bundled development keystore by default)
- `--keystore-password`: Keystore password (optional, defaults to "password")
- `--working-dir`: Base working directory
- `--tmp-dir`: Temporary directory for processing
- `--dex2jar-home`: dex2jar tools directory

### Input/Output Options

- `--apk`: APK file to instrument (single mode)
- `--apks-dir`: Directory containing APKs (batch mode)
- `--output`: Output directory for instrumented APKs
- `--force`: Force re-instrumentation

### Utility Options

- `--verbose, -v`: Enable verbose output
- `--summary`: Display instrumentation summary
- `--dry-run`: Validate configuration only

## Error Handling

The instrumentation pipeline provides comprehensive error tracking:

- **Configuration Errors**: Invalid paths, missing tools, permission issues
- **Command Execution Errors**: Tool failures with specific error codes
- **General Errors**: Unexpected failures with full context
- **Error Reports**: JSON error reports saved to output directory

## Integration

### With rv-monitor-generator

```bash
# 1. Generate monitors
rv-monitor-generator generate --specs-dir /path/to/specs --output /monitors

# 2. Instrument APKs with generated monitors
rv-instrumentation batch \
    --monitor-dir /monitors \
    --apks-dir /path/to/apks \
    --output /instrumented
```

### With Experiment Frameworks

The instrumented APKs can be used with various Android testing frameworks:

- DroidBot: Automated UI testing
- Monkey: Random UI testing
- Custom testing scripts

### Environment Variables

- `RVSEC_HOME`: RVSEC installation root directory
- `ANDROID_HOME`: Android SDK installation directory

## Output

### Instrumented APKs

- Signed APKs ready for deployment
- Integrated runtime verification monitors
- Complete monitoring pointcut coverage
- Minimal runtime overhead

### Error Reports

- `instrument_errors.json`: Detailed error information
- Tool-specific error codes and messages
- Pipeline stage failure identification

## Examples

### Basic Workflow

```bash
# 1. Set environment
export RVSEC_HOME=/path/to/rvsec
export ANDROID_HOME=/path/to/android-sdk

# 2. Generate monitors (from rv-monitor-generator)
rv-monitor-generator generate --specs-dir $RVSEC_HOME/specs/jca --output /tmp/monitors

# 3. Instrument APKs
rv-instrumentation batch \
    --monitor-dir /tmp/monitors \
    --apks-dir /path/to/apks \
    --output /tmp/instrumented \
    --summary

# 4. Results
ls /tmp/instrumented/        # Instrumented APKs
cat /tmp/instrumented/instrument_errors.json  # Error report (if any)
```

### Development Workflow

```bash
# Validate configuration
rv-instrumentation instrument --apk test.apk --output /tmp --dry-run

# Test with single APK
rv-instrumentation instrument \
    --apk test.apk \
    --output /tmp/test \
    --verbose \
    --summary

# Batch process
rv-instrumentation batch \
    --apks-dir /experiments/apks \
    --output /experiments/instrumented \
    --force \
    --summary
```

## Dependencies

### Internal (rv-android)

- `rv-android-core`: App domain model, ErrorHandler, LoggingManager, utilities

### External

- `pydantic`: Configuration validation and data models
- Python 3.12+
- Android SDK with platform tools (d8 compiler)
- Java 8+ (jarsigner, AspectJ compiler)
- dex2jar toolchain
- Maven (dependency resolution for runtime libraries)

Note: rv-monitor-generator is not a Python dependency, but its output artifacts (*.aj, *.java) are required input for the instrumentation pipeline.

## License

Part of the rv-android project.