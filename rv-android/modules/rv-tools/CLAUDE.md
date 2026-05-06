# CLAUDE.md - rv-tools

## Purpose

The rv-tools module provides a centralized tool registry and plugin system for Android application testing tools within the RV-Android framework. It manages tool discovery, registration, instantiation, and configuration with comprehensive support for tool variants.

Key responsibilities:
- **Tool Registry**: Central repository for testing tool classes and specifications
- **Tool Factory**: Creates configured tool instances with variant resolution
- **Built-in Tools**: Collection of 8 Android testing tools with predefined variants
- **Plugin System**: Extensible architecture for external tool integration
- **Variant Management**: Tool configuration presets for different testing scenarios

## Architecture

### Design Patterns

1. **Singleton Pattern**: `ToolRegistry` uses singleton pattern for centralized tool management
2. **Factory Pattern**: `ToolFactory` creates configured tool instances from `ToolConfig` specifications
3. **Registry Pattern**: Tools register themselves with metadata and variants at module import
4. **Template Method**: `AbstractTool` defines standard execution workflow for all tools

### Tool Registration Flow

```
Module Import
     |
     v
_register_builtin_tools()
     |
     v
ToolRegistry.register_tool_class(tool_class)
     |
     +-> tool_class.get_tool_spec() -> ToolSpec
     +-> tool_class.get_variants() -> Dict[str, Dict]
     |
     v
Registry stores: tool_classes, tool_specs, variants
```

### Tool Creation Flow

