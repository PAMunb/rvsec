# rvandroid/util/logcat_manager.py - Pydantic v2 migrated version

import os
from pathlib import Path
from typing import List, Optional

from pydantic import ConfigDict, Field, field_validator
from rv_android_core.commands.command import Command
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import LogcatValidationError
from rv_android_core.util.logging.constants import (
    CONTEXT_COMPONENT,
    LOG_COMPLETE,
    LOG_ERROR,
)
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.validation import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model

# Single source of truth for the opt-in diagnostic capture tags (gh72).
# Each tag carries its own priority suffix (`:E`/`:W`) so the command builder keeps
# it verbatim instead of appending `:V`. Consumed by the platform LogcatComponent,
# which appends these to the baseline tags only when RV_LOGCAT_DIAGNOSTICS is set.
DIAGNOSTIC_TAGS = ["AndroidRuntime:E", "art:E", "dalvikvm:E", "ActivityManager:W"]


@validated_model([])
class LogcatManager(BaseValidatedModel):
    """
    Manages logcat operations for Android devices with validated configuration.

    ### Architectural Decisions:
    - Inherits from BaseValidatedModel for comprehensive validation and type safety
    - Separates logcat concerns from task execution logic with validated parameters
    - Improves resource management with proper cleanup and file handle validation
    - Provides structured access to logcat data with validated file paths and tags

    ### Role in the System:
    - Captures logcat output during test execution with validated configuration
    - Provides filtering for relevant log entries with validated tag formats
    - Manages logcat process lifecycle with proper resource cleanup
    - Ensures secure file operations through path validation

    ### Validation Features:
    - Output file path validation to ensure proper directory structure
    - Tag format validation for Android logcat filtering
    - Process state management with validated lifecycle operations
    - Resource cleanup validation to prevent memory leaks

    ### Integration Points:
    - Uses validated Command class for all ADB operations
    - Integrates with LoggingManager for comprehensive error tracking
    - Supports validated configuration for different testing scenarios
    - Provides validated interfaces for logcat data extraction
    """

    model_config = ConfigDict(
        # Allow process and file handle objects as arbitrary types
        arbitrary_types_allowed=True,
        # Validate assignments for runtime safety
        validate_assignment=True,
        # Allow extra attributes for runtime state
        extra="allow",
    )

    # Configuration fields
    default_tags: List[str] = Field(
        default_factory=lambda: ["RVSEC", "RVSEC-COV"],
        description="Default logcat tags to filter when none provided",
    )

    clear_buffer_on_start: bool = Field(
        default=True,
        description="Whether to clear logcat buffer before starting capture",
    )

    logcat_format: str = Field(
        default="threadtime", description="Logcat output format specification"
    )

    device_serial: str = Field(
        default="emulator-5554", description="Android device serial for logcat capture"
    )

    @field_validator("default_tags")
    @classmethod
    def validate_tags(cls, v):
        """Validate that all tags are non-empty strings using system exceptions."""
        if not v:
            raise LogcatValidationError(
                "At least one default tag must be specified", field_name="default_tags"
            )

        for i, tag in enumerate(v):
            if not isinstance(tag, str) or not tag.strip():
                raise LogcatValidationError(
                    f"Tag at position {i} must be a non-empty string",
                    field_name="default_tags",
                )

        return v

    @field_validator("logcat_format")
    @classmethod
    def validate_logcat_format(cls, v):
        """Validate logcat format specification using system exceptions."""
        valid_formats = {"brief", "process", "tag", "raw", "time", "threadtime", "long"}
        if v not in valid_formats:
            raise LogcatValidationError(
                f"Logcat format must be one of: {valid_formats}",
                field_name="logcat_format",
            )
        return v

    def model_post_init(self, __context):
        """Initialize logging, error handling and runtime state after model validation."""
        # Use object.__setattr__ to bypass Pydantic validation for logger
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            "util.logcat_manager", {CONTEXT_COMPONENT: "LogcatManager"}
        )
        object.__setattr__(self, "logger", logger)

        # Initialize error handler for integrated error management
        error_handler = ErrorHandler.get_instance()
        object.__setattr__(self, "error_handler", error_handler)

        # Initialize runtime state
        object.__setattr__(self, "logcat_process", None)
        object.__setattr__(self, "logcat_file_handle", None)

    def start_capture(
        self,
        output_file: str,
        tags: Optional[List[str]] = None,
        clear_buffer: Optional[bool] = None,
    ) -> bool:
        """
        Start capturing logcat output to a file with validated parameters.

        Args:
            output_file: Path to write logcat output (validated for proper format)
            tags: Optional list of tags to filter (validated for format)
            clear_buffer: Whether to clear logcat buffer first (defaults to instance setting)

        Returns:
            True if capture started successfully, False otherwise
        """
        # Use instance defaults if not provided
        if tags is None:
            tags = self.default_tags
        if clear_buffer is None:
            clear_buffer = self.clear_buffer_on_start

        # Validate parameters
        validated_output_file = self._validate_output_file_path(output_file)
        validated_tags = self._validate_tag_list(tags)

        with self.logger.with_context(
            output_file=validated_output_file,
            tags=validated_tags,
            clear_buffer=clear_buffer,
            phase="start_capture",
        ):
            try:
                # Create output directory if needed
                output_dir = os.path.dirname(validated_output_file)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)

                # Clear logcat buffer if requested
                if clear_buffer:
                    clear_cmd = Command(
                        "adb", ["-s", self.device_serial, "logcat", "-c"]
                    )
                    clear_cmd.invoke()
                    self.logger.debug(
                        f"Cleared logcat buffer for device {self.device_serial}"
                    )

                # Build command with device serial and tag filters
                cmd_args = [
                    "-s",
                    self.device_serial,
                    "logcat",
                    "-v",
                    self.logcat_format,
                ]
                if validated_tags:
                    cmd_args.extend(["-s"])  # Tag filter option
                    # Each bare tag needs a priority suffix (V=Verbose) for proper
                    # filtering; without it the logcat filter does not work correctly.
                    # A tag that already carries a priority (e.g. "AndroidRuntime:E"
                    # from DIAGNOSTIC_TAGS) is kept verbatim — appending ":V" would
                    # produce an invalid "AndroidRuntime:E:V" spec. Baseline tags
                    # ("RVSEC"/"RVSEC-COV") have no colon, so they still become
                    # "RVSEC:V"/"RVSEC-COV:V", keeping the flag-off command byte-identical.
                    cmd_args.extend(
                        [tag if ":" in tag else f"{tag}:V" for tag in validated_tags]
                    )

                # Start logcat capture
                logcat_cmd = Command("adb", cmd_args)
                log_file = open(validated_output_file, "wb")

                try:
                    # CHANGED: Using invoke_as_process instead of invoke_as_deamon to prevent process duplication
                    # The invoke_as_deamon method was causing fork-based process duplication in parallel execution.
                    # Original line (causes duplication): logcat_process = logcat_cmd.invoke_as_deamon(stdout=log_file)
                    logcat_process = logcat_cmd.invoke_as_process(stdout=log_file)
                    object.__setattr__(self, "logcat_process", logcat_process)
                    object.__setattr__(self, "logcat_file_handle", log_file)

                    self.logger.info(
                        LOG_COMPLETE.format(
                            phase=f"logcat capture to {validated_output_file}"
                        )
                    )
                    return True

                except Exception as e:
                    # Close file handle if command fails
                    log_file.close()
                    self.logger.error(
                        LOG_ERROR.format(phase="starting logcat capture", error=str(e))
                    )
                    return False

            except Exception as e:
                self.logger.error(
                    LOG_ERROR.format(phase="setting up logcat capture", error=str(e))
                )
                return False

    def stop_capture(self) -> bool:
        """
        Stop logcat capture and clean up resources with validation.

        Returns:
            True if cleanup succeeded, False otherwise
        """
        with self.logger.with_context(phase="stop_capture"):
            success = True

            # Kill logcat process
            if hasattr(self, "logcat_process") and self.logcat_process:
                try:
                    self.logger.debug("Stopping logcat process")
                    self.logcat_process.kill()
                    object.__setattr__(self, "logcat_process", None)
                except Exception as e:
                    self.logger.warning(
                        LOG_ERROR.format(phase="stopping logcat process", error=str(e))
                    )
                    success = False

            # Close logcat file handle
            if hasattr(self, "logcat_file_handle") and self.logcat_file_handle:
                try:
                    self.logger.debug("Closing logcat file")
                    self.logcat_file_handle.close()
                    object.__setattr__(self, "logcat_file_handle", None)
                except Exception as e:
                    self.logger.warning(
                        LOG_ERROR.format(phase="closing logcat file", error=str(e))
                    )
                    success = False

            if success:
                self.logger.info(LOG_COMPLETE.format(phase="logcat capture shutdown"))

            return success

    def is_capturing(self) -> bool:
        """
        Check if logcat capture is currently active.

        Returns:
            True if capture is active, False otherwise
        """
        return (
            hasattr(self, "logcat_process")
            and self.logcat_process is not None
            and hasattr(self, "logcat_file_handle")
            and self.logcat_file_handle is not None
        )

    def _validate_output_file_path(self, output_file: str) -> str:
        """
        Validate output file path format and accessibility using system exceptions.

        Args:
            output_file: File path to validate

        Returns:
            Validated file path

        Raises:
            LogcatValidationError: If path is invalid or inaccessible
        """
        try:
            if not output_file or not isinstance(output_file, str):
                raise LogcatValidationError(
                    "Output file path must be a non-empty string",
                    field_name="output_file",
                )

            # Convert to Path for validation
            path = Path(output_file)

            # Basic path validation - ensure it's not a directory if it exists
            if path.exists() and path.is_dir():
                raise LogcatValidationError(
                    f"Output path {output_file} is a directory, not a file",
                    field_name="output_file",
                )

            # Return absolute path for consistency
            return str(path.resolve())

        except LogcatValidationError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Handle any other errors with error handler
            context = {
                "output_file": output_file,
                "validation_method": "_validate_output_file_path",
            }
            self.error_handler.handle_error(e, context)
            raise LogcatValidationError(
                f"Failed to validate output file path: {str(e)}",
                field_name="output_file",
                cause=e,
            )

    def _validate_tag_list(self, tags: List[str]) -> List[str]:
        """
        Validate logcat tag list format using system exceptions.

        Args:
            tags: List of logcat tags to validate

        Returns:
            Validated tag list

        Raises:
            LogcatValidationError: If any tag is invalid
        """
        try:
            if not tags:
                return []

            validated_tags = []
            for i, tag in enumerate(tags):
                if not isinstance(tag, str):
                    raise LogcatValidationError(
                        f"Tag at position {i} must be string, got {type(tag)}",
                        field_name="tags",
                    )

                tag = tag.strip()
                if not tag:
                    raise LogcatValidationError(
                        f"Tag at position {i} cannot be empty or whitespace-only",
                        field_name="tags",
                    )

                # Basic Android logcat tag validation
                if len(tag) > 23:  # Android logcat tag limit
                    raise LogcatValidationError(
                        f"Tag '{tag}' exceeds 23 character limit", field_name="tags"
                    )

                validated_tags.append(tag)

            return validated_tags

        except LogcatValidationError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Handle any other errors with error handler
            context = {"tags": tags, "validation_method": "_validate_tag_list"}
            self.error_handler.handle_error(e, context)
            raise LogcatValidationError(
                f"Failed to validate tag list: {str(e)}", field_name="tags", cause=e
            )
