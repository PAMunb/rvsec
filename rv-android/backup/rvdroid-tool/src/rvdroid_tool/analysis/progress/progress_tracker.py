"""
Progress tracker for RVDroid.

This module provides functionality to track testing progress,
measure exploration effectiveness, and detect exploration plateaus.
"""

import time
from typing import Dict, Any, List, Optional, Set, Tuple

from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.parser.screen.visitor.model import ItemAction, ScreenDescription
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class ProgressTracker:
    """
    Tracks testing progress and exploration effectiveness.

    Provides metrics for measuring testing progress, detecting exploration
    plateaus, and identifying areas that need more testing.
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the progress tracker.

        Args:
            static_data: Optional static analysis data
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.analysis.progress_tracker",
            {CONTEXT_COMPONENT: "ProgressTracker"}
        )

        # Store static data
        self.static_data = static_data

        # Initialize tracking data
        self.start_time = time.time()
        self.seen_activities: Set[str] = set()
        self.seen_states: Set[str] = set()
        self.seen_elements: Set[str] = set()
        self.executed_actions: Dict[int, int] = {}  # Action ID -> execution count
        self.activity_visit_count: Dict[str, int] = {}
        self.state_visit_times: Dict[str, List[float]] = {}
        self.state_duration: Dict[str, float] = {}
        self.current_state: Optional[str] = None
        self.current_state_start_time: float = 0

        # Monitored method coverage tracking
        self.monitored_methods_reached: Set[str] = set()  # Method signatures
        self.crypto_methods_reached: Set[str] = set()     # Crypto specification methods
        self.general_api_methods_reached: Set[str] = set() # General API specification methods
        self.total_monitored_methods = 0
        self.total_crypto_methods = 0
        self.total_general_api_methods = 0

        # Initialize method counts from static analysis if available
        if static_data:
            self._initialize_method_counts()

        # Exploration metrics
        self.last_new_state_time = time.time()
        self.exploration_plateaus: List[Dict[str, Any]] = []
        self.coverage_snapshots: List[Dict[str, Any]] = []

        self.logger.info("Initialized progress tracker")

    def update_progress(self, screen: ScreenDescription, state_fingerprint: str,
                        executed_action: Optional[ItemAction] = None) -> Dict[str, Any]:
        """
        Update progress tracking with the current state.

        Args:
            screen: Parsed screen description
            state_fingerprint: Unique fingerprint for the current state
            executed_action: Optional action that was just executed

        Returns:
            Dictionary with progress metrics
        """
        current_time = time.time()
        activity_name = screen.activity

        # Update state duration tracking
        if self.current_state:
            state_duration = current_time - self.current_state_start_time
            self.state_duration[self.current_state] = self.state_duration.get(self.current_state, 0) + state_duration

        # Update current state tracking
        self.current_state = state_fingerprint
        self.current_state_start_time = current_time

        # Track executed action
        if executed_action:
            action_id = executed_action.id
            self.executed_actions[action_id] = self.executed_actions.get(action_id, 0) + 1
            
            # Track monitored method hits
            if hasattr(executed_action, 'reaches_mop') and executed_action.reaches_mop:
                method_signature = None
                if hasattr(executed_action, 'target_method'):
                    method_signature = executed_action.target_method
                
                if method_signature:
                    self.monitored_methods_reached.add(method_signature)
                    
                    # Try to categorize based on method signature
                    if self._is_crypto_method(method_signature):
                        self.crypto_methods_reached.add(method_signature)
                    elif self._is_general_api_method(method_signature):
                        self.general_api_methods_reached.add(method_signature)

        # Track state visits
        if state_fingerprint not in self.state_visit_times:
            self.state_visit_times[state_fingerprint] = []
        self.state_visit_times[state_fingerprint].append(current_time)

        # Track activity visits
        self.activity_visit_count[activity_name] = self.activity_visit_count.get(activity_name, 0) + 1

        # Check for new state or activity discovery
        new_state = state_fingerprint not in self.seen_states
        new_activity = activity_name not in self.seen_activities

        # Update seen sets
        if new_state:
            self.seen_states.add(state_fingerprint)
            self.last_new_state_time = current_time

        if new_activity:
            self.seen_activities.add(activity_name)

        # Track UI elements
        for item in screen.items:
            element_id = item.view.get("resource_id", "")
            if element_id:
                self.seen_elements.add(element_id)

        # Check for exploration plateau
        plateau_detected = self._check_for_plateau(current_time)

        # Take periodic coverage snapshot
        if len(self.coverage_snapshots) == 0 or (current_time - self.coverage_snapshots[-1]["timestamp"]) > 60:
            self._take_coverage_snapshot(current_time)

        # Generate progress metrics
        metrics = self._calculate_metrics(current_time)
        metrics.update({
            "new_state": new_state,
            "new_activity": new_activity,
            "plateau_detected": plateau_detected
        })

        return metrics

    def _check_for_plateau(self, current_time: float) -> bool:
        """
        Check if the exploration has reached a plateau.

        Args:
            current_time: Current timestamp

        Returns:
            True if a plateau is detected, False otherwise
        """
        # Check time since last new state
        time_since_new_state = current_time - self.last_new_state_time

        # Define plateau threshold (5 minutes without new states)
        plateau_threshold = 300  # seconds

        if time_since_new_state > plateau_threshold:
            # Check if we already recorded this plateau
            if not self.exploration_plateaus or self.exploration_plateaus[-1]["end_time"] < self.last_new_state_time:
                # Record new plateau
                plateau = {
                    "start_time": self.last_new_state_time,
                    "end_time": current_time,
                    "duration": time_since_new_state,
                    "states_before": len(self.seen_states),
                    "activities_before": len(self.seen_activities)
                }
                self.exploration_plateaus.append(plateau)

                self.logger.warning(
                    f"Exploration plateau detected: {time_since_new_state:.1f} seconds with no new states")
                return True

        return False

    def _take_coverage_snapshot(self, current_time: float) -> None:
        """
        Take a snapshot of the current coverage metrics.

        Args:
            current_time: Current timestamp
        """
        metrics = self._calculate_metrics(current_time)

        snapshot = {
            "timestamp": current_time,
            "elapsed_time": current_time - self.start_time,
            "states_count": len(self.seen_states),
            "activities_count": len(self.seen_activities),
            "elements_count": len(self.seen_elements),
            "actions_count": sum(self.executed_actions.values()),
            "unique_actions_count": len(self.executed_actions),
            "activity_coverage": metrics["activity_coverage"],
            "state_change_rate": metrics["state_change_rate"]
        }

        self.coverage_snapshots.append(snapshot)

    def _calculate_metrics(self, current_time: float) -> Dict[str, Any]:
        """
        Calculate progress metrics.

        Args:
            current_time: Current timestamp

        Returns:
            Dictionary with metrics
        """
        elapsed_time = current_time - self.start_time

        # Calculate activity coverage if static data is available
        activity_coverage = 0.0
        total_activities = 0
        if self.static_data and self.static_data.classes:
            app_activities = [c for c in self.static_data.classes.classes.values() if c.is_activity]
            total_activities = len(app_activities)
            if total_activities > 0:
                covered_activities = sum(1 for a in app_activities if a.name in self.seen_activities)
                activity_coverage = (covered_activities / total_activities) * 100

        # Calculate state change rate (states per minute)
        state_change_rate = len(self.seen_states) / (elapsed_time / 60) if elapsed_time > 0 else 0

        # Calculate redundancy ratio (repeated actions / total actions)
        total_actions = sum(self.executed_actions.values())
        redundant_actions = total_actions - len(self.executed_actions)
        redundancy_ratio = redundant_actions / total_actions if total_actions > 0 else 0

        return {
            "elapsed_time": elapsed_time,
            "states_count": len(self.seen_states),
            "activities_count": len(self.seen_activities),
            "unique_elements_count": len(self.seen_elements),
            "actions_count": total_actions,
            "unique_actions_count": len(self.executed_actions),
            "activity_coverage": activity_coverage,
            "total_activities": total_activities,
            "state_change_rate": state_change_rate,
            "redundancy_ratio": redundancy_ratio,
            "plateaus_count": len(self.exploration_plateaus)
        }

    def _initialize_method_counts(self) -> None:
        """
        Initialize monitored method counts from static analysis data.
        """
        if not self.static_data or not self.static_data.classes:
            return
            
        # Look for a static analyzer in the context
        static_analyzer = None
        if hasattr(self, 'context') and hasattr(self.context, 'static_analyzer'):
            static_analyzer = self.context.static_analyzer
        
        # Use enhanced static analyzer if available
        if static_analyzer and hasattr(static_analyzer, 'get_monitored_methods'):
            # Get counts by specification type
            all_methods = static_analyzer.get_monitored_methods()
            crypto_methods = static_analyzer.get_monitored_methods("crypto")
            general_api_methods = static_analyzer.get_monitored_methods("general_api")
            
            self.total_monitored_methods = len(all_methods)
            self.total_crypto_methods = len(crypto_methods)
            self.total_general_api_methods = len(general_api_methods)
        else:
            # Fallback to manual counting
            monitored_methods = 0
            crypto_methods = 0
            general_api_methods = 0
            
            for clazz in self.static_data.classes.get_classes():
                for method in clazz.methods:
                    if method.reaches_mop or method.directly_reaches_mop:
                        monitored_methods += 1
                        
                        # Use simple classification
                        if self._is_crypto_method(method.signature):
                            crypto_methods += 1
                        elif self._is_general_api_method(method.signature):
                            general_api_methods += 1
                            
            self.total_monitored_methods = monitored_methods
            self.total_crypto_methods = crypto_methods
            self.total_general_api_methods = general_api_methods
            
        self.logger.info(f"Initialized method counts: {self.total_monitored_methods} total monitored methods, "
                       f"{self.total_crypto_methods} crypto methods, {self.total_general_api_methods} general API methods")
    
    def _is_crypto_method(self, method_signature: str) -> bool:
        """
        Check if a method is related to cryptography.
        
        Args:
            method_signature: Method signature
            
        Returns:
            True if the method is crypto-related, False otherwise
        """
        crypto_keywords = {"cipher", "encrypt", "decrypt", "key", "mac", "hash", "digest", 
                          "random", "secure", "sign", "verify", "certificate"}
        
        method_lower = method_signature.lower()
        return any(kw in method_lower for kw in crypto_keywords)
    
    def _is_general_api_method(self, method_signature: str) -> bool:
        """
        Check if a method is related to general API usage.
        
        Args:
            method_signature: Method signature
            
        Returns:
            True if the method is general API-related, False otherwise
        """
        general_api_keywords = {"iterator", "next", "hasnext", "collection", "map", "list", 
                              "compare", "equals", "hashcode", "clone", "close"}
        
        method_lower = method_signature.lower()
        return any(kw in method_lower for kw in general_api_keywords)
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the testing progress.

        Returns:
            Dictionary with progress summary
        """
        current_time = time.time()
        metrics = self._calculate_metrics(current_time)

        # Calculate testing efficiency
        actions_per_state = metrics["actions_count"] / metrics["states_count"] if metrics["states_count"] > 0 else 0
        states_per_hour = (metrics["states_count"] / metrics["elapsed_time"]) * 3600 if metrics[
                                                                                            "elapsed_time"] > 0 else 0

        # Format time for display
        elapsed_hours = int(metrics["elapsed_time"] // 3600)
        elapsed_minutes = int((metrics["elapsed_time"] % 3600) // 60)
        elapsed_seconds = int(metrics["elapsed_time"] % 60)
        elapsed_str = f"{elapsed_hours}h {elapsed_minutes}m {elapsed_seconds}s"
        
        # Calculate specification coverage percentages
        monitored_methods_coverage = 0.0
        crypto_methods_coverage = 0.0
        general_api_methods_coverage = 0.0
        
        if self.total_monitored_methods > 0:
            monitored_methods_coverage = (len(self.monitored_methods_reached) / self.total_monitored_methods) * 100
            
        if self.total_crypto_methods > 0:
            crypto_methods_coverage = (len(self.crypto_methods_reached) / self.total_crypto_methods) * 100
            
        if self.total_general_api_methods > 0:
            general_api_methods_coverage = (len(self.general_api_methods_reached) / self.total_general_api_methods) * 100

        return {
            "elapsed_time": elapsed_str,
            "states_explored": metrics["states_count"],
            "activities_covered": metrics["activities_count"],
            "activity_coverage_percent": f"{metrics['activity_coverage']:.1f}%",
            "actions_executed": metrics["actions_count"],
            "unique_actions": metrics["unique_actions_count"],
            "actions_per_state": f"{actions_per_state:.1f}",
            "states_per_hour": f"{states_per_hour:.1f}",
            "redundancy_ratio": f"{metrics['redundancy_ratio'] * 100:.1f}%",
            "exploration_plateaus": len(self.exploration_plateaus),
            "monitored_methods": {
                "total": self.total_monitored_methods,
                "reached": len(self.monitored_methods_reached),
                "coverage_percent": f"{monitored_methods_coverage:.1f}%"
            },
            "crypto_methods": {
                "total": self.total_crypto_methods,
                "reached": len(self.crypto_methods_reached),
                "coverage_percent": f"{crypto_methods_coverage:.1f}%"
            },
            "general_api_methods": {
                "total": self.total_general_api_methods,
                "reached": len(self.general_api_methods_reached),
                "coverage_percent": f"{general_api_methods_coverage:.1f}%"
            }
        }
