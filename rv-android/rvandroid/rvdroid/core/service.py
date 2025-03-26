# rvandroid/rvdroid/core/service.py
"""
Core service for RVDroid.

This module provides the central service that coordinates all RVDroid components,
manages the testing lifecycle, and integrates with the RV-Android framework.
"""

import time
from typing import Dict, Any, Optional, List

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription, ItemAction
from rvandroid.rvdroid.analysis.context.context_analyzer import ContextAnalyzer
from rvandroid.rvdroid.analysis.opportunity.opportunity_detector import OpportunityDetector
from rvandroid.rvdroid.analysis.progress.progress_tracker import ProgressTracker
from rvandroid.rvdroid.analysis.state_analyzer import StateAnalyzer
from rvandroid.rvdroid.executor.action_executor import ActionExecutor
from rvandroid.rvdroid.llm.llm_service import LLMService
from rvandroid.rvdroid.memory.exploration.exploration_optimizer import ExplorationOptimizer
from rvandroid.rvdroid.memory.long_term.long_term_memory import LongTermMemory
from rvandroid.rvdroid.memory.patterns.pattern_recognition import PatternRecognition
from rvandroid.rvdroid.memory.short_term.short_term_memory import ShortTermMemory
from rvandroid.rvdroid.strategy.balancer.strategy_balancer import StrategyBalancer
from rvandroid.rvdroid.strategy.strategy import StrategyRegistry
from rvandroid.rvdroid.uiautomator.adapter import UIAutomator2Adapter
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor


