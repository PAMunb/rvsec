"""
UI element interaction tracking for LLM-driven testing.

This module provides tracking of UI element interactions performed by the LLM during
testing, separate from system coverage tracking (methods/activities/classes). This
focuses on which UI elements the LLM has selected and tested.

### Architectural Decisions:
- **Memory Efficiency**: Uses dictionaries for element tracking without complex data structures
- **LLM Decision Support**: Provides analytics to help LLM make informed decisions
- **Integration Ready**: Compatible with existing StateEntry constants and logging infrastructure
- **Task Isolation**: No state persistence between task executions
- **Error Handling**: Error handling using rv-android-core infrastructure

### Role in the System:
- **UI Element Tracking**: Records which UI elements have been selected by LLM (distinct from system coverage)
- **Element Annotations**: Provides [UNTESTED]/[TESTED-Nx] markers for LLM guidance
- **Action Balance**: Monitors action type distribution for testing variety
- **Selection Statistics**: UI element selection metrics for LLM decision-making

### Integration Points:
- **ActionService**: Records LLM element selections via record_interaction()
- **Fragment System**: Provides UI element coverage data for prompt generation
- **StateEntry**: Uses existing constants for screen identification
- **LoggingManager**: Standardized logging with contextual information

### Distinction from System Coverage:
- **System Coverage** (rv-coverage): Methods, activities, classes, MOP violations
- **UI Coverage** (this module): UI elements selected/tested by LLM
"""

from typing import Set, Dict, Any, Optional, List
from dataclasses import dataclass
import hashlib

from rv_android_core.constants import UI_COVERAGE_CONSTANTS
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_llm.llm.constants import StateEntry


@dataclass
class UIElementStats:
    """
    UI element interaction statistics for LLM decision-making support.
    
    Distinct from system coverage metrics (methods/activities/classes).
    Focuses on UI element selection and testing by LLM.
    
    ### UI Element Metrics:
    - **total_elements**: Total UI elements discovered across screens
    - **tested_elements**: Number of elements that have been selected/tested by LLM
    - **untested_elements**: Number of elements not yet tested by LLM
    - **coverage_percentage**: Percentage of UI elements tested (computed property)
    """
    total_elements: int = 0
    tested_elements: int = 0
    untested_elements: int = 0
    
    @property
    def coverage_percentage(self) -> float:
        """Calculate UI element coverage percentage for LLM context."""
        if self.total_elements == 0:
            return 0.0
        return (self.tested_elements / self.total_elements) * 100


