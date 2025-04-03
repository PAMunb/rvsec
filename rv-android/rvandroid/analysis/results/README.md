# Advanced Results Analysis System

This directory contains the implementation of an advanced results analysis system for RV-Android, designed to provide comprehensive analysis of experiment results and rich reporting capabilities.

## Key Features

- Comprehensive analysis of experiment results
- Advanced metrics collection and calculation
- Rich visualization capabilities
- Multiple report formats (HTML, JSON)
- Integration with existing result processing

## Architecture

The results analysis system is designed with a modular, component-based architecture:

- `analysis.py`: Core analysis functionality
- `processor.py`: Result processing with enhanced capabilities
- `report_generator.py`: Advanced report generation
- `integration.py`: Integration with existing result processing

## Report Generation

The system supports multiple report formats and visualization types:

- **HTML Reports**: Interactive reports with charts and tables
- **JSON Reports**: Machine-readable reports for further processing
- **Visualizations**: Coverage charts, error distributions, performance graphs

## Integration with Existing Workflow

The `integration.py` module provides adapters and integration points to connect the new analysis system with the existing result processing:

- `AnalysisAdapter`: Adapter for the new analysis system
- `EnhancedResultProcessor`: Enhanced version of the legacy result processor
- `LegacyResultAdapter`: Adapter for converting between legacy and new result formats

## Usage

### Command-Line Interface

Use the analysis system through the enhanced experiment controller:

```bash
python -m rvandroid.experiment.cli --enhanced
```

### Programmatic Usage

```python
from rvandroid.analysis.results.integration import AnalysisAdapter

# Create analysis adapter
adapter = AnalysisAdapter(results_dir='/path/to/results')

# Process results with advanced analysis
results = adapter.process_results()

# Access analysis results
print(f"Overall coverage: {results['coverage']['overall']}%")
print(f"Execution time: {results['metrics']['execution_time']} seconds")
print(f"Report path: {results['report_path']}")
```

### Using the Legacy Adapter

```python
from rvandroid.analysis.results.integration import LegacyResultAdapter

# Convert legacy results to new format
legacy_results = {...}  # Legacy result format
new_format = LegacyResultAdapter.convert_to_new_format(legacy_results)

# Convert new results to legacy format
new_results = {...}  # New result format
legacy_format = LegacyResultAdapter.convert_to_legacy_format(new_results)
```

### Using Enhanced Result Processor

```python
from rvandroid.analysis.results.integration import AnalysisAdapter
from rvandroid.analysis.results.analysis import ResultAnalyzer
from rvandroid.analysis.results.report_generator import ReportGenerator, ReportConfig

# Create components
analyzer = ResultAnalyzer(results_dir='/path/to/results')
report_config = ReportConfig(include_visualizations=True)
report_generator = ReportGenerator(report_config)

# Create analysis adapter
adapter = AnalysisAdapter(results_dir='/path/to/results')

# Get enhanced result processor
processor = adapter.get_legacy_processor()

# Process results with enhanced capabilities
enhanced_results = processor.process()
```

## Extending the System

The system is designed to be extensible. To add a new analysis metric:

1. Extend the `ResultAnalyzer` class in `analysis.py`
2. Add your metric calculation logic
3. Include the new metric in the analysis result

Example:

```python
class CustomAnalyzer(ResultAnalyzer):
    def analyze(self):
        # Get base analysis result
        result = super().analyze()
        
        # Add custom metric
        result.metrics['custom_metric'] = self._calculate_custom_metric()
        
        return result
    
    def _calculate_custom_metric(self):
        # Custom metric calculation logic
        return value
```

## Integration with Orchestration System

The analysis system integrates with the advanced orchestration system:

```python
from rvandroid.experiment.integration_factory import IntegrationFactory

# Create integration factory
factory = IntegrationFactory()

# Create result manager with new analysis system
result_manager = factory.create_result_manager_with_new_analysis(
    results_dir='/path/to/results'
)

# Generate reports with enhanced analysis
results = result_manager.generate_reports()
```