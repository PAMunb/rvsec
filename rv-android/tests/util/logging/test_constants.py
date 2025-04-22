# tests/util/logging/test_constants.py
import logging

import pytest

from rvandroid.util.logging.constants import (
    # Custom log levels
    EXPERIMENT_START, EXPERIMENT_END, TASK_START, TASK_END, ERROR,
    # Standard context keys
    CONTEXT_TASK_ID, CONTEXT_APP_NAME, CONTEXT_TOOL_NAME, CONTEXT_COMPONENT, CONTEXT_PHASE,
    # Common log message patterns
    LOG_START, LOG_COMPLETE, LOG_ERROR, LOG_SKIPPED
)


class TestLoggingConstants:
    """Tests for logging constants module"""

    def test_custom_log_levels_values(self):
        """Test that custom log levels have the expected values"""
        assert EXPERIMENT_START == 25
        assert EXPERIMENT_END == 26
        assert TASK_START == 27
        assert TASK_END == 28
        assert ERROR == 40  # Same as logging.ERROR

    def test_custom_log_levels_registered(self):
        """Test that custom log levels are registered with the logging module"""
        assert logging.getLevelName(EXPERIMENT_START) == "EXPERIMENT_START"
        assert logging.getLevelName(EXPERIMENT_END) == "EXPERIMENT_END"
        assert logging.getLevelName(TASK_START) == "TASK_START"
        assert logging.getLevelName(TASK_END) == "TASK_END"

    def test_error_level_matches_standard_error(self):
        """Test that ERROR level matches Python's standard logging.ERROR"""
        assert ERROR == logging.ERROR

    def test_context_keys_defined(self):
        """Test that context keys are defined as strings"""
        assert isinstance(CONTEXT_TASK_ID, str)
        assert isinstance(CONTEXT_APP_NAME, str)
        assert isinstance(CONTEXT_TOOL_NAME, str)
        assert isinstance(CONTEXT_COMPONENT, str)
        assert isinstance(CONTEXT_PHASE, str)

    def test_context_keys_values(self):
        """Test that context keys have the expected values"""
        assert CONTEXT_TASK_ID == "task_id"
        assert CONTEXT_APP_NAME == "app_name"
        assert CONTEXT_TOOL_NAME == "tool_name"
        assert CONTEXT_COMPONENT == "component"
        assert CONTEXT_PHASE == "phase"

    def test_log_message_patterns_defined(self):
        """Test that log message patterns are defined as strings"""
        assert isinstance(LOG_START, str)
        assert isinstance(LOG_COMPLETE, str)
        assert isinstance(LOG_ERROR, str)
        assert isinstance(LOG_SKIPPED, str)

    def test_log_message_patterns_have_format_placeholders(self):
        """Test that log message patterns have the expected format placeholders"""
        assert "{operation}" in LOG_START
        assert "{operation}" in LOG_COMPLETE
        assert "{operation}" in LOG_ERROR
        assert "{error}" in LOG_ERROR
        assert "{operation}" in LOG_SKIPPED
        assert "{reason}" in LOG_SKIPPED

    def test_log_message_formatting(self):
        """Test that log message patterns can be formatted correctly"""
        # Test LOG_START
        formatted = LOG_START.format(operation="test operation")
        assert "test operation" in formatted

        # Test LOG_COMPLETE
        formatted = LOG_COMPLETE.format(operation="test operation")
        assert "test operation" in formatted

        # Test LOG_ERROR
        formatted = LOG_ERROR.format(operation="test operation", error="test error")
        assert "test operation" in formatted
        assert "test error" in formatted

        # Test LOG_SKIPPED
        formatted = LOG_SKIPPED.format(operation="test operation", reason="test reason")
        assert "test operation" in formatted
        assert "test reason" in formatted

    def test_log_levels_ordering(self):
        """Test that custom log levels maintain the expected ordering"""
        # Standard Python log levels for reference
        # DEBUG = 10, INFO = 20, WARNING = 30, ERROR = 40, CRITICAL = 50

        # Our custom levels should be between INFO and WARNING
        assert logging.INFO < EXPERIMENT_START < logging.WARNING
        assert logging.INFO < EXPERIMENT_END < logging.WARNING
        assert logging.INFO < TASK_START < logging.WARNING
        assert logging.INFO < TASK_END < logging.WARNING

        # ERROR should be the same as logging.ERROR
        assert ERROR == logging.ERROR


if __name__ == "__main__":
    pytest.main()
