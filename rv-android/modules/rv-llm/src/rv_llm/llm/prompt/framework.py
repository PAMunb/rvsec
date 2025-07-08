"""
Framework for Prompt Generation

### Architectural Overview:
This module implements a prompt generation framework that coordinates
the prompt generation process through factory patterns, with direct component integration.

### Key Architectural Decisions:
- **Factory Pattern**: Uses factory pattern for strategy and LLM creation
- **Direct Integration**: Direct configuration dependencies
- **Component Composition**: Coordinates information gathering, template management, and strategy execution
- **Error Handling**: Error handling using rv-android-core decorators
- **Configuration**: Uses parameter passing instead of configuration objects

### Role in the System:
- Central coordination point for prompt generation activities
- Factory orchestration for strategy and LLM component creation
- Integration layer between information fragments and template management
- Primary interface for LLM-driven prompt generation workflows

### Design Patterns:
- **Factory Pattern**: Strategy and LLM creation through factories
- **Facade Pattern**: Interface over prompt generation subsystem
- **Strategy Pattern**: Dynamic prompt generation strategy selection
- **Composition Pattern**: Coordinates multiple specialized components
"""

from typing import Any, Dict, List, Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVPromptError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
# from rv_llm import LLMConfig
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
    """
    Framework for prompt generation.
    
    ### Architectural Overview:
    This framework integrates the three layers of the prompt system using
    architecture principles and factory patterns:
    1. **Information Gathering**: Through specialized fragments for different data types
    2. **Template Management**: Through repository pattern with Jinja2 rendering
    3. **Strategy Execution**: Through factory-created strategies for prompt generation
    
    ### Key Features:
    - **Factory-Based Creation**: Uses factory pattern for component creation
    - **Interface**: Facade over prompt generation subsystem
    - **Configuration**: Direct parameter passing instead of configuration objects
    - **Error Handling**: Uses rv-android-core error handling decorators
    - **Template Integration**: Jinja2-based templating with capabilities
    
    ### Role in the System:
    - Central entry point for prompt generation and LLM interaction
    - Coordinates information gathering, template management, and strategy execution
    - Provides interface for different prompt generation strategies
    - Manages component lifecycle and configuration coordination
    
    ### Design Evolution:
    This implementation eliminates ComponentConfigurator dependencies in favor
    of direct factory pattern usage, providing separation of concerns and
    component integration.
    """

    def __init__(
            self,
            information_manager: InformationManager,
            template_repository: Jinja2TemplateRepository,
            config: Optional['LLMConfig']
    ):
        """Initialize the prompt framework.
        
        Args:
            information_manager: Manager for information fragments.
            template_repository: Repository for templates using Jinja2.
            config: LLM configuration.
        """
        # Store components
        self.information_manager = information_manager
        self.template_repository = template_repository

        from rv_llm import LLMConfig
        self.config = config or LLMConfig()

        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.prompt.framework",
            {CONTEXT_COMPONENT: "PromptFramework"}
        )

        # Set up error handling
        self.error_handler = ErrorHandler.get_instance()

    @classmethod
    def create(cls, config: Optional['LLMConfig']) -> 'PromptFramework':
        # Create information manager and fragments
        information_manager = InformationManager()

        # Create and register default fragments
        fragments = [
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
            config=config
        )

        return framework

    @ErrorHandler.handle_errors(
        component="PromptFramework",
        phase="configuration"
    )
    def configure(
            self,
            template_format: str = "jinja2",
            template_validation: bool = True,
            **kwargs
    ) -> None:
        """Configure the framework and its components using direct parameter passing.
        
        ### Architectural Decision:
        - Uses direct parameter passing instead of complex configuration objects
        - Provides simple configuration management following clean architecture principles
        - Eliminates legacy configuration dependencies in favor of modern patterns
        
        Args:
            template_format: Template format to use (default: "jinja2")
            template_validation: Enable template validation (default: True)
            **kwargs: Additional configuration parameters for component customization
        """
        self.logger.info("Configuring PromptFramework with modern parameter passing")

        # Configure information manager if available
        if self.information_manager and hasattr(self.information_manager, 'configure'):
            try:
                # Pass relevant parameters to information manager
                info_config = {k: v for k, v in kwargs.items() if k.startswith('info_')}
                if info_config:
                    self.information_manager.configure(**info_config)
                    self.logger.debug("Information manager configured with custom parameters")
            except Exception as e:
                self.logger.warning(f"Failed to configure information manager: {e}")

        # Configure template repository with direct parameters
        if self.template_repository and hasattr(self.template_repository, 'configure'):
            try:
                template_config = {
                    'template_format': template_format,
                    'template_validation': template_validation
                }
                # Add any template-specific parameters from kwargs
                template_specific = {k[9:]: v for k, v in kwargs.items() if k.startswith('template_')}
                template_config.update(template_specific)

                self.template_repository.configure(template_config)
                self.logger.debug(f"Template repository configured with format: {template_format}")
            except Exception as e:
                self.logger.warning(f"Failed to configure template repository: {e}")

        self.logger.debug("PromptFramework configuration completed with modern architecture")

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

    # @ErrorHandler.handle_errors(
    #     component="PromptFramework",
    #     phase="strategy_registration"
    # )
    # # TODO deprecated
    # def register_strategy(self, strategy_name: str, strategy_class) -> None:
    #     """Register a prompt generation strategy with the factory.
    #
    #     ### Architectural Decision:
    #     - Uses modern factory pattern instead of legacy ComponentConfigurator
    #     - Provides error handling with decorator pattern
    #     - Follows the established architectural pattern from rv-android-core
    #
    #     Args:
    #         strategy_name: The name/type of the strategy to register.
    #         strategy_class: The strategy class to register.
    #     """
    #     if self.strategy_factory and hasattr(self.strategy_factory, 'register_strategy'):
    #         self.strategy_factory.register_strategy(strategy_name, strategy_class)
    #         self.logger.info(f"Registered strategy: {strategy_name}")
    #     else:
    #         self.logger.warning("Strategy factory not available for registration")

    def get_strategy(self, config: Optional['LLMConfig'] = None) -> Optional:
        """Get a strategy implementation using the factory pattern."""
        if config is None:
            config = self.config

        self.logger.debug(f"Retrieving strategy: {config.strategy_type}")

        # Use factory to create strategy
        try:
            from rv_llm.factories.component_factory import LLMComponentFactory
            return LLMComponentFactory.create_strategy(
                self.config,
                information_manager=self.information_manager,
                template_repository=self.template_repository
            )
        except RVPromptError:
            # Re-raise RVPromptError without wrapping to avoid double handling
            raise
        except Exception as e:
            error_msg = f"Error creating strategy '{config.strategy_type}': {e}"
            self.logger.error(error_msg)
            # Only create new RVPromptError for non-RVPromptError exceptions
            raise RVPromptError(error_msg, config.strategy_type, e) from e

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
