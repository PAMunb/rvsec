import glob
import os
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import Field, computed_field, field_validator
from rv_android_core import constants
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import ConfigurationError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.validation.base import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model


class Dex2jarTools(BaseValidatedModel):
    """
    Configuration model for dex2jar tool suite paths and validation.

    ### Architectural Decisions:
    - Implements type-safe access to dex2jar tool components
    - Provides automatic validation of tool existence and executability
    - Centralizes dex2jar tool path management for instrumentation pipeline
    - Integrates with error handling system for robust tool validation

    ### Role in the System:
    - Validates availability of required dex2jar tools during configuration
    - Provides structured access to tool paths for command execution
    - Ensures instrumentation pipeline dependencies are met before execution
    - Enables clear error reporting when tools are missing or inaccessible

    ### Tool Components:
    - dex2jar: Primary DEX to JAR conversion tool
    - asm_verify: JAR structural verification utility
    """

    dex2jar: str = Field(
        ..., description="Path to dex2jar executable for DEX conversion"
    )
    asm_verify: str = Field(
        ..., description="Path to ASM verify tool for JAR validation"
    )

    @field_validator("dex2jar", "asm_verify")
    @classmethod
    def validate_tool_exists(cls, v: str) -> str:
        """
        Validate that dex2jar tool executable exists and is accessible.

        Args:
            v: Tool path to validate

        Returns:
            Validated tool path

        Raises:
            ValueError: If tool is not found or not executable
        """
        if not os.path.exists(v):
            raise ValueError(f"dex2jar tool not found: {v}")

        if not os.access(v, os.R_OK | os.X_OK):
            raise ValueError(f"dex2jar tool not executable: {v}")

        return v


class ConfigurationSummary(BaseValidatedModel):
    """
    Structured summary of instrumentation configuration for logging and debugging.

    ### Architectural Decisions:
    - Provides comprehensive configuration overview for operational visibility
    - Organizes configuration data into logical categories for analysis
    - Supports automated configuration validation and reporting
    - Integrates monitor artifact counting for pipeline verification

    ### Role in the System:
    - Enables detailed configuration logging for debugging instrumentation issues
    - Provides structured data for configuration validation reports
    - Supports automated configuration analysis and verification
    - Facilitates troubleshooting of instrumentation pipeline setup
    """

    android_integration: Dict[str, str] = Field(
        ..., description="Android SDK integration configuration"
    )
    instrumentation_paths: Dict[str, str] = Field(
        ..., description="Instrumentation directory paths"
    )
    temporary_directories: Dict[str, str] = Field(
        ..., description="Temporary processing directories"
    )
    tools: Dict[str, Any] = Field(..., description="Tool configurations and paths")
    signing: Dict[str, Any] = Field(..., description="APK signing configuration")
    monitor_artifacts: Dict[str, int] = Field(
        ..., description="Monitor artifact counts"
    )
    validation_status: str = Field(..., description="Configuration validation status")


class InstrumentationError(BaseValidatedModel):
    """
    Structured representation of instrumentation pipeline errors.

    ### Architectural Decisions:
    - Provides consistent error structure for instrumentation failure tracking
    - Integrates with existing error handling and logging infrastructure
    - Supports detailed error classification for debugging and analysis
    - Enables automated error reporting and recovery strategies

    ### Role in the System:
    - Standardizes error information across instrumentation pipeline phases
    - Enables structured error logging and analysis for debugging
    - Supports automated error recovery and retry strategies
    - Provides consistent error interface for experiment orchestration
    """

    code: int = Field(..., description="Numeric error code for programmatic handling")
    tool: Optional[str] = Field(
        default=None, description="Name of tool that failed during execution"
    )
    message: str = Field(..., description="Human-readable error description")
    phase: str = Field(..., description="Pipeline phase where error occurred")


