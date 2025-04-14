# rvandroid/rvdroid/memory/manager.py

"""
Memory manager module for RVDroid.

This module provides a centralized memory management system that coordinates
short-term and long-term memory operations while interfacing with other system components.
"""

from typing import Dict, Any, List, Optional, Set, Tuple

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription, ItemAction
from rvandroid.rvdroid.core.component import Component
from rvandroid.rvdroid.memory.action.memory_action import MemoryAction
from rvandroid.rvdroid.memory.long_term.long_term_memory import LongTermMemory
from rvandroid.rvdroid.memory.short_term.short_term_memory import ShortTermMemory
from rvandroid.rvdroid.memory.state.memory_state import MemoryState
from rvandroid.rvdroid.memory.state.state_fingerprinter import StateFingerprinter
from rvandroid.rvdroid.memory.patterns.pattern_recognition import PatternRecognition
from rvandroid.rvdroid.memory.exploration.exploration_optimizer import ExplorationOptimizer


class MemoryManager(Component):
    """
    Central memory management system for RVDroid.
    
    ### Architectural Decisions:
    - Implements Component interface for standardized lifecycle management
    - Coordinates information flow between short-term and long-term memory
    - Separates concerns between working memory and persistent memory
    - Provides high-level memory operations while abstracting storage details
    - Integrates with pattern recognition and exploration optimization
    
    ### Role in the System:
    - Serves as the central point for all memory operations
    - Maintains the application state history and transitions
    - Provides access to past actions and their outcomes
    - Enables memory-based exploration optimization
    - Facilitates detection of UI patterns and recurring behaviors
    """
    
    def __init__(self, 
                 config: Optional[Dict[str, Any]] = None,
                 app_package: Optional[str] = None,
                 static_data: Optional[StaticAnalysisData] = None,
                 short_term_capacity: int = 50):
        """
        Initialize the memory manager.
        
        Args:
            config: Optional configuration dictionary
            app_package: Optional application package name
            static_data: Optional static analysis data
            short_term_capacity: Maximum capacity of short-term memory
        """
        super().__init__("MemoryManager", config)
        
        # Set properties 
        self.app_package = app_package
        self.static_data = static_data
        self.short_term_capacity = short_term_capacity
        
        # Memory components - initialized in initialize()
        self.short_term_memory = None
        self.long_term_memory = None
        self.fingerprinter = None
        self.pattern_recognition = None
        self.exploration_optimizer = None
        
        # State tracking
        self.last_state_fingerprint = None
        self.last_action = None
        
        # Action statistics
        self.action_statistics = {}
        
        # Discovered states
        self.discovered_states = set()
        
    def initialize(self) -> bool:
        """
        Initialize memory subsystems.
        
        Returns:
            True if initialization is successful, False otherwise
        """
        self.logger.info("Initializing memory manager")
        
        try:
            # Initialize state fingerprinter
            self.fingerprinter = StateFingerprinter()
            
            # Initialize memory components
            self.short_term_memory = ShortTermMemory(capacity=self.short_term_capacity)
            self.long_term_memory = LongTermMemory(
                app_package=self.app_package, 
                static_data=self.static_data
            )
            
            # Initialize pattern recognition and exploration optimizer
            self.pattern_recognition = PatternRecognition(
                short_term_memory=self.short_term_memory,
                long_term_memory=self.long_term_memory
            )
            
            self.exploration_optimizer = ExplorationOptimizer(
                short_term_memory=self.short_term_memory,
                long_term_memory=self.long_term_memory,
                pattern_recognition=self.pattern_recognition,
                static_data=self.static_data
            )
            
            self.initialized = True
            self.logger.info("Memory manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing memory manager: {e}")
            return False
            
    def start(self) -> bool:
        """
        Start the memory manager.
        
        Returns:
            True if start is successful, False otherwise
        """
        if not self.initialized:
            self.logger.error("Cannot start memory manager: not initialized")
            return False
            
        self.logger.info("Starting memory manager")
        
        # Reset state tracking
        self.last_state_fingerprint = None
        self.last_action = None
        self.discovered_states = set()
        
        self.running = True
        return True
        
    def stop(self) -> bool:
        """
        Stop the memory manager.
        
        Returns:
            True if stop is successful, False otherwise
        """
        if not self.running:
            self.logger.warning("Memory manager is not running")
            return True
            
        self.logger.info("Stopping memory manager")
        
        # Perform final analysis if needed
        self._perform_final_analysis()
        
        self.running = False
        return True
        
    def cleanup(self) -> None:
        """
        Clean up memory resources.
        """
        self.logger.info("Cleaning up memory manager")
        
        # Clean up components
        if self.short_term_memory:
            self.logger.debug("Clearing short-term memory")
            self.short_term_memory.clear()
            
        if self.long_term_memory:
            self.logger.debug("Finalizing long-term memory")
            # This doesn't clear the memory but performs any finalization steps
            
        # Reset state
        self.last_state_fingerprint = None
        self.last_action = None
        self.discovered_states = set()
        
        self.initialized = False
        self.running = False
        
    def process_state(self, screen: ScreenDescription,
                      state_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an application state.
        
        Args:
            screen: Parsed screen description
            state_data: Raw state data
            
        Returns:
            Processed state information including fingerprint and analysis
        """
        if not self.running:
            self.logger.warning("Memory manager is not running")
            return {"error": "Memory manager is not running"}
            
        try:
            # Generate state fingerprint
            fingerprint = self.fingerprinter.generate_fingerprint(screen, state_data)
            
            # Determine if this is a new state
            is_new_state = fingerprint not in self.discovered_states
            if is_new_state:
                self.discovered_states.add(fingerprint)
                
            # Update the state data with fingerprint
            state_data["fingerprint"] = fingerprint
            
            # Create memory state object
            memory_state = MemoryState(
                fingerprint=fingerprint,
                activity=state_data.get("activity", "unknown")
            )
            
            # Set additional properties
            memory_state.interactive_elements_count = len(screen.items)
            memory_state.set_screenshot(state_data.get("screenshot_path"))
            
            # Record state in memory systems
            self.short_term_memory.record_state(memory_state)
            self.long_term_memory.record_state(memory_state, is_new_state)
            
            # Record transition if this is a new state and we have a previous action
            if self.last_state_fingerprint and self.last_action:
                self._record_transition(self.last_state_fingerprint, fingerprint, self.last_action)
                
            # Update last state tracking
            self.last_state_fingerprint = fingerprint
            
            # Create result
            result = {
                "fingerprint": fingerprint,
                "is_new_state": is_new_state,
                "memory_state": memory_state
            }
            
            # Scan for patterns if we have enough history
            if len(self.short_term_memory.state_history) > 5:
                result["patterns"] = self._analyze_patterns()
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing state: {e}")
            return {"error": f"Error processing state: {e}"}
            
    def process_action(self, action: ItemAction, success: bool) -> Dict[str, Any]:
        """
        Process an executed action.
        
        Args:
            action: Action that was executed
            success: Whether the action was successful
            
        Returns:
            Processed action information
        """
        if not self.running:
            self.logger.warning("Memory manager is not running")
            return {"error": "Memory manager is not running"}
            
        try:
            # Create memory action
            memory_action = MemoryAction.from_item_action(action)
            
            # Record in memory systems
            self.short_term_memory.record_action(memory_action, success)
            
            if self.last_state_fingerprint:
                self.long_term_memory.record_action(memory_action, self.last_state_fingerprint, success)
                
            # Record for exploration optimizer
            self.exploration_optimizer.record_action_result(action, {"success": success})
            
            # Update last action tracking
            self.last_action = memory_action
            
            # Update action statistics
            action_id = action.id
            if action_id not in self.action_statistics:
                self.action_statistics[action_id] = {
                    "execution_count": 0,
                    "success_count": 0,
                    "led_to_new_state": 0
                }
                
            stats = self.action_statistics[action_id]
            stats["execution_count"] += 1
            if success:
                stats["success_count"] += 1
                
            # Create result
            result = {
                "action_id": action.id,
                "success": success,
                "memory_action": memory_action
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing action: {e}")
            return {"error": f"Error processing action: {e}"}
            
    def optimize_actions(self, screen: ScreenDescription,
                        state_data: Dict[str, Any],
                        available_actions: List[ItemAction]) -> List[ItemAction]:
        """
        Optimize the order of actions based on memory-guided exploration.
        
        Args:
            screen: Parsed screen description
            state_data: State data dictionary
            available_actions: List of available actions
            
        Returns:
            Re-prioritized list of actions
        """
        if not self.running or not available_actions:
            return available_actions
            
        try:
            # Ensure state_data is a dictionary (not None)
            safe_state_data = state_data if isinstance(state_data, dict) else {}
            
            # Extract current activity with safety check
            current_activity = safe_state_data.get("activity", "unknown")
            self.logger.debug(f"Optimizing actions for activity: {current_activity}")
            
            # Create a copy of actions to avoid modifying the original list
            optimized_actions = list(available_actions)
            
            # Get visited activities from long term memory
            visited_activities = set()
            try:
                visited_activities = {info.get("activity", "unknown")
                                     for info in self.long_term_memory.activities.values()}
            except Exception as e:
                self.logger.error(f"Error retrieving activities: {e}")
                
            # If we've visited more than one activity, prioritize navigation actions
            if len(visited_activities) > 1:
                navigation_candidates = []
                other_actions = []
                
                for action in optimized_actions:
                    # Determine if this action might be a navigation action
                    is_navigation = self._is_navigation_action(action)
                    
                    # Add to appropriate list
                    if is_navigation:
                        navigation_candidates.append(action)
                    else:
                        other_actions.append(action)
                        
                # If we found navigation candidates, prioritize them
                if navigation_candidates:
                    self.logger.info(f"Prioritizing {len(navigation_candidates)} navigation candidates")
                    return navigation_candidates + other_actions
                    
            # Use exploration optimizer for general case
            return self.exploration_optimizer.optimize_action_selection(
                screen, safe_state_data, optimized_actions
            )
            
        except Exception as e:
            self.logger.error(f"Error optimizing actions: {e}")
            return available_actions
            
    def get_state_summary(self, fingerprint: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a summary of a state.
        
        Args:
            fingerprint: State fingerprint or None for current state
            
        Returns:
            State summary information
        """
        # Use last state fingerprint if none provided
        if fingerprint is None:
            fingerprint = self.last_state_fingerprint
            
        if not fingerprint:
            return {"error": "No state available"}
            
        # Try to get state from memory
        state = self._get_state_from_memory(fingerprint)
        
        if not state:
            return {"error": f"State not found: {fingerprint}"}
            
        # Create result
        return {
            "fingerprint": state.fingerprint,
            "activity": state.activity,
            "visit_count": state.visit_count,
            "first_visit": state.first_visit,
            "last_visit": state.last_visit,
            "action_count": len(state.all_actions),
            "successful_actions": list(state.successful_actions),
            "outgoing_transitions": state.outgoing_transitions,
            "screenshot_path": state.screenshot_path
        }
        
    def get_action_summary(self, action_id: int) -> Dict[str, Any]:
        """
        Get a summary of an action.
        
        Args:
            action_id: Action ID
            
        Returns:
            Action summary information
        """
        # Try to get action from memory
        action = self._get_action_from_memory(action_id)
        
        if not action:
            return {"error": f"Action not found: {action_id}"}
            
        # Create result
        return {
            "id": action.id,
            "text": action.text,
            "type": action.type,
            "execution_count": action.execution_count,
            "success_count": action.success_count,
            "success_rate": action.get_success_rate(),
            "reaches_monitored_operation": action.reaches_mop,
            "element_properties": action.element_properties
        }
        
    def get_memory_statistics(self) -> Dict[str, Any]:
        """
        Get memory system statistics.
        
        Returns:
            Dictionary with memory statistics
        """
        return {
            "short_term": self.short_term_memory.get_memory_stats(),
            "long_term": self.long_term_memory.get_memory_stats(),
            "discovered_states": len(self.discovered_states),
            "actions_executed": sum(stats["execution_count"] for stats in self.action_statistics.values())
        }
        
    def save_memory(self, file_path: str) -> bool:
        """
        Save long-term memory to disk.
        
        Args:
            file_path: Path to save the memory
            
        Returns:
            True if successful, False otherwise
        """
        if not self.initialized:
            self.logger.error("Cannot save memory: not initialized")
            return False
            
        try:
            return self.long_term_memory.save(file_path)
        except Exception as e:
            self.logger.error(f"Error saving memory: {e}")
            return False
            
    def load_memory(self, file_path: str) -> bool:
        """
        Load long-term memory from disk.
        
        Args:
            file_path: Path to load the memory from
            
        Returns:
            True if successful, False otherwise
        """
        if not self.initialized:
            self.logger.error("Cannot load memory: not initialized")
            return False
            
        try:
            success = self.long_term_memory.load(file_path)
            if success:
                # Update discovered states
                self.discovered_states = set(self.long_term_memory.states.keys())
            return success
        except Exception as e:
            self.logger.error(f"Error loading memory: {e}")
            return False
            
    def _record_transition(self, from_state: str, to_state: str, action: MemoryAction) -> None:
        """
        Record a state transition in memory systems.
        
        Args:
            from_state: Source state fingerprint
            to_state: Destination state fingerprint
            action: Action that caused the transition
        """
        # Record in short-term memory
        self.short_term_memory.record_transition(from_state, to_state, action, True)
        
        # Record in long-term memory
        self.long_term_memory.record_transition(from_state, to_state, action, True)
        
        # Update action statistics
        if action.id in self.action_statistics:
            self.action_statistics[action.id]["led_to_new_state"] += 1
            
    def _analyze_patterns(self) -> Dict[str, Any]:
        """
        Analyze patterns in short-term memory.
        
        Returns:
            Dictionary with pattern analysis results
        """
        action_patterns = self.pattern_recognition.analyze_action_sequences()
        state_patterns = self.pattern_recognition.analyze_state_transitions()
        
        return {
            "action_patterns": [p.to_dict() for p in action_patterns],
            "state_patterns": [p.to_dict() for p in state_patterns],
            "action_pattern_count": len(action_patterns),
            "state_pattern_count": len(state_patterns)
        }
        
    def _get_state_from_memory(self, fingerprint: str) -> Optional[MemoryState]:
        """
        Retrieve a state from memory systems.
        
        Args:
            fingerprint: State fingerprint
            
        Returns:
            Memory state or None if not found
        """
        # Try short-term memory first
        state = None
        for s in self.short_term_memory.states.values():
            if s.fingerprint == fingerprint:
                state = s
                break
                
        # If not found, try long-term memory
        if not state and self.long_term_memory:
            state = self.long_term_memory.get_state_by_fingerprint(fingerprint)
            
        return state
        
    def _get_action_from_memory(self, action_id: int) -> Optional[MemoryAction]:
        """
        Retrieve an action from memory systems.
        
        Args:
            action_id: Action ID
            
        Returns:
            Memory action or None if not found
        """
        # Try short-term memory first
        action = None
        if action_id in self.short_term_memory.actions:
            action = self.short_term_memory.actions[action_id]
            
        # If not found, try long-term memory
        if not action and self.long_term_memory and action_id in self.long_term_memory.actions:
            action = self.long_term_memory.actions[action_id]
            
        return action
        
    def _is_navigation_action(self, action: ItemAction) -> bool:
        """
        Determine if an action is likely to be a navigation action.
        
        Args:
            action: The action to analyze
            
        Returns:
            True if the action is likely a navigation action, False otherwise
        """
        # Check if this action has led to transitions before
        if hasattr(self.long_term_memory, 'actions') and action.id in self.long_term_memory.actions:
            try:
                action_obj = self.long_term_memory.actions[action.id]
                
                # Check if this action has transitions to different activities
                if hasattr(action_obj, 'state_transitions'):
                    for from_state, transitions in action_obj.state_transitions.items():
                        for to_state in transitions:
                            # Get state objects
                            from_state_obj = self.long_term_memory.get_state_by_fingerprint(from_state)
                            to_state_obj = self.long_term_memory.get_state_by_fingerprint(to_state)
                            
                            # Check if transition crosses activity boundaries
                            if (from_state_obj and to_state_obj and
                                    from_state_obj.activity != to_state_obj.activity):
                                return True
            except Exception as e:
                self.logger.error(f"Error checking state transitions: {e}")
                
        # Also check if it's a button with text (likely navigation)
        if hasattr(action, 'target_view') and action.target_view:
            class_name = action.target_view.get("class", "")
            has_text = bool(action.target_view.get("text", ""))
            
            if "Button" in class_name and has_text and "CLICK" in action.text:
                return True
                
        return False
        
    def _perform_final_analysis(self) -> None:
        """
        Perform final analysis before stopping the memory manager.
        """
        self.logger.info("Performing final memory analysis")
        
        # Get overall statistics
        stats = self.get_memory_statistics()
        self.logger.info(f"Memory stats: {stats['discovered_states']} states, {stats['actions_executed']} actions")
        
        # Analyze patterns one last time
        patterns = self._analyze_patterns()
        self.logger.info(f"Found {patterns['action_pattern_count']} action patterns and {patterns['state_pattern_count']} state patterns")