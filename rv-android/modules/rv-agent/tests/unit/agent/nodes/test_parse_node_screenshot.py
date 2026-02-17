"""
Unit tests for parse_node conditional screenshot capture for error detection.

Tests that parse_ui_node captures a screenshot when the screen hash repeats
(same screen after action), which indicates a potential validation error
visible on screen.
"""

import logging
import pytest
from unittest.mock import MagicMock

from rv_agent.agent.nodes.parse_node import parse_ui_node


def _make_agent(error_detection_enabled=True):
    """Create a mock agent with screen_processor, device, and config."""
    agent = MagicMock()
    agent.config.error_detection_enabled = error_detection_enabled
    agent.config.package_name = "com.example.app"
    agent.device.take_screenshot.return_value = "/tmp/screenshot.png"
    # ui_coverage attribute for the register_screen_elements path
    agent.ui_coverage = MagicMock()
    return agent


def _make_screen_processor_result(screen_hash="hash_abc"):
    """Create a standard parse_current_screen return dict."""
    return {
        "screen_hash": screen_hash,
        "activity": "MainActivity",
        "screen_description": MagicMock(items=[]),
        "ui_elements_text": "1. Button 'Submit' at (200, 400) - bounds [[100, 350], [300, 450]]",
        "is_external": False,
        "external_navigation_count": 0,
        "ui_xml": "<hierarchy></hierarchy>",
    }


class TestParseNodeScreenshotCapture:
    """Tests for conditional screenshot capture in parse_ui_node."""

    def test_hash_repeats_and_detection_enabled_takes_screenshot(self):
        """When screen hash equals previous_screen_hash and detection is enabled,
        take_screenshot is called and the path is returned."""
        agent = _make_agent(error_detection_enabled=True)
        agent.screen_processor.parse_current_screen.return_value = (
            _make_screen_processor_result(screen_hash="same_hash")
        )

        state = {
            "external_navigation_count": 0,
            "previous_screen_hash": "same_hash",
        }

        result = parse_ui_node(agent, state)

        agent.device.take_screenshot.assert_called_once()
        assert result["error_detection_screenshot"] == "/tmp/screenshot.png"

    def test_hash_differs_no_screenshot(self):
        """When screen hash differs from previous, no screenshot is taken."""
        agent = _make_agent(error_detection_enabled=True)
        agent.screen_processor.parse_current_screen.return_value = (
            _make_screen_processor_result(screen_hash="new_hash")
        )

        state = {
            "external_navigation_count": 0,
            "previous_screen_hash": "old_hash",
        }

        result = parse_ui_node(agent, state)

        agent.device.take_screenshot.assert_not_called()
        assert result["error_detection_screenshot"] is None

    def test_detection_disabled_no_screenshot(self):
        """When error_detection_enabled is False, no screenshot is taken
        even if the hash repeats."""
        agent = _make_agent(error_detection_enabled=False)
        agent.screen_processor.parse_current_screen.return_value = (
            _make_screen_processor_result(screen_hash="same_hash")
        )

        state = {
            "external_navigation_count": 0,
            "previous_screen_hash": "same_hash",
        }

        result = parse_ui_node(agent, state)

        agent.device.take_screenshot.assert_not_called()
        assert result["error_detection_screenshot"] is None

    def test_screenshot_exception_caught(self, caplog):
        """When take_screenshot raises, the exception is caught, a warning
        is logged, and error_detection_screenshot is None."""
        agent = _make_agent(error_detection_enabled=True)
        agent.device.take_screenshot.side_effect = RuntimeError("Device disconnected")
        agent.screen_processor.parse_current_screen.return_value = (
            _make_screen_processor_result(screen_hash="same_hash")
        )

        state = {
            "external_navigation_count": 0,
            "previous_screen_hash": "same_hash",
        }

        with caplog.at_level(logging.WARNING):
            result = parse_ui_node(agent, state)

        assert result["error_detection_screenshot"] is None
        assert any(
            "Screenshot capture for error detection failed" in record.message
            for record in caplog.records
        )

    def test_screenshot_always_in_result_when_hash_repeats(self):
        """error_detection_screenshot key is present when hash repeats."""
        agent = _make_agent(error_detection_enabled=True)
        agent.screen_processor.parse_current_screen.return_value = (
            _make_screen_processor_result(screen_hash="same_hash")
        )

        state = {
            "external_navigation_count": 0,
            "previous_screen_hash": "same_hash",
        }

        result = parse_ui_node(agent, state)

        assert "error_detection_screenshot" in result
        assert result["error_detection_screenshot"] is not None

    def test_screenshot_always_in_result_when_hash_differs(self):
        """error_detection_screenshot key is present (as None) when hash differs."""
        agent = _make_agent(error_detection_enabled=True)
        agent.screen_processor.parse_current_screen.return_value = (
            _make_screen_processor_result(screen_hash="new_hash")
        )

        state = {
            "external_navigation_count": 0,
            "previous_screen_hash": "old_hash",
        }

        result = parse_ui_node(agent, state)

        assert "error_detection_screenshot" in result
        assert result["error_detection_screenshot"] is None

    def test_no_previous_hash_no_screenshot(self):
        """When there is no previous_screen_hash in state, no screenshot is taken."""
        agent = _make_agent(error_detection_enabled=True)
        agent.screen_processor.parse_current_screen.return_value = (
            _make_screen_processor_result(screen_hash="some_hash")
        )

        # No previous_screen_hash key in state
        state = {
            "external_navigation_count": 0,
        }

        result = parse_ui_node(agent, state)

        agent.device.take_screenshot.assert_not_called()
        assert result["error_detection_screenshot"] is None
