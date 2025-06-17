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
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, TYPE_CHECKING

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


@dataclass
class ToolConfiguration:
    """
    Configuration for individual testing tools.
    
    ### Architectural Overview:
    This class encapsulates tool-specific configuration with support for variants
    and parameters using the modern tool specification DSL format. It provides
    clean serialization and factory-ready structure for DI containers.
    
    ### Key Features:
    - **Tool Specification DSL**: Support for tool:variant:variant@param=value format
    - **Parameter Management**: Type-safe parameter handling with validation
    - **Variant Support**: Multiple tool variants (e.g., llama:batch, droidbot:dfs_greedy)
    - **Factory Ready**: Designed for factory pattern instantiation
    
    ### Role in the System:
    - Encapsulates individual tool configuration and parameters
    - Provides serialization/deserialization for tool specifications
    - Enables tool variant selection and parameter customization
    - Supports factory-based tool creation with configuration injection
    """
    name: str
    variants: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeout_override: Optional[int] = None
    enabled: bool = True

    def __post_init__(self):
        """Validate tool configuration after initialization."""
        if not self.name:
            raise ValueError("Tool name cannot be empty")

        if not isinstance(self.variants, list):
            self.variants = [self.variants] if self.variants else []

        if not isinstance(self.parameters, dict):
            self.parameters = {}

    def to_spec_string(self) -> str:
        """
        Convert tool configuration to specification string format.
        
        Returns:
            Tool specification string (e.g., "tool:variant1:variant2@param1=value1,param2=value2")
        """
        spec = self.name

        if self.variants:
            spec += ":" + ":".join(self.variants)

        if self.parameters:
            params = ",".join([f"{k}={v}" for k, v in self.parameters.items()])
            spec += f"@{params}"

        return spec

    @classmethod
    def from_spec_string(cls, spec: str) -> 'ToolConfiguration':
        """
        Create tool configuration from specification string.
        
        Args:
            spec: Tool specification string
            
        Returns:
            ToolConfiguration instance
        """
        # Parse tool specification string
        parts = spec.split('@')
        tool_part = parts[0]
        params_part = parts[1] if len(parts) > 1 else ""

        # Parse tool name and variants
        tool_parts = tool_part.split(':')
        name = tool_parts[0]
        variants = tool_parts[1:] if len(tool_parts) > 1 else []

        # Parse parameters
        parameters = {}
        if params_part:
            for param in params_part.split(','):
                if '=' in param:
                    key, value = param.split('=', 1)
                    parameters[key.strip()] = value.strip()

        return cls(name=name, variants=variants, parameters=parameters)


