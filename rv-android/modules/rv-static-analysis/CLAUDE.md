# CLAUDE.md - rv-static-analysis Module

This file provides guidance to Claude Code when working with the rv-static-analysis module.

## Module Overview

The rv-static-analysis module provides static analysis capabilities for Android applications through coordinated execution of three analysis tools: GATOR, GESDA, and REACH. It parses tool outputs into unified domain objects for integration with the broader RV-Android ecosystem.

### Purpose

- Orchestrate execution of static analysis tools (GATOR, GESDA, REACH)
- Parse tool outputs into consistent domain objects
- Provide unified configuration management for static analysis workflows
- Enable navigation and reachability analysis for Android applications

### Key Features

- **Tool Orchestration**: Coordinated execution of GATOR, GESDA, and REACH tools
- **Unified Parsing**: Convert tool-specific outputs into consistent domain objects
- **Configuration Management**: Multi-source configuration with environment variables and validation
- **Intelligent Caching**: Skip analysis if output files already exist

## Architecture

### Directory Structure

```
rv-static-analysis/
├── src/rv_static_analysis/
│   ├── __init__.py              # Public API exports
│   ├── __main__.py              # CLI entry point
│   ├── config.py                # RVStaticAnalysisConfig
│   ├── analysis/
│   │   └── static/
│   │       └── static_analysis.py  # StaticAnalyzer, StaticAnalysisResult
│   └── parser/
│       └── static/
│           ├── base_parser.py           # BaseStaticAnalysisParser
│           ├── gator_parser.py          # GatorParser (WTG)
│           ├── gesda_parser.py          # GesdaParser (GUI elements)
│           ├── reach_parser.py          # ReachParser (reachability)
│           └── static_analysis_parser.py # StaticAnalysisParser (facade)
└── tests/
    ├── conftest.py              # Test fixtures
    ├── test_config.py           # Configuration tests
    ├── analysis/                # Analyzer tests
    ├── parser/                  # Parser tests
    └── resources/               # Sample output files (.gesda, .wtg, .reach)
```

### Core Components

#### StaticAnalyzer (`analysis/static/static_analysis.py`)

Main orchestrator for static analysis execution:

```python
from rv_static_analysis import StaticAnalyzer, RVStaticAnalysisConfig
from rv_android_core.domain.app import App

config = RVStaticAnalysisConfig(rvsec_root="/path/to/rvsec")
app = App("/path/to/app.apk")
analyzer = StaticAnalyzer(app=app, config=config, output_dir="/output")

result = analyzer.analyze()
if result.success:
    static_data = analyzer.get_static_data()  # Returns StaticAnalysisData
```

**Analysis Pipeline Order**:
1. GESDA - Application structure extraction (required by REACH)
2. GATOR - Window Transition Graph generation (independent)
3. REACH - Reachability analysis (depends on GESDA output)

#### RVStaticAnalysisConfig (`config.py`)

Configuration management with priority-based path resolution:

```python
from rv_static_analysis.config import RVStaticAnalysisConfig

# Priority order for path resolution:
# 1. Explicit parameters (highest)
# 2. rvsec_root parameter with standard paths
# 3. RVSEC_HOME environment variable
# 4. Current working directory parent (fallback)

config = RVStaticAnalysisConfig(
    rvsec_root="/path/to/rvsec",
    lib_dir="/custom/lib",        # Optional: override lib directory
    output_dir="/output",
    validate_on_init=True         # Validate tool availability
)

# Get tool commands
cmd = config.get_tool_command('gesda', apk_path, output_file)
```

#### Parser Infrastructure

**BaseStaticAnalysisParser** - Abstract base class:
- Provides consistent interface for all parsers
- Standard logging and error handling
- Package validation helper

**Specialized Parsers**:

| Parser | Input Format | Output | Purpose |
|--------|-------------|--------|---------|
| GatorParser | JSON (.wtg) | WindowTransitionGraph | UI navigation graph |
| GesdaParser | JSON (.gesda) | Windows, Widgets | GUI element extraction |
| ReachParser | CSV (.reach) | Classes, Methods | Method reachability |

**StaticAnalysisParser** - Facade that coordinates all parsers:

```python
from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser

parser = StaticAnalysisParser()
static_data = parser.parse(reach_file, gator_file, gesda_file, package_name)
# Returns StaticAnalysisData(classes, windows, wtg)
```

## Static Analysis Tools

### GATOR (GUI Analysis TOol foR Android)

**Purpose**: Builds Window Transition Graph (WTG) representing app navigation structure

**Output Format**: JSON file with windows and transitions
```json
{
  "windows": [{"id": 1, "name": "com.example.MainActivity"}],
  "transitions": [{"sourceId": 1, "targetId": 2, "events": [...]}]
}
```

**Parsed Data**:
- Window definitions with IDs
- Widget event handlers (click, long_click, scroll, etc.)
- Navigation transitions between windows

### GESDA (GUI Element Static Detection for Android)

