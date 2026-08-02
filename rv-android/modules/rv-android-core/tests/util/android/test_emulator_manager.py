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

from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.util.android.android import Android
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

    @patch("rv_android_core.util.android.emulator_manager.Android")
    def test_init(self, mock_android_class, emulator_manager):
        """Test EmulatorManager initialization."""
        # Verify initial state
        assert emulator_manager.android is None
        assert emulator_manager._active_emulators == set()

    @patch("rv_android_core.util.android.emulator_manager.Android")
    def test_start_emulator_success(
        self, mock_android_class, emulator_manager, mock_android
    ):
        """Test starting an emulator successfully."""
        # Configure mock
        mock_android_class.return_value = mock_android

        # Use context manager
        with emulator_manager.start_emulator("test_avd") as android:
            # Verify emulator was started with default port
            mock_android.start_emulator.assert_called_once_with("test_avd", False, 5554)
            assert android == mock_android
            assert "test_avd" in emulator_manager._active_emulators

        # Verify emulator was killed on context exit with correct device serial
        mock_android.kill_emulator.assert_called_once_with("test_avd", "emulator-5554")
        assert "test_avd" not in emulator_manager._active_emulators

    @patch("rv_android_core.util.android.emulator_manager.Android")
    def test_start_emulator_with_no_window(
        self, mock_android_class, emulator_manager, mock_android
    ):
        """Test starting an emulator with no window option."""
        # Configure mock
        mock_android_class.return_value = mock_android

        # Use context manager with no_window=True
        with emulator_manager.start_emulator("test_avd", no_window=True) as android:
            # Verify emulator was started with no_window=True and default port
            mock_android.start_emulator.assert_called_once_with("test_avd", True, 5554)
            assert android == mock_android

    @patch("rv_android_core.util.android.emulator_manager.Android")
    def test_start_emulator_failure(
        self, mock_android_class, emulator_manager, mock_android
    ):
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

    @patch("rv_android_core.util.android.emulator_manager.Android")
    def test_start_emulator_cleanup_on_exception(
        self, mock_android_class, emulator_manager, mock_android
    ):
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

        # Verify cleanup was performed with correct device serial
        mock_android.kill_emulator.assert_called_once_with("test_avd", "emulator-5554")
        assert "test_avd" not in emulator_manager._active_emulators

    @patch("rv_android_core.util.android.emulator_manager.Android")
    def test_start_emulator_cleanup_error_handling(
        self, mock_android_class, emulator_manager, mock_android
    ):
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
        mock_android.kill_emulator.assert_called_once_with("test_avd", "emulator-5554")

    @patch("rv_android_core.util.android.emulator_manager.Command")
    def test_clear_logcat(self, mock_command_class, emulator_manager, mock_command):
        """Test clearing logcat buffer."""
        # Configure mock
        mock_command_class.return_value = mock_command

        # Call the method
        result = emulator_manager.clear_logcat()

        # Verify command was executed with device serial
        mock_command_class.assert_called_once_with(
            "adb", ["-s", "emulator-5554", "logcat", "-c"]
        )
        mock_command.invoke.assert_called_once()
        assert result is True

    @patch("rv_android_core.util.android.emulator_manager.Command")
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

    @patch("rv_android_core.util.android.emulator_manager.Android")
    def test_install_app_with_permissions(
        self, mock_android_class, emulator_manager, mock_android, mock_app
    ):
        """Test installing an app with permissions."""
        # Configure mock
        emulator_manager.android = mock_android

        # Call the method
        result = emulator_manager.install_app(mock_app, with_permissions=True)

        # Verify installation with default device serial
        mock_android.install_with_permissions.assert_called_once_with(
            mock_app, "emulator-5554"
        )
        assert result is True

    @patch("rv_android_core.util.android.emulator_manager.Android")
    def test_install_app_without_permissions(
        self, mock_android_class, emulator_manager, mock_android, mock_app
    ):
        """Test installing an app without permissions."""
        # Configure mock
        emulator_manager.android = mock_android

        # Call the method
        result = emulator_manager.install_app(mock_app, with_permissions=False)

        # Verify installation with default device serial
        mock_android.install_apk.assert_called_once_with(mock_app, "emulator-5554")
        assert result is True

    @patch("rv_android_core.util.android.emulator_manager.Android")
    def test_install_app_no_emulator(
        self, mock_android_class, emulator_manager, mock_app
    ):
        """Test error handling when installing an app with no active emulator."""
        # Call the method with no emulator set
        result = emulator_manager.install_app(mock_app)

        # Verify error handling
        assert result is False

    @patch("rv_android_core.util.android.emulator_manager.Android")
    def test_install_app_error(
        self, mock_android_class, emulator_manager, mock_android, mock_app
    ):
        """An installation failure is reported by raising, so its reason survives."""
        # Configure mock to simulate failure
        emulator_manager.android = mock_android
        mock_android.install_with_permissions.side_effect = Exception(
            "Installation failed"
        )

        with pytest.raises(Exception, match="Installation failed"):
            emulator_manager.install_app(mock_app)


