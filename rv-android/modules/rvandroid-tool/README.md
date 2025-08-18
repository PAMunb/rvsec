# RVAndroid-Tool Module

AI-driven Android testing tool with LLM integration, screenshot analysis, and action generation for monitored operations testing.

## Overview

The RVAndroid-Tool module provides an AI-driven testing implementation that combines Large Language Model integration with Android UI analysis to generate testing actions. It serves as a concrete tool implementation for AI-guided testing in the RV-Android ecosystem, implementing comprehensive architecture patterns with error handling, memory management, and multi-provider LLM support.

### Key Features

- **LLM Integration**: Integration with multiple language model providers using rv-llm component factory for Ollama, OpenAI, Anthropic, and other providers
- **Screenshot Analysis**: UI analysis with action recommendation, visual element detection, and context interpretation
- **Memory Management**: Multi-layered memory systems with long-term pattern learning, short-term context retention, and state transition tracking
- **Action Generation**: Context-aware Android action generation with constraint handling, semantic understanding, and goal-oriented planning
- **State Analysis**: UI state understanding with transition planning, pattern recognition, and testing strategies
- **Tool Configuration**: Flexible configuration system with parser, visitor, and LLM settings separation
- **Variant System**: Predefined variants with different LLM and prompt configurations for various testing scenarios

## Architecture

### Core Components

#### LLM Service Layer
- **LLMActionService**: Orchestrates AI-driven test action generation using PromptFramework
- **LLMManager**: Language model orchestration and configuration management
- **ActionGenerator**: Action planning and optimization with DroidBot integration
- **ResponseProcessor**: LLM response parsing and validation with error handling
- **StateEnricher**: Context enhancement with historical and static analysis data

#### Memory Management
- **MemoryManager**: Memory coordination and persistence with activity tracking
- **LongTermMemory**: Persistent storage for learned patterns and testing strategies
- **ShortTermMemory**: Session-based context and action history management
- **TransitionManager**: State transition tracking and navigation guidance

#### Configuration Management
- **RvAndroidToolConfig**: Configuration through composition of LLMConfig and PromptConfig
- **Template Management**: Tool-specific template registration with PromptFramework
- **Multi-instance Support**: Independent configuration for parallel tool execution
- **Variant Management**: Predefined variants with automatic configuration resolution

### Integration Points

- **rv-llm**: Uses PromptFramework, LLMConfig, PromptConfig, and LLMComponentFactory for language model integration
- **rv-screen-parser**: Integrates screen parsing capabilities using ScreenParserType and VisitorType constants
- **rv-android-core**: Uses ErrorHandler decorators, LoggingManager, EventBus, and domain models for infrastructure
- **rv-experiment**: Provides AI-driven testing capabilities for experiment orchestration
- **rv-static-analysis**: Integrates static analysis data for context and action planning
- **rv-coverage**: Coordinates with coverage tracking for testing optimization

## Installation

### Prerequisites

- Python 3.12+
- Poetry for dependency management
- rv-android-core, rv-llm, and rv-screen-parser modules
- LLM provider access (Ollama, OpenAI API key, etc.)
- Android SDK and emulator for testing

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

### Basic LLM Action Service

```python
from rvandroid_tool.llm.service.action_service import LLMActionService
from rvandroid_tool.config.tool_config import RvAndroidToolConfig
from rv_llm.config import LLMConfig, PromptConfig
from rv_llm.llm.constants import LLMType, PromptStrategyType
from rv_screen_parser.constants import ScreenParserType, VisitorType
from rv_android_core.domain.static import StaticAnalysisData

# Create LLM configuration
llm_config = LLMConfig(
    llm_type=LLMType.OLLAMA,
    model="llama3.2:3b",
    temperature=0.2,
    max_tokens=800
)

# Create prompt configuration
prompt_config = PromptConfig(
    strategy_type=PromptStrategyType.BATCH_ACTION,
    parser_type=ScreenParserType.DROIDBOT,
    visitor_type=VisitorType.DETAILED
)

# Create unified tool configuration
tool_config = RvAndroidToolConfig(
    llm_config=llm_config,
    prompt_config=prompt_config,
    server_port=8080,
    debug_mode=True
)

# Initialize service
static_data = StaticAnalysisData({})
service = LLMActionService(
    static_data=static_data,
    tool_config=tool_config,
    app_package="com.example.app"
)

# Process application state
state = {
    "package_name": "com.example.app",
    "activity": "MainActivity",
    "screen": {"components": [...]}
}

actions = service.process_state(state)
```

### Variant System Usage

```python
from rvandroid_tool.tools.rvandroid.tool import RVAndroidTool

# Get available variants
variants = RVAndroidTool.get_variants()
print("Available variants:")
for variant_name, variant_config in variants.items():
    print(f"  {variant_name}: {variant_config}")

# Create tool with variant using factory
from rv_tools.registry.factory import ToolFactory
from rv_android_core.domain.task import ToolConfig

tool_config = ToolConfig(
    tool_name="rvandroid",
    variant="default",  # or "openai_gpt4", "multimodal", etc.
    additional_params={"custom_param": "value"}
)

factory = ToolFactory()
rvandroid_tool = factory.create_tool(tool_config)

# Configuration created from variant
tool_config = rvandroid_tool.tool_config
print(f"LLM Type: {tool_config.llm_config.llm_type}")
print(f"Model: {tool_config.llm_config.model}")
print(f"Strategy: {tool_config.prompt_config.strategy_type}")
```

