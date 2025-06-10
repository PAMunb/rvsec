# RV-Static-Analysis Module

Modern static analysis orchestration system for Android applications with comprehensive tool integration, unified result parsing, and dependency injection architecture.

## Overview

The RV-Static-Analysis module provides sophisticated static analysis capabilities for Android applications through orchestrated execution of multiple analysis tools (GATOR, GESDA, REACH). It implements a modern architecture with comprehensive error handling, flexible configuration management, and unified result parsing into consistent domain models for integration with the broader RV-Android ecosystem.

### Key Features

- **Modern Tool Orchestration**: Sophisticated coordination of GATOR, GESDA, and REACH static analysis tools with lifecycle management
- **Unified Result Parsing**: Advanced parsing system converting tool outputs into consistent domain objects with validation
- **DI-Ready Architecture**: Full dependency injection support with comprehensive configuration management and error handling
- **Flexible Configuration**: Multi-source configuration system with environment variables, explicit parameters, and validation
- **Batch Processing**: High-performance batch analysis workflows with parallel execution and error recovery
- **Modern CLI Interface**: Advanced command-line interface with comprehensive options and progress reporting
- **Monitored Operations Analysis**: Specialized analysis for both JCA cryptography and generic programming pattern reachability

## Architecture

### Static Analysis Pipeline

1. **GESDA Analysis**: Extracts application components, classes, and structural elements
2. **GATOR Analysis**: Builds Window Transition Graph (WTG) for UI navigation analysis
3. **REACH Analysis**: Determines reachability of security-relevant code from entry points
4. **Result Parsing**: Converts tool outputs into unified `StaticAnalysisData` objects

### Core Components

#### Analysis Infrastructure
- **StaticAnalyzer**: Modern analysis orchestrator with comprehensive tool coordination, error handling, and result management
- **StaticAnalysisManager**: High-level analysis coordination with batch processing and lifecycle management
- **AnalysisEngine**: Core execution engine with parallel processing and resource management

#### Configuration System
- **RVStaticAnalysisConfig**: Advanced configuration management with multi-source support, validation, and type safety
- **ConfigurationProvider**: Flexible configuration provider with environment integration and validation
- **PathResolver**: Intelligent path resolution with fallback mechanisms and validation

#### Parsing Infrastructure
- **StaticAnalysisParser**: Unified parsing system with comprehensive format support and validation
- **ToolResultParser**: Specialized parsers for GATOR, GESDA, and REACH output formats
- **DomainModelConverter**: Advanced conversion system for creating consistent domain objects

#### Integration Points

- **rv-android-core**: Uses App domain model, ErrorHandler decorators, LoggingManager, and configuration utilities
- **rv-experiment**: Provides static analysis components for experiment orchestration and task management
- **rv-monitor-generator**: Integrates with monitor specifications for reachability analysis and monitored operations detection

## Installation

```bash
# Install using Poetry (recommended)
cd modules/rv-static-analysis
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

- **GATOR**: Window transition graph analysis tool
- **GESDA**: GUI element static detection tool
- **REACH**: Method reachability analysis tool
- Android SDK (ANDROID_HOME environment variable)
- Java runtime for tool execution
- MOP specifications for reachability analysis

## Usage

### Command Line Interface

#### Single APK Analysis

```bash
# Basic analysis using environment configuration
rv-static-analysis analyze --apk /path/to/app.apk --output /output

# Analysis with custom RVSEC root and verbose output
rv-static-analysis analyze \
    --apk /path/to/app.apk \
    --rvsec-root /custom/rvsec \
    --output /output \
    --verbose \
    --summary
```

#### Batch APK Analysis

```bash
# Batch analyze all APKs in directory
rv-static-analysis batch --apks-dir /path/to/apks --output /output

# Batch with custom configuration and error handling
rv-static-analysis batch \
    --apks-dir /path/to/apks \
    --output /output \
    --continue-on-error \
    --verbose \
    --summary
```

#### Configuration Validation

```bash
# Validate configuration without performing analysis
rv-static-analysis analyze --apk /path/to/app.apk --output /tmp --dry-run
```

### Programmatic Interface

```python
from rv_static_analysis import RVStaticAnalysisConfig, StaticAnalyzer
from rv_static_analysis.analysis.static import StaticAnalysis
from rv_android_core.app import App
from rv_android_core.util.error.error_handler import ErrorHandler

