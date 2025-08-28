"""
Vision prompt strategy implementation for Android testing with coordinate support.

This module implements the VisionStrategy class, providing compact prompt generation
for multimodal LLMs with support for three action types: standard UI actions, text input,
and custom coordinate-based actions for advanced interaction scenarios.
"""

from typing import Any, Dict, List, Optional

from rv_llm.llm.constants import (ContextEntry, FragmentType, PromptStrategyType,
                                  StateEntry, ContextMode)
from rv_llm.llm.prompt.information.fragment_manager import InformationManager
from rv_llm.llm.prompt.strategy.base_strategy import PromptStrategy
from rv_llm.llm.prompt.template.jinja_repository import Jinja2TemplateRepository

from rvsmart_tool.constants import (
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
            template_repository: Optional[Jinja2TemplateRepository] = None,
            context_mode: str = ContextMode.STATELESS
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
            context_mode: Context enrichment mode (stateless or rich)
        """
        super().__init__(name, information_manager, template_repository)
        self.context_mode = context_mode

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
            # Use context mode to determine processing strategy
            if self.context_mode == ContextMode.RICH:
                return self._generate_rich_context_prompt(state, context)
            else:
                return self._generate_stateless_prompt(state, context)
                
        except Exception as e:
            self.logger.error(f"Error generating multimodal prompt: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": f"PromptStrategy:{self.name}",
                    "state_id": state.get("id", "unknown"),
                    "multimodal": True,
                    "context_mode": self.context_mode
                }
            )
            # Return fallback messages
            return self._create_fallback_messages()

    def _generate_stateless_prompt(
            self,
            state: Dict[str, Any],
            context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """
        Generate stateless prompt with complete context inline.
        
        Args:
            state: Current application state
            context: Additional context information
            
        Returns:
            List of message dictionaries for template processing
        """
        try:
            # Use vision template with compact format
            template_name = self.get_template_name(context) or self.DEFAULT_TEMPLATE
            self.logger.info(f"Using vision template: {template_name}")
            print(f">>>>>>>>>>>>>>>>> Using vision template: {template_name}")

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
            self.logger.error(f"Error generating stateless prompt: {e}", exc_info=True)
            return self._create_fallback_messages()

    def _generate_rich_context_prompt(
            self,
            state: Dict[str, Any],
            context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """
        Generate rich context prompt with sliding window and compression.
        
        ### Rich Context Strategy:
        Implements sliding window approach with configurable context compression
        to maintain relevant historical information while respecting token limits.
        
        Args:
            state: Current application state
            context: Additional context information
            
        Returns:
            List of message dictionaries for template processing
        """
        try:
            # Process rich context with sliding window
            rich_state = self._process_rich_context(state, context)
            
            # Use stateless generation with enriched context
            return self._generate_stateless_prompt(rich_state, context)
            
        except Exception as e:
            self.logger.error(f"Error generating rich context prompt: {e}", exc_info=True)
            # Fallback to stateless mode
            self.logger.info("Falling back to stateless context mode")
            return self._generate_stateless_prompt(state, context)

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

        # Ensure context completeness - include all variables available to Single/Batch strategies
        # Extract and include memory-managed context variables from state
        if StateEntry.ACTION_HISTORY in state:
            variables["action_history"] = state[StateEntry.ACTION_HISTORY]
        
        if StateEntry.MEMORY_INSIGHTS in state:
            variables["memory_insights"] = state[StateEntry.MEMORY_INSIGHTS]
            
        if StateEntry.NAVIGATION_PATH in state:
            variables["navigation_path"] = state[StateEntry.NAVIGATION_PATH]
            
        if StateEntry.ACTIVITY_VISITS in state:
            variables["activity_visits"] = state[StateEntry.ACTIVITY_VISITS]
        
        # Core context information for template compatibility
        variables.update({
            "activity": state.get("activity", "unknown"),
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

    def _process_rich_context(
            self,
            state: Dict[str, Any],
            context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process rich context with sliding window and compression.
        
        ### Sliding Window Strategy:
        Maintains a configurable window of recent iterations, compressing older
        entries while preserving key insights, coverage progression, and MOP violations.
        
        ### Context Content per Iteration:
        - Screen description (UI elements and actions available)
        - Generated actions from that iteration
        - Coverage metrics at that point
        - MOP violations detected
        - Activity transitions
        
        Args:
            state: Current application state
            context: Additional context information
            
        Returns:
            Enhanced state with rich context data
        """
        rich_state = state.copy()
        
        # Get recent iterations from state (populated by memory system)
        recent_iterations = state.get(StateEntry.RECENT_ITERATIONS, [])
        
        if not recent_iterations:
            self.logger.debug("No recent iterations available for rich context")
            return rich_state
            
        # Default window size (configurable via context)
        window_size = context.get(ContextEntry.CONTEXT_WINDOW_SIZE, 5) if context else 5
        compression_enabled = context.get(ContextEntry.CONTEXT_COMPRESSION, True) if context else True
        
        # Apply sliding window
        windowed_iterations = recent_iterations[-window_size:] if len(recent_iterations) > window_size else recent_iterations
        
        # Process iterations into structured context
        context_summary = self._build_context_summary(windowed_iterations, compression_enabled)
        
        # Enhance state with rich context
        if context_summary:
            # Override action_history with rich version
            rich_state[StateEntry.ACTION_HISTORY] = context_summary["action_sequence"]
            
            # Add coverage timeline if enabled
            if context and context.get(ContextEntry.INCLUDE_COVERAGE_TIMELINE, False):
                rich_state["coverage_timeline"] = context_summary.get("coverage_progression", [])
            
            # Enhance memory insights with iteration patterns
            existing_insights = rich_state.get(StateEntry.MEMORY_INSIGHTS, "")
            rich_insights = context_summary.get("pattern_insights", "")
            if rich_insights:
                combined_insights = f"{existing_insights}\nRecent Patterns: {rich_insights}" if existing_insights else f"Recent Patterns: {rich_insights}"
                rich_state[StateEntry.MEMORY_INSIGHTS] = combined_insights
                
        self.logger.debug(f"Rich context processed: {len(windowed_iterations)} iterations, compression: {compression_enabled}")
        return rich_state
        
    def _build_context_summary(
            self,
            iterations: List[Dict[str, Any]],
            compression_enabled: bool
    ) -> Dict[str, Any]:
        """
        Build context summary from recent iterations.
        
        ### Summary Strategy:
        Extracts key information from each iteration and builds comprehensive
        context summary with optional compression for older entries.
        
        Args:
            iterations: List of recent iteration data
            compression_enabled: Whether to compress older entries
            
        Returns:
            Context summary with structured information
        """
        if not iterations:
            return {}
            
        action_sequence = []
        coverage_progression = []
        mop_violations = []
        activity_transitions = []
        
        for i, iteration in enumerate(iterations):
            # Extract iteration information
            iteration_num = i + 1
            screen_desc = iteration.get("screen_description", "")
            actions_taken = iteration.get("actions_generated", [])
            coverage_data = iteration.get("coverage_metrics", {})
            mop_errors = iteration.get("mop_errors", [])
            activity = iteration.get("activity", "")
            
            # Build action sequence entry
            if actions_taken:
                if compression_enabled and i < len(iterations) - 3:  # Compress all but last 3
                    action_summary = f"Iteration {iteration_num}: {len(actions_taken)} actions in {activity}"
                else:
                    action_details = [f"{act.get('explanation', 'action')}".split('.')[0] for act in actions_taken[:3]]
                    action_summary = f"Iteration {iteration_num}: {', '.join(action_details)}"
                action_sequence.append(action_summary)
            
            # Track coverage progression
            if coverage_data:
                coverage_progression.append({
                    "iteration": iteration_num,
                    "method_coverage": coverage_data.get("method_coverage", 0),
                    "mop_coverage": coverage_data.get("mop_method_coverage", 0),
                    "violations": coverage_data.get("unique_errors", 0)
                })
            
            # Track MOP violations
            if mop_errors:
                for error in mop_errors:
                    mop_violations.append(f"Iteration {iteration_num}: {error.get('spec', 'unknown')} in {error.get('method', 'unknown')}")
            
            # Track activity transitions
            if activity:
                activity_transitions.append(activity)
        
        # Generate pattern insights
        pattern_insights = self._analyze_iteration_patterns(iterations)
        
        return {
            "action_sequence": "\n".join(action_sequence) if action_sequence else "No recent actions",
            "coverage_progression": coverage_progression,
            "mop_violations": mop_violations,
            "activity_flow": " → ".join(list(dict.fromkeys(activity_transitions))),  # Deduplicated transitions
            "pattern_insights": pattern_insights
        }
    
    def _analyze_iteration_patterns(self, iterations: List[Dict[str, Any]]) -> str:
        """
        Analyze patterns across iterations for insights.
        
        Args:
            iterations: List of iteration data
            
        Returns:
            Pattern analysis insights
        """
        if not iterations or len(iterations) < 2:
            return ""
            
        insights = []
        
        # Analyze activity repetition
        activities = [it.get("activity", "") for it in iterations if it.get("activity")]
        if activities:
            most_common = max(set(activities), key=activities.count)
            if activities.count(most_common) > len(iterations) * 0.6:
                insights.append(f"Focus on {most_common}")
        
        # Analyze action patterns
        total_actions = sum(len(it.get("actions_generated", [])) for it in iterations)
        if total_actions > 0:
            avg_actions = total_actions / len(iterations)
            if avg_actions < 2:
                insights.append("Low action generation rate")
            elif avg_actions > 4:
                insights.append("High action generation rate")
        
        # Analyze MOP violation trends
        violation_counts = [len(it.get("mop_errors", [])) for it in iterations]
        if any(violation_counts):
            recent_violations = sum(violation_counts[-2:]) if len(violation_counts) >= 2 else sum(violation_counts)
            if recent_violations > 0:
                insights.append(f"Recent MOP violations: {recent_violations}")
        
        return "; ".join(insights) if insights else "Standard interaction pattern"