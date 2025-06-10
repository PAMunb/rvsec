# RV-Tools Module

Modern tool registry and plugin system for Android application testing with dependency injection architecture and comprehensive tool management.

## Overview

The RV-Tools module provides a sophisticated tool management infrastructure for the RV-Android system, enabling seamless integration of various Android testing tools through a modern plugin architecture. The module implements DI-ready patterns with comprehensive tool registration, discovery, and lifecycle management capabilities.

### Key Features

- **Modern Plugin Architecture**: Extensible DI-ready system for external tool registration with lifecycle management
- **Comprehensive Tool Registry**: Centralized tool discovery, registration, and management with metadata support
- **Built-in Tool Collection**: Production-ready testing tools (APE, ARES) with configuration variants
- **Factory Pattern**: Consistent tool creation and configuration with dependency injection support
- **Configuration Management**: Rich configuration system with validation and type safety
- **Tool Specification DSL**: Advanced tool specification language for flexible tool parameterization

## Architecture

### Core Components

#### Registry Infrastructure
- **ToolRegistry**: Modern centralized registry with DI support for tool discovery, registration, and lifecycle management
- **ToolFactory**: Advanced factory for creating configured tool instances with dependency injection
- **PluginLoader**: Sophisticated plugin discovery and loading system with automatic registration

#### Plugin System
- **IPluginInterface**: DI-ready interface for external tool plugins with lifecycle support
- **PluginRegistry**: Plugin management system with dependency resolution and validation
- **ToolMetadata**: Rich metadata system for tool capabilities, requirements, and configuration schemas

#### Tool Infrastructure (from rv-android-core)
- **AbstractTool**: Base abstraction for all testing tools with error handling integration
- **ConfigurableTool**: Enhanced tool base with comprehensive configuration support and validation
- **ToolSpec**: Tool specification and metadata management with capability declarations

### Tool Categories

#### Built-in Tools (Production Ready)
- **APE (Android Programmatic Events)**: Advanced model-based testing with CEGAR abstraction refinement
- **ARES**: Containerized testing environment with Docker integration for isolated execution

#### External Tools (Plugin Architecture)
- **AI-Driven Tools**: Support for LLM-guided testing tools through plugin interface
- **Third-Party Integration**: Extensible plugin system for custom and commercial testing tools
- **Legacy Tool Migration**: Framework for migrating existing tools to modern architecture

### Integration Points

- **rv-android-core**: Uses AbstractTool, ConfigurableTool, ErrorHandler decorators, and LoggingManager
- **rv-experiment**: Provides tool registry and factory for experiment orchestration and tool coordination
- **Plugin Ecosystem**: Supports external plugins through standardized interfaces and lifecycle management

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

### Modern Tool Registry Usage

```python
from rv_tools.registry import ToolRegistry, ToolFactory
from rv_android_core.tools import AbstractTool, ConfigurableTool, ToolSpec

# Get singleton tool registry instance
registry = ToolRegistry.get_instance()

# List all available tools with metadata
tools = registry.get_all_tools()
print(f"Available tools: {[tool.name for tool in tools]}")

# Get tools by capability
model_based_tools = registry.get_tools_by_capability("model_based_testing")
ai_guided_tools = registry.get_tools_by_capability("ai_guided")

# Create configured tools using factory
ape_tool = ToolFactory.create_tool_from_spec("ape:sata@strategy=bfs,timeout=300")
ares_tool = ToolFactory.create_tool_from_spec("ares@container_config=standard")

# Get tool information and capabilities
tool_info = registry.get_tool_info("ape")
print(f"APE capabilities: {tool_info.capabilities}")
print(f"APE variants: {tool_info.variants}")
```

### Built-in Tool Examples

