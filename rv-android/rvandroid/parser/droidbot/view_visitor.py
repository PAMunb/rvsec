# view_visitor.py

from typing import Dict, List, Optional
from rvandroid.model.classes import Classes
from rvandroid.model.window import Window
from rvandroid.model.widget import Widget, WidgetEventType, WidgetType

class ViewVisitor:
    """Visitor for processing view elements and combining with static analysis"""
    
    def __init__(self, classes: Classes, window: Optional[Window]):
        self.classes = classes
        self.window = window
        self.processed_views: List[Dict] = []
        self.window_info: Dict = {
            "total_widgets": 0,
            "matched_widgets": 0,
            "interactive_elements": 0
        }
        
    def visit_view(self, view: 'ViewTreeElement') -> None:
        """
        Process a view element and enrich with static analysis data
        
        Args:
            view: View element to process
        """
        view_data = view.data
        self.window_info["total_widgets"] += 1
        
        print(f"\n\nProcessing view: {view_data}")
        
        # Basic view information
        name = view_data.get("resource_id", "")
        if name and "/" in name:
            name = name.split("/")[-1]
        processed_view = {
            "id": "",
            "name": name, 
            "class": view_data.get("class", ""),
            "text": view_data.get("text", ""),
            "hint": view_data.get("hint", ""),
            "description": view_data.get("content_description", ""),
            "clickable": view_data.get("clickable", False),
            "checkable": view_data.get("checkable", False),
            "checked": view_data.get("checked", False),
            "selected": view_data.get("selected", False),
            "scrollable": view_data.get("scrollable", False),
            "is_password": view_data.get("is_password", False),
            "visible": view_data.get("visible", True),
            "enabled": view_data.get("enabled", True),
            "focused": view_data.get("focused", False),
            "editable": view_data.get("editable", False),
            "bounds": view_data.get("bounds", {}),
        }
        
        # Add interaction capabilities
        self._add_interaction_info(processed_view, view_data)
        
        # Match with static analysis widget if possible
        print(f"window: {self.window}")
        if self.window:
            static_widget = self._find_matching_widget(processed_view)
            print(f"static_widget: {static_widget}")
            if static_widget:
                self._enrich_with_static_data(processed_view, static_widget)
                self.window_info["matched_widgets"] += 1
        
        if self._is_interactive(processed_view):
            self.window_info["interactive_elements"] += 1
            self.processed_views.append(processed_view)
    
    def _add_interaction_info(self, processed_view: Dict, view_data: Dict) -> None:
        """Adds interaction-related information to the processed view"""
        interactions = []
        
        if view_data.get("clickable") or view_data.get("checkable"):
            interactions.append(WidgetEventType.CLICK.name)
        if view_data.get("long_clickable"):
            interactions.append(WidgetEventType.LONG_CLICK.name)
        if view_data.get("scrollable"):
            interactions.append(WidgetEventType.SCROLL.name)
        if view_data.get("editable"):
            interactions.append(WidgetEventType.TEXT_CHANGE.name)
            
        processed_view["possible_actions"] = interactions
        
    def _find_matching_widget(self, view: Dict) -> Optional[Widget]:
        """Attempts to match view with static analysis widget"""
        if not self.window:
            return None
        
        print(f"Finding matching widget for view: {view}")
            
        # Try matching by resource ID
        if view["id"]:
            widget = self.window.get_widget(view["id"])
            if widget:
                return widget
            
        if view["name"]:
            widget = self.window.get_widget_by_name(view["name"])
            if widget:
                return widget
                
        # Try matching by class and properties
        for widget in self.window.widgets.values():
            if self._is_matching_widget(view, widget):
                return widget
                
        return None
        
    def _is_matching_widget(self, view: Dict, widget: Widget) -> bool:
        """Checks if view matches static analysis widget"""
        # Match by widget type
        view_class = view["class"].split(".")[-1]
        # if widget.type != WidgetType.from_class_name(view["class"]):
        if widget.type != WidgetType.from_class_name(view_class):
            return False
            
        # Match by text content if available
        if widget.text and view["text"] and widget.text == view["text"]:
            return True
            
        return False
        
    def _enrich_with_static_data(self, view: Dict, widget: Widget) -> None:
        """Adds static analysis information to view data"""
        # TODO events: type, reaches_mop, directly_reaches_mop
        # update widget id with static analysis id
        view["id"] = widget.id
        events = []
        for event in widget.events:
            method = self.classes.methods[event.signature] if event.signature in self.classes.methods else None
            data = {
                "type": event.type.name,
                "reaches_mop": method.reaches_mop if method else False,
                "directly_reaches_mop": method.directly_reaches_mop if method else False
            }
            events.append(data)
            
        view["static_info"] = {
            "widget_type": widget.type.name,
            "registered_events": events,
            "field_name": widget.field if widget.field else None
        }
        
    def _is_interactive(self, view: Dict) -> bool:
        """Determines if view is interactive based on properties"""
        return bool(view.get("possible_actions"))
        
    def get_processed_views(self) -> List[Dict]:
        """Returns list of processed views"""
        return self.processed_views
        
    def get_window_info(self) -> Dict:
        """Returns window statistics"""
        return self.window_info