"""Unified framework for prompt generation.

This module defines the PromptFramework class, which coordinates the
prompt generation process by integrating information gathering, template
management, and strategy execution.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.constants import FragmentType, PromptStrategyType
from rvandroid.llm.data_structures import MCPMessage
from rvandroid.llm.language_model import LanguageModel
from rvandroid.llm.prompt.information.fragment_manager import InformationManager
from rvandroid.llm.prompt.information.fragments.monitored_operations_fragment import MonitoredOperationsFragment
from rvandroid.llm.prompt.information.fragments.screenshot_fragment import ScreenshotFragment
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
        model: Optional[LanguageModel] = None
    ):
        """Initialize the prompt framework.
        
        Args:
            information_manager: Manager for information fragments.
            template_repository: Repository for templates.
            strategy_registry: Registry for prompt strategies.
            model: Language model for generating responses (optional).
        """
        # Store components
        self.information_manager = information_manager
        self.template_repository = template_repository
        self.strategy_registry = strategy_registry
        self.model = model
        
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
            ScreenshotFragment()
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
        model = None
        if config is not None and hasattr(config, 'llm_config'):
            try:
                model = config.create_llm()
            except Exception as e:
                logging.error(f"Error creating language model: {e}", exc_info=True)
        
        # Create framework
        framework = cls(
            information_manager=information_manager,
            template_repository=template_repository,
            strategy_registry=strategy_registry,
            model=model
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
        strategy_name: Optional[str], 
        state: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """Generate a prompt using the specified strategy.
        
        Args:
            strategy_name: Name of the strategy to use (or None for default).
            state: Current application state.
            context: Additional context information.
            
        Returns:
            List of message dictionaries with role and content.
        """
        try:
            # Get the appropriate strategy
            strategy = self.strategy_registry.get_strategy(strategy_name)
            
            if strategy is None:
                self.logger.error(f"Strategy not found: {strategy_name}")
                # Fall back to standard strategy
                strategy = self.strategy_registry.get_strategy(PromptStrategyType.STANDARD)
                
                if strategy is None:
                    self.logger.error("No strategy available")
                    return []
            
            self.logger.debug(f"Using strategy: {strategy.name}")
            
            # Generate the prompt using the strategy
            # TODO converter em mensagens MCP ... aqui?
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
    
    def generate_mcp_prompt(
        self, 
        strategy_name: Optional[str], 
        state: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> List[MCPMessage]:
        """Generate an MCP prompt using the specified strategy.
        
        Args:
            strategy_name: Name of the strategy to use (or None for default).
            state: Current application state.
            context: Additional context information.
            
        Returns:
            List of MCPMessage objects.
        """
        try:
            # Get the appropriate strategy
            strategy = self.strategy_registry.get_strategy(strategy_name)
            
            if strategy is None:
                self.logger.error(f"Strategy not found: {strategy_name}")
                # Fall back to standard strategy
                strategy = self.strategy_registry.get_strategy(PromptStrategyType.STANDARD)
                
                if strategy is None:
                    self.logger.error("No strategy available")
                    return []
            
            self.logger.debug(f"Using strategy: {strategy.name}")
            
            # Generate the MCP prompt using the strategy
            return strategy.generate_mcp_prompt(state, context)
        except Exception as e:
            self.logger.error(f"Error generating MCP prompt: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "PromptFramework",
                    "function": "generate_mcp_prompt",
                    "strategy": strategy_name
                }
            )
            return []

    # TODO deprecated ... pode usar o llm manager
    def generate_with_llm(
        self, 
        strategy_name: Optional[str], 
        state: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """Generate a prompt and send it to the LLM for a response.
        
        Args:
            strategy_name: Name of the strategy to use (or None for default).
            state: Current application state.
            context: Additional context information.
            
        Returns:
            LLM response, or None if an error occurred.
        """
        if self.model is None:
            self.logger.error("No language model configured")
            return None
        
        messages = self.generate_mcp_prompt(strategy_name, state, context)
        
        if not messages:
            self.logger.error("No messages generated")
            return None
        
        try:
            self.logger.debug(f"Sending {len(messages)} messages to LLM")
            response = self.model.generate_sync(messages)
            return response
        except Exception as e:
            self.logger.error(f"Error generating LLM response: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "PromptFramework",
                    "function": "generate_with_llm",
                    "strategy": strategy_name
                }
            )
            return None

    # TODO deprecated
    def select_strategy_for_state(self, state: Dict[str, Any]) -> str:
        """Select the appropriate strategy for the given state.
        
        Args:
            state: Current application state.
            
        Returns:
            Name of the selected strategy.
        """
        # Try to get the batch action strategy
        batch_strategy = self.strategy_registry.get_strategy(PromptStrategyType.BATCH_ACTION)
        
        # If batch strategy is available and should be used, return it
        if batch_strategy and hasattr(batch_strategy, 'should_use_batch') and batch_strategy.should_use_batch(state):
            return PromptStrategyType.BATCH_ACTION
        
        # Otherwise, return the standard strategy
        return PromptStrategyType.STANDARD