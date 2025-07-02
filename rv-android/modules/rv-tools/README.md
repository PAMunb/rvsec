# RV-Tools Module

Tool registry and management system for Android application testing tools.

## Overview

The RV-Tools module provides a centralized tool management system for Android testing tools within the RV-Android framework. It implements a registry-based architecture for tool discovery, registration, and instantiation with support for tool variants and parameter configuration.

### Key Features

- **Tool Registry**: Centralized tool discovery and management
- **Tool Factory**: Tool instantiation with configuration support
- **Plugin System**: Extensible architecture for external tool integration
- **Built-in Tools**: Collection of Android testing tools
- **Configuration Management**: Tool parameter and variant configuration
- **Tool Specification DSL**: Flexible tool specification format

## Architecture

### Core Components

#### Registry Infrastructure
- **ToolRegistry**: Singleton registry for tool management
- **ToolFactory**: Factory for creating configured tool instances
- **PluginLoader**: Plugin discovery and loading system

#### Tool Infrastructure
- **AbstractTool**: Base class for all testing tools (from rv-android-core)
- **ToolSpec**: Tool specification and metadata
- **Plugin Interface**: Interface for external tool plugins

### Integration Points

- **rv-android-core**: Uses AbstractTool, ErrorHandler, and LoggingManager
- **rv-experiment**: Provides tool registry for experiment orchestration
- **rv-platform**: Tool integration for platform execution

## Installation

### Prerequisites

- Python 3.12+
- Poetry for dependency management
- rv-android-core module

### Setup

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest
```

## Usage

### Tool Registry Usage

```python
from rv_tools.registry.registry import ToolRegistry
from rv_tools.registry.factory import ToolFactory

# Get registry instance
registry = ToolRegistry.get_instance()

# List available tools
tool_names = registry.get_tool_names()
print(f"Available tools: {tool_names}")

# Create tool instances
tool = ToolFactory.create_tool_from_spec("monkey", registry)
tool_with_params = ToolFactory.create_tool_from_spec("droidbot:bfs_greedy@count=1000", registry)
```

### Tool Specification Format

Tools can be specified using a flexible string format:

```
tool_name[:variant1][:variant2][@param1=value1,param2=value2]
```

Examples:
- `monkey` - Basic Monkey tool
- `droidbot:bfs_greedy` - DroidBot with BFS greedy policy
- `ape@running_minutes=10` - APE with 10-minute timeout
- `droidbot:dfs_greedy@count=2000,seed=42` - DroidBot with DFS policy and parameters

### Batch Tool Creation

```python
# Create multiple tools from specifications
tools = ToolFactory.batch_create_tools([
    "monkey@event_count=1000",
    "droidbot:bfs_greedy",
    "ape@running_minutes=5"
], registry)
```

## Built-in Tools

### Android Monkey
- **Description**: UI/Application exerciser generating pseudo-random user events
- **Parameters**: event_count, seed, throttle, package_whitelist
- **Capabilities**: random_testing, stress_testing

### DroidBot
- **Description**: Lightweight test input generator for Android applications
- **Variants**: bfs_greedy, dfs_greedy, bfs_naive, dfs_naive, random
- **Parameters**: count, interval, timeout, policy
- **Capabilities**: systematic_testing, state_modeling

### APE (Android Programmatic Events)
- **Description**: Model-based testing tool with state space exploration
- **Parameters**: running_minutes, strategy, ape_timeout
- **Capabilities**: model_based_testing, state_exploration

### Fastbot
- **Description**: Model-based testing tool developed by Bytedance
- **Parameters**: max_running_minutes, throttle, activity_blacklist
- **Capabilities**: model_based_testing, intelligent_exploration

### DroidMate
- **Description**: GUI testing tool for Android applications
- **Parameters**: exploration_timeout, reset_every_nth_exploration
- **Capabilities**: systematic_testing, gui_exploration

### ARES
- **Description**: Automated security testing framework
- **Parameters**: timeout, analysis_depth
- **Capabilities**: security_testing, vulnerability_analysis

### QTesting
- **Description**: Q-learning based testing tool
- **Parameters**: episode_count, epsilon, learning_rate
- **Capabilities**: reinforcement_learning, adaptive_testing

### Humanoid
- **Description**: Learning-based Android testing tool
- **Parameters**: test_count, model_path
- **Capabilities**: learning_based_testing, human_like_interaction

## Plugin Development

### Creating Tool Plugins

1. **Implement Plugin Interface**:
```python
from rv_tools.interfaces.plugin_interface import ToolPlugin
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec

