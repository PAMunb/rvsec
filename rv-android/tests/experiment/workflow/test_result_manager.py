# tests/experiment/workflow/test_result_manager.py
"""
Unit tests for the ResultManager component in the experiment workflow.
"""
import json
import os
from unittest.mock import MagicMock, patch, mock_open

import pytest

from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.experiment.workflow.result_manager import ResultManager
from rvandroid.util.logging.manager import LoggingManager


@pytest.fixture
def setup_environment():
    """Set up common test environment."""
    # Mock event bus
    event_bus = MagicMock(spec=EventBus)

    # Set up results directory
    results_dir = "/tmp/test_results"
    os.makedirs(results_dir, exist_ok=True)

    # Create result manager instance
    result_manager = ResultManager(results_dir, event_bus)

    # Mock logging
    LoggingManager._instance = MagicMock()
    logger_mock = MagicMock()
    result_manager.logger = logger_mock

    # Return all needed objects
    yield {
        'result_manager': result_manager,
        'event_bus': event_bus,
        'logger_mock': logger_mock,
        'results_dir': results_dir
    }

    # Clean up
    dashboard_dir = os.path.join(results_dir, "dashboard")
    charts_dir = os.path.join(results_dir, "charts")
    for dir_path in [dashboard_dir, charts_dir]:
        if os.path.exists(dir_path):
            for filename in os.listdir(dir_path):
                os.remove(os.path.join(dir_path, filename))
            os.rmdir(dir_path)


@patch('rvandroid.util.performance_visualizer.PerformanceVisualizer')
def test_generate_performance_dashboard(mock_visualizer_class, setup_environment):
    """Test the generation of a performance dashboard."""
    env = setup_environment
    result_manager = env['result_manager']
    results_dir = env['results_dir']
    logger_mock = env['logger_mock']

    # Mock PerformanceVisualizer
    mock_visualizer = MagicMock()
    mock_visualizer_class.return_value = mock_visualizer
    mock_visualizer.generate_performance_dashboard.return_value = os.path.join(results_dir, "dashboard")

    # Mock os.path.exists to return True for the dashboard index
    with patch('os.path.exists', return_value=True):
        # Call the method
        result_manager._generate_performance_dashboard()

    # Verify visualizer was used
    mock_visualizer.generate_performance_dashboard.assert_called_once_with(results_dir)

    # Verify path was logged
    log_calls = [call[0][0] for call in logger_mock.info.call_args_list]
    dashboard_log = any("Dashboard available at" in str(log) for log in log_calls)
    assert dashboard_log, "Dashboard URL should be logged"


@patch('rvandroid.util.performance_visualizer.PerformanceVisualizer')
def test_generate_performance_dashboard_error(mock_visualizer_class, setup_environment):
    """Test error handling during dashboard generation."""
    env = setup_environment
    result_manager = env['result_manager']
    logger_mock = env['logger_mock']

    # Mock PerformanceVisualizer to raise an exception
    mock_visualizer = MagicMock()
    mock_visualizer_class.return_value = mock_visualizer
    mock_visualizer.generate_performance_dashboard.side_effect = Exception("Dashboard error")

    # Call the method
    result_manager._generate_performance_dashboard()

    # Verify error was logged
    logger_mock.error.assert_called()


@patch('rvandroid.util.performance_visualizer.PerformanceVisualizer')
@patch('os.path.exists')
@patch('builtins.open', new_callable=mock_open, read_data='{"summary": {"avg_method_coverage": 75}}')
def test_generate_coverage_charts(mock_open_file, mock_path_exists, mock_visualizer_class, setup_environment):
    """Test the generation of coverage charts."""
    env = setup_environment
    result_manager = env['result_manager']
    results_dir = env['results_dir']

    # Mock PerformanceVisualizer
    mock_visualizer = MagicMock()
    mock_visualizer_class.return_value = mock_visualizer

    # Mock os.path.exists to return True for the coverage report
    mock_path_exists.return_value = True

    # Mock os.makedirs to avoid creating directories
    with patch('os.makedirs'):
        # Call the method
        result_manager._generate_coverage_charts()

    # Verify visualizer was used
    mock_visualizer.generate_coverage_comparison_chart.assert_called_once()

    # Verify file was opened
    mock_open_file.assert_called_once_with(os.path.join(results_dir, "coverage_report.json"), 'r')


