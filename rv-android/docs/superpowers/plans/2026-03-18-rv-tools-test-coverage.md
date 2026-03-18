# rv-tools Test Coverage Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Increase rv-tools test coverage from 13% to ~60%+ by testing registry, factory, and builtin tool registration/configuration — without modifying business code.

**Architecture:** Tests use a `FakeTool` (minimal `AbstractTool` subclass) for registry/factory unit tests, avoiding coupling to real tool implementations. Builtin integration tests import real tool classes to validate specs, variants, and configuration. All tests use `ToolRegistry.reset_instance()` in fixtures for isolation (INV-TOOL-01).

**Tech Stack:** pytest, rv-android-core (AbstractTool, ToolSpec, ToolConfig, exceptions)

**Traceability:** Each test docstring references the invariant (INV-TOOL-XX), requirement (FRXX), or scenario it verifies from `openspec/specs/tools/spec.md`.

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `modules/rv-tools/tests/conftest.py` | Shared fixtures: `FakeTool`, fresh registry, factory |
| Create | `modules/rv-tools/tests/test_registry.py` | ToolRegistry unit tests (INV-TOOL-01/02/03/04/13, FR18, FR20) |
| Create | `modules/rv-tools/tests/test_factory.py` | ToolFactory unit tests (INV-TOOL-05, FR18, FR20) |
| Create | `modules/rv-tools/tests/test_builtin_registration.py` | Builtin tool integration tests (INV-TOOL-02/04/08, FR19, FR20) |
| Keep | `modules/rv-tools/tests/test_basic.py` | Existing smoke tests (unchanged) |

---

## Chunk 1: Fixtures and Registry Tests

### Task 1: Shared Test Fixtures

**Files:**
- Create: `modules/rv-tools/tests/conftest.py`

- [ ] **Step 1: Create conftest.py with FakeTool and fixtures**

```python
"""
Shared fixtures for rv-tools tests.

FakeTool is a minimal AbstractTool subclass used to test registry and factory
logic without coupling to real tool implementations or device dependencies.
"""

import pytest
from typing import Any, Dict

from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_tools.registry.registry import ToolRegistry
from rv_tools.registry.factory import ToolFactory


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
```

- [ ] **Step 2: Verify fixtures load without errors**

Run: `uv run pytest modules/rv-tools/tests/conftest.py --collect-only`
Expected: no errors, fixtures discovered

- [ ] **Step 3: Commit**

```bash
git add modules/rv-tools/tests/conftest.py
git commit -m "test(rv-tools): add shared fixtures with FakeTool for registry/factory tests"
```

---

### Task 2: ToolRegistry Unit Tests

**Files:**
- Create: `modules/rv-tools/tests/test_registry.py`

- [ ] **Step 1: Write registry test file**

