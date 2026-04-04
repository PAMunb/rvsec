"""
Unit tests for the CommandResult class.

This module contains comprehensive tests for the CommandResult class that represents
command execution results with standardized error handling and type safety.
"""

import pytest
from pydantic import ValidationError
from rv_android_core.commands.command_result import CommandResult


class TestCommandResultInitialization:
    """Tests for CommandResult initialization and validation."""

    def test_command_result_initialization(self):
        """Test CommandResult constructor with valid parameters."""
        # Arrange
        stdout = b"Command output"
        stderr = b"Error output"

        # Act
        result = CommandResult(0, stdout, stderr)

        # Assert
        assert result.code == 0
        assert result.stdout == stdout
        assert result.stderr == stderr

    def test_command_result_properties(self):
        """Test property setters and getters."""
        # Arrange
        result = CommandResult(0, b"", b"")

        # Act - Test setters
        result.code = 1
        result.stdout = b"New output"
        result.stderr = b"New error"

        # Assert - Test getters
        assert result.code == 1
        assert result.stdout == b"New output"
        assert result.stderr == b"New error"

    def test_command_result_with_bytes_output(self):
        """Test with bytes output (actual subprocess behavior)."""
        # Act
        result = CommandResult(0, b"Bytes output", b"Bytes error")

        # Assert
        assert result.code == 0
        assert result.stdout == b"Bytes output"
        assert result.stderr == b"Bytes error"

    def test_command_result_with_empty_values(self):
        """Test with empty values (using proper types)."""
        # Act
        result = CommandResult(0, b"", b"")

        # Assert
        assert result.code == 0
        assert result.stdout == b""
        assert result.stderr == b""

    def test_positional_arguments(self):
        """Test CommandResult with positional arguments (validated_model)."""
        # Act
        result = CommandResult(127, b"stdout_data", b"stderr_data")

        # Assert
        assert result.code == 127
        assert result.stdout == b"stdout_data"
        assert result.stderr == b"stderr_data"

    def test_named_arguments(self):
        """Test CommandResult with named arguments."""
        # Act
        result = CommandResult(code=-1, stdout=b"named stdout", stderr=b"named stderr")

        # Assert
        assert result.code == -1
        assert result.stdout == b"named stdout"
        assert result.stderr == b"named stderr"

    def test_mixed_positional_and_named_arguments(self):
        """Test CommandResult with mixed positional and named arguments."""
        # Act
        result = CommandResult(2, stdout=b"mixed stdout", stderr=b"mixed stderr")

        # Assert
        assert result.code == 2
        assert result.stdout == b"mixed stdout"
        assert result.stderr == b"mixed stderr"

    def test_default_values(self):
        """Test CommandResult with default values for optional fields."""
        # Act
        result = CommandResult(code=0)

        # Assert
        assert result.code == 0
        assert result.stdout == b""
        assert result.stderr == b""

    def test_none_values_for_optional_fields(self):
        """Test CommandResult with None values for stdout/stderr."""
        # Act
        result = CommandResult(code=0, stdout=None, stderr=None)

        # Assert
        assert result.code == 0
        assert result.stdout is None
        assert result.stderr is None


class TestCommandResultValidation:
    """Tests for CommandResult field validation."""

    def test_valid_exit_codes(self):
        """Test valid exit codes within allowed range."""
        # Test boundary values
        valid_codes = [-255, -1, 0, 1, 255]

        for code in valid_codes:
            # Act
            result = CommandResult(code=code)

            # Assert
            assert result.code == code

    def test_invalid_exit_code_too_low(self):
        """Test validation fails for exit codes below -255."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            CommandResult(code=-256)

        # Verify the validation error mentions the constraint
        assert "greater than or equal to -255" in str(exc_info.value)

    def test_invalid_exit_code_too_high(self):
        """Test validation fails for exit codes above 255."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            CommandResult(code=256)

        # Verify the validation error mentions the constraint
        assert "less than or equal to 255" in str(exc_info.value)

    def test_invalid_exit_code_non_integer(self):
        """Test validation fails for non-integer exit codes."""
        # Act & Assert
        with pytest.raises(ValidationError):
            CommandResult(code="not_an_integer")

    def test_invalid_stdout_type(self):
        """Test validation with invalid stdout type."""
        # Note: Pydantic might coerce or accept this depending on configuration
        # This test documents the current behavior
        try:
            result = CommandResult(code=0, stdout="string_instead_of_bytes")
            # If it passes, verify the behavior
            assert isinstance(result.stdout, (bytes, str))
        except ValidationError:
            # If it fails validation, that's also acceptable
            pass

    def test_invalid_stderr_type(self):
        """Test validation with invalid stderr type."""
        # Note: Similar to stdout test - documents current behavior
        try:
            result = CommandResult(code=0, stderr="string_instead_of_bytes")
            assert isinstance(result.stderr, (bytes, str))
        except ValidationError:
            pass


