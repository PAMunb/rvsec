"""
Context analyzer for RVDroid.

This module provides functionality to analyze the contextual meaning
of application screens, identify semantic patterns, and track context
transitions during testing.
"""

from typing import Dict, Any, List, Optional, Set

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.model import ScreenDescription
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class ContextAnalyzer:
    """
    Analyzes application context to understand semantic meaning and state transitions.

    Provides functionality to identify the contextual meaning of screens,
    track context transitions, and understand application behavior patterns.
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the context analyzer.

        Args:
            static_data: Optional static analysis data
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.analysis.context_analyzer",
            {CONTEXT_COMPONENT: "ContextAnalyzer"}
        )

        # Store static data
        self.static_data = static_data

        # Initialize context tracking
        self.current_context: Optional[Dict[str, Any]] = None
        self.context_history: List[Dict[str, Any]] = []
        self.domain_patterns: Dict[str, Dict[str, Any]] = self._initialize_domain_patterns()

        self.logger.info("Initialized context analyzer")

    def _initialize_domain_patterns(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize domain patterns for context recognition.

        Returns:
            Dictionary with domain patterns
        """
        return {
            "authentication": {
                "keywords": ["login", "sign in", "password", "username", "email", "authenticate"],
                "ui_classes": ["EditText", "Button"],
                "operation_sensitivity": "high"
            },
            "registration": {
                "keywords": ["register", "sign up", "create account", "new user"],
                "ui_classes": ["EditText", "Button"],
                "operation_sensitivity": "high"
            },
            "payment": {
                "keywords": ["pay", "payment", "credit card", "checkout", "purchase"],
                "ui_classes": ["EditText", "Button"],
                "operation_sensitivity": "critical"
            },
            "messaging": {
                "keywords": ["message", "chat", "send", "reply", "conversation"],
                "ui_classes": ["EditText", "Button", "ListView", "RecyclerView"],
                "operation_sensitivity": "medium"
            },
            "settings": {
                "keywords": ["settings", "preferences", "configure", "options"],
                "ui_classes": ["CheckBox", "Switch", "RadioButton"],
                "operation_sensitivity": "medium"
            },
            "navigation": {
                "keywords": ["menu", "home", "back", "next", "previous"],
                "ui_classes": ["Button", "ImageButton"],
                "operation_sensitivity": "low"
            },
            "content_display": {
                "keywords": ["view", "display", "show", "details"],
                "ui_classes": ["TextView", "ImageView"],
                "operation_sensitivity": "low"
            },
            "data_entry": {
                "keywords": ["edit", "input", "enter", "fill", "form"],
                "ui_classes": ["EditText", "Button"],
                "operation_sensitivity": "medium"
            }
        }

    # rvandroid/rvdroid/analysis/context/context_analyzer.py

    def analyze_context(self, screen: ScreenDescription, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the context of the current screen.

        Args:
            screen: Parsed screen description
            state_data: Raw state data

        Returns:
            Dictionary with context analysis
        """
        # Extract text content from screen
        text_content = self._extract_text_content(screen)

        # Extract UI classes from screen
        ui_classes = self._extract_ui_classes(screen)

        # Identify domain patterns
        domain_matches = self._identify_domain_patterns(text_content, ui_classes)

        # Determine primary context
        primary_context, confidence = self._determine_primary_context(domain_matches)

        # Create context object
        context = {
            "activity": screen.activity,
            "primary_context": primary_context,
            "confidence": confidence,
            "domain_matches": domain_matches,
            "text_content": text_content,
            "ui_classes": ui_classes,
        }

        # Track context transition
        self._track_context_transition(context)

        return context

    def _extract_text_content(self, screen: ScreenDescription) -> List[str]:
        """
        Extract textual content from the screen.

        Args:
            screen: Parsed screen description

        Returns:
            List of text strings
        """
        text_content = []

        for item in screen.items:
            # Extract text from view
            view_text = item.view.get("text", "")
            if view_text:
                text_content.append(view_text)

            # Extract content description
            content_desc = item.view.get("content_description", "")
            if content_desc:
                text_content.append(content_desc)

            # Extract hint text
            hint = item.view.get("hint", "")
            if hint:
                text_content.append(hint)

        return text_content

    def _extract_ui_classes(self, screen: ScreenDescription) -> List[str]:
        """
        Extract UI class names from the screen.

        Args:
            screen: Parsed screen description

        Returns:
            List of UI class names
        """
        ui_classes = []

        for item in screen.items:
            class_name = item.view.get("class", "")
            if class_name:
                # Extract the simple class name
                simple_class = class_name.split('.')[-1]
                ui_classes.append(simple_class)

        return ui_classes

    def _identify_domain_patterns(self, text_content: List[str], ui_classes: List[str]) -> Dict[str, float]:
        """
        Identify domain patterns in the screen content.

        Args:
            text_content: List of text strings
            ui_classes: List of UI class names

        Returns:
            Dictionary mapping domain patterns to confidence scores
        """
        domain_matches = {}

        # Combine all text for easier matching
        text_combined = " ".join(text_content).lower()

        for domain, pattern in self.domain_patterns.items():
            # Count keyword matches
            keyword_count = 0
            for keyword in pattern["keywords"]:
                if keyword.lower() in text_combined:
                    keyword_count += 1

            # Count UI class matches
            class_count = 0
            for ui_class in pattern["ui_classes"]:
                if ui_class in ui_classes:
                    class_count += 1

            # Calculate confidence based on matches
            keyword_confidence = keyword_count / len(pattern["keywords"]) if pattern["keywords"] else 0
            class_confidence = class_count / len(pattern["ui_classes"]) if pattern["ui_classes"] else 0

            # Combined confidence (weighted toward keywords)
            confidence = (keyword_confidence * 0.7) + (class_confidence * 0.3)

            if confidence > 0:
                domain_matches[domain] = confidence

        return domain_matches

    def _determine_primary_context(self, domain_matches: Dict[str, float]) -> tuple:
        """
        Determine the primary context from domain matches.

        Args:
            domain_matches: Dictionary mapping domains to confidence scores

        Returns:
            Tuple of (primary_context, confidence)
        """
        if not domain_matches:
            return "unknown", 0.0

        # Find domain with highest confidence
        domain, confidence = max(domain_matches.items(), key=lambda x: x[1])
        return domain, confidence

    def _track_context_transition(self, context: Dict[str, Any]) -> None:
        """
        Track a context transition.

        Args:
            context: Current context
        """
        # Only track if there's a transition
        if not self.current_context or self.current_context["primary_context"] != context["primary_context"]:
            # Store previous context
            if self.current_context:
                self.context_history.append(self.current_context)

            # Update current context
            self.current_context = context

            self.logger.info(
                f"Context transition to: {context['primary_context']} (confidence: {context['confidence']:.2f})")

    def get_context_history(self) -> List[Dict[str, Any]]:
        """
        Get the context transition history.

        Returns:
            List of context objects
        """
        return self.context_history

    def suggest_testing_focus(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Suggest testing focus based on the current context.

        Args:
            context: Current context

        Returns:
            Dictionary with testing suggestions
        """
        primary_context = context["primary_context"]

        # Default suggestions
        suggestions = {
            "focus_areas": [],
            "operation_sensitivity": "low",
            "recommended_actions": []
        }

        # Context-specific suggestions
        if primary_context == "authentication":
            suggestions["focus_areas"] = ["input validation", "error handling", "specification compliance", "usability"]
            suggestions["operation_sensitivity"] = "high"
            suggestions["recommended_actions"] = [
                "Test invalid credentials",
                "Test password requirements",
                "Check error messages",
                "Verify secure input for passwords"
            ]

        elif primary_context == "payment":
            suggestions["focus_areas"] = ["input validation", "error handling", "specification compliance", "transaction flow"]
            suggestions["operation_sensitivity"] = "critical"
            suggestions["recommended_actions"] = [
                "Test invalid payment information",
                "Verify transaction confirmation",
                "Check method usage indicators",
                "Validate payment flow"
            ]

        elif primary_context == "data_entry":
            suggestions["focus_areas"] = ["input validation", "error handling", "data persistence"]
            suggestions["operation_sensitivity"] = "medium"
            suggestions["recommended_actions"] = [
                "Test boundary values",
                "Test invalid input",
                "Check form submission",
                "Verify data persistence"
            ]

        elif primary_context == "navigation":
            suggestions["focus_areas"] = ["navigation flow", "state management", "accessibility"]
            suggestions["operation_sensitivity"] = "low"
            suggestions["recommended_actions"] = [
                "Test navigation paths",
                "Check state preservation",
                "Verify back button behavior"
            ]

        # Add specification focus if domain pattern has high operation sensitivity
        if primary_context in self.domain_patterns:
            sensitivity_level = self.domain_patterns[primary_context].get("operation_sensitivity", "low")
            suggestions["operation_sensitivity"] = sensitivity_level

            if sensitivity_level in ["high", "critical"]:
                if "specification compliance" not in suggestions["focus_areas"]:
                    suggestions["focus_areas"].append("specification compliance")

        return suggestions
