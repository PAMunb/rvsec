"""Unified framework for prompt generation.

This module defines the PromptFramework class, which coordinates the
prompt generation process by integrating information gathering, template
management, and strategy execution.
"""

from typing import Any, Dict, List, Optional

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.constants import PromptStrategyType
from rvandroid.llm.data_structures import LLMMessage
from rvandroid.llm.prompt.information.fragment_manager import InformationManager
from rvandroid.llm.prompt.information.fragments.history_fragment import HistoryFragment
from rvandroid.llm.prompt.information.fragments.monitored_operations_fragment import MonitoredOperationsFragment
from rvandroid.llm.prompt.information.fragments.screenshot_fragment import ScreenshotFragment
from rvandroid.llm.prompt.information.fragments.transition_guidance_fragment import TransitionGuidanceFragment
from rvandroid.llm.prompt.information.fragments.ui_elements_fragment import UIElementsFragment
from rvandroid.llm.prompt.information.fragments.ui_pattern_fragment import UIPatternFragment
from rvandroid.llm.prompt.strategy.strategies.batch_action_strategy import BatchActionStrategy
from rvandroid.llm.prompt.strategy.strategies.standard_strategy import StandardStrategy
from rvandroid.llm.prompt.strategy.strategy_registry import StrategyRegistry
from rvandroid.llm.prompt.template.xml_repository import XMLTemplateRepository
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class PromptFramework:
    """Unified framework for prompt generation.
    
    The PromptFramework integrates the three layers of the prompt system:
    1. Information gathering through fragments
    2. Template management through repository
    3. Strategy execution for generating prompts
    
    It serves as the central entry point for prompt generation and LLM interaction.
    """

    def __init__(
            self,
            information_manager: InformationManager,
            template_repository: XMLTemplateRepository,
            strategy_registry: StrategyRegistry,
            config: ComponentConfigurator
    ):
        """Initialize the prompt framework.
        
        Args:
            information_manager: Manager for information fragments.
            template_repository: Repository for templates.
            strategy_registry: Registry for prompt strategies.
            config: Component configuration.
        """
        # Store components
        self.information_manager = information_manager
        self.template_repository = template_repository
        self.strategy_registry = strategy_registry
        self.config = config

        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.prompt.framework",
            {CONTEXT_COMPONENT: "PromptFramework"}
        )

        # Set up error handling
        self.error_handler = ErrorHandler.get_instance()

    @classmethod
    def create(cls, config: ComponentConfigurator) -> 'PromptFramework':
        """Create and configure a new prompt framework with default components.
        
        Args:
            config: Configuration for components (optional).
            
        Returns:
            Configured PromptFramework instance.
        """
        # Create information manager and fragments
        information_manager = InformationManager()

        # Create and register default fragments
        fragments = [
            UIElementsFragment(),
            UIPatternFragment(),
            MonitoredOperationsFragment(),
            ScreenshotFragment(),
            HistoryFragment(),
            TransitionGuidanceFragment()
        ]
        information_manager.register_fragments(fragments)

        # Create template repository
        template_repository = XMLTemplateRepository()

        # Create strategy registry
        strategy_registry = StrategyRegistry()

        # Create and register default strategies
        strategies = [
            StandardStrategy(
                information_manager=information_manager,
                template_repository=template_repository
            ),
            BatchActionStrategy(
                information_manager=information_manager,
                template_repository=template_repository
            )
        ]

        for strategy in strategies:
            strategy_registry.register_strategy(strategy)

        # Create language model (if configured)
        if config is None:
            config = ComponentConfigurator()

        # Create framework
        framework = cls(
            information_manager=information_manager,
            template_repository=template_repository,
            strategy_registry=strategy_registry,
            config=config
        )

        # Configure components if configuration provided
        if config is not None:
            framework.configure(config)

        return framework

    def configure(self, config: ComponentConfigurator) -> None:
        """Configure the framework and its components.
        
        Args:
            config: Configuration for components.
        """
        self.logger.info("Configuring PromptFramework")
        self.config = config

        # Configure components
        if self.information_manager:
            self.information_manager.configure(config)

        if self.template_repository:
            self.template_repository.configure(config)

        if self.strategy_registry:
            self.strategy_registry.configure(config)

    def register_information_fragment(self, fragment) -> None:
        """Register an information fragment.
        
        Args:
            fragment: The information fragment to register.
        """
        if self.information_manager:
            self.information_manager.register_fragment(fragment)

    def register_strategy(self, strategy) -> None:
        """Register a prompt generation strategy.
        
        Args:
            strategy: The prompt strategy to register.
        """
        if self.strategy_registry:
            self.strategy_registry.register_strategy(strategy)

    def generate_prompt(
            self,
            state: Dict[str, Any],
            context: Optional[Dict[str, Any]] = None
    ) -> List[LLMMessage]:
        """Generate a prompt using the specified strategy.
        
        Args:
            state: Current application state.
            context: Additional context information.
            
        Returns:
            List of LLMMessage objects.
        """
        # Get the appropriate strategy
        if self.config and self.config.llm_config:
            strategy_name = self.config.llm_config.strategy_type
        else:
            strategy_name = PromptStrategyType.DEFAULT
        try:
            strategy = self.strategy_registry.get_strategy(strategy_name)

            if strategy is None:
                self.logger.error(f"Strategy not found: {strategy_name}")
                # Fall back to standard strategy
                strategy = self.strategy_registry.get_strategy(PromptStrategyType.DEFAULT)

                if strategy is None:
                    self.logger.error("No strategy available")
                    return []

            self.logger.debug(f"Using strategy: {strategy.name}")

            # Generate the prompt using the strategy
            return strategy.generate_prompt(state, context)
        except Exception as e:
            self.logger.error(f"Error generating prompt: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "PromptFramework",
                    "function": "generate_prompt",
                    "strategy": strategy_name
                }
            )
            return []
