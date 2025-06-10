"""
LLM Factories - Modern Factory Pattern for Language Model Components

### Architectural Overview:
This module provides DI-ready factory implementations for language model components
with clean, testable factory interfaces. The factories are designed to be easily 
integrated with dependency injection containers while maintaining simplicity and clarity.

### Key Factory Components:
- **ILLMFactory**: Interface for LLM component creation (DI container ready)
- **LLMFactory**: Concrete implementation with comprehensive error handling
- **IPromptStrategyFactory**: Interface for prompt strategy creation (DI container ready)
- **PromptStrategyFactory**: Concrete implementation for prompt strategy management

### Design Principles:
- **DI-Ready**: All factories implement interfaces suitable for dependency injection
- **Error Handling**: Comprehensive error handling using rv-android-core decorators
- **Logging Integration**: Consistent logging throughout factory operations
- **Configuration Driven**: Factory methods accept configuration dictionaries
- **Testability**: Clean interfaces enable easy mocking and testing
"""

from .llm_factory import ILLMFactory, LLMFactory
from .prompt_strategy_factory import IPromptStrategyFactory, PromptStrategyFactory

__all__ = [
    'ILLMFactory',
    'LLMFactory', 
    'IPromptStrategyFactory',
    'PromptStrategyFactory'
]