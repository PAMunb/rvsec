"""UI Elements information fragment for the prompt system.

This module defines a specialized fragment for extracting and formatting UI element
information from the application state.
"""

from typing import Any, Dict, Optional, List

from rvandroid.llm.constants import FragmentType, StateEntry
from rvandroid.llm.prompt.information.base_fragment import InformationFragment


class UIElementsFragment(InformationFragment):
    """Fragment for extracting and formatting UI element information.
    
    This fragment converts the UI elements from the screen state into a
    formatted string representation that can be included in prompts.
    """
    
    def __init__(self, name: str = FragmentType.UI_ELEMENTS, priority: int = 500):
        """Initialize the UI elements fragment.
        
        Args:
            name: The name of the fragment (default: FragmentType.UI_ELEMENTS).
            priority: The priority of the fragment (default: 500 - highest priority).
        """
        super().__init__(name, priority)
    
    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """Generate formatted UI element information from the application state.
        
        Args:
            state: The current application state.
            context: Additional context information.
            
        Returns:
            A formatted string representation of the UI elements.
        """
        if not state:
            return "No state information available."
        
        # Priority 1: Use ScreenDescription if available
        if StateEntry.STRUCTURED_SCREEN in state:
            # Get the ScreenDescription object
            screen_description = state[StateEntry.STRUCTURED_SCREEN]
            # Use the object's __str__ method to get a formatted representation
            return str(screen_description)
        
        # Priority 2: Use pre-formatted screen description if already available
        if StateEntry.SCREEN_DESCRIPTION in state:
            return state[StateEntry.SCREEN_DESCRIPTION]
        
        return "No screen information available."
    
    def _format_screen_elements(self, screen: Dict[str, Any]) -> str:
        """Format screen elements for display in the prompt.
        
        This method handles different formats of screen data, including both
        DroidBot and UIAutomator structures, and produces a consistently formatted
        output regardless of the input format. It extracts component attributes
        carefully with comprehensive error handling to ensure robustness.
        
        Args:
            screen: The screen information from the state.
            
        Returns:
            A formatted string representation of the screen elements.
        """
        if not screen:
            return "No screen information available."
        
        # Extract components, handling both flat and hierarchical structures
        components = screen.get("components", [])
        
        # Handle hierarchical structure if components is empty but children exists
        if not components and "children" in screen:
            # This might be a hierarchical tree structure; flatten it
            components = self._flatten_component_tree(screen)
        
        if not components:
            return "No UI components found on screen."
        
        formatted_parts = []
        
        # Add screen information
        title = screen.get("title", "")
        activity = screen.get("activity", "")
        package = screen.get("package", "")
        
        # Add header information if available
        if title:
            formatted_parts.append(f"Screen title: {title}")
        if activity:
            formatted_parts.append(f"Activity: {activity}")
        if package:
            formatted_parts.append(f"Package: {package}")
        
        # Add section header for components
        formatted_parts.append("\nUI Components:")
        
        # Process each component
        for i, component in enumerate(components):
            try:
                # Extract basic component properties with fallbacks
                component_type = self._extract_component_type(component)
                component_text = component.get("text", "")
                component_id = component.get("resource_id", "")
                component_content_desc = component.get("content_desc", "") or component.get("content_description", "")
                component_class = component.get("class", "")
                component_clickable = component.get("clickable", False)
                component_enabled = component.get("enabled", True)
                component_checkable = component.get("checkable", False)
                component_checked = component.get("checked", False)
                component_focused = component.get("focused", False)
                
                # Begin component description
                details = []
                
                # Add text content if available
                if component_text:
                    details.append(f"text='{self._safe_truncate(component_text)}'")
                
                # Add resource ID if available
                if component_id:
                    # Extract short ID from package:id/name format if needed
                    if "/" in component_id:
                        short_id = component_id.split("/")[-1]
                        details.append(f"id='{short_id}'")
                    else:
                        details.append(f"id='{component_id}'")
                
                # Add content description if available
                if component_content_desc:
                    details.append(f"desc='{self._safe_truncate(component_content_desc)}'")
                
                # Add class name if available and not already covered by component_type
                if component_class and component_type != component_class.split(".")[-1]:
                    # Just use the base class name without package
                    base_class = component_class.split(".")[-1]
                    details.append(f"class='{base_class}'")
                
                # Add bounds if available
                bounds_str = self._format_bounds(component.get("bounds"))
                if bounds_str:
                    details.append(bounds_str)
                
                # Add state information
                state_flags = []
                if component_clickable:
                    state_flags.append("clickable")
                else:
                    state_flags.append("not clickable")
                    
                if not component_enabled:
                    state_flags.append("disabled")
                    
                if component_checkable:
                    state_flags.append("checkable")
                    if component_checked:
                        state_flags.append("checked")
                        
                if component_focused:
                    state_flags.append("focused")
                
                if state_flags:
                    details.append(", ".join(state_flags))
                
                # Format the final component description
                formatted_parts.append(f"{i+1}. {component_type}: {', '.join(details)}")
                
            except Exception as e:
                # Safely handle any errors in component processing
                self.logger.error(f"Error formatting component {i}: {e}")
                formatted_parts.append(f"{i+1}. [Error formatting component]")
        
        return "\n".join(formatted_parts)
    
    def _extract_component_type(self, component: Dict[str, Any]) -> str:
        """Extract the component type using various fallback strategies.
        
        Args:
            component: The component data.
            
        Returns:
            The component type string.
        """
        # Try different fields that might contain type information
        if "type" in component and component["type"]:
            return component["type"]
        
        if "class" in component and component["class"]:
            # Extract the last part of the class name (e.g., android.widget.Button -> Button)
            class_name = component["class"]
            return class_name.split(".")[-1]
        
        # Look for common UI component indicators in other fields
        resource_id = component.get("resource_id", "").lower()
        if resource_id and ("button" in resource_id or "btn" in resource_id):
            return "Button"
        
        if resource_id and ("text" in resource_id or "edit" in resource_id):
            return "EditText"
        
        # Default type if nothing else is found
        return "View"
    
    def _format_bounds(self, bounds) -> str:
        """Format component bounds consistently regardless of input format.
        
        Handles multiple bounds formats:
        - Dictionary: {"left": 0, "top": 0, "right": 100, "bottom": 100}
        - List of points: [[0, 0], [100, 100]]
        - String: "[0,0][100,100]"
        
        Args:
            bounds: Bounds data in various formats.
            
        Returns:
            Formatted bounds string or empty string if bounds are invalid.
        """
        if not bounds:
            return ""
            
        try:
            if isinstance(bounds, dict):
                # Dictionary format
                left = bounds.get("left", 0)
                top = bounds.get("top", 0)
                right = bounds.get("right", 0)
                bottom = bounds.get("bottom", 0)
                return f"bounds=[{left},{top},{right},{bottom}]"
                
            elif isinstance(bounds, list) and len(bounds) >= 2:
                # List format [[left,top], [right,bottom]]
                try:
                    left, top = bounds[0]
                    right, bottom = bounds[1]
                    return f"bounds=[{left},{top},{right},{bottom}]"
                except (IndexError, TypeError, ValueError):
                    # Try alternative interpretation if needed
                    if len(bounds) >= 4 and all(isinstance(coord, (int, float)) for coord in bounds[:4]):
                        # List format [left, top, right, bottom]
                        left, top, right, bottom = bounds[:4]
                        return f"bounds=[{left},{top},{right},{bottom}]"
            
            elif isinstance(bounds, str):
                # String format like "[0,0][100,100]"
                import re
                coords = re.findall(r'\[(\d+),(\d+)\]', bounds)
                if len(coords) >= 2:
                    left, top = map(int, coords[0])
                    right, bottom = map(int, coords[1])
                    return f"bounds=[{left},{top},{right},{bottom}]"
        
        except Exception:
            # Silently handle any parsing errors
            pass
            
        return ""
    
    def _safe_truncate(self, text: str, max_length: int = 50) -> str:
        """Safely truncate text to prevent excessively long descriptions.
        
        Args:
            text: The text to truncate.
            max_length: Maximum length before truncation.
            
        Returns:
            The truncated text.
        """
        if not text:
            return ""
            
        text = str(text).replace("\n", " ").strip()
        
        if len(text) > max_length:
            return text[:max_length-3] + "..."
            
        return text
    
    def _flatten_component_tree(self, root: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Flatten a hierarchical component tree into a list of components.
        
        This handles DroidBot's hierarchical structure by recursively traversing
        the component tree and flattening it into a single list.
        
        Args:
            root: The root component or tree.
            
        Returns:
            A list of flattened components.
        """
        components = []
        
        def extract_components(node, depth=0):
            """Extract components recursively from a node."""
            if not node:
                return
                
            # Create a copy to avoid modifying the original
            node_copy = node.copy()
            
            # Add depth information
            node_copy["depth"] = depth
            
            # Add type information if missing
            if "type" not in node_copy and "class" in node_copy:
                node_copy["type"] = node_copy["class"].split(".")[-1]
                
            # Add the node to our list
            components.append(node_copy)
            
            # Process children recursively
            children = node.get("children", [])
            for child in children:
                extract_components(child, depth + 1)
                
        # Start extraction from the root
        extract_components(root)
        return components
    
    def should_include(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if UI elements information should be included.
        
        Args:
            state: The current application state.
            context: Additional context information.
            
        Returns:
            True (UI elements information should always be included).
        """
        # UI elements information should always be included as it's essential
        # for the LLM to understand the screen
        return True