class UICoverageTracker:
    """
    UI element coverage tracking for LLM decision-making.
    
    Provides analytics to help LLM make informed decisions about which elements
    to test while maintaining simplicity and performance.
    
    ### Architectural Decisions:
    - **Implementation**: Functionality for element tracking
    - **LLM Focus**: All features designed to support LLM decision-making
    - **Memory Efficient**: Simple dictionaries and sets for storage
    - **Task Scoped**: Lifetime matches task execution, no cross-task persistence
    - **Error Resilient**: Graceful degradation when tracking fails
    - **Integration Ready**: Uses existing rv-android-core infrastructure
    
    ### Key Features:
    - **Element Interaction Tracking**: Records which elements LLM has tested with counts
    - **Action Type Distribution**: Monitors action types for balanced exploration
    - **Coverage Annotations**: [UNTESTED], [TESTED-1x], [WELL-TESTED] markers
    - **Simple Statistics**: Basic coverage percentages and element counts
    - **Screen Context**: Screen-specific tracking for contextual guidance
    
    ### Performance Characteristics:
    - **O(1) Lookups**: Fast element existence checks and count updates
    - **Minimal Memory**: No complex data structures or caching
    - **CPU Efficient**: Simple operations without expensive calculations
    - **Scalable**: Handles screens with hundreds of elements efficiently
    """
    
    def __init__(self):
        """
        Initialize coverage tracker with essential infrastructure.
        
        ### Initialization Strategy:
        Sets up logging, error handling, and storage structures for
        efficient element tracking and LLM guidance generation.
        """
        # Set up logging infrastructure using existing patterns
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvsmart_tool.core.memory.ui_coverage_tracker",
            {CONTEXT_COMPONENT: "UICoverageTracker"}
        )
        
        # Element tracking: element_id -> interaction_count  
        self.tested_elements: Dict[str, int] = {}
        
        # Action type distribution for balance guidance
        self.action_type_counts: Dict[str, int] = {}
        
        # Screen tracking: screen_hash -> set of element_ids
        self.screen_elements: Dict[str, Set[str]] = {}
        
        self.logger.info("UICoverageTracker initialized for task execution")
    
    @ErrorHandler.handle_errors(
        component="UICoverageTracker",
        phase="interaction_recording"
    )
    def record_interaction(self, element_id: str, action_type: str = "click", 
                          screen_hash: Optional[str] = None) -> None:
        """
        Record element interaction with action type for balanced guidance.
        
        ### Recording Strategy:
        Tracks both element usage frequency and action type distribution
        to provide LLM with comprehensive testing guidance.
        
        Args:
            element_id: Unique identifier for the UI element
            action_type: Type of action (click, set_text, coordinate, etc.)
            screen_hash: Optional screen hash for context
        """
        # Track element interaction count (essential for LLM decisions)
        self.tested_elements[element_id] = self.tested_elements.get(element_id, 0) + 1
        
        # Track action type distribution (helps prevent testing bias)
        self.action_type_counts[action_type] = self.action_type_counts.get(action_type, 0) + 1
        
        # Track screen elements if screen_hash provided
        if screen_hash:
            if screen_hash not in self.screen_elements:
                self.screen_elements[screen_hash] = set()
            self.screen_elements[screen_hash].add(element_id)
        
        self.logger.debug(
            f"Recorded interaction: {element_id} ({action_type}, "
            f"count: {self.tested_elements[element_id]})"
        )
    
    @ErrorHandler.handle_errors(
        component="UICoverageTracker",
        phase="coverage_stats_calculation",
        default_return=UIElementStats()
    )
    def get_ui_element_stats(self, screen_hash: Optional[str] = None) -> UIElementStats:
        """
        Get UI element interaction statistics for LLM context.
        
        ### Statistics Strategy:
        Provides screen-specific or global UI element statistics to help
        LLM understand testing progress and element priorities.
        
        Args:
            screen_hash: Optional screen to get stats for (or global if None)
            
        Returns:
            UIElementStats with UI element interaction information
        """
        if screen_hash and screen_hash in self.screen_elements:
            # Screen-specific stats for focused guidance
            screen_element_ids = self.screen_elements[screen_hash]
            tested_on_screen = sum(1 for elem_id in screen_element_ids 
                                 if elem_id in self.tested_elements)
            
            return UIElementStats(
                total_elements=len(screen_element_ids),
                tested_elements=tested_on_screen,
                untested_elements=len(screen_element_ids) - tested_on_screen
            )
        else:
            # Global stats across all discovered screens
            all_elements = set()
            for screen_set in self.screen_elements.values():
                all_elements.update(screen_set)
            
            return UIElementStats(
                total_elements=len(all_elements),
                tested_elements=len(self.tested_elements),
                untested_elements=len(all_elements) - len(self.tested_elements)
            )
    
    @ErrorHandler.handle_errors(
        component="UICoverageTracker",
        phase="screen_annotation",
        default_return=""
    )
    def annotate_screen_elements(self, screen_description, screen_hash: str) -> str:
        """
        Add [UNTESTED]/[TESTED] annotations to screen description.
        
        ### Annotation Strategy:
        Modifies screen description to include coverage annotations that
        help LLM prioritize untested elements for systematic exploration.
        
        ### Annotation Types:
        - [UNTESTED]: Highest priority for LLM selection
        - [TESTED-1x]: Tested once, may need more exploration
        - [TESTED-Nx]: Tested N times, moderate priority  
        - [WELL-TESTED]: Tested extensively, lowest priority
        
        Args:
            screen_description: Screen description to annotate
            screen_hash: Hash of current screen
            
        Returns:
            Annotated screen description string
        """
        if not hasattr(screen_description, 'items'):
            return str(screen_description)
        
        # Track elements on this screen
        if screen_hash not in self.screen_elements:
            self.screen_elements[screen_hash] = set()
        
        # Process each screen item for annotation
        for item in screen_description.items:
            for action in item.actions:
                # Generate element ID using existing patterns
                element_id = f"{action.id}_{action.text}"
                
                # Track element for future reference
                self.screen_elements[screen_hash].add(element_id)
                
                # Generate annotation based on testing frequency
                if element_id in self.tested_elements:
                    count = self.tested_elements[element_id]
                    if count == 1:
                        annotation = "[TESTED-1x]"
                    elif count <= 3:
                        annotation = f"[TESTED-{count}x]" 
                    else:
                        annotation = "[WELL-TESTED]"
                else:
                    annotation = "[UNTESTED]"  # Highest priority for LLM
                
                # Apply annotation to action text
                action.text = f"{annotation} {action.text}"
        
        return str(screen_description)
    
    @ErrorHandler.handle_errors(
        component="UICoverageTracker",
        phase="untested_elements_lookup",
        default_return=[]
    )
    def get_untested_elements(self, screen_hash: str) -> List[str]:
        """
        Get list of untested element IDs for a screen.
        
        Essential for LLM prioritization - helps focus on unexplored elements.
        
        Args:
            screen_hash: Screen identifier
            
        Returns:
            List of element IDs that have not been tested
        """
        if screen_hash not in self.screen_elements:
            return []
            
        return [elem_id for elem_id in self.screen_elements[screen_hash]
                if elem_id not in self.tested_elements]
    
    @ErrorHandler.handle_errors(
        component="UICoverageTracker",
        phase="action_balance_guidance",
        default_return="Action Balance: Vary action types for comprehensive testing"
    )
    def get_action_balance_guidance(self) -> str:
        """
        Get action balance guidance for LLM decision-making.
        
        ### Balance Analysis Strategy:
        Analyzes action type distribution to identify testing bias
        and provides recommendations for more balanced exploration.
        
        Returns:
            Simple guidance string about action type distribution
        """
        if not self.action_type_counts:
            return f"Action Balance: {UI_COVERAGE_CONSTANTS.GUIDANCE_VARY_ACTIONS}"
        
        total_actions = sum(self.action_type_counts.values())
        guidance = []
        
        # Check if click actions are over-represented using constants
        click_pct = (self.action_type_counts.get(UI_COVERAGE_CONSTANTS.ACTION_TYPE_CLICK, 0) / total_actions) * 100
        if click_pct > UI_COVERAGE_CONSTANTS.CLICK_OVERUSE_THRESHOLD:
            guidance.append("Consider more SET_TEXT and coordinate actions")
        
        # Check if text actions are under-represented using constants  
        text_pct = (self.action_type_counts.get(UI_COVERAGE_CONSTANTS.ACTION_TYPE_SET_TEXT, 0) / total_actions) * 100
        if (text_pct < UI_COVERAGE_CONSTANTS.TEXT_UNDERUSE_THRESHOLD and 
            self.action_type_counts.get(UI_COVERAGE_CONSTANTS.ACTION_TYPE_SET_TEXT, 0) > 0):
            guidance.append("Text input actions are underused")
        
        if not guidance:
            return f"Action Balance: {UI_COVERAGE_CONSTANTS.GUIDANCE_GOOD_BALANCE}"
        
        return f"Action Balance: {', '.join(guidance)}"
    
    @ErrorHandler.handle_errors(
        component="UICoverageTracker",
        phase="coverage_summary",
        default_return="Coverage: No elements tracked"
    )
    def get_coverage_summary(self, screen_hash: Optional[str] = None) -> str:
        """
        Get UI element interaction summary for LLM context.
        
        ### Summary Strategy:
        Provides concise UI element interaction information that LLM can use for
        decision-making without overwhelming the prompt context.
        
        Args:
            screen_hash: Optional screen for specific UI element stats
            
        Returns:
            Simple summary string for LLM guidance
        """
        stats = self.get_ui_element_stats(screen_hash)
        
        if stats.total_elements == 0:
            return "Coverage: No elements tracked yet"
        
        return (f"Coverage: {stats.tested_elements}/{stats.total_elements} "
                f"elements tested ({stats.coverage_percentage:.0f}%)")
    
    @ErrorHandler.handle_errors(
        component="UICoverageTracker",
        phase="data_clearing"
    )
    def clear(self) -> None:
        """
        Clear all tracking data for new task execution.
        
        ### Clearing Strategy:
        Resets all tracking data to provide clean state for new tasks
        without cross-task interference.
        """
        self.tested_elements.clear()
        self.action_type_counts.clear()  
        self.screen_elements.clear()
        self.logger.info("Coverage tracking data cleared for new task")
    
    @ErrorHandler.handle_errors(
        component="UICoverageTracker",
        phase="screen_hash_computation",
        default_return=None
    )
    def compute_screen_hash(self, state: Dict[str, Any]) -> Optional[str]:
        """
        Compute screen hash using existing system components.
        
        ### Hash Strategy:
        Uses existing system hash when available, falls back to VIEW_TREE
        structure for consistent screen identification across system.
        
        Args:
            state: Current application state
            
        Returns:
            Screen hash string or None if computation fails
        """
        # Use existing system hash (preferred approach)
        existing_hash = state.get(StateEntry.HASH_SCREEN)
        if existing_hash:
            return existing_hash
            
        # Use VIEW_TREE structure when available
        view_tree = state.get(StateEntry.VIEW_TREE)
        if view_tree:
            # Use SHA-256 for secure hashing
            hash_data = str(view_tree)[:200]  # First 200 chars for structure
            return hashlib.sha256(hash_data.encode()).hexdigest()[:UI_COVERAGE_CONSTANTS.SCREEN_HASH_LENGTH]
            
        # Final fallback: activity name only
        activity = state.get(StateEntry.ACTIVITY, "unknown")
        return hashlib.sha256(activity.encode()).hexdigest()[:UI_COVERAGE_CONSTANTS.SCREEN_HASH_LENGTH]