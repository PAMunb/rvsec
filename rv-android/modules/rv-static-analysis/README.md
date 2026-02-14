# RV-Static-Analysis Module

Static analysis orchestration system for Android applications with comprehensive tool integration and unified result parsing.

## Overview

The RV-Static-Analysis module provides static analysis capabilities for Android applications through coordinated execution of multiple analysis tools (GATOR, GESDA, REACH). It implements an architecture with error handling, configuration management, and unified result parsing into consistent domain models for integration with the broader RV-Android ecosystem.

### Key Features

- **Tool Orchestration**: Coordination of GATOR, GESDA, and REACH static analysis tools
- **Unified Result Parsing**: Parsing system converting tool outputs into consistent domain objects
- **Configuration Management**: Multi-source configuration system with environment variables and validation
- **Batch Processing**: Batch analysis workflows with error recovery
- **Monitored Operations Analysis**: Analysis for both JCA cryptography and generic programming pattern reachability

## Architecture

### Static Analysis Pipeline

1. **GESDA Analysis**: Extracts application components, classes, and structural elements
2. **GATOR Analysis**: Builds Window Transition Graph (WTG) for UI navigation analysis
3. **REACH Analysis**: Determines reachability of monitored operations from entry points
4. **Result Parsing**: Converts tool outputs into unified `StaticAnalysisData` objects

### Core Components

#### Analysis Infrastructure
- **StaticAnalyzer**: Analysis orchestrator with tool coordination, error handling, and result management
- **StaticAnalysisResult**: Result data structure with execution metrics and file paths

#### Configuration System
- **RVStaticAnalysisConfig**: Configuration management with multi-source support and validation
- **PathResolver**: Path resolution with fallback mechanisms and validation

#### Parsing Infrastructure
- **StaticAnalysisParser**: Unified parsing system with format support and validation
- **BaseStaticAnalysisParser**: Base parser for tool-specific output formats
- **GatorParser, GesdaParser, ReachParser**: Specialized parsers for each tool

#### Integration Points

- **rv-android-core**: Uses App domain model, ErrorHandler decorators, LoggingManager
- **rv-experiment**: Provides static analysis components for experiment orchestration
- **rv-monitor-generator**: Integrates with monitor specifications for reachability analysis

## Installation

```bash
# Install dependencies
cd modules/rv-static-analysis
uv sync

# Run tests
uv run pytest
```

## Configuration

The module uses a priority-based configuration system:

1. **Individual parameters** (highest priority)
2. **Explicit rvsec_root parameter**
3. **RVSEC_HOME environment variable**
4. **Error if no valid source**

### Required Dependencies

- **GATOR**: Window transition graph analysis tool
- **GESDA**: GUI element static detection tool
- **REACH**: Method reachability analysis tool
- Android SDK (ANDROID_HOME environment variable)
- Java runtime for tool execution

## Usage

### Programmatic Interface

```python
from rv_static_analysis.config import RVStaticAnalysisConfig
from rv_static_analysis.analysis.static.static_analysis import StaticAnalyzer
from rv_android_core.domain.app import App

# Create configuration
config = RVStaticAnalysisConfig(
    rvsec_root="/path/to/rvsec",
    lib_dir="/path/to/tools",
    output_dir="/output"
)

# Create App object
app = App("/path/to/app.apk")

# Initialize analyzer
analyzer = StaticAnalyzer(app, config, output_dir="/analysis")

# Run analysis
result = analyzer.analyze()

# Process results
if result and result.success:
    print("Static analysis completed successfully")

    # Get metrics
    metrics = analyzer.get_metrics()
    print(f"Execution times: {result.execution_times}")
else:
    print(f"Static analysis failed: {result.errors if result else 'Unknown error'}")
```

### Configuration Usage

