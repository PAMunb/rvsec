
from unittest.mock import MagicMock, patch

import pytest

from rv_llm.llm.prompt.information.base_fragment import InformationFragment
from rv_llm.llm.prompt.information.fragment_manager import InformationManager


@pytest.fixture
def manager_instance():
    """Fixture to create an InformationManager instance."""
    return InformationManager()


@pytest.fixture
def mock_fragment_factory():
    """Factory fixture to create mock InformationFragment instances."""

    def _factory(name, priority, content):
        fragment = MagicMock(spec=InformationFragment)
        fragment.name = name
        fragment.priority = priority
        fragment.get_info.return_value = {name: content}
        return fragment

    return _factory


class TestInformationManagerRegistration:
    """Tests for fragment registration and unregistration."""

    def test_register_fragment(self, manager_instance, mock_fragment_factory):
        """Test that a single fragment can be registered."""
        fragment = mock_fragment_factory("frag1", 100, "content1")
        manager_instance.register_fragment(fragment)
        assert manager_instance.get_fragment("frag1") == fragment

    def test_register_fragments(self, manager_instance, mock_fragment_factory):
        """Test that multiple fragments can be registered at once."""
        fragments = [
            mock_fragment_factory("frag1", 100, "c1"),
            mock_fragment_factory("frag2", 200, "c2"),
        ]
        manager_instance.register_fragments(fragments)
        assert manager_instance.get_fragment("frag1") is not None
        assert manager_instance.get_fragment("frag2") is not None

    def test_unregister_fragment(self, manager_instance, mock_fragment_factory):
        """Test that a fragment can be unregistered."""
        fragment = mock_fragment_factory("frag1", 100, "c1")
        manager_instance.register_fragment(fragment)
        assert manager_instance.get_fragment("frag1") is not None

        manager_instance.unregister_fragment("frag1")
        assert manager_instance.get_fragment("frag1") is None


class TestInformationManagerComposition:
    """Tests for the compose_information method."""

    def test_compose_information_sorted_by_priority(self, manager_instance, mock_fragment_factory):
        """Test that fragments are composed in priority order."""
        frag1 = mock_fragment_factory("frag1", 100, "content1")
        frag2 = mock_fragment_factory("frag2", 200, "content2")
        manager_instance.register_fragments([frag1, frag2])

        sorted_fragments = manager_instance._get_sorted_fragments()
        assert sorted_fragments[0].name == "frag2"  # Higher priority first
        assert sorted_fragments[1].name == "frag1"

    def test_compose_information_with_all_fragments(self, manager_instance, mock_fragment_factory):
        """Test composing information from all registered fragments."""
        frag1 = mock_fragment_factory("frag1", 100, "content1")
        frag2 = mock_fragment_factory("frag2", 200, "content2")
        manager_instance.register_fragments([frag1, frag2])

        composed_info = manager_instance.compose_information(state={})
        assert composed_info == {"frag1": "content1", "frag2": "content2"}

    def test_compose_information_with_requested_fragments(self, manager_instance, mock_fragment_factory):
        """Test composing information from a specific subset of fragments."""
        frag1 = mock_fragment_factory("frag1", 100, "content1")
        frag2 = mock_fragment_factory("frag2", 200, "content2")
        manager_instance.register_fragments([frag1, frag2])

        composed_info = manager_instance.compose_information(
            state={},
            requested_fragments=["frag1"]
        )
        assert composed_info == {"frag1": "content1"}
        assert "frag2" not in composed_info

    def test_compose_information_handles_fragment_error(self, manager_instance, mock_fragment_factory):
        """Test that an error in one fragment does not stop composition."""
        frag1 = mock_fragment_factory("frag1", 100, "content1")
        frag2 = mock_fragment_factory("frag2", 200, "content2")
        frag2.get_info.side_effect = Exception("Fragment error")
        manager_instance.register_fragments([frag1, frag2])

        with patch.object(manager_instance, "error_handler") as mock_error_handler:
            composed_info = manager_instance.compose_information(state={})
            assert composed_info == {"frag1": "content1"}
            mock_error_handler.handle_error.assert_called_once()