```python
"""
ToolRegistry unit tests.

Tests cover:
- INV-TOOL-01: Singleton behavior and reset_instance
- INV-TOOL-03: Unique names, re-registration replaces + logs warning
- INV-TOOL-13: get_variant_config returns copy, not reference
- FR18: Tool registration and retrieval
- FR20: Variant registration, listing, validation
"""

import pytest
from rv_android_core.util.error.exceptions import (
    ConfigurationError,
    ToolNotFoundError,
    ToolRegistrationError,
)
from rv_tools.registry.registry import ToolRegistry

from conftest import FakeTool, FakeToolNoDefault


class TestSingleton:
    """INV-TOOL-01: Singleton must return same instance across callers."""

    def test_same_instance(self, fresh_registry):
        """INV-TOOL-01: get_instance returns same object."""
        other = ToolRegistry.get_instance()
        assert fresh_registry is other

    def test_reset_creates_new_instance(self):
        """INV-TOOL-01: reset_instance allows a fresh registry."""
        first = ToolRegistry.get_instance()
        ToolRegistry.reset_instance()
        second = ToolRegistry.get_instance()
        assert first is not second
        ToolRegistry.reset_instance()


class TestToolRegistration:
    """FR18: Tool registration and retrieval."""

    def test_register_tool_class(self, fresh_registry):
        """FR18: register_tool_class stores class, spec, and variants."""
        fresh_registry.register_tool_class(FakeTool)

        assert fresh_registry.has_tool("faketool")
        assert fresh_registry.get_tool_class("faketool") is FakeTool
        assert fresh_registry.get_tool_spec("faketool").name == "faketool"

    def test_register_tool_class_registers_variants(self, fresh_registry):
        """FR18/FR20: register_tool_class auto-registers all variants."""
        fresh_registry.register_tool_class(FakeTool)

        variant_names = fresh_registry.get_tool_variants("faketool")
        assert "default" in variant_names
        assert "fast" in variant_names
        assert "stress" in variant_names

    def test_has_tool_false_for_unregistered(self, fresh_registry):
        """FR18: has_tool returns False for unknown tool."""
        assert not fresh_registry.has_tool("nonexistent")

    def test_is_tool_registered_alias(self, registry_with_fake):
        """FR18: is_tool_registered is alias for has_tool."""
        assert registry_with_fake.is_tool_registered("faketool")
        assert not registry_with_fake.is_tool_registered("nonexistent")

    def test_get_tool_names(self, registry_with_fake):
        """FR18: get_tool_names lists all registered tools."""
        names = registry_with_fake.get_tool_names()
        assert "faketool" in names

    def test_get_all_tool_names_alias(self, registry_with_fake):
        """FR18: get_all_tool_names is alias for get_tool_names."""
        assert registry_with_fake.get_all_tool_names() == registry_with_fake.get_tool_names()

    def test_get_tool_class_raises_for_unknown(self, fresh_registry):
        """FR18: get_tool_class raises ToolNotFoundError for unknown tool."""
        with pytest.raises(ToolNotFoundError):
            fresh_registry.get_tool_class("nonexistent")

    def test_get_tool_spec_raises_for_unknown(self, fresh_registry):
        """FR18: get_tool_spec raises ToolNotFoundError for unknown tool."""
        with pytest.raises(ToolNotFoundError):
            fresh_registry.get_tool_spec("nonexistent")


class TestReRegistration:
    """INV-TOOL-03: Re-registering a tool replaces previous and logs warning."""

    def test_re_registration_replaces(self, registry_with_fake):
        """INV-TOOL-03: duplicate name replaces tool class."""
        # Re-register with same class — should replace without error
        registry_with_fake.register_tool_class(FakeTool)
        assert registry_with_fake.get_tool_class("faketool") is FakeTool
        # Still only one entry
        assert registry_with_fake.get_tool_names().count("faketool") == 1


class TestVariants:
    """FR20: Variant registration, listing, validation, and retrieval."""

    def test_get_tool_variants(self, registry_with_fake):
        """FR20 scenario: listing variants for a registered tool."""
        variants = registry_with_fake.get_tool_variants("faketool")
        assert set(variants) == {"default", "fast", "stress"}

    def test_get_tool_variants_empty_for_unknown(self, fresh_registry):
        """FR20: get_tool_variants returns empty list for unknown tool."""
        assert fresh_registry.get_tool_variants("nonexistent") == []

    def test_validate_tool_variant_true(self, registry_with_fake):
        """FR20 scenario: validate_tool_variant returns True for valid combo."""
        assert registry_with_fake.validate_tool_variant("faketool", "fast")

    def test_validate_tool_variant_false(self, registry_with_fake):
        """FR20 scenario: validate_tool_variant returns False for invalid variant."""
        assert not registry_with_fake.validate_tool_variant("faketool", "nonexistent")

    def test_validate_tool_variant_false_unknown_tool(self, fresh_registry):
        """FR20: validate_tool_variant returns False for unknown tool."""
        assert not fresh_registry.validate_tool_variant("nonexistent", "default")

    def test_has_variant(self, registry_with_fake):
        """FR20: has_variant checks specific tool+variant combo."""
        assert registry_with_fake.has_variant("faketool", "default")
        assert registry_with_fake.has_variant("faketool", "fast")
        assert not registry_with_fake.has_variant("faketool", "nonexistent")
        assert not registry_with_fake.has_variant("nonexistent", "default")

    def test_get_variant_config(self, registry_with_fake):
        """FR20 scenario: get_variant_config returns complete parameters."""
        config = registry_with_fake.get_variant_config("faketool", "fast")
        assert config == {"param_a": 5, "param_b": "fast"}

    def test_get_variant_config_raises_for_unknown_tool(self, fresh_registry):
        """FR20: get_variant_config raises for unknown tool."""
        with pytest.raises((ConfigurationError, ToolNotFoundError)):
            fresh_registry.get_variant_config("nonexistent", "default")

    def test_get_variant_config_raises_for_unknown_variant(self, registry_with_fake):
        """FR20: get_variant_config raises for unknown variant."""
        with pytest.raises((ConfigurationError, ToolNotFoundError)):
            registry_with_fake.get_variant_config("faketool", "nonexistent")

    def test_register_variant_for_unregistered_tool_raises(self, fresh_registry):
        """FR20: cannot register variant for a tool that does not exist."""
        with pytest.raises((ToolRegistrationError, ToolNotFoundError)):
            fresh_registry.register_variant("nonexistent", "v1", {"key": "val"})


class TestVariantConfigIsCopy:
    """INV-TOOL-13: get_variant_config must return a copy, not a reference."""

    def test_mutation_does_not_affect_registry(self, registry_with_fake):
        """INV-TOOL-13: modifying returned dict must not change registry state."""
        config = registry_with_fake.get_variant_config("faketool", "fast")
        config["param_a"] = 99999
        config["injected"] = "hack"

        # Re-fetch — must be unchanged
        original = registry_with_fake.get_variant_config("faketool", "fast")
        assert original["param_a"] == 5
        assert "injected" not in original


class TestGetTool:
    """FR18: get_tool creates a configured tool instance."""

    def test_get_tool_default(self, registry_with_fake):
        """FR18: get_tool with default variant returns working instance."""
        tool = registry_with_fake.get_tool("faketool")
        assert tool.name == "faketool"

    def test_get_tool_raises_for_unknown(self, fresh_registry):
        """FR18: get_tool raises ToolNotFoundError for unknown tool."""
        with pytest.raises(ToolNotFoundError):
            fresh_registry.get_tool("nonexistent")


class TestGetAllTools:
    """FR18: get_all_tools creates instances of all registered tools."""

    def test_get_all_tools(self, registry_with_fake):
        """FR18: get_all_tools returns list with one tool instance."""
        tools = registry_with_fake.get_all_tools()
        assert len(tools) == 1
        assert tools[0].name == "faketool"

    def test_get_all_tools_empty(self, fresh_registry):
        """FR18: get_all_tools returns empty list when no tools registered."""
        tools = fresh_registry.get_all_tools()
        assert tools == []


class TestClearAndInfo:
    """Registry housekeeping: clear and get_registry_info."""

    def test_clear(self, registry_with_fake):
        """clear removes all tools and variants."""
        registry_with_fake.clear()
        assert registry_with_fake.get_tool_names() == []
        assert registry_with_fake.get_registry_info()["total_tools"] == 0

    def test_get_registry_info(self, registry_with_fake):
        """get_registry_info returns correct stats."""
        info = registry_with_fake.get_registry_info()
        assert info["total_tools"] == 1
        assert info["total_variants"] == 3  # default, fast, stress
        assert "faketool" in info["tools"]
        assert set(info["variants_by_tool"]["faketool"]) == {"default", "fast", "stress"}

    def test_get_registry_info_empty(self, fresh_registry):
        """get_registry_info on empty registry."""
        info = fresh_registry.get_registry_info()
        assert info["total_tools"] == 0
        assert info["total_variants"] == 0
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `uv run pytest modules/rv-tools/tests/test_registry.py -v`
Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add modules/rv-tools/tests/test_registry.py
git commit -m "test(rv-tools): add ToolRegistry tests — INV-TOOL-01/03/13, FR18, FR20"
```

