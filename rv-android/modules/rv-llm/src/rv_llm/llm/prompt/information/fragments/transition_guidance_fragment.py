"""Transition guidance information fragment for the prompt system.

This module defines a specialized fragment for extracting and formatting transition
guidance information from application state to provide navigation context and
exploration recommendations for LLM-driven testing systems.

### Architectural Overview:
The TransitionGuidanceFragment serves as the interface between navigation analysis
systems and prompt generation, converting transition data and exploration insights
into structured guidance for intelligent navigation decision making.

### Core Responsibilities:
- **Navigation Context**: Processes current activity and navigation path information
- **Exploration Guidance**: Identifies unexplored actions and suggested targets
- **Static Analysis Integration**: Incorporates static transition analysis for planning
- **History Management**: Tracks visited activities and transition patterns

### Integration Architecture:
- Consumes transition guidance data from navigation analysis systems
- Integrates with rv-android-core error handling and logging infrastructure
- Supports both dynamic exploration data and static analysis insights
- Maintains compatibility with different navigation tracking backends

### Design Patterns:
- **Information Aggregator**: Combines multiple navigation data sources
- **Template Method**: Consistent processing pipeline with specialized formatting
- **Error Isolation**: Comprehensive error handling to prevent prompt generation failures
- **Context Enrichment**: Enhances navigation decisions through structured guidance
"""

from typing import Dict, Any, Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.error.exceptions import RVParsingError

from rv_llm.llm.constants import StateEntry
from rv_llm.llm.prompt.information.base_fragment import InformationFragment


