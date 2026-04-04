"""
State format conversion utilities.

Convert between UIAutomator and DroidBot state representations. The UIAutomator
adapter captures state with keys like ``xml``, ``current_activity``, and
``current_package``, while DroidBot parsers expect ``hierarchy``/``view_tree``,
``activity``, and ``package_name``. This module bridges that gap.

### Architectural Decisions:
    This is a temporary adapter. A proper DeviceState model with typed attributes
    should replace dictionary-based state passing in the future.

### Integration Points:
    - rv-agent's StateEnricher consumes the DroidBot-format output
    - Screen hashes feed into the DFS exploration strategy for state identification
"""

import hashlib
from typing import Any, Dict, Optional

from pydantic import Field
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.validation import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model

from ..constants import SCREEN_HASH_LENGTH


@validated_model(["source_format", "target_format"])
class StateConversionMetrics(BaseValidatedModel):
    """
    Metrics for state conversion operations.

    ### Architectural Role:
    - Tracks conversion performance and accuracy
    - Provides diagnostics for format compatibility
    - Enables optimization of conversion processes
    """

    source_format: str = Field(description="Original state format identifier")
    target_format: str = Field(description="Target state format identifier")
    fields_converted: int = Field(default=0, description="Number of fields converted")
    fields_preserved: int = Field(
        default=0, description="Number of fields preserved unchanged"
    )
    conversion_time_ms: float = Field(
        default=0.0, description="Conversion time in milliseconds"
    )


class StateConverter:
    """
    Converts between different UI state representations.

    ### Architectural Decisions:
    - Provides unidirectional conversion from UIAutomator to DroidBot format
    - Maintains all essential state information during conversion
    - Handles missing fields gracefully with defaults
    - Preserves screenshot and hierarchy data integrity
    - Uses BaseValidatedModel for conversion metrics

    ### Role in the System:
    - Enables compatibility between UIAutomator and DroidBot formats
    - Allows reuse of existing StateEnricher without modification
    - Provides clear documentation of format differences
    - Temporary solution until full state model implementation

    ### Note on Future Evolution:
    This converter is a temporary solution. Future versions should
    implement a proper DeviceState model with typed attributes.
    """

    def __init__(self):
        """Initialize state converter.

        State:
            logger: Component logger with StateConverter context.
        """
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_uiautomator.state.converter", {CONTEXT_COMPONENT: "StateConverter"}
        )

        self.logger.debug("StateConverter initialized")

    @ErrorHandler.handle_errors(
        component="StateConverter", phase="format_conversion", default_return={}
    )
    def uiautomator_to_droidbot(self, ui_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert UIAutomator state format to DroidBot-compatible format.

        ### Format Mapping:
        - UIAutomator 'xml' -> DroidBot 'hierarchy'
        - UIAutomator 'current_activity' -> DroidBot 'activity'
        - UIAutomator 'current_package' -> DroidBot 'package_name'
        - Preserves screenshot_path, device_info unchanged

        Args:
            ui_state: UIAutomator state dictionary

        Returns:
            DroidBot-compatible state dictionary
        """
        if not ui_state:
            self.logger.warning("Empty UI state provided for conversion")
            return {}

        try:
            # Core field mappings
            # STATE_CONVERSION_FIX: DroidBot parser expects 'view_tree', not 'hierarchy'
            converted = {
                "view_tree": ui_state.get("xml", ""),  # DroidBot expects view_tree
                "hierarchy": ui_state.get(
                    "xml", ""
                ),  # Keep hierarchy for compatibility
                "activity": ui_state.get("current_activity", "unknown"),
                "package_name": ui_state.get("current_package", "unknown"),
                "screenshot_path": ui_state.get("screenshot_path"),
                "device_info": ui_state.get("device_info", {}),
                "views": [],  # Not used when view_tree is present
                "enabled_actions": [],  # Will be populated by parser
            }

            # Preserve any additional fields that don't conflict
            preserved_count = 0
            for key, value in ui_state.items():
                if key not in ["xml", "current_activity", "current_package"]:
                    if key not in converted:
                        converted[key] = value
                        preserved_count += 1

            # Add conversion metadata
            converted["_conversion_metadata"] = {
                "source_format": "uiautomator",
                "target_format": "droidbot",
                "converted_fields": [
                    "xml->hierarchy",
                    "current_activity->activity",
                    "current_package->package_name",
                ],
                "preserved_fields": preserved_count,
            }

            self.logger.debug(
                f"State conversion completed: {len(converted)} fields in result"
            )
            return converted

        except Exception as e:
            self.logger.error(f"State conversion failed: {e}")
            return {}

    @ErrorHandler.handle_errors(
        component="StateConverter", phase="screen_hash_computation", default_return=None
    )
    def compute_screen_hash(self, state: Dict[str, Any]) -> Optional[str]:
        """
        Compute screen hash for state identification.

        ### Hash Strategy:
        Uses hierarchy structure when available, falls back to activity
        name for consistent screen identification across system.

        Args:
            state: Current application state

        Returns:
            Screen hash string or None if computation fails
        """
        try:
            # Use hierarchy structure when available (preferred)
            hierarchy = state.get("hierarchy") or state.get("xml")
            if hierarchy:
                # Use first 500 chars of hierarchy for structure-based hash
                hash_data = str(hierarchy)[:500]
                return hashlib.sha256(hash_data.encode()).hexdigest()[
                    :SCREEN_HASH_LENGTH
                ]

            # Fallback to activity-based hash
            activity = state.get("activity") or state.get("current_activity", "unknown")
            package = state.get("package_name") or state.get(
                "current_package", "unknown"
            )

            hash_data = f"{package}/{activity}"
            return hashlib.sha256(hash_data.encode()).hexdigest()[:SCREEN_HASH_LENGTH]

        except Exception as e:
            self.logger.error(f"Screen hash computation failed: {e}")
            return None