@patch('os.path.exists')
def test_generate_coverage_charts_no_report(mock_path_exists, setup_environment):
    """Test handling when no coverage report is available."""
    env = setup_environment
    result_manager = env['result_manager']
    logger_mock = env['logger_mock']

    # Mock os.path.exists to return False for the coverage report
    mock_path_exists.return_value = False

    # Call the method
    result_manager._generate_coverage_charts()

    # Verify warning was logged
    logger_mock.warning.assert_called()


@patch('rvandroid.util.performance_visualizer.PerformanceVisualizer')
@patch('os.path.exists')
@patch('builtins.open', new_callable=mock_open, read_data='{"summary": {"avg_method_coverage": 75}}')
def test_generate_coverage_charts_error(mock_open_file, mock_path_exists, mock_visualizer_class, setup_environment):
    """Test error handling during coverage chart generation."""
    env = setup_environment
    result_manager = env['result_manager']
    logger_mock = env['logger_mock']

    # Mock PerformanceVisualizer to raise an exception
    mock_visualizer = MagicMock()
    mock_visualizer_class.return_value = mock_visualizer
    mock_visualizer.generate_coverage_comparison_chart.side_effect = Exception("Chart error")

    # Mock os.path.exists to return True for the coverage report
    mock_path_exists.return_value = True

    # Mock os.makedirs to avoid creating directories
    with patch('os.makedirs'):
        # Call the method
        result_manager._generate_coverage_charts()

    # Verify error was logged
    logger_mock.error.assert_called()


@patch('os.path.exists')
def test_generate_error_summary(mock_path_exists, setup_environment):
    """Test the generation of error summary."""
    env = setup_environment
    result_manager = env['result_manager']
    results_dir = env['results_dir']

    # Mock os.path.exists to return True for the analysis results
    mock_path_exists.return_value = True

    # Create mock data
    mock_data = {
        "apps": {"app1": {"summary": {"errors": 2}}},
        "tools": {"tool1": {"errors": 1}}
    }

    # Call the method with mocked file operations
    with patch('builtins.open', mock_open(read_data=json.dumps(mock_data))) as mock_file:
        result_manager._generate_error_summary()

        # Verify read file was opened
        mock_file.assert_any_call(os.path.join(results_dir, "analysis_results.json"), 'r')

        # Verify write file was opened
        mock_file.assert_any_call(os.path.join(results_dir, "error_summary.json"), 'w')


@patch('os.path.exists')
def test_generate_error_summary_no_analysis(mock_path_exists, setup_environment):
    """Test handling when no analysis results are available."""
    env = setup_environment
    result_manager = env['result_manager']
    logger_mock = env['logger_mock']

    # Mock os.path.exists to return False for the analysis results
    mock_path_exists.return_value = False

    # Call the method
    result_manager._generate_error_summary()

    # Verify warning was logged
    logger_mock.warning.assert_called()


@patch('os.path.exists')
def test_generate_error_summary_file_error(mock_path_exists, setup_environment):
    """Test error handling when opening analysis results file."""
    env = setup_environment
    result_manager = env['result_manager']
    logger_mock = env['logger_mock']

    # Mock os.path.exists to return True for the analysis results
    mock_path_exists.return_value = True

    # Mock open to raise an exception
    with patch('builtins.open', side_effect=Exception("File error")):
        # Call the method
        result_manager._generate_error_summary()

    # Verify error was logged
    logger_mock.error.assert_called()


def test_generate_reports_full_workflow(setup_environment):
    """Test the complete report generation workflow."""
    env = setup_environment
    result_manager = env['result_manager']
    event_bus = env['event_bus']

    # Mock report generation methods
    result_manager._generate_performance_dashboard = MagicMock()
    result_manager._generate_coverage_charts = MagicMock()
    result_manager._generate_error_summary = MagicMock()

    # Call the generate_reports method
    result_manager.generate_reports()

    # Verify all methods were called
    result_manager._generate_performance_dashboard.assert_called_once()
    result_manager._generate_coverage_charts.assert_called_once()
    result_manager._generate_error_summary.assert_called_once()

    # Verify event was published
    event_bus.publish_experiment_event.assert_called_once_with(
        EventType.EXPERIMENT_STARTED,
        experiment_id="report_generation",
        message="Report generation completed",
        source="ResultManager"
    )
