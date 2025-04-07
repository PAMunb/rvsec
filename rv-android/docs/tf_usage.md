# RV-Android Test Framework - Usage Guide

This guide provides information on how to use the test framework to evaluate different configurations of RVAndroid and RVDroid tools.

## 1. Introduction

The test framework allows systematic evaluation of different configurations of RVAndroid and RVDroid tools, including variations of LLM models, prompt strategies, parsers, and visitors to identify optimal configurations for testing Android applications.

## 2. Installation

The test framework is part of the RV-Android system and does not require additional installation. Make sure all RV-Android dependencies are installed.

## 3. Basic Usage

### 3.1 Running Tests

To run a simple test suite:

```bash
python run_test_framework.py run --apps out --analyze
```

This command will:
1. Run tests on all APKs in the `out` directory
2. Use default test configurations
3. Analyze the results after completion

You can specify either a directory containing APK files or individual APK files:

```bash
# Specify a directory containing APKs and their static analysis files
python run_test_framework.py run --apps out --analyze

# Specify individual APK files
python run_test_framework.py run --apps apks_examples/*.apk --analyze
```

You can also use a configuration file that already contains app directory definitions:

```bash
python run_test_framework.py run --config my_config.json --analyze
```

When using a configuration file, the `--apps` parameter is optional. If provided, it will override the apps defined in the configuration file.

### 3.2 Creating a Custom Configuration

To create a custom configuration file:

```bash
python run_test_framework.py create-config --name "My Experiment" --output my_config.json
```

You can edit the `my_config.json` file to customize the test configurations as needed.

### 3.3 Running with Custom Configuration

To run tests with a custom configuration:

```bash
python run_test_framework.py run --config my_config.json --analyze
```

You can override the apps defined in the configuration file:

```bash
python run_test_framework.py run --apps apks_examples/*.apk --config my_config.json --analyze
```

### 3.4 Analyzing Previous Results

To analyze results from a previous test run:

```bash
python run_test_framework.py analyze --results-dir test_results --visualize --export-csv --export-xlsx --enhanced-export --detect-anomalies --analyze-correlations --dashboard --launch-dashboard
```

This command will:
1. Load test results from the specified directory
2. Generate visualizations if `--visualize` is specified
3. Export results to CSV if `--export-csv` is specified
4. Export results to Excel if `--export-xlsx` is specified
5. Use enhanced spreadsheet export if `--enhanced-export` is specified
6. Detect anomalies in results if `--detect-anomalies` is specified
7. Analyze correlations between app characteristics and configurations if `--analyze-correlations` is specified
8. Generate an interactive dashboard if `--dashboard` is specified
9. Launch the dashboard in a web browser if `--launch-dashboard` is specified

You can also adjust the anomaly detection threshold:

```bash
python run_test_framework.py analyze --results-dir test_results --detect-anomalies --anomaly-threshold 2.5
```

Higher threshold values (like 2.5 or 3.0) will detect only more extreme anomalies, while lower values (like 1.5) will be more sensitive but may include more false positives.

To focus on finding correlations:

```bash
python run_test_framework.py analyze --results-dir test_results --analyze-correlations
```

This will identify relationships between app characteristics (such as using encryption, complex UI, etc.) and configuration performance, providing recommendations for which configurations work best with specific types of apps.

## 4. Advanced Configuration

### 4.1 Configuration File Structure

The configuration file is a JSON document with the following structure:

```json
{
  "name": "Experiment Name",
  "description": "Experiment description",
  "tool_configurations": [
    {
      "tool_name": "rvandroid",
      "timeout": 300,
      "llm_type": "ollama",
      "llm_model": "llama3.2:3b",
      "temperature": 0.2,
      "max_tokens": 800,
      "strategy_type": "composable_single_action",
      "parser_type": "droidbot",
      "visitor_type": "enhanced",
      "use_static_analysis": true,
      "static_analysis_level": "detailed",
      "use_screenshot_analysis": false,
      "extra_params": {}
    },
    // More configurations...
  ],
  "apps": [],
  "output_dir": "test_results",
  "repetitions": 3
}
```

### 4.2 Configuration Parameters

#### Tool Configuration

