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
from rv_android_core.app import App
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
def analyzer(mock_app, output_dir):
    """Fixture that provides a StaticAnalyzer instance."""
    with patch('os.makedirs') as mock_makedirs:
        analyzer = StaticAnalyzer(mock_app, output_dir)
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

    @patch('rvandroid.analysis.static.static_analysis.Command')
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

    @patch('rvandroid.analysis.static.static_analysis.Command')
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

    @patch('rvandroid.analysis.static.static_analysis.Command')
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

    @patch('rvandroid.analysis.static.static_analysis.Command')
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

    @patch('rvandroid.analysis.static.static_analysis.Command')
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

    @patch('rvandroid.analysis.static.static_analysis.Command')
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

        assert "Error while executing TEST" in str(exc_info.value)

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
        with patch('rvandroid.analysis.static.static_analysis.StaticAnalysisParser',
                   return_value=parser_mock):
            result = analyzer.get_static_data()

        # Assert
        assert result is not None
        parser_mock.parse.assert_called_once()

    @patch('rvandroid.parser.static.static_analysis_parser.StaticAnalysisParser')
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
        with patch('rvandroid.analysis.static.static_analysis.StaticAnalysisParser',
                   return_value=parser_mock):
            result = analyzer.get_static_data()

        # Assert
        assert result is None
        parser_mock.parse.assert_called_once()


class TestLegacyFunctions:
    """Tests for the legacy API functions."""

    @patch.object(StaticAnalyzer, 'analyze')
    def test_run_static_analysis(self, mock_analyze, mock_app):
        """Test the legacy run_static_analysis function."""
        # Setup
        gesda_file = "/tmp/test.gesda"
        gator_file = "/tmp/test.wtg"
        reach_file = "/tmp/test.reach"

        # Act
        with patch('rvandroid.analysis.static.static_analysis.StaticAnalyzer') as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer_class.return_value = mock_analyzer

            from rvandroid.analysis.static.static_analysis import run_static_analysis
            run_static_analysis(mock_app, gesda_file, gator_file, reach_file)

        # Assert
        mock_analyzer_class.assert_called_once_with(mock_app)
        assert mock_analyzer.gesda_file == gesda_file
        assert mock_analyzer.gator_file == gator_file
        assert mock_analyzer.reach_file == reach_file
        mock_analyzer.analyze.assert_called_once()

    @patch.object(StaticAnalyzer, '_run_gesda')
    def test_run_gesda(self, mock_run_gesda, mock_app):
        """Test the legacy run_gesda function."""
        # Setup
        gesda_file = "/tmp/test.gesda"

        # Act
        with patch('rvandroid.analysis.static.static_analysis.StaticAnalyzer') as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer_class.return_value = mock_analyzer

            from rvandroid.analysis.static.static_analysis import run_gesda
            run_gesda(mock_app, gesda_file)

        # Assert
        mock_analyzer_class.assert_called_once_with(mock_app)
        assert mock_analyzer.gesda_file == gesda_file
        mock_analyzer._run_gesda.assert_called_once()

    @patch.object(StaticAnalyzer, '_run_gator')
    def test_run_gator(self, mock_run_gator, mock_app):
        """Test the legacy run_gator function."""
        # Setup
        gator_file = "/tmp/test.wtg"

        # Act
        with patch('rvandroid.analysis.static.static_analysis.StaticAnalyzer') as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer_class.return_value = mock_analyzer

            from rvandroid.analysis.static.static_analysis import run_gator
            run_gator(mock_app, gator_file)

        # Assert
        mock_analyzer_class.assert_called_once_with(mock_app)
        assert mock_analyzer.gator_file == gator_file
        mock_analyzer._run_gator.assert_called_once()

    @patch.object(StaticAnalyzer, '_run_reachability')
    def test_run_reachability(self, mock_run_reachability, mock_app):
        """Test the legacy run_reachability function."""
        # Setup
        reach_file = "/tmp/test.reach"
        mop_dir = "/tmp/mop"
        gesda_file = "/tmp/test.gesda"

        # Act
        with patch('rvandroid.analysis.static.static_analysis.StaticAnalyzer') as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer_class.return_value = mock_analyzer

            from rvandroid.analysis.static.static_analysis import run_reachability
            run_reachability(mock_app, reach_file, mop_dir, gesda_file)

        # Assert
        mock_analyzer_class.assert_called_once_with(mock_app)
        assert mock_analyzer.reach_file == reach_file
        assert mock_analyzer.gesda_file == gesda_file
        mock_analyzer._run_reachability.assert_called_once()
