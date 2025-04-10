# rvandroid/llm/service/prompt_processor.py
from typing import Dict, List, Any, Optional

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.experiment.event.bus import EventBus
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class PromptProcessor:
    """
    Handles the creation and management of prompts for LLM interaction.

    ### Architectural Decisions:
    - Encapsulates prompt generation logic in a focused component
    - Delegates specific prompt strategy implementations to strategy classes
    - Provides a consistent interface for prompt generation
    - Enables custom prompt strategies through configuration
    - Supports both traditional prompt generation and screen parsing for pattern detection

    ### Role in the System:
    - Generates prompts based on application state and configuration
    - Applies prompt strategies to create effective LLM inputs
    - Formats prompts according to the required LLM interface
    - Handles context management for prompt generation
    - Parses screen state for pattern detection and batch action generation
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
            {CONTEXT_COMPONENT: "PromptProcessor"}
        )

        # Store configuration
        self.config = config
        self.static_data = static_data

        # Create prompt strategy
        self.strategy = config.create_strategy(static_data)

        strategy_name = self.strategy.__class__.__name__ if self.strategy else "unknown"
        self.logger.info(f"Prompt processor initialized with strategy: {strategy_name}")

    def parse_screen(self, state: Dict[str, Any]):
        """
        Parse the screen from state data.
        
        This method is used by batch action strategies to get the parsed screen
        without generating full prompts.
        
        Args:
            state: Current application state
            
        Returns:
            ScreenDescription or None if parsing fails
        """
        self.logger.debug("Parsing screen for pattern detection")
        
        try:
            # Use the strategy to process the screen
            screen_description = self.strategy.process_screen(state)
            
            if screen_description:
                # Extract available action IDs and add to state
                available_action_ids = []
                for item in screen_description.items:
                    for action in item.actions:
                        available_action_ids.append(str(action.id))
                
                # Update state with screen data
                state["available_actions"] = available_action_ids
                self.logger.debug(f"Added {len(available_action_ids)} available action IDs to state")
            
            return screen_description
            
        except Exception as e:
            self.logger.error(f"Error parsing screen: {e}", exc_info=True)
            return None

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
            # Check if we already have a parsed screen in state
            screen_description = state.get("screen_description")
            
            # If no parsed screen, parse it now
            if not screen_description:
                screen_description = self.strategy.process_screen(state)
                
                # Store the screen description in state for later use
                if screen_description:
                    state["screen_description"] = screen_description
                    
                    # Extract available action IDs and add to state if not already present
                    if "available_actions" not in state:
                        available_action_ids = []
                        for item in screen_description.items:
                            for action in item.actions:
                                available_action_ids.append(str(action.id))
                        
                        state["available_actions"] = available_action_ids
                        self.logger.debug(f"Added {len(available_action_ids)} available action IDs to state")
            
            # Generate prompts using the strategy
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
       