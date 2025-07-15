"""
Test framework for RV-Android system.

This package provides a comprehensive framework for evaluating 
different configurations of LLM models and prompt strategies.
"""

from rvandroid.test_framework.config import (
    TestSuite, ToolConfiguration, TestCase,
    create_default_test_suite, create_default_configurations
)
from rvandroid.test_framework.executor import (
    TestRunner, TestResult, TestExecutor
)
from rvandroid.test_framework.analyzer import (
    ResultAnalyzer, ConfigurationMetrics
)
from rvandroid.test_framework.plateau_analyzer import (
    PlateauAnalyzer, analyze_plateau
)
from rvandroid.test_framework.config_generator import (
    ConfigurationGenerator, create_minimal_test_suite,
    create_plateau_test_suite, create_comparative_test_suite
)
from rvandroid.test_framework.config_validator import (
    validate_configurations, ValidationError
)
from rvandroid.test_framework.results_loader import (
    ResultsLoader, load_results
)
from rvandroid.test_framework.framework import TestFramework

# Import exporters and visualization for convenience
from rvandroid.test_framework.exporters import (
    export_to_csv, export_to_excel
)
from rvandroid.test_framework.spreadsheet_exporter import (
    SpreadsheetExporter, export_to_enhanced_csv, export_to_enhanced_excel
)
from rvandroid.test_framework.visualization import (
    generate_visualizations
)
from rvandroid.test_framework.anomaly_detector import (
    AnomalyDetector, AnomalyReport, detect_anomalies
)
from rvandroid.test_framework.correlation_analyzer import (
    CorrelationAnalyzer, CorrelationResult, AppCharacteristic, analyze_correlations
)
from rvandroid.test_framework.dashboard import (
    Dashboard, generate_dashboard, launch_dashboard
)