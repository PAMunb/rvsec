# rvandroid/llm/service/prompt_processor.py
from typing import Dict, List, Any, Optional

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.experiment.event_system import EventBus
from rvandroid.model.static import StaticAnalysisData
from rvandroid.util.logging_manager import LoggingManager


class PromptProcessor:
    """
    Handles the creation and management of prompts for LLM interaction.

    ### Architectural Decisions:
    - Encapsulates prompt generation logic in a focused component
    - Delegates specific prompt strategy implementations to strategy classes
    - Provides a consistent interface for prompt generation
    - Enables custom prompt strategies through configuration

    ### Role in the System:
    - Generates prompts based on application state and configuration
    - Applies prompt strategies to create effective LLM inputs
    - Formats prompts according to the required LLM interface
    - Handles context management for prompt generation
    """

    def __init__(self, config: ComponentConfigurator, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the prompt processor.

        Args:
            config: Component configurator for prompt strategy configuration
            static_data: Static analysis data for prompt enrichment
        """
        # Get system services
        self.event_bus = EventBus.get_instance()
        logging_manager = LoggingManager.get_instance()

        # Configure logging
        self.logger = logging_manager.get_logger(
            "llm.service.prompt_processor",
            {LoggingManager.CONTEXT_COMPONENT: "PromptProcessor"}
        )

        # Store configuration
        self.config = config
        self.static_data = static_data

        # Create prompt strategy
        self.strategy = config.create_strategy(static_data)

        strategy_name = self.strategy.__class__.__name__ if self.strategy else "unknown"
        self.logger.info(f"Prompt processor initialized with strategy: {strategy_name}")

    def generate_prompts(self, state: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Generate prompts for the given application state.

        Args:
            state: Current application state

        Returns:
            List of prompt messages in the format expected by the LLM
        """
        self.logger.debug(f"Generating prompts using {self.strategy.__class__.__name__}")

        try:
            # Use the strategy to generate prompts
            messages = self.strategy.generate_prompts(state)

            # Debug log the prompt sizes
            if len(messages) >= 2:
                self.logger.debug(f"System prompt length: {len(messages[0]['content'])}")
                self.logger.debug(f"User prompt length: {len(messages[1]['content'])}")

            return messages

        except Exception as e:
            self.logger.error(f"Error generating prompts: {e}", exc_info=True)

            # Fallback to basic prompts if strategy fails
            system_prompt = "You are an Android UI testing expert. Analyze the current app state and suggest the next action to take for testing."
            user_prompt = f"Current activity: {state.get('activity', 'unknown')}\nSuggest one test action."

            return [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
       