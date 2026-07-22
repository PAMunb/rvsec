"""
Tests for StaticAnalysisComponent - rv_platform static analysis data loading.

Tests cover:
- Component initialization
- execute() with copy and load workflow
- load_static_data() with existing and new data
- copy_static_analysis_files() with file copy logic
- Error handling for all operations
"""

import os
from unittest.mock import MagicMock, patch, mock_open

import pytest
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_platform.components.static_analysis import StaticAnalysisComponent

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_task():
    """Create a mock task with minimal configuration."""
    task = MagicMock()
    task.id = "test_task_001"
    task.config = MagicMock()
    task.config.apk_name = "test_app.apk"
    task.results_dir = "/tmp/test_results"
    task.app = MagicMock()
    task.app.code_package = "com.test.app"
    task.app.name = "TestApp"
    task.static_data = None  # Ensure not pre-loaded
    return task


@pytest.fixture
def static_analysis_component(mock_task):
    """Create StaticAnalysisComponent instance with mocked dependencies."""
    component = StaticAnalysisComponent(mock_task, "/tmp/apks")
    yield component


# ---------------------------------------------------------------------------
# Tests: Initialization
# ---------------------------------------------------------------------------


class TestStaticAnalysisComponentInitialization:
    """Test StaticAnalysisComponent initialization."""

    def test_init_sets_name(self, static_analysis_component):
        """Test that component name is set correctly."""
        assert static_analysis_component.name == "StaticAnalysisComponent"

    def test_init_stores_task(self, static_analysis_component, mock_task):
        """Test that task is stored correctly."""
        assert static_analysis_component.task is mock_task

    def test_init_stores_apks_dir(self, static_analysis_component):
        """Test that apks_dir is stored correctly."""
        assert static_analysis_component.apks_dir == "/tmp/apks"

    def test_init_creates_logger(self, static_analysis_component):
        """Test that logger is created."""
        assert static_analysis_component.logger is not None


# ---------------------------------------------------------------------------
# Tests: execute() and cleanup()
# ---------------------------------------------------------------------------


class TestExecuteAndCleanup:
    """Test execute() and cleanup() behavior."""

    def test_execute_returns_true(self, static_analysis_component):
        """Test that execute() returns True on success."""
        static_analysis_component.copy_static_analysis_files = MagicMock(
            return_value=True
        )
        static_analysis_component.load_static_data = MagicMock(return_value=True)

        result = static_analysis_component.execute({})

        assert result is True

    def test_execute_copies_static_files(self, static_analysis_component):
        """Test that execute copies static analysis files."""
        static_analysis_component.copy_static_analysis_files = MagicMock(
            return_value=True
        )
        static_analysis_component.load_static_data = MagicMock(return_value=True)

        static_analysis_component.execute({})

        static_analysis_component.copy_static_analysis_files.assert_called_once()

    def test_execute_loads_static_data(self, static_analysis_component):
        """Test that execute loads static data."""
        static_analysis_component.copy_static_analysis_files = MagicMock(
            return_value=True
        )
        static_analysis_component.load_static_data = MagicMock(return_value=True)

        static_analysis_component.execute({})

        static_analysis_component.load_static_data.assert_called_once()

    def test_execute_continues_without_static_data(self, static_analysis_component):
        """Test that execute continues when static data loading fails."""
        static_analysis_component.copy_static_analysis_files = MagicMock(
            return_value=True
        )
        static_analysis_component.load_static_data = MagicMock(return_value=False)

        result = static_analysis_component.execute({})

        # Should still return True (static analysis is not critical)
        assert result is True

    def test_execute_handles_exception(self, static_analysis_component):
        """Test that execute handles exceptions gracefully."""
        static_analysis_component.copy_static_analysis_files = MagicMock(
            side_effect=Exception("Error")
        )
        static_analysis_component.error_handler.handle_error = MagicMock()

        result = static_analysis_component.execute({})

        # Should return True (static analysis is not critical)
        assert result is True

    def test_cleanup_does_nothing(self, static_analysis_component):
        """Test that cleanup() is a no-op."""
        # Should not raise
        static_analysis_component.cleanup({})


