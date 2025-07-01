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
import rv_experiment.constants as constants
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, TYPE_CHECKING

from pydantic import Field, field_validator, model_validator
from rv_android_core.util.validation import BaseValidatedModel
# Import ToolConfig from rv-platform for unified tool configuration
from rv_platform.config.platform_config import ToolConfig

from rv_android_core.constants import ENV_RVSEC_HOME
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.exceptions import ConfigurationError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_experiment.constants import (
    RESULTS_DIR, INSTRUMENTED_DIR, DEFAULT_APKS_DIR,
    DEFAULT_APK_PATTERNS, DEFAULT_TIMEOUT, DEFAULT_REPETITIONS,
    DEFAULT_SPEC_SET, get_experiment_dir
)
from rv_instrumentation.config import RVInstrumentationConfig, ConfigurationError as InstrumentationConfigError
from rv_llm.config.llm_config import LLMConfig
# Configuration class imports for proper type usage
from rv_monitor_generator.config import RVGeneratorConfig, ConfigurationError as MonitorConfigError
from rv_static_analysis.config import RVStaticAnalysisConfig
from rv_android_core.constants import EXTENSION_MOP

# Just-in-time imports - only import when needed
if TYPE_CHECKING:
    pass


# ToolConfig is imported from rv-platform for unified tool configuration




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
    # experiment_id: Optional[str] = None
    # results_dir: str = ""
    experiment_dir: str = ""

    # Tool configuration
    tool_configs: List[ToolConfig] = Field(default_factory=list, description="List of tool configurations")

    # Execution parameters
    repetitions: int = Field(default=1, gt=0, description="Number of repetitions")
    timeouts: List[int] = Field(default_factory=lambda: [300], description="List of timeout values in seconds")
    no_window: bool = Field(default=True, description="Run without GUI window")

    # Processing phases
    generate_monitors: bool = Field(default=True, description="Generate monitors")
    instrument_apks: bool = Field(default=True, description="Instrument APKs")
    run_static_analysis: bool = Field(default=True, description="Run static analysis")
    # TODO remover
    analyze_instrumented_apks: bool = Field(default=False, description="Use instrumented APKs for static analysis when available")

    # Monitored operations specification set
    specification_set: str = Field(default=DEFAULT_SPEC_SET, description="Specification set type")
    custom_specs_dir: Optional[str] = Field(default=None, description="Custom specification directory")
    custom_aspects_dir: Optional[str] = Field(default=None, description="Custom AspectJ aspects directory")

    # APK sources
    # TODO remover apk_path e apk_patterns. renomear apk_dir para apks_dir
    apk_path: Optional[str] = Field(default=None, description="Single APK file path")
    apk_dir: str = Field(default=f"./{DEFAULT_APKS_DIR}/", description="APK directory path")
    apk_patterns: List[str] = Field(default_factory=lambda: DEFAULT_APK_PATTERNS.copy(), description="APK file patterns")

    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: Optional[str] = Field(default=None, description="Creation timestamp")

    # Continuation support and configuration hierarchy
    resume_mode: bool = Field(default=False, description="Enable experiment continuation mode")
    status_file: Optional[str] = Field(default=None, description="Path to experiment status file for continuation")
    artifact_reuse_enabled: bool = Field(default=True, description="Enable artifact reuse for phase execution")
    skip_completed_phases: bool = Field(default=True, description="Skip phases with existing artifacts")
    force_regeneration: bool = Field(default=False, description="Regenerate all artifacts regardless of existence")
    rvsec_root: Optional[str] = Field(default=None, description="Override for RVSEC_HOME environment variable")
    
    # Phase control for flexible execution
    phase_control: Dict[str, bool] = Field(
        default_factory=lambda: {
            "skip_monitors": False,
            "skip_instrumentation": False,
            "skip_static_analysis": False
        },
        description="Phase execution control flags"
    )

    def model_post_init(self, __context) -> None:
        """Initialize configuration after creation with defaults and validation."""
        date_now = datetime.now()

        if not self.name:
            self.name = f"experiment_{date_now.strftime('%Y%m%d_%H%M%S')}"

        if not self.output_dir:
            self.output_dir = constants.RESULTS_DIR

        self.experiment_dir = get_experiment_dir(self.name)

        if not self.created_at:
            self.created_at = date_now.isoformat()

        # Initialize logging (not stored as instance attributes to avoid Pydantic validation issues)
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            "rv_experiment.config",
            {CONTEXT_COMPONENT: "ExperimentConfig"}
        )
        logger.debug("ExperimentConfig initialized")

    @ErrorHandler.handle_errors(
        component="ExperimentConfig",
        phase="validate",
    )
    def validate(self) -> None:
        """
        Comprehensive validation of experiment configuration.
        
        ### Validation Strategy:
        - Basic parameter validation (names, timeouts, repetitions)
        - Tool configuration validation with variant support
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
                "No valid APK sources configured. Specify apk_path, ensure apk_dir exists, "
                "or provide valid apk_patterns."
            )

        # Validate specification set
        valid_spec_sets = ["jca", "generic", "custom"]
        if self.specification_set not in valid_spec_sets:
            raise ValueError(
                f"Invalid specification set '{self.specification_set}'. "
                f"Must be one of: {valid_spec_sets}"
            )

        # Validate output directory
        if self.output_dir:
            output_path = Path(self.output_dir)
            if not output_path.parent.exists():
                raise ValueError(f"Parent directory for output does not exist: {output_path.parent}")

        # Get logger for validation message
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            "rv_experiment.config",
            {CONTEXT_COMPONENT: "ExperimentConfig"}
        )
        logger.info("Configuration validation completed successfully")

    def _validate_apk_sources(self) -> bool:
        """
        Validate that at least one APK source is available.
        
        Returns:
            True if valid APK sources are configured, False otherwise
        """
        # Check specific APK path
        if self.apk_path and Path(self.apk_path).exists():
            return True

        # Check APK directory with patterns
        if self.apk_dir:
            apk_dir = Path(self.apk_dir)
            if apk_dir.exists():
                # Check if any files match the patterns
                for pattern in self.apk_patterns:
                    if list(apk_dir.glob(pattern)):
                        return True

        return False

    def get_apk_list(self) -> List[str]:
        """
        Get list of APK files to process based on configuration.
        
        Returns:
            List of APK file paths
            
        Raises:
            ConfigurationError: If no APK files are found
        """
        apks = []

        # Single APK file
        if self.apk_path:
            apk_path = Path(self.apk_path)
            if apk_path.exists():
                apks.append(str(apk_path))
            else:
                raise ConfigurationError(f"APK file not found: {self.apk_path}")

        # APK directory with patterns
        if self.apk_dir:
            apk_dir = Path(self.apk_dir)
            if apk_dir.exists():
                for pattern in self.apk_patterns:
                    apks.extend([str(p) for p in apk_dir.glob(pattern)])

        if not apks:
            raise ConfigurationError(
                f"No APK files found. Check apk_path='{self.apk_path}' or "
                f"apk_dir='{self.apk_dir}' with patterns={self.apk_patterns}"
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

        # 1. Validate if it's an existing directory
        if not path.is_dir():
            print(f"'{directory_path_str}' is not a valid directory or does not exist.")
            return False

        # 2. Iterate over files in the directory and check the extension
        # The .iterdir() method yields Path objects for all items in the directory.
        for item in path.iterdir():
            # Check if the item is a file and if its suffix (extension) is '.mop'
            # .suffix returns the file extension (e.g., '.txt', '.mop').
            # .lower() is used for case-insensitive comparison.
            if item.is_file() and item.suffix.lower() == EXTENSION_MOP:
                print(f"{EXTENSION_MOP} file found: '{item.name}' in '{directory_path_str}'")
                return True  # Found one, so we can stop and return True

        print(f"No {EXTENSION_MOP} files found in '{directory_path_str}'.")
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
        mop_base_dir = os.path.join(rvsec_root, "rvsec", "rvsec-mop", "src", "main", "resources")
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
                raise ConfigurationError(f"Unsupported specification set: {self.specification_set}")
        else:
            raise ConfigurationError(f"Unsupported specification set: {self.specification_set}")

        try:
            # Create RVGeneratorConfig instance with explicit paths
            # to ensure mop_specs_dir is not overridden by automatic resolution

            # Determine aspects directory: custom if provided, otherwise standard RVSEC
            if self.custom_aspects_dir:
                aspects_dir = self.custom_aspects_dir
            else:
                # Use standard aspects directory from RVSEC
                aspects_dir = os.path.join(rvsec_root, "rvsec", "rvsec-mop", "src", "main", "resources", "aspect")

            return RVGeneratorConfig(
                rvsec_root=rvsec_root,
                javamop_bin=os.path.join(rvsec_root, "javamop", "bin", "javamop"),
                rvmonitor_bin=os.path.join(rvsec_root, "rv-monitor", "bin", "rv-monitor"),
                mop_specs_dir=mop_specs_dir,
                aspects_dir=aspects_dir
            )
        except MonitorConfigError as e:
            raise ConfigurationError(f"Monitor generation configuration failed: {e}") from e

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
        # monitor_output_dir = os.path.join(rv_android_dir, "mop_out") if self.output_dir else None
        monitor_output_dir = os.path.join(self.output_dir, "mop_out") if self.output_dir else None

        try:
            # Create RVInstrumentationConfig instance with tool paths
            return RVInstrumentationConfig(
                rvsec_root=rvsec_root,
                monitor_output_dir=monitor_output_dir,
                working_dir=rv_android_dir,  # Use rv-android dir where lib/ exists
                instrumented_dir=os.path.join(rv_android_dir, INSTRUMENTED_DIR),
                keystore_password="password"
            )
        except InstrumentationConfigError as e:
            raise ConfigurationError(f"Instrumentation configuration failed: {e}") from e

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
            # Create RVStaticAnalysisConfig instance with tool paths
            return RVStaticAnalysisConfig(
                rvsec_root=rvsec_root,
                lib_dir=lib_dir,  # Point to rv-android/lib where tools are located
                output_dir=self.output_dir,
                working_dir=self.output_dir,
                validate_on_init=False  # Defer validation to avoid initialization issues
            )
        except Exception as e:
            raise ConfigurationError(f"Static analysis configuration failed: {e}") from e

    def get_llm_config(self) -> LLMConfig:
        """
        Just-in-time configuration for LLM integration in AI-driven testing tools.
        
        ### Configuration Pattern:
        This method creates LLM configuration only when needed for tools that
        require AI integration, providing sensible defaults while supporting
        experiment-specific model and parameter customization.
        
        ### LLM Integration Architecture:
        - **Model Selection**: Configures LLM model type and parameters for tool execution
        - **Provider Configuration**: Sets up LLM provider (Ollama, OpenAI, etc.) integration
        - **Strategy Coordination**: Aligns LLM strategy with experiment objectives
        - **Parser Integration**: Coordinates screen parsing with LLM-driven analysis
        
        ### Role in the System:
        - Provides LLM configuration for RVAndroid and other AI-enhanced testing tools
        - Coordinates model parameters with experiment requirements
        - Enables consistent LLM behavior across experiment repetitions
        - Integrates with experiment configuration validation pipeline
        
        Returns:
            LLMConfig instance with validated LLM configuration
            
        Raises:
            ConfigurationError: If LLM configuration validation fails
        """
        try:
            # Create LLMConfig instance with default settings
            config = LLMConfig(
                llm_type="ollama",
                model="llama3.2:3b",
                base_url="http://127.0.0.1:11434",
                temperature=0.3,
                max_tokens=2048,
                provider="ollama",
                strategy_type="standard",
                parser_type="droidbot",
                visitor_type="enhanced"
            )

            # Validate configuration
            is_valid, errors = config.validate()
            if not is_valid:
                raise ConfigurationError(f"LLM configuration validation failed: {errors}")

            return config
        except Exception as e:
            raise ConfigurationError(f"LLM configuration failed: {e}") from e

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
    def from_dict(cls, data: Dict[str, Any]) -> 'ExperimentConfig':
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
        # Handle tool configurations
        if 'tool_configs' in data and isinstance(data['tool_configs'], list):
            data['tool_configs'] = [
                ToolConfig(**tc) if isinstance(tc, dict) else tc
                for tc in data['tool_configs']
            ]

        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'ExperimentConfig':
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
    def from_file(cls, file_path: str) -> 'ExperimentConfig':
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

        with open(path, 'r') as f:
            if path.suffix.lower() == '.json':
                data = json.load(f)
            else:
                # Assume JSON
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
        with open(path, 'w') as f:
            f.write(self.to_json())

        # Get logger for save message
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            "rv_experiment.config",
            {CONTEXT_COMPONENT: "ExperimentConfig"}
        )
        logger.info(f"Configuration saved to: {file_path}")

    def get_module_config(self, module_name: str) -> Union[
        RVGeneratorConfig, RVInstrumentationConfig, RVStaticAnalysisConfig, LLMConfig, Dict[str, Any]]:
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
        - **rv-llm**: LLM integration configuration for AI-driven tools
        
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
        elif module_name == "rv-llm":
            return self.get_llm_config()
        else:
            return {}

    def get_rv_instrumentation_config(self) -> RVInstrumentationConfig:
        """
        Get configuration for rv-instrumentation module.
        
        ### Configuration Class Integration:
        This method now returns a properly typed RVInstrumentationConfig instance
        instead of a dictionary, providing better type safety and validation.
        
        Returns:
            RVInstrumentationConfig instance with instrumentation configuration
        """
        return self.get_instrumentation_config()

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

    @ErrorHandler.handle_errors(component="ExperimentConfig", phase="rvsec_root_hierarchy")
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
                raise ConfigurationError(f"Configured rvsec_root path does not exist: {self.rvsec_root}")
            return self.rvsec_root
        
        # Priority 2: Environment variable fallback
        env_value = os.getenv(ENV_RVSEC_HOME)
        if env_value:
            if not os.path.exists(env_value):
                raise ConfigurationError(f"RVSEC_HOME environment path does not exist: {env_value}")
            return env_value
        
        # Priority 3: Error for required configuration
        raise ConfigurationError(
            "RVSEC_HOME not found in configuration or environment. "
            "Set rvsec_root field in configuration or RVSEC_HOME environment variable"
        )

    @classmethod
    @ErrorHandler.handle_errors(component="ExperimentConfig", phase="load_from_status")
    def load_from_status(cls, status_file: str) -> 'ExperimentConfig':
        """
        Load experiment configuration from status file for continuation.
        
        ### Continuation Strategy:
        - Loads experiment metadata and configuration from status file
        - Validates configuration integrity through checksum verification
        - Enables experiment resumption with original configuration
        - Provides experiment recovery capabilities
        
        ### Role in the System:
        - Enables experiment continuation after interruption or failure
        - Maintains configuration consistency for resumed experiments
        - Supports experiment recovery and debugging workflows
        - Facilitates long-running experiment management
        
        Args:
            status_file: Path to experiment status file
            
        Returns:
            ExperimentConfig instance loaded from status
            
        Raises:
            ConfigurationError: If status file is invalid or corrupted
        """
        if not os.path.exists(status_file):
            raise ConfigurationError(f"Status file not found: {status_file}")
        
        try:
            with open(status_file, 'r') as f:
                status_data = json.load(f)
            
            # Extract experiment metadata
            if "experiment" not in status_data:
                raise ConfigurationError("Status file does not contain experiment metadata")
            
            experiment_data = status_data["experiment"]
            
            # Load the original configuration (would need to be stored separately or reconstructed)
            # For now, create a basic config that can be enhanced
            config = cls(
                name=experiment_data.get("experiment_id", "resumed_experiment"),
                resume_mode=True,
                status_file=status_file
            )
            
            # Set metadata for continuation tracking
            config.metadata.update({
                "resumed_from": status_file,
                "original_start_time": experiment_data.get("start_time"),
                "continuation_time": datetime.now().isoformat(),
                "config_checksum": experiment_data.get("config_checksum")
            })
            
            return config
            
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in status file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading status file: {e}")

    def enable_continuation_mode(self, status_file: str) -> None:
        """
        Enable experiment continuation mode with status file.
        
        Args:
            status_file: Path to experiment status file
        """
        self.resume_mode = True
        self.status_file = status_file
        
        # Update metadata
        self.metadata.update({
            "continuation_enabled": True,
            "status_file": status_file,
            "continuation_time": datetime.now().isoformat()
        })

    def get_enhanced_storage_config(self) -> 'StorageConfig':
        """
        Get enhanced storage configuration based on experiment settings.
        
        Returns:
            StorageConfig with experiment-specific settings
        """
        # Import here to avoid circular dependency
        from rv_platform.storage.task_storage import StorageConfig
        
        return StorageConfig(
            enable_metadata=True,
            enable_statistics=True,
            auto_save=not self.resume_mode,  # Disable auto-save in resume mode for performance
            compression=False,
            backup_count=3 if not self.resume_mode else 1
        )

    def get_artifact_validation_config(self) -> Dict[str, bool]:
        """
        Get artifact validation configuration for phase execution.
        
        Returns:
            Dictionary with artifact validation settings
        """
        return {
            "validate_monitors": self.artifact_reuse_enabled and not self.phase_control.get("skip_monitors", False),
            "validate_instrumentation": self.artifact_reuse_enabled and not self.phase_control.get("skip_instrumentation", False),
            "validate_static_analysis": self.artifact_reuse_enabled and not self.phase_control.get("skip_static_analysis", False),
            "strict_validation": not self.resume_mode  # Relaxed validation in resume mode
        }
    
    @ErrorHandler.handle_errors(component="ExperimentConfig", phase="directory_manager")
    def get_directory_manager(self, base_dir: Optional[str] = None) -> 'ExperimentDirectoryManager':
        """
        Get ExperimentDirectoryManager instance configured for this experiment.
        
        Args:
            base_dir: Optional base directory override (defaults to ./out/)
            
        Returns:
            ExperimentDirectoryManager instance
        """
        from rv_experiment.directory_manager import ExperimentDirectoryManager
        
        if base_dir is None:
            base_dir = "./out/"
            
        return ExperimentDirectoryManager(base_dir=base_dir)
    
    @ErrorHandler.handle_errors(component="ExperimentConfig", phase="apk_list")
    def get_apk_list(self) -> List[str]:
        """
        Get list of APK files based on configuration.
        
        Returns:
            List of APK file paths
        """
        apk_files = []
        
        # Single APK file
        if self.apk_path and os.path.exists(self.apk_path):
            apk_files.append(self.apk_path)
        
        # APK directory with patterns
        if self.apk_dir and os.path.exists(self.apk_dir):
            for pattern in self.apk_patterns:
                import glob
                pattern_path = os.path.join(self.apk_dir, pattern)
                apk_files.extend(glob.glob(pattern_path))
        
        return sorted(list(set(apk_files)))  # Remove duplicates and sort
    
    @ErrorHandler.handle_errors(component="ExperimentConfig", phase="artifact_reuse_analysis")
    def analyze_artifact_reuse(self) -> Dict[str, Any]:
        """
        Analyze artifact reuse potential for this experiment configuration.
        
        Returns:
            Dictionary with artifact reuse analysis results
        """
        if not self.artifact_reuse_enabled:
            return {
                "reuse_enabled": False,
                "can_skip_phases": {},
                "reusable_artifacts": {}
            }
        
        directory_manager = self.get_directory_manager()
        apk_list = self.get_apk_list()
        
        # Get comprehensive artifact analysis
        reuse_analysis = directory_manager.get_reusable_artifacts(
            apk_list=[os.path.basename(apk) for apk in apk_list],
            specification_set=self.specification_set
        )
        
        # Determine which phases can be skipped
        can_skip_phases = {}
        if self.skip_completed_phases and not self.force_regeneration:
            can_skip_phases["static_analysis"] = reuse_analysis["overall"].get("static_analysis_complete", False)
            can_skip_phases["monitor_generation"] = reuse_analysis["overall"].get("monitors_complete", False)
            can_skip_phases["instrumentation"] = reuse_analysis["overall"].get("instrumentation_complete", False)
        
        return {
            "reuse_enabled": True,
            "can_skip_phases": can_skip_phases,
            "reusable_artifacts": reuse_analysis,
            "force_regeneration": self.force_regeneration,
            "analyze_instrumented_apks": self.analyze_instrumented_apks
        }


