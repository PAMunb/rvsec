# CLAUDE.md - rv-coverage

This file provides guidance to Claude Code when working with the rv-coverage module.

## Module Overview

The rv-coverage module provides coverage analysis and tracking capabilities for Android runtime verification. It monitors logcat output in real-time, extracts coverage information and formal property violations, and calculates comprehensive coverage metrics.

### Primary Responsibilities

- Parse Android logcat output for runtime verification events
- Track method execution coverage in real-time during test execution
- Detect and report formal property violations (MOP errors)
- Calculate multi-dimensional coverage metrics (method, activity, MOP-specific)
- Publish events for system-wide coordination through EventBus

## Architecture

### Module Structure

```
src/rv_coverage/
    __init__.py                    # Public API exports
    parser/
        __init__.py
        log/
            __init__.py
            logcat_parser.py       # Logcat line and file parsing
    analysis/
        __init__.py
        coverage/
            __init__.py
            analyzer.py            # Batch coverage analysis with fallback
            tracker.py             # Real-time coverage tracking
```

### Core Components

#### LogcatParser (`parser/log/logcat_parser.py`)

Parses Android logcat output for runtime verification data:
- **parse_logcat_line()**: Parse single logcat line for RVSEC/RVSEC-COV tags
- **parse_logcat_file()**: Process complete logcat file into LogcatRepository
- **stream_logcat_entries()**: Generator for real-time log streaming

Supported log formats:
- RVSEC tag: Runtime verification errors (property violations)
- RVSEC-COV tag: Method coverage entries

Error message formats:
- Standard format: `spec,class,init,method,source,error_type,message`
- FSM format: `class.method():::Spec went into an error state.`
- Generic format: `class.method(file:line) ::: Spec went into an error state.`

Coverage message formats:
- Modern: `<class: returnType method(params)>`
- Legacy: `class:::method:::params`

#### CoverageTracker (`analysis/coverage/tracker.py`)

Real-time coverage monitoring during test execution:
- Monitors logcat files for new entries in a background thread
- Publishes coverage events and MOP error events through EventBus
- Calculates metrics incrementally with change detection optimization
- Supports context manager usage for lifecycle management

Key features:
- Thread-safe operation with proper locking
- Change detection to avoid redundant metric calculations
- Direct LogcatRepository integration for performance
- Task correlation through task_id parameter

#### CoverageAnalyzer (`analysis/coverage/analyzer.py`)

Batch analysis with fallback capabilities:
- Processes logcat files offline
- Supports graceful degradation when static analysis data is unavailable
- Multiple calculation modes: FULL_STATIC_ANALYSIS, PARTIAL_STATIC_ANALYSIS, RUNTIME_ONLY, FALLBACK_MODE

Extends BaseAnalyzer from rv-android-core with coverage-specific implementation.

### Domain Models (from rv-android-core)

- **RvErrorLog**: Formal property violation with spec, class, method, source, message
- **RvCoverageLog**: Method call record with class, method, params, signature
- **LogcatRepository**: Repository for storing and querying coverage data

### Event Types

Published through EventBus:
- **COVERAGE_UPDATED**: Coverage metrics changed
- **MOP_ERROR_DETECTED**: Formal property violation detected

## Dependencies

```toml
[tool.poetry.dependencies]
python = ">=3.12,<4.0"
rv-android-core = {path = "../rv-android-core", develop = true}
pydantic = "^2.9.0"
regex = "^2024.9.11"
python-dateutil = "^2.9.0"
```

## Usage Examples

### Real-time Coverage Tracking

```python
from rv_coverage import CoverageTracker
from rv_android_core.domain.static import StaticAnalysisData

# Context manager usage (recommended)
with CoverageTracker(logcat_file, static_data, task_id="task_123") as tracker:
    # Run tests - tracker monitors automatically
    pass

# Manual lifecycle management
tracker = CoverageTracker(logcat_file, static_data)
tracker.start()
try:
    # Run tests
    metrics = tracker.get_coverage_metrics()
finally:
    tracker.stop()
```

