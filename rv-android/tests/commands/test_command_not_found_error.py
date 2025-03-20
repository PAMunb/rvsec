import pytest
from rvandroid.commands.command_not_found_error import CommandNotFoundError


class TestCommandNotFoundError:
    """Tests for CommandNotFoundError class"""

    def test_command_not_found_error_inheritance(self):
        """Test inheritance from Exception"""
        error = CommandNotFoundError("Command not found")
        assert isinstance(error, Exception)

    def test_command_not_found_error_message(self):
        """Test error message"""
        error_message = "The command 'test' was not found"
        error = CommandNotFoundError(error_message)

        assert str(error) == error_message

    def test_command_not_found_error_as_exception(self):
        """Test CommandNotFoundError can be raised and caught"""
        try:
            raise CommandNotFoundError("The command 'python3' was not found")
        except CommandNotFoundError as e:
            assert "not found" in str(e)
        except Exception:
            pytest.fail("CommandNotFoundError was not caught as expected")

    def test_command_not_found_error_without_message(self):
        """Test without message"""
        error = CommandNotFoundError()
        assert str(error) == ""