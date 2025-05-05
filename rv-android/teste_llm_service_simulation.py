#!/usr/bin/env python3
"""
RV-Android Memory and Transition Systems Integration Test

This script provides an integration test for the memory and transition management
systems of RV-Android using real data files. It simulates a realistic navigation
path through an Android application by loading screen states in sequence and
processing them through the memory and transition managers.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from rvandroid.app import App
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.constants import PromptStrategyType, StateEntry
from rvandroid.llm.constants import ScreenParserType, VisitorType
from rvandroid.llm.service.action_generator import GeneratedAction
from rvandroid.llm.service.action_service import LLMActionService
from rvandroid.llm.service.memory_manager import MemoryManager
from rvandroid.llm.service.transition_manager import TransitionManager
from rvandroid.parser.screen.parser_factory import ParserFactory, ParserType
from rvandroid.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rvandroid.parser.static import static_analysis_parser
from rvandroid.util.logging.manager import LoggingManager


class RVAndroidSimulator:
    """
    Simulates the execution of RV-Android using real data files.

    This class loads real screen state files and static analysis data,
    then processes them through the memory and transition managers to
    simulate a realistic navigation path through an Android application.
    """

    def __init__(self, data_dir: str, app_name: str):
        """
        Initialize the simulator with paths to data files.

        Args:
            data_dir: Directory containing data files
            app_name: Name of the APK being tested
        """
        # Set up logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "simulator.rv_android_simulator",
            {"app": app_name}
        )

        # Store paths
        self.data_dir = data_dir
        self.app_name = app_name
        self.app_dir = os.path.join(data_dir, app_name)

        # Set up static analysis file paths
        self.reach_file = os.path.join(self.app_dir, f"{app_name}.reach")
        self.wtg_file = os.path.join(self.app_dir, f"{app_name}.wtg")
        self.gesda_file = os.path.join(self.app_dir, f"{app_name}.gesda")

        # Initialize core components
        self.static_data = None
        self.parser = None
        self.memory_manager = None
        self.transition_manager = None
        self.llm_service: LLMActionService = None
        self.app = None
        self.package_name = None

        # Statistics for validation
        self.states_processed = 0
        self.actions_executed = 0
        self.transitions_detected = 0

        self.logger.info(f"Initialized RV-Android simulator for {app_name}")

    def load_static_data(self) -> bool:
        """
        Load static analysis data from files.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Loading static analysis data...")

            # Check if files exist
            for file_path in [self.reach_file, self.wtg_file, self.gesda_file]:
                if not os.path.exists(file_path):
                    self.logger.error(f"File not found: {file_path}")
                    return False

            # Load app information
            self.app = App(os.path.join(self.app_dir, self.app_name))
            self.package_name = self.app.package_name

            # Parse static analysis data
            self.static_data = static_analysis_parser.parse(
                self.reach_file,
                self.wtg_file,
                self.gesda_file,
                self.package_name
            )

            # Initialize parser
            visitor_class = DefaultTextVisitor
            self.parser = ParserFactory.create(ParserType.DROIDBOT, visitor_class)

            self.logger.info("Static analysis data loaded successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error loading static data: {e}", exc_info=True)
            return False

    def initialize_components(self) -> bool:
        """
        Initialize memory and transition management components.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Initializing components...")

            # Create memory manager
            self.memory_manager = MemoryManager()

            # Create transition manager
            self.transition_manager = TransitionManager(self.static_data)

            # Create LLM action service configuration
            config = ComponentConfigurator()
            config.set_strategy(PromptStrategyType.BATCH_ACTION)
            config.set_parser(ScreenParserType.DROIDBOT)
            config.set_visitor(VisitorType.DEFAULT)

            # Create LLM action service
            self.llm_service = LLMActionService(
                static_data=self.static_data,
                config=config,
                app_package=self.package_name
            )

            # Set dependencies
            self.llm_service.memory_manager = self.memory_manager
            self.llm_service.transition_manager = self.transition_manager

            self.logger.info("Components initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error initializing components: {e}", exc_info=True)
            return False

    def load_droidbot_state(self, prefix: str) -> Optional[Dict[str, Any]]:
        """
        Load a DroidBot state file for the given prefix.

        Args:
            prefix: State file prefix (e.g., '001')

        Returns:
            Loaded state data or None if failed
        """
        state_file = os.path.join(self.app_dir, f"{prefix}.state")

        if not os.path.exists(state_file):
            self.logger.error(f"State file not found: {state_file}")
            return None

        try:
            with open(state_file, 'r') as file:
                return json.load(file)
        except Exception as e:
            self.logger.error(f"Error loading state file {state_file}: {e}")
            return None

    def create_state(self, prefix: str) -> Optional[Dict[str, Any]]:
        """
        Create a complete state object from a prefix.

        Args:
            prefix: State file prefix (e.g., '001')

        Returns:
            State dictionary or None if failed
        """
        try:
            # Load state data
            state_data = self.load_droidbot_state(prefix)
            if not state_data:
                return None

            # Set screenshot path
            screenshot_path = os.path.join(self.app_dir, f"{prefix}.png")
            if not os.path.exists(screenshot_path):
                self.logger.warning(f"Screenshot not found: {screenshot_path}")
                screenshot_path = None

            # Parse screen description
            screen_description = self.parser.parse(state_data, self.static_data)

            # Create state dictionary
            state = {
                StateEntry.PACKAGE_NAME: self.package_name,
                StateEntry.ACTIVITY: screen_description.activity,
                StateEntry.VIEW_TREE: state_data.get("view_tree", {}),
                StateEntry.STRUCTURED_SCREEN: screen_description,
                StateEntry.SCREENSHOT_PATH: screenshot_path,
                StateEntry.STATIC_DATA: self.static_data,
                "timestamp": datetime.now().isoformat()
            }

            return state

        except Exception as e:
            self.logger.error(f"Error creating state for prefix {prefix}: {e}", exc_info=True)
            return None

    def select_actions(self, state: Dict[str, Any], strategy: str = "smart") -> List[GeneratedAction]:
        """
        Select actions to execute from the available actions.

        Args:
            state: Current state
            strategy: Selection strategy ('smart', 'random', or 'priority')

        Returns:
            List of selected actions
        """
        screen_description = state[StateEntry.STRUCTURED_SCREEN]
        available_actions = []

        # Collect all available actions
        for item in screen_description.items:
            for action in item.actions:
                available_actions.append(action)

        if not available_actions:
            self.logger.warning("No available actions found")
            return []

        # Different selection strategies
        if strategy == "smart":
            # Prioritize actions that reach monitored operations
            prioritized_actions = []
            regular_actions = []

            for action in available_actions:
                if action.directly_reaches_mop:
                    prioritized_actions.append(action)
                elif action.reaches_mop:
                    prioritized_actions.append(action)
                else:
                    regular_actions.append(action)

            # If we have prioritized actions, use them
            if prioritized_actions:
                # Take up to 3 prioritized actions
                selected_actions = prioritized_actions[:min(3, len(prioritized_actions))]
            else:
                # Take a few regular actions
                selected_actions = regular_actions[:min(3, len(regular_actions))]

        elif strategy == "random":
            # Just take a random subset
            import random
            random.shuffle(available_actions)
            selected_actions = available_actions[:min(3, len(available_actions))]

        elif strategy == "priority":
            # Try to select a balanced set of actions
            clicks = []
            text_inputs = []
            other_actions = []

            for action in available_actions:
                if action.text.startswith("CLICK"):
                    clicks.append(action)
                elif action.text.startswith("SET_TEXT"):
                    text_inputs.append(action)
                else:
                    other_actions.append(action)

            # Build a balanced set
            selected_actions = []
            if clicks:
                selected_actions.append(clicks[0])
            if text_inputs:
                selected_actions.append(text_inputs[0])
            if other_actions:
                selected_actions.append(other_actions[0])

            # If we didn't get enough, add more clicks
            while len(selected_actions) < 3 and len(clicks) > len(selected_actions):
                selected_actions.append(clicks[len(selected_actions)])

        else:
            # Default: just take the first few
            selected_actions = available_actions[:min(3, len(available_actions))]

        # Convert ItemAction to GeneratedAction
        generated_actions = []
        for action in selected_actions:
            params = {}

            # Add appropriate parameters for action types
            if action.text.startswith("SET_TEXT"):
                params["text"] = "test_input"

            # Get coordinates if available
            coordinates = action.coordinates
            if not coordinates and action.target_view and "bounds" in action.target_view:
                bounds = action.target_view["bounds"]
                if bounds and len(bounds) == 2:
                    x = (bounds[0][0] + bounds[1][0]) // 2
                    y = (bounds[0][1] + bounds[1][1]) // 2
                    coordinates = (x, y)

            # Default coordinates if none found
            if not coordinates:
                coordinates = (100, 100)

            generated_action = GeneratedAction(
                action,
                params,
                coordinates,
                "resource_id",
                f"Testing action: {action.text}"
            )

            generated_actions.append(generated_action)

        return generated_actions

    def simulate_state_transition(self, from_state: Dict[str, Any], to_state: Dict[str, Any],
                                  action: GeneratedAction, success: bool = True) -> None:
        """
        Simulate a state transition due to an action.

        Args:
            from_state: Source state
            to_state: Destination state
            action: Action that caused the transition
            success: Whether the transition succeeded
        """
        # Process the action result through the LLM action service
        self.llm_service.process_action_result(from_state, to_state, action.to_droidbot_format(), success)

        # Update statistics
        self.transitions_detected += 1

        # Log transition
        from_activity = from_state[StateEntry.ACTIVITY]
        to_activity = to_state[StateEntry.ACTIVITY]
        self.logger.info(f"Transition: {from_activity} -> {to_activity} via action {action.text}")

    def run_simulation(self, prefixes: List[str]) -> Dict[str, Any]:
        """
        Run a simulation using the provided state prefixes.

        Args:
            prefixes: List of state prefixes in order of execution

        Returns:
            Dictionary with simulation results and statistics
        """
        results = {
            "states_processed": 0,
            "actions_executed": 0,
            "transitions_detected": 0,
            "validation": {}
        }

        if not self.static_data or not self.memory_manager or not self.transition_manager:
            self.logger.error("Components not initialized")
            return results

        self.logger.info(f"Starting simulation with {len(prefixes)} states")

        previous_state = None
        current_state = None

        # Process each state in sequence
        for i, prefix in enumerate(prefixes):
            self.logger.info(f"Processing state {i + 1}/{len(prefixes)}: {prefix}")

            # Load current state
            current_state = self.create_state(prefix)
            if not current_state:
                self.logger.error(f"Failed to create state for prefix {prefix}")
                continue

            # Update components with current state
            self.llm_service._initialize_state(current_state)
            transition_detected = self.llm_service.pre_process_state(current_state)

            # Select actions to execute
            actions = self.select_actions(current_state, strategy="smart")

            if actions:
                self.logger.info(f"Selected {len(actions)} actions to execute")

                self.llm_service.post_process_state(current_state, actions, transition_detected)
                aaa
                # Record actions in memory
                self.memory_manager.record_actions(current_state, actions)

                # Execute each action
                for action in actions:
                    self.logger.info(f"Executing action: {action.text}")
                    self.actions_executed += 1

                    # If there's a next state, simulate transition
                    if i < len(prefixes) - 1 and previous_state:
                        next_prefix = prefixes[i + 1]
                        next_state = self.create_state(next_prefix)

                        if next_state:
                            self.simulate_state_transition(current_state, next_state, action)

            # Visualize state
            self.visualize_state(current_state)

            # Store current state as previous for next iteration
            previous_state = current_state
            self.states_processed += 1

        # Collect final statistics
        results["states_processed"] = self.states_processed
        results["actions_executed"] = self.actions_executed
        results["transitions_detected"] = self.transitions_detected
        results["validation"] = self.validate_components()

        return results

    def validate_components(self) -> Dict[str, Any]:
        """
        Validate the correctness of memory and transition managers.

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
            # Check if long-term memory has recorded activities
            if not self.memory_manager.long_term.visited_activities:
                validation["memory_manager"]["passed"] = False
                validation["memory_manager"]["issues"].append("No activities recorded in long-term memory")

            # Check if actions were recorded
            if not self.memory_manager.long_term.action_history:
                validation["memory_manager"]["passed"] = False
                validation["memory_manager"]["issues"].append("No actions recorded in long-term memory")

        # Validate transition manager
        if not self.transition_manager:
            validation["transition_manager"]["passed"] = False
            validation["transition_manager"]["issues"].append("Transition manager not initialized")
        else:
            # Check if dynamic WTG has recorded activities
            if not self.transition_manager.dynamic_wtg.activities:
                validation["transition_manager"]["passed"] = False
                validation["transition_manager"]["issues"].append("No activities recorded in dynamic WTG")

            # Check if transitions were recorded
            if not self.transition_manager.dynamic_wtg.transitions:
                validation["transition_manager"]["passed"] = False
                validation["transition_manager"]["issues"].append("No transitions recorded in dynamic WTG")

        return validation

    def visualize_state(self, state: Dict[str, Any]) -> None:
        """
        Visualize the current state of memory and transition managers.

        Args:
            state: Current application state
        """
        print("\n" + "=" * 80)
        print(f" STATE VISUALIZATION: {state[StateEntry.ACTIVITY]} ".center(80, "="))
        print("=" * 80)

        # Visualize memory manager state
        self._visualize_memory_state()

        # Visualize transition manager state
        self._visualize_transition_state()

        print("=" * 80 + "\n")

    def _visualize_memory_state(self) -> None:
        """Visualize the current state of the memory manager."""
        if not self.memory_manager:
            print("Memory Manager: Not initialized")
            return

        print("\nMEMORY MANAGER STATE:")
        print("-" * 80)

        # Short-term memory
        print("SHORT-TERM MEMORY:")
        if hasattr(self.memory_manager, 'short_term') and self.memory_manager.short_term:
            print(f"  Current Activity: {self.memory_manager.short_term.current_activity}")
            print(f"  Iterations: {len(self.memory_manager.short_term.iterations)}")

            if self.memory_manager.short_term.iterations:
                print("\n  Recent Iterations:")
                for i, iteration in enumerate(self.memory_manager.short_term.iterations[:3]):  # Show last 3
                    # Handle actions that might be dictionaries or objects
                    if hasattr(iteration, 'actions'):
                        if isinstance(iteration.actions[0], dict):
                            # Handle actions as dictionaries
                            actions_text = ", ".join([a.get("text", a.get("action_type", "Unknown"))
                                                      for a in iteration.actions])
                        else:
                            # Handle actions as objects
                            actions_text = ", ".join([getattr(a, "text", str(a)) for a in iteration.actions])
                    else:
                        actions_text = "No actions"

                    print(
                        f"    [{i + 1}] {len(iteration.actions) if hasattr(iteration, 'actions') else 0} actions: {actions_text}")
        else:
            print("  No short-term memory data available")

        # Long-term memory
        print("\nLONG-TERM MEMORY:")
        if hasattr(self.memory_manager, 'long_term') and self.memory_manager.long_term:
            print(f"  Visited Activities: {len(self.memory_manager.long_term.activity_visits)}")
            print(f"  Total Actions: {len(self.memory_manager.long_term.action_history)}")

            if self.memory_manager.long_term.visited_activities:
                print("\n  Navigation Path:")
                path = " → ".join(self.memory_manager.long_term.visited_activities[-5:])  # Last 5
                print(f"    {path}")

            if self.memory_manager.long_term.activity_visits:
                print("\n  Activity Statistics:")
                for activity, visits in self.memory_manager.long_term.activity_visits.items():
                    print(f"    {activity}: {visits} visits")
        else:
            print("  No long-term memory data available")

    def _visualize_transition_state(self) -> None:
        """Visualize the current state of the transition manager."""
        if not self.transition_manager:
            print("Transition Manager: Not initialized")
            return

        print("\nTRANSITION MANAGER STATE:")
        print("-" * 80)

        # Dynamic WTG
        print("DYNAMIC TRANSITION GRAPH:")
        dtg = self.transition_manager.get_dtg()
        if dtg:
            print(f"  Activities: {len(dtg.activities)}")
            print(f"  Transitions: {len(dtg.transitions)}")

            if dtg.activities:
                print("\n  Activity Nodes:")
                for activity_name, node in dtg.activities.items():
                    print(f"    {activity_name}: {node.visit_count} visits")

            if dtg.transitions:
                print("\n  Recorded Transitions:")
                for i, transition in enumerate(dtg.transitions[:5]):  # Show first 5
                    print(
                        f"    [{i + 1}] {transition.source_activity} → {transition.target_activity} (count: {transition.count})")
        else:
            print("  No dynamic transition graph available")

        # Current navigation state
        print("\nCURRENT NAVIGATION STATE:")
        print(f"  Current Activity: {self.transition_manager.current_activity}")
        print(f"  Previous Activity: {self.transition_manager.previous_activity}")

        # If we have a current state, show transition guidance
        if self.transition_manager.current_activity:
            guidance = self.transition_manager.get_transition_guidance({
                StateEntry.ACTIVITY: self.transition_manager.current_activity
            })

            print("\n  Transition Guidance:")
            print(f"    Visit Count: {guidance.get('visit_count', 0)}")

            if guidance.get('suggested_targets'):
                print("\n    Suggested Targets:")
                for target in guidance.get('suggested_targets')[:3]:  # Show top 3
                    print(f"      {target.get('name')}: {target.get('visits', 0)} visits")


