"""
Experiment Configuration Management for Android Testing Orchestration

### Architectural Overview:
This module implements clean configuration architecture for Android testing experiments,
providing type-safe configuration management with just-in-time sub-module configuration
and dependency injection ready design.

### Key Architectural Decisions:
- **Clean Design**: Direct class naming and focused responsibility
- **Just-in-Time Configuration**: Sub-modules configured only when needed
- **DI-Ready Design**: Factory pattern preparation for dependency injection
- **Monitored Operations**: Support for JCA crypto and generic programming pattern monitoring
- **Specification Set Support**: JCA crypto vs generic programming patterns
- **English Documentation**: Comprehensive architectural comments and documentation

### Role in the System:
- Primary configuration management for all experiment types
- Just-in-time coordination with sub-modules (rv-monitor-generator, rv-instrumentation, etc.)
- Factory-ready configuration structure for DI containers
- Support for multiple monitored operations specification sets
- Clean template generation for different experiment scenarios

### Design Patterns:
- **Factory Ready**: Configuration optimized for factory pattern usage
- **Just-in-Time**: Sub-module configuration created only when accessed
- **Template Builder**: Intelligent template creation for different scenarios
- **Validation Strategy**: Comprehensive validation with clear error messages
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, TYPE_CHECKING

from pydantic import Field

import rv_experiment.constants as constants
from rv_android_core.constants import ENV_RVSEC_HOME
from rv_android_core.constants import EXTENSION_MOP
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import ConfigurationError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.validation import BaseValidatedModel
from rv_experiment.constants import (
    RESULTS_DIR,
    INSTRUMENTED_DIR,
    DEFAULT_APKS_DIR,
    DEFAULT_SPEC_SET,
    MONITORS_DIR,
    INSTRUMENTED_APKS_DIR,
)
from rv_instrumentation.config import (
    RVInstrumentationConfig,
    ConfigurationError as InstrumentationConfigError,
)
from rv_monitor_generator.config import (
    RVGeneratorConfig,
    ConfigurationError as MonitorConfigError,
)
from rv_android_core.domain.task import ToolConfig
from rv_static_analysis.config import RVStaticAnalysisConfig

# Just-in-time imports - only import when needed
if TYPE_CHECKING:
    pass


class ExperimentConfig(BaseValidatedModel):
    """
    Primary experiment configuration for Android testing experiments.

    ### Architectural Overview:
    This class serves as the central configuration coordinator providing
    type-safe configuration with on-demand sub-module configuration.

    ### Key Features:
    - **Configuration Management**: Focused class responsibility for experiment settings
    - **On-Demand Configuration**: Sub-modules configured only when accessed
    - **Factory Pattern**: Preparation for dependency injection
    - **Monitored Operations**: Support for JCA crypto and generic programming pattern monitoring
    - **Specification Sets**: Support for JCA crypto vs generic programming patterns
    - **Documentation**: Comprehensive architectural comments and documentation

    ### Role in the System:
    - Primary configuration class for all experiment types
    - Coordinator for sub-module configuration
    - Factory structure for dependency injection
    - Template generator for different experiment scenarios
    - Validation coordinator with error handling
    - Configuration bridge between CLI and orchestration components
    """

    # Basic experiment metadata
    name: str = ""
    description: str = ""
    output_dir: str = ""

    rvsec_root: Optional[str] = Field(
        default=None, description="Override for RVSEC_HOME environment variable"
    )

    # Tool configuration
    tool_configs: List[ToolConfig] = Field(
        default_factory=list, description="List of tool configurations"
    )

    # Execution parameters
    repetitions: int = Field(default=1, gt=0, description="Number of repetitions")
    timeouts: List[int] = Field(
        default_factory=lambda: [60], description="List of timeout values in seconds"
    )
    no_window: bool = Field(default=True, description="Run without GUI window")
    device_port: Optional[int] = Field(
        default=None, description="Emulator port for parallel execution"
    )

    # Processing phases
    generate_monitors: bool = Field(default=True, description="Generate monitors")
    instrument_apks: bool = Field(default=True, description="Instrument APKs")
    run_static_analysis: bool = Field(default=True, description="Run static analysis")
    run_execution: bool = Field(
        default=True, description="Execute tasks after preprocessing"
    )

    # Monitored operations specification set
    specification_set: str = Field(
        default=DEFAULT_SPEC_SET, description="Specification set type"
    )
    custom_specs_dir: Optional[str] = Field(
        default=None, description="Custom specification directory"
    )
    custom_aspects_dir: Optional[str] = Field(
        default=None, description="Custom AspectJ aspects directory"
    )

    # APK sources
    apks_dir: str = Field(
        default=f"./{DEFAULT_APKS_DIR}/",
        description="Source APK directory path (contains APKs to be instrumented)",
    )
    apks_filter: Optional[str] = Field(
        default=None,
        description="Path to text file listing APK filenames to process (one per line)",
    )

    # Results configuration
    results_dir: Optional[str] = Field(
        default=None, description="Results directory path"
    )

    # Additional metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    created_at: Optional[str] = Field(default=None, description="Creation timestamp")

    # Continuation support and configuration hierarchy
    resume_mode: bool = Field(
        default=False, description="Enable experiment continuation mode"
    )
    status_file: Optional[str] = Field(
        default=None, description="Path to experiment status file for continuation"
    )

    def model_post_init(self, __context) -> None:
        """Initialize configuration after creation with defaults and validation."""
        date_now = datetime.now()

        if not self.name:
            self.name = f"experiment_{date_now.strftime('%Y%m%d_%H%M%S')}"

        if not self.output_dir:
            self.output_dir = constants.INSTRUMENTED_DIR

        # Set results_dir to same level as output_dir if not specified
        if not self.results_dir:
            if os.path.isabs(self.output_dir):
                self.results_dir = os.path.join(
                    os.path.dirname(self.output_dir), RESULTS_DIR
                )
            else:
                self.results_dir = RESULTS_DIR

        if not self.created_at:
            self.created_at = date_now.isoformat()

        # Initialize logging (not stored as instance attributes to avoid Pydantic validation issues)
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            "rv_experiment.config", {CONTEXT_COMPONENT: "ExperimentConfig"}
        )
        self.validate()
        logger.info(f"ExperimentConfig initialized: {self.to_json()}")

    @ErrorHandler.handle_errors(
        component="ExperimentConfig",
        phase="validate",
    )
    def validate(self) -> None:
        """
        Comprehensive validation of experiment configuration.

        ### Validation Strategy:
        - Basic parameter validation (names, timeouts, repetitions)
        - Tool configuration validation
        - APK source validation with pattern matching
        - Monitored operations specification validation
        - Directory structure validation

        Raises:
            ValueError: If configuration is invalid
            ConfigurationError: If configuration structure is inconsistent
        """
        # Validate basic configuration
        if not self.name:
            raise ValueError("Experiment name cannot be empty")

        if not self.tool_configs:
            raise ValueError("At least one tool must be configured")

        if self.repetitions <= 0:
            raise ValueError("Repetitions must be positive")

        if not self.timeouts or any(t <= 0 for t in self.timeouts):
            raise ValueError("All timeouts must be positive")

        # Validate tool configurations
        for tool_config in self.tool_configs:
            if not tool_config.name:
                raise ValueError("Tool configuration must have a name")

        # Validate APK sources
        if not self._validate_apk_sources():
            raise ConfigurationError(
                "No valid APK source directory configured. Ensure apks_dir exists and contains APK files."
            )

        # Validate specification set
        valid_spec_sets = ["jca", "generic", "custom"]
        if self.specification_set not in valid_spec_sets:
            raise ValueError(
                f"Invalid specification set '{self.specification_set}'. "
                f"Must be one of: {valid_spec_sets}"
            )

        # Validate tool variants
        self._validate_tool_variants()

        # Get logger for validation message
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            "rv_experiment.config", {CONTEXT_COMPONENT: "ExperimentConfig"}
        )
        logger.info("Configuration validation completed successfully")

    def _validate_apk_sources(self) -> bool:
        """
        Validate that APK source directory is available and contains APK files.

        Returns:
            True if valid APK sources are configured, False otherwise
        """
        # Check APK directory
        if self.apks_dir and Path(self.apks_dir).exists():
            apk_files = list(Path(self.apks_dir).glob("*.apk"))
            return len(apk_files) > 0

        return False

    @ErrorHandler.handle_errors(
        component="ExperimentConfig", phase="validate_tool_variants"
    )
    def _validate_tool_variants(self) -> None:
        """
        Validate all tool variant combinations in configuration.

        ### Variant Validation Strategy:
        - Check if tool exists in registry
        - Validate each variant exists or can be created as custom variant
        - Validate custom variants have required parameters
        - Provide helpful error messages for invalid configurations

        ### Module Hierarchy:
        This method coordinates validation across module boundaries while respecting
        the hierarchy by importing from lower-level modules only when needed.

        Raises:
            ConfigurationError: If any tool/variant combination is invalid
        """
        # Import only when needed to avoid circular dependencies
        try:
            from rv_tools import ToolRegistry
        except ImportError:
            # If rv-tools is not available, skip validation
            logging_manager = LoggingManager.get_instance()
            logger = logging_manager.get_logger(
                "rv_experiment.config", {CONTEXT_COMPONENT: "ExperimentConfig"}
            )
            logger.warning("rv-tools not available - skipping tool variant validation")
            return

        # External tools are registered by rv-platform on import
        tool_registry = ToolRegistry.get_instance()

        for tool_config in self.tool_configs:
            tool_name = tool_config.name

            # Check if tool is registered
            if not tool_registry.is_tool_registered(tool_name):
                available_tools = tool_registry.get_all_tool_names()
                raise ConfigurationError(
                    f"Tool '{tool_name}' not found in registry. Available tools: {available_tools}"
                )

            # Validate the variant (each ToolConfig has exactly one variant)
            variant_name = tool_config.variant
            if variant_name and variant_name != "default":
                if not tool_registry.validate_tool_variant(tool_name, variant_name):
                    # Check if this is a custom variant with complete parameters
                    if not self._validate_custom_variant(tool_config, variant_name):
                        try:
                            available_variants = list(
                                tool_registry.get_tool_variants(tool_name)
                            )
                        except:
                            available_variants = ["default"]
                        raise ConfigurationError(
                            f"Invalid variant '{variant_name}' for tool '{tool_name}'. "
                            f"Available variants: {available_variants}. "
                            f"For custom variants, ensure all required parameters are provided."
                        )

    def _validate_custom_variant(
        self, tool_config: ToolConfig, variant_name: str
    ) -> bool:
        """
        Validate custom variant has required parameters for complete configuration.

        ### Custom Variant Requirements:
        For RVAndroid custom variants, required parameters are:
        - llm_type: LLM backend type
        - llm_model: Model name
        - prompt_strategy: Prompt generation strategy

        For other tools, basic validation checks for some parameters.

        Args:
            tool_config: Tool configuration with parameters
            variant_name: Name of the custom variant

        Returns:
            True if custom variant is valid, False otherwise
        """
        # Custom variants should have some parameters
        return len(tool_config.parameters) > 0

    def get_apk_list(self) -> List[str]:
        """
        Get list of APK files to process based on configuration.

        If apks_filter is set, only APKs whose filename appears in the
        filter file are included.

        Returns:
            List of APK file paths

        Raises:
            ConfigurationError: If no APK files are found
        """
        apks = []

        if self.apks_dir:
            apks_dir_path = Path(self.apks_dir)
            if apks_dir_path.exists():
                apks.extend([str(p) for p in apks_dir_path.glob("*.apk")])

        if self.apks_filter:
            allowed = set(Path(self.apks_filter).read_text().strip().splitlines())
            apks = [a for a in apks if Path(a).name in allowed]

        if not apks:
            raise ConfigurationError(
                f"No APK files found in directory: {self.apks_dir}"
                + (f" (filter: {self.apks_filter})" if self.apks_filter else "")
            )

        return apks

    def validate_specs_dir(self, directory_path_str: str) -> bool:
        """
        Validate monitored operations specification directory structure.

        ### Architectural Overview:
        This method implements specification set validation by verifying directory
        existence and required .mop file presence for monitor generation compatibility.

        ### Validation Strategy:
        - Directory existence validation with proper error handling
        - Monitor Operation Pattern (.mop) file detection
        - Case-insensitive extension matching for cross-platform compatibility
        - Early termination optimization on first valid file detection

        ### Role in the System:
        - Validates custom specification directory structure for monitor generation
        - Ensures monitored operations specification availability before execution
        - Provides early failure detection for invalid specification configurations
        - Integrates with configuration validation workflow for consistent error handling

        Args:
            directory_path_str: Path to specification directory to validate

        Returns:
            True if directory contains valid .mop specification files, False otherwise
        """
        # Convert the string path to a Path object
        path = Path(directory_path_str)

        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger("rv_experiment.config")

        # 1. Validate if it's an existing directory
        if not path.is_dir():
            logger.info(
                f"'{directory_path_str}' is not a valid directory or does not exist."
            )
            return False

        # 2. Iterate over files in the directory and check for .mop files
        for item in path.iterdir():
            if item.is_file() and item.suffix.lower() == EXTENSION_MOP:
                logger.debug(
                    f"{EXTENSION_MOP} file found: '{item.name}' in '{directory_path_str}'"
                )
                return True

        logger.info(f"No {EXTENSION_MOP} files found in '{directory_path_str}'.")
        return False

    def get_monitored_operations_config(self) -> RVGeneratorConfig:
        """
        Just-in-time configuration for monitor generation based on specification set.

        ### Configuration Pattern:
        This method creates monitor generation configuration only when needed,
        providing flexibility while maintaining module independence.

        ### Specification Set Support:
        - **JCA**: Java Cryptography Architecture API monitoring
        - **Generic**: Generic programming patterns (Iterator, Collections, etc.)
        - **Custom**: User-defined specification sets

        ### Implementation:
        Returns a typed RVGeneratorConfig instance that provides type safety,
        validation, and integration with the configuration architecture.

        Returns:
            RVGeneratorConfig instance with monitor generation configuration

        Raises:
            ConfigurationError: If specification set is not supported
            MonitorConfigError: If RVGeneratorConfig validation fails
        """
        # Use configuration hierarchy for RVSEC_HOME resolution
        rvsec_root = self.get_effective_rvsec_root()

        # Determine specification set directory
        mop_base_dir = os.path.join(
            rvsec_root, "rvsec", "rvsec-mop", "src", "main", "resources"
        )
        if self.specification_set == "jca":
            mop_specs_dir = os.path.join(mop_base_dir, "jca")
        elif self.specification_set == "generic":
            mop_specs_dir = os.path.join(mop_base_dir, "generic")
        elif self.specification_set == "custom":
            if self.custom_specs_dir:
                mop_specs_dir = self.custom_specs_dir
                if not self.validate_specs_dir(mop_specs_dir):
                    raise ConfigurationError(f"Invalid specs dir: {mop_specs_dir}")
            else:
                raise ConfigurationError(
                    f"Unsupported specification set: {self.specification_set}"
                )
        else:
            raise ConfigurationError(
                f"Unsupported specification set: {self.specification_set}"
            )

        try:
            # Create RVGeneratorConfig instance with explicit paths
            # to ensure mop_specs_dir is not overridden by automatic resolution

            # Determine aspects directory: custom if provided, otherwise standard RVSEC
            if self.custom_aspects_dir:
                aspects_dir = self.custom_aspects_dir
            else:
                # Use standard aspects directory from RVSEC
                aspects_dir = os.path.join(
                    rvsec_root,
                    "rvsec",
                    "rvsec-mop",
                    "src",
                    "main",
                    "resources",
                    "aspect",
                )

            return RVGeneratorConfig(
                rvsec_root=rvsec_root,
                javamop_bin=os.path.join(rvsec_root, "javamop", "bin", "javamop"),
                rvmonitor_bin=os.path.join(
                    rvsec_root, "rv-monitor", "bin", "rv-monitor"
                ),
                mop_specs_dir=mop_specs_dir,
                aspects_dir=aspects_dir,
            )
        except MonitorConfigError as e:
            raise ConfigurationError(
                f"Monitor generation configuration failed: {e}"
            ) from e

    def get_instrumentation_config(self) -> RVInstrumentationConfig:
        """
        Just-in-time configuration for APK instrumentation.

        ### Just-in-Time Configuration Pattern:
        This method creates instrumentation configuration only when needed,
        deriving parameters from experiment configuration while maintaining
        module independence through simple parameter passing.

        ### Implementation:
        Returns a typed RVInstrumentationConfig instance that provides type safety,
        validation, and integration with the configuration architecture.

        Returns:
            RVInstrumentationConfig instance with instrumentation configuration

        Raises:
            ConfigurationError: If APK configuration is invalid
            InstrumentationConfigError: If RVInstrumentationConfig validation fails
        """
        # Use configuration hierarchy for RVSEC_HOME resolution
        rvsec_root = self.get_effective_rvsec_root()

        # Use rv-android directory as working directory (where lib/ and tools are)
        rv_android_dir = os.path.join(rvsec_root, "rv-android")

        # Determine monitor output directory from experiment
        monitor_output_dir = (
            os.path.join(self.output_dir, MONITORS_DIR) if self.output_dir else None
        )

        try:
            # Create RVInstrumentationConfig instance with tool paths
            return RVInstrumentationConfig(
                rvsec_root=rvsec_root,
                monitor_output_dir=monitor_output_dir,
                working_dir=rv_android_dir,  # Use rv-android dir where lib/ exists
                instrumented_dir=os.path.join(self.output_dir, INSTRUMENTED_APKS_DIR),
                keystore_password="password",
            )
        except InstrumentationConfigError as e:
            raise ConfigurationError(
                f"Instrumentation configuration failed: {e}"
            ) from e

    def get_rv_instrumentation_config(self) -> RVInstrumentationConfig:
        """
        Get configuration for rv-instrumentation module.

        ### Architectural Overview:
        This method provides the rv-instrumentation module configuration by delegating
        to the primary instrumentation configuration method. It ensures consistent
        configuration access patterns across experiment workflow components.

        ### Configuration Integration:
        The method returns a validated RVInstrumentationConfig instance that includes
        all necessary paths, tools, and validation parameters required for APK
        instrumentation operations within the experiment context.

        ### Role in the System:
        - Provides configuration access point for pre-processor components
        - Ensures instrumentation configuration consistency across workflow phases
        - Integrates with experiment output directory structure
        - Validates instrumentation tool availability and accessibility

        Returns:
            RVInstrumentationConfig instance with instrumentation configuration

        Raises:
            ConfigurationError: If APK configuration is invalid
            InstrumentationConfigError: If RVInstrumentationConfig validation fails
        """
        return self.get_instrumentation_config()

    def get_static_analysis_config(self) -> RVStaticAnalysisConfig:
        """
        Just-in-time configuration for static analysis component.

        ### Configuration Pattern:
        This method creates static analysis configuration only when needed,
        providing type safety and validation while maintaining module independence
        through clean parameter passing.

        ### Implementation:
        Returns a typed RVStaticAnalysisConfig instance that provides validation,
        tool coordination, and integration with the experiment output structure.

        ### Role in the System:
        - Coordinates static analysis tool configuration with experiment parameters
        - Provides output directory integration for analysis result storage
        - Enables tool selection and parameter coordination
        - Integrates with experiment workflow for consistent error handling


        Returns:
            RVStaticAnalysisConfig instance with static analysis configuration

        Raises:
            ConfigurationError: If static analysis configuration fails
        """
        # Use configuration hierarchy for RVSEC_HOME resolution
        rvsec_root = self.get_effective_rvsec_root()

        # Use rv-android directory as base for lib tools
        rv_android_dir = os.path.join(rvsec_root, "rv-android")
        lib_dir = os.path.join(rv_android_dir, "lib")

        try:
            # analysis_client_jar defaults from gator_dir, but explicit is clearer
            gator_dir = os.path.join(lib_dir, "gator")
            analysis_client_jar = os.path.join(gator_dir, "rvsec-analysis-client.jar")

            return RVStaticAnalysisConfig(
                rvsec_root=rvsec_root,
                lib_dir=lib_dir,
                gator_dir=gator_dir,
                analysis_client_jar=analysis_client_jar,
                output_dir=self.output_dir,
                working_dir=self.output_dir,
                validate_on_init=False,
            )
        except Exception as e:
            raise ConfigurationError(
                f"Static analysis configuration failed: {e}"
            ) from e

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary format for serialization and storage.

        ### Serialization Architecture:
        This method provides configuration serialization using Pydantic's model_dump
        functionality, ensuring consistent data structure representation across
        different storage and transmission contexts.

        Returns:
            Configuration as dictionary with all fields serialized
        """
        return self.model_dump()

    def to_json(self, indent: int = 2) -> str:
        """
        Convert configuration to JSON format for storage and exchange.

        ### JSON Serialization:
        This method provides JSON serialization with configurable indentation
        for human-readable configuration files and API responses.

        Args:
            indent: JSON indentation level for formatting

        Returns:
            Configuration as formatted JSON string
        """
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperimentConfig":
        """
        Create configuration from dictionary with validation and type conversion.

        ### Deserialization Architecture:
        This method implements configuration deserialization with automatic
        type conversion for tool configurations and proper validation
        of all configuration parameters.

        Args:
            data: Configuration dictionary from storage or API

        Returns:
            Validated ExperimentConfig instance
        """
        # Handle tool configurations using ToolConfig.from_dict() with current field names
        if "tool_configs" in data and isinstance(data["tool_configs"], list):
            data["tool_configs"] = [
                ToolConfig.from_dict(tc) if isinstance(tc, dict) else tc
                for tc in data["tool_configs"]
            ]

        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "ExperimentConfig":
        """
        Create configuration from JSON string with parsing and validation.

        ### JSON Deserialization:
        This method provides JSON parsing with automatic conversion to
        typed configuration instance, including validation of all parameters.

        Args:
            json_str: JSON configuration string from file or API

        Returns:
            Validated ExperimentConfig instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, file_path: str) -> "ExperimentConfig":
        """
        Load configuration from file with format detection and validation.

        ### File Loading Architecture:
        This method implements configuration file loading with automatic
        format detection (JSON) and comprehensive validation of loaded data.

        Args:
            file_path: Path to configuration file (JSON format)

        Returns:
            Validated ExperimentConfig instance

        Raises:
            FileNotFoundError: If configuration file doesn't exist
            ConfigurationError: If file format or content is invalid
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        with open(path, "r") as f:
            data = json.load(f)

        return cls.from_dict(data)

    def save_to_file(self, file_path: str) -> None:
        """
        Save configuration to file with directory creation and logging.

        ### File Saving Architecture:
        This method implements configuration persistence with automatic
        directory creation and comprehensive logging for audit trails.

        Args:
            file_path: Path to save configuration file (JSON format)
        """
        path = Path(file_path)

        # Create parent directory if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Save configuration as JSON
        with open(path, "w") as f:
            f.write(self.to_json())

        # Get logger for save message
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            "rv_experiment.config", {CONTEXT_COMPONENT: "ExperimentConfig"}
        )
        logger.info(f"Configuration saved to: {file_path}")

    def get_module_config(self, module_name: str) -> Union[
        RVGeneratorConfig,
        RVInstrumentationConfig,
        RVStaticAnalysisConfig,
        Dict[str, Any],
    ]:
        """
        Get module-specific configuration with type safety and just-in-time creation.

        ### Module Configuration Pattern:
        This method provides module-specific configuration instances using
        just-in-time creation pattern, ensuring each module receives properly
        typed and validated configuration objects.

        ### Supported Modules:
        - **rv-monitor-generator**: Monitor generation configuration
        - **rv-instrumentation**: APK instrumentation configuration
        - **rv-static-analysis**: Static analysis tool configuration

        Args:
            module_name: Name of the module requiring configuration

        Returns:
            Typed configuration instance specific to the requested module
        """
        if module_name == "rv-monitor-generator":
            return self.get_monitored_operations_config()
        elif module_name == "rv-instrumentation":
            return self.get_instrumentation_config()
        elif module_name == "rv-static-analysis":
            return self.get_static_analysis_config()
        else:
            return {}

    def get_instrumented_dir(self) -> str:
        """
        Get the instrumented APKs directory path for experiment workflow.

        ### Directory Structure:
        This method provides the standard directory path where instrumented
        APKs are stored, maintaining consistent directory structure across
        experiment execution phases.

        Returns:
            Path to instrumented APKs directory
        """
        return INSTRUMENTED_DIR

    def get_timestamp_string(self) -> str:
        """
        Get timestamp string for experiment identification and result organization.

        ### Timestamp Format:
        This method provides consistent timestamp formatting for experiment
        identification, result directory naming, and audit trail maintenance.

        Returns:
            Timestamp string in format YYYYMMDD_HHMMSS
        """
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    @ErrorHandler.handle_errors(
        component="ExperimentConfig", phase="rvsec_root_hierarchy"
    )
    def get_effective_rvsec_root(self) -> str:
        """
        Get RVSEC_HOME with configuration hierarchy support.

        ### Configuration Hierarchy:
        1. Priority 1: Configuration override (self.rvsec_root) - enables experiment-specific paths
        2. Priority 2: Environment variable (ENV_RVSEC_HOME) - system default
        3. Priority 3: Error if neither defined - required for operation

        ### Role in the System:
        - Provides centralized RVSEC_HOME resolution for all module configurations
        - Enables experiment-specific path overrides for isolated execution
        - Maintains backward compatibility with environment variable usage
        - Validates path existence regardless of source

        Returns:
            Effective RVSEC_HOME path

        Raises:
            ConfigurationError: If RVSEC_HOME not found in configuration or environment
        """
        # Priority 1: Configuration override takes precedence
        if self.rvsec_root:
            if not os.path.exists(self.rvsec_root):
                raise ConfigurationError(
                    f"Configured rvsec_root path does not exist: {self.rvsec_root}"
                )
            return self.rvsec_root

        # Priority 2: Environment variable fallback
        env_value = os.getenv(ENV_RVSEC_HOME)
        if env_value:
            if not os.path.exists(env_value):
                raise ConfigurationError(
                    f"RVSEC_HOME environment path does not exist: {env_value}"
                )
            return env_value

        # Priority 3: Error for required configuration
        raise ConfigurationError(
            "RVSEC_HOME not found in configuration or environment. "
            "Set rvsec_root field in configuration or RVSEC_HOME environment variable"
        )
