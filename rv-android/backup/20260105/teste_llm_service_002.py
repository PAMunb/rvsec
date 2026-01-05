#!/usr/bin/env python3

"""
RV-Android Memory and Transition Components Test.

This file contains simplified examples of how to use the refactored Memory and Transition
components of RV-Android. It simulates state transitions and action execution to
demonstrate the functionality of these components.
"""

import json
import logging
import os
import sys
import time
from typing import Dict, Any, List
import glob
import random

from rvandroid.app import App
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.llm.constants import PromptStrategyType, StateEntry, ScreenParserType, VisitorType
from rvandroid.llm.data_structures import Action
from rvandroid.llm.service.memory_manager import MemoryManager
from rvandroid.llm.service.transition_manager import TransitionManager


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("MemoryTransitionTest")


def load_sample_state(screenshot_path: str) -> Dict[str, Any]:
    """
    Create a sample state using a screenshot file.
    
    Args:
        screenshot_path: Path to the screenshot file
        
    Returns:
        A dictionary representing a sample application state
    """
    # Extract activity name from the filename
    filename = os.path.basename(screenshot_path)
    # For this test, we'll use a simple naming convention: screenshot_<state_id>.png
    state_id = filename.split('_')[-1].split('.')[0]
    
    # For testing purposes, create different activities based on the filename
    if "login" in filename.lower():
        activity = "com.example.cryptoapp.LoginActivity"
    elif "register" in filename.lower():
        activity = "com.example.cryptoapp.RegisterActivity"
    elif "home" in filename.lower():
        activity = "com.example.cryptoapp.HomeActivity"
    elif "settings" in filename.lower():
        activity = "com.example.cryptoapp.SettingsActivity"
    else:
        activity = f"com.example.cryptoapp.Activity{state_id}"
    
    # Create a basic state
    state = {
        StateEntry.STATE_ID: state_id,
        StateEntry.ACTIVITY: activity,
        StateEntry.PACKAGE_NAME: "com.example.cryptoapp",
        StateEntry.SCREENSHOT_PATH: screenshot_path,
        StateEntry.AVAILABLE_ACTIONS: generate_sample_actions(activity, int(state_id))
    }
    
    return state


def generate_sample_actions(activity: str, state_id: int) -> List[Dict[str, Any]]:
    """
    Generate sample actions for a state.
    
    Args:
        activity: Activity name
        state_id: State identifier
        
    Returns:
        List of actions
    """
    actions = []
    
    # Create different actions based on the activity
    if "LoginActivity" in activity:
        actions = [
            {"action_id": "1", "action_type": "touch", "view": {"resource_id": "login_button"}},
            {"action_id": "2", "action_type": "set_text", "view": {"resource_id": "username_field"}},
            {"action_id": "3", "action_type": "set_text", "view": {"resource_id": "password_field"}},
            {"action_id": "4", "action_type": "touch", "view": {"resource_id": "register_link"}}
        ]
    elif "RegisterActivity" in activity:
        actions = [
            {"action_id": "1", "action_type": "touch", "view": {"resource_id": "register_button"}},
            {"action_id": "2", "action_type": "set_text", "view": {"resource_id": "username_field"}},
            {"action_id": "3", "action_type": "set_text", "view": {"resource_id": "password_field"}},
            {"action_id": "4", "action_type": "set_text", "view": {"resource_id": "email_field"}},
            {"action_id": "5", "action_type": "touch", "view": {"resource_id": "login_link"}}
        ]
    elif "HomeActivity" in activity:
        actions = [
            {"action_id": "1", "action_type": "touch", "view": {"resource_id": "menu_button"}},
            {"action_id": "2", "action_type": "touch", "view": {"resource_id": "crypto_list_item"}},
            {"action_id": "3", "action_type": "touch", "view": {"resource_id": "settings_button"}},
            {"action_id": "4", "action_type": "touch", "view": {"resource_id": "logout_button"}}
        ]
    elif "SettingsActivity" in activity:
        actions = [
            {"action_id": "1", "action_type": "touch", "view": {"resource_id": "save_button"}},
            {"action_id": "2", "action_type": "touch", "view": {"resource_id": "back_button"}},
            {"action_id": "3", "action_type": "set_text", "view": {"resource_id": "api_key_field"}},
            {"action_id": "4", "action_type": "touch", "view": {"resource_id": "toggle_notifications"}}
        ]
    else:
        # Generate generic actions
        actions = [
            {"action_id": "1", "action_type": "touch", "view": {"resource_id": f"button_{state_id}_1"}},
            {"action_id": "2", "action_type": "touch", "view": {"resource_id": f"button_{state_id}_2"}},
            {"action_id": "3", "action_type": "set_text", "view": {"resource_id": f"text_field_{state_id}"}}
        ]
    
    return actions


def create_action_from_dict(action_dict: Dict[str, Any]) -> Action:
    """
    Create an Action object from a dictionary.
    
    Args:
        action_dict: Dictionary containing action parameters
        
    Returns:
        Action object
    """
    return Action(
        action_id=action_dict["action_id"],
        action_type=action_dict["action_type"],
        view=action_dict["view"],
        parameters=action_dict.get("params", {})
    )


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80 + "\n")


def print_formatted_json(data: Any):
    """
    Print data as formatted JSON.
    
    Args:
        data: Data to print
    """
    print(json.dumps(data, indent=2, sort_keys=False))


