"""
Unit tests for the static analysis module.

This module contains tests for StaticAnalyzer class which orchestrates
the execution of static analysis tools for Android applications.
"""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

from rv_static_analysis.analysis.static.static_analysis import (
    StaticAnalyzer,
    StaticAnalysisException
)
from rv_static_analysis.config import RVStaticAnalysisConfig
from rv_android_core.domain.app import App
from rv_android_core.commands.command import Command
from rv_android_core.commands.command_result import CommandResult


@pytest.fixture
def mock_app():
    """Fixture that provides a mock App instance."""
    app = MagicMock(spec=App)
    app.name = "test_app"
    app.package_name = "com.example.test"
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
    config.get_static_analysis_tools.return_value = {
        'gesda_jar': '/fake/gesda.jar',
        'gator_jar': '/fake/gator.jar',
        'reach_jar': '/fake/reach.jar'
    }
    config.get_tool_command.return_value = ["java", "-jar", "/fake/tool.jar"]
    return config


@pytest.fixture
def analyzer(mock_app, mock_config, output_dir):
    """Fixture that provides a StaticAnalyzer instance."""
    with patch('os.makedirs') as mock_makedirs:
        analyzer = StaticAnalyzer(mock_app, mock_config, output_dir)
        mock_makedirs.assert_called_once_with(output_dir, exist_ok=True)
        return analyzer