| Parameter | Description | Possible Values |
|-----------|-------------|-----------------|
| `tool_name` | Tool name | `rvandroid`, `rvdroid` |
| `timeout` | Timeout in seconds | Integer |
| `llm_type` | LLM model type | `ollama`, `huggingface`, `dspy`, `langchain`, `frontier` |
| `llm_model` | Model name | Depends on `llm_type` |
| `temperature` | Generation temperature | Float between 0.0 and 1.0 |
| `max_tokens` | Maximum tokens in response | Integer |
| `strategy_type` | Prompt strategy | `basic`, `single_action`, `composable_single_action`, etc. |
| `parser_type` | Parser type | `droidbot`, `uiautomator` |
| `visitor_type` | Visitor type | `basic`, `enhanced`, `detailed` |
| `use_static_analysis` | Use static analysis | `true`, `false` |
| `static_analysis_level` | Static analysis level | `basic`, `standard`, `detailed` |
| `use_screenshot_analysis` | Use screenshot analysis | `true`, `false` |

## 5. Interpreting Results

### 5.1 Analysis Report

After running tests, if the `--analyze` option is specified, an HTML report will be generated in the output directory. This report includes:

- Overall score chart by configuration
- Coverage comparison between configurations
- MOP error metrics analysis
- Performance comparison between tools
- List of top configurations by category

### 5.2 Optimal Configurations

Optimal configurations are identified based on different criteria:

- **Overall**: Best overall score considering coverage, execution time, and success rate
- **Method Coverage**: Highest method coverage
- **Activity Coverage**: Highest activity coverage
- **MOP Coverage**: Highest coverage of methods with MOP specifications
- **MOP Error Detection**: Best at finding violations of monitored operations specifications
- **Execution Speed**: Lowest execution time

### 5.3 Result Analysis Features

The test framework provides several analysis features:

- **Visualization**: Generate charts and graphs for visual analysis
- **CSV Export**: Export results to CSV format for further analysis
- **Excel Export**: Export results to Excel format with multiple sheets
- **Enhanced Spreadsheet Export**: Export comprehensive data with detailed metrics and multiple sheets/files
- **Interactive Dashboard**: Web-based dashboard for exploring results with charts and filtering
- **Top Performers**: Identify the best configurations for each metric
- **Correlation Analysis**: Analyze relationships between different metrics
- **Anomaly Detection**: Identify configurations and apps with unusual behavior
- **App-Configuration Correlation**: Find relationships between app characteristics and optimal configurations

#### 5.3.1 Anomaly Detection

The anomaly detector identifies data points that significantly deviate from expected patterns:

- **Configuration Anomalies**: Detects configurations with unexpected performance metrics
- **Tool Anomalies**: Identifies tools that behave significantly differently than others
- **App Anomalies**: Detects apps that respond differently to certain configurations
- **Severity Levels**: Classifies anomalies as low, medium, or high based on deviation
- **Statistical Analysis**: Uses Z-scores to identify significant deviations
- **Contextual Grouping**: Groups configurations by tool, LLM type for proper comparison

#### 5.3.2 App-Configuration Correlation

The correlation analyzer identifies relationships between app characteristics and configuration performance:

- **App Characteristics**: Extracts app features like UI complexity, iterator operations, I/O operations, cryptographic API usage, etc.
- **Monitored Operations Characteristics**: Identifies patterns of monitored specifications relevant to the app
- **Performance Correlation**: Identifies which configurations work best for specific app types
- **Recommendations**: Provides configuration recommendations based on app characteristics
- **App-Specific Guidance**: Generates tailored recommendations for each analyzed app
- **Configuration Insights**: Explains why certain configurations may work better with specific app types
- **Statistical Analysis**: Uses correlation coefficients to identify significant relationships

#### 5.3.3 Enhanced Spreadsheet Export

The enhanced spreadsheet exporter provides comprehensive data exports:

- **Multiple Sheets/Files**: Organizes data into logical categories
- **Configuration Analysis**: Detailed metrics for each configuration
- **App-Specific Analysis**: Insights on how apps respond to different configurations
- **Tool Comparison**: Performance metrics grouped by tool
- **MOP Error Summary**: Detailed breakdown of monitored operations errors
- **Correlation Data**: Exported correlation findings
- **Anomaly Report**: Detailed information about detected anomalies
- **Excel Formatting**: Enhanced readability with formatting in Excel workbooks
- **CSV Collection**: Multiple CSV files for different analysis perspectives

