"""
Core Dependency Injection Interfaces - Modern Architecture Contracts

### Architectural Overview:
This module defines the core interfaces for dependency injection in the Phase 8
modernized architecture. These interfaces establish clear contracts between
components while enabling clean testing, configuration management, and future
DI container integration.

### Key Architectural Decisions:
- **Single Responsibility**: Each interface has a focused, cohesive purpose
- **Dependency Inversion**: High-level modules depend on abstractions, not concretions
- **Interface Segregation**: Clients depend only on interfaces they need
- **Open/Closed Principle**: Open for extension, closed for modification
- **Configuration-Driven**: All interfaces support configuration-based initialization

### Design Patterns:
- **Factory Pattern**: Interface-based component creation
- **Strategy Pattern**: Pluggable algorithm implementations
- **Observer Pattern**: Lifecycle event notification
- **Template Method**: Common lifecycle operations with customization points
- **Dependency Injection**: Constructor and setter injection support

### Role in the System:
- Defines contracts for all major system components
- Enables comprehensive testing through interface mocking
- Supports configuration-driven component composition
- Prepares for future DI container integration (Spring, etc.)
- Provides clear extension points for new functionality
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, TypeVar, Generic
from pathlib import Path
from enum import Enum

# Type variables for generic interfaces
T = TypeVar('T')
ConfigType = TypeVar('ConfigType')


class IComponentLifecycle(ABC):
    """
    Interface for component lifecycle management in the DI system.
    
    ### Lifecycle Contract:
    Components implementing this interface provide standardized initialization,
    startup, shutdown, and cleanup operations. This enables consistent lifecycle
    management across all system components and supports graceful system startup
    and shutdown procedures.
    
    ### Lifecycle States:
    - **CREATED**: Component instantiated but not initialized
    - **INITIALIZED**: Component configured and ready for startup
    - **STARTED**: Component actively running and processing
    - **STOPPED**: Component stopped but can be restarted
    - **DESTROYED**: Component cleaned up and cannot be reused
    """
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize component with configuration.
        
        Args:
            config: Component configuration dictionary
            
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def start(self) -> bool:
        """
        Start component operations.
        
        Returns:
            True if startup successful, False otherwise
        """
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """
        Stop component operations gracefully.
        
        Returns:
            True if shutdown successful, False otherwise
        """
        pass
    
    @abstractmethod
    def destroy(self) -> bool:
        """
        Clean up component resources.
        
        Returns:
            True if cleanup successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_state(self) -> str:
        """
        Get current component lifecycle state.
        
        Returns:
            Current lifecycle state as string
        """
        pass
    
    @abstractmethod
    def is_healthy(self) -> bool:
        """
        Check if component is in healthy state.
        
        Returns:
            True if component is healthy, False otherwise
        """
        pass


class IConfigurationProvider(ABC):
    """
    Interface for configuration providers in the DI system.
    
    ### Configuration Strategy:
    Configuration providers supply component configuration from various sources
    (files, environment variables, command line arguments, etc.). They provide
    a unified interface for configuration access while supporting multiple
    configuration formats and sources.
    
    ### Configuration Sources:
    - JSON configuration files
    - YAML configuration files  
    - Environment variables
    - Command line arguments
    - Database configuration stores
    - Remote configuration services
    """
    
    @abstractmethod
    def get_config(self, component_name: str) -> Dict[str, Any]:
        """
        Get configuration for specific component.
        
        Args:
            component_name: Name of component to get configuration for
            
        Returns:
            Configuration dictionary for the component
        """
        pass
    
    @abstractmethod
    def get_global_config(self) -> Dict[str, Any]:
        """
        Get global system configuration.
        
        Returns:
            Global configuration dictionary
        """
        pass
    
    @abstractmethod
    def has_config(self, component_name: str) -> bool:
        """
        Check if configuration exists for component.
        
        Args:
            component_name: Name of component to check
            
        Returns:
            True if configuration exists, False otherwise
        """
        pass
    
    @abstractmethod
    def reload_config(self) -> bool:
        """
        Reload configuration from source.
        
        Returns:
            True if reload successful, False otherwise
        """
        pass


