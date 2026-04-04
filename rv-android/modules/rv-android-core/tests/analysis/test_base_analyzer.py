"""
Unit tests for the base analyzer module.

This module contains tests for the BaseAnalyzer and BaseRepository abstract
classes that serve as foundation for dynamic analysis components.
"""

from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.analysis.base_analyzer import BaseAnalyzer, BaseRepository
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.util.logging.manager import LoggingManager


class ConcreteAnalyzer(BaseAnalyzer[str]):
    """Concrete implementation of BaseAnalyzer for testing purposes."""

    def _initialize_from_static_data(self) -> None:
        """Initialize with static data."""
        self.initialized = True

    def analyze(self, data: Any) -> str:
        """Analyze data and return string result."""
        return f"Analyzed: {data}"

    def get_metrics(self) -> Dict[str, Any]:
        """Get test metrics."""
        return {"test_metric": 42}


class ConcreteRepository(BaseRepository):
    """Concrete implementation of BaseRepository for testing purposes."""

    def __init__(self, repository_name: str):
        """Initialize the repository."""
        super().__init__(repository_name)
        self.data = {}

    def add_data(self, key: str, value: Any) -> None:
        """Add data to the repository."""
        self.data[key] = value

    def get_data(self, key: str) -> Optional[Any]:
        """Get data from the repository."""
        return self.data.get(key)


@pytest.fixture
def mock_logging_manager():
    """Fixture providing a mock logging manager."""
    mock_manager = MagicMock(spec=LoggingManager)
    mock_logger = MagicMock()
    mock_manager.get_logger.return_value = mock_logger
    return mock_manager


@pytest.fixture
def mock_static_data():
    """Fixture providing mock static analysis data."""
    return MagicMock(spec=StaticAnalysisData)


class TestBaseAnalyzer:
    """Tests for the BaseAnalyzer abstract class."""

    def test_initialization_without_static_data(self, mock_logging_manager):
        """Test initialization of analyzer without static data."""
        with patch(
            "rv_android_core.analysis.base_analyzer.LoggingManager.get_instance",
            return_value=mock_logging_manager,
        ):
            analyzer = ConcreteAnalyzer("test_analyzer")

            # Verify initialization
            assert analyzer.analyzer_name == "test_analyzer"
            assert analyzer.static_data is None

            # Verify logging setup
            mock_logging_manager.get_logger.assert_called_once()
            assert "test_analyzer" in mock_logging_manager.get_logger.call_args[0][0]

    def test_initialization_with_static_data(
        self, mock_logging_manager, mock_static_data
    ):
        """Test initialization of analyzer with static data."""
        with patch(
            "rv_android_core.analysis.base_analyzer.LoggingManager.get_instance",
            return_value=mock_logging_manager,
        ):
            analyzer = ConcreteAnalyzer("test_analyzer", mock_static_data)

            # Verify initialization
            assert analyzer.analyzer_name == "test_analyzer"
            assert analyzer.static_data is mock_static_data
            assert hasattr(analyzer, "initialized") and analyzer.initialized

    def test_analyze_method(self, mock_logging_manager):
        """Test the analyze method implementation."""
        with patch(
            "rv_android_core.analysis.base_analyzer.LoggingManager.get_instance",
            return_value=mock_logging_manager,
        ):
            analyzer = ConcreteAnalyzer("test_analyzer")
            result = analyzer.analyze("test_data")

            assert result == "Analyzed: test_data"

    def test_get_metrics_method(self, mock_logging_manager):
        """Test the get_metrics method implementation."""
        with patch(
            "rv_android_core.analysis.base_analyzer.LoggingManager.get_instance",
            return_value=mock_logging_manager,
        ):
            analyzer = ConcreteAnalyzer("test_analyzer")
            metrics = analyzer.get_metrics()

            assert metrics == {"test_metric": 42}

    def test_log_processing_summary(self, mock_logging_manager):
        """Test the log_processing_summary method."""
        with patch(
            "rv_android_core.analysis.base_analyzer.LoggingManager.get_instance",
            return_value=mock_logging_manager,
        ):
            analyzer = ConcreteAnalyzer("test_analyzer")
            analyzer.log_processing_summary("items", 10)

            # Verify logging call
            analyzer.logger.info.assert_called_once_with("Processed 10 items")


class TestBaseRepository:
    """Tests for the BaseRepository abstract class."""

    def test_initialization(self, mock_logging_manager):
        """Test initialization of repository."""
        with patch(
            "rv_android_core.analysis.base_analyzer.LoggingManager.get_instance",
            return_value=mock_logging_manager,
        ):
            repo = ConcreteRepository("test_repo")

            # Verify initialization
            assert repo.repository_name == "test_repo"

            # Verify logging setup
            mock_logging_manager.get_logger.assert_called_once()
            assert "test_repo" in mock_logging_manager.get_logger.call_args[0][0]

    def test_log_storage_summary(self, mock_logging_manager):
        """Test the log_storage_summary method."""
        with patch(
            "rv_android_core.analysis.base_analyzer.LoggingManager.get_instance",
            return_value=mock_logging_manager,
        ):
            repo = ConcreteRepository("test_repo")
            repo.log_storage_summary("items", 5)

            # Verify logging call
            repo.logger.info.assert_called_once_with("Storing 5 items")

    def test_repository_functionality(self, mock_logging_manager):
        """Test concrete repository implementation functionality."""
        with patch(
            "rv_android_core.analysis.base_analyzer.LoggingManager.get_instance",
            return_value=mock_logging_manager,
        ):
            repo = ConcreteRepository("test_repo")

            # Add and retrieve data
            repo.add_data("key1", "value1")
            repo.add_data("key2", 42)

            assert repo.get_data("key1") == "value1"
            assert repo.get_data("key2") == 42
            assert repo.get_data("non_existent") is None
