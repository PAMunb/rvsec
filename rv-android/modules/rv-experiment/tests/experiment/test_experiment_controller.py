"""
Tests for ExperimentController - three-phase experiment workflow orchestration.

Tests cover:
- __init__() initialization with component creation
- run() with execution enabled/disabled
- _run_pre_processing() delegation
- _run_execution() APK and tool setup
- _get_configured_tools() with ToolFactory
- get_experiment_status() and save_experiment_config()
"""

import os
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch, mock_open

import pytest
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_experiment.config import ExperimentConfig
from rv_experiment.experiment.experiment_controller import ExperimentController

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_config():
    """Create mock ExperimentConfig."""
    config = MagicMock(spec=ExperimentConfig)
    config.name = "test_experiment"
    config.results_dir = None
    config.run_execution = True
    config.generate_monitors = False
    config.instrument_apks = False
    config.run_static_analysis = False
    config.repetitions = 1
    config.timeouts = [300]
    config.tool_configs = []
    config.no_window = False
    return config


@pytest.fixture
def controller(mock_config):
    """Create ExperimentController instance."""
    with patch("rv_experiment.experiment.experiment_controller.PreProcessor"):
        with patch(
            "rv_experiment.experiment.experiment_controller.ExecutionController"
        ):
            with patch("rv_experiment.experiment.experiment_controller.PostProcessor"):
                return ExperimentController(mock_config, experiment_id="test_001")


# ---------------------------------------------------------------------------
# Tests: __init__()
# ---------------------------------------------------------------------------


class TestInitialization:
    """Test ExperimentController initialization."""

    def test_init_stores_config(self, controller, mock_config):
        """Test that config is stored."""
        assert controller.config is mock_config

    def test_init_sets_experiment_id(self, controller):
        """Test that experiment_id is set."""
        assert controller.experiment_id == "test_001"

    def test_init_generates_id_if_none(self, mock_config):
        """Test that experiment_id is generated if not provided."""
        with patch("rv_experiment.experiment.experiment_controller.PreProcessor"):
            with patch(
                "rv_experiment.experiment.experiment_controller.ExecutionController"
            ):
                with patch(
                    "rv_experiment.experiment.experiment_controller.PostProcessor"
                ):
                    c = ExperimentController(mock_config)
                    assert c.experiment_id is not None

    def test_init_creates_results_dir(self, controller):
        """Test that results directory is created."""
        assert os.path.exists(controller.results_dir)

    def test_init_creates_components(self, mock_config):
        """Test that components are created."""
        with patch(
            "rv_experiment.experiment.experiment_controller.PreProcessor"
        ) as mock_pp:
            with patch(
                "rv_experiment.experiment.experiment_controller.ExecutionController"
            ) as mock_ec:
                with patch(
                    "rv_experiment.experiment.experiment_controller.PostProcessor"
                ) as mock_post:
                    ExperimentController(mock_config, experiment_id="test_001")
                    mock_pp.assert_called_once()
                    mock_ec.assert_called_once()
                    mock_post.assert_called_once()

    def test_init_creates_logger(self, controller):
        """Test that logger is created."""
        assert controller.logger is not None


# ---------------------------------------------------------------------------
# Tests: run()
# ---------------------------------------------------------------------------


class TestRun:
    """Test run() with execution enabled/disabled."""

    def test_run_with_execution_enabled(self, controller):
        """Test run with execution enabled."""
        controller.save_experiment_config = MagicMock()
        controller._run_pre_processing = MagicMock()
        controller._run_execution = MagicMock(return_value=True)
        controller.config.run_execution = True

        result = controller.run()

        assert result is True
        controller._run_pre_processing.assert_called_once()
        controller._run_execution.assert_called_once()

    def test_run_with_execution_disabled(self, controller, mock_config):
        """Test run with execution disabled."""
        mock_config.run_execution = False
        controller.save_experiment_config = MagicMock()
        controller._run_pre_processing = MagicMock()
        controller._run_execution = MagicMock()

        result = controller.run()

        assert result is True
        controller._run_pre_processing.assert_called_once()
        controller._run_execution.assert_not_called()

    def test_run_execution_failure(self, controller):
        """Test run with execution failure."""
        controller.save_experiment_config = MagicMock()
        controller._run_pre_processing = MagicMock()
        controller._run_execution = MagicMock(return_value=False)
        controller.config.run_execution = True

        result = controller.run()

        assert result is False

    def test_run_saves_config(self, controller):
        """Test that run saves experiment config."""
        controller.save_experiment_config = MagicMock()
        controller._run_pre_processing = MagicMock()
        controller._run_execution = MagicMock(return_value=True)

        controller.run()

        controller.save_experiment_config.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: _run_pre_processing()
