"""
Experiment Configuration Management

### Architectural Overview:
This module provides comprehensive configuration management for RV-Android experiments,
replacing the centralized settings.py approach with a modern, modular configuration
system that respects module independence while enabling coordinated experiment execution.

### Key Architectural Decisions:
- **Typed Configuration**: Uses dataclasses with type hints for robust configuration validation
- **Module Coordination**: Coordinates configuration across multiple modules while maintaining their independence
- **Validation Framework**: Implements comprehensive validation with clear error messages
- **Serialization Support**: Supports multiple configuration formats (JSON, YAML, TOML)
- **Environment Integration**: Seamlessly integrates with environment variables and CLI arguments

### Role in the System:
- Centralizes experiment-specific configuration while respecting module boundaries
- Provides type-safe configuration management with validation
- Coordinates configuration distribution to dependent modules
- Supports multiple configuration sources and formats
- Enables configuration reuse and template generation

### Design Patterns:
- **Builder Pattern**: Fluent configuration construction and modification
- **Factory Pattern**: Configuration creation from multiple sources
- **Validation Pattern**: Comprehensive configuration validation with clear error reporting
- **Serialization Pattern**: Multi-format configuration serialization support
"""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import tempfile

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.exceptions import ConfigurationError


@dataclass
class ToolConfiguration:
    """
    Configuration for individual testing tools.
    
    ### Architectural Decisions:
    - Encapsulates tool-specific configuration parameters
    - Supports tool variants and custom parameters
    - Enables consistent tool configuration across experiments
    - Provides validation for tool-specific requirements
    
    ### Role in the System:
    - Defines configuration structure for testing tools
    - Supports tool customization and variant selection
    - Enables tool parameter validation and defaults
    - Facilitates tool configuration serialization
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
class ApplicationConfiguration:
    """
    Configuration for target applications in experiments.
    
    ### Architectural Decisions:
    - Encapsulates application-specific configuration and metadata
    - Supports flexible application discovery and selection
    - Enables application-specific experiment parameters
    - Provides validation for application requirements
    
    ### Role in the System:
    - Defines configuration structure for target applications
    - Supports application discovery and validation
    - Enables application-specific experiment customization
    - Facilitates application metadata management
    """
    path: Optional[str] = None
    package_name: Optional[str] = None
    name: Optional[str] = None
    directory: Optional[str] = None
    patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """
        Initialize application configuration after creation.
        
        Note: Validation is deferred to get_applications() method to allow
        empty initialization for default configuration that will be populated later.
        """
        pass  # Validation moved to get_applications() method
    
    def get_applications(self) -> List[str]:
        """
        Get list of application paths based on configuration.
        
        Returns:
            List of application file paths
            
        Raises:
            ValueError: If no applications are configured or found
        """
        # Validate configuration when actually used
        if not any([self.path, self.directory, self.patterns]):
            raise ConfigurationError("Must specify at least one: path, directory, or patterns")
        
        applications = []
        
        if self.path and Path(self.path).exists():
            applications.append(self.path)
        
        if self.directory and Path(self.directory).exists():
            directory_path = Path(self.directory)
            for pattern in self.patterns or ["*.apk"]:
                applications.extend([str(p) for p in directory_path.glob(pattern)])
        
        # Apply exclude patterns
        if self.exclude_patterns:
            filtered_apps = []
            for app in applications:
                app_path = Path(app)
                excluded = False
                for exclude_pattern in self.exclude_patterns:
                    if app_path.match(exclude_pattern):
                        excluded = True
                        break
                if not excluded:
                    filtered_apps.append(app)
            applications = filtered_apps
        
        return applications


@dataclass
class ExecutionConfiguration:
    """
    Configuration for experiment execution parameters.
    
    ### Architectural Decisions:
    - Centralizes execution-specific configuration parameters
    - Supports flexible execution modes and resource management
    - Enables execution optimization and parallelization
    - Provides validation for execution constraints
    
    ### Role in the System:
    - Defines execution behavior and resource allocation
    - Supports execution mode selection and optimization
    - Enables execution monitoring and control
    - Facilitates execution parameter validation
    """
    repetitions: int = 1
    timeouts: List[int] = field(default_factory=lambda: [300])
    no_window: bool = True
    parallel_execution: bool = False
    max_parallel_tasks: int = 2
    execution_delay: int = 0
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate execution configuration after initialization."""
        if self.repetitions < 1:
            raise ValueError("Repetitions must be at least 1")
        
        if not self.timeouts or any(t <= 0 for t in self.timeouts):
            raise ValueError("All timeouts must be positive")
        
        if self.max_parallel_tasks < 1:
            raise ValueError("Max parallel tasks must be at least 1")


