# CLAUDE.md - rv-monitor-generator

This document provides guidance for Claude Code when working with the rv-monitor-generator module.

## Module Overview

The rv-monitor-generator module provides JavaMOP and RV-Monitor integration for generating runtime verification monitors from MOP (Monitoring-Oriented Programming) specifications. It transforms formal property specifications into executable monitoring artifacts (AspectJ aspects and Java monitor classes) that can be woven into Android applications for runtime verification.

## Architecture

### Core Components

```
src/rv_monitor_generator/
├── __init__.py                          # Public API exports
├── __main__.py                          # CLI entry point
├── config.py                            # RVGeneratorConfig with path resolution
└── runtime_verification_generator.py   # Core generation pipeline
```

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `RuntimeVerificationGenerator` | Core generator orchestrating JavaMOP and RV-Monitor execution pipeline |
| `RVGeneratorConfig` | Configuration management with intelligent path resolution and validation |
| `ConfigurationError` | Custom exception for configuration validation failures |

### Class Diagram

```
RVGeneratorConfig (Pydantic Model)
├── javamop_bin: str          # Path to JavaMOP binary
├── rvmonitor_bin: str        # Path to RV-Monitor binary
├── mop_specs_dir: str        # Directory with .mop specification files
├── aspects_dir: str          # Directory with custom .aj AspectJ files
└── rvsec_root: str           # Optional RVSEC root for auto-discovery

RuntimeVerificationGenerator (Pydantic Model)
├── config: RVGeneratorConfig
├── _logger: Logger
├── _error_handler: ErrorHandler
├── generate_monitors(output_dir) -> bool
├── get_generation_summary(output_dir) -> Dict
├── _execute_javamop(output_dir)
├── _execute_rvmonitor(output_dir)
└── _get_mop_specs() -> list
```

## Monitor Generation Pipeline

The generation process follows a well-defined pipeline:

```
1. Validate Configuration
   └── Check tool binaries, directories, MOP files

2. Prepare Output Directory
   └── Reset/create clean output folder

3. Execute JavaMOP
   ├── Process .mop files with -merge flag
   ├── Generate .aj AspectJ files
   ├── Generate .rvm intermediate files
   └── Move .rvm files to output (workaround for JavaMOP -d bug)

4. Copy Custom Aspects
   └── Copy .aj files from aspects_dir to output

5. Execute RV-Monitor
   ├── Process .rvm files with -merge flag
   ├── Generate .java monitor classes
   └── Clean up intermediate .rvm files

6. Return Success/Failure
```

## Configuration Priority System

The configuration system uses a priority-based path resolution:

1. **Individual tool paths** (highest priority): Explicit paths for `javamop_bin`, `rvmonitor_bin`, `mop_specs_dir`, `aspects_dir`
2. **Explicit rvsec_root**: Automatic path discovery from RVSEC installation root
3. **RVSEC_HOME environment variable**: Fallback to environment-based discovery
4. **Configuration error**: If no valid source is available

### Standard RVSEC Directory Layout

```
$RVSEC_HOME/
├── javamop/bin/javamop           # JavaMOP binary
├── rv-monitor/bin/rv-monitor     # RV-Monitor binary
└── rvsec/rvsec-mop/src/main/resources/
    ├── jca/                      # JCA cryptographic specifications
    │   ├── MessageDigestSpec.mop
    │   ├── SecureRandomSpec.mop
    │   ├── CipherSpec.mop
    │   └── ...
    ├── generic/                  # Generic pattern specifications
    │   ├── IteratorSpec.mop
    │   └── ...
    └── aspect/                   # Custom AspectJ files
        ├── logging.aj
        └── coverage.aj
```

## Specification Sets

The module supports two distinct specification categories:

### JCA Specifications (Java Cryptography Architecture)

Monitor cryptographic API usage patterns:
- `MessageDigest`: Algorithm validation (SHA-256, SHA-384, SHA-512)
- `SecureRandom`: Entropy source and PRNG algorithm verification
- `Cipher`: Encryption/decryption sequence monitoring
- `KeyGenerator`: Key generation operation validation

### Generic Specifications

Monitor general programming patterns:
- `Iterator`: Enforce hasNext() before next() pattern
- `Collections`: Detect modification during iteration
- `Streams`: Resource lifecycle management

**Important**: These specification sets are used independently in experiments. Do not mix them - one experiment uses JCA specs, another uses generic specs.

## Development Commands

### Installation

```bash
cd modules/rv-monitor-generator
uv sync
```

### Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=rv_monitor_generator

# Skip slow integration tests
uv run pytest -m "not slow"

# Specific test file
uv run pytest tests/test_runtime_verification_generator.py -v
```

### CLI Usage

```bash
# Generate JCA monitors (using RVSEC_HOME)
rv-monitor-generator generate --output /output/jca-monitors

# Explicit specification directory
rv-monitor-generator generate \
  --specs-dir /path/to/rvsec/rvsec-mop/src/main/resources/jca \
  --output /output/jca-monitors

# Full explicit configuration
rv-monitor-generator generate \
  --javamop-bin /path/to/javamop \
  --rvmonitor-bin /path/to/rv-monitor \
  --specs-dir /path/to/specs \
  --aspects-dir /path/to/aspects \
  --output /output/monitors

