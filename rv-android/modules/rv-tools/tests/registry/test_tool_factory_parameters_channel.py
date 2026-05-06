"""Verify ToolFactory.create_tool forwards exactly `{**variant_defaults, **parameters}`.

gh55 INV-TOOL-25: `ToolFactory.create_tool(tool_config)` MUST forward
`tool_config.parameters` (merged on top of variant defaults) as the sole input
to `AbstractTool.configure(...)`. There is no other channel — no env reads, no
config-file reads, no other source — by which tool-specific config values reach
a tool plugin.

The factory lives at L2 in `rv_tools.registry.factory`; this test verifies the
contract there. Patches `os.environ` to a sentinel that would corrupt the result
if any consumer accidentally read it.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from rv_android_core.domain.task import ToolConfig
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_tools import ToolFactory, ToolRegistry


class _SpyTool(AbstractTool):
    """Minimal tool that records the exact dict it received in configure()."""

    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="_spy_tool",
        description="Test spy that records the configure() input.",
        url="https://example.invalid/spy",
        version="1.0.0",
        process_pattern="_spy",
    )

    def __init__(self):
        spec = self.get_tool_spec()
        super().__init__(name=spec.name, description=spec.description, process_pattern=spec.process_pattern)
        self.received_config = None

    @classmethod
    def get_tool_spec(cls):
        return cls.TOOL_SPEC

    @classmethod
    def get_variants(cls):
        return {
            "default": {"a": 1, "b": "default-b"},
            "fast": {"a": 9, "b": "fast-b", "extra": True},
        }

    def configure(self, config):
        self.received_config = dict(config)

    def execute_tool_specific_logic(self, task, app):
        pass


def _register_spy_once():
    registry = ToolRegistry.get_instance()
    if not registry.is_tool_registered("_spy_tool"):
        registry.register_tool_class(_SpyTool)


def test_factory_forwards_default_variant_when_no_parameters():
    _register_spy_once()
    factory = ToolFactory()
    tc = ToolConfig(name="_spy_tool", variant="default", parameters={})
    tool = factory.create_tool(tc)
    assert isinstance(tool, _SpyTool)
    assert tool.received_config == {"a": 1, "b": "default-b"}


def test_factory_forwards_parameters_overriding_variant_default():
    _register_spy_once()
    factory = ToolFactory()
    tc = ToolConfig(name="_spy_tool", variant="default", parameters={"a": 99})
    tool = factory.create_tool(tc)
    assert tool.received_config == {"a": 99, "b": "default-b"}


def test_factory_uses_named_variant_when_specified():
    _register_spy_once()
    factory = ToolFactory()
    tc = ToolConfig(name="_spy_tool", variant="fast", parameters={})
    tool = factory.create_tool(tc)
    assert tool.received_config == {"a": 9, "b": "fast-b", "extra": True}


def test_factory_does_not_inject_environment():
    """gh55 INV-TOOL-25: even with arbitrary RV_* / TOOLS_DIR / RVSEC_HOME set in
    os.environ, the factory MUST NOT include any of them in the merged dict
    forwarded to configure(). The dict is exactly {variant_defaults, parameters}.
    """
    _register_spy_once()
    factory = ToolFactory()
    sentinel_env = {
        "RV_TOOLS": "monkey",
        "RV_HUMANOID_URL": "http://leak.invalid:50405",
        "TOOLS_DIR": "/leak",
        "RVSEC_HOME": "/leak",
        "RV_PYDANTIC": "true",
    }
    with patch.dict(os.environ, sentinel_env, clear=False):
        tc = ToolConfig(name="_spy_tool", variant="default", parameters={"b": "explicit-b"})
        tool = factory.create_tool(tc)
    assert tool.received_config == {"a": 1, "b": "explicit-b"}
    # No env-derived keys leaked into the dict.
    for leaked_key in ("RV_TOOLS", "RV_HUMANOID_URL", "TOOLS_DIR", "RVSEC_HOME", "RV_PYDANTIC"):
        assert leaked_key not in tool.received_config


def test_factory_parameters_dict_is_independent_per_call():
    """Mutating one tool's received config must not affect a sibling call."""
    _register_spy_once()
    factory = ToolFactory()
    tc1 = ToolConfig(name="_spy_tool", variant="default", parameters={})
    tool1 = factory.create_tool(tc1)
    tool1.received_config["a"] = -1

    tc2 = ToolConfig(name="_spy_tool", variant="default", parameters={})
    tool2 = factory.create_tool(tc2)
    assert tool2.received_config == {"a": 1, "b": "default-b"}
