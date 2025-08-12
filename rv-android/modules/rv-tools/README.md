# RV-Tools Module

Tool registry and management system for Android application testing tools.

## Overview

The RV-Tools module provides a centralized tool management system for Android testing tools within the RV-Android framework. It implements a registry-based architecture for tool discovery, registration, and instantiation with support for tool variants and parameter configuration.

### Key Features

- **Tool Registry**: Centralized tool discovery and management with variant support
- **Tool Factory**: Tool instantiation with configuration and variant resolution
- **Plugin System**: Extensible architecture for external tool integration
- **Built-in Tools**: Collection of Android testing tools with predefined variants
- **Configuration Management**: Tool parameter and variant configuration with automatic merging
- **Tool Specification DSL**: Flexible tool specification format supporting variants
- **Variant System**: Comprehensive variant management with automatic registration and resolution

## Architecture

### Core Components

#### Registry Infrastructure
- **ToolRegistry**: Singleton registry for tool management with variant support and automatic registration
- **ToolFactory**: Factory for creating configured tool instances with variant resolution
- **PluginLoader**: Plugin discovery and loading system with variant-aware registration

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
tool_names = registry.get_all_tool_names()
print(f"Available tools: {tool_names}")

# List tool variants
for tool_name in tool_names[:3]:  # Show first 3 tools
    variants = registry.get_tool_variants(tool_name)
    print(f"{tool_name}: {list(variants.keys())}")

# Create tool instances with variants
from rv_android_core.domain.task import ToolConfig

# Create tool configuration with variant
tool_config = ToolConfig(
    tool_name="droidbot",
    variant="dfs_greedy",
    additional_params={"count": 1000}
)

# Create tool using factory
factory = ToolFactory()
tool = factory.create_tool(tool_config)
```

### Variant Management

```python
from rv_tools.registry.registry import ToolRegistry

registry = ToolRegistry.get_instance()

# Check if tool is registered
if registry.is_tool_registered("droidbot"):
    print("DroidBot is registered")

# Get available variants for a tool
variants = registry.get_tool_variants("droidbot")
print(f"DroidBot variants: {list(variants.keys())}")

# Get specific variant configuration
config = registry.get_variant_config("droidbot", "dfs_greedy")
print(f"DFS Greedy config: {config}")

# Validate tool and variant combination
is_valid = registry.validate_tool_variant("droidbot", "dfs_greedy")
print(f"DroidBot with DFS Greedy is valid: {is_valid}")
```

### Tool Creation with Variants

```python
from rv_tools.registry.factory import ToolFactory
from rv_android_core.domain.task import ToolConfig

factory = ToolFactory()

# Create tool with default variant
tool_config_default = ToolConfig(
    tool_name="ape",
    variant="default",
    additional_params={}
)
ape_tool = factory.create_tool(tool_config_default)

# Create tool with specific variant and parameters
tool_config_custom = ToolConfig(
    tool_name="droidbot",
    variant="dfs_greedy", 
    additional_params={"count": 2000, "interval": 1}
)
droidbot_tool = factory.create_tool(tool_config_custom)

# Create RVAndroid tool with typed configuration
rvandroid_config = ToolConfig(
    tool_name="rvandroid",
    variant="default",
    additional_params={
        "llm_type": "ollama",
        "llm_model": "llama3.2",
        "prompt_strategy": "standard_modular"
    }
)
rvandroid_tool = factory.create_tool(rvandroid_config)
```

## Built-in Tools

### Android Monkey
- **Description**: UI/Application exerciser generating pseudo-random user events
- **Variants**: default, fast, stress (predefined configurations with different event counts and timeouts)
- **Parameters**: event_count, seed, throttle, package_whitelist
- **Capabilities**: random_testing, stress_testing

### DroidBot
- **Description**: Lightweight test input generator for Android applications
- **Variants**: default, dfs_greedy, bfs_greedy, dfs_naive, bfs_naive, random (different exploration policies)
- **Parameters**: count, interval, timeout, policy
- **Capabilities**: systematic_testing, state_modeling

### APE (Android Programmatic Events)  
- **Description**: CEGAR-based model abstraction testing tool for systematic exploration
- **Variants**: default, sata, bfs, dfs, random (different exploration strategies)
- **Parameters**: running_minutes, strategy, device_serial
- **Capabilities**: model_based_testing, systematic_exploration

### FastBot
- **Description**: Model-based testing tool with reinforcement learning capabilities
- **Variants**: conservative, aggressive, balanced, model_based
- **Parameters**: max_step, throttle, learning_rate, exploration_rate
- **Capabilities**: model_based_testing, reinforcement_learning

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

## Tool Development

### Creating Tools with Variant Support

1. **Implement AbstractTool Interface with Variant Methods**:
```python
from rv_android_core.tools.abstract_tool import AbstractTool
from typing import Dict, Any

