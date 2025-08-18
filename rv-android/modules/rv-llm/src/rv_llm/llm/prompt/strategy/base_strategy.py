"""Base prompt strategy for the prompt system.

This module defines the base PromptStrategy class that all specialized strategies
should inherit from, providing a standardized interface for prompt generation.
"""

import abc
from typing import Any, Dict, List, Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.config import PromptConfig
from rv_llm.llm.constants import ContextEntry, PromptStrategyType
from rv_llm.llm.data_structures import LLMMessage, LLMRole, LLMTextContent, LLMImageContent, LLMContentType
from rv_llm.llm.constants import StateEntry
import os

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
            template_repository=None,
            config: Optional[PromptConfig] = None
    ):
        """Initialize the prompt strategy.
        
        Args:
            name: A unique identifier for the strategy.
            information_manager: The information manager to use.
            template_repository: The template repository to use.
            config: Optional PromptConfig for strategy configuration.
        """
        self.name = name
        self.information_manager = information_manager
        self.template_repository = template_repository
        self.config = config

        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            f"rv_llm.llm.prompt.strategy.{name}",
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
    def configure_from_config(self, config: PromptConfig) -> None:
        """
        Configure strategy with PromptConfig for monitored operations testing.
        
        ### Architectural Note:
        This method provides the primary interface for strategy configuration
        using the modern PromptConfig system. It extracts strategy-specific parameters
        and applies them to the strategy for prompt generation operations.
        
        ### Configuration Strategy:
        - Extracts strategy-specific parameters from PromptConfig
        - Creates configuration dictionary for internal processing
        - Validates configuration before applying
        - Provides error handling and logging for configuration failures
        
        Args:
            config: PromptConfig instance with strategy configuration
            
        Raises:
            ValueError: If configuration is invalid or conversion fails
        """
        self.logger.info(f"Configuring strategy {self.name} from PromptConfig")

        try:
            # Extract strategy parameters from PromptConfig
            strategy_params = config.get_strategy_parameters()

            # Create configuration dictionary from PromptConfig parameters
            config_dict = {
                "strategy_name": config.strategy_type,
                "max_context_length": config.max_context_length,
                "parser_type": config.parser_type,
                "visitor_type": config.visitor_type,
                **{k: v for k, v in strategy_params.items() if k.startswith("strategy_")}
            }

            # Store the config directly for easier access
            self.config = config
            
            # Use existing configure method with converted config
            self.configure(config_dict)

            self.logger.info(f"Strategy {self.name} configured successfully from LLMConfig")

        except Exception as e:
            error_msg = f"Failed to configure strategy {self.name} from LLMConfig: {e}"
            self.logger.error(error_msg)
            # Import here to avoid circular dependencies
            from rv_android_core.util.error.exceptions import RVLLMConfigurationError
            raise RVLLMConfigurationError(error_msg) from e

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
        self.logger.warning(f"No template specified for strategy {self.name}, using 'single'")
        return PromptStrategyType.SINGLE

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
            content: list[LLMContentType] = [LLMTextContent(text=content_text)]

            # Add image message (screenshot)
            if role == LLMRole.USER:
                image_message = _create_image_message(state)
                if image_message is not None:
                    content.append(image_message)

            message = LLMMessage(
                role=role,
                content=content
            )
            messages.append(message)

        return messages


def _create_image_message(state: Dict[str, Any]):
    if StateEntry.SCREENSHOT_PATH in state and state[StateEntry.SCREENSHOT_PATH]:
        screenshot_path = state[StateEntry.SCREENSHOT_PATH]
        if os.path.exists(screenshot_path):
            encoded_string = get_image_base64_local(screenshot_path)
            if encoded_string is not None:
                return LLMImageContent(url=screenshot_path, encoded_string=encoded_string)
    return None

def get_image_base64_local(image_path: str) -> str:
    # TODO traduzir para ingles
    """
    Lê uma imagem de um arquivo local e retorna sua string codificada em base64.
    """
    try:
        with open(image_path, "rb") as image_file:
            import base64
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return encoded_string
    # TODO usar error handler
    except FileNotFoundError:
        print(f"Erro: O arquivo de imagem não foi encontrado em: {image_path}")
        return None
    except Exception as e:
        print(f"Erro ao ler ou codificar a imagem local: {e}")
        return None