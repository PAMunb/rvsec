from unittest.mock import MagicMock

import pytest
from rv_android_core.domain.classes import Classes
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.window import Windows
from rv_android_core.domain.wtg import WindowTransitionGraph


class TestStaticAnalysisData:
    """Tests for the StaticAnalysisData class"""

    @pytest.fixture
    def mock_classes(self):
        """Create a mock Classes instance"""
        return MagicMock(spec=Classes)

    @pytest.fixture
    def mock_windows(self):
        """Create a mock Windows instance"""
        return MagicMock(spec=Windows)

    @pytest.fixture
    def mock_wtg(self):
        """Create a mock WindowTransitionGraph instance"""
        return MagicMock(spec=WindowTransitionGraph)

    def test_static_analysis_data_initialization(
        self, mock_classes, mock_windows, mock_wtg
    ):
        """Test StaticAnalysisData constructor"""
        static_data = StaticAnalysisData(mock_classes, mock_windows, mock_wtg)

        assert static_data.classes == mock_classes
        assert static_data.windows == mock_windows
        assert static_data.wtg == mock_wtg

    def test_static_analysis_data_access(self, mock_classes, mock_windows, mock_wtg):
        """Test accessing properties of StaticAnalysisData"""
        # Setup mock methods
        mock_classes.get_classes.return_value = ["TestClass1", "TestClass2"]
        mock_windows.get_window.return_value = "TestWindow"

        # Create instance
        static_data = StaticAnalysisData(mock_classes, mock_windows, mock_wtg)

        # Access properties via mock methods
        classes_list = static_data.classes.get_classes()
        window = static_data.windows.get_window("TestWindow")

        # Verify
        assert classes_list == ["TestClass1", "TestClass2"]
        assert window == "TestWindow"
        mock_classes.get_classes.assert_called_once()
        mock_windows.get_window.assert_called_once_with("TestWindow")
