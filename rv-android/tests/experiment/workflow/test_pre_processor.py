# tests/experiment/workflow/test_pre_processor.py
"""
Unit tests for the PreProcessor component in the experiment workflow.
"""
import os
from unittest.mock import MagicMock, patch

import pytest

from rvandroid.experiment.event_system import EventBus, EventType
from rvandroid.experiment.workflow.pre_processor import PreProcessor
from rvandroid.util.logging_manager import LoggingManager


@pytest.fixture
def setup_environment():
    """Set up common test environment."""
    # Mock event bus
    event_bus = MagicMock(spec=EventBus)

    # Set up results directory
    results_dir = "/tmp/test_results"
    os.makedirs(results_dir, exist_ok=True)

    # Create pre processor instance
    pre_processor = PreProcessor(results_dir, event_bus)

    # Mock logging
    LoggingManager._instance = MagicMock()
    logger_mock = MagicMock()
    pre_processor.logger = logger_mock

    # Mock RVSec and RvAndroid
    with patch('rvandroid.experiment.workflow.pre_processor.RVSec') as mock_rvsec_class:
        mock_rvsec = MagicMock()
        mock_rvsec_class.return_value = mock_rvsec

        with patch('rvandroid.experiment.workflow.pre_processor.RvAndroid') as mock_rvandroid_class:
            mock_rvandroid = MagicMock()
            mock_rvandroid_class.return_value = mock_rvandroid

            # Return all needed objects
            yield {
                'pre_processor': pre_processor,
                'event_bus': event_bus,
                'logger_mock': logger_mock,
                'results_dir': results_dir,
                'mock_rvsec': mock_rvsec,
                'mock_rvandroid': mock_rvandroid
            }


def test_generate_monitors(setup_environment):
    """Test monitor generation."""
    env = setup_environment
    pre_processor = env['pre_processor']
    event_bus = env['event_bus']
    mock_rvsec = env['mock_rvsec']

    # Call the method
    pre_processor._generate_monitors()

    # Verify RVSec.generate_monitors was called
    mock_rvsec.generate_monitors.assert_called_once()

    # Verify event was published
    event_bus.publish_experiment_event.assert_called_once_with(
        EventType.EXPERIMENT_STARTED,
        experiment_id="monitor_generation",
        message="Monitor generation completed",
        source="PreProcessor"
    )


def test_instrument_apks(setup_environment):
    """Test APK instrumentation."""
    env = setup_environment
    pre_processor = env['pre_processor']
    event_bus = env['event_bus']
    mock_rvandroid = env['mock_rvandroid']

    # Call the method
    pre_processor._instrument_apks()

    # Verify RvAndroid.instrument_apks was called
    mock_rvandroid.instrument_apks.assert_called_once()

    # Verify event was published
    event_bus.publish_experiment_event.assert_called_once_with(
        EventType.EXPERIMENT_STARTED,
        experiment_id="apk_instrumentation",
        message="APK instrumentation completed",
        source="PreProcessor"
    )


@patch('rvandroid.analysis.static_analysis.run_static_analysis')
@patch('os.listdir')
@patch('os.path.join')
def test_run_static_analysis(mock_join, mock_listdir, mock_run_static_analysis, setup_environment):
    """Test static analysis execution."""
    env = setup_environment
    pre_processor = env['pre_processor']
    event_bus = env['event_bus']

    # Mock os.listdir to return a list of APK files
    mock_listdir.return_value = ['app1.apk', 'app2.apk', 'not_an_apk.txt']

    # Mock os.path.join to return paths
    mock_join.side_effect = lambda *args: '/'.join(args)

    # Mock App class
    with patch('rvandroid.experiment.workflow.pre_processor.App') as mock_app_class:
        mock_app1 = MagicMock()
        mock_app1.name = 'app1'
        mock_app2 = MagicMock()
        mock_app2.name = 'app2'
        mock_app_class.side_effect = [mock_app1, mock_app2]

        # Call the method
        pre_processor._run_static_analysis()

        # Verify run_static_analysis was called for each app
        assert mock_run_static_analysis.call_count == 2

        # Verify events were published
        assert event_bus.publish_analysis_event.call_count == 2


