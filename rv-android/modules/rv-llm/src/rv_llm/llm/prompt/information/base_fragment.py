"""Base information fragment for the prompt system.

This module defines the base InformationFragment class that all specialized fragments
should inherit from, providing a standardized interface for collecting and formatting
information from various sources for use in prompt generation.
"""

import abc
from typing import Any, Dict, Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class InformationFragment(abc.ABC):
    """Base class for all information fragments.
    
    Information fragments are responsible for collecting and formatting specific 
    types of information from various sources (UI state, screenshots, application 
    metadata, etc.) to be included in prompts for LLMs.
    """

    def __init__(self, name: str, priority: int = 100):
        """Initialize the information fragment.
        
        Args:
            name: A unique identifier for the fragment.
            priority: The priority level of this fragment (higher values = higher priority).
        """
        self.name = name
        self.priority = priority

        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            f"llm.prompt.information.{name}",
            {CONTEXT_COMPONENT: f"InformationFragment:{name}"}
        )

        # Set up error handling
        self.error_handler = ErrorHandler.get_instance()

    @abc.abstractmethod
    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        """Generate the formatted information from the given state and context.
        
        Args:
            state: The current state (e.g., app UI state, test state).
            context: Additional contextual information.
            
        Returns:
            The formatted information object or string.
        """
        pass

    def should_include(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if this fragment should be included in the current prompt.
        
        Args:
            state: The current state (e.g., app UI state, test state).
            context: Additional contextual information.
            
        Returns:
            True if the fragment should be included, False otherwise.
        """
        return True

    def get_info(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get the information from this fragment if it should be included.
        
        Args:
            state: The current state (e.g., app UI state, test state).
            context: Additional contextual information.
            
        Returns:
            A dictionary containing the fragment's information, or an empty dictionary
            if the fragment should not be included.
        """
        try:
            if not self.should_include(state, context):
                return {}

            result = self.generate(state, context)
            if result is None:
                return {}

            return {self.name: result}
        except Exception as e:
            self.logger.error(f"Error generating information: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": f"InformationFragment:{self.name}",
                    "state_id": state.get("id", "unknown")
                }
            )
            return {}
