# rvandroid/llm/__init__.py
"""
Language model integration package for RV-Android.

This package provides a standardized way to interact with various language models
using the Model Context Protocol (MCP). It includes adapters for different model types,
templates for generating prompts, and utilities for managing model interactions.

Key components:
- Model Context Protocol (MCP) for standardized communication
- Adapters for different model types (Ollama, DSPy, etc.)
- Template system for generating structured prompts
- Configuration management for language models

The package follows a consistent design pattern:
1. Data structures represent messages and configurations
2. Adapters convert between MCP and model-specific formats
3. Language model implementations provide a consistent interface
4. Templates generate standardized prompts

This design enables easy switching between different model implementations
while maintaining a consistent interface for the RV-Android system.
"""

# Import public classes for easy access
from rvandroid.llm.data_structures import LLMMessage, LLMRole
from rvandroid.llm.language_model import LanguageModel

# Import adapters
from rvandroid.llm.adapters import *

# We'll register models later to avoid circular imports
def register_models():
    """Register all model implementations"""
    from rvandroid.llm.ollama_llm import register as register_ollama
    from rvandroid.llm.dspy_llm import register as register_dspy
    from rvandroid.llm.huggingface_llm import register as register_huggingface
    
    register_ollama()
    register_dspy()
    register_huggingface()