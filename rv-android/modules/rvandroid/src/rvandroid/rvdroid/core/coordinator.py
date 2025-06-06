# rvandroid/rvdroid/core/coordinator.py

"""
Core coordinator module for RVDroid.

This module provides the central coordination service for RVDroid,
managing the interaction between UI adapters, memory systems, 
strategies, and other components during the testing process.
"""

import time
import traceback
from typing import Dict, Any, Optional, List, TypeVar, Tuple

from rv_android_core.config.component_configurator import ComponentConfigurator
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.parser.screen.visitor.model import ItemAction, ScreenDescription
from rv_android_core.util.error.decorators import handle_error
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.performance_monitor import PerformanceMonitor

from rv_android_core.rvdroid.core.component import Component
from rv_android_core.rvdroid.core.lifecycle import LifecycleManager, ExecutionPhase


class TestingCoordinator(Component):
    """
    Central coordination service for the RVDroid testing process.
    
    ### Architectural Decisions:
    - Implements a centralized coordination service for testing activities
    - Uses a modular architecture with clear separation of concerns
    - Follows a layered design for testing state management and execution
    - Adopts a phase-based execution model for structured testing
    - Leverages the Component pattern for lifecycle management
    - Integrates with memory systems for state tracking and optimization
    - Provides comprehensive error handling and recovery mechanisms
    
    ### Role in the System:
    - Manages the testing lifecycle from initialization to termination
    - Orchestrates interaction between UI, memory, and strategy components
    - Processes testing state transitions and action generation
    - Coordinates LLM integration for intelligent testing guidance
    - Handles execution errors with structured recovery strategies
    - Provides access to testing metrics and progress information
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None,
                 static_data: Optional[StaticAnalysisData] = None,
                 device_id: str = "emulator-5554"):
        """
        Initialize the testing coordinator.
        
        Args:
            config: Optional configuration dictionary
            static_data: Optional static analysis data
            device_id: Target device ID
        """
        super().__init__("TestingCoordinator", config)
        
        # Store configuration and static data
        self.static_data = static_data
        self.device_id = device_id
        
        # Initialize configuration
        self.config_manager = config or ComponentConfigurator(static_data)
        
        # Initialize performance monitor
        self.performance_monitor = PerformanceMonitor.get_instance()
        
        # Initialize error handler
        self.error_handler = ErrorHandler.get_instance()
        
        # Component references (will be initialized later)
        self.lifecycle_manager = None
        self.ui_adapter = None
        self.memory_manager = None
        self.strategy_manager = None
        self.pattern_registry = None
        self.llm_service = None
        
        # State tracking
        self.app_package_name = None
        self.current_state = None
        self.current_screen = None
        self.last_action = None
        
        # Statistics
        self.stats = {
            "actions_executed": 0,
            "successful_actions": 0,
            "new_states": 0,
            "errors_detected": 0,
            "llm_guidance_count": 0
        }
        
    @handle_error(level="ERROR")
    def initialize(self) -> bool:
        """
        Initialize the coordinator and all required components.
        
        Returns:
            True if initialization succeeded, False otherwise
        """
        self.logger.info("Initializing Testing Coordinator")
        
        # Initialize lifecycle manager
        self.lifecycle_manager = LifecycleManager(
            timeout=self.config.get("execution_timeout", 3600)
        )
        
        # Initialize UI adapter (component-specific implementation will be injected)
        self.logger.debug("UI adapter will be injected during setup")
        
        # Initialize memory manager (component-specific implementation will be injected)
        self.logger.debug("Memory manager will be injected during setup")
        
        # Initialize strategy manager (component-specific implementation will be injected)
        self.logger.debug("Strategy manager will be injected during setup")
        
        # Initialize pattern registry (component-specific implementation will be injected)
        self.logger.debug("Pattern registry will be injected during setup")
        
        # Register lifecycle phase handlers
        self._register_lifecycle_handlers()
        
        self.initialized = True
        return True
        
    @handle_error(level="ERROR")
    def start(self) -> bool:
        """
        Start the coordinator.
        
        Returns:
            True if start succeeded, False otherwise
        """
        if not self.initialized:
            self.logger.error("Cannot start: coordinator not initialized")
            return False
            
        self.logger.info("Starting Testing Coordinator")
        
        # Start lifecycle
        if not self.lifecycle_manager.start_execution():
            self.logger.error("Failed to start lifecycle execution")
            return False
            
        self.running = True
        return True
        
    @handle_error(level="ERROR")
    def stop(self) -> bool:
        """
        Stop the coordinator.
        
        Returns:
            True if stop succeeded, False otherwise
        """
        if not self.running:
            self.logger.warning("Coordinator is not running")
            return True
            
        self.logger.info("Stopping Testing Coordinator")
        
        # Stop lifecycle
        if self.lifecycle_manager.execution_running:
            self.lifecycle_manager.stop_execution()
            
        self.running = False
        return True
        
    @handle_error(level="ERROR")
    def cleanup(self) -> None:
        """
        Clean up coordinator resources.
        """
        self.logger.info("Cleaning up Testing Coordinator")
        
        # Clean up components
        components_to_cleanup = [
            ("UI Adapter", self.ui_adapter),
            ("Memory Manager", self.memory_manager),
            ("Strategy Manager", self.strategy_manager),
            ("Pattern Registry", self.pattern_registry),
            ("LLM Service", self.llm_service)
        ]
        
        for name, component in components_to_cleanup:
            if component is not None:
                try:
                    self.logger.debug(f"Cleaning up {name}")
                    
                    # If component is a Component, use its cleanup method
                    if isinstance(component, Component):
                        component.cleanup()
                    # Otherwise, check if it has a cleanup method
                    elif hasattr(component, "cleanup") and callable(getattr(component, "cleanup")):
                        component.cleanup()
                except Exception as e:
                    self.logger.error(f"Error cleaning up {name}: {e}")
        
        self.initialized = False
        self.running = False
        
    @handle_error(level="ERROR")
    def start_testing(self, package_name: str, activity: Optional[str] = None) -> bool:
        """
        Start testing an application.
        
        Args:
            package_name: Application package name
            activity: Optional activity to start
            
        Returns:
            True if testing started successfully, False otherwise
        """
        self.logger.info(f"Starting test execution for {package_name}")
        
        # Store the app package name
        self.app_package_name = package_name
        
        # Validate required components
        if not self.ui_adapter:
            self.logger.error("UI adapter not set")
            return False
            
        if not self.memory_manager:
            self.logger.error("Memory manager not set")
            return False
            
        # Start the application
        try:
            if not self.ui_adapter.start_app(package_name, activity):
                self.logger.error(f"Failed to start app: {package_name}")
                return False
                
            # Give app time to fully initialize
            time.sleep(2)
            
            # Ensure soft keyboard is disabled or hidden
            if hasattr(self.ui_adapter, 'hide_keyboard'):
                self.ui_adapter.hide_keyboard()
                
            # Get initial state
            with self.performance_monitor.measure_time("get_initial_state"):
                self._update_current_state()
                
            # Transition to exploration phase
            self.lifecycle_manager.transition_to_next_phase()  # INITIALIZATION -> EXPLORATION
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting testing: {e}")
            self.lifecycle_manager.emergency_stop()
            return False
            
    @handle_error(level="ERROR")
    def execute_testing_loop(self) -> Dict[str, Any]:
        """
        Execute the main testing loop using the phase-based lifecycle.
        
        Returns:
            Results dictionary with execution statistics
        """
        self.logger.info("Starting testing loop")
        
        if not self.lifecycle_manager.execution_running:
            self.logger.error("Cannot execute testing loop: testing not started")
            return {"error": "Testing not started"}
            
        try:
            # Main testing loop - continues until stopped or timeout reached
            while self.lifecycle_manager.execution_running:
                # Check global timeout
                if self.lifecycle_manager.is_timeout_reached():
                    self.logger.info(f"Execution timeout reached: {self.lifecycle_manager.timeout}s")
                    break
                    
                # Execute based on current phase
                current_phase = self.lifecycle_manager.get_current_phase()
                
                if current_phase == ExecutionPhase.EXPLORATION:
                    # Execute exploration phase
                    self._execute_exploration_phase()
                    
                    # Check phase timeout
                    if self.lifecycle_manager.is_phase_timeout_reached():
                        self.logger.info("Exploration phase timeout reached")
                        if self.llm_service:
                            self.lifecycle_manager.transition_to_next_phase()  # EXPLORATION -> CONSULTATION
                        else:
                            # Skip consultation phase if LLM not enabled
                            self.logger.info("Skipping consultation phase (LLM not enabled)")
                            # Reset exploration phase to continue exploring
                            self.lifecycle_manager._transition_to_phase(ExecutionPhase.EXPLORATION)
                
                elif current_phase == ExecutionPhase.CONSULTATION:
                    # Execute consultation phase
                    self._execute_consultation_phase()
                    
                    # Always transition after consultation
                    self.lifecycle_manager.transition_to_next_phase()  # CONSULTATION -> ADAPTATION
                
                elif current_phase == ExecutionPhase.ADAPTATION:
                    # Execute adaptation phase
                    self._execute_adaptation_phase()
                    
                    # Always transition after adaptation
                    self.lifecycle_manager.transition_to_next_phase()  # ADAPTATION -> EXPLORATION
                
                elif current_phase == ExecutionPhase.RECOVERY:
                    # Execute recovery phase
                    self._execute_recovery_phase()
                    
                    # Transition back to exploration after recovery
                    self.lifecycle_manager.transition_to_next_phase()  # RECOVERY -> EXPLORATION
                
                elif current_phase == ExecutionPhase.TERMINATION:
                    # Break the loop if in termination phase
                    break
                
                else:
                    # Should not normally reach here
                    self.logger.warning(f"Unexpected phase: {current_phase}")
                    self.lifecycle_manager.transition_to_next_phase()
            
            # Execute termination phase if not already in it
            if self.lifecycle_manager.get_current_phase() != ExecutionPhase.TERMINATION:
                self.lifecycle_manager._transition_to_phase(ExecutionPhase.TERMINATION)
                
            # Collect final results
            results = self._collect_results()
            
            self.logger.info(f"Testing loop completed with {self.stats['actions_executed']} actions executed")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in testing loop: {e}")
            traceback.print_exc()
            # Emergency stop on unexpected exception
            self.lifecycle_manager.emergency_stop()
            return {"error": str(e)}
            
    @handle_error(level="ERROR")
    def _execute_exploration_phase(self) -> None:
        """
        Execute the exploration phase, performing multiple test iterations.
        """
        # Execute test iterations for this phase
        iteration_count = min(5, int(self.lifecycle_manager.phase_timings[ExecutionPhase.EXPLORATION] / 5))
        
        for _ in range(iteration_count):
            # Check if execution has been stopped
            if not self.lifecycle_manager.execution_running:
                break
                
            # Execute one test iteration
            with self.performance_monitor.measure_time("test_iteration"):
                try:
                    result = self._execute_test_iteration()
                    
                    # Update statistics
                    if result.get("success", False):
                        self.stats["successful_actions"] += 1
                        
                    if result.get("new_state", False):
                        self.stats["new_states"] += 1
                        
                except Exception as e:
                    self.logger.error(f"Error in test iteration: {e}")
                    # Transition to recovery phase on error
                    self.lifecycle_manager._transition_to_phase(ExecutionPhase.RECOVERY)
                    break
            
            # Small delay between iterations
            time.sleep(0.5)
            
    @handle_error(level="WARN")
    def _execute_consultation_phase(self) -> None:
        """
        Execute the consultation phase, getting guidance from LLM.
        """
        if not self.llm_service:
            self.logger.warning("Skipping consultation phase - LLM not enabled")
            return
            
        # Get memory insights for LLM context
        memory_insights = self.memory_manager.get_memory_stats() if self.memory_manager else {}
        
        # Get progress metrics from pattern registry
        progress_metrics = self.pattern_registry.get_progress_summary() if self.pattern_registry else {}
        
        # Get exploration context
        exploration_context = {
            "metrics": progress_metrics,
            "memory_stats": memory_insights,
            "patterns": self.memory_manager.get_patterns() if self.memory_manager else {}
        }
        
        try:
            # Get strategic guidance from LLM
            with self.performance_monitor.measure_time("llm_consultation"):
                guidance = self.llm_service.get_strategic_guidance(
                    "exploration",
                    self.current_state or {},
                    exploration_context
                )
                
            # Store guidance for use in adaptation phase
            self.last_llm_guidance = guidance
            self.stats["llm_guidance_count"] += 1
            
            self.logger.info("Received strategic guidance from LLM")
            
        except Exception as e:
            self.logger.error(f"Error getting LLM guidance: {e}")
            self.last_llm_guidance = None
            
    @handle_error(level="WARN")
    def _execute_adaptation_phase(self) -> None:
        """
        Execute the adaptation phase, applying LLM guidance.
        """
        if not hasattr(self, 'last_llm_guidance') or not self.last_llm_guidance:
            self.logger.warning("No LLM guidance available to apply")
            return
            
        # Apply directives to testing strategy
        try:
            directives = self.last_llm_guidance.get("directives", [])
            if directives:
                self.logger.info(f"Applying {len(directives)} LLM directives")
                self._apply_llm_directives(directives)
            else:
                self.logger.info("No directives in LLM guidance")
                
        except Exception as e:
            self.logger.error(f"Error applying LLM directives: {e}")
            
    @handle_error(level="WARN")
    def _execute_recovery_phase(self) -> None:
        """
        Execute the recovery phase, attempting to recover from errors.
        """
        self.logger.info("Executing recovery phase")
        
        # Check if we have error context
        if not hasattr(self, 'last_error') or not self.last_error:
            self.logger.warning("No error context available for recovery")
            return
            
        # Attempt recovery
        self.logger.info(f"Attempting recovery from error: {self.last_error}")
        
        # Try basic recovery strategies
        if self._attempt_basic_recovery():
            self.logger.info("Recovery successful")
            # Update state after recovery
            self._update_current_state()
        else:
            self.logger.warning("Recovery failed, will attempt to continue")
            
    @handle_error(level="WARN")
    def _attempt_basic_recovery(self) -> bool:
        """
        Attempt basic recovery strategies.
        
        Returns:
            True if recovery was successful, False otherwise
        """
        # Strategy 1: Try pressing BACK
        self.logger.debug("Recovery: Trying BACK key")
        try:
            if self.ui_adapter:
                self.ui_adapter.press_key("BACK")
                time.sleep(1.5)
                return True
        except Exception as e:
            self.logger.debug(f"BACK key recovery failed: {e}")
            
        # Strategy 2: Try restarting the app
        self.logger.debug("Recovery: Trying app restart")
        try:
            if self.ui_adapter and self.app_package_name:
                self.ui_adapter.stop_app(self.app_package_name)
                time.sleep(1)
                if self.ui_adapter.start_app(self.app_package_name):
                    time.sleep(3)
                    return True
        except Exception as e:
            self.logger.debug(f"App restart recovery failed: {e}")
            
        # Strategy 3: Try reconnecting to the device
        self.logger.debug("Recovery: Trying device reconnection")
        try:
            if hasattr(self.ui_adapter, 'reconnect') and callable(getattr(self.ui_adapter, 'reconnect')):
                if self.ui_adapter.reconnect():
                    time.sleep(2)
                    # Try to start the app again
                    if self.app_package_name:
                        self.ui_adapter.start_app(self.app_package_name)
                        time.sleep(3)
                        return True
        except Exception as e:
            self.logger.debug(f"Device reconnection recovery failed: {e}")
            
        return False
        
    @handle_error(level="WARN")
    def _execute_test_iteration(self) -> Dict[str, Any]:
        """
        Execute a single test iteration.
        
        Returns:
            Result dictionary with execution details
        """
        try:
            # 1. Analyze and prepare current state
            result = self._prepare_and_analyze_state()
            if not result["success"]:
                return result
                
            # 2. Generate action
            action = self._generate_action()
            if not action:
                return {"success": False, "error": "No valid action could be generated"}
                
            # 3. Execute action and process transition
            result = self._execute_action_and_process_transition(action)
            
            # 4. Update statistics
            if result["success"]:
                self._update_statistics_and_feedback(action, result)
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error in test iteration: {e}")
            # Store error information for recovery phase
            self.last_error = e
            
            # Re-raise so the exploration phase can transition to recovery
            raise
            
    @handle_error(level="WARN")
    def _prepare_and_analyze_state(self) -> Dict[str, Any]:
        """
        Prepare and analyze the current application state.
        
        Returns:
            Result dictionary with success flag and state analysis
        """
        # Check if app is in foreground
        if self.ui_adapter and self.app_package_name:
            is_foreground = self.ui_adapter.ensure_app_in_foreground(self.app_package_name)
            if not is_foreground:
                return {"success": False, "error": "App not in foreground"}
                
        # Analyze current state
        if not self.current_state or not self.current_screen:
            self._update_current_state()
            
        if not self.current_state or not self.current_screen:
            return {"success": False, "error": "Failed to get current state"}
            
        return {"success": True}
        
    @handle_error(level="WARN")
    def _generate_action(self) -> Optional[ItemAction]:
        """
        Generate the next action to execute.
        
        Returns:
            Next action or None if no action available
        """
        if not self.strategy_manager or not self.current_screen:
            self.logger.error("Cannot generate action: missing strategy manager or screen")
            return None
            
        try:
            # Get recent history from memory if available
            history = []
            if self.memory_manager:
                history = self.memory_manager.get_recent_states(10)
                
            # Get all available actions
            all_actions = []
            for item in self.current_screen.items:
                all_actions.extend(item.actions)
                
            if not all_actions:
                self.logger.warning("No UI actions available")
                return None
                
            # Use strategy manager to select next action
            return self.strategy_manager.generate_action(
                self.current_screen,
                self.current_state or {},
                history
            )
            
        except Exception as e:
            self.logger.error(f"Error generating action: {e}")
            return None
            
    @handle_error(level="WARN")
    def _execute_action_and_process_transition(self, action: ItemAction) -> Dict[str, Any]:
        """
        Execute an action and process the resulting state transition.
        
        Args:
            action: Action to execute
            
        Returns:
            Result dictionary with execution details
        """
        # Save previous state information
        previous_state_fingerprint = self.current_state.get("fingerprint") if self.current_state else None
        previous_state_activity = self.current_state.get("activity") if self.current_state else None
        
        # Record action reference for later use
        self.last_action = action
        
        # Execute the action
        success = False
        try:
            if not self.ui_adapter:
                return {"success": False, "error": "No UI adapter available"}
                
            # Determine action type and execute accordingly
            if "CLICK" in action.text:
                if hasattr(action, 'target_view') and action.target_view:
                    x = action.target_view.get("x", 0)
                    y = action.target_view.get("y", 0)
                    success = self.ui_adapter.click(x, y)
                    
            elif "LONG_CLICK" in action.text:
                if hasattr(action, 'target_view') and action.target_view:
                    x = action.target_view.get("x", 0)
                    y = action.target_view.get("y", 0)
                    success = self.ui_adapter.long_click(x, y)
                    
            elif "SCROLL" in action.text:
                if hasattr(action, 'target_view') and action.target_view:
                    x = action.target_view.get("x", 0)
                    y = action.target_view.get("y", 0)
                    direction = "DOWN"  # Default direction
                    if "UP" in action.text:
                        direction = "UP"
                    elif "LEFT" in action.text:
                        direction = "LEFT"
                    elif "RIGHT" in action.text:
                        direction = "RIGHT"
                    success = self.ui_adapter.scroll(x, y, direction)
                    
            elif "SET_TEXT" in action.text:
                # Extract text to input
                text = ""
                if hasattr(action, 'parameters') and action.parameters:
                    text = action.parameters.get("text", "")
                    
                if hasattr(action, 'target_view') and action.target_view:
                    resource_id = action.target_view.get("resource_id", None)
                    x = action.target_view.get("x", 0)
                    y = action.target_view.get("y", 0)
                    
                    if resource_id:
                        success = self.ui_adapter.input_text_to_field(resource_id, text, (x, y))
                    else:
                        # Click first to focus
                        self.ui_adapter.click(x, y)
                        time.sleep(0.5)
                        success = self.ui_adapter.input_text(text)
                        
            elif "BACK" in action.text:
                success = self.ui_adapter.press_key("BACK")
                
            else:
                self.logger.warning(f"Unknown action type: {action.text}")
                success = False
                
        except Exception as e:
            self.logger.error(f"Error executing action {action.id}: {e}")
            success = False
            
        # Process action result in memory system
        if self.memory_manager:
            self.memory_manager.process_action(action, success)
            
        # Update state
        self._update_current_state()
        
        # Check if state changed
        current_fingerprint = self.current_state.get("fingerprint") if self.current_state else None
        current_activity = self.current_state.get("activity") if self.current_state else None
        
        new_state = False
        activity_changed = False
        
        if previous_state_fingerprint and current_fingerprint:
            new_state = previous_state_fingerprint != current_fingerprint
            
            # Check if we've moved to a different activity
            activity_changed = previous_state_activity != current_activity
            if activity_changed:
                self.logger.info(f"Activity transition: {previous_state_activity} -> {current_activity}")
                
        # Create result
        return {
            "success": success,
            "new_state": new_state,
            "previous_state": previous_state_fingerprint,
            "previous_state_activity": previous_state_activity,
            "state_fingerprint": current_fingerprint,
            "current_state_activity": current_activity,
            "action_id": action.id,
            "activity_changed": activity_changed
        }
        
    @handle_error(level="WARN")
    def _update_statistics_and_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update statistics and provide feedback based on action execution.
        
        Args:
            action: Executed action
            result: Execution result
        """
        # Update strategy manager feedback
        if self.strategy_manager:
            self.strategy_manager.update_feedback(action, result)
            
        # Get action feedback from LLM if enabled
        if self.llm_service and result.get("new_state", False) and result.get("activity_changed", False):
            self._get_action_feedback(action, result)
            
        # Update statistics
        self.stats["actions_executed"] += 1
        
    @handle_error(level="WARN")
    def _update_current_state(self) -> None:
        """
        Update the current application state.
        """
        try:
            if not self.ui_adapter:
                self.logger.error("Cannot update state: UI adapter not available")
                return
                
            # Ensure keyboard is hidden before getting UI state
            if hasattr(self.ui_adapter, 'hide_keyboard'):
                self.ui_adapter.hide_keyboard()
                
            # Get UI state from adapter
            ui_state = self.ui_adapter.get_ui_state(force_refresh=True)
            
            if not ui_state:
                self.logger.error("Failed to get UI state")
                return
                
            # Parse state to create ScreenDescription
            self.current_screen = self.ui_adapter.parse_screen(ui_state, self.static_data)
            
            if not self.current_screen:
                self.logger.error("Failed to parse screen description")
                return
                
            # Process state through memory system
            memory_result = {}
            if self.memory_manager:
                memory_result = self.memory_manager.process_state(self.current_screen, ui_state)
                
            # Extract state information
            current_activity = ui_state.get("activity", "unknown")
            current_package = ui_state.get("package_name", "unknown")
            current_fingerprint = memory_result.get("fingerprint", "unknown")
            
            # Take screenshot if available
            screenshot_path = None
            if hasattr(self.ui_adapter, 'take_screenshot'):
                screenshot_path = self.ui_adapter.take_screenshot()
                
            # Create state data
            self.current_state = {
                "activity": current_activity,
                "package_name": current_package,
                "fingerprint": current_fingerprint,
                "timestamp": time.time(),
                "interactive_elements_count": len(self.current_screen.items) if self.current_screen else 0,
                "screenshot_path": screenshot_path,
                "is_new_state": memory_result.get("is_new_state", False)
            }
            
        except Exception as e:
            self.logger.error(f"Error updating current state: {e}")
            
    @handle_error(level="WARN")
    def _get_action_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Get feedback from the LLM about an executed action and its result.
        
        Args:
            action: Action that was executed
            result: Execution result
        """
        if not self.llm_service:
            return
            
        try:
            # Get action information from memory system
            action_info = self.memory_manager.get_action_info(action.id) if self.memory_manager else {}
            
            # Prepare action data for LLM
            action_data = {
                "id": action.id,
                "text": action.text,
                "type": action_info.get("type", self._get_action_type(action.text)),
                "reaches_mop": action.reaches_mop if hasattr(action, 'reaches_mop') else False,
                "directly_reaches_mop": action.directly_reaches_mop if hasattr(action, 'directly_reaches_mop') else False
            }
            
            # Get feedback from LLM service
            feedback = self.llm_service.get_action_feedback(action_data, result, self.current_state or {})
            
            # Process suggestions if available
            if "suggestions" in feedback and feedback["suggestions"]:
                self._process_llm_suggestions(feedback["suggestions"])
                
            self.logger.debug(f"Received LLM feedback for action {action.id}")
            
        except Exception as e:
            self.logger.error(f"Error getting LLM action feedback: {e}")
            
    def _get_action_type(self, action_text: str) -> str:
        """
        Extract action type from action text.
        
        Args:
            action_text: Text description of the action
            
        Returns:
            Action type string
        """
        if "CLICK" in action_text:
            return "click"
        elif "LONG_CLICK" in action_text:
            return "long_click"
        elif "SCROLL" in action_text:
            return "scroll"
        elif "SET_TEXT" in action_text:
            return "text_input"
        elif "BACK" in action_text:
            return "back"
        else:
            return "other"
            
    @handle_error(level="WARN")
    def _apply_llm_directives(self, directives: List[Dict[str, Any]]) -> None:
        """
        Apply directives from LLM to testing strategy.
        
        Args:
            directives: List of directives from LLM
        """
        if not self.strategy_manager:
            self.logger.warning("Cannot apply directives: strategy manager not available")
            return
            
        for directive in directives:
            directive_type = directive.get("type", "")
            
            # Pass directive to strategy manager
            self.strategy_manager.apply_directive(directive)
                
            # Log directive application
            self.logger.info(f"Applied LLM directive: {directive_type}")
            
    @handle_error(level="WARN")
    def _process_llm_suggestions(self, suggestions: List[Dict[str, Any]]) -> None:
        """
        Process suggestions from LLM action feedback.
        
        Args:
            suggestions: List of suggestions from LLM
        """
        if not suggestions:
            return
            
        # Pass suggestions to strategy manager
        if self.strategy_manager:
            self.strategy_manager.process_suggestions(suggestions)
            
    def _register_lifecycle_handlers(self) -> None:
        """
        Register handlers for lifecycle phase transitions.
        """
        # Register initialization phase handlers
        self.lifecycle_manager.register_phase_handler(
            ExecutionPhase.INITIALIZATION,
            on_entry=self._on_initialization_start,
            on_exit=self._on_initialization_end
        )
        
        # Register exploration phase handlers
        self.lifecycle_manager.register_phase_handler(
            ExecutionPhase.EXPLORATION,
            on_entry=self._on_exploration_start,
            on_exit=self._on_exploration_end
        )
        
        # Register consultation phase handlers
        self.lifecycle_manager.register_phase_handler(
            ExecutionPhase.CONSULTATION,
            on_entry=self._on_consultation_start,
            on_exit=self._on_consultation_end
        )
        
        # Register adaptation phase handlers
        self.lifecycle_manager.register_phase_handler(
            ExecutionPhase.ADAPTATION,
            on_entry=self._on_adaptation_start,
            on_exit=self._on_adaptation_end
        )
        
        # Register recovery phase handlers
        self.lifecycle_manager.register_phase_handler(
            ExecutionPhase.RECOVERY,
            on_entry=self._on_recovery_start,
            on_exit=self._on_recovery_end
        )
        
        # Register termination phase handlers
        self.lifecycle_manager.register_phase_handler(
            ExecutionPhase.TERMINATION,
            on_entry=self._on_termination_start,
            on_exit=self._on_termination_end
        )
        
    def _on_initialization_start(self) -> None:
        """Handler for when the initialization phase begins."""
        self.logger.info("Starting initialization phase")
    
    def _on_initialization_end(self) -> None:
        """Handler for when the initialization phase ends."""
        self.logger.info("Completed initialization phase")
    
    def _on_exploration_start(self) -> None:
        """Handler for when the exploration phase begins."""
        self.logger.info("Starting exploration phase")
    
    def _on_exploration_end(self) -> None:
        """Handler for when the exploration phase ends."""
        self.logger.info("Completed exploration phase")
        
        # Log statistics for this exploration cycle
        actions_executed = self.stats["actions_executed"]
        successful_actions = self.stats["successful_actions"]
        new_states = self.stats["new_states"]
        
        self.logger.info(f"Exploration statistics: {successful_actions}/{actions_executed} " 
                       f"successful actions, {new_states} new states discovered")
    
    def _on_consultation_start(self) -> None:
        """Handler for when the LLM consultation phase begins."""
        self.logger.info("Starting LLM consultation phase")
    
    def _on_consultation_end(self) -> None:
        """Handler for when the LLM consultation phase ends."""
        self.logger.info("Completed LLM consultation phase")
    
    def _on_adaptation_start(self) -> None:
        """Handler for when the adaptation phase begins."""
        self.logger.info("Starting adaptation phase")
    
    def _on_adaptation_end(self) -> None:
        """Handler for when the adaptation phase ends."""
        self.logger.info("Completed adaptation phase")
    
    def _on_recovery_start(self) -> None:
        """Handler for when the recovery phase begins."""
        self.logger.info("Starting recovery phase")
    
    def _on_recovery_end(self) -> None:
        """Handler for when the recovery phase ends."""
        self.logger.info("Completed recovery phase")
    
    def _on_termination_start(self) -> None:
        """Handler for when the termination phase begins."""
        self.logger.info("Starting termination phase")
    
    def _on_termination_end(self) -> None:
        """Handler for when the termination phase ends."""
        self.logger.info("Completed termination phase")
        
        # Log final statistics
        elapsed_time = time.time() - self.lifecycle_manager.start_time
        self.logger.info(f"Testing completed in {elapsed_time:.1f}s with "
                       f"{self.stats['actions_executed']} actions executed, "
                       f"{self.stats['new_states']} unique states discovered")
                       
    def _collect_results(self) -> Dict[str, Any]:
        """
        Collect comprehensive results from the testing execution.
        
        Returns:
            Results dictionary with execution statistics and metrics
        """
        # Get lifecycle statistics
        phase_stats = self.lifecycle_manager.get_phase_statistics()
        
        # Build results dictionary
        results = {
            "elapsed_time": phase_stats.get("total_execution_time", 0),
            "actions_executed": self.stats["actions_executed"],
            "successful_actions": self.stats["successful_actions"],
            "new_states": self.stats["new_states"],
            "errors_detected": self.stats["errors_detected"],
            "llm_guidance_count": self.stats.get("llm_guidance_count", 0),
            "phase_statistics": phase_stats
        }
        
        # Add memory statistics if available
        if self.memory_manager:
            results["memory_stats"] = self.memory_manager.get_memory_stats()
            
        # Add pattern statistics if available
        if self.pattern_registry:
            results["pattern_stats"] = self.pattern_registry.get_pattern_stats()
            
        # Calculate success rate
        if results["actions_executed"] > 0:
            results["success_rate"] = results["successful_actions"] / results["actions_executed"]
        else:
            results["success_rate"] = 0.0
            
        # Add exploration efficiency metrics
        if results["elapsed_time"] > 0:
            results["action_rate"] = results["actions_executed"] / (results["elapsed_time"] / 60.0)  # Actions per minute
            results["new_state_rate"] = results["new_states"] / (results["elapsed_time"] / 60.0)  # New states per minute
            
        return results
        
    def set_ui_adapter(self, ui_adapter: Any) -> None:
        """
        Set the UI adapter for this coordinator.
        
        Args:
            ui_adapter: UI adapter instance
        """
        self.ui_adapter = ui_adapter
        self.logger.info(f"UI adapter set: {ui_adapter.__class__.__name__}")
        
    def set_memory_manager(self, memory_manager: Any) -> None:
        """
        Set the memory manager for this coordinator.
        
        Args:
            memory_manager: Memory manager instance
        """
        self.memory_manager = memory_manager
        self.logger.info(f"Memory manager set: {memory_manager.__class__.__name__}")
        
    def set_strategy_manager(self, strategy_manager: Any) -> None:
        """
        Set the strategy manager for this coordinator.
        
        Args:
            strategy_manager: Strategy manager instance
        """
        self.strategy_manager = strategy_manager
        self.logger.info(f"Strategy manager set: {strategy_manager.__class__.__name__}")
        
    def set_pattern_registry(self, pattern_registry: Any) -> None:
        """
        Set the pattern registry for this coordinator.
        
        Args:
            pattern_registry: Pattern registry instance
        """
        self.pattern_registry = pattern_registry
        self.logger.info(f"Pattern registry set: {pattern_registry.__class__.__name__}")
        
    def set_llm_service(self, llm_service: Any) -> None:
        """
        Set the LLM service for this coordinator.
        
        Args:
            llm_service: LLM service instance
        """
        self.llm_service = llm_service
        self.logger.info(f"LLM service set: {llm_service.__class__.__name__ if llm_service else 'None'}")