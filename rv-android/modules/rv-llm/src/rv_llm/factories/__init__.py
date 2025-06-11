"""
LLM Factories - Modern Factory Pattern for Language Model Components

### Architectural Overview:
This module provides modern factory implementations for language model components
with clean, testable factory interfaces. The factories use the simplified LLMConfig-based 
approach for monitored operations testing.

### Key Factory Components:
- **LLMComponentFactory**: Main factory for creating LLM components (backends and strategies)
- Clean, stateless factory operations for thread safety
- Comprehensive error handling using rv-android-core decorators
- Direct integration with LLMConfig for type-safe configuration
- Respects module boundaries - no external tool dependencies

### Design Principles:
- **Clean Architecture**: Simple data classes for configuration, factories for creation
- **Error Handling**: Comprehensive error handling using rv-android-core decorators
- **Logging Integration**: Consistent logging throughout factory operations
- **Type Safety**: Full type annotations and validation
- **Testability**: Clean interfaces enable easy mocking and testing

### Migration Notes:
This module has been modernized to remove all legacy ComponentConfigurator dependencies.
All factories now use the clean LLMConfig system for monitored operations testing.

### Usage Examples:
```python
# Modern approach with LLMConfig
from rv_llm.factories import LLMComponentFactory
from rv_llm.config import LLMConfig

config = LLMConfig(llm_type="ollama", strategy_type="batch_action")

# Individual component creation
llm = LLMComponentFactory.create_llm(config)
strategy = LLMComponentFactory.create_strategy(config)
```
"""

from .component_factory import LLMComponentFactory

__all__ = [
    'LLMComponentFactory'
]