### Batch Analysis

```python
from rv_coverage import CoverageAnalyzer

# With static analysis data
analyzer = CoverageAnalyzer(static_data=static_analysis_result)
metrics = analyzer.analyze("/path/to/logcat.txt")

# Fallback mode (no static data)
analyzer = CoverageAnalyzer()
analyzer.initialize_fallback_mode()
metrics = analyzer.get_coverage_metrics_with_fallback()
```

### Parsing Individual Lines

```python
from rv_coverage import parse_logcat_line

error_log, coverage_log = parse_logcat_line(logcat_line)
if error_log:
    print(f"Property violation: {error_log.spec} in {error_log.class_full_name}")
if coverage_log:
    print(f"Method called: {coverage_log.clazz}.{coverage_log.method}")
```

## Development Commands

```bash
# Navigate to module
cd modules/rv-coverage

# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=rv_coverage

# Run specific test category
poetry run pytest tests/parser/        # Logcat parser tests
poetry run pytest tests/analysis/      # Coverage analysis tests
```

## Test Structure

```
tests/
    parser/
        log/
            test_logcat_parser.py      # Comprehensive parser tests
    analysis/
        coverage/
            test_tracker.py            # CoverageTracker tests
```

Test categories:
- Logcat line parsing (various formats)
- Error message parsing (standard, FSM, generic)
- Coverage message parsing (modern, legacy)
- File processing and streaming
- Real-time tracking with mock data
- Edge cases and error handling

## Coverage Metrics

The module calculates the following metrics:

| Metric | Description |
|--------|-------------|
| method_coverage | Percentage of reachable methods executed |
| activity_coverage | Percentage of activities accessed |
| mop_method_coverage | Coverage of monitored operations methods |
| called_methods | Total unique methods called |
| total_errors | Number of formal property violations |

## Integration Points

### With rv-platform

CoverageTracker is used as a component during task execution:
```python
tracker = CoverageTracker(
    logcat_file=task.logcat_path,
    static_data=task.static_analysis,
    task_start_time=tool_execution_start,
    task_id=task.id
)
```

### With rv-experiment

CoverageAnalyzer processes results post-experiment:
```python
analyzer = CoverageAnalyzer(static_data=experiment.static_data)
for logcat_file in experiment.logcat_files:
    metrics = analyzer.analyze(logcat_file)
```

### With EventBus

Subscribe to coverage events:
```python
from rv_android_core.event.bus import EventBus, EventType

event_bus = EventBus.get_instance()
event_bus.subscribe(EventType.COVERAGE_UPDATED, on_coverage_update)
event_bus.subscribe(EventType.MOP_ERROR_DETECTED, on_error_detected)
```

## Performance Characteristics

- Real-time processing latency: < 1ms per logcat entry
- Memory efficient: Incremental processing without data accumulation
- CPU optimized: Change detection avoids redundant calculations
- Thread efficient: Adaptive sleep patterns based on data availability

## Important Notes

### Logcat Format

The parser expects standard Android logcat format:
```
MM-DD HH:MM:SS.mmm  PID  TID LEVEL TAG: message
```

### Year Handling

Logcat timestamps lack year information. The parser handles year transitions:
- December logs in January are attributed to the previous year
- Other months use the current year

### Error vs Coverage Disambiguation

- RVSEC tag: Always indicates a formal property violation (error)
- RVSEC-COV tag: Always indicates a method call (coverage)

### Thread Safety

CoverageTracker operations are thread-safe:
- Background thread for logcat monitoring
- RLock protection for shared state
- Event publishing is non-blocking


## Development Notes

This module is part of the RV-Android Poetry workspace. All modules are installed in **editable mode** via the root `pyproject.toml`.

**Key points:**
- Run `poetry install` from the project root to install all modules
- Source code changes are reflected immediately (no reinstall needed)
- Only reinstall if `pyproject.toml` dependencies change

```bash
# From project root
poetry install          # Install/update all modules
poetry install --sync   # Also remove unused packages
```

