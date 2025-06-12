"""Base prompt strategy for the prompt system.

This module defines the base PromptStrategy class that all specialized strategies
should inherit from, providing a standardized interface for prompt generation.
"""

import abc
from typing import Any, Dict, List, Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.config.llm_config import LLMConfig
from rv_llm.llm.constants import ContextEntry, PromptStrategyType
from rv_llm.llm.data_structures import LLMMessage, LLMRole, LLMTextContent


class PromptStrategy(abc.ABC):
    """Base class for all prompt generation strategies.
    
    Prompt strategies are responsible for coordinating the prompt generation
    process, deciding which information to include and which templates to use
    based on the current state and context.
    """

    # Default template to use if none specified - should be overridden by subclasses
    DEFAULT_TEMPLATE = None

    def __init__(
            self,
            name: str,
            information_manager=None,
            template_repository=None
    ):
        """Initialize the prompt strategy.
        
        Args:
            name: A unique identifier for the strategy.
            information_manager: The information manager to use.
            template_repository: The template repository to use.
        """
        self.name = name
        self.information_manager = information_manager
        self.template_repository = template_repository
        self.config = None # TODO deprecated

        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            f"llm.prompt.strategy.{name}",
            {CONTEXT_COMPONENT: f"PromptStrategy:{name}"}
        )

        # Set up error handling
        self.error_handler = ErrorHandler.get_instance()

    def configure(self, config_dict: Dict[str, Any]) -> None:
        """
        Configure the strategy with configuration dictionary.
        
        ### Configuration Strategy:
        - Accepts configuration parameters as dictionary
        - Validates required parameters for strategy operation
        - Stores configuration for template and context management
        - Provides error handling for invalid configurations
        
        Args:
            config_dict: Dictionary with strategy configuration parameters
            
        Raises:
            ValueError: If configuration is invalid or missing required parameters
        """
        self.logger.info(f"Configuring strategy: {self.name}")

        # Validate required configuration parameters
        required_params = ["strategy_name"]
        missing_params = [param for param in required_params if param not in config_dict]
        if missing_params:
            error_msg = f"Missing required configuration parameters: {missing_params}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        # Store configuration as dictionary
        self.config = config_dict
        self.logger.debug(f"Strategy {self.name} configured successfully")

    @ErrorHandler.handle_errors(
        component="PromptStrategy",
        operation="configure_from_config"
    )
    def configure_from_config(self, config: LLMConfig) -> None:
        """
        Configure strategy with LLMConfig for monitored operations testing.
        
        ### Architectural Note:
        This method provides the primary interface for strategy configuration
        using the modern LLMConfig system. It extracts strategy-specific parameters
        and applies them to the strategy for prompt generation operations.
        
        ### Configuration Strategy:
        - Extracts strategy-specific parameters from LLMConfig
        - Creates configuration dictionary for internal processing
        - Validates configuration before applying
        - Provides error handling and logging for configuration failures
        
        Args:
            config: LLMConfig instance with strategy configuration
            
        Raises:
            ValueError: If configuration is invalid or conversion fails
        """
        self.logger.info(f"Configuring strategy {self.name} from LLMConfig")

        try:
            # Extract strategy parameters from LLMConfig
            strategy_params = config.get_strategy_parameters()

            # Create configuration dictionary from LLMConfig parameters
            config_dict = {
                "strategy_name": config.strategy_type,
                "template_name": config.template_name,
                "enable_context_caching": config.enable_context_caching,
                "max_context_length": config.max_context_length,
                **{k: v for k, v in strategy_params.items() if k.startswith("strategy_")}
            }

            # Use existing configure method with converted config
            self.configure(config_dict)

            self.logger.info(f"Strategy {self.name} configured successfully from LLMConfig")

        except Exception as e:
            error_msg = f"Failed to configure strategy {self.name} from LLMConfig: {e}"
            self.logger.error(error_msg)
            raise ValueError(error_msg) from e

    def get_template_name(self, context: Optional[Dict[str, Any]] = None) -> str:
        """Get the template name to use for prompt generation.
        
        Template selection priority:
        1. Context-specified template
        2. Configuration-specified template
        3. Strategy default template
        
        Args:
            context: Optional context with template override
            
        Returns:
            Template name to use
        """
        if context is not None and ContextEntry.TEMPLATE in context:
            # First priority: context-specified template
            return context[ContextEntry.TEMPLATE]

        if (self.config is not None and
                isinstance(self.config, dict) and
                self.config.get("template_name") is not None):
            # Second priority: configuration-specified template
            return self.config["template_name"]

        # Third priority: strategy default template
        if self.DEFAULT_TEMPLATE is not None:
            return self.DEFAULT_TEMPLATE

        # Fallback
        self.logger.warning(f"No template specified for strategy {self.name}, using 'standard'")
        return PromptStrategyType.STANDARD

    # TODO deprecated ... deve retornar lista de mensgaens
    @abc.abstractmethod
    def _generate_prompt(
            self,
            state: Dict[str, Any],
            context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """Generate a prompt for the given state and context.

        Args:
            state: The current state (e.g., app UI state, test state).
            context: Additional contextual information.

        Returns:
            A list of message dictionaries with role and content.
        """
        pass

    def generate_prompt(
            self,
            state: Dict[str, Any],
            context: Optional[Dict[str, Any]] = None
    ) -> List[LLMMessage]:
        """Generate LLMMessage objects for the given state and context.
        
        This method converts the dictionary messages from generate_prompt
        to LLMMessage objects. Subclasses can override this for custom behavior.
        
        Args:
            state: The current state (e.g., app UI state, test state).
            context: Additional contextual information.
            
        Returns:
            A list of LLMMessage objects.
        """
        # Get dictionary messages
        dict_messages = self._generate_prompt(state, context)

        if not dict_messages:
            return []

        # Convert to LLMMessage objects
        messages = []
        for msg in dict_messages:
            role_value = msg["role"]
            content_text = msg["content"]

            # Convert role string to LLMRole enum
            role = LLMRole(role_value)

            # Create LLMMessage object
            message = LLMMessage(
                role=role,
                content=[LLMTextContent(text=content_text)]
            )
            messages.append(message)

        return messages