class IDependencyContainer(ABC):
    """
    Interface for dependency injection containers.
    
    ### Container Strategy:
    Dependency containers manage component creation, configuration, and lifecycle
    while providing comprehensive dependency injection capabilities. They support
    both singleton and prototype scopes, constructor and setter injection, and
    circular dependency resolution.
    
    ### DI Features:
    - Constructor injection with automatic dependency resolution
    - Setter injection for optional dependencies
    - Interface-based component registration
    - Singleton and prototype scope management
    - Circular dependency detection and resolution
    - Lifecycle-aware component management
    """
    
    @abstractmethod
    def register(self, interface: type, implementation: type, 
                scope: str = "singleton") -> None:
        """
        Register component implementation for interface.
        
        Args:
            interface: Interface type to register
            implementation: Implementation type for the interface
            scope: Component scope ("singleton" or "prototype")
        """
        pass
    
    @abstractmethod
    def register_instance(self, interface: type, instance: Any) -> None:
        """
        Register specific instance for interface.
        
        Args:
            interface: Interface type to register
            instance: Pre-created instance to register
        """
        pass
    
    @abstractmethod
    def get(self, interface: type) -> Any:
        """
        Get component instance for interface.
        
        Args:
            interface: Interface type to resolve
            
        Returns:
            Component instance implementing the interface
        """
        pass
    
    @abstractmethod
    def has(self, interface: type) -> bool:
        """
        Check if interface is registered.
        
        Args:
            interface: Interface type to check
            
        Returns:
            True if interface is registered, False otherwise
        """
        pass
    
    @abstractmethod
    def create_child_container(self) -> 'IDependencyContainer':
        """
        Create child container with inheritance.
        
        Returns:
            New child container inheriting parent registrations
        """
        pass


class IExperimentConfig(ABC):
    """
    Interface for experiment configuration in the DI system.
    
    ### Configuration Strategy:
    Experiment configurations provide structured access to all experiment
    parameters while supporting validation, serialization, and template
    generation. They integrate with the DI system to provide consistent
    configuration management across all experiment components.
    
    ### Configuration Features:
    - Structured experiment parameter management
    - Configuration validation and error reporting
    - Template generation for common experiment scenarios
    - Serialization support for persistence and sharing
    - Integration with monitored operations specifications
    """
    
    @abstractmethod
    def validate(self) -> bool:
        """
        Validate experiment configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Configuration as dictionary
        """
        pass
    
    @abstractmethod
    def from_dict(self, config_dict: Dict[str, Any]) -> None:
        """
        Load configuration from dictionary.
        
        Args:
            config_dict: Configuration dictionary to load
        """
        pass
    
    @abstractmethod
    def get_tools_config(self) -> List[Dict[str, Any]]:
        """
        Get tools configuration.
        
        Returns:
            List of tool configuration dictionaries
        """
        pass
    
    @abstractmethod
    def get_specification_set(self) -> str:
        """
        Get specification set type.
        
        Returns:
            Specification set type ("jca", "generic", "custom")
        """
        pass
    
    @abstractmethod
    def get_experiment_id(self) -> str:
        """
        Get experiment identifier.
        
        Returns:
            Unique experiment identifier
        """
        pass


class IDirectoryManager(ABC):
    """
    Interface for directory management in the DI system.
    
    ### Directory Strategy:
    Directory managers provide standardized directory structure management
    for all experiment operations. They ensure consistent directory layouts
    while supporting different specification sets (JCA crypto vs generic)
    and enabling efficient resource sharing and caching.
    
    ### Directory Features:
    - Standardized ./out/ directory structure management
    - Specification-specific directory separation (JCA vs generic)
    - Experiment isolation with shared resource optimization
    - Multi-level caching strategy (tools, models, temporary files)
    - Directory validation and integrity checking
    """
    
    @abstractmethod
    def create_full_structure(self) -> bool:
        """
        Create complete directory structure.
        
        Returns:
            True if structure created successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def create_experiment_directory(self, experiment_id: str, 
                                  specification_set: str = "jca") -> Path:
        """
        Create directory for specific experiment.
        
        Args:
            experiment_id: Unique experiment identifier
            specification_set: Specification set type
            
        Returns:
            Path to created experiment directory
        """
        pass
    
    @abstractmethod
    def get_instrumented_dir(self, specification_set: str) -> Path:
        """
        Get instrumented APKs directory for specification set.
        
        Args:
            specification_set: Specification set type
            
        Returns:
            Path to instrumented APKs directory
        """
        pass
    
    @abstractmethod
    def get_monitors_dir(self, specification_set: str) -> Path:
        """
        Get monitors directory for specification set.
        
        Args:
            specification_set: Specification set type
            
        Returns:
            Path to monitors directory
        """
        pass
    
    @abstractmethod
    def validate_structure(self) -> Dict[str, bool]:
        """
        Validate directory structure integrity.
        
        Returns:
            Dictionary with validation results for each component
        """
        pass
    
    @abstractmethod
    def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up temporary files older than specified age.
        
        Args:
            max_age_hours: Maximum age of temporary files in hours
            
        Returns:
            Number of files cleaned up
        """
        pass


