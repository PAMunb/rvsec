# rvandroid/llm/adapters/__init__.py
"""Adapters for Model Context Protocol language models."""

# Import adapters for automatic registration
from rvandroid.llm.adapters.ollama_adapter import OllamaAdapter
from rvandroid.llm.adapters.frontier_adapter import FrontierAdapter 
from rvandroid.llm.adapters.huggingface_adapter import HuggingFaceAdapter
from rvandroid.llm.adapter import AdapterRegistry

# Register all adapters
def register_adapters():
    """Register all MCP adapters with the adapter registry."""
    registry = AdapterRegistry.get_instance()
    
    # Register adapters for each model type
    registry.register_adapter("ollama", OllamaAdapter)
    registry.register_adapter("frontier", FrontierAdapter)
    registry.register_adapter("huggingface", HuggingFaceAdapter)
    
    # Also register aliases for backward compatibility
    registry.register_adapter("claude", FrontierAdapter)
    registry.register_adapter("openai", FrontierAdapter)
    registry.register_adapter("gpt", FrontierAdapter)
    registry.register_adapter("gemini", FrontierAdapter)

# Auto-register adapters when importing this module
register_adapters()