# Create configuration with validation
config = RVStaticAnalysisConfig(
    rvsec_root="/path/to/rvsec",
    lib_dir="/path/to/tools",
    output_dir="/output"
)

# Create App object with metadata
app = App("/path/to/app.apk")

# Initialize analyzer with error handling
analyzer = StaticAnalyzer(app, config)

# Run analysis with error handling
@ErrorHandler.handle_errors(component="StaticAnalysisExample", phase="analyze")
def run_analysis():
    result = analyzer.analyze(tools=["gator", "gesda", "reach"])
    return result

result = run_analysis()

# Process results
if result and result.success:
    print("Static analysis completed successfully")
    
    # Get parsed domain objects
    static_data = analyzer.get_static_data()
    if static_data:
        print(f"Application structure:")
        print(f"  Classes: {len(static_data.classes.classes)}")
        print(f"  Windows: {len(static_data.windows.windows) if static_data.windows else 0}")
        print(f"  WTG nodes: {len(static_data.wtg.nodes) if static_data.wtg else 0}")
        print(f"  Reachable methods: {len(static_data.reach.reachable_methods) if static_data.reach else 0}")
else:
    print(f"Static analysis failed: {result.errors if result else 'Unknown error'}")
```

## CLI Options

### Commands

- `analyze`: Analyze a single APK with static analysis tools
- `batch`: Batch analyze multiple APKs

### Configuration Options

- `--rvsec-root`: RVSEC installation root directory
- `--lib-dir`: Directory containing analysis tool JAR files
- `--android-jar`: Path to Android SDK android.jar
- `--output-dir`: Output directory for analysis results
- `--working-dir`: Base working directory
- `--tmp-dir`: Temporary directory for processing

### Input/Output Options

- `--apk`: APK file to analyze (single mode)
- `--apks-dir`: Directory containing APKs (batch mode)
- `--output`: Output directory for analysis results
- `--force`: Force re-analysis of existing results

### Analysis Control Options

- `--tools`: Specific tools to run (gator,gesda,reach)
- `--android-api-level`: Target Android API level (default: 28)
- `--timeout`: Tool execution timeout in seconds
- `--continue-on-error`: Continue batch processing on tool failures

### Utility Options

- `--verbose, -v`: Enable verbose output
- `--summary`: Display analysis summary
- `--dry-run`: Validate configuration only

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
- Security-relevant code identification
- Entry point analysis

**Output**: JSON file with reachability information

## Output Structure

### Analysis Results

```
output/
├── app_name.apk.gesda      # GESDA application structure
├── app_name.apk.wtg        # GATOR window transition graph
├── app_name.apk.reach      # REACH reachability analysis
└── static_analysis.json    # Unified analysis metadata
```

### Unified Domain Objects

```python
# Access parsed results through StaticAnalysisData
static_data = analyzer.get_static_data()

# Application classes and methods
classes = static_data.classes.classes
for class_info in classes:
    print(f"Class: {class_info.name}")
    print(f"Methods: {len(class_info.methods)}")

# Window transition graph
wtg = static_data.wtg
for window in wtg.windows:
    print(f"Window: {window.class_name}")
    print(f"Transitions: {len(window.transitions)}")

# Reachability information
reach_data = static_data.reach
reachable_methods = reach_data.get_reachable_methods()
print(f"Reachable monitored methods: {len(reachable_methods)}")
```

## Integration

### With rv-monitor-generator

```bash
# 1. Generate monitors from specifications
rv-monitor-generator generate --specs-dir /rvsec/specs/jca --output /monitors

# 2. Run static analysis with monitor context
rv-static-analysis analyze \
    --apk app.apk \
    --output /analysis \
    --monitor-specs /monitors

# 3. Results include monitor reachability
cat /analysis/app.apk.reach  # Shows which monitored operations are reachable
```

### With rv-instrumentation

```bash
# 1. Run static analysis
rv-static-analysis analyze --apk app.apk --output /analysis

# 2. Use analysis results for instrumentation optimization
rv-instrumentation instrument \
    --apk app.apk \
    --static-analysis /analysis \
    --output /instrumented
```

### With Experiment Framework

```python
# Integration with rv-experiment
from rv_experiment.experiment.task.components.static_analysis import StaticAnalysisComponent

