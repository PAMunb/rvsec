"""Unified framework for prompt generation.

This module defines the PromptFramework class, which coordinates the
prompt generation process by integrating information gathering, template
management, and strategy execution.
"""

from typing import Any, Dict, List, Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.config.strategy_config import PromptStrategyConfig
from rv_llm.llm.constants import PromptStrategyType
from rv_llm.llm.data_structures import LLMMessage
from rv_llm.llm.prompt.information.fragment_manager import InformationManager
from rv_llm.llm.prompt.information.fragments.history_fragment import HistoryFragment
from rv_llm.llm.prompt.information.fragments.monitored_operations_fragment import MonitoredOperationsFragment
from rv_llm.llm.prompt.information.fragments.screenshot_fragment import ScreenshotFragment
from rv_llm.llm.prompt.information.fragments.transition_guidance_fragment import TransitionGuidanceFragment
from rv_llm.llm.prompt.information.fragments.ui_elements_fragment import UIElementsFragment
from rv_llm.llm.prompt.template.jinja_repository import Jinja2TemplateRepository


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
            llm_factory=None,
            strategy_factory=None
    ):
        """Initialize the prompt framework.
        
        Args:
            information_manager: Manager for information fragments.
            template_repository: Repository for templates using Jinja2.
            llm_factory: Factory for creating LLM instances.
            strategy_factory: Factory for creating strategy instances.
        """
        # Store components
        self.information_manager = information_manager
        self.template_repository = template_repository
        
        # Use factory pattern for component creation
        # Import factories here to avoid circular imports
        from rv_llm.factories.llm_factory import LLMFactory
        from rv_llm.factories.prompt_strategy_factory import PromptStrategyFactory
        
        self.llm_factory = llm_factory or LLMFactory()
        self.strategy_factory = strategy_factory or PromptStrategyFactory()

        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.prompt.framework",
            {CONTEXT_COMPONENT: "PromptFramework"}
        )

        # Set up error handling
        self.error_handler = ErrorHandler.get_instance()

    @classmethod
    def create(cls, llm_factory=None, strategy_factory=None) -> 'PromptFramework':
        """Create and configure a new prompt framework with default components.
        
        This factory method instantiates all necessary components using the modern
        factory pattern. It handles the initialization of the entire prompt generation system.
        
        Args:
            llm_factory: Optional LLM factory instance.
            strategy_factory: Optional strategy factory instance.
            
        Returns:
            Configured PromptFramework instance.
        """
        # Import factories here to avoid circular imports
        from rv_llm.factories.llm_factory import LLMFactory
        from rv_llm.factories.prompt_strategy_factory import PromptStrategyFactory
        
        # Create factories if not provided
        llm_factory = llm_factory or LLMFactory()
        strategy_factory = strategy_factory or PromptStrategyFactory()

        # Create information manager and fragments
        information_manager = InformationManager()

        # Create and register default fragments
        fragments = [
            # UIPatternFragment(),
            MonitoredOperationsFragment(),
            ScreenshotFragment(),
            HistoryFragment(),
            TransitionGuidanceFragment(),
            UIElementsFragment()
        ]
        information_manager.register_fragments(fragments)

        # Create Jinja2-based template repository
        template_repository = Jinja2TemplateRepository()

        # Create framework
        framework = cls(
            information_manager=information_manager,
            template_repository=template_repository,
            llm_factory=llm_factory,
            strategy_factory=strategy_factory
        )

        return framework

    @ErrorHandler.handle_errors(
        component="PromptFramework",
        phase="configuration"
    )
    def configure(self, config: Optional[PromptStrategyConfig] = None) -> None:
        """Configure the framework and its components.
        
        ### Architectural Decision:
        - Uses typed configuration class instead of dictionary
        - Provides comprehensive component configuration
        - Follows the established architectural pattern from rv-android-core
        
        Args:
            config: Optional typed configuration instance for components.
        """
        self.logger.info("Configuring PromptFramework")
        
        if config is None:
            config = PromptStrategyConfig()
            
        # Validate configuration
        is_valid, errors = config.validate()
        if not is_valid:
            self.logger.warning(f"Configuration validation errors: {errors}")

        # Configure components with validation
        if self.information_manager and hasattr(self.information_manager, 'configure'):
            try:
                self.information_manager.configure(config)
            except Exception as e:
                self.logger.warning(f"Failed to configure information manager: {e}")

        if self.template_repository and hasattr(self.template_repository, 'configure'):
            try:
                # Template repository might use different config format
                template_config = {
                    'template_format': config.template_format,
                    'template_validation': config.template_validation
                }
                self.template_repository.configure(template_config)
            except Exception as e:
                self.logger.warning(f"Failed to configure template repository: {e}")
                
        self.logger.debug("PromptFramework configuration completed")

    @ErrorHandler.handle_errors(
        component="PromptFramework",
        phase="fragment_registration"
    )
    def register_information_fragment(self, fragment) -> None:
        """Register an information fragment.
        
        ### Architectural Decision:
        - Uses error handling decorator pattern for robustness
        - Follows the established architectural pattern from rv-android-core
        
        Args:
            fragment: The information fragment to register.
        """
        if self.information_manager:
            self.information_manager.register_fragment(fragment)
            self.logger.info(f"Registered information fragment: {type(fragment).__name__}")
        else:
            self.logger.warning("Information manager not available for fragment registration")

    @ErrorHandler.handle_errors(
        component="PromptFramework",
        phase="strategy_registration"
    )
    def register_strategy(self, strategy_name: str, strategy_class) -> None:
        """Register a prompt generation strategy with the factory.
        
        ### Architectural Decision:
        - Uses modern factory pattern instead of legacy ComponentConfigurator
        - Provides error handling with decorator pattern
        - Follows the established architectural pattern from rv-android-core
        
        Args:
            strategy_name: The name/type of the strategy to register.
            strategy_class: The strategy class to register.
        """
        if self.strategy_factory and hasattr(self.strategy_factory, 'register_strategy'):
            self.strategy_factory.register_strategy(strategy_name, strategy_class)
            self.logger.info(f"Registered strategy: {strategy_name}")
        else:
            self.logger.warning("Strategy factory not available for registration")

    @ErrorHandler.handle_errors(
        component="PromptFramework", 
        phase="strategy_retrieval"
    )
    def get_strategy(self, name: Optional[str] = None) -> Optional:
        """Get a strategy implementation by name using the factory pattern.
        
        ### Architectural Decision:
        - Uses factory pattern for strategy creation
        - Provides fallback mechanism for robustness
        - Implements proper error handling with decorators
        
        Args:
            name: The name of the strategy to retrieve. If None, uses standard strategy.
                 
        Returns:
            The strategy implementation, or None if not found.
        """
        # Use default strategy if name not provided
        if name is None:
            name = PromptStrategyType.STANDARD
            
        self.logger.debug(f"Retrieving strategy: {name}")

        # Use factory to create strategy
        try:
            if name == PromptStrategyType.STANDARD:
                return self.strategy_factory.create_standard(
                    information_manager=self.information_manager,
                    template_repository=self.template_repository
                )
            elif name == PromptStrategyType.BATCH_ACTION:
                return self.strategy_factory.create_batch_action(
                    information_manager=self.information_manager,
                    template_repository=self.template_repository
                )
            else:
                # Try generic factory method
                return self.strategy_factory.create_strategy(
                    strategy_type=name,
                    information_manager=self.information_manager,
                    template_repository=self.template_repository
                )
        except Exception as e:
            self.logger.error(f"Error creating strategy '{name}': {e}")

            # Fall back to standard strategy if possible
            if name != PromptStrategyType.STANDARD:
                try:
                    self.logger.info("Falling back to standard strategy")
                    return self.strategy_factory.create_standard(
                        information_manager=self.information_manager,
                        template_repository=self.template_repository
                    )
                except Exception as fallback_error:
                    self.logger.error(f"Standard strategy fallback failed: {fallback_error}")

            return None

    @ErrorHandler.handle_errors(
        component="PromptFramework",
        phase="prompt_generation"
    )
    def generate_prompt(
            self,
            state: Dict[str, Any],
            context: Optional[Dict[str, Any]] = None,
            strategy_name: Optional[str] = None
    ) -> List[LLMMessage]:
        """Generate a prompt using the appropriate strategy.
        
        ### Architectural Decision:
        - Uses factory pattern for strategy selection
        - Provides robust error handling with decorator pattern
        - Follows the established architectural pattern from rv-android-core
        - Eliminates dependency on legacy ComponentConfigurator
        
        Args:
            state: Current application state containing all relevant information.
            context: Additional context information for prompt generation.
            strategy_name: Optional strategy name override.
            
        Returns:
            List of LLMMessage objects forming the complete prompt.
        """
        # Determine strategy name from parameter or default
        if strategy_name is None:
            strategy_name = PromptStrategyType.STANDARD
            
        # Extract strategy from context if provided
        if context and 'strategy_type' in context:
            strategy_name = context['strategy_type']

        self.logger.debug(f"Generating prompt with strategy: {strategy_name}")

        # Get the strategy implementation using factory pattern
        strategy = self.get_strategy(strategy_name)

        if strategy is None:
            self.logger.error(f"Strategy not found: {strategy_name}")
            return []

        self.logger.debug(f"Using strategy: {getattr(strategy, 'name', strategy_name)}")

        # Generate the prompt using the strategy
        return strategy.generate_prompt(state, context)
