"""
Mock device interface for offline validation.

Simulates device interaction by reading from pre-captured files instead of
connecting to an actual Android device.
"""

import base64
import logging
from pathlib import Path
from typing import Dict, Optional

from rv_agent.validation.sequence_loader import AppSequence, ScreenData
from rv_agent.validation.action_validator import ActionValidator, ValidationResult

logger = logging.getLogger(__name__)


class MockDeviceInterface:
    """
    Mock DeviceInterface that reads from pre-captured files.

    Replaces DeviceInterface for offline validation. Provides the same
    API but reads from files instead of connecting to a device.

    Key behaviors:
    - Actions advance the sequence to next screen
    - Actions are validated against actual UI elements
    - Invalid actions are logged but still advance sequence
    - Sequence loops back to start when exhausted
    """

    def __init__(self, sequence: AppSequence, device_id: str = "mock"):
        """
        Initialize mock device interface.

        Args:
            sequence: AppSequence to simulate
            device_id: Mock device ID
        """
        self.sequence = sequence
        self.device_id = device_id
        self.logger = logger

        # Current position in sequence
        self.current_step = 0

        # Action validator
        self.validator = ActionValidator()

        # Load initial screen UI elements
        if self.sequence.screens:
            self.validator.load_ui_elements(self.current_screen.uiautomator_path)

        # Action tracking
        self.actions_executed = []

        logger.info(f"MockDeviceInterface initialized: {sequence.app_name}")
        logger.info(f"  Sequence length: {len(sequence.screens)} screens")
        logger.info(f"  Starting at step: {self.current_step + 1}")

    @property
    def current_screen(self) -> ScreenData:
        """Get current screen data."""
        return self.sequence.screens[self.current_step]

    def _advance_sequence(self, action_type: str, validation: ValidationResult):
        """
        Advance to next screen in sequence.

        Args:
            action_type: Type of action executed
            validation: Validation result
        """
        # Record action
        self.actions_executed.append({
            'step': self.current_step + 1,
            'action_type': action_type,
            'valid': validation.valid,
            'reason': validation.reason,
            'element': str(validation.element) if validation.element else None
        })

        # Log validation
        if not validation.valid:
            logger.warning(f"❌ Invalid {action_type}: {validation.reason}")
        else:
            logger.info(f"✅ Valid {action_type}: {validation.reason}")

        # Advance sequence
        self.current_step = (self.current_step + 1) % len(self.sequence.screens)

        # Load UI elements for new screen
        self.validator.load_ui_elements(self.current_screen.uiautomator_path)

        logger.info(f"Advanced to step {self.current_step + 1}/{len(self.sequence.screens)}: "
                   f"{self.current_screen.activity}")

    def get_current_ui_state(self) -> Dict:
        """
        Get current UI state by reading UIAutomator XML file.

        Returns:
            Dictionary with UI state data (matches UIAutomator2 format)
        """
        try:
            # Read UIAutomator XML
            with open(self.current_screen.uiautomator_path, 'r') as f:
                xml_content = f.read()

            return {
                'xml': xml_content,
                'current_activity': self.current_screen.activity,
                'current_package': self.current_screen.package
            }

        except Exception as e:
            logger.error(f"Failed to read UI state: {e}")
            return {
                'xml': '',
                'current_activity': 'unknown',
                'current_package': 'unknown'
            }

    def get_screenshot(self) -> Optional[bytes]:
        """
        Get screenshot by reading PNG file.

        Returns:
            Screenshot as PNG bytes, or None if error
        """
        try:
            with open(self.current_screen.screenshot_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read screenshot: {e}")
            return None

    def take_screenshot(self, output_dir: str = "/tmp") -> Optional[str]:
        """
        Mock screenshot capture (returns path to pre-captured screenshot).

        Args:
            output_dir: Ignored in mock mode

        Returns:
            Path to screenshot file
        """
        return str(self.current_screen.screenshot_path)

    def get_screenshot_base64(self) -> str:
        """
        Get screenshot as base64 string.

        Returns:
            Base64-encoded screenshot
        """
        screenshot = self.get_screenshot()
        if screenshot:
            return base64.b64encode(screenshot).decode('utf-8')
        return ""

    def get_current_activity(self) -> str:
        """
        Get current activity name.

        Returns:
            Activity name
        """
        return self.current_screen.activity

    def get_current_package(self) -> str:
        """
        Get current package name.

        Returns:
            Package name
        """
        return self.current_screen.package

    def click(self, x: int, y: int) -> bool:
        """
        Simulate click action.

        Validates click and advances sequence.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            True (always succeeds in mock mode)
        """
        logger.debug(f"Click at ({x}, {y})")

        # Validate action
        validation = self.validator.validate_click(x, y)

        # Advance sequence
        self._advance_sequence('CLICK', validation)

        return True

    def input_text(self, text: str) -> bool:
        """
        Input text into currently focused element.

        This is called by android_type_text after clicking to focus.
        In mock mode, we don't need to do anything - just return success.

        Args:
            text: Text to input

        Returns:
            True (always succeeds in mock mode)
        """
        logger.debug(f"Input text: '{text}' (mock mode - no-op)")
        return True

    def type_text(self, text: str, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """
        Simulate type text action.

        Validates target element and advances sequence.

        Args:
            text: Text to type
            x: X coordinate (optional)
            y: Y coordinate (optional)

        Returns:
            True (always succeeds in mock mode)
        """
        logger.debug(f"Type text: '{text}' at ({x}, {y})")

        # If coordinates provided, validate target element
        if x is not None and y is not None:
            validation = self.validator.validate_type_text(x, y, text)
        else:
            # No coordinates - assume system action (valid)
            validation = ValidationResult(
                valid=True,
                reason="Type text (no coordinates provided)"
            )

        # Advance sequence
        self._advance_sequence('SET_TEXT', validation)

        return True

    def long_click(self, x: int, y: int) -> bool:
        """
        Simulate long click action.

        Validates long click and advances sequence.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            True (always succeeds in mock mode)
        """
        logger.debug(f"Long click at ({x}, {y})")

        # Validate action
        validation = self.validator.validate_long_click(x, y)

        # Advance sequence
        self._advance_sequence('LONG_CLICK', validation)

        return True

    def back(self) -> bool:
        """
        Simulate BACK button press.

        System action - always valid.

        Returns:
            True (always succeeds in mock mode)
        """
        logger.debug("Press BACK button")

        # Validate as system action
        validation = self.validator.validate_system_action('BACK')

        # Advance sequence
        self._advance_sequence('BACK', validation)

        return True

    def home(self) -> bool:
        """
        Simulate HOME button press.

        System action - always valid.

        Returns:
            True (always succeeds in mock mode)
        """
        logger.debug("Press HOME button")

        # Validate as system action
        validation = self.validator.validate_system_action('HOME')

        # Advance sequence
        self._advance_sequence('HOME', validation)

        return True

    def launch_app(self, package_name: str) -> bool:
        """
        Simulate app launch.

        In mock mode, this is a no-op since sequence starts at app screen.

        Args:
            package_name: Package name to launch

        Returns:
            True (always succeeds in mock mode)
        """
        logger.info(f"Launch app: {package_name} (no-op in mock mode)")
        return True

    def disable_soft_keyboard(self) -> bool:
        """
        Mock keyboard disable.

        In mock mode, this is a no-op.

        Returns:
            True (always succeeds in mock mode)
        """
        logger.debug("Disable soft keyboard (no-op in mock mode)")
        return True

    def get_action_summary(self) -> Dict:
        """
        Get summary of actions executed.

        Returns:
            Dictionary with action statistics
        """
        total = len(self.actions_executed)
        valid = sum(1 for a in self.actions_executed if a['valid'])
        invalid = total - valid

        action_types = {}
        for action in self.actions_executed:
            atype = action['action_type']
            action_types[atype] = action_types.get(atype, 0) + 1

        return {
            'total_actions': total,
            'valid_actions': valid,
            'invalid_actions': invalid,
            'valid_rate': valid / total if total > 0 else 0.0,
            'action_types': action_types,
            'actions': self.actions_executed
        }

    def get_current_step(self) -> int:
        """Get current step number (1-indexed)."""
        return self.current_step + 1

    def get_sequence_length(self) -> int:
        """Get total sequence length."""
        return len(self.sequence.screens)
