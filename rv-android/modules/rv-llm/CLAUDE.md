# RV-LLM Module

Language Model integration infrastructure and prompt framework for the RV-Android system.

## Overview

The rv-llm module provides LLM integration capabilities for AI-driven Android application testing. It implements a provider-agnostic architecture supporting multiple LLM backends (Ollama, HuggingFace, OpenAI, Anthropic, Google, AWS Bedrock), a prompt framework with strategy patterns, and type-safe configuration management.

## Architecture

### Module Structure

```
rv-llm/
├── src/rv_llm/
│   ├── config/                    # Configuration management
│   │   ├── llm_config.py          # LLM backend configuration
│   │   └── prompt_config.py       # Prompt strategy configuration
│   ├── factories/
│   │   └── component_factory.py   # LLM and strategy factory
│   └── llm/
│       ├── language_model.py      # Base LLM abstraction
│       ├── ollama_llm.py          # Ollama integration
│       ├── huggingface_llm.py     # HuggingFace transformers
│       ├── frontier_models.py     # Cloud providers (OpenAI, Anthropic, etc.)
│       ├── data_structures.py     # LLMMessage, LLMResponse, LLMRole
│       ├── constants.py           # Type constants and enums
│       └── prompt/
│           ├── framework.py       # Prompt generation framework
│           ├── strategy/
│           │   └── base_strategy.py  # Base prompt strategy
│           ├── information/
│           │   ├── base_fragment.py     # Information fragment base
│           │   └── fragment_manager.py  # Fragment coordination
│           └── template/
│               ├── jinja_repository.py  # Template management
│               ├── jinja_template.py    # Jinja2 template wrapper
│               └── xml_utils.py         # XML template utilities
└── tests/
```

### Key Components

#### Language Models

| Component | Description |
|-----------|-------------|
| `LanguageModel` | Abstract base class defining the LLM interface |
| `OllamaLLM` | Local LLM integration via Ollama platform |
| `HuggingFaceLLM` | Direct HuggingFace transformers with quantization |
| `FrontierModel` | Cloud providers (OpenAI, Anthropic, Google, AWS) |

#### Data Structures

| Structure | Description |
|-----------|-------------|
| `LLMMessage` | Message structure with multimodal content support |
| `LLMRole` | Role enumeration (system, user, assistant, tool) |
| `LLMResponse` | Response with content and performance metrics |
| `LLMTextContent` | Text content for messages |
| `LLMImageContent` | Image content for multimodal messages |

#### Configuration

| Config Class | Purpose |
|--------------|---------|
| `LLMConfig` | Backend configuration (model, temperature, API keys) |
| `PromptConfig` | Prompt configuration (strategy, parser, visitor) |

#### Prompt Framework

| Component | Description |
|-----------|-------------|
| `PromptFramework` | Coordinates prompt generation workflow |
| `PromptStrategy` | Base class for prompt generation strategies |
| `InformationManager` | Manages and composes information fragments |
| `InformationFragment` | Base class for data extraction fragments |
| `Jinja2TemplateRepository` | XML/Jinja2 template management |

## Development Commands

### Installation

```bash
cd modules/rv-llm
poetry install

# With development dependencies
poetry install --with dev
```

### Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=rv_llm

# Run specific test file
poetry run pytest tests/test_data_structures.py -v

# Run tests for specific component
poetry run pytest tests/llm/test_language_model.py -v
poetry run pytest tests/config/test_llm_config.py -v
```

### Code Quality

```bash
# Linting
poetry run flake8 src/

# Type checking
poetry run mypy src/

# Dead code detection
poetry run vulture src/
```

## Usage Examples

### Basic LLM Usage

```python
from rv_llm.config import LLMConfig
from rv_llm.llm.ollama_llm import OllamaLLM
from rv_llm.llm.data_structures import LLMMessage, LLMRole, LLMTextContent

# Create configuration
config = LLMConfig(
    llm_type="ollama",
    model="llama3.2:3b",
    temperature=0.2,
    max_tokens=800
)

# Initialize model
model = OllamaLLM(config)

# Create message
messages = [
    LLMMessage(
        role=LLMRole.USER,
        content=[LLMTextContent(text="Analyze the login screen")]
    )
]