@dataclass
class ProcessingConfiguration:
    """
    Configuration for experiment processing phases.
    
    ### Architectural Decisions:
    - Controls which processing phases are enabled
    - Supports selective processing for development and testing
    - Enables processing phase customization and optimization
    - Provides validation for processing dependencies
    
    ### Role in the System:
    - Controls experiment processing pipeline
    - Supports processing phase selection and configuration
    - Enables processing optimization and customization
    - Facilitates processing phase validation
    """
    generate_monitors: bool = True
    instrument: bool = True
    static_analysis: bool = True
    skip_experiment: bool = False
    process_results: bool = True
    generate_reports: bool = True
    
    def validate_dependencies(self):
        """Validate processing phase dependencies."""
        if self.generate_reports and not self.process_results:
            raise ValueError("Cannot generate reports without processing results")


@dataclass
class ExperimentConfiguration:
    """
    Comprehensive configuration for RV-Android experiments.
    
    ### Architectural Overview:
    This class serves as the central configuration coordinator for RV-Android experiments,
    replacing the monolithic settings.py approach with a modern, modular configuration
    system that maintains module independence while enabling coordinated experiment execution.
    
    ### Key Architectural Decisions:
    - **Modular Design**: Separates configuration concerns into logical groups
    - **Type Safety**: Uses dataclasses with type hints for robust validation
    - **Module Coordination**: Coordinates configuration across modules without violating independence
    - **Validation Framework**: Comprehensive validation with clear error messages
    - **Serialization Support**: Multi-format configuration serialization
    
    ### Role in the System:
    - Central coordinator for experiment-specific configuration
    - Provides type-safe configuration management and validation
    - Coordinates configuration distribution to dependent modules
    - Supports configuration reuse and template generation
    - Enables flexible experiment setup and customization
    
    ### Integration Points:
    - Integrates with CLI for argument-based configuration
    - Coordinates with module-specific configuration classes
    - Interfaces with environment variables and configuration files
    - Supports configuration validation and error reporting
    """
    
    # Basic experiment metadata
    name: str = ""
    description: str = ""
    output_dir: str = ""
    experiment_id: Optional[str] = None
    
    # Tool configuration
    tools: List[str] = field(default_factory=lambda: ["monkey"])
    tool_configs: List[ToolConfiguration] = field(default_factory=list)
    
    # Application configuration
    applications: ApplicationConfiguration = field(default_factory=ApplicationConfiguration)
    
    # Execution configuration
    execution: ExecutionConfiguration = field(default_factory=ExecutionConfiguration)
    
    # Processing configuration
    processing: ProcessingConfiguration = field(default_factory=ProcessingConfiguration)
    
    # Module-specific configurations
    module_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    
    def __post_init__(self):
        """Initialize configuration after creation."""
        if not self.name:
            self.name = f"experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        if not self.output_dir:
            self.output_dir = f"./results/{self.name}"
            
        if not self.experiment_id:
            self.experiment_id = self.name
            
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        
        # Initialize error handling and logging first
        self.error_handler = ErrorHandler.get_instance()
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "rv_experiment.config",
            {CONTEXT_COMPONENT: "ExperimentConfiguration"}
        )
        
        # Create tool configurations if not provided
        if not self.tool_configs and self.tools:
            self.tool_configs = [
                ToolConfiguration(name=tool) for tool in self.tools
            ]
        
        # Configure default module settings for standard operation
        self.configure_default_modules()
    
    # Backward compatibility properties for old settings.py usage
    @property
    def repetitions(self) -> int:
        """Backward compatibility property for repetitions."""
        return self.execution.repetitions
    
    @repetitions.setter
    def repetitions(self, value: int):
        """Backward compatibility setter for repetitions."""
        self.execution.repetitions = value
    
    @property
    def timeouts(self) -> List[int]:
        """Backward compatibility property for timeouts."""
        return self.execution.timeouts
    
    @timeouts.setter
    def timeouts(self, value: List[int]):
        """Backward compatibility setter for timeouts."""
        self.execution.timeouts = value
    
    @property
    def no_window(self) -> bool:
        """Backward compatibility property for no_window."""
        return self.execution.no_window
    
    @no_window.setter
    def no_window(self, value: bool):
        """Backward compatibility setter for no_window."""
        self.execution.no_window = value
    
    @property
    def generate_monitors(self) -> bool:
        """Backward compatibility property for generate_monitors."""
        return self.processing.generate_monitors
    
    @generate_monitors.setter
    def generate_monitors(self, value: bool):
        """Backward compatibility setter for generate_monitors."""
        self.processing.generate_monitors = value
    
    @property
    def instrument(self) -> bool:
        """Backward compatibility property for instrument."""
        return self.processing.instrument
    
    @instrument.setter
    def instrument(self, value: bool):
        """Backward compatibility setter for instrument."""
        self.processing.instrument = value
    
    @property
    def static_analysis(self) -> bool:
        """Backward compatibility property for static_analysis."""
        return self.processing.static_analysis
    
    @static_analysis.setter
    def static_analysis(self, value: bool):
        """Backward compatibility setter for static_analysis."""
        self.processing.static_analysis = value
    
    @property
    def parallel_execution(self) -> bool:
        """Property for parallel execution."""
        return self.execution.parallel_execution
    
    @parallel_execution.setter
    def parallel_execution(self, value: bool):
        """Setter for parallel execution."""
        self.execution.parallel_execution = value
    
    
    def validate(self) -> None:
        """
        Comprehensive validation of experiment configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        try:
            # Validate basic configuration
            if not self.name:
                raise ValueError("Experiment name cannot be empty")
            
            if not self.tools and not self.tool_configs:
                raise ValueError("At least one tool must be specified")
            
            # Validate tool configurations
            for tool_config in self.tool_configs:
                if not tool_config.name:
                    raise ValueError("Tool configuration must have a name")
            
            # Validate execution configuration
            self.execution.__post_init__()
            
            # Validate processing configuration
            self.processing.validate_dependencies()
            
            # Validate applications configuration
            self.applications.__post_init__()
            
            # Validate output directory
            if self.output_dir:
                output_path = Path(self.output_dir)
                if not output_path.parent.exists():
                    raise ValueError(f"Parent directory for output does not exist: {output_path.parent}")
            
            self.logger.info("Configuration validation completed successfully")
            
        except Exception as e:
            self.error_handler.handle_error(e, {
                "component": "ExperimentConfiguration",
                "operation": "validate",
                "experiment_name": self.name
            })
            raise
    
    def get_module_config(self, module_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific module.
        
        Args:
            module_name: Name of the module
            
        Returns:
            Module-specific configuration dictionary
        """
        return self.module_configs.get(module_name, {})
    
    def set_module_config(self, module_name: str, config: Dict[str, Any]) -> None:
        """
        Set configuration for a specific module.
        
        Args:
            module_name: Name of the module
            config: Module configuration dictionary
        """
        self.module_configs[module_name] = config
        self.logger.debug(f"Updated configuration for module: {module_name}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary format.
        
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
    
    def to_yaml(self) -> str:
        """
        Convert configuration to YAML format.
        
        Returns:
            Configuration as YAML string
        """
        try:
            import yaml
            return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)
        except ImportError:
            raise ValueError("PyYAML is required for YAML export")
    
    def to_toml(self) -> str:
        """
        Convert configuration to TOML format.
        
        Returns:
            Configuration as TOML string
        """
        try:
            import toml
            return toml.dumps(self.to_dict())
        except ImportError:
            raise ValueError("toml is required for TOML export")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExperimentConfiguration':
        """
        Create configuration from dictionary.
        
        Args:
            data: Configuration dictionary
            
        Returns:
            ExperimentConfiguration instance
        """
        # Handle nested configurations
        if 'applications' in data and isinstance(data['applications'], dict):
            data['applications'] = ApplicationConfiguration(**data['applications'])
        
        if 'execution' in data and isinstance(data['execution'], dict):
            data['execution'] = ExecutionConfiguration(**data['execution'])
        
        if 'processing' in data and isinstance(data['processing'], dict):
            data['processing'] = ProcessingConfiguration(**data['processing'])
        
        if 'tool_configs' in data and isinstance(data['tool_configs'], list):
            data['tool_configs'] = [
                ToolConfiguration(**tc) if isinstance(tc, dict) else tc
                for tc in data['tool_configs']
            ]
        
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ExperimentConfiguration':
        """
        Create configuration from JSON string.
        
        Args:
            json_str: JSON configuration string
            
        Returns:
            ExperimentConfiguration instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def from_file(cls, file_path: str) -> 'ExperimentConfiguration':
        """
        Load configuration from file.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            ExperimentConfiguration instance
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        with open(path, 'r') as f:
            if path.suffix.lower() == '.json':
                data = json.load(f)
            elif path.suffix.lower() in ['.yml', '.yaml']:
                import yaml
                data = yaml.safe_load(f)
            elif path.suffix.lower() == '.toml':
                import toml
                data = toml.load(f)
            else:
                # Assume JSON
                data = json.load(f)
        
        return cls.from_dict(data)
    
    def save_to_file(self, file_path: str, format: Optional[str] = None) -> None:
        """
        Save configuration to file.
        
        Args:
            file_path: Path to save configuration
            format: Format to use (json, yaml, toml) - auto-detected from extension if not provided
        """
        path = Path(file_path)
        
        # Auto-detect format from extension
        if not format:
            if path.suffix.lower() == '.json':
                format = 'json'
            elif path.suffix.lower() in ['.yml', '.yaml']:
                format = 'yaml'
            elif path.suffix.lower() == '.toml':
                format = 'toml'
            else:
                format = 'json'  # Default to JSON
        
        # Create parent directory if needed
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save configuration
        with open(path, 'w') as f:
            if format == 'json':
                f.write(self.to_json())
            elif format == 'yaml':
                f.write(self.to_yaml())
            elif format == 'toml':
                f.write(self.to_toml())
            else:
                raise ValueError(f"Unsupported format: {format}")
        
        self.logger.info(f"Configuration saved to: {file_path}")
    
    @classmethod
    def create_sample_configuration(cls) -> 'ExperimentConfiguration':
        """
        Create a comprehensive sample configuration for documentation and testing.
        
        Returns:
            Sample ExperimentConfiguration instance
        """
        return cls(
            name="sample_experiment",
            description="Sample experiment configuration showing all available options",
            output_dir="./results/sample_experiment",
            tools=["monkey", "droidbot", "rvandroid"],
            tool_configs=[
                ToolConfiguration(
                    name="monkey",
                    variants=["fixed_seed"],
                    parameters={"seed": 42, "throttle": 100}
                ),
                ToolConfiguration(
                    name="droidbot",
                    variants=["dfs_greedy"],
                    parameters={"count": 1000}
                ),
                ToolConfiguration(
                    name="rvandroid",
                    variants=["llama", "batch"],
                    parameters={"temperature": 0.3, "model": "llama3"}
                )
            ],
            applications=ApplicationConfiguration(
                directory="./apks",
                patterns=["*.apk"],
                exclude_patterns=["*test*.apk", "*debug*.apk"]
            ),
            execution=ExecutionConfiguration(
                repetitions=3,
                timeouts=[300, 600, 900],
                no_window=True,
                parallel_execution=False,
                max_parallel_tasks=2
            ),
            processing=ProcessingConfiguration(
                generate_monitors=True,
                instrument=True,
                static_analysis=True,
                skip_experiment=False,
                process_results=True,
                generate_reports=True
            ),
            module_configs={
                "rv-monitor-generator": {
                    "javamop_path": "/path/to/javamop.jar",
                    "timeout": 300
                },
                "rv-instrumentation": {
                    "enable_coverage": True,
                    "instrumentation_level": "method"
                },
                "rv-static-analysis": {
                    "tools": ["gator", "gesda", "reach"],
                    "timeout": 600
                }
            },
            metadata={
                "author": "RV-Android Team",
                "version": "1.0",
                "tags": ["sample", "comprehensive", "documentation"]
            }
        )


    def get_instrumented_dir(self) -> str:
        """Get instrumented directory path."""
        return self.get_module_config("rv-instrumentation").get(
            "instrumented_dir", 
            os.path.join(self.output_dir, "instrumented")
        )
    
    def get_timestamp_string(self) -> str:
        """Get formatted timestamp string."""
        if self.created_at:
            return self.created_at.replace(':', '').replace('-', '').replace('T', '_').split('.')[0]
        return datetime.now().strftime('%Y%m%d_%H%M%S')
    
    @ErrorHandler.handle_errors(component="ExperimentConfiguration", operation="get_rv_generator_config")
    def get_rv_generator_config(self) -> 'RVGeneratorConfig':
        """
        Create RVGeneratorConfig instance from experiment configuration.
        
        ### Architectural Decisions:
        This method implements the configuration coordination pattern by mapping
        experiment-level configuration to module-specific configuration instances.
        It provides intelligent defaults while allowing explicit overrides through
        the module_configs system.
        
        ### Configuration Priority (highest to lowest):
        1. Explicit module configuration parameters (module_configs["rv-monitor-generator"])
        2. RVSEC_HOME environment variable for automatic path discovery
        3. Default configuration error if no valid source is available
        
        ### Role in the System:
        - Acts as the bridge between experiment coordination and module independence
        - Ensures module configuration consistency across experiment execution
        - Provides validation through the RVGeneratorConfig constructor
        - Enables flexible deployment scenarios while maintaining defaults
        
        Returns:
            RVGeneratorConfig: Validated configuration instance for monitor generation
            
        Raises:
            ImportError: If rv-monitor-generator module is not available
            ConfigurationError: If configuration validation fails
        """
        try:
            from rv_monitor_generator.config import RVGeneratorConfig
        except ImportError:
            raise ConfigurationError(
                "rv-monitor-generator module not available. "
                "Ensure the module is properly installed and accessible."
            )
        
        # Get module-specific configuration with intelligent defaults
        module_config = self.get_module_config("rv-monitor-generator")
        
        # Extract configuration parameters with fallback to environment
        rvsec_root = module_config.get("rvsec_root") or os.getenv("RVSEC_HOME")
        javamop_bin = module_config.get("javamop_bin")
        rvmonitor_bin = module_config.get("rvmonitor_bin")
        mop_specs_dir = module_config.get("mop_specs_dir")
        aspects_dir = module_config.get("aspects_dir")
        
        # Create and return validated configuration instance
        return RVGeneratorConfig(
            rvsec_root=rvsec_root,
            javamop_bin=javamop_bin,
            rvmonitor_bin=rvmonitor_bin,
            mop_specs_dir=mop_specs_dir,
            aspects_dir=aspects_dir
        )
    
    @ErrorHandler.handle_errors(component="ExperimentConfiguration", operation="get_rv_instrumentation_config")
    def get_rv_instrumentation_config(self) -> 'InstrumentationConfig':
        """
        Create InstrumentationConfig instance from experiment configuration.
        
        ### Architectural Decisions:
        This method coordinates APK instrumentation configuration by mapping
        experiment-level settings to instrumentation-specific parameters.
        It automatically derives input/output paths from application configuration
        and experiment directory structure.
        
        ### Configuration Mapping Strategy:
        - Input directory: First application from applications configuration
        - Output directory: Experiment-specific instrumented directory
        - Monitor integration: References monitor generation output
        - Processing options: Maps from experiment processing configuration
        
        ### Role in the System:
        - Links application discovery with instrumentation processing
        - Ensures consistent directory structure across experiment phases
        - Coordinates monitor integration with APK instrumentation
        - Provides instrumentation-specific configuration validation
        
        Returns:
            InstrumentationConfig: Validated configuration for APK instrumentation
            
        Raises:
            ImportError: If rv-instrumentation module is not available
            ValueError: If no applications are configured for instrumentation
        """
        try:
            from rv_instrumentation.config import InstrumentationConfig
        except ImportError:
            raise ConfigurationError(
                "rv-instrumentation module not available. "
                "Ensure the module is properly installed and accessible."
            )
        
        # Get module-specific configuration
        module_config = self.get_module_config("rv-instrumentation")
        
        # Determine input sources from application configuration
        applications = self.applications.get_applications()
        if not applications:
            raise ConfigurationError(
                "No applications configured for instrumentation. "
                "Specify applications through path, directory, or patterns."
            )
        
        # Map experiment configuration to instrumentation parameters
        input_dir = module_config.get("input_dir")
        if not input_dir:
            # Use directory from first application or parent directory
            first_app = Path(applications[0])
            input_dir = str(first_app.parent if first_app.is_file() else first_app)
        
        output_dir = module_config.get("output_dir", self.get_instrumented_dir())
        monitor_output_dir = module_config.get("monitor_output_dir")
        
        # Create configuration instance with coordinated parameters
        return InstrumentationConfig(
            input_dir=input_dir,
            output_dir=output_dir,
            monitor_output_dir=monitor_output_dir,
            enable_coverage=module_config.get("enable_coverage", True),
            instrumentation_level=module_config.get("instrumentation_level", "method"),
            keystore_path=module_config.get("keystore_path"),
            keystore_password=module_config.get("keystore_password", "password")
        )
    
    @ErrorHandler.handle_errors(component="ExperimentConfiguration", operation="get_rv_static_analysis_config")
    def get_rv_static_analysis_config(self) -> 'StaticAnalysisConfig':
        """
        Create StaticAnalysisConfig instance from experiment configuration.
        
        ### Architectural Decisions:
        This method coordinates static analysis configuration by mapping
        experiment-level settings to static analysis tool parameters.
        It manages tool selection, timeout configuration, and output coordination
        with other experiment phases.
        
        ### Tool Coordination Strategy:
        - Tool selection: Configurable subset of available static analysis tools
        - Output coordination: Results stored in instrumented directory for task access
        - Timeout management: Tool-specific timeouts with experiment-level defaults
        - Resource management: Parallel execution control and resource limits
        
        ### Role in the System:
        - Coordinates static analysis tool execution with experiment workflow
        - Ensures static analysis results are accessible to coverage tracking
        - Manages tool-specific configuration and resource allocation
        - Provides validation for static analysis tool availability
        
        Returns:
            StaticAnalysisConfig: Validated configuration for static analysis execution
            
        Raises:
            ImportError: If rv-static-analysis module is not available
        """
        try:
            from rv_static_analysis.config import StaticAnalysisConfig
        except ImportError:
            raise ConfigurationError(
                "rv-static-analysis module not available. "
                "Ensure the module is properly installed and accessible."
            )
        
        # Get module-specific configuration with intelligent defaults
        module_config = self.get_module_config("rv-static-analysis")
        
        # Map experiment configuration to static analysis parameters
        tools = module_config.get("tools", ["gator", "gesda", "reach"])
        timeout = module_config.get("timeout", 600)
        output_dir = module_config.get("output_dir", self.get_instrumented_dir())
        parallel_execution = module_config.get("parallel_execution", False)
        
        # Create configuration instance with coordinated parameters
        return StaticAnalysisConfig(
            tools=tools,
            timeout=timeout,
            output_dir=output_dir,
            parallel_execution=parallel_execution,
            max_parallel_tools=module_config.get("max_parallel_tools", 2)
        )
    
    @ErrorHandler.handle_errors(component="ExperimentConfiguration", operation="get_rvandroid_tool_config")
    def get_rvandroid_tool_config(self) -> Dict[str, Any]:
        """
        Create rvandroid tool configuration from experiment configuration.
        
        ### Architectural Decisions:
        This method coordinates rvandroid tool configuration by combining
        LLM configuration with tool-specific parameters. It enables dynamic
        tool registration with proper LLM integration and strategy selection.
        
        ### Configuration Integration Strategy:
        - LLM configuration: Extracted from rv-llm module configuration
        - Tool parameters: Combined from rvandroid-tool module configuration
        - Strategy coordination: Maps experiment-level preferences to tool strategies
        - Model management: Coordinates model selection with LLM provider configuration
        
        ### Role in the System:
        - Bridges LLM configuration with tool execution parameters
        - Enables dynamic tool registration with experiment-specific configuration
        - Coordinates strategy selection with experiment objectives
        - Provides comprehensive tool configuration for complex testing scenarios
        
        Returns:
            Dict[str, Any]: Combined configuration for rvandroid tool registration
        """
        # Get LLM configuration from rv-llm module
        llm_config = self.get_module_config("rv-llm")
        
        # Get rvandroid-specific configuration
        rvandroid_config = self.get_module_config("rvandroid-tool")
        
        # Create comprehensive tool configuration
        tool_config = {
            # LLM integration configuration
            "llm": {
                "provider": llm_config.get("provider", "ollama"),
                "model": llm_config.get("model", "llama3"),
                "temperature": llm_config.get("temperature", 0.3),
                "max_tokens": llm_config.get("max_tokens", 2048),
                "timeout": llm_config.get("timeout", 30)
            },
            
            # Strategy configuration
            "strategy": {
                "type": rvandroid_config.get("strategy_type", "single_action"),
                "use_batch_strategy": rvandroid_config.get("use_batch_strategy", False),
                "batch_size": rvandroid_config.get("batch_size", 3)
            },
            
            # Parser configuration
            "parser": {
                "type": rvandroid_config.get("parser_type", "uiautomator_detailed"),
                "visitor_type": rvandroid_config.get("visitor_type", "enhanced")
            },
            
            # Server configuration
            "server": {
                "url": rvandroid_config.get("server_url", "http://127.0.0.1:5000"),
                "timeout": rvandroid_config.get("server_timeout", 60)
            },
            
            # Memory management
            "memory": {
                "enable_long_term": rvandroid_config.get("enable_long_term_memory", True),
                "max_history_size": rvandroid_config.get("max_history_size", 50)
            }
        }
        
        return tool_config
    
    def configure_default_modules(self) -> None:
        """
        Configure default module settings for standard experiment execution.
        
        ### Architectural Decisions:
        This method provides intelligent defaults for all integrated modules
        when explicit configuration is not provided. It implements the
        "convention over configuration" principle while maintaining flexibility
        for custom experiment scenarios.
        
        ### Default Configuration Strategy:
        - Environment-based discovery: Uses RVSEC_HOME for tool path resolution
        - Standard directory layout: Follows conventional experiment structure
        - Intelligent path mapping: Derives related paths from base configuration
        - Extensible defaults: Easily customizable for different deployment scenarios
        
        ### Role in the System:
        - Ensures experiment executability with minimal configuration
        - Provides consistent default behavior across different environments
        - Enables rapid experiment setup for development and testing
        - Maintains compatibility with existing deployment practices
        
        ### Configuration Modules:
        - rv-monitor-generator: Monitor generation tool configuration
        - rv-instrumentation: APK instrumentation configuration  
        - rv-static-analysis: Static analysis tool configuration
        - rv-llm: Language model integration configuration
        - rvandroid-tool: Advanced testing tool configuration
        """
        # Set default monitor generator configuration
        if "rv-monitor-generator" not in self.module_configs:
            self.set_module_config("rv-monitor-generator", {
                "rvsec_root": os.getenv("RVSEC_HOME"),
                "timeout": 300,
                "specification_type": "jca"  # Default to JCA monitored operations
            })
        
        # Set default instrumentation configuration
        if "rv-instrumentation" not in self.module_configs:
            self.set_module_config("rv-instrumentation", {
                "enable_coverage": True,
                "instrumentation_level": "method",
                "keystore_password": "password"
            })
        
        # Set default static analysis configuration
        if "rv-static-analysis" not in self.module_configs:
            self.set_module_config("rv-static-analysis", {
                "tools": ["gator", "gesda", "reach"],
                "timeout": 600,
                "parallel_execution": False
            })
        
        # Set default LLM configuration
        if "rv-llm" not in self.module_configs:
            self.set_module_config("rv-llm", {
                "provider": "ollama",
                "model": "llama3",
                "temperature": 0.3,
                "max_tokens": 2048,
                "timeout": 30
            })
        
        # Set default rvandroid tool configuration
        if "rvandroid-tool" not in self.module_configs:
            self.set_module_config("rvandroid-tool", {
                "strategy_type": "single_action",
                "use_batch_strategy": False,
                "parser_type": "uiautomator_detailed",
                "visitor_type": "enhanced",
                "server_url": "http://127.0.0.1:5000",
                "enable_long_term_memory": True
            })