---

### Task 3: ToolFactory Unit Tests

**Files:**
- Create: `modules/rv-tools/tests/test_factory.py`

- [ ] **Step 1: Write factory test file**

```python
"""
ToolFactory unit tests.

Tests cover:
- INV-TOOL-05: Factory must call configure() before returning
- FR18 scenario: Factory creates configured tool from ToolConfig
- FR18 scenario: Factory rejects invalid tool or variant
- FR20 scenario: Parameter overrides replace variant values
"""

import pytest
from unittest.mock import patch, MagicMock

from rv_android_core.domain.task import ToolConfig
from rv_android_core.util.error.exceptions import ConfigurationError
from rv_tools.registry.factory import ToolFactory

from conftest import FakeTool


class TestCreateTool:
    """FR18: Factory creates configured tool instances from ToolConfig."""

    def test_create_with_default_variant(self, factory):
        """FR18 scenario: create_tool with default variant applies default config."""
        tool_config = ToolConfig(name="faketool", variant="default", parameters={})
        tool = factory.create_tool(tool_config)

        assert isinstance(tool, FakeTool)
        assert tool.config["param_a"] == 10
        assert tool.config["param_b"] == "hello"

    def test_create_with_named_variant(self, factory):
        """FR18 scenario: create_tool with named variant applies variant config."""
        tool_config = ToolConfig(name="faketool", variant="fast", parameters={})
        tool = factory.create_tool(tool_config)

        assert isinstance(tool, FakeTool)
        assert tool.config["param_a"] == 5
        assert tool.config["param_b"] == "fast"

    def test_parameter_override(self, factory):
        """FR20 scenario: parameters override variant values."""
        tool_config = ToolConfig(
            name="faketool",
            variant="fast",
            parameters={"param_a": 999},
        )
        tool = factory.create_tool(tool_config)

        # param_a overridden, param_b preserved from variant
        assert tool.config["param_a"] == 999
        assert tool.config["param_b"] == "fast"

    def test_extra_parameter_added(self, factory):
        """FR20: extra parameters are merged into final config."""
        tool_config = ToolConfig(
            name="faketool",
            variant="default",
            parameters={"extra_key": "extra_value"},
        )
        tool = factory.create_tool(tool_config)

        assert tool.config["extra_key"] == "extra_value"
        # variant params still present
        assert tool.config["param_a"] == 10


class TestConfigureCalled:
    """INV-TOOL-05: Factory must call configure() before returning."""

    def test_configure_is_called(self, factory):
        """INV-TOOL-05: tool.configure(config) is called with merged config."""
        tool_config = ToolConfig(name="faketool", variant="stress", parameters={})
        tool = factory.create_tool(tool_config)

        # FakeTool.configure stores config — non-empty means it was called
        assert tool.config == {"param_a": 100, "param_b": "stress"}


class TestFactoryRejectsInvalid:
    """FR18 scenario: Factory rejects invalid tool or variant."""

    def test_rejects_unknown_tool(self, factory):
        """FR18 scenario: ConfigurationError for nonexistent tool."""
        tool_config = ToolConfig(name="nonexistent_tool", parameters={})
        with pytest.raises((ConfigurationError, Exception)):
            factory.create_tool(tool_config)

    def test_rejects_invalid_variant(self, factory):
        """FR18 scenario: ConfigurationError for invalid variant."""
        tool_config = ToolConfig(name="faketool", variant="invalid_variant", parameters={})
        with pytest.raises((ConfigurationError, Exception)):
            factory.create_tool(tool_config)


class TestFactoryInit:
    """ToolFactory initialization."""

    def test_factory_uses_provided_registry(self, registry_with_fake):
        """Factory uses the registry passed in constructor."""
        factory = ToolFactory(registry_with_fake)
        assert factory.registry is registry_with_fake

    def test_factory_default_registry(self):
        """Factory falls back to singleton registry when none provided."""
        factory = ToolFactory()
        assert factory.registry is not None
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `uv run pytest modules/rv-tools/tests/test_factory.py -v`
Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add modules/rv-tools/tests/test_factory.py
git commit -m "test(rv-tools): add ToolFactory tests — INV-TOOL-05, FR18, FR20"
```

