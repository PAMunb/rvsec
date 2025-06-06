import os
from unittest.mock import patch, MagicMock

import pytest

from rv_android_core.app import App


class TestApp:
    """Tests for the App class"""

    @pytest.fixture
    def mock_apk(self):
        """Create a mock APK object"""
        mock = MagicMock()
        mock.get_package.return_value = "com.example.testapp"
        mock.get_effective_target_sdk_version.return_value = 30
        mock.get_permissions.return_value = ["android.permission.INTERNET", "android.permission.CAMERA"]
        mock.get_min_sdk_version.return_value = 24
        return mock

    @pytest.fixture
    def sample_app_path(self):
        """Sample app path for testing"""
        return "/path/to/testapp.apk"

    def test_app_initialization(self, sample_app_path, mock_apk):
        """Test App constructor"""
        with patch('rv_android_core.app.APK', return_value=mock_apk) as mock_apk_class:
            app = App(sample_app_path)

            # Verify APK was created with correct path
            mock_apk_class.assert_called_once_with(os.path.join(sample_app_path))

            # Verify properties were set correctly
            assert app.path == os.path.join(sample_app_path)
            assert app.name == "testapp.apk"
            assert app.package_name == "com.example.testapp"
            assert app.sdk_target == 30
            assert app.permissions == ["android.permission.INTERNET", "android.permission.CAMERA"]
            assert app.min_api == 24

    def test_app_initialization_with_none_path(self):
        """Test App constructor with None path"""
        with pytest.raises(AssertionError):
            App(None)

    def test_app_initialization_with_absolute_path(self, mock_apk):
        """Test App constructor with absolute path"""
        with patch('rv_android_core.app.APK', return_value=mock_apk), \
                patch('os.path.basename', return_value="testapp.apk"):
            # Unix-style absolute path
            app = App("/absolute/path/to/testapp.apk")
            assert app.name == "testapp.apk"

            # Windows-style absolute path (if on Windows)
            app = App("C:\\absolute\\path\\to\\testapp.apk")
            assert app.name == "testapp.apk"

    def test_app_initialization_with_relative_path(self, mock_apk):
        """Test App constructor with relative path"""
        with patch('rv_android_core.app.APK', return_value=mock_apk):
            app = App("relative/path/to/testapp.apk")
            assert app.path == os.path.join("relative/path/to/testapp.apk")
            assert app.name == "testapp.apk"

    def test_app_initialization_with_empty_path(self):
        """Test App constructor with empty path"""
        with pytest.raises(AssertionError):
            App(None)

        # For empty string, we should mock the APK to avoid FileNotFoundError
        with patch('rv_android_core.app.APK', side_effect=Exception("Invalid APK")), \
                pytest.raises(Exception) as excinfo:
            App("")
        assert "Invalid APK" in str(excinfo.value)

    def test_app_initialization_with_invalid_apk(self):
        """Test App constructor with invalid APK"""
        with patch('rv_android_core.app.APK', side_effect=Exception("Invalid APK")):
            with pytest.raises(Exception) as excinfo:
                App("/path/to/invalid.apk")
            assert "Invalid APK" in str(excinfo.value)
