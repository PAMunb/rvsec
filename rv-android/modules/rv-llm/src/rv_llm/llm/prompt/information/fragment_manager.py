"""Information fragment manager for the prompt system.

This module contains the InformationManager class, which coordinates the collection
and composition of information from various sources through specialized fragments.
"""

from typing import Any, Dict, List, Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.config.strategy_config import PromptStrategyConfig
from .base_fragment import InformationFragment


class InformationManager:
    """Manages information fragments and composes information for prompt generation.
    
    The InformationManager is responsible for registering, prioritizing, and composing
    information from various fragments to create a comprehensive view of the current
    state for use in prompt generation.
    """

    def __init__(self):
        """Initialize the InformationManager."""
        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.prompt.information.manager",
            {CONTEXT_COMPONENT: "InformationManager"}
        )

        # Set up error handling
        self.error_handler = ErrorHandler.get_instance()

        # Initialize fragment registry
        self.fragments: Dict[str, InformationFragment] = {}

    @ErrorHandler.handle_errors(
        component="InformationManager",
        phase="configuration"
    )
    def configure(self, config: Optional[PromptStrategyConfig] = None) -> None:
        """Configure the InformationManager with the given configuration.
        
        ### Architectural Decision:
        - Uses typed configuration class instead of dictionary
        - Provides error handling with decorator pattern
        - Follows the established architectural pattern from rv-android-core
        
        Args:
            config: Optional typed configuration instance.
        """
        self.logger.debug("Configuring InformationManager")
        
        if config is None:
            config = PromptStrategyConfig()
            
        # Validate configuration
        is_valid, errors = config.validate()
        if not is_valid:
            self.logger.warning(f"Configuration validation errors: {errors}")
            
        # Configure all registered fragments
        for fragment_name, fragment in self.fragments.items():
            if hasattr(fragment, 'configure'):
                try:
                    # Get fragment-specific configuration
                    fragment_config = config.get_fragment_config(fragment_name)
                    fragment.configure(fragment_config)
                    self.logger.debug(f"Configured fragment: {fragment_name}")
                except Exception as e:
                    self.logger.warning(f"Failed to configure fragment {fragment_name}: {e}")
                    
        self.logger.debug("InformationManager configuration completed")

    def register_fragment(self, fragment: InformationFragment) -> None:
        """Register an information fragment.
        
        Args:
            fragment: The information fragment to register.
        """
        if fragment.name in self.fragments:
            self.logger.warning(f"Overwriting existing fragment: {fragment.name}")

        self.fragments[fragment.name] = fragment
        self.logger.debug(f"Registered fragment: {fragment.name} (priority: {fragment.priority})")

    def register_fragments(self, fragments: List[InformationFragment]) -> None:
        """Register multiple information fragments.
        
        Args:
            fragments: The information fragments to register.
        """
        for fragment in fragments:
            self.register_fragment(fragment)

    def unregister_fragment(self, name: str) -> None:
        """Unregister an information fragment.
        
        Args:
            name: The name of the fragment to unregister.
        """
        if name in self.fragments:
            self.logger.info(f"Unregistered fragment: {name}")
            del self.fragments[name]
        else:
            self.logger.warning(f"Attempted to unregister non-existent fragment: {name}")

    def get_fragment(self, name: str) -> Optional[InformationFragment]:
        """Get a registered fragment by name.
        
        Args:
            name: The name of the fragment to get.
            
        Returns:
            The fragment, or None if not found.
        """
        return self.fragments.get(name)

    def _get_sorted_fragments(self) -> List[InformationFragment]:
        """Get all registered fragments sorted by priority (highest first).
        
        Returns:
            A list of fragments sorted by priority.
        """
        return sorted(self.fragments.values(), key=lambda f: -f.priority)

    def compose_information(
            self,
            state: Dict[str, Any],
            context: Optional[Dict[str, Any]] = None,
            requested_fragments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Compose information from all relevant fragments.
        
        Args:
            state: The current state (e.g., app UI state, test state).
            context: Additional contextual information.
            requested_fragments: Optional list of specific fragments to include.
            
        Returns:
            A dictionary containing the composed information from all relevant fragments.
        """
        if context is None:
            context = {}

        result = {}

        try:
            # Get the sorted fragments
            fragments = self._get_sorted_fragments()

            # Filter by requested fragments if provided
            if requested_fragments:
                fragments = [f for f in fragments if f.name in requested_fragments]

            self.logger.debug(f"Composing information with {len(fragments)} fragments")

            # Generate information from each fragment
            for fragment in fragments:
                try:
                    fragment_info = fragment.get_info(state, context)
                    result.update(fragment_info)
                except Exception as e:
                    self.logger.error(f"Error in fragment {fragment.name}: {e}", exc_info=True)
                    self.error_handler.handle_error(
                        e,
                        context={
                            "component": "InformationManager",
                            "fragment": fragment.name
                        }
                    )

            return result
        except Exception as e:
            self.logger.error(f"Error composing information: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "InformationManager",
                    "state_id": state.get("id", "unknown")
                }
            )
            return {}
