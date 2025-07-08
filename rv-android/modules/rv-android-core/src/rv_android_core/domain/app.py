"""
Android application metadata management and validation.

This module provides structured data models for Android application information
extracted through static analysis using Androguard.
"""

import os
from typing import List, Optional
from pydantic import Field, field_validator, computed_field

from androguard.core.bytecodes.apk import APK
from rv_android_core.util.validation import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model
from rv_android_core.util.error.exceptions import ConfigurationError


@validated_model(['app_path'])
class App(BaseValidatedModel):
    """
    Validated data model representing an Android application with comprehensive metadata.
    
    This model extracts and validates Android application metadata including package
    information, permissions, SDK versions, and other properties relevant for
    monitoring operations and experiment execution.

    ### Architectural Decisions:
    - Uses Androguard for reliable APK metadata extraction without execution
    - Provides comprehensive validation of APK file accessibility and structure
    - Maintains structured representation for consistent data access patterns
    - Supports automated decision-making for instrumentation and testing workflows

    ### Role in the System:
    - Serves as the primary interface for Android application representation
    - Enables structured access to application metadata across experiment components
    - Facilitates automated analysis and monitoring operation configuration
    - Provides foundation for instrumentation and runtime verification workflows

    ### Integration Points:
    - Used by static analysis tools for application structure understanding
    - Consumed by instrumentation systems for APK modification workflows
    - Integrated with experiment orchestration for application-specific configuration
    - Supports monitoring operation setup and execution planning
    """

    app_path: str = Field(
        description="Absolute path to the APK file for analysis and instrumentation"
    )
    validate_on_init: bool = Field(
        default=True,
        description="Whether to validate APK file accessibility and structure on initialization"
    )

    # Computed fields based on APK analysis
    _apk_instance: Optional[APK] = None

    def model_post_init(self, __context) -> None:
        """
        Execute APK analysis and validation after model initialization.
        
        This method loads the APK file using Androguard and validates its structure
        and accessibility for downstream processing components.
        """
        if self.validate_on_init:
            self._load_and_validate_apk()

    def _load_and_validate_apk(self) -> None:
        """
        Load APK file and validate its structure using Androguard.
        
        Raises:
            ConfigurationError: If APK file is not accessible or has invalid structure
        """
        if not os.path.isfile(self.app_path):
            raise ConfigurationError(f"APK file not found: {self.app_path}")
        
        if not self.app_path.lower().endswith('.apk'):
            raise ConfigurationError(f"File is not an APK: {self.app_path}")
        
        try:
            self._apk_instance = APK(self.app_path)
            # Validate that essential metadata can be extracted
            if not self._apk_instance.get_package():
                raise ConfigurationError(f"APK has no package name: {self.app_path}")
        except Exception as e:
            raise ConfigurationError(f"Invalid APK file {self.app_path}: {str(e)}")

    @computed_field
    @property
    def path(self) -> str:
        """Absolute path to the APK file."""
        return os.path.abspath(self.app_path)

    @computed_field
    @property
    def name(self) -> str:
        """Application filename (basename of APK file)."""
        return os.path.basename(self.app_path)

    @computed_field
    @property
    def package_name(self) -> str:
        """Android package name extracted from APK manifest."""
        if self._apk_instance is None:
            self._load_and_validate_apk()
        return self._apk_instance.get_package()

    @computed_field
    @property
    def sdk_target(self) -> int:
        """Target SDK version extracted from APK manifest."""
        if self._apk_instance is None:
            self._load_and_validate_apk()
        return self._apk_instance.get_effective_target_sdk_version()

    @computed_field
    @property
    def permissions(self) -> List[str]:
        """List of permissions requested by the application."""
        if self._apk_instance is None:
            self._load_and_validate_apk()
        return self._apk_instance.get_permissions()

    @computed_field
    @property
    def min_api(self) -> int:
        """Minimum API level required by the application."""
        if self._apk_instance is None:
            self._load_and_validate_apk()
        return self._apk_instance.get_min_sdk_version()

    @field_validator('app_path')
    @classmethod
    def validate_app_path(cls, v: str) -> str:
        """Validate that app_path is not empty."""
        if not v or not v.strip():
            raise ValueError("Application path cannot be empty")
        return v.strip()
