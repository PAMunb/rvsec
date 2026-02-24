# CLAUDE.md - rv-static-analysis Module

This file provides guidance to Claude Code when working with the rv-static-analysis module.

## Module Overview

The rv-static-analysis module runs unified GATOR-based static analysis on Android applications, producing a single JSON output with reachability, windows, and transitions data. It provides both analysis orchestration (running GATOR) and parsing (loading JSON into domain objects).

### Purpose

- Run unified GATOR analysis client on Android APKs
- Parse analysis JSON into `StaticAnalysisData` domain objects
- Provide configuration management for the analysis pipeline
- Enable navigation guidance and MOP prioritization in rv-agent

### Key Features

- **Single-Client Architecture**: One GATOR invocation produces all analysis data (reachability, windows, transitions) in a single JSON file
- **Priority-Ordered Output**: Reachability written first, then windows, then transitions — timeout preserves the most critical data
- **Graceful Degradation**: Parser recovers partial data when sections are missing (e.g., timeout killed analysis before transitions were written)
- **File-Level Caching**: If output JSON already exists, analysis is skipped

## Architecture

### Directory Structure

```
rv-static-analysis/
├── src/rv_static_analysis/
│   ├── __init__.py              # Public API: StaticAnalyzer, RVStaticAnalysisConfig
│   ├── __main__.py              # CLI entry point
│   ├── config.py                # RVStaticAnalysisConfig (Pydantic model)
│   ├── analysis/
│   │   └── static/
│   │       └── static_analysis.py  # StaticAnalyzer, StaticAnalysisResult
│   └── parser/
│       └── static/
│           └── static_analysis_parser.py  # parse_file(), StaticAnalysisParser
└── tests/
    ├── conftest.py              # Test fixtures (parser, tmp_path helpers)
    ├── test_config.py           # Configuration tests
    ├── analysis/
    │   └── static/
    │       └── test_static_analysis.py  # Analyzer tests
    ├── parser/
    │   └── static/
    │       └── test_static_analysis_parser.py  # Parser tests (55 tests)
    └── resources/
        └── cryptoapp.apk.json   # Reference analysis output for testing
```

### Core Components

#### StaticAnalyzer (`analysis/static/static_analysis.py`)

Orchestrates GATOR execution and produces `StaticAnalysisData`:

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

#### RVStaticAnalysisConfig (`config.py`)

Pydantic configuration model with priority-based path resolution:

```python
from rv_static_analysis.config import RVStaticAnalysisConfig

# Priority order:
# 1. Explicit parameters (highest)
# 2. rvsec_root with standard layout
# 3. RVSEC_HOME environment variable
# 4. Current working directory parent

config = RVStaticAnalysisConfig(
    rvsec_root="/path/to/rvsec",
    output_dir="/output",
    jvm_memory="8g",         # JVM heap for GATOR (default: 8g)
    validate_on_init=True    # Validate GATOR availability
)

# Build GATOR command
cmd = config.build_analysis_command(apk_path, output_file, mop_dir)
```

Key config fields: `rvsec_root`, `lib_dir`, `gator_dir`, `analysis_client_jar`, `android_jar`, `mop_dir`, `output_dir`, `jvm_memory`.

#### Parser (`parser/static/static_analysis_parser.py`)

Parses unified JSON into `StaticAnalysisData`:

```python
from rv_static_analysis.parser.static.static_analysis_parser import parse_file

# Convenience function (recommended)
static_data = parse_file("/path/to/app.apk.json", "com.example.app")

# Class-based API
from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser
parser = StaticAnalysisParser()
static_data = parser.parse_file("/path/to/app.apk.json", "com.example.app")
```

The parser processes three JSON sections:
1. **reachability**: Classes, methods, activity flags, MOP reachability flags
2. **windows**: Window definitions with widgets, event listeners, inputType, hint, entries
3. **transitions**: WTG edges between windows with triggering events

**Important**: The `code_package` parameter filters classes by prefix — only classes starting with `code_package` are included. This handles APKs where the manifest package differs from the implementation package (e.g., Godot games: manifest=`ir.hsn6.trans`, code=`org.godotengine.godot`).

