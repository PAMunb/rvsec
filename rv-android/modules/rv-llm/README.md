# RV-LLM Module

Language Model integration infrastructure and prompt framework for monitored operations testing.

## Overview

The RV-LLM module provides LLM integration capabilities for the RV-Android system, enabling AI-driven Android application testing through component architecture, prompt generation, and provider abstraction. The module implements a clean configuration approach with comprehensive error handling.

### Key Features

- **Multi-Provider Support**: Integration with Ollama, HuggingFace, OpenAI, Anthropic, Google, and AWS Bedrock
- **Prompt Framework**: Prompt generation using strategy patterns and template systems
- **Type-Safe Configuration**: Separated configuration management with validation and error handling
- **Component Factory**: Component creation through factory patterns
- **Performance Monitoring**: Built-in metrics and performance tracking with structured logging

## Architecture

### Core Components

#### Language Models
- **LanguageModel**: Base abstraction for all LLM implementations with standardized interface
- **OllamaLLM**: Local LLM integration via Ollama for privacy and control
- **HuggingFaceLLM**: Direct HuggingFace transformers integration with quantization support
- **FrontierModel**: Cloud provider integration (OpenAI, Anthropic, Google Gemini, AWS Bedrock)

#### Prompt Framework
- **PromptFramework**: Unified prompt generation system with strategy coordination and context management
- **PromptStrategy**: Strategy pattern for different prompt generation approaches with template support
- **InformationManager**: Fragment-based information gathering and composition
- **Jinja2TemplateRepository**: Template management with XML support and caching

#### Configuration Management
- **LLMConfig**: LLM backend configuration with validation and error reporting
- **PromptConfig**: Prompt generation configuration with strategy and parser settings
- **LLMComponentFactory**: Component creation through factory patterns

#### Data Structures
- **LLMMessage**: Message structure for LLM communication
- **LLMRole**: Role enumeration (system, user, assistant, tool)
- **LLMResponse**: Structured response from LLM interactions
- **LLMTextContent**: Text content handling for messages

### Integration Points

- **rv-android-core**: Uses ErrorHandler decorators and LoggingManager for error handling and logging
- **rv-experiment**: Provides prompt framework and LLM integration for AI-driven testing tools
- **rv-screen-parser**: Screen parsing integration for UI analysis and context enhancement
- **rv-static-analysis**: Static analysis data integration for prompt context
- **rv-coverage**: Coverage information for prompt enrichment and testing strategy optimization
- **rv-monitor-generator**: Monitor generation context integration

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
from rv_llm.config import LLMConfig
from rv_llm.llm.ollama_llm import OllamaLLM
from rv_llm.llm.data_structures import LLMMessage, LLMRole, LLMTextContent

# Initialize model with configuration
config = LLMConfig(
    llm_type="ollama",
    model="llama3.2:3b",
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

### Prompt Framework Usage

```python
from rv_llm.config import PromptConfig
from rv_llm.llm.prompt.framework import PromptFramework
from rv_llm.llm.constants import PromptStrategyType
from rv_screen_parser.constants import ScreenParserType, VisitorType

# Create prompt configuration
prompt_config = PromptConfig(
    strategy_type=PromptStrategyType.BATCH,
    parser_type=ScreenParserType.DROIDBOT,
    visitor_type=VisitorType.DETAILED
)

# Create framework with configuration
framework = PromptFramework.create(prompt_config)

# Generate prompts with context
state = {
    "current_screen": screen_data,
    "action_history": previous_actions,
    "static_analysis": static_data,
    "coverage_info": coverage_metrics
}

context = {
    "app_package": "com.example.app",
    "app_activity": "MainActivity"
}

# Generate context-aware prompts
prompt_messages = framework.generate_prompt(state, context)

# Use with configured LLM
response = model.generate(prompt_messages, llm_config)
```

### Configuration Management

```python
from rv_llm.config import LLMConfig, PromptConfig
from rv_llm.llm.constants import LLMType, PromptStrategyType
from rv_screen_parser.constants import ScreenParserType, VisitorType

# Create LLM configuration
llm_config = LLMConfig(
    llm_type=LLMType.OLLAMA,
    model="llama3.2:3b",
    temperature=0.2,
    max_tokens=800
)

# Create prompt configuration
prompt_config = PromptConfig(
    strategy_type=PromptStrategyType.SINGLE,
    parser_type=ScreenParserType.DROIDBOT,
    visitor_type=VisitorType.DETAILED
)

# Validate configurations
if not llm_config.validate():
    print(f"LLM Configuration errors: {llm_config.get_validation_errors()}")

if not prompt_config.validate():
    print(f"Prompt Configuration errors: {prompt_config.get_validation_errors()}")
```

### Component Factory Usage

```python
from rv_llm.factories.component_factory import LLMComponentFactory
from rv_llm.config import LLMConfig, PromptConfig

# Create LLM backend
llm_config = LLMConfig(llm_type="ollama", model="llama3.2:3b")
llm = LLMComponentFactory.create_llm(llm_config)

# Create prompt strategy
prompt_config = PromptConfig(strategy_type="batch")
strategy = LLMComponentFactory.create_strategy(prompt_config)

# Check supported backends
supported_llms = LLMComponentFactory.get_supported_llm_types()
supported_strategies = LLMComponentFactory.get_supported_strategy_types()
```

## Configuration

### LLM Configuration Options

```python
from rv_llm.config import LLMConfig
from rv_llm.llm.constants import LLMType

config = LLMConfig(
    llm_type=LLMType.OLLAMA,       # Provider type
    model="llama3.2:3b",           # Specific model
    temperature=0.2,               # Creativity control
    max_tokens=800,                # Response length limit
    top_p=1.0,                     # Nucleus sampling
    frequency_penalty=0.0,         # Repetition penalty
    presence_penalty=0.0,          # Topic diversity
    base_url="http://localhost:11434"  # Provider URL
)
```

### Prompt Configuration Options

```python
from rv_llm.config import PromptConfig
from rv_llm.llm.constants import PromptStrategyType
from rv_screen_parser.constants import ScreenParserType, VisitorType

config = PromptConfig(
    strategy_type=PromptStrategyType.BATCH,  # Prompt strategy
    parser_type=ScreenParserType.DROIDBOT,         # Screen parser type
    visitor_type=VisitorType.DETAILED,             # Visitor type
    max_context_length=8192                        # Context limit
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

- Core data structures validation
- LLM message creation and handling
- Response object functionality
- Role enumeration correctness

## Contributing

### Code Standards

- Follow PEP 8 guidelines
- Use type hints for all public interfaces
- Include comprehensive docstrings following Google style
- Maintain architectural comment patterns consistent with other modules

### Architecture Guidelines

- Use separated configuration approach (LLMConfig + PromptConfig)
- Use LLMComponentFactory for component creation
- Integrate with ErrorHandler decorators for comprehensive error management
- Use constants from rv_llm.llm.constants for type-safe configuration
- Maintain provider-agnostic interfaces with clear abstraction layers
- Use BaseValidatedModel for configuration classes

## License

This module is part of the RV-Android project and follows the same licensing terms.