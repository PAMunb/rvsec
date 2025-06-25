"""Testing history information fragment for the prompt system.

This module defines a specialized fragment for extracting and formatting testing
history information from memory management systems to provide contextual guidance
for LLM-driven action generation.

### Architectural Overview:
The HistoryFragment serves as the interface between memory management systems
and prompt generation, converting historical action data and insights into
structured text representations that inform future decision making.

### Core Responsibilities:
- **Memory Integration**: Processes data from short-term and long-term memory systems
- **History Formatting**: Converts action sequences into human-readable summaries
- **Context Prioritization**: Emphasizes recent actions while maintaining long-term insights
- **Insight Delivery**: Provides memory-derived guidance for exploration and optimization

### Integration Architecture:
- Consumes memory data from MemoryManager and related systems
- Integrates with rv-android-core error handling and logging infrastructure
- Supports both formatted string data and raw action list processing
- Maintains compatibility with different memory storage backends

### Design Patterns:
- **Adapter Pattern**: Converts memory system data to prompt-compatible format
- **Template Method**: Consistent processing pipeline with specialized formatting
- **Error Isolation**: Comprehensive error handling to prevent prompt generation failures
- **Memory Abstraction**: Flexible handling of different memory data structures
"""

from typing import Any, Dict, Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.exceptions import RVParsingError

from rv_llm.llm.constants import FragmentType, StateEntry
from rv_llm.llm.prompt.information.base_fragment import InformationFragment


