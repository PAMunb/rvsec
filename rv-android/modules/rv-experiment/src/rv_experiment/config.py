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
        """Validate application configuration after initialization."""
        if not any([self.path, self.directory, self.patterns]):
            raise ValueError("Must specify at least one: path, directory, or patterns")
    
    def get_applications(self) -> List[str]:
        """
        Get list of application paths based on configuration.
        
        Returns:
            List of application file paths
        """
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
        
        # Create tool configurations if not provided
        if not self.tool_configs and self.tools:
            self.tool_configs = [
                ToolConfiguration(name=tool) for tool in self.tools
            ]
        
        # Initialize error handling and logging
        self.error_handler = ErrorHandler.get_instance()
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "rv_experiment.config",
            {CONTEXT_COMPONENT: "ExperimentConfiguration"}
        )
    
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