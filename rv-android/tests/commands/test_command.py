import signal
import subprocess
import sys
from unittest.mock import patch, MagicMock

import pytest

from rvandroid.commands.command import Command, kill_process_tree
from rvandroid.commands.command_not_found_error import CommandNotFoundError


class TestCommand:
    """Tests for the Command class"""

    def test_command_initialization(self):
        """Test Command constructor"""
        cmd = Command("ls", ["-l"], 10.0)
        assert cmd.command == "ls"
        assert cmd.args == ["-l"]
        assert cmd.timeout == 10.0

        # Test default values
        cmd2 = Command("pwd")
        assert cmd2.command == "pwd"
        assert cmd2.args == []
        assert cmd2.timeout is None

    def test_command_properties(self):
        """Test property setters and getters"""
        cmd = Command("ls")
        cmd.command = "pwd"
        cmd.args = ["-a"]
        cmd.timeout = 5.0

        assert cmd.command == "pwd"
        assert cmd.args == ["-a"]
        assert cmd.timeout == 5.0

    @patch('rvandroid.commands.command.Popen')
    def test_command_invoke_success(self, mock_popen):
        """Test successful command invocation"""
        # Setup the mock
        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = (b"output", b"error")
        mock_popen.return_value = process_mock

        cmd = Command("echo", ["test"], 1.0)
        result = cmd.invoke()

        # Verify
        mock_popen.assert_called_once_with(["echo", "test"], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        assert result.code == 0
        assert result.stdout == b"output"
        assert result.stderr == b"error"

    @patch('rvandroid.commands.command.Popen')
    def test_command_invoke_command_not_found(self, mock_popen):
        """Test command not found error handling"""
        # Setup the mock to raise OSError
        mock_popen.side_effect = OSError("Command not found")

        cmd = Command("nonexistent_command")

        # Verify exception is raised
        with pytest.raises(CommandNotFoundError):
            cmd.invoke()

    @pytest.mark.skipif(sys.version_info < (3, 3), reason="TimeoutExpired requires Python 3.3+")
    @patch('rvandroid.commands.command.Popen')
    def test_command_invoke_timeout(self, mock_popen):
        """Test timeout handling"""
        # Setup the mock
        process_mock = MagicMock()
        process_mock.returncode = -1

        # Configurando o side_effect do communicate adequadamente
        timeout_exc = subprocess.TimeoutExpired(cmd="cmd", timeout=1.0)
        process_mock.communicate.side_effect = [
            timeout_exc,
            (b"output after timeout", b"error after timeout")
        ]

        mock_popen.return_value = process_mock

        # Patch kill_process para evitar erros com a chamada real
        with patch.object(Command, 'kill_process') as mock_kill:
            cmd = Command("sleep", ["10"], 1.0)
            result = cmd.invoke()

            # Verify
            assert mock_popen.called
            assert result.code == -1
            assert result.stdout == b"output after timeout"
            assert result.stderr == b"error after timeout"
            assert process_mock.communicate.call_count == 2
            assert mock_kill.called

    @patch('rvandroid.commands.command.Popen')
    def test_command_invoke_as_daemon(self, mock_popen):
        """Test invoking command as a daemon"""
        # Setup the mock
        process_mock = MagicMock()
        mock_popen.return_value = process_mock

        cmd = Command("server", ["start"])
        result = cmd.invoke_as_deamon()

        # Verify
        mock_popen.assert_called_once_with(["server", "start"], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        assert result == process_mock

    @patch('rvandroid.commands.command.Popen')
    def test_command_invoke_as_daemon_not_found(self, mock_popen):
        """Test daemon command not found error handling"""
        # Setup the mock to raise OSError
        mock_popen.side_effect = OSError("Command not found")

        cmd = Command("nonexistent_daemon")

        # Verify exception is raised
        with pytest.raises(CommandNotFoundError):
            cmd.invoke_as_deamon()

    @patch('rvandroid.commands.command.logging')
    @patch('rvandroid.commands.command.kill_process_tree')
    def test_kill_process(self, mock_kill_process_tree, mock_logging):
        """Test the kill_process method"""
        # Setup
        process_mock = MagicMock()
        process_mock.pid = 12345

        cmd = Command("test", timeout=5.0)
        cmd.kill_process(process_mock)

        # Verify
        mock_logging.info.assert_called_once()
        mock_kill_process_tree.assert_called_once_with(12345)

    @patch('rvandroid.commands.command.os.kill')
    @patch('rvandroid.commands.command.psutil.Process')
    def test_kill_process_tree(self, mock_process, mock_kill):
        """Test the kill_process_tree function"""
        # Setup
        parent_process = MagicMock()
        parent_process.pid = 1000

        child1 = MagicMock()
        child1.pid = 1001
        child2 = MagicMock()
        child2.pid = 1002

        parent_process.children.return_value = [child1, child2]
        mock_process.return_value = parent_process

        # Call function
        kill_process_tree(1000)

        # Verify process tree is killed
        parent_process.children.assert_called_once_with(recursive=True)
        assert mock_kill.call_count == 3  # Parent + 2 children
        mock_kill.assert_any_call(1001, signal.SIGKILL)
        mock_kill.assert_any_call(1002, signal.SIGKILL)
        mock_kill.assert_any_call(1000, signal.SIGKILL)