class HistoryFragment(InformationFragment):
    """Fragment for extracting and formatting testing history information.

    ### Architectural Role:
    This fragment serves as the bridge between memory management systems and
    prompt generation, ensuring reliable conversion of historical data into
    actionable context for LLM decision making.

    ### Processing Strategy:
    - Prioritizes pre-formatted memory summaries for efficiency
    - Implements fallback processing for raw action data structures
    - Maintains configurable history limits to prevent context bloat
    - Provides comprehensive error handling for malformed memory data

    ### Integration Points:
    - Consumes memory data from MemoryManager state enrichment
    - Integrates with rv-android-core error handling and logging systems
    - Supports various action data formats from different testing frameworks
    - Delivers formatted history for template-based prompt generation
    """

    def __init__(self, name: str = FragmentType.HISTORY, priority: int = 100):
        """Initialize the testing history fragment with comprehensive infrastructure.

        Sets up the complete fragment processing pipeline including error handling,
        logging, and memory processing systems for robust history data management.

        Args:
            name: The name of the fragment (default: FragmentType.HISTORY).
            priority: The priority of the fragment (default: 100).
        """
        super().__init__(name, priority)
        
        # Initialize logging infrastructure
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.prompt.history_fragment",
            {CONTEXT_COMPONENT: "HistoryFragment"}
        )
        
        # Initialize error handling
        self.error_handler = ErrorHandler.get_instance()
        
        # Configuration for history processing
        self.max_history_entries = 5  # Limit history to last N entries
        
        self.logger.debug("Initialized HistoryFragment for memory data processing")

    @ErrorHandler.handle_errors(component="HistoryFragment", phase="generation", reraise=True)
    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """Generate testing history information from memory management state.

        Processes historical action data and memory insights to generate formatted
        text representations for LLM prompt integration. Implements comprehensive
        validation and error handling for reliable history processing.

        Args:
            state: The current application state containing memory data
            context: Additional context information for processing customization

        Returns:
            A formatted string containing testing history information
            
        Raises:
            RVParsingError: If state validation fails or contains invalid data
        """
        if not state:
            raise RVParsingError(
                "State dictionary is empty or None",
                parser_type="HistoryFragment"
            )

        history_parts = []

        # Process action history from memory management
        if StateEntry.ACTION_HISTORY in state:
            action_history = state[StateEntry.ACTION_HISTORY]
            
            if isinstance(action_history, str) and action_history.strip():
                # Pre-formatted history from MemoryManager
                self.logger.debug("Using pre-formatted action history from MemoryManager")
                history_parts.append(action_history)
            elif isinstance(action_history, (list, tuple)):
                # Raw action data requiring formatting
                self.logger.debug(f"Formatting {len(action_history)} raw action entries")
                formatted_history = self._format_action_history(action_history)
                if formatted_history:
                    history_parts.append(formatted_history)
            else:
                self.logger.warning(f"Invalid action history format: {type(action_history)}")

        # Process memory insights if available
        if StateEntry.MEMORY_INSIGHTS in state:
            memory_insights = state[StateEntry.MEMORY_INSIGHTS]
            
            if isinstance(memory_insights, str) and memory_insights.strip():
                self.logger.debug("Including memory insights in history")
                history_parts.append(f"\nMemory Insights:\n{memory_insights}")
            elif memory_insights:
                self.logger.debug("Including structured memory insights")
                history_parts.append(f"\nMemory Insights:\n{str(memory_insights)}")

        # Generate final history output
        if history_parts:
            final_history = "\n\n".join(history_parts)
            self.logger.debug(f"Generated history with {len(history_parts)} sections")
            return final_history
        else:
            self.logger.debug("No valid testing history found in state")
            return "No previous testing history available."

    @ErrorHandler.handle_errors(component="HistoryFragment", phase="action_formatting")
    def _format_action_history(self, actions) -> str:
        """Format action history data for prompt display.

        Processes raw action data structures to generate human-readable history
        summaries with configurable entry limits to prevent context bloat.

        Args:
            actions: List of historical actions with results (list of dicts or objects)

        Returns:
            Formatted action history string or empty string if no valid data
        """
        if not actions:
            return "No previous testing actions recorded."

        # Handle string input (should not occur but defensive)
        if isinstance(actions, str):
            self.logger.warning("String action data passed to formatting method")
            return actions

        # Ensure we have a list or tuple
        if not isinstance(actions, (list, tuple)):
            self.logger.error(f"Invalid action data type: {type(actions)}")
            return "Error: Invalid action history format."

        # Limit to the last N entries to prevent context bloat
        limited_actions = (
            actions[-self.max_history_entries:] 
            if len(actions) > self.max_history_entries 
            else actions
        )

        if not limited_actions:
            return "No recent testing actions available."

        formatted_parts = [f"Recent testing history ({len(limited_actions)} actions):"]

        # Process each action with comprehensive format handling
        for i, action in enumerate(limited_actions):
            try:
                if isinstance(action, str):
                    # Pre-formatted string action
                    formatted_parts.append(f"  {i + 1}. {action}")
                    
                elif hasattr(action, 'text') and hasattr(action, 'action_type'):
                    # Structured action object (GeneratedAction, Iteration, etc.)
                    action_type = getattr(action, 'action_type', 'unknown')
                    text = getattr(action, 'text', '')
                    formatted_parts.append(f"  {i + 1}. {action_type} - {text}")
                    
                elif isinstance(action, dict):
                    # Dictionary format with action details
                    action_type = action.get("action_type", "unknown")
                    text = action.get("text", "")
                    success = action.get("success", None)
                    
                    result_text = ""
                    if success is not None:
                        result_text = " (succeeded)" if success else " (failed)"
                    
                    formatted_parts.append(f"  {i + 1}. {action_type} - {text}{result_text}")
                    
                else:
                    # Unknown format, attempt string representation
                    action_str = str(action)[:100]  # Limit length
                    formatted_parts.append(f"  {i + 1}. {action_str}")
                    
            except Exception as e:
                self.logger.warning(f"Error formatting action {i}: {e}")
                formatted_parts.append(f"  {i + 1}. [Error formatting action]")

        return "\n".join(formatted_parts)

    @ErrorHandler.handle_errors(component="HistoryFragment", phase="inclusion_check")
    def should_include(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if testing history information should be included in prompt generation.

        Validates state content to ensure meaningful history data is available and
        suitable for prompt inclusion. Implements comprehensive validation to prevent
        empty or invalid history data from being included in prompts.

        Args:
            state: The current application state to validate
            context: Additional context information for inclusion decisions

        Returns:
            True if valid testing history information is available, False otherwise
        """
        if not state:
            self.logger.debug("History not included: empty state")
            return False

        # Check for action history in state
        if StateEntry.ACTION_HISTORY in state:
            action_history = state[StateEntry.ACTION_HISTORY]
            
            if isinstance(action_history, str) and action_history.strip():
                self.logger.debug("Including pre-formatted action history")
                return True
            elif isinstance(action_history, (list, tuple)) and len(action_history) > 0:
                self.logger.debug(f"Including {len(action_history)} raw action entries")
                return True
            else:
                self.logger.debug("Action history exists but is empty or invalid")

        # Check for memory insights in state
        if StateEntry.MEMORY_INSIGHTS in state:
            memory_insights = state[StateEntry.MEMORY_INSIGHTS]
            
            if isinstance(memory_insights, str) and memory_insights.strip():
                self.logger.debug("Including memory insights")
                return True
            elif memory_insights:
                self.logger.debug("Including structured memory insights")
                return True

        # Check for testing history in context (fallback)
        if context and "testing_history" in context:
            context_history = context["testing_history"]
            if context_history:
                self.logger.debug("Including testing history from context")
                return True

        # No valid history information found
        self.logger.debug("No valid testing history found for inclusion")
        return False
