# Fixed version of rvandroid/rvdroid/analysis/opportunity/opportunity_detector.py

from typing import Dict, Any, List, Optional, Set

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription, ItemAction
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class OpportunityDetector:
    """
    Identifies and prioritizes testing opportunities within application states.

    Evaluates UI elements for testing value based on multiple heuristics
    including security-sensitivity, UI element type, and exploration value.
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the opportunity detector.

        Args:
            static_data: Optional static analysis data
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.analysis.opportunity_detector",
            {CONTEXT_COMPONENT: "OpportunityDetector"}
        )

        # Store static data
        self.static_data = static_data

        # Initialize tracking
        self.tested_actions: Set[int] = set()
        self.exploration_scores: Dict[str, Dict[str, float]] = {
            "element_types": {
                "Button": 5.0,
                "EditText": 4.0,
                "CheckBox": 3.5,
                "RadioButton": 3.5,
                "Spinner": 4.0,
                "SeekBar": 3.0,
                "Switch": 3.5,
                "ImageButton": 4.0,
                "TextView": 1.0,
                "ImageView": 1.0
            },
            "element_traits": {
                "clickable": 3.0,
                "long_clickable": 2.0,
                "scrollable": 2.5,
                "checkable": 2.5,
                "editable": 3.5,
                "password": 5.0,
                "has_resource_id": 1.5,
                "has_text": 1.0
            },
            "keywords": {
                "login": 5.0,
                "sign": 4.5,
                "submit": 4.0,
                "confirm": 4.0,
                "password": 5.0,
                "username": 4.0,
                "pay": 5.0,
                "credit": 5.0,
                "send": 4.0,
                "settings": 3.5,
                "account": 4.0,
                "delete": 4.5,
                "cancel": 3.0,
                "save": 4.0
            }
        }

        self.logger.info("Initialized opportunity detector")

    def detect_opportunities(self, screen: ScreenDescription,
                             context_info: Optional[Dict[str, Any]] = None,
                             state_history: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Detect testing opportunities based on screen content and context.

        Args:
            screen: Parsed screen description
            context_info: Optional context analysis information
            state_history: Optional history of previous states

        Returns:
            List of testing opportunities with scores and metadata
        """
        opportunities = []

        # Extract context information
        context_type = context_info.get("primary_context", "unknown") if context_info else "unknown"
        security_level = "medium"  # Default

        if context_info and "domain_matches" in context_info:
            # Get security level from domain pattern matches
            domain_matches = context_info["domain_matches"]

            # Fix: Check the type of domain_matches to handle different possible structures
            if isinstance(domain_matches, dict):
                # Possible structures:
                # 1. domain_matches = {'authentication': 0.8, 'payment': 0.3}
                # 2. domain_matches = {'authentication': {'security_level': 'high'}}

                if context_type in domain_matches:
                    match_value = domain_matches[context_type]

                    # Case 1: If it's a confidence score (float)
                    if isinstance(match_value, float):
                        # Determine security level based on confidence
                        if match_value > 0.7:
                            security_level = "high"
                        elif match_value > 0.4:
                            security_level = "medium"
                        else:
                            security_level = "low"

                    # Case 2: If it's a dictionary with security_level
                    elif isinstance(match_value, dict) and "security_level" in match_value:
                        security_level = match_value["security_level"]

                # Also look for domains with security implications
                for domain, value in domain_matches.items():
                    if domain in ["authentication", "payment", "registration"] and domain != context_type:
                        # If another security-sensitive domain has high confidence
                        if isinstance(value, float) and value > 0.6:
                            security_level = "medium"  # At least medium security
                        elif isinstance(value, dict) and value.get("security_level") in ["high", "critical"]:
                            security_level = "medium"  # At least medium security

        # Track which resource IDs we've seen to avoid duplicates
        seen_resource_ids = set()

        # Score each action
        for item in screen.items:
            for action in item.actions:
                # Skip if we've already added an action for this UI element
                resource_id = item.view.get("resource_id", "")
                if resource_id and resource_id in seen_resource_ids:
                    continue

                # Add resource ID to seen set if not empty
                if resource_id:
                    seen_resource_ids.add(resource_id)

                # Get view properties
                class_name = item.view.get("class", "")
                simple_class = class_name.split(".")[-1] if class_name else ""
                text = item.view.get("text", "")

                # Calculate base score from element type
                score = self._calculate_base_score(item.view, simple_class)

                # Adjust for security sensitivity
                if action.reaches_mop or action.directly_reaches_mop:
                    score *= 1.5
                    if action.directly_reaches_mop:
                        score *= 1.2

                # Adjust for context type
                score = self._adjust_for_context(score, context_type, item.view, action)

                # Adjust for exploration value (prefer untested actions)
                if action.id in self.tested_actions:
                    score *= 0.5

                # Create opportunity object
                opportunity = {
                    "action_id": action.id,
                    "score": score,
                    "resource_id": resource_id,
                    "class": simple_class,
                    "text": text,
                    "already_tested": action.id in self.tested_actions,
                    "reaches_mop": action.reaches_mop,
                    "directly_reaches_mop": action.directly_reaches_mop,
                    "security_level": security_level
                }

                opportunities.append(opportunity)

        # Sort by score (highest first)
        opportunities.sort(key=lambda x: x["score"], reverse=True)

        return opportunities

    def _calculate_base_score(self, view: Dict[str, Any], simple_class: str) -> float:
        """
        Calculate the base score for an element based on its properties.

        Args:
            view: View data dictionary
            simple_class: Simplified class name

        Returns:
            Base score for the element
        """
        score = 1.0  # Default score

        # Score based on element type
        if simple_class in self.exploration_scores["element_types"]:
            score = self.exploration_scores["element_types"][simple_class]

        # Adjust for element traits
        if view.get("clickable", False):
            score += self.exploration_scores["element_traits"]["clickable"]

        if view.get("long_clickable", False):
            score += self.exploration_scores["element_traits"]["long_clickable"]

        if view.get("scrollable", False):
            score += self.exploration_scores["element_traits"]["scrollable"]

        if view.get("checkable", False):
            score += self.exploration_scores["element_traits"]["checkable"]

        if view.get("editable", False) or "EditText" in simple_class:
            score += self.exploration_scores["element_traits"]["editable"]

        if view.get("password", False):
            score += self.exploration_scores["element_traits"]["password"]

        # Adjust for identifiers
        if view.get("resource_id", ""):
            score += self.exploration_scores["element_traits"]["has_resource_id"]

        if view.get("text", ""):
            score += self.exploration_scores["element_traits"]["has_text"]

            # Check for keywords in text
            text = view.get("text", "").lower()
            for keyword, keyword_score in self.exploration_scores["keywords"].items():
                if keyword in text:
                    score += keyword_score * 0.5  # Apply partial keyword score

        return score

    def _adjust_for_context(self, base_score: float, context_type: str, view: Dict[str, Any],
                            action: ItemAction) -> float:
        """
        Adjust the opportunity score based on context.

        Args:
            base_score: Base score for the element
            context_type: Context type (e.g., "authentication", "payment")
            view: View data dictionary
            action: Action object

        Returns:
            Adjusted score
        """
        score = base_score

        # Adjust for context type
        if context_type == "authentication":
            # Prioritize password fields and submission buttons
            if view.get("password", False):
                score *= 1.5

            text = view.get("text", "").lower()
            if "login" in text or "sign in" in text or "submit" in text:
                score *= 1.3

        elif context_type == "payment":
            # Prioritize payment fields and submission buttons
            text = view.get("text", "").lower()
            if "pay" in text or "purchase" in text or "buy" in text or "credit" in text:
                score *= 1.5

        elif context_type == "registration":
            # Prioritize form fields and submission buttons
            if "EditText" in view.get("class", ""):
                score *= 1.2

            text = view.get("text", "").lower()
            if "register" in text or "sign up" in text or "create" in text:
                score *= 1.3

        # Prioritize untested security-sensitive operations
        if action.reaches_mop and action.id not in self.tested_actions:
            score *= 1.5

        return score

    def mark_action_tested(self, action_id: int) -> None:
        """
        Mark an action as tested.

        Args:
            action_id: ID of the action
        """
        self.tested_actions.add(action_id)

    def get_high_value_actions(self, opportunities: List[Dict[str, Any]], count: int = 3) -> List[Dict[str, Any]]:
        """
        Get a list of high-value actions from the opportunities.

        Args:
            opportunities: List of opportunities
            count: Maximum number of actions to return

        Returns:
            List of high-value actions
        """
        # Already sorted by score, just return the top ones
        return opportunities[:count]
