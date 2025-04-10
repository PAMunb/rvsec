# rvandroid/config/component_configurator.py
"""
Component configurator for managing component configurations.
Provides a unified registration system and flexible component configuration.
"""
import importlib
import json
import logging
import os
from typing import Dict, List, Any, Type, Optional, Callable, TypeVar, Generic

from rvandroid.config.configuration import Configuration
# Remove circular import
# from rvandroid.config.configuration_manager import ConfigurationManager
from rvandroid.llm.llm_config import LLMConfiguration
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser
from rvandroid.parser.screen.parser_factory import ParserType
from rvandroid.parser.screen.visitor.base_visitor import BaseScreenVisitor

# Type variables for generic component types
T = TypeVar('T')


class ComponentRegistry(Generic[T]):
    """
    A generic registry for component types and their implementation classes.
    Provides unified registration and discovery mechanisms.

    ### Architectural Decisions:
    - Implements a dynamic, type-safe registry for component registration
    - Supports runtime component discovery and instantiation
    - Enables centralized component management with validation
    - Provides a consistent interface for component lookup and creation
    """

    def __init__(self, component_type: str):
        """
        Initialize the component registry.

        Args:
            component_type: Type of components stored in this registry
        """
        self.component_type = component_type
        self._components: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(f"{__name__}.{component_type}")

    def register(self, name: str, implementation: Type[T], 
                 module_path: str = None, metadata: Dict[str, Any] = None) -> None:
        """
        Register a component implementation with the registry.

        Args:
            name: Component name/identifier
            implementation: Component class
            module_path: Module path for lazy loading (optional)
            metadata: Additional component metadata (optional)

        Raises:
            ValueError: If name is already registered with a different implementation
        """
        if name in self._components and implementation != self._components[name].get('implementation'):
            raise ValueError(f"{self.component_type} '{name}' already registered with a different implementation")

        self._components[name] = {
            'implementation': implementation,
            'module_path': module_path,
            'metadata': metadata or {}
        }
        self.logger.debug(f"Registered {self.component_type} '{name}'")

    def register_lazy(self, name: str, module_path: str, class_name: str, 
                      metadata: Dict[str, Any] = None) -> None:
        """
        Register a component for lazy loading.

        Args:
            name: Component name/identifier
            module_path: Module path for importing
            class_name: Class name within the module
            metadata: Additional component metadata (optional)
        """
        self._components[name] = {
            'implementation': None,
            'module_path': module_path,
            'class_name': class_name,
            'metadata': metadata or {}
        }
        self.logger.debug(f"Registered {self.component_type} '{name}' for lazy loading")

    def get(self, name: str) -> Optional[Type[T]]:
        """
        Get a component implementation by name, loading it if necessary.

        Args:
            name: Component name/identifier

        Returns:
            Component implementation class or None if not found

        Raises:
            ImportError: If lazy loading fails
        """
        if name not in self._components:
            return None

        component = self._components[name]
        implementation = component.get('implementation')

        # Lazy load if necessary
        if implementation is None and component.get('module_path'):
            try:
                module = importlib.import_module(component['module_path'])
                implementation = getattr(module, component['class_name'])
                component['implementation'] = implementation
                self.logger.debug(f"Lazy loaded {self.component_type} '{name}'")
            except (ImportError, AttributeError) as e:
                self.logger.error(f"Failed to lazy load {self.component_type} '{name}': {e}")
                raise ImportError(f"Could not load {self.component_type} '{name}': {str(e)}")

        return implementation

    def get_all(self) -> Dict[str, Type[T]]:
        """
        Get all registered component implementations, loading any lazy components.

        Returns:
            Dictionary of component names to implementation classes
        """
        result = {}
        for name in self._components:
            try:
                implementation = self.get(name)
                if implementation:
                    result[name] = implementation
            except ImportError:
                pass  # Skip components that fail to load
        return result

    def get_names(self) -> List[str]:
        """
        Get names of all registered components.

        Returns:
            List of component names
        """
        return list(self._components.keys())

    def get_metadata(self, name: str) -> Dict[str, Any]:
        """
        Get metadata for a component.

        Args:
            name: Component name/identifier

        Returns:
            Component metadata or empty dict if not found
        """
        if name not in self._components:
            return {}
        return self._components[name].get('metadata', {})

    def has(self, name: str) -> bool:
        """
        Check if a component is registered.

        Args:
            name: Component name/identifier

        Returns:
            True if component is registered, False otherwise
        """
        return name in self._components

    def unregister(self, name: str) -> bool:
        """
        Unregister a component.

        Args:
            name: Component name/identifier

        Returns:
            True if component was unregistered, False if not found
        """
        if name in self._components:
            del self._components[name]
            self.logger.debug(f"Unregistered {self.component_type} '{name}'")
            return True
        return False