```python
from rv_static_analysis.config import RVStaticAnalysisConfig

# Basic configuration
config = RVStaticAnalysisConfig(
    rvsec_root="/path/to/rvsec"
)

# Get available tools
tools = config.get_static_analysis_tools()
print(f"Available tools: {list(tools.keys())}")

# Get tool components
components = config.get_tool_components()
print(f"Tool components: {list(components.keys())}")

# Generate tool command
command = config.get_tool_command(
    tool_name="gesda",
    apk_path="/path/to/app.apk",
    output_file="/output/app.gesda"
)
print(f"GESDA command: {' '.join(command)}")
```

## Analysis Tools

### GATOR (GUI Analysis Tool for Android)

**Purpose**: Builds Window Transition Graph (WTG) representing app navigation structure

**Capabilities**:
- Activity and window identification
- UI transition mapping
- Event handler analysis
- Navigation flow understanding

**Output**: WTG XML file with navigation graph

### GESDA (GUI Element Static Detection for Android)

**Purpose**: Extracts comprehensive application structure and GUI elements

**Capabilities**:
- Class hierarchy extraction
- Method signature analysis
- GUI element identification
- Component relationship mapping

**Output**: JSON file with application structure

### REACH (Reachability Analysis)

**Purpose**: Determines reachability of monitored operations from application entry points

**Capabilities**:
- Method reachability analysis
- MOP specification integration
- Entry point analysis

**Output**: CSV file with reachability information

## Output Structure

### Analysis Results

```
output/
├── app_name.gesda      # GESDA application structure
├── app_name.wtg        # GATOR window transition graph
└── app_name.reach      # REACH reachability analysis
```

### Domain Objects

```python
# Access parsed results through StaticAnalysisParser
from rv_static_analysis.parser.static.static_analysis_parser import read_static_analysis_files

static_data = read_static_analysis_files("app_name", "/output")

# Application classes
if static_data.classes:
    print(f"Classes found: {len(static_data.classes.classes)}")

# Window transition graph
if static_data.wtg:
    print(f"Windows: {len(static_data.wtg.windows)}")

# Reachability information
if static_data.reach:
    print(f"Reachable methods: {len(static_data.reach.reachable_methods)}")
```

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=rv_static_analysis

# Run specific test categories
uv run pytest tests/analysis/
uv run pytest tests/parser/
```

### Test Structure

- `tests/analysis/`: Analysis infrastructure tests
- `tests/parser/`: Parser functionality tests
- `tests/config/`: Configuration management tests

## Integration

### With rv-experiment

```python
# Integration through experiment configuration
from rv_experiment.config import ExperimentConfig

config = ExperimentConfig(
    name="static_analysis_experiment",
    run_static_analysis=True
)

# Static analysis configuration is created automatically
static_config = config.get_static_analysis_config()
```

### With rv-monitor-generator

```python
# Reachability analysis with monitor specifications
config = RVStaticAnalysisConfig(
    rvsec_root="/path/to/rvsec",
    mop_dir="/path/to/specifications"
)

# REACH tool will use specifications for reachability analysis
```

## Environment Variables

- `RVSEC_HOME`: RVSEC installation root directory
- `ANDROID_HOME`: Android SDK installation directory
- `RV_RT_JAR`: Java runtime JAR path (rt.jar)

## Dependencies

- `rv-android-core`: Core Android utilities and domain models
- Android SDK with platform tools
- Java 8+ for tool execution
- Static analysis tools: GATOR, GESDA, REACH (JAR files)

## Contributing

### Adding New Analysis Tools

1. Create tool wrapper following existing patterns
2. Add tool configuration to RVStaticAnalysisConfig
3. Implement parser for tool output format
4. Add comprehensive tests
5. Update domain models if needed

### Code Standards

1. Follow existing code style and documentation patterns
2. Add comprehensive tests for new functionality
3. Ensure backward compatibility
4. Use rv-android-core infrastructure for error handling and logging

## License

This module is part of the RV-Android project and follows the same licensing terms.