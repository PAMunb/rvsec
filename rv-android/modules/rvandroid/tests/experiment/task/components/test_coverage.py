import pytest
from unittest.mock import Mock, patch

from rvandroid.experiment.task.components.coverage import CoverageComponent
from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.domain.coverage import LogcatRepository
from rvandroid.experiment.task.task_model import Task
from rvandroid.analysis.coverage.tracker import CoverageTracker


@pytest.fixture
def mock_task():
    task = Mock(spec=Task)
    task.id = "test_task_123"
    task.config = Mock()
    task.config.apk_name = "test_app"
    task.result = Mock()
    task.result.logcat_file = "test_logcat.txt"
    task.result.coverage_metrics = {}
    task.static_data = {}
    task.repository = None
    return task


@pytest.fixture
def mock_event_bus():
    return Mock(spec=EventBus)


@pytest.fixture
def coverage_component(mock_task, mock_event_bus):
    component = CoverageComponent(mock_task, mock_event_bus)
    component.error_handler = Mock()
    return component


@pytest.fixture
def mock_coverage_tracker():
    tracker = Mock(spec=CoverageTracker)
    tracker.repository = Mock(spec=LogcatRepository)
    return tracker


def test_initialization(coverage_component, mock_task):
    assert coverage_component is not None
    assert coverage_component.task == mock_task
    assert isinstance(coverage_component.repository, LogcatRepository)


def test_initialize_tracker_success(coverage_component, mock_task):
    with patch('rvandroid.experiment.task.components.coverage.CoverageTracker') as mock_tracker_cls:
        mock_tracker = Mock()
        mock_tracker_cls.return_value = mock_tracker

        result = coverage_component.initialize_tracker()

        assert result is True
        mock_tracker_cls.assert_called_once_with(
            logcat_file=mock_task.result.logcat_file,
            static_data=mock_task.static_data,
            task_start_time=mock_task.result.start_time
        )


def test_initialize_tracker_failure(coverage_component):
    with patch('rvandroid.experiment.task.components.coverage.CoverageTracker') as mock_tracker_cls:
        mock_tracker_cls.side_effect = Exception("Tracker init failed")

        result = coverage_component.initialize_tracker()

        assert result is False
        coverage_component.error_handler.handle_error.assert_called_once()


def test_start_tracking_without_initialization(coverage_component):
    coverage_component.coverage_tracker = None
    result = coverage_component.start_tracking()
    assert result is False


def test_start_tracking_success(coverage_component, mock_coverage_tracker, mock_task):
    coverage_component.coverage_tracker = mock_coverage_tracker

    result = coverage_component.start_tracking()

    assert result is True
    mock_coverage_tracker.start.assert_called_once()


def test_stop_tracking_without_tracker(coverage_component):
    coverage_component.coverage_tracker = None
    result = coverage_component.stop_tracking()
    assert result is True


def test_stop_tracking_success(coverage_component, mock_coverage_tracker, mock_task):
    coverage_component.coverage_tracker = mock_coverage_tracker

    result = coverage_component.stop_tracking()

    assert result is True
    mock_coverage_tracker.stop.assert_called_once()


def test_process_results_without_tracker(coverage_component):
    coverage_component.coverage_tracker = None
    result = coverage_component.process_results()
    assert result is False


def test_process_results_success(coverage_component, mock_coverage_tracker, mock_task):
    coverage_component.coverage_tracker = mock_coverage_tracker
    mock_metrics = Mock()
    mock_metrics.to_dict.return_value = {
        "method_coverage": 80.0,
        "activity_coverage": 75.0,
        "mop_method_coverage": 70.0,
        "unique_errors": 0
    }
    mock_coverage_tracker.repository.calculate_metrics.return_value = mock_metrics

    result = coverage_component.process_results()

    assert result is True


def test_get_repository(coverage_component, mock_coverage_tracker):
    coverage_component.coverage_tracker = None
    assert coverage_component.get_repository() is None

    coverage_component.coverage_tracker = mock_coverage_tracker
    assert coverage_component.get_repository() == mock_coverage_tracker.repository
