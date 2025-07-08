"""UI Elements information fragment for the prompt system.

This module defines a specialized fragment for extracting and formatting UI element
information from the application state using structured ScreenDescription objects
from the rv-screen-parser system.

### Architectural Overview:
The UIElementsFragment serves as the primary interface between the screen parsing
system and the prompt generation pipeline, converting structured UI hierarchy data
into human-readable text representations for LLM consumption.

### Core Responsibilities:
- **ScreenDescription Processing**: Handles typed ScreenDescription objects from rv-screen-parser
- **UI Hierarchy Translation**: Converts structured UI data into prompt-friendly text
- **Fallback Mechanisms**: Provides robust error handling for missing or invalid state data
- **Format Standardization**: Ensures consistent UI element representation across prompts

### Integration Architecture:
- Consumes ScreenDescription objects with full type safety and validation
- Integrates with rv-android-core error handling and logging infrastructure
- Supports both structured screen data and fallback text representations
- Maintains compatibility with different screen parser backends (DroidBot, UIAutomator)

### Design Patterns:
- **Strategy Pattern**: Flexible handling of different screen data formats
- **Template Method**: Consistent processing pipeline with specialized formatting
- **Error Isolation**: Comprehensive error handling to prevent prompt generation failures
- **Type Safety**: Full integration with Pydantic models and validation
"""

from typing import Any, Dict, Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.error.exceptions import RVParsingError
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription

from rv_llm.llm.constants import FragmentType, StateEntry
from rv_llm.llm.prompt.information.base_fragment import InformationFragment


class UIElementsFragment(InformationFragment):
    """Fragment for extracting and formatting UI element information.
    
    ### Architectural Role:
    This fragment serves as the primary bridge between the structured screen parsing
    system and the prompt generation pipeline, ensuring reliable UI element data
    extraction and formatting for LLM consumption.
    
    ### Processing Strategy:
    - Prioritizes ScreenDescription objects for type-safe processing
    - Implements fallback mechanisms for pre-formatted screen descriptions
    - Provides comprehensive error handling for malformed or missing data
    - Maintains consistent output format regardless of input data structure
    
    ### Integration Points:
    - Consumes ScreenDescription objects from rv-screen-parser visitor pattern
    - Integrates with rv-android-core error handling and logging systems
    - Supports state enrichment pipeline from rvandroid-tool components
    - Delivers formatted text for template-based prompt generation
    """

    def __init__(self, name: str = FragmentType.UI_ELEMENTS, priority: int = 500):
        """Initialize the UI elements fragment with comprehensive infrastructure.
        
        Sets up the complete fragment processing pipeline including error handling,
        logging, and type validation systems for robust UI element processing.
        
        Args:
            name: The name of the fragment (default: FragmentType.UI_ELEMENTS).
            priority: The priority of the fragment (default: 500 - highest priority).
        """
        super().__init__(name, priority)
        
        # Initialize logging infrastructure
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.prompt.ui_elements_fragment",
            {CONTEXT_COMPONENT: "UIElementsFragment"}
        )
        
        # Initialize error handling
        self.error_handler = ErrorHandler.get_instance()
        
        self.logger.debug("Initialized UIElementsFragment for structured screen processing")

    @ErrorHandler.handle_errors(component="UIElementsFragment", phase="generation", reraise=True)
    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """Generate formatted UI element information from structured application state.
        
        Processes structured ScreenDescription objects to generate human-readable
        UI element representations for LLM prompt integration. Implements type-safe
        processing with comprehensive fallback mechanisms.
        
        Args:
            state: The current application state containing screen information
            context: Additional context information for processing customization
            
        Returns:
            A formatted string representation of the UI elements
            
        Raises:
            RVParsingError: If state validation fails or contains invalid data
        """
        if not state:
            raise RVParsingError(
                "State dictionary is empty or None",
                parser_type="UIElementsFragment"
            )

        # Priority 1: Process ScreenDescription objects with type validation
        if StateEntry.STRUCTURED_SCREEN in state:
            screen_description = state[StateEntry.STRUCTURED_SCREEN]
            
            # Validate ScreenDescription type for type safety
            if not isinstance(screen_description, ScreenDescription):
                self.logger.warning(
                    f"Expected ScreenDescription object, got {type(screen_description)}. "
                    "Falling back to string representation."
                )
                # Attempt string conversion with error handling
                try:
                    return str(screen_description)
                except Exception as e:
                    self.logger.error(f"Failed to convert screen description to string: {e}")
                    return "Error: Invalid screen description format"
            
            # Use ScreenDescription's built-in string representation
            self.logger.debug(f"Processing ScreenDescription with {len(screen_description.items)} items")
            return str(screen_description)

        # Priority 2: Use pre-formatted screen description if available
        if StateEntry.SCREEN_DESCRIPTION in state:
            screen_text = state[StateEntry.SCREEN_DESCRIPTION]
            if isinstance(screen_text, str) and screen_text.strip():
                self.logger.debug("Using pre-formatted screen description")
                return screen_text
            else:
                self.logger.warning("Pre-formatted screen description is empty or invalid")

        # No valid screen information found
        self.logger.warning("No valid screen information found in state")
        return "No screen information available."


    @ErrorHandler.handle_errors(component="UIElementsFragment", phase="inclusion_check")
    def should_include(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if UI elements information should be included in prompt generation.
        
        Validates state content to ensure UI element information is available and
        suitable for prompt inclusion. Implements comprehensive validation to prevent
        empty or invalid data from being included in prompts.
        
        Args:
            state: The current application state to validate
            context: Additional context information for inclusion decisions
            
        Returns:
            True if valid UI elements information is available, False otherwise
        """
        if not state:
            self.logger.debug("UI elements not included: empty state")
            return False

        # Check for structured screen description (preferred)
        if StateEntry.STRUCTURED_SCREEN in state:
            screen_description = state[StateEntry.STRUCTURED_SCREEN]
            if isinstance(screen_description, ScreenDescription):
                has_items = len(screen_description.items) > 0
                self.logger.debug(f"ScreenDescription validation: {len(screen_description.items)} items")
                return has_items
            else:
                self.logger.warning("STRUCTURED_SCREEN exists but is not a ScreenDescription object")

        # Check for pre-formatted screen description (fallback)
        if StateEntry.SCREEN_DESCRIPTION in state:
            screen_text = state[StateEntry.SCREEN_DESCRIPTION]
            if isinstance(screen_text, str) and screen_text.strip():
                self.logger.debug("Using pre-formatted screen description")
                return True
            else:
                self.logger.debug("Pre-formatted screen description is empty or invalid")

        # No valid UI information found
        self.logger.debug("No valid UI elements information found for inclusion")
        return False