```
ToolConfig (name, variant, params)
     |
     v
ToolFactory.create_tool(tool_config)
     |
     +-> Resolve tool class from registry
     +-> Get variant configuration
     +-> Merge with additional params
     +-> Create tool instance
     +-> Call tool.configure(merged_config)
     |
     v
Configured AbstractTool instance
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| `ToolRegistry` | `registry/registry.py` | Singleton registry storing tool classes, specs, and variants |
| `ToolFactory` | `registry/factory.py` | Creates configured tool instances from ToolConfig |
| `AbstractTool` | rv-android-core | Base class for all testing tools (imported) |
| `ToolSpec` | rv-android-core | Tool metadata and specification (imported) |
| Built-in Tools | `builtin/*/tool.py` | 8 Android testing tool implementations |

### Registry Storage

```python
class ToolRegistry:
    tool_classes: Dict[str, Type[AbstractTool]]  # tool_name -> class
    tool_specs: Dict[str, ToolSpec]               # tool_name -> specification
    variants: Dict[str, Dict[str, Dict[str, Any]]]  # tool_name -> variant_name -> config
```

## Directory Structure

```
rv-tools/
├── src/rv_tools/
│   ├── __init__.py              # Module entry, auto-registers built-in tools
│   ├── registry/
│   │   ├── __init__.py          # Exports ToolRegistry, ToolFactory
│   │   ├── registry.py          # ToolRegistry singleton
│   │   └── factory.py           # ToolFactory with variant support
│   └── builtin/
│       ├── __init__.py          # BUILTIN_TOOLS list, tool imports
│       ├── ape/                 # APE tool (CEGAR-based exploration)
│       ├── ares/                # ARES tool (Docker-based, systematic)
│       ├── droidbot/            # DroidBot (policy-based exploration)
│       ├── droidmate/           # DroidMate (JAR-based, research)
│       ├── fastbot/             # FastBot (reinforcement learning)
│       ├── humanoid/            # Humanoid (DroidBot + inference server)
│       ├── monkey/              # Android Monkey (random events)
│       └── qtesting/            # QTesting (Docker-based Q-learning)
├── tests/
│   ├── conftest.py              # Test fixtures and registry setup
│   ├── helpers.py               # Test helper utilities
│   ├── test_basic.py            # Registry initialization and singleton behavior
│   ├── test_builtin_registration.py  # Auto-registration of 8 built-in tools
│   ├── test_factory.py          # Factory creation and variant resolution
│   └── test_registry.py         # Registry operations (register, query, validate)
├── pyproject.toml               # Project configuration
└── README.md                    # Detailed documentation
```

## Key Files

### Registry Core

**`src/rv_tools/registry/registry.py`** - Central tool registry
- `ToolRegistry.get_instance()` - Get singleton instance
- `register_tool_class(tool_class)` - Register tool with automatic variant registration
- `get_tool(tool_name, variant)` - Get configured tool instance
- `get_tool_variants(tool_name)` - List available variants
- `get_variant_config(tool_name, variant_name)` - Get variant configuration

**`src/rv_tools/registry/factory.py`** - Tool factory
- `ToolFactory.create_tool(tool_config)` - Create tool from ToolConfig
- Resolves variants from registry
- Merges variant config with tool parameters

### Tool Implementation Pattern

Each built-in tool follows this structure:

```python
class SomeTool(AbstractTool):
    TOOL_SPEC = ToolSpec.create_builtin_spec(...)

    @classmethod
    def get_tool_spec(cls) -> ToolSpec:
        return cls.TOOL_SPEC

    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        return {"default": {...}, "variant1": {...}}

    def configure(self, config: Dict[str, Any]) -> None:
        # Apply configuration to tool

    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        # Tool-specific execution
```

## Built-in Tools

| Tool | Description | Key Variants |
|------|-------------|--------------|
| **Monkey** | Pseudo-random event generation | default, fast, stress |
| **DroidBot** | Policy-based UI exploration | dfs_greedy, bfs_greedy, random |
| **APE** | CEGAR model abstraction | default, sata, bfs, dfs |
| **FastBot** | Reinforcement learning | conservative, aggressive, balanced |
| **ARES** | Docker-based systematic exploration (spawns a sibling container) | default |
| **DroidMate** | JAR-based research tool | default |
| **Humanoid** | DroidBot with Humanoid inference server (`-humanoid <url>`) for human-like input generation. Stateless TensorFlow inference — one server instance can be shared across many concurrent containers (Phase 0 finding, gh55) — container-per-APK isolation is unnecessary. | default |
| **QTesting** | Docker-based Q-learning exploration (spawns a QTesting container) | default |

### Docker Network Configuration (INV-TOOL-15)

ARES and QTesting are Docker-based tools that spawn sibling containers. Inside Docker (`/.dockerenv` exists), the sibling uses `--network container:$(hostname)` to share the parent's network namespace. Outside Docker, `--network host` is used.

### Variant-default pattern for per-tool URLs/paths (gh55 INV-TOOL-20, INV-TOOL-25)

L2 tool plugins (this module's `builtin/`, plus `aperv-tool` and
`rvagent-tool`) MUST NOT read environment variables. The canonical default
for any per-tool URL, path, or image name lives in `get_variants()` —
matching the ARES (`ares/tool.py:79` `docker_image`) and QTesting
(`qtesting/tool.py:67`) precedents. The factory merge
`{**variant_defaults, **tool_config.parameters}` guarantees the key is
present at `configure(config)` time. L5 (`rv-experiment`) overrides via
`ToolConfig.parameters` when an env var or CLI flag is set.

Example — Humanoid (canonical implementation):

```python
@classmethod
def get_variants(cls) -> Dict[str, Dict[str, Any]]:
    return {
        "default": {
            "policy": "dfs_greedy",
            "humanoid_url": "127.0.0.1:50405",  # variant default
            ...
        }
    }

def configure(self, config: Dict[str, Any]) -> None:
    self.url = config["humanoid_url"]   # always present after factory merge
    # No os.environ access. No literal fallback. No KeyError on the
    # standard local case — variant default carries through.
```

ADR rationale: `docs/adr/0001-env-var-pattern.md` (decision D8).

## Dependencies

```toml
[project.dependencies]
python = ">=3.12,<4.0"
rv-android-core = {path = "../rv-android-core", develop = true}
pydantic = "^2.9.0"
```

**From rv-android-core:**
- `AbstractTool` - Base class for all tools
- `ToolSpec` - Tool specification model
- `ErrorHandler` - Centralized error handling
- `LoggingManager` - Standardized logging
- `Command` - Command execution abstraction
- Exception classes: `ToolNotFoundError`, `ToolRegistrationError`, `ConfigurationError`

## Testing

```bash
# Run all tests
cd modules/rv-tools
uv run pytest

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing
```

### Test Categories

| File | Purpose |
|------|---------|
| `tests/test_basic.py` | Registry initialization and singleton behavior |
| `tests/test_registry.py` | Registry operations (register, query, validate, clear) |
| `tests/test_factory.py` | Factory creation and variant resolution |
| `tests/test_builtin_registration.py` | Auto-registration of 8 built-in tools |

## Common Tasks

### List Available Tools

```python
from rv_tools import ToolRegistry

registry = ToolRegistry.get_instance()
tool_names = registry.get_tool_names()
print(f"Available tools: {tool_names}")
```

### Get Tool Variants

```python
variants = registry.get_tool_variants("droidbot")
# Returns: ['default', 'dfs_greedy', 'bfs_greedy', 'dfs_naive', 'bfs_naive', 'random']
```

### Create Tool with Variant

```python
from rv_tools import ToolFactory
from rv_android_core.domain.task import ToolConfig

tool_config = ToolConfig(
    name="droidbot",
    variant="dfs_greedy",
    parameters={"count": 2000}
)

factory = ToolFactory()
tool = factory.create_tool(tool_config)
```

### Register Custom Tool

```python
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec

class MyTool(AbstractTool):
    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="mytool",
        description="My custom tool",
        url="https://example.com",
        version="1.0.0",
        process_pattern="mytool"
    )

    @classmethod
    def get_tool_spec(cls):
        return cls.TOOL_SPEC

    @classmethod
    def get_variants(cls):
        return {
            "default": {"param": "value"},
            "fast": {"param": "fast_value"}
        }

    def configure(self, config):
        self.param = config.get("param", "default")

    def execute_tool_specific_logic(self, task, app):
        # Implementation
        pass

# Register
registry = ToolRegistry.get_instance()
registry.register_tool_class(MyTool)
```

### Validate Tool and Variant

```python
# Check if tool exists
if registry.is_tool_registered("droidbot"):
    # Check if variant is valid
    if registry.validate_tool_variant("droidbot", "dfs_greedy"):
        config = registry.get_variant_config("droidbot", "dfs_greedy")
```

## Integration Points

- **rv-experiment**: Uses ToolRegistry for experiment tool selection
- **rv-platform**: Uses ToolFactory to create tools for task execution
- **rv-agent**: Registered as a tool through rv-platform (not in rv-tools builtin)


## Development Notes

This module is part of the RV-Android uv workspace. All modules are installed in **editable mode** via the root `pyproject.toml`.

**Key points:**
- Run `uv sync` from the project root to install all modules
- Source code changes are reflected immediately (no reinstall needed)
- Only reinstall if `pyproject.toml` dependencies change

```bash
# From project root
uv sync             # Install/update all modules (also removes unused packages)
```

