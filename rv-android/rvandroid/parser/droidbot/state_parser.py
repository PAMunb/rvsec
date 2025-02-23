# state_parser.py

from typing import Dict, List, Optional
from rvandroid.model.classes import Classes
from rvandroid.model.window import Windows, Window
from rvandroid.model.wtg import WindowTransitionGraph
from rvandroid.parser.droidbot.view_visitor import ViewVisitor

class StateElement:
    """Base class for state elements"""
    def accept(self, visitor: 'StateVisitor') -> None:
        pass

class ViewTreeElement(StateElement):
    """Represents a view element in the UI tree"""
    def __init__(self, data: Dict):
        self.data = data
        self.children: List[ViewTreeElement] = []
        
    def accept(self, visitor: 'StateVisitor') -> None:
        visitor.visit_view(self)
        # Fixed: Changed child.visit(visitor) to child.accept(visitor)
        for child in self.children:
            child.accept(visitor)  # Using accept instead of visit

class StateParser:
    """Parses DroidBot state and combines with static analysis data"""
    def __init__(self, classes: Classes, windows: Windows, wtg: WindowTransitionGraph):
        self.classes = classes
        self.windows = windows
        self.wtg = wtg
        
    def parse_state(self, state: Dict) -> Dict:
        """
        Parses DroidBot state and enriches with static analysis info
        
        Args:
            state: Raw state data from DroidBot
            
        Returns:
            Enriched state information
        """
        stack = state.get("stack", [])
        new_stack = [name.replace("/", "") for name in stack]
            
        parsed_state = {
            "activity": state.get("activity", "").replace("/", ""),
            "activity_stack": new_stack,
            "screen_dimensions": state.get("screen_size", {}),
            "views": []
        }
        
        # Create view tree
        view_tree = self._build_view_tree(state.get("view_tree", {}))
        
        # Find corresponding Window from static analysis
        current_window = self._find_matching_window(parsed_state["activity"])
        
        # Create visitor to process view tree
        visitor = ViewVisitor(self.classes, current_window)
        if view_tree:
            view_tree.accept(visitor)
            
        parsed_state["views"] = visitor.get_processed_views()
        parsed_state["window_info"] = visitor.get_window_info()
        
        return parsed_state
        
    def _build_view_tree(self, view_data: Dict) -> Optional[ViewTreeElement]:
        """Builds tree structure from view hierarchy"""
        if not view_data:
            return None
            
        element = ViewTreeElement(view_data)
        for child in view_data.get("children", []):
            child_element = self._build_view_tree(child)
            if child_element:
                element.children.append(child_element)
        
        return element
        
    def _find_matching_window(self, activity_name: str) -> Optional[Window]:
        """Finds corresponding Window from static analysis"""
        if not activity_name:
            return None
        return self.windows.get_window(activity_name)