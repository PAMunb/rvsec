# rvandroid/rvdroid/core/service.py

"""
Core service for RVDroid.

This module provides the central service that coordinates all RVDroid components,
manages the testing lifecycle, and integrates with the RV-Android framework.
"""

import time
from typing import Dict, Any, Optional, List, TypeVar, Generic
import traceback

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.model import ItemAction, ScreenDescription
from rvandroid.rvdroid.analysis.context.context_analyzer import ContextAnalyzer
from rvandroid.rvdroid.analysis.opportunity.opportunity_detector import OpportunityDetector
from rvandroid.rvdroid.analysis.progress.progress_tracker import ProgressTracker
from rvandroid.rvdroid.analysis.state_analyzer import StateAnalyzer
from rvandroid.rvdroid.core.action_manager import ActionManager
from rvandroid.rvdroid.core.llm_consultation_manager import LLMConsultationManager
from rvandroid.rvdroid.core.state_manager import StateManager
from rvandroid.rvdroid.memory.memory_system import MemorySystem
from rvandroid.rvdroid.orchestration.lifecycle import LifecycleManager, ExecutionPhase
from rvandroid.rvdroid.orchestration.recovery import RecoveryManager
from rvandroid.rvdroid.ui.uiautomator import UIAutomator2Adapter
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor
from rvandroid.util.error.error_handler import ErrorHandler

# Type variable for test result
T = TypeVar('T')


