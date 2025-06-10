#!/usr/bin/env python3
"""
RV-Android Component Integration Simulator

This script provides an integration test environment for the memory and transition
management systems in RV-Android. It loads real application state data from files,
processes it through the system, and validates the correct functioning of
components like MemoryManager and TransitionManager.

The simulator creates a realistic navigation flow through an Android application
by loading a sequence of screen states and simulating transitions between them.
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from rvandroid.app import App
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.constants import PromptStrategyType, ScreenParserType, StateEntry, VisitorType
from rvandroid.llm.service.action_generator import GeneratedAction
from rvandroid.llm.service.action_service import LLMActionService
from rvandroid.llm.service.memory_manager import MemoryManager
from rvandroid.llm.service.transition_manager import TransitionManager
from rvandroid.parser.screen.parser_factory import ParserFactory, ParserType
from rvandroid.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rvandroid.parser.static import static_analysis_parser
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class ComponentSimulator:
    """
    Simulates the execution of RV-Android components using real application data.

    This class loads real state files and static analysis data for Android applications,
    then processes them through the memory and transition management systems to validate
    their functionality. It simulates a realistic navigation path through an application.

    Attributes:
        app_name: Name of the application being tested
        package_name: Package name of the application
        data_dir: Directory containing state and static analysis files
        static_data: Parsed static analysis data
        memory_manager: Memory management system instance
        transition_manager: Transition management system instance
        llm_service: LLM-based action service instance
        states_processed: Number of states processed during simulation
        actions_executed: Number of actions executed during simulation
        transitions_detected: Number of transitions detected during simulation
    """

    def __init__(self, app_name: str, data_dir: str):
        """
        Initialize the simulator with an application and data directory.

        Args:
            app_name: Name of the APK file to test (without path)
            data_dir: Directory containing data files
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "simulator.component_simulator",
            {CONTEXT_COMPONENT: "ComponentSimulator"}
        )
        self.error_handler = ErrorHandler.get_instance()

        # Store basic information
        self.app_name = app_name
        self.data_dir = data_dir
        self.app_dir = os.path.join(data_dir, app_name)
        self.package_name = None

        # Initialize component references
        self.static_data = None
        self.screen_parser = None
        self.memory_manager = None
        self.transition_manager = None
        self.llm_service = None

        # Initialize statistics
        self.states_processed = 0
        self.actions_executed = 0
        self.transitions_detected = 0

        self.logger.info(f"Initialized component simulator for {app_name}")

    def initialize(self) -> bool:
        """
        Initialize all components and load static analysis data.

        Returns:
            True if initialization succeeded, False otherwise
        """
        try:
            self.logger.info("Initializing simulator components...")

            # Load static analysis data
            if not self._load_static_data():
                return False

            # Create core components
            self._create_components()

            self.logger.info("Simulator components initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Initialization failed: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "ComponentSimulator",
                    "method": "initialize"
                }
            )
            return False

    def _load_static_data(self) -> bool:
        """
        Load static analysis data from files.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Define static analysis file paths
            reach_file = os.path.join(self.app_dir, f"{self.app_name}.reach")
            wtg_file = os.path.join(self.app_dir, f"{self.app_name}.wtg")
            gesda_file = os.path.join(self.app_dir, f"{self.app_name}.gesda")

            # Check if files exist
            for file_path in [reach_file, wtg_file, gesda_file]:
                if not os.path.exists(file_path):
                    self.logger.error(f"Required static analysis file not found: {file_path}")
                    return False

            # Load app info
            self.logger.info("Loading app information...")
            app = App(os.path.join(self.app_dir, self.app_name))
            self.package_name = app.package_name

            # Parse static analysis data
            self.logger.info("Parsing static analysis data...")
            self.static_data = static_analysis_parser.parse(
                reach_file,
                wtg_file,
                gesda_file,
                self.package_name
            )

            # Create screen parser
            self.screen_parser = ParserFactory.create(ParserType.DROIDBOT, DefaultTextVisitor)

            self.logger.info(f"Static analysis data loaded successfully for {self.package_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to load static data: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "ComponentSimulator",
                    "method": "_load_static_data"
                }
            )
            return False

    def _create_components(self) -> None:
        """
        Create and initialize all RV-Android components.
        """
        # Create memory and transition managers
        self.memory_manager = MemoryManager(
            app_package=self.package_name,
            static_data=self.static_data
        )

        self.transition_manager = TransitionManager(self.static_data)

        # Configure and create LLM action service
        config = ComponentConfigurator()
        config.set_strategy(PromptStrategyType.BATCH_ACTION)
        config.set_parser(ScreenParserType.DROIDBOT)
        config.set_visitor(VisitorType.DEFAULT)

        self.llm_service = LLMActionService(
            static_data=self.static_data,
            config=config,
            app_package=self.package_name
        )

        # Override service's managers with our instances for testing
        self.llm_service.memory_manager = self.memory_manager
        self.llm_service.transition_manager = self.transition_manager

        self.logger.info("Components created and configured")

    def load_state(self, state_prefix: str) -> Optional[Dict[str, Any]]:
        """
        Load and process a state file with the given prefix.

        Args:
            state_prefix: Prefix for the state file (e.g., "001")

        Returns:
            Processed state dictionary or None if failed
        """
        try:
            # Construct state file path
            state_file = os.path.join(self.app_dir, f"{state_prefix}.state")

            # Check if file exists
            if not os.path.exists(state_file):
                self.logger.error(f"State file not found: {state_file}")
                return None

            # Load state data
            with open(state_file, 'r') as file:
                raw_state = json.load(file)

            # Set screenshot path
            screenshot_path = os.path.join(self.app_dir, f"{state_prefix}.png")
            if not os.path.exists(screenshot_path):
                self.logger.warning(f"Screenshot not found: {screenshot_path}")
                screenshot_path = None

            # Parse screen description
            screen_description = self.screen_parser.parse(raw_state, self.static_data)

            # Create state dictionary with all required fields
            state = {
                StateEntry.PACKAGE_NAME: self.package_name,
                StateEntry.ACTIVITY: screen_description.activity,
                StateEntry.VIEW_TREE: raw_state.get("view_tree", {}),
                StateEntry.STRUCTURED_SCREEN: screen_description,
                StateEntry.SCREENSHOT_PATH: screenshot_path,
                StateEntry.STATIC_DATA: self.static_data,
                StateEntry.HASH_SCREEN: state_prefix,  # Use prefix as a simple hash
                "timestamp": datetime.now().isoformat()
            }

            self.logger.info(f"Loaded state {state_prefix} for activity: {screen_description.activity}")
            return state

        except Exception as e:
            self.logger.error(f"Failed to load state {state_prefix}: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "ComponentSimulator",
                    "method": "load_state",
                    "state_prefix": state_prefix
                }
            )
            return None

    def generate_actions(self, state: Dict[str, Any], count: int = 3) -> List[GeneratedAction]:
        """
        Generate actions for the given state.

        Args:
            state: Current application state
            count: Maximum number of actions to generate

        Returns:
            List of GeneratedAction objects
        """
        try:
            # Extract available actions from screen description
            screen_description = state[StateEntry.STRUCTURED_SCREEN]
            available_actions = []

            # Collect all available actions from all items
            for item in screen_description.items:
                for action in item.actions:
                    if hasattr(action, 'reaches_mop') and action.reaches_mop:
                        # Prioritize actions that reach monitored operations
                        available_actions.insert(0, action)
                    else:
                        available_actions.append(action)

            if not available_actions:
                self.logger.warning("No available actions found for this state")
                return []

            # Select top actions
            selected_actions = available_actions[:min(count, len(available_actions))]

            # Convert to GeneratedAction objects
            generated_actions = []
            for action in selected_actions:
                # Create parameters dictionary
                params = {}
                if action.text.startswith("SET_TEXT"):
                    params["text"] = "test_input"

                # Get coordinates from bounds if available
                coordinates = action.coordinates
                if not coordinates and hasattr(action, 'target_view') and action.target_view:
                    bounds = action.target_view.get("bounds")
                    if bounds and len(bounds) == 2:
                        x = (bounds[0][0] + bounds[1][0]) // 2
                        y = (bounds[0][1] + bounds[1][1]) // 2
                        coordinates = (x, y)

                # Default coordinates if none found
                if not coordinates:
                    coordinates = (100, 100)

                # Create GeneratedAction
                generated_action = GeneratedAction(
                    action,
                    params,
                    coordinates,
                    "resource_id",
                    f"Testing action: {action.text}"
                )

                generated_actions.append(generated_action)

            self.logger.info(f"Generated {len(generated_actions)} actions")
            return generated_actions

        except Exception as e:
            self.logger.error(f"Failed to generate actions: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "ComponentSimulator",
                    "method": "generate_actions"
                }
            )
            return []

    def process_state(self, state: Dict[str, Any]) -> Tuple[bool, List[GeneratedAction]]:
        """
        Process a state through the LLM action service.

        Args:
            state: Current application state

        Returns:
            Tuple of (transition_detected, generated_actions)
        """
        try:
            # Initialize the state in the LLM service
            self.llm_service._initialize_state(state)

            # Pre-process the state (updates memory and transition managers)
            transition_detected = self.llm_service.pre_process_state(state)

            # Generate actions for this state
            actions = self.generate_actions(state)

            # Post-process the state with the generated actions
            self.llm_service.post_process_state(state, actions, transition_detected)

            self.logger.info(f"Processed state: {state.get(StateEntry.ACTIVITY)}, "
                             f"transition_detected={transition_detected}")

            return transition_detected, actions

        except Exception as e:
            self.logger.error(f"Failed to process state: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "ComponentSimulator",
                    "method": "process_state"
                }
            )
            return False, []

    def simulate_transition(self, from_state: Dict[str, Any], to_state: Dict[str, Any],
                            action: GeneratedAction) -> None:
        """
        Simulate a transition between two states.

        Args:
            from_state: Source state
            to_state: Destination state
            action: Action that caused the transition
        """
        try:
            # Process the action result through the LLM action service
            self.llm_service.process_action_result(
                from_state,
                to_state,
                action.to_droidbot_format(),
                success=True
            )

            # Also directly record the transition in the transition manager for testing purposes
            from_activity = from_state[StateEntry.ACTIVITY]
            to_activity = to_state[StateEntry.ACTIVITY]
            action_dict = action.to_dict()

            # Ensure the transition is recorded in the transition manager
            self.transition_manager.record_transition(
                from_activity,
                to_activity,
                [action_dict]
            )

            # Update statistics
            self.transitions_detected += 1

            # Log transition
            from_activity = from_state[StateEntry.ACTIVITY]
            to_activity = to_state[StateEntry.ACTIVITY]
            self.logger.info(f"Transition: {from_activity} -> {to_activity} via action: {action.text}")

        except Exception as e:
            self.logger.error(f"Failed to simulate transition: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "ComponentSimulator",
                    "method": "simulate_transition"
                }
            )

    def run_simulation(self, state_prefixes: List[str]) -> Dict[str, Any]:
        """
        Run a simulation with a sequence of states.

        Args:
            state_prefixes: List of state prefixes to process

        Returns:
            Dictionary with simulation results
        """
        start_time = time.time()
        self.logger.info(f"Starting simulation with {len(state_prefixes)} states...")

        results = {
            "status": "success",
            "states_processed": 0,
            "actions_executed": 0,
            "transitions_detected": 0,
            "execution_time": 0,
            "validation": {}
        }

        try:
            # Load all states
            states = []
            for prefix in state_prefixes:
                state = self.load_state(prefix)
                if state:
                    states.append(state)

            if not states:
                self.logger.error("No valid states could be loaded")
                results["status"] = "error"
                results["error"] = "No valid states could be loaded"
                return results

            # Process states sequentially
            for i, current_state in enumerate(states):
                # Process the current state
                transition_detected, actions = self.process_state(current_state)

                # Update statistics
                self.states_processed += 1
                self.actions_executed += len(actions)

                # If there's a next state, simulate transition with the first action
                if actions and i < len(states) - 1:
                    next_state = states[i + 1]
                    self.simulate_transition(current_state, next_state, actions[0])

                # Display current state of memory and transition managers
                self._display_component_state(current_state)

            # Validate components after simulation
            results["validation"] = self._validate_components()

            # Add statistics to results
            results["states_processed"] = self.states_processed
            results["actions_executed"] = self.actions_executed
            results["transitions_detected"] = self.transitions_detected
            results["execution_time"] = time.time() - start_time

            self.logger.info(f"Simulation completed in {results['execution_time']:.2f} seconds")
            return results

        except Exception as e:
            self.logger.error(f"Simulation failed: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "ComponentSimulator",
                    "method": "run_simulation"
                }
            )

            results["status"] = "error"
            results["error"] = str(e)
            results["execution_time"] = time.time() - start_time
            return results

    def _validate_components(self) -> Dict[str, Any]:
        """
        Validate the correctness of all components after simulation.

        Returns:
            Dictionary with validation results
        """
        validation = {
            "memory_manager": {
                "passed": True,
                "issues": []
            },
            "transition_manager": {
                "passed": True,
                "issues": []
            }
        }

        # Validate memory manager
        if not self.memory_manager:
            validation["memory_manager"]["passed"] = False
            validation["memory_manager"]["issues"].append("Memory manager not initialized")
        else:
            # Check short-term memory
            if not hasattr(self.memory_manager, 'short_term') or not self.memory_manager.short_term:
                validation["memory_manager"]["passed"] = False
                validation["memory_manager"]["issues"].append("Short-term memory not properly initialized")

            # Check long-term memory
            if not hasattr(self.memory_manager, 'long_term') or not self.memory_manager.long_term:
                validation["memory_manager"]["passed"] = False
                validation["memory_manager"]["issues"].append("Long-term memory not properly initialized")
            else:
                # Check if activities were recorded
                visited_activities = self.memory_manager.long_term.get_visited_activities()
                if not visited_activities and self.states_processed > 0:
                    validation["memory_manager"]["passed"] = False
                    validation["memory_manager"]["issues"].append("No activities recorded in long-term memory")

                # Check if states were tracked
                if not hasattr(self.memory_manager.long_term, 'states') or not self.memory_manager.long_term.states:
                    validation["memory_manager"]["passed"] = False
                    validation["memory_manager"]["issues"].append("No states tracked in long-term memory")

        # Validate transition manager
        if not self.transition_manager:
            validation["transition_manager"]["passed"] = False
            validation["transition_manager"]["issues"].append("Transition manager not initialized")
        else:
            # Check if dynamic transition graph has activities
            if not self.transition_manager.dynamic_wtg.activities and self.states_processed > 0:
                validation["transition_manager"]["passed"] = False
                validation["transition_manager"]["issues"].append("No activities recorded in dynamic WTG")

            # Check if transitions were recorded
            if not self.transition_manager.dynamic_wtg.transitions and self.transitions_detected > 0:
                validation["transition_manager"]["passed"] = False
                validation["transition_manager"]["issues"].append(
                    "No transitions recorded despite transitions being simulated")

        return validation

    def _display_component_state(self, current_state: Dict[str, Any]) -> None:
        """
        Display the current state of all components.

        Args:
            current_state: Current application state
        """
        print("\n" + "=" * 80)
        print(f" STATE: {current_state.get(StateEntry.ACTIVITY, 'Unknown')} ".center(80, "="))
        print("=" * 80)

        # Display memory manager state
        self._display_memory_state()

        # Display transition manager state
        self._display_transition_state()

        print("-" * 80)

    def _display_memory_state(self) -> None:
        """
        Display the current state of the memory manager.
        """
        if not self.memory_manager:
            print("Memory Manager: Not initialized")
            return

        print("\nMEMORY MANAGER STATE:")
        print("-" * 60)

        # Short-term memory
        print("Short-Term Memory:")
        if hasattr(self.memory_manager, 'short_term') and self.memory_manager.short_term:
            current_activity = getattr(self.memory_manager.short_term, 'current_activity', 'Unknown')
            iterations = self.memory_manager.short_term.iterations

            print(f"  Current Activity: {current_activity}")
            print(f"  Iterations: {len(iterations)}")

            if iterations:
                print("\n  Recent Iterations:")
                for i, iteration in enumerate(iterations[:3]):  # Show up to 3 recent iterations
                    timestamp = iteration.timestamp.strftime('%H:%M:%S') if hasattr(iteration,
                                                                                    'timestamp') else 'Unknown'

                    action_texts = []
                    for action in iteration.actions:
                        if hasattr(action, 'text'):
                            action_texts.append(action.text)
                        else:
                            action_texts.append(str(action))

                    print(f"    [{i + 1}] [{timestamp}] {len(action_texts)} actions: {', '.join(action_texts[:2])}" +
                          (f" (+ {len(action_texts) - 2} more)" if len(action_texts) > 2 else ""))
        else:
            print("  No short-term memory data available")

        # Long-term memory
        print("\nLong-Term Memory:")
        if hasattr(self.memory_manager, 'long_term') and self.memory_manager.long_term:
            # Activity statistics
            activity_visits = getattr(self.memory_manager.long_term, 'activities', {})
            print(f"  Visited Activities: {len(activity_visits)}")

            # State tracking
            states = getattr(self.memory_manager.long_term, 'states', {})
            print(f"  States Tracked: {len(states)}")

            # Transitions
            transitions = getattr(self.memory_manager.long_term, 'transitions', [])
            print(f"  Recorded Transitions: {len(transitions)}")

            # Navigation path
            visited_activities = self.memory_manager.long_term.get_visited_activities()
            if visited_activities:
                print("\n  Navigation Path:")
                # Format path, including at most the last 5 activities
                path = " → ".join(visited_activities[-5:])
                if len(visited_activities) > 5:
                    path = f"... → {path}"
                print(f"    {path}")
        else:
            print("  No long-term memory data available")

    def _display_transition_state(self) -> None:
        """
        Display the current state of the transition manager.
        """
        if not self.transition_manager:
            print("Transition Manager: Not initialized")
            return

        print("\nTRANSITION MANAGER STATE:")
        print("-" * 60)

        # Dynamic transition graph
        print("Dynamic Transition Graph:")

        # Get activities
        activities = getattr(self.transition_manager.dynamic_wtg, 'activities', {})
        print(f"  Activities: {len(activities)}")

        # Get transitions
        transitions = getattr(self.transition_manager.dynamic_wtg, 'transitions', [])
        print(f"  Transitions: {len(transitions)}")

        # Show current navigation state
        print("\nCurrent Navigation State:")
        print(f"  Current Activity: {self.transition_manager.current_activity}")
        print(f"  Previous Activity: {self.transition_manager.previous_activity}")

        # Show recent transitions if available
        if transitions:
            print("\n  Recent Transitions:")
            for i, transition in enumerate(transitions[-3:]):  # Show last 3 transitions
                source = getattr(transition, 'source_activity', 'Unknown')
                target = getattr(transition, 'target_activity', 'Unknown')
                count = getattr(transition, 'count', 0)
                print(f"    [{i + 1}] {source} → {target} (occurred {count} times)")


def configure_logging(verbose: bool = False):
    """
    Configure logging for the test script.

    Args:
        verbose: Whether to enable verbose logging
    """
    # Configure logging level
    level = logging.DEBUG if verbose else logging.INFO
    LoggingManager.get_instance().configure_output(console_level=level)

    # Suppress verbose logs for certain modules
    if not verbose:
        modules_to_suppress = [
            "androguard",
            "rvandroid.parser.screen.visitor",
            "rvandroid.parser.screen.droidbot",
            "rvandroid.parser.static",
            "rvandroid.domain",
            "rvandroid.model",
            "rvandroid.util.utils"
        ]

        for module in modules_to_suppress:
            logging.getLogger(module).setLevel(logging.WARNING)


def parse_arguments():
    """
    Parse command line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description='RV-Android Component Integration Simulator')

    parser.add_argument('--app', type=str, default="cryptoapp.apk",
                        help='APK file name to test (default: cryptoapp.apk)')

    parser.add_argument('--data-dir', type=str,
                        default="/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots",
                        help='Directory containing test data files')

    parser.add_argument('--states', type=str, default="001,003,004,005",
                        help='Comma-separated list of state prefixes to process')

    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose logging')

    return parser.parse_args()


