# rvandroid/rvdroid/core/state_manager.py

"""
State management for RVDroid.

This module provides components for managing application state,
including state tracking, transition detection, and state comparison.
"""

import time
from typing import Dict, Any, Optional, List, Set

from rvandroid.parser.screen.visitor.model import ScreenDescription
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.util.error.decorators import handle_error
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.rvdroid.core.component import Component


class StateManager(Component):
    """
    Manager for application state in RVDroid.
    
    ### Architectural Decisions:
    - Implements a centralized state management system
    - Provides state tracking, comparison, and fingerprinting
    - Enables detection of state transitions and loops
    - Supports state persistence and serialization
    - Integrates with the component-based architecture for lifecycle management
    
    ### Role in the System:
    - Maintains representation of current application state
    - Detects and analyzes state transitions
    - Identifies new and repeated states
    - Provides state-related metrics and insights
    - Facilitates state-based decision making for testing strategies
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the state manager.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__("StateManager", config)
        
        # Static data from config
        self.static_data = config.get("static_data") if config else None
        
        # Current state information
        self.current_state: Optional[Dict[str, Any]] = None
        self.current_screen: Optional[ScreenDescription] = None
        self.previous_state: Optional[Dict[str, Any]] = None
        
        # State history tracking
        self.state_history: List[Dict[str, Any]] = []
        self.visited_states: Set[str] = set()
        self.state_visit_counts: Dict[str, int] = {}
        
        # State transition tracking
        self.state_transitions: Dict[str, Dict[str, int]] = {}
        self.last_state_change_time = 0
        
        # Screen capture tracking
        self.last_screenshot_path: Optional[str] = None
        
    @handle_error(level="ERROR")
    def initialize(self) -> bool:
        """
        Initialize the state manager.
        
        Returns:
            True if initialization succeeded, False otherwise
        """
        self.logger.info("Initializing state manager")
        
        # Clear any existing state
        self.current_state = None
        self.current_screen = None
        self.previous_state = None
        self.state_history = []
        self.visited_states = set()
        self.state_visit_counts = {}
        self.state_transitions = {}
        
        self.initialized = True
        return True
        
    @handle_error(level="ERROR")
    def start(self) -> bool:
        """
        Start the state manager.
        
        Returns:
            True if start succeeded, False otherwise
        """
        if not self.initialized:
            self.logger.error("Cannot start: state manager not initialized")
            return False
            
        self.logger.info("Starting state manager")
        
        self.running = True
        return True
        
    @handle_error(level="ERROR")
    def stop(self) -> bool:
        """
        Stop the state manager.
        
        Returns:
            True if stop succeeded, False otherwise
        """
        if not self.running:
            self.logger.warning("State manager is not running")
            return True
            
        self.logger.info("Stopping state manager")
        
        self.running = False
        return True
        
    @handle_error(level="ERROR")
    def cleanup(self) -> None:
        """
        Clean up state manager resources.
        """
        self.logger.info("Cleaning up state manager")
        
        # Clear state data
        self.current_state = None
        self.current_screen = None
        self.previous_state = None
        self.state_history = []
        self.visited_states = set()
        self.state_visit_counts = {}
        self.state_transitions = {}
        
        self.initialized = False
        self.running = False
        
    @handle_error(level="WARN")
    def update_state(self, screen: ScreenDescription, raw_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update current state information based on screen and raw state data.
        
        Args:
            screen: Parsed screen description
            raw_state: Raw state data from UI adapter
            
        Returns:
            Dictionary with state update information
        """
        if not self.running:
            self.logger.warning("State manager is not running")
            return {"success": False, "error": "State manager not running"}
            
        # Save previous state
        self.previous_state = self.current_state
        
        # Extract key state information
        current_time = time.time()
        fingerprint = raw_state.get("fingerprint", self._generate_state_fingerprint(screen, raw_state))
        activity = raw_state.get("activity", "unknown")
        package_name = raw_state.get("package_name", "unknown")
        
        # Create new state object
        self.current_state = {
            "fingerprint": fingerprint,
            "activity": activity,
            "package_name": package_name,
            "timestamp": current_time,
            "interactive_elements_count": len(screen.items),
            "screenshot_path": raw_state.get("screenshot_path"),
            "is_new_state": False  # Will be updated below
        }
        
        # Set current screen
        self.current_screen = screen
        
        # Update screenshot reference
        self.last_screenshot_path = raw_state.get("screenshot_path")
        
        # Check if this is a new state
        is_new_state = fingerprint not in self.visited_states
        self.current_state["is_new_state"] = is_new_state
        
        if is_new_state:
            # Add to visited states
            self.visited_states.add(fingerprint)
            self.state_visit_counts[fingerprint] = 1
            
            # Record state change time
            self.last_state_change_time = current_time
            
            self.logger.info(f"New state detected: {fingerprint} (Activity: {activity})")
        else:
            # Increment visit count
            self.state_visit_counts[fingerprint] = self.state_visit_counts.get(fingerprint, 0) + 1
            self.logger.debug(f"Revisited state: {fingerprint} (Count: {self.state_visit_counts[fingerprint]})")
            
        # Update state history
        self.state_history.append(self.current_state)
        
        # Limit history size to avoid memory issues
        max_history = 100
        if len(self.state_history) > max_history:
            self.state_history = self.state_history[-max_history:]
            
        # Update state transitions
        if self.previous_state:
            prev_fingerprint = self.previous_state.get("fingerprint")
            if prev_fingerprint:
                if prev_fingerprint not in self.state_transitions:
                    self.state_transitions[prev_fingerprint] = {}
                    
                transitions = self.state_transitions[prev_fingerprint]
                transitions[fingerprint] = transitions.get(fingerprint, 0) + 1
                
        # Return information about the state update
        return {
            "success": True,
            "is_new_state": is_new_state,
            "fingerprint": fingerprint,
            "activity": activity,
            "previous_fingerprint": self.previous_state.get("fingerprint") if self.previous_state else None,
            "state_visits": self.state_visit_counts.get(fingerprint, 1)
        }
        
    def get_current_state(self) -> Optional[Dict[str, Any]]:
        """
        Get the current application state.
        
        Returns:
            Current state dictionary or None if not available
        """
        return self.current_state
        
    def get_current_screen(self) -> Optional[ScreenDescription]:
        """
        Get the current screen description.
        
        Returns:
            Current screen description or None if not available
        """
        return self.current_screen
        
    def get_state_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent state history.
        
        Args:
            limit: Maximum number of states to return
            
        Returns:
            List of recent states
        """
        return self.state_history[-limit:] if self.state_history else []
        
    def get_state_visit_counts(self) -> Dict[str, int]:
        """
        Get counts of state visits.
        
        Returns:
            Dictionary mapping state fingerprints to visit counts
        """
        return self.state_visit_counts
        
    def is_state_transition(self, from_state: str, to_state: str) -> bool:
        """
        Check if a transition between states exists in the observed history.
        
        Args:
            from_state: Source state fingerprint
            to_state: Target state fingerprint
            
        Returns:
            True if transition exists, False otherwise
        """
        return from_state in self.state_transitions and to_state in self.state_transitions[from_state]
        
    def get_state_transitions(self) -> Dict[str, Dict[str, int]]:
        """
        Get all observed state transitions.
        
        Returns:
            Dictionary of state transitions and counts
        """
        return self.state_transitions
        
    def get_state_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about application state.
        
        Returns:
            Dictionary with state statistics
        """
        unique_states = len(self.visited_states)
        unique_activities = len(set(state.get("activity", "") 
                                 for state in self.state_history 
                                 if state.get("activity")))
        
        most_visited = ""
        most_visited_count = 0
        
        for state, count in self.state_visit_counts.items():
            if count > most_visited_count:
                most_visited = state
                most_visited_count = count
                
        return {
            "unique_states": unique_states,
            "unique_activities": unique_activities,
            "total_transitions": sum(sum(transitions.values()) 
                                    for transitions in self.state_transitions.values()),
            "most_visited_state": most_visited,
            "most_visited_count": most_visited_count,
            "current_state": self.current_state.get("fingerprint") if self.current_state else None,
            "current_activity": self.current_state.get("activity") if self.current_state else None
        }
        
    def detect_cycle(self, length: int = 3) -> bool:
        """
        Detect cycles in recent state history.
        
        Args:
            length: Length of cycle to detect
            
        Returns:
            True if cycle detected, False otherwise
        """
        if len(self.state_history) < length * 2:
            return False
            
        # Get fingerprints from recent states
        recent = [state.get("fingerprint") for state in self.state_history]
        
        # Check for repeating pattern of the specified length
        if recent[-length:] == recent[-2*length:-length]:
            return True
            
        return False
        
    def detect_repeating_activity(self, threshold: int = 5) -> Optional[str]:
        """
        Detect if we're stuck in the same activity.
        
        Args:
            threshold: Number of consecutive visits to consider "stuck"
            
        Returns:
            Activity name if stuck, None otherwise
        """
        if len(self.state_history) < threshold:
            return None
            
        # Get activities from recent states
        recent = [state.get("activity") for state in self.state_history[-threshold:]]
        
        # Check if all recent states have the same activity
        if len(set(recent)) == 1:
            return recent[0]
            
        return None
        
    def estimate_exploration_progress(self) -> Dict[str, Any]:
        """
        Estimate exploration progress based on state transitions.
        
        Returns:
            Dictionary with progress metrics
        """
        # Count total possible transitions (n² where n is number of states)
        unique_states = len(self.visited_states)
        if unique_states <= 1:
            return {
                "progress": 0.0,
                "explored_transitions": 0,
                "total_possible_transitions": 0,
                "transitions_per_state": 0.0
            }
            
        total_possible = unique_states * unique_states
        
        # Count actual explored transitions
        explored_transitions = sum(len(transitions) for transitions in self.state_transitions.values())
        
        # Calculate progress percentage (explored / possible)
        progress = explored_transitions / total_possible
        
        # Calculate average transitions per state
        transitions_per_state = explored_transitions / unique_states
        
        return {
            "progress": progress,
            "explored_transitions": explored_transitions,
            "total_possible_transitions": total_possible,
            "transitions_per_state": transitions_per_state
        }
        
    def _generate_state_fingerprint(self, screen: ScreenDescription, 
                                  state_data: Dict[str, Any]) -> str:
        """
        Generate a unique fingerprint for a state.
        
        Args:
            screen: Parsed screen description
            state_data: Raw state data
            
        Returns:
            State fingerprint string
        """
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
        
        return fingerprint