### Predefined Variants

The RVAndroid tool includes several predefined variants:

```python
VARIANTS = {
    "default": {
        "llm_type": "ollama",
        "llm_model": "llama3.2",
        "prompt_strategy": "single",
        "temperature": 0.2,
        "max_tokens": 1000
    },
    "openai_gpt4": {
        "llm_type": "openai", 
        "llm_model": "gpt-4",
        "prompt_strategy": "batch",
        "temperature": 0.1,
        "max_tokens": 1500
    },
    "multimodal": {
        "llm_type": "ollama",
        "llm_model": "llava",
        "prompt_strategy": "vision",
        "temperature": 0.3,
        "max_tokens": 800
    }
}
```

### Tool Configuration

```python
from rvandroid_tool.config.tool_config import RvAndroidToolConfig
from rv_llm.config import LLMConfig, PromptConfig
from rv_llm.llm.constants import LLMType, PromptStrategyType
from rv_screen_parser.constants import ScreenParserType, VisitorType

# Create configuration components
llm_config = LLMConfig(
    llm_type=LLMType.OLLAMA,
    model="llama3.2:3b",
    temperature=0.2,
    max_tokens=800
)

prompt_config = PromptConfig(
    strategy_type=PromptStrategyType.STANDARD,
    parser_type=ScreenParserType.DROIDBOT,
    visitor_type=VisitorType.DETAILED
)

# Create tool configuration through composition
tool_config = RvAndroidToolConfig(
    llm_config=llm_config,
    prompt_config=prompt_config,
    server_port=8080,
    debug_mode=False
)

# Access configuration components
strategy_type = tool_config.get_strategy_type()
parser_type = tool_config.get_parser_type()
visitor_type = tool_config.get_visitor_type()

# Get template paths
template_paths = tool_config.get_template_paths()

# Register templates with PromptFramework
tool_config.register_templates_with_framework(prompt_framework)
```

### Memory System Usage

```python
from rvandroid_tool.llm.service.memory_manager import MemoryManager
from rv_android_core.domain.static import StaticAnalysisData

# Initialize memory system
static_data = StaticAnalysisData({})
memory_manager = MemoryManager("com.example.app", static_data)

# Update with current state
state = {"activity": "MainActivity", "screen": {...}}
memory_manager.update(state)

# Enrich state with historical information
memory_manager.enrich_state_with_history(state)

# Record actions
generated_actions = [...]
memory_manager.record_actions(state, generated_actions)
```

### Action Generation with Multiple Configurations

```python
from rvandroid_tool.llm.service.action_service import LLMActionService
from rvandroid_tool.config.tool_config import RvAndroidToolConfig
from rv_llm.config import LLMConfig, PromptConfig
from rv_llm.llm.constants import LLMType, PromptStrategyType
from rv_screen_parser.constants import ScreenParserType, VisitorType

# Configuration 1: Ollama with batch actions
llm_config_1 = LLMConfig(
    llm_type=LLMType.OLLAMA,
    model="llama3.2:3b",
    temperature=0.2
)

prompt_config_1 = PromptConfig(
    strategy_type=PromptStrategyType.BATCH_ACTION,
    parser_type=ScreenParserType.DROIDBOT,
    visitor_type=VisitorType.DETAILED
)

tool_config_1 = RvAndroidToolConfig(
    llm_config=llm_config_1,
    prompt_config=prompt_config_1,
    server_port=8080
)

service_1 = LLMActionService(
    static_data=static_data,
    tool_config=tool_config_1,
    app_package="com.example.app"
)

# Configuration 2: Different settings for parallel execution
llm_config_2 = LLMConfig(
    llm_type=LLMType.OLLAMA,
    model="qwen2.5:7b",
    temperature=0.7
)

prompt_config_2 = PromptConfig(
    strategy_type=PromptStrategyType.STANDARD,
    parser_type=ScreenParserType.DROIDBOT,
    visitor_type=VisitorType.BASIC
)

tool_config_2 = RvAndroidToolConfig(
    llm_config=llm_config_2,
    prompt_config=prompt_config_2,
    server_port=8081
)

service_2 = LLMActionService(
    static_data=static_data,
    tool_config=tool_config_2,
    app_package="com.example.app"
)

# Each service operates independently
actions_1 = service_1.process_state(test_state)
actions_2 = service_2.process_state(test_state)
```

## Configuration

### Tool Configuration Options