class MyToolPlugin(ToolPlugin):
    def get_plugin_name(self) -> str:
        return "mytool_plugin"
    
    def get_tool_names(self) -> List[str]:
        return ["mytool"]
    
    def get_tool_spec(self, tool_name: str) -> ToolSpec:
        return ToolSpec(
            name="mytool",
            description="Custom testing tool",
            url="https://github.com/example/mytool",
            version="1.0.0"
        )
    
    def get_tool_class(self, tool_name: str) -> Type[AbstractTool]:
        return MyTool
    
    def register_tools(self, registry) -> None:
        registry.register_tool("mytool", MyTool, self.get_tool_spec("mytool"))

class MyTool(AbstractTool):
    def __init__(self, name="mytool", description="Custom tool", process_pattern=None):
        super().__init__(name, description, process_pattern or "mytool.*")
    
    def execute_tool_specific_logic(self, task, app):
        # Tool implementation
        pass
```

2. **Register via Entry Points** (pyproject.toml):
```toml
[tool.poetry.plugins."rv_tools.plugins"]
mytool = "mypackage.plugin:MyToolPlugin"
```

## Configuration

### Tool Configuration Structure

```python
config = {
    "timeout": 300,
    "device_id": "emulator-5554",
    "tool_specific_param": "value",
    "nested": {
        "param": "value"
    }
}

# Configure tool
tool.configure(config)
```

### Variant Registration

```python
# Register tool variants
registry.register_variant("mytool", "fast", {"timeout": 60})
registry.register_variant("mytool", "thorough", {"timeout": 1800, "depth": 10})

# Create tool with variant
tool = ToolFactory.create_tool_from_spec("mytool:fast", registry)
```

## Testing

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest tests/test_main_functionalities.py
```

### Test Structure

```
tests/
├── fixtures/
│   └── mock_tools.py          # Mock tool implementations
├── test_main_functionalities.py  # Main functionality tests
└── conftest.py                # Test configuration
```

## Integration Examples

### With rv-experiment

```python
# Tool specifications in experiment configuration
tool_configs = [
    {"name": "monkey", "variants": [], "parameters": {"event_count": 1000}},
    {"name": "droidbot", "variants": ["bfs_greedy"], "parameters": {"count": 2000}}
]

# Automatic tool creation in experiment
for config in tool_configs:
    spec = f"{config['name']}"
    if config['variants']:
        spec += f":{':'.join(config['variants'])}"
    if config['parameters']:
        params = ','.join([f"{k}={v}" for k, v in config['parameters'].items()])
        spec += f"@{params}"
    
    tool = ToolFactory.create_tool_from_spec(spec, registry)
```

### With rv-platform

```python
# Platform tool listing
available_tools = registry.get_all_tools()
for tool in available_tools:
    print(f"Tool: {tool.name}")
    
    # Get tool variants
    variants = registry.get_tool_variants(tool.name)
    if variants and len(variants) > 1:
        variant_list = [v for v in variants if v != 'default']
        if variant_list:
            print(f"  Variants: {', '.join(variant_list)}")
```

## Contributing

### Code Standards

- Follow PEP 8 guidelines
- Use type hints for public interfaces
- Include docstrings following Google style
- Maintain consistency with rv-android-core patterns

### Tool Development Guidelines

- Extend AbstractTool for new tools
- Use ToolSpec for tool metadata
- Integrate with ErrorHandler and LoggingManager
- Include comprehensive test coverage
- Follow established naming conventions

### Adding New Built-in Tools

1. Create tool module in `src/rv_tools/builtin/toolname/`
2. Implement tool class extending AbstractTool
3. Add tool registration in builtin `__init__.py`
4. Create comprehensive tests
5. Update documentation

## Error Handling

The module integrates with rv-android-core error handling:

```python
from rv_android_core.util.exceptions import ToolNotFoundError, ToolRegistrationError

try:
    tool = registry.get_tool("nonexistent_tool")
except ToolNotFoundError as e:
    print(f"Tool not found: {e}")

try:
    ToolFactory.create_tool_from_spec("invalid:spec", registry)
except ToolRegistrationError as e:
    print(f"Tool creation failed: {e}")
```

## License

This module is part of the RV-Android project and follows the same licensing terms.