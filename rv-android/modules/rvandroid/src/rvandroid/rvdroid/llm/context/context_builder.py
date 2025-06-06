# rvandroid/rvdroid/llm/context/context_builder.py
"""
Context builder for RVDroid LLM integration.

This module provides functionality to prepare context for LLM queries,
including selection, summarization, and formatting of relevant information.
"""

from typing import Dict, Any, List, Optional

from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class ContextBuilder:
    """
    Prepares context for LLM queries from application state and data.

    ### Architectural Decisions:
    - Separates context preparation from LLM interaction logic
    - Uses modular approach for different types of context
    - Implements compression techniques for token efficiency
    - Structures information for optimal model comprehension

    ### Role in the System:
    - Selects relevant information for LLM consultation
    - Summarizes data for token efficiency
    - Formats information for model comprehension
    - Implements context compression techniques
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the context builder.

        Args:
            static_data: Optional static analysis data
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.llm.context.builder",
            {CONTEXT_COMPONENT: "ContextBuilder"}
        )

        # Store static data
        self.static_data = static_data

        # Maximum context sizes
        self.max_elements = 15  # Maximum UI elements to include
        self.max_history_items = 5  # Maximum history items to include
        self.max_actions = 8  # Maximum actions per element

        self.logger.info("Initialized context builder")

    def build_context(self, state_data: Dict[str, Any],
                      exploration_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build context for general LLM queries.

        Args:
            state_data: Current application state data
            exploration_context: Exploration context information

        Returns:
            Dictionary with formatted context
        """
        # Extract key information
        activity = state_data.get("activity", "unknown")
        elements = state_data.get("elements", [])

        # Limit number of elements
        if len(elements) > self.max_elements:
            elements = elements[:self.max_elements]

        # Get exploration phase and metrics
        exploration_phase = exploration_context.get("exploration_phase", "unknown")
        metrics = exploration_context.get("metrics", {})

        # Format metrics for readability
        formatted_metrics = self._format_metrics(metrics)

        # Build current screen description
        current_screen = self._build_screen_description(activity, elements)

        # Build history summary
        history = exploration_context.get("history", [])
        history_summary = self._summarize_history(history)

        # Combine context
        context = {
            "current_screen": current_screen,
            "elements_count": len(elements),
            "exploration_phase": exploration_phase,
            "progress": formatted_metrics,
            "history_summary": history_summary,
            "progress_metrics": self._format_progress_metrics(metrics)
        }

        # Add static analysis insights if available
        if self.static_data:
            static_insights = self._get_static_insights(activity)
            if static_insights:
                context["static_insights"] = static_insights

        return context

    def build_action_context(self, action_data: Dict[str, Any],
                             result: Dict[str, Any],
                             state_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build context for action feedback queries.

        Args:
            action_data: Data about the executed action
            result: Result of the action execution
            state_data: Current application state data

        Returns:
            Dictionary with formatted context
        """
        # Extract action information
        action_id = action_data.get("id", "unknown")
        action_type = action_data.get("type", "unknown")
        action_target = action_data.get("target", "unknown")

        # Create action description
        action_description = f"{action_type} on {action_target} (ID: {action_id})"

        # Format result
        success = result.get("success", False)
        new_state = result.get("new_state", False)

        result_description = f"{'Success' if success else 'Failed'}"
        if success:
            result_description += f", {'new state' if new_state else 'same state'}"

        # Get current screen description
        activity = state_data.get("activity", "unknown")
        elements = state_data.get("elements", [])
        current_screen = self._build_screen_description(activity, elements)

        return {
            "action_description": action_description,
            "action_result": result_description,
            "current_screen": current_screen,
            "success": success,
            "new_state": new_state
        }

    def build_strategy_context(self, state_data: Dict[str, Any],
                               exploration_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build context for strategy recommendation queries.

        Args:
            state_data: Current application state data
            exploration_history: History of exploration states and actions

        Returns:
            Dictionary with formatted context
        """
        # Extract current state information
        activity = state_data.get("activity", "unknown")
        elements = state_data.get("elements", [])
        current_screen = self._build_screen_description(activity, elements)

        # Determine exploration phase
        # This could be derived from history and progress metrics
        exploration_phase = self._determine_exploration_phase(exploration_history)

        # Calculate progress metrics
        progress_metrics = self._calculate_progress_metrics(exploration_history)

        # Summarize recent actions
        recent_actions = self._summarize_recent_actions(exploration_history)

        return {
            "current_screen": current_screen,
            "exploration_phase": exploration_phase,
            "progress_metrics": progress_metrics,
            "recent_actions": recent_actions,
            "elements_count": len(elements)
        }

    def build_monitored_operations_context(self, state_data: Dict[str, Any],
                                     monitored_operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build context for monitored operations interpretation queries.

        Args:
            state_data: Current application state data
            monitored_operations: List of operations being monitored in the current state

        Returns:
            Dictionary with formatted context
        """
        # Extract current state information
        activity = state_data.get("activity", "unknown")
        elements = state_data.get("elements", [])
        current_screen = self._build_screen_description(activity, elements)

        # Format monitored operations
        formatted_operations = []
        for operation in monitored_operations:
            op_id = operation.get("id", "unknown")
            op_type = operation.get("type", "unknown")
            op_desc = operation.get("description", "")
            op_priority = "high" if operation.get("directly_reaches_mop", False) else "medium"

            formatted_operations.append(f"{op_type} (ID: {op_id}, Priority: {op_priority}): {op_desc}")

        # Limit the number of operations
        if len(formatted_operations) > self.max_actions:
            formatted_operations = formatted_operations[:self.max_actions]

        # Join operations into a string
        operations_str = "\n".join(formatted_operations) if formatted_operations else "No monitored operations available"

        # Get static insights about monitored operations from static analysis if available
        monitored_ops_insights = self._get_monitored_operations_insights(activity)

        return {
            "current_screen": current_screen,
            "monitored_operations": operations_str,
            "monitored_ops_insights": monitored_ops_insights,
            "elements_count": len(elements)
        }

    def _build_screen_description(self, activity: str, elements: List[Dict[str, Any]]) -> str:
        """
        Build a text description of the current screen.

        Args:
            activity: Current activity name
            elements: List of UI elements

        Returns:
            String description of the screen
        """
        # Build basic screen description
        description = f"Activity: {activity}\n"

        # Add elements description
        if elements:
            description += "UI Elements:\n"

            for i, element in enumerate(elements):
                if i >= self.max_elements:
                    description += f"...and {len(elements) - self.max_elements} more elements\n"
                    break

                element_type = element.get("type", "unknown")
                element_id = element.get("id", "unknown")
                element_text = element.get("text", "")

                element_desc = f"{i + 1}. {element_type}"
                if element_id != "unknown":
                    element_desc += f" (ID: {element_id})"
                if element_text:
                    element_desc += f": \"{element_text}\""

                # Add available actions
                actions = element.get("actions", [])
                if actions:
                    element_desc += f" - Actions: {', '.join([a.get('type', 'unknown') for a in actions[:3]])}"
                    if len(actions) > 3:
                        element_desc += f" and {len(actions) - 3} more"

                description += element_desc + "\n"
        else:
            description += "No UI elements available\n"

        return description

    def _summarize_history(self, history: List[Dict[str, Any]]) -> str:
        """
        Summarize exploration history.

        Args:
            history: List of history items

        Returns:
            Summarized history string
        """
        if not history:
            return "No exploration history available"

        # Limit history items
        if len(history) > self.max_history_items:
            recent_history = history[-self.max_history_items:]
        else:
            recent_history = history

        # Format history items
        summary_items = []

        for item in recent_history:
            action = item.get("action", {})
            result = item.get("result", {})

            action_type = action.get("type", "unknown")
            action_target = action.get("target", "unknown")
            success = result.get("success", False)
            new_state = result.get("new_state", False)

            item_summary = f"{action_type} on {action_target}: "
            item_summary += f"{'Success' if success else 'Failed'}"
            if success:
                item_summary += f", {'new state' if new_state else 'same state'}"

            summary_items.append(item_summary)

        return "Recent actions:\n" + "\n".join(summary_items)

    def _format_metrics(self, metrics: Dict[str, Any]) -> str:
        """
        Format metrics for readability.

        Args:
            metrics: Metrics dictionary

        Returns:
            Formatted metrics string
        """
        if not metrics:
            return "No metrics available"

        formatted_items = []

        # Format key metrics
        if "states_explored" in metrics:
            formatted_items.append(f"States explored: {metrics['states_explored']}")

        if "actions_executed" in metrics:
            formatted_items.append(f"Actions executed: {metrics['actions_executed']}")

        if "activity_coverage" in metrics:
            formatted_items.append(f"Activity coverage: {metrics['activity_coverage']:.1f}%")

        if "elements_interacted" in metrics:
            formatted_items.append(f"Elements interacted with: {metrics['elements_interacted']}")

        if "unique_transitions" in metrics:
            formatted_items.append(f"Unique transitions: {metrics['unique_transitions']}")

        if not formatted_items:
            # Use raw metrics if no key metrics found
            formatted_items = [f"{k}: {v}" for k, v in metrics.items()]

        return ", ".join(formatted_items)

    def _format_progress_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format progress metrics for structured representation.

        Args:
            metrics: Metrics dictionary

        Returns:
            Dictionary with formatted metrics
        """
        formatted = {}

        # Copy numerical metrics
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                formatted[key] = value

        # Format percentages
        for key in list(formatted.keys()):
            if "coverage" in key.lower() and isinstance(formatted[key], float):
                formatted[key] = f"{formatted[key]:.1f}%"

        return formatted

    def _determine_exploration_phase(self, history: List[Dict[str, Any]]) -> str:
        """
        Determine the current exploration phase from history.

        Args:
            history: Exploration history

        Returns:
            Exploration phase string
        """
        if not history:
            return "initial_exploration"

        # Calculate metrics to determine phase
        states_seen = set()
        activities_seen = set()
        recent_new_states = 0

        # Analyze recent history (last 10 items or less)
        recent_history = history[-min(10, len(history)):]

        for item in history:
            state = item.get("state", {})
            result = item.get("result", {})

            # Track states and activities
            state_fingerprint = state.get("fingerprint", "unknown")
            activity = state.get("activity", "unknown")

            states_seen.add(state_fingerprint)
            activities_seen.add(activity)

            # Count recent new states
            if item in recent_history and result.get("new_state", False):
                recent_new_states += 1

        # Determine phase based on metrics
        if len(history) < 10:
            return "initial_exploration"
        elif recent_new_states >= 3:
            return "active_exploration"
        elif len(activities_seen) < 3:
            return "focused_exploration"
        elif len(recent_history) > 8 and recent_new_states == 0:
            return "exploration_plateau"
        else:
            return "systematic_exploration"

    def _calculate_progress_metrics(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate progress metrics from exploration history.

        Args:
            history: Exploration history

        Returns:
            Dictionary with progress metrics
        """
        metrics = {
            "total_actions": len(history),
            "states_explored": 0,
            "activities_explored": 0,
            "success_rate": 0,
            "new_state_rate": 0
        }

        if not history:
            return metrics

        # Calculate metrics
        states_seen = set()
        activities_seen = set()
        successful_actions = 0
        new_states = 0

        for item in history:
            state = item.get("state", {})
            result = item.get("result", {})

            # Track states and activities
            state_fingerprint = state.get("fingerprint", "unknown")
            activity = state.get("activity", "unknown")

            if state_fingerprint != "unknown":
                states_seen.add(state_fingerprint)

            if activity != "unknown":
                activities_seen.add(activity)

            # Track success and new states
            if result.get("success", False):
                successful_actions += 1

            if result.get("new_state", False):
                new_states += 1

        # Update metrics
        metrics["states_explored"] = len(states_seen)
        metrics["activities_explored"] = len(activities_seen)
        metrics["success_rate"] = (successful_actions / len(history)) * 100 if history else 0
        metrics["new_state_rate"] = (new_states / len(history)) * 100 if history else 0

        return metrics

    def _summarize_recent_actions(self, history: List[Dict[str, Any]]) -> str:
        """
        Summarize recent actions from history.

        Args:
            history: Exploration history

        Returns:
            Summarized recent actions string
        """
        if not history:
            return "No recent actions"

        # Get recent actions
        recent_history = history[-min(5, len(history)):]

        # Format action summaries
        action_summaries = []

        for item in recent_history:
            action = item.get("action", {})
            result = item.get("result", {})

            action_type = action.get("type", "unknown")
            action_target = action.get("target", "unknown")
            success = result.get("success", False)

            summary = f"{action_type} on {action_target}: {'Success' if success else 'Failed'}"
            action_summaries.append(summary)

        return "Recent actions: " + ", ".join(action_summaries)

    def _get_static_insights(self, activity: str) -> Dict[str, Any]:
        """
        Get insights from static analysis for an activity.

        Args:
            activity: Activity name

        Returns:
            Dictionary with static analysis insights
        """
        if not self.static_data:
            return {}

        insights = {}

        # Try to find activity in static data
        if hasattr(self.static_data, 'classes'):
            # Find the class for this activity
            activity_class = None
            for class_name, class_data in self.static_data.classes.classes.items():
                if class_name.endswith(activity) or activity.endswith(class_name):
                    activity_class = class_data
                    break

            if activity_class:
                # Count methods with different properties
                total_methods = len(activity_class.methods)
                reaches_mop_methods = sum(1 for m in activity_class.methods if m.reaches_mop)
                directly_reaches_mop = sum(1 for m in activity_class.methods if m.directly_reaches_mop)

                insights["total_methods"] = total_methods
                insights["monitored_methods"] = reaches_mop_methods
                insights["direct_monitored_methods"] = directly_reaches_mop
                insights[
                    "monitored_ratio"] = f"{(reaches_mop_methods / total_methods) * 100:.1f}%" if total_methods > 0 else "0%"

        # Get window transition information if available
        if hasattr(self.static_data, 'wtg'):
            # This would extract transition information from the Window Transition Graph
            # Implementation depends on WTG structure
            pass

        return insights

    def _get_monitored_operations_insights(self, activity: str) -> Dict[str, Any]:
        """
        Get insights about monitored operations from static analysis for an activity.

        Args:
            activity: Activity name

        Returns:
            Dictionary with monitored operations insights
        """
        # Start with general insights
        insights = self._get_static_insights(activity)

        # Add monitored operations-specific insights
        if not self.static_data:
            return insights

        # Check if this activity handles monitored operations
        monitored_methods = []

        if hasattr(self.static_data, 'classes'):
            # Find the class for this activity
            activity_class = None
            for class_name, class_data in self.static_data.classes.classes.items():
                if class_name.endswith(activity) or activity.endswith(class_name):
                    activity_class = class_data
                    break

            if activity_class:
                # Look for methods that are monitored or that reach monitored operations
                for method in activity_class.methods:
                    if method.reaches_mop or method.directly_reaches_mop:
                        op_type = "Direct" if method.directly_reaches_mop else "Indirect"
                        monitored_methods.append(f"{op_type}: {method.name}")

        if monitored_methods:
            insights["monitored_methods"] = monitored_methods[:5]  # Limit to 5 operations
            if len(monitored_methods) > 5:
                insights["monitored_methods"].append(f"...and {len(monitored_methods) - 5} more")

        return insights