#### 5.3.4 Interactive Dashboard

The interactive dashboard provides a web-based visualization environment for exploring test results:

- **Summary Overview**: High-level statistics and key metrics at a glance
- **Interactive Charts**: Dynamic visualizations of metrics and correlations
- **Configuration Comparison**: Compare different configurations side-by-side
- **Filtering System**: Filter configurations by tool, LLM type, or metric
- **Tool Analysis**: Detailed metrics and comparisons by tool
- **Anomaly Visualization**: Visual representation of detected anomalies by type and severity
- **Correlation Insights**: Interactive exploration of correlations between app characteristics and configurations
- **Recommendation Views**: Recommendations based on app characteristics
- **Responsive Design**: Works on desktop, tablet and mobile devices
- **Browser Integration**: Can be launched directly in your default web browser
- **Self-Contained**: Single HTML file with embedded JavaScript and CSS

## 6. Result Analysis Example

Using the standalone result analysis script:

```bash
python examples/analyze_results.py --results-dir test_results --visualize --export-csv --export-excel --enhanced-export --detect-anomalies --analyze-correlations
```

For a more focused analysis of MOP error metrics, you can use the custom analyzer that directly processes CSV files:

```bash
python custom_analyzer.py test_results/run_20250404_131009
```

This custom analyzer is specifically designed to highlight Monitored Operations (MOP) metrics, handling both cryptographic API specifications and general programming specifications.

You can also run anomaly detection with a custom threshold:

```bash
python examples/analyze_results.py --results-dir test_results --detect-anomalies --anomaly-threshold 1.5
```

For apps with specific characteristics, focus on correlation analysis:

```bash
python examples/analyze_results.py --results-dir test_results --analyze-correlations
```

For detailed spreadsheets with comprehensive metrics:

```bash
python examples/analyze_results.py --results-dir test_results --export-csv --export-excel --enhanced-export
```

To generate and view the interactive dashboard:

```bash
python examples/analyze_results.py --results-dir test_results --dashboard --launch-dashboard
```

For a complete analysis with all features:

```bash
python examples/analyze_results.py --results-dir test_results --visualize --export-xlsx --enhanced-export --detect-anomalies --analyze-correlations --dashboard --launch-dashboard
```

## 7. Examples

### Example 1: Basic Test

```bash
python run_test_framework.py run --apps apks_examples/cryptoapp.apk --analyze
```

### Example 2: Tool Comparison with Configuration File

```bash
python run_test_framework.py run --config test_suite_example.json --repetitions 3 --analyze --save-optimal
```

### Example 3: Plateau Analysis with Multiple Timeouts

For plateau analysis, use a configuration file with multiple timeouts and run:

```bash
python run_test_framework.py create-config --type plateau --timeouts 60,120,180,300,600 --tool rvandroid --output plateau_config.json
# Edit the plateau_config.json file to set the "apps" field to point to your app directory
python run_test_framework.py run --config plateau_config.json --analyze
```

Note: After generating the configuration file, you need to update the "apps" field to point to your directory containing the APK(s) and their static analysis files.

### Example 4: Custom Configuration Generator

To generate a custom configuration with specific LLM types and models:

```bash
python run_test_framework.py create-config --type custom --tools rvandroid,rvdroid --llm-types ollama,dspy --models "ollama:llama3.2:3b,gemma3:4b;dspy:meta-llama/Meta-Llama-3.1-8B-Instruct" --strategies composable_single_action --visitors enhanced --output custom_config.json
```

## 8. Recommended Configurations

Based on previous experiments, here are some recommended configurations to start with:

### RVAndroid
- LLM: `ollama` with `llama3.2:3b`
- Strategy: `composable_single_action`
- Parser: `droidbot`
- Visitor: `enhanced`
- Static Analysis: `detailed`

### RVDroid
- LLM: `ollama` with `llama3.2:3b`
- Strategy: `composable_single_action`
- Parser: `uiautomator` (only available)
- Visitor: `enhanced`
- Static Analysis: `standard`
- Screenshot Analysis: `true` with level `standard`