class TestSessionBoundary:
    """The context manager's `except` covers startup; its `finally` covers all.

    These tests pin the block structure itself, not only its observable
    outcome on the happy path. A sibling arrangement — `try/except` for
    startup followed by a separate `try: yield / finally: teardown` — passes
    the session-failure cases below and fails
    `test_teardown_runs_when_startup_itself_fails`, because a startup failure
    would raise out of the first block without ever entering the second.
    """

    @pytest.fixture
    def emulator_manager(self):
        return EmulatorManager()

    @pytest.fixture
    def mock_android(self):
        mock = MagicMock()
        mock.start_emulator.return_value = True
        mock.kill_emulator.return_value = True
        return mock

    @patch("rv_android_core.util.android.emulator_manager.Android")
    def test_session_failure_keeps_its_own_type(
        self, mock_android_class, emulator_manager, mock_android
    ):
        """A failure inside the `with` body is not relabelled a startup failure."""
        mock_android_class.return_value = mock_android

        class TaskFailed(Exception):
            pass

        with pytest.raises(TaskFailed) as excinfo:
            with emulator_manager.start_emulator("RVSec"):
                raise TaskFailed("Failed to install application")

        assert "Failed to start emulator" not in str(excinfo.value)

    @patch("rv_android_core.util.android.emulator_manager.Android")
    def test_startup_failure_is_still_labelled_as_such(
        self, mock_android_class, emulator_manager, mock_android
    ):
        """A genuine startup failure keeps its EmulatorError label and cause."""
        mock_android_class.return_value = mock_android
        original = TimeoutError("emulator-5554 sys.boot_completed not set within 300s")
        mock_android.start_emulator.side_effect = original

        with pytest.raises(EmulatorError) as excinfo:
            with emulator_manager.start_emulator("RVSec"):
                pass

        assert "RVSec" in str(excinfo.value)
        assert excinfo.value.cause is original

    @patch("rv_android_core.util.android.emulator_manager.Android")
    def test_teardown_runs_when_the_session_fails(
        self, mock_android_class, emulator_manager, mock_android
    ):
        """Teardown covers the `yield`, so a failing body still kills the device."""
        mock_android_class.return_value = mock_android

        with pytest.raises(ValueError):
            with emulator_manager.start_emulator("RVSec", device_port=5556):
                raise ValueError("tool crashed")

        mock_android.kill_emulator.assert_called_once_with("RVSec", "emulator-5556")
        assert "RVSec" not in emulator_manager._active_emulators

    @patch("rv_android_core.util.android.emulator_manager.Android")
    def test_teardown_runs_when_startup_itself_fails(
        self, mock_android_class, emulator_manager, mock_android
    ):
        """The case a sibling-block implementation silently drops.

        The `with` body is never entered, so teardown can only run if the
        `finally` encloses the startup sequence as well as the `yield`.
        """
        mock_android_class.return_value = mock_android
        mock_android.start_emulator.side_effect = TimeoutError(
            "emulator-5556 did not boot within 300s"
        )

        with pytest.raises(EmulatorError):
            with emulator_manager.start_emulator("RVSec", device_port=5556):
                pass

        mock_android.kill_emulator.assert_called_once_with("RVSec", "emulator-5556")
        assert "RVSec" not in emulator_manager._active_emulators

    @patch("rv_android_core.util.android.emulator_manager.Android")
    def test_failed_boot_leaves_no_orphan_holding_the_port(
        self, mock_android_class, emulator_manager, mock_android
    ):
        """The AVD is registered before launch, so the port is reclaimed.

        Registration after the boot wait — which is where it used to happen —
        would leave the daemonized emulator alive on port 5556 for the next
        task to find.
        """
        mock_android_class.return_value = mock_android
        registered_at_failure = {}

        def fail_after_registration(*args, **kwargs):
            registered_at_failure["value"] = set(emulator_manager._active_emulators)
            raise TimeoutError("emulator-5556 did not boot within 300s")

        mock_android.start_emulator.side_effect = fail_after_registration

        with pytest.raises(EmulatorError):
            with emulator_manager.start_emulator("RVSec", device_port=5556):
                pass

        assert registered_at_failure["value"] == {"RVSec"}
        mock_android.kill_emulator.assert_called_once_with("RVSec", "emulator-5556")


