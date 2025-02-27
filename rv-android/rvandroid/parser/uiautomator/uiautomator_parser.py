# rvandroid/parser/uiautomator/uiautomator_parser.py

import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
import json

from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.droidbot.visitor import ScreenDescription, ScreenItem, ItemAction, Counter
from rvandroid.model.widget import WidgetEventType

logger = logging.getLogger(__name__)

class UIElement:
    """Represents a UI element from UIAutomator XML dump"""
    
    def __init__(self, attributes: Dict[str, str]):
        self.attributes = attributes
        self.children: List[UIElement] = []
        
        # Common attributes
        self.resource_id = attributes.get('resource-id', '')
        self.text = attributes.get('text', '')
        self.content_desc = attributes.get('content-desc', '')
        self.class_name = attributes.get('class', '')
        self.package = attributes.get('package', '')
        self.clickable = attributes.get('clickable', 'false') == 'true'
        self.checkable = attributes.get('checkable', 'false') == 'true'
        self.checked = attributes.get('checked', 'false') == 'true'
        self.scrollable = attributes.get('scrollable', 'false') == 'true'
        self.long_clickable = attributes.get('long-clickable', 'false') == 'true'
        self.enabled = attributes.get('enabled', 'false') == 'true'
        self.focused = attributes.get('focused', 'false') == 'true'
        self.selected = attributes.get('selected', 'false') == 'true'
        self.password = attributes.get('password', 'false') == 'true'
        self.bounds_str = attributes.get('bounds', '')
        
        # Parse bounds string like "[0,0][1080,1920]"
        self.bounds = self._parse_bounds(self.bounds_str)
        
    def _parse_bounds(self, bounds_str: str) -> List[List[int]]:
        """Parse bounds string into a list of coordinates"""
        if not bounds_str:
            return [[0, 0], [0, 0]]
        
        try:
            # Handle bounds like "[0,0][1080,1920]"
            parts = bounds_str.replace('[', '').replace(']', '').split(',')
            if len(parts) == 4:
                return [[int(parts[0]), int(parts[1])], [int(parts[2]), int(parts[3])]]
        except Exception as e:
            logger.error(f"Error parsing bounds: {e}")
        
        return [[0, 0], [0, 0]]
    
    def add_child(self, child: 'UIElement') -> None:
        self.children.append(child)
    
    @property
    def actionable(self) -> bool:
        """Check if the element is actionable"""
        return (self.clickable or self.scrollable or self.checkable or 
                self.long_clickable or self.enabled)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format similar to DroidBot state"""
        return {
            "class": self.class_name,
            "resource_id": self.resource_id,
            "text": self.text,
            "content_description": self.content_desc,
            "clickable": self.clickable,
            "checkable": self.checkable,
            "checked": self.checked,
            "scrollable": self.scrollable,
            "long_clickable": self.long_clickable,
            "enabled": self.enabled,
            "focused": self.focused,
            "selected": self.selected,
            "is_password": self.password,
            "package": self.package,
            "bounds": self.bounds
        }


def parse_xml_dump(xml_content: str) -> UIElement:
    """Parse UIAutomator XML dump into a tree of UIElements"""
    root = ET.fromstring(xml_content)
    return _parse_element(root)


def _parse_element(element: ET.Element) -> UIElement:
    """Recursively parse XML elements into UIElements"""
    ui_element = UIElement(element.attrib)
    
    for child in element:
        ui_element.add_child(_parse_element(child))
    
    return ui_element


def get_activity_from_uiautomator(xml_content: str) -> str:
    """Extract current activity from UIAutomator dump"""
    print(f"Parsing XML content (get_activity_from_uiautomator): {xml_content}")
    try:
        root = ET.fromstring(xml_content)
        # The activity is usually the package name of the top element
        if 'package' in root.attrib:
            return root.attrib['package']
    except Exception as e:
        logger.error(f"Error extracting activity: {e}")
    
    return "unknown.activity"


def extract_text_description(element: UIElement, counter: Counter, static_info: Optional[StaticAnalysisData] = None) -> ScreenItem:
    """Extract text description for a UI element"""
    view_dict = element.to_dict()
    actions = []
    
    # Generate description based on element type
    if "Button" in element.class_name:
        description = f"Button {_with_text(element)}{_with_description(element)}{_with_resource_id(element)}"
    elif "EditText" in element.class_name:
        description = f"Editable text field {_with_text(element)}{_with_description(element)}{_with_resource_id(element)}"
        if element.password:
            description = f"Password field {_with_text(element)}{_with_description(element)}{_with_resource_id(element)}"
    elif "TextView" in element.class_name:
        description = f"Text view {_with_text(element)}{_with_description(element)}{_with_resource_id(element)}"
    elif "CheckBox" in element.class_name:
        checked = " that is checked" if element.checked else " that is unchecked"
        description = f"Checkbox{checked} {_with_text(element)}{_with_description(element)}{_with_resource_id(element)}"
    elif "ImageButton" in element.class_name:
        description = f"Image button {_with_text(element)}{_with_description(element)}{_with_resource_id(element)}"
    elif "ImageView" in element.class_name:
        description = f"Image {_with_text(element)}{_with_description(element)}{_with_resource_id(element)}"
    elif "ToggleButton" in element.class_name:
        state = " that is ON" if element.checked else " that is OFF"
        description = f"Toggle button{state} {_with_text(element)}{_with_description(element)}{_with_resource_id(element)}"
    elif "Switch" in element.class_name:
        state = " that is ON" if element.checked else " that is OFF"
        description = f"Switch{state} {_with_text(element)}{_with_description(element)}{_with_resource_id(element)}"
    elif "RadioButton" in element.class_name:
        selected = " that is selected" if element.selected else " that is not selected"
        description = f"Radio button{selected} {_with_text(element)}{_with_description(element)}{_with_resource_id(element)}"
    else:
        description = f"Element {element.class_name} {_with_text(element)}{_with_description(element)}{_with_resource_id(element)}"
    
    # Generate possible actions
    actions = _get_possible_actions(element, counter, static_info)
    
    return ScreenItem(view_dict, description, actions)


def _get_possible_actions(element: UIElement, counter: Counter, static_info: Optional[StaticAnalysisData] = None) -> List[ItemAction]:
    """Generate possible actions for an element"""
    actions = []
    
    # Generate actions based on element properties
    if element.clickable:
        action = ItemAction(
            id=counter.inc(),
            text=f"CLICK ({counter.get()})" + (f" on '{element.text}'" if element.text else ""),
            event=WidgetEventType.CLICK,
            reaches_mop=False,
            directly_reaches_mop=False
        )
        
        # Enhance with static analysis if available
        if static_info and element.resource_id:
            resource_name = element.resource_id.split('/')[-1] if '/' in element.resource_id else element.resource_id
            window = static_info.windows.get_window(get_activity_from_resource_id(element.resource_id))
            if window:
                widget = window.get_widget_by_name(resource_name)
                if widget and widget.events:
                    for event in widget.events:
                        if event.type == WidgetEventType.CLICK:
                            method = static_info.classes.methods.get(event.signature)
                            if method:
                                action.reaches_mop = method.reaches_mop
                                action.directly_reaches_mop = method.directly_reaches_mop
        
        actions.append(action)
    
    if element.long_clickable:
        actions.append(ItemAction(
            id=counter.inc(),
            text=f"LONG_CLICK ({counter.get()})" + (f" on '{element.text}'" if element.text else ""),
            event=WidgetEventType.LONG_CLICK,
            reaches_mop=False,
            directly_reaches_mop=False
        ))
    
    if element.checkable:
        if element.checked:
            actions.append(ItemAction(
                id=counter.inc(),
                text=f"UNCHECK ({counter.get()})" + (f" '{element.text}'" if element.text else ""),
                event=WidgetEventType.CLICK,
                reaches_mop=False,
                directly_reaches_mop=False
            ))
        else:
            actions.append(ItemAction(
                id=counter.inc(),
                text=f"CHECK ({counter.get()})" + (f" '{element.text}'" if element.text else ""),
                event=WidgetEventType.CLICK,
                reaches_mop=False,
                directly_reaches_mop=False
            ))
    
    if element.scrollable:
        for direction in ["UP", "DOWN", "LEFT", "RIGHT"]:
            actions.append(ItemAction(
                id=counter.inc(),
                text=f"SCROLL {direction} ({counter.get()})",
                event=WidgetEventType.SCROLL,
                reaches_mop=False,
                directly_reaches_mop=False
            ))
    
    # Handle EditText elements
    if "EditText" in element.class_name:
        hint = ""
        if element.text:
            hint = f" [current: '{element.text}']"
        elif element.content_desc:
            hint = f" [hint: '{element.content_desc}']"
            
        actions.append(ItemAction(
            id=counter.inc(),
            text=f"SET_TEXT ({counter.get()}) {hint}",
            event=WidgetEventType.TEXT_CHANGE,
            reaches_mop=False,
            directly_reaches_mop=False
        ))
    
    return actions


def _with_text(element: UIElement) -> str:
    """Format element text description"""
    return f"with text '{element.text}'" if element.text else "with no text"


def _with_description(element: UIElement) -> str:
    """Format element content description"""
    return f" with description '{element.content_desc}'" if element.content_desc else ""


def _with_resource_id(element: UIElement) -> str:
    """Format element resource ID description"""
    if element.resource_id:
        parts = element.resource_id.split('/')
        if len(parts) > 1:
            return f" with id={parts[1]}"
    return ""


def get_activity_from_resource_id(resource_id: str) -> str:
    """Extract activity name from resource ID"""
    if '/' in resource_id:
        package = resource_id.split('/')[0]
        activity = package.split('.')[-1]
        return activity
    return ""


def parse_uiautomator_dump(xml_content: str, static_data: Optional[StaticAnalysisData] = None) -> ScreenDescription:
    """
    Parse UIAutomator XML dump to create a ScreenDescription
    
    Args:
        xml_content: UIAutomator XML dump
        static_data: Optional static analysis data
        
    Returns:
        ScreenDescription object containing all parsed items
    """
    print(f"Parsing UIAutomator XML dump...")
    # Parse XML into a tree structure
    root_element = parse_xml_dump(xml_content)
    
    # Extract current activity
    activity = get_activity_from_uiautomator(xml_content)
    
    # Process elements to extract screen items
    counter = Counter()
    items = []
    
    def process_element(element):
        """Recursively process elements to find actionable ones"""
        if element.actionable:
            item = extract_text_description(element, counter, static_data)
            items.append(item)
        
        for child in element.children:
            process_element(child)
    
    # Process the entire tree
    process_element(root_element)
    
    print(f">>>>= {ScreenDescription(activity, items)}")
    # Create and return the screen description
    return ScreenDescription(activity, items)


def uiautomator_to_state(xml_content: str) -> Dict[str, Any]:
    """
    Convert UIAutomator XML to a state dictionary similar to DroidBot state
    
    Args:
        xml_content: UIAutomator XML dump
        
    Returns:
        State dictionary compatible with existing code
    """
    root_element = parse_xml_dump(xml_content)
    activity = get_activity_from_uiautomator(xml_content)
    
    def element_to_dict(element):
        result = element.to_dict()
        if element.children:
            result["children"] = [element_to_dict(child) for child in element.children]
        return result
    
    state = {
        "activity": activity,
        "view_tree": element_to_dict(root_element),
        "package_name": root_element.package
    }
    
    print(f"State: {state}")    
    
    return state