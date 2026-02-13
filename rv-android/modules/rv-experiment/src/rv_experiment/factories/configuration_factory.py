"""
Configuration Factory - Phase 8 Clean Architecture Implementation

### Architectural Overview:
This module implements the configuration factory pattern for Phase 8 clean architecture,
providing factory methods for creating different types of experiment configurations
with just-in-time parameter validation and DI-ready design.

### Key Features:
- **Factory Pattern**: Clean configuration creation through factory methods
- **Template Generation**: Intelligent template creation for different scenarios
- **Just-in-Time Validation**: Configuration validation only when needed
- **DI-Ready Design**: Structure optimized for dependency injection containers
- **Specification Set Support**: JCA crypto vs generic programming patterns

### Role in the System:
- Provides factory methods for creating experiment configurations
- Eliminates complex configuration coordination patterns
- Enables clean template generation for different experiment types
- Supports just-in-time configuration validation and error handling
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT

from rv_experiment.config import ExperimentConfig
from rv_platform.config.platform_config import ToolConfig


class ConfigurationFactory:
    """
    Factory for creating experiment configurations with Phase 8 clean architecture.
    
    ### Architectural Overview:
    This factory implements clean configuration creation patterns, eliminating complex
    coordination in favor of simple factory methods that create properly configured
    experiment configurations for different scenarios.
    
    ### Phase 8 Key Features:
    - **Factory Pattern**: Clean configuration creation through factory methods
    - **Just-in-Time Configuration**: Configuration parameters set only when needed
    - **Template Generation**: Intelligent template creation for different scenarios
    - **DI-Ready Design**: Structure optimized for dependency injection containers
    - **Specification Set Support**: Support for different monitored operations types
    
    ### Role in the System:
    - Provides factory methods for creating different types of configurations
    - Eliminates complex configuration coordination and ComponentConfigurator patterns
    - Enables clean template generation with intelligent defaults
    - Supports configuration validation and error handling
    """
    
    def __init__(self):
        """Initialize configuration factory with logging and error handling."""
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "rv_experiment.factories.configuration",
            {CONTEXT_COMPONENT: "ConfigurationFactory"}
        )
        
        self.logger.info("ConfigurationFactory initialized")
    
    @ErrorHandler.handle_errors(
        component="ConfigurationFactory",
        phase="create_cli_config",
    )
    def create_cli_config(self, 
                         tools: List[Dict[str, Any]],
                         experiment_dir: str = "./out/",
                         timeout: int = 300,
                         repetitions: int = 1,
                         apk_dir: str = "./apks_examples/",
                         specification_set: str = "jca",
                         **kwargs) -> ExperimentConfig:
        """
        Create CLI experiment configuration using factory pattern.
        
        ### Factory Pattern Implementation:
        This method implements the factory pattern for CLI configuration creation,
        providing intelligent defaults while allowing customization through parameters.
        It eliminates complex coordination in favor of simple parameter passing.
        
        Args:
            tools: List of tool specifications with variants and parameters
            experiment_dir: Base experiment directory (default: ./out/)
            timeout: Execution timeout in seconds (default: 300)
            repetitions: Number of repetitions (default: 1)
            apk_dir: APK directory path (default: ./apks_examples/)
            specification_set: Monitored operations specification set (default: jca)
            **kwargs: Additional configuration parameters
            
        Returns:
            Configured ExperimentConfig instance
        """
        try:
            # Generate unique experiment ID
            experiment_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            # Create configuration with factory pattern
            config = ExperimentConfig(
                experiment_dir=experiment_dir,
                experiment_id=experiment_id,
                tools=tools,
                timeout=timeout,
                repetitions=repetitions,
                apks_dir=apk_dir,
                specification_set=specification_set,
                **kwargs
            )
            
            # Validate configuration
            config.validate()
            
            self.logger.info(f"Created CLI configuration for experiment: {experiment_id}")
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to create CLI configuration: {e}")
            raise
    
    @ErrorHandler.handle_errors(
        component="ConfigurationFactory",
        phase="create_full_config",
    )
    def create_full_config(self,
                          name: str,
                          tool_configs: List[ToolConfig],
                          output_dir: str = "",
                          specification_set: str = "jca",
                          **kwargs) -> ExperimentConfig:
        """
        Create full experiment configuration using factory pattern.
        
        ### Factory Pattern Implementation:
        This method creates comprehensive experiment configurations for complex
        scenarios, providing full control over all experiment parameters while
        maintaining clean factory-based creation patterns.
        
        Args:
            name: Experiment name
            tool_configs: List of tool configurations
            output_dir: Output directory for experiment results
            specification_set: Monitored operations specification set
            **kwargs: Additional configuration parameters
            
        Returns:
            Configured ExperimentConfig instance
        """
        try:
            # Generate defaults if not provided
            if not output_dir:
                output_dir = f"./out/experiments/{name}"
            
            # Create configuration with factory pattern
            config = ExperimentConfig(
                name=name,
                tool_configs=tool_configs,
                output_dir=output_dir,
                specification_set=specification_set,
                **kwargs
            )
            
            # Validate configuration
            config.validate()
            
            self.logger.info(f"Created full configuration for experiment: {name}")
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to create full configuration: {e}")
            raise
    
    @ErrorHandler.handle_errors(
        component="ConfigurationFactory",
        phase="create_basic_template",
    )
    def create_basic_template(self) -> ExperimentConfig:
        """
        Create basic configuration template using factory pattern.
        
        ### Template Factory Pattern:
        This method implements the template factory pattern for creating basic
        experiment configurations with sensible defaults for typical scenarios.
        
        Returns:
            Basic ExperimentConfig template
        """
        return ExperimentConfig(
            name="basic_experiment",
            description="Basic experiment template",
            tool_configs=[ToolConfig(name="monkey")],
            specification_set="jca"
        )
    
    @ErrorHandler.handle_errors(
        component="ConfigurationFactory",
        phase="create_advanced_template",
    )
    def create_advanced_template(self) -> ExperimentConfig:
        """
        Create advanced configuration template using factory pattern.
        
        ### Template Factory Pattern:
        This method creates advanced configuration templates showcasing all
        available options and complex experiment scenarios.
        
        Returns:
            Advanced ExperimentConfig template
        """
        return ExperimentConfig(
            name="advanced_experiment", 
            description="Advanced experiment template",
            tool_configs=[
                ToolConfig(name="monkey"),
                ToolConfig(name="droidbot", variants=["dfs_greedy"])
            ],
            repetitions=3,
            specification_set="jca"
        )
    
    @ErrorHandler.handle_errors(
        component="ConfigurationFactory",
        phase="create_llm_template",
    )
    def create_llm_template(self) -> ExperimentConfig:
        """
        Create LLM-focused configuration template using factory pattern.

        ### Template Factory Pattern:
        This method creates LLM-focused configuration templates optimized for
        agentic testing scenarios with rvagent and monitored operations.

        Returns:
            LLM-focused ExperimentConfig template
        """
        return ExperimentConfig(
            name="llm_experiment",
            description="LLM-driven testing experiment",
            tool_configs=[ToolConfig(name="rvagent", variants=["multimode"])],
            timeouts=[1800],  # 30 minutes for LLM
            specification_set="jca"
        )
    
    @ErrorHandler.handle_errors(
        component="ConfigurationFactory",
        phase="parse_tool_specifications",
    )
    def parse_tool_specifications(self, tool_specs: List[str]) -> List[Dict[str, Any]]:
        """
        Parse tool specification strings into structured configurations.
        
        ### Tool Specification DSL Factory:
        This method implements the tool specification DSL factory pattern,
        parsing tool:variant@parameter strings into structured configurations
        suitable for factory-based component creation.
        
        Args:
            tool_specs: List of tool specification strings
            
        Returns:
            List of structured tool configuration dictionaries
        """
        try:
            parsed_tools = []
            
            for tool_spec in tool_specs:
                # Parse tool specification using DSL
                parsed_tool = self._parse_single_tool_spec(tool_spec.strip())
                parsed_tools.append(parsed_tool)
            
            self.logger.info(f"Parsed {len(parsed_tools)} tool specifications")
            return parsed_tools
            
        except Exception as e:
            self.logger.error(f"Failed to parse tool specifications: {e}")
            raise
    
    def _parse_single_tool_spec(self, tool_spec: str) -> Dict[str, Any]:
        """
        Parse a single tool specification string.
        
        ### Tool Specification DSL:
        Format: `tool_name[:variant1][:variant2][@param1=value1,param2=value2]`
        
        Args:
            tool_spec: Tool specification string to parse
            
        Returns:
            Structured tool configuration dictionary
        """
        try:
            # Split tool name/variants from parameters
            if '@' in tool_spec:
                tool_part, params_part = tool_spec.split('@', 1)
                # Parse parameters
                parameters = {}
                for param in params_part.split(','):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        parameters[key.strip()] = value.strip()
                    else:
                        # Boolean flag parameter
                        parameters[param.strip()] = True
            else:
                tool_part = tool_spec
                parameters = {}
            
            # Split tool name and variants
            parts = tool_part.split(':')
            tool_name = parts[0].strip()
            variants = [v.strip() for v in parts[1:] if v.strip()]
            
            if not tool_name:
                raise ValueError("Tool name cannot be empty")
                
            return {
                "name": tool_name,
                "variants": variants,
                "parameters": parameters
            }
            
        except Exception as e:
            raise ValueError(f"Invalid tool specification '{tool_spec}': {e}")
    
    @ErrorHandler.handle_errors(
        component="ConfigurationFactory",
        phase="create_from_dict",
    )
    def create_from_dict(self, config_data: Dict[str, Any], 
                        config_type: str = "cli") -> ExperimentConfig:
        """
        Create configuration from dictionary using factory pattern.
        
        ### Dictionary Factory Pattern:
        This method implements the dictionary factory pattern for creating
        configurations from structured data, supporting both CLI and full
        configuration formats with proper validation.
        
        Args:
            config_data: Configuration data dictionary
            config_type: Type of configuration to create ("cli" or "full")
            
        Returns:
            Configured experiment configuration instance
        """
        try:
            if config_type == "cli":
                config = ExperimentConfig.from_dict(config_data)
            elif config_type == "full":
                config = ExperimentConfig.from_dict(config_data)
            else:
                raise ValueError(f"Unknown configuration type: {config_type}")
            
            # Validate configuration
            config.validate()
            
            self.logger.info(f"Created {config_type} configuration from dictionary")
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to create configuration from dictionary: {e}")
            raise