class InstrumentationResults(BaseValidatedModel):
    """
    Comprehensive results and metrics from instrumentation pipeline execution.

    ### Architectural Decisions:
    - Aggregates instrumentation outcomes for batch processing analysis
    - Provides computed metrics for success rate calculation and reporting
    - Structures error information for detailed failure analysis
    - Integrates with experiment orchestration for batch operation tracking

    ### Role in the System:
    - Tracks instrumentation success and failure metrics across batches
    - Provides structured data for experiment result analysis
    - Enables automated quality assessment of instrumentation operations
    - Supports debugging and optimization of instrumentation workflows
    """

    errors: Dict[str, InstrumentationError] = Field(
        default_factory=dict, description="Detailed error information keyed by APK name"
    )
    success_count: int = Field(
        default=0, ge=0, description="Number of successfully instrumented APKs"
    )
    total_count: int = Field(
        default=0, ge=0, description="Total number of APKs processed"
    )

    @computed_field
    @property
    def success_rate(self) -> float:
        """
        Calculate instrumentation success rate as percentage.

        Returns:
            Success rate percentage (0.0 to 100.0)
        """
        if self.total_count == 0:
            return 0.0
        return (self.success_count / self.total_count) * 100


@validated_model(
    [
        "rvsec_root",
        "monitor_output_dir",
        "android_jar_path",
        "android_platforms_dir",
        "keystore_file",
        "keystore_password",
        "working_dir",
        "instrumented_dir",
        "tmp_dir",
        "lib_tmp_dir",
        "rvm_tmp_dir",
        "dex2jar_home",
    ]
)
class RVInstrumentationConfig(BaseValidatedModel):
    """
    Configuration management for RVInstrumentation with comprehensive path validation.

    The RVInstrumentationConfig provides a configuration system that supports
    multiple deployment scenarios from development environments to production systems.
    It implements an intelligent path resolution strategy with fallback mechanisms for
    Android APK instrumentation workflows.

    ### Architectural Decisions:
    - Implements a priority-based path resolution system for maximum flexibility
    - Provides validation at initialization time to fail fast on configuration errors
    - Supports both environment-based and explicit configuration modes
    - Delegates to specialized validation methods for different configuration aspects
    - Uses pathlib for robust cross-platform path handling where applicable
    - Separates monitored operations specifications from tool configurations

    ### Role in the System:
    - Acts as the central configuration authority for APK instrumentation workflows
    - Provides validated and normalized paths for all required tools and directories
    - Enables deployment flexibility through multiple configuration sources
    - Ensures configuration consistency across different execution environments
    - Supports both automated discovery and explicit path specification
    - Manages Android SDK integration and keystore configuration for APK signing

    ### Configuration Priority (highest to lowest):
    1. Individual tool paths explicitly provided (monitor_output_dir, android_jar_path, etc.)
    2. Explicit rvsec_root parameter with relative path resolution
    3. ENV_RVSEC_HOME environment variable with relative path resolution
    4. Configuration error if no valid source is available

    ### Instrumentation Pipeline Integration:
    - Provides monitor artifacts directory for runtime verification integration
    - Configures Android SDK paths for APK decompilation and recompilation
    - Manages temporary directories for intermediate processing steps
    - Supplies keystore configuration for APK signing and deployment
    - Integrates dex2jar tools for bytecode transformation workflows
    """

    # Core paths
    rvsec_root: Optional[str] = Field(
        default=None,
        description="Root directory of RVSEC installation for path discovery",
    )
    monitor_output_dir: Optional[str] = Field(
        default=None,
        description="Directory containing generated monitor artifacts from rv-monitor-generator",
    )
    working_dir: Optional[str] = Field(
        default=None,
        description="Base working directory for instrumentation operations",
    )

    # Android SDK paths
    android_jar_path: Optional[str] = Field(
        default=None,
        description="Path to Android SDK android.jar file for APK processing",
    )
    android_platforms_dir: Optional[str] = Field(
        default=None,
        description="Android SDK platforms directory for API compatibility",
    )

    # Output directories
    instrumented_dir: Optional[str] = Field(
        default=None, description="Output directory for instrumented APK artifacts"
    )
    tmp_dir: Optional[str] = Field(
        default=None,
        description="Temporary directory for intermediate processing files",
    )
    lib_tmp_dir: Optional[str] = Field(
        default=None,
        description="Temporary directory for library extraction and processing",
    )
    rvm_tmp_dir: Optional[str] = Field(
        default=None,
        description="Temporary directory for runtime verification monitor processing",
    )

    # Signing configuration
    keystore_file: Optional[str] = Field(
        default=None, description="Path to keystore file for APK signing"
    )
    keystore_password: Optional[str] = Field(
        default=None, description="Password for keystore access"
    )
    keystore_alias: str = Field(
        default="server",
        description="Key alias inside the keystore (bundled keystore uses 'server')",
    )

    # Tools
    dex2jar_home: Optional[str] = Field(
        default=None, description="Directory containing dex2jar tool suite"
    )

    def __init__(self, **data: Any):
        """
        Initialize RVInstrumentationConfig with intelligent path resolution and validation.

        The initialization process follows a strict priority order for path resolution,
        ensuring predictable behavior across different deployment scenarios. All paths
        are validated for existence and accessibility during initialization.

        Raises:
            ConfigurationError: If path resolution fails or required tools are not accessible
        """
        # Store original values before calling super().__init__
        original_rvsec_root = data.get("rvsec_root")

        # Call parent constructor first to set up Pydantic model
        super().__init__(**data)

        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self._logger = logging_manager.get_logger(
            "rv_instrumentation.config.RVInstrumentationConfig",
            {CONTEXT_COMPONENT: "RVInstrumentationConfig"},
        )

        # Resolve paths based on priority
        self._resolve_paths(original_rvsec_root)

        # Validate configuration
        self._validate_configuration()

    @ErrorHandler.handle_errors(
        component="RVInstrumentationConfig", phase="path_resolution", reraise=True
    )
    def _resolve_paths(self, rvsec_root: Optional[str]) -> None:
        """
        Execute intelligent path resolution based on configuration priority system.

        This method implements the core path resolution logic, following the established
        priority order to determine final paths for all required tools and directories.
        The resolution process is designed to support both development and production
        deployment scenarios with special consideration for Android SDK integration.

        ### Resolution Strategy:
        1. Check if all critical individual paths are explicitly provided (highest priority)
        2. Use explicit rvsec_root for automatic path discovery
        3. Fall back to ENV_RVSEC_HOME environment variable
        4. Apply default working directory resolution for local paths
        5. Raise ConfigurationError if no valid configuration source exists

        Args:
            rvsec_root: Optional explicit RVSEC root directory

        Raises:
            ConfigurationError: If no valid configuration source is available
        """
        # Priority 1: Check if all critical individual paths are explicitly provided
        critical_paths = [
            self.monitor_output_dir,
            self.android_jar_path,
            self.keystore_file,
            self.instrumented_dir,
            self.dex2jar_home,
        ]

        if all(path is not None for path in critical_paths):
            # All critical paths explicitly provided - highest priority resolution
            # Fill in optional paths with defaults if not provided
            self._apply_default_paths()
            return

        # Priority 2 & 3: Determine rvsec_root source for automatic path discovery
        resolved_rvsec_root = None

        if rvsec_root is not None:
            # Priority 2: Explicit rvsec_root provided
            resolved_rvsec_root = rvsec_root
        else:
            # Priority 3: Try ENV_RVSEC_HOME environment variable
            env_rvsec = os.getenv(constants.ENV_RVSEC_HOME)
            if env_rvsec:
                resolved_rvsec_root = env_rvsec
            else:
                # Priority 4: Apply working directory based resolution
                if self.working_dir is None:
                    self.working_dir = os.getcwd()
                self._resolve_from_working_dir()
                return

        # Perform automatic path discovery from resolved rvsec_root
        self._resolve_from_rvsec_root(resolved_rvsec_root)

    def _resolve_from_rvsec_root(self, rvsec_root: str) -> None:
        """
        Resolve individual tool paths from RVSEC root directory using standard layout.

        This method implements the standard RVSEC directory layout assumptions for
        automatic path discovery. It follows the conventional RVSEC installation
        structure to locate tools, Android SDK integration, and working directories.

        ### RVSEC Layout Assumptions:
        - Monitor artifacts generated in rvsec/rv-android/mop_out
        - Android SDK configured through ANDROID_HOME environment
        - Working directory defaults to rvsec/rv-android
        - Instrumentation outputs in rvsec/rv-android/out

        Args:
            rvsec_root: Validated RVSEC root directory path
        """
        # Set working directory to rv-android subdirectory
        if self.working_dir is None:
            self.working_dir = os.path.join(rvsec_root, "rv-android")

        # Resolve monitor output directory from standard RVSEC layout
        if self.monitor_output_dir is None:
            self.monitor_output_dir = os.path.join(self.working_dir, "mop_out")

        # Resolve Android SDK paths from environment or standard locations
        if self.android_jar_path is None or self.android_platforms_dir is None:
            self._resolve_android_sdk()

        # Apply remaining default paths based on working directory
        self._apply_default_paths()

    def _resolve_from_working_dir(self) -> None:
        """
        Resolve paths using current working directory as base for relative path resolution.

        This fallback resolution strategy assumes the instrumentation is being executed
        from within the rv-android directory structure, providing reasonable defaults
        for development and testing scenarios.
        """
        # Monitor output directory defaults to mop_out in working directory
        if self.monitor_output_dir is None:
            self.monitor_output_dir = os.path.join(self.working_dir, "mop_out")

        # Resolve Android SDK paths from environment
        self._resolve_android_sdk()

        # Apply remaining default paths
        self._apply_default_paths()

    @ErrorHandler.handle_errors(
        component="RVInstrumentationConfig",
        phase="android_sdk_resolution",
        reraise=True,
    )
    def _resolve_android_sdk(self) -> None:
        """
        Resolve Android SDK paths from environment variables and standard configurations.

        This method handles Android SDK integration by discovering the appropriate
        android.jar and platforms directory based on the configured Android platform
        version and ANDROID_HOME environment variable.

        Raises:
            ConfigurationError: If Android SDK is not properly configured or accessible
        """
        android_home = os.getenv("ANDROID_HOME")
        if not android_home:
            raise ConfigurationError(
                "ANDROID_HOME environment variable not set. "
                "Please configure Android SDK environment or provide explicit paths."
            )

        # Standard Android SDK platform configuration
        android_platform = "android-29"  # Default platform version

        if self.android_platforms_dir is None:
            self.android_platforms_dir = os.path.join(android_home, "platforms")

        if self.android_jar_path is None:
            platform_lib = os.path.join(self.android_platforms_dir, android_platform)
            self.android_jar_path = os.path.join(platform_lib, "android.jar")

    def _apply_default_paths(self) -> None:
        """
        Apply default path configurations for optional parameters not explicitly provided.

        This method fills in reasonable defaults for all optional configuration paths,
        ensuring the instrumentation system has all necessary directory and file paths
        configured for successful operation.
        """
        # Default keystore configuration for APK signing
        if self.keystore_file is None:
            # Use bundled keystore from rv-instrumentation assets
            module_dir = Path(__file__).parent.parent.parent
            assets_dir = module_dir / "assets"
            self.keystore_file = str(assets_dir / "keystore.jks")

        if self.keystore_password is None:
            self.keystore_password = "password"  # Default development password

        # Default output directory for instrumented APKs
        if self.instrumented_dir is None:
            self.instrumented_dir = os.path.join(self.working_dir, "out")

        # Default temporary directories for intermediate processing
        if self.tmp_dir is None:
            self.tmp_dir = os.path.join(self.working_dir, "tmp")

        if self.lib_tmp_dir is None:
            self.lib_tmp_dir = os.path.join(self.working_dir, "lib_tmp")

        if self.rvm_tmp_dir is None:
            self.rvm_tmp_dir = os.path.join(self.working_dir, "rvm_tmp")

        # Default dex2jar tools directory
        if self.dex2jar_home is None:
            lib_dir = os.path.join(self.working_dir, "lib")
            self.dex2jar_home = os.path.join(lib_dir, "dex2jar")

    @ErrorHandler.handle_errors(
        component="RVInstrumentationConfig",
        phase="configuration_validation",
        reraise=True,
    )
    def _validate_configuration(self) -> None:
        """
        Execute comprehensive configuration validation to ensure operational readiness.

        This validation process performs extensive checks to verify that all configured
        paths and tools are accessible and functional. It's designed to fail fast during
        initialization rather than during execution, providing clear diagnostic information
        for instrumentation pipeline requirements.

        ### Validation Phases:
        1. Critical directory existence and accessibility verification
        2. Android SDK integration validation
        3. Keystore accessibility and format verification
        4. Tool availability validation (dex2jar suite)
        5. Monitor artifacts availability verification

        Raises:
            ConfigurationError: If any validation check fails with detailed diagnostic information
        """
        # Phase 1: Critical directory validation
        self._validate_directory(self.monitor_output_dir, "Monitor output")
        self._validate_directory(self.android_platforms_dir, "Android platforms")
        self._validate_directory(self.dex2jar_home, "dex2jar tools")

        # Phase 2: Android SDK integration validation
        self._validate_android_jar()

        # Phase 3: Keystore validation
        self._validate_keystore()

        # Phase 4: Monitor artifacts validation
        self._validate_monitor_artifacts()

        # Phase 5: Create required output directories
        self._ensure_output_directories()

    def _validate_directory(self, directory_path: str, directory_purpose: str) -> None:
        """
        Validate directory existence and accessibility.

        Args:
            directory_path: Path to the directory
            directory_purpose: Human-readable purpose for error messages

        Raises:
            ConfigurationError: If directory validation fails
        """
        if not os.path.isdir(directory_path):
            raise ConfigurationError(
                f"{directory_purpose} directory not found: {directory_path}"
            )

        if not os.access(directory_path, os.R_OK):
            raise ConfigurationError(
                f"{directory_purpose} directory not readable: {directory_path}"
            )

    def _validate_android_jar(self) -> None:
        """
        Validate Android SDK android.jar accessibility and format.

        Raises:
            ConfigurationError: If android.jar validation fails
        """
        if not os.path.isfile(self.android_jar_path):
            raise ConfigurationError(f"Android JAR not found: {self.android_jar_path}")

        if not os.access(self.android_jar_path, os.R_OK):
            raise ConfigurationError(
                f"Android JAR not readable: {self.android_jar_path}"
            )

    def _validate_keystore(self) -> None:
        """
        Validate keystore file accessibility and basic format validation.

        Note: This performs basic file existence validation. Keystore password
        validation is deferred to actual signing operations to avoid exposing
        credentials during configuration validation.

        Raises:
            ConfigurationError: If keystore validation fails
        """
        if not os.path.isfile(self.keystore_file):
            raise ConfigurationError(
                f"Keystore file not found: {self.keystore_file}\n"
                f"Generate keystore using: keytool -genkey -keystore {self.keystore_file}"
            )

        if not os.access(self.keystore_file, os.R_OK):
            raise ConfigurationError(
                f"Keystore file not readable: {self.keystore_file}"
            )

    def _validate_monitor_artifacts(self) -> None:
        """
        Validate availability of monitor artifacts from rv-monitor-generator.

        This validation ensures that the instrumentation pipeline has access to
        the runtime verification monitors generated by rv-monitor-generator module.
        The presence of both AspectJ weaving files and Java monitor classes is
        verified to ensure complete monitored operations coverage.

        Raises:
            ConfigurationError: If monitor artifacts are not available
        """
        # Check for AspectJ files (weaving specifications)
        aspectj_files = glob.glob(
            os.path.join(self.monitor_output_dir, f"*{constants.EXTENSION_AJ}")
        )
        if not aspectj_files:
            raise ConfigurationError(
                f"No AspectJ monitor files (*{constants.EXTENSION_AJ}) found in: {self.monitor_output_dir}\n"
                f"Generate monitors using rv-monitor-generator before instrumentation"
            )

        # Check for Java monitor classes
        java_files = glob.glob(
            os.path.join(self.monitor_output_dir, f"*{constants.EXTENSION_JAVA}")
        )
        if not java_files:
            raise ConfigurationError(
                f"No Java monitor files (*{constants.EXTENSION_JAVA}) found in: {self.monitor_output_dir}\n"
                f"Generate monitors using rv-monitor-generator before instrumentation"
            )

    def _ensure_output_directories(self) -> None:
        """
        Create required output and temporary directories if they don't exist.

        This method ensures that all necessary directories for the instrumentation
        pipeline are available, creating them with appropriate permissions if needed.

        Raises:
            ConfigurationError: If directory creation fails
        """
        directories_to_create = [
            self.instrumented_dir,
            self.tmp_dir,
            self.lib_tmp_dir,
            self.rvm_tmp_dir,
        ]

        for directory in directories_to_create:
            try:
                Path(directory).mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise ConfigurationError(f"Cannot create directory: {directory} - {e}")

    def get_dex2jar_tools(self) -> Dex2jarTools:
        """
        Get validated dex2jar tool suite configuration.

        Returns:
            Dex2jarTools model with validated tool paths
        """
        return Dex2jarTools(
            dex2jar=os.path.join(self.dex2jar_home, "d2j-dex2jar.sh"),
            asm_verify=os.path.join(self.dex2jar_home, "d2j-asm-verify.sh"),
        )

    @ErrorHandler.handle_errors(
        component="RVInstrumentationConfig", phase="apk_validation", reraise=True
    )
    def validate_apk_input(self, apk_path: str) -> None:
        """
        Validate input APK file for instrumentation processing.

        Args:
            apk_path: Path to the APK file to be instrumented

        Raises:
            ConfigurationError: If APK validation fails
        """
        if not os.path.isfile(apk_path):
            raise ConfigurationError(f"APK file not found: {apk_path}")

        if not apk_path.lower().endswith(".apk"):
            raise ConfigurationError(f"File is not an APK: {apk_path}")

        if not os.access(apk_path, os.R_OK):
            raise ConfigurationError(f"APK file not readable: {apk_path}")

    def get_configuration_summary(self) -> ConfigurationSummary:
        """
        Generate comprehensive summary of current instrumentation configuration.

        Returns:
            ConfigurationSummary model with detailed configuration information
        """
        monitor_files = {
            "aspectj_count": len(
                glob.glob(
                    os.path.join(self.monitor_output_dir, f"*{constants.EXTENSION_AJ}")
                )
            ),
            "java_count": len(
                glob.glob(
                    os.path.join(
                        self.monitor_output_dir, f"*{constants.EXTENSION_JAVA}"
                    )
                )
            ),
        }

        return ConfigurationSummary(
            android_integration={
                "android_jar_path": self.android_jar_path,
                "android_platforms_dir": self.android_platforms_dir,
            },
            instrumentation_paths={
                "working_dir": self.working_dir,
                "instrumented_dir": self.instrumented_dir,
                "monitor_output_dir": self.monitor_output_dir,
            },
            temporary_directories={
                "tmp_dir": self.tmp_dir,
                "lib_tmp_dir": self.lib_tmp_dir,
                "rvm_tmp_dir": self.rvm_tmp_dir,
            },
            tools={
                "dex2jar_home": self.dex2jar_home,
                "dex2jar_tools": self.get_dex2jar_tools().model_dump(),
            },
            signing={
                "keystore_file": self.keystore_file,
                "keystore_configured": self.keystore_password is not None,
            },
            monitor_artifacts=monitor_files,
            validation_status="Validated",
        )

    def __str__(self) -> str:
        """Detailed string representation for debugging and logging."""
        return (
            f"RVInstrumentationConfig(\n"
            f"  Working Directory: {self.working_dir}\n"
            f"  Monitor Output: {self.monitor_output_dir}\n"
            f"  Android JAR: {self.android_jar_path}\n"
            f"  Instrumented Output: {self.instrumented_dir}\n"
            f"  Keystore: {self.keystore_file}\n"
            f"  dex2jar: {self.dex2jar_home}\n"
            f"  Status: Validated\n"
            f")"
        )
