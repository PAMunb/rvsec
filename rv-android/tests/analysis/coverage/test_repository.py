import os
import sys
import logging

# Modify sys.path to ensure correct importing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import pytest
from unittest.mock import MagicMock, patch


def create_mock_metrics():
    """Create a mock metrics object with predefined values."""
    mock_metrics = MagicMock()
    mock_metrics.to_dict.return_value = {
        'method_coverage': 50.0,
        'activity_coverage': 30.0,
        'mop_method_coverage': 20.0,
        'unique_errors': 2
    }
    mock_metrics.called_methods = 42
    return mock_metrics


class TestCoverageRepository:
    @pytest.fixture
    def mock_logcat_repository(self):
        """Create a mock LogcatRepository."""
        mock_repo = MagicMock()
        mock_repo.classes = {}
        mock_repo.errors = []
        mock_repo.unique_errors = set()
        mock_repo.calculate_metrics.return_value = create_mock_metrics()
        return mock_repo

    @pytest.fixture
    def mock_logging_manager(self):
        """Create a mock LoggingManager."""
        mock_manager = MagicMock()
        mock_logger = MagicMock()
        mock_manager.get_logger.return_value = mock_logger
        return mock_manager

    @pytest.fixture
    def coverage_repository(self, mock_logcat_repository, mock_logging_manager):
        """Create a CoverageRepository with mock dependencies."""
        # Dynamically patch dependencies
        with patch('rvandroid.analysis.coverage.repository.LogcatRepository',
                   return_value=mock_logcat_repository), \
                patch('rvandroid.analysis.coverage.repository.LoggingManager.get_instance',
                      return_value=mock_logging_manager):
            # Import CoverageRepository after patching
            from rvandroid.analysis.coverage.repository import CoverageRepository
            return CoverageRepository()

    def test_init(self, coverage_repository):
        """Test repository initialization."""
        assert hasattr(coverage_repository, 'repository')
        assert hasattr(coverage_repository, 'logger')

    def test_classes_property(self, coverage_repository, mock_logcat_repository):
        """Test classes property delegation."""
        assert coverage_repository.classes == mock_logcat_repository.classes

    def test_register_method_call(self, coverage_repository):
        """Test registering a method call."""
        mock_coverage_log = MagicMock()
        coverage_repository.register_method_call(mock_coverage_log)

    def test_register_error(self, coverage_repository):
        """Test registering an error."""
        mock_error_log = MagicMock()
        coverage_repository.register_error(mock_error_log)

    def test_get_metrics(self, coverage_repository):
        """Test getting metrics."""
        metrics = coverage_repository.get_metrics()

        expected_metrics = {
            'method_coverage': 50.0,
            'activity_coverage': 30.0,
            'mop_method_coverage': 20.0,
            'unique_errors': 2
        }
        assert metrics == expected_metrics

    def test_get_error_count(self, coverage_repository, mock_logcat_repository):
        """Test getting error count."""
        mock_logcat_repository.unique_errors = {'error1', 'error2'}
        assert coverage_repository.get_error_count() == 2

    def test_get_method_call_count(self, coverage_repository):
        """Test getting method call count."""
        assert coverage_repository.get_method_call_count() == 42

    def test_get_underlying_repository(self, coverage_repository, mock_logcat_repository):
        """Test getting the underlying repository."""
        assert coverage_repository.get_underlying_repository() == mock_logcat_repository

    def test_calculate_metrics(self, coverage_repository):
        """Test calculating metrics directly."""
        result = coverage_repository.calculate_metrics(False)
        expected_metrics = {
            'method_coverage': 50.0,
            'activity_coverage': 30.0,
            'mop_method_coverage': 20.0,
            'unique_errors': 2
        }
        assert result.to_dict() == expected_metrics

    def test_errors_property(self, coverage_repository, mock_logcat_repository):
        """Test errors property delegation."""
        mock_errors = [MagicMock(), MagicMock()]
        mock_logcat_repository.errors = mock_errors
        assert coverage_repository.errors == mock_errors

    def test_logger_creation(self, coverage_repository, mock_logging_manager):
        """Test that a logger is created using LoggingManager."""
        # Verify that get_logger was called with correct parameters
        mock_logging_manager.get_logger.assert_called_once_with(
            'analysis.coverage.repository',
            {'component': 'CoverageRepository'}
        )

        # Verify that the logger attribute is set
        assert hasattr(coverage_repository, 'logger')