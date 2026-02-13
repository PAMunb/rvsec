#!/usr/bin/env python3
"""
Manual test for rv-llm module with clean architecture.

This test validates that the rv-llm module works correctly with:
- Clean LLMConfig without parser/visitor fields
- Enhanced LLMComponentFactory with registry system
- FrontierModel architecture without MCP
- Exception handling system
- Custom backend registration
"""

import os
import sys
from pathlib import Path

from rv_llm.config.llm_config import LLMConfig
from rv_llm.factories.component_factory import LLMComponentFactory
from rv_llm.llm.constants import LLMType, PromptStrategyType
from rv_llm.llm.data_structures import LLMMessage, LLMTextContent, LLMRole
from rv_llm.llm.ollama_llm import OllamaLLM

# Setup RVSEC_HOME before importing modules
current_directory = os.getcwd()
parent_directory = os.path.dirname(current_directory)

# Add the modules to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-platform" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-experiment" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-tools" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-coverage" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-static-analysis" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-screen-parser" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-llm" / "src"))

# Import constants after path setup
from rv_android_core import constants

# Set RVSEC_HOME environment variable
os.environ[constants.ENV_RVSEC_HOME] = parent_directory


def setup_logging(debug: bool = True):
    """Set up logging configuration."""
    import logging
    from rv_android_core.util.logging.manager import LoggingManager

    # Setup basic logging first
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )

    # Silence noisy third-party loggers for clean CLI output
    for noisy_logger in ["androguard", "matplotlib", "PIL", "requests", "urllib3"]:
        logging.getLogger(noisy_logger).setLevel(logging.ERROR)

    # Get the logging manager
    logging_manager = LoggingManager.get_instance()

    # Configure output to show all rvandroid logs including module logs
    logging_manager.configure_output(
        console=True,
        file=False,
        console_level=10 if debug else 20,  # DEBUG (10) or INFO (20)
        file_level=10,  # DEBUG
        json_format=False
    )

    return logging_manager.get_logger('teste.rv_experiment')


def tmp_ollama():
    """Test LLM with clean architecture."""
    messages = [
        # LLMMessage(role=LLMRole.SYSTEM, content=[LLMTextContent(text="Hello, Ollama!")]),
        LLMMessage(role=LLMRole.USER, content=[LLMTextContent(text="Hello, Ollama!")])
    ]
    
    # Create clean LLM configuration
    config = LLMConfig(
        llm_type=LLMType.OLLAMA,
        model=OllamaLLM.QWEN,
        strategy_type=PromptStrategyType.BATCH_ACTION,
        temperature=0.2,
        max_tokens=800
    )
    
    # Create LLM using the factory
    llm = LLMComponentFactory.create_llm(config)
    response = llm.generate(messages, config)
    print(f"response={response}")
    
    # Test factory registry info
    registry_info = LLMComponentFactory.get_registry_info()
    print(f"\n\n\n*********************************************\nRegistry info: {registry_info}")
    
    # Test supported types
    supported_llm_types = LLMComponentFactory.get_supported_llm_types()
    print(f"Supported LLM types: {supported_llm_types}")
    
    supported_strategy_types = LLMComponentFactory.get_supported_strategy_types()
    print(f"Supported strategy types: {supported_strategy_types}")

def test_registry_system():
    """Test the registry system for custom backends."""
    from rv_llm.llm.language_model import LanguageModel
    
    class MockLLM(LanguageModel):
        """Mock LLM for testing registry system."""
        def __init__(self, **kwargs):
            super().__init__("mock-model")
            self.kwargs = kwargs
        
        def generate(self, messages, config=None):
            """Mock generate method."""
            return LLMMessage(role=LLMRole.ASSISTANT, content=[LLMTextContent(text="Mock response")])
        
        def cleanup(self):
            """Mock cleanup method."""
            pass
        
        @staticmethod
        def models():
            """Mock models method."""
            return ["mock-model"]
    
    # Test registry
    print("Testing registry system...")
    print(f"Before registration: {LLMComponentFactory.get_supported_llm_types()}")
    
    # Register custom backend
    LLMComponentFactory.register_llm_backend("mock", MockLLM)
    print(f"After registration: {LLMComponentFactory.get_supported_llm_types()}")
    
    # Test using registered backend
    config = LLMConfig(
        llm_type="mock",
        model="mock-model",
        strategy_type=PromptStrategyType.STANDARD
    )
    
    messages = [
        LLMMessage(role=LLMRole.USER, content=[LLMTextContent(text="Test custom backend")])
    ]
    
    llm = LLMComponentFactory.create_llm(config)
    response = llm.generate(messages, config)
    print(f"Custom backend response={response}")
    
    # Show registry info
    registry_info = LLMComponentFactory.get_registry_info()
    print(f"Final registry info: {registry_info}")


if __name__ == "__main__":
    setup_logging()
    
    print("=== Testing Ollama LLM ===")
    tmp_ollama()
    
    print("\n=== Testing Registry System ===")
    test_registry_system()
