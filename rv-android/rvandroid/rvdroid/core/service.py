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
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription, ItemAction
from rvandroid.rvdroid.analysis.context.context_analyzer import ContextAnalyzer
from rvandroid.rvdroid.analysis.opportunity.opportunity_detector import OpportunityDetector
from rvandroid.rvdroid.analysis.progress.progress_tracker import ProgressTracker
from rvandroid.rvdroid.analysis.state_analyzer import StateAnalyzer
from rvandroid.rvdroid.executor.action_executor import ActionExecutor
from rvandroid.rvdroid.llm.llm_service import LLMService
from rvandroid.rvdroid.llm.service.llm_manager import ResourceAwareLLMManager
from rvandroid.rvdroid.memory.memory_system import MemorySystem
from rvandroid.rvdroid.orchestration.lifecycle import LifecycleManager, ExecutionPhase
from rvandroid.rvdroid.orchestration.recovery import RecoveryManager
from rvandroid.rvdroid.strategy.balancer.strategy_balancer import StrategyBalancer
from rvandroid.rvdroid.strategy.strategy import StrategyRegistry, Strategy
from rvandroid.rvdroid.uiautomator.adapter import UIAutomator2Adapter
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor

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

        # Initialize screenshot components
        if use_screenshot_analysis:
            from rvandroid.analysis.screenshot.screenshot_action_complementor import ScreenshotActionComplementor
            self.screenshot_complementor = ScreenshotActionComplementor()
            self.logger.info("Screenshot action complementation enabled")
        else:
            self.screenshot_complementor = None

        # Initialize screenshot tracking
        self.last_screenshot_path = None
        self.last_state_fingerprint = None
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

        # Initialize action executor
        self.action_executor = ActionExecutor(device_id)

        # Initialize strategies
        self._ensure_strategies_registered()
        self.strategy_balancer = StrategyBalancer(static_data, use_llm_guidance=use_llm)
        self.current_strategy = None

        # Set preferred strategy if specified
        if self.preferred_strategy_name:
            self._set_preferred_strategy(self.preferred_strategy_name)

        # Initialize LLM service with resource-aware manager if needed
        self.llm_manager = ResourceAwareLLMManager(static_data) if use_llm else None
        self.llm_service = self.llm_manager.llm_service if self.llm_manager else None
        self.last_llm_guidance_time = 0
        self.llm_guidance_interval = 60  # Get new guidance every minute

        # Initialize state tracking 
        self.current_state: Optional[Dict[str, Any]] = None
        self.current_screen: Optional[ScreenDescription] = None
        self.last_action: Optional[ItemAction] = None

        # Statistics
        self.stats = {
            "actions_executed": 0,
            "successful_actions": 0,
            "new_states": 0,
            "errors_detected": 0,
            "llm_guidance_count": 0
        }

        # Setup recovery strategies
        self._setup_recovery_strategies()
        
        # Register lifecycle phase handlers
        self._register_lifecycle_handlers()
        
        self.logger.info("RVDroid service initialized successfully")
        if use_llm:
            self.logger.info("LLM guidance enabled")
        if self.preferred_strategy_name:
            self.logger.info(f"Preferred strategy set to: {self.preferred_strategy_name}")

    def _set_preferred_strategy(self, strategy_name: str) -> bool:
        """
        Set the preferred strategy by name or class type.

        Args:
            strategy_name: Name of the strategy class or strategy instance (case-insensitive)

        Returns:
            True if strategy was found and set as preferred, False otherwise
        """
        if not self.strategy_balancer or not self.strategy_balancer.strategies:
            self.logger.warning(f"Cannot set preferred strategy: no strategy balancer or strategies available")
            return False

        # Normalize the strategy name for comparison
        normalized_name = strategy_name.lower()
        # Add "Strategy" suffix if not already present
        if not normalized_name.endswith("strategy"):
            normalized_name = f"{normalized_name}strategy"

        # Try to find the strategy by class name match
        matched_strategy_info = None

        for strategy_info in self.strategy_balancer.strategies:
            strategy = strategy_info["strategy"]
            strategy_class_name = strategy.__class__.__name__.lower()
            strategy_instance_name = strategy.name.lower()

            # Check for match with class name or instance name (case-insensitive)
            if normalized_name == strategy_class_name or normalized_name == strategy_instance_name:
                matched_strategy_info = strategy_info
                break

        # If we didn't find an exact match, try a partial match
        if not matched_strategy_info:
            for strategy_info in self.strategy_balancer.strategies:
                strategy = strategy_info["strategy"]
                strategy_class_name = strategy.__class__.__name__.lower()

                # Check if the provided name is a prefix of the strategy class name
                if strategy_class_name.startswith(normalized_name.replace("strategy", "")):
                    matched_strategy_info = strategy_info
                    break

        # If still no match, attempt to create the strategy directly
        if not matched_strategy_info:
            strategy_class_name = normalized_name.capitalize() if not normalized_name.startswith(
                "visual") else "VisualAwareStrategy"

            # Try to dynamically create the strategy
            try:
                # Import the strategy module
                if strategy_class_name == "VisualAwareStrategy":
                    from rvandroid.rvdroid.strategy.visual_aware_strategy import VisualAwareStrategy as StrategyClass
                elif strategy_class_name == "RandomStrategy":
                    from rvandroid.rvdroid.strategy.basic_strategies import RandomStrategy as StrategyClass
                elif strategy_class_name == "SystematicStrategy":
                    from rvandroid.rvdroid.strategy.basic_strategies import SystematicStrategy as StrategyClass
                elif strategy_class_name == "SecurityfocusedStrategy" or strategy_class_name == "SecurityFocusedStrategy" or strategy_class_name == "SpecificationfocusedStrategy" or strategy_class_name == "MonitoredmethodfocusedStrategy" or strategy_class_name == "MonitoredMethodFocusedStrategy":
                    from rvandroid.rvdroid.strategy.basic_strategies import SpecificationFocusedStrategy as StrategyClass
                else:
                    self.logger.error(f"Unknown strategy class: {strategy_class_name}")
                    return False

                # Create the strategy
                strategy_instance = StrategyClass(self.static_data)

                # Add to strategy balancer
                strategy_info = {
                    "strategy": strategy_instance,
                    "weight": 1.0,
                    "performance": {
                        "new_states": 0,
                        "successful_actions": 0,
                        "total_actions": 0
                    }
                }

                self.strategy_balancer.strategies.append(strategy_info)
                matched_strategy_info = strategy_info

                # Re-normalize weights
                if hasattr(self.strategy_balancer, '_normalize_weights'):
                    self.strategy_balancer._normalize_weights()

                self.logger.info(f"Created and added strategy: {strategy_class_name}")

            except Exception as e:
                self.logger.error(f"Failed to create strategy {strategy_class_name}: {e}")
                return False

        # Set the matched strategy as preferred
        if matched_strategy_info:
            # Set as preferred
            self.strategy_balancer.preferred_strategy_info = matched_strategy_info
            self.strategy_balancer.last_strategy_switch = time.time()

            # Set current strategy
            self.current_strategy = matched_strategy_info["strategy"]

            self.logger.info(
                f"Set preferred strategy to {matched_strategy_info['strategy'].__class__.__name__} ({matched_strategy_info['strategy'].name})")
            return True
        else:
            self.logger.warning(f"Could not find strategy matching '{strategy_name}'")
            return False

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
        actions_executed = self.stats["actions_executed"]
        successful_actions = self.stats["successful_actions"]
        new_states = self.stats["new_states"]
        
        self.logger.info(f"Exploration statistics: {successful_actions}/{actions_executed} " 
                         f"successful actions, {new_states} new states discovered")
    
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
        self.logger.info(f"Testing completed in {elapsed_time:.1f}s with "
                         f"{self.stats['actions_executed']} actions executed, "
                         f"{self.stats['new_states']} unique states discovered")
    
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
            if llm_guidance and self.llm_service is None:
                self.llm_service = LLMService(self.static_data)
            elif not llm_guidance:
                self.llm_service = None

        # Store the app package name for use in other methods
        self.app_package_name = package_name

        # Update memory system with the correct package name
        self.memory_system.app_package = package_name

        try:
            # Start lifecycle
            if not self.lifecycle_manager.start_execution():
                self.logger.error("Failed to start lifecycle execution")
                return False
                
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
                        if self.use_llm and self.llm_service:
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
    
    def _execute_consultation_phase(self) -> None:
        """
        Execute the consultation phase, getting guidance from LLM with resource awareness.
        """
        if not self.use_llm or not self.llm_manager:
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
            # Get strategic guidance from LLM via resource-aware manager
            with self.performance_monitor.measure_time("llm_consultation"):
                guidance = self.llm_manager.get_strategic_guidance(
                    "exploration",
                    self.current_state or {},
                    exploration_context
                )
                
            # Store guidance for use in adaptation phase
            self.last_llm_guidance = guidance
            self.stats["llm_guidance_count"] += 1
            
            # Log resource metrics from the LLM manager
            resource_metrics = self.llm_manager.get_metrics()
            self.logger.info(f"Resource status: Memory {resource_metrics['resource_status']['memory_usage']}, " +
                            f"CPU {resource_metrics['resource_status']['cpu_usage']}, " +
                            f"Throttling level: {resource_metrics['resource_status']['throttling_level']}")
            
            self.logger.info("Received strategic guidance from LLM")
            
        except Exception as e:
            self.logger.error(f"Error getting LLM guidance: {e}")
            self.last_llm_guidance = None
    
    def _execute_adaptation_phase(self) -> None:
        """
        Execute the adaptation phase, applying LLM guidance.
        """
        if not self.last_llm_guidance:
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

        # Clean up UI adapter
        if hasattr(self, 'ui_adapter'):
            try:
                self.ui_adapter.cleanup()
            except Exception as e:
                self.logger.warning(f"Error cleaning up UI adapter: {e}")

        # Clean up action executor
        if hasattr(self, 'action_executor'):
            try:
                self.action_executor.cleanup()
            except Exception as e:
                self.logger.warning(f"Error cleaning up action executor: {e}")

        # Save memory system state if needed
        if hasattr(self, 'memory_system'):
            try:
                # For now, we don't persist memory between runs
                pass
            except Exception as e:
                self.logger.warning(f"Error saving memory system state: {e}")
                
        self.logger.info("Cleanup completed")

    def _ensure_strategies_registered(self):
        """
        Ensure all strategy classes are properly registered with the registry.
        
        This method checks if all required strategy classes are registered with
        the StrategyRegistry and registers any missing strategies. It supports
        both legacy names (like 'SecurityFocusedStrategy') and the new 'SpecificationFocusedStrategy'
        name for backward compatibility.
        """
        from rvandroid.rvdroid.strategy.strategy import StrategyRegistry
        from rvandroid.rvdroid.strategy.basic_strategies import (
            RandomStrategy,
            SystematicStrategy,
            SpecificationFocusedStrategy
        )
        from rvandroid.rvdroid.strategy.visual_aware_strategy import VisualAwareStrategy

        # Check if strategies are registered
        registered_strategies = StrategyRegistry.list_strategies()
        self.logger.info(f"Currently registered strategies: {registered_strategies}")

        # Register any missing strategies
        for strategy_class in [RandomStrategy, SystematicStrategy, SpecificationFocusedStrategy, VisualAwareStrategy]:
            class_name = strategy_class.__name__
            if class_name not in registered_strategies:
                self.logger.info(f"Registering missing strategy: {class_name}")
                StrategyRegistry.register(strategy_class)

        # Verify registration
        registered_strategies = StrategyRegistry.list_strategies()
        self.logger.info(f"Updated registered strategies: {registered_strategies}")

    def _ensure_back_action_available(self, actions: List[ItemAction]) -> List[ItemAction]:
        """
        Ensure that a BACK action is available in the action list.

        Args:
            actions: Original list of actions

        Returns:
            List with BACK action added if not already present
        """
        # Check if BACK action already exists
        has_back = any("BACK" in action.text.upper() for action in actions)

        if not has_back:
            # Create a BACK action
            from rvandroid.parser.screen.visitor.base_visitor import ItemAction
            from rvandroid.domain.widget import WidgetEventType

            # Generate a unique ID for the BACK action
            action_id = max([action.id for action in actions], default=0) + 1000

            # Create the BACK action
            back_action = ItemAction(
                id=action_id,
                text=f"BACK ({action_id})",
                event=WidgetEventType.KEY,
                target_view=None,
                coordinates=None
            )

            # Add an is_back flag to make it easily identifiable
            back_action.is_back = True

            # Add reaches_mop=False and directly_reaches_mop=False attributes
            back_action.reaches_mop = False
            back_action.directly_reaches_mop = False

            # Add to the actions list
            self.logger.debug(f"Adding BACK action {action_id} to available actions")
            return actions + [back_action]

        return actions

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get current execution statistics.

        Returns:
            Dictionary with execution statistics
        """
        current_time = time.time()
        elapsed_time = current_time - self.start_time if self.start_time > 0 else 0

        # Get memory system statistics
        memory_stats = self.memory_system.get_memory_stats()

        stats = {
            "elapsed_time": elapsed_time,
            "running": self.execution_running,
            **self.stats,
            "memory": memory_stats
        }

        # Add component-specific statistics
        if self.progress_tracker:
            stats["progress"] = self.progress_tracker.get_progress_summary()

        if self.strategy_balancer:
            stats["strategies"] = self.strategy_balancer.get_strategy_statistics()

        # Add screenshot statistics if enabled
        if self.use_screenshot_analysis:
            stats["screenshot_stats"] = self.get_screenshot_statistics()

        return stats

    def cleanup(self) -> None:
        """
        Clean up resources used by RVDroid.
        """
        self.logger.info("Cleaning up RVDroid resources")

        # Stop execution
        self.execution_running = False

        # Clean up components
        if self.ui_adapter:
            self.ui_adapter.cleanup()

        if self.action_executor:
            self.action_executor.cleanup()
            
        # Clean up LLM resources
        if self.llm_manager:
            self.llm_manager.cleanup()

        # # Save any state if needed
        # if self.memory_system:
        #     pass  # save memory when implemented

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
            # 1. Analyze and prepare current state
            result = self._prepare_and_analyze_state()
            if not result["success"]:
                return result
            state_analysis = result["state_analysis"]

            # 2. Ensure we have a valid strategy and generate action
            action = self._ensure_strategy_and_generate_action()
            if not action:
                return {"success": False, "error": "No valid action could be generated"}

            # 3. Execute action and process transition
            result = self._execute_action_and_process_transition(action)
            
            # 4. Update statistics and provide feedback
            if result["success"]:
                self._update_statistics_and_feedback(action, result)
            
            return result

        except Exception as e:
            self.logger.error(f"Error in test iteration: {e}")
            # Store error information for recovery phase
            self.last_error = e
            self.last_error_context = {
                "phase": "test_iteration",
                "action": getattr(self, 'last_action', None),
                "current_state": self.current_state
            }
            
            # Re-raise so the exploration phase can transition to recovery
            raise
            
    def _prepare_and_analyze_state(self) -> Dict[str, Any]:
        """
        Prepare and analyze the current application state.
        
        Returns:
            Result dictionary with success flag and state analysis
        """
        # Analyze current state
        state_analysis = self._analyze_state()

        # Track current activity and visited activities
        current_activity = self.current_state.get("activity", "unknown") if self.current_state else "unknown"

        # Initialize visited activities tracking if needed
        if not hasattr(self, 'visited_activities'):
            self.visited_activities = set()
            self.activity_visit_counts = {}

        # Update activity visit tracking
        self.visited_activities.add(current_activity)
        self.activity_visit_counts[current_activity] = self.activity_visit_counts.get(current_activity, 0) + 1

        # Check if app is in foreground
        if not state_analysis or state_analysis.get("app_in_foreground", False) == False:
            result = self._handle_app_not_in_foreground()
            if not result["success"]:
                return result
                
            # Update state after recovery
            state_analysis = self._analyze_state()

        return {
            "success": True,
            "state_analysis": state_analysis
        }
        
    def _handle_app_not_in_foreground(self) -> Dict[str, Any]:
        """
        Handle the condition when the application is not in foreground.
        
        Returns:
            Result dictionary with success flag
        """
        self.logger.warning("App not in foreground, trying to recover...")

        # Use the correct attribute for the target app's package name
        app_package = getattr(self, 'app_package_name', None)

        # Create error context for recovery
        error_context = {
            "type": "app_not_foreground",
            "app_package": app_package,
            "current_state": self.current_state
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
        
    def _ensure_strategy_and_generate_action(self) -> Optional[ItemAction]:
        """
        Ensure we have a valid strategy and generate an action.
        
        Returns:
            Generated action or None if no action could be generated
        """
        # Ensure we have a valid strategy
        if not self.current_strategy:
            if not self._ensure_valid_strategy():
                return None
                
        # Generate next action - using memory-optimized action generation
        action = self._generate_action_with_memory()

        if not action:
            self.logger.warning("No action generated, using fallback")
            action = self._generate_fallback_action()

            if not action:
                # Try recovery for no action available
                if not self._handle_no_action_available():
                    return None
                    
                # Try again after recovery
                action = self._generate_fallback_action()
                if not action:
                    self.logger.error("Still no action available after recovery")
                    return None
        
        return action
        
    def _ensure_valid_strategy(self) -> bool:
        """
        Ensure we have a valid strategy by trying different approaches.
        
        Returns:
            True if a valid strategy was set, False otherwise
        """
        try:
            # First try to use strategy balancer
            if self.strategy_balancer:
                self.current_strategy = self.strategy_balancer.select_strategy()
                
            # If still no strategy, create a default one
            if not self.current_strategy:
                from rvandroid.rvdroid.strategy.basic_strategies import RandomStrategy
                self.current_strategy = RandomStrategy(self.static_data)
                self.logger.info("Created RandomStrategy directly as fallback")
                
            return self.current_strategy is not None
            
        except Exception as e:
            self.logger.error(f"Failed to create strategy: {e}")
            # Final fallback: create an extremely simple strategy
            self.current_strategy = self._create_emergency_strategy()
            return self.current_strategy is not None
            
    def _handle_no_action_available(self) -> bool:
        """
        Handle the condition when no action is available.
        
        Returns:
            True if recovery successful, False otherwise
        """
        # Create error context for recovery
        error_context = {
            "type": "no_action_available",
            "current_state": self.current_state,
            "strategy": self.current_strategy.name if self.current_strategy else "none"
        }
        
        # Create exception for recovery
        exception = Exception("No action available")
        
        # Store for later use in recovery phase
        self.last_error = exception
        self.last_error_context = error_context
        
        # Attempt recovery
        return self.recovery_manager.handle_error(exception, error_context)
        
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
            success = self.action_executor.execute_item_action(action)
        except Exception as e:
            # Handle action execution error
            if not self._handle_action_execution_error(action, e):
                return {
                    "success": False, 
                    "error": f"Action execution failed: {str(e)}"
                }
            # Assume success if recovery worked
            success = True

        # Process action result in memory system
        self.memory_system.process_action(action, success)

        # Update state and record transition
        self._update_current_state()

        # Check if state changed
        result = self._analyze_state_transition(previous_state_fingerprint, previous_state_activity, action.id, success)
        
        return result
        
    def _handle_action_execution_error(self, action: ItemAction, exception: Exception) -> bool:
        """
        Handle an error that occurred during action execution.
        
        Args:
            action: Action that failed
            exception: Exception that was raised
            
        Returns:
            True if recovery successful, False otherwise
        """
        # Create error context for recovery
        error_context = {
            "type": "action_execution_failed",
            "action": action,
            "action_id": action.id,
            "current_state": self.current_state
        }
        
        # Store for later use in recovery phase
        self.last_error = exception
        self.last_error_context = error_context
        
        # Attempt recovery
        return self.recovery_manager.handle_error(exception, error_context)
        
    def _analyze_state_transition(self, previous_fingerprint: Optional[str], 
                                 previous_activity: Optional[str],
                                 action_id: int, success: bool) -> Dict[str, Any]:
        """
        Analyze the state transition after an action execution.
        
        Args:
            previous_fingerprint: Fingerprint of previous state
            previous_activity: Activity of previous state
            action_id: ID of the executed action
            success: Whether action execution was successful
            
        Returns:
            Result dictionary with transition analysis
        """
        # Get current state information
        current_fingerprint = self.current_state.get("fingerprint") if self.current_state else None
        current_activity = self.current_state.get("activity") if self.current_state else None

        # Check if state changed
        new_state = False
        if previous_fingerprint and current_fingerprint:
            new_state = previous_fingerprint != current_fingerprint

            # Check if we've moved to a different activity
            activity_changed = previous_activity != current_activity
            if activity_changed:
                self.logger.info(f"Activity transition: {previous_activity} -> {current_activity}")

        # Create result
        return {
            "success": success,
            "new_state": new_state,
            "previous_state": previous_fingerprint,
            "previous_state_activity": previous_activity,
            "state_fingerprint": current_fingerprint,
            "current_state_activity": current_activity,
            "action_id": action_id,
            "strategy": self.current_strategy.name if self.current_strategy else "emergency",
            "activity_changed": (previous_activity != current_activity)
            if previous_activity and current_activity else False
        }
        
    def _update_statistics_and_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update statistics and provide feedback based on action execution.
        
        Args:
            action: Executed action
            result: Execution result
        """
        # Get action feedback from LLM if enabled
        if self.use_llm and self.llm_manager and result.get("new_state", False) and result.get("activity_changed", False):
            self._get_action_feedback(action, result)

        # Update strategy feedback
        if self.current_strategy:
            self.current_strategy.update_feedback(action, result)

            if self.strategy_balancer:
                self.strategy_balancer.update_performance(self.current_strategy, action, result)

        # Update statistics
        self.stats["actions_executed"] += 1

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
            success = self.action_executor.execute_item_action(action)
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
            # Generate a new action using the current state
            if not self.current_strategy or not self.current_screen:
                self.logger.warning("No strategy or screen available for alternative recovery")
                return False
                
            # Explicitly avoid the failed action
            failed_action_id = context.get("action_id")
            
            # Use a different strategy to generate an alternative action
            alternative_action = self._generate_alternative_action(failed_action_id)
            
            if not alternative_action:
                self.logger.warning("Failed to generate alternative action")
                return False
                
            self.logger.info(f"Executing alternative action: {alternative_action.text}")
            success = self.action_executor.execute_item_action(alternative_action)
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
            # Execute back key event
            self.logger.info("Pressing BACK key to navigate away from problematic state")
            success = self.action_executor._execute_key_event("BACK")
            
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
            app_package = getattr(self, 'app_package_name', None)
            if not app_package:
                self.logger.warning("No app package name available, cannot reset app")
                return False
                
            # Stop and restart the app
            self.logger.info(f"Stopping and restarting app: {app_package}")
            
            self.ui_adapter.stop_app(app_package)
            time.sleep(1)  # Give it time to stop
            
            success = self.ui_adapter.start_app(app_package)
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
            app_package = getattr(self, 'app_package_name', None)
            if app_package:
                success = self.ui_adapter.start_app(app_package)
                time.sleep(3)  # Give it time to start
                
                # Update state after restart
                if success:
                    self._update_current_state()
                    return True
            
            return False
        except Exception as e:
            self.logger.error(f"Emulator reset strategy failed: {e}")
            return False
    
    def _generate_alternative_action(self, failed_action_id: Optional[int] = None) -> Optional[ItemAction]:
        """
        Generate an alternative action, avoiding a failed action.
        
        Args:
            failed_action_id: ID of the action to avoid
            
        Returns:
            An alternative action or None if not available
        """
        if not self.current_screen or not self.current_screen.items:
            return None
            
        # Collect all actions except the failed one
        available_actions = []
        for item in self.current_screen.items:
            for action in item.actions:
                if failed_action_id is None or action.id != failed_action_id:
                    available_actions.append(action)
        
        if not available_actions:
            # Create a BACK action as last resort
            from rvandroid.parser.screen.visitor.base_visitor import ItemAction
            from rvandroid.domain.widget import WidgetEventType
            
            back_action = ItemAction(
                id=9999,
                text="BACK (Recovery)",
                event=WidgetEventType.KEY,
                target_view=None,
                coordinates=None
            )
            back_action.is_back = True
            back_action.reaches_mop = False
            back_action.directly_reaches_mop = False
            
            return back_action
        
        # Use memory system to optimize if available
        if hasattr(self.memory_system, 'optimize_actions'):
            try:
                optimized_actions = self.memory_system.optimize_actions(
                    self.current_screen,
                    self.current_state or {},
                    available_actions
                )
                if optimized_actions:
                    return optimized_actions[0]  # Use highest priority action
            except Exception as e:
                self.logger.warning(f"Memory optimization failed: {e}")
        
        # Fallback to a random action
        import random
        return random.choice(available_actions)
    
    def _create_emergency_strategy(self) -> 'Strategy':
        """
        Create an emergency, bare-bones strategy for when all other strategies fail.

        This is a last-resort approach to ensure the system can continue testing.

        Returns:
            A minimal working Strategy implementation
        """
        from rvandroid.rvdroid.strategy.strategy import Strategy
        from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription, ItemAction
        import random

        class EmergencyStrategy(Strategy):
            def __init__(self, static_data=None):
                super().__init__(static_data, "EmergencyStrategy")

            def generate_action(self, screen, state_data, history=None):
                """Simply pick a random action or back button."""
                all_actions = []
                back_actions = []

                # Collect all actions
                for item in screen.items:
                    for action in item.actions:
                        all_actions.append(action)
                        if "BACK" in action.text.upper():
                            back_actions.append(action)

                # Prioritize back actions
                if back_actions and random.random() < 0.3:  # 30% chance to use back
                    return random.choice(back_actions)

                # Otherwise pick a random action
                if all_actions:
                    return random.choice(all_actions)

                return None

            def update_feedback(self, action, result):
                """Do nothing for this emergency strategy."""
                pass

        # Create and return instance
        return EmergencyStrategy(self.static_data)

    def _generate_action_with_memory(self) -> Optional[ItemAction]:
        """
        Generate the next action using memory-based optimization.

        Enhanced to prioritize actions that lead to unexplored activities.

        Returns:
            Next action to execute or None if no action available
        """
        if not self.current_strategy:
            self.logger.error("Cannot generate action: missing strategy")
            return None

        if not self.current_screen:
            self.logger.error("Cannot generate action: missing screen")
            return None

        try:
            # Get all actions from screen
            all_actions = []
            for item in self.current_screen.items:
                all_actions.extend(item.actions)

            # If no actions are available, return None early
            if not all_actions:
                self.logger.warning("No UI actions available")
                return None

            # Ensure BACK action is available
            all_actions = self._ensure_back_action_available(all_actions)

            # Track current activity and visited activities - with safety checks
            current_activity = "unknown"
            if self.current_state and "activity" in self.current_state:
                current_activity = self.current_state.get("activity", "unknown")

            # Initialize activity tracking if needed
            if not hasattr(self, 'visited_activities'):
                self.visited_activities = set()
                self.activity_visit_counts = {}

            # Update activity tracking
            self.visited_activities.add(current_activity)
            self.activity_visit_counts[current_activity] = self.activity_visit_counts.get(current_activity, 0) + 1

            # Check if this activity is potentially overexplored
            activity_count = self.activity_visit_counts.get(current_activity, 0)
            is_overexplored = activity_count > 10 and len(self.visited_activities) > 1

            # Optimize using memory system if available
            optimized_actions = all_actions
            if hasattr(self.memory_system, 'optimize_actions'):
                try:
                    optimized_actions = self.memory_system.optimize_actions(
                        self.current_screen,
                        self.current_state or {},
                        all_actions
                    )
                except Exception as e:
                    self.logger.error(f"Memory system optimization failed: {e}, using all actions")
                    optimized_actions = all_actions

            # If the activity is overexplored, prioritize actions that might lead elsewhere
            if is_overexplored:
                self.logger.info(
                    f"Activity {current_activity} appears overexplored (visits={activity_count}), prioritizing navigation")

                # Look for navigation-related actions and monitored methods
                navigation_actions = []
                monitored_method_actions = []
                other_actions = []

                for action in optimized_actions:
                    # First prioritize actions that reach monitored methods
                    if hasattr(action, 'reaches_mop') and action.reaches_mop:
                        monitored_method_actions.append(action)
                        continue
                    
                    # Then check if this looks like a navigation action
                    is_navigation = False

                    # Check action properties for navigation potential
                    if hasattr(action, 'target_view') and action.target_view:
                        class_name = action.target_view.get("class", "")
                        text = action.target_view.get("text", "")
                        resource_id = action.target_view.get("resource_id", "")
                        
                        # Check if this component might relate to monitored methods
                        # using the enhanced static analyzer if available through memory system
                        static_analyzer = None
                        if hasattr(self.memory_system, 'exploration_optimizer') and \
                           hasattr(self.memory_system.exploration_optimizer, 'static_analyzer'):
                            static_analyzer = self.memory_system.exploration_optimizer.static_analyzer
                        
                        if static_analyzer and resource_id:
                            related_methods = static_analyzer.match_resource_to_monitored_methods(resource_id)
                            if related_methods:
                                # This component might reach monitored methods
                                monitored_method_actions.append(action)
                                continue

                        # Buttons with text are likely navigation elements
                        if "Button" in class_name and text and "CLICK" in action.text:
                            is_navigation = True
                        
                        # Menu items, tabs, and similar UI elements are likely navigation
                        elif any(nav_term in class_name for nav_term in ["Menu", "Tab", "Nav", "Toolbar"]):
                            is_navigation = True

                    # Add to appropriate list
                    if is_navigation:
                        navigation_actions.append(action)
                    else:
                        other_actions.append(action)

                # Prioritize based on exploration goals:
                # 1. First try actions that reach monitored methods
                # 2. Then navigation actions that might lead to new states
                # 3. Finally, any other actions
                if monitored_method_actions:
                    self.logger.debug(f"Selected action related to monitored methods in overexplored activity")
                    return monitored_method_actions[0]  # Use the first monitored method action
                elif navigation_actions:
                    self.logger.debug(f"Selected navigation action to leave overexplored activity")
                    return navigation_actions[0]  # Use the first navigation action

            # Use strategy to select from optimized actions
            action = None
            if optimized_actions:
                try:
                    action = self.current_strategy.generate_action(
                        self.current_screen,
                        self.current_state or {},
                        []  # No need to pass history - memory system already used it
                    )
                except Exception as e:
                    self.logger.error(f"Strategy action generation failed: {e}")
                    # Fall back to a random action
                    if optimized_actions:
                        import random
                        action = random.choice(optimized_actions)
                        self.logger.info(f"Selected random action after strategy failure: {action.id}")

                if action:
                    self.logger.debug(f"Generated action {action.id}: {action.text}")
                    return action

                # If strategy couldn't select an action, use the first optimized action
                if optimized_actions:
                    return optimized_actions[0]

            return None

        except Exception as e:
            self.logger.error(f"Error generating action with memory: {e}")
            return None

    def _get_action_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Get feedback from the LLM about an executed action and its result.

        Args:
            action: Action that was executed
            result: Execution result
        """
        if not self.use_llm or not self.llm_manager:
            return

        try:
            # Get action information from memory system
            action_info = self.memory_system.get_action_info(action.id) or {}

            # Prepare action data for LLM
            action_data = {
                "id": action.id,
                "text": action.text,
                "type": action_info.get("type", self._get_action_type(action.text)),
                "reaches_mop": action.reaches_mop,
                "directly_reaches_mop": action.directly_reaches_mop,
                "success_rate": action_info.get("success_rate", 0.0)
            }

            # Get feedback from resource-aware LLM manager
            feedback = self.llm_manager.get_action_feedback(action_data, result, self.current_state or {})

            # Process suggestions if available
            if "suggestions" in feedback and feedback["suggestions"]:
                self._process_llm_suggestions(feedback["suggestions"])

            self.logger.debug(f"Received LLM feedback for action {action.id}")

        except Exception as e:
            self.logger.error(f"Error getting LLM action feedback: {e}")

    def _get_llm_guidance(self, state_analysis: Dict[str, Any]) -> None:
        """
        Get guidance from the LLM using the resource-aware manager.

        Args:
            state_analysis: Analysis of the current state
        """
        if not self.llm_manager:
            return

        # Prepare exploration context
        memory_stats = self.memory_system.get_memory_stats()

        # Get state history from short_term_memory
        recent_states = []
        if hasattr(self.memory_system, 'short_term_memory'):
            recent_states = self.memory_system.short_term_memory.get_recent_states(10)

        exploration_context = {
            "exploration_phase": self.memory_system.exploration_optimizer.exploration_phase if hasattr(
                self.memory_system, 'exploration_optimizer') else "exploration",
            "metrics": self.progress_tracker.get_progress_summary() if self.progress_tracker else {},
            "history": recent_states,
            "patterns": self.memory_system.get_patterns(),
            "memory_stats": memory_stats
        }

        try:
            # Get strategic guidance from LLM via resource-aware manager
            guidance = self.llm_manager.get_strategic_guidance(
                "exploration",
                self.current_state or {},
                exploration_context
            )

            # Apply directives to testing strategy
            if "directives" in guidance and guidance["directives"]:
                self._apply_llm_directives(guidance["directives"])

            # Update statistics
            self.stats["llm_guidance_count"] += 1

            # Log resource metrics
            resource_metrics = self.llm_manager.get_metrics()
            if int(self.stats["llm_guidance_count"]) % 5 == 0:  # Log every 5 guidance requests
                self.logger.info(f"LLM resource metrics - Memory: {resource_metrics['resource_status']['memory_usage']}, " +
                                f"CPU: {resource_metrics['resource_status']['cpu_usage']}, " +
                                f"Throttling: {resource_metrics['resource_status']['throttling_level']}")

            self.logger.info("Applied LLM strategic guidance")

        except Exception as e:
            self.logger.error(f"Error getting LLM guidance: {e}")

    def _analyze_state(self) -> Dict[str, Any]:
        """
        Analyze the current application state.

        Returns:
            Analysis dictionary with state insights
        """
        if not self.current_state or not self.current_screen:
            self._update_current_state()

        if not self.current_state or not self.current_screen:
            self.logger.error("Failed to get current state for analysis")
            return {}

        try:
            # Check if app is in foreground
            current_package = self.current_state.get("package_name", "unknown")
            print(f"Current package:: {current_package}")

            # Use the correct attribute for the target app's package name
            app_package = getattr(self, 'app_package_name', current_package)

            app_in_foreground = (current_package == app_package)

            # Get memory system insights
            memory_insights = {
                "patterns": self.memory_system.get_patterns(),
                "state_info": self.memory_system.get_state_info(self.current_state.get("fingerprint")),
                "memory_stats": self.memory_system.get_memory_stats()
            }

            # Analyze state with different analyzers
            state_analysis = self.state_analyzer.analyze_state(self.current_screen, self.current_state)

            # Add app_in_foreground flag
            state_analysis["app_in_foreground"] = app_in_foreground

            # Add memory insights
            state_analysis["memory_insights"] = memory_insights

            # Add context analysis if available
            if self.context_analyzer:
                context_analysis = self.context_analyzer.analyze_context(self.current_screen, self.current_state)
                state_analysis["context_info"] = context_analysis

            # Add opportunity detection if available
            print(f"Opportunity detector={self.opportunity_detector}")
            if self.opportunity_detector:
                opportunities = self.opportunity_detector.detect_opportunities(
                    self.current_screen,
                    state_analysis.get("context_info")
                )
                state_analysis["opportunities"] = opportunities

            # Add progress tracking if available
            print(f"Progress tracker={self.progress_tracker}")
            if self.progress_tracker:
                progress_metrics = self.progress_tracker.update_progress(
                    self.current_screen,
                    state_analysis.get("fingerprint", "unknown"),
                    self.last_action
                )
                state_analysis["progress_metrics"] = progress_metrics

            print(f"*** State analysis: {state_analysis}")

            return state_analysis

        except Exception as e:
            self.logger.error(f"Error analyzing state: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def _generate_action(self) -> Optional[ItemAction]:
        """
        Generate the next action to execute.

        Returns:
            Next action or None if no action available
        """
        if not self.current_strategy or not self.current_screen:
            self.logger.error("Cannot generate action: missing strategy or screen")
            return None

        try:
            # Get history if needed by the strategy
            history = list(self.short_term_memory.state_history)

            # Make sure we have all UI elements and ensure BACK is available
            if self.current_screen.items:
                # Get all actions
                all_actions = []
                for item in self.current_screen.items:
                    all_actions.extend(item.actions)

                # Ensure BACK action is available
                all_actions = self._ensure_back_action_available(all_actions)

                # Update the screen with the modified actions list if needed
                if len(all_actions) > sum(len(item.actions) for item in self.current_screen.items):
                    # We added a BACK action, so we need to update the screen
                    # For simplicity, we'll just attach it to the first item
                    if self.current_screen.items:
                        self.current_screen.items[0].actions.append(all_actions[-1])

            # Use current strategy to generate action
            action = self.current_strategy.generate_action(
                self.current_screen,
                self.current_state or {},
                history
            )

            if action:
                self.logger.debug(f"Generated action {action.id}: {action.text}")
                return action

            return None

        except Exception as e:
            self.logger.error(f"Error generating action: {e}")
            return None

    def _generate_fallback_action(self) -> Optional[ItemAction]:
        """
        Generate a fallback action when normal action generation fails.

        Returns:
            Fallback action or None if no action available
        """
        if not self.current_screen or not self.current_screen.items:
            # If no screen or items, try to create a BACK action
            from rvandroid.parser.screen.visitor.base_visitor import ItemAction
            from rvandroid.domain.widget import WidgetEventType

            back_action = ItemAction(
                id=9999,
                text="BACK (Fallback)",
                event=WidgetEventType.KEY,
                target_view=None,
                coordinates=None
            )
            back_action.is_back = True
            back_action.reaches_mop = False
            back_action.directly_reaches_mop = False

            self.logger.info("No screen elements, creating fallback BACK action")
            return back_action

        # First, try to find a BACK action in the existing actions
        all_actions = []
        for item in self.current_screen.items:
            all_actions.extend(item.actions)

        # Look for BACK actions
        back_actions = [a for a in all_actions if "BACK" in a.text.upper()]
        if back_actions:
            self.logger.info("Using BACK action as fallback")
            return back_actions[0]

        # If no BACK action, select a random action
        import random
        if all_actions:
            return random.choice(all_actions)

        return None

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

            # Parse state to create ScreenDescription - ensure this happens before memory processing
            self.current_screen = self.ui_adapter.parse_screen(ui_state, self.static_data)

            if not self.current_screen:
                self.logger.error("Failed to parse screen description")
                return

            # Extract state information
            current_activity = ui_state.get("activity", "unknown")
            current_package = ui_state.get("package_name", "unknown")

            # Process state through memory system
            memory_result = self.memory_system.process_state(self.current_screen, ui_state)

            # Update fingerprint tracking
            current_fingerprint = memory_result["fingerprint"]
            self.last_state_fingerprint = current_fingerprint

            # Take screenshot if necessary
            should_take_screenshot = False
            previous_fingerprint = self.last_state_fingerprint

            if self.use_screenshot_analysis:
                if self.screenshot_frequency == "always":
                    should_take_screenshot = True
                elif self.last_screenshot_path is None:  # First state
                    should_take_screenshot = True
                elif self.screenshot_frequency == "state_change" and previous_fingerprint != current_fingerprint:
                    should_take_screenshot = True

            if should_take_screenshot:
                self.last_screenshot_path = self.ui_adapter.take_screenshot()
                if self.last_screenshot_path:
                    self.screenshot_stats["total_screenshots"] += 1

                    # Update the screenshot filename with the state fingerprint
                    if self.last_state_fingerprint:
                        self.last_screenshot_path = self.ui_adapter.update_screenshot_with_state(
                            self.last_screenshot_path, self.last_state_fingerprint)

            # Complement actions with screenshot analysis
            if self.use_screenshot_analysis and self.screenshot_complementor and self.last_screenshot_path:
                self.logger.debug("Complementing actions with screenshot analysis")

                # Store action count before complementation
                actions_before = sum(len(item.actions) for item in self.current_screen.items)

                # Complement actions with screenshot analysis
                with self.performance_monitor.measure_time("screenshot_analysis"):
                    self.current_screen = self.screenshot_complementor.complement_screen_actions(
                        self.current_screen, self.last_screenshot_path)

                # Calculate how many actions were added
                actions_after = sum(len(item.actions) for item in self.current_screen.items)
                added_actions = actions_after - actions_before

                if added_actions > 0:
                    self.screenshot_stats["complemented_actions_count"] += added_actions
                    self.logger.info(f"Added {added_actions} complementary actions from screenshot analysis")

            # Create state data
            self.current_state = {
                "activity": current_activity,
                "package_name": current_package,
                "fingerprint": current_fingerprint,
                "timestamp": time.time(),
                "interactive_elements_count": len(self.current_screen.items),
                "screenshot_path": self.last_screenshot_path,
                "is_new_state": memory_result["is_new_state"]
            }

        except Exception as e:
            self.logger.error(f"Error updating current state: {e}")

    def get_screenshot_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about screenshot analysis.

        Returns:
            Dictionary with screenshot statistics
        """
        return {
            "screenshot_enabled": self.use_screenshot_analysis,
            "screenshot_frequency": self.screenshot_frequency,
            "total_screenshots": self.screenshot_stats["total_screenshots"],
            "complemented_actions": self.screenshot_stats["complemented_actions_count"],
            "error_indicators_detected": self.screenshot_stats["error_indicators_detected"],
            "last_screenshot": self.last_screenshot_path
        }

    def _generate_state_fingerprint(self, screen: ScreenDescription, state_data: Dict[str, Any]) -> str:
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
        
        # Get basic stats
        results = {
            "elapsed_time": phase_stats.get("total_execution_time", 0),
            "actions_executed": self.stats["actions_executed"],
            "successful_actions": self.stats["successful_actions"],
            "new_states": self.stats["new_states"],
            "errors_detected": self.stats["errors_detected"],
            "states_explored": len(self.memory_system.short_term_memory.state_history) 
                if hasattr(self.memory_system, 'short_term_memory') else 0,
            "llm_guidance_count": self.stats.get("llm_guidance_count", 0),
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
            results["screenshot_stats"] = self.get_screenshot_statistics()
            
        # Add strategy information
        if self.strategy_balancer:
            results["strategy_stats"] = self.strategy_balancer.get_strategy_statistics()
            
        # Add LLM resource metrics if available
        if self.llm_manager:
            results["llm_resource_metrics"] = self.llm_manager.get_metrics()
            
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

    def _apply_llm_directives(self, directives: List[Dict[str, Any]]) -> None:
        """
        Apply directives from LLM to testing strategy.

        Args:
            directives: List of directives from LLM
        """
        for directive in directives:
            directive_type = directive.get("type", "")

            if directive_type == "strategy":
                # Apply strategy directive
                strategy_name = directive.get("name", "")
                if strategy_name and self.strategy_balancer:
                    # Convert strategy name to class name format
                    if not strategy_name.endswith("Strategy"):
                        strategy_name = f"{strategy_name.capitalize()}Strategy"
                    
                    # Handle naming consistency - map legacy names to current names
                    if strategy_name == "SecurityFocusedStrategy" or strategy_name == "SecurityfocusedStrategy":
                        strategy_name = "SpecificationFocusedStrategy"
                    elif strategy_name == "MonitoredMethodFocusedStrategy" or strategy_name == "MonitoredmethodfocusedStrategy":
                        strategy_name = "SpecificationFocusedStrategy"

                    # Update strategy balancer weights
                    for strategy_info in self.strategy_balancer.strategies:
                        strategy = strategy_info["strategy"]
                        if strategy.__class__.__name__ == strategy_name:
                            strategy_info["weight"] *= 2.0  # Boost this strategy
                            self.logger.info(f"Boosted strategy weight for {strategy_name}")
                        else:
                            strategy_info["weight"] *= 0.8  # Reduce others

                    # Normalize weights
                    self.strategy_balancer._normalize_weights()

            elif directive_type == "focus":
                # Update focus areas for exploration through memory system
                target = directive.get("target", "")
                if target and hasattr(self.memory_system, 'exploration_optimizer'):
                    # Adjust exploration parameters
                    if "security" in target.lower() or "crypto" in target.lower() or "monitored" in target.lower():
                        # Support legacy "security" term and new "monitored method" terminology
                        if hasattr(self.memory_system.exploration_optimizer, 'exploration_parameters'):
                            self.memory_system.exploration_optimizer.exploration_parameters["monitored_method_factor"] = 0.8
                            # Check if we have specific focus on crypto vs general API
                            if "crypto" in target.lower():
                                self.memory_system.exploration_optimizer.exploration_parameters["crypto_spec_factor"] = 0.8
                            elif "api" in target.lower():
                                self.memory_system.exploration_optimizer.exploration_parameters["general_api_factor"] = 0.8
                            else:
                                # Balanced approach to both types
                                self.memory_system.exploration_optimizer.exploration_parameters["crypto_spec_factor"] = 0.6
                                self.memory_system.exploration_optimizer.exploration_parameters["general_api_factor"] = 0.6
                        else:
                            # Backward compatibility
                            self.memory_system.exploration_optimizer.security_focus_factor = 0.8
                    elif "diversity" in target.lower():
                        if hasattr(self.memory_system.exploration_optimizer, 'exploration_parameters'):
                            self.memory_system.exploration_optimizer.exploration_parameters["breadth_factor"] = 0.8
                            self.memory_system.exploration_optimizer.exploration_parameters["novelty_factor"] = 0.8
                        else:
                            # Backward compatibility
                            self.memory_system.exploration_optimizer.diversity_factor = 0.8
                    elif "exploration" in target.lower():
                        if hasattr(self.memory_system.exploration_optimizer, 'exploration_parameters'):
                            self.memory_system.exploration_optimizer.exploration_parameters["randomization_factor"] = 0.4
                        else:
                            # Backward compatibility
                            self.memory_system.exploration_optimizer.exploration_factor = 0.8

            elif directive_type == "explore":
                # Update exploration phase
                target = directive.get("target", "")
                if target and hasattr(self.memory_system, 'exploration_optimizer'):
                    # Use our enhanced phase-based approach if available
                    if hasattr(self.memory_system.exploration_optimizer, 'exploration_phases'):
                        if "initial" in target.lower() or "exploration" in target.lower():
                            self.memory_system.exploration_optimizer._transition_to_phase("initial_exploration")
                        elif "targeted" in target.lower() or "security" in target.lower() or "monitored" in target.lower():
                            self.memory_system.exploration_optimizer._transition_to_phase("targeted_exploration")
                        elif "deep" in target.lower() or "exploitation" in target.lower():
                            self.memory_system.exploration_optimizer._transition_to_phase("deep_exploration")
                        elif "coverage" in target.lower() or "optimize" in target.lower():
                            self.memory_system.exploration_optimizer._transition_to_phase("coverage_optimization")
                        elif "regression" in target.lower() or "revisit" in target.lower():
                            self.memory_system.exploration_optimizer._transition_to_phase("regression_testing")
                    else:
                        # Backward compatibility
                        if "exploration" in target.lower():
                            self.memory_system.exploration_optimizer.exploration_phase = "exploration"
                            self.memory_system.exploration_optimizer._adjust_parameters_for_phase("exploration")
                        elif "exploitation" in target.lower():
                            self.memory_system.exploration_optimizer.exploration_phase = "exploitation"
                            self.memory_system.exploration_optimizer._adjust_parameters_for_phase("exploitation")
                        elif "security" in target.lower():
                            self.memory_system.exploration_optimizer.exploration_phase = "security_focus"
                            self.memory_system.exploration_optimizer._adjust_parameters_for_phase("security_focus")

            # Log the directive application
            self.logger.info(f"Applied LLM directive: {directive_type} - {directive}")

    def _process_llm_suggestions(self, suggestions: List[Dict[str, Any]]) -> None:
        """
        Process suggestions from LLM action feedback.

        Args:
            suggestions: List of suggestions from LLM
        """
        if not suggestions:
            return

        # Apply high priority suggestions first
        for suggestion in suggestions:
            text = suggestion.get("text", "")
            priority = suggestion.get("priority", "medium")

            if not text:
                continue

            # Only process high priority suggestions for now
            if priority != "high":
                continue

            # Parse the suggestion to see if it's actionable
            if "try" in text.lower() or "should" in text.lower() or "recommend" in text.lower():
                # Extract key focus areas and update memory system focus
                if hasattr(self.memory_system, 'exploration_optimizer'):
                    explorer = self.memory_system.exploration_optimizer
                    
                    # Check if we have the new parameters structure
                    if hasattr(explorer, 'exploration_parameters'):
                        # New parameter structure
                        if "input" in text.lower():
                            # Increase focus on input fields
                            explorer.exploration_parameters["novelty_factor"] = 0.6
                        elif "button" in text.lower():
                            # Increase focus on buttons
                            explorer.exploration_parameters["breadth_factor"] = 0.7
                        elif "security" in text.lower() or "crypto" in text.lower() or "monitored" in text.lower():
                            # Increase focus on monitored methods with appropriate terminology
                            explorer.exploration_parameters["monitored_method_factor"] = 0.8
                            
                            # Specific crypto or API focus
                            if "crypto" in text.lower():
                                explorer.exploration_parameters["crypto_spec_factor"] = 0.8
                            elif "api" in text.lower() or "iterator" in text.lower():
                                explorer.exploration_parameters["general_api_factor"] = 0.8
                        elif "diversity" in text.lower() or "explore" in text.lower():
                            # Increase exploration
                            explorer.exploration_parameters["breadth_factor"] = 0.8
                            explorer.exploration_parameters["randomization_factor"] = 0.3
                    else:
                        # Legacy parameter structure
                        if "input" in text.lower():
                            # Increase focus on input fields
                            explorer.diversity_factor = 0.4
                        elif "button" in text.lower():
                            # Increase focus on buttons
                            explorer.diversity_factor = 0.6
                        elif "security" in text.lower() or "monitored" in text.lower():
                            # Increase security focus
                            explorer.security_focus_factor = 0.8
                        elif "diversity" in text.lower() or "explore" in text.lower():
                            # Increase exploration
                            explorer.exploration_factor = 0.8

            # Log the suggestion processing
            self.logger.info(f"Processed LLM suggestion: {text}")

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
