"""
RV-LLM Module

Language Model integration infrastructure and prompt framework for RV-Android.

This module provides comprehensive LLM integration capabilities including:
- Language model abstractions for multiple providers
- Advanced prompt generation framework
- Template management system
- Configuration management for LLM components

### Key Components:

#### Language Models:
- **LanguageModel**: Base abstraction for all LLM implementations
- **OllamaLLM**: Local LLM integration via Ollama
- **HuggingFaceLLM**: Direct HuggingFace transformers integration
- **FrontierModel**: Integration with cloud providers (OpenAI, Anthropic, Google, AWS)

#### Prompt Framework:
- **PromptFramework**: Unified prompt generation system
- **PromptStrategy**: Strategy pattern for different prompt types
- **InformationManager**: Fragment-based information gathering
- **TemplateRepository**: Jinja2-based template management

#### Configuration:
- **LLMConfiguration**: Type-safe LLM configuration management
- **ConfigurationManager**: Comprehensive configuration facade
- **PromptStrategyConfig**: Typed configuration for prompt strategies

### Architectural Principles:
- **Provider Agnostic**: Seamless switching between different LLM providers
- **Strategy Pattern**: Flexible prompt generation strategies
- **Template-Driven**: XML/Jinja2 template system for maintainable prompts
- **Configuration Management**: Centralized configuration with validation
- **Error Handling**: Integrated with rv-android-core error handling infrastructure
- **Performance Monitoring**: Built-in metrics and performance tracking

### Integration Points:
- **rv-android-core**: Base infrastructure, error handling, logging
- **rv-screen-parser**: Screen parsing for UI analysis
- **rv-static-analysis**: Static analysis data integration
- **rv-coverage**: Coverage information for prompt enrichment
- **rv-monitor-generator**: Monitor generation context
"""

# Core LLM components
from .llm.language_model import LanguageModel
from .llm.data_structures import LLMMessage, LLMRole, LLMResponse, LLMTextContent, LLMImageContent
from .llm.llm_config import LLMConfiguration
from .llm.constants import PromptStrategyType

# Model implementations
from .llm.ollama_llm import OllamaLLM
from .llm.huggingface_llm import HuggingFaceLLM
from .llm.frontier_models import FrontierModel

# Prompt framework
from .llm.prompt.framework import PromptFramework
from .llm.prompt.prompt_strategy import PromptStrategy as BasePromptStrategy

# Configuration
from .config.llm_config import LLMConfig

__version__ = "0.1.0"
__all__ = [
    # Core abstractions
    "LanguageModel",
    "LLMMessage", 
    "LLMRole",
    "LLMResponse",
    "LLMTextContent",
    "LLMImageContent",
    "LLMConfiguration",
    "PromptStrategyType",
    
    # Model implementations
    "OllamaLLM",
    "HuggingFaceLLM", 
    "FrontierModel",
    
    # Prompt framework
    "PromptFramework",
    "BasePromptStrategy",
    
    # Configuration
    "LLMConfig"
]


# We'll register models later to avoid circular imports
def register_models():
    """Register all model implementations"""
    from .llm.ollama_llm import register as register_ollama
    # from .llm.huggingface_llm import register as register_huggingface

    register_ollama()
    # register_huggingface()
