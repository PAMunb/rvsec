# RV-Instrumentation Module

Modern APK instrumentation system for seamless runtime verification monitor integration with comprehensive pipeline orchestration and dependency injection architecture.

## Overview

The RV-Instrumentation module provides sophisticated APK instrumentation capabilities that transform standard Android applications into runtime verification-enabled artifacts through an advanced instrumentation pipeline. It seamlessly integrates generated monitor artifacts from rv-monitor-generator with Android applications, enabling comprehensive monitored operations analysis during application execution with modern error handling and performance optimization.

### Key Features

- **Advanced Instrumentation Pipeline**: Comprehensive APK transformation with decompilation, monitor integration, AspectJ weaving, recompilation, and signing stages
- **Seamless Monitor Integration**: Advanced integration with rv-monitor-generator artifacts supporting both JCA cryptography and generic programming pattern specifications
- **DI-Ready Configuration**: Modern configuration system with multi-source support, validation, and dependency injection preparation
- **High-Performance Batch Processing**: Optimized batch instrumentation workflows with parallel processing and error recovery mechanisms
- **Comprehensive Error Handling**: Full error tracking, reporting, and recovery with rv-android-core infrastructure integration
- **Modern CLI Interface**: Advanced command-line interface with progress reporting, validation, and comprehensive option support

## Architecture

### Instrumentation Pipeline

1. **APK Decompilation**: DEX � JAR conversion using dex2jar toolchain
2. **Monitor Integration**: Injection of generated AspectJ and Java monitor artifacts
3. **AspectJ Weaving**: Integration of monitoring pointcuts with application bytecode
4. **Dependency Integration**: Merge runtime verification support libraries
5. **Recompilation**: JAR � DEX conversion using Android d8 compiler
6. **APK Signing**: Create deployment-ready instrumented APK

### Core Components

#### Instrumentation Infrastructure
- **RVInstrumentation**: Modern core instrumentation engine with comprehensive APK transformation capabilities, error handling, and performance optimization
- **InstrumentationPipeline**: Advanced pipeline orchestrator with stage management, dependency tracking, and rollback capabilities
- **MonitorIntegrator**: Sophisticated monitor integration system supporting multiple specification types and optimization strategies

#### Configuration and Management
- **RVInstrumentationConfig**: Advanced configuration management with multi-source support, validation, and DI-ready design
- **PipelineManager**: High-level pipeline coordination with batch processing and lifecycle management
- **ArtifactManager**: Comprehensive artifact management with caching, validation, and cleanup capabilities

### Integration Points

- **rv-android-core**: Uses App domain model, ErrorHandler decorators, LoggingManager, and configuration utilities
- **rv-monitor-generator**: Integrates generated monitor artifacts for comprehensive runtime verification instrumentation
- **rv-experiment**: Provides instrumentation components for experiment orchestration and automated APK preparation
- **Android Toolchain**: Seamless integration with Android SDK tools, AspectJ compiler, and DEX processing utilities

## Installation

```bash
# Install using Poetry (recommended)
cd modules/rv-instrumentation
poetry install

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
errors = instrumentation.instrument_apks(
    apks_dir="/path/to/apks",
    results_dir="/output/instrumented",
    force_instrumentation=False
)

# Check results
if not errors:
    print("All APKs instrumented successfully")
else:
    print(f"Instrumentation failed for {len(errors)} APKs")
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

- `rv-android-core`: Core Android utilities and domain models
- `rv-monitor-generator`: Monitor generation from MOP specifications
- Python 3.12+
- Android SDK with platform tools
- Java 8+ for tool execution

## Contributing

1. Follow the existing code style and documentation patterns
2. Add comprehensive tests for new features
3. Update CLI help and README for new options
4. Ensure backward compatibility with existing configurations