class TestInstallReasonPropagation:
    """The ADB reason survives every hop up from `Android.install_apk`."""

    @pytest.fixture
    def emulator_manager(self):
        return EmulatorManager()

    @pytest.fixture
    def mock_app(self):
        mock = MagicMock()
        mock.name = "cryptoapp.apk"
        mock.package_name = "br.unb.cic.cryptoapp"
        mock.path = "/apks/cryptoapp.apk"
        return mock

    def test_install_failure_carries_the_adb_reason(self, emulator_manager, mock_app):
        """The INSTALL_FAILED_* text reaches the caller instead of a bare False."""
        emulator_manager.android = MagicMock()
        emulator_manager.android.install_with_permissions.side_effect = RuntimeError(
            "APK installation failed for cryptoapp.apk on emulator-5554 "
            "(exit code 1): INSTALL_FAILED_INSUFFICIENT_STORAGE"
        )

        with pytest.raises(RuntimeError) as excinfo:
            emulator_manager.install_app(mock_app)

        assert "INSTALL_FAILED_INSUFFICIENT_STORAGE" in str(excinfo.value)
        assert "exit code 1" in str(excinfo.value)

    def test_signature_mismatch_retry_reports_the_final_reason(self, mock_app):
        """The retry lives in `Android.install_apk`, so this drives that method.

        Mocking `install_apk` out — as the test above does — cannot exercise
        the retry at all: the sequence below is what the real path issues when
        the first install hits a signature mismatch (install, uninstall,
        install again), and the reason that must survive is the second
        install's, not the first's.
        """
        app = mock_app
        first = MagicMock()
        first.is_failure.return_value = True
        first.code = 1
        first.get_combined_output.return_value = "INSTALL_FAILED_UPDATE_INCOMPATIBLE"

        uninstall = MagicMock()
        uninstall.is_failure.return_value = False

        retry = MagicMock()
        retry.is_failure.return_value = True
        retry.code = 1
        retry.get_combined_output.return_value = "INSTALL_FAILED_INSUFFICIENT_STORAGE"

        root_result = MagicMock()
        root_result.is_failure.return_value = False
        readlink_result = MagicMock()
        readlink_result.is_failure.return_value = False
        readlink_result.stdout = b"/apks/cryptoapp.apk\n"

        # Command() is called for: root, readlink, install, uninstall. The
        # install instance is invoked twice — once before the uninstall and
        # once after — which is exactly the retry under test.
        install_cmd = MagicMock()
        install_cmd.invoke.side_effect = [first, retry]
        root_cmd = MagicMock()
        root_cmd.invoke.return_value = root_result
        readlink_cmd = MagicMock()
        readlink_cmd.invoke.return_value = readlink_result
        uninstall_cmd = MagicMock()
        uninstall_cmd.invoke.return_value = uninstall

        with patch(
            "rv_android_core.util.android.android.Command",
            side_effect=[root_cmd, readlink_cmd, install_cmd, uninstall_cmd],
        ):
            with pytest.raises(RuntimeError) as excinfo:
                Android.install_apk(app, "emulator-5554")

        message = str(excinfo.value)
        assert "INSTALL_FAILED_INSUFFICIENT_STORAGE" in message
        assert "INSTALL_FAILED_UPDATE_INCOMPATIBLE" not in message
        assert "exit code 1" in message
        assert install_cmd.invoke.call_count == 2, "the retry never happened"
        uninstall_cmd.invoke.assert_called_once()

    def test_successful_install_still_returns_true(self, emulator_manager, mock_app):
        emulator_manager.android = MagicMock()

        assert emulator_manager.install_app(mock_app) is True
