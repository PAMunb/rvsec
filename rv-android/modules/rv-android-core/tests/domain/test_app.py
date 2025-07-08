import os
from unittest.mock import patch, MagicMock

import pytest

from rv_android_core.domain.app import App
from rv_android_core.util.error.exceptions import ConfigurationError


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
        """Test App constructor with positional argument (backward compatibility)"""
        with patch('rv_android_core.domain.app.APK', return_value=mock_apk) as mock_apk_class, \
             patch('os.path.isfile', return_value=True):
            app = App(sample_app_path)  # Using positional argument like original code

            # Verify APK was created with correct path
            mock_apk_class.assert_called_once_with(sample_app_path)

            # Verify properties were set correctly
            assert app.path == os.path.abspath(sample_app_path)
            assert app.name == "testapp.apk"
            assert app.package_name == "com.example.testapp"
            assert app.sdk_target == 30
            assert app.permissions == ["android.permission.INTERNET", "android.permission.CAMERA"]
            assert app.min_api == 24

    def test_app_initialization_with_none_path(self):
        """Test App constructor with None path"""
        with pytest.raises(ValueError):
            App(None)

    def test_app_initialization_with_absolute_path(self, mock_apk):
        """Test App constructor with absolute path"""
        with patch('rv_android_core.domain.app.APK', return_value=mock_apk), \
             patch('os.path.isfile', return_value=True):
            # Unix-style absolute path
            app = App("/absolute/path/to/testapp.apk")
            assert app.name == "testapp.apk"

    def test_app_initialization_with_relative_path(self, mock_apk):
        """Test App constructor with relative path"""
        with patch('rv_android_core.domain.app.APK', return_value=mock_apk), \
             patch('os.path.isfile', return_value=True):
            app = App("relative/path/to/testapp.apk")
            assert app.path == os.path.abspath("relative/path/to/testapp.apk")
            assert app.name == "testapp.apk"

    def test_app_initialization_with_empty_path(self):
        """Test App constructor with empty path"""
        with pytest.raises(ValueError):
            App("")

    def test_app_initialization_with_invalid_apk(self):
        """Test App constructor with invalid APK"""
        with patch('os.path.isfile', return_value=True), \
             patch('rv_android_core.domain.app.APK', side_effect=Exception("Invalid APK")):
            with pytest.raises(ConfigurationError) as excinfo:
                App("/path/to/invalid.apk")
            assert "Invalid APK file" in str(excinfo.value)

    def test_app_initialization_file_not_found(self):
        """Test App constructor with non-existent file"""
        with pytest.raises(ConfigurationError) as excinfo:
            App("/path/to/nonexistent.apk")
        assert "APK file not found" in str(excinfo.value)

    def test_app_initialization_non_apk_file(self):
        """Test App constructor with non-APK file"""
        with patch('os.path.isfile', return_value=True):
            with pytest.raises(ConfigurationError) as excinfo:
                App("/path/to/notapk.txt")
            assert "File is not an APK" in str(excinfo.value)

    def test_app_initialization_with_validation_disabled(self, mock_apk):
        """Test App constructor with validation disabled"""
        with patch('rv_android_core.domain.app.APK', return_value=mock_apk), \
             patch('os.path.isfile', return_value=True):
            app = App("/path/to/testapp.apk", validate_on_init=False)
            assert app.app_path == "/path/to/testapp.apk"
            # Properties should still work when accessed (will trigger validation)
            assert app.package_name == "com.example.testapp"

    def test_app_initialization_named_parameters(self, mock_apk):
        """Test App constructor with named parameters (new Pydantic style)"""
        with patch('rv_android_core.domain.app.APK', return_value=mock_apk), \
             patch('os.path.isfile', return_value=True):
            app = App(app_path="/path/to/testapp.apk", validate_on_init=True)
            assert app.app_path == "/path/to/testapp.apk"
            assert app.package_name == "com.example.testapp"
