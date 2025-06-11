# RV-Monitor-Generator Module

Runtime verification monitor generation system with JavaMOP and RV-Monitor integration for monitored operations testing.

## Overview

The RV-Monitor-Generator module provides runtime verification monitor generation capabilities through integrated JavaMOP and RV-Monitor tools. It transforms formal property specifications into runtime verification monitors, AspectJ aspects, and Java monitor classes for integration with Android applications. The module supports both JCA cryptography and generic programming pattern specifications.

### Key Features

- **JavaMOP Integration**: Integration with JavaMOP compiler for monitor generation
- **RV-Monitor Support**: Monitor generation using RV-Monitor with runtime verification capabilities
- **AspectJ Generation**: Generation of AspectJ aspects with pointcut support
- **Specification Management**: Multi-specification support for JCA, generic patterns, and custom sets
- **Configuration System**: Configuration system with multi-source support and validation
- **Batch Processing**: Batch monitor generation with error recovery

## Architecture

### Monitor Generation Pipeline

1. **Specification Parsing**: Parse MOP specifications from .mop files
2. **JavaMOP Processing**: Generate Java monitor classes using JavaMOP compiler
3. **RV-Monitor Integration**: Apply RV-Monitor optimizations for performance
4. **AspectJ Generation**: Create AspectJ aspects for runtime weaving
5. **Library Integration**: Package supporting runtime verification libraries
6. **Output Organization**: Structure generated artifacts for instrumentation pipeline

### Core Components

#### Monitor Generation Infrastructure
- **RuntimeVerificationGenerator**: Core generator with pipeline orchestration and error handling
- **RVGeneratorConfig**: Configuration management with multi-source support and validation

#### Integration Points
- **rv-android-core**: Uses ErrorHandler decorators, LoggingManager for infrastructure
- **rv-experiment**: Provides monitor generation components for experiment orchestration
- **rv-static-analysis**: Coordinates with static analysis for monitor placement
- **rv-instrumentation**: Integrates generated monitors with instrumentation pipeline

### Specification Categories

#### JCA Cryptography Specifications
- **Purpose**: Monitor Java Cryptography Architecture API usage patterns
- **Specifications**: Cipher, MessageDigest, SecureRandom, KeyGenerator, etc.
- **Use Cases**: Cryptographic security testing, compliance validation

#### Generic Programming Pattern Specifications
- **Purpose**: Monitor common programming patterns and best practices
- **Specifications**: Iterator patterns, Collections usage, Resource management
- **Use Cases**: General software quality assurance, pattern compliance

#### Custom Specification Sets
- **Purpose**: User-defined monitoring specifications
- **Format**: Standard MOP specification format
- **Use Cases**: Domain-specific monitoring, specialized testing requirements

## Installation

```bash
# Install using Poetry
cd modules/rv-monitor-generator
poetry install

# Run tests
poetry run pytest
```

## Configuration

### Required Dependencies

- **JavaMOP**: Monitor-oriented programming compiler
- **RV-Monitor**: Runtime verification monitor generator  
- **AspectJ**: Aspect-oriented programming framework
- Java 8+ for tool execution

### Environment Variables

- `RVSEC_HOME`: RVSEC installation root directory
- `JAVAMOP_HOME`: JavaMOP installation directory (optional)

## Usage

### Programmatic Interface

```python
from rv_monitor_generator import RuntimeVerificationGenerator, RVGeneratorConfig

# Create configuration
config = RVGeneratorConfig(
    rvsec_root="/path/to/rvsec",
    javamop_bin="/path/to/javamop",
    rvmonitor_bin="/path/to/rv-monitor",
    mop_specs_dir="/path/to/specifications",
    aspects_dir="/path/to/aspects"
)

# Initialize generator
generator = RuntimeVerificationGenerator(config)

# Generate monitors
output_dir = "/path/to/output"
generator.generate_monitors(output_dir)

print("Monitor generation completed")
```

### Configuration Usage

