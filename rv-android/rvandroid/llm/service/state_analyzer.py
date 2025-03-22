# rvandroid/llm/service/state_analyzer.py
from typing import Dict, List, Any, Optional

from rvandroid.experiment.event_system import EventBus
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.util.logging_manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor


class StateAnalyzer:
    """
    Analyzes and enhances application state for more effective testing.

    ### Architectural Decisions:
    - Focuses on state analysis and enrichment as a distinct responsibility
    - Provides specialized methods for state introspection
    - Enhances state with historical context and action metadata
    - Implements performance monitoring for state operations

    ### Role in the System:
    - Analyzes application state to extract key testing insights
    - Enhances state with action history and contextual information
    - Provides available actions and UI elements for decision making
    - Facilitates more effective action selection through state enrichment
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the state analyzer.

        Args:
            static_data: Static analysis data for state enrichment
        """
        # Get system services
        self.event_bus = EventBus.get_instance()
        self.performance_monitor = PerformanceMonitor.get_instance()
        logging_manager = LoggingManager.get_instance()

        # Configure logging
        self.logger = logging_manager.get_logger(
            "llm.service.state_analyzer",
            {LoggingManager.CONTEXT_COMPONENT: "StateAnalyzer"}
        )

        # Store configuration
        self.static_data = static_data

        self.logger.info("State analyzer initialized")

    def analyze_and_enhance_state(self, state: Dict[str, Any]) -> None:
        """
        Analyze and enhance the application state with additional context.

        Args:
            state: Application state to analyze and enhance
        """
        context = {"activity": state.get("activity", "unknown")}

        with self.performance_monitor.measure_time("enhance_state", context):
            # Enhance action history if present
            if "action_history" in state:
                with self.performance_monitor.measure_time("enhance_action_history", context):
                    self._enhance_action_history(state)

            # Add action-specific history
            with self.performance_monitor.measure_time("add_action_specific_history", context):
                self._add_action_specific_history(state)

            # Add static analysis insights if available
            if self.static_data and "activity" in state:
                with self.performance_monitor.measure_time("add_static_insights", context):
                    self._add_static_analysis_insights(state)

    def get_available_action_ids(self, state: Dict[str, Any]) -> List[str]:
        """
        Get the list of available action IDs from the current state.

        Args:
            state: Current application state

        Returns:
            List of available action IDs
        """
        action_ids = []

        # We need to parse the screen to get action IDs
        # This requires access to a parser, which we'll get from the component configurator
        # For now, we'll use a placeholder implementation

        # If screen_description is in the state, extract action IDs
        if "available_actions" in state:
            return state["available_actions"]

        # Otherwise, try to extract from view_tree if present
        if "view_tree" in state:
            try:
                # Extract clickable elements as potential actions
                self._extract_clickable_elements(state["view_tree"], action_ids)
            except Exception as e:
                self.logger.warning(f"Error extracting action IDs from view tree: {e}")

        return action_ids

    def _extract_clickable_elements(self, view: Dict[str, Any], action_ids: List[str], max_elements: int = 50):
        """
        Extract clickable elements from view tree as potential actions.

        Args:
            view: View tree dictionary
            action_ids: List to append action IDs to
            max_elements: Maximum number of elements to extract
        """
        # Check if this view is clickable
        if (len(action_ids) < max_elements and
                view.get('clickable', False) and
                view.get('enabled', True) and
                view.get('visible', True)):

            # Add resource ID as action ID if available
            resource_id = view.get('resource_id', '')
            if resource_id:
                action_ids.append(resource_id)

            # Use bounds as action ID if no resource ID
            elif 'bounds' in view:
                bounds = view['bounds']
                x = (bounds[0][0] + bounds[1][0]) // 2
                y = (bounds[0][1] + bounds[1][1]) // 2
                action_ids.append(f"{x}_{y}")

        # Recursively process children
        for child in view.get('children', []):
            if len(action_ids) >= max_elements:
                break
            self._extract_clickable_elements(child, action_ids, max_elements)

    def _enhance_action_history(self, state: Dict[str, Any]) -> None:
        """
        Enhance action history with better formatting and context.

        Args:
            state: State dictionary to enhance
        """
        if "action_history" not in state:
            return

        self.logger.debug("Processing action history for enhanced format")
        enhanced_history = []

        for action in state.get("action_history", []):
            # Skip if already in enhanced format
            if isinstance(action, str) and action.startswith("[Action ID:"):
                enhanced_history.append(action)
                continue

            # Convert dictionary actions to enhanced format
            if isinstance(action, dict):
                action_id = action.get("action_id", "unknown")
                action_type = action.get("action_type", "unknown")
                target = action.get("target", "unknown")
                params = action.get("params", {})
                explanation = action.get("explanation", "")

                # Format parameters
                params_str = ""
                if params:
                    if "text" in params:
                        params_str = f" with text '{params['text']}'"
                    elif "direction" in params:
                        params_str = f" {params['direction']}"

                # Create context-sensitive description
                if action_type == "click":
                    if "spinner" in target.lower() or "dropdown" in target.lower():
                        description = f"CLICKED ON DROPDOWN '{target}'{params_str}"
                    elif any(keyword in target.lower() for keyword in
                             ["submit", "login", "save", "apply", "ok", "next"]):
                        description = f"SUBMITTED FORM by clicking '{target}'{params_str}"
                    else:
                        description = f"CLICKED on '{target}'{params_str}"
                elif action_type == "set_text":
                    description = f"FILLED text field '{target}'{params_str}"
                elif action_type in ["scroll_up", "scroll_down"]:
                    description = f"SCROLLED {action_type.split('_')[1]} on '{target}'{params_str}"
                else:
                    description = f"{action_type.upper()} on '{target}'{params_str}"

                enhanced_action = f"[Action ID: {action_id}] {description} - {explanation}"
                enhanced_history.append(enhanced_action)
            else:
                # Keep string actions as is
                enhanced_history.append(action)

        # Update the state
        state["action_history"] = enhanced_history
        self.logger.debug(f"Enhanced action history now has {len(enhanced_history)} entries")

    def _add_action_specific_history(self, state: Dict[str, Any]) -> None:
        """
        Add action-specific history information to the state.
        This helps the LLM understand the history of each possible action.

        Args:
            state: State dictionary to augment with action history
        """
        # Get action history
        action_history = state.get("action_history", [])

        # Get current activity
        activity = state.get("activity", "unknown")

        # Create action-specific history
        action_specific_history = {}

        # Get available action IDs
        action_ids = self.get_available_action_ids(state)

        for action_id in action_ids:
            # Filter history entries that reference this action ID
            specific_history = [
                entry for entry in action_history
                if isinstance(entry, str) and f"[Action ID: {action_id}]" in entry
            ]

            # Store in the dictionary
            action_specific_history[action_id] = specific_history

        # Add to state
        state["action_specific_history"] = action_specific_history

    def _add_static_analysis_insights(self, state: Dict[str, Any]) -> None:
        """
        Add insights from static analysis to the state.

        Args:
            state: State dictionary to enhance with static analysis
        """
        if not self.static_data:
            return

        activity = state.get("activity", "unknown")

        # Create insights container
        if "static_insights" not in state:
            state["static_insights"] = {}

        insights = {}

        # Get activity class data if available
        activity_class = self.static_data.classes.get_clazz(activity)
        if activity_class:
            # Count methods with different properties
            reachable_methods = [m for m in activity_class.methods if m.reachable]
            critical_methods = [m for m in activity_class.methods if m.reaches_mop]
            direct_critical_methods = [m for m in activity_class.methods if m.directly_reaches_mop]

            # Add method statistics
            insights["reachable_methods_count"] = len(reachable_methods)
            insights["critical_methods_count"] = len(critical_methods)
            insights["direct_critical_methods_count"] = len(direct_critical_methods)

            # Add method examples for reference
            if critical_methods:
                insights["critical_methods_examples"] = [m.name for m in critical_methods[:5]]

        # Add window transition information
        if self.static_data.wtg:
            edges = [edge for edge in self.static_data.wtg.graph.edges()
                     if edge[0].name == activity_class.name]

            if edges:
                insights["possible_transitions_count"] = len(edges)
                insights["possible_transitions"] = [edge[1].name for edge in edges[:5]]

        # Store insights in state
        state["static_insights"] = insights
       