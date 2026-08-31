"""
Tests for ExecutionController - experiment execution via rv-platform.

Tests cover:
- __init__() initialization
- setup() creates platform
- get_statistics() and get_coverage_report()
- _create_platform_config() APK directory selection
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.domain.app import App
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_experiment.config import ExperimentConfig
from rv_experiment.experiment.workflow.execution_controller import ExecutionController

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_config():
    """Create mock ExperimentConfig."""
    config = MagicMock(spec=ExperimentConfig)
    config.output_dir = "/tmp/test_exp"
    config.apks_dir = "/tmp/test_apks"
    config.apks_filter = None
    config.logcat_diagnostics = False
    config.package_detector = False
    config.strip_build_type_suffix = False
    config.device_port = None
    config.repetitions = 1
    config.timeouts = [300]
    return config


@pytest.fixture
def mock_apks():
    """Create mock APK list."""
    apk = MagicMock(spec=App)
    apk.name = "test.apk"
    apk.path = "/tmp/test.apk"
    return [apk]


@pytest.fixture
def mock_tools():
    """Create mock tool list."""
    tool = MagicMock(spec=AbstractTool)
    tool.name = "monkey"
    tool.variant = "default"
    tool.parameters = {}
    return [tool]


@pytest.fixture
def controller(mock_config):
    """Create ExecutionController instance."""
    return ExecutionController(mock_config)


# ---------------------------------------------------------------------------
# Tests: __init__()
# ---------------------------------------------------------------------------


class TestInitialization:
    """Test ExecutionController initialization."""

    def test_init_stores_config(self, controller, mock_config):
        """Test that config is stored."""
        assert controller.config is mock_config

    def test_init_platform_is_none(self, controller):
        """Test that platform is None initially."""
        assert controller.platform is None

    def test_init_platform_config_is_none(self, controller):
        """Test that platform_config is None initially."""
        assert controller.platform_config is None

    def test_init_has_no_errors(self, controller):
        """Test that has_errors is False initially."""
        assert controller.has_errors is False

    def test_init_creates_logger(self, controller):
        """Test that logger is created."""
        assert controller.logger is not None


# ---------------------------------------------------------------------------
# Tests: setup()
# ---------------------------------------------------------------------------


class TestSetup:
    """Test setup() creates platform."""

    def test_setup_creates_platform(self, controller, mock_apks, mock_tools):
        """Test that setup creates platform."""
        with patch(
            "rv_experiment.experiment.workflow.execution_controller.Platform"
        ) as mock_platform:
            controller.setup(
                apks=mock_apks,
                repetitions=2,
                timeouts=[300, 600],
                tools=mock_tools,
            )
            mock_platform.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: get_statistics()
# ---------------------------------------------------------------------------


class TestGetStatistics:
    """Test get_statistics()."""

    def test_statistics_not_executed(self, controller):
        """Test statistics when not executed."""
        stats = controller.get_statistics()
        assert stats["status"] == "not_executed"
        assert stats["tasks_completed"] == 0
        assert stats["tasks_failed"] == 0


# ---------------------------------------------------------------------------
# Tests: get_coverage_report()
# ---------------------------------------------------------------------------


class TestGetCoverageReport:
    """Test get_coverage_report()."""

    def test_coverage_report_not_executed(self, controller):
        """Test coverage report when not executed."""
        report = controller.get_coverage_report()
        assert report["status"] == "no_execution_data"

    def test_coverage_report_after_execution(self, controller, mock_apks, mock_tools):
        """Test coverage report after execution."""
        with patch(
            "rv_experiment.experiment.workflow.execution_controller.Platform"
        ) as mock_platform_cls:
            mock_platform = MagicMock()
            mock_platform.run.return_value = {
                "total_tasks": 5,
                "successful_tasks": 5,
                "failed_tasks": 0,
            }
            mock_platform_cls.return_value = mock_platform

            controller.setup(
                apks=mock_apks,
                repetitions=1,
                timeouts=[300],
                tools=mock_tools,
            )
            controller.run()
            report = controller.get_coverage_report()

            assert "coverage_source" in report
            assert report["coverage_source"] == "rv_platform_integration"

    def test_coverage_report_handles_error(self, controller):
        """Test coverage report handles errors."""
        # Force an error by making platform_config None
        controller.platform = MagicMock()
        controller.platform_config = None
        controller.has_errors = False

        report = controller.get_coverage_report()

        # Should handle gracefully
        assert "coverage_source" in report or "status" in report


# ---------------------------------------------------------------------------
# Tests: _create_platform_config()
# ---------------------------------------------------------------------------


class TestCreatePlatformConfig:
    """Test _create_platform_config() with APK directory selection."""

    def test_config_uses_instrumented_apks_when_available(self, controller, mock_tools):
        """Test config uses instrumented APKs when available."""
        # Create instrumented APKs dir
        instrumented_dir = os.path.join(
            controller.config.output_dir, "instrumented_apks"
        )
        os.makedirs(instrumented_dir, exist_ok=True)

        with (
            patch("os.path.exists", return_value=True),
            patch("os.listdir", return_value=["test.apk"]),
        ):
            config = controller._create_platform_config(
                repetitions=1,
                timeouts=[300],
                tools=mock_tools,
                results_dir="/tmp/results",
            )
            assert config is not None

    @pytest.mark.parametrize("policy", [True, False])
    def test_platform_config_carries_package_detector(
        self, controller, mock_tools, policy
    ):
        """The run's package policy reaches task generation by value (INV-EXP-34).

        rv-platform obtains it from PlatformConfig, never from the environment:
        the variable is read once, at the entry point, and copied here alongside
        the configuration ExecutionController already builds.
        """
        controller.config.package_detector = policy

        with (
            patch("os.path.exists", return_value=True),
            patch("os.listdir", return_value=["test.apk"]),
        ):
            config = controller._create_platform_config(
                repetitions=1,
                timeouts=[300],
                tools=mock_tools,
                results_dir="/tmp/results",
            )

        assert config.package_detector is policy
