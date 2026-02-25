"""
Unit tests for the static analysis module.

Tests for StaticAnalyzer which runs the unified GATOR-based analysis client.
"""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

from rv_static_analysis.analysis.static.static_analysis import (
    StaticAnalyzer,
    StaticAnalysisException,
)
from rv_static_analysis.config import RVStaticAnalysisConfig
from rv_android_core.domain.app import App
from rv_android_core.commands.command_result import CommandResult
from rv_android_core.util.error.exceptions import RVCommandTimeoutError


@pytest.fixture
def mock_app():
    """Fixture that provides a mock App instance."""
    app = MagicMock(spec=App)
    app.name = "test_app"
    app.package_name = "com.example.test"
    app.code_package = "com.example.test"
    app.path = "/path/to/test_app.apk"
    return app


@pytest.fixture
def output_dir():
    """Fixture that provides a test output directory."""
    return "/tmp/test_output"


@pytest.fixture
def mock_config():
    """Fixture that provides a mocked RVStaticAnalysisConfig instance."""
    config = MagicMock(spec=RVStaticAnalysisConfig)
    config.output_dir = "/tmp/test_output"
    config.gator_dir = "/fake/gator"
    config.analysis_client_jar = "/fake/gator/rvsec-analysis-client.jar"
    config.jvm_memory = "8g"
    config.analysis_timeout = 600
    config.get_tool_command.return_value = [
        "python",
        "/fake/gator/gator",
        "a",
        "-p",
        "/path/to/test_app.apk",
        "--client-jar",
        "/fake/gator/rvsec-analysis-client.jar",
        "--out",
        "/tmp/test_output/test_app.json",
        "-client",
        "RvsecAnalysisClient",
    ]
    return config


@pytest.fixture
def analyzer(mock_app, mock_config, output_dir):
    """Fixture that provides a StaticAnalyzer instance."""
    with patch("os.makedirs") as mock_makedirs:
        analyzer = StaticAnalyzer(
            app=mock_app, config=mock_config, output_dir=output_dir
        )
        mock_makedirs.assert_called_once_with(output_dir, exist_ok=True)
        return analyzer


