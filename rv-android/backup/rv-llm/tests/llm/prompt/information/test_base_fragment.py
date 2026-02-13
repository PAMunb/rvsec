
from unittest.mock import MagicMock, patch

import pytest

from rv_llm.llm.prompt.information.base_fragment import InformationFragment


# Concrete implementation for testing
class ConcreteFragment(InformationFragment):
    def generate(self, state, context=None):
        if state.get("error"):
            raise ValueError("Test error")
        return f"Generated content for {self.name}"

    def should_include(self, state, context=None):
        return state.get("include", True)


@pytest.fixture
def fragment_instance():
    """Fixture to create a ConcreteFragment instance."""
    return ConcreteFragment("test_fragment", priority=50)


class TestInformationFragmentInitialization:
    """Tests for the initialization of the InformationFragment."""

    def test_initialization(self, fragment_instance):
        """Test that the fragment is initialized with the correct attributes."""
        assert fragment_instance.name == "test_fragment"
        assert fragment_instance.priority == 50
        assert hasattr(fragment_instance, "logger")
        assert hasattr(fragment_instance, "error_handler")


class TestInformationFragmentGetInfo:
    """Tests for the get_info method."""

    def test_get_info_when_included(self, fragment_instance):
        """Test that get_info returns data when should_include is True."""
        state = {"include": True}
        info = fragment_instance.get_info(state)
        assert info == {"test_fragment": "Generated content for test_fragment"}

    def test_get_info_when_not_included(self, fragment_instance):
        """Test that get_info returns an empty dict when should_include is False."""
        state = {"include": False}
        info = fragment_instance.get_info(state)
        assert info == {}

    def test_get_info_handles_generation_error(self, fragment_instance):
        """Test that get_info handles exceptions during generation and returns an empty dict."""
        state = {"error": True}
        with patch.object(fragment_instance, "error_handler") as mock_error_handler:
            info = fragment_instance.get_info(state)
            assert info == {}
            mock_error_handler.handle_error.assert_called_once()

    def test_get_info_when_generate_returns_none(self, fragment_instance):
        """Test that get_info returns an empty dict when generate returns None."""
        with patch.object(fragment_instance, "generate", return_value=None):
            state = {"include": True}
            info = fragment_instance.get_info(state)
            assert info == {}