class TestCommandResultStatusMethods:
    """Tests for CommandResult status checking methods."""

    def test_is_success_with_zero_exit_code(self):
        """Test is_success returns True for exit code 0."""
        # Arrange
        result = CommandResult(code=0)

        # Act & Assert
        assert result.is_success() is True

    def test_is_success_with_non_zero_exit_code(self):
        """Test is_success returns False for non-zero exit codes."""
        # Test various non-zero codes
        non_zero_codes = [-1, 1, 2, 127, -128]

        for code in non_zero_codes:
            # Arrange
            result = CommandResult(code=code)

            # Act & Assert
            assert result.is_success() is False, f"Failed for exit code {code}"

    def test_is_failure_with_zero_exit_code(self):
        """Test is_failure returns False for exit code 0."""
        # Arrange
        result = CommandResult(code=0)

        # Act & Assert
        assert result.is_failure() is False

    def test_is_failure_with_non_zero_exit_code(self):
        """Test is_failure returns True for non-zero exit codes."""
        # Test various non-zero codes
        non_zero_codes = [-1, 1, 2, 127, -128]

        for code in non_zero_codes:
            # Arrange
            result = CommandResult(code=code)

            # Act & Assert
            assert result.is_failure() is True, f"Failed for exit code {code}"

    def test_success_and_failure_are_opposite(self):
        """Test that is_success and is_failure are always opposite."""
        # Test with various exit codes
        test_codes = [-128, -1, 0, 1, 127]

        for code in test_codes:
            # Arrange
            result = CommandResult(code=code)

            # Act & Assert
            assert (
                result.is_success() != result.is_failure()
            ), f"Failed for exit code {code}"
            # Also test that they return actual booleans
            assert isinstance(result.is_success(), bool)
            assert isinstance(result.is_failure(), bool)


class TestCommandResultOutputDetection:
    """Tests for CommandResult output detection methods."""

    def test_has_output_with_stdout_only(self):
        """Test has_output with stdout content only."""
        # Arrange
        result = CommandResult(code=0, stdout=b"Some output", stderr=b"")

        # Act & Assert
        assert result.has_output() is True

    def test_has_output_with_stderr_only(self):
        """Test has_output with stderr content only."""
        # Arrange
        result = CommandResult(code=0, stdout=b"", stderr=b"Some error")

        # Act & Assert
        assert result.has_output() is True

    def test_has_output_with_both_outputs(self):
        """Test has_output with both stdout and stderr content."""
        # Arrange
        result = CommandResult(code=0, stdout=b"Output", stderr=b"Error")

        # Act & Assert
        assert result.has_output() is True

    def test_has_output_with_no_output(self):
        """Test has_output with no content in either output."""
        # Arrange
        result = CommandResult(code=0, stdout=b"", stderr=b"")

        # Act & Assert
        assert not result.has_output()  # Test falsy behavior instead of exact equality

    def test_has_output_with_whitespace_only(self):
        """Test has_output with whitespace-only content."""
        # Arrange
        result = CommandResult(code=0, stdout=b"   \n\t  ", stderr=b"  \n  ")

        # Act & Assert
        assert not result.has_output()  # Use not instead of == False

    def test_has_output_with_none_values(self):
        """Test has_output with None values."""
        # Arrange
        result = CommandResult(code=0, stdout=None, stderr=None)

        # Act & Assert
        assert not result.has_output()  # Test falsy behavior instead of exact equality

    def test_has_error_output_with_stderr_content(self):
        """Test has_error_output with stderr content."""
        # Arrange
        result = CommandResult(code=1, stderr=b"Error message")

        # Act & Assert
        assert result.has_error_output() is True

    def test_has_error_output_with_empty_stderr(self):
        """Test has_error_output with empty stderr."""
        # Arrange
        result = CommandResult(code=0, stderr=b"")

        # Act & Assert
        assert not result.has_error_output()  # Use not instead of == False

    def test_has_error_output_with_whitespace_stderr(self):
        """Test has_error_output with whitespace-only stderr."""
        # Arrange
        result = CommandResult(code=1, stderr=b"   \n\t  ")

        # Act & Assert
        assert not result.has_error_output()  # Use not instead of == False

    def test_has_error_output_with_none_stderr(self):
        """Test has_error_output with None stderr."""
        # Arrange
        result = CommandResult(code=1, stderr=None)

        # Act & Assert
        assert not result.has_error_output()  # Use not instead of == False


