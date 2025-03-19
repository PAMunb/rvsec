import json
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple


class ActionReplay:
    """
    Tool for replaying recorded action sequences from previous test sessions.
    Helps with debugging, regression testing, and reproducing issues.
    """

    def __init__(self, log_dir: str = None):
        """
        Initialize the action replay tool.

        Args:
            log_dir: Directory containing session logs (optional)
        """
        # Import here to avoid circular imports
        from rvandroid.util.logging_manager import LoggingManager
        self.logger = LoggingManager.get_instance().get_logger('session_replay')
        self.log_dir = log_dir

    def load_session(self, session_file: str) -> List[Dict[str, Any]]:
        """
        Load a recorded session from a file.

        Args:
            session_file: Path to session file

        Returns:
            List of action records
        """
        self.logger.info(f"Loading session from {session_file}")

        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)

            if isinstance(session_data, list):
                return session_data
            elif isinstance(session_data, dict) and 'actions' in session_data:
                return session_data['actions']
            else:
                self.logger.error(f"Invalid session format in {session_file}")
                return []

        except Exception as e:
            self.logger.error(f"Error loading session: {e}")
            return []

    def save_session(self, actions: List[Dict[str, Any]], file_path: str) -> bool:
        """
        Save a session to a file.

        Args:
            actions: List of action records
            file_path: Path to save the session file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

            # Add metadata
            session_data = {
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'action_count': len(actions)
                },
                'actions': actions
            }

            # Save to file
            with open(file_path, 'w') as f:
                json.dump(session_data, f, indent=2)

            self.logger.info(f"Session saved to {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving session: {e}")
            return False

    def extract_session_from_logs(self, logcat_file: str) -> List[Dict[str, Any]]:
        """
        Extract a session from logcat file.

        Args:
            logcat_file: Path to logcat file

        Returns:
            List of extracted actions
        """
        self.logger.info(f"Extracting session from logcat: {logcat_file}")

        actions = []
        try:
            # Read logcat file
            with open(logcat_file, 'r') as f:
                lines = f.readlines()

            # Extract actions from logs
            for line in lines:
                # Look for lines with action execution info
                if "Executing action" in line and "coordinates" in line:
                    try:
                        # Extract action info
                        parts = line.split("Executing action")
                        if len(parts) < 2:
                            continue

                        action_part = parts[1].strip()

                        # Try to extract key information from the log
                        action_type = None
                        target = None
                        coordinates = None

                        if "action_type" in action_part:
                            action_type_match = re.search(r"action_type['\"]:\s*['\"]([^'\"]+)", action_part)
                            if action_type_match:
                                action_type = action_type_match.group(1)

                        if "target" in action_part:
                            target_match = re.search(r"target['\"]:\s*['\"]([^'\"]+)", action_part)
                            if target_match:
                                target = target_match.group(1)

                        if "coordinates" in action_part:
                            coord_match = re.search(r"coordinates['\"]:\s*\[(\d+),\s*(\d+)\]", action_part)
                            if coord_match:
                                x = int(coord_match.group(1))
                                y = int(coord_match.group(2))
                                coordinates = [x, y]

                        # Create action record
                        if action_type:
                            action = {
                                'action_type': action_type,
                                'timestamp': self._extract_timestamp(line)
                            }

                            if target:
                                action['target'] = target

                            if coordinates:
                                action['coordinates'] = coordinates

                            actions.append(action)

                    except Exception as e:
                        self.logger.warning(f"Error parsing action from log line: {e}")

            self.logger.info(f"Extracted {len(actions)} actions from logcat")
            return actions

        except Exception as e:
            self.logger.error(f"Error extracting session from logcat: {e}")
            return []

    def _extract_timestamp(self, log_line: str) -> Optional[str]:
        """Extract timestamp from a log line."""
        try:
            # Most log formats have timestamp at the beginning
            timestamp_match = re.search(r"(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})", log_line)
            if timestamp_match:
                return timestamp_match.group(1)
            return None
        except:
            return None

    def replay_session(self, session: List[Dict[str, Any]], device_id: str = "emulator-5554") -> Tuple[bool, List[str]]:
        """
        Replay a session using adb commands.

        Args:
            session: List of action records
            device_id: Target device ID

        Returns:
            Tuple of (success, errors)
        """
        self.logger.info(f"Replaying session with {len(session)} actions on device {device_id}")

        errors = []
        success = True

        for i, action in enumerate(session):
            try:
                action_type = action.get('action_type')
                if not action_type:
                    errors.append(f"Action {i}: Missing action_type")
                    continue

                self.logger.info(f"Replaying action {i + 1}/{len(session)}: {action_type}")

                if action_type == 'click':
                    # Get coordinates
                    coordinates = action.get('coordinates')
                    if not coordinates or len(coordinates) < 2:
                        errors.append(f"Action {i}: Missing coordinates for click")
                        continue

                    x, y = coordinates

                    # Execute tap command
                    cmd = f"adb -s {device_id} shell input tap {x} {y}"
                    os.system(cmd)

                elif action_type == 'long_click':
                    # Get coordinates
                    coordinates = action.get('coordinates')
                    if not coordinates or len(coordinates) < 2:
                        errors.append(f"Action {i}: Missing coordinates for long_click")
                        continue

                    x, y = coordinates

                    # Execute swipe command with same start/end points (simulates long press)
                    cmd = f"adb -s {device_id} shell input swipe {x} {y} {x} {y} 1000"
                    os.system(cmd)

                elif action_type == 'scroll_up' or action_type == 'scroll_down':
                    # Get coordinates or use screen center
                    coordinates = action.get('coordinates', [500, 500])
                    if len(coordinates) < 2:
                        coordinates = [500, 500]

                    x, y = coordinates

                    # Determine direction
                    if action_type == 'scroll_up':
                        # Swipe from bottom to top
                        cmd = f"adb -s {device_id} shell input swipe {x} {y + 300} {x} {y - 300} 500"
                    else:
                        # Swipe from top to bottom
                        cmd = f"adb -s {device_id} shell input swipe {x} {y - 300} {x} {y + 300} 500"

                    os.system(cmd)

                elif action_type == 'set_text':
                    # Get text
                    text = action.get('params', {}).get('text', '')
                    if not text:
                        errors.append(f"Action {i}: Missing text for set_text")
                        continue

                    # First tap on the target to focus
                    coordinates = action.get('coordinates')
                    if coordinates and len(coordinates) >= 2:
                        x, y = coordinates
                        tap_cmd = f"adb -s {device_id} shell input tap {x} {y}"
                        os.system(tap_cmd)
                        time.sleep(0.5)  # Wait for keyboard

                    # Execute text input command
                    # For special characters, we need to escape them
                    escaped_text = text.replace(' ', '%s').replace('&', '\&').replace('<', '\<').replace('>', '\>')
                    cmd = f"adb -s {device_id} shell input text '{escaped_text}'"
                    os.system(cmd)

                elif action_type == 'key_event':
                    # Get key event
                    key = action.get('params', {}).get('name', 'BACK')

                    # Execute key event command
                    cmd = f"adb -s {device_id} shell input keyevent KEYCODE_{key}"
                    os.system(cmd)

                # Add a small delay between actions
                time.sleep(0.5)

            except Exception as e:
                self.logger.error(f"Error replaying action {i}: {e}")
                errors.append(f"Action {i}: {str(e)}")
                success = False

        self.logger.info(f"Session replay completed with status: {'success' if success else 'failure'}")
        return success, errors

    def record_current_session(self, actions: List[Dict[str, Any]], session_name: Optional[str] = None) -> str:
        """
        Record the current session.

        Args:
            actions: List of actions performed
            session_name: Optional session name

        Returns:
            Path to the saved session file
        """
        if not session_name:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            session_name = f"session_{timestamp}"

        if not self.log_dir:
            # Use a default log directory
            self.log_dir = os.path.join(os.getcwd(), "sessions")

        # Create log directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)

        # Create session file path
        session_file = os.path.join(self.log_dir, f"{session_name}.json")

        # Save session
        self.save_session(actions, session_file)

        return session_file
