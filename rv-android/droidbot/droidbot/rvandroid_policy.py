"""
RVAndroid policy for DroidBot integration.

This module provides DroidBot policy implementation that communicates with 
RVAndroid server for AI-driven action generation, enabling intelligent test
exploration guided by large language models.
"""

import json
import logging
import requests
import time
from typing import Dict, List, Any, Optional

from droidbot.app import App
from droidbot.device import Device
from droidbot.device_state import DeviceState
from droidbot.input_event import (
    InputEvent, KeyEvent, TouchEvent, LongTouchEvent, 
    ScrollEvent, SetTextEvent
)
from .input_policy import UtgBasedInputPolicy, UtgGreedySearchPolicy, POLICY_GREEDY_DFS


class RVAndroidPolicy(UtgBasedInputPolicy):
    """
    DroidBot policy with RVAndroid server integration for AI-driven testing.
    
    ### Architecture Overview:
    Integrates DroidBot's testing framework with RVAndroid's AI-driven action
    generation service. Sends application state to RVAndroid server and receives
    complete action specifications for reliable execution.
    
    ### Communication Protocol:
    Uses HTTP REST API to communicate with RVAndroid server, sending optimized
    state data and receiving complete action specifications with all required
    fields for DroidBot execution.
    
    ### Action Processing:
    Processes server responses containing complete action format with action_type,
    coordinates, parameters, and target information. Maps these to appropriate
    DroidBot InputEvent objects for device execution.
    
    ### Error Handling:
    Implements comprehensive error handling with fallback to greedy search policy
    when server communication fails. Provides session continuity through robust
    recovery mechanisms.
    """

    def __init__(self, 
                 device: Device, 
                 app: App, 
                 random_input: bool,
                 server_url: str = "http://localhost:5000/api/get_actions",
                 include_screenshots: bool = False,
                 **kwargs):
        """
        Initialize RVAndroid policy with server communication.
        
        Args:
            device: DroidBot device interface
            app: Application under test
            random_input: Enable random input (inherited parameter)
            server_url: RVAndroid server endpoint URL
            include_screenshots: Include screenshots for multimodal LLMs
            **kwargs: Additional policy parameters
        """
        super(RVAndroidPolicy, self).__init__(device, app, random_input)
        
        # Configure logging
        self.logger = logging.getLogger('RVAndroidPolicy')
        
        # Server communication
        self.server_url = server_url
        self.session = requests.Session()
        self.session.timeout = 60
        
        # Multimodal support
        self.include_screenshots = include_screenshots
        
        # Fallback policy for error cases
        self.fallback_policy = UtgGreedySearchPolicy(device, app, random_input, POLICY_GREEDY_DFS)
        
        # Error tracking
        self.consecutive_errors = 0
        self.max_consecutive_errors = 3
        
        # Application tracking
        self.target_package = self.app.get_package_name()
        self.external_navigation_count = 0
        self.max_external_attempts = 3
        
        # Enable touch visualization for testing
        self.device.adb.shell("settings put system show_touches 1")
        
        self.logger.info(f"RVAndroid policy initialized - server: {self.server_url}, "
                        f"screenshots: {self.include_screenshots}")

    def generate_event(self) -> Optional[InputEvent]:
        """
        Generate next input event using RVAndroid server guidance.
        
        ### Event Generation Strategy:
        1. Capture current device state
        2. Check for external navigation (outside target app)
        3. Send state to RVAndroid server for action recommendation
        4. Convert server response to DroidBot InputEvent
        5. Handle errors with fallback policy
        
        ### State Management:
        Handles both target application states and external navigation scenarios,
        providing appropriate guidance and recovery mechanisms for each context.
        
        Returns:
            InputEvent object for device execution or None if generation fails
        """
        current_state: DeviceState = self.device.get_current_state()
        if current_state is None:
            self.logger.warning("Could not capture device state, using fallback")
            return self.fallback_policy.generate_event()

        # Check for external navigation
        current_package = self._extract_current_package(current_state)
        if not self._is_target_package(current_package):
            return self._handle_external_navigation(current_state, current_package)

        # Reset external navigation counter when back in target app
        if self.external_navigation_count > 0:
            self.logger.info("Returned to target application")
            self.external_navigation_count = 0

        # Process target application state
        return self._process_target_app_state(current_state)

    def _extract_current_package(self, state: DeviceState) -> Optional[str]:
        """
        Extract current foreground package from device state.
        
        Args:
            state: Current device state
            
        Returns:
            Package name string or None if extraction fails
        """
        if state.foreground_activity:
            return state.foreground_activity.split('/')[0]
        return None

    def _is_target_package(self, current_package: Optional[str]) -> bool:
        """
        Check if current package matches target application.
        
        Args:
            current_package: Current foreground package name
            
        Returns:
            True if current package is target application
        """
        return current_package == self.target_package

    def _handle_external_navigation(self, 
                                   current_state: DeviceState, 
                                   current_package: str) -> Optional[InputEvent]:
        """
        Handle navigation outside target application.
        
        ### External Navigation Strategy:
        Attempts to return to target application using server guidance or
        standard navigation actions. Implements attempt limiting to prevent
        infinite external navigation loops.
        
        Args:
            current_state: Current device state
            current_package: Current foreground package
            
        Returns:
            InputEvent to return to target application or restart it
        """
        self.external_navigation_count += 1
        self.logger.warning(f"External navigation - target: {self.target_package}, "
                           f"current: {current_package}, attempt: {self.external_navigation_count}")

        # Force app restart after max attempts
        if self.external_navigation_count >= self.max_external_attempts:
            self.logger.info("Max external attempts reached, restarting application")
            self._restart_application()
            return None

        # Try server guidance for external navigation
        try:
            state_data = self._prepare_state_data(current_state)
            state_data['external_navigation'] = True
            
            actions = self._get_actions_from_server(state_data)
            if actions:
                return self._convert_action_to_event(actions[0])
        except Exception as e:
            self.logger.error(f"Error processing external state: {e}")

        # Fallback to BACK key for external navigation
        return KeyEvent(name="BACK")

    def _process_target_app_state(self, current_state: DeviceState) -> Optional[InputEvent]:
        """
        Process state when target application is in foreground.
        
        ### Processing Pipeline:
        1. Prepare optimized state data for server transmission
        2. Request action recommendations from RVAndroid server
        3. Convert server response to DroidBot InputEvent
        4. Handle errors with fallback policy
        
        Args:
            current_state: Current device state with target app in foreground
            
        Returns:
            InputEvent for execution or fallback event on error
        """
        try:
            # Prepare state data for server
            state_data = self._prepare_state_data(current_state)
            
            # Get action recommendations from server
            actions = self._get_actions_from_server(state_data)
            
            if actions:
                # Reset error counter on successful response
                self.consecutive_errors = 0
                
                # Convert first action to InputEvent
                event = self._convert_action_to_event(actions[0])
                if event:
                    return event
                    
            # No valid actions received
            self.logger.warning("No valid actions from server, using fallback")
            return self.fallback_policy.generate_event()
            
        except Exception as e:
            self.logger.error(f"Error processing target app state: {e}")
            return self._handle_server_error()

    def _prepare_state_data(self, state: DeviceState) -> Dict[str, Any]:
        """
        Prepare optimized state data for server transmission.
        
        ### Optimization Strategy:
        Sends only essential data required by RVAndroid server for action
        generation, reducing bandwidth and processing overhead while maintaining
        all necessary information for intelligent decision making.
        
        Args:
            state: Current device state
            
        Returns:
            Optimized state data dictionary for server transmission
        """
        # Essential state data for RVAndroid server
        state_data = {
            "activity": state.foreground_activity,
            "package_name": self.app.get_package_name(),
            "view_tree": state.view_tree,
            "state_str": state.state_str
        }
        
        # Include screenshot for multimodal LLMs
        if self.include_screenshots and hasattr(state, 'screenshot_path') and state.screenshot_path:
            state_data["screenshot_path"] = state.screenshot_path
            self.logger.debug(f"Including screenshot: {state.screenshot_path}")
        
        # Log data optimization
        self.logger.debug(f"Prepared state data for activity: {state.foreground_activity}")
        return state_data

    def _get_actions_from_server(self, state_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Request action recommendations from RVAndroid server.
        
        ### Communication Protocol:
        Sends HTTP POST request with state data and receives action recommendations
        in complete format with all required fields for DroidBot execution.
        
        Args:
            state_data: Prepared state data for server
            
        Returns:
            List of complete action dictionaries from server
            
        Raises:
            requests.RequestException: On communication failure
            json.JSONDecodeError: On invalid server response
        """
        self.logger.info(f"Sending state to server: {self.server_url}")
        
        try:
            response = self.session.post(
                self.server_url,
                json=state_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                self.logger.error(f"Server returned status {response.status_code}: {response.text}")
                return []
            
            response_data = response.json()
            
            # Validate response format
            if "actions" not in response_data or not isinstance(response_data["actions"], list):
                self.logger.error(f"Invalid response format: {response_data}")
                return []
            
            actions = response_data["actions"]
            self.logger.info(f"Received {len(actions)} actions from server")
            
            return actions
            
        except requests.RequestException as e:
            self.logger.error(f"Server communication failed: {e}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON response: {e}")
            raise

    def _convert_action_to_event(self, action: Dict[str, Any]) -> Optional[InputEvent]:
        """
        Convert complete action specification to DroidBot InputEvent.
        
        ### Action Format Processing:
        Processes complete action format from RVAndroid server containing:
        - action_type: Standardized action type string
        - coordinates: Screen coordinates for action execution
        - params: Action-specific parameters
        - target: Target identifier for debugging
        - explanation: Human-readable action description
        
        ### Event Type Mapping:
        Maps action types to appropriate DroidBot InputEvent classes with
        proper parameter handling for reliable device interaction.
        
        Args:
            action: Complete action dictionary from server
            
        Returns:
            InputEvent object for device execution or None if conversion fails
        """
        action_type = action.get("action_type", "").lower()
        coordinates = action.get("coordinates", [])
        params = action.get("params", {})
        explanation = action.get("explanation", "")
        
        self.logger.debug(f"Converting action: {action_type} at {coordinates}")
        
        try:
            # Validate coordinates
            if coordinates and len(coordinates) >= 2:
                x, y = int(coordinates[0]), int(coordinates[1])
            else:
                self.logger.warning(f"Invalid coordinates for action: {action}")
                return None
            
            # Map action types to InputEvent objects
            if action_type == "click":
                return TouchEvent(x=x, y=y)
            
            elif action_type == "long_click":
                return LongTouchEvent(x=x, y=y)
            
            elif action_type in ["set_text", "text_change"]:
                text = params.get("text", "")
                return SetTextEvent(x=x, y=y, text=text)
            
            elif action_type.startswith("scroll"):
                direction = params.get("direction", "DOWN")
                return ScrollEvent(x=x, y=y, direction=direction.upper())
            
            elif action_type == "key_event":
                key_name = params.get("name", "BACK")
                return KeyEvent(name=key_name.upper())
            
            else:
                self.logger.warning(f"Unknown action type: {action_type}")
                return None
                
        except (ValueError, TypeError) as e:
            self.logger.error(f"Error converting action {action}: {e}")
            return None

    def _handle_server_error(self) -> Optional[InputEvent]:
        """
        Handle server communication or processing errors.
        
        ### Error Recovery Strategy:
        Implements progressive error handling with consecutive error tracking
        and fallback to greedy search policy when error threshold is exceeded.
        
        Returns:
            Fallback InputEvent or BACK key event for error recovery
        """
        self.consecutive_errors += 1
        
        if self.consecutive_errors >= self.max_consecutive_errors:
            self.logger.warning(f"Too many consecutive errors ({self.consecutive_errors}), "
                               f"using fallback policy")
            self.consecutive_errors = 0
            return self.fallback_policy.generate_event()
        
        # Simple BACK key for temporary errors
        self.logger.debug("Using BACK key for error recovery")
        return KeyEvent(name="BACK")

    def _restart_application(self) -> None:
        """
        Restart target application using proper DroidBot lifecycle management.
        
        ### Restart Strategy:
        Uses DroidBot's application lifecycle management to cleanly stop
        and restart the target application, providing reliable recovery
        from external navigation scenarios.
        """
        try:
            self.logger.info(f"Restarting application: {self.target_package}")
            
            # Stop application
            stop_intent = self.app.get_stop_intent()
            self.device.send_intent(stop_intent)
            time.sleep(2)
            
            # Start application
            self.device.start_app(self.app)
            
            # Reset external navigation counter
            self.external_navigation_count = 0
            
            self.logger.info("Application restart completed")
            
        except Exception as e:
            self.logger.error(f"Application restart failed: {e}")