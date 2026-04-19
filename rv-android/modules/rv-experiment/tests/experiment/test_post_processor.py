"""
Tests for PostProcessor - rv_experiment experiment post-processing.

Tests cover:
- PostProcessor initialization with TaskStorage
- process() orchestration
- _generate_instrumentation_errors() via ResultManager
- _generate_completion_diagnostics() JSON file creation
- Error handling for all operations
"""

import json
import os
from unittest.mock import MagicMock, patch, mock_open

import pytest
from rv_experiment.experiment.workflow.post_processor import PostProcessor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_results_dir(tmp_path):
    """Create a temporary results directory."""
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    # Create tasks.json for TaskStorage
    tasks_file = results_dir / "tasks.json"
    tasks_file.write_text('{"tasks": []}')
    return str(results_dir)


@pytest.fixture
def post_processor(temp_results_dir):
    """Create PostProcessor instance with mocked dependencies."""
    with patch("rv_experiment.experiment.workflow.post_processor.ResultManager"):
        with patch("rv_experiment.experiment.workflow.post_processor.TaskStorage") as mock_storage:
            mock_storage_instance = MagicMock()
            mock_storage_instance.get_tasks.return_value = []
            mock_storage.return_value = mock_storage_instance
            mock_storage_instance.load.return_value = None
            
            processor = PostProcessor(temp_results_dir)
            yield processor


# ---------------------------------------------------------------------------
# Tests: Initialization
# ---------------------------------------------------------------------------


class TestPostProcessorInitialization:
    """Test PostProcessor initialization."""

    def test_init_stores_results_dir(self, post_processor, temp_results_dir):
        """Test that results_dir is stored correctly."""
        assert post_processor.results_dir == temp_results_dir

    def test_init_creates_task_storage(self, temp_results_dir):
        """Test that TaskStorage is created with correct file."""
        with patch("rv_experiment.experiment.workflow.post_processor.TaskStorage") as mock_storage:
            mock_storage_instance = MagicMock()
            mock_storage.return_value = mock_storage_instance
            
            PostProcessor(temp_results_dir)
            
            mock_storage.assert_called_once()
            call_args = mock_storage.call_args[0][0]
            assert "tasks.json" in call_args

    def test_init_creates_logger(self, post_processor):
        """Test that logger is created."""
        assert post_processor.logger is not None

    def test_init_loads_task_storage(self, temp_results_dir):
        """Test that TaskStorage.load() is called."""
        with patch("rv_experiment.experiment.workflow.post_processor.TaskStorage") as mock_storage:
            mock_instance = MagicMock()
            mock_storage.return_value = mock_instance
            
            PostProcessor(temp_results_dir)
            
            mock_instance.load.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: process()
# ---------------------------------------------------------------------------


class TestProcess:
    """Test process() orchestration."""

    def test_process_calls_instrumentation_errors(self, post_processor):
        """Test that process() generates instrumentation errors."""
        post_processor._generate_instrumentation_errors = MagicMock()
        post_processor._generate_completion_diagnostics = MagicMock()

        post_processor.process()

        post_processor._generate_instrumentation_errors.assert_called_once()

    def test_process_calls_completion_diagnostics(self, post_processor):
        """Test that process() generates completion diagnostics."""
        post_processor._generate_instrumentation_errors = MagicMock()
        post_processor._generate_completion_diagnostics = MagicMock()

        post_processor.process()

        post_processor._generate_completion_diagnostics.assert_called_once()

    def test_process_logs_start(self, post_processor):
        """Test that process() logs start."""
        post_processor._generate_instrumentation_errors = MagicMock()
        post_processor._generate_completion_diagnostics = MagicMock()
        post_processor.logger.info = MagicMock()

        post_processor.process()

        # Should log start and completion
        assert post_processor.logger.info.called


# ---------------------------------------------------------------------------
# Tests: _generate_instrumentation_errors()
# ---------------------------------------------------------------------------


