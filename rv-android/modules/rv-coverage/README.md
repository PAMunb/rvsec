# RV-Coverage Module

Real-time coverage tracking and analysis for Android runtime verification testing.

## Overview

The RV-Coverage module provides comprehensive coverage tracking capabilities for Android applications during runtime verification testing. It monitors method execution, tracks formal property violations, and calculates detailed coverage metrics in real-time.

### Key Features

- **Real-time Coverage Tracking**: Monitors logcat output during test execution
- **Formal Property Violation Detection**: Identifies and reports MOP (Monitoring-Oriented Programming) errors
- **Comprehensive Metrics**: Calculates method, activity, and JCA-reachable coverage
- **Event-driven Architecture**: Publishes coverage and error events for system integration
- **High Performance**: Direct repository integration with optimized processing
- **Thread-safe Operation**: Concurrent processing without blocking test execution

## Architecture

### Core Components

#### CoverageAnalyzer
Centralized analyzer for batch processing of coverage data from various sources.

**Key Capabilities:**
- Batch analysis of logcat files
- Integration with static analysis data
- Unified metrics calculation
- Multi-source data processing

#### CoverageTracker
Real-time coverage monitoring system for live test execution.

**Key Capabilities:**
- Continuous logcat monitoring
- Real-time event publishing
- Thread-safe concurrent operation
- Performance-optimized processing

### Integration Points

- **EventBus**: Real-time event publishing for coverage updates and error detection
- **LogcatRepository**: Direct repository access for optimal performance
- **StaticAnalysisData**: Integration with static analysis results
- **LoggingManager**: Standardized logging infrastructure
- **ErrorHandler**: Centralized error handling patterns

## Installation

### Prerequisites

- Python 3.12+
- Poetry for dependency management
- rv-android-core module

### Setup

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Install in development mode
poetry install --extras dev
```

## Usage

### Basic Coverage Analysis

```python
from rv_coverage import CoverageAnalyzer, CoverageTracker

# Batch analysis of logcat file
analyzer = CoverageAnalyzer(static_data=static_analysis_result)
metrics = analyzer.analyze("/path/to/logcat.txt")

print(f"Method Coverage: {metrics['method_coverage']}%")
print(f"Activity Coverage: {metrics['activities_coverage']}%")
print(f"Total Errors: {metrics['total_errors']}")
```

### Real-time Coverage Tracking

```python
# Using context manager (recommended)
with CoverageTracker(logcat_file, static_data) as tracker:
    # Run your tests here
    # Tracker automatically monitors coverage
    pass

# Manual lifecycle management
tracker = CoverageTracker(logcat_file, static_data)
tracker.start()
try:
    # Run tests
    current_metrics = tracker.get_coverage_metrics()
finally:
    tracker.stop()
```

### Processing Individual Log Entries

```python
from rv_coverage.parser.log.logcat_parser import parse_logcat_line

# Parse individual logcat line
error_log, coverage_log = parse_logcat_line(logcat_line)

if coverage_log:
    analyzer.add_method_call(coverage_log)
    
if error_log:
    analyzer.add_error(error_log)
```

## Event System Integration

The module publishes events through the EventBus system:

### Coverage Update Events

```python
# Subscribe to coverage updates
def on_coverage_update(event):
    data = event.data
    print(f"Coverage: {data['method_coverage']}%")

event_bus.subscribe(EventType.COVERAGE_UPDATED, on_coverage_update)
```

### Error Detection Events

```python
# Subscribe to MOP error detection
def on_error_detected(event):
    error_data = event.data
    print(f"Property violation in {error_data['class_name']}.{error_data['method']}")

event_bus.subscribe(EventType.COVERAGE_ERROR_DETECTED, on_error_detected)
```

## Configuration

### Performance Tuning

The module includes several performance optimizations:

- **Change Detection**: Metrics calculated only when data changes
- **Efficient Threading**: Adaptive sleep patterns based on data availability  
- **Memory Management**: Incremental processing without data accumulation
- **Direct Repository Access**: Eliminates unnecessary abstraction layers

### Logging Configuration

```python
from rv_android_core.util.logging.manager import LoggingManager

# Configure logging level for coverage components
logging_manager = LoggingManager.get_instance()
logger = logging_manager.get_logger('analysis.coverage')
logger.setLevel('DEBUG')
```

## Metrics

### Coverage Metrics

- **Method Coverage**: Percentage of reachable methods executed
- **Activity Coverage**: Percentage of activities accessed
- **MOP Method Coverage**: Coverage of security-relevant methods
- **Called Methods**: Total number of unique methods called
- **Total Errors**: Number of formal property violations detected

### Example Metrics Output

```json
{
  "method_coverage": 75.5,
  "activities_coverage": 90.0,
  "methods_jca_reachable_coverage": 60.2,
  "total_method_calls": 1247,
  "total_errors": 3
}
```

## Error Handling

The module implements comprehensive error handling:

- **Parsing Errors**: Graceful handling of malformed logcat entries
- **I/O Errors**: Robust file access error management
- **Threading Errors**: Safe thread termination and cleanup
- **Integration Errors**: Proper error propagation to calling components

## Testing

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=rv_coverage

# Run specific test categories
poetry run pytest tests/analysis/
poetry run pytest tests/parser/
```

### Test Structure

- `tests/analysis/coverage/`: Tests for analyzer and tracker components
- `tests/parser/log/`: Tests for logcat parsing functionality
- Integration tests with mock EventBus and repository components

## Performance Characteristics

### Benchmarks

- **Real-time Processing**: < 1ms latency for logcat entry processing
- **Memory Usage**: Constant memory footprint regardless of logcat size
- **CPU Efficiency**: < 5% CPU overhead during intensive testing
- **Threading Overhead**: Minimal impact on test execution performance

### Scalability

- Handles logcat files of any size through streaming processing
- Supports concurrent tracking across multiple test sessions
- Efficient memory usage for long-running test scenarios
- Optimized for high-frequency log generation applications

## Integration Examples

### With Testing Frameworks

```python
# DroidBot integration
def run_droidbot_with_coverage():
    logcat_file = "/tmp/droidbot.logcat"
    
    with CoverageTracker(logcat_file, static_data) as tracker:
        # Run DroidBot testing
        droidbot.run(app_path, output_dir, logcat_file=logcat_file)
        
        # Get final metrics
        final_metrics = tracker.get_coverage_metrics()
        return final_metrics
```

### With Analysis Pipeline

```python
# Integration with experiment framework
class CoverageExperimentComponent:
    def __init__(self):
        self.analyzer = CoverageAnalyzer()
        
    def process_experiment_results(self, experiment_data):
        for logcat_file in experiment_data.logcat_files:
            metrics = self.analyzer.analyze(logcat_file)
            experiment_data.add_metrics("coverage", metrics)
```

## Contributing

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all public interfaces
- Include comprehensive docstrings following Google style
- Maintain architectural comment patterns consistent with other modules

### Architecture Guidelines

- Extend BaseAnalyzer for new analyzer components
- Use EventBus for decoupled component communication
- Implement proper error handling with ErrorHandler integration
- Follow direct repository access patterns for performance
- Maintain thread safety for concurrent operations

## License

This module is part of the RV-Android project and follows the same licensing terms.