class ComponentConfigurator:
    """
    A sophisticated configuration management system for dynamically configuring and composing experimental components.

    ### Architectural Decisions:
    - Implements a flexible, modular approach to component configuration
    - Uses a centralized registry system for component management
    - Supports dynamic composition of language models, strategies, and parsing components
    - Provides a centralized mechanism for configuring experimental components
    - Enables runtime configuration and component selection

    ### Role in the System:
    - Acts as a central configuration factory for experiment components
    - Manages the creation and configuration of language models, parsers, and strategies
    - Provides a flexible mechanism for swapping and configuring experiment components
    - Supports complex configuration scenarios across different experimental workflows
    - Enables runtime customization of AI-driven testing components

    ### Key Considerations:
    - Supports multiple language model providers and strategies
    - Handles complex configuration scenarios with type-safe mechanisms
    - Provides dynamic component creation and configuration
    - Enables flexible parsing and visitor strategy selection
    - Supports comprehensive configuration introspection and management

    ### Integration Strategy:
    - Deeply integrated with the RV-Android experimental framework
    - Compatible with multiple language models, parsing strategies, and visitor implementations
    - Supports configuration loading from files and environment variables
    - Provides a uniform interface for component configuration
    - Enables dependency injection and component composition

    ### Performance and Scalability:
    - Designed for lightweight and efficient component configuration
    - Minimizes overhead in component creation and configuration
    - Supports dynamic component swapping with minimal performance impact
    - Adaptable to different experimental complexity levels
    - Enables efficient runtime configuration management
    """

    # Component registries
    _registries = {
        'llm': ComponentRegistry('LLM'),
        'strategy': ComponentRegistry('Strategy'),
        'parser': ComponentRegistry('Parser'),
        'visitor': ComponentRegistry('Visitor')
    }

    # Model registries
    LLM_MODELS = {
        "ollama": ["llama3.2:3b", "gemma3:4b", "phi3.5:3.8b"],
        "huggingface": ["meta-llama/Meta-Llama-3.1-8B-Instruct"],
        "dspy": ["meta-llama/Meta-Llama-3.1-8B-Instruct"],
        "langchain": ["meta-llama/Meta-Llama-3.1-8B-Instruct"],
        "frontier": ["claude-3-opus-20240229", "claude-3-sonnet-20240229"]
    }

    @classmethod
    def register_llm(cls, name: str, implementation=None, module_path=None, class_name=None, 
                     metadata: Dict[str, Any] = None) -> None:
        """
        Register a language model implementation.

        Args:
            name: Model type name
            implementation: Implementation class (optional if module_path is provided)
            module_path: Module path for lazy loading (required if implementation is None)
            class_name: Class name for lazy loading (required if implementation is None)
            metadata: Additional metadata
        """
        registry = cls._registries['llm']
        if implementation:
            registry.register(name, implementation, metadata=metadata)
        elif module_path and class_name:
            registry.register_lazy(name, module_path, class_name, metadata=metadata)
        else:
            raise ValueError("Either implementation or module_path+class_name must be provided")

    @classmethod
    def register_strategy(cls, name: str, implementation=None, module_path=None, class_name=None,
                          metadata: Dict[str, Any] = None) -> None:
        """
        Register a prompt strategy implementation.

        Args:
            name: Strategy type name
            implementation: Implementation class (optional if module_path is provided)
            module_path: Module path for lazy loading (required if implementation is None)
            class_name: Class name for lazy loading (required if implementation is None)
            metadata: Additional metadata
        """
        registry = cls._registries['strategy']
        if implementation:
            registry.register(name, implementation, metadata=metadata)
        elif module_path and class_name:
            registry.register_lazy(name, module_path, class_name, metadata=metadata)
        else:
            raise ValueError("Either implementation or module_path+class_name must be provided")

    @classmethod
    def register_parser(cls, name: str, implementation=None, module_path=None, class_name=None,
                        metadata: Dict[str, Any] = None) -> None:
        """
        Register a parser implementation.

        Args:
            name: Parser type name
            implementation: Implementation class (optional if module_path is provided)
            module_path: Module path for lazy loading (required if implementation is None)
            class_name: Class name for lazy loading (required if implementation is None)
            metadata: Additional metadata
        """
        registry = cls._registries['parser']
        if implementation:
            registry.register(name, implementation, metadata=metadata)
        elif module_path and class_name:
            registry.register_lazy(name, module_path, class_name, metadata=metadata)
        else:
            raise ValueError("Either implementation or module_path+class_name must be provided")

    @classmethod
    def register_visitor(cls, name: str, implementation=None, module_path=None, class_name=None,
                         metadata: Dict[str, Any] = None) -> None:
        """
        Register a visitor implementation.

        Args:
            name: Visitor type name
            implementation: Implementation class (optional if module_path is provided)
            module_path: Module path for lazy loading (required if implementation is None)
            class_name: Class name for lazy loading (required if implementation is None)
            metadata: Additional metadata
        """
        registry = cls._registries['visitor']
        if implementation:
            registry.register(name, implementation, metadata=metadata)
        elif module_path and class_name:
            registry.register_lazy(name, module_path, class_name, metadata=metadata)
        else:
            raise ValueError("Either implementation or module_path+class_name must be provided")

    def __init__(self, static_data=None):
        """
        Initialize the configurator.

        Args:
            static_data: Optional static analysis data
        """
        self.static_data = static_data
        self.logger = logging.getLogger(__name__)

        # Initialize configuration systems
        self.config = Configuration.get_instance()
        self.config_manager = None

        # Component configurations
        self.llm_config = LLMConfiguration(
            model_type="ollama",
            model_name="llama3.2:3b",
            strategy_type="single_action",
            parser_type=ParserType.DROIDBOT,
            max_tokens=800,
            temperature=0.2
        )

        # Component class references
        self.parser_class = None
        self.visitor_class = None
        self.strategy_class = None

        # Component parameters
        self.parser_kwargs = {}
        self.visitor_kwargs = {}
        self.strategy_kwargs = {}

        # Initialize default configuration
        self._initialize_default_configuration()
        
        # Register built-in components if not already registered
        self._initialize_registries()

    def _initialize_registries(self):
        """Initialize component registries with built-in components if not already registered."""
        # Register LLM types
        if not self._registries['llm'].get_names():
            self._registries['llm'].register_lazy('ollama', 'rvandroid.llm.ollama_llm', 'OllamaLLM')
            self._registries['llm'].register_lazy('huggingface', 'rvandroid.llm.huggingface_llm', 'HuggingFaceLLM')
            self._registries['llm'].register_lazy('dspy', 'rvandroid.llm.dspy_llm', 'DSPyLLM')
            self._registries['llm'].register_lazy('langchain', 'rvandroid.llm.langchain_llm', 'LangchainLLM')
            self._registries['llm'].register_lazy('frontier', 'rvandroid.llm.frontier_models', 'FrontierModel')

        # Register strategy types
        if not self._registries['strategy'].get_names():
            self._registries['strategy'].register_lazy(
                'basic', 'rvandroid.llm.prompt.prompt_strategy_basic_001', 'BasicPromptStrategy001')
            self._registries['strategy'].register_lazy(
                'dspy', 'rvandroid.llm.prompt.prompt_strategy_dspy', 'DSPyPromptStrategy')
            self._registries['strategy'].register_lazy(
                'single_action', 'rvandroid.llm.prompt.single_action_prompt_strategy', 'SingleActionPromptStrategy')
            self._registries['strategy'].register_lazy(
                'dspy_single_action', 'rvandroid.llm.prompt.dspy_single_action_prompt_strategy', 'DSPySingleActionPromptStrategy')
            self._registries['strategy'].register_lazy(
                'composable', 'rvandroid.llm.prompt.composable_prompt_strategy', 'ComposablePromptStrategy')
            self._registries['strategy'].register_lazy(
                'composable_single_action', 'rvandroid.llm.prompt.composable_single_action_strategy', 'ComposableSingleActionStrategy')
            self._registries['strategy'].register_lazy(
                'flow_based_batch_action', 'rvandroid.llm.prompt.flow_based_batch_action_strategy', 'FlowBasedBatchActionStrategy')

        # Register parser types
        if not self._registries['parser'].get_names():
            self._registries['parser'].register_lazy(
                'droidbot', 'rvandroid.parser.screen.droidbot.droidbot_parser', 'DroidBotParser')
            self._registries['parser'].register_lazy(
                'uiautomator', 'rvandroid.parser.screen.uiautomator.uiautomator_parser', 'UIAutomator2Parser')

        # Register visitor types
        if not self._registries['visitor'].get_names():
            self._registries['visitor'].register_lazy(
                'basic', 'rvandroid.parser.screen.visitor.basic_visitor', 'BasicTextVisitor')
            self._registries['visitor'].register_lazy(
                'enhanced', 'rvandroid.parser.screen.visitor.text_visitor', 'TextVisitor')
            self._registries['visitor'].register_lazy(
                'detailed', 'rvandroid.parser.screen.visitor.enhanced_visitor', 'EnhancedTextVisitor')

    def _initialize_default_configuration(self):
        """Initialize default component configuration."""
        # Set default parser class
        from rvandroid.parser.screen.droidbot.droidbot_parser import DroidBotParser
        self.parser_class = DroidBotParser

        # Set default visitor class
        from rvandroid.parser.screen.visitor.text_visitor import TextVisitor
        self.visitor_class = TextVisitor

        # Set default strategy class
        from rvandroid.llm.prompt.prompt_strategy_basic_001 import BasicPromptStrategy001
        self.strategy_class = BasicPromptStrategy001

    def set_llm(self, llm_type: str, model: str = None, **kwargs) -> 'ComponentConfigurator':
        """
        Set the language model type and model to be used.

        Args:
            llm_type: Type of LLM (ollama, huggingface, dspy, langchain, frontier)
            model: Name of the model
            **kwargs: Additional LLM-specific parameters

        Returns:
            Self for method chaining

        Raises:
            ValueError: If LLM type is unknown
        """
        if not self._registries['llm'].has(llm_type):
            raise ValueError(f"Unknown LLM type: {llm_type}. Options: {self._registries['llm'].get_names()}")

        # Update LLM configuration
        self.llm_config.model_type = llm_type

        # If model not specified, use first available model
        if not model:
            model = self.LLM_MODELS.get(llm_type, [])[0] if self.LLM_MODELS.get(llm_type) else None

        self.llm_config.model_name = model

        # Process specific parameters
        if "base_url" in kwargs:
            self.llm_config.kwargs["base_url"] = kwargs.pop("base_url")
        if "api_key" in kwargs:
            self.llm_config.kwargs["api_key"] = kwargs.pop("api_key")
        if "provider" in kwargs:
            self.llm_config.kwargs["provider"] = kwargs.pop("provider")
        if "temperature" in kwargs:
            self.llm_config.temperature = kwargs.pop("temperature")
        if "max_tokens" in kwargs:
            self.llm_config.max_tokens = kwargs.pop("max_tokens")

        # Store other parameters
        for key, value in kwargs.items():
            self.llm_config.kwargs[key] = value

        return self

    def set_strategy(self, strategy_type: str, **kwargs) -> 'ComponentConfigurator':
        """
        Set the prompt strategy to be used.

        Args:
            strategy_type: Type of strategy (basic, dspy, single_action, etc.)
            **kwargs: Additional strategy parameters

        Returns:
            Self for method chaining

        Raises:
            ValueError: If strategy type is unknown
        """
        if not self._registries['strategy'].has(strategy_type):
            raise ValueError(
                f"Unknown strategy type: {strategy_type}. Options: {self._registries['strategy'].get_names()}"
            )

        # Update strategy configuration
        self.llm_config.strategy_type = strategy_type

        # Import the strategy class dynamically
        strategy_class = self._registries['strategy'].get(strategy_type)
        if not strategy_class:
            raise ValueError(f"Failed to load strategy class for '{strategy_type}'")
        
        self.strategy_class = strategy_class

        # Store strategy parameters
        self.strategy_kwargs = kwargs

        return self

    def set_parser(self, parser_type: str, **kwargs) -> 'ComponentConfigurator':
        """
        Set the parser to be used.

        Args:
            parser_type: Type of parser (droidbot, uiautomator)
            **kwargs: Additional parser parameters

        Returns:
            Self for method chaining

        Raises:
            ValueError: If parser type is unknown
        """
        if not self._registries['parser'].has(parser_type):
            raise ValueError(f"Unknown parser type: {parser_type}. Options: {self._registries['parser'].get_names()}")

        # Import the parser class dynamically
        parser_class = self._registries['parser'].get(parser_type)
        if not parser_class:
            raise ValueError(f"Failed to load parser class for '{parser_type}'")
        
        self.parser_class = parser_class

        # Update parser type in LLM configuration
        if parser_type == "droidbot":
            self.llm_config.parser_type = ParserType.DROIDBOT
        elif parser_type == "uiautomator":
            self.llm_config.parser_type = ParserType.UIAUTOMATOR

        # Store parser parameters
        self.parser_kwargs = kwargs

        return self

    def set_visitor(self, visitor_type: str, **kwargs) -> 'ComponentConfigurator':
        """
        Set the visitor to be used.

        Args:
            visitor_type: Type of visitor (basic, enhanced, detailed)
            **kwargs: Additional visitor parameters

        Returns:
            Self for method chaining

        Raises:
            ValueError: If visitor type is unknown
        """
        if not self._registries['visitor'].has(visitor_type):
            raise ValueError(f"Unknown visitor type: {visitor_type}. Options: {self._registries['visitor'].get_names()}")

        # Import the visitor class dynamically
        visitor_class = self._registries['visitor'].get(visitor_type)
        if not visitor_class:
            raise ValueError(f"Failed to load visitor class for '{visitor_type}'")
        
        self.visitor_class = visitor_class

        # Store visitor parameters
        self.visitor_kwargs = kwargs

        return self

    def create_parser(self) -> AbstractScreenParser:
        """
        Create an instance of the configured parser with the configured visitor.

        Returns:
            AbstractScreenParser instance

        Raises:
            ValueError: If parser class is not configured
        """
        if not self.parser_class:
            raise ValueError("Parser class not configured")
        return self.parser_class(self.visitor_class)

    def create_visitor(self, static_data=None, activity: str = "") -> BaseScreenVisitor:
        """
        Create an instance of the configured visitor.

        Args:
            static_data: Static analysis data (optional)
            activity: Current activity name (optional)

        Returns:
            BaseScreenVisitor instance

        Raises:
            ValueError: If visitor class is not configured
        """
        if not self.visitor_class:
            raise ValueError("Visitor class not configured")

        # Use provided static data or fall back to the instance's static data
        static_data = static_data or self.static_data

        kwargs = self.visitor_kwargs.copy()
        return self.visitor_class(static_data, activity, **kwargs)

    def create_strategy(self, static_data=None) -> Any:
        """
        Create an instance of the configured prompt strategy.

        Args:
            static_data: Static analysis data (optional)

        Returns:
            Strategy instance

        Raises:
            ValueError: If strategy class is not configured
        """
        if not self.strategy_class:
            raise ValueError("Strategy class not configured")

        # Use provided static data or fall back to the instance's static data
        static_data = static_data or self.static_data

        kwargs = self.strategy_kwargs.copy()
        return self.strategy_class(static_data, self.create_parser(), **kwargs)

    def create_llm(self):
        """
        Create an LLM instance based on current configuration.

        Returns:
            LanguageModel instance

        Raises:
            ValueError: If LLM creation fails
        """
        # Import dynamically to avoid circular imports
        from rvandroid.llm.model_factory import ModelFactory

        kwargs = self.llm_config.kwargs.copy()

        # Add standard parameters
        model_type = self.llm_config.model_type
        model_name = self.llm_config.model_name

        return ModelFactory.create(model_type, model_name, **kwargs)

    def from_config(self, config_file: str = None) -> 'ComponentConfigurator':
        """
        Configure components from a configuration file.

        Args:
            config_file: Path to configuration file

        Returns:
            Self for method chaining
        """
        if config_file and os.path.exists(config_file):
            self.config.load_from_file(config_file)

        # Configure LLM
        llm_type = self.config.get_str("llm.type", "ollama")
        llm_model = self.config.get_str("llm.model", None)
        llm_kwargs = {}

        if self.config.get("llm.base_url"):
            llm_kwargs["base_url"] = self.config.get_str("llm.base_url")
        if self.config.get("llm.api_key"):
            llm_kwargs["api_key"] = self.config.get_str("llm.api_key")
        if self.config.get("llm.temperature"):
            llm_kwargs["temperature"] = self.config.get("llm.temperature")
        if self.config.get("llm.max_tokens"):
            llm_kwargs["max_tokens"] = self.config.get("llm.max_tokens")

        self.set_llm(llm_type, llm_model, **llm_kwargs)

        # Configure strategy
        strategy_type = self.config.get_str("strategy.type", "composable_single_action")
        strategy_kwargs = {}
        
        # Extract strategy-specific configuration
        strategy_section = self.config.get("strategy", {})
        if isinstance(strategy_section, dict):
            for key, value in strategy_section.items():
                if key != "type":
                    strategy_kwargs[key] = value
                    
        self.set_strategy(strategy_type, **strategy_kwargs)

        # Configure parser
        parser_type = self.config.get_str("parser.type", "droidbot")
        parser_kwargs = {}
        
        # Extract parser-specific configuration
        parser_section = self.config.get("parser", {})
        if isinstance(parser_section, dict):
            for key, value in parser_section.items():
                if key != "type":
                    parser_kwargs[key] = value
                    
        self.set_parser(parser_type, **parser_kwargs)

        # Configure visitor
        visitor_type = self.config.get_str("visitor.type", "enhanced")
        visitor_kwargs = {}
        
        # Extract visitor-specific configuration
        visitor_section = self.config.get("visitor", {})
        if isinstance(visitor_section, dict):
            for key, value in visitor_section.items():
                if key != "type":
                    visitor_kwargs[key] = value
                    
        self.set_visitor(visitor_type, **visitor_kwargs)

        return self

    def to_config_dict(self) -> Dict[str, Any]:
        """
        Convert configurator state to configuration dictionary.

        Returns:
            Dictionary for configuration file
        """
        return {
            "llm": {
                "type": self.llm_config.model_type,
                "model": self.llm_config.model_name,
                "temperature": self.llm_config.temperature,
                "max_tokens": self.llm_config.max_tokens,
                **self.llm_config.kwargs
            },
            "strategy": {
                "type": self.llm_config.strategy_type,
                **self.strategy_kwargs
            },
            "parser": {
                "type": self.llm_config.parser_type.name.lower(),
                **self.parser_kwargs
            },
            "visitor": {
                "type": self._get_visitor_type_name(),
                **self.visitor_kwargs
            }
        }

    def _get_visitor_type_name(self) -> str:
        """
        Get visitor type name from class.

        Returns:
            Visitor type name or default if not found
        """
        if not self.visitor_class:
            return "enhanced"  # Default
            
        visitor_class_name = self.visitor_class.__name__
        
        for name in self._registries['visitor'].get_names():
            visitor_class = self._registries['visitor'].get(name)
            if visitor_class and visitor_class.__name__ == visitor_class_name:
                return name
                
        return "enhanced"  # Default
        
    def _get_config_manager(self):
        """
        Get or initialize the configuration manager.
        
        Returns:
            Initialized ConfigurationManager instance
        """
        if self.config_manager is None:
            # Import locally to avoid circular import
            from rvandroid.config.configuration_manager import ConfigurationManager
            self.config_manager = ConfigurationManager()
        return self.config_manager

    def save_to_config_file(self, filename: str) -> bool:
        """
        Save current configuration to file.

        Args:
            filename: Path to save configuration

        Returns:
            True if saved successfully, False otherwise
        """
        config_dict = self.to_config_dict()

        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            with open(filename, 'w') as f:
                json.dump(config_dict, f, indent=2)

            self.logger.info(f"Configuration saved to {filename}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False

    def describe_configuration(self) -> Dict[str, Any]:
        """
        Return a detailed description of the current configuration.

        Returns:
            Dictionary with configuration details
        """
        strategy_class = self.strategy_class
        parser_class = self.parser_class
        visitor_class = self.visitor_class

        return {
            "llm": {
                "type": self.llm_config.model_type,
                "model": self.llm_config.model_name,
                "max_tokens": self.llm_config.max_tokens,
                "temperature": self.llm_config.temperature,
                "strategy_type": self.llm_config.strategy_type,
                "parser_type": self.llm_config.parser_type.name,
                "kwargs": self.llm_config.kwargs
            },
            "strategy": strategy_class.__name__ if strategy_class else "None",
            "parser": parser_class.__name__ if parser_class else "None",
            "visitor": visitor_class.__name__ if visitor_class else "None",
            "strategy_kwargs": self.strategy_kwargs,
            "parser_kwargs": self.parser_kwargs,
            "visitor_kwargs": self.visitor_kwargs
        }

    def get_available_llm_types(self) -> List[str]:
        """
        Return available LLM types.

        Returns:
            List of LLM type names
        """
        return self._registries['llm'].get_names()

    def get_available_strategy_types(self) -> List[str]:
        """
        Return available strategy types.

        Returns:
            List of strategy type names
        """
        return self._registries['strategy'].get_names()

    def get_available_parser_types(self) -> List[str]:
        """
        Return available parser types.

        Returns:
            List of parser type names
        """
        return self._registries['parser'].get_names()

    def get_available_visitor_types(self) -> List[str]:
        """
        Return available visitor types.

        Returns:
            List of visitor type names
        """
        return self._registries['visitor'].get_names()

    def get_available_models(self, llm_type: str) -> List[str]:
        """
        Return available models for an LLM type.

        Args:
            llm_type: Type of LLM

        Returns:
            List of model names
        """
        return self.LLM_MODELS.get(llm_type, [])