# With verbose output and summary
rv-monitor-generator generate \
  --specs-dir /path/to/specs \
  --output /output/monitors \
  --verbose --summary
```

### Programmatic Usage

```python
from rv_monitor_generator import RuntimeVerificationGenerator, RVGeneratorConfig

# Environment-based configuration (uses RVSEC_HOME)
generator = RuntimeVerificationGenerator()
success = generator.generate_monitors('/output/monitors')

# Explicit configuration for JCA specifications
jca_config = RVGeneratorConfig(
    rvsec_root='/path/to/rvsec',
    mop_specs_dir='/path/to/rvsec/rvsec-mop/src/main/resources/jca'
)
jca_generator = RuntimeVerificationGenerator(jca_config)
jca_generator.generate_monitors('/output/jca-monitors')

# Generic specifications
generic_config = RVGeneratorConfig(
    rvsec_root='/path/to/rvsec',
    mop_specs_dir='/path/to/rvsec/rvsec-mop/src/main/resources/generic'
)
generic_generator = RuntimeVerificationGenerator(generic_config)
generic_generator.generate_monitors('/output/generic-monitors')

# Get generation summary
summary = generator.get_generation_summary('/output/monitors')
print(f"AspectJ files: {summary['aspectj_files']}")
print(f"Monitor classes: {summary['monitor_classes']}")
```

## Generated Artifacts

After successful generation, the output directory contains:

```
output/
├── MultiSpec_*.aj              # Merged AspectJ aspects (pointcuts + advice)
├── *MonitorAspect.aj           # Individual monitor aspects
├── *.java                      # Java monitor classes
├── logging.aj                  # Custom aspects (copied from aspects_dir)
└── coverage.aj                 # Custom aspects (copied from aspects_dir)
```

### Artifact Purposes

| Artifact Type | Extension | Purpose |
|--------------|-----------|---------|
| AspectJ aspects | `.aj` | Define pointcuts for method interception, used by rv-instrumentation |
| Monitor classes | `.java` | Implement runtime verification logic, compiled into instrumented APKs |

## Integration Points

### With rv-instrumentation

The generated monitors are consumed by rv-instrumentation for APK weaving:

```bash
# 1. Generate monitors
rv-monitor-generator generate --specs-dir /specs/jca --output /monitors

# 2. Instrument APK with generated monitors
rv-instrumentation instrument --apk app.apk --monitors /monitors --output /instrumented
```

### With rv-experiment

The experiment orchestration system uses rv-monitor-generator in the pre-processing phase:

```python
# Experiment configuration specifies specification set
config = ExperimentConfig(
    specification_set="jca",  # or "generic"
    generate_monitors=True
)
```

## Error Handling

The module uses rv-android-core infrastructure for error handling:

- `ErrorHandler`: Centralized error handling with context
- `ConfigurationError`: Raised for configuration validation failures
- `CommandException`: Raised when JavaMOP or RV-Monitor execution fails

### Common Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| `ConfigurationError: JavaMOP binary not found` | Invalid javamop_bin path | Verify RVSEC installation and paths |
| `ConfigurationError: No MOP specification files found` | Empty or invalid specs directory | Check mop_specs_dir path |
| `CommandException: javamop failed` | Invalid MOP specification syntax | Review .mop file syntax |
| `CommandException: rvmonitor failed` | Invalid RVM file | Check JavaMOP output |

## Dependencies

- **rv-android-core**: ErrorHandler, LoggingManager, Command utilities
- **pydantic**: Configuration validation
- **External**: JavaMOP, RV-Monitor, AspectJ (Java 8+)

## Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `RVSEC_HOME` | RVSEC installation root for auto-discovery | Only if not using explicit paths |

## Performance Characteristics

| Specification Set Size | Generation Time | Memory Usage |
|----------------------|-----------------|--------------|
| Small (< 5 specs) | < 30 seconds | 512MB |
| Medium (5-15 specs) | 30-90 seconds | 1GB |
| Large (> 15 specs) | 90-180 seconds | 2GB |

## Testing Strategy

### Test Categories

| Directory | Purpose | Dependencies |
|-----------|---------|--------------|
| `tests/test_runtime_verification_generator.py` | Unit tests with mocking | None |
| `tests/test_runtime_verification_generator_complete.py` | Complete coverage tests | None |

### Test Fixtures

- `temp_environment`: Creates mock RVSEC directory structure
- `temp_environment_with_real_specs`: Creates mock structure with real MOP content
- `rvsec_root_dir`: Discovers real RVSEC installation (skips if not found)

### Integration Tests

Integration tests require a valid RVSEC installation and are marked with `@pytest.mark.slow`. They are skipped automatically if RVSEC is not found.

## Known Issues and Workarounds

### JavaMOP -d Option Bug

JavaMOP's `-d` option does not correctly move `.rvm` files to the output directory. The generator implements a workaround by manually moving `.rvm` files after JavaMOP execution:

```python
# In _execute_javamop()
utils.move_files_by_extension(constants.EXTENSION_RVM, self.config.mop_specs_dir, output_dir)
```

### Tool Help Exit Codes

JavaMOP and RV-Monitor may return non-zero exit codes when invoked with `-h` flag. The configuration validation handles this by checking for any output (stdout or stderr) rather than exit code.


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

