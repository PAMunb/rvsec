"""Unified framework for prompt generation.

This module defines the PromptFramework class, which coordinates the
prompt generation process by integrating information gathering, template
management, and strategy execution.
"""

from typing import Any, Dict, List, Optional
import logging

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
from rvandroid.llm.prompt.template.jinja_repository import Jinja2TemplateRepository
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
    
    This implementation uses Jinja2 for template rendering, providing advanced
    templating capabilities while maintaining compatibility with the XML-based
    template structure.
    
    Architecture Notes:
    ------------------
    - The framework uses ComponentConfigurator directly for strategy management,
      eliminating the need for a separate StrategyRegistry
    - This design creates a single source of truth for component registration
    - The framework acts as a facade over the underlying components, providing
      a simplified interface for prompt generation
    """

    def __init__(
            self,
            information_manager: InformationManager,
            template_repository: Jinja2TemplateRepository,
            config: ComponentConfigurator
    ):
        """Initialize the prompt framework.
        
        Args:
            information_manager: Manager for information fragments.
            template_repository: Repository for templates using Jinja2.
            config: Component configuration that manages strategies.
        """
        # Store components
        self.information_manager = information_manager
        self.template_repository = template_repository
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
    def create(cls, config: Optional[ComponentConfigurator] = None) -> 'PromptFramework':
        """Create and configure a new prompt framework with default components.
        
        This factory method instantiates all necessary components and registers
        default strategies with the provided ComponentConfigurator. It handles
        the initialization of the entire prompt generation system.
        
        Args:
            config: Configuration for components (optional).
            
        Returns:
            Configured PromptFramework instance.
        """
        # Create a default config if not provided
        if config is None:
            config = ComponentConfigurator()
            
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

        # Create Jinja2-based template repository
        template_repository = Jinja2TemplateRepository()

        # Get existing strategy types before registering defaults
        # This prevents overwriting custom strategies
        existing_strategy_types = config.get_available_strategy_types()
        
        # Register default strategies if they don't already exist
        if PromptStrategyType.STANDARD not in existing_strategy_types:
            standard_strategy = StandardStrategy(
                information_manager=information_manager,
                template_repository=template_repository
            )
            config.register_strategy(PromptStrategyType.STANDARD, implementation=standard_strategy)
            
        if PromptStrategyType.BATCH_ACTION not in existing_strategy_types:
            batch_strategy = BatchActionStrategy(
                information_manager=information_manager,
                template_repository=template_repository
            )
            config.register_strategy(PromptStrategyType.BATCH_ACTION, implementation=batch_strategy)

        # Create framework
        framework = cls(
            information_manager=information_manager,
            template_repository=template_repository,
            config=config
        )

        # Configure components
        framework.configure(config)

        return framework

    def configure(self, config: ComponentConfigurator) -> None:
        """Configure the framework and its components.
        
        This method updates the configuration of all components managed by the
        framework, ensuring that system-wide configuration changes are propagated.
        
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

    def register_information_fragment(self, fragment) -> None:
        """Register an information fragment.
        
        Args:
            fragment: The information fragment to register.
        """
        if self.information_manager:
            self.information_manager.register_fragment(fragment)

    def register_strategy(self, strategy) -> None:
        """Register a prompt generation strategy.
        
        This method registers the strategy directly with the ComponentConfigurator.
        
        Args:
            strategy: The prompt strategy to register.
        """
        if strategy and hasattr(strategy, 'name'):
            self.config.register_strategy(strategy.name, implementation=strategy)
            self.logger.info(f"Registered strategy: {strategy.name}")

    def get_strategy(self, name: Optional[str] = None) -> Optional:
        """Get a strategy implementation by name.
        
        Args:
            name: The name of the strategy to retrieve. If None, uses the default
                 strategy specified in the LLM configuration.
                 
        Returns:
            The strategy implementation, or None if not found.
        """
        # Use default from config if name not provided
        if name is None:
            if hasattr(self.config, 'llm_config') and self.config.llm_config:
                name = self.config.llm_config.strategy_type
            else:
                name = PromptStrategyType.STANDARD
        print(f" *** strategy_name = {name}")

        # Get strategy from ComponentConfigurator
        try:
            xxx = self.config._registries['strategy'].get(name)
            print(f" *** strategy = {xxx}")
            return self.config.create_strategy(strategy_type=name)
        except Exception as e:
            self.logger.error(f"Error getting strategy '{name}': {e}")
            
            # Fall back to standard strategy if possible
            if name != PromptStrategyType.STANDARD:
                try:
                    return self.config.create_strategy(strategy_type=PromptStrategyType.STANDARD)
                except Exception:
                    self.logger.error("Standard strategy not available for fallback")
                    
            return None

    def generate_prompt(
            self,
            state: Dict[str, Any],
            context: Optional[Dict[str, Any]] = None
    ) -> List[LLMMessage]:
        """Generate a prompt using the appropriate strategy.
        
        This is the main method for prompt generation. It selects the appropriate
        strategy based on configuration or defaults, and delegates the prompt
        generation to that strategy.
        
        Args:
            state: Current application state containing all relevant information.
            context: Additional context information for prompt generation.
            
        Returns:
            List of LLMMessage objects forming the complete prompt.
        """
        # Get the appropriate strategy name
        if self.config and hasattr(self.config, 'llm_config') and self.config.llm_config:
            strategy_name = self.config.llm_config.strategy_type
        else:
            strategy_name = PromptStrategyType.STANDARD
            
        try:
            # Get the strategy implementation
            strategy = self.get_strategy(strategy_name)

            if strategy is None:
                self.logger.error(f"Strategy not found: {strategy_name}")
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