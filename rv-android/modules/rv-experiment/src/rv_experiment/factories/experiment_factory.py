"""
Experiment Factory - Phase 8 Clean Architecture Implementation

### Architectural Overview:
This module implements the experiment factory pattern for Phase 8 clean architecture,
providing factory methods for creating experiment orchestrators and components with
just-in-time configuration and DI-ready design.

### Key Features:
- **Factory Pattern**: Clean experiment component creation through factory methods
- **Just-in-Time Configuration**: Components configured only when created
- **DI-Ready Design**: Structure optimized for dependency injection containers
- **Module Independence**: Maintains module independence through factory-based creation
- **Event Bus Integration**: Proper event bus setup and coordination

### Role in the System:
- Provides factory methods for creating experiment orchestrators and components
- Eliminates complex coordination and ComponentConfigurator patterns
- Enables clean component creation with proper dependency injection preparation
- Supports event bus integration and error handling coordination
"""

from typing import Optional, Any

from rv_android_core.event import EventBus, get_event_bus
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT

from rv_experiment.config import CLIExperimentConfig
from rv_experiment.orchestrator import ExperimentOrchestrator


class ExperimentFactory:
    """
    Factory for creating experiment components with Phase 8 clean architecture.
    
    ### Architectural Overview:
    This factory implements clean experiment component creation patterns, eliminating
    complex coordination in favor of simple factory methods that create properly
    configured experiment orchestrators and related components.
    
    ### Phase 8 Key Features:
    - **Factory Pattern**: Clean component creation through factory methods
    - **Event Bus Integration**: Proper event bus setup and management
    - **Just-in-Time Configuration**: Components configured only when created
    - **DI-Ready Design**: Structure optimized for dependency injection containers
    - **Error Handling**: Comprehensive error handling using rv-android-core patterns
    
    ### Role in the System:
    - Provides factory methods for creating experiment orchestrators
    - Eliminates complex coordination and ComponentConfigurator patterns
    - Enables clean component creation with proper dependency injection preparation
    - Supports event bus integration and error handling coordination
    """
    
    def __init__(self):
        """Initialize experiment factory with logging and error handling."""
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "rv_experiment.factories.experiment",
            {CONTEXT_COMPONENT: "ExperimentFactory"}
        )
        
        self.logger.info("ExperimentFactory initialized")
    
    @ErrorHandler.handle_errors(
        component="ExperimentFactory",
        phase="create_orchestrator",
    )
    def create_orchestrator(self, 
                           config: CLIExperimentConfig,
                           event_bus: Optional[EventBus] = None,
                           logger: Optional[Any] = None) -> ExperimentOrchestrator:
        """
        Create experiment orchestrator using factory pattern.
        
        ### Factory Pattern Implementation:
        This method implements the factory pattern for orchestrator creation,
        providing proper component initialization with event bus integration
        and logging coordination using rv-android-core patterns.
        
        ### Component Creation Strategy:
        - Event bus: Uses provided instance or creates default
        - Logger: Uses provided instance or creates factory-specific logger
        - Configuration: Validates and prepares configuration for orchestration
        - Dependencies: Initializes all required dependencies using clean patterns
        
        Args:
            config: Experiment configuration for orchestrator
            event_bus: Optional event bus instance (creates default if not provided)
            logger: Optional logger instance (creates new if not provided)
            
        Returns:
            Configured ExperimentOrchestrator instance ready for execution
        """
        try:
            # Get or create event bus with proper initialization
            if event_bus is None:
                event_bus = get_event_bus()
                self.logger.debug("Created default event bus for orchestrator")
            
            # Get or create logger with proper context
            if logger is None:
                logger = self.logging_manager.get_logger(
                    f"rv_experiment.orchestrator.{config.experiment_id}",
                    {CONTEXT_COMPONENT: "ExperimentOrchestrator"}
                )
                self.logger.debug("Created experiment-specific logger for orchestrator")
            
            # Validate configuration before orchestrator creation
            config.validate()
            
            # Create orchestrator with factory pattern
            orchestrator = ExperimentOrchestrator(
                config=config,
                event_bus=event_bus,
                logger=logger
            )
            
            self.logger.info(f"Created experiment orchestrator for: {config.experiment_id}")
            return orchestrator
            
        except Exception as e:
            self.logger.error(f"Failed to create experiment orchestrator: {e}")
            raise
    
    @ErrorHandler.handle_errors(
        component="ExperimentFactory",
        phase="create_orchestrator_with_defaults",
    )
    def create_orchestrator_with_defaults(self, 
                                        config: CLIExperimentConfig) -> ExperimentOrchestrator:
        """
        Create experiment orchestrator with intelligent defaults.
        
        ### Factory Pattern with Defaults:
        This method implements the factory pattern with intelligent defaults,
        creating a fully configured orchestrator with minimal parameter
        specification while maintaining clean architecture principles.
        
        ### Default Configuration Strategy:
        - Event bus: Creates default event bus with proper initialization
        - Logger: Creates experiment-specific logger with proper context
        - Error handling: Uses rv-android-core ErrorHandler patterns
        - Dependencies: Initializes all required dependencies automatically
        
        Args:
            config: Experiment configuration for orchestrator
            
        Returns:
            Configured ExperimentOrchestrator with intelligent defaults
        """
        try:
            # Create with all defaults
            return self.create_orchestrator(config)
            
        except Exception as e:
            self.logger.error(f"Failed to create orchestrator with defaults: {e}")
            raise
    
    @ErrorHandler.handle_errors(
        component="ExperimentFactory",
        phase="create_for_single_tool",
    )
    def create_for_single_tool(self, 
                              tool_spec: str,
                              experiment_dir: str = "./out/",
                              timeout: int = 300,
                              apk_dir: str = "./apks_examples/",
                              specification_set: str = "jca") -> ExperimentOrchestrator:
        """
        Create orchestrator for single-tool experiments using factory pattern.
        
        ### Single-Tool Factory Pattern:
        This method implements the factory pattern specifically for single-tool
        experiments, providing a simplified interface that creates a complete
        orchestrator setup for single tool execution scenarios.
        
        ### Single-Tool Configuration Strategy:
        - Tool parsing: Parses tool specification using modern DSL format
        - Configuration: Creates CLI configuration optimized for single-tool execution
        - Orchestrator: Creates orchestrator with proper single-tool setup
        - Validation: Ensures configuration is valid for single-tool scenarios
        
        Args:
            tool_spec: Tool specification string (e.g., "monkey", "droidbot:dfs_greedy")
            experiment_dir: Base experiment directory (default: ./out/)
            timeout: Execution timeout in seconds (default: 300)
            apk_dir: APK directory path (default: ./apks_examples/)
            specification_set: Monitored operations specification set (default: jca)
            
        Returns:
            Configured ExperimentOrchestrator for single-tool execution
        """
        try:
            # Import configuration factory for tool parsing
            from .configuration_factory import ConfigurationFactory
            
            config_factory = ConfigurationFactory()
            
            # Parse tool specification
            tools = config_factory.parse_tool_specifications([tool_spec])
            
            # Create CLI configuration for single tool
            config = config_factory.create_cli_config(
                tools=tools,
                experiment_dir=experiment_dir,
                timeout=timeout,
                apk_dir=apk_dir,
                specification_set=specification_set
            )
            
            # Create orchestrator
            orchestrator = self.create_orchestrator(config)
            
            self.logger.info(f"Created single-tool orchestrator for: {tool_spec}")
            return orchestrator
            
        except Exception as e:
            self.logger.error(f"Failed to create single-tool orchestrator: {e}")
            raise
    
    @ErrorHandler.handle_errors(
        component="ExperimentFactory",
        phase="create_for_comparative",
    )
    def create_for_comparative(self, 
                             tool_specs: list,
                             experiment_dir: str = "./out/",
                             timeout: int = 300,
                             apk_dir: str = "./apks_examples/",
                             specification_set: str = "jca") -> ExperimentOrchestrator:
        """
        Create orchestrator for comparative experiments using factory pattern.
        
        ### Comparative Factory Pattern:
        This method implements the factory pattern specifically for comparative
        experiments, providing a simplified interface that creates a complete
        orchestrator setup for multi-tool comparison scenarios.
        
        ### Comparative Configuration Strategy:
        - Tool parsing: Parses multiple tool specifications using modern DSL format
        - Configuration: Creates CLI configuration optimized for comparative execution
        - Orchestrator: Creates orchestrator with proper comparative setup
        - Validation: Ensures configuration is valid for comparative scenarios
        
        Args:
            tool_specs: List of tool specification strings
            experiment_dir: Base experiment directory (default: ./out/)
            timeout: Execution timeout in seconds (default: 300)
            apk_dir: APK directory path (default: ./apks_examples/)
            specification_set: Monitored operations specification set (default: jca)
            
        Returns:
            Configured ExperimentOrchestrator for comparative execution
        """
        try:
            # Import configuration factory for tool parsing
            from .configuration_factory import ConfigurationFactory
            
            config_factory = ConfigurationFactory()
            
            # Parse tool specifications
            tools = config_factory.parse_tool_specifications(tool_specs)
            
            # Validate minimum tools for comparative experiment
            if len(tools) < 2:
                raise ValueError("Comparative experiments require at least 2 tools")
            
            # Create CLI configuration for comparative experiment
            config = config_factory.create_cli_config(
                tools=tools,
                experiment_dir=experiment_dir,
                timeout=timeout,
                apk_dir=apk_dir,
                specification_set=specification_set
            )
            
            # Create orchestrator
            orchestrator = self.create_orchestrator(config)
            
            self.logger.info(f"Created comparative orchestrator for {len(tools)} tools")
            return orchestrator
            
        except Exception as e:
            self.logger.error(f"Failed to create comparative orchestrator: {e}")
            raise
    
    @ErrorHandler.handle_errors(
        component="ExperimentFactory",
        phase="create_for_llm_testing",
    )
    def create_for_llm_testing(self, 
                             llm_model: str = "llama3",
                             strategy: str = "standard",
                             experiment_dir: str = "./out/",
                             timeout: int = 900,
                             apk_dir: str = "./apks_examples/",
                             specification_set: str = "jca") -> ExperimentOrchestrator:
        """
        Create orchestrator for LLM-driven testing using factory pattern.
        
        ### LLM Testing Factory Pattern:
        This method implements the factory pattern specifically for LLM-driven
        testing scenarios, providing a simplified interface that creates a complete
        orchestrator setup for AI-guided exploration with monitored operations.
        
        ### LLM Configuration Strategy:
        - Tool configuration: Creates rvandroid tool with LLM-specific parameters
        - Model selection: Configures LLM model and strategy parameters
        - Orchestrator: Creates orchestrator with proper LLM integration setup
        - Specification: Uses appropriate monitored operations for LLM scenarios
        
        Args:
            llm_model: LLM model to use (default: llama3)
            strategy: LLM strategy (standard, batch) (default: standard)
            experiment_dir: Base experiment directory (default: ./out/)
            timeout: Execution timeout in seconds (default: 900, longer for LLM)
            apk_dir: APK directory path (default: ./apks_examples/)
            specification_set: Monitored operations specification set (default: jca)
            
        Returns:
            Configured ExperimentOrchestrator for LLM-driven testing
        """
        try:
            # Import configuration factory for tool parsing
            from .configuration_factory import ConfigurationFactory
            
            config_factory = ConfigurationFactory()
            
            # Create LLM-specific tool specification
            tool_spec = f"rvandroid:llama:{strategy}@model={llm_model},temperature=0.3,max_tokens=2048"
            tools = config_factory.parse_tool_specifications([tool_spec])
            
            # Create CLI configuration for LLM testing
            config = config_factory.create_cli_config(
                tools=tools,
                experiment_dir=experiment_dir,
                timeout=timeout,
                apk_dir=apk_dir,
                specification_set=specification_set
            )
            
            # Create orchestrator
            orchestrator = self.create_orchestrator(config)
            
            self.logger.info(f"Created LLM testing orchestrator with model: {llm_model}, strategy: {strategy}")
            return orchestrator
            
        except Exception as e:
            self.logger.error(f"Failed to create LLM testing orchestrator: {e}")
            raise