### Directory Structure
For proper operation, the directory structure should contain:
- APK file(s)
- Static analysis files with the same base name as the APK file:
  - `.gesda` file: Contains static analysis data for monitored methods
  - `.reach` file: Contains reachability information
  - `.wtg` file: Contains window transition graph

Example directory structure:
```
out/
  ├── cryptoapp.apk
  ├── cryptoapp.apk.gesda
  ├── cryptoapp.apk.reach
  └── cryptoapp.apk.wtg
```

## 9. Troubleshooting

### Common Issues

1. **Emulator error**: Make sure the emulator is working correctly before starting tests.
2. **LLM models not found**: Check if Ollama models are installed and available.
3. **Memory error**: Reduce the number of workers or use fewer configurations simultaneously.

### Logs

Detailed logs are saved in the output directory and can be used for diagnosing problems.

## 10. Advanced Analysis with Python API

You can also use the Python API for custom result analysis:

```python
from rvandroid.test_framework.results_loader import ResultsLoader
from rvandroid.test_framework.exporters import export_to_csv
from rvandroid.test_framework.spreadsheet_exporter import export_to_enhanced_excel
from rvandroid.test_framework.visualization import generate_visualizations
from rvandroid.test_framework.anomaly_detector import detect_anomalies
from rvandroid.test_framework.correlation_analyzer import analyze_correlations
from rvandroid.test_framework.dashboard import generate_dashboard, launch_dashboard

# Load and analyze results
loader = ResultsLoader("test_results")
results = loader.load_and_analyze()

# Generate visualizations
generate_visualizations(results, "visualizations")

# Basic export to CSV
export_to_csv(results, "results.csv")

# Enhanced export to Excel with multiple sheets
export_to_enhanced_excel(results, "detailed_results.xlsx")

# Detect anomalies
anomaly_report = detect_anomalies(results, z_threshold=2.0)
print(f"Detected {anomaly_report['total_anomalies']} anomalies")

# Analyze correlations
correlation_report = analyze_correlations(results)
print(f"Found {correlation_report['total_correlations']} correlations")

# Generate and launch interactive dashboard
dashboard_file = generate_dashboard(results, "dashboard_output")
if dashboard_file:
    launch_dashboard(dashboard_file)  # Opens dashboard in browser

# Advanced use with custom anomaly detector
from rvandroid.test_framework.anomaly_detector import AnomalyDetector

detector = AnomalyDetector(z_threshold=1.8, min_samples=5)
anomalies = detector.detect_anomalies(results)
for anomaly in anomalies:
    print(f"{anomaly.id}: {anomaly.severity} anomaly in {anomaly.metric}")

# Advanced use with custom correlation analyzer
from rvandroid.test_framework.correlation_analyzer import CorrelationAnalyzer

analyzer = CorrelationAnalyzer(min_samples=3)
app_characteristics = analyzer.extract_app_characteristics(results)
correlations = analyzer.analyze_correlations(results, app_characteristics)
for correlation in correlations:
    print(f"{correlation.app_characteristic} -> {correlation.config_id}: {correlation.correlation_value:.2f}")

# Generate recommendations for specific app characteristics
recommendations = analyzer.generate_recommendations(correlations, app_characteristics)
for char, recs in recommendations.items():
    print(f"For apps with {char}:")
    for rec in recs:
        print(f"  {rec['config_id']}: {rec['explanation']}")
        
# Advanced export with custom spreadsheet exporter
from rvandroid.test_framework.spreadsheet_exporter import SpreadsheetExporter

exporter = SpreadsheetExporter()
# Export to multiple CSV files
exporter.export_to_csv(results, "custom_export.csv")
# Export to Excel with custom formatting
exporter.export_to_excel(results, "custom_export.xlsx")

# Advanced dashboard customization
from rvandroid.test_framework.dashboard import Dashboard

# Create a custom dashboard instance
dashboard = Dashboard()
# Enable MOP metrics visualization
dashboard.set_option("show_mop_metrics", True)
# Generate dashboard with results
dashboard_file = dashboard.generate_dashboard(results, "custom_dashboard")
# Launch in browser
dashboard.launch_dashboard(dashboard_file)
```