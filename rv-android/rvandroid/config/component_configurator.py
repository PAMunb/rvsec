# rvandroid/config/component_configurator.py
"""
Component configurator for managing component configurations.
"""
import json
import logging
import os
from typing import Dict, List, Any

from rvandroid.config.configuration import Configuration
from rvandroid.config.configuration_manager import ConfigurationManager
from rvandroid.llm.llm_config import LLMConfiguration
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser
from rvandroid.parser.screen.parser_factory import ParserType
from rvandroid.parser.screen.visitor.base_visitor import BaseScreenVisitor


class ComponentConfigurator:
    """
    A sophisticated configuration management system for dynamically configuring and composing experimental components.

    ### Architectural Decisions:
    - Implements a flexible, modular approach to component configuration
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

    # Component type registries
    LLM_TYPES = {
        "ollama": "OllamaLLM",
        "huggingface": "HuggingFaceLLM",
        "dspy": "DSPyLLM",
        "langchain": "LangchainLLM",
        "frontier": "FrontierModel"
    }

    STRATEGY_TYPES = {
        "basic": "BasicPromptStrategy001",
        "dspy": "DSPyPromptStrategy",
        "single_action": "SingleActionPromptStrategy",
        "dspy_single_action": "DSPySingleActionPromptStrategy",
        "composable": "ComposablePromptStrategy",
        "composable_single_action": "ComposableSingleActionStrategy"
    }

    PARSER_TYPES = {
        "droidbot": "DroidBotParser",
        "uiautomator": "UIAutomator2Parser"
    }

    VISITOR_TYPES = {
        "basic": "BasicTextVisitor",
        "enhanced": "EnhancedTextVisitor",
        "detailed": "NewEnhancedTextVisitor"
    }

    # Model registries
    LLM_MODELS = {
        "ollama": ["llama3.2:3b", "gemma3:4b", "phi3.5:3.8b"],
        "huggingface": ["meta-llama/Meta-Llama-3.1-8B-Instruct"],
        "dspy": ["meta-llama/Meta-Llama-3.1-8B-Instruct"],
        "langchain": ["meta-llama/Meta-Llama-3.1-8B-Instruct"],
        "frontier": ["claude-3-opus-20240229", "claude-3-sonnet-20240229"]
    }

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
        self.config_manager = ConfigurationManager()

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

    def _initialize_default_configuration(self):
        """Initialize default component configuration."""
        # Set default parser class
        from rvandroid.parser.screen.droidbot.droidbot_parser import DroidBotParser
        self.parser_class = DroidBotParser

        # Set default visitor class
        from rvandroid.parser.screen.visitor.text_visitor import EnhancedTextVisitor
        self.visitor_class = EnhancedTextVisitor

        # Set default strategy class
        from rvandroid.llm.prompt.prompt_strategy_basic_001 import BasicPromptStrategy001
        self.strategy_class = BasicPromptStrategy001

    def set_llm(self, llm_type: str, model: str = None, **kwargs) -> 'ComponentConfigurator':
        """
        Define o tipo de LLM e modelo a ser usado.

        Args:
            llm_type: Tipo de LLM (ollama, huggingface, dspy, langchain, frontier)
            model: Nome do modelo
            **kwargs: Parâmetros adicionais específicos do LLM

        Returns:
            Self para encadeamento de métodos
        """
        if llm_type not in self.LLM_TYPES:
            raise ValueError(f"Unknown LLM type: {llm_type}. Options: {list(self.LLM_TYPES.keys())}")

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
            strategy_type: Type of strategy (basic, dspy, single_action)
            **kwargs: Additional strategy parameters

        Returns:
            Self for method chaining
        """
        if strategy_type not in self.STRATEGY_TYPES:
            raise ValueError(
                f"Unknown strategy type: {strategy_type}. Options: {list(self.STRATEGY_TYPES.keys())}"
            )

        # Update strategy configuration
        self.llm_config.strategy_type = strategy_type

        # Import the strategy class dynamically
        # TODO remover
        strategy_class_name = self.STRATEGY_TYPES[strategy_type]

        # Import different strategies based on type
        if strategy_type == "basic":
            from rvandroid.llm.prompt.prompt_strategy_basic_001 import BasicPromptStrategy001
            self.strategy_class = BasicPromptStrategy001
        elif strategy_type == "dspy":
            from rvandroid.llm.prompt.prompt_strategy_dspy import DSPyPromptStrategy
            self.strategy_class = DSPyPromptStrategy
        elif strategy_type == "single_action":
            from rvandroid.llm.prompt.single_action_prompt_strategy import SingleActionPromptStrategy
            self.strategy_class = SingleActionPromptStrategy
        elif strategy_type == "dspy_single_action":
            from rvandroid.llm.prompt.dspy_single_action_prompt_strategy import DSPySingleActionPromptStrategy
            self.strategy_class = DSPySingleActionPromptStrategy
        elif strategy_type == "composable":
            from rvandroid.llm.prompt.composable_prompt_strategy import ComposablePromptStrategy
            self.strategy_class = ComposablePromptStrategy
        elif strategy_type == "composable_single_action":
            from rvandroid.llm.prompt.composable_single_action_strategy import ComposableSingleActionStrategy
            self.strategy_class = ComposableSingleActionStrategy

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
        """
        if parser_type not in self.PARSER_TYPES:
            raise ValueError(f"Unknown parser type: {parser_type}. Options: {list(self.PARSER_TYPES.keys())}")

        # Import the parser class dynamically
        if parser_type == "droidbot":
            from rvandroid.parser.screen.droidbot.droidbot_parser import DroidBotParser
            self.parser_class = DroidBotParser
        elif parser_type == "uiautomator":
            from rvandroid.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
            self.parser_class = UIAutomator2Parser

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
        """
        if visitor_type not in self.VISITOR_TYPES:
            raise ValueError(f"Unknown visitor type: {visitor_type}. Options: {list(self.VISITOR_TYPES.keys())}")

        # Import the visitor class dynamically
        if visitor_type == "basic":
            from rvandroid.parser.screen.visitor.basic_visitor import BasicTextVisitor
            self.visitor_class = BasicTextVisitor
        elif visitor_type == "enhanced":
            from rvandroid.parser.screen.visitor.text_visitor import EnhancedTextVisitor
            self.visitor_class = EnhancedTextVisitor
        elif visitor_type == "detailed":
            from rvandroid.parser.screen.visitor.enhanced_visitor import NewEnhancedTextVisitor
            self.visitor_class = NewEnhancedTextVisitor

        # Store visitor parameters
        self.visitor_kwargs = kwargs

        return self

    def create_parser(self) -> AbstractScreenParser:
        """Create an instance of the configured parser with the configured visitor."""
        if not self.parser_class:
            raise ValueError("Parser class not configured")
        return self.parser_class(self.visitor_class)

    def create_visitor(self, static_data=None, activity: str = "") -> BaseScreenVisitor:
        """Create an instance of the configured visitor."""
        if not self.visitor_class:
            raise ValueError("Visitor class not configured")

        # Use provided static data or fall back to the instance's static data
        static_data = static_data or self.static_data

        kwargs = self.visitor_kwargs.copy()
        return self.visitor_class(static_data, activity, **kwargs)

    def create_strategy(self, static_data=None) -> Any:
        """Create an instance of the configured prompt strategy."""
        if not self.strategy_class:
            raise ValueError("Strategy class not configured")

        # Use provided static data or fall back to the instance's static data
        static_data = static_data or self.static_data

        kwargs = self.strategy_kwargs.copy()
        return self.strategy_class(static_data, self.create_parser(), **kwargs)

    def create_llm(self):
        """Create an LLM instance based on current configuration."""
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

        self.set_llm(llm_type, llm_model, **llm_kwargs)

        # Configure strategy
        strategy_type = self.config.get_str("strategy.type", "basic")
        self.set_strategy(strategy_type)

        # Configure parser
        parser_type = self.config.get_str("parser.type", "droidbot")
        self.set_parser(parser_type)

        # Configure visitor
        visitor_type = self.config.get_str("visitor.type", "enhanced")
        self.set_visitor(visitor_type)

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
        """Get visitor type name from class."""
        for name, cls_name in self.VISITOR_TYPES.items():
            if self.visitor_class and self.visitor_class.__name__ == cls_name:
                return name
        return "enhanced"  # Default

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
        """Return available LLM types."""
        return list(self.LLM_TYPES.keys())

    def get_available_strategy_types(self) -> List[str]:
        """Return available strategy types."""
        return list(self.STRATEGY_TYPES.keys())

    def get_available_parser_types(self) -> List[str]:
        """Return available parser types."""
        return list(self.PARSER_TYPES.keys())

    def get_available_visitor_types(self) -> List[str]:
        """Return available visitor types."""
        return list(self.VISITOR_TYPES.keys())

    def get_available_models(self, llm_type: str) -> List[str]:
        """
        Return available models for an LLM type.

        Args:
            llm_type: Type of LLM

        Returns:
            List of model names
        """
        return self.LLM_MODELS.get(llm_type, [])
