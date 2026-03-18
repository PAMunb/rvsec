"""
Test helpers for rv-tools tests.

FakeTool and FakeToolNoDefault are minimal AbstractTool subclasses used to test
registry and factory logic without coupling to real tool implementations.
"""

from typing import Any, Dict

from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec


class FakeTool(AbstractTool):
    """Minimal AbstractTool for testing registry/factory without device deps."""

    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="faketool",
        description="Fake tool for testing",
        url="https://example.com/faketool",
        version="1.0.0",
        process_pattern="faketool",
    )

    def __init__(self):
        spec = self.TOOL_SPEC
        super().__init__(
            name=spec.name,
            description=spec.description,
            process_pattern=spec.process_pattern,
        )
        self.config = {}

    @classmethod
    def get_tool_spec(cls) -> ToolSpec:
        return cls.TOOL_SPEC

    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "default": {"param_a": 10, "param_b": "hello"},
            "fast": {"param_a": 5, "param_b": "fast"},
            "stress": {"param_a": 100, "param_b": "stress"},
        }

    def configure(self, config: Dict[str, Any]) -> None:
        self.config = dict(config)

    def execute_tool_specific_logic(self, task, app) -> None:
        pass


class FakeToolNoDefault(AbstractTool):
    """Tool with no 'default' variant — used to test INV-TOOL-02 violation."""

    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="nodefault",
        description="Tool without default variant",
        url="https://example.com",
        version="1.0.0",
    )

    def __init__(self):
        spec = self.TOOL_SPEC
        super().__init__(
            name=spec.name,
            description=spec.description,
            process_pattern=spec.process_pattern or "",
        )
        self.config = {}

    @classmethod
    def get_tool_spec(cls) -> ToolSpec:
        return cls.TOOL_SPEC

    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        return {"only_variant": {"key": "value"}}

    def configure(self, config: Dict[str, Any]) -> None:
        self.config = dict(config)

    def execute_tool_specific_logic(self, task, app) -> None:
        pass