def test_memory_and_transition_components():
    """Test the Memory and Transition components by simulating state changes and actions."""
    print_section("Memory and Transition Components Test")
    
    # Initialize the components
    memory_manager = MemoryManager()
    transition_manager = TransitionManager()
    
    # Simulate loading multiple application states
    screenshot_dir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/screenshots"
    if not os.path.exists(screenshot_dir):
        logger.error(f"Screenshot directory not found: {screenshot_dir}")
        return
    
    # Get a list of screenshots
    screenshots = glob.glob(os.path.join(screenshot_dir, "*.png"))
    screenshots.sort()  # Sort to ensure a consistent order
    
    if not screenshots:
        logger.error("No screenshots found")
        return
    
    # For this test, we'll use a predefined sequence to simulate a realistic flow
    # Let's create a map of screenshot paths to state "activities"
    states_sequence = []
    
    # Load the first few screenshots and assign them different activities
    for i, path in enumerate(screenshots[:10]):
        state = load_sample_state(path)
        states_sequence.append(state)
    
    # Simulate first state
    current_state = states_sequence[0]
    print(f"Initial state: {current_state[StateEntry.ACTIVITY]} (ID: {current_state[StateEntry.STATE_ID]})")
    
    # Update components with initial state
    memory_manager.update(current_state)
    transition_manager.update(current_state)
    
    # Enrich state with history (empty at first)
    enriched_state = memory_manager.enrich_state_with_history(current_state)
    
    # Get transition guidance (empty at first)
    guidance = transition_manager.get_transition_guidance(enriched_state)
    
    print("\nInitial Transition Guidance:")
    print_formatted_json(guidance)
    
    # Simulate a sequence of actions and state transitions
    for iteration in range(5):
        print_section(f"Iteration {iteration + 1}")
        
        # Select available actions from current state
        available_actions = current_state[StateEntry.AVAILABLE_ACTIONS]
        
        # Randomly choose 1-2 actions to execute
        num_actions = random.randint(1, min(2, len(available_actions)))
        selected_action_dicts = random.sample(available_actions, num_actions)
        
        # Create Action objects
        selected_actions = [create_action_from_dict(a) for a in selected_action_dicts]
        
        print(f"Executing {len(selected_actions)} actions in {current_state[StateEntry.ACTIVITY]}")
        for i, action in enumerate(selected_actions):
            print(f"  {i+1}. {action.action_type} (ID: {action.action_id}) on {action.view.get('resource_id', 'unknown')}")
        
        # Record actions in memory and transition managers
        memory_manager.record_actions(current_state, selected_actions, 
                                     action_selection_reason="Test execution")
        transition_manager.update_with_actions(current_state, selected_actions)
        
        # Get a new state (simulate a state change)
        next_state_index = min(len(states_sequence) - 1, (iteration + 1) % len(states_sequence))
        next_state = states_sequence[next_state_index]
        
        # If we've executed more than one iteration, sometimes simulate a transition to a different activity
        if iteration > 0 and iteration % 2 == 0:
            # Find a state with a different activity
            for potential_state in states_sequence:
                if potential_state[StateEntry.ACTIVITY] != current_state[StateEntry.ACTIVITY]:
                    next_state = potential_state
                    break
        
        print(f"\nTransitioning to: {next_state[StateEntry.ACTIVITY]} (ID: {next_state[StateEntry.STATE_ID]})")
        
        # Update state
        current_state = next_state
        
        # Update components with new state
        memory_manager.update(current_state)
        detected_transition = transition_manager.update(current_state)
        
        if detected_transition:
            print("\n>>> Transition detected! <<<\n")
        
        # Enrich state with history
        enriched_state = memory_manager.enrich_state_with_history(current_state)
        
        # Get new transition guidance
        guidance = transition_manager.get_transition_guidance(enriched_state)
        
        print("\nMemory (Short-term iterations):")
        if StateEntry.RECENT_ITERATIONS in enriched_state:
            iterations = enriched_state[StateEntry.RECENT_ITERATIONS]
            print(f"Number of recent iterations: {len(iterations)}")
            for i, iteration in enumerate(iterations):
                print(f"  Iteration {i+1}: {len(iteration['actions'])} actions, reason: {iteration['action_selection_reason']}")
        else:
            print("No recent iterations found in state")
            
        print("\nMemory (Navigation path):")
        if StateEntry.NAVIGATION_PATH in enriched_state:
            path = enriched_state[StateEntry.NAVIGATION_PATH]
            print(f"Navigation path length: {len(path)}")
            print("→ ".join(path[-5:]))  # Show last 5 activities
        else:
            print("No navigation path found in state")
        
        print("\nUpdated Transition Guidance:")
        print_formatted_json(guidance)
        
        # Small delay to make the output more readable
        time.sleep(0.5)
    
    # Print final memory and transition statistics
    print_section("Final Memory and Transition Statistics")
    
    print("Memory Manager Statistics:")
    print(f"  Activities in long-term memory: {len(memory_manager.long_term.activity_visits)}")
    print(f"  Total actions recorded: {len(memory_manager.long_term.action_history)}")
    print(f"  Navigation path length: {len(memory_manager.long_term.visited_activities)}")
    
    print("\nTransition Manager Statistics:")
    print(f"  Activities in dynamic WTG: {len(transition_manager.activity_visits)}")
    
    # Get full dynamic transition builder
    dynamic_wtg = transition_manager.get_dtg()
    
    print("\nDynamic Transition Graph:")
    for from_activity, to_dict in dynamic_wtg.builder.items():
        print(f"  From: {from_activity}")
        for to_activity, actions in to_dict.items():
            action_str = ", ".join([f"{action_id} ({count})" for action_id, count in actions.items()])
            print(f"    → To: {to_activity} via actions: {action_str}")


if __name__ == "__main__":
    test_memory_and_transition_components()