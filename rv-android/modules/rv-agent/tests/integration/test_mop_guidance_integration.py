"""
Integration tests for MOP guidance in LLM prompts (gh26 Group 9, task 9.3).

Verifies NavigationGuidance.format_for_llm() produces MOP-specific hints
when static analysis data is available.
"""

import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass

from rv_agent.services.navigation_guidance import NavigationGuidance


@dataclass
class MockMopDescription:
    """Mock MOP description for testing."""

    element_text: str
    class_name: str
    method_name: str
    directly_reaches: bool


class TestMopGuidanceWithStaticData:
    """Verify LLM prompt contains MOP-specific hints from NavigationGuidance."""

    def test_format_for_llm_includes_mop_descriptions(self):
        """format_for_llm includes element-to-MOP-method mapping."""
        guidance = NavigationGuidance()

        # Create a context with MOP descriptions
        context = MagicMock()
        context.has_guidance = True
        context.unvisited_screens = []
        context.priority_targets = ["CryptoActivity"]
        context.mop_descriptions = [
            MockMopDescription(
                element_text="Encrypt",
                class_name="javax.crypto.Cipher",
                method_name="init",
                directly_reaches=True,
            ),
            MockMopDescription(
                element_text="Generate Key",
                class_name="javax.crypto.KeyGenerator",
                method_name="generateKey",
                directly_reaches=False,
            ),
        ]
        context.suggested_actions = []
        context.coverage_percent = 45.0

        result = guidance.format_for_llm(context)

        assert "Navigation guidance:" in result
        assert "Encrypt" in result
        assert "Cipher" in result
        assert "directly calls" in result
        assert "Generate Key" in result
        assert "reaches" in result

    def test_format_for_llm_empty_without_static_data(self):
        """format_for_llm returns empty string when no guidance available."""
        guidance = NavigationGuidance()

        context = MagicMock()
        context.has_guidance = False

        result = guidance.format_for_llm(context)

        assert result == ""
