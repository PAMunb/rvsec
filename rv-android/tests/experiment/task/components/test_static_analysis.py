# tests/experiment/task/components/test_static_analysis.py
import os
import pytest
from unittest.mock import MagicMock, patch

from rvandroid.experiment.task.components.static_analysis import StaticAnalysisComponent
from rvandroid.experiment.task.task_model import Task, TaskConfiguration
from rvandroid.experiment.event.bus import EventBus
from rvandroid.experiment.event.models import EventType
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.util.exceptions import AnalysisError


class TestStaticAnalysisComponent:
    @pytest.fixture
    def mock_task(self):
        """Create a mock task for testing"""
        config = TaskConfiguration(
            apk_name="test_app.apk",
            repetition=1,
            timeout=60,
            tool_name="monkey"
        )
        task = Task(config)
        task.app = MagicMock()
        task.app.package_name = "com.example.test"
        task.results_dir = "/tmp/test_results"
        return task

    @pytest.fixture
    def static_analysis_component(self, mock_task):
        """Create a StaticAnalysisComponent instance for testing"""
        event_bus = MagicMock(spec=EventBus)
        return StaticAnalysisComponent(mock_task, event_bus)

    @patch('rvandroid.parser.static.static_analysis_parser.read_static_analysis_files')
    def test_load_static_data_success(self, mock_read_static_files, static_analysis_component, mock_task):
        """Test successful loading of static analysis data"""
        # Prepare mock data
        mock_static_data = MagicMock(spec=StaticAnalysisData)
        mock_read_static_files.return_value = mock_static_data

        # Define task context
        task_context = {
            "task_id": mock_task.id,
            "apk_name": mock_task.config.apk_name,
            "phase": "load_static_data"
        }

        # Call the method
        result = static_analysis_component.load_static_data(task_context)

        # Assertions
        assert result is True
        assert mock_task.static_data == mock_static_data
        mock_read_static_files.assert_called_once_with(
            mock_task.results_dir,
            mock_task.config.apk_name,
            mock_task.app.package_name
        )
        static_analysis_component.event_bus.publish_analysis_event.assert_called_once_with(
            EventType.STATIC_ANALYSIS_COMPLETED,
            data={"app_name": mock_task.app.name},
            related_task_id=mock_task.id,
            source="StaticAnalysisComponent"
        )

    def test_load_static_data_already_loaded(self, static_analysis_component, mock_task):
        """Test loading static data when it's already loaded"""
        # Pre-set static data
        mock_static_data = MagicMock(spec=StaticAnalysisData)
        mock_task.static_data = mock_static_data

        # Define task context
        task_context = {
            "task_id": mock_task.id,
            "apk_name": mock_task.config.apk_name,
            "phase": "load_static_data"
        }

        # Call the method
        result = static_analysis_component.load_static_data(task_context)

        # Assertions
        assert result is True
        static_analysis_component.event_bus.publish_analysis_event.assert_not_called()

    @patch('rvandroid.parser.static.static_analysis_parser.read_static_analysis_files')
    def test_load_static_data_no_data(self, mock_read_static_files, static_analysis_component, mock_task):
        """Test loading static data when no data is found"""
        mock_read_static_files.return_value = None

        # Define task context
        task_context = {
            "task_id": mock_task.id,
            "apk_name": mock_task.config.apk_name,
            "phase": "load_static_data"
        }

        # Call the method
        result = static_analysis_component.load_static_data(task_context)

        # Assertions
        assert result is False
        assert mock_task.static_data is None
        static_analysis_component.event_bus.publish_analysis_event.assert_not_called()

    @patch('rvandroid.parser.static.static_analysis_parser.read_static_analysis_files')
    def test_load_static_data_error(self, mock_read_static_files, static_analysis_component, mock_task):
        """Test error handling during static data loading"""
        mock_read_static_files.side_effect = Exception("Test error")

        # Define task context
        task_context = {
            "task_id": mock_task.id,
            "apk_name": mock_task.config.apk_name,
            "phase": "load_static_data"
        }

        # Call the method
        result = static_analysis_component.load_static_data(task_context)

        # Assertions
        assert result is False
        assert mock_task.static_data is None
        static_analysis_component.event_bus.publish_analysis_event.assert_not_called()