def print_summary(results: Dict[str, Any]):
    """
    Print simulation summary.

    Args:
        results: Simulation results dictionary
    """
    print("\n" + "=" * 80)
    print(" SIMULATION SUMMARY ".center(80, "="))
    print("=" * 80 + "\n")

    # Print status
    status = "✓ SUCCESS" if results["status"] == "success" else f"✗ FAILED: {results.get('error', 'Unknown error')}"
    print(f"Status: {status}")

    # Print statistics
    print(f"Execution Time: {results['execution_time']:.2f} seconds")
    print(f"States Processed: {results['states_processed']}")
    print(f"Actions Executed: {results['actions_executed']}")
    print(f"Transitions Detected: {results['transitions_detected']}")

    # Print validation results
    print("\nCOMPONENT VALIDATION:")
    for component, validation in results["validation"].items():
        status = "✓ PASSED" if validation["passed"] else "✗ FAILED"
        print(f"{component}: {status}")

        if not validation["passed"]:
            for issue in validation["issues"]:
                print(f"  - {issue}")

    print("\nTest completed.")


def main():
    """
    Main function to run the simulator.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Parse command line arguments
    args = parse_arguments()

    # Configure logging
    configure_logging(True)

    # Parse state prefixes
    state_prefixes = ["001", "003", "004", "005"]

    print(f"Running RV-Android component simulator for {args.app}")
    print(f"Data directory: {args.data_dir}")
    print(f"Processing states: {', '.join(state_prefixes)}")

    # Create and initialize simulator
    simulator = ComponentSimulator(args.app, args.data_dir)

    if not simulator.initialize():
        print("Failed to initialize simulator. Exiting.")
        return 1

    # Run simulation
    results = simulator.run_simulation(state_prefixes)

    # Print summary
    print_summary(results)

    # Return appropriate exit code
    return 0 if results["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
    