@dataclass
class CLIExperimentConfig:
    """
    CLI-focused experiment configuration for Android testing orchestration.
    
    ### Architectural Overview:
    This class implements simplified configuration approach for CLI usage,
    providing direct parameter passing and factory-ready design. It focuses 
    on the streamlined 3-command CLI structure requirements.
    
    ### CLI Features:
    - **Simplified Structure**: Optimized for 3-command CLI (run, generate-config, list-tools)
    - **Tool Specification DSL**: Modern tool:variant@parameter format support
    - **Standard Directories**: Uses ./results/ for experiments, ./out/ for pre-processing
    - **Monitored Operations**: JCA crypto vs generic specification set support
    - **Factory Ready**: Designed for factory pattern instantiation
    
    ### Key Architectural Decisions:
    - **Direct Parameter Passing**: Simple parameter management without complex coordination
    - **DI Preparation**: Structure optimized for dependency injection containers
    - **Template Generation**: Intelligent template creation for different scenarios
    - **Specification Sets**: Support for different monitored operations categories
    
    ### Role in the System:
    - Primary configuration for CLI-driven experiments
    - Bridge between CLI arguments and experiment orchestration
    - Template generator for configuration examples
    - Factory input for component creation
    - Validation coordinator for CLI parameter validation
    """

    # Core experiment identification
    experiment_dir: str = f"./{RESULTS_DIR}/"
    experiment_id: Optional[str] = None

    # Tool configuration with modern specification format
    tools: List[Dict[str, Any]] = field(default_factory=list)
    timeout: int = DEFAULT_TIMEOUT
    repetitions: int = DEFAULT_REPETITIONS

    # APK configuration
    apk_path: Optional[str] = None
    apk_dir: str = f"./{DEFAULT_APKS_DIR}/"
    apk_patterns: List[str] = field(default_factory=lambda: DEFAULT_APK_PATTERNS.copy())

    # Processing configuration
    generate_monitors: bool = True
    instrument_apks: bool = True
    run_static_analysis: bool = True

    # Monitored operations specification set selection
    specification_set: str = DEFAULT_SPEC_SET  # Options: "jca", "generic", "custom"

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize configuration after creation with validation and defaults."""
        if not self.experiment_id:
            self.experiment_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    @ErrorHandler.handle_errors(
        component="CLIExperimentConfig",
        phase="validate",
    )
    def validate(self) -> None:
        """
        Comprehensive validation of simplified experiment configuration.
        
        ### Validation Strategy:
        - Tool specification format validation
        - APK source validation with intelligent fallbacks
        - Directory structure validation
        - Monitored operations specification validation
        - Parameter range and type validation
        
        Raises:
            ValueError: If configuration parameters are invalid
            ConfigurationError: If configuration structure is inconsistent
        """
        # Validate basic parameters
        if not self.experiment_id:
            raise ValueError("Experiment ID cannot be empty")

        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")

        if self.repetitions <= 0:
            raise ValueError("Repetitions must be positive")

        # Validate tools configuration
        if not self.tools:
            raise ValueError("At least one tool must be specified")

        for tool in self.tools:
            if not isinstance(tool, dict):
                raise ValueError(f"Tool specification must be a dictionary: {tool}")

            if "name" not in tool:
                raise ValueError(f"Tool specification must have 'name' field: {tool}")

            # Validate tool variants if present
            if "variants" in tool and not isinstance(tool["variants"], list):
                raise ValueError(f"Tool variants must be a list: {tool}")

            # Validate tool parameters if present
            if "parameters" in tool and not isinstance(tool["parameters"], dict):
                raise ValueError(f"Tool parameters must be a dictionary: {tool}")

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

        # Validate experiment directory
        exp_dir = Path(self.experiment_dir)
        if not exp_dir.parent.exists():
            raise ValueError(f"Parent directory for experiment does not exist: {exp_dir.parent}")

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

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary format for serialization.
        
        Returns:
            Configuration as dictionary
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CLIExperimentConfig':
        """
        Create configuration from dictionary.
        
        Args:
            data: Configuration dictionary
            
        Returns:
            CLIExperimentConfig instance
            
        Raises:
            ValueError: If dictionary contains invalid data
        """
        try:
            # Handle legacy format conversion if needed
            if "tools" in data and isinstance(data["tools"], list):
                # Convert string tool names to dict format if needed
                converted_tools = []
                for tool in data["tools"]:
                    if isinstance(tool, str):
                        converted_tools.append({"name": tool, "variants": [], "parameters": {}})
                    elif isinstance(tool, dict):
                        converted_tools.append(tool)
                    else:
                        raise ValueError(f"Invalid tool specification: {tool}")
                data["tools"] = converted_tools

            return cls(**data)

        except TypeError as e:
            raise ValueError(f"Invalid configuration data: {e}")

    @classmethod
    @ErrorHandler.handle_errors(
        component="CLIExperimentConfig",
        phase="create_basic_template",
    )
    def create_basic_template(cls) -> 'CLIExperimentConfig':
        """
        Create a basic configuration template for standard experiments.
        
        ### Template Design:
        This template provides sensible defaults for typical experiment scenarios
        with commonly used tools and standard monitored operations settings.
        
        Returns:
            CLIExperimentConfig with basic template configuration
        """
        return cls(
            experiment_dir=f"./{RESULTS_DIR}/",
            tools=[
                {"name": "monkey", "variants": [], "parameters": {}},
                {"name": "droidbot", "variants": ["dfs_greedy"], "parameters": {"count": 1000}}
            ],
            timeout=DEFAULT_TIMEOUT,
            repetitions=DEFAULT_REPETITIONS,
            apk_dir=f"./{DEFAULT_APKS_DIR}/",
            apk_patterns=DEFAULT_APK_PATTERNS.copy(),
            generate_monitors=True,
            instrument_apks=True,
            run_static_analysis=True,
            specification_set=DEFAULT_SPEC_SET,  # Default to JCA crypto monitored operations
            metadata={
                "template_type": "basic",
                "description": "Basic experiment template with standard tools and JCA monitored operations",
                "target_audience": "general_testing"
            }
        )

    @classmethod
    @ErrorHandler.handle_errors(
        component="CLIExperimentConfig",
        phase="create_advanced_template",
    )
    def create_advanced_template(cls) -> 'CLIExperimentConfig':
        """
        Create an advanced configuration template for comprehensive experiments.
        
        ### Template Design:
        This template demonstrates advanced tool configurations, multiple variants,
        and comprehensive monitored operations coverage for thorough testing scenarios.
        
        Returns:
            CLIExperimentConfig with advanced template configuration
        """
        return cls(
            experiment_dir=f"./{RESULTS_DIR}/",
            tools=[
                {"name": "monkey", "variants": ["fixed_seed"], "parameters": {"seed": 42, "throttle": 100}},
                {"name": "droidbot", "variants": ["dfs_greedy"], "parameters": {"count": 2000, "timeout": 600}},
                {"name": "ape", "variants": [], "parameters": {"running_minutes": 10}},
                {"name": "rvandroid", "variants": ["llama", "standard"],
                 "parameters": {"temperature": 0.3, "max_tokens": 2048}}
            ],
            timeout=600,
            repetitions=3,
            apk_dir="./apks_examples/",
            apk_patterns=["*.apk", "!*test*.apk", "!*debug*.apk"],
            generate_monitors=True,
            instrument_apks=True,
            run_static_analysis=True,
            specification_set="generic",  # Generic programming patterns monitored operations
            metadata={
                "template_type": "advanced",
                "description": "Advanced experiment template with multiple tools and comprehensive monitored operations",
                "target_audience": "research_comprehensive_testing",
                "execution_time_estimate": "2-4 hours",
                "resource_requirements": "high"
            }
        )

    @classmethod
    @ErrorHandler.handle_errors(
        component="CLIExperimentConfig",
        phase="create_llm_template",
    )
    def create_llm_template(cls) -> 'CLIExperimentConfig':
        """
        Create an LLM-focused configuration template for AI-driven testing.
        
        ### Template Design:
        This template focuses on LLM-driven testing capabilities with RVAndroid,
        showcasing different model configurations, prompt strategies, and
        monitored operations specifically designed for AI-guided exploration.
        
        Returns:
            CLIExperimentConfig with LLM-focused template configuration
        """
        return cls(
            experiment_dir=f"./{RESULTS_DIR}/",
            tools=[
                # LLM-driven testing with different strategies
                {
                    "name": "rvandroid",
                    "variants": ["llama", "standard"],
                    "parameters": {
                        "temperature": 0.2,
                        "max_tokens": 2048,
                        "model": "llama3",
                        "provider": "ollama"
                    }
                },
                {
                    "name": "rvandroid",
                    "variants": ["llama", "batch"],
                    "parameters": {
                        "temperature": 0.3,
                        "max_tokens": 2048,
                        "batch_size": 3,
                        "model": "llama3",
                        "provider": "ollama"
                    }
                },
                # Baseline comparison tool
                {"name": "monkey", "variants": [], "parameters": {}}
            ],
            timeout=900,  # Longer timeout for LLM processing
            repetitions=2,
            apk_dir=f"./{DEFAULT_APKS_DIR}/",
            apk_patterns=DEFAULT_APK_PATTERNS.copy(),
            generate_monitors=True,
            instrument_apks=True,
            run_static_analysis=True,
            specification_set="jca",  # Focus on crypto API monitored operations for LLM
            metadata={
                "template_type": "llm_focused",
                "description": "LLM-driven testing template with RVAndroid and crypto monitored operations",
                "target_audience": "ai_testing_research",
                "llm_requirements": "Ollama with Llama3 model",
                "execution_time_estimate": "1-3 hours depending on LLM performance",
                "monitored_operations_focus": "JCA cryptography API usage patterns"
            }
        )


@dataclass
class ExperimentConfig:
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
    experiment_id: Optional[str] = None

    # Tool configuration
    tool_configs: List[ToolConfiguration] = field(default_factory=list)

    # Execution parameters
    repetitions: int = 1
    timeouts: List[int] = field(default_factory=lambda: [300])
    no_window: bool = True

    # Processing phases
    generate_monitors: bool = True
    instrument_apks: bool = True
    run_static_analysis: bool = True

    # Monitored operations specification set
    specification_set: str = DEFAULT_SPEC_SET  # "jca", "generic", "custom"
    custom_specs_dir: Optional[str] = None  # Custom specification directory for "custom" specification set
    custom_aspects_dir: Optional[str] = None  # Custom AspectJ aspects directory (optional)

    # APK sources
    apk_path: Optional[str] = None
    apk_dir: str = f"./{DEFAULT_APKS_DIR}/"
    apk_patterns: List[str] = field(default_factory=lambda: DEFAULT_APK_PATTERNS.copy())

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None

    def __post_init__(self):
        """Initialize configuration after creation with defaults and validation."""
        if not self.name:
            self.name = f"experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if not self.output_dir:
            self.output_dir = get_experiment_dir(self.name)

        if not self.experiment_id:
            self.experiment_id = self.name

        if not self.created_at:
            self.created_at = datetime.now().isoformat()

        # Initialize logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "rv_experiment.config",
            {CONTEXT_COMPONENT: "ExperimentConfig"}
        )

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

        self.logger.info("Configuration validation completed successfully")

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
        Validates if the given directory_path_str is an existing directory
        and contains at least one file with the .mop extension.

        Args:
            directory_path_str (str): The path to the directory to be checked.

        Returns:
            bool: True if it's a valid directory containing at least one .mop file,
                  False otherwise.
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
        rvsec_root = os.getenv(ENV_RVSEC_HOME)
        if not rvsec_root:
            raise ConfigurationError(
                f"{ENV_RVSEC_HOME} environment variable not set. "
                "This is required for monitored operations specification location."
            )

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
        # Get RVSEC root directory for proper path resolution
        rvsec_root = os.getenv("RVSEC_HOME")
        if not rvsec_root:
            raise ConfigurationError(
                "RVSEC_HOME environment variable not set. "
                "This is required for instrumentation configuration."
            )

        # Determine monitor output directory from experiment
        monitor_output_dir = os.path.join(self.output_dir, "mop_out") if self.output_dir else None

        # Use rv-android directory as working directory (where lib/ and tools are)
        rv_android_dir = os.path.join(rvsec_root, "rv-android")

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

    def get_static_analysis_config(self) -> RVStaticAnalysisConfig:
        """
        Just-in-time configuration for static analysis.
        
        ### Configuration Pattern:
        This method creates static analysis configuration only when needed,
        providing defaults while allowing experiment-specific customization
        through parameter specification.
        
        ### Implementation:
        Returns a typed RVStaticAnalysisConfig instance that provides type safety,
        validation, and integration with the configuration architecture.
        
        Returns:
            RVStaticAnalysisConfig instance with static analysis configuration
            
        Raises:
            ConfigurationError: If static analysis configuration fails
        """
        rvsec_root = os.getenv("RVSEC_HOME")
        if not rvsec_root:
            raise ConfigurationError(
                "RVSEC_HOME environment variable not set. "
                "This is required for static analysis configuration."
            )

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
        Just-in-time configuration for LLM integration.
        
        ### Configuration Pattern:
        This method creates LLM configuration only when needed for tools that
        require AI integration, providing defaults while supporting
        experiment-specific model and parameter selection.
        
        ### Implementation:
        Returns a typed LLMConfig instance that provides type safety,
        validation, and integration with the configuration architecture.
        
        Returns:
            LLMConfig instance with LLM configuration
            
        Raises:
            ConfigurationError: If LLM configuration fails validation
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
        Convert configuration to dictionary format for serialization.
        
        Returns:
            Configuration as dictionary
        """
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """
        Convert configuration to JSON format.
        
        Args:
            indent: JSON indentation level
            
        Returns:
            Configuration as JSON string
        """
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExperimentConfig':
        """
        Create configuration from dictionary.
        
        Args:
            data: Configuration dictionary
            
        Returns:
            ExperimentConfig instance
        """
        # Handle tool configurations
        if 'tool_configs' in data and isinstance(data['tool_configs'], list):
            data['tool_configs'] = [
                ToolConfiguration(**tc) if isinstance(tc, dict) else tc
                for tc in data['tool_configs']
            ]

        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'ExperimentConfig':
        """
        Create configuration from JSON string.
        
        Args:
            json_str: JSON configuration string
            
        Returns:
            ExperimentConfig instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, file_path: str) -> 'ExperimentConfig':
        """
        Load configuration from file.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            ExperimentConfig instance
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
        Save configuration to file.
        
        Args:
            file_path: Path to save configuration
        """
        path = Path(file_path)

        # Create parent directory if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Save configuration as JSON
        with open(path, 'w') as f:
            f.write(self.to_json())

        self.logger.info(f"Configuration saved to: {file_path}")

    def get_module_config(self, module_name: str) -> Union[
        RVGeneratorConfig, RVInstrumentationConfig, RVStaticAnalysisConfig, LLMConfig, Dict[str, Any]]:
        """
        Get module-specific configuration based on the module name.
        
        ### Configuration Class Integration:
        This method now returns properly typed configuration class instances
        instead of dictionaries, providing better type safety and validation.
        
        Args:
            module_name: Name of the module to get configuration for
            
        Returns:
            Configuration class instance specific to the requested module
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
        Get the instrumented APKs directory path.
        
        Returns:
            Path to instrumented APKs directory
        """
        return INSTRUMENTED_DIR

    def get_timestamp_string(self) -> str:
        """
        Get timestamp string for experiment identification.
        
        Returns:
            Timestamp string in format YYYYMMDD_HHMMSS
        """
        return datetime.now().strftime("%Y%m%d_%H%M%S")


# Backward compatibility alias for migration
SimpleExperimentConfig = CLIExperimentConfig
