# RV-Static-Analysis Module

Unified GATOR-based static analysis for Android applications, producing a single JSON output with reachability, windows, and transitions data.

## Overview

The RV-Static-Analysis module runs a unified GATOR analysis client on Android APKs and parses the results into `StaticAnalysisData` domain objects. A single GATOR invocation produces all analysis data (reachability, windows, transitions) in one JSON file with priority-ordered output.

### Key Features

- **Single-Client Architecture**: One GATOR invocation produces all data in a single JSON file
- **Priority-Ordered Output**: Reachability first, then windows, then transitions — timeout preserves the most critical data
- **Graceful Degradation**: Parser recovers partial data when sections are missing
- **File-Level Caching**: If output JSON already exists, analysis is skipped

## Architecture

### Analysis Pipeline

1. **GATOR Analysis**: Runs unified `RvsecAnalysisClient` on APK
2. **JSON Output**: Produces `{app_name}.json` with reachability, windows, transitions
3. **Result Parsing**: `parse_file()` converts JSON into `StaticAnalysisData` objects

### Core Components

- **StaticAnalyzer**: Analysis orchestrator — runs GATOR, manages output files
- **RVStaticAnalysisConfig**: Configuration with priority-based path resolution
- **StaticAnalysisParser**: Parses unified JSON into domain objects
- **parse_file()**: Convenience function for one-call parsing

### Integration Points

- **rv-android-core**: `App` domain model, `StaticAnalysisData`, `SignatureNormalizer`
- **rv-platform**: `StaticAnalysisComponent` calls `StaticAnalyzer.analyze()`
- **rv-agent**: WTG for navigation guidance, MOP flags for action prioritization
- **rv-coverage**: Method universe (denominator for coverage %)

## Usage

### Programmatic Interface

```python
from rv_static_analysis import StaticAnalyzer, RVStaticAnalysisConfig
from rv_android_core.domain.app import App

config = RVStaticAnalysisConfig(rvsec_root="/path/to/rvsec")
app = App("/path/to/app.apk")
analyzer = StaticAnalyzer(app=app, config=config, output_dir="/output")

result = analyzer.analyze()
if result.success:
    static_data = analyzer.get_static_data()
```

### Parsing Results

```python
from rv_static_analysis.parser.static.static_analysis_parser import parse_file

static_data = parse_file("/path/to/app.apk.json", "com.example.app")

if static_data.classes:
    print(f"Classes: {len(static_data.classes.classes)}")
if static_data.windows:
    print(f"Windows: {len(static_data.windows.windows)}")
```

### CLI

```bash
# Analyze single APK
rv-static-analysis analyze --apk /path/to/app.apk --output /output

# Batch analyze
rv-static-analysis batch --apks-dir /path/to/apks --output /output
```

## Output Format

Analysis produces one JSON file per APK: `{app_name}.json`

```
output/
└── app_name.json    # Unified analysis (reachability, windows, transitions)
```

## Configuration

Priority-based resolution:
1. Explicit parameters (highest priority)
2. `rvsec_root` with standard layout
3. `RVSEC_HOME` environment variable

### Environment Variables

- `RVSEC_HOME`: RVSEC installation root directory
- `ANDROID_HOME`: Android SDK path

### Required Dependencies

- GATOR analysis client JAR
- Android SDK (ANDROID_HOME)
- Java runtime

## Testing

```bash
cd modules/rv-static-analysis

uv run pytest tests/ -v              # All tests (76)
uv run pytest tests/parser/ -v       # Parser tests (55)
uv run pytest tests/analysis/ -v     # Analyzer tests (13)
uv run pytest tests/test_config.py -v # Config tests (8)
```

## Dependencies

- `rv-android-core`: Domain models, error handling, logging
- Android SDK with platform tools
- Java 8+ for GATOR execution

## License

This module is part of the RV-Android project and follows the same licensing terms.
