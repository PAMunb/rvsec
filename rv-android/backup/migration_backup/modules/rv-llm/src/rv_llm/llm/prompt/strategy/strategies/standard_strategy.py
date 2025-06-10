"""Standard prompt strategy implementation.

This module defines the StandardStrategy class, which implements a basic
prompt generation strategy that works with most use cases and generates
exactly one action per response.
"""

from typing import Any, Dict, List, Optional

from rv_llm.config.component_configurator import ComponentConfigurator
from rv_llm.llm.constants import (PromptStrategyType)
from rv_llm.llm.prompt.information.fragment_manager import InformationManager
from rv_llm.llm.prompt.strategy.base_strategy import PromptStrategy
from rv_llm.llm.prompt.template.jinja_repository import Jinja2TemplateRepository


class StandardStrategy(PromptStrategy):
    """Standard prompt generation strategy.
    
    This strategy provides a basic implementation that works with most use cases
    by using the appropriate template based on the context and including all
    relevant information. It always generates exactly one action per response.
    """

    # Default template to use if none specified
    DEFAULT_TEMPLATE = PromptStrategyType.STANDARD

    def __init__(
            self,
            name: str = PromptStrategyType.STANDARD,
            information_manager: Optional[InformationManager] = None,
            template_repository: Optional[Jinja2TemplateRepository] = None
    ):
        """Initialize the standard strategy.
        
        Args:
            name: The name of the strategy (default: "standard").
            information_manager: The information manager to use.
            template_repository: The template repository to use.
        """
        super().__init__(name, information_manager, template_repository)

    def configure(self, config: ComponentConfigurator) -> None:
        """Configure the strategy with the given configuration.
        
        Args:
            config: The configuration to use.
        """
        super().configure(config)

        # Other configuration specific logic can be added here

    def _generate_prompt(
            self,
            state: Dict[str, Any],
            context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """Generate a prompt for the given state and context.
        
        This strategy always generates a prompt that will result in exactly
        one action per response, even though it returns a list for consistency
        with the strategy interface.
        
        Args:
            state: The current state (e.g., app UI state, test state).
            context: Additional contextual information.
            
        Returns:
            A list of message dictionaries with role and content.
        """
        if context is None:
            context = {}

        try:
            # Determine which template to use based on strategy's template selection logic
            template_name = self.get_template_name(context)
            self.logger.debug(f"Using template: {template_name}")

            # Get information from fragments
            info = {}
            if self.information_manager:
                info = self.information_manager.compose_information(state, context)

            # Combine information with context to create variables for template
            variables = {**state, **info, **context}

            # Format basic UI information if not present
            # if FragmentType.UI_ELEMENTS not in variables and StateEntry.SCREEN_DESCRIPTION not in state and StateEntry.SCREEN_PATTERNS in state:
            #     variables["ui_elements"] = self._format_screen_elements(state[StateEntry.SCREEN_PATTERNS])
            # elif StateEntry.SCREEN_DESCRIPTION in state:
            #     variables["ui_elements"] = state[StateEntry.SCREEN_DESCRIPTION]

            # Add prompt guidance for single action
            if "additional_guidelines" not in variables:
                variables["additional_guidelines"] = (
                    "Suggest exactly ONE specific action that can be executed to test the application. "
                    "Do not provide multiple options or actions."
                )

            # Generate messages from template
            if self.template_repository:
                # Try to generate messages from the specified template
                messages = self.template_repository.create_messages(template_name, variables)

                if not messages and ":" in template_name:
                    # If template name contains a prefix (e.g., "rvdroid:exploration"),
                    # try the base name without the prefix as a fallback
                    base_template_name = template_name.split(":", 1)[1]
                    self.logger.warning(f"Template not found: {template_name}, trying fallback: {base_template_name}")
                    messages = self.template_repository.create_messages(base_template_name, variables)

                if not messages:
                    self.logger.warning(f"No messages generated for template: {template_name}")
                    # Fall back to a simple message
                    messages = [{
                        "role": "user",
                        "content": (
                            "Based on the current application state, suggest ONE specific test action "
                            "that would help explore the functionality. Be specific about which UI element "
                            "to interact with and how."
                        )
                    }]

                return messages
            else:
                self.logger.error("Template repository not initialized")
                return [{
                    "role": "user",
                    "content": (
                        "Based on the current application state, suggest ONE specific test action "
                        "that would help explore the functionality. Be specific about which UI element "
                        "to interact with and how."
                    )
                }]
        except Exception as e:
            self.logger.error(f"Error generating prompt: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": f"PromptStrategy:{self.name}",
                    "state_id": state.get("id", "unknown")
                }
            )
            # Return a simple fallback prompt
            return [{
                "role": "user",
                "content": "Suggest ONE specific test action for the current screen."
            }]

    def _format_screen_elements(self, screen: Dict[str, Any]) -> str:
        """Format screen elements for display in the prompt.
        
        Args:
            screen: The screen information from the state.
            
        Returns:
            A formatted string representation of the screen elements.
        """
        if not screen:
            return "No screen information available."

        components = screen.get("components", [])
        if not components:
            return "No UI components found on screen."

        formatted_components = []

        for i, component in enumerate(components):
            component_type = component.get("type", "unknown")
            component_text = component.get("text", "")
            component_id = component.get("resource_id", "")

            if component_text:
                formatted_components.append(
                    f"{i + 1}. {component_type}: '{component_text}' "
                    f"(ID: {component_id})"
                )
            else:
                formatted_components.append(
                    f"{i + 1}. {component_type} "
                    f"(ID: {component_id})"
                )

        return "\n".join(formatted_components)
