# RV-LLM Module

Language Model integration infrastructure and modern factory-based prompt framework for AI-driven Android application testing with dependency injection architecture.

## Overview

The RV-LLM module provides comprehensive LLM integration capabilities for the RV-Android system, enabling sophisticated AI-driven Android application testing through modern factory patterns, advanced prompt generation, and seamless provider abstraction. The module implements a DI-ready architecture with comprehensive error handling and performance monitoring.

### Key Features

- **Modern Factory Architecture**: LLMFactory and PromptStrategyFactory with DI-ready interfaces for flexible component creation
- **Multi-Provider Support**: Seamless integration with Ollama, HuggingFace, OpenAI, Anthropic, Google, and AWS Bedrock
- **Advanced Prompt Framework**: Sophisticated prompt generation using strategy patterns and template systems
- **Type-Safe Configuration**: Comprehensive configuration management with validation and error handling
- **Performance Monitoring**: Built-in metrics and performance tracking with structured logging
- **DI Integration**: Full dependency injection support with lifecycle management

## Architecture

### Core Components

#### Modern Factory System
- **LLMFactory**: Central factory for creating LLM instances with comprehensive provider support
- **ILLMFactory**: Interface defining factory contract for dependency injection
- **PromptStrategyFactory**: Factory for creating prompt generation strategies with configuration support
- **IPromptStrategyFactory**: Interface for strategy factory implementations

#### Language Models
- **LanguageModel**: Base abstraction for all LLM implementations with standardized interface
- **OllamaLLM**: Local LLM integration via Ollama for privacy and control with enhanced configuration
- **HuggingFaceLLM**: Direct HuggingFace transformers integration with quantization support
- **FrontierModel**: Cloud provider integration (OpenAI, Anthropic, Google Gemini, AWS Bedrock)

#### Prompt Framework
- **PromptFramework**: Unified prompt generation system with strategy coordination and context management
- **PromptStrategy**: Strategy pattern for different prompt generation approaches with template support
- **InformationManager**: Fragment-based information gathering and composition with validation
- **TemplateRepository**: Jinja2-based template management with XML support and caching

#### Configuration Management
- **LLMConfiguration**: Type-safe LLM configuration with comprehensive validation and error reporting
- **ConfigurationManager**: Modern configuration facade with multi-source support and validation

### Integration Points

- **rv-android-core**: Uses ErrorHandler decorators, LoggingManager, and EventBus for infrastructure
- **rv-experiment**: Provides LLMFactory and PromptStrategyFactory for orchestration and experiment management
- **rv-screen-parser**: Screen parsing integration for UI analysis and context enhancement
- **rv-static-analysis**: Static analysis data integration for prompt context and validation
- **rv-coverage**: Coverage information for prompt enrichment and testing strategy optimization
- **rv-monitor-generator**: Monitor generation context and constraint integration

## Installation

### Prerequisites

- Python 3.12+
- Poetry for dependency management
- rv-android-core module
- Additional dependencies based on providers used

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

### Basic Language Model Usage

```python
from rv_llm import OllamaLLM, LLMConfiguration, LLMMessage, LLMRole, LLMTextContent

# Initialize model with configuration
config = LLMConfiguration(
    model_name="llama3.2:3b",
    temperature=0.2,
    max_tokens=800
)
model = OllamaLLM("llama3.2:3b")

# Create messages with rich content
text_content = LLMTextContent(text="Generate Android test actions for login screen")
messages = [
    LLMMessage(role=LLMRole.USER, content=[text_content])
]

# Generate response with performance metrics
response = model.generate(messages, config)
print(f"Response: {response.content}")
print(f"Tokens: {response.output_tokens}")
print(f"Duration: {response.total_duration}ms")
```

### Modern Factory Usage

```python
from rv_llm.factories import LLMFactory, PromptStrategyFactory

# Create factories with DI-ready design
llm_factory = LLMFactory()
strategy_factory = PromptStrategyFactory()

# Create LLM instances through factory
ollama_llm = llm_factory.create_ollama(
    model="llama3.2:3b",
    temperature=0.3,
    base_url="http://localhost:11434"
)

frontier_llm = llm_factory.create_frontier(
    provider="anthropic",
    model="claude-3-sonnet",
    api_key="your-key"
)

# Create prompt strategies through factory
standard_strategy = strategy_factory.create_standard(
    use_context_enhancement=True,
    include_ui_analysis=True
)

batch_strategy = strategy_factory.create_batch_action(
    batch_size=3,
    use_action_coordination=True
)

# Configuration-driven creation
llm_config = {
    "provider": "ollama",
    "model": "llama3",
    "temperature": 0.2
}
llm = llm_factory.create_from_config(llm_config)
```

### Advanced Prompt Framework Integration

```python
from rv_llm import PromptFramework, ConfigurationManager
from rv_llm.factories import PromptStrategyFactory

# Create framework with factory-created strategy
strategy_factory = PromptStrategyFactory()
strategy = strategy_factory.create_standard(
    use_context_enhancement=True,
    include_static_analysis=True
)

framework = PromptFramework.create(strategy=strategy)

# Generate sophisticated prompts with enhanced context
state = {
    "current_screen": screen_data,
    "action_history": previous_actions,
    "static_analysis": static_data,
    "coverage_info": coverage_metrics
}

context = {
    "strategy": "exploration",
    "constraints": ["avoid_destructive_actions"]
}

# Generate context-aware prompts
prompt_messages = framework.generate_prompt(state, context)

# Use with factory-created LLM
response = ollama_llm.generate(prompt_messages, config)
```

## Configuration

### LLM Configuration Options

```python
from rv_llm import LLMConfiguration

config = LLMConfiguration(
    model_type="ollama",           # Provider type
    model_name="llama3.2:3b",     # Specific model
    temperature=0.2,              # Creativity control
    max_tokens=800,               # Response length limit
    top_p=1.0,                    # Nucleus sampling
    frequency_penalty=0.0,        # Repetition penalty
    presence_penalty=0.0,         # Topic diversity
    strategy_type="standard",     # Prompt strategy
    parser_type="droidbot"        # Screen parser type
)
```

## Testing

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=rv_llm

# Run specific test categories
poetry run pytest tests/test_data_structures.py
```

### Test Results

Current test status: **4/4 tests passing (100%)**

-  Core data structures validation
-  LLM message creation and handling
-  Response object functionality
-  Role enumeration correctness

## Contributing

### Code Standards

- Follow PEP 8 guidelines
- Use type hints for all public interfaces
- Include comprehensive docstrings following Google style
- Maintain architectural comment patterns consistent with other modules

### Architecture Guidelines

- Use LLMFactory and PromptStrategyFactory for all component creation
- Implement DI-ready interfaces for new components
- Integrate with ErrorHandler decorators for comprehensive error management
- Follow factory patterns for consistent component lifecycle
- Maintain provider-agnostic interfaces with clear abstraction layers
- Use configuration-driven component creation where possible

## License

This module is part of the RV-Android project and follows the same licensing terms.