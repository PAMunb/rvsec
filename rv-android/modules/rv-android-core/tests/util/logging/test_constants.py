# tests/util/logging/test_constants.py
import logging

import pytest
from rv_android_core.util.logging.constants import (  # Standard context keys; Common log message patterns
    CONTEXT_APP_NAME,
    CONTEXT_COMPONENT,
    CONTEXT_PHASE,
    CONTEXT_TASK_ID,
    CONTEXT_TOOL_NAME,
    ERROR,
    LOG_COMPLETE,
    LOG_ERROR,
    LOG_SKIPPED,
    LOG_START,
)


class TestLoggingConstants:
    """Tests for logging constants module"""

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
        assert "{phase}" in LOG_START
        assert "{phase}" in LOG_COMPLETE
        assert "{phase}" in LOG_ERROR
        assert "{error}" in LOG_ERROR
        assert "{phase}" in LOG_SKIPPED
        assert "{reason}" in LOG_SKIPPED

    def test_log_message_formatting(self):
        """Test that log message patterns can be formatted correctly"""
        # Test LOG_START
        formatted = LOG_START.format(phase="test operation")
        assert "test operation" in formatted

        # Test LOG_COMPLETE
        formatted = LOG_COMPLETE.format(phase="test operation")
        assert "test operation" in formatted

        # Test LOG_ERROR
        formatted = LOG_ERROR.format(phase="test operation", error="test error")
        assert "test operation" in formatted
        assert "test error" in formatted

        # Test LOG_SKIPPED
        formatted = LOG_SKIPPED.format(phase="test operation", reason="test reason")
        assert "test operation" in formatted
        assert "test reason" in formatted


if __name__ == "__main__":
    pytest.main()
