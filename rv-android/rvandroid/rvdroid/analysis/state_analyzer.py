"""
State analyzer for RVDroid.

This module provides functionality to analyze application states,
classify screens, extract semantic meaning, and identify testing opportunities.
"""

from typing import Dict, Any, List, Optional, Set, Tuple

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.model import ItemAction, ScreenDescription
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor


class StateAnalyzer:
    """
    Analyzes application states to identify patterns, contexts, and testing opportunities.

    Provides functionality to understand the semantic meaning of UI elements,
    classify screens, and identify high-value testing targets.
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the state analyzer.

        Args:
            static_data: Optional static analysis data
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.analysis.state_analyzer",
            {CONTEXT_COMPONENT: "StateAnalyzer"}
        )

        # Store static data
        self.static_data = static_data

        # Initialize performance monitor
        self.performance_monitor = PerformanceMonitor.get_instance()

        # Initialize state tracking
        self.seen_states: Set[str] = set()
        self.state_transitions: List[Tuple[str, str, ItemAction]] = []
        self.state_fingerprints: Dict[str, Dict[str, Any]] = {}

        self.logger.info("Initialized state analyzer")

    def analyze_state(self, screen: ScreenDescription, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a screen description and state data to extract insights.

        Args:
            screen: Parsed screen description
            state_data: Raw state data

        Returns:
            Dictionary with analysis results
        """
        print("Analyzing state...")
        with self.performance_monitor.measure_time("state_analysis"):
            # Generate state fingerprint
            fingerprint = self._generate_fingerprint(screen, state_data)

            # Check if we've seen this state before
            is_new_state = fingerprint not in self.seen_states
            print(f"is_new_state={is_new_state}")

            # Track state
            if is_new_state:
                self.seen_states.add(fingerprint)
                self.state_fingerprints[fingerprint] = {
                    "activity": screen.activity,
                    "item_count": len(screen.items),
                    "timestamp": state_data.get("timestamp", 0)
                }

            # Classify screen
            screen_type = self._classify_screen(screen, state_data)
            print(f"screen_type={screen_type}")

            # Identify testing opportunities
            opportunities = self._identify_opportunities(screen, state_data)
            print(f"opportunities={opportunities}")

            # Enrich with static analysis if available
            static_insights = self._get_static_insights(screen.activity)
            print(f"static_insights={static_insights}")

            # Combine all results
            analysis = {
                "fingerprint": fingerprint,
                "is_new_state": is_new_state,
                "screen_type": screen_type,
                "opportunities": opportunities,
                "static_insights": static_insights,
                "seen_states_count": len(self.seen_states),
                "interactive_elements_count": len(screen.items)
            }
            print(f"analysis={analysis}")

            return analysis

    def _generate_fingerprint(self, screen: ScreenDescription, state_data: Dict[str, Any]) -> str:
        """
        Generate a unique fingerprint for a state to identify duplicate states.

        Args:
            screen: Parsed screen description
            state_data: Raw state data

        Returns:
            State fingerprint string
        """
        print("Generating fingerprint...")
        # Start with activity name
        components = [screen.activity]

        # Add essential UI elements
        ui_elements = []
        for item in screen.items:
            # Extract key properties that identify the element
            element_id = item.view.get("resource_id", "")
            element_class = item.view.get("class", "")
            element_text = item.view.get("text", "")

            if element_id:
                ui_elements.append(f"id:{element_id}")
            elif element_text:
                ui_elements.append(f"text:{element_text}:{element_class}")

        # Sort to ensure consistent ordering
        ui_elements.sort()
        components.extend(ui_elements)

        # Create fingerprint
        import hashlib
        fingerprint = hashlib.md5("|".join(components).encode()).hexdigest()
        print(f"********** Fingerprint: {fingerprint}")

        return fingerprint

    def _classify_screen(self, screen: ScreenDescription, state_data: Dict[str, Any]) -> str:
        """
        Classify the screen based on its content and structure.

        Args:
            screen: Parsed screen description
            state_data: Raw state data

        Returns:
            Screen classification
        """
        # Extract key elements for classification
        has_text_fields = False
        has_buttons = False
        has_lists = False
        has_checkboxes = False
        has_images = False

        for item in screen.items:
            class_name = item.view.get("class", "")

            if "EditText" in class_name:
                has_text_fields = True
            elif "Button" in class_name:
                has_buttons = True
            elif "ListView" in class_name or "RecyclerView" in class_name:
                has_lists = True
            elif "CheckBox" in class_name:
                has_checkboxes = True
            elif "ImageView" in class_name:
                has_images = True

        # Classify based on composition
        if has_text_fields and has_buttons:
            return "form"
        elif has_lists:
            return "list"
        elif has_checkboxes:
            return "options"
        elif has_images and not has_text_fields:
            return "gallery"
        elif not has_text_fields and not has_buttons and not has_lists:
            return "information"
        else:
            return "generic"

    def _identify_opportunities(self, screen: ScreenDescription, state_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify testing opportunities based on the screen content.

        Args:
            screen: Parsed screen description
            state_data: Raw state data

        Returns:
            List of testing opportunities
        """
        opportunities = []

        for item in screen.items:
            for action in item.actions:
                # Skip if no view data
                if not hasattr(action, 'target_view') or not action.target_view:
                    continue

                view = action.target_view
                resource_id = view.get("resource_id", "")
                class_name = view.get("class", "")
                text = view.get("text", "")

                # Assign scores to different opportunities
                score = 0
                rationale = []

                # Prioritize security-sensitive elements
                if action.reaches_mop:
                    score += 10
                    rationale.append("Reaches security-sensitive operations")

                # Prioritize interactive elements
                if "Button" in class_name:
                    score += 5
                    rationale.append("Interactive button element")

                # Prioritize password fields
                if "EditText" in class_name and view.get("password", False):
                    score += 8
                    rationale.append("Password field")

                # Prioritize form submission elements
                if "submit" in text.lower() or "login" in text.lower() or "sign in" in text.lower():
                    score += 7
                    rationale.append("Form submission element")

                # Prioritize elements with IDs (more stable)
                if resource_id:
                    score += 3
                    rationale.append("Has stable resource ID")

                # Add as opportunity if score is significant
                if score > 0:
                    opportunities.append({
                        "action_id": action.id,
                        "score": score,
                        "rationale": rationale,
                        "resource_id": resource_id,
                        "class_name": class_name,
                        "text": text
                    })

        # Sort by score (highest first)
        opportunities.sort(key=lambda x: x["score"], reverse=True)

        return opportunities

    def _get_static_insights(self, activity: str) -> Dict[str, Any]:
        """
        Get insights from static analysis for the current activity.

        Args:
            activity: Current activity name

        Returns:
            Dictionary with static analysis insights
        """
        insights = {}

        if not self.static_data:
            return insights

        # Normalize activity name
        normalized_activity = activity.replace("/", "")

        # Get activity class data if available
        activity_class = self.static_data.classes.get_clazz(normalized_activity)
        if not activity_class:
            return insights

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

        # Add window transition information if available
        if self.static_data.wtg:
            edges = []
            for edge in self.static_data.wtg.graph.edges():
                # edge is now (source_id, target_id) where both are strings
                source_id = edge[0]
                target_id = edge[1]
                
                # Get the window objects by ID if needed
                source_window = self.static_data.windows.get_window_by_id(source_id)
                
                # Compare with activity class name
                if source_window and source_window.name == activity_class.name:
                    edges.append(edge)
                # Also check by ID directly in case the window names use IDs
                elif source_id == activity_class.name:
                    edges.append(edge)

            if edges:
                insights["possible_transitions_count"] = len(edges)
                
                # Get the window names if possible, otherwise use the IDs
                target_names = []
                for edge in edges[:5]:
                    target_id = edge[1]
                    target_window = self.static_data.windows.get_window_by_id(target_id)
                    if target_window:
                        target_names.append(target_window.name)
                    else:
                        target_names.append(target_id)
                        
                insights["possible_transitions"] = target_names

        return insights

    def record_transition(self, from_state: str, to_state: str, action: ItemAction) -> None:
        """
        Record a state transition.

        Args:
            from_state: Source state fingerprint
            to_state: Destination state fingerprint
            action: Action that caused the transition
        """
        self.state_transitions.append((from_state, to_state, action))

    def get_state_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about observed states.

        Returns:
            Dictionary with state statistics
        """
        # Calculate transitions per state
        transitions_per_state = {}
        for from_state, to_state, _ in self.state_transitions:
            if from_state not in transitions_per_state:
                transitions_per_state[from_state] = set()
            transitions_per_state[from_state].add(to_state)

        # Find states with most and least transitions
        most_transitions = None
        least_transitions = None
        most_count = 0
        least_count = float('inf')

        for state, transitions in transitions_per_state.items():
            count = len(transitions)
            if count > most_count:
                most_count = count
                most_transitions = state
            if count < least_count:
                least_count = count
                least_transitions = state

        return {
            "total_states": len(self.seen_states),
            "total_transitions": len(self.state_transitions),
            "unique_transitions": len(set((f, t) for f, t, _ in self.state_transitions)),
            "most_transitions": {
                "state": most_transitions,
                "count": most_count
            } if most_transitions else None,
            "least_transitions": {
                "state": least_transitions,
                "count": least_count
            } if least_transitions else None
        }
