"""
LLM Configuration - Modern Configuration System for Monitored Operations Testing

### Architectural Overview:
This module provides a modern, simplified configuration system for language model
components in monitored operations testing. It implements clean separation between
LLM backend configuration and prompt-specific configuration.

### Key Components:
- **LLMConfig**: Configuration data class for LLM backend operations
- **PromptConfig**: Configuration data class for prompt generation and strategy management
- Clean separation between configuration data and object creation
- Type-safe parameter management with comprehensive validation
- Support for CLI variant parsing and parameter overrides

### Design Principles:
- **Pure Data Classes**: Configuration without business logic
- **Type Safety**: Full type annotations with Pydantic validation
- **Clean Interfaces**: Simple, predictable API for configuration management
- **Separation of Concerns**: LLM backend vs prompt configuration
- **Validation**: Comprehensive parameter validation and error reporting
- **CLI Integration**: Variant-based configuration from command line

### Configuration Separation:
- **LLMConfig**: Backend configuration (model, temperature, API keys, etc.)
- **PromptConfig**: Prompt configuration (strategy, parser, visitor, templates, etc.)

### Usage Examples:
```python
# LLM backend configuration
from rv_llm.config import LLMConfig

llm_config = LLMConfig(llm_type="ollama", model="llama3.2:3b")

# Prompt configuration
from rv_llm.config import PromptConfig

prompt_config = PromptConfig(
    strategy_type="standard",
    parser_type="droidbot",
    visitor_type="detailed"
)

# Validation
is_valid, errors = llm_config.validate()
is_valid, errors = prompt_config.validate()
```
"""

from .llm_config import LLMConfig
from .prompt_config import PromptConfig

__all__ = [
    'LLMConfig',
    'PromptConfig'
]