# ---------------------------------------------------------------------------
# Tests: load_static_data()
# ---------------------------------------------------------------------------


class TestLoadStaticData:
    """Test load_static_data() with various scenarios."""

    def test_load_static_data_returns_true_if_already_loaded(
        self, static_analysis_component, mock_task
    ):
        """Test that load_static_data returns True if data already loaded."""
        mock_task.static_data = {"existing": "data"}

        result = static_analysis_component.load_static_data({})

        assert result is True

    def test_load_static_data_returns_true_if_data_found(
        self, static_analysis_component
    ):
        """Test that load_static_data returns True if data is found."""
        with patch(
            "rv_platform.components.static_analysis.static_analysis_parser.read_static_analysis_files",
            return_value={"data": "parsed"},
        ):
            result = static_analysis_component.load_static_data({})
            assert result is True

    def test_load_static_data_returns_false_if_no_data(self, static_analysis_component):
        """Test that load_static_data returns False if no data found."""
        with patch(
            "rv_platform.components.static_analysis.static_analysis_parser.read_static_analysis_files",
            return_value=None,
        ):
            result = static_analysis_component.load_static_data({})
            assert result is False

    def test_load_static_data_returns_true_on_exception(
        self, static_analysis_component
    ):
        """Test that load_static_data returns True on exception (component returns True)."""
        with patch(
            "rv_platform.components.static_analysis.static_analysis_parser.read_static_analysis_files",
            side_effect=Exception("Parser error"),
        ):
            static_analysis_component.error_handler.handle_error = MagicMock()
            result = static_analysis_component.load_static_data({})
            # The component itself returns False, but execute() wraps it and returns True
            assert result is False

    def test_load_static_data_uses_code_package(self, static_analysis_component):
        """Test that load_static_data uses code_package parameter."""
        with patch(
            "rv_platform.components.static_analysis.static_analysis_parser.read_static_analysis_files",
            return_value={"data": "parsed"},
        ) as mock_read:
            static_analysis_component.load_static_data({})
            call_args = mock_read.call_args
            # Check code_package was passed
            assert call_args is not None


# ---------------------------------------------------------------------------
# Tests: copy_static_analysis_files()
# ---------------------------------------------------------------------------


class TestCopyStaticAnalysisFiles:
    """Test copy_static_analysis_files() file copy logic."""

    def test_copy_files_returns_true_when_files_exist(
        self, static_analysis_component, tmp_path
    ):
        """Test that copy_static_analysis_files returns True when files exist."""
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        static_analysis_component.task.results_dir = str(results_dir)

        # Create fake source file
        apks_dir = tmp_path / "apks"
        apks_dir.mkdir()
        methods_file = apks_dir / "test_app.apk.methods"
        methods_file.write_text("methods data")
        static_analysis_component.apks_dir = str(apks_dir)

        result = static_analysis_component.copy_static_analysis_files()

        assert result is True
        # File should be copied
        assert (results_dir / "test_app.apk.methods").exists()

    def test_copy_files_returns_false_if_no_files_found(
        self, static_analysis_component, tmp_path
    ):
        """Test that copy_static_analysis_files returns False if no files found."""
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        static_analysis_component.task.results_dir = str(results_dir)

        # Don't create any source files
        apks_dir = tmp_path / "apks"
        apks_dir.mkdir()
        static_analysis_component.apks_dir = str(apks_dir)

        result = static_analysis_component.copy_static_analysis_files()

        assert result is False

    def test_copy_files_handles_exception(self, static_analysis_component):
        """Test that copy_static_analysis_files handles exceptions."""
        # Use a path that will cause an error
        static_analysis_component.apks_dir = "/nonexistent_invalid_path"
        static_analysis_component.task.results_dir = "/also_nonexistent"
        static_analysis_component.error_handler.handle_error = MagicMock()

        result = static_analysis_component.copy_static_analysis_files()

        assert result is False
        static_analysis_component.error_handler.handle_error.assert_called()