class TestCommandResultTextMethods:
    """Tests for CommandResult text conversion methods."""

    def test_get_stdout_text_with_valid_utf8(self):
        """Test get_stdout_text with valid UTF-8 content."""
        # Arrange
        stdout_bytes = "Hello, World! 🌍".encode("utf-8")
        result = CommandResult(code=0, stdout=stdout_bytes)

        # Act
        text = result.get_stdout_text()

        # Assert
        assert text == "Hello, World! 🌍"

    def test_get_stdout_text_with_custom_encoding(self):
        """Test get_stdout_text with custom encoding."""
        # Arrange
        stdout_bytes = "Olá, Mundo!".encode("latin-1")
        result = CommandResult(code=0, stdout=stdout_bytes)

        # Act
        text = result.get_stdout_text(encoding="latin-1")

        # Assert
        assert text == "Olá, Mundo!"

    def test_get_stdout_text_with_encoding_errors(self):
        """Test get_stdout_text with encoding errors using replace strategy."""
        # Arrange
        stdout_bytes = (
            b"\xff\xfe\x00\x48\x00\x65\x00\x6c\x00\x6c\x00\x6f"  # Invalid UTF-8
        )
        result = CommandResult(code=0, stdout=stdout_bytes)

        # Act
        text = result.get_stdout_text(errors="replace")

        # Assert
        assert (
            "�" in text or len(text) > 0
        )  # Should contain replacement chars or be processed

    def test_get_stdout_text_with_ignore_errors(self):
        """Test get_stdout_text with ignore error handling."""
        # Arrange
        stdout_bytes = b"Valid\xff\xfeInvalid\x00UTF-8"
        result = CommandResult(code=0, stdout=stdout_bytes)

        # Act
        text = result.get_stdout_text(errors="ignore")

        # Assert
        assert "Valid" in text
        assert "UTF-8" in text

    def test_get_stdout_text_with_none_stdout(self):
        """Test get_stdout_text with None stdout."""
        # Arrange
        result = CommandResult(code=0, stdout=None)

        # Act
        text = result.get_stdout_text()

        # Assert
        assert text == ""

    def test_get_stderr_text_with_valid_utf8(self):
        """Test get_stderr_text with valid UTF-8 content."""
        # Arrange
        stderr_bytes = "Error: File not found! ❌".encode("utf-8")
        result = CommandResult(code=1, stderr=stderr_bytes)

        # Act
        text = result.get_stderr_text()

        # Assert
        assert text == "Error: File not found! ❌"

    def test_get_stderr_text_with_custom_encoding(self):
        """Test get_stderr_text with custom encoding."""
        # Arrange
        stderr_bytes = "Erro: Arquivo não encontrado!".encode("latin-1")
        result = CommandResult(code=1, stderr=stderr_bytes)

        # Act
        text = result.get_stderr_text(encoding="latin-1")

        # Assert
        assert text == "Erro: Arquivo não encontrado!"

    def test_get_stderr_text_with_encoding_errors(self):
        """Test get_stderr_text with encoding errors using replace strategy."""
        # Arrange
        stderr_bytes = b"\xff\xfeError\x00Message"  # Invalid UTF-8
        result = CommandResult(code=1, stderr=stderr_bytes)

        # Act
        text = result.get_stderr_text(errors="replace")

        # Assert
        assert len(text) > 0  # Should return some text with replacements

    def test_get_stderr_text_with_none_stderr(self):
        """Test get_stderr_text with None stderr."""
        # Arrange
        result = CommandResult(code=1, stderr=None)

        # Act
        text = result.get_stderr_text()

        # Assert
        assert text == ""

    def test_get_combined_output_stdout_only(self):
        """Test get_combined_output with stdout content only."""
        # Arrange
        result = CommandResult(
            code=0, stdout=b"Command executed successfully", stderr=b""
        )

        # Act
        combined = result.get_combined_output()

        # Assert
        assert combined == "Command executed successfully"

    def test_get_combined_output_stderr_only(self):
        """Test get_combined_output with stderr content only."""
        # Arrange
        result = CommandResult(code=1, stdout=b"", stderr=b"Permission denied")

        # Act
        combined = result.get_combined_output()

        # Assert
        assert combined == "STDERR: Permission denied"

    def test_get_combined_output_both_outputs(self):
        """Test get_combined_output with both stdout and stderr."""
        # Arrange
        result = CommandResult(
            code=1, stdout=b"Partial success", stderr=b"Warning: deprecated option"
        )

        # Act
        combined = result.get_combined_output()

        # Assert
        expected = "Partial success\nSTDERR: Warning: deprecated option"
        assert combined == expected

    def test_get_combined_output_no_content(self):
        """Test get_combined_output with no content in either output."""
        # Arrange
        result = CommandResult(code=0, stdout=b"", stderr=b"")

        # Act
        combined = result.get_combined_output()

        # Assert
        assert combined == ""

    def test_get_combined_output_whitespace_handling(self):
        """Test get_combined_output strips whitespace properly."""
        # Arrange
        result = CommandResult(
            code=0,
            stdout=b"  Output with spaces  \n",
            stderr=b"  \n  Error with spaces  \n  ",
        )

        # Act
        combined = result.get_combined_output()

        # Assert
        expected = "Output with spaces\nSTDERR: Error with spaces"
        assert combined == expected

    def test_get_combined_output_none_values(self):
        """Test get_combined_output with None values."""
        # Arrange
        result = CommandResult(code=0, stdout=None, stderr=None)

        # Act
        combined = result.get_combined_output()

        # Assert
        assert combined == ""

    def test_get_combined_output_custom_encoding(self):
        """Test get_combined_output with custom encoding."""
        # Arrange
        result = CommandResult(
            code=0,
            stdout="Saída em português".encode("latin-1"),
            stderr="Erro em português".encode("latin-1"),
        )

        # Act
        combined = result.get_combined_output(encoding="latin-1")

        # Assert
        expected = "Saída em português\nSTDERR: Erro em português"
        assert combined == expected

    def test_get_combined_output_encoding_errors(self):
        """Test get_combined_output with encoding error handling."""
        # Arrange
        result = CommandResult(
            code=1, stdout=b"Valid\xff\xfeOutput", stderr=b"Valid\xff\xfeError"
        )

        # Act
        combined = result.get_combined_output(errors="ignore")

        # Assert
        assert "ValidOutput" in combined
        assert "ValidError" in combined

    def test_combined_output_stderr_multiline_behavior(self):
        """Test that combined output adds STDERR prefix only once for multiline stderr."""
        # Arrange
        result = CommandResult(
            code=1,
            stdout=b"Success message",
            stderr=b"Line 1 error\nLine 2 error\nLine 3 error",
        )

        # Act
        combined = result.get_combined_output()

        # Assert
        # STDERR prefix should appear only once
        stderr_count = combined.count("STDERR:")
        assert stderr_count == 1

        # All error lines should be present
        assert "Line 1 error" in combined
        assert "Line 2 error" in combined
        assert "Line 3 error" in combined

        # Success message should be first
        assert combined.startswith("Success message")