**SignatureNormalizer** normalizes inner class notation (`.` → `$`) for consistent matching. The GATOR client writes `$` notation via `SootClass.getName()`, so the normalizer is a safety net — it should be a no-op on well-formed output.

## JSON Output Format

Analysis produces one JSON file per APK: `{app_name}.json`

```json
{
  "reachability": [
    {
      "className": "com.example.MainActivity",
      "isActivity": true,
      "isMainActivity": true,
      "methods": [
        {
          "name": "onCreate",
          "signature": "<com.example.MainActivity: void onCreate(android.os.Bundle)>",
          "reachable": true,
          "reachesMop": true,
          "directlyReachesMop": false
        }
      ]
    }
  ],
  "windows": [
    {
      "id": 1234,
      "name": "com.example.MainActivity",
      "type": "ACTIVITY",
      "isMain": true,
      "widgets": [
        {
          "id": 5678,
          "name": "buttonSubmit",
          "type": "Button",
          "text": "Submit",
          "hint": "Click to submit",
          "inputType": "none",
          "entries": [],
          "listeners": [
            {
              "eventType": "click",
              "handlerMethod": "<com.example.MainActivity$1: void onClick(android.view.View)>"
            }
          ]
        }
      ]
    }
  ],
  "transitions": [
    {
      "sourceId": 1234,
      "targetId": 5679,
      "events": [
        {
          "widgetId": 5678,
          "type": "click",
          "handlerMethod": "<com.example.MainActivity: void showSettings(android.view.View)>"
        }
      ]
    }
  ]
}
```

## Development Commands

### Running Tests

```bash
cd modules/rv-static-analysis

# All tests
uv run pytest tests/ -v

# Parser tests (55 tests — includes baseline equivalence, normalizer safety net)
uv run pytest tests/parser/ -v

# Analyzer tests (13 tests)
uv run pytest tests/analysis/ -v

# Configuration tests (8 tests)
uv run pytest tests/test_config.py -v
```

### CLI Usage

```bash
# Analyze single APK
rv-static-analysis analyze --apk /path/to/app.apk --output /output

# Batch analyze
rv-static-analysis batch --apks-dir /path/to/apks --output /output

# Verbose with summary
rv-static-analysis analyze --apk app.apk --output /output --verbose --summary
```

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `RVSEC_HOME` | RVSEC installation root | `/home/user/rvsec` |
| `ANDROID_HOME` | Android SDK path | `/opt/android-sdk` |

### Standard Directory Layout

```
$RVSEC_HOME/
├── rv-android/
│   └── lib/
│       └── gator/
│           ├── gator                         # Python launcher script
│           └── rvsec-analysis-client.jar     # Unified analysis client JAR
└── rvsec/rvsec-mop/src/main/resources/jca/   # MOP specifications
```

### Validation

Configuration validation checks:
1. GATOR directory exists with Python launcher
2. Analysis client JAR available
3. Android SDK platforms directory with android.jar
4. MOP specifications directory (for reachability analysis)

## Integration Points

### With rv-android-core

- `App` domain model for APK metadata (package_name, code_package)
- `StaticAnalysisData`, `Classes`, `Windows`, `WindowTransitionGraph` domain models
- `EXTENSION_STATIC_ANALYSIS = ".json"` constant
- `SignatureNormalizer` for inner class notation
- `ErrorHandler`, `LoggingManager`, `BaseAnalyzer`

### With rv-platform

- `StaticAnalysisComponent` calls `StaticAnalyzer.analyze()` in pre-processing
- Passes `app.code_package` (not `package_name`) to parser for correct class filtering

### With rv-agent

- `TransitionManager` uses WTG for navigation guidance
- `RVAgentVisitor` uses MOP flags for action prioritization
- `NavigationGuidance` provides unvisited-screen hints from WTG

### With rv-coverage

- `Classes.methods` defines the method universe (denominator for coverage %)
- `reachable` flag distinguishes reachable vs unreachable methods

## Error Handling

- `StaticAnalysisException`: Analysis execution failures
- `ConfigurationError`: Invalid configuration
- Parser returns empty sections for missing/malformed JSON data (graceful degradation)
- Timeout produces partial JSON — parser recovers whatever sections were written

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
