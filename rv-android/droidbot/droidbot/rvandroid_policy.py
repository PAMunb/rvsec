# droidbot/policy/rvandroid_policy.py

import logging
import json
import traceback
import requests
import time
from typing import Optional, Dict, List, Any

from droidbot.app import App
from .input_policy import UtgBasedInputPolicy, UtgGreedySearchPolicy, POLICY_GREEDY_DFS
from droidbot.input_event import KeyEvent, TouchEvent, LongTouchEvent, ScrollEvent, SetTextEvent, InputEvent
from droidbot.device import Device
from droidbot.device_state import DeviceState

class RVAndroidPolicy(UtgBasedInputPolicy):
    """
    A DroidBot input policy that communicates with an RV-Android server
    to get the next action based on the current app state.
    It handles external navigation and system-level actions like app restarts.
    """

    def __init__(self, device: Device, app: App, random_input, server_url="http://localhost:5000/api/get_actions"):
        super(RVAndroidPolicy, self).__init__(device, app, random_input)
        self.logger = logging.getLogger('RVAndroidPolicy')
        self.server_url = server_url
        self.fallback_policy = UtgGreedySearchPolicy(device, app, random_input, POLICY_GREEDY_DFS)
        
        self.action_history = []
        self.consecutive_errors = 0
        self.max_consecutive_errors = 3

        # External navigation control
        self.target_package = self.app.get_package_name()
        self.external_navigation_count = 0
        self.max_external_attempts = 3

        # This setting will be kept for local testing until production deployment
        self.device.adb.shell("settings put system show_touches 1")

        self.logger.info(f"RVAndroidPolicy initialized with server: {self.server_url}")

    def generate_event(self) -> Optional[InputEvent]:
        """
        Generate the next input event.
        This method handles external navigation and delegates to the appropriate
        state processing method.
        """
        current_state: DeviceState = self.device.get_current_state()
        if current_state is None:
            self.logger.warning("Could not get current device state. Using fallback.")
            return self.fallback_policy.generate_event()

        current_package = self._extract_current_package(current_state)

        if not self._is_target_package(current_package):
            return self._handle_external_navigation(current_state, current_package)

        if self.external_navigation_count > 0:
            self.logger.info("Returned to target application, resetting external counter.")
            self.external_navigation_count = 0

        return self._process_target_app_state(current_state)

    def _extract_current_package(self, state: DeviceState) -> Optional[str]:
        """Extracts the current foreground package from the device state."""
        if state.foreground_activity:
            return state.foreground_activity.split('/')[0]
        return None

    def _is_target_package(self, current_package: Optional[str]) -> bool:
        """Checks if the current package is the target application."""
        return current_package == self.target_package

    def _handle_external_navigation(self, current_state, current_package: str) -> Optional[InputEvent]:
        """
        Handle navigation outside the target application with attempt limiting.
        """
        self.external_navigation_count += 1
        self.logger.warning(
            f"External navigation detected - target: {self.target_package}, "
            f"current: {current_package}, attempt: {self.external_navigation_count}/{self.max_external_attempts}"
        )

        if self.external_navigation_count >= self.max_external_attempts:
            self.logger.info("Maximum external attempts reached, forcing application restart.")
            self._execute_app_restart()
            # Return None to let DroidBot handle the next iteration
            # The restarted app should be available in the next generate_event() call
            return None

        return self._process_external_state_with_context(current_state)

    def _process_external_state_with_context(self, current_state: DeviceState) -> Optional[InputEvent]:
        """
        Send the external state to the server with additional context to get a corrective action.
        """
        try:
            state_data = self._prepare_state_data(current_state)
            state_data.update({
                'external_navigation': True,
                'external_attempt': self.external_navigation_count,
                'max_external_attempts': self.max_external_attempts,
                'target_package': self.target_package,
                'remaining_attempts': self.max_external_attempts - self.external_navigation_count,
                'navigation_guidance': self._generate_navigation_guidance()
            })

            actions = self._get_actions_from_server(state_data)
            if actions:
                # Use first action from server response for external navigation
                return self._convert_to_droidbot_event(actions[0])
            else:
                self.logger.warning("Server provided no action for external state, sending BACK event.")
                return KeyEvent(name="BACK")

        except Exception as e:
            self.logger.error(f"Error processing external state: {e}", exc_info=True)
            return KeyEvent(name="BACK")

    # TODO vamos usar?
    def _generate_navigation_guidance(self) -> str:
        """
        Generate guidance text for the LLM about the external navigation context.
        """
        remaining = self.max_external_attempts - self.external_navigation_count
        if remaining <= 0:
            return "Maximum external navigation attempts reached. Application will be restarted."
        return (
            f"Currently outside target application. {remaining} attempt(s) remaining "
            f"before automatic restart. Consider using SYSTEM_BACK or RESTART_APP actions "
            f"to return to the target application."
        )

    def _process_target_app_state(self, current_state: DeviceState) -> Optional[InputEvent]:
        """
        Process the state when the app is in the foreground.
        """
        state_data = self._prepare_state_data(current_state)
        try:
            actions = self._get_actions_from_server(state_data)
            if actions:
                self.consecutive_errors = 0  # Reset error counter on successful server response
                action = actions[0]
                event = self._convert_to_droidbot_event(action)
                # self._update_action_history(self._get_action_description(action))
                return event

            self.logger.warning("No valid actions from server, using fallback policy.")
            return self.fallback_policy.generate_event()

        except Exception as e:
            self.logger.error(f"Error getting actions from server: {e}", exc_info=True)
            self.consecutive_errors += 1
            if self.consecutive_errors >= self.max_consecutive_errors:
                self.logger.warning(f"Too many consecutive errors ({self.consecutive_errors}), using fallback policy.")
                self.consecutive_errors = 0
                return self.fallback_policy.generate_event()

            time.sleep(1)
            return KeyEvent(name="BACK")

    def _prepare_state_data(self, state: DeviceState) -> Dict[str, Any]:
        """
        Convert DroidBot state to the format expected by the RV-Android server.
        """
        # Convert state to dictionary for server transmission
        state_dict = state.to_dict()
        # Note: Screenshot handling is now managed by server-side processing
        # Add action history, which is not part of the default state dict
        # state_dict["action_history"] = self.action_history[-20:] if self.action_history else []
        return state_dict

    def _get_actions_from_server(self, state_data: Dict[str, Any], timeout: int = 60) -> List[Dict[str, Any]]:
        """
        Send state data to the RV-Android server and get suggested actions.
        """
        try:
            self.logger.info(f"Sending state to server: {self.server_url}")
            response = requests.post(
                self.server_url,
                json=state_data,
                headers={"Content-Type": "application/json"},
                timeout=timeout
            )
            if response.status_code != 200:
                self.logger.error(f"Server returned status {response.status_code}: {response.text}")
                return []
            
            response_data = response.json()
            if "actions" not in response_data or not isinstance(response_data["actions"], list):
                self.logger.error(f"Invalid response format from server: {response_data}")
                return []

            actions = response_data["actions"]
            self.logger.info(f"Received {len(actions)} actions from server.")
            return actions

        except requests.RequestException as e:
            self.logger.error(f"Failed to communicate with server: {e}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse server response: {e}")
            return []

    def _convert_to_droidbot_event(self, action_data: Dict[str, Any]) -> Optional[InputEvent]:
        """
        Convert an action from the server into a DroidBot InputEvent.
        Handles system actions and standard UI actions.
        """
        action_type = action_data.get("action_type", "").lower()
        explanation = action_data.get("explanation", "")

        if self._is_system_back_action(action_type, explanation):
            self.logger.info("Executing SYSTEM_BACK action.")
            return KeyEvent(name="BACK")
        
        if self._is_restart_action(action_type, explanation):
            self.logger.info("Executing RESTART_APP action.")
            self._execute_app_restart()
            return None

        return self._convert_ui_action_to_event(action_data)

    def _is_system_back_action(self, action_type: str, explanation: str) -> bool:
        """Check if the action represents a system back operation."""
        return action_type == "system_back" or "SYSTEM_BACK" in explanation.upper()

    def _is_restart_action(self, action_type: str, explanation: str) -> bool:
        """Check if the action represents an app restart operation."""
        return action_type == "restart_app" or "RESTART_APP" in explanation.upper()

    def _execute_app_restart(self) -> None:
        """
        Execute the application restart operation via the device object.
        
        Uses DroidBot's proper intent-based app lifecycle management.
        """
        try:
            self.logger.info(f"Restarting application: {self.target_package}")
            
            # Stop the application using DroidBot's force-stop intent
            stop_intent = self.app.get_stop_intent()
            self.device.send_intent(stop_intent)
            
            # Wait for application to fully stop
            time.sleep(2)
            
            # Start the application again
            self.device.start_app(self.app)
            
            # Reset external navigation counter
            self.external_navigation_count = 0
            self.logger.info("Application restart completed.")
            
        except Exception as e:
            self.logger.error(f"Application restart failed: {e}", exc_info=True)

    def _convert_ui_action_to_event(self, action: Dict[str, Any]) -> Optional[InputEvent]:
        """
        Convert a standard UI action into a DroidBot InputEvent.
        """
        action_type = action.get("action_type", "").lower()
        target = action.get("target", "")
        params = action.get("params", {})
        coordinates = action.get("coordinates", None)

        self.logger.debug(f"Converting UI action to event: {action}")
        
        x, y = None, None
        if coordinates and isinstance(coordinates, (list, tuple)) and len(coordinates) == 2:
            x, y = coordinates
        elif isinstance(target, str) and " " in target:
            parts = target.split()
            if len(parts) == 2 and all(part.isdigit() for part in parts):
                x, y = int(parts[0]), int(parts[1])
        
        try:
            if action_type == "key_event":
                # Handle system actions: BACK and potential RESTART
                key_name = params.get("name", "BACK")
                if key_name.upper() in ["BACK", "MENU", "HOME"]:
                    return KeyEvent(name=key_name)
                else:
                    self.logger.warning(f"Unknown system key: {key_name}, defaulting to BACK")
                    return KeyEvent(name="BACK")
                
            if x is not None and y is not None:
                event: InputEvent = self._action_to_event(action_type, params, x, y)
                if event:
                    return event

            # Handle coordinate-based targeting when action_id contains coordinates
            # This supports the multimodal strategy where LLM provides direct coordinates
            if ":" in target and not target.isdigit():
                current_state = self.device.get_current_state()
                view = self._find_view_by_resource_id(current_state, target)
                if view:
                    if action_type == "click": return TouchEvent(view=view)
                    if action_type == "long_click": return LongTouchEvent(view=view)
                    if "scroll" in action_type:
                        direction = action_type.replace("scroll_", "") if "_" in action_type else params.get("direction", "DOWN")
                        return ScrollEvent(view=view, direction=direction.upper())
                    if action_type == "set_text":
                        return SetTextEvent(view=view, text=params.get("text", ""))
            
            self.logger.warning(f"Could not find target for action, falling back to center screen: {action}")
            return self._fallback_to_center_screen(action_type, params)

        except Exception as e:
            self.logger.error(f"Error converting UI action to event: {e}", exc_info=True)
            return KeyEvent(name="BACK")

    def _fallback_to_center_screen(self, action_type: str, params: Dict[str, Any]) -> InputEvent:
        """Creates an event at the center of the screen as a last resort."""
        screen_width = self.device.get_width()
        screen_height = self.device.get_height()
        center_x, center_y = screen_width // 2, screen_height // 2

        event: InputEvent = self._action_to_event(action_type, params, center_x, center_y)
        if event:
            return event
        
        self.logger.error(f"Unknown action type for fallback: {action_type}. Sending BACK.")
        return KeyEvent(name="BACK")

    def _action_to_event(self, action_type: str, params: Dict[str, Any], center_x: int, center_y: int) -> Optional[InputEvent]:
        if action_type == "click": return TouchEvent(x=center_x, y=center_y)
        if action_type == "long_click": return LongTouchEvent(x=center_x, y=center_y)
        if "scroll" in action_type:
            direction = action_type.replace("scroll_", "") if "_" in action_type else params.get("direction", "DOWN")
            return ScrollEvent(x=center_x, y=center_y, direction=direction.upper())
        if action_type == "set_text":
            return SetTextEvent(x=center_x, y=center_y, text=params.get("text", ""))
        return None

    def _find_view_by_resource_id(self, state: DeviceState, resource_id: str) -> Optional[Dict[str, Any]]:
        """Find a view by its resource ID in the current state's view list."""
        if not state or not resource_id: return None
            
        for view in state.views:
            if view.get('resource_id') == resource_id:
                return view
                
        if ':id/' in resource_id:
            id_part = resource_id.split(':id/')[-1]
            for view in state.views:
                if view.get('resource_id', '').endswith(id_part):
                    return view
        return None
    
    def _get_action_description(self, action: Dict[str, Any]) -> str:
        """Create a descriptive string for an action to store in the history."""
        action_type = action.get("action_type", "unknown").upper()
        explanation = action.get("explanation", "")
        return f"{action_type} - {explanation}"
    
    def _update_action_history(self, action_desc: str):
        """Update the action history, keeping it to a maximum of 20 entries."""
        self.action_history.append(action_desc)
        if len(self.action_history) > 20:
            self.action_history.pop(0)