def configure_logging():
    """Configure logging for the test script."""
    LoggingManager.get_instance().configure_output(console_level=logging.INFO)

    # Suppress verbose logs
    modules_to_suppress = [
        "androguard",
        "rvandroid.parser.screen.visitor.base_visitor",
        "rvandroid.parser.screen.droidbot.droidbot_parser",
        "rvandroid.model.classes.Classes",
        "rvandroid.model.window.Window",
        "rvandroid.model.window.Windows",
        "rvandroid.model.widget.Widget",
        "rvandroid.parser.static.reach",
        "rvandroid.parser.static.gator",
        "rvandroid.parser.static.gesda",
        "rvandroid.parser.screen.droidbot",
        "rvandroid.parser.screen.visitor",
        "rvandroid.util.utils"
    ]

    for module in modules_to_suppress:
        logging.getLogger(module).setLevel(logging.WARNING)


def main():
    """Main function to run the test."""
    # Configure logging
    configure_logging()

    # Parse command line arguments
    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    else:
        data_dir = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"

    # Default app to test
    app_name = "cryptoapp.apk"

    # Test prefixes - these should be in order of a realistic navigation path
    prefixes = ["001", "003", "004", "005"]

    print(f"Running RV-Android simulator for {app_name} with {len(prefixes)} states")
    print(f"Data directory: {data_dir}")

    # Create and initialize simulator
    simulator = RVAndroidSimulator(data_dir, app_name)

    # Load static data
    if not simulator.load_static_data():
        print("Failed to load static data. Exiting.")
        return 1

    # Initialize components
    if not simulator.initialize_components():
        print("Failed to initialize components. Exiting.")
        return 1

    # Run simulation
    start_time = time.time()
    results = simulator.run_simulation(prefixes)
    end_time = time.time()

    # Show summary
    print("\n" + "=" * 80)
    print(" SIMULATION SUMMARY ".center(80, "="))
    print("=" * 80)

    print(f"\nExecution Time: {end_time - start_time:.2f} seconds")
    print(f"States Processed: {results['states_processed']}")
    print(f"Actions Executed: {results['actions_executed']}")
    print(f"Transitions Detected: {results['transitions_detected']}")

    # Validation results
    print("\nVALIDATION RESULTS:")
    for component, validation in results["validation"].items():
        status = "✓ PASSED" if validation["passed"] else "✗ FAILED"
        print(f"{component}: {status}")

        if not validation["passed"]:
            for issue in validation["issues"]:
                print(f"  - {issue}")

    print("\nTest completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