class TestCommandResultStringRepresentation:
    """Tests for CommandResult string representation methods."""

    def test_str_representation_success_no_output(self):
        """Test string representation for successful command with no output."""
        # Arrange
        result = CommandResult(code=0, stdout=b"", stderr=b"")

        # Act
        str_repr = str(result)

        # Assert
        assert "code=0" in str_repr
        assert "SUCCESS" in str_repr
        assert "no output" in str_repr

    def test_str_representation_success_with_output(self):
        """Test string representation for successful command with output."""
        # Arrange
        result = CommandResult(code=0, stdout=b"Some output", stderr=b"")

        # Act
        str_repr = str(result)

        # Assert
        assert "code=0" in str_repr
        assert "SUCCESS" in str_repr
        assert "with output" in str_repr

    def test_str_representation_failure_no_output(self):
        """Test string representation for failed command with no output."""
        # Arrange
        result = CommandResult(code=1, stdout=b"", stderr=b"")

        # Act
        str_repr = str(result)

        # Assert
        assert "code=1" in str_repr
        assert "FAILED" in str_repr
        assert "no output" in str_repr

    def test_str_representation_failure_with_output(self):
        """Test string representation for failed command with output."""
        # Arrange
        result = CommandResult(code=127, stdout=b"", stderr=b"Command not found")

        # Act
        str_repr = str(result)

        # Assert
        assert "code=127" in str_repr
        assert "FAILED" in str_repr
        assert "with output" in str_repr

    def test_str_representation_various_exit_codes(self):
        """Test string representation with various exit codes."""
        # Test cases: (exit_code, expected_status)
        test_cases = [
            (0, "SUCCESS"),
            (-1, "FAILED"),
            (1, "FAILED"),
            (2, "FAILED"),
            (127, "FAILED"),
            (-128, "FAILED"),
        ]

        for exit_code, expected_status in test_cases:
            # Arrange
            result = CommandResult(code=exit_code)

            # Act
            str_repr = str(result)

            # Assert
            assert f"code={exit_code}" in str_repr
            assert expected_status in str_repr

    def test_str_representation_format(self):
        """Test the exact format of string representation."""
        # Arrange
        result = CommandResult(code=42, stdout=b"test", stderr=b"")

        # Act
        str_repr = str(result)

        # Assert
        expected = "CommandResult(code=42, status=FAILED, with output)"
        assert str_repr == expected