class IExperimentOrchestrator(ABC):
    """
    Interface for experiment orchestration in the DI system.
    
    ### Orchestration Strategy:
    Experiment orchestrators coordinate all aspects of experiment execution
    including tool management, monitoring operations, result collection, and
    error handling. They provide the primary interface for experiment execution
    while integrating with all other system components through dependency injection.
    
    ### Orchestration Features:
    - Comprehensive experiment lifecycle management
    - Multi-tool coordination and execution
    - Monitored operations integration (JCA crypto and generic specifications)
    - Result collection and analysis coordination
    - Error handling and recovery mechanisms
    - Progress tracking and reporting
    """
    
    @abstractmethod
    def execute(self) -> bool:
        """
        Execute complete experiment workflow.
        
        Returns:
            True if experiment completed successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_progress(self) -> Dict[str, Any]:
        """
        Get current experiment progress.
        
        Returns:
            Progress information dictionary
        """
        pass
    
    @abstractmethod
    def stop_experiment(self) -> bool:
        """
        Stop experiment execution gracefully.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_results_summary(self) -> Dict[str, Any]:
        """
        Get experiment results summary.
        
        Returns:
            Results summary dictionary
        """
        pass
    
    @abstractmethod
    def validate_configuration(self) -> bool:
        """
        Validate experiment configuration before execution.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        pass


class IFactory(Generic[T], ABC):
    """
    Generic interface for factory implementations in the DI system.
    
    ### Factory Strategy:
    Factories provide standardized component creation while supporting
    dependency injection and configuration-driven instantiation. They
    enable clean separation between component creation logic and business
    logic while supporting comprehensive error handling and logging.
    
    ### Factory Features:
    - Type-safe component creation with generics
    - Configuration-driven instantiation
    - Dependency injection integration
    - Comprehensive error handling and validation
    - Lifecycle-aware component creation
    """
    
    @abstractmethod
    def create(self, config: Dict[str, Any]) -> T:
        """
        Create component instance from configuration.
        
        Args:
            config: Component configuration dictionary
            
        Returns:
            Created component instance
        """
        pass
    
    @abstractmethod
    def create_default(self) -> T:
        """
        Create component instance with default configuration.
        
        Returns:
            Component instance with default settings
        """
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration for component creation.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if configuration is valid, False otherwise
        """
        pass


class ILLMProvider(ABC):
    """
    Interface for LLM providers in the DI system.
    
    ### Provider Strategy:
    LLM providers abstract different language model backends (Ollama, HuggingFace,
    Frontier models) while providing a unified interface for text generation.
    They support configuration-driven model selection and comprehensive
    error handling for model operations.
    """
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text from prompt.
        
        Args:
            prompt: Input prompt for text generation
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if LLM provider is available.
        
        Returns:
            True if provider is available, False otherwise
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.
        
        Returns:
            Model information dictionary
        """
        pass


class IPromptStrategy(ABC):
    """
    Interface for prompt strategies in the DI system.
    
    ### Strategy Pattern:
    Prompt strategies provide different approaches to prompt generation
    while maintaining a consistent interface. They support both single-action
    and batch-action generation with comprehensive context management.
    """
    
    @abstractmethod
    def generate_prompt(self, context: Dict[str, Any]) -> str:
        """
        Generate prompt from context.
        
        Args:
            context: Context information for prompt generation
            
        Returns:
            Generated prompt string
        """
        pass
    
    @abstractmethod
    def supports_batch(self) -> bool:
        """
        Check if strategy supports batch action generation.
        
        Returns:
            True if batch actions supported, False otherwise
        """
        pass
    
    @abstractmethod
    def get_strategy_info(self) -> Dict[str, Any]:
        """
        Get information about the strategy.
        
        Returns:
            Strategy information dictionary
        """
        pass