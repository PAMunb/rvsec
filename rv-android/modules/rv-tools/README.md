# RV-Tools Module

Tool registry and plugin system for monitored operations testing in RV-Android.

## Overview

The RV-Tools module provides comprehensive tool management capabilities for the RV-Android monitored operations framework, enabling seamless integration of various testing tools through a sophisticated plugin architecture.

### Key Features

- **Plugin Architecture**: Extensible system for external tool registration
- **Built-in Tools**: Standard testing tools (APE, Monkey, DroidBot, etc.)
- **Configuration Management**: Rich configuration and variant support
- **Tool Registry**: Centralized tool discovery and management
- **Factory Pattern**: Consistent tool creation and configuration

## Architecture

### Core Components

#### Base Classes (from rv-android-core)
- **AbstractTool**: Base abstraction for all testing tools (rv_android_core.tools)
- **ConfigurableTool**: Enhanced tool base with configuration support (rv_android_core.tools)
- **ToolSpec**: Tool specification and metadata management (rv_android_core.tools)

#### Registry System
- **ToolRegistry**: Central registry for tool discovery and access
- **ToolFactory**: Factory for creating configured tool instances
- **PluginLoader**: Plugin discovery and loading system

#### Plugin System
- **ToolPlugin**: Interface for external tool plugins
- **PluginManager**: Lifecycle management for plugins
- **ExperimentToolManager**: Tool coordination for experiments

### Tool Categories

#### Built-in Tools
- **Random Testing**: Monkey
- **Model-Based**: APE, DroidBot, DroidMate
- **AI-Guided**: Fastbot, Humanoid, QTesting
- **Systematic**: DroidMate

#### External Tools (Plugins)
- **RVAndroid**: AI-driven testing with LLM guidance
- **RVDroid**: UIAutomator2-based testing with AI integration

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

# Install in development mode
poetry install --extras dev
```

## Usage

### Basic Tool Usage

```python
from rv_tools import ToolRegistry, ToolFactory
from rv_android_core.tools import AbstractTool, ConfigurableTool, ToolSpec

# Get tool registry instance
registry = ToolRegistry.get_instance()

# List available tools
tools = registry.get_all_tools()
print(f"Available tools: {[tool.name for tool in tools]}")

# Create a configured tool
ape_tool = ToolFactory.create_tool_from_spec("ape:sata@strategy=bfs")
monkey_tool = ToolFactory.create_tool_from_spec("monkey@event_count=10000")
```

### Built-in Tool Examples

#### APE Tool
```python
from rv_tools.builtin.ape import APETool

# Create APE tool with default configuration
ape = APETool()

# Configure for BFS strategy
ape.configure({
    "strategy": "bfs",
    "running_minutes": 10
})

# Execute on an app
ape.execute(task, app)
```

#### Monkey Tool
```python
from rv_tools.builtin.monkey import MonkeyTool

# Create Monkey tool
monkey = MonkeyTool()

# Configure for stress testing
monkey.configure({
    "event_count": 50000,
    "seed": 123,
    "throttle": 100,
    "ignore_crashes": True,
    "event_percentages": {
        "touch": 70,
        "motion": 20,
        "nav": 10
    }
})

# Execute testing
monkey.execute(task, app)
```

### Tool Specifications

Tools can be specified using a flexible string format:

```
tool_name[:variant1][:variant2][@param1=value1,param2=value2]
```

Examples:
- `ape` - Basic APE tool
- `ape:sata` - APE with SATA strategy variant
- `monkey@event_count=10000` - Monkey with custom event count
- `ape:bfs@running_minutes=5` - APE with BFS strategy and 5-minute timeout

## Built-in Tools

### APE (Android Programmatic Events)
- **Category**: Model-Based Testing
- **Description**: CEGAR-based model abstraction refinement
- **Strategies**: sata, bfs, dfs, random
- **Capabilities**: model_based_testing, state_space_exploration, abstraction_refinement

### Monkey
- **Category**: Random Testing  
- **Description**: Pseudo-random user event generation
- **Event Types**: touch, motion, trackball, syskeys, nav, majornav, appswitch
- **Capabilities**: random_testing, stress_testing, event_generation, crash_detection

### DroidBot (To be migrated)
- **Category**: Model-Based Testing
- **Description**: Lightweight UI-guided testing framework

### Other Tools
Additional tools (DroidMate, Fastbot, Humanoid, QTesting, ARES) are available as placeholders and will be migrated from the rvandroid module.

## Plugin Development

### Creating External Tool Plugins

1. **Implement ToolPlugin Interface**:
```python
from rv_tools.interfaces.plugin_interface import ToolPlugin

class MyToolPlugin(ToolPlugin):
    def get_tool_name(self) -> str:
        return "mytool"
    
    def get_tool_class(self) -> type:
        return MyTool
    
    def register_tool(self, registry) -> None:
        tool = MyTool()
        registry.register_tool(tool)
```

2. **Register via Entry Points** (pyproject.toml):
```toml
[tool.poetry.plugins."rv_tools.plugins"]
mytool = "mypackage.plugin:MyToolPlugin"
```

3. **Tool Discovery**: Tools are automatically discovered and registered when the plugin system initializes.

## Configuration

### Tool Configuration Structure

```python
config = {
    "timeout": 300,                    # Execution timeout
    "device_id": "emulator-5554",      # Target device
    "tool_specific_param": "value",    # Tool-specific parameters
    "nested": {                        # Nested configuration
        "param": "value"
    }
}
```

### Configuration Access

```python
# Get configuration values with dot notation
value = tool.get_config_value("nested.param", default="default_value")

# Set configuration values
tool.set_config_value("timeout", 600)

# Check if configuration exists
if tool.has_config("device_id"):
    device = tool.get_config_value("device_id")
```

## Testing

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=rv_tools

# Run specific test categories
poetry run pytest tests/test_builtin_tools.py
```

### Test Structure

```
tests/
├── base/
│   ├── test_abstract_tool.py
│   ├── test_configurable_tool.py
│   └── test_tool_spec.py
├── builtin/
│   ├── test_ape_tool.py
│   └── test_monkey_tool.py
├── registry/
│   ├── test_registry.py
│   └── test_factory.py
└── interfaces/
    └── test_plugin_interface.py
```

## Contributing

### Code Standards

- Follow PEP 8 guidelines
- Use type hints for all public interfaces
- Include comprehensive docstrings following Google style
- Maintain architectural comment patterns consistent with other modules

### Tool Development Guidelines

- Extend AbstractTool or ConfigurableTool for new tools
- Follow the established naming and structure conventions
- Integrate with ErrorHandler and LoggingManager infrastructure
- Provide comprehensive tool specifications with capabilities
- Include proper test coverage for all tool functionality

### Adding New Built-in Tools

1. Create tool package in `src/rv_tools/builtin/toolname/`
2. Implement tool class extending ConfigurableTool
3. Add tool specification with appropriate capabilities
4. Create comprehensive tests
5. Update builtin package imports and registrations

## License

This module is part of the RV-Android project and follows the same licensing terms.