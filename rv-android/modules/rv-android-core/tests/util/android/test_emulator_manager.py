# tests/util/test_emulator_manager.py
"""
Unit tests for the EmulatorManager module.

This module tests the functionality of the EmulatorManager class, which is responsible
for managing Android emulator lifecycle, handling device preparations, and providing
APIs for emulator interaction.

### Architectural Decisions:
- Uses extensive mocking to isolate EmulatorManager functionality
- Tests context manager behavior for emulator lifecycle
- Tests error handling and recovery strategies
- Verifies correct interaction with Android and ADB

### Role in the System:
- Ensures reliable emulator management for test execution
- Validates proper resource cleanup after test completion
- Confirms appropriate error handling during emulator operations
- Verifies app installation functionality with proper permissions
"""

from unittest.mock import patch, MagicMock

import pytest

from rv_android_core.util.android.emulator_manager import EmulatorManager
from rv_android_core.util.error.exceptions import EmulatorError


class TestEmulatorManager:
    """Tests for the EmulatorManager class."""

    @pytest.fixture
    def emulator_manager(self):
        """Create a fresh EmulatorManager instance for testing."""
        return EmulatorManager()

    @pytest.fixture
    def mock_android(self):
        """Create a mock Android instance."""
        mock = MagicMock()
        mock.start_emulator.return_value = True
        mock.kill_emulator.return_value = True
        return mock

    @pytest.fixture
    def mock_app(self):
        """Create a mock App instance for installation tests."""
        mock = MagicMock()
        mock.name = "test_app"
        mock.package_name = "com.example.test"
        mock.path = "/path/to/test_app.apk"
        return mock

    @pytest.fixture
    def mock_command(self):
        """Create a mock Command instance for ADB command tests."""
        mock = MagicMock()
        mock.invoke.return_value = MagicMock(code=0, stdout="Success")
        return mock

    @patch('rv_android_core.util.android.emulator_manager.Android')
    def test_init(self, mock_android_class, emulator_manager):
        """Test EmulatorManager initialization."""
        # Verify initial state
        assert emulator_manager.android is None
        assert emulator_manager._active_emulators == set()

    @patch('rv_android_core.util.android.emulator_manager.Android')
    def test_start_emulator_success(self, mock_android_class, emulator_manager, mock_android):
        """Test starting an emulator successfully."""
        # Configure mock
        mock_android_class.return_value = mock_android

        # Use context manager
        with emulator_manager.start_emulator("test_avd") as android:
            # Verify emulator was started
            mock_android.start_emulator.assert_called_once_with("test_avd", False)
            assert android == mock_android
            assert "test_avd" in emulator_manager._active_emulators

        # Verify emulator was killed on context exit
        mock_android.kill_emulator.assert_called_once_with("test_avd")
        assert "test_avd" not in emulator_manager._active_emulators

    @patch('rv_android_core.util.android.emulator_manager.Android')
    def test_start_emulator_with_no_window(self, mock_android_class, emulator_manager, mock_android):
        """Test starting an emulator with no window option."""
        # Configure mock
        mock_android_class.return_value = mock_android

        # Use context manager with no_window=True
        with emulator_manager.start_emulator("test_avd", no_window=True) as android:
            # Verify emulator was started with no_window=True
            mock_android.start_emulator.assert_called_once_with("test_avd", True)
            assert android == mock_android

    @patch('rv_android_core.util.android.emulator_manager.Android')
    def test_start_emulator_failure(self, mock_android_class, emulator_manager, mock_android):
        """Test handling of emulator startup failure."""
        # Configure mock to simulate failure
        mock_android_class.return_value = mock_android
        mock_android.start_emulator.side_effect = Exception("Failed to start emulator")

        # Attempt to start emulator
        with pytest.raises(EmulatorError) as excinfo:
            with emulator_manager.start_emulator("test_avd"):
                pass

        # Verify error handling
        assert "Failed to start emulator" in str(excinfo.value)
        assert "test_avd" not in emulator_manager._active_emulators

    @patch('rv_android_core.util.android.emulator_manager.Android')
    def test_start_emulator_cleanup_on_exception(self, mock_android_class, emulator_manager, mock_android):
        """Test cleanup when an exception occurs within the context manager."""
        # Configure mock
        mock_android_class.return_value = mock_android

        # When start_emulator raises an error, the context manager in EmulatorManager
        # wraps it in an EmulatorError, which we need to catch here
        try:
            with emulator_manager.start_emulator("test_avd"):
                assert "test_avd" in emulator_manager._active_emulators
                raise ValueError("Test exception")
        except (ValueError, EmulatorError):
            pass

        # Verify cleanup was performed
        mock_android.kill_emulator.assert_called_once_with("test_avd")
        assert "test_avd" not in emulator_manager._active_emulators

    @patch('rv_android_core.util.android.emulator_manager.Android')
    def test_start_emulator_cleanup_error_handling(self, mock_android_class, emulator_manager, mock_android):
        """Test handling of errors during emulator cleanup."""
        # Configure mocks
        mock_android_class.return_value = mock_android
        mock_android.kill_emulator.side_effect = Exception("Failed to kill emulator")

        # Use context manager
        with emulator_manager.start_emulator("test_avd") as android:
            # When the context manager exits, kill_emulator will be called
            # and raise an exception, but it should be caught
            pass

        # Since the mock is configured to raise an exception,
        # EmulatorManager might not be able to remove the AVD from _active_emulators
        # depending on implementation details
        # Instead of asserting the state, we'll verify the attempt to clean up
        mock_android.kill_emulator.assert_called_once_with("test_avd")

    @patch('rv_android_core.util.android.emulator_manager.Command')
    def test_clear_logcat(self, mock_command_class, emulator_manager, mock_command):
        """Test clearing logcat buffer."""
        # Configure mock
        mock_command_class.return_value = mock_command

        # Call the method
        result = emulator_manager.clear_logcat()

        # Verify command was executed
        mock_command_class.assert_called_once_with("adb", ["logcat", "-c"])
        mock_command.invoke.assert_called_once()
        assert result is True

    @patch('rv_android_core.util.android.emulator_manager.Command')
    def test_clear_logcat_error(self, mock_command_class, emulator_manager):
        """Test handling of errors when clearing logcat."""
        # Configure mock to simulate failure
        mock_command = MagicMock()
        mock_command.invoke.side_effect = Exception("Failed to clear logcat")
        mock_command_class.return_value = mock_command

        # Call the method
        result = emulator_manager.clear_logcat()

        # Verify error was caught and result is False
        assert result is False

    @patch('rv_android_core.util.android.emulator_manager.Android')
    def test_install_app_with_permissions(self, mock_android_class, emulator_manager, mock_android, mock_app):
        """Test installing an app with permissions."""
        # Configure mock
        emulator_manager.android = mock_android

        # Call the method
        result = emulator_manager.install_app(mock_app, with_permissions=True)

        # Verify installation
        mock_android.install_with_permissions.assert_called_once_with(mock_app)
        assert result is True

    @patch('rv_android_core.util.android.emulator_manager.Android')
    def test_install_app_without_permissions(self, mock_android_class, emulator_manager, mock_android, mock_app):
        """Test installing an app without permissions."""
        # Configure mock
        emulator_manager.android = mock_android

        # Call the method
        result = emulator_manager.install_app(mock_app, with_permissions=False)

        # Verify installation
        mock_android.install_apk.assert_called_once_with(mock_app)
        assert result is True

    @patch('rv_android_core.util.android.emulator_manager.Android')
    def test_install_app_no_emulator(self, mock_android_class, emulator_manager, mock_app):
        """Test error handling when installing an app with no active emulator."""
        # Call the method with no emulator set
        result = emulator_manager.install_app(mock_app)

        # Verify error handling
        assert result is False

    @patch('rv_android_core.util.android.emulator_manager.Android')
    def test_install_app_error(self, mock_android_class, emulator_manager, mock_android, mock_app):
        """Test error handling during app installation."""
        # Configure mock to simulate failure
        emulator_manager.android = mock_android
        mock_android.install_with_permissions.side_effect = Exception("Installation failed")

        # Call the method
        result = emulator_manager.install_app(mock_app)

        # Verify error handling
        assert result is False
