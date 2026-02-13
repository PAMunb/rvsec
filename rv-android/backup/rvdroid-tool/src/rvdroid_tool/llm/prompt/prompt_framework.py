# modules/rvdroid-tool/src/rvdroid_tool/llm/prompt/prompt_framework.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from jinja2 import Environment, FileSystemLoader

from rv_llm.llm.config import PromptConfig
from rv_llm.llm.constants import PromptStrategyType
from rv_android_core.util.error.exceptions import ConfigurationError
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT

class BasePromptStrategy(ABC):
    """
    Abstract base class for all prompt strategies.

    ### Architectural Role:
    - Defines the interface for building system and user prompts.
    - Ensures consistency across different prompt generation approaches.

    ### Usage:
    Subclasses must implement `build_system_prompt` and `build_user_prompt`.
    """
    def __init__(self, env: Environment):
        self.env = env
        self.logger = LoggingManager.get_instance().get_logger(
            "rvdroid_tool.llm.prompt.base_strategy",
            {CONTEXT_COMPONENT: "BasePromptStrategy"}
        )

    @abstractmethod
    def build_system_prompt(self, context: Dict[str, Any]) -> str:
        """
        Builds the system-level prompt for the LLM.

        Args:
            context: A dictionary containing all necessary context for the system prompt.

        Returns:
            The constructed system prompt string.
        """
        pass

    @abstractmethod
    def build_user_prompt(self, context: Dict[str, Any]) -> str:
        """
        Builds the user-level prompt for the LLM.

        Args:
            context: A dictionary containing all necessary context for the user prompt.

        Returns:
            The constructed user prompt string.
        """
        pass

class PromptFramework:
    """
    Manages the creation and selection of prompt strategies.

    ### Architectural Role:
    - Acts as a factory for `BasePromptStrategy` implementations.
    - Centralizes the loading of Jinja2 templates from the file system.
    - Ensures the correct prompt strategy is instantiated based on configuration.

    ### System Integration:
    - Uses `jinja2.Environment` for template management.
    - Integrates with `rv-android-core` logging.

    ### Usage:
    Call `create_prompt_strategy` with a `PromptConfig` to get a strategy instance.
    """

    def __init__(self, template_dir: str):
        """
        Initializes the PromptFramework with the base directory for templates.

        Args:
            template_dir: The absolute path to the directory containing prompt templates.
        """
        self.template_dir = template_dir
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.logger = LoggingManager.get_instance().get_logger(
            "rvdroid_tool.llm.prompt.prompt_framework",
            {CONTEXT_COMPONENT: "PromptFramework"}
        )
        self.logger.info(f"PromptFramework initialized with template directory: {template_dir}")

    def create_prompt_strategy(self, prompt_config: PromptConfig) -> BasePromptStrategy:
        """
        Creates and returns a prompt strategy instance based on the provided configuration.

        Args:
            prompt_config: Configuration object for the prompt strategy.

        Returns:
            An instance of a concrete `BasePromptStrategy`.

        Raises:
            ConfigurationError: If the strategy type is unknown or not implemented.
        """
        strategy_type = prompt_config.strategy_type

        if strategy_type == PromptStrategyType.STANDARD: # This will be our guidance strategy
            from rvdroid_tool.llm.prompt.strategies.guidance_strategy import GuidanceStrategy
            return GuidanceStrategy(self.env)
        # Add other strategy types here as needed
        # elif strategy_type == PromptStrategyType.BATCH_ACTION:
        #     from .strategies.batch_action_strategy import BatchActionStrategy
        #     return BatchActionStrategy(self.env)
        # elif strategy_type == PromptStrategyType.MULTIMODAL:
        #     from .strategies.multimodal_strategy import MultimodalStrategy
        #     return MultimodalStrategy(self.env)
        else:
            raise ConfigurationError(f"Unknown or unsupported prompt strategy type: {strategy_type}")
