"""
Prompt Generation Framework

### Architectural Overview:
This module implements a prompt generation framework that coordinates
the prompt generation process through factory patterns and component composition.
The framework serves as a base class that can be extended by specific implementations
to provide domain-specific prompt generation capabilities.

### Key Components:
- **Information Management**: Coordinates data gathering through fragments
- **Template Repository**: Manages template loading and rendering
- **Strategy Integration**: Delegates prompt generation to configurable strategies
- **Factory Coordination**: Uses factory patterns for component creation

### Design Patterns:
- **Template Method**: Defines prompt generation workflow with extension points
- **Factory Pattern**: Strategy creation through component factories
- **Composition Pattern**: Coordinates multiple specialized components
- **Strategy Pattern**: Configurable prompt generation algorithms

### Extension Points:
Subclasses can override component registration and configuration to provide
specialized implementations for different domains or use cases.
"""

from typing import Any, Dict, List, Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVPromptError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.config import PromptConfig
from rv_llm.llm.constants import PromptStrategyType
from rv_llm.llm.data_structures import LLMMessage
from rv_llm.llm.prompt.information.fragment_manager import InformationManager, InformationFragment
from rv_llm.llm.prompt.template.jinja_repository import Jinja2TemplateRepository


class PromptFramework:
    """
    Base framework for prompt generation systems.
    
    ### Architectural Overview:
    This framework provides a foundation for prompt generation systems by coordinating
    three main components:
    1. **Information Management**: Fragments that extract and format contextual data
    2. **Template Repository**: Template loading, rendering, and management
    3. **Strategy Execution**: Configurable algorithms for prompt generation
    
    ### Core Responsibilities:
    - **Component Coordination**: Manages interaction between information fragments and templates
    - **Strategy Delegation**: Routes prompt generation to appropriate strategy implementations
    - **Error Handling**: Provides consistent error handling across all operations
    - **Extension Support**: Offers extension points for domain-specific implementations
    
    ### Extension Pattern:
    This base class is designed to be extended by domain-specific implementations
    that register their own fragments, templates, and strategies during initialization.
    """

    def __init__(
            self,
            information_manager: InformationManager,
            template_repository: Jinja2TemplateRepository,
            config: Optional['PromptConfig']
    ):
        """Initialize the prompt framework.
        
        Args:
            information_manager: Manager for information fragments.
            template_repository: Repository for templates using Jinja2.
            config: Prompt configuration.
        """
        # Store components
        self.information_manager = information_manager
        self.template_repository = template_repository
        self.config = config or PromptConfig()

        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_llm.llm.prompt.framework",
            {CONTEXT_COMPONENT: "PromptFramework"}
        )

        # Set up error handling
        self.error_handler = ErrorHandler.get_instance()
        self.logger.info("PromptFramework initialized")

    @classmethod
    def create(cls, config: Optional['PromptConfig']) -> 'PromptFramework':
        """Create a basic framework instance with default components.
        
        ### Framework Creation:
        This method creates a framework with basic components. Subclasses should
        override this method to register domain-specific fragments and configure
        specialized components.
        
        Args:
            config: Configuration for the framework
            
        Returns:
            Configured PromptFramework instance
        """
        logger = LoggingManager.get_instance().get_logger("rv_llm.llm.prompt.framework")
        logger.info("Creating PromptFramework...")

        # Create information manager
        information_manager = InformationManager()

        # Create template repository
        template_repository = Jinja2TemplateRepository()

        # Create framework instance
        framework = cls(
            information_manager=information_manager,
            template_repository=template_repository,
            config=config
        )

        return framework

    def get_strategy(self, strategy_name: Optional[str] = None) -> Optional:
        """Get a strategy implementation using the factory pattern.
        
        ### Strategy Resolution:
        This method resolves the strategy from configuration and uses the component
        factory to create the appropriate strategy instance. The factory handles
        the complexity of strategy instantiation and dependency injection.
        
        Args:
            strategy_name: Optional strategy name override
            
        Returns:
            Strategy instance or None if creation fails
        """
        if strategy_name is None:
            strategy_name = self.config.strategy_type if self.config else PromptStrategyType.STANDARD

        self.logger.debug(f"Retrieving strategy: {strategy_name}")

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
            error_msg = f"Error creating strategy '{strategy_name}': {e}"
            self.logger.error(error_msg)
            # Only create new RVPromptError for non-RVPromptError exceptions
            raise RVPromptError(error_msg, strategy_name, e) from e

    @ErrorHandler.handle_errors(
        component="PromptFramework",
        operation="generate_prompt"
    )
    def generate_prompt(
            self,
            state: Dict[str, Any],
            context: Optional[Dict[str, Any]] = None
    ) -> List[LLMMessage]:
        """Generate a prompt using the configured strategy.
        
        ### Prompt Generation Workflow:
        1. Resolve strategy from configuration
        2. Delegate prompt generation to strategy
        3. Return generated prompt messages
        
        This method serves as the main entry point for prompt generation and
        coordinates between the framework's components and the strategy implementation.
        
        Args:
            state: Current application state containing all relevant information
            context: Additional context information for prompt generation
            
        Returns:
            List of LLMMessage objects forming the complete prompt
        """
        # Use strategy from configuration
        strategy_name = self.config.strategy_type if self.config else PromptStrategyType.STANDARD
        self.logger.debug(f"Generating prompt with strategy: {strategy_name}")

        # Get the strategy implementation using factory pattern
        strategy = self.get_strategy(strategy_name)

        if strategy is None:
            self.logger.error(f"Strategy not found: {strategy_name}")
            return []

        self.logger.debug(f"Using strategy: {getattr(strategy, 'name', strategy_name)}")

        # Generate the prompt using the strategy
        return strategy.generate_prompt(state, context)

    def register_fragments(self, fragments: list[InformationFragment]):
        """Register information fragments with the framework.
        
        ### Fragment Registration:
        This method registers fragments with the information manager, making them
        available for use in prompt generation. Fragments provide contextual data
        that informs the prompt generation process.
        
        Args:
            fragments: List of information fragments to register
        """
        self.logger.info(f"Registering fragments: {len(fragments)}")
        self.information_manager.register_fragments(fragments)