# Generate response
response = model.generate(messages)
print(f"Response: {response.content}")
print(f"Tokens: {response.output_tokens}")
```

### Multimodal Message (with Image)

```python
from rv_llm.llm.data_structures import LLMMessage, LLMRole, LLMTextContent, LLMImageContent

# Create multimodal message with text and image
message = LLMMessage(
    role=LLMRole.USER,
    content=[
        LLMTextContent(text="Describe this Android screen"),
        LLMImageContent(
            url="/path/to/screenshot.png",
            encoded_string="base64_encoded_image_data"
        )
    ]
)
```

### Using Component Factory

```python
from rv_llm.factories.component_factory import LLMComponentFactory
from rv_llm.config import LLMConfig, PromptConfig

# Create LLM via factory
llm_config = LLMConfig(llm_type="ollama", model="llama3.2:3b")
llm = LLMComponentFactory.create_llm(llm_config)

# Check supported backends
supported = LLMComponentFactory.get_supported_llm_types()
# Returns: ["ollama", "openai", "anthropic", "google", "huggingface"]

# Register custom backend
LLMComponentFactory.register_llm_backend("custom", CustomLLMClass)
```

### Prompt Framework Usage

```python
from rv_llm.config import PromptConfig
from rv_llm.llm.prompt.framework import PromptFramework

# Create prompt configuration
prompt_config = PromptConfig(
    strategy_type="single",
    parser_type="droidbot",
    visitor_type="detailed"
)

# Create framework
framework = PromptFramework.create(prompt_config)

# Generate prompt from state
state = {
    "package_name": "com.example.app",
    "activity": "MainActivity",
    "available_actions": [...],
    "screenshot_path": "/path/to/screenshot.png"
}

messages = framework.generate_prompt(state)
```

### Cloud Provider Configuration

```python
from rv_llm.config import LLMConfig
from rv_llm.llm.frontier_models import FrontierModel

# OpenAI
config = LLMConfig(
    llm_type="openai",
    model="gpt-4",
    api_key="your-api-key"
)

# Anthropic Claude
config = LLMConfig(
    llm_type="anthropic",
    model="claude-3-5-sonnet-20241022",
    api_key="your-api-key"
)

