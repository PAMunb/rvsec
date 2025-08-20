"""
RVAndroid policy for DroidBot integration.

This module provides DroidBot policy implementation that communicates with 
RVAndroid server for AI-driven action generation, enabling intelligent test
exploration guided by large language models.
"""

import json
import logging
import os
import requests
import time
from typing import Dict, List, Any, Optional

from droidbot.app import App
from droidbot.device import Device
from droidbot.device_state import DeviceState
from droidbot.input_event import (
    BackEvent, InputEvent, KeyEvent, RestartEvent, TouchEvent, LongTouchEvent, 
    ScrollEvent, SetTextEvent, IntentEvent, CompoundEvent
)
from .input_policy import UtgBasedInputPolicy, UtgGreedySearchPolicy, POLICY_GREEDY_DFS

# Local constants (no external dependencies to maintain DroidBot independence)
REQUEST_TYPE_JSON = "json"
REQUEST_TYPE_MULTIPART = "multipart"
SERVER_REQUEST_TIMEOUT = 60
MAX_SCREENSHOT_SIZE_MB = 10
CUSTOM_ACTION_PREFIX = "custom:"
MAX_COMPOUND_ACTIONS = 5
COORDINATE_VALIDATION_MIN = 0
COORDINATE_VALIDATION_MAX = 4096


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
        self.app_started = False  # Track if app has been started
        
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

        # Check if app needs to be started for the first time
        current_package = self._extract_current_package(current_state)
        if not self.app_started and not self._is_target_package(current_package):
            self.logger.info("App not started yet, launching target application")
            self.app_started = True
            return self._start_target_app()

        # Check for external navigation
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
                
                # Handle single vs multiple actions
                if len(actions) == 1:
                    # Single action - existing logic
                    event = self._convert_action_to_event(actions[0])
                    if event:
                        return event
                else:
                    # Multiple actions - create CompoundEvent
                    self.logger.info(f"Processing {len(actions)} actions as CompoundEvent")
                    compound_event = self._create_compound_event(actions)
                    if compound_event:
                        return compound_event
                    
            # No valid actions received
            self.logger.warning("No valid actions from server, using fallback")
            return self.fallback_policy.generate_event()
            
        except Exception as e:
            self.logger.error(f"Error processing target app state: {e}")
            return self._handle_server_error()

    def _create_compound_event(self, actions: List[Dict[str, Any]]) -> Optional[InputEvent]:
        """
        Create CompoundEvent for executing multiple actions sequentially.
        
        ### Multiple Action Strategy:
        Converts list of actions to CompoundEvent for atomic execution,
        providing robust handling of action sequences like form completion
        or multi-step navigation workflows.
        
        ### Error Handling:
        Validates each action individually before creating CompoundEvent,
        falling back to single action or None if conversion fails.
        
        Args:
            actions: List of action dictionaries from server
            
        Returns:
            CompoundEvent containing converted actions or None if conversion fails
        """
        if not actions:
            self.logger.warning("No actions provided for CompoundEvent")
            return None
            
        # Limit number of actions for safety
        if len(actions) > MAX_COMPOUND_ACTIONS:
            self.logger.warning(f"Too many actions ({len(actions)}), limiting to {MAX_COMPOUND_ACTIONS}")
            actions = actions[:MAX_COMPOUND_ACTIONS]
            
        converted_events = []
        failed_conversions = 0
        
        for i, action in enumerate(actions):
            event = self._convert_action_to_event(action)
            if event:
                converted_events.append(event)
                self.logger.debug(f"Action {i+1} converted: {action.get('explanation', 'no explanation')}")
            else:
                failed_conversions += 1
                self.logger.warning(f"Failed to convert action {i+1}: {action}")
                
        # Require at least one successful conversion
        if not converted_events:
            self.logger.error("No actions could be converted to events")
            return None
            
        # Log conversion results
        success_rate = len(converted_events) / len(actions)
        self.logger.info(f"CompoundEvent created: {len(converted_events)}/{len(actions)} actions converted "
                        f"(success rate: {success_rate:.1%})")
        
        if failed_conversions > 0:
            self.logger.warning(f"{failed_conversions} actions failed conversion but proceeding with CompoundEvent")
            
        return CompoundEvent(converted_events)

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
            # Check if screenshot file actually exists
            if os.path.exists(state.screenshot_path):
                state_data["screenshot_path"] = state.screenshot_path
                state_data["_send_screenshot"] = True  # Flag to indicate multipart upload needed
                self.logger.debug(f"Including screenshot for upload: {state.screenshot_path}")
            else:
                self.logger.warning(f"Screenshot path does not exist: {state.screenshot_path}")
        
        # Log data optimization
        self.logger.debug(f"Prepared state data for activity: {state.foreground_activity}")
        return state_data

    def _get_actions_from_server(self, state_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Request action recommendations from RVAndroid server.
        
        ### Communication Protocol:
        Supports both JSON and multipart requests. Uses multipart when screenshot 
        upload is required, JSON otherwise for optimal performance.
        
        Args:
            state_data: Prepared state data for server
            
        Returns:
            List of complete action dictionaries from server
            
        Raises:
            requests.RequestException: On communication failure
            json.JSONDecodeError: On invalid server response
        """
        # Choose request type based on screenshot upload requirement
        if state_data.get("_send_screenshot") and state_data.get("screenshot_path"):
            return self._send_multipart_request(state_data)
        else:
            return self._send_json_request(state_data)

    def _send_json_request(self, state_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Send state data as JSON request (existing logic).
        
        ### JSON Request Strategy:
        Standard JSON request for scenarios without screenshot upload,
        maintaining optimal performance for text-only interactions.
        
        Args:
            state_data: State data dictionary
            
        Returns:
            List of action dictionaries from server
        """
        self.logger.info(f"Sending JSON request to server: {self.server_url}")
        
        # Clean internal flags before sending
        clean_state_data = {k: v for k, v in state_data.items() if not k.startswith("_")}
        
        try:
            response = self.session.post(
                self.server_url,
                json=clean_state_data,
                headers={"Content-Type": "application/json"},
                timeout=SERVER_REQUEST_TIMEOUT
            )
            
            return self._process_server_response(response, REQUEST_TYPE_JSON)
            
        except requests.RequestException as e:
            self.logger.error(f"JSON request failed: {e}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON response: {e}")
            raise

    def _send_multipart_request(self, state_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Send state data with screenshot as multipart request.
        
        ### Multipart Request Strategy:
        Sends screenshot file and state data for multimodal LLM processing.
        The server expects 'screenshot' file and 'state' JSON data fields.
        
        Args:
            state_data: State data dictionary with screenshot path
            
        Returns:
            List of action dictionaries from server
        """
        screenshot_path = state_data.get("screenshot_path")
        if not screenshot_path or not os.path.exists(screenshot_path):
            self.logger.warning("Screenshot path invalid for multipart request, falling back to JSON")
            return self._send_json_request(state_data)
        
        self.logger.info(f"Sending multipart request with screenshot to server: {self.server_url}")
        
        # Prepare clean state data (remove internal flags and screenshot_path)
        clean_state_data = {k: v for k, v in state_data.items() 
                           if not k.startswith("_") and k != "screenshot_path"}
        
        # Debug logging
        self.logger.debug(f"Screenshot path: {screenshot_path}")
        self.logger.debug(f"Clean state data keys: {list(clean_state_data.keys())}")
        self.logger.debug(f"Clean state data size: {len(str(clean_state_data))} chars")
        
        try:
            # Check file size
            file_size_mb = os.path.getsize(screenshot_path) / (1024 * 1024)
            if file_size_mb > MAX_SCREENSHOT_SIZE_MB:
                self.logger.warning(f"Screenshot too large ({file_size_mb:.1f}MB), falling back to JSON")
                return self._send_json_request(state_data)
            
            # Prepare multipart data
            with open(screenshot_path, 'rb') as screenshot_file:
                files = {
                    'screenshot': (
                        os.path.basename(screenshot_path),
                        screenshot_file,
                        'image/png'
                    )
                }
                # Prepare form data
                json_state = json.dumps(clean_state_data)
                data = {
                    'state': json_state
                }
                
                # Debug logging before send
                self.logger.debug(f"File size: {file_size_mb:.2f}MB")
                self.logger.debug(f"JSON state length: {len(json_state)} chars")
                self.logger.debug(f"JSON state preview: {json_state[:200]}...")
                
                response = self.session.post(
                    self.server_url,
                    files=files,
                    data=data,
                    timeout=SERVER_REQUEST_TIMEOUT
                )
                
            return self._process_server_response(response, REQUEST_TYPE_MULTIPART)
            
        except requests.RequestException as e:
            self.logger.error(f"Multipart request failed: {e}")
            raise
        except (OSError, IOError) as e:
            self.logger.error(f"Screenshot file error: {e}")
            # Fall back to JSON request without screenshot
            return self._send_json_request(state_data)
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON response: {e}")
            raise

    def _process_server_response(self, response: requests.Response, request_type: str) -> List[Dict[str, Any]]:
        """
        Process server response and validate action format.
        
        ### Response Processing:
        Validates server response format and extracts action list with
        comprehensive error handling for malformed responses.
        
        Args:
            response: HTTP response from server
            request_type: Type of request (json/multipart) for logging
            
        Returns:
            List of validated action dictionaries
        """
        if response.status_code != 200:
            self.logger.error(f"Server returned status {response.status_code} for {request_type} request: {response.text}")
            return []
        
        try:
            response_data = response.json()
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON response for {request_type} request: {e}")
            return []
        
        # Validate response format
        if "actions" not in response_data or not isinstance(response_data["actions"], list):
            self.logger.error(f"Invalid response format for {request_type} request: {response_data}")
            return []
        
        actions = response_data["actions"]
        self.logger.info(f"Received {len(actions)} actions from server via {request_type} request")
        
        if actions:
            print(f"Received actions:\n{json.dumps(actions, indent=2)}")
        
        return actions

    def _convert_action_to_event(self, action: Dict[str, Any]) -> Optional[InputEvent]:
        """
        Convert complete action specification to DroidBot InputEvent.
        
        ### Action Format Processing:
        Processes complete action format from RVAndroid server with support for
        three action types: standard UI actions, text input actions, and custom
        coordinate-based actions for multimodal interaction scenarios.
        
        ### Action Type Support:
        - Standard UI Actions: Target specific UI elements via coordinates
        - Text Input Actions: Include text parameters for form completion
        - Custom Coordinate Actions: Screenshot-based interaction for games/canvas
        
        ### Event Type Mapping:
        Maps action types to appropriate DroidBot InputEvent classes with
        comprehensive parameter handling and validation for reliable execution.
        
        Args:
            action: Complete action dictionary from RVAndroid server
            
        Returns:
            InputEvent object for device execution or None if conversion fails
        """
        action_type = action.get("action_type", "").lower()
        coordinates = action.get("coordinates", [])
        params = action.get("params", {})
        explanation = action.get("explanation", "")
        target = action.get("target", "")
        
        self.logger.debug(f"Converting action: {action_type} at {coordinates} (target: {target})")
        
        try:
            # Handle coordinate validation for all action types
            if coordinates and len(coordinates) >= 2:
                x, y = int(coordinates[0]), int(coordinates[1])
                
                # Validate coordinate range for safety
                if not (COORDINATE_VALIDATION_MIN <= x <= COORDINATE_VALIDATION_MAX and
                        COORDINATE_VALIDATION_MIN <= y <= COORDINATE_VALIDATION_MAX):
                    self.logger.warning(f"Coordinates out of safe range: ({x}, {y})")
                    return None
                    
            else:
                self.logger.warning(f"Invalid coordinates format for action: {action}")
                return None
            
            # Detect custom coordinate actions (from Vision Strategy)
            is_custom_action = target.startswith(CUSTOM_ACTION_PREFIX) if target else False
            if is_custom_action:
                self.logger.info(f"Processing custom coordinate action from Vision Strategy: {explanation}")
            
            # Map action types to InputEvent objects with enhanced support
            if action_type == "click":
                return TouchEvent(x=x, y=y)
            
            elif action_type == "long_click":
                return LongTouchEvent(x=x, y=y)
            
            elif action_type in ["set_text", "text_change"]:
                text = params.get("text", "")
                if not text and not is_custom_action:
                    self.logger.warning(f"No text provided for text action: {action}")
                    return None
                return SetTextEvent(x=x, y=y, text=text)
            
            elif action_type.startswith("scroll"):
                direction = params.get("direction", "DOWN").upper()
                if direction not in ["UP", "DOWN", "LEFT", "RIGHT"]:
                    self.logger.warning(f"Invalid scroll direction: {direction}")
                    direction = "DOWN"
                return ScrollEvent(x=x, y=y, direction=direction)
            
            elif action_type == "back":   
                self.logger.info("Processing system BACK action")             
                return BackEvent()
            elif action_type == "restart":   
                self.logger.info(f"Processing system RESTART action")                             
                return RestartEvent(self.app)
            
            # Handle additional action types for custom coordinate actions
            elif action_type in ["tap", "touch"]:
                # Alternative names for click in custom actions
                return TouchEvent(x=x, y=y)
            
            elif action_type == "long_tap":
                # Alternative name for long click in custom actions  
                return LongTouchEvent(x=x, y=y)
            
            else:
                self.logger.warning(f"Unknown action type: {action_type}, defaulting to click")
                # Default to click for unknown action types in multimodal scenarios
                return TouchEvent(x=x, y=y)
                
        except (ValueError, TypeError) as e:
            self.logger.error(f"Error converting action {action}: {e}", exc_info=True)
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

    def _start_target_app(self) -> Optional[InputEvent]:
        """
        Generate event to start the target application.
        
        ### Start Strategy:
        Creates an IntentEvent with the app's start intent to launch the
        target application. This is used when the app needs to be started
        for the first time or after a kill event.
        
        Returns:
            IntentEvent to start the target application
        """
        try:
            self.logger.info(f"Generating start event for application: {self.target_package}")
            start_intent = self.app.get_start_intent()
            return IntentEvent(intent=start_intent)
            
        except Exception as e:
            self.logger.error(f"Failed to generate start event: {e}")
            return None

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
            
            # Reset external navigation counter and app started flag
            self.external_navigation_count = 0
            self.app_started = True
            
            self.logger.info("Application restart completed")
            
        except Exception as e:
            self.logger.error(f"Application restart failed: {e}")