#### APE Tool (Advanced Model-Based Testing)
```python
from rv_tools.builtin.ape import APETool

# Create APE tool through registry
registry = ToolRegistry.get_instance()
ape = registry.create_tool("ape")

# Configure for advanced model-based testing
ape.configure({
    "strategy": "sata",           # SATA abstraction refinement
    "running_minutes": 15,        # Extended execution time
    "model_checking": True,       # Enable model checking
    "abstraction_level": "medium" # Abstraction granularity
})

# Execute with comprehensive monitoring
result = ape.execute(task, app)
print(f"Coverage achieved: {result.coverage_metrics}")
```

#### ARES Tool (Containerized Testing)
```python
from rv_tools.builtin.ares import ARESTool

# Create ARES tool for isolated testing
ares = ARESTool()

# Configure Docker-based testing environment
ares.configure({
    "container_image": "ares:latest",
    "memory_limit": "2G",
    "cpu_limit": "2",
    "network_isolation": True,
    "volume_mounts": {
        "/data": "/host/data"
    },
    "environment_vars": {
        "ANDROID_HOME": "/opt/android-sdk"
    }
})

# Execute in isolated container
result = ares.execute(task, app)
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
- **Category**: Advanced Model-Based Testing
- **Description**: Sophisticated CEGAR-based model abstraction refinement with state space exploration
- **Strategies**: sata, bfs, dfs, random, hybrid
- **Capabilities**: model_based_testing, state_space_exploration, abstraction_refinement, formal_verification
- **Container Support**: Native execution with optional Docker isolation
- **Integration**: Full rv-android-core error handling and logging integration

### ARES (Android Runtime Evaluation System)
- **Category**: Containerized Testing Environment
- **Description**: Docker-based isolated testing environment for secure and reproducible testing
- **Features**: Container orchestration, resource management, network isolation, volume mounting
- **Capabilities**: containerized_testing, isolation, resource_control, security_testing
- **Integration**: Advanced configuration management and lifecycle control

### Tool Migration Status
- **Current**: APE and ARES are production-ready with full modern architecture integration
- **Planned**: Migration of additional tools (DroidBot, Monkey, etc.) to plugin architecture
- **Plugin Support**: External tools can be integrated through standardized plugin interfaces

## Plugin Development

### Creating Modern Tool Plugins

1. **Implement DI-Ready Plugin Interface**:
```python
from rv_tools.interfaces.plugin_interface import IPluginInterface
from rv_android_core.tools import ConfigurableTool
from rv_android_core.util.error.decorators import handle_errors

class MyToolPlugin(IPluginInterface):
    def get_tool_name(self) -> str:
        return "mytool"
    
    def get_tool_class(self) -> type:
        return MyTool
    
    def get_tool_metadata(self) -> Dict[str, Any]:
        return {
            "name": "mytool",
            "description": "Custom testing tool",
            "capabilities": ["custom_testing", "ai_guided"],
            "variants": ["standard", "enhanced"],
            "configuration_schema": {
                "timeout": {"type": "int", "default": 300},
                "mode": {"type": "str", "choices": ["fast", "thorough"]}
            }
        }
    
    @handle_errors(component="MyToolPlugin", operation="register")
    def register_tool(self, registry) -> None:
        tool = MyTool()
        registry.register_tool(tool, self.get_tool_metadata())

class MyTool(ConfigurableTool):
    def __init__(self):
        super().__init__(
            name="mytool",
            description="Custom testing tool with modern architecture",
            process_pattern="com.mytool"
        )
    
    @handle_errors(component="MyTool", operation="execute")
    def execute_tool_specific_logic(self, task, app):
        # Tool implementation with full error handling
        with self.logger.with_context(app_name=app.name):
            return self._run_custom_testing(task, app)
```

2. **Register via Entry Points** (pyproject.toml):
```toml
[tool.poetry.plugins."rv_tools.plugins"]
mytool = "mypackage.plugin:MyToolPlugin"
```

3. **Automatic Discovery**: Tools are automatically discovered, validated, and registered with full metadata support when the plugin system initializes.

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