# Create model
model = FrontierModel.create_anthropic(config)
```

## Configuration Reference

### LLMConfig Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `llm_type` | str | "ollama" | Provider type (ollama, openai, anthropic, google, huggingface) |
| `model` | str | "llama3.2:3b" | Model identifier |
| `base_url` | str | "http://localhost:11434" | Base URL for local providers |
| `temperature` | float | 0.2 | Sampling temperature (0.0-2.0) |
| `max_tokens` | int | 800 | Maximum tokens to generate |
| `vision` | bool | False | Enable vision capabilities |
| `think` | bool | False | Enable thinking mode (Ollama) |
| `api_key` | str | None | API key for cloud providers |
| `top_p` | float | 1.0 | Nucleus sampling parameter |
| `top_k` | int | 40 | Top-k sampling parameter |
| `max_context_length` | int | 8192 | Maximum context length |

### PromptConfig Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `strategy_type` | str | "single" | Prompt strategy (single, batch, vision, mop_vision) |
| `parser_type` | str | "droidbot" | Screen parser type |
| `visitor_type` | str | "detailed" | Visitor type for element extraction |
| `template_name` | str | "" | Template name to use |
| `max_context_length` | int | 800 | Maximum context length |
| `context_mode` | str | "stateless" | Context mode (stateless, rich) |
| `context_window_size` | int | 10 | Sliding window size for rich mode |
| `context_compression` | bool | True | Enable compression for older entries |

## Supported Models

### Ollama Models

```python
OllamaLLM.LLAMA        # "llama3.2:1b"
OllamaLLM.DEEPSEEK     # "deepseek-r1:1.5B"
OllamaLLM.GEMMA        # "gemma3:4b"
OllamaLLM.QWEN         # "qwen3:0.6b"
OllamaLLM.QWEN_2_5VL_3B # "qwen2.5vl:3b" (vision)
OllamaLLM.QWEN_2_5VL_7B # "qwen2.5vl:7b" (vision)
OllamaLLM.PHI          # "phi4-mini-reasoning:3.8b"
OllamaLLM.GRANITE      # "granite3.3:2b"
OllamaLLM.FALCON       # "falcon3:3b"
```

### HuggingFace Models

```python
HuggingFaceLLM.LLAMA    # "meta-llama/Meta-Llama-3.1-8B-Instruct"
HuggingFaceLLM.DEEPSEEK # "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
HuggingFaceLLM.GEMMA    # "google/gemma-3-4b-it"
HuggingFaceLLM.QWEN     # "Qwen/Qwen2.5-3B-Instruct"
HuggingFaceLLM.PHI      # "microsoft/Phi-3.5-mini-instruct"
HuggingFaceLLM.GRANITE  # "ibm-granite/granite-3.1-8b-instruct"
HuggingFaceLLM.FALCON   # "tiiuae/Falcon3-3B-Instruct"
```

### Frontier Models

```python
FrontierModel.CLAUDE_SONNET  # "claude-4-sonnet-20250514"
FrontierModel.CLAUDE_OPUS    # "claude-4-opus-20250514"
FrontierModel.GPT_4          # "gpt-4-turbo-2024-04-09"
FrontierModel.GPT_3_5        # "gpt-3.5-turbo-0125"
FrontierModel.GEMINI_PRO     # "gemini-pro"
FrontierModel.GEMINI_ULTRA   # "gemini-ultra"
```

## Integration Points

### Dependencies

- **rv-android-core**: Error handling, logging, validation infrastructure
- **rv-screen-parser**: Screen parsing constants (ScreenParserType, VisitorType)

### Consumers

- **rv-agent**: Uses LLM client for AI-driven testing
- **rv-experiment**: Integrates prompt framework for experiment workflows

## Architectural Patterns

### Provider Abstraction

The `LanguageModel` base class provides a unified interface:
- `generate(messages, config)` - Generate response from messages
- `cleanup()` - Release resources
- `supports_multimodal()` - Check vision capability
- `format_message_with_multimodal_support()` - Format for specific provider

### Factory Pattern

`LLMComponentFactory` centralizes component creation:
- Registry-based backend registration
- Strategy factory with dependency injection
- Validation of backend availability

### Strategy Pattern

Prompt strategies implement `PromptStrategy`:
- `_generate_prompt(state, context)` - Core generation logic
- `generate_prompt(state, context)` - Returns LLMMessage list
- `configure_from_config(config)` - Apply configuration

### Fragment Pattern

Information fragments implement `InformationFragment`:
- `generate(state, context)` - Extract specific data
- `should_include(state, context)` - Conditional inclusion
- Priority-based composition through `InformationManager`

## Performance Metrics

LLMResponse captures comprehensive metrics:

```python
response.total_duration      # Total request-to-response time (ms)
response.load_duration       # Model loading time (ms)
response.input_tokens        # Input prompt token count
response.input_tokens_duration  # Prompt processing time (ms)
response.output_tokens       # Generated response token count
response.output_tokens_duration # Token generation time (ms)
response.get_tokens_per_second() # Generation rate
response.to_performance_dict()   # All metrics as dict
```

## Error Handling

The module uses `ErrorHandler` decorators for consistent error management:

```python
from rv_android_core.util.error.exceptions import (
    RVLLMError,
    RVLLMConfigurationError,
    RVLLMConnectionError,
    RVLLMModelError,
    RVPromptError
)
```

All major operations are wrapped with error handlers that provide:
- Component and phase context
- Automatic logging
- Error recovery strategies

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | API key for OpenAI models |
| `ANTHROPIC_API_KEY` | API key for Anthropic Claude models |
| `GOOGLE_API_KEY` | API key for Google Gemini models |
| `AWS_REGION` | AWS region for Bedrock (default: us-east-1) |

## Test Structure

```
tests/
├── test_data_structures.py     # LLMMessage, LLMResponse tests
├── config/
│   ├── test_llm_config.py      # LLMConfig validation tests
│   └── test_prompt_config.py   # PromptConfig validation tests
├── factories/                   # Factory tests
└── llm/
    ├── test_language_model.py  # Base model tests
    ├── test_ollama_llm.py      # Ollama integration tests
    └── prompt/
        ├── test_framework.py   # Framework tests
        ├── information/        # Fragment tests
        ├── strategy/           # Strategy tests
        └── template/           # Template tests
```
