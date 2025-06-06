import pytest

from rv_android_core.commands.command_exception import CommandException


class TestCommandException:
    """Tests for CommandException class"""

    def test_command_exception_initialization(self):
        """Test CommandException constructor"""
        exception = CommandException("adb", 1, "Device not found")

        assert exception.tool == "adb"
        assert exception.code == 1
        assert exception.message == "Device not found"

    def test_command_exception_str(self):
        """Test string representation of CommandException"""
        exception = CommandException("adb", 1, "Device not found")
        expected_str = "CommandException[tool=adb ::: code=1 ::: message=Device not found]"

        assert str(exception) == expected_str

    def test_command_exception_as_exception(self):
        """Test CommandException can be raised and caught as exception"""
        try:
            raise CommandException("adb", 1, "Device not found")
        except CommandException as e:
            assert e.tool == "adb"
            assert e.code == 1
            assert e.message == "Device not found"
        except Exception:
            pytest.fail("CommandException was not caught as expected")
