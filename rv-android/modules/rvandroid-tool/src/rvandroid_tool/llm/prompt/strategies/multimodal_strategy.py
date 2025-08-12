
from typing import Any, Dict, List, Optional

from rv_llm.llm.constants import (ContextEntry, FragmentType, PromptStrategyType,
                                  StateEntry)
from rv_llm.llm.data_structures import LLMMessage, LLMTextContent, LLMImageContent, LLMRole
from rv_llm.llm.prompt.information.fragment_manager import InformationManager
from rv_llm.llm.prompt.strategy.base_strategy import PromptStrategy
from rv_llm.llm.prompt.template.jinja_repository import Jinja2TemplateRepository


class MultimodalStrategy(PromptStrategy):

    # Default template to use if none specified
    DEFAULT_TEMPLATE = PromptStrategyType.MULTIMODAL

    def __init__(
            self,
            name: str = PromptStrategyType.MULTIMODAL,
            information_manager: Optional[InformationManager] = None,
            template_repository: Optional[Jinja2TemplateRepository] = None
    ):
        """Initialize the multimodal strategy.

        Args:
            name: The name of the strategy (default: "multimodal").
            information_manager: The information manager to use.
            template_repository: The template repository to use.
        """
        super().__init__(name, information_manager, template_repository)

    def _generate_prompt(
            self,
            state: Dict[str, Any],
            context: Optional[Dict[str, Any]] = None
    ) -> List[LLMMessage]:

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
                **info,  # Include information from fragments
                **context,  # Include context information
                ContextEntry.TESTING_HISTORY: testing_history
            }
            
            # Check for screenshot image in state
            screenshot_image = state.get('screenshot_image')
            has_screenshot = screenshot_image is not None

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

            # Add multimodal-specific additional guidelines if needed
            if "additional_guidelines" not in variables:
                action_limit = context.get(ContextEntry.ACTION_LIMIT, 3)
                if has_screenshot:
                    variables["additional_guidelines"] = (
                        f"Based on the screenshot provided, generate 1-{action_limit} test actions in JSON format. "
                        "Use visual elements from the image to identify specific targets for interaction. "
                        "Focus on exploring unique functionality and potential monitored operations features."
                    )
                else:
                    variables["additional_guidelines"] = (
                        f"Generate 1-{action_limit} test actions in JSON format based on the screen description. "
                        "Focus on exploring unique functionality and potential monitored operations features."
                    )

            # Generate messages with multimodal support
            if self.template_repository:
                # Get template messages as text
                template_messages = self.template_repository.create_messages(template_name, variables)
                
                if not template_messages:
                    self.logger.warning(f"No messages generated for template: {template_name}")
                    return self._create_fallback_multimodal_messages(has_screenshot, screenshot_image)
                
                # Convert template messages to LLMMessage objects with multimodal support
                return self._create_multimodal_messages(template_messages, screenshot_image)
            else:
                self.logger.error("Template repository not initialized")
                return self._create_fallback_multimodal_messages(has_screenshot, screenshot_image)
        except Exception as e:
            self.logger.error(f"Error generating multimodal prompt: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": f"PromptStrategy:{self.name}",
                    "state_id": state.get("id", "unknown")
                }
            )
            # Return a simple fallback prompt
            screenshot_image = state.get('screenshot_image')
            return self._create_fallback_multimodal_messages(screenshot_image is not None, screenshot_image)

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


    def _create_multimodal_messages(self, template_messages: List[Dict[str, str]], screenshot_image: Optional[LLMImageContent]) -> List[LLMMessage]:
        """
        Convert template messages to LLMMessage objects with multimodal support.
        
        ### Multimodal Message Creation Strategy:
        - Converts template dictionary messages to LLMMessage objects
        - Adds screenshot image content to user messages when available
        - Maintains message roles and text content from templates
        - Creates proper multimodal messages for LLM processing
        
        Args:
            template_messages: List of message dictionaries from template
            screenshot_image: Optional LLMImageContent with screenshot
            
        Returns:
            List of LLMMessage objects for multimodal LLM processing
        """
        llm_messages = []
        
        for msg in template_messages:
            # Extract role and content from template message
            role_str = msg.get("role", "user").lower()
            content_text = msg.get("content", "")
            
            # Map string role to LLMRole enum
            if role_str == "system":
                role = LLMRole.SYSTEM
            elif role_str == "assistant":
                role = LLMRole.ASSISTANT
            else:
                role = LLMRole.USER
            
            # Create content list starting with text
            content = [LLMTextContent(text=content_text)]
            
            # Add screenshot to user messages if available
            if role == LLMRole.USER and screenshot_image:
                content.append(screenshot_image)
                self.logger.debug("Added screenshot to user message for multimodal processing")
            
            # Create LLMMessage with multimodal content
            llm_message = LLMMessage(
                role=role,
                content=content
            )
            llm_messages.append(llm_message)
        
        return llm_messages
    
    def _create_fallback_multimodal_messages(self, has_screenshot: bool, screenshot_image: Optional[LLMImageContent]) -> List[LLMMessage]:
        """
        Create fallback multimodal messages when template processing fails.
        
        ### Fallback Message Strategy:
        - Creates simple user message with basic testing instructions
        - Includes screenshot in message content if available
        - Provides different instructions based on screenshot availability
        - Ensures system can continue even when templates fail
        
        Args:
            has_screenshot: Whether screenshot is available
            screenshot_image: Optional LLMImageContent with screenshot
            
        Returns:
            List containing single fallback LLMMessage
        """
        if has_screenshot:
            content_text = (
                "Based on the screenshot provided, generate a JSON array of 2-3 testing actions. "
                "Use visual elements from the image to identify specific targets for interaction. "
                "Each action should have action_id, params, and explanation fields."
            )
        else:
            content_text = (
                "Based on the current screen description, generate a JSON array of 2-3 testing actions. "
                "Each action should have action_id, params, and explanation fields."
            )
        
        # Create content list
        content = [LLMTextContent(text=content_text)]
        
        # Add screenshot if available
        if has_screenshot and screenshot_image:
            content.append(screenshot_image)
        
        # Create fallback message
        fallback_message = LLMMessage(
            role=LLMRole.USER,
            content=content
        )
        
        return [fallback_message]
