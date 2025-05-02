# tests/analysis/coverage/test_repository.py
# Import just what we need without triggering the whole module chain
# This is a better way to direct import, bypassing the circular imports
from importlib import import_module
from unittest.mock import Mock, MagicMock

import pytest


class TestCoverageRepository:
    """Tests for the CoverageRepository class"""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        """Set up test fixtures for each test"""
        # Create a mock LogcatRepository
        self.mock_logcat_repo = MagicMock()

        # Create a class mock that returns our instance mock
        self.mock_logcat_repo_class = MagicMock(return_value=self.mock_logcat_repo)

        # Monkeypatch the LogcatRepository to use our mock
        # This works better than patch() in many cases with import issues
        monkeypatch.setattr('rvandroid.domain.coverage.LogcatRepository',
                            self.mock_logcat_repo_class)

        # Now import the module under test safely
        # We use a direct import approach to bypass circular dependencies
        module = import_module('rvandroid.analysis.coverage.repository')
        self.CoverageRepository = module.CoverageRepository

        # Create the repository for testing and explicitly set our mock
        self.repo = self.CoverageRepository()
        self.repo.repository = self.mock_logcat_repo

    def test_initialization(self):
        """Test that CoverageRepository initializes correctly"""
        # We're manually injecting our mock, so we can check it's used
        assert self.repo is not None
        assert self.repo.repository == self.mock_logcat_repo

    def test_classes_property(self):
        """Test the classes property"""
        # Setup expected data
        mock_classes = {"TestClass1": "ClassData1", "TestClass2": "ClassData2"}
        self.mock_logcat_repo.classes = mock_classes

        # Test the property
        assert self.repo.classes == mock_classes

    def test_register_method_call(self):
        """Test registering a method call"""
        # Create a mock coverage log
        mock_coverage_log = Mock()

        # Call the method
        self.repo.register_method_call(mock_coverage_log)

        # Verify the call was forwarded
        self.mock_logcat_repo.register_method_call.assert_called_once_with(mock_coverage_log)

    def test_register_error(self):
        """Test registering an error"""
        # Create a mock error log
        mock_error_log = Mock()

        # Call the method
        self.repo.register_error(mock_error_log)

        # Verify the call was forwarded
        self.mock_logcat_repo.register_rv_error.assert_called_once_with(mock_error_log)

    def test_get_metrics(self):
        """Test getting metrics with default parameters"""
        # Setup expected data
        expected_metrics = {"method_coverage": 75.0}
        metrics_mock = Mock()
        metrics_mock.to_dict.return_value = expected_metrics
        self.mock_logcat_repo.calculate_metrics.return_value = metrics_mock

        # Get metrics
        metrics = self.repo.get_metrics()

        # Verify results
        assert metrics == expected_metrics
        self.mock_logcat_repo.calculate_metrics.assert_called_once_with(True)

    def test_get_metrics_with_restrict_to_static_false(self):
        """Test getting metrics with custom parameters"""
        # Setup expected data
        expected_metrics = {"method_coverage": 65.0}
        metrics_mock = Mock()
        metrics_mock.to_dict.return_value = expected_metrics
        self.mock_logcat_repo.calculate_metrics.return_value = metrics_mock

        # Get metrics
        metrics = self.repo.get_metrics(restrict_to_static=False)

        # Verify results
        assert metrics == expected_metrics
        self.mock_logcat_repo.calculate_metrics.assert_called_once_with(False)

    def test_get_error_count(self):
        """Test getting error count"""
        # Setup expected data
        expected_errors = {"error1", "error2", "error3"}
        self.mock_logcat_repo.unique_errors = expected_errors

        # Get error count
        error_count = self.repo.get_error_count()

        # Verify results
        assert error_count == 3

    def test_get_method_call_count(self):
        """Test getting method call count"""
        # Setup expected data
        metrics_mock = Mock()
        metrics_mock.called_methods = 42
        self.mock_logcat_repo.calculate_metrics.return_value = metrics_mock

        # Get method call count
        call_count = self.repo.get_method_call_count()

        # Verify results
        assert call_count == 42
        self.mock_logcat_repo.calculate_metrics.assert_called_once()

    def test_get_underlying_repository(self):
        """Test getting the underlying repository"""
        # Get the underlying repository
        underlying_repo = self.repo.get_underlying_repository()

        # Verify it's the same as our mock
        assert underlying_repo == self.mock_logcat_repo

    def test_errors_property(self):
        """Test accessing the errors property"""
        # Setup expected data
        expected_errors = ["Error1", "Error2", "Error3"]
        self.mock_logcat_repo.errors = expected_errors

        # Access errors property
        errors = self.repo.errors

        # Verify results
        assert errors == expected_errors

    def test_calculate_metrics(self):
        """Test the calculate_metrics method"""
        # Setup expected data
        metrics_mock = Mock()
        self.mock_logcat_repo.calculate_metrics.return_value = metrics_mock

        # Call calculate_metrics
        result = self.repo.calculate_metrics()

        # Verify results
        assert result == metrics_mock
        self.mock_logcat_repo.calculate_metrics.assert_called_once_with(True)

    def test_calculate_metrics_with_restrict_to_static_false(self):
        """Test the calculate_metrics method with custom parameters"""
        # Setup expected data
        metrics_mock = Mock()
        self.mock_logcat_repo.calculate_metrics.return_value = metrics_mock

        # Call calculate_metrics
        result = self.repo.calculate_metrics(restrict_to_static=False)

        # Verify results
        assert result == metrics_mock
        self.mock_logcat_repo.calculate_metrics.assert_called_once_with(False)