@patch('os.listdir')
def test_get_instrumented_apks(mock_listdir, setup_environment):
    """Test retrieving instrumented APKs."""
    env = setup_environment
    pre_processor = env['pre_processor']

    # Mock os.listdir to return a list of files
    mock_listdir.return_value = ['app1.apk', 'app2.apk', 'not_an_apk.txt']

    # Mock App class
    with patch('rvandroid.experiment.workflow.pre_processor.App') as mock_app_class:
        mock_app1 = MagicMock()
        mock_app2 = MagicMock()
        mock_app_class.side_effect = [mock_app1, mock_app2]

        # Call the method
        apks = pre_processor.get_instrumented_apks()

        # Verify correct number of APKs returned
        assert len(apks) == 2
        assert apks[0] == mock_app1
        assert apks[1] == mock_app2


@patch('os.listdir')
def test_get_instrumented_apks_with_error(mock_listdir, setup_environment):
    """Test error handling when retrieving instrumented APKs."""
    env = setup_environment
    pre_processor = env['pre_processor']
    logger_mock = env['logger_mock']

    # Mock os.listdir to return a list of files
    mock_listdir.return_value = ['app1.apk', 'app2.apk', 'error.apk']

    # Mock App class to raise exception for error.apk
    def mock_app_side_effect(path):
        if 'error.apk' in path:
            raise Exception("Invalid APK")
        return MagicMock()

    with patch('rvandroid.experiment.workflow.pre_processor.App') as mock_app_class:
        mock_app_class.side_effect = mock_app_side_effect

        # Call the method
        apks = pre_processor.get_instrumented_apks()

        # Verify correct number of APKs returned (error.apk should be skipped)
        assert len(apks) == 2

        # Verify error was logged
        logger_mock.error.assert_called_once()


def test_run_static_analysis_error_handling(setup_environment):
    """Test error handling during static analysis."""
    env = setup_environment
    pre_processor = env['pre_processor']
    logger_mock = env['logger_mock']

    # Mock os.listdir to return a list of APK files
    with patch('os.listdir') as mock_listdir:
        mock_listdir.return_value = ['app1.apk']

        # Mock App class
        with patch('rvandroid.experiment.workflow.pre_processor.App') as mock_app_class:
            mock_app = MagicMock()
            mock_app.name = 'app1'
            mock_app_class.return_value = mock_app

            # Mock static_analysis.run_static_analysis to raise an exception
            with patch('rvandroid.analysis.static_analysis.run_static_analysis') as mock_run_static_analysis:
                mock_run_static_analysis.side_effect = Exception("Static analysis error")

                # Call the method
                pre_processor._run_static_analysis()

                # Verify error was logged
                logger_mock.error.assert_called()


def test_process_with_all_steps(setup_environment):
    """Test processing with all steps enabled."""
    env = setup_environment
    pre_processor = env['pre_processor']

    # Mock the steps
    pre_processor._generate_monitors = MagicMock()
    pre_processor._instrument_apks = MagicMock()
    pre_processor._run_static_analysis = MagicMock()

    # Call the process method with all steps enabled
    pre_processor.process(
        generate_monitors=True,
        instrument=True,
        static_analysis=True
    )

    # Verify all steps were called
    pre_processor._generate_monitors.assert_called_once()
    pre_processor._instrument_apks.assert_called_once()
    pre_processor._run_static_analysis.assert_called_once()


def test_process_with_some_steps_disabled(setup_environment):
    """Test processing with some steps disabled."""
    env = setup_environment
    pre_processor = env['pre_processor']

    # Mock the steps
    pre_processor._generate_monitors = MagicMock()
    pre_processor._instrument_apks = MagicMock()
    pre_processor._run_static_analysis = MagicMock()

    # Call the process method with some steps disabled
    pre_processor.process(
        generate_monitors=False,
        instrument=True,
        static_analysis=False
    )

    # Verify only enabled steps were called
    pre_processor._generate_monitors.assert_not_called()
    pre_processor._instrument_apks.assert_called_once()
    pre_processor._run_static_analysis.assert_not_called()


def test_process_with_all_steps_disabled(setup_environment):
    """Test processing with all steps disabled."""
    env = setup_environment
    pre_processor = env['pre_processor']

    # Mock the steps
    pre_processor._generate_monitors = MagicMock()
    pre_processor._instrument_apks = MagicMock()
    pre_processor._run_static_analysis = MagicMock()

    # Call the process method with all steps disabled
    pre_processor.process(
        generate_monitors=False,
        instrument=False,
        static_analysis=False
    )

    # Verify no steps were called
    pre_processor._generate_monitors.assert_not_called()
    pre_processor._instrument_apks.assert_not_called()
    pre_processor._run_static_analysis.assert_not_called()