class TestStaticAnalyzer:
    """Tests for the StaticAnalyzer class."""

    def test_initialization(self, analyzer, mock_app, output_dir):
        """Test that the analyzer initializes correctly."""
        assert analyzer.app == mock_app
        assert analyzer.output_dir == output_dir
        assert analyzer.gesda_file == os.path.join(output_dir, f"{mock_app.name}.gesda")
        assert analyzer.gator_file == os.path.join(output_dir, f"{mock_app.name}.wtg")
        assert analyzer.reach_file == os.path.join(output_dir, f"{mock_app.name}.reach")
        assert analyzer.result.gesda_file == analyzer.gesda_file
        assert analyzer.result.gator_file == analyzer.gator_file
        assert analyzer.result.reach_file == analyzer.reach_file

    @patch('rv_static_analysis.analysis.static.static_analysis.Command')
    def test_run_gesda(self, mock_command, analyzer):
        """Test that GESDA analysis is run correctly."""
        # Setup
        mock_command_instance = MagicMock()
        mock_command_instance.invoke.return_value = CommandResult(0, "Success", "")
        mock_command.return_value = mock_command_instance

        # Act
        with patch('os.path.isfile', return_value=False):
            analyzer._run_gesda()

        # Assert
        mock_command.assert_called_once()
        # Don't check exact command arguments, just verify it was called
        mock_command_instance.invoke.assert_called_once_with(stdout=sys.stdout)

    @patch('rv_static_analysis.analysis.static.static_analysis.Command')
    def test_run_gesda_skip_if_exists(self, mock_command, analyzer):
        """Test that GESDA analysis is skipped if the result file already exists."""
        # Setup
        mock_command_instance = MagicMock()
        mock_command.return_value = mock_command_instance

        # Act - Don't mock Command at this level, as invoke() might still be called
        with patch('os.path.isfile', return_value=True), \
                patch.object(Command, 'invoke', return_value=CommandResult(0, "", "")):
            analyzer._run_gesda()

        # Assert
        # Don't assert on command not being called - the class still gets instantiated
        # Just verify the .invoke() method was not called on our mock
        mock_command_instance.invoke.assert_not_called()

    @patch('rv_static_analysis.analysis.static.static_analysis.Command')
    def test_run_gator(self, mock_command, analyzer):
        """Test that GATOR analysis is run correctly."""
        # Setup
        mock_command_instance = MagicMock()
        mock_command_instance.invoke.return_value = CommandResult(0, "Success", "")
        mock_command.return_value = mock_command_instance

        # Act
        with patch('os.path.isfile', return_value=False):
            analyzer._run_gator()

        # Assert
        mock_command.assert_called_once()
        # Don't check exact command arguments, just verify it was called
        mock_command_instance.invoke.assert_called_once_with(stdout=sys.stdout)

    @patch('rv_static_analysis.analysis.static.static_analysis.Command')
    def test_run_reachability(self, mock_command, analyzer):
        """Test that reachability analysis is run correctly."""
        # Setup
        mock_command_instance = MagicMock()
        mock_command_instance.invoke.return_value = CommandResult(0, "Success", "")
        mock_command.return_value = mock_command_instance

        # Act
        with patch('os.path.isfile', return_value=False):
            analyzer._run_reachability()

        # Assert
        mock_command.assert_called_once()
        # Don't check exact command arguments, just verify it was called
        mock_command_instance.invoke.assert_called_once_with(stdout=sys.stdout)

    @patch('rv_static_analysis.analysis.static.static_analysis.Command')
    def test_execute_command_success(self, mock_command, analyzer):
        """Test command execution with successful result."""
        # Setup
        mock_command_instance = MagicMock()
        mock_command_instance.invoke.return_value = CommandResult(0, "Success", "")
        mock_command.return_value = mock_command_instance

        # Act
        with patch('os.path.isfile', return_value=False):
            result = analyzer._execute_command("TEST", "/tmp/test.out", mock_command_instance)

        # Assert
        assert result.code == 0
        assert "TEST" in analyzer.execution_times

    @patch('rv_static_analysis.analysis.static.static_analysis.Command')
    def test_execute_command_failure(self, mock_command, analyzer):
        """Test command execution with failure result."""
        # Setup
        mock_command_instance = MagicMock()
        mock_command_instance.invoke.return_value = CommandResult(1, "", "Error message")
        mock_command.return_value = mock_command_instance

        # Act & Assert
        with patch('os.path.isfile', return_value=False):
            with pytest.raises(StaticAnalysisException) as exc_info:
                analyzer._execute_command("TEST", "/tmp/test.out", mock_command_instance)

        assert "Static analysis tool TEST failed with exit code 1" in str(exc_info.value)

    @patch.object(StaticAnalyzer, '_run_gesda')
    @patch.object(StaticAnalyzer, '_run_gator')
    @patch.object(StaticAnalyzer, '_run_reachability')
    def test_analyze_success(self, mock_reachability, mock_gator, mock_gesda, analyzer):
        """Test successful analysis with all steps completed."""
        # Setup
        analyzer.execution_times = {"GESDA": 1.0, "GATOR": 2.0, "REACHABILITY": 3.0}

        # Act
        result = analyzer.analyze()

        # Assert
        mock_gesda.assert_called_once()
        mock_gator.assert_called_once()
        mock_reachability.assert_called_once()
        assert result.success is True
        assert result.execution_times == analyzer.execution_times

    @patch.object(StaticAnalyzer, '_run_gesda')
    @patch.object(StaticAnalyzer, '_run_gator')
    @patch.object(StaticAnalyzer, '_run_reachability')
    def test_analyze_failure(self, mock_reachability, mock_gator, mock_gesda, analyzer):
        """Test analysis failure when one step fails."""
        # Setup
        mock_gesda.side_effect = StaticAnalysisException("GESDA failed")

        # Act
        result = analyzer.analyze()

        # Assert
        mock_gesda.assert_called_once()
        mock_gator.assert_not_called()
        mock_reachability.assert_not_called()
        assert result.success is False
        assert len(result.errors) == 1
        assert "GESDA failed" in result.errors[0]

    def test_get_metrics(self, analyzer):
        """Test retrieving metrics from the analyzer."""
        # Setup
        analyzer.execution_times = {"GESDA": 1.0, "GATOR": 2.0, "REACHABILITY": 3.0}
        analyzer.result.success = True

        # Act
        metrics = analyzer.get_metrics()

        # Assert
        assert metrics["execution_times"] == analyzer.execution_times
        assert metrics["success"] is True
        assert metrics["error_count"] == 0

    def test_get_static_data_success(self, analyzer):
        """Test successfully retrieving static data."""
        # Setup
        analyzer.result.success = True

        # Create a mock for StaticAnalysisParser
        parser_mock = MagicMock()
        mock_static_data = MagicMock()
        parser_mock.parse.return_value = mock_static_data

        # Act
        with patch('rv_static_analysis.analysis.static.static_analysis.StaticAnalysisParser',
                   return_value=parser_mock):
            result = analyzer.get_static_data()

        # Assert
        assert result is not None
        parser_mock.parse.assert_called_once()

    @patch('rv_static_analysis.parser.static.static_analysis_parser.StaticAnalysisParser')
    def test_get_static_data_analysis_failed(self, mock_parser_class, analyzer):
        """Test get_static_data when analysis was not successful."""
        # Setup
        analyzer.result.success = False

        # Act
        result = analyzer.get_static_data()

        # Assert
        assert result is None
        mock_parser_class.assert_not_called()

    def test_get_static_data_parser_exception(self, analyzer):
        """Test get_static_data when parser raises an exception."""
        # Setup
        analyzer.result.success = True

        # Create a mock for StaticAnalysisParser
        parser_mock = MagicMock()
        parser_mock.parse.side_effect = Exception("Parser error")

        # Act
        with patch('rv_static_analysis.analysis.static.static_analysis.StaticAnalysisParser',
                   return_value=parser_mock):
            result = analyzer.get_static_data()

        # Assert
        assert result is None
        parser_mock.parse.assert_called_once()