class TestGenerateInstrumentationErrors:
    """Test _generate_instrumentation_errors() via ResultManager."""

    def test_generate_instrumentation_errors_creates_result_manager(self, temp_results_dir):
        """Test that ResultManager is created with correct parameters."""
        with patch("rv_experiment.experiment.workflow.post_processor.ResultManager") as mock_rm:
            mock_rm_instance = MagicMock()
            mock_rm.return_value = mock_rm_instance
            
            with patch("rv_experiment.experiment.workflow.post_processor.TaskStorage") as mock_storage:
                mock_storage_instance = MagicMock()
                mock_storage.return_value = mock_storage_instance
                
                processor = PostProcessor(temp_results_dir)
                processor._generate_instrumentation_errors()
                
                mock_rm.assert_called_once()

    def test_generate_instrumentation_errors_calls_generate_reports(self, temp_results_dir):
        """Test that ResultManager.generate_reports() is called."""
        with patch("rv_experiment.experiment.workflow.post_processor.ResultManager") as mock_rm:
            mock_rm_instance = MagicMock()
            mock_rm.return_value = mock_rm_instance
            
            with patch("rv_experiment.experiment.workflow.post_processor.TaskStorage") as mock_storage:
                mock_storage_instance = MagicMock()
                mock_storage.return_value = mock_storage_instance
                
                processor = PostProcessor(temp_results_dir)
                processor._generate_instrumentation_errors()
                
                mock_rm_instance.generate_reports.assert_called_once()

    def test_generate_instrumentation_errors_handles_exception(self, post_processor):
        """Test that exceptions are handled gracefully."""
        post_processor.error_handler.handle_error = MagicMock()
        
        # Force an exception by removing results_dir
        post_processor.results_dir = "/nonexistent/path"
        
        # Should not raise
        post_processor._generate_instrumentation_errors()
        
        # Error handler may or may not be called depending on exception type
        # Just ensure no exception propagates


# ---------------------------------------------------------------------------
# Tests: _generate_completion_diagnostics()
# ---------------------------------------------------------------------------


class TestGenerateCompletionDiagnostics:
    """Test _generate_completion_diagnostics() JSON file creation."""

    def test_generate_completion_diagnostics_creates_file(self, post_processor, temp_results_dir):
        """Test that completion diagnostics file is created."""
        post_processor._generate_completion_diagnostics()

        diagnostic_file = os.path.join(temp_results_dir, "experiment_completion.json")
        assert os.path.exists(diagnostic_file)

    def test_generate_completion_diagnostics_content(self, post_processor, temp_results_dir):
        """Test that completion diagnostics contains expected fields."""
        post_processor._generate_completion_diagnostics()

        diagnostic_file = os.path.join(temp_results_dir, "experiment_completion.json")
        with open(diagnostic_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "results_directory" in data
        assert "completion_timestamp" in data
        assert "post_processing_completed" in data
        assert data["post_processing_completed"] is True

    def test_generate_completion_diagnostics_results_dir(self, post_processor, temp_results_dir):
        """Test that results_directory matches the configured path."""
        post_processor._generate_completion_diagnostics()

        diagnostic_file = os.path.join(temp_results_dir, "experiment_completion.json")
        with open(diagnostic_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["results_directory"] == temp_results_dir

    def test_generate_completion_diagnostics_handles_exception(self, post_processor):
        """Test that exceptions are handled gracefully."""
        post_processor.error_handler.handle_error = MagicMock()
        # Force an exception by making _save_diagnostics fail
        post_processor._save_diagnostics = MagicMock(side_effect=OSError("Cannot write"))

        # Should not raise
        post_processor._generate_completion_diagnostics()

        post_processor.error_handler.handle_error.assert_called_once()

    def test_generate_completion_diagnostics_logs_completion(self, post_processor):
        """Test that completion diagnostics logs completion."""
        post_processor.logger.info = MagicMock()
        
        post_processor._generate_completion_diagnostics()

        assert post_processor.logger.info.called


# ---------------------------------------------------------------------------
# Tests: Helper methods
# ---------------------------------------------------------------------------


class TestHelperMethods:
    """Test helper methods."""

    def test_get_current_timestamp_returns_iso_format(self, post_processor):
        """Test that timestamp is in ISO format."""
        timestamp = post_processor._get_current_timestamp()
        
        # Should be a valid ISO format string
        assert isinstance(timestamp, str)
        assert "T" in timestamp  # ISO format separator

    def test_save_diagnostics_creates_file(self, post_processor, tmp_path):
        """Test that _save_diagnostics creates file."""
        diagnostic_path = str(tmp_path / "test_diagnostic.json")
        diagnostic_info = {"test": "data"}

        post_processor._save_diagnostics(diagnostic_path, diagnostic_info)

        assert os.path.exists(diagnostic_path)

    def test_save_diagnostics_content(self, post_processor, tmp_path):
        """Test that _save_diagnostics saves correct content."""
        diagnostic_path = str(tmp_path / "test_diagnostic.json")
        diagnostic_info = {"key": "value", "number": 42}

        post_processor._save_diagnostics(diagnostic_path, diagnostic_info)

        with open(diagnostic_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data == diagnostic_info

    def test_save_diagnostics_handles_exception(self, post_processor):
        """Test that _save_diagnostics handles exceptions."""
        post_processor.logger.warning = MagicMock()

        # Should not raise
        post_processor._save_diagnostics("/nonexistent/path/file.json", {"test": "data"})

        post_processor.logger.warning.assert_called_once()
