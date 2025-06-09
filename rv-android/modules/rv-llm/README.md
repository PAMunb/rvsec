# RV-LLM Module

Language Model integration infrastructure and prompt framework for RV-Android.

## Overview

The RV-LLM module provides comprehensive LLM integration capabilities for the RV-Android system, enabling AI-driven Android application testing through sophisticated prompt generation and language model interactions.

### Key Features

- **Multi-Provider Support**: Seamless integration with Ollama, HuggingFace, OpenAI, Anthropic, Google, and AWS Bedrock
- **Advanced Prompt Framework**: Sophisticated prompt generation using strategy patterns and template systems
- **Type-Safe Configuration**: Comprehensive configuration management with validation
- **Performance Monitoring**: Built-in metrics and performance tracking
- **Error Handling Integration**: Robust error handling with rv-android-core infrastructure

## Architecture

### Core Components

#### Language Models
- **LanguageModel**: Base abstraction for all LLM implementations
- **OllamaLLM**: Local LLM integration via Ollama for privacy and control
- **HuggingFaceLLM**: Direct HuggingFace transformers integration with quantization support
- **FrontierModel**: Cloud provider integration (OpenAI, Anthropic, Google Gemini, AWS Bedrock)

#### Prompt Framework
- **PromptFramework**: Unified prompt generation system with strategy coordination
- **PromptStrategy**: Strategy pattern for different prompt generation approaches
- **InformationManager**: Fragment-based information gathering and composition
- **TemplateRepository**: Jinja2-based template management with XML support

#### Configuration Management
- **LLMConfiguration**: Type-safe LLM configuration with validation
- **ConfigurationManager**: Comprehensive configuration facade
- **ComponentConfigurator**: Component registration and dependency management

### Integration Points

- **rv-android-core**: Base infrastructure, error handling, logging, event system
- **rv-screen-parser**: Screen parsing integration for UI analysis
- **rv-static-analysis**: Static analysis data integration for context enhancement
- **rv-coverage**: Coverage information for prompt enrichment
- **rv-monitor-generator**: Monitor generation context and constraints

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

### Advanced Prompt Framework

```python
from rv_llm import PromptFramework, ConfigurationManager

# Create framework with default components
framework = PromptFramework.create()

# Generate sophisticated prompts
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

# Use with any language model
response = model.generate(prompt_messages, config)
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

- Extend LanguageModel for new provider integrations
- Use PromptStrategy pattern for new prompt approaches
- Integrate with ErrorHandler for error management
- Follow configuration patterns for type safety
- Maintain provider-agnostic interfaces

## License

This module is part of the RV-Android project and follows the same licensing terms.