class EnhancedStaticAnalysisComponent(StaticAnalysisComponent):
    def analyze_application(self, app):
        """Enhanced analysis with tool selection."""
        
        # Configure analysis based on experiment requirements
        if self.experiment_type == "ui_testing":
            tools = ["gator", "gesda"]  # Focus on UI structure
        elif self.experiment_type == "monitored_operations":
            tools = ["gesda", "reach"]  # Focus on method reachability
        else:
            tools = ["gator", "gesda", "reach"]  # Complete analysis
        
        # Run analysis
        analyzer = StaticAnalyzer(app, self.config)
        result = analyzer.analyze(tools=tools)
        
        return result
```

### Environment Variables

- `RVSEC_HOME`: RVSEC installation root directory
- `ANDROID_HOME`: Android SDK installation directory

## Analysis Metrics

### Performance Characteristics

- **GATOR Analysis**: 30-180 seconds depending on app complexity
- **GESDA Analysis**: 15-60 seconds for structure extraction
- **REACH Analysis**: 20-120 seconds for reachability computation
- **Memory Usage**: 1-4 GB depending on application size

### Scalability

- **Small Apps** (< 100 classes): < 2 minutes total
- **Medium Apps** (100-500 classes): 2-8 minutes total
- **Large Apps** (> 500 classes): 8-20 minutes total
- **Batch Processing**: Parallel execution support for multiple APKs

## Error Handling

The analysis pipeline provides comprehensive error tracking:

- **Configuration Errors**: Invalid paths, missing tools, permission issues
- **Tool Execution Errors**: Analysis tool failures with specific error codes
- **APK Processing Errors**: Invalid APKs, decompilation failures
- **Output Errors**: File system issues, parsing failures
- **Error Reports**: JSON error reports saved to output directory

## Examples

### Basic Analysis Workflow

```bash
# 1. Set environment
export RVSEC_HOME=/path/to/rvsec
export ANDROID_HOME=/path/to/android-sdk

# 2. Run complete static analysis
rv-static-analysis analyze \
    --apk /path/to/app.apk \
    --output /analysis/results \
    --summary

# 3. Results
ls /analysis/results/
# app.apk.gesda  app.apk.wtg  app.apk.reach  static_analysis.json
```

### Selective Tool Analysis

```bash
# Run only GATOR for UI analysis
rv-static-analysis analyze \
    --apk app.apk \
    --output /results \
    --tools gator

# Run GESDA and REACH for monitored operations analysis
rv-static-analysis analyze \
    --apk app.apk \
    --output /results \
    --tools gesda,reach
```

### Batch Processing

```bash
# Analyze all APKs in directory
rv-static-analysis batch \
    --apks-dir /experiments/apks \
    --output /experiments/static_analysis \
    --continue-on-error \
    --summary

# Results organized by APK
ls /experiments/static_analysis/
# app1.apk.gesda  app1.apk.wtg  app1.apk.reach
# app2.apk.gesda  app2.apk.wtg  app2.apk.reach
```

### Development and Debugging

```bash
# Validate configuration
rv-static-analysis analyze \
    --apk test.apk \
    --output /tmp \
    --dry-run

# Verbose analysis with detailed logging
rv-static-analysis analyze \
    --apk app.apk \
    --output /analysis \
    --verbose \
    --timeout 600

# Force re-analysis
rv-static-analysis analyze \
    --apk app.apk \
    --output /analysis \
    --force \
    --summary
```

## Dependencies

- `rv-android-core`: Core Android utilities and domain models
- Android SDK with platform tools
- Java 8+ for tool execution
- Static analysis tools: GATOR, GESDA, REACH (JAR files)

## Contributing

### Adding New Analysis Tools

1. Implement tool wrapper following existing patterns
2. Add tool configuration to RVStaticAnalysisConfig
3. Update CLI options and documentation
4. Add comprehensive tests for new tool integration
5. Update domain models if tool provides new data types

### Code Standards

1. Follow existing code style and documentation patterns
2. Add comprehensive tests for new analysis capabilities
3. Update CLI help and README for new options
4. Ensure backward compatibility with existing analysis results
5. Use rv-android-core infrastructure for error handling and logging

## License

This module is part of the RV-Android project and follows the same licensing terms.