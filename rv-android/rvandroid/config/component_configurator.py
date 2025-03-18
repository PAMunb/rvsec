# rvandroid/config/component_configurator.py
import logging
from typing import Dict, Any, Type, Optional, List, Union

from rvandroid.llm.dspy_llm import DSPyLLM
from rvandroid.llm.frontier_models import FrontierModel
from rvandroid.llm.huggingface_llm import HuggingFaceLLM
from rvandroid.llm.langchain_llm import LangchainLLM
from rvandroid.llm.llm import LanguageModel
from rvandroid.llm.model_factory import ModelFactory
from rvandroid.llm.ollama_llm import OllamaLLM
from rvandroid.llm.prompt.composable_prompt_strategy import ComposablePromptStrategy
from rvandroid.llm.prompt.composable_single_action_strategy import ComposableSingleActionStrategy
from rvandroid.llm.prompt.dspy_single_action_prompt_strategy import DSPySingleActionPromptStrategy
from rvandroid.llm.prompt.prompt_strategy import PromptStrategy
from rvandroid.llm.prompt.prompt_strategy_basic_001 import BasicPromptStrategy001
from rvandroid.llm.prompt.prompt_strategy_dspy import DSPyPromptStrategy
from rvandroid.llm.prompt.single_action_prompt_strategy import SingleActionPromptStrategy
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser
from rvandroid.parser.screen.droidbot.droidbot_parser import DroidBotParser
from rvandroid.parser.screen.parser_factory import ParserType
from rvandroid.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
from rvandroid.parser.screen.visitor.base_visitor import BaseScreenVisitor
from rvandroid.parser.screen.visitor.basic_visitor import BasicTextVisitor
from rvandroid.parser.screen.visitor.enhanced_visitor import NewEnhancedTextVisitor
from rvandroid.parser.screen.visitor.text_visitor import EnhancedTextVisitor

logger = logging.getLogger(__name__)