class TestStaticAnalyzer:
    """Tests for the StaticAnalyzer class."""

    def test_initialization(self, analyzer, mock_app, output_dir):
        """Test that the analyzer initializes correctly."""
        assert analyzer.app == mock_app
        assert analyzer.output_dir == output_dir
        assert analyzer.analysis_file == os.path.join(
            output_dir, f"{mock_app.name}.json"
        )
        assert analyzer.result.analysis_file == analyzer.analysis_file

    @patch("rv_static_analysis.analysis.static.static_analysis.Command")
    def test_run_analysis(self, mock_command, analyzer):
        """Test that analysis is run correctly."""
        mock_command_instance = MagicMock()
        mock_command_instance.invoke.return_value = CommandResult(0, "Success", "")
        mock_command.return_value = mock_command_instance

        with patch("os.path.isfile", return_value=False):
            analyzer._run_analysis()

        mock_command.assert_called_once()
        mock_command_instance.invoke.assert_called_once_with(stdout=sys.stdout)

    @patch("rv_static_analysis.analysis.static.static_analysis.Command")
    def test_run_analysis_passes_code_package(self, mock_command, analyzer):
        """Test that _run_analysis passes code_package to get_tool_command."""
        mock_command_instance = MagicMock()
        mock_command_instance.invoke.return_value = CommandResult(0, "Success", "")
        mock_command.return_value = mock_command_instance

        with patch("os.path.isfile", return_value=False):
            analyzer._run_analysis()

        # Verify get_tool_command was called with code_package kwarg
        analyzer.config.get_tool_command.assert_called_once_with(
            "analysis",
            analyzer.app.path,
            analyzer.analysis_file,
            code_package=analyzer.app.code_package,
        )

    @patch("rv_static_analysis.analysis.static.static_analysis.Command")
    def test_run_analysis_skip_if_exists(self, mock_command, analyzer):
        """Test that analysis is skipped if the result file already exists."""
        mock_command_instance = MagicMock()
        mock_command.return_value = mock_command_instance

        with patch("os.path.isfile", return_value=True):
            analyzer._run_analysis()

        # Command is still created but invoke() should NOT be called
        mock_command_instance.invoke.assert_not_called()

    @patch("rv_static_analysis.analysis.static.static_analysis.Command")
    def test_execute_command_success(self, mock_command, analyzer):
        """Test command execution with successful result."""
        mock_command_instance = MagicMock()
        mock_command_instance.invoke.return_value = CommandResult(0, "Success", "")
        mock_command.return_value = mock_command_instance

        with patch("os.path.isfile", return_value=False):
            result = analyzer._execute_command(
                "ANALYSIS", "/tmp/test.json", mock_command_instance
            )

        assert result.code == 0
        assert "ANALYSIS" in analyzer.execution_times

    @patch("rv_static_analysis.analysis.static.static_analysis.Command")
    def test_execute_command_failure(self, mock_command, analyzer):
        """Test command execution with failure result."""
        mock_command_instance = MagicMock()
        mock_command_instance.invoke.return_value = CommandResult(
            1, "", "Error message"
        )
        mock_command.return_value = mock_command_instance

        with patch("os.path.isfile", return_value=False):
            with pytest.raises(StaticAnalysisException) as exc_info:
                analyzer._execute_command(
                    "ANALYSIS", "/tmp/test.json", mock_command_instance
                )

        assert "Analysis ANALYSIS failed with exit code 1" in str(exc_info.value)

    @patch("rv_static_analysis.analysis.static.static_analysis.Command")
    def test_execute_command_timeout(self, mock_command, analyzer):
        """Test command execution with timeout preserves partial result."""
        mock_command_instance = MagicMock()
        mock_command_instance.invoke.side_effect = RVCommandTimeoutError("Timed out")
        mock_command.return_value = mock_command_instance

        with patch("os.path.isfile", return_value=False):
            result = analyzer._execute_command(
                "ANALYSIS", "/tmp/test.json", mock_command_instance
            )

        assert result.code == 0
        assert analyzer.result.timed_out is True
        assert "ANALYSIS" in analyzer.execution_times

    @patch.object(StaticAnalyzer, "_run_analysis")
    def test_analyze_success(self, mock_run, analyzer):
        """Test successful analysis."""
        analyzer.execution_times = {"ANALYSIS": 5.0}

        result = analyzer.analyze()

        mock_run.assert_called_once()
        assert result.success is True
        assert result.execution_times == analyzer.execution_times

    @patch.object(StaticAnalyzer, "_run_analysis")
    def test_analyze_failure(self, mock_run, analyzer):
        """Test analysis failure."""
        mock_run.side_effect = StaticAnalysisException("Analysis failed")

        result = analyzer.analyze()

        mock_run.assert_called_once()
        assert result.success is False
        assert len(result.errors) == 1
        assert "Analysis failed" in result.errors[0]

    def test_get_metrics(self, analyzer):
        """Test retrieving metrics from the analyzer."""
        analyzer.execution_times = {"ANALYSIS": 5.0}
        analyzer.result.success = True

        metrics = analyzer.get_metrics()

        assert metrics["execution_times"] == analyzer.execution_times
        assert metrics["success"] is True
        assert metrics["timed_out"] is False
        assert metrics["error_count"] == 0
        assert metrics["analysis_file"] == analyzer.analysis_file

    def test_get_static_data_success(self, analyzer):
        """Test successfully retrieving static data."""
        analyzer.result.success = True

        parser_mock = MagicMock()
        mock_static_data = MagicMock()
        parser_mock.parse_file.return_value = mock_static_data

        with patch(
            "rv_static_analysis.analysis.static.static_analysis.StaticAnalysisParser",
            return_value=parser_mock,
        ):
            result = analyzer.get_static_data()

        assert result is not None
        parser_mock.parse_file.assert_called_once_with(
            analyzer.analysis_file, analyzer.app.code_package
        )

    def test_get_static_data_analysis_failed(self, analyzer):
        """Test get_static_data when analysis was not successful."""
        analyzer.result.success = False
        analyzer.result.timed_out = False

        result = analyzer.get_static_data()

        assert result is None

    def test_get_static_data_timeout_still_parses(self, analyzer):
        """Test get_static_data still parses when timed out (partial JSON)."""
        analyzer.result.success = True
        analyzer.result.timed_out = True

        parser_mock = MagicMock()
        mock_static_data = MagicMock()
        parser_mock.parse_file.return_value = mock_static_data

        with patch(
            "rv_static_analysis.analysis.static.static_analysis.StaticAnalysisParser",
            return_value=parser_mock,
        ):
            result = analyzer.get_static_data()

        assert result is not None
        parser_mock.parse_file.assert_called_once()

    def test_get_static_data_parser_exception(self, analyzer):
        """Test get_static_data when parser raises an exception."""
        analyzer.result.success = True

        parser_mock = MagicMock()
        parser_mock.parse_file.side_effect = Exception("Parser error")

        with patch(
            "rv_static_analysis.analysis.static.static_analysis.StaticAnalysisParser",
            return_value=parser_mock,
        ):
            result = analyzer.get_static_data()

        assert result is None
        parser_mock.parse_file.assert_called_once()
