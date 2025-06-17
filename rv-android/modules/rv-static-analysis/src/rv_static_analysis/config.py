"""
Configuration management for rv-static-analysis module.

This module provides comprehensive configuration management for static analysis tools
(GATOR, GESDA, REACH) with intelligent path resolution and validation.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any

from rv_android_core.constants import ENV_RVSEC_HOME, ENV_ANDROID_HOME, ENV_RT_JAR
from rv_android_core.util.exceptions import RVAndroidError, ConfigurationError
from rv_android_core.util.validation import BaseValidatedModel
from pydantic import Field


class RVStaticAnalysisConfig(BaseValidatedModel):
    """
    Configuration manager for static analysis tools and environments.
    
    The RVStaticAnalysisConfig provides comprehensive configuration management for
    the three primary static analysis tools (GATOR, GESDA, REACH) used in the
    RV-Android system. It implements intelligent path resolution with multiple
    fallback strategies and extensive validation.

    ### Architectural Decisions:
    - Implements priority-based path resolution for maximum deployment flexibility
    - Provides comprehensive validation for tool availability and environment setup
    - Supports both explicit configuration and automatic discovery modes
    - Integrates with Android SDK and Java runtime environment detection
    - Uses pathlib for robust cross-platform path handling

    ### Role in the System:
    - Acts as the central configuration authority for static analysis workflows
    - Provides validated paths for all required tools and dependencies
    - Enables flexible deployment across different development environments
    - Ensures configuration consistency for static analysis tool execution
    - Supports both manual configuration and environment-based discovery

    ### Path Resolution Priority (highest to lowest):
    1. Explicit parameters provided during initialization (highest priority)
    2. rvsec_root parameter with standard relative path resolution
    3. ENV_RVSEC_HOME environment variable with standard relative paths
    4. Current working directory as fallback rvsec_root
    """

    rvsec_root: Optional[str] = Field(
        default=None,
        description="RVSEC installation root directory for tool discovery"
    )
    lib_dir: Optional[str] = Field(
        default=None,
        description="Directory containing static analysis tool JARs"
    )
    android_platforms_dir: Optional[str] = Field(
        default=None,
        description="Android SDK platforms directory"
    )
    android_jar: Optional[str] = Field(
        default=None,
        description="Android SDK JAR path (android.jar)"
    )
    rt_jar: Optional[str] = Field(
        default=None,
        description="Java runtime JAR path (rt.jar)"
    )
    mop_dir: Optional[str] = Field(
        default=None,
        description="Monitor-Oriented Programming specifications directory"
    )
    output_dir: Optional[str] = Field(
        default=None,
        description="Base output directory for analysis results"
    )
    working_dir: Optional[str] = Field(
        default=None,
        description="Working directory for temporary files"
    )
    gesda_jar: Optional[str] = Field(
        default=None,
        description="Explicit path to GESDA JAR file"
    )
    gator_dir: Optional[str] = Field(
        default=None,
        description="Explicit path to GATOR tools directory"
    )
    reach_jar: Optional[str] = Field(
        default=None,
        description="Explicit path to REACH JAR file"
    )
    validate_on_init: bool = Field(
        default=True,
        description="Whether to validate configuration on initialization"
    )

    def model_post_init(self, __context) -> None:
        """
        Execute path resolution and validation after model initialization.
        
        This method implements the complete configuration workflow including
        intelligent path resolution and comprehensive validation when requested.
        """
        # Apply path resolution strategy
        self._resolve_paths()

        # Validate configuration if requested
        if self.validate_on_init:
            self._validate_configuration()

    def _resolve_paths(self) -> None:
        """
        Execute comprehensive path resolution using priority-based strategy.
        
        This method implements the core path resolution logic, following the established
        priority order to determine final paths for all required tools and directories.
        The resolution process supports multiple deployment scenarios and provides
        intelligent fallback mechanisms.
        """
        # Determine RVSEC root directory using priority-based resolution
        if not self.rvsec_root:
            self.rvsec_root = os.environ.get(ENV_RVSEC_HOME)
            if not self.rvsec_root:
                self.rvsec_root = os.getcwd()

        # Apply default paths based on resolved RVSEC root
        self._apply_default_paths()

        # Ensure all paths are absolute for consistency
        self._normalize_paths()

    def _apply_default_paths(self) -> None:
        """
        Apply intelligent default path values based on RVSEC root directory.
        
        This method implements the standard RVSEC directory layout assumptions and
        provides sensible defaults for all configuration paths. It also integrates
        with standard Android SDK and Java runtime environment detection.
        """
        rvsec_path = Path(self.rvsec_root)

        # Lib directory containing all static analysis tools
        if not self.lib_dir:
            self.lib_dir = str(rvsec_path / "rv-android" / "lib")

        # Android SDK configuration with environment variable integration
        if not self.android_platforms_dir:
            android_home = os.environ.get(ENV_ANDROID_HOME)
            if android_home:
                self.android_platforms_dir = str(Path(android_home) / "platforms")

        # Android JAR discovery with multiple API level fallbacks
        if not self.android_jar and self.android_platforms_dir:
            # Try Android API levels in order of preference
            for api_level in ["29", "28", "27", "26"]:
                candidate = Path(self.android_platforms_dir) / f"android-{api_level}" / "android.jar"
                if candidate.exists():
                    self.android_jar = str(candidate)
                    break

        # Java Runtime JAR with environment variable and SDKMAN integration
        if not self.rt_jar:
            default_rt_jar = str(
                Path.home() / ".sdkman" / "candidates" / "java" / "8.0.302-open" / "jre" / "lib" / "rt.jar")
            self.rt_jar = os.environ.get(ENV_RT_JAR, default_rt_jar)

        # MOP directory for monitor specifications (default to JCA)
        if not self.mop_dir:
            self.mop_dir = str(rvsec_path / "rvsec" / "rvsec-mop" / "src" / "main" / "resources" / "jca")

        # Output and working directories
        if not self.output_dir:
            self.output_dir = str(rvsec_path / "out")

        if not self.working_dir:
            self.working_dir = str(rvsec_path / "working")

        # Tool-specific path resolution using standard RVSEC layout
        lib_path = Path(self.lib_dir)

        if not self.gesda_jar:
            self.gesda_jar = str(lib_path / "gesda" / "rvsec-gesda.jar")

        if not self.gator_dir:
            self.gator_dir = str(lib_path / "gator")

        if not self.reach_jar:
            self.reach_jar = str(lib_path / "reach" / "rvsec-reach.jar")

    def _normalize_paths(self) -> None:
        """
        Convert all configuration paths to absolute paths for consistency.
        
        This method ensures that all path fields contain absolute paths, which
        prevents issues with relative path resolution during tool execution.
        """
        path_attributes = [
            'rvsec_root', 'lib_dir', 'android_platforms_dir', 'android_jar', 'rt_jar',
            'mop_dir', 'output_dir', 'working_dir', 'gesda_jar', 'gator_dir', 'reach_jar'
        ]

        for attr in path_attributes:
            value = getattr(self, attr)
            if value:
                setattr(self, attr, os.path.abspath(value))

    def _validate_configuration(self) -> None:
        """
        Execute comprehensive configuration validation to ensure operational readiness.
        
        This validation process performs extensive checks to verify that all configured
        paths, tools, and dependencies are accessible and functional. It's designed to
        fail fast during initialization rather than during analysis execution.
        
        ### Validation Phases:
        1. Required paths validation
        2. Tool availability verification
        3. Android SDK and Java runtime validation
        4. MOP specifications directory validation
        
        Raises:
            ConfigurationError: If any validation check fails with detailed diagnostic information
        """
        self._validate_required_paths()
        self._validate_tool_availability()
        self._validate_android_sdk()
        self._validate_mop_directory()

    def _validate_required_paths(self) -> None:
        """
        Validate that all required configuration paths are properly set.
        
        Raises:
            ConfigurationError: If any required path is not configured
        """
        required_paths = {
            'lib_dir': self.lib_dir,
            'output_dir': self.output_dir,
            'working_dir': self.working_dir
        }

        for name, path in required_paths.items():
            if not path:
                raise ConfigurationError(f"Required path '{name}' is not configured")

    def _validate_tool_availability(self) -> None:
        """
        Validate that all static analysis tools are available and accessible.
        
        This method checks for the existence of all tool components required
        for static analysis execution.
        
        Raises:
            ConfigurationError: If any required tool component is not available
        """
        components = self.get_tool_components()

        for component_name, component_path in components.items():
            if component_name == 'gator_python':
                # GATOR python script might not have .py extension
                if not os.path.isfile(component_path):
                    raise ConfigurationError(
                        f"Static analysis tool component '{component_name}' not found: {component_path}")
            elif component_name in ['gesda_jar', 'gator_client_jar', 'reach_jar']:
                if not os.path.isfile(component_path):
                    raise ConfigurationError(
                        f"Static analysis tool component '{component_name}' not found: {component_path}")

    def _validate_android_sdk(self) -> None:
        """
        Validate Android SDK and Java runtime environment configuration.
        
        This method ensures that the Android SDK is properly configured and
        that the Java runtime JAR is accessible for tool execution.
        
        Raises:
            ConfigurationError: If Android SDK or Java runtime configuration is invalid
        """
        if not self.android_platforms_dir:
            raise ConfigurationError("Android platforms directory not configured")

        if not os.path.isdir(self.android_platforms_dir):
            raise ConfigurationError(f"Android platforms directory does not exist: {self.android_platforms_dir}")

        if not self.android_jar:
            raise ConfigurationError("Android JAR (android_jar) not configured")

        if not os.path.isfile(self.android_jar):
            raise ConfigurationError(f"Android JAR does not exist: {self.android_jar}")

        if not self.rt_jar:
            raise ConfigurationError(f"Java runtime JAR (rt_jar) not configured. Set {ENV_RT_JAR} environment variable")

        if not os.path.isfile(self.rt_jar):
            raise ConfigurationError(
                f"Java runtime JAR does not exist: {self.rt_jar}. Set {ENV_RT_JAR} environment variable to correct path.")

    def _validate_mop_directory(self) -> None:
        """
        Validate MOP specifications directory configuration.
        
        Raises:
            ConfigurationError: If MOP directory is not properly configured
        """
        if not self.mop_dir:
            raise ConfigurationError("MOP specifications directory not configured")

        if not os.path.isdir(self.mop_dir):
            raise ConfigurationError(f"MOP specifications directory does not exist: {self.mop_dir}")

    def get_static_analysis_tools(self) -> Dict[str, str]:
        """
        Get paths to the three primary static analysis tools.
        
        Returns:
            Dictionary mapping logical tool names to their primary executable paths
        """
        return {
            'gesda': self.gesda_jar,
            'gator': self.gator_dir,
            'reach': self.reach_jar
        }

    def get_tool_components(self) -> Dict[str, str]:
        """
        Get detailed paths to all tool components for internal execution.
        
        This method provides access to the individual components that make up
        each static analysis tool, including JAR files and Python scripts.
        
        Returns:
            Dictionary mapping component names to their executable paths
        """
        gator_path = Path(self.gator_dir)

        return {
            'gesda_jar': self.gesda_jar,
            'gator_python': str(gator_path / "gator"),
            'gator_client_jar': str(gator_path / "rvsec-gator-client.jar"),
            'reach_jar': self.reach_jar
        }

    def validate_apk_input(self, apk_path: str) -> None:
        """
        Validate APK input file for static analysis.
        
        This method performs comprehensive validation of the APK file to ensure
        it's suitable for static analysis processing.
        
        Args:
            apk_path: Path to APK file for validation
        
        Raises:
            ConfigurationError: If APK validation fails
        """
        if not apk_path:
            raise ConfigurationError("APK path is required")

        if not os.path.isfile(apk_path):
            raise ConfigurationError(f"APK file does not exist: {apk_path}")

        if not apk_path.lower().endswith('.apk'):
            raise ConfigurationError(f"File is not an APK: {apk_path}")

    def get_tool_command(self, tool_name: str, apk_path: str, output_file: str, **kwargs) -> list:
        """
        Generate command line for static analysis tool execution.
        
        This method constructs the complete command line arguments required
        to execute each static analysis tool with the appropriate configuration.
        
        Args:
            tool_name: Name of tool ('gesda', 'gator', 'reach')
            apk_path: Path to APK file to analyze
            output_file: Path to output file for analysis results
            **kwargs: Additional tool-specific arguments
        
        Returns:
            Command line as list of strings ready for execution
        
        Raises:
            ConfigurationError: If tool is not supported or required parameters are missing
        """
        tools = self.get_static_analysis_tools()
        components = self.get_tool_components()

        if tool_name == 'gesda':
            return [
                'java', '-jar', components['gesda_jar'],
                '--android-dir', self.android_platforms_dir,
                '--rt-jar', self.rt_jar,
                '--output', output_file,
                '--apk', apk_path
            ]
        elif tool_name == 'gator':
            client_jar = kwargs.get('client_jar', components['gator_client_jar'])
            return [
                'python', components['gator_python'], 'a',
                '-p', apk_path,
                '--client-jar', client_jar,
                '--out', output_file,
                '-client', 'RvsecWtgClient'
            ]
        elif tool_name == 'reach':
            gesda_file = kwargs.get('gesda_file')
            if not gesda_file:
                raise ConfigurationError("REACH tool requires GESDA output file")

            timeout = kwargs.get('timeout', 300)
            return [
                'java', '-jar', components['reach_jar'],
                '--android-dir', self.android_platforms_dir,
                '--rt-jar', self.rt_jar,
                '--mop-dir', self.mop_dir,
                '--gesda', gesda_file,
                '--writer', 'csv',
                '--timeout', str(timeout),
                '--apk', apk_path,
                '--output', output_file
            ]
        else:
            raise ConfigurationError(f"Unsupported static analysis tool: {tool_name}")

    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        Generate comprehensive configuration summary for debugging and logging.
        
        This method provides detailed information about the current configuration
        state, including tool availability and validation status.
        
        Returns:
            Dictionary containing comprehensive configuration details
        """
        tools = self.get_static_analysis_tools()
        components = self.get_tool_components()

        return {
            'rvsec_integration': {
                'rvsec_root': self.rvsec_root,
                'lib_dir': self.lib_dir,
                'mop_dir': self.mop_dir,
                'output_dir': self.output_dir,
                'working_dir': self.working_dir
            },
            'java_android_integration': {
                'android_platforms_dir': self.android_platforms_dir,
                'android_jar': self.android_jar,
                'rt_jar': self.rt_jar
            },
            'static_analysis_tools': {
                'gesda': tools['gesda'],
                'gator': tools['gator'],
                'reach': tools['reach']
            },
            'tool_components': {
                'gesda_jar': components['gesda_jar'],
                'gator_python': components['gator_python'],
                'gator_client_jar': components['gator_client_jar'],
                'reach_jar': components['reach_jar']
            },
            'tool_availability': {
                tool_name: os.path.isfile(tool_path) if tool_name != 'gator' else os.path.isdir(tool_path)
                for tool_name, tool_path in tools.items()
            },
            'validation_status': 'Validated'
        }

    def create_output_directories(self) -> None:
        """
        Create necessary output and working directories for static analysis.
        
        This method ensures that all required directories exist before starting
        the static analysis process.
        """
        directories = [self.output_dir, self.working_dir]

        for directory in directories:
            if directory:
                os.makedirs(directory, exist_ok=True)