class RVDroidService:
    """
    Central service that coordinates all RVDroid components and testing activities.

    ### Architectural Decisions:
    - Implements a centralized coordination service for all RVDroid components
    - Uses a modular architecture with clear separation of concerns
    - Follows a layered design with analysis, strategy, memory, and execution components
    - Provides integration with RV-Android's static analysis and instrumentation systems
    - Supports dynamic strategy selection and optimization based on runtime feedback

    ### Role in the System:
    - Acts as the main entry point for RVDroid functionality
    - Coordinates the interaction between different RVDroid subsystems
    - Manages the testing lifecycle from initialization to result processing
    - Integrates with RV-Android's event bus, logging, and monitoring systems
    - Provides a clean API for controlling and querying RVDroid functionality
    - Enables effective test generation through LLM-guided exploration

    ### Key Considerations:
    - Handles complex coordination of testing activities
    - Manages state transitions and exploration strategies
    - Provides robust error handling and recovery mechanisms
    - Supports flexible configuration of testing parameters
    - Enables integration with various testing strategies and approaches
    - Facilitates LLM-guided testing for more intelligent exploration

    ### Integration Strategy:
    - Seamlessly integrates with RV-Android's instrumentation and analysis systems
    - Uses RV-Android's static analysis data to guide testing strategies
    - Publishes testing progress and results to RV-Android's event system
    - Provides hooks for custom testing strategies and analysis components
    - Supports flexible extension and customization of testing behavior
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None,
                 config: Optional[ComponentConfigurator] = None,
                 device_id: str = "emulator-5554",
                 use_llm: bool = True,
                 preferred_strategy: str = "SecurityFocusedStrategy"):
        """
        Initialize the RVDroid service.

        Args:
            static_data: Optional static analysis data
            config: Optional component configuration
            device_id: Target device ID
            use_llm: Whether to use LLM guidance
            preferred_strategy: Optional name of preferred strategy (default will be used if not specified)
        """
        import rvandroid.rvdroid.strategy.basic_strategies
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

        # Initialize performance monitor
        self.performance_monitor = PerformanceMonitor.get_instance()

        # Initialize core components
        self.logger.info("Initializing RVDroid core components")

        # Initialize UIAutomator adapter
        self.ui_adapter = UIAutomator2Adapter(device_id)

        # Initialize memory components
        self.short_term_memory = ShortTermMemory()
        self.long_term_memory = LongTermMemory("target_app", static_data) if static_data else None
        self.pattern_recognition = PatternRecognition(self.short_term_memory, self.long_term_memory)
        self.exploration_optimizer = ExplorationOptimizer(
            self.short_term_memory,
            self.long_term_memory,
            self.pattern_recognition
        )

        # Initialize analysis components
        self.state_analyzer = StateAnalyzer(static_data)
        self.opportunity_detector = OpportunityDetector(static_data)
        self.progress_tracker = ProgressTracker(static_data)
        self.context_analyzer = ContextAnalyzer(static_data)

        # Initialize action executor
        self.action_executor = ActionExecutor(device_id)

        # Initialize strategy components
        self.strategy_balancer = StrategyBalancer(static_data, use_llm_guidance=use_llm)
        self.current_strategy = None

        # Set preferred strategy if specified
        if self.preferred_strategy_name:
            self._set_preferred_strategy(self.preferred_strategy_name)

        # Initialize LLM service if needed
        self.llm_service = LLMService(static_data) if use_llm else None
        self.last_llm_guidance_time = 0
        self.llm_guidance_interval = 60  # Get new guidance every minute

        # Initialize tracking variables
        self.current_state: Optional[Dict[str, Any]] = None
        self.current_screen: Optional[ScreenDescription] = None
        self.last_action: Optional[ItemAction] = None
        self.execution_running = False
        self.start_time = 0
        self.execution_timeout = 0

        # Statistics
        self.stats = {
            "actions_executed": 0,
            "successful_actions": 0,
            "new_states": 0,
            "errors_detected": 0,
            "llm_guidance_count": 0
        }

        self.logger.info("RVDroid service initialized successfully")
        if use_llm:
            self.logger.info("LLM guidance enabled")
        if self.preferred_strategy_name:
            self.logger.info(f"Preferred strategy set to: {self.preferred_strategy_name}")

    def _set_preferred_strategy(self, strategy_name: str) -> bool:
        """
        Set the preferred strategy by name.

        Args:
            strategy_name: Name of the strategy class or strategy instance

        Returns:
            True if strategy was found and set as preferred, False otherwise
        """
        if not self.strategy_balancer or not self.strategy_balancer.strategies:
            self.logger.warning(f"Cannot set preferred strategy: no strategy balancer or strategies available")
            return False

        # Try to find the strategy by name match
        for strategy_info in self.strategy_balancer.strategies:
            strategy = strategy_info["strategy"]
            strategy_class_name = strategy.__class__.__name__

            # Check for match with class name or instance name
            if (strategy_name == strategy_class_name or
                    strategy_name == strategy.name or
                    strategy_class_name.lower().startswith(strategy_name.lower())):
                # Set as preferred
                self.strategy_balancer.preferred_strategy_info = strategy_info
                self.strategy_balancer.last_strategy_switch = time.time()

                self.logger.info(f"Set preferred strategy to {strategy_class_name} ({strategy.name})")
                return True

        self.logger.warning(f"Could not find strategy matching '{strategy_name}'")
        return False

    def start_testing(self, package_name: str, activity: Optional[str] = None,
                      timeout: int = 3600, llm_guidance: bool = True) -> bool:
        """
        Start testing an application.

        Args:
            package_name: Application package name
            activity: Optional activity to start
            timeout: Execution timeout in seconds
            llm_guidance: Whether to use LLM guidance

        Returns:
            True if started successfully, False otherwise
        """
        self.logger.info(f"Starting test execution for {package_name}")

        # Set execution parameters
        self.execution_running = True
        self.start_time = time.time()
        self.execution_timeout = timeout

        # Store the app package name for use in other methods
        self.app_package_name = package_name

        try:
            # Start application
            if not self.ui_adapter.start_app(package_name, activity):
                self.logger.error(f"Failed to start app: {package_name}")
                return False

            # Get initial state
            with self.performance_monitor.measure_time("get_initial_state"):
                self._update_current_state()

            # Main execution loop is handled by execute_testing_loop()
            return True

        except Exception as e:
            self.logger.error(f"Error starting testing: {e}")
            self.execution_running = False
            return False

    def execute_testing_loop(self) -> Dict[str, Any]:
        """
        Execute the main testing loop.

        Returns:
            Results dictionary with execution statistics
        """
        self.logger.info("Starting testing loop")

        if not self.execution_running:
            self.logger.error("Cannot execute testing loop: testing not started")
            return {"error": "Testing not started"}

        try:
            # Main testing loop
            while self.execution_running:
                # Check timeout
                current_time = time.time()
                elapsed_time = current_time - self.start_time

                if elapsed_time >= self.execution_timeout:
                    self.logger.info(f"Execution timeout reached: {self.execution_timeout}s")
                    break

                # Execute one test iteration
                with self.performance_monitor.measure_time("test_iteration"):
                    result = self._execute_test_iteration()
                    print(f"*** Result: {result}")
                    input("$$$ Press Enter to continue...")

                # Update statistics
                if result.get("success", False):
                    self.stats["successful_actions"] += 1

                if result.get("new_state", False):
                    self.stats["new_states"] += 1

                # Small delay between iterations
                time.sleep(0.5) # TODO externalize

            # Collect final results
            results = self._collect_results()

            self.logger.info(f"Testing loop completed with {self.stats['actions_executed']} actions executed")
            return results

        except Exception as e:
            self.logger.error(f"Error in testing loop: {e}")
            self.execution_running = False
            return {"error": str(e)}

        finally:
            # Ensure execution flag is reset
            self.execution_running = False

    def stop_testing(self) -> Dict[str, Any]:
        """
        Stop the current testing execution.

        Returns:
            Results dictionary with execution statistics
        """
        self.logger.info("Stopping test execution")

        # Set flag to stop execution
        self.execution_running = False

        # Collect results
        results = self._collect_results()

        return results

    def process_results(self, logcat_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Process results after testing has completed.

        Args:
            logcat_file: Optional path to logcat file

        Returns:
            Results dictionary with processed metrics
        """
        self.logger.info("Processing test results")

        # If logcat file is provided, parse it for coverage and violations
        if logcat_file:
            self.logger.info(f"Parsing logcat file: {logcat_file}")
            # This would typically use the LogcatRepository to parse coverage and violations
            # For now, we'll just return the basic statistics

        # For now, just return the statistics we've collected
        return self._collect_results()

    def get_current_state(self) -> Optional[Dict[str, Any]]:
        """
        Get the current application state.

        Returns:
            Current state dictionary or None if not available
        """
        return self.current_state

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get current execution statistics.

        Returns:
            Dictionary with execution statistics
        """
        current_time = time.time()
        elapsed_time = current_time - self.start_time if self.start_time > 0 else 0

        stats = {
            "elapsed_time": elapsed_time,
            "running": self.execution_running,
            **self.stats
        }

        # Add component-specific statistics
        if self.progress_tracker:
            stats["progress"] = self.progress_tracker.get_progress_summary()

        if self.short_term_memory:
            stats["short_term_memory"] = self.short_term_memory.get_memory_stats()

        if self.long_term_memory:
            stats["long_term_memory"] = self.long_term_memory.get_memory_stats()

        if self.strategy_balancer:
            stats["strategies"] = self.strategy_balancer.get_strategy_statistics()

        if self.pattern_recognition:
            stats["patterns"] = self.pattern_recognition.get_pattern_stats()

        return stats

    def execute_specific_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a specific action.

        Args:
            action: Action dictionary with type, target, and parameters

        Returns:
            Result dictionary with success status and state change info
        """
        self.logger.info(f"Executing specific action: {action}")

        try:
            # Execute the action
            success = self.action_executor.execute_action(action)

            # Update current state
            previous_state = self.current_state
            self._update_current_state()

            # Check if state changed
            new_state = False
            if previous_state and self.current_state:
                new_state = previous_state.get("fingerprint") != self.current_state.get("fingerprint")

            # Create result
            result = {
                "success": success,
                "new_state": new_state,
                "previous_state": previous_state.get("fingerprint") if previous_state else None,
                "current_state": self.current_state.get("fingerprint") if self.current_state else None
            }

            # Update statistics
            self.stats["actions_executed"] += 1

            return result

        except Exception as e:
            self.logger.error(f"Error executing specific action: {e}")
            return {"success": False, "error": str(e)}

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

        # Save any state if needed
        if self.long_term_memory:
            pass  # save memory when implemented

    def _execute_test_iteration(self) -> Dict[str, Any]:
        """
        Execute a single test iteration.

        Returns:
            Result dictionary with execution details
        """
        print("Executing test iteration .......................")
        try:
            # 1. Analyze current state
            state_analysis = self._analyze_state()
            print("State analysis: ", state_analysis)

            # Check if app is in foreground
            if not state_analysis or state_analysis.get("app_in_foreground", False) == False:
                self.logger.warning("App not in foreground, trying to recover...")

                # Use the correct attribute for the target app's package name
                app_package = getattr(self, 'app_package_name', None)

                if app_package and not self.ui_adapter.ensure_app_in_foreground(app_package):
                    self.logger.error("Failed to bring app to foreground, skipping iteration")
                    return {"success": False, "error": "App not in foreground"}

                # Update state after recovery
                state_analysis = self._analyze_state()

            # 2. Get LLM guidance if it's time
            current_time = time.time()
            if self.use_llm and self.llm_service and (
                    current_time - self.last_llm_guidance_time >= self.llm_guidance_interval):
                self._get_llm_guidance(state_analysis)
                self.last_llm_guidance_time = current_time

            # 3. Select the strategy to use
            if self.strategy_balancer:
                self.current_strategy = self.strategy_balancer.select_strategy(state_analysis)
                print("=== Selected strategy: ", self.current_strategy)

            if not self.current_strategy:
                # Fall back to default strategy
                self.current_strategy = StrategyRegistry.create_strategy("RandomStrategy", self.static_data)
                print("=== Fallback strategy: ", self.current_strategy)

            # 4. Generate next action
            action = self._generate_action()

            if not action:
                self.logger.warning("No action generated, using fallback")
                action = self._generate_fallback_action()

                if not action:
                    self.logger.error("Failed to generate fallback action, skipping iteration")
                    return {"success": False, "error": "No action available"}

            # 5. Execute action
            previous_state_fingerprint = self.current_state.get("fingerprint") if self.current_state else None

            # Record action in memory
            self.last_action = action
            self.short_term_memory.record_action(action)

            # Execute the action
            success = self.action_executor.execute_item_action(action)

            # 6. Update state and record transition
            self._update_current_state()

            # 7. Check if state changed
            new_state = False
            current_fingerprint = self.current_state.get("fingerprint") if self.current_state else None

            if previous_state_fingerprint and current_fingerprint:
                new_state = previous_state_fingerprint != current_fingerprint

                # Record transition
                if success:
                    self.short_term_memory.record_transition(
                        previous_state_fingerprint,
                        current_fingerprint,
                        action,
                        success
                    )

                    if self.long_term_memory:
                        self.long_term_memory.record_transition(
                            previous_state_fingerprint,
                            current_fingerprint,
                            action,
                            success
                        )

            # 8. Create result
            result = {
                "success": success,
                "new_state": new_state,
                "previous_state": previous_state_fingerprint,
                "state_fingerprint": current_fingerprint,
                "action_id": action.id,
                "strategy": self.current_strategy.name if self.current_strategy else "unknown"
            }

            # 9. Get action feedback from LLM if enabled
            if self.use_llm and self.llm_service and new_state:
                # TODO implementar ........
                self._get_action_feedback(action, result)

            # 10. Update strategy feedback
            if self.current_strategy:
                self.current_strategy.update_feedback(action, result)

                if self.strategy_balancer:
                    self.strategy_balancer.update_performance(self.current_strategy, action, result)

            # 11. Update exploration optimizer
            if self.exploration_optimizer:
                self.exploration_optimizer.record_action_result(action, result)

            # 12. Update statistics
            self.stats["actions_executed"] += 1

            return result

        except Exception as e:
            self.logger.error(f"Error in test iteration: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}


    def _get_action_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Get feedback from the LLM about an executed action and its result.

        Args:
            action: Action that was executed
            result: Execution result
        """
        if not self.use_llm or not self.llm_service:
            return

        try:
            # Prepare action data for LLM
            action_data = {
                "id": action.id,
                "text": action.text,
                "type": self._get_action_type(action.text),
                "reaches_mop": action.reaches_mop,
                "directly_reaches_mop": action.directly_reaches_mop
            }

            # Get feedback from LLM
            feedback = self.llm_service.get_action_feedback(action_data, result, self.current_state or {})

            # Process suggestions if available
            if "suggestions" in feedback and feedback["suggestions"]:
                self._process_llm_suggestions(feedback["suggestions"])

            self.logger.debug(f"Received LLM feedback for action {action.id}")

        except Exception as e:
            self.logger.error(f"Error getting LLM action feedback: {e}")

    def _get_llm_guidance(self, state_analysis: Dict[str, Any]) -> None:
        """
        Get guidance from the LLM.

        Args:
            state_analysis: Analysis of the current state
        """
        if not self.llm_service:
            return

        # Prepare exploration context
        exploration_context = {
            "exploration_phase": self.progress_tracker.get_current_phase() if self.progress_tracker else "exploration",
            "metrics": self.progress_tracker.get_progress_summary() if self.progress_tracker else {},
            "history": list(self.short_term_memory.state_history) if self.short_term_memory else []
        }

        try:
            # Get strategic guidance from LLM
            guidance = self.llm_service.get_strategic_guidance(
                "exploration",
                self.current_state or {},
                exploration_context
            )

            # Apply directives to testing strategy
            if "directives" in guidance and guidance["directives"]:
                self._apply_llm_directives(guidance["directives"])

            # Update statistics
            self.stats["llm_guidance_count"] += 1

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
            # The app package name should be available when the service is initialized
            # or through the current task configuration
            app_package = getattr(self, 'app_package_name', current_package)

            app_in_foreground = (current_package == app_package)

            # Analyze state with different analyzers
            state_analysis = self.state_analyzer.analyze_state(self.current_screen, self.current_state)

            # Add app_in_foreground flag
            state_analysis["app_in_foreground"] = app_in_foreground

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

        print(f"********** Generating action... strategy: {self.current_strategy} ::: screen={self.current_screen} ::::::::::::: {self.current_state}")

        try:
            # Get history if needed by the strategy
            history = list(self.short_term_memory.state_history)
            print(f"History: {history}")

            # Use current strategy to generate action
            action = self.current_strategy.generate_action(
                self.current_screen,
                self.current_state or {},
                history
            )
            print(f"==== Generated action: {action}")

            input(">>> Press Enter to continue...")

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
        print("%%%%%%%%%%%%%%%%%%% Generating fallback action...")
        if not self.current_screen or not self.current_screen.items:
            return None

        # Get all available actions
        available_actions = []
        for item in self.current_screen.items:
            available_actions.extend(item.actions)

        if not available_actions:
            return None

        # Select a random action
        import random
        return random.choice(available_actions)

    def _update_current_state(self) -> None:
        """
        Update the current application state.
        """
        try:
            # Get UI state from adapter
            ui_state = self.ui_adapter.get_ui_state(force_refresh=True)

            if not ui_state:
                self.logger.error("Failed to get UI state")
                return

            # Parse state to create ScreenDescription
            self.current_screen = self.ui_adapter.parse_screen(ui_state, self.static_data)

            # Generate fingerprint and metadata
            fingerprint = self._generate_state_fingerprint(self.current_screen, ui_state)

            # Create state data
            self.current_state = {
                "activity": ui_state.get("activity", "unknown"),
                "package_name": ui_state.get("package_name", "unknown"),
                "fingerprint": fingerprint,
                "timestamp": time.time(),
                "interactive_elements_count": len(self.current_screen.items)
            }

            # Record in memory
            is_new_state = fingerprint not in self.short_term_memory.state_history
            self.short_term_memory.record_state(self.current_state)

            if self.long_term_memory:
                self.long_term_memory.record_state(self.current_state, is_new_state)

        except Exception as e:
            self.logger.error(f"Error updating current state: {e}")

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
        Collect results from the testing execution.

        Returns:
            Results dictionary
        """
        current_time = time.time()
        elapsed_time = current_time - self.start_time if self.start_time > 0 else 0

        results = {
            "elapsed_time": elapsed_time,
            "actions_executed": self.stats["actions_executed"],
            "successful_actions": self.stats["successful_actions"],
            "new_states": self.stats["new_states"],
            "errors_detected": self.stats["errors_detected"],
            "states_explored": len(self.short_term_memory.state_history) if self.short_term_memory else 0
        }

        # Add component-specific results
        if self.progress_tracker:
            results["progress"] = self.progress_tracker.get_progress_summary()

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

                    # Update strategy balancer weights
                    for strategy_info in self.strategy_balancer.strategies:
                        strategy = strategy_info["strategy"]
                        if strategy.__class__.__name__ == strategy_name:
                            strategy_info["weight"] *= 2.0  # Boost this strategy
                        else:
                            strategy_info["weight"] *= 0.8  # Reduce others

                    # Normalize weights
                    self.strategy_balancer._normalize_weights()

            elif directive_type == "focus":
                # Update focus areas for opportunity detector
                target = directive.get("target", "")
                if target and self.opportunity_detector:
                    # Adjust opportunity detector scoring
                    if "security" in target.lower():
                        self.opportunity_detector.security_focus_factor = 0.8
                    elif "input" in target.lower():
                        # Prioritize text inputs
                        if hasattr(self.opportunity_detector, "exploration_scores"):
                            self.opportunity_detector.exploration_scores["element_types"]["EditText"] *= 1.5
                    elif "button" in target.lower() or "click" in target.lower():
                        # Prioritize buttons
                        if hasattr(self.opportunity_detector, "exploration_scores"):
                            self.opportunity_detector.exploration_scores["element_types"]["Button"] *= 1.5

            elif directive_type == "explore":
                # Update exploration parameters
                target = directive.get("target", "")
                if target and self.exploration_optimizer:
                    if "diversity" in target.lower():
                        self.exploration_optimizer.diversity_factor = 0.8
                    elif "security" in target.lower():
                        self.exploration_optimizer.security_focus_factor = 0.8
                    elif "new" in target.lower() or "unexplored" in target.lower():
                        self.exploration_optimizer.exploration_factor = 0.8

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
                # Extract key focus areas
                if "input" in text.lower() and self.opportunity_detector:
                    # Increase weight for text inputs
                    if hasattr(self.opportunity_detector, "exploration_scores"):
                        self.opportunity_detector.exploration_scores["element_types"]["EditText"] *= 1.5
                elif "button" in text.lower() and self.opportunity_detector:
                    # Increase weight for buttons
                    if hasattr(self.opportunity_detector, "exploration_scores"):
                        self.opportunity_detector.exploration_scores["element_types"]["Button"] *= 1.5
                elif "security" in text.lower() and self.exploration_optimizer:
                    # Increase security focus
                    self.exploration_optimizer.security_focus_factor = 0.8

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