# ---------------------------------------------------------------------------


class TestRunPreProcessing:
    """Test _run_pre_processing() delegation."""

    def test_run_pre_processing_delegates_to_processor(self, controller):
        """Test that _run_pre_processing delegates to pre_processor."""
        controller.config.generate_monitors = False
        controller.config.instrument_apks = False
        controller.config.run_static_analysis = False

        controller.pre_processor.process = MagicMock()
        controller._run_pre_processing()

        controller.pre_processor.process.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: _run_execution()
# ---------------------------------------------------------------------------


class TestRunExecution:
    """Test _run_execution() APK and tool setup."""

    def test_run_execution_returns_success(self, controller):
        """Test _run_execution returns success."""
        controller.pre_processor.get_instrumented_apks = MagicMock(
            return_value=[MagicMock()]
        )
        controller._get_configured_tools = MagicMock(return_value=[MagicMock()])
        controller.execution_controller.setup = MagicMock()
        controller.execution_controller.run = MagicMock(return_value=True)

        result = controller._run_execution()

        assert result is True
        controller.execution_controller.setup.assert_called_once()
        controller.execution_controller.run.assert_called_once()

    def test_run_execution_no_apks(self, controller):
        """Test _run_execution with no APKs."""
        controller.pre_processor.get_instrumented_apks = MagicMock(return_value=[])

        result = controller._run_execution()

        assert result is False

    def test_run_execution_no_tools(self, controller):
        """Test _run_execution with no tools."""
        controller.pre_processor.get_instrumented_apks = MagicMock(
            return_value=[MagicMock()]
        )
        controller._get_configured_tools = MagicMock(return_value=[])

        result = controller._run_execution()

        assert result is False

    def test_run_execution_failure(self, controller):
        """Test _run_execution with platform failure."""
        controller.pre_processor.get_instrumented_apks = MagicMock(
            return_value=[MagicMock()]
        )
        controller._get_configured_tools = MagicMock(return_value=[MagicMock()])
        controller.execution_controller.setup = MagicMock()
        controller.execution_controller.run = MagicMock(return_value=False)

        result = controller._run_execution()

        assert result is False


# ---------------------------------------------------------------------------
# Tests: _get_configured_tools()
# ---------------------------------------------------------------------------


class TestGetConfiguredTools:
    """Test _get_configured_tools() with ToolFactory."""

    def test_get_configured_tools_success(self, controller, mock_config):
        """Test successful tool creation."""
        mock_config.tool_configs = [MagicMock()]
        mock_config.tool_configs[0].name = "monkey"

        with patch("rv_tools.ToolFactory") as mock_factory:
            mock_tool = MagicMock()
            mock_factory.return_value.create_tool.return_value = mock_tool

            tools = controller._get_configured_tools()

            assert len(tools) == 1
            mock_factory.return_value.create_tool.assert_called_once()

    def test_get_configured_tools_skips_failed_tool(self, controller, mock_config):
        """Test that failed tool creation is skipped."""
        mock_config.tool_configs = [MagicMock(), MagicMock()]
        mock_config.tool_configs[0].name = "monkey"
        mock_config.tool_configs[1].name = "droidbot"

        with patch("rv_tools.ToolFactory") as mock_factory:
            mock_factory.return_value.create_tool.side_effect = [
                MagicMock(),  # First succeeds
                Exception("Tool error"),  # Second fails
            ]

            tools = controller._get_configured_tools()

            assert len(tools) == 1

    def test_get_configured_tools_import_error(self, controller):
        """Test _get_configured_tools with import error."""
        with patch.dict("sys.modules", {"rv_tools": None}):
            tools = controller._get_configured_tools()
            assert tools == []


# ---------------------------------------------------------------------------
# Tests: get_experiment_status() and save_experiment_config()
# ---------------------------------------------------------------------------


class TestExperimentStatus:
    """Test get_experiment_status() and save_experiment_config()."""

    def test_get_experiment_status(self, controller):
        """Test get_experiment_status returns status."""
        status = controller.get_experiment_status()
        assert "experiment_id" in status
        assert "results_dir" in status
        assert "execution_method" in status

    def test_save_experiment_config_success(self, controller):
        """Test save_experiment_config success."""
        controller.config.save_to_file = MagicMock()

        controller.save_experiment_config()

        controller.config.save_to_file.assert_called_once()

    def test_save_experiment_config_failure(self, controller):
        """Test save_experiment_config handles failure."""
        controller.config.save_to_file = MagicMock(side_effect=Exception("Save error"))
        controller.logger.warning = MagicMock()

        # Should not raise
        controller.save_experiment_config()

        controller.logger.warning.assert_called_once()
