# RV-Coverage Module

Modern coverage tracking and analysis system for Android monitored operations testing with real-time monitoring, comprehensive metrics, and dependency injection architecture.

## Overview

The RV-Coverage module provides sophisticated coverage tracking capabilities for Android applications during monitored operations testing. It implements real-time method execution monitoring, formal property violation detection, and comprehensive coverage metrics calculation through a modern architecture with event-driven design and comprehensive error handling integration.

### Key Features

- **Real-time Coverage Tracking**: Sophisticated logcat monitoring with parallel processing and event publishing
- **Monitored Operations Detection**: Advanced identification and reporting of both JCA cryptography and generic programming pattern violations
- **Comprehensive Metrics System**: Multi-dimensional coverage calculation including method, activity, and specification-specific coverage
- **Modern Event Architecture**: EventBus integration with typed events for system-wide coordination
- **DI-Ready Infrastructure**: Full dependency injection support with lifecycle management and configuration
- **High-Performance Processing**: Optimized direct repository integration with concurrent, non-blocking operation
- **Error Handling Integration**: Comprehensive error handling with rv-android-core decorators and recovery strategies

## Architecture

### Core Components

#### Coverage Analysis Infrastructure
- **CoverageAnalyzer**: Modern centralized analyzer with comprehensive batch processing, multi-source data integration, and advanced metrics calculation
- **CoverageTracker**: High-performance real-time monitoring system with concurrent logcat processing and event-driven architecture
- **MetricsCalculator**: Sophisticated metrics engine with support for method, activity, and specification-specific coverage calculation

#### Monitoring Operations Support
- **MonitoredOperationsDetector**: Advanced detection system for both JCA cryptography and generic programming pattern violations
- **SpecificationAnalyzer**: Comprehensive analyzer for different specification types with validation and error reporting
- **ViolationProcessor**: Specialized processor for handling different types of monitored operations violations

#### Integration Infrastructure
- **LogcatParser**: Enhanced logcat parsing with real-time processing and structured data extraction
- **EventPublisher**: Modern event publishing system with typed events and comprehensive error handling
- **RepositoryIntegration**: Direct repository access with optimized performance and caching

### Integration Points

- **rv-android-core**: Uses ErrorHandler decorators, LoggingManager, EventBus, and domain models for comprehensive infrastructure
- **rv-experiment**: Provides coverage tracking components for experiment orchestration and real-time monitoring
- **rv-static-analysis**: Integrates static analysis data for enhanced coverage calculation and baseline establishment
- **rv-monitor-generator**: Coordinates with monitor specifications for comprehensive monitored operations detection

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

### Modern Coverage Analysis

```python
from rv_coverage.analysis.coverage import CoverageAnalyzer, CoverageTracker
from rv_coverage.analysis.coverage.tracker import MetricsCalculator
from rv_android_core.util.error.decorators import handle_errors
from rv_android_core.util.logging.manager import LoggingManager

# Create modern coverage analyzer with comprehensive configuration
analyzer = CoverageAnalyzer(
    static_data=static_analysis_result,
    specification_type="jca",  # "jca", "generic", or "custom"
    enable_real_time_events=True,
    validation_enabled=True
)

# Batch analysis with enhanced error handling
@handle_errors(component="CoverageAnalysis", operation="analyze")
def analyze_coverage():
    metrics = analyzer.analyze("/path/to/logcat.txt")
    return metrics

metrics = analyze_coverage()

if metrics:
    print(f"Coverage Analysis Results:")
    print(f"  Method Coverage: {metrics['method_coverage']:.2f}%")
    print(f"  Activity Coverage: {metrics['activities_coverage']:.2f}%")
    print(f"  JCA Operations Coverage: {metrics.get('jca_coverage', 0):.2f}%")
    print(f"  Generic Patterns Coverage: {metrics.get('generic_coverage', 0):.2f}%")
    print(f"  Total Violations: {metrics['total_errors']}")
    print(f"  Performance Metrics: {metrics.get('performance_stats', {})}")
```

### Real-time Coverage Tracking with Modern Architecture

```python
from rv_coverage.analysis.coverage.tracker import CoverageTracker
from rv_android_core.event.bus import EventBus, EventType

# Setup event handling for real-time updates
event_bus = EventBus.get_instance()

def on_coverage_update(event):
    print(f"Coverage update: {event.metrics}")

def on_violation_detected(event):
    print(f"Monitored operation violation: {event.violation_type} - {event.details}")

event_bus.subscribe(EventType.COVERAGE_UPDATED, on_coverage_update)
event_bus.subscribe(EventType.VIOLATION_DETECTED, on_violation_detected)

# Modern context manager usage with comprehensive configuration
tracker_config = {
    "specification_type": "jca",
    "real_time_events": True,
    "performance_monitoring": True,
    "violation_detection": True
}

with CoverageTracker(logcat_file, static_data, config=tracker_config) as tracker:
    # Tracker automatically monitors coverage with real-time events
    # Run your testing framework here
    
    # Get intermediate coverage metrics
    current_metrics = tracker.get_coverage_metrics()
    print(f"Current method coverage: {current_metrics.method_coverage:.2f}%")
    
    # Get real-time violation information
    violations = tracker.get_detected_violations()
    for violation in violations:
        print(f"Violation: {violation.type} at {violation.timestamp}")

# Advanced manual lifecycle management with error handling
@handle_errors(component="CoverageTracker", operation="lifecycle")
def run_advanced_tracking():
    tracker = CoverageTracker(
        logcat_file, 
        static_data,
        enable_parallel_processing=True,
        specification_aware=True
    )
    
    try:
        tracker.start()
        
        # Advanced metrics access
        real_time_metrics = tracker.get_real_time_metrics()
        specification_metrics = tracker.get_specification_metrics()
        performance_stats = tracker.get_performance_statistics()
        
        return {
            "real_time": real_time_metrics,
            "specifications": specification_metrics,
            "performance": performance_stats
        }
        
    finally:
        tracker.stop()

tracking_results = run_advanced_tracking()
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