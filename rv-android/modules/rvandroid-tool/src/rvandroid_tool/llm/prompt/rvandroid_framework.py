"""
RVAndroid Prompt Framework Implementation

### Architectural Overview:
This module implements the RVAndroid-specific prompt framework that extends
the base PromptFramework with domain-specific components for Android application
testing and analysis.

### Key Components:
- **Fragment Registration**: Registers Android-specific information fragments
- **Template Integration**: Configures templates for Android testing scenarios
- **Strategy Registration**: Registers strategies with the LLM component factory
- **DroidBot Integration**: Provides specialized configuration for DroidBot parsing

### Design Patterns:
- **Template Method**: Extends base framework creation pattern
- **Registry Pattern**: Registers components with appropriate factories
- **Composition Pattern**: Composes Android-specific components
- **Factory Pattern**: Uses factories for consistent component creation

### Integration Points:
This framework integrates with the LLM component factory to register strategies
and provides a complete prompt generation system for Android testing scenarios.
"""

from typing import Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.config import PromptConfig
from rv_llm.llm.constants import PromptStrategyType
from rv_llm.llm.prompt.framework import PromptFramework
from rv_llm.llm.prompt.information.fragment_manager import InformationManager
from rv_llm.llm.prompt.template.jinja_repository import Jinja2TemplateRepository

# Import RVAndroid-specific components
from rvandroid_tool.llm.prompt.fragments.history_fragment import HistoryFragment
from rvandroid_tool.llm.prompt.fragments.monitored_operations_fragment import MonitoredOperationsFragment
from rvandroid_tool.llm.prompt.fragments.screenshot_fragment import ScreenshotFragment
from rvandroid_tool.llm.prompt.fragments.transition_guidance_fragment import TransitionGuidanceFragment
from rvandroid_tool.llm.prompt.fragments.ui_elements_fragment import UIElementsFragment
from rvandroid_tool.llm.prompt.strategies.batch_action_strategy import BatchActionStrategy
from rvandroid_tool.llm.prompt.strategies.standard_strategy import StandardStrategy


class RVAndroidPromptFramework(PromptFramework):
    """
    RVAndroid-specific prompt framework implementation.
    
    ### Architectural Overview:
    This framework extends the base PromptFramework to provide specialized
    functionality for Android application testing and analysis. It automatically
    registers domain-specific fragments, strategies, and templates during creation.
    
    ### Key Features:
    - **Automatic Registration**: Registers all Android-specific components
    - **Template Integration**: Loads Android testing templates and fragments
    - **Strategy Registration**: Registers strategies with component factory
    - **DroidBot Support**: Optimized for DroidBot-based Android testing
    
    ### Component Registration:
    - Information fragments for Android-specific data extraction
    - Prompt strategies for different testing scenarios
    - Template directories for Android testing templates
    
    ### Usage Pattern:
    This framework is designed to be created once per testing session and
    provides a complete prompt generation system for Android scenarios.
    """

    @classmethod
    @ErrorHandler.handle_errors(
        component="RVAndroidPromptFramework",
        operation="create"
    )
    def create(cls, config: Optional[PromptConfig]) -> 'RVAndroidPromptFramework':
        """Create RVAndroid framework with complete component registration.
        
        ### Framework Creation Process:
        1. Register strategies with LLM component factory
        2. Create base framework components
        3. Register Android-specific information fragments
        4. Configure template directories for Android testing
        
        This method performs all necessary registrations to provide a complete
        prompt generation system for Android testing scenarios.
        
        Args:
            config: Configuration for the framework
            
        Returns:
            Configured RVAndroidPromptFramework instance with all components registered
        """
        logger = LoggingManager.get_instance().get_logger(
            "rvandroid_tool.llm.prompt.rvandroid_framework",
            {CONTEXT_COMPONENT: "RVAndroidPromptFramework"}
        )
        logger.info("Creating RVAndroidPromptFramework with complete registration")

        # Register strategies with the component factory
        cls._register_strategies()

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

        # Register Android-specific information fragments
        framework._register_fragments()

        # Register templates and fragments with framework
        framework._register_templates_and_fragments()

        logger.info("RVAndroidPromptFramework created with all components registered")
        return framework

    @classmethod
    def _register_strategies(cls) -> None:
        """Register RVAndroid strategies with the LLM component factory.
        
        ### Strategy Registration:
        This method registers all RVAndroid-specific strategies with the component
        factory, enabling the factory to create strategy instances without hardcoded
        imports. Uses constants for strategy type consistency.
        """
        logger = LoggingManager.get_instance().get_logger(
            "rvandroid_tool.llm.prompt.rvandroid_framework"
        )

        try:
            from rv_llm.factories.component_factory import LLMComponentFactory

            # Register strategies using constants
            LLMComponentFactory.register_strategy(PromptStrategyType.BATCH_ACTION, BatchActionStrategy)
            LLMComponentFactory.register_strategy(PromptStrategyType.STANDARD, StandardStrategy)

            logger.info("Registered RVAndroid strategies with component factory")

        except Exception as e:
            logger.error(f"Failed to register strategies: {e}")
            raise

    def _register_fragments(self) -> None:
        """Register Android-specific information fragments.
        
        ### Fragment Registration:
        This method creates and registers all information fragments that provide
        contextual data for Android testing scenarios. Each fragment specializes
        in extracting specific types of information from the testing environment.
        """
        self.logger.debug("Registering Android-specific information fragments")

        try:
            # Create Android-specific fragments
            fragments = [
                HistoryFragment(),
                MonitoredOperationsFragment(),
                ScreenshotFragment(),
                TransitionGuidanceFragment(),
                UIElementsFragment()
            ]

            # Register fragments with information manager
            self.register_fragments(fragments)

            self.logger.info(f"Registered {len(fragments)} Android-specific fragments")

        except Exception as e:
            self.logger.error(f"Failed to register fragments: {e}")
            raise

    def _register_templates_and_fragments(self) -> None:
        """Register template and fragment directories with the framework.
        
        ### Template Integration:
        This method directly accesses template paths and registers them with
        the framework, maintaining separation of concerns by not depending
        on configuration classes for template registration logic.
        """
        self.logger.debug("Registering template and fragment directories")

        try:
            # Import template paths utility directly
            from rvandroid_tool.templates import get_template_paths

            # Get template paths directly without config dependency
            template_paths = get_template_paths()
            
            # Register fragments directory if available
            if "fragments" in template_paths:
                fragment_path = template_paths["fragments"]
                self.template_repository.register_fragment_directory(fragment_path)
                self.logger.debug(f"Registered fragment directory: {fragment_path}")
            
            # Register templates directory if available  
            if "templates" in template_paths:
                template_path = template_paths["templates"]
                self.template_repository.register_template_directory(template_path)
                self.logger.debug(f"Registered template directory: {template_path}")

            self.logger.info(f"Template and fragment directories registered successfully: {list(template_paths.keys())}")

        except Exception as e:
            self.logger.warning(f"Failed to register template directories: {e}")
            # Don't raise - templates are optional for basic operation