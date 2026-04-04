"""
Test file focused on achieving 100% coverage of command.py
Only covers lines that are currently missing coverage.
"""

import signal
from unittest.mock import Mock, patch

import pytest
from rv_android_core.commands.command import Command, kill_process_tree
from rv_android_core.util.error.exceptions import RVCommandTimeoutError


class TestCommandCoverage:
    """Tests specifically for missing coverage lines in command.py"""

    def test_invoke_with_string_stdin_real(self):
        """Test invoke with string stdin - covers line 200"""
        cmd = Command(command="echo", args=["hello"])
        result = cmd.invoke(stdin="test")
        # Just ensure it runs without error
        assert result.code == 0

    def test_invoke_with_failing_command_real(self):
        """Test invoke with failing command - covers line 208"""
        cmd = Command(command="false")
        result = cmd.invoke()
        # Should log warning for non-zero exit code
        assert result.code == 1

    def test_invoke_with_timeout_real(self):
        """Test invoke with actual timeout - covers timeout handling"""
        cmd = Command(command="sleep", args=["3"], timeout=0.1)

        with pytest.raises(RVCommandTimeoutError):
            cmd.invoke()

    def test_kill_process_method_real(self):
        """Test kill_process method directly"""
        mock_process = Mock()
        mock_process.pid = 99999  # Non-existent PID

        cmd = Command(command="test", timeout=1.0)
        # Should not raise exception even with invalid PID
        cmd.kill_process(mock_process)


class TestKillProcessTreeCoverage:
    """Test kill_process_tree function coverage"""

    @patch("psutil.Process")
    @patch("os.kill")
    def test_kill_process_tree_os_error_on_parent(self, mock_kill, mock_process_class):
        """Test kill_process_tree when parent kill fails with OSError"""
        # Setup mock process
        mock_parent = Mock()
        mock_parent.pid = 1000
        mock_parent.children.return_value = []
        mock_process_class.return_value = mock_parent

        # Simulate OSError on parent kill
        mock_kill.side_effect = OSError("Permission denied")

        # Should not raise exception
        kill_process_tree(1000)

        # Should attempt to kill parent
        mock_kill.assert_called_once_with(1000, signal.SIGKILL)

    @patch("psutil.Process")
    @patch("os.kill")
    def test_kill_process_tree_with_no_children(self, mock_kill, mock_process_class):
        """Test kill_process_tree with process that has no children"""
        # Setup mock process with no children
        mock_parent = Mock()
        mock_parent.pid = 1000
        mock_parent.children.return_value = []
        mock_process_class.return_value = mock_parent

        kill_process_tree(1000)

        # Should only kill parent
        mock_kill.assert_called_once_with(1000, signal.SIGKILL)

    @patch("psutil.Process")
    @patch("os.kill")
    def test_kill_process_tree_child_os_error(self, mock_kill, mock_process_class):
        """Test kill_process_tree when child kill fails with OSError - covers lines 34-38"""
        # Setup mock process with children
        mock_parent = Mock()
        mock_child1 = Mock()
        mock_child1.pid = 1001
        mock_child2 = Mock()
        mock_child2.pid = 1002

        mock_parent.pid = 1000
        mock_parent.children.return_value = [mock_child1, mock_child2]
        mock_process_class.return_value = mock_parent

        # Simulate OSError on first child, success on others
        kill_calls = []

        def kill_side_effect(pid, sig):
            kill_calls.append((pid, sig))
            if pid == 1001:
                raise OSError("Process already gone")

        mock_kill.side_effect = kill_side_effect

        # Should not raise exception
        kill_process_tree(1000)

        # Should attempt to kill all processes
        expected_calls = [
            (1001, signal.SIGKILL),  # child1 - fails
            (1002, signal.SIGKILL),  # child2 - succeeds
            (1000, signal.SIGKILL),  # parent - succeeds
        ]
        assert kill_calls == expected_calls
