"""
LLM Configuration - Modern Configuration System for Monitored Operations Testing

### Architectural Overview:
This module provides a modern, simplified configuration system for language model
components in monitored operations testing. It replaces the complex legacy
ComponentConfigurator with a clean, type-safe data class approach.

### Key Components:
- **LLMConfig**: Main configuration data class for all LLM operations
- Clean separation between configuration data and object creation
- Type-safe parameter management with comprehensive validation
- Support for CLI variant parsing and parameter overrides

### Design Principles:
- **Pure Data Classes**: Configuration without business logic
- **Type Safety**: Full type annotations with dataclass validation
- **Clean Interfaces**: Simple, predictable API for configuration management
- **Validation**: Comprehensive parameter validation and error reporting
- **CLI Integration**: Variant-based configuration from command line

### Migration Notes:
This module has been modernized to remove all legacy configuration dependencies.
The system now uses only LLMConfig for all configuration needs in monitored
operations testing scenarios.

### Usage Examples:
```python
# Basic configuration
from rv_llm.config import LLMConfig

config = LLMConfig(llm_type="ollama", model="llama3.2:3b")

# From CLI variants
config = LLMConfig.from_variants_and_params(
    variants=["llama", "batch_action"],
    params={"temperature": "0.3"}
)

# Validation
is_valid, errors = config.validate()
```
"""

from .llm_config import LLMConfig

__all__ = [
    'LLMConfig'
]