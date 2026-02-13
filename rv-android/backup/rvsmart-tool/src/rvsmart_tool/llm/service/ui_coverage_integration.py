"""
UI Coverage Integration for ActionService

This module provides helper methods for integrating UICoverageTracker
with the ActionService for recording LLM UI element interactions and
applying coverage annotations to screen descriptions.
"""

from typing import Dict, Any, Optional, TYPE_CHECKING

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_llm.llm.constants import StateEntry

if TYPE_CHECKING:
    from rvsmart_tool.core.memory.ui_coverage_tracker import UICoverageTracker


class UICoverageIntegration:
    """Helper class for UI coverage integration in ActionService."""
    
    def __init__(self, ui_coverage_tracker: Optional['UICoverageTracker'] = None):
        """Initialize UI coverage integration.
        
        Args:
            ui_coverage_tracker: UICoverageTracker instance or None
        """
        self.ui_coverage_tracker = ui_coverage_tracker
        
        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvsmart_tool.llm.service.ui_coverage_integration",
            {CONTEXT_COMPONENT: "UICoverageIntegration"}
        )
    
    @ErrorHandler.handle_errors(component="UICoverageIntegration", phase="screen_hash_extraction", default_return=None)
    def get_screen_hash_from_state(self, state: Dict[str, Any]) -> Optional[str]:
        """Extract screen hash from state for UI coverage context.
        
        Args:
            state: Current application state
            
        Returns:
            Screen hash string or None if unavailable
        """
        # Try to use existing screen hash from MemoryManager
        existing_hash = state.get(StateEntry.HASH_SCREEN)
        if existing_hash:
            return existing_hash
            
        # Use UICoverageTracker's hash computation if available
        if self.ui_coverage_tracker:
            return self.ui_coverage_tracker.compute_screen_hash(state)
            
        return None
    
    @ErrorHandler.handle_errors(component="UICoverageIntegration", phase="coverage_annotation")
    def apply_ui_coverage_annotations(self, state: Dict[str, Any]) -> None:
        """Apply UI coverage annotations to screen elements.
        
        Modifies the state in-place to add [UNTESTED]/[TESTED-Nx] annotations
        to UI elements based on interaction history from UICoverageTracker.
        
        Args:
            state: Current application state (modified in-place)
        """
        if not self.ui_coverage_tracker:
            return
            
        try:
            # Get screen hash for context
            screen_hash = self.get_screen_hash_from_state(state)
            if not screen_hash:
                return
            
            # Get structured screen description
            screen_description = state.get(StateEntry.STRUCTURED_SCREEN)
            if not screen_description:
                return
            
            # Apply coverage annotations using UICoverageTracker
            annotated_description = self.ui_coverage_tracker.annotate_screen_elements(
                screen_description, screen_hash
            )
            
            # Update state with annotated description
            state[StateEntry.STRUCTURED_SCREEN] = annotated_description
            
            self.logger.debug("Applied UI coverage annotations to screen elements")
            
        except Exception as e:
            self.logger.error(f"Error applying coverage annotations: {e}")
    
    @ErrorHandler.handle_errors(component="UICoverageIntegration", phase="interaction_recording")
    def record_action_interaction(self, action_data: Dict[str, Any], state: Dict[str, Any]) -> None:
        """Record UI element interaction from LLM action selection.
        
        Args:
            action_data: Action data containing element and type information
            state: Current application state for context
        """
        if not self.ui_coverage_tracker:
            return
            
        try:
            # Extract action information
            action_type = action_data.get('action_type', 'unknown')
            item = action_data.get('item')
            
            if not item:
                return
            
            # Create unique element identifier
            element_id = f"{getattr(item, 'id', 'unknown')}_{getattr(item, 'text', 'unknown')}"
            
            # Get screen hash for context-specific tracking
            screen_hash = self.get_screen_hash_from_state(state)
            
            # Record UI element interaction
            self.ui_coverage_tracker.record_interaction(
                element_id=element_id,
                action_type=action_type,
                screen_hash=screen_hash
            )
            
            self.logger.debug(f"Recorded UI interaction: {element_id} ({action_type})")
            
        except Exception as e:
            self.logger.error(f"Error recording action interaction: {e}")