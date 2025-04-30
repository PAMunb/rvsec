# rvandroid/core/strategies/flow_based_batch_strategy.py
"""
Flow-Based Batch Action Strategy implementation.

This module provides the implementation of the Flow-Based Batch Action Strategy,
which generates sequences of related actions based on detected UI patterns.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

from rvandroid.core.memory.long_term_memory import LongTermMemory
from rvandroid.analysis.patterns import (
    UIPatternDetectorManager, PatternType, PatternResult, PatternElement
)
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.model import ScreenDescription
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class BaseBatchActionStrategy(ABC):
    """
    Abstract base class for batch action strategies.
    
    ### Architectural Decisions:
    - Defines a common interface for all batch action strategies
    - Provides shared utilities for batch action generation
    - Enables different implementations to share core functionality
    - Supports future DSPy integration through clean abstractions
    
    ### Role in the System:
    - Serves as the foundation for all batch action strategy implementations
    - Defines the core contract for batch action generation
    - Provides utility methods for batch action handling
    - Enables flexible extension for specialized strategies
    """
    
    def __init__(self, 
                 static_data: Optional[StaticAnalysisData] = None,
                 memory: Optional[LongTermMemory] = None,
                 pattern_detector: Optional[UIPatternDetectorManager] = None):
        """
        Initialize the base batch action strategy.
        
        Args:
            static_data: Optional static analysis data
            memory: Optional long-term memory system
            pattern_detector: Optional UI pattern detector
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            f"core.strategies.{self.__class__.__name__.lower()}",
            {CONTEXT_COMPONENT: self.__class__.__name__}
        )
        
        # Initialize core components
        self.static_data = static_data
        self.memory = memory
        
        # Create pattern detector if not provided
        self.pattern_detector = pattern_detector or UIPatternDetectorManager(static_data)
        
        # Strategy configuration
        self.max_batch_size = 5  # Maximum actions in a batch
        self.min_batch_size = 2  # Minimum actions to consider a batch
        
        self.logger.info(f"Initialized {self.__class__.__name__}")
    
    @abstractmethod
    def generate_batch_actions(self, screen: ScreenDescription, 
                             state_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate a batch of related actions.
        
        Args:
            screen: Parsed screen description
            state_data: Additional state data
            
        Returns:
            List of action dictionaries
        """
        pass
    
    def should_generate_batch(self, screen: ScreenDescription, 
                            state_data: Dict[str, Any]) -> bool:
        """
        Determine if batch generation should be used.
        
        Args:
            screen: Parsed screen description
            state_data: Additional state data
            
        Returns:
            True if batch generation should be used
        """
        # Check if a pattern is detected
        dominant_pattern = self.pattern_detector.get_dominant_pattern(screen, state_data)
        
        if dominant_pattern:
            pattern_type, pattern_result = dominant_pattern
            
            # Use batch generation if pattern is valid with high confidence
            return pattern_result.is_valid() and pattern_result.confidence >= 0.8
        
        return False
    
    def get_patterns(self, screen: ScreenDescription, 
                   state_data: Dict[str, Any]) -> Dict[PatternType, PatternResult]:
        """
        Get detected patterns for the screen.
        
        Args:
            screen: Parsed screen description
            state_data: Additional state data
            
        Returns:
            Dictionary of pattern results by type
        """
        return self.pattern_detector.detect_patterns(screen, state_data)
    
    def validate_batch_actions(self, actions: List[Dict[str, Any]]) -> bool:
        """
        Validate a batch of actions.
        
        Args:
            actions: List of action dictionaries
            
        Returns:
            True if the batch is valid
        """
        # Ensure there are enough actions
        if len(actions) < self.min_batch_size:
            return False
        
        # Ensure not too many actions
        if len(actions) > self.max_batch_size:
            # Trim to max batch size
            del actions[self.max_batch_size:]
        
        # Ensure each action has required fields
        for action in actions:
            if not self._is_valid_action(action):
                return False
        
        return True
    
    def _is_valid_action(self, action: Dict[str, Any]) -> bool:
        """
        Check if an action is valid.
        
        Args:
            action: Action dictionary
            
        Returns:
            True if the action is valid
        """
        # Minimum required fields
        required_fields = ['action_type', 'target']
        
        for field in required_fields:
            if field not in action:
                return False
        
        # Check action type
        action_type = action.get('action_type', '')
        if not action_type:
            return False
        
        # Special validation for set_text
        if action_type == 'set_text':
            if 'params' not in action or 'text' not in action['params']:
                return False
        
        return True
    
    def format_batch_actions(self, batch_actions: List[Dict[str, Any]], 
                          pattern_type: PatternType,
                          confidence: float) -> List[Dict[str, Any]]:
        """
        Format batch actions with metadata.
        
        Args:
            batch_actions: List of actions
            pattern_type: Type of pattern that generated this batch
            confidence: Confidence in the pattern
            
        Returns:
            Formatted batch actions
        """
        # Add batch metadata to each action
        for i, action in enumerate(batch_actions):
            # Add metadata if not present
            if 'meta' not in action:
                action['meta'] = {}
            
            # Add batch information
            action['meta']['batch_index'] = i
            action['meta']['batch_size'] = len(batch_actions)
            action['meta']['batch_pattern'] = pattern_type.value
            action['meta']['batch_confidence'] = confidence
            
            # Add action purpose based on position in batch
            if i == 0:
                action['meta']['batch_role'] = 'start'
            elif i == len(batch_actions) - 1:
                action['meta']['batch_role'] = 'end'
            else:
                action['meta']['batch_role'] = 'middle'
        
        return batch_actions


class FlowBasedBatchActionStrategy(BaseBatchActionStrategy):
    """
    Flow-based batch action strategy implementation.
    
    This strategy generates batches of actions based on detected UI patterns,
    optimizing for coherent interaction sequences that follow application workflow.
    
    ### Architectural Decisions:
    - Uses pattern-specific sequence generation for different UI elements
    - Leverages memory system for optimizing batch effectiveness
    - Integrates MOP awareness to prioritize operations of interest
    - Balances exploration with effective pattern interaction
    
    ### Role in the System:
    - Serves as the primary batch action generation strategy
    - Provides pattern-specific interaction sequences
    - Enables efficient testing through related action batches
    - Supports monitored operation coverage optimization
    """
    
    def __init__(self, static_data: Optional[StaticAnalysisData] = None,
               memory: Optional[LongTermMemory] = None,
               pattern_detector: Optional[UIPatternDetectorManager] = None):
        """
        Initialize the flow-based batch strategy.
        
        Args:
            static_data: Optional static analysis data
            memory: Optional long-term memory system
            pattern_detector: Optional UI pattern detector
        """
        super().__init__(static_data, memory, pattern_detector)
        
        # Batch configuration
        self.form_max_fields = 5  # Max fields to fill in a form batch
        self.list_max_items = 3    # Max items to interact with in a list batch
        
        # Temperature config for different patterns
        self.temperature_config = {
            PatternType.FORM: 0.2,      # Forms need precise content
            PatternType.LIST: 0.3,       # Lists need systematic exploration
            PatternType.TABS: 0.3,       # Tab navigation is structured
            PatternType.NAVIGATION: 0.4, # Navigation can be more creative
            PatternType.DIALOG: 0.2,     # Dialogs need precise handling
            PatternType.CAROUSEL: 0.3,   # Carousels need systematic exploration
        }
    
    def generate_batch_actions(self, screen: ScreenDescription, 
                             state_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate a batch of related actions based on UI patterns.
        
        Args:
            screen: Parsed screen description
            state_data: Additional state data
            
        Returns:
            List of action dictionaries
        """
        # Get detected patterns
        patterns = self.get_patterns(screen, state_data)
        
        # Enrich patterns with MOP info if needed
        patterns = self.pattern_detector.enrich_patterns_with_mop_info(patterns)
        
        # Get the dominant pattern
        dominant_pattern = self.pattern_detector.get_dominant_pattern(screen, state_data)
        
        if not dominant_pattern:
            self.logger.debug("No dominant pattern detected, using single action")
            return []
        
        pattern_type, pattern_result = dominant_pattern
        self.logger.info(f"Generating batch actions for {pattern_type.value} pattern "
                        f"with confidence {pattern_result.confidence:.2f}")
        
        # Generate pattern-specific batch actions
        if pattern_type == PatternType.FORM:
            batch_actions = self._generate_form_batch(pattern_result, screen, state_data)
        elif pattern_type == PatternType.LIST:
            batch_actions = self._generate_list_batch(pattern_result, screen, state_data)
        elif pattern_type == PatternType.TABS:
            batch_actions = self._generate_tabs_batch(pattern_result, screen, state_data)
        elif pattern_type == PatternType.DIALOG:
            batch_actions = self._generate_dialog_batch(pattern_result, screen, state_data)
        elif pattern_type == PatternType.NAVIGATION:
            batch_actions = self._generate_navigation_batch(pattern_result, screen, state_data)
        else:
            # Default to empty batch for unsupported patterns
            self.logger.debug(f"Unsupported pattern type: {pattern_type.value}")
            return []
        
        # Validate batch actions
        if not self.validate_batch_actions(batch_actions):
            self.logger.debug("Generated batch actions failed validation")
            return []
        
        # Format batch actions with metadata
        batch_actions = self.format_batch_actions(
            batch_actions, pattern_type, pattern_result.confidence)
        
        # Log batch actions
        self.logger.info(f"Generated {len(batch_actions)} batch actions for {pattern_type.value}")
        
        return batch_actions
    
    def get_temperature_for_pattern(self, pattern_type: PatternType) -> float:
        """
        Get the appropriate temperature for a pattern type.
        
        Args:
            pattern_type: Pattern type
            
        Returns:
            Temperature value
        """
        return self.temperature_config.get(pattern_type, 0.5)
    
    def _generate_form_batch(self, pattern: PatternResult, screen: ScreenDescription,
                          state_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate a batch of actions for a form pattern.
        
        Args:
            pattern: Form pattern result
            screen: Screen description
            state_data: State data
            
        Returns:
            List of batch actions
        """
        batch_actions = []
        
        # Get form elements by role
        input_fields = []
        submit_buttons = []
        
        for element in pattern.elements:
            if element.role == "input":
                input_fields.append(element)
            elif element.role == "submit":
                submit_buttons.append(element)
        
        # No input fields or submit buttons = cannot create form batch
        if not input_fields or not submit_buttons:
            return []
        
        # Limit number of fields to process
        input_fields = input_fields[:self.form_max_fields]
        
        # Action history to check if fields already filled
        action_history = state_data.get("action_history", [])
        
        # First, generate actions to fill in input fields
        for field in input_fields:
            # Check if field has any set_text actions
            set_text_actions = [a for a in field.actions if a.event == "set_text"]
            if not set_text_actions:
                continue
            
            set_text_action = set_text_actions[0]
            
            # Check if field was recently filled
            field_id = field.id
            
            # Skip if field was recently filled
            if any(field_id in action and "set_text" in action for action in action_history[-5:]):
                continue
            
            # Generate appropriate text value based on field type
            input_type = field.properties.get("input_type", "text")
            text_value = self._generate_text_for_input_type(input_type)
            
            batch_actions.append({
                "action_type": "set_text",
                "target": field_id,
                "target_view": field.view,
                "params": {
                    "text": text_value
                },
                "action_id": str(set_text_action.id),
                "explanation": f"Fill {input_type} field with appropriate value"
            })
        
        # Add submit button click as the final action
        if submit_buttons:
            # Choose the most appropriate submit button
            submit_button = submit_buttons[0]
            
            # Find click action
            click_actions = [a for a in submit_button.actions if a.event == "click"]
            if click_actions:
                click_action = click_actions[0]
                
                batch_actions.append({
                    "action_type": "click",
                    "target": submit_button.id,
                    "target_view": submit_button.view,
                    "action_id": str(click_action.id),
                    "explanation": "Submit the form after filling fields"
                })
        
        return batch_actions
    
    def _generate_text_for_input_type(self, input_type: str) -> str:
        """
        Generate appropriate text for an input type.
        
        Args:
            input_type: Type of input field
            
        Returns:
            Generated text value
        """
        if input_type == "password":
            return "testpassword123"
        elif input_type == "email":
            return "test@example.com"
        elif input_type == "phone":
            return "1234567890"
        elif input_type == "username":
            return "testuser"
        elif input_type == "search":
            return "test query"
        elif input_type == "first_name":
            return "John"
        elif input_type == "last_name":
            return "Doe"
        elif input_type == "name":
            return "John Doe"
        elif input_type == "address":
            return "123 Test St"
        elif input_type == "city":
            return "Test City"
        elif input_type == "state":
            return "TX"
        elif input_type == "postal_code":
            return "12345"
        elif input_type == "country":
            return "US"
        elif input_type == "credit_card":
            return "4111111111111111"
        elif input_type == "number":
            return "42"
        elif input_type == "date":
            return "2023-01-01"
        elif input_type == "time":
            return "10:00"
        else:
            return "test"
    
    def _generate_list_batch(self, pattern: PatternResult, screen: ScreenDescription,
                          state_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate a batch of actions for a list pattern.
        
        Args:
            pattern: List pattern result
            screen: Screen description
            state_data: State data
            
        Returns:
            List of batch actions
        """
        batch_actions = []
        
        # Get list elements by role
        container = None
        list_items = []
        
        for element in pattern.elements:
            if element.role == "container":
                container = element
            elif element.role == "list_item":
                list_items.append(element)
        
        # No list items = cannot create list batch
        if not list_items:
            return []
        
        # Determine list type
        list_type = pattern.properties.get("list_type", "vertical")
        
        # Check if we can scroll the list
        can_scroll = False
        scroll_directions = []
        
        if container:
            if container.properties.get("scrollable", False):
                can_scroll = True
                scroll_directions = pattern.properties.get("scroll_directions", ["down"])
        
        # First scrolling action if applicable
        if can_scroll and scroll_directions:
            # Add scroll action if container has scroll action
            if container and any("scroll" in a.event for a in container.actions):
                scroll_actions = [a for a in container.actions if "scroll" in a.event]
                if scroll_actions:
                    scroll_action = scroll_actions[0]
                    
                    # Determine appropriate scroll direction for list type
                    scroll_direction = "down"
                    if list_type == "horizontal":
                        scroll_direction = "right"
                    
                    # Ensure the direction exists in available directions
                    if scroll_direction.upper() in [d.upper() for d in scroll_directions]:
                        batch_actions.append({
                            "action_type": f"scroll_{scroll_direction.lower()}",
                            "target": container.id,
                            "target_view": container.view,
                            "action_id": str(scroll_action.id),
                            "explanation": f"Scroll the {list_type} list to reveal more items"
                        })
        
        # Select a subset of items to interact with
        items_to_interact = min(len(list_items), self.list_max_items)
        selected_items = list_items[:items_to_interact]
        
        # Try to select items with MOP relevance if available
        mop_items = [item for item in list_items if item.properties.get("reaches_mop", False)]
        if mop_items:
            # Replace some selected items with MOP-relevant items
            for mop_item in mop_items[:items_to_interact]:
                if mop_item not in selected_items and selected_items:
                    selected_items[-1] = mop_item
        
        # Generate click actions for selected items
        for item in selected_items:
            # Skip if not clickable or no click actions
            if not item.properties.get("has_click_action", False):
                continue
            
            # Get click action
            click_actions = [a for a in item.actions if a.event == "click"]
            if not click_actions:
                continue
                
            click_action = click_actions[0]
            
            # Get item text if available
            item_text = item.properties.get("text", "")
            explanation = f"Click on list item"
            if item_text:
                explanation = f"Click on list item '{item_text[:20]}'"
            
            batch_actions.append({
                "action_type": "click",
                "target": item.id,
                "target_view": item.view,
                "action_id": str(click_action.id),
                "explanation": explanation
            })
        
        return batch_actions
    
    def _generate_tabs_batch(self, pattern: PatternResult, screen: ScreenDescription,
                          state_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate a batch of actions for a tabs pattern.
        
        Args:
            pattern: Tabs pattern result
            screen: Screen description
            state_data: State data
            
        Returns:
            List of batch actions
        """
        batch_actions = []
        
        # Get tab elements and content area
        tab_elements = []
        active_tab = None
        content_area = None
        
        for element in pattern.elements:
            if element.role == "tab":
                tab_elements.append(element)
            elif element.role == "active_tab":
                active_tab = element
                tab_elements.append(element)  # Also add to general tabs
            elif element.role == "content":
                content_area = element
        
        # No tabs = cannot create tab batch
        if not tab_elements:
            return []
        
        # Get current active tab
        if not active_tab and tab_elements:
            # If no active tab detected, assume the first one
            active_tab = tab_elements[0]
        
        # Strategy: Navigate through tabs systematically
        # 1. Start with tabs after the active tab
        # 2. Then tabs before the active tab (if any)
        
        # Reorder tabs to start with the one after active tab
        if active_tab:
            active_index = next((i for i, tab in enumerate(tab_elements) if tab.id == active_tab.id), -1)
            if active_index >= 0:
                # Place tabs after active tab first, then tabs before
                tabs_to_visit = tab_elements[active_index+1:] + tab_elements[:active_index]
            else:
                tabs_to_visit = tab_elements
        else:
            tabs_to_visit = tab_elements
        
        # Limit number of tabs to process (to avoid too many actions)
        tabs_to_visit = tabs_to_visit[:min(len(tabs_to_visit), 3)]  # Visit up to 3 tabs
        
        # Generate click actions for tabs
        for tab in tabs_to_visit:
            # Skip tab if it's already active
            if active_tab and tab.id == active_tab.id:
                continue
            
            # Skip if not clickable or no click actions
            if not tab.properties.get("has_click_action", False):
                continue
            
            # Get click action
            click_actions = [a for a in tab.actions if a.event == "click"]
            if not click_actions:
                continue
                
            click_action = click_actions[0]
            
            # Get tab text if available
            tab_text = tab.properties.get("text", "")
            explanation = f"Click on tab"
            if tab_text:
                explanation = f"Click on '{tab_text}' tab"
            
            batch_actions.append({
                "action_type": "click",
                "target": tab.id,
                "target_view": tab.view,
                "action_id": str(click_action.id),
                "explanation": explanation
            })
            
            # If we have a content area, add interactions with it after clicking a tab
            if content_area and len(batch_actions) > 0:
                content_actions = self._generate_content_area_actions(content_area, 1)  # 1 action per tab content
                if content_actions:
                    batch_actions.extend(content_actions)
        
        return batch_actions
    
    def _generate_content_area_actions(self, content_area: PatternElement, max_actions: int = 1) -> List[Dict[str, Any]]:
        """
        Generate actions to interact with tab content area.
        
        Args:
            content_area: Content area element
            max_actions: Maximum number of actions to generate
            
        Returns:
            List of content area actions
        """
        actions = []
        
        # Check for scrollability in content area
        if content_area.view.get("scrollable", False):
            # Find scroll actions
            scroll_actions = [a for a in content_area.actions if "scroll" in a.event]
            if scroll_actions:
                scroll_action = scroll_actions[0]
                
                # Assume vertical scrolling by default
                scroll_direction = "down"
                
                # If width > height, might be horizontal scrolling
                bounds = content_area.view.get("bounds", {})
                if bounds:
                    width = bounds.get("right", 0) - bounds.get("left", 0)
                    height = bounds.get("bottom", 0) - bounds.get("top", 0)
                    if width > height * 1.5:  # Width significantly larger than height
                        scroll_direction = "right"
                
                # Add scroll action
                actions.append({
                    "action_type": f"scroll_{scroll_direction}",
                    "target": content_area.id,
                    "target_view": content_area.view,
                    "action_id": str(scroll_action.id),
                    "explanation": f"Scroll {scroll_direction} in tab content to explore"
                })
        
        # Limit to requested number of actions
        return actions[:max_actions]
    
    def _generate_dialog_batch(self, pattern: PatternResult, screen: ScreenDescription,
                            state_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate a batch of actions for a dialog pattern.
        
        Args:
            pattern: Dialog pattern result
            screen: Screen description
            state_data: State data
            
        Returns:
            List of batch actions
        """
        batch_actions = []
        
        # Get dialog elements by role
        input_fields = []
        buttons = []
        positive_button = None
        negative_button = None
        
        for element in pattern.elements:
            if element.role == "input":
                input_fields.append(element)
            elif "button" in element.role:
                buttons.append(element)
                
                # Track specific button types
                if element.role == "positive_button":
                    positive_button = element
                elif element.role == "negative_button":
                    negative_button = element
        
        # No buttons = cannot create meaningful dialog batch
        if not buttons:
            return []
        
        # Determine dialog type and strategy
        dialog_type = pattern.properties.get("dialog_type", "simple_dialog")
        
        # For input dialogs, fill inputs then click positive button
        if dialog_type == "input_dialog" and input_fields:
            # Add actions to fill input fields
            for field in input_fields:
                # Skip if no set_text actions
                set_text_actions = [a for a in field.actions if a.event == "set_text"]
                if not set_text_actions:
                    continue
                
                set_text_action = set_text_actions[0]
                
                # Generate appropriate text value
                text_value = "test input"  # Default
                
                # Try to infer input type from properties
                hint = field.properties.get("hint", "").lower()
                if hint:
                    if "email" in hint:
                        text_value = "test@example.com"
                    elif "password" in hint:
                        text_value = "password123"
                    elif "name" in hint:
                        text_value = "Test User"
                    elif "phone" in hint:
                        text_value = "1234567890"
                
                batch_actions.append({
                    "action_type": "set_text",
                    "target": field.id,
                    "target_view": field.view,
                    "params": {
                        "text": text_value
                    },
                    "action_id": str(set_text_action.id),
                    "explanation": f"Fill dialog input field"
                })
            
            # Choose appropriate button to click (prefer positive button)
            target_button = positive_button if positive_button else buttons[0]
        
        # For confirmation dialogs, usually click positive button
        elif dialog_type in ["confirmation_dialog", "alert_dialog"]:
            # Choose appropriate button to click (prefer positive button)
            target_button = positive_button if positive_button else buttons[0]
        
        # For date/time pickers, interact then confirm
        elif dialog_type in ["date_picker", "time_picker"]:
            # TODO: Add specific interactions for date/time pickers
            # For now, just click the positive button
            target_button = positive_button if positive_button else buttons[0]
        
        # For other dialogs, choose appropriate button
        else:
            # Default to first button
            target_button = buttons[0]
        
        # Add button click action if we have a target button
        if target_button:
            # Find click action
            click_actions = [a for a in target_button.actions if a.event == "click"]
            if click_actions:
                click_action = click_actions[0]
                
                # Get button text if available
                button_text = target_button.properties.get("button_text", "")
                explanation = f"Click {target_button.role.replace('_', ' ')} on dialog"
                if button_text:
                    explanation = f"Click '{button_text}' button on dialog"
                
                batch_actions.append({
                    "action_type": "click",
                    "target": target_button.id,
                    "target_view": target_button.view,
                    "action_id": str(click_action.id),
                    "explanation": explanation
                })
        
        return batch_actions
        
    def _generate_navigation_batch(self, pattern: PatternResult, screen: ScreenDescription,
                               state_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate a batch of actions for a navigation pattern.
        
        Args:
            pattern: Navigation pattern result
            screen: Screen description
            state_data: State data
            
        Returns:
            List of batch actions
        """
        batch_actions = []
        
        # Get navigation elements
        container = None
        nav_items = []
        
        for element in pattern.elements:
            if element.role == "container":
                container = element
            elif element.role == "navigation_item":
                nav_items.append(element)
        
        # No navigation items = cannot create batch
        if not nav_items:
            return []
        
        # Determine navigation type
        nav_type = pattern.properties.get("navigation_type", "unknown")
        
        # For drawer navigation, first open drawer if needed
        if nav_type == "drawer" and container:
            # Check if drawer is already open
            drawer_open = False
            
            # Look for drawer container to determine if it's already open
            if container.view.get("visible", False):
                drawer_open = True
                
            # If drawer is not open, find and click hamburger menu button
            if not drawer_open:
                # Look for the first nav item that seems like a drawer toggle
                drawer_toggle = None
                for item in screen.items:
                    resource_id = item.view.get("resource_id", "").lower()
                    content_desc = item.view.get("content_description", "").lower()
                    
                    # Check for hamburger menu indicators
                    if (("drawer" in resource_id or "menu" in resource_id) and 
                        item.view.get("clickable", False)):
                        drawer_toggle = item
                        break
                    
                    # Check content description for menu indicators
                    if (any(menu_term in content_desc for menu_term in 
                           ["menu", "drawer", "navigation"]) and 
                        item.view.get("clickable", False)):
                        drawer_toggle = item
                        break
                
                # Add action to open drawer
                if drawer_toggle:
                    # Find click action
                    click_actions = [a for a in drawer_toggle.actions if a.event == "click"]
                    if click_actions:
                        click_action = click_actions[0]
                        
                        batch_actions.append({
                            "action_type": "click",
                            "target": drawer_toggle.view.get("id", ""),
                            "target_view": drawer_toggle.view,
                            "action_id": str(click_action.id),
                            "explanation": "Open navigation drawer"
                        })
        
        # Add navigation items (limited to prevent too many actions)
        nav_items_to_use = nav_items[:min(len(nav_items), 2)]  # Use up to 2 navigation items
        
        # Look for MOP-relevant items and prioritize them
        mop_items = [item for item in nav_items if item.properties.get("reaches_mop", False)]
        if mop_items and len(mop_items) > 0:
            # Replace one item with MOP-relevant item if not already included
            if mop_items[0] not in nav_items_to_use:
                if len(nav_items_to_use) > 0:
                    nav_items_to_use[-1] = mop_items[0]
        
        # Generate click actions for navigation items
        for item in nav_items_to_use:
            # Skip if not clickable or no click actions
            if not item.properties.get("has_click_action", False):
                continue
            
            # Get click action
            click_actions = [a for a in item.actions if a.event == "click"]
            if not click_actions:
                continue
                
            click_action = click_actions[0]
            
            # Get item text if available
            item_text = item.properties.get("text", "")
            explanation = f"Navigate to menu item"
            if item_text:
                explanation = f"Navigate to '{item_text}'"
            
            batch_actions.append({
                "action_type": "click",
                "target": item.id,
                "target_view": item.view,
                "action_id": str(click_action.id),
                "explanation": explanation
            })
        
        return batch_actions