class TransitionGuidanceFragment(InformationFragment):
    """Fragment for formatting transition guidance data for LLM templates.
    
    ### Architectural Role:
    This fragment serves as the bridge between navigation analysis systems and
    prompt generation, ensuring reliable conversion of transition data into
    actionable guidance for LLM navigation decision making.
    
    ### Processing Strategy:
    - Aggregates navigation path, activity visit counts, and exploration data
    - Implements priority-based guidance with recent activity emphasis
    - Maintains configurable limits to prevent context bloat
    - Provides comprehensive error handling for malformed navigation data
    
    ### Integration Points:
    - Consumes transition guidance from navigation analysis components
    - Integrates with rv-android-core error handling and logging systems
    - Supports both dynamic navigation tracking and static analysis data
    - Delivers formatted guidance for template-based prompt generation
    """

    def __init__(self, name: str = "transition_guidance", priority: int = 200):
        """Initialize the transition guidance fragment with comprehensive infrastructure.
        
        Sets up the complete fragment processing pipeline including error handling,
        logging, and navigation data processing systems for robust guidance generation.
        
        Args:
            name: The name of the fragment for identification
            priority: The priority of the fragment (higher values are displayed first)
        """
        super().__init__(name, priority)
        
        # Initialize logging infrastructure
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.prompt.transition_guidance_fragment",
            {CONTEXT_COMPONENT: "TransitionGuidanceFragment"}
        )
        
        # Initialize error handling
        self.error_handler = ErrorHandler.get_instance()
        
        self.logger.debug("Initialized TransitionGuidanceFragment for navigation guidance processing")

    @ErrorHandler.handle_errors(component="TransitionGuidanceFragment", phase="generation", reraise=True)
    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """Generate transition guidance formatted text from navigation state information.
        
        Processes transition guidance data from navigation analysis systems to generate
        structured navigation recommendations and exploration context for LLM prompt
        integration. Implements comprehensive validation and error handling.
        
        Args:
            state: The current state dictionary containing transition guidance information
            context: Optional additional context information for processing customization
            
        Returns:
            Formatted transition guidance text for inclusion in prompts
            
        Raises:
            RVParsingError: If state validation fails or contains invalid data
        """
        if not state:
            raise RVParsingError(
                "State dictionary is empty or None",
                parser_type="TransitionGuidanceFragment"
            )
            
        # Get transition guidance information from state
        guidance = state.get(StateEntry.TRANSITION_GUIDANCE, {})
        if not guidance:
            self.logger.debug("No transition guidance information found in state")
            return ""
            
        if not isinstance(guidance, dict):
            self.logger.warning(f"Invalid guidance format: {type(guidance)}")
            return "Error: Invalid transition guidance format"

        # Begin formatted output with structured sections
        formatted_sections = []
        formatted_sections.append("## Transition Guidance")

        # Add current activity and visit information
        current_activity = guidance.get("current_activity", "unknown")
        visit_count = guidance.get("visit_count", 0)
        formatted_sections.append(f"Current activity: {current_activity} (visited {visit_count} times)")

        # Add navigation path if available
        if "navigation_path" in guidance:
            path = guidance["navigation_path"]
            if isinstance(path, (list, tuple)) and path:
                formatted_sections.append("\n### Navigation Path")
                # Show last 5 activities for brevity
                display_path = path[-5:] if len(path) > 5 else path
                path_text = " → ".join(str(activity) for activity in display_path)
                if len(path) > 5:
                    path_text += f" (showing last 5 of {len(path)} activities)"
                formatted_sections.append(path_text)
            elif "navigation_path" in guidance:
                formatted_sections.append("\n### Navigation Path")
                formatted_sections.append("No navigation history yet.")

        # Add unexplored actions information
        unexplored_actions = guidance.get("unexplored_actions", [])
        if isinstance(unexplored_actions, (list, tuple)) and unexplored_actions:
            formatted_sections.append("\n### Unexplored Actions")
            action_list = ", ".join([f"Action {action_id}" for action_id in unexplored_actions[:10]])
            count_text = f"There are {len(unexplored_actions)} unexplored actions on this screen: {action_list}"
            if len(unexplored_actions) > 10:
                count_text += f" (+ {len(unexplored_actions) - 10} more)"
            formatted_sections.append(count_text)

        # Add transition suggestions
        suggested_targets = guidance.get("suggested_targets", [])
        if isinstance(suggested_targets, (list, tuple)) and suggested_targets:
            formatted_sections.append("\n### Suggested Activities to Explore")
            for target in suggested_targets[:3]:  # Limit to top 3 for brevity
                if isinstance(target, dict):
                    name = target.get("name", "unknown")
                    visits = target.get("visits", 0)
                    action_ids = target.get("action_ids", [])
                    
                    if isinstance(action_ids, (list, tuple)):
                        action_text = ", ".join([f"Action {action_id}" for action_id in action_ids[:3]])
                        if len(action_ids) > 3:
                            action_text += f" (+ {len(action_ids) - 3} more)"
                    else:
                        action_text = "No actions available"
                    
                    formatted_sections.append(f"- {name} (visited {visits} times) via {action_text}")

        # Add static transition information
        static_transitions = guidance.get("static_transitions", [])
        if isinstance(static_transitions, (list, tuple)) and static_transitions:
            formatted_sections.append("\n### Potential Transitions (Static Analysis)")
            for transition in static_transitions[:5]:  # Limit to 5 for brevity
                if isinstance(transition, dict):
                    target = transition.get("target", "unknown")
                    action_id = transition.get("action_id", "?")
                    visited = "✓" if transition.get("visited", False) else "✗"
                    formatted_sections.append(f"- {target} via Action {action_id} [Visited: {visited}]")
            
            if len(static_transitions) > 5:
                formatted_sections.append(f"(+ {len(static_transitions) - 5} more transitions)")

        # Return formatted guidance
        final_guidance = "\n".join(formatted_sections)
        self.logger.debug(f"Generated transition guidance with {len(formatted_sections)} sections")
        return final_guidance

    @ErrorHandler.handle_errors(component="TransitionGuidanceFragment", phase="inclusion_check")
    def should_include(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        """Determine whether transition guidance should be included in prompt generation.
        
        Validates state content to ensure meaningful transition guidance data is available
        and suitable for prompt inclusion. Implements comprehensive validation to prevent
        empty or invalid guidance data from being included in prompts.
        
        Args:
            state: The current state dictionary to validate
            context: Optional additional context information for inclusion decisions
            
        Returns:
            True if valid transition guidance information is available, False otherwise
        """
        if not state:
            self.logger.debug("Transition guidance not included: empty state")
            return False
            
        # Check if transition guidance exists in state
        if StateEntry.TRANSITION_GUIDANCE not in state:
            self.logger.debug("Transition guidance not included: not available in state")
            return False
            
        guidance = state[StateEntry.TRANSITION_GUIDANCE]
        
        # Validate guidance data structure
        if not isinstance(guidance, dict):
            self.logger.debug(f"Transition guidance not included: invalid format {type(guidance)}")
            return False
            
        if not guidance:
            self.logger.debug("Transition guidance not included: empty guidance dictionary")
            return False
            
        # Check for meaningful content in guidance
        meaningful_fields = [
            "current_activity", "navigation_path", "unexplored_actions", 
            "suggested_targets", "static_transitions"
        ]
        
        has_meaningful_content = any(
            field in guidance and guidance[field] 
            for field in meaningful_fields
        )
        
        if has_meaningful_content:
            self.logger.debug("Including transition guidance with meaningful content")
            return True
        else:
            self.logger.debug("Transition guidance not included: no meaningful content found")
            return False