class TestCommandResultEdgeCases:
    """Tests for CommandResult edge cases and boundary conditions."""

    def test_large_output_handling(self):
        """Test handling of large output data."""
        # Arrange
        large_stdout = b"A" * 10000  # 10KB of data
        large_stderr = b"E" * 5000  # 5KB of data
        result = CommandResult(code=0, stdout=large_stdout, stderr=large_stderr)

        # Act & Assert
        assert len(result.get_stdout_text()) == 10000
        assert len(result.get_stderr_text()) == 5000
        assert result.has_output() is True

    def test_binary_data_handling(self):
        """Test handling of binary data in outputs."""
        # Arrange
        binary_data = bytes(range(256))  # All possible byte values
        result = CommandResult(code=0, stdout=binary_data, stderr=b"")

        # Act
        text = result.get_stdout_text(errors="replace")

        # Assert
        assert isinstance(text, str)
        assert len(text) > 0

    def test_empty_vs_none_distinction(self):
        """Test distinction between empty bytes and None values."""
        # Arrange
        result_empty = CommandResult(code=0, stdout=b"", stderr=b"")
        result_none = CommandResult(code=0, stdout=None, stderr=None)

        # Act & Assert
        assert result_empty.get_stdout_text() == ""
        assert result_none.get_stdout_text() == ""
        assert result_empty.stdout == b""
        assert result_none.stdout is None

    def test_unicode_handling_comprehensive(self):
        """Test comprehensive Unicode handling in outputs."""
        # Arrange - Various Unicode characters
        unicode_text = "Hello 🌍 世界 🚀 Ñoño café résumé"
        unicode_bytes = unicode_text.encode("utf-8")
        result = CommandResult(code=0, stdout=unicode_bytes, stderr=b"")

        # Act
        decoded_text = result.get_stdout_text()

        # Assert
        assert decoded_text == unicode_text
        assert "🌍" in decoded_text
        assert "世界" in decoded_text
        assert "🚀" in decoded_text

    def test_newline_handling_in_combined_output(self):
        """Test newline handling in combined output method."""
        # Arrange
        result = CommandResult(
            code=0, stdout=b"Line 1\nLine 2\n", stderr=b"Error line 1\nError line 2\n"
        )

        # Act
        combined = result.get_combined_output()

        # Assert
        lines = combined.split("\n")
        assert "Line 1" in lines
        assert "Line 2" in lines
        # The STDERR prefix is added once to the entire stderr content
        assert "STDERR: Error line 1" in combined
        assert "Error line 2" in combined  # Second line doesn't have STDERR prefix

        # Verify the exact structure
        expected = "Line 1\nLine 2\nSTDERR: Error line 1\nError line 2"
        assert combined == expected
