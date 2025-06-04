# rvandroid/rvdroid/analysis/opportunity/opportunity_detector.py

"""
Opportunity detector for RVDroid.

This module provides functionality to identify and prioritize testing
opportunities within application states, based on multiple criteria
including UI element properties, operations of interest, and history.
"""

from typing import Dict, Any, List, Optional, Set, Tuple

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.model import ItemAction, ScreenDescription
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor


class OpportunityDetector:
    """
    Identifies and prioritizes testing opportunities within application states.

    ### Architectural Decisions:
    - Implements a scoring system for UI element prioritization
    - Uses multiple heuristic categories for comprehensive evaluation
    - Incorporates specification awareness through MOP reachability
    - Adapts to context and domain patterns
    - Tracks testing history for exploration optimization
    
    ### Role in the System:
    - Provides prioritized action recommendations
    - Guides testing toward operations of interest and monitored methods
    - Balances exploration with targeted testing
    - Integrates static analysis with runtime opportunities
    - Provides contextual awareness to testing strategies
    
    ### Key Considerations:
    - Specification-first approach to opportunity identification
    - Adaptive scoring based on application context
    - History tracking to avoid redundant exploration
    - Performance optimization through prioritization
    - Integration with static analysis for enhanced targeting
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

        # Initialize performance monitor
        self.performance_monitor = PerformanceMonitor.get_instance()

        # Store static data
        self.static_data = static_data

        # Initialize tracking
        self.tested_actions: Set[int] = set()
        self.action_success_rates: Dict[int, Dict[str, int]] = {}
        
        # Track overall exploration statistics
        self.exploration_stats = {
            "total_actions_evaluated": 0,
            "monitored_methods_found": 0,
            "unique_activities_seen": set(),
            "context_types_seen": set()
        }
        
        # Scoring system for opportunity evaluation
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
                # Security-related keywords
                "login": 5.0,
                "sign": 4.5,
                "register": 4.5,
                "submit": 4.0,
                "confirm": 4.0,
                "password": 5.0,
                "username": 4.0,
                "pay": 5.0,
                "credit": 5.0,
                "card": 4.8,
                "security": 5.0,
                "permission": 5.0,
                "access": 4.2,
                "authenticate": 5.0,
                "authorize": 5.0,
                # Navigation keywords
                "send": 4.0,
                "settings": 3.5,
                "account": 4.0,
                "profile": 3.8,
                "edit": 3.5,
                "delete": 4.5,
                "remove": 4.0,
                "cancel": 3.0,
                "save": 4.0,
                "next": 3.5,
                "back": 2.5,
                "finish": 4.0,
                "continue": 3.8
            },
            "context_types": {
                "authentication": 1.8,
                "payment": 1.8,
                "registration": 1.5,
                "settings": 1.3,
                "sensitive_data": 1.7,
                "permissions": 1.6,
                "content_entry": 1.4,
                "navigation": 1.0
            }
        }
        
        # Operation sensitivity patterns - used to identify potential specification-related contexts
        self.operation_patterns = {
            "authentication": [
                "login", "sign in", "password", "username", "email", "auth", "verify"
            ],
            "payment": [
                "pay", "credit", "card", "cvv", "expiry", "billing", "purchase"
            ],
            "data_processing": [
                "personal", "private", "encrypt", "key", "token", "iterate", "process", "validate"
            ],
            "permissions": [
                "permission", "allow", "access", "camera", "location", "contacts", "storage"
            ]
        }

        self.logger.info("Initialized opportunity detector")

    def detect_opportunities(self, screen: ScreenDescription,
                             context_info: Optional[Dict[str, Any]] = None,
                             state_history: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Detect testing opportunities based on screen content and context.

        Analyzes the current screen and state to identify high-value testing
        opportunities, prioritizing operations that reach monitored methods, unexplored paths,
        and contextually relevant interactions.

        Args:
            screen: Parsed screen description
            context_info: Optional context analysis information
            state_history: Optional history of previous states

        Returns:
            List of testing opportunities with scores and metadata
        """
        with self.performance_monitor.measure_time("detect_opportunities"):
            opportunities = []
            
            # Update exploration statistics
            if screen.activity and screen.activity not in self.exploration_stats["unique_activities_seen"]:
                self.exploration_stats["unique_activities_seen"].add(screen.activity)
    
            # Try to infer context type if not provided
            inferred_context_type = "unknown"
            inferred_context_confidence = 0.0
            operation_sensitivity = "medium"  # Default
            
            # First attempt: use provided context_info
            if context_info and "primary_context" in context_info:
                inferred_context_type = context_info.get("primary_context", "unknown")
                
                # Add to seen contexts
                if inferred_context_type != "unknown":
                    self.exploration_stats["context_types_seen"].add(inferred_context_type)
                
                # Extract operation sensitivity if available
                if "domain_matches" in context_info:
                    domain_matches = context_info["domain_matches"]
                    
                    if isinstance(domain_matches, dict):
                        # Extract operation sensitivity based on domain match structure
                        if inferred_context_type in domain_matches:
                            match_value = domain_matches[inferred_context_type]
                            
                            # Handle different structure formats
                            if isinstance(match_value, float):
                                inferred_context_confidence = match_value
                                # Determine operation sensitivity based on confidence
                                if match_value > 0.7:
                                    operation_sensitivity = "high"
                                elif match_value > 0.4:
                                    operation_sensitivity = "medium"
                                else:
                                    operation_sensitivity = "low"
                            elif isinstance(match_value, dict) and ("security_level" in match_value or "operation_sensitivity" in match_value):
                                if "operation_sensitivity" in match_value:
                                    operation_sensitivity = match_value["operation_sensitivity"]
                                else:
                                    operation_sensitivity = match_value["security_level"]
                                inferred_context_confidence = match_value.get("confidence", 0.7)
                
                        # Also look for other domains with high operation sensitivity
                        for domain, value in domain_matches.items():
                            if domain in ["authentication", "payment", "registration", "sensitive_data"] and domain != inferred_context_type:
                                # If another domain with monitored methods has high confidence
                                domain_confidence = 0.0
                                if isinstance(value, float):
                                    domain_confidence = value
                                elif isinstance(value, dict) and "confidence" in value:
                                    domain_confidence = value["confidence"]
                                
                                if domain_confidence > 0.5:
                                    # Upgrade operation sensitivity if needed
                                    if operation_sensitivity == "low":
                                        operation_sensitivity = "medium"
                                        self.logger.info(f"Upgraded operation sensitivity to medium due to {domain} domain")
            
            # Second attempt: infer from screen content
            if inferred_context_type == "unknown" or inferred_context_confidence < 0.4:
                # Try to infer context from screen content
                detected_context = self._detect_context_from_screen(screen)
                if detected_context:
                    inferred_context_type, inferred_context_confidence = detected_context
                    self.exploration_stats["context_types_seen"].add(inferred_context_type)
                    
                    if inferred_context_confidence > 0.7:
                        if inferred_context_type in ["authentication", "payment", "sensitive_data", "permissions"]:
                            operation_sensitivity = "high"
                            self.logger.info(f"Set operation sensitivity to high for {inferred_context_type} context (confidence: {inferred_context_confidence:.2f})")
                        elif inferred_context_confidence > 0.5:
                            operation_sensitivity = "medium"
    
            self.logger.debug(f"Detected context: {inferred_context_type} (confidence: {inferred_context_confidence:.2f}, operation sensitivity: {operation_sensitivity})")
            
            # Look for operations that reach monitored methods based on static analysis
            monitored_method_actions = self._identify_monitored_method_actions(screen)
            
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
                    content_desc = item.view.get("content-desc", "")
    
                    # Calculate base score from element type
                    score = self._calculate_base_score(item.view, simple_class)
    
                    # Adjust for operations reaching monitored methods
                    reaches_monitored_method = action.id in monitored_method_actions
                    if action.reaches_mop or action.directly_reaches_mop or reaches_monitored_method:
                        score *= 1.5
                        if action.directly_reaches_mop:
                            score *= 1.2
                        
                        # Update overall statistics
                        self.exploration_stats["monitored_methods_found"] += 1
    
                    # Adjust for context type
                    score = self._adjust_for_context(score, inferred_context_type, item.view, action)
    
                    # Adjust for history if available
                    if state_history:
                        score = self._adjust_for_history(score, action, state_history)
    
                    # Adjust for exploration value (prefer untested actions)
                    if action.id in self.tested_actions:
                        success_rate = self._get_action_success_rate(action.id)
                        # Reduce score less for actions with low success rate
                        if success_rate < 0.3:
                            score *= 0.8  # May need to retry failed actions
                        else:
                            score *= 0.5  # Successfully tested actions get lower priority
    
                    # Create opportunity object
                    opportunity = {
                        "action_id": action.id,
                        "score": score,
                        "resource_id": resource_id,
                        "class": simple_class,
                        "text": text,
                        "content_desc": content_desc,
                        "already_tested": action.id in self.tested_actions,
                        "reaches_mop": action.reaches_mop or reaches_monitored_method,
                        "directly_reaches_mop": action.directly_reaches_mop,
                        "operation_sensitivity": operation_sensitivity,
                        "context_type": inferred_context_type,
                        "context_confidence": inferred_context_confidence,
                        "success_rate": self._get_action_success_rate(action.id) if action.id in self.tested_actions else None
                    }
    
                    opportunities.append(opportunity)
                    self.exploration_stats["total_actions_evaluated"] += 1
    
            # Sort by score (highest first)
            opportunities.sort(key=lambda x: x["score"], reverse=True)
    
            # Add a human-readable rationale to the top opportunities
            for opportunity in opportunities[:5]:
                opportunity["rationale"] = self._generate_opportunity_rationale(opportunity, screen)
    
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

    def _detect_context_from_screen(self, screen: ScreenDescription) -> Optional[Tuple[str, float]]:
        """
        Detect the context type from screen content.
        
        Args:
            screen: Parsed screen description
            
        Returns:
            Tuple of (context_type, confidence) or None if not detected
        """
        # Count matches for each context type
        context_matches = {
            context_type: 0 for context_type in self.operation_patterns.keys()
        }
        context_matches["navigation"] = 0
        context_matches["content_entry"] = 0
        
        # Scan all elements for pattern matches
        total_elements = 0
        for item in screen.items:
            total_elements += 1
            
            # Extract text from multiple sources
            element_text = []
            if item.view.get("text", ""):
                element_text.append(item.view.get("text", "").lower())
            if item.view.get("content-desc", ""):
                element_text.append(item.view.get("content-desc", "").lower())
            if item.view.get("resource_id", ""):
                element_text.append(item.view.get("resource_id", "").split("/")[-1].lower())
                
            element_text = " ".join(element_text)
            
            # Check for context pattern matches
            for context_type, patterns in self.operation_patterns.items():
                for pattern in patterns:
                    if pattern in element_text:
                        context_matches[context_type] += 1
                        
            # Check for navigation elements
            class_name = item.view.get("class", "").lower()
            if "button" in class_name or "menu" in class_name or "nav" in class_name:
                if "back" in element_text or "menu" in element_text or "home" in element_text:
                    context_matches["navigation"] += 1
                    
            # Check for content entry
            if "edittext" in class_name or "input" in class_name:
                context_matches["content_entry"] += 1
                    
        # Find the context with most matches
        if total_elements == 0:
            return None
            
        best_context = max(context_matches.items(), key=lambda x: x[1])
        context_type, match_count = best_context
        
        # Calculate confidence score
        if match_count == 0:
            return None
            
        confidence = min(1.0, match_count / (total_elements * 0.5))  # Scale to account for not all elements having matches
        
        # Only return if confidence is reasonable
        if confidence >= 0.2:
            return context_type, confidence
            
        return None
        
    def _identify_monitored_method_actions(self, screen: ScreenDescription) -> Set[int]:
        """
        Identify actions that reach monitored methods based on static analysis and heuristics.
        
        Args:
            screen: Screen description
            
        Returns:
            Set of action IDs that reach monitored methods
        """
        monitored_method_actions = set()
        
        # Look for actions that reach monitored methods based on static analysis
        for item in screen.items:
            for action in item.actions:
                # First check: explicit MOP reachability
                if action.reaches_mop or action.directly_reaches_mop:
                    monitored_method_actions.add(action.id)
                    continue
                    
                # Second check: resource ID or text contains operation keywords
                if self._check_operation_keywords(item.view):
                    monitored_method_actions.add(action.id)
        
        return monitored_method_actions
        
    def _check_operation_keywords(self, view: Dict[str, Any]) -> bool:
        """
        Check if a view contains keywords related to monitored operations.
        
        Args:
            view: UI element view data
            
        Returns:
            True if operation keywords found, False otherwise
        """
        operation_keywords = [
            "password", "login", "sign", "auth", "encrypt", "key", "iterator", "next",
            "credential", "token", "verify", "permission", "validate", "compare", "check"
        ]
        
        # Check resource ID
        resource_id = view.get("resource_id", "").lower()
        for keyword in operation_keywords:
            if keyword in resource_id:
                return True
                
        # Check text
        text = view.get("text", "").lower()
        for keyword in operation_keywords:
            if keyword in text:
                return True
                
        # Check content description
        content_desc = view.get("content-desc", "").lower()
        for keyword in operation_keywords:
            if keyword in content_desc:
                return True
                
        return False
        
    def _adjust_for_history(self, score: float, action: ItemAction, 
                           state_history: List[Dict[str, Any]]) -> float:
        """
        Adjust score based on exploration history.
        
        Args:
            score: Current score
            action: Action to score
            state_history: Exploration history
            
        Returns:
            Adjusted score
        """
        # If no history or short history, no adjustment
        if not state_history or len(state_history) < 3:
            return score
            
        # Extract recent actions
        recent_actions = []
        for state in state_history[-5:]:  # Last 5 states
            if "action" in state and state["action"]:
                recent_actions.append(state["action"].get("id", -1))
                
        # Penalize actions that were recently performed
        if action.id in recent_actions:
            # More recent actions get higher penalty
            recency_index = recent_actions[::-1].index(action.id)  # Reverse to get most recent first
            recency_penalty = 0.5 + (0.1 * recency_index)  # 0.5 for most recent, increasing with age
            score *= recency_penalty
            
        # Boost actions that lead to new states (from history)
        for state in state_history[-10:]:  # Check last 10 states
            if "action" in state and state["action"] and state["action"].get("id") == action.id:
                if state.get("result", {}).get("new_state", False):
                    score *= 1.2  # Boost if action led to new state
                    break
                    
        return score
        
    def _get_action_success_rate(self, action_id: int) -> float:
        """
        Get the success rate for an action.
        
        Args:
            action_id: ID of the action
            
        Returns:
            Success rate (0.0-1.0)
        """
        if action_id not in self.action_success_rates:
            return 0.5  # Default for unknown actions
            
        stats = self.action_success_rates[action_id]
        attempts = stats.get("attempts", 0)
        
        if attempts == 0:
            return 0.5  # Default when no attempts
            
        successes = stats.get("successes", 0)
        return successes / attempts
        
    def _generate_opportunity_rationale(self, opportunity: Dict[str, Any], 
                                      screen: ScreenDescription) -> str:
        """
        Generate a human-readable rationale for an opportunity.
        
        Args:
            opportunity: Opportunity data
            screen: Screen description
            
        Returns:
            Rationale string
        """
        rationale_parts = []
        
        # Add element type information
        element_class = opportunity.get("class", "")
        if element_class:
            rationale_parts.append(f"{element_class}")
            
        # Add monitored method information
        if opportunity.get("directly_reaches_mop", False):
            rationale_parts.append("directly reaches monitored methods")
        elif opportunity.get("reaches_mop", False):
            rationale_parts.append("reaches monitored methods")
            
        # Add context information
        context_type = opportunity.get("context_type", "unknown")
        if context_type != "unknown":
            rationale_parts.append(f"in {context_type} context")
            
        # Add testing status
        if opportunity.get("already_tested", False):
            success_rate = opportunity.get("success_rate", None)
            if success_rate is not None:
                rationale_parts.append(f"previously tested with {success_rate:.0%} success rate")
            else:
                rationale_parts.append("previously tested")
        else:
            rationale_parts.append("not yet tested")
            
        # Generate final rationale
        if not rationale_parts:
            return "No specific rationale"
            
        return ", ".join(rationale_parts)
        
    def mark_action_tested(self, action_id: int, success: bool = True) -> None:
        """
        Mark an action as tested with success information.

        Args:
            action_id: ID of the action
            success: Whether the action executed successfully
        """
        self.tested_actions.add(action_id)
        
        # Update success rate tracking
        if action_id not in self.action_success_rates:
            self.action_success_rates[action_id] = {
                "attempts": 0,
                "successes": 0
            }
            
        self.action_success_rates[action_id]["attempts"] += 1
        if success:
            self.action_success_rates[action_id]["successes"] += 1

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
        
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about opportunity detection.
        
        Returns:
            Dictionary with opportunity detection statistics
        """
        stats = {
            "total_actions_evaluated": self.exploration_stats["total_actions_evaluated"],
            "monitored_method_actions_found": self.exploration_stats["monitored_methods_found"],
            "unique_activities_seen": len(self.exploration_stats["unique_activities_seen"]),
            "context_types_seen": list(self.exploration_stats["context_types_seen"]),
            "tested_actions_count": len(self.tested_actions)
        }
        
        # Calculate success rates
        if self.action_success_rates:
            total_attempts = sum(stats["attempts"] for stats in self.action_success_rates.values())
            total_successes = sum(stats["successes"] for stats in self.action_success_rates.values())
            
            if total_attempts > 0:
                stats["overall_success_rate"] = total_successes / total_attempts
            else:
                stats["overall_success_rate"] = 0.0
        else:
            stats["overall_success_rate"] = 0.0
            
        return stats