class ComponentConfigurator:
    """
    The ComponentConfigurator class is responsible for managing the configuration
    of system components within the rvandroid framework. It provides a centralized
    mechanism for initializing and applying configurations dynamically.

    ### Architectural Decisions:
    - Uses a modular approach to allow flexible configuration of different components.
    - Supports environment-based and runtime configuration overrides.
    - Ensures consistency by validating and applying settings before execution.

    ### Role in the System:
    - Centralizes component configuration to avoid hardcoded settings in individual modules.
    - Enables dynamic adjustments to experimental parameters and tool integrations.
    - Supports extensibility, allowing new configurations to be easily incorporated.
    - Plays a crucial role in ensuring that experiments, analysis tools, and LLM integrations
      are properly configured before execution.
    """

    LLM_TYPES = {
        "ollama": OllamaLLM,
        "huggingface": HuggingFaceLLM,
        "dspy": DSPyLLM,
        "langchain": LangchainLLM,
        "frontier": FrontierModel
    }

    STRATEGY_TYPES = {
        "basic": BasicPromptStrategy001,
        "dspy": DSPyPromptStrategy,
        "single_action": SingleActionPromptStrategy,
        "dspy_single_action": DSPySingleActionPromptStrategy,
        "composable": ComposablePromptStrategy,
        "composable_single_action": ComposableSingleActionStrategy
    }

    PARSER_TYPES = {
        "droidbot": DroidBotParser,
        "uiautomator": UIAutomator2Parser
    }

    VISITOR_TYPES = {
        "basic": BasicTextVisitor,
        "enhanced": EnhancedTextVisitor,
        "detailed": NewEnhancedTextVisitor
    }

    # Modelos disponíveis por tipo de LLM
    LLM_MODELS = {
        "ollama": OllamaLLM.MODELS,
        "huggingface": HuggingFaceLLM.MODELS,
        "dspy": DSPyLLM.MODELS,
        "langchain": LangchainLLM.MODELS,
        "frontier": FrontierModel.MODELS
    }

    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """
        Inicializa o configurador.

        Args:
            static_data: Dados de análise estática
        """
        self.static_data = static_data
        # self.component_config = ComponentConfig()
        self.llm_config = {
            "type": "ollama",
            "model": OllamaLLM.LLAMA,
            "base_url": "http://localhost:11434",
            "api_key": None,
            "provider": None,
            "extra_params": {}
        }

        # Configuração inicial padrão
        self.parser_class: Optional[Type[AbstractScreenParser]] = DroidBotParser
        self.visitor_class: Optional[Type[BaseScreenVisitor]] = EnhancedTextVisitor
        self.strategy_class: Optional[Type[PromptStrategy]] = BasicPromptStrategy001
        self.parser_kwargs: Dict[str, Any] = {}
        self.visitor_kwargs: Dict[str, Any] = {}
        self.strategy_kwargs: Dict[str, Any] = {}

        self.logger = logger

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
            raise ValueError(f"Tipo de LLM desconhecido: {llm_type}. Opções: {list(self.LLM_TYPES.keys())}")

        self.llm_config["type"] = llm_type

        # Se modelo não foi especificado, use o primeiro modelo disponível
        if not model:
            model = self.LLM_MODELS.get(llm_type, [])[0] if self.LLM_MODELS.get(llm_type) else None

        self.llm_config["model"] = model

        # Processa parâmetros específicos
        if "base_url" in kwargs:
            self.llm_config["base_url"] = kwargs.pop("base_url")
        if "api_key" in kwargs:
            self.llm_config["api_key"] = kwargs.pop("api_key")
        if "provider" in kwargs:
            self.llm_config["provider"] = kwargs.pop("provider")

        # Armazena todos os outros parâmetros
        self.llm_config["extra_params"] = kwargs

        return self

    def set_strategy(self, strategy_type: str, **kwargs) -> 'ComponentConfigurator':
        """
        Define a estratégia de prompt a ser usada.

        Args:
            strategy_type: Tipo de estratégia (basic, dspy, single_action)

        Returns:
            Self para encadeamento de métodos
        """
        if strategy_type not in self.STRATEGY_TYPES:
            raise ValueError(
                f"Tipo de estratégia desconhecido: {strategy_type}. Opções: {list(self.STRATEGY_TYPES.keys())}")

        self.strategy_class = self.STRATEGY_TYPES[strategy_type]
        self.strategy_kwargs = kwargs
        return self

    def set_parser(self, parser_type: str, **kwargs) -> 'ComponentConfigurator':
        """
        Define the parser to be used.

        Args:
            parser_type: Type of parser (droidbot, uiautomator)

        Returns:
            Self for encadeamento de métodos
        """
        if parser_type not in self.PARSER_TYPES:
            raise ValueError(f"Unknown parser type: {parser_type}. Options: {list(self.PARSER_TYPES.keys())}")

        self.parser_class = self.PARSER_TYPES[parser_type]
        self.parser_kwargs = kwargs
        return self

    def set_visitor(self, visitor_type: str, **kwargs) -> 'ComponentConfigurator':
        """
        Define the visitor to be used.

        Args:
            visitor_type: Type of visitor (enhanced)

        Returns:
            Self for method chaining
        """
        if visitor_type not in self.VISITOR_TYPES:
            raise ValueError(f"Unknown visitor type: {visitor_type}. Options: {list(self.VISITOR_TYPES.keys())}")

        self.visitor_class = self.VISITOR_TYPES[visitor_type]
        self.visitor_kwargs = kwargs
        return self

    # def create_service(self) -> LLMActionService:
    #     """
    #     Cria e retorna um LLMActionService configurado.
    #
    #     Returns:
    #         LLMActionService configurado
    #     """
    #     # Prepara os parâmetros para o serviço
    #     llm_type = self.llm_config["type"]
    #     model_name = self.llm_config["model"]
    #
    #     # Prepara os parâmetros específicos para o tipo de LLM
    #     kwargs = self.llm_config["extra_params"].copy()
    #
    #     if llm_type in ["ollama", "dspy", "langchain"]:
    #         kwargs["base_url"] = self.llm_config["base_url"]
    #
    #     if llm_type in ["dspy", "langchain", "frontier"]:
    #         if self.llm_config["provider"]:
    #             kwargs["provider"] = self.llm_config["provider"]
    #
    #     if llm_type in ["frontier"] and self.llm_config["api_key"]:
    #         kwargs["api_key"] = self.llm_config["api_key"]
    #
    #     # Cria o serviço
    #     service = LLMActionService(
    #         static_data=self.static_data,
    #         # model_type=llm_type,
    #         # model_name=model_name,
    #         config=self,
    #         **kwargs
    #     )
    #
    #     return service

    def get_available_llm_types(self) -> List[str]:
        """Retorna os tipos de LLM disponíveis"""
        return list(self.LLM_TYPES.keys())

    def get_available_strategy_types(self) -> List[str]:
        """Retorna os tipos de estratégia disponíveis"""
        return list(self.STRATEGY_TYPES.keys())

    def get_available_parser_types(self) -> List[str]:
        """Retorna os tipos de parser disponíveis"""
        return list(self.PARSER_TYPES.keys())

    def get_available_visitor_types(self) -> List[str]:
        """Retorna os tipos de visitor disponíveis"""
        return list(self.VISITOR_TYPES.keys())

    def get_available_models(self, llm_type: str) -> List[str]:
        """
        Retorna os modelos disponíveis para um tipo de LLM.

        Args:
            llm_type: Tipo de LLM

        Returns:
            Lista de modelos disponíveis
        """
        if llm_type not in self.LLM_MODELS:
            return []
        return self.LLM_MODELS[llm_type]

    def create_parser(self) -> AbstractScreenParser:
        """Create an instance of the configured parser with the configured visitor."""
        if not self.parser_class:
            raise ValueError("Parser class not configured")
        return self.parser_class(self.visitor_class)

    def create_visitor(self, static_data: Optional["StaticAnalysisData"], activity: str) -> BaseScreenVisitor:
        """Create an instance of the configured visitor."""
        if not self.visitor_class:
            raise ValueError("Visitor class not configured")
        kwargs = self.visitor_kwargs.copy()
        return self.visitor_class(static_data, activity, **kwargs)

    def create_strategy(self, static_data: Optional["StaticAnalysisData"] = None) -> PromptStrategy:
        """Create an instance of the configured prompt strategy."""
        if not self.strategy_class:
            raise ValueError("Strategy class not configured")
        kwargs = self.strategy_kwargs.copy()
        return self.strategy_class(static_data, self.create_parser(), **kwargs)

    def create_llm(self):
        if not self.llm_config:
            raise ValueError("LLM not configured")
        kwargs = self.llm_config["extra_params"].copy()
        if self.llm_config["type"] in ["ollama", "dspy", "langchain"]:
            kwargs["base_url"] = self.llm_config["base_url"]
        if self.llm_config["type"] in ["dspy", "langchain", "frontier"]:
            if self.llm_config["provider"]:
                kwargs["provider"] = self.llm_config["provider"]
        if self.llm_config["api_key"]:
            kwargs["api_key"] = self.llm_config["api_key"]
        return ModelFactory.create(
            self.llm_config["type"],
            self.llm_config["model"],
            **kwargs
        )

    def describe_configuration(self) -> Dict[str, Any]:
        """
        Retorna uma descrição detalhada da configuração atual.

        Returns:
            Dicionário com a configuração
        """
        strategy_class = self.strategy_class
        parser_class = self.parser_class
        visitor_class = self.visitor_class

        return {
            "llm": {
                "type": self.llm_config["type"],
                "model": self.llm_config["model"],
                "base_url": self.llm_config["base_url"],
                "provider": self.llm_config["provider"],
                "extra_params": self.llm_config["extra_params"]
            },
            "strategy": strategy_class.__name__ if strategy_class else "None",
            "parser": parser_class.__name__ if parser_class else "None",
            "visitor": visitor_class.__name__ if visitor_class else "None"
        }