```python
from rvandroid_tool.config.tool_config import RvAndroidToolConfig
from rv_llm.config import LLMConfig, PromptConfig
from rv_llm.llm.constants import LLMType, PromptStrategyType
from rv_screen_parser.constants import ScreenParserType, VisitorType

# Create configuration from variant
tool_config = RvAndroidToolConfig.create_from_variant(
    variant_name="default",
    additional_params={"temperature": 0.2}
)

# Create configuration from experiment with variant
from rv_experiment.config import ExperimentConfig
from rv_platform.config.platform_config import ToolConfig

experiment_config = ExperimentConfig(
    app_path="/path/to/app.apk",
    tool_configs=[
        ToolConfig(name="rvandroid", variants=["default"], parameters={"temperature": "0.2"})
    ]
)

# Configuration created automatically through variant resolution

# Access configuration components
strategy_type = tool_config.get_strategy_type()
parser_type = tool_config.get_parser_type()
visitor_type = tool_config.get_visitor_type()
template_paths = tool_config.get_template_paths()
```

### Multi-Instance Configuration

```python
# Independent configurations for parallel testing
configs = []

for i in range(3):
    llm_config = LLMConfig(
        llm_type=LLMType.OLLAMA,
        model=f"llama3.2:{i+1}b",
        temperature=0.2 + (i * 0.1)
    )
    
    prompt_config = PromptConfig(
        strategy_type=PromptStrategyType.BATCH_ACTION,
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.DETAILED
    )
    
    tool_config = RvAndroidToolConfig(
        llm_config=llm_config,
        prompt_config=prompt_config,
        server_port=8080 + i
    )
    
    configs.append(tool_config)

# Each configuration creates independent service instances
services = []
for tool_config in configs:
    service = LLMActionService(
        static_data=static_data,
        tool_config=tool_config,
        app_package="com.example.app"
    )
    services.append(service)
```

## Template System

### Template Registration

```python
from rvandroid_tool.config.tool_config import RvAndroidToolConfig
from rv_llm.llm.prompt.framework import PromptFramework
from rv_llm.config import LLMConfig, PromptConfig
from rv_llm.llm.constants import LLMType, PromptStrategyType
from rv_screen_parser.constants import ScreenParserType, VisitorType

# Create configurations
llm_config = LLMConfig(
    llm_type=LLMType.OLLAMA,
    model="llama3.2:3b"
)

prompt_config = PromptConfig(
    strategy_type=PromptStrategyType.BATCH_ACTION,
    parser_type=ScreenParserType.DROIDBOT,
    visitor_type=VisitorType.DETAILED
)

# Create tool configuration
tool_config = RvAndroidToolConfig(
    llm_config=llm_config,
    prompt_config=prompt_config
)

# Create prompt framework
framework = PromptFramework.create(prompt_config)

# Register tool templates
tool_config.register_templates_with_framework(framework)
```

### Template Paths

The tool provides templates and fragments in:
- `rvandroid_tool/templates/fragments/`: Reusable template fragments
- `rvandroid_tool/templates/templates/`: Complete prompt templates

## Testing

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=rvandroid_tool

# Run specific test categories
poetry run pytest tests/llm/service/
poetry run pytest tests/config/
```

### Test Structure

- `tests/llm/service/`: LLM service integration tests
- `tests/config/`: Configuration management tests
- `tests/core/memory/`: Memory system validation

### Manual Testing

```bash
# Test LLM service with real data
poetry run python teste_llm_service.py
```

## Performance Characteristics

### LLM Response Times
- **Local Models (Ollama)**: 2-5 seconds per action generation
- **Cloud Models (OpenAI)**: 1-3 seconds per action generation
- **Template Processing**: 50-100ms per prompt generation

### Memory Operations
- **Pattern Storage**: < 100ms per pattern
- **Pattern Retrieval**: < 50ms for relevant context lookup
- **State Enrichment**: 100-200ms per state update

### Configuration Management
- **Tool Configuration**: < 10ms per instance creation
- **Template Registration**: 50-100ms per framework setup
- **Multi-instance Setup**: < 100ms per additional instance

## Error Handling

The tool provides comprehensive error handling:

- **LLM Errors**: Provider failures, rate limiting, timeout handling with fallback actions
- **Configuration Errors**: Validation failures, missing parameters, invalid settings
- **Memory Errors**: Database issues, persistence failures, corruption recovery
- **Template Errors**: Missing templates, rendering failures, fragment issues
- **Integration Errors**: Parser failures, static analysis issues, communication problems

## Dependencies

- `rv-android-core`: Core infrastructure and utilities
- `rv-llm`: Language model integration framework
- `rv-screen-parser`: UI parsing and analysis
- `pydantic`: Configuration validation
- `jinja2`: Template processing

## Contributing

### Development Guidelines

1. Follow existing architectural patterns for service components
2. Use comprehensive error handling with rv-android-core infrastructure
3. Implement proper logging for debugging and monitoring
4. Add integration tests for new functionality
5. Document configuration options and usage patterns

### Configuration Design Principles

1. Maintain clear separation between LLM and prompt concerns
2. Use constants from appropriate modules for type safety
3. Implement comprehensive validation for all configuration options
4. Support multi-instance scenarios with independent configurations
5. Provide clear factory methods for configuration creation

## License

This module is part of the RV-Android project and follows the same licensing terms.