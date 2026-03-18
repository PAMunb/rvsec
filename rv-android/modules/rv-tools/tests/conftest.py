"""
Shared fixtures for rv-tools tests.
"""

import pytest

from rv_tools.registry.registry import ToolRegistry
from rv_tools.registry.factory import ToolFactory
from helpers import FakeTool, FakeToolNoDefault


@pytest.fixture
def fake_tool_class():
    """Return the FakeTool class for direct use in tests."""
    return FakeTool


@pytest.fixture
def fake_tool_no_default_class():
    """Return the FakeToolNoDefault class for direct use in tests."""
    return FakeToolNoDefault


@pytest.fixture
def fresh_registry():
    """Provide a clean ToolRegistry for each test (INV-TOOL-01: reset_instance for testing)."""
    ToolRegistry.reset_instance()
    registry = ToolRegistry.get_instance()
    yield registry
    ToolRegistry.reset_instance()


@pytest.fixture
def registry_with_fake(fresh_registry):
    """Registry with FakeTool already registered."""
    fresh_registry.register_tool_class(FakeTool)
    return fresh_registry


@pytest.fixture
def factory(registry_with_fake):
    """ToolFactory backed by a registry containing FakeTool."""
    return ToolFactory(registry_with_fake)
