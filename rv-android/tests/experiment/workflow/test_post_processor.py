# tests/experiment/workflow/test_post_processor.py
"""
Unit tests for the PostProcessor component in the experiment workflow.
"""
import os
from unittest.mock import MagicMock, patch, mock_open

import pytest

from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.experiment.workflow.post_processor import PostProcessor
from rvandroid.util.logging.manager import LoggingManager


@pytest.fixture
def setup_environment():
    """Set up common test environment."""
    # Mock event bus
    event_bus = MagicMock(spec=EventBus)

    # Set up results directory
    results_dir = "/tmp/test_results"
    os.makedirs(results_dir, exist_ok=True)

    # Mock execution controller
    execution_controller = MagicMock()
    execution_controller.get_coverage_report.return_value = {
        "summary": {
            "total_tasks": 5,
            "completed_tasks": 3,
            "avg_method_coverage": 75.5,
            "avg_activities_coverage": 80.2,
            "avg_mop_coverage": 60.1,
            "total_errors": 2
        },
        "tasks": {
            "app1_tool1_1_60": {
                "method_coverage": 78.5,
                "activities_coverage": 85.0
            }
        }
    }

    # Create post processor instance
    post_processor = PostProcessor(results_dir, event_bus, execution_controller)

    # Mock logging
    LoggingManager._instance = MagicMock()
    logger_mock = MagicMock()
    post_processor.logger = logger_mock

    # Return all needed objects
    yield {
        'post_processor': post_processor,
        'event_bus': event_bus,
        'execution_controller': execution_controller,
        'logger_mock': logger_mock,
        'results_dir': results_dir
    }

    # Clean up created files
    report_path = os.path.join(results_dir, "coverage_report.json")
    analysis_path = os.path.join(results_dir, "analysis_results.json")
    diagnostic_path = os.path.join(results_dir, "diagnostic_report.json")

    for path in [report_path, analysis_path, diagnostic_path]:
        if os.path.exists(path):
            os.remove(path)


def test_process_coverage_data_with_execution_controller(setup_environment):
    """Test that coverage data is correctly processed when execution controller is available."""
    env = setup_environment
    post_processor = env['post_processor']
    event_bus = env['event_bus']
    execution_controller = env['execution_controller']
    results_dir = env['results_dir']

    # Call the method
    with patch('builtins.open', mock_open()) as mock_file:
        post_processor._process_coverage_data()

    # Verify execution controller was called
    execution_controller.get_coverage_report.assert_called_once()

    # Verify file was written
    mock_file.assert_called_once_with(os.path.join(results_dir, "coverage_report.json"), 'w')

    # Verify event was published
    event_bus.publish_analysis_event.assert_called_once_with(
        EventType.COVERAGE_UPDATED,
        data={"report_path": os.path.join(results_dir, "coverage_report.json")},
        source="PostProcessor"
    )


def test_process_coverage_data_without_execution_controller(setup_environment):
    """Test that fallback coverage report is created when no execution controller is available."""
    env = setup_environment
    event_bus = env['event_bus']
    results_dir = env['results_dir']
    logger_mock = env['logger_mock']

    # Create processor without execution controller
    processor = PostProcessor(results_dir, event_bus)
    processor.logger = logger_mock

    # Call the method
    with patch('builtins.open', mock_open()) as mock_file:
        processor._process_coverage_data()

    # Verify default report was written
    mock_file.assert_called_once_with(os.path.join(results_dir, "coverage_report.json"), 'w')

    # Verify event was published
    event_bus.publish_analysis_event.assert_called_once()


@patch('rvandroid.analysis.results_analysis.process_results')
def test_analyze_results_success(mock_process_results, setup_environment):
    """Test successful results analysis."""
    env = setup_environment
    post_processor = env['post_processor']
    results_dir = env['results_dir']

    # Mock the process_results function
    mock_results = {
        "apps": {"app1": {"summary": {"errors": 2}}},
        "tools": {"tool1": {"errors": 1}}
    }
    mock_process_results.return_value = mock_results

    # Use a context manager to patch the open function and json.dump
    with patch('builtins.open', mock_open()) as mock_file:
        # Also mock _generate_diagnostics to prevent it from opening files
        with patch.object(post_processor, '_generate_diagnostics'):
            post_processor._analyze_results()

    # Verify process_results was called
    mock_process_results.assert_called_once_with(results_dir)

    # Verify file was written
    mock_file.assert_called_once_with(os.path.join(results_dir, "analysis_results.json"), 'w')


@patch('rvandroid.analysis.results_analysis.process_results')
def test_analyze_results_error_handling(mock_process_results, setup_environment):
    """Test error handling during results analysis."""
    env = setup_environment
    post_processor = env['post_processor']
    logger_mock = env['logger_mock']

    # Mock the process_results function to raise an exception
    mock_process_results.side_effect = Exception("Analysis error")

    # Also patch _generate_diagnostics to prevent it from being called
    with patch.object(post_processor, '_generate_diagnostics'):
        post_processor._analyze_results()

    # Verify error was logged
    logger_mock.error.assert_called()


@patch('rvandroid.util.diagnostics.DiagnosticTool')
def test_generate_diagnostics_success(mock_diagnostic_tool_class, setup_environment):
    """Test successful diagnostics generation."""
    env = setup_environment
    post_processor = env['post_processor']
    results_dir = env['results_dir']

    # Mock the DiagnosticTool
    mock_diagnostic_tool = MagicMock()
    mock_report = MagicMock()
    mock_diagnostic_tool.generate_report.return_value = mock_report
    mock_diagnostic_tool_class.return_value = mock_diagnostic_tool

    # Call the method
    post_processor._generate_diagnostics()

    # Verify diagnostic tool was used
    mock_diagnostic_tool.generate_report.assert_called_once()
    mock_report.save_to_file.assert_called_once_with(
        os.path.join(results_dir, "diagnostic_report.json")
    )


@patch('rvandroid.util.diagnostics.DiagnosticTool')
def test_generate_diagnostics_error_handling(mock_diagnostic_tool_class, setup_environment):
    """Test error handling during diagnostics generation."""
    env = setup_environment
    post_processor = env['post_processor']
    logger_mock = env['logger_mock']

    # Mock the DiagnosticTool to raise an exception
    mock_diagnostic_tool = MagicMock()
    mock_diagnostic_tool.generate_report.side_effect = Exception("Diagnostics error")
    mock_diagnostic_tool_class.return_value = mock_diagnostic_tool

    # Call the method
    post_processor._generate_diagnostics()

    # Verify error was logged
    logger_mock.error.assert_called()


def test_process_full_workflow(setup_environment):
    """Test the complete processing workflow."""
    env = setup_environment
    post_processor = env['post_processor']
    event_bus = env['event_bus']

    # Mock internal methods
    post_processor._process_coverage_data = MagicMock()
    post_processor._analyze_results = MagicMock()
    post_processor._generate_diagnostics = MagicMock()

    # Call the process method
    post_processor.process()

    # Verify all methods were called
    post_processor._process_coverage_data.assert_called_once()
    post_processor._analyze_results.assert_called_once()

    # Verify event was published
    event_bus.publish_experiment_event.assert_called_once_with(
        EventType.EXPERIMENT_STARTED,
        experiment_id="post_processing",
        message="Post-processing completed",
        source="PostProcessor"
    )