```python
from rv_monitor_generator.config import RVGeneratorConfig

# Basic configuration with defaults
config = RVGeneratorConfig(
    rvsec_root="/path/to/rvsec"
)

# JCA cryptography specifications
config_jca = RVGeneratorConfig(
    rvsec_root="/path/to/rvsec",
    mop_specs_dir="/path/to/rvsec/specs/jca"
)

# Generic programming patterns
config_generic = RVGeneratorConfig(
    rvsec_root="/path/to/rvsec", 
    mop_specs_dir="/path/to/rvsec/specs/generic"
)

# Custom specifications
config_custom = RVGeneratorConfig(
    rvsec_root="/path/to/rvsec",
    mop_specs_dir="/path/to/custom/specs"
)
```

## Output Structure

### Generated Artifacts

```
output/
├── *.rvm                    # RV-Monitor files
├── *.aj                     # AspectJ aspects 
├── *.java                   # Java monitor classes
└── MultiSpec_*MonitorAspect.aj  # Combined aspects
```

### Monitor Integration

```bash
# Generated monitors are ready for instrumentation
# AspectJ files: Used by rv-instrumentation for APK weaving
# Java files: Compiled and included in instrumented applications
# RVM files: Intermediate representation for debugging
```

## Specification Management

### JCA Cryptography Monitoring

```python
# Configuration for JCA specifications
config = RVGeneratorConfig(
    rvsec_root="/path/to/rvsec",
    mop_specs_dir="/path/to/rvsec/specs/jca"
)

# Generates monitors for:
# - Cipher usage patterns
# - MessageDigest operations  
# - SecureRandom generation
# - Key management operations
# - SSL/TLS context usage
```

### Generic Pattern Monitoring

```python
# Configuration for generic specifications
config = RVGeneratorConfig(
    rvsec_root="/path/to/rvsec",
    mop_specs_dir="/path/to/rvsec/specs/generic"
)

# Generates monitors for:
# - Iterator usage patterns
# - Collections operations
# - Resource management
# - Threading patterns
```

### Custom Specifications

```python
# Configuration for custom specifications
config = RVGeneratorConfig(
    rvsec_root="/path/to/rvsec",
    mop_specs_dir="/path/to/custom/specs"
)

# User-defined MOP specifications
# Standard .mop file format
# Custom monitoring logic
```

## Testing

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=rv_monitor_generator

# Run specific tests
poetry run pytest tests/test_runtime_verification_generator.py
```

### Test Structure

- `tests/`: Core generator functionality tests
- Test specification parsing and validation
- Test monitor generation pipeline
- Test configuration management

## Integration

### With rv-experiment

```python
# Integration through experiment configuration
from rv_experiment.config import ExperimentConfig

config = ExperimentConfig(
    name="monitor_experiment",
    specification_set="jca",  # or "generic" or "custom"
    generate_monitors=True
)

# Monitor generation configuration is created automatically
monitor_config = config.get_monitored_operations_config()
```

### With rv-instrumentation

```bash
# 1. Generate monitors
rv-monitor-generator generate --specs-dir /specs/jca --output /monitors

# 2. Use monitors for instrumentation
rv-instrumentation instrument --apk app.apk --monitors /monitors --output /instrumented
```

## Performance Characteristics

### Generation Performance

- **Small Specification Sets** (< 5 specs): < 30 seconds
- **Medium Specification Sets** (5-15 specs): 30-90 seconds  
- **Large Specification Sets** (> 15 specs): 90-180 seconds
- **Memory Usage**: 512MB-2GB depending on specification complexity

## Dependencies

- `rv-android-core`: Core utilities and error handling
- JavaMOP: Monitor-oriented programming compiler
- RV-Monitor: Runtime verification monitor generator
- AspectJ: Aspect-oriented programming framework
- Java 8+ runtime

## Contributing

### Adding New Specifications

1. Create .mop specification files following JavaMOP format
2. Place in appropriate specification directory (jca, generic, custom)
3. Test monitor generation and validation
4. Add tests for new specifications
5. Update documentation

### Code Standards

1. Follow existing code style and patterns
2. Add comprehensive tests for new functionality
3. Use rv-android-core infrastructure for error handling
4. Maintain backward compatibility

## License

This module is part of the RV-Android project and follows the same licensing terms.