---

## Chunk 2: Builtin Tool Integration Tests

### Task 4: Builtin Tool Registration and Spec/Variant Validation

**Files:**
- Create: `modules/rv-tools/tests/test_builtin_registration.py`

- [ ] **Step 1: Write builtin registration test file**

```python
"""
Builtin tool integration tests.

Tests cover:
- INV-TOOL-02: Every registered tool must have a "default" variant
- INV-TOOL-04: ToolSpec must have non-empty name, description, url, version
- INV-TOOL-08: Auto-registration must not fail module import
- FR19: 8 built-in tools registered correctly
- FR20: Each tool's variants match spec table
"""

import importlib

import pytest

from rv_tools.registry.registry import ToolRegistry
from rv_tools.builtin import BUILTIN_TOOLS


# Expected tools with their variant names (from spec FR20 table)
EXPECTED_TOOLS = {
    "monkey": {"default", "fast", "stress"},
    "droidbot": {"default", "dfs_greedy", "bfs_greedy", "dfs_naive", "bfs_naive", "random"},
    "ape": {"default", "sata", "bfs", "dfs", "random"},
    "fastbot": {"default", "conservative", "aggressive", "balanced"},
    "ares": {"default"},
    "droidmate": {"default"},
    "humanoid": {"default"},
    "qtesting": {"default"},
}

# All 8 expected tool names
EXPECTED_TOOL_NAMES = set(EXPECTED_TOOLS.keys())


@pytest.fixture(scope="module")
def builtin_registry():
    """Registry with all builtins registered (module-scoped for performance)."""
    ToolRegistry.reset_instance()
    registry = ToolRegistry.get_instance()
    for tool_class in BUILTIN_TOOLS:
        registry.register_tool_class(tool_class)
    yield registry
    ToolRegistry.reset_instance()


class TestAutoRegistration:
    """INV-TOOL-08: Auto-registration must not fail module import."""

    def test_import_rv_tools_succeeds(self):
        """INV-TOOL-08: importing rv_tools does not raise."""
        import rv_tools  # noqa: F401

    def test_builtin_tools_count(self):
        """FR19: BUILTIN_TOOLS contains exactly 8 tool classes."""
        assert len(BUILTIN_TOOLS) == 8


class TestAllToolsRegistered:
    """FR19: All 8 built-in tools are registered correctly."""

    def test_all_expected_tools_present(self, builtin_registry):
        """FR19: registry contains all 8 expected tools."""
        registered = set(builtin_registry.get_tool_names())
        assert EXPECTED_TOOL_NAMES.issubset(registered), (
            f"Missing tools: {EXPECTED_TOOL_NAMES - registered}"
        )


class TestToolSpecs:
    """INV-TOOL-04: Every ToolSpec must have non-empty name, description, url, version."""

    @pytest.mark.parametrize("tool_class", BUILTIN_TOOLS, ids=lambda c: c.__name__)
    def test_spec_fields_non_empty(self, tool_class):
        """INV-TOOL-04: ToolSpec fields are non-empty for {tool_class.__name__}."""
        spec = tool_class.get_tool_spec()
        assert spec.name, f"{tool_class.__name__}: name is empty"
        assert spec.description, f"{tool_class.__name__}: description is empty"
        assert spec.url, f"{tool_class.__name__}: url is empty"
        assert spec.version, f"{tool_class.__name__}: version is empty"

    @pytest.mark.parametrize("tool_class", BUILTIN_TOOLS, ids=lambda c: c.__name__)
    def test_spec_name_matches_registration(self, tool_class, builtin_registry):
        """FR19: spec.name matches the key used in registry."""
        spec = tool_class.get_tool_spec()
        assert builtin_registry.has_tool(spec.name)


class TestDefaultVariant:
    """INV-TOOL-02: Every registered tool must have a 'default' variant."""

    @pytest.mark.parametrize("tool_name", EXPECTED_TOOL_NAMES)
    def test_has_default_variant(self, tool_name, builtin_registry):
        """INV-TOOL-02: {tool_name} has a 'default' variant."""
        variants = builtin_registry.get_tool_variants(tool_name)
        assert "default" in variants, f"{tool_name} missing 'default' variant"


class TestVariantsMatchSpec:
    """FR20: Each tool's variants match the spec table."""

    @pytest.mark.parametrize(
        "tool_name,expected_variants",
        EXPECTED_TOOLS.items(),
        ids=lambda x: x if isinstance(x, str) else None,
    )
    def test_variants_present(self, tool_name, expected_variants, builtin_registry):
        """FR20: {tool_name} contains expected variants."""
        actual = set(builtin_registry.get_tool_variants(tool_name))
        assert expected_variants.issubset(actual), (
            f"{tool_name}: missing variants {expected_variants - actual}"
        )


class TestDroidBotPolicyValidation:
    """FR19 scenario: DroidBot rejects invalid policy in configure()."""

    def test_valid_policy_accepted(self, builtin_registry):
        """FR19 scenario: DroidBot accepts valid policy."""
        tool = builtin_registry.get_tool("droidbot")
        tool.configure({"policy": "dfs_greedy", "count": 10000000000})
        assert tool.config["policy"] == "dfs_greedy"
        assert tool.config["count"] == 10000000000

    def test_invalid_policy_rejected(self, builtin_registry):
        """FR19 scenario: DroidBot raises ConfigurationError for invalid policy."""
        from rv_android_core.util.error.exceptions import ConfigurationError

        tool = builtin_registry.get_tool("droidbot")
        with pytest.raises(ConfigurationError, match="invalid_policy"):
            tool.configure({"policy": "invalid_policy"})


class TestMonkeyConfiguration:
    """FR19: MonkeyTool configure applies parameters."""

    def test_configure_event_count(self, builtin_registry):
        """FR19: MonkeyTool.configure sets event_count."""
        tool = builtin_registry.get_tool("monkey")
        tool.configure({"event_count": 5000, "throttle": 100})
        assert tool.config["event_count"] == 5000
        assert tool.config["throttle"] == 100


class TestVariantConfigValues:
    """FR20 scenario: Variant config contains complete parameters."""

    def test_droidbot_dfs_greedy_config(self, builtin_registry):
        """FR20 scenario: droidbot:dfs_greedy has correct parameters."""
        config = builtin_registry.get_variant_config("droidbot", "dfs_greedy")
        assert config["policy"] == "dfs_greedy"
        assert config["count"] == 10000000000
        assert config["interval"] == 3
        assert config["ignore_ad"] is True

    def test_monkey_fast_config(self, builtin_registry):
        """FR20: monkey:fast has seed and reduced event count."""
        config = builtin_registry.get_variant_config("monkey", "fast")
        assert config["event_count"] == 500
        assert config["seed"] == 12345
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `uv run pytest modules/rv-tools/tests/test_builtin_registration.py -v`
Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add modules/rv-tools/tests/test_builtin_registration.py
git commit -m "test(rv-tools): add builtin registration tests — INV-TOOL-02/04/08, FR19, FR20"
```

---

### Task 5: Run Full Suite and Verify Coverage

- [ ] **Step 1: Run all rv-tools tests**

Run: `uv run pytest modules/rv-tools/tests/ -v`
Expected: all tests PASS (existing 3 + new tests)

- [ ] **Step 2: Check coverage**

Run: `uv run pytest modules/rv-tools/tests/ --cov=rv_tools --cov-report=term-missing --no-header -q 2>&1 | tail -25`
Expected: registry.py and factory.py coverage ~80%+

- [ ] **Step 3: Final commit with all files**

```bash
git add modules/rv-tools/tests/
git commit -m "test(rv-tools): complete test coverage for registry, factory, builtins

Covers INV-TOOL-01/02/03/04/05/08/13, FR18/FR19/FR20.
Registry: singleton, registration, variants, copy semantics.
Factory: create_tool, variant resolution, parameter override.
Builtins: 8 tools, specs, variants, DroidBot policy validation."
```
