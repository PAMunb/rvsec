"""
Android application metadata management and validation.

This module provides structured data models for Android application information
extracted through static analysis using Androguard.
"""

import logging
import os
from typing import List, Optional

from androguard.core.bytecodes.apk import APK
from pydantic import Field, computed_field, field_validator
from rv_android_core.util.android.build_type_suffix import (
    neutralize_build_type_suffix,
)
from rv_android_core.util.android.package_detector import (
    PackageDetectionResult,
    PackageDetector,
)
from rv_android_core.util.error.exceptions import ConfigurationError
from rv_android_core.util.validation import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model

logger = logging.getLogger(__name__)


@validated_model(["app_path"])
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
    - Separates the two package questions: `package_name` answers what the APK
      calls itself to the device, `code_package` answers which package scopes the
      classes a study treats as the app's own. The second is a property of the
      corpus rather than of the APK, so it is an input — `package_detector`,
      resolved at the entry point the user invoked — and never an inference made
      here. This model reads no environment variable (INV-CORE-55)

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
    package_detector: bool = Field(
        default=False,
        description="Elect the implementation package heuristically instead of "
        "reporting the one declared in the manifest. User input, resolved at the "
        "entry point the user invoked and passed in already decided — this model "
        "reads no environment variable (INV-CORE-55)",
    )
    strip_build_type_suffix: bool = Field(
        default=False,
        description="Neutralize the build-type suffix of the declared applicationId "
        "before using it as the scope key (INV-CORE-58). Like `package_detector`, it "
        "is a property of the corpus under study and therefore user input, resolved "
        "at the entry point and passed in already decided — this model reads no "
        "environment variable (INV-CORE-55). Off by default: it changes which classes "
        "a study counts, so no run acquires it by accident",
    )
    validate_on_init: bool = Field(
        default=True,
        description="Whether to validate APK file accessibility and structure on initialization",
    )

    # Computed fields based on APK analysis
    _apk_instance: Optional[APK] = None
    _code_package_result: Optional[PackageDetectionResult] = None

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

        if not self.app_path.lower().endswith(".apk"):
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
        """Android package name extracted from APK manifest.
        Use for device operations (install, launch, force-stop)."""
        if self._apk_instance is None:
            self._load_and_validate_apk()
        return self._apk_instance.get_package()

    @computed_field
    @property
    def code_package(self) -> str:
        """Package that scopes the classes this study treats as the app's own.

        Use for static analysis parsing and class filtering. For device
        operations (install, launch): use package_name.

        The declared applicationId is the answer unless a policy asks for
        something else, because which package scopes app-owned classes depends on
        the corpus under study and not on the APK. Two policies exist, both off by
        default and both decided at the entry point (INV-CORE-18):

        - `strip_build_type_suffix` neutralizes the Gradle build-type suffix, so
          the debug variant of `com.example.app` is scoped by the package its
          classes were actually compiled under rather than by `…app.debug`, under
          which nothing was compiled at all.
        - `package_detector` elects the implementation package heuristically.

        Prefix repair is neither, and stays out: no string rule resolves it (forty
        of the 219 broad-corpus APKs), and the backstop for those is the
        denominator gate. The election is lazy and runs only when enabled, so the
        default path never enumerates components.
        """
        if not self.package_detector:
            if self.strip_build_type_suffix:
                return neutralize_build_type_suffix(self.package_name)
            return self.package_name
        if self._code_package_result is None:
            self._detect_code_package()
        return self._code_package_result.code_package

    @computed_field
    @property
    def code_package_source(self) -> str:
        """Which mechanism produced `code_package`.

        One of "manifest", "manifest-neutralized" or "detector". It reports
        "manifest" when the neutralization policy was on but removed nothing —
        the value names what actually produced the key, not what was requested,
        because a reader asking why a key looks the way it does is asking about
        the former.

        The choice does not survive in the data it shapes unless it is carried
        there deliberately — the GATOR analysis JSON records the manifest package
        regardless of the key that filtered its contents — so this value crosses
        into the artefact as its own member (INV-ANA-58, INV-ANA-66).
        """
        if self.package_detector:
            return "detector"
        if self.strip_build_type_suffix and self.code_package != self.package_name:
            return "manifest-neutralized"
        return "manifest"

    def _detect_code_package(self) -> None:
        """Run PackageDetector on the loaded APK instance."""
        if self._apk_instance is None:
            self._load_and_validate_apk()
        detector = PackageDetector()
        self._code_package_result = detector.detect_package(self._apk_instance)

        # Log only when there is a mismatch (the interesting case)
        if (
            self._code_package_result.code_package
            != self._code_package_result.manifest_package
        ):
            logger.info(
                "Package mismatch detected: manifest='%s', code='%s' "
                "(method=%s, confidence=%s)",
                self._code_package_result.manifest_package,
                self._code_package_result.code_package,
                self._code_package_result.detection_method,
                self._code_package_result.confidence,
            )

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

    @field_validator("app_path")
    @classmethod
    def validate_app_path(cls, v: str) -> str:
        """Validate that app_path is not empty."""
        if not v or not v.strip():
            raise ValueError("Application path cannot be empty")
        return v.strip()
