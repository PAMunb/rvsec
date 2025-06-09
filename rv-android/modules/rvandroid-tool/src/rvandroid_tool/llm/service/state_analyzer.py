# rvandroid/llm/service/state_analyzer.py
from typing import Dict, List, Any, Optional

from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.performance_monitor import PerformanceMonitor
from rv_android_core.event.bus import EventBus
from rvandroid.llm.constants import StateEntry


# TODO deprecated
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
            {CONTEXT_COMPONENT: "StateAnalyzer"}
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
            if StateEntry.ACTION_HISTORY in state:
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

        # If available_actions is explicitly provided in the state, use that
        if "available_actions" in state:
            return state["available_actions"]

        # Extract action IDs from screen description items (preferred method)
        # This data structure is built by the parser and used to generate the prompt
        if "screen_description" in state and hasattr(state["screen_description"], "items"):
            screen_description = state["screen_description"]
            for item in screen_description.items:
                for action in item.actions:
                    action_ids.append(str(action.id))

            self.logger.debug(f"Extracted {len(action_ids)} action IDs from screen_description")
            if action_ids:  # If we found actions, return them
                return action_ids

        # Otherwise, try to extract from items directly if present
        # This handles when screen_description exists but doesn't have the expected structure
        if "items" in state:
            try:
                items = state["items"]
                for item in items:
                    if "actions" in item:
                        for action in item["actions"]:
                            if "id" in action:
                                action_ids.append(str(action["id"]))

                self.logger.debug(f"Extracted {len(action_ids)} action IDs from items")
                if action_ids:  # If we found actions, return them
                    return action_ids
            except Exception as e:
                self.logger.warning(f"Error extracting action IDs from items: {e}")

        # As a last resort, try to extract from view_tree if present
        if "view_tree" in state:
            try:
                # Extract clickable elements as potential actions
                self._extract_clickable_elements(state["view_tree"], action_ids)
                self.logger.debug(f"Extracted {len(action_ids)} action IDs from view_tree")
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
        try:
            if not self.static_data:
                return

            activity = state.get("activity", "unknown")
            activity = activity.replace("/", "")
            self.logger.debug(f"Processing static insights for activity: {activity}")

            # Create insights container
            if "static_insights" not in state:
                state["static_insights"] = {}

            insights = {}

            # Get activity class data if available
            activity_class = None
            try:
                if hasattr(self.static_data, 'classes') and hasattr(self.static_data.classes, 'get_clazz'):
                    activity_class = self.static_data.classes.get_clazz(activity)
                    self.logger.debug(f"Found activity class: {activity_class}")
            except Exception as e:
                self.logger.warning(f"Error retrieving activity class for {activity}: {e}")

            if activity_class:
                try:
                    # Count methods with different properties
                    reachable_methods = [m for m in activity_class.methods if hasattr(m, 'reachable') and m.reachable]
                    critical_methods = [m for m in activity_class.methods if
                                        hasattr(m, 'reaches_mop') and m.reaches_mop]
                    direct_critical_methods = [m for m in activity_class.methods if
                                               hasattr(m, 'directly_reaches_mop') and m.directly_reaches_mop]

                    # Add method statistics
                    insights["reachable_methods_count"] = len(reachable_methods)
                    insights["critical_methods_count"] = len(critical_methods)
                    insights["direct_critical_methods_count"] = len(direct_critical_methods)

                    # Add method examples for reference
                    if critical_methods:
                        insights["critical_methods_examples"] = [
                            m.name if hasattr(m, 'name') else str(m)
                            for m in critical_methods[:5]
                        ]
                except Exception as e:
                    self.logger.warning(f"Error processing method information: {e}")

            # Add window transition information if available
            try:
                if hasattr(self.static_data, 'wtg') and self.static_data.wtg:
                    # Safely check edge format and access edge source properties
                    edges = []

                    # Check if graph has edges method
                    if not hasattr(self.static_data.wtg, 'graph') or not hasattr(self.static_data.wtg.graph, 'edges'):
                        self.logger.warning("WTG graph doesn't have expected structure")
                    else:
                        # Process edges safely
                        for edge in self.static_data.wtg.graph.edges():
                            # Check if edge elements are objects with name attribute or strings
                            try:
                                if not edge or len(edge) < 2:
                                    continue

                                source = edge[0]
                                # Handle both object with name attribute and string cases
                                source_name = source.name if hasattr(source, 'name') else source

                                if activity_class and hasattr(activity_class, 'name'):
                                    if source_name == activity_class.name:
                                        edges.append(edge)
                                else:
                                    # Match by activity name string comparison if activity_class is unavailable
                                    if isinstance(source_name, str) and activity in source_name:
                                        edges.append(edge)
                            except Exception as e:
                                self.logger.debug(f"Error processing edge: {e}")
                                continue

                        if edges:
                            insights["possible_transitions_count"] = len(edges)

                            # Safely extract target names
                            transitions = []
                            for edge in edges[:5]:
                                try:
                                    target = edge[1]
                                    target_name = target.name if hasattr(target, 'name') else str(target)
                                    transitions.append(target_name)
                                except Exception as e:
                                    self.logger.debug(f"Error extracting target name: {e}")

                            insights["possible_transitions"] = transitions
            except Exception as e:
                self.logger.warning(f"Error processing WTG information: {e}")

            # Store insights in state
            state["static_insights"] = insights

        except Exception as e:
            self.logger.error(f"Error adding static analysis insights: {e}")
            # Make sure we always have a valid static_insights object even if processing fails
            if "static_insights" not in state:
                state["static_insights"] = {}