**Purpose**: Extracts comprehensive application structure and GUI elements

**Output Format**: JSON file with windows and widgets
```json
{
  "windows": [{
    "name": "com.example.MainActivity",
    "type": "ACTIVITY",
    "isMain": true,
    "widgets": [...]
  }]
}
```

**Parsed Data**:
- Application components (Activities, Services)
- Widget properties (id, type, text, hint, inputType)
- Event listeners (OnClickListener, OnScrollListener, etc.)
- Layout file associations

### REACH (Reachability Analysis)

**Purpose**: Determines reachability of monitored operations from entry points

**Output Format**: CSV file with method reachability
```csv
class,isActivity,isMainActivity,method,params,reachable,reachesMop,directlyReachesMop,signature
com.example.MainActivity,true,true,onCreate,[Bundle],true,true,false,<sig>
```

**Parsed Data**:
- Class information (activity status, main activity flag)
- Method details (name, parameters, signature)
- Reachability flags (reachable, reaches_mop, directly_reaches_mop)

## Development Commands

### Installation

```bash
cd modules/rv-static-analysis
poetry install
```

### Running Tests

```bash
# All tests
poetry run pytest

# With coverage
poetry run pytest --cov=rv_static_analysis

# Specific test categories
poetry run pytest tests/parser/     # Parser tests
poetry run pytest tests/analysis/   # Analyzer tests
poetry run pytest tests/test_config.py  # Configuration tests
```

### CLI Usage

```bash
# Analyze single APK
rv-static-analysis analyze --apk /path/to/app.apk --output /output

# Batch analyze multiple APKs
rv-static-analysis batch --apks-dir /path/to/apks --output /output

# Dry run (validate configuration only)
rv-static-analysis analyze --apk app.apk --output /tmp --dry-run

# With custom tool paths
rv-static-analysis analyze --apk app.apk --gesda-jar /custom/gesda.jar --output /output

# Verbose output with summary
rv-static-analysis analyze --apk app.apk --output /output --verbose --summary
```

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `RVSEC_HOME` | RVSEC installation root | `/home/user/rvsec` |
| `ANDROID_HOME` | Android SDK path | `/opt/android-sdk` |
| `RV_RT_JAR` | Java runtime JAR | `/usr/lib/jvm/java-8/jre/lib/rt.jar` |

### Standard Directory Layout

The configuration expects this RVSEC directory structure:
```
$RVSEC_HOME/
├── rv-android/
│   └── lib/
│       ├── gesda/rvsec-gesda.jar
│       ├── gator/
│       │   ├── gator (Python script)
│       │   └── rvsec-gator-client.jar
│       └── reach/rvsec-reach.jar
└── rvsec/rvsec-mop/src/main/resources/jca/  # MOP specifications
```

### Validation

Configuration validation checks:
1. Required paths (lib_dir, output_dir)
2. Tool availability (JAR files, GATOR Python script)
3. Android SDK (platforms directory, android.jar)
4. Java runtime (rt.jar)
5. MOP specifications directory

Disable validation for dry-run mode:
```python
config = RVStaticAnalysisConfig(validate_on_init=False)
```

## Integration Points

### With rv-android-core

- Uses `App` domain model for APK representation
- Uses `ErrorHandler` decorators for error management
- Uses `LoggingManager` for structured logging
- Uses domain models: `Classes`, `Windows`, `WindowTransitionGraph`, `StaticAnalysisData`

### With rv-experiment

```python
from rv_experiment.config import ExperimentConfig

config = ExperimentConfig(
    name="experiment",
    run_static_analysis=True
)
# Static analysis automatically configured and executed in pre-processing phase
```

### With rv-agent

Static analysis data provides:
- Window Transition Graph for navigation guidance
- Method reachability for MOP prioritization
- Widget information for UI interaction

## Output Files

Analysis generates three output files per APK:
```
output_dir/
├── app_name.gesda   # GESDA application structure (JSON)
├── app_name.wtg     # GATOR window transition graph (JSON)
└── app_name.reach   # REACH reachability analysis (CSV)
```

## Error Handling

- `StaticAnalysisException`: Raised for analysis execution failures
- `ConfigurationError`: Raised for invalid configuration
- All parsers gracefully handle missing files (return empty objects)
- Tool execution failures logged with detailed context

## Important Notes

### Caching Behavior

StaticAnalyzer implements intelligent caching:
- If output file exists, tool execution is skipped
- Use `--force` CLI flag to override caching

### Tool Dependencies

- GESDA output is required for REACH analysis
- GATOR is independent and can run in parallel with GESDA
- All tools require Java runtime

### MOP Specifications

- Default MOP directory points to JCA (Java Cryptography Architecture) specifications
- Can be overridden for generic specifications or custom monitors
- REACH tool uses these specifications for reachability analysis

### Performance Considerations

- Static analysis can be slow for large APKs
- Execution times tracked per tool in `StaticAnalysisResult.execution_times`
- Use `get_metrics()` for detailed performance information
