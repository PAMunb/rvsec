"""Batch action prompt strategy implementation.

This module defines the BatchActionStrategy class, which implements a specialized
prompt generation strategy for generating batches of testing actions.
"""

from typing import Any, Dict, List, Optional

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.constants import (ContextEntry, FragmentType, PromptStrategyType,
                                     StateEntry)
from rvandroid.llm.prompt.information.fragment_manager import InformationManager
from rvandroid.llm.prompt.strategy.base_strategy import PromptStrategy
from rvandroid.llm.prompt.template.jinja_repository import Jinja2TemplateRepository


class BatchActionStrategy(PromptStrategy):
    """Batch action prompt generation strategy.
    
    This strategy is specialized for generating prompts that ask the LLM to
    produce a batch of testing actions in a structured format (e.g., JSON).
    It can generate 1-10 actions to be executed in batch.
    """

    # Default template to use if none specified
    DEFAULT_TEMPLATE = PromptStrategyType.BATCH_ACTION

    def __init__(
            self,
            name: str = PromptStrategyType.BATCH_ACTION,
            information_manager: Optional[InformationManager] = None,
            template_repository: Optional[Jinja2TemplateRepository] = None
    ):
        """Initialize the batch action strategy.
        
        Args:
            name: The name of the strategy (default: "batch_action").
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

    def should_use_batch(self, state: Dict[str, Any]) -> bool:
        """Determine if batch actions should be used for the current state.
        
        Args:
            state: The current application state.
            
        Returns:
            True if batch actions should be used, False otherwise.
        """
        # Check for UI patterns
        if StateEntry.UI_PATTERNS in state:
            return True

        # Check for detected pattern
        if StateEntry.DETECTED_PATTERN in state:
            pattern = state[StateEntry.DETECTED_PATTERN]
            confidence = pattern.get("confidence", 0)
            # Only use batch if pattern confidence is high enough
            return confidence >= 0.7

        return False

    def _generate_prompt(
            self,
            state: Dict[str, Any],
            context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """Generate a batch action prompt for the given state and context.
        
        Args:
            state: The current state (e.g., app UI state, test state).
            context: Additional contextual information.
            
        Returns:
            A list of message dictionaries with role and content.
        """
        if context is None:
            context = {}

        try:
            # Always use the batch_action template
            template_name = self.get_template_name(context)
            self.logger.debug(f"Using template: {template_name}")

            # Get information from fragments
            info = {}
            if self.information_manager:
                info = self.information_manager.compose_information(state, context)

            # Extract testing history from context if available
            testing_history = context.get(ContextEntry.TESTING_HISTORY, "")

            # Combine information from state, fragments, and context to create variables for template
            variables = {
                **state,  # Include state information (like activity)
                **info,   # Include information from fragments
                **context,  # Include context information
                ContextEntry.TESTING_HISTORY: testing_history
            }

            # Format basic UI information if not present
            if FragmentType.UI_ELEMENTS not in variables and StateEntry.SCREEN_DESCRIPTION not in state and StateEntry.SCREEN_PATTERNS in state:
                # Set both ui_elements and screen_elements for compatibility with different templates
                variables["ui_elements"] = self._format_screen_elements(state[StateEntry.SCREEN_PATTERNS])
                variables["screen_elements"] = variables["ui_elements"]
            elif StateEntry.SCREEN_DESCRIPTION in state:
                # Set both ui_elements and screen_elements for compatibility with different templates
                variables["ui_elements"] = state[StateEntry.SCREEN_DESCRIPTION]
                variables["screen_elements"] = state[StateEntry.SCREEN_DESCRIPTION]
            
            # Ensure static_context is defined (even if empty) for templates that expect it
            if "static_context" not in variables:
                variables["static_context"] = ""

            # Add batch-specific additional guidelines if needed
            if "additional_guidelines" not in variables:
                action_limit = context.get(ContextEntry.ACTION_LIMIT, 5)
                variables["additional_guidelines"] = (
                    f"Generate 1-{action_limit} test actions in JSON format. "
                    "Focus on exploring unique functionality and potential monitored operations features. "
                    "Ensure each action is specific and executable by an automated testing system."
                )

            # Generate messages from template
            if self.template_repository:
                messages = self.template_repository.create_messages(template_name, variables)

                if not messages:
                    self.logger.warning(f"No messages generated for template: {template_name}")
                    # Fall back to a simple message
                    messages = [{
                        "role": "user",
                        "content": (
                            "Based on the current screen, generate a JSON array of 3-5 testing actions. "
                            "Each action should have action_type, target, and description fields."
                        )
                    }]

                return messages
            else:
                self.logger.error("Template repository not initialized")
                return [{
                    "role": "user",
                    "content": (
                        "Based on the current screen, generate a JSON array of 3-5 testing actions. "
                        "Each action should have action_type, target, and description fields."
                    )
                }]
        except Exception as e:
            self.logger.error(f"Error generating batch action prompt: {e}", exc_info=True)
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
                "content": (
                    "Based on the current screen, generate a JSON array of 3-5 testing actions. "
                    "Each action should have action_type, target, and description fields."
                )
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

        # For batch actions, provide more detailed information about components
        formatted_parts = []

        # Add screen title and description if available
        title = screen.get("title", "")
        if title:
            formatted_parts.append(f"Screen title: {title}")

        # Add screen size if available
        size = screen.get("size", {})
        if size:
            width = size.get("width", "unknown")
            height = size.get("height", "unknown")
            formatted_parts.append(f"Screen size: {width} x {height}")

        # Add components with more details
        formatted_parts.append("UI Components:")

        for i, component in enumerate(components):
            component_type = component.get("type", "unknown")
            component_text = component.get("text", "")
            component_id = component.get("resource_id", "")
            component_clickable = "clickable" if component.get("clickable", False) else "not clickable"
            component_enabled = "enabled" if component.get("enabled", True) else "disabled"

            details = []
            if component_text:
                details.append(f"text='{component_text}'")
            if component_id:
                details.append(f"id='{component_id}'")

            # Add bounds if available
            bounds = component.get("bounds", {})
            if bounds:
                left = bounds.get("left", 0)
                top = bounds.get("top", 0)
                right = bounds.get("right", 0)
                bottom = bounds.get("bottom", 0)
                details.append(f"bounds=[{left},{top},{right},{bottom}]")

            details.append(component_clickable)
            details.append(component_enabled)

            formatted_parts.append(f"{i + 1}. {component_type}: {', '.join(details)}")

        return "\n".join(formatted_parts)
