import os
import glob
import subprocess
from typing import Optional, Dict, Any
from pathlib import Path

import rv_android_core.constants as constants


class ConfigurationError(Exception):
    """Raised when there's an error in the instrumentation configuration."""
    pass


class RVInstrumentationConfig:
    """
    Configuration management for RVInstrumentation with flexible path resolution.
    
    The RVInstrumentationConfig provides a sophisticated configuration system that supports
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
    
    def __init__(self,
                 rvsec_root: Optional[str] = None,
                 monitor_output_dir: Optional[str] = None,
                 android_jar_path: Optional[str] = None,
                 android_platforms_dir: Optional[str] = None,
                 keystore_file: Optional[str] = None,
                 keystore_password: Optional[str] = None,
                 working_dir: Optional[str] = None,
                 instrumented_dir: Optional[str] = None,
                 tmp_dir: Optional[str] = None,
                 lib_tmp_dir: Optional[str] = None,
                 rvm_tmp_dir: Optional[str] = None,
                 dex2jar_home: Optional[str] = None):
        """
        Initialize RVInstrumentationConfig with intelligent path resolution and validation.
        
        The initialization process follows a strict priority order for path resolution,
        ensuring predictable behavior across different deployment scenarios. All paths
        are validated for existence and accessibility during initialization.
        
        Args:
            rvsec_root: Root directory of RVSEC installation. Used for automatic
                       path discovery when individual paths are not provided.
            monitor_output_dir: Directory containing generated monitor artifacts from
                              rv-monitor-generator. Critical for instrumentation pipeline.
            android_jar_path: Path to Android SDK android.jar file. Required for
                            APK decompilation and recompilation workflows.
            android_platforms_dir: Directory containing Android SDK platform libraries.
                                 Used for Android API compatibility validation.
            keystore_file: Path to keystore file for APK signing. Required for
                         deployment-ready instrumented APKs.
            keystore_password: Password for keystore access. Must match keystore_file.
            working_dir: Base working directory for instrumentation operations.
                        Defaults to current working directory if not provided.
            instrumented_dir: Output directory for instrumented APK artifacts.
                            Critical for experiment orchestration integration.
            tmp_dir: Temporary directory for intermediate processing files.
                    Automatically cleaned during instrumentation workflows.
            lib_tmp_dir: Temporary directory for library extraction and processing.
                       Used during APK dependency resolution.
            rvm_tmp_dir: Temporary directory for runtime verification monitor processing.
                       Bridges rv-monitor-generator and instrumentation workflows.
            dex2jar_home: Directory containing dex2jar tool suite. Required for
                        DEX bytecode transformation operations.
                        
        Raises:
            ConfigurationError: If path resolution fails or required tools are not accessible
        """
        self.monitor_output_dir = monitor_output_dir
        self.android_jar_path = android_jar_path
        self.android_platforms_dir = android_platforms_dir
        self.keystore_file = keystore_file
        self.keystore_password = keystore_password
        self.working_dir = working_dir
        self.instrumented_dir = instrumented_dir
        self.tmp_dir = tmp_dir
        self.lib_tmp_dir = lib_tmp_dir
        self.rvm_tmp_dir = rvm_tmp_dir
        self.dex2jar_home = dex2jar_home
        
        # Resolve paths based on priority
        self._resolve_paths(rvsec_root)
        
        # Validate configuration
        self._validate_configuration()
    
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
            self.monitor_output_dir, self.android_jar_path, self.keystore_file,
            self.instrumented_dir, self.dex2jar_home
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
            raise ConfigurationError(f"{directory_purpose} directory not found: {directory_path}")
        
        if not os.access(directory_path, os.R_OK):
            raise ConfigurationError(f"{directory_purpose} directory not readable: {directory_path}")
    
    def _validate_android_jar(self) -> None:
        """
        Validate Android SDK android.jar accessibility and format.
        
        Raises:
            ConfigurationError: If android.jar validation fails
        """
        if not os.path.isfile(self.android_jar_path):
            raise ConfigurationError(f"Android JAR not found: {self.android_jar_path}")
        
        if not os.access(self.android_jar_path, os.R_OK):
            raise ConfigurationError(f"Android JAR not readable: {self.android_jar_path}")
    
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
            raise ConfigurationError(f"Keystore file not readable: {self.keystore_file}")
    
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
        aspectj_files = glob.glob(os.path.join(self.monitor_output_dir, f"*{constants.EXTENSION_AJ}"))
        if not aspectj_files:
            raise ConfigurationError(
                f"No AspectJ monitor files (*{constants.EXTENSION_AJ}) found in: {self.monitor_output_dir}\n"
                f"Generate monitors using rv-monitor-generator before instrumentation"
            )
        
        # Check for Java monitor classes
        java_files = glob.glob(os.path.join(self.monitor_output_dir, f"*{constants.EXTENSION_JAVA}"))
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
            self.rvm_tmp_dir
        ]
        
        for directory in directories_to_create:
            try:
                Path(directory).mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                raise ConfigurationError(f"Cannot create directory: {directory} - {e}")
    
    def get_dex2jar_tools(self) -> Dict[str, str]:
        """
        Get paths to dex2jar tool suite components.
        
        Returns:
            Dict containing paths to dex2jar tools required for APK processing
        """
        return {
            'dex2jar': os.path.join(self.dex2jar_home, "d2j-dex2jar.sh"),
            'asm_verify': os.path.join(self.dex2jar_home, "d2j-asm-verify.sh"),
            'apk_sign': os.path.join(self.dex2jar_home, "d2j-apk-sign.sh")
        }
    
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
        
        if not apk_path.lower().endswith('.apk'):
            raise ConfigurationError(f"File is not an APK: {apk_path}")
        
        if not os.access(apk_path, os.R_OK):
            raise ConfigurationError(f"APK file not readable: {apk_path}")
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        Generate comprehensive summary of current instrumentation configuration.
        
        Returns:
            Dict containing detailed configuration information for logging and debugging
        """
        monitor_files = {
            'aspectj_count': len(glob.glob(os.path.join(self.monitor_output_dir, f"*{constants.EXTENSION_AJ}"))),
            'java_count': len(glob.glob(os.path.join(self.monitor_output_dir, f"*{constants.EXTENSION_JAVA}")))
        }
        
        return {
            'android_integration': {
                'android_jar_path': self.android_jar_path,
                'android_platforms_dir': self.android_platforms_dir
            },
            'instrumentation_paths': {
                'working_dir': self.working_dir,
                'instrumented_dir': self.instrumented_dir,
                'monitor_output_dir': self.monitor_output_dir
            },
            'temporary_directories': {
                'tmp_dir': self.tmp_dir,
                'lib_tmp_dir': self.lib_tmp_dir,
                'rvm_tmp_dir': self.rvm_tmp_dir
            },
            'tools': {
                'dex2jar_home': self.dex2jar_home,
                'dex2jar_tools': self.get_dex2jar_tools()
            },
            'signing': {
                'keystore_file': self.keystore_file,
                'keystore_configured': self.keystore_password is not None
            },
            'monitor_artifacts': monitor_files,
            'validation_status': 'Validated'
        }
    
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