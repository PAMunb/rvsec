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
from rvandroid.test_framework.framework import TestFramework