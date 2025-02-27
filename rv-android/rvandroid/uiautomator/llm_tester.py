# rvandroid/uiautomator/llm_tester.py

import logging
import json
import time
from typing import List, Dict, Any, Optional

from rvandroid.model.static import StaticAnalysisData
from rvandroid.llm.model_factory import ModelFactory
from rvandroid.llm.prompt_strategy import PromptStrategyFactory
from rvandroid.uiautomator.uiautomator_executor import UIAutomatorExecutor
from rvandroid.parser.uiautomator.uiautomator_parser import parse_uiautomator_dump

logger = logging.getLogger(__name__)

class LLMTester:
    """
    Main class for LLM-based UI testing using UIAutomator.
    Handles the full pipeline from screen state extraction to action execution.
    """
    
    def __init__(
            self, 
            static_data: StaticAnalysisData,
            model_type: str, 
            model_name: str,
            strategy_type: str,
            device_id: str = "emulator-5554",
            max_actions: int = 100,
            **model_kwargs
        ):
        """
        Initialize the LLM Tester
        
        Args:
            static_data: Static analysis data for the application
            model_type: Type of model to use ('huggingface', 'ollama', etc.)
            model_name: Name of the model
            strategy_type: Type of prompt strategy to use
            device_id: Target device ID
            max_actions: Maximum number of actions to execute
            **model_kwargs: Additional arguments for model initialization
        """
        self.static_data = static_data
        self.uiautomator = UIAutomatorExecutor(device_id)
        self.logger = logging.getLogger(__name__)
        self.max_actions = max_actions
        self.action_history = []
        
        # Initialize LLM model and strategy
        self.model = ModelFactory.create(model_type, model_name, **model_kwargs)
        self.strategy = PromptStrategyFactory.create(strategy_type, static_data)
        
        self.logger.info(f"Initialized LLM Tester with model: {model_name}, strategy: {strategy_type}")
    
    def run(self, duration_seconds: int = 3600) -> Dict[str, Any]:
        """
        Run the testing process for the specified duration
        
        Args:
            duration_seconds: Maximum duration in seconds
            
        Returns:
            Dictionary with testing results
        """
        self.logger.info(f"Starting LLM Tester for {duration_seconds} seconds")
        
        start_time = time.time()
        action_count = 0
        visited_activities = set()
        
        results = {
            "total_actions": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "visited_activities": 0
        }
        
        # Main testing loop
        while time.time() - start_time < duration_seconds and action_count < self.max_actions:
            try:
                input("\n\n\nPress Enter to continue...")
                
                # Get current UI state
                current_state = self.uiautomator.get_current_state()
                print(f"Current state: {current_state}")
                
                # Add action history to state
                current_state["action_history"] = self.action_history[-10:] if self.action_history else []
                
                # Track visited activities
                activity = current_state.get("activity", "unknown")
                print(f"Activity: {activity}")
                visited_activities.add(activity)
                
                self.logger.info(f"Current activity: {activity}")

                # Generate LLM prompt and get suggested actions
                actions = self.process_state(current_state)
                print(f"Actions: {actions}")
                
                if not actions:
                    self.logger.warning("No actions suggested by LLM, using fallback")
                    # Fallback: try to find a clickable element
                    actions = self._generate_fallback_actions(current_state)
                
                # Execute actions
                for action in actions[:3]:  # Limit to first 3 actions per iteration
                    success = self.uiautomator.execute_action(action)
                    
                    # Update metrics
                    action_count += 1
                    results["total_actions"] += 1
                    
                    if success:
                        results["successful_actions"] += 1
                        # Record the executed action
                        action_desc = f"{action['action_type']} on {action['target']}"
                        self.action_history.append(action_desc)
                    else:
                        results["failed_actions"] += 1
                    
                    # Small delay between actions
                    time.sleep(1.5)
                
                # Log progress
                if action_count % 10 == 0:
                    elapsed = time.time() - start_time
                    self.logger.info(f"Executed {action_count} actions in {elapsed:.1f} seconds")
                
            except Exception as e:
                self.logger.error(f"Error in testing loop: {e}", exc_info=True)
                # Wait a bit before trying again
                time.sleep(5)
        
        # Update final results
        results["visited_activities"] = len(visited_activities)
        results["execution_time"] = time.time() - start_time
        
        self.logger.info(f"Testing completed: {results}")
        
        # Clean up LLM model resources
        try:
            self.model.clean()
        except Exception as e:
            self.logger.error(f"Error cleaning up model: {e}")
        
        return results
    
    def process_state(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process the current state and generate actions using LLM
        
        Args:
            state: Current UI state
            
        Returns:
            List of action dictionaries
        """
        self.logger.info("Processing current state with LLM")
        
        try:
            # Generate prompts using the strategy
            prompts = self.strategy.generate_prompts(state)
            print(f"Generated prompts: {prompts}")
            
            # Get LLM response
            response = self.model.generate(prompts)
            
            self.logger.debug(f"LLM response: {response}")
            print(f"********************************* RESPONSE: \n{response}")
            
            # Parse and validate the actions
            actions = self._parse_llm_response(response)
            print(f"Parsed actions_: {actions}")
            
            if not actions:
                self.logger.warning("Failed to parse valid actions from LLM response")
            else:
                self.logger.info(f"Generated {len(actions)} actions")
            
            return actions
            
        except Exception as e:
            self.logger.error(f"Error generating actions: {e}", exc_info=True)
            return []
    
    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse LLM response to extract action dictionaries
        
        Args:
            response: LLM response text
            
        Returns:
            List of action dictionaries
        """
        # Find JSON content in the response (helpful if LLM adds explanations)
        import re
        json_match = re.search(r'\[\s*{.*}\s*\]', response, re.DOTALL)
        
        if json_match:
            json_str = json_match.group(0)
        else:
            # Try to use the whole response
            json_str = response
        
        try:
            # Parse the JSON
            actions = json.loads(json_str)
            print(f"Parsed actions (json.loads): {actions}")
            
            # Validate and fix actions
            valid_actions = []
            for action in actions:
                if self._validate_action(action):
                    valid_actions.append(action)
            
            return valid_actions
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON from LLM response: {e}")
            return []
    
    def _validate_action(self, action: Dict[str, Any]) -> bool:
        """
        Validate an action dictionary
        
        Args:
            action: Action dictionary to validate
            
        Returns:
            True if action is valid, False otherwise
        """
        # Check required fields
        if "action_type" not in action or "target" not in action:
            return False
        
        # Ensure params is a dictionary
        if "params" not in action or not isinstance(action["params"], dict):
            action["params"] = {}
        
        # Validate action type
        valid_action_types = ["click", "long_click", "set_text", "scroll", "key_event"]
        if action["action_type"].lower() not in valid_action_types:
            return False
        
        # Special handling for set_text
        if action["action_type"].lower() == "set_text" and "text" not in action["params"]:
            # Try to find text in target or add default
            if "text:" in action["target"]:
                text = action["target"].split("text:")[1].strip()
                action["params"]["text"] = text
            else:
                action["params"]["text"] = "test input"
        
        # Special handling for scroll
        if action["action_type"].lower() == "scroll" and "direction" not in action["params"]:
            # Default direction
            action["params"]["direction"] = "down"
        
        return True
    
    def _generate_fallback_actions(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate fallback actions when LLM fails
        
        Args:
            state: Current UI state
            
        Returns:
            List of fallback actions
        """
        print("Generating fallback actions .......................")
        actions = []
        
        # Try to find clickable elements
        view_tree = state.get("view_tree", {})
        
        def find_clickable(view_dict, actions_list):
            if view_dict.get("clickable", False):
                resource_id = view_dict.get("resource_id", "")
                print(f"Found clickable element: {resource_id}")
                if resource_id:
                    actions_list.append({
                        "action_type": "click",
                        "target": resource_id,
                        "params": {},
                        "explanation": "Fallback action on clickable element"
                    })
            
            # Search in children
            children = view_dict.get("children", [])
            for child in children:
                find_clickable(child, actions_list)
        
        # Find clickable elements
        find_clickable(view_tree, actions)
        
        # If no clickable elements found, try a back action
        if not actions:
            actions.append({
                "action_type": "key_event",
                "target": "BACK",
                "params": {"key_code": 4},
                "explanation": "Fallback action: press back"
            })
        
        return actions #[:3]  # Return at most 3 actions