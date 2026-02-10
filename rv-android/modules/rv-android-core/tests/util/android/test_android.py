import pytest
from unittest.mock import MagicMock, patch, call
from contextlib import ExitStack
import time
from rv_android_core.util.android.android import Android
from rv_android_core.commands.command import Command
from rv_android_core.domain.app import App
from rv_android_core.util import utils

# Mock the Command class globally for these tests
@pytest.fixture(autouse=True)
def mock_command_class():
    with patch('rv_android_core.util.android.android.Command') as mock_command:
        yield mock_command

# Mock logging globally
@pytest.fixture(autouse=True)
def mock_logging():
    with patch('rv_android_core.util.android.android.logging') as mock_log:
        yield mock_log

# Mock time.sleep globally
@pytest.fixture(autouse=True)
def mock_time_sleep():
    with patch('time.sleep') as mock_sleep:
        yield mock_sleep

# Mock utils.to_readable_time globally
@pytest.fixture(autouse=True)
def mock_to_readable_time():
    with patch('rv_android_core.util.android.android.utils.to_readable_time') as mock_readable_time:
        mock_readable_time.return_value = "0m 0s"
        yield mock_readable_time


class TestAndroid:

    def test_create_emulator_context_manager(self, mock_command_class, mock_logging):
        mock_emulator_proc = MagicMock()
        mock_command_class.return_value.invoke_as_deamon.return_value = mock_emulator_proc

        with patch.object(Android, 'start_emulator', return_value=mock_emulator_proc) as mock_start_emulator, \
             patch.object(Android, 'kill_emulator') as mock_kill_emulator:
            with Android.create_emulator("test_avd", device_port=5556):
                mock_start_emulator.assert_called_once_with("test_avd", False, 5556)
            mock_kill_emulator.assert_called_once_with("test_avd", "emulator-5556")

    def test_create_emulator_context_manager_with_exception(self, mock_command_class, mock_logging):
        mock_emulator_proc = MagicMock()
        mock_command_class.return_value.invoke_as_deamon.return_value = mock_emulator_proc

        with patch.object(Android, 'start_emulator', return_value=mock_emulator_proc) as mock_start_emulator, \
             patch.object(Android, 'kill_emulator') as mock_kill_emulator:
            with pytest.raises(ValueError):
                with Android.create_emulator("test_avd", device_port=5556):
                    raise ValueError("Test exception")
            mock_kill_emulator.assert_called_once_with("test_avd", "emulator-5556")
            mock_logging.error.assert_called_with("Error while using emulator: Test exception")

    def test_start_emulator(self, mock_command_class, mock_logging):
        mock_emulator_proc = MagicMock()
        mock_command_class.return_value.invoke_as_deamon.return_value = mock_emulator_proc
        
        with patch.object(Android, '_wait_for_boot') as mock_wait_for_boot:
            Android.start_emulator("test_avd", True, 5556)
            mock_command_class.assert_called_once_with('emulator', [
                '-avd', 'test_avd',
                '-port', '5556',
                '-read-only',
                '-no-cache',
                '-no-boot-anim',
                '-noaudio',
                '-no-snapshot-save',
                '-delay-adb',
                '-no-window'
            ])
            mock_command_class.return_value.invoke_as_deamon.assert_called_once()
            mock_wait_for_boot.assert_called_once_with("emulator-5556")
            mock_logging.info.assert_called_with("Starting emulator on emulator-5556")

    def test_kill_emulator(self, mock_command_class, mock_logging, mock_time_sleep):
        mock_kill_emu_cmd_instance = MagicMock()
        mock_command_class.side_effect = [mock_kill_emu_cmd_instance]

        # Use non-default serial to prove device_name is propagated correctly
        Android.kill_emulator("test_avd", "emulator-5556")

        mock_command_class.assert_has_calls([
            call('adb', ['-s', 'emulator-5556', 'emu', 'kill']),
        ])
        mock_kill_emu_cmd_instance.invoke.assert_called_once()
        mock_time_sleep.assert_called_once_with(10)
        mock_logging.info.assert_any_call("Killing emulator emulator-5556...")
        mock_logging.info.assert_called_with("Emulator emulator-5556 has been killed")

    def test_wait_for_boot(self, mock_command_class, mock_logging, mock_time_sleep, mock_to_readable_time):
        # Mock the invoke results for bootanim, boot_completed, root, remount
        mock_command_class.return_value.invoke.side_effect = [
            MagicMock(stdout=b'booting'),  # bootanim not stopped
            MagicMock(stdout=b'stopped'),  # bootanim stopped
            MagicMock(stdout=b''),         # sys.boot_completed
            MagicMock(stderr=b'error'),    # root not ready
            MagicMock(stderr=b''),         # root ready
            MagicMock(stderr=b'error'),    # remount not ready
            MagicMock(stderr=b''),         # remount ready
        ]
        
        with patch('time.time', side_effect=[0, 10]): # Simulate 10 seconds boot time
            Android._wait_for_boot("emulator-5554")
            mock_logging.info.assert_has_calls([
                call('Waiting for emulator-5554 to boot'),
                call('Waiting for emulator-5554 to boot'),
                call('emulator-5554 booted!'),
                call('emulator-5554 took 0m 0s to boot')
            ])
            assert mock_time_sleep.call_count == 3 # 5s for bootanim, 5s for root, 5s for remount

    def test_simulate_reboot(self, mock_command_class, mock_logging, mock_time_sleep):
        with patch.object(Android, '_wait_for_boot') as mock_wait_for_boot:
            Android.simulate_reboot()
            mock_command_class.assert_called_once_with('adb', ['shell', 'am', 'broadcast', '-a', 'android.intent.action.BOOT_COMPLETED'], 15)
            mock_command_class.return_value.invoke.assert_called_once()
            mock_time_sleep.assert_called_once_with(1)
            mock_wait_for_boot.assert_called_once()
            mock_logging.info.assert_called_with("Starting reboot simulation")

    def test_install_with_permissions(self, mock_command_class):
        mock_app = MagicMock(spec=App)
        with patch.object(Android, 'install_apk') as mock_install_apk, \
             patch.object(Android, 'grant_permissions') as mock_grant_permissions:
            Android.install_with_permissions(mock_app, "emulator-5554")
            mock_install_apk.assert_called_once_with(mock_app, "emulator-5554")
            mock_grant_permissions.assert_called_once_with(mock_app, "emulator-5554")

    def test_install_apk(self, mock_command_class, mock_logging):
        mock_app = MagicMock(spec=App)
        mock_app.name = "test_app"
        mock_app.path = "/path/to/app.apk"

        mock_root_cmd_instance = MagicMock()
        mock_readlink_cmd_instance = MagicMock()
        mock_install_cmd_instance = MagicMock()

        mock_command_class.side_effect = [
            mock_root_cmd_instance,
            mock_readlink_cmd_instance,
            mock_install_cmd_instance
        ]
        mock_readlink_cmd_instance.invoke.return_value = MagicMock(stdout=b'/real/path/to/app.apk\n')
        
        Android.install_apk(mock_app, "emulator-5554")
        mock_logging.info.assert_called_with("Installing APK: test_app on emulator-5554")
        mock_command_class.assert_has_calls([
            call('adb', ['-s', 'emulator-5554', 'root']),
            call('readlink', ['-f', '/path/to/app.apk']),
            call('adb', ['-s', 'emulator-5554', 'install', '-r', '-g', '/real/path/to/app.apk'])
        ])
        mock_root_cmd_instance.invoke.assert_called_once()
        mock_readlink_cmd_instance.invoke.assert_called_once()
        mock_install_cmd_instance.invoke.assert_called_once()

    def test_uninstall_apk(self, mock_command_class, mock_logging):
        mock_app = MagicMock(spec=App)
        mock_app.name = "test_app"
        mock_app.package_name = "com.example.test"
        Android.uninstall_apk(mock_app, "emulator-5554")
        mock_logging.info.assert_called_with("Uninstalling APK: test_app from emulator-5554")
        mock_command_class.assert_called_once_with('adb', ['-s', 'emulator-5554', 'uninstall', 'com.example.test'])
        mock_command_class.return_value.invoke.assert_called_once()

    def test_grant_permissions(self, mock_command_class, mock_logging):
        mock_app = MagicMock(spec=App)
        mock_app.name = "test_app"
        mock_app.permissions = ["PERMISSION_A", "PERMISSION_B"]
        mock_app.package_name = "com.example.test"

        mock_grant_cmd_instance_a = MagicMock()
        mock_grant_cmd_instance_b = MagicMock()

        mock_command_class.side_effect = [
            mock_grant_cmd_instance_a,
            mock_grant_cmd_instance_b
        ]

        Android.grant_permissions(mock_app, "emulator-5554")
        assert mock_logging.info.call_count == 2
        mock_logging.info.assert_has_calls([
            call("Granting permission PERMISSION_A on emulator-5554"),
            call("Granting permission PERMISSION_B on emulator-5554")
        ])
        mock_command_class.assert_has_calls([
            call('adb', ['-s', 'emulator-5554', 'shell', 'pm', 'grant', 'com.example.test', 'PERMISSION_A']),
            call('adb', ['-s', 'emulator-5554', 'shell', 'pm', 'grant', 'com.example.test', 'PERMISSION_B'])
        ])
        mock_grant_cmd_instance_a.invoke.assert_called_once()
        mock_grant_cmd_instance_b.invoke.assert_called_once()