class RVDroidService(Generic[T]):
    """
    Central service that coordinates all RVDroid components and testing activities.

    RVDroidService orchestrates the testing process by combining various specialized 
    components such as the UIAutomator2 adapter, strategies, memory systems, and LLM 
    guidance. It manages the entire testing lifecycle and provides a cohesive interface 
    to the RV-Android framework.

    ### Architectural Decisions:
    - Implements a centralized coordination service for all RVDroid components
    - Uses a modular architecture with clear separation of concerns
    - Follows a layered design with analysis, strategy, memory, and execution components
    - Provides integration with RV-Android's static analysis and instrumentation systems
    - Supports dynamic strategy selection and optimization based on runtime feedback
    - Uses orchestration components for lifecycle and error management
    - Implements a phase-based execution model for structured testing

    ### Role in the System:
    - Acts as the main entry point for RVDroid functionality
    - Coordinates the interaction between different RVDroid subsystems
    - Manages the testing lifecycle from initialization to result processing
    - Integrates with RV-Android's event bus, logging, and monitoring systems
    - Provides a clean API for controlling and querying RVDroid functionality
    - Enables effective test generation through LLM-guided exploration
    - Handles error recovery and ensures robust operation

    ### Key Considerations:
    - Implements a clean phase-based execution model
    - Manages state transitions and exploration strategies
    - Provides robust error handling and recovery mechanisms
    - Supports flexible configuration of testing parameters
    - Enables integration with various testing strategies and approaches
    - Facilitates LLM-guided testing for more intelligent exploration
    - Ensures proper resource management and cleanup

    ### Integration Strategy:
    - Seamlessly integrates with RV-Android's instrumentation and analysis systems
    - Uses RV-Android's static analysis data to guide testing strategies
    - Publishes testing progress and results to RV-Android's event system
    - Provides hooks for custom testing strategies and analysis components
    - Supports flexible extension and customization of testing behavior
    - Uses the Event Bus for loosely coupled communication
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None,
                 config: Optional[ComponentConfigurator] = None,
                 device_id: str = "emulator-5554",
                 use_llm: bool = True,
                 use_screenshot_analysis: bool = True,
                 screenshot_frequency: str = "state_change",
                 preferred_strategy: str = "SpecificationFocusedStrategy",
                 execution_timeout: int = 3600):
        """
        Initialize the RVDroid service.

        Args:
            static_data: Optional static analysis data
            config: Optional component configuration
            device_id: Target device ID
            use_llm: Whether to use LLM guidance
            use_screenshot_analysis: Whether to use screenshot analysis
            screenshot_frequency: When to take screenshots ("state_change" or "always")
            preferred_strategy: Optional name of preferred strategy
            execution_timeout: Maximum execution time in seconds (default: 1 hour)
        """
        # Import strategies to ensure registration
        import rvandroid.rvdroid.strategy.basic_strategies
        import rvandroid.rvdroid.strategy.visual_aware_strategy
        import rvandroid.rvdroid.strategy.advanced_strategies
        import rvandroid.rvdroid.strategy.adaptive_strategies
        
        self.app_package_name = None

        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.core.service",
            {CONTEXT_COMPONENT: "RVDroidService"}
        )

        # Store configuration
        self.static_data = static_data
        self.config = config or ComponentConfigurator(static_data)
        self.device_id = device_id
        self.use_llm = use_llm
        self.preferred_strategy_name = preferred_strategy
        self.use_screenshot_analysis = use_screenshot_analysis
        self.screenshot_frequency = screenshot_frequency

        # Initialize performance monitor
        self.performance_monitor = PerformanceMonitor.get_instance()

        # Initialize orchestration components
        self.lifecycle_manager = LifecycleManager(timeout=execution_timeout)
        self.recovery_manager = RecoveryManager()
        
        # Initialize UIAutomator adapter
        self.ui_adapter = UIAutomator2Adapter(device_id)
        # Do not initialize here - we'll initialize during start_testing to avoid double initialization
        # This prevents the "initialization is called twice" issue
        self.ui_adapter_initialized = False

        # Initialize screenshot components
        if use_screenshot_analysis:
            from rvandroid.analysis.screenshot.screenshot_action_complementor import ScreenshotActionComplementor
            self.screenshot_complementor = ScreenshotActionComplementor()
            self.logger.info("Screenshot action complementation enabled")
        else:
            self.screenshot_complementor = None

        # Initialize screenshot tracking
        self.last_screenshot_path = None
        self.screenshot_stats = {
            "total_screenshots": 0,
            "complemented_actions_count": 0,
            "error_indicators_detected": 0
        }

        # Initialize memory system
        self.memory_system = MemorySystem(
            app_package="target_app",  # Will be updated when start_testing is called
            static_data=static_data
        )

        # Initialize analysis components
        self.state_analyzer = StateAnalyzer(static_data)
        self.opportunity_detector = OpportunityDetector(static_data)
        self.progress_tracker = ProgressTracker(static_data)
        self.context_analyzer = ContextAnalyzer(static_data)

        # Initialize refactored components
        
        # State Manager - for tracking application state
        state_manager_config = {
            "static_data": static_data
        }
        self.state_manager = StateManager(state_manager_config)
        
        # Action Manager - for generating and executing actions
        action_manager_config = {
            "static_data": static_data,
            "memory_system": self.memory_system,
            "device_id": device_id,
            "preferred_strategy": preferred_strategy,
            "use_llm": use_llm
        }
        self.action_manager = ActionManager(action_manager_config)
        
        # LLM Consultation Manager - for LLM guidance
        llm_consultation_config = {
            "static_data": static_data,
            "memory_system": self.memory_system,
            "use_llm": use_llm,
            "strategy_balancer": None  # Will be updated after action_manager is initialized
        }
        self.llm_consultation_manager = LLMConsultationManager(llm_consultation_config)

        # Setup recovery strategies
        self._setup_recovery_strategies()
        
        # Register lifecycle phase handlers
        self._register_lifecycle_handlers()
        
        self.logger.info("RVDroid service initialized successfully")
        if use_llm:
            self.logger.info("LLM guidance enabled")
        if self.preferred_strategy_name:
            self.logger.info(f"Preferred strategy set to: {self.preferred_strategy_name}")

    def _on_initialization_start(self) -> None:
        """
        Handler for when the initialization phase begins.
        """
        self.logger.info("Starting initialization phase")
    
    def _on_initialization_end(self) -> None:
        """
        Handler for when the initialization phase ends.
        """
        self.logger.info("Completed initialization phase")
    
    def _on_exploration_start(self) -> None:
        """
        Handler for when the exploration phase begins.
        """
        self.logger.info("Starting exploration phase")
    
    def _on_exploration_end(self) -> None:
        """
        Handler for when the exploration phase ends.
        """
        self.logger.info("Completed exploration phase")
        
        # Log statistics for this exploration cycle
        actions_executed = self.action_manager.stats["actions_executed"]
        successful_actions = self.action_manager.stats["successful_actions"]
        new_states = len(self.state_manager.visited_states)
        
        self.logger.info(f"Exploration statistics: {successful_actions}/{actions_executed} " 
                         f"successful actions, {new_states} unique states discovered")
    
    def _on_consultation_start(self) -> None:
        """
        Handler for when the LLM consultation phase begins.
        """
        self.logger.info("Starting LLM consultation phase")
    
    def _on_consultation_end(self) -> None:
        """
        Handler for when the LLM consultation phase ends.
        """
        self.logger.info("Completed LLM consultation phase")
    
    def _on_adaptation_start(self) -> None:
        """
        Handler for when the adaptation phase begins.
        """
        self.logger.info("Starting adaptation phase")
    
    def _on_adaptation_end(self) -> None:
        """
        Handler for when the adaptation phase ends.
        """
        self.logger.info("Completed adaptation phase")
    
    def _on_recovery_start(self) -> None:
        """
        Handler for when the recovery phase begins.
        """
        self.logger.info("Starting recovery phase")
    
    def _on_recovery_end(self) -> None:
        """
        Handler for when the recovery phase ends.
        """
        self.logger.info("Completed recovery phase")
        
        # Log recovery statistics
        recovery_stats = self.recovery_manager.get_recovery_statistics()
        success_rate = recovery_stats.get("success_rate", 0.0) * 100
        
        self.logger.info(f"Recovery statistics: {recovery_stats.get('total_successes', 0)}/"
                         f"{recovery_stats.get('total_attempts', 0)} successful "
                         f"({success_rate:.1f}%)")
    
    def _on_termination_start(self) -> None:
        """
        Handler for when the termination phase begins.
        """
        self.logger.info("Starting termination phase")
    
    def _on_termination_end(self) -> None:
        """
        Handler for when the termination phase ends.
        """
        self.logger.info("Completed termination phase")
        
        # Log final statistics
        elapsed_time = time.time() - self.lifecycle_manager.start_time
        actions_executed = self.action_manager.stats["actions_executed"]
        unique_states = len(self.state_manager.visited_states)
        
        self.logger.info(f"Testing completed in {elapsed_time:.1f}s with "
                         f"{actions_executed} actions executed, "
                         f"{unique_states} unique states discovered")
    
    def start_testing(self, package_name: str, activity: Optional[str] = None,
                      timeout: Optional[int] = None, llm_guidance: Optional[bool] = None) -> bool:
        """
        Start testing an application.

        Args:
            package_name: Application package name
            activity: Optional activity to start
            timeout: Execution timeout in seconds (overrides constructor setting if provided)
            llm_guidance: Whether to use LLM guidance (overrides constructor setting if provided)

        Returns:
            True if started successfully, False otherwise
        """
        self.logger.info(f"Starting test execution for {package_name}")

        # Update configuration if provided
        if timeout is not None:
            self.lifecycle_manager.timeout = timeout
            
        if llm_guidance is not None:
            self.use_llm = llm_guidance

        # Store the app package name for use in other methods
        self.app_package_name = package_name

        # Update memory system with the correct package name
        self.memory_system.app_package = package_name

        try:
            # Initialize and start the component managers
            if not self.state_manager.initialize() or not self.state_manager.start():
                self.logger.error("Failed to initialize or start state manager")
                return False
                
            if not self.action_manager.initialize() or not self.action_manager.start():
                self.logger.error("Failed to initialize or start action manager")
                return False
                
            if self.use_llm:
                # Update LLM consultation manager with strategy balancer from action manager
                self.llm_consultation_manager.strategy_balancer = self.action_manager.strategy_balancer
                if not self.llm_consultation_manager.initialize() or not self.llm_consultation_manager.start():
                    self.logger.error("Failed to initialize or start LLM consultation manager")
                    self.use_llm = False  # Disable LLM if it fails to initialize
            
            # Start lifecycle
            if not self.lifecycle_manager.start_execution():
                self.logger.error("Failed to start lifecycle execution")
                return False
            
            # Initialize UI adapter only if not already initialized
            if not hasattr(self, 'ui_adapter_initialized') or not self.ui_adapter_initialized:
                self.logger.info("Initializing UI adapter")
                if not self.ui_adapter.initialize():
                    self.logger.error("Failed to initialize UIAutomator2Adapter")
                    # Continue anyway and retry if needed
                else:
                    self.ui_adapter_initialized = True
                    self.logger.info("UIAutomator2Adapter initialized successfully")
                
            # Start application
            if not self.ui_adapter.start_app(package_name, activity):
                self.logger.error(f"Failed to start app: {package_name}")
                self.lifecycle_manager.stop_execution()
                return False

            # Give app time to fully initialize
            time.sleep(2)

            # Ensure soft keyboard is disabled or hidden
            if hasattr(self.ui_adapter, 'hide_keyboard'):
                self.ui_adapter.hide_keyboard()

            # Attempt to disable auto-showing of keyboard
            try:
                from rvandroid.commands.command import Command
                # Disable auto-show of soft keyboard
                cmd = Command("adb", [
                    "-s", self.ui_adapter.device_id,
                    "shell",
                    "settings put secure show_ime_with_hard_keyboard 0"
                ])
                cmd.invoke()

                # Also try disabling automatic keyboard popup
                cmd = Command("adb", [
                    "-s", self.ui_adapter.device_id,
                    "shell",
                    "settings put secure default_input_method com.android.inputmethod.latin/.LatinIME"
                ])
                cmd.invoke()

                self.logger.info("Disabled automatic keyboard display")
            except Exception as e:
                self.logger.warning(f"Could not disable automatic keyboard: {e}")

            # Get initial state
            with self.performance_monitor.measure_time("get_initial_state"):
                self._update_current_state()

            # Transition to exploration phase
            self.lifecycle_manager.transition_to_next_phase()  # INITIALIZATION -> EXPLORATION

            return True

        except Exception as e:
            self.logger.error(f"Error starting testing: {e}")
            import traceback
            traceback.print_exc()
            self.lifecycle_manager.emergency_stop()
            return False

    def execute_testing_loop(self) -> Dict[str, Any]:
        """
        Execute the main testing loop using the phase-based lifecycle.

        This method manages the testing execution through a structured phase-based
        approach, with exploration, consultation, and adaptation phases coordinated
        through the lifecycle manager.

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
                        if self.use_llm:
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

            self.logger.info(f"Testing loop completed with {self.action_manager.stats['actions_executed']} actions executed")
            return results

        except Exception as e:
            self.logger.error(f"Error in testing loop: {e}")
            traceback.print_exc()
            # Emergency stop on unexpected exception
            self.lifecycle_manager.emergency_stop()
            return {"error": str(e)}

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
                except Exception as e:
                    self.logger.error(f"Error in test iteration: {e}")
                    # Transition to recovery phase on error
                    self.lifecycle_manager._transition_to_phase(ExecutionPhase.RECOVERY)
                    break
            
            # Small delay between iterations
            time.sleep(0.5)
    
    def _execute_consultation_phase(self) -> None:
        """
        Execute the consultation phase, getting guidance from LLM with resource awareness.
        """
        if not self.use_llm:
            self.logger.warning("Skipping consultation phase - LLM not enabled")
            return
            
        # Get memory system insights for LLM context
        memory_insights = self.memory_system.get_memory_stats()
        
        # Get progress metrics
        progress_metrics = {}
        if self.progress_tracker:
            progress_metrics = self.progress_tracker.get_progress_summary()
        
        # Get exploration context
        exploration_context = {
            "metrics": progress_metrics,
            "memory_stats": memory_insights,
            "patterns": self.memory_system.get_patterns()
        }
        
        try:
            # Get strategic guidance via LLM consultation manager
            with self.performance_monitor.measure_time("llm_consultation"):
                guidance = self.llm_consultation_manager.get_strategic_guidance(
                    "exploration",
                    self.state_manager.get_current_state() or {},
                    exploration_context
                )
                
            self.logger.info("Received strategic guidance from LLM")
            
        except Exception as e:
            self.logger.error(f"Error getting LLM guidance: {e}")
    
    def _execute_adaptation_phase(self) -> None:
        """
        Execute the adaptation phase, applying LLM guidance.
        """
        if not self.use_llm:
            self.logger.warning("No LLM guidance available to apply")
            return
            
        # Get the most recent guidance
        guidance = self.llm_consultation_manager.get_last_guidance()
        if not guidance:
            self.logger.warning("No LLM guidance available")
            return
            
        # Apply directives to testing strategy
        try:
            directives = guidance.get("directives", [])
            if directives:
                self.logger.info(f"Applying {len(directives)} LLM directives")
                self.llm_consultation_manager.apply_directives(directives)
            else:
                self.logger.info("No directives in LLM guidance")
                
        except Exception as e:
            self.logger.error(f"Error applying LLM directives: {e}")
    
    def _execute_recovery_phase(self) -> None:
        """
        Execute the recovery phase, attempting to recover from errors.
        """
        self.logger.info("Executing recovery phase")
        
        # Check if we have error context
        if not hasattr(self, 'last_error') or not self.last_error:
            self.logger.warning("No error context available for recovery")
            # Create a simple error context
            error_context = {}
            exception = Exception("Unknown error - no context available")
        else:
            # Use the stored error information
            error_context = self.last_error_context
            exception = self.last_error
        
        # Attempt recovery
        success = self.recovery_manager.handle_error(exception, error_context)
        
        if success:
            self.logger.info("Recovery successful")
            # Update state after recovery
            self._update_current_state()
        else:
            self.logger.warning("Recovery failed, will attempt to continue")

    def stop_testing(self) -> Dict[str, Any]:
        """
        Stop the current testing execution gracefully.

        Returns:
            Results dictionary with execution statistics
        """
        self.logger.info("Stopping test execution")

        # Transition to termination phase
        if self.lifecycle_manager.execution_running:
            self.lifecycle_manager.stop_execution()
        
        # Stop all component managers
        try:
            self.state_manager.stop()
            self.action_manager.stop()
            if self.use_llm:
                self.llm_consultation_manager.stop()
        except Exception as e:
            self.logger.warning(f"Error stopping component managers: {e}")
        
        # Ensure UI Automator is cleaned up
        try:
            self.ui_adapter.cleanup()
        except Exception as e:
            self.logger.warning(f"Error during UI Automator cleanup: {e}")
        
        # Collect results
        results = self._collect_results()

        return results

    def process_results(self, logcat_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Process results after testing has completed.

        This method analyzes the testing results, extracting coverage information
        and identified violations from the logcat file when available.

        Args:
            logcat_file: Optional path to logcat file

        Returns:
            Results dictionary with processed metrics
        """
        self.logger.info("Processing test results")
        
        results = self._collect_results()

        # If logcat file is provided, parse it for coverage and violations
        if logcat_file:
            self.logger.info(f"Analyzing logcat file: {logcat_file}")
            
            try:
                # Parse logcat for method coverage using parse_logcat_file function
                from rvandroid.parser.log.logcat_parser import parse_logcat_file
                
                # Use the parse_logcat_file function directly
                repository = parse_logcat_file(logcat_file, self.static_data)
                
                # Create parsed_data dictionary from repository
                parsed_data = {
                    "coverage": repository.to_dict() if hasattr(repository, "to_dict") else {},
                    "errors": repository.get_errors_dict() if hasattr(repository, "get_errors_dict") else {}
                }
                
                if parsed_data:
                    # Extract coverage information
                    coverage_data = parsed_data.get("coverage", {})
                    method_calls = parsed_data.get("method_calls", [])
                    violations = parsed_data.get("violations", [])
                    
                    # Add to results
                    results["coverage"] = {
                        "methods_called": len(method_calls),
                        "unique_methods": len(set(method_calls)),
                        **coverage_data
                    }
                    
                    # Add violations data
                    results["violations"] = {
                        "count": len(violations),
                        "details": violations
                    }
                    
                    self.logger.info(f"Extracted coverage data: {len(method_calls)} method calls, "
                                    f"{len(violations)} violations")
            except Exception as e:
                self.logger.error(f"Error processing logcat file: {e}")
                results["logcat_processing_error"] = str(e)

        return results
    
    def cleanup(self) -> None:
        """
        Clean up resources used by RVDroid.
        
        This method ensures that all resources are properly released
        when testing is complete.
        """
        self.logger.info("Cleaning up RVDroid resources")

        # Ensure execution is stopped
        if hasattr(self, 'lifecycle_manager') and self.lifecycle_manager.execution_running:
            self.lifecycle_manager.stop_execution()

        # Clean up component managers
        try:
            if hasattr(self, 'state_manager'):
                self.state_manager.cleanup()
                
            if hasattr(self, 'action_manager'):
                self.action_manager.cleanup()
                
            if hasattr(self, 'llm_consultation_manager'):
                self.llm_consultation_manager.cleanup()
        except Exception as e:
            self.logger.warning(f"Error cleaning up component managers: {e}")

        # Clean up UI adapter
        if hasattr(self, 'ui_adapter'):
            try:
                self.ui_adapter.cleanup()
            except Exception as e:
                self.logger.warning(f"Error cleaning up UI adapter: {e}")
                
        self.logger.info("Cleanup completed")

    def _execute_test_iteration(self) -> Dict[str, Any]:
        """
        Execute a single test iteration.

        This method performs a complete test iteration, including state analysis,
        action generation, execution, and result processing. It handles errors using
        the recovery manager for robust execution.

        Returns:
            Result dictionary with execution details
        """
        try:
            # 1. Update and analyze current state
            current_state = self.state_manager.get_current_state()
            current_screen = self.state_manager.get_current_screen()
            
            if not current_state or not current_screen:
                self._update_current_state()
                current_state = self.state_manager.get_current_state()
                current_screen = self.state_manager.get_current_screen()
                
            if not current_state or not current_screen:
                return {"success": False, "error": "Failed to get current state"}
                
            # Check if app is in foreground
            app_in_foreground = self._check_app_in_foreground()
            if not app_in_foreground:
                result = self._handle_app_not_in_foreground()
                if not result.get("success", False):
                    return result
                    
                # Update state after recovery
                self._update_current_state()
                current_state = self.state_manager.get_current_state()
                current_screen = self.state_manager.get_current_screen()

            # 2. Generate action using action manager
            action = self.action_manager.generate_action(current_screen, current_state)
            if not action:
                fallback_action = self.action_manager.generate_fallback_action(current_screen)
                if not fallback_action:
                    return {"success": False, "error": "No action could be generated"}
                action = fallback_action
                self.logger.info("Using fallback action")

            # 3. Execute action
            previous_state = current_state
            action_result = self.action_manager.execute_action(action)
            
            # 4. Update state after action
            self._update_current_state()
            current_state = self.state_manager.get_current_state()
            
            # 5. Update action feedback
            self.action_manager.update_feedback(action, action_result, previous_state, current_state)
            
            # 6. Process action with LLM if enabled and appropriate
            if (self.use_llm and 
                action_result.get("success", False) and 
                current_state.get("is_new_state", False) and
                previous_state.get("activity") != current_state.get("activity")):
                
                self._get_action_feedback(action, action_result)
            
            return action_result
            
        except Exception as e:
            self.logger.error(f"Error in test iteration: {e}")
            # Store error information for recovery phase
            self.last_error = e
            self.last_error_context = {
                "phase": "test_iteration",
                "action": getattr(self.action_manager, 'last_action', None),
                "current_state": self.state_manager.get_current_state()
            }
            
            # Re-raise so the exploration phase can transition to recovery
            raise
            
    def _check_app_in_foreground(self) -> bool:
        """
        Check if the target app is in the foreground.
        
        Returns:
            True if app is in foreground, False otherwise
        """
        current_state = self.state_manager.get_current_state()
        if not current_state:
            return False
            
        current_package = current_state.get("package_name", "unknown")
        return current_package == self.app_package_name
            
    def _handle_app_not_in_foreground(self) -> Dict[str, Any]:
        """
        Handle the condition when the application is not in foreground.
        
        Returns:
            Result dictionary with success flag
        """
        self.logger.warning("App not in foreground, trying to recover...")

        # Create error context for recovery
        error_context = {
            "type": "app_not_foreground",
            "app_package": self.app_package_name,
            "current_state": self.state_manager.get_current_state()
        }
        
        # Create exception for recovery
        exception = Exception("App not in foreground")
        
        # Store for later use in recovery phase
        self.last_error = exception
        self.last_error_context = error_context
        
        # Attempt recovery
        if not self.recovery_manager.handle_error(exception, error_context):
            self.logger.error("Failed to recover app foreground state")
            return {"success": False, "error": "App not in foreground, recovery failed"}
            
        return {"success": True}
        
    def _get_action_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Get feedback from the LLM about an executed action and its result.

        Args:
            action: Action that was executed
            result: Execution result
        """
        if not self.use_llm:
            return

        try:
            # Get action information from memory system
            action_info = self.memory_system.get_action_info(action.id) if hasattr(self.memory_system, 'get_action_info') else {}

            # Prepare action data for LLM
            action_data = {
                "id": action.id,
                "text": action.text,
                "type": action_info.get("type", self._get_action_type(action.text)),
                "reaches_mop": getattr(action, 'reaches_mop', False),
                "directly_reaches_mop": getattr(action, 'directly_reaches_mop', False),
                "success_rate": action_info.get("success_rate", 0.0)
            }

            # Get feedback from LLM consultation manager
            feedback = self.llm_consultation_manager.get_action_feedback(
                action_data, 
                result, 
                self.state_manager.get_current_state() or {}
            )

            self.logger.debug(f"Received LLM feedback for action {action.id}")

        except Exception as e:
            self.logger.error(f"Error getting LLM action feedback: {e}", exc_info=True)
            error_handler = ErrorHandler.get_instance()
            error_handler.handle_error(
                "llm_action_feedback_error", 
                str(e),
                context={
                    "action_id": action.id if hasattr(action, 'id') else 'unknown',
                    "app_package": self.app_package_name,
                    "phase": "action_feedback"
                }
            )

    def _update_current_state(self) -> None:
        """
        Update the current application state.
        """
        try:
            # Ensure keyboard is hidden before getting UI state
            if hasattr(self.ui_adapter, 'hide_keyboard'):
                self.ui_adapter.hide_keyboard()

            # Get UI state from adapter
            ui_state = self.ui_adapter.get_ui_state(force_refresh=True)

            if not ui_state:
                self.logger.error("Failed to get UI state")
                return

            # Parse state to create ScreenDescription
            screen = self.ui_adapter.parse_screen(ui_state, self.static_data)

            if not screen:
                self.logger.error("Failed to parse screen description")
                return

            # Take screenshot if necessary
            if self.use_screenshot_analysis:
                should_take_screenshot = False
                
                if self.screenshot_frequency == "always":
                    should_take_screenshot = True
                elif not self.last_screenshot_path:  # First state
                    should_take_screenshot = True
                elif self.screenshot_frequency == "state_change":
                    current_fingerprint = ui_state.get("fingerprint", "") 
                    previous_fingerprint = getattr(self.state_manager.get_current_state() or {}, 
                                              "fingerprint", "")
                    should_take_screenshot = current_fingerprint != previous_fingerprint

                if should_take_screenshot:
                    self.last_screenshot_path = self.ui_adapter.take_screenshot()
                    if self.last_screenshot_path:
                        self.screenshot_stats["total_screenshots"] += 1
                        
                        # Update ui_state with screenshot path
                        ui_state["screenshot_path"] = self.last_screenshot_path

            # Complement actions with screenshot analysis
            if self.use_screenshot_analysis and self.screenshot_complementor and self.last_screenshot_path:
                self.logger.debug("Complementing actions with screenshot analysis")

                # Store action count before complementation
                actions_before = sum(len(item.actions) for item in screen.items)

                # Complement actions with screenshot analysis
                with self.performance_monitor.measure_time("screenshot_analysis"):
                    screen = self.screenshot_complementor.complement_screen_actions(
                        screen, self.last_screenshot_path)

                # Calculate how many actions were added
                actions_after = sum(len(item.actions) for item in screen.items)
                added_actions = actions_after - actions_before

                if added_actions > 0:
                    self.screenshot_stats["complemented_actions_count"] += added_actions
                    self.logger.info(f"Added {added_actions} complementary actions from screenshot analysis")

            # Update state in state manager
            self.state_manager.update_state(screen, ui_state)

        except Exception as e:
            self.logger.error(f"Error updating current state: {e}")

    def _collect_results(self) -> Dict[str, Any]:
        """
        Collect comprehensive results from the testing execution.

        This method gathers statistics and metrics from all components to provide
        a complete view of the testing execution results.

        Returns:
            Results dictionary with execution statistics and metrics
        """
        # Get lifecycle statistics
        phase_stats = self.lifecycle_manager.get_phase_statistics()
        
        # Get state manager statistics
        state_stats = self.state_manager.get_state_statistics()
        
        # Get action manager statistics
        action_stats = self.action_manager.get_statistics()
        
        # Get LLM consultation statistics if enabled
        llm_stats = {}
        if self.use_llm:
            llm_stats = self.llm_consultation_manager.get_statistics()
        
        # Aggregate basic stats
        results = {
            "elapsed_time": phase_stats.get("total_execution_time", 0),
            "actions_executed": action_stats.get("actions_executed", 0),
            "successful_actions": action_stats.get("successful_actions", 0),
            "unique_states": state_stats.get("unique_states", 0),
            "unique_activities": state_stats.get("unique_activities", 0),
            "phase_statistics": phase_stats
        }
        
        # Add memory system statistics
        results["memory_stats"] = self.memory_system.get_memory_stats()
        
        # Add recovery statistics
        results["recovery_stats"] = self.recovery_manager.get_recovery_statistics()
        
        # Add progress tracking if available
        if self.progress_tracker:
            results["progress"] = self.progress_tracker.get_progress_summary()

        # Add screenshot statistics if enabled
        if self.use_screenshot_analysis:
            results["screenshot_stats"] = self.screenshot_stats
            
        # Add strategy information
        results["strategy_stats"] = action_stats.get("strategy_info", {})
            
        # Add LLM resource metrics if available
        if self.use_llm:
            results["llm_stats"] = llm_stats
            
        # Calculate success rate
        if results["actions_executed"] > 0:
            results["success_rate"] = results["successful_actions"] / results["actions_executed"]
        else:
            results["success_rate"] = 0.0
            
        # Add exploration efficiency metrics
        if results["elapsed_time"] > 0:
            results["action_rate"] = results["actions_executed"] / (results["elapsed_time"] / 60.0)  # Actions per minute
            results["new_state_rate"] = results["unique_states"] / (results["elapsed_time"] / 60.0)  # New states per minute
            
        return results

    def _setup_recovery_strategies(self) -> None:
        """
        Setup recovery strategies for different error scenarios.
        
        This method configures the recovery manager with handlers for various
        recovery strategies, enabling automatic error recovery during testing.
        """
        # Import RecoveryStrategy here to avoid circular imports
        from rvandroid.rvdroid.orchestration.recovery import RecoveryStrategy
        
        # Register retry strategy handler
        self.recovery_manager.register_strategy_handler(
            RecoveryStrategy.RETRY,
            self._recovery_strategy_retry
        )
        
        # Register alternative strategy handler
        self.recovery_manager.register_strategy_handler(
            RecoveryStrategy.ALTERNATIVE,
            self._recovery_strategy_alternative
        )
        
        # Register back navigation strategy handler
        self.recovery_manager.register_strategy_handler(
            RecoveryStrategy.BACK_NAVIGATION,
            self._recovery_strategy_back
        )
        
        # Register app reset strategy handler
        self.recovery_manager.register_strategy_handler(
            RecoveryStrategy.APP_RESET,
            self._recovery_strategy_app_reset
        )
        
        # Register emulator reset strategy handler (most aggressive)
        self.recovery_manager.register_strategy_handler(
            RecoveryStrategy.EMULATOR_RESET,
            self._recovery_strategy_emulator_reset
        )
        
        self.logger.info("Recovery strategies configured")
    
    def _register_lifecycle_handlers(self) -> None:
        """
        Register handlers for lifecycle phase transitions.
        
        This method configures the lifecycle manager with callbacks for
        different execution phases, ensuring proper coordination of activities.
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
        
        self.logger.info("Lifecycle phase handlers registered")
    
    def _recovery_strategy_retry(self, error: Exception, context: Dict[str, Any]) -> bool:
        """
        Retry the failed operation.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            
        Returns:
            True if recovery successful, False otherwise
        """
        self.logger.info("Executing retry recovery strategy")
        
        # Extract context information
        action = context.get("action")
        if not action:
            self.logger.warning("No action in context, cannot retry")
            return False
            
        try:
            # Simple retry of the same action
            self.logger.info(f"Retrying action: {action.text}")
            success = self.action_manager.execute_action(action).get("success", False)
            return success
        except Exception as e:
            self.logger.error(f"Retry strategy failed: {e}")
            return False
    
    def _recovery_strategy_alternative(self, error: Exception, context: Dict[str, Any]) -> bool:
        """
        Try an alternative approach to achieve the same goal.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            
        Returns:
            True if recovery successful, False otherwise
        """
        self.logger.info("Executing alternative recovery strategy")
        
        try:
            # Get current screen
            current_screen = self.state_manager.get_current_screen()
            if not current_screen:
                self.logger.warning("No screen available for alternative recovery")
                return False
                
            # Generate a fallback action
            action = self.action_manager.generate_fallback_action(current_screen)
            if not action:
                self.logger.warning("Failed to generate alternative action")
                return False
                
            # Execute the alternative action
            self.logger.info(f"Executing alternative action: {action.text}")
            result = self.action_manager.execute_action(action)
            success = result.get("success", False)
            
            # Update state if successful
            if success:
                self._update_current_state()
                
            return success
        except Exception as e:
            self.logger.error(f"Alternative strategy failed: {e}")
            return False
    
    def _recovery_strategy_back(self, error: Exception, context: Dict[str, Any]) -> bool:
        """
        Navigate back and try a different path.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            
        Returns:
            True if recovery successful, False otherwise
        """
        self.logger.info("Executing back navigation recovery strategy")
        
        try:
            # Create a back action
            from rvandroid.parser.screen.visitor.model import ItemAction
            from rvandroid.domain.widget import WidgetEventType
            
            back_action = ItemAction(
                id=9999,
                text="BACK (Recovery)",
                event=WidgetEventType.KEY,
                target_view=None,
                coordinates=None
            )
            
            # Execute the back action
            self.logger.info("Pressing BACK key to navigate away from problematic state")
            result = self.action_manager.execute_action(back_action)
            success = result.get("success", False)
            
            # If back navigation worked, give the UI a moment to update
            if success:
                time.sleep(1.5)  # Wait longer for UI to stabilize after back
                self._update_current_state()  # Refresh the state
            
            return success
        except Exception as e:
            self.logger.error(f"Back navigation strategy failed: {e}")
            return False
    
    def _recovery_strategy_app_reset(self, error: Exception, context: Dict[str, Any]) -> bool:
        """
        Reset the application state.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            
        Returns:
            True if recovery successful, False otherwise
        """
        self.logger.info("Executing app reset recovery strategy")
        
        try:
            if not self.app_package_name:
                self.logger.warning("No app package name available, cannot reset app")
                return False
                
            # Stop and restart the app
            self.logger.info(f"Stopping and restarting app: {self.app_package_name}")
            
            self.ui_adapter.stop_app(self.app_package_name)
            time.sleep(1)  # Give it time to stop
            
            success = self.ui_adapter.start_app(self.app_package_name)
            time.sleep(3)  # Give it time to start
            
            # Update state after restart
            if success:
                self._update_current_state()
                
            return success
        except Exception as e:
            self.logger.error(f"App reset strategy failed: {e}")
            return False
    
    def _recovery_strategy_emulator_reset(self, error: Exception, context: Dict[str, Any]) -> bool:
        """
        Reset the emulator (last resort).
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            
        Returns:
            True if recovery successful, False otherwise
        """
        self.logger.warning("Executing emulator reset recovery strategy (last resort)")
        
        try:
            # This is a more aggressive recovery that we should rarely need
            # It would typically interact with EmulatorManager from rv-android
            self.logger.info("Attempting to reconnect UIAutomator2 without full reset")
            
            # Close and reopen the connection
            self.ui_adapter.cleanup()
            time.sleep(2)
            
            # Create a new adapter
            self.ui_adapter = UIAutomator2Adapter(self.device_id)
            time.sleep(3)
            
            # Restart the app
            if self.app_package_name:
                success = self.ui_adapter.start_app(self.app_package_name)
                time.sleep(3)  # Give it time to start
                
                # Update state after restart
                if success:
                    self._update_current_state()
                    return True
            
            return False
        except Exception as e:
            self.logger.error(f"Emulator reset strategy failed: {e}")
            return False
            
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