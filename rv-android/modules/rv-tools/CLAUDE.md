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
│       ├── humanoid/            # Humanoid (computer vision + NLP)
│       ├── monkey/              # Android Monkey (random events)
│       └── qtesting/            # QTesting (Q-learning based)
├── tests/
│   └── test_basic.py            # Basic registry and factory tests
├── pyproject.toml               # Poetry configuration
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
- Merges variant config with additional params
- Special handling for RVAndroid typed configuration

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
| **ARES** | Docker-based systematic exploration | default |
| **DroidMate** | JAR-based research tool | default |
| **Humanoid** | CV + NLP based testing | default |
| **QTesting** | Q-learning exploration | default |

## Dependencies

```toml
[tool.poetry.dependencies]
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
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run with coverage
poetry run pytest --cov=src --cov-report=term-missing
```

### Test Categories

| File | Purpose |
|------|---------|
| `tests/test_basic.py` | Registry initialization and singleton behavior |

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
    tool_name="droidbot",
    variant="dfs_greedy",
    additional_params={"count": 2000}
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
