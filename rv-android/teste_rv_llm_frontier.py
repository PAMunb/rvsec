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

    return logging_manager.get_logger('teste_rv_llm_frontier')

def tmp_frontier_001():
    # Test factory registry info
    registry_info = LLMComponentFactory.get_registry_info()
    print(f"\n\n\n*********************************************\nRegistry info: {registry_info}")

    # Test supported types
    supported_llm_types = LLMComponentFactory.get_supported_llm_types()
    print(f"Supported LLM types: {supported_llm_types}")

    supported_strategy_types = LLMComponentFactory.get_supported_strategy_types()
    print(f"Supported strategy types: {supported_strategy_types}")



def tmp_frontier():
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv('ANTHROPIC_API_KEY')

    # messages = [
    #     # LLMMessage(role=LLMRole.SYSTEM, content=[LLMTextContent(text="Hello, Ollama!")]),
    #     LLMMessage(role=LLMRole.USER, content=[LLMTextContent(text="Hello, world!")])
    # ]
    messages = create_messages()
    
    # Create clean LLM configuration
    config = LLMConfig(
        llm_type="anthropic",
        model="claude-3-5-sonnet-20240620", # "claude-sonnet-4-20250514"
        temperature=0.2,
        max_tokens=800,
        api_key=api_key
    )
    
    # Create LLM using the factory
    llm = LLMComponentFactory.create_llm(config)
    print(f"llm={llm}")
    response = llm.generate(messages, config)
    print(f"response={response}")

    print(response.to_performance_dict())

def create_messages():
    base_dir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-evaluator/src/rv_evaluator/prompts"

    system_prompt = read_file(os.path.join(base_dir, "002_system.txt"))
    user_prompt = read_file(os.path.join(base_dir, "002_user.txt"))

    messages = [
        LLMMessage(role=LLMRole.USER, content=[LLMTextContent(text=system_prompt)]),
        LLMMessage(role=LLMRole.USER, content=[LLMTextContent(text=user_prompt)])
    ]

    return messages

def read_file(file_path):
    with open(file_path, "r") as f:
        return f.read()

if __name__ == "__main__":
    setup_logging()

    # tmp_frontier_001()
    tmp_frontier()
