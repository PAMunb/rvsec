# RV-LLM Module

Language Model integration infrastructure and prompt framework for AI-driven Android application testing.

## Overview

The RV-LLM module provides LLM integration capabilities for the RV-Android system, enabling AI-driven Android application testing through component architecture, prompt generation, and provider abstraction. The module implements a configuration approach with error handling.

### Key Features

- **Multi-Provider Support**: Integration with Ollama, HuggingFace, OpenAI, Anthropic, Google, and AWS Bedrock
- **Prompt Framework**: Prompt generation using strategy patterns and template systems
- **Type-Safe Configuration**: Configuration management with validation and error handling
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
- **InformationManager**: Fragment-based information gathering and composition with direct parameter passing
- **Jinja2TemplateRepository**: Template management with XML support and caching

#### Configuration Management
- **LLMConfig**: LLM configuration with validation and error reporting
- **ComponentFactory**: Component creation through factory patterns

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
from rv_llm import OllamaLLM, LLMConfig, LLMMessage, LLMRole, LLMTextContent

# Initialize model with configuration
config = LLMConfig(
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
response = model.generate(messages, config.get_llm_parameters())
print(f"Response: {response.content}")
print(f"Tokens: {response.output_tokens}")
print(f"Duration: {response.total_duration}ms")
```

### Prompt Framework Usage

```python
from rv_llm import PromptFramework

# Create framework with clean architecture
framework = PromptFramework.create()

# Configure framework with direct parameters
framework.configure(
    template_format="jinja2",
    template_validation=True
)

# Generate sophisticated prompts with context
state = {
    "current_screen": screen_data,
    "action_history": previous_actions,
    "static_analysis": static_data,
    "coverage_info": coverage_metrics
}

context = {
    "strategy_type": "exploration",
    "constraints": ["avoid_destructive_actions"]
}

# Generate context-aware prompts
prompt_messages = framework.generate_prompt(state, context)

# Use with configured LLM
response = model.generate(prompt_messages, config.get_llm_parameters())
```

### Configuration Management

```python
from rv_llm.config.llm_config import LLMConfig

# Create configuration from CLI variants
config = LLMConfig.from_variants_and_params(
    variants=["llama", "batch_action"],
    params={"temperature": "0.3", "max_tokens": "1000"}
)

# Validate configuration
is_valid, errors = config.validate()
if not is_valid:
    print(f"Configuration errors: {errors}")

# Get specific parameter sets
llm_params = config.get_llm_parameters()
strategy_params = config.get_strategy_parameters()
parser_params = config.get_parser_parameters()
```

## Configuration

### LLM Configuration Options

```python
from rv_llm import LLMConfig

config = LLMConfig(
    llm_type="ollama",            # Provider type
    model="llama3.2:3b",          # Specific model
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

- Use PromptFramework.create() for framework initialization
- Use direct parameter passing for component configuration
- Integrate with ErrorHandler decorators for comprehensive error management
- Use LLMConfig for configuration management with validation
- Maintain provider-agnostic interfaces with clear abstraction layers
- Use simple factory methods for component creation

## License

This module is part of the RV-Android project and follows the same licensing terms.