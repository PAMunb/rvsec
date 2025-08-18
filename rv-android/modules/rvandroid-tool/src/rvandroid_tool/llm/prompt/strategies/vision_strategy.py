"""
Vision prompt strategy implementation for Android testing with coordinate support.

This module implements the VisionStrategy class, providing compact prompt generation
for multimodal LLMs with support for three action types: standard UI actions, text input,
and custom coordinate-based actions for advanced interaction scenarios.
"""

from typing import Any, Dict, List, Optional

from rv_llm.llm.constants import (ContextEntry, FragmentType, PromptStrategyType,
                                  StateEntry)
from rv_llm.llm.prompt.information.fragment_manager import InformationManager
from rv_llm.llm.prompt.strategy.base_strategy import PromptStrategy
from rv_llm.llm.prompt.template.jinja_repository import Jinja2TemplateRepository

from rvandroid_tool.constants import (
    VISION_STRATEGY_NAME,
    VISION_MAX_TOKENS_DEFAULT,
    VISION_TEMPERATURE_DEFAULT
)


class VisionStrategy(PromptStrategy):
    """
    Vision-based prompt generation strategy for Android testing.
    
    ### Architecture Overview:
    Specialized strategy for generating compact, vision-enabled prompts that leverage
    both textual UI descriptions and visual screenshot information. Supports three
    distinct action types for comprehensive Android application testing.
    
    ### Key Features:
    - **Compact Prompts**: Reduces prompt size from 60+ lines to 25-30 lines
    - **Three Action Types**: Standard UI, text input, and coordinate-based actions
    - **Visual Integration**: Seamlessly incorporates screenshots for multimodal LLMs
    - **Context Intelligence**: Includes dynamic context status and coverage information
    - **Strategic Priorities**: Focuses on monitored operations and coverage expansion
    
    ### Action Type Support:
    1. Standard UI Actions: Target UI elements via ItemAction numeric IDs
    2. Text Input Actions: Include text parameters for form filling scenarios  
    3. Custom Coordinate Actions: Enable screenshot-based interaction for games/canvas
    
    ### Template Integration:
    Uses specialized vision templates with context_status fragment for intelligent
    state management and strategic action prioritization based on coverage metrics.
    """

    # Template configuration for vision strategy
    DEFAULT_TEMPLATE = PromptStrategyType.VISION

    def __init__(
            self,
            name: str = PromptStrategyType.VISION,
            information_manager: Optional[InformationManager] = None,
            template_repository: Optional[Jinja2TemplateRepository] = None
    ):
        """
        Initialize multimodal strategy with specialized configuration.

        ### Initialization Strategy:
        Configures strategy for multimodal operation with compact prompt generation
        and comprehensive action type support. Inherits base functionality while
        adding multimodal-specific capabilities.

        Args:
            name: Strategy identifier for registration and selection
            information_manager: Component for information fragment coordination
            template_repository: Template management system for prompt generation
        """
        super().__init__(name, information_manager, template_repository)

    def _generate_prompt(
            self,
            state: Dict[str, Any],
            context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """
        Generate vision-based prompt with compact format and strategic context.
        
        ### Prompt Generation Pipeline:
        1. Extract and validate template configuration
        2. Collect information fragments with context intelligence
        3. Generate compact template variables with strategic priorities
        4. Create template messages for multimodal processing
        
        ### Context Intelligence:
        Incorporates dynamic context including activity visits, MOP coverage,
        recent action history, and available transitions for strategic decision making.
        
        ### Note on Multimodal Integration:
        This method returns standard dictionary messages. The base class handles
        automatic image integration through the generate_prompt() method.
        
        Args:
            state: Current application state with UI and screenshot information
            context: Additional context including testing history and configuration
            
        Returns:
            List of message dictionaries with role and content for template processing
        """
        if context is None:
            context = {}

        try:
            # Use vision template with compact format
            template_name = self.get_template_name(context) or self.DEFAULT_TEMPLATE
            self.logger.debug(f"Using vision template: {template_name}")

            # Collect information fragments with vision focus
            information = {}
            if self.information_manager:
                information = self.information_manager.compose_information(state, context)

            # Build template variables with context intelligence
            template_variables = self._build_template_variables(
                state, context, information
            )

            # Generate messages using template system
            if self.template_repository:
                messages = self.template_repository.create_messages(
                    template_name, template_variables
                )
                
                if not messages:
                    self.logger.warning(f"No messages generated for template: {template_name}")
                    return self._create_fallback_messages()
                
                return messages
            else:
                self.logger.error("Template repository not initialized")
                return self._create_fallback_messages()
                
        except Exception as e:
            self.logger.error(f"Error generating multimodal prompt: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": f"PromptStrategy:{self.name}",
                    "state_id": state.get("id", "unknown"),
                    "multimodal": True
                }
            )
            # Return fallback messages
            return self._create_fallback_messages()

    def _build_template_variables(
            self,
            state: Dict[str, Any],
            context: Dict[str, Any],
            information: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build comprehensive template variables for vision prompt generation.
        
        ### Variable Construction:
        Combines state information, context data, and fragment information into
        a unified variable set optimized for compact vision templates with
        strategic context intelligence.
        
        Args:
            state: Current application state
            context: Testing context and configuration
            information: Information from fragments
            
        Returns:
            Complete template variable dictionary
        """
        variables = {
            **state,
            **information,
            **context
        }

        # Core context information for compact templates
        variables.update({
            "activity": state.get("activity", "unknown"),
            "activity_visits": context.get("activity_visits", 1),
            "mop_current": context.get("mop_current", 0),
            "mop_total": context.get("mop_total", 0),
            "mop_errors": context.get("mop_errors", 0),
            "recent_history": context.get(ContextEntry.TESTING_HISTORY, ""),
            "available_transitions": context.get("available_transitions", "")
        })

        # UI elements formatting with multimodal optimization
        if FragmentType.UI_ELEMENTS not in variables:
            if StateEntry.SCREEN_DESCRIPTION in state:
                variables["ui_elements"] = state[StateEntry.SCREEN_DESCRIPTION]
            elif StateEntry.SCREEN_PATTERNS in state:
                variables["ui_elements"] = self._format_screen_elements_compact(
                    state[StateEntry.SCREEN_PATTERNS]
                )
            else:
                variables["ui_elements"] = "No UI elements available"

        # Vision-specific guidelines with multimodal capabilities
        if "additional_guidelines" not in variables:
            action_limit = context.get(ContextEntry.ACTION_LIMIT, 5)
            variables["additional_guidelines"] = (
                f"Generate 1-{action_limit} strategic actions that form a logical sequence. "
                "Use both UI description and visual screenshot analysis. Prioritize monitored "
                "operations, form completions, and coverage expansion opportunities. "
                "Consider custom coordinate actions for visual elements not in the UI list."
            )

        return variables

    def _format_screen_elements_compact(self, screen: Dict[str, Any]) -> str:
        """
        Format screen elements in compact representation for vision templates.
        
        ### Compact Formatting Strategy:
        Provides concise element descriptions optimized for vision contexts where
        visual information complements textual descriptions. Focuses on actionable
        elements with monitoring annotations.
        
        Args:
            screen: Screen information with UI components
            
        Returns:
            Compact string representation of UI elements
        """
        if not screen or "components" not in screen:
            return "No UI components available"

        components = screen["components"]
        if not components:
            return "No interactive components found"

        # Compact representation for vision context
        formatted_elements = []
        for i, component in enumerate(components[:10]):  # Limit for compact format
            element_type = component.get("type", "element")
            text = component.get("text", "")
            resource_id = component.get("resource_id", "")
            clickable = component.get("clickable", False)
            
            if clickable:
                description = f"{i+1}. {element_type}"
                if text:
                    description += f" '{text}'"
                if resource_id:
                    description += f" ({resource_id.split('/')[-1]})"
                formatted_elements.append(description)

        return "\n".join(formatted_elements) if formatted_elements else "No clickable elements"

    def _create_fallback_messages(self) -> List[Dict[str, str]]:
        """
        Create fallback messages for error recovery scenarios.
        
        ### Fallback Strategy:
        Provides minimal viable messages when template processing fails,
        ensuring testing continuity with basic action generation capabilities.
        The base class will handle image integration automatically.
        
        Returns:
            List containing fallback message dictionary
        """
        fallback_text = (
            "Analyze the screenshot and UI elements. Generate 1-3 strategic testing actions. "
            "Use JSON format with action_id (numeric or 'coord'), params, and explanation fields. "
            "Prioritize monitored operations and coverage expansion. "
            "Use coordinate actions for visual elements not in the UI list."
        )
        
        return [{
            "role": "user",
            "content": fallback_text
        }]