class MyTool(AbstractTool):
    """Custom testing tool with variant support."""
    
    def __init__(self, tool_spec=None):
        super().__init__(tool_spec or {
            "name": "mytool",
            "description": "Custom testing tool",
            "process_pattern": "mytool"
        })
        # Tool-specific configuration attributes
        self.exploration_depth = 10
        self.timeout_multiplier = 1.0
    
    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        """Define tool variants with different configurations."""
        return {
            "default": {
                "exploration_depth": 10,
                "timeout_multiplier": 1.0,
                "mode": "standard"
            },
            "thorough": {
                "exploration_depth": 50,
                "timeout_multiplier": 2.0,
                "mode": "comprehensive"
            },
            "quick": {
                "exploration_depth": 5,
                "timeout_multiplier": 0.5,
                "mode": "fast"
            }
        }
    
    def configure(self, variant_config: Dict[str, Any]) -> None:
        """Configure tool with variant-specific parameters."""
        self.exploration_depth = variant_config.get("exploration_depth", 10)
        self.timeout_multiplier = variant_config.get("timeout_multiplier", 1.0)
        self.mode = variant_config.get("mode", "standard")
        
        self.logger.info(f"Configured {self.name} with variant parameters: "
                        f"depth={self.exploration_depth}, "
                        f"timeout_mult={self.timeout_multiplier}, "
                        f"mode={self.mode}")
    
    def get_tool_spec(self) -> Dict[str, Any]:
        """Return tool specification for registry."""
        return {
            "name": self.name,
            "description": self.description,
            "process_pattern": self.process_pattern,
            "supported_platforms": ["android"],
            "requires_emulator": True,
            "version": "1.0.0"
        }
    
    def execute_tool_specific_logic(self, task, app):
        """Implement tool-specific execution logic."""
        self.logger.info(f"Starting {self.name} execution for {app.package_name}")
        self.logger.info(f"Using configuration: depth={self.exploration_depth}, "
                        f"mode={self.mode}")
        
        # Build tool command with variant-specific configuration
        command = self._build_tool_command(task, app)
        
        # Execute with centralized error handling
        with open(task.result.trace_file, 'wb') as trace_file:
            result = self._execute_and_check_command(command, stdout=trace_file)
        
        self.logger.info(f"{self.name} execution completed successfully")
    
    def _build_tool_command(self, task, app):
        """Build tool-specific command with variant configuration."""
        from rv_android_core.commands.command import Command
        
        # Adjust timeout based on variant configuration
        adjusted_timeout = int(task.config.timeout * self.timeout_multiplier)
        
        # Build command arguments based on variant
        args = [
            app.apk_path,
            "--depth", str(self.exploration_depth),
            "--mode", self.mode
        ]
        
        return Command("mytool", args, timeout=adjusted_timeout)
```

2. **Register Tool with Automatic Variant Registration**:
```python
from rv_tools.registry.registry import ToolRegistry

# Register tool class - variants are automatically registered
registry = ToolRegistry.get_instance()
registry.register_tool_class(MyTool)

# Verify registration
print(f"Tool registered: {registry.is_tool_registered('mytool')}")
variants = registry.get_tool_variants("mytool")
print(f"Available variants: {list(variants.keys())}")
```

3. **Create Tool with Variant**:
```python
from rv_tools.registry.factory import ToolFactory
from rv_android_core.domain.task import ToolConfig

# Create tool configuration with variant
tool_config = ToolConfig(
    tool_name="mytool",
    variant="thorough",  # Use thorough variant
    additional_params={"custom_param": "value"}
)

# Create tool instance
factory = ToolFactory()
tool = factory.create_tool(tool_config)

# Tool will be automatically configured with thorough variant parameters
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
from rv_android_core.util.error.exceptions import ToolNotFoundError, ToolRegistrationError

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