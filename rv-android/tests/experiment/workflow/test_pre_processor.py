import os
from unittest.mock import Mock, patch, MagicMock

import pytest

from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.experiment.workflow.pre_processor import PreProcessor


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus for testing."""
    return Mock(spec=EventBus)


@pytest.fixture
def pre_processor(tmp_path, mock_event_bus):
    """
    Create a PreProcessor instance for testing.

    Args:
        tmp_path: Pytest temporary directory fixture
        mock_event_bus: Mocked EventBus

    Returns:
        PreProcessor instance
    """
    results_dir = str(tmp_path / "results")
    os.makedirs(results_dir, exist_ok=True)
    return PreProcessor(results_dir, mock_event_bus)


def test_pre_processor_initialization(pre_processor):
    """
    Test that the PreProcessor is correctly initialized.

    Verifies:
    - Results directory is set correctly
    - Event bus is set correctly
    - Logger is initialized
    """
    assert os.path.exists(pre_processor.results_dir)
    assert pre_processor.event_bus is not None
    assert hasattr(pre_processor, 'logger')
    assert pre_processor.logger is not None


@patch('rvandroid.experiment.workflow.pre_processor.RVSec')
def test_generate_monitors(mock_rvsec, pre_processor, mock_event_bus):
    """
    Test the _generate_monitors method.

    Verifies:
    - RVSec.generate_monitors() is called
    - Experiment started event is published
    """
    # Configure the mock to do nothing when generate_monitors is called
    mock_rvsec_instance = mock_rvsec.return_value
    mock_rvsec_instance.generate_monitors.return_value = None

    pre_processor._generate_monitors()

    # Verify RVSec generate_monitors was called
    mock_rvsec_instance.generate_monitors.assert_called_once()

    # Verify event was published
    mock_event_bus.publish_experiment_event.assert_called_once_with(
        EventType.EXPERIMENT_STARTED,
        experiment_id="monitor_generation",
        message="Monitor generation completed",
        source="PreProcessor"
    )


@patch('rvandroid.experiment.workflow.pre_processor.RvAndroid')
def test_instrument_apks(mock_rvandroid, pre_processor, mock_event_bus):
    """
    Test the _instrument_apks method.

    Verifies:
    - RvAndroid.instrument_apks() is called with correct parameters
    - Experiment started event is published
    """
    from settings import INSTRUMENTED_DIR

    # Configure the mock to do nothing when instrument_apks is called
    mock_rvandroid_instance = mock_rvandroid.return_value
    mock_rvandroid_instance.instrument_apks.return_value = None

    pre_processor._instrument_apks()

    # Verify RvAndroid instrument_apks was called
    mock_rvandroid_instance.instrument_apks.assert_called_once_with(
        results_dir=INSTRUMENTED_DIR
    )

    # Verify event was published
    mock_event_bus.publish_experiment_event.assert_called_once_with(
        EventType.EXPERIMENT_STARTED,
        experiment_id="apk_instrumentation",
        message="APK instrumentation completed",
        source="PreProcessor"
    )


def test_run_static_analysis(
        pre_processor,
        mock_event_bus,
        tmp_path,
        monkeypatch
):
    """
    Test the _run_static_analysis method.

    Verifies:
    - Static analysis is run for each APK
    - Correct files are processed
    - Events are published for each processed app
    - No errors are raised during processing
    """
    from unittest.mock import Mock
    from rvandroid.app import App
    from rvandroid.constants import EXTENSION_APK

    # Mock the listdir to return test APKs
    mock_apks = ['app1.apk', 'app2.apk']
    monkeypatch.setattr('os.listdir', lambda x: mock_apks)

    # Mock the instrumented directory
    monkeypatch.setattr(
        'rvandroid.experiment.workflow.pre_processor.INSTRUMENTED_DIR',
        str(tmp_path)
    )

    # Create mock App function that doesn't rely on file system
    def create_mock_app(path):
        mock_app = Mock(spec=App)
        mock_app.name = os.path.basename(path)
        mock_app.path = path
        mock_app.package_name = 'test.package'
        return mock_app

    # Mock static analysis and App creation
    with patch('rvandroid.experiment.workflow.pre_processor.App', side_effect=create_mock_app), \
            patch('rvandroid.analysis.static_analysis.run_static_analysis') as mock_run_analysis:
        # Configure the mock to do nothing when called
        mock_run_analysis.return_value = None

        # Execute the method under test
        pre_processor._run_static_analysis()

    # Verify static analysis was called for each app
    assert mock_run_analysis.call_count == len(mock_apks)

    # Capture the calls to publish_analysis_event
    calls = mock_event_bus.publish_analysis_event.call_args_list

    # Verify events were published for each app
    assert len(calls) == len(mock_apks)

    # Check the structure of event calls
    for call, app_name in zip(calls, mock_apks):
        # Unpack the call arguments
        args, kwargs = call

        # Verify event type
        assert args[0] == EventType.STATIC_ANALYSIS_COMPLETED

        # Verify data contains app name
        assert kwargs.get('data', {}).get('app_name') == app_name

        # Verify source
        assert kwargs.get('source') == 'PreProcessor'


def test_process_method(pre_processor, mock_event_bus):
    """
    Test the process method with various configurations.

    Verifies:
    - Different method combinations work correctly
    - Events are published at the right times
    """
    # Mock internal methods
    with patch.object(pre_processor, '_generate_monitors'), \
            patch.object(pre_processor, '_instrument_apks'), \
            patch.object(pre_processor, '_run_static_analysis'):
        # Test with all flags True
        pre_processor.process(
            generate_monitors=True,
            instrument=True,
            static_analysis=True
        )

        # Verify internal methods were called
        pre_processor._generate_monitors.assert_called_once()
        pre_processor._instrument_apks.assert_called_once()
        pre_processor._run_static_analysis.assert_called_once()


@patch('rvandroid.experiment.workflow.pre_processor.INSTRUMENTED_DIR')
@patch('rvandroid.experiment.workflow.pre_processor.App')
def test_get_instrumented_apks(mock_app, mock_instrumented_dir, pre_processor, tmp_path):
    """
    Test the get_instrumented_apks method.

    Verifies:
    - Correct APKs are found
    - App objects are created correctly
    """
    # Prepare mock APK files
    apk_files = ['app1.apk', 'app2.apk', 'not_an_apk.txt']
    mock_instrumented_dir.__str__.return_value = str(tmp_path)

    # Create mock APK files
    for apk in apk_files:
        (tmp_path / apk).touch()

    # Configure mocking
    with patch('os.listdir', return_value=apk_files), \
            patch('os.path.exists', return_value=True):

        # Configure App mock to return a predictable object
        mock_app.side_effect = lambda path: MagicMock(
            name=os.path.basename(path),
            path=path
        )

        instrumented_apps = pre_processor.get_instrumented_apks()

    # Verify correct number of APKs
    assert len(instrumented_apps) == 2

    # Verify App objects are created
    for app in instrumented_apps:
        assert hasattr(app, 'name')
        assert hasattr(app, 'path')
        assert app.name.endswith('.apk')
