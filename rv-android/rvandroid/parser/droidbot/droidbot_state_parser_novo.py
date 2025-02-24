from rvandroid.model.classes import Classes
from rvandroid.model.window import Windows
from rvandroid.model.wtg import WindowTransitionGraph
from rvandroid.parser.droidbot.visitor import *


from rvandroid.model.classes import Classes
from rvandroid.model.window import Windows
from rvandroid.model.wtg import WindowTransitionGraph
from rvandroid.parser.droidbot.visitor import *
from rvandroid.model.static import StaticAnalysisData


class TextVisitor(Visitor):
    """
    A visitor implementation for generating text descriptions of Android UI elements.
    This visitor traverses the UI hierarchy and creates human-readable descriptions 
    of interactive elements like buttons, text fields, checkboxes, etc.
    """

    def __init__(self, static_info: StaticAnalysisData, activity: str):
        """
        Initialize the TextVisitor with static analysis data and activity context.
        
        Args:
            static_info: Static analysis data containing classes, windows, and transitions
            activity: Current activity being analyzed
        """
        super().__init__(static_info, activity)
        self.logging.debug(f"Initialized TextVisitor for activity: {activity}")

    def visit_node(self, node):
        """
        Visit a container node in the UI hierarchy.
        
        Args:
            node: The node to visit
        """
        self.logging.debug(f"Visiting node: {node.view_class}")
        # Container nodes are processed via their children

    def visit_leaf_node(self, leaf_node):
        """
        Visit a leaf node in the UI hierarchy that doesn't have a specific handler.
        
        Args:
            leaf_node: The leaf node to visit
        """
        self.logging.debug(f"Visiting leaf node: {leaf_node.view_class}")
        if leaf_node.actionable:
            actions = self.get_possible_actions(leaf_node, self.counter)
            text = f"Element {leaf_node.view_class} {self.__with_text(leaf_node)}{self.__has_focus(leaf_node)}{self.__with_description(leaf_node)}{self.__with_resource_id(leaf_node)}"
            item = ScreenItem(leaf_node.data, text, actions)
            self.items.append(item)
            self.window_info["interactive_elements"] += 1

    def visit_button(self, node: Node):
        """
        Visit a button element and generate its description.
        
        Args:
            node: The button node to visit
        """
        self.logging.debug(f"Visiting button: {node.resource_id}")
        widget = self.find_matching_widget(node)
        actions = self.get_possible_actions(node, self.counter)
        
        # Update actions with additional information from static analysis if available
        if widget:
            for action in actions:
                for event in widget.events:
                    if event.type == action.event:
                        action.reaches_mop = self._check_method_reaches_mop(event.signature)
                        action.directly_reaches_mop = self._check_method_directly_reaches_mop(event.signature)
                        
        text = self.__default_message(node, "Button ")
        item = ScreenItem(node.data, text, actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_edit_text(self, node):
        """
        Visit an editable text field and generate its description.
        
        Args:
            node: The edit text node to visit
        """
        self.logging.debug(f"Visiting edit text: {node.resource_id}")
        widget = self.find_matching_widget(node)
        actions = self.get_possible_actions(node, self.counter)
        
        # Add input type information if available
        input_type = ""
        if widget and widget.input_type:
            input_type = f" for {widget.input_type}"
            
        text = f"Editable text field{input_type} {self.__with_text(node)}{self.__has_focus(node)}{self.__with_description(node)}{self.__with_resource_id(node)}"
        
        if node.is_password:
            text = f"Password field {self.__with_text(node)}{self.__has_focus(node)}{self.__with_description(node)}{self.__with_resource_id(node)}"
            
        item = ScreenItem(node.data, text, actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_text_view(self, node):
        """
        Visit a text view element and generate its description.
        
        Args:
            node: The text view node to visit
        """
        self.logging.debug(f"Visiting text view: {node.resource_id}")
        actions = self.get_possible_actions(node, self.counter)
        
        # Only add if it has text content or is interactive
        if node.view_text or actions:
            text = f"Text view {self.__with_text(node)}{self.__with_description(node)}{self.__with_resource_id(node)}"
            
            text = text + f" :: clickable={node.clickable}, long_clickable={node.long_clickable}, checkable={node.checkable}, selected={node.selected}"
            
            item = ScreenItem(node.data, text, actions)
            self.items.append(item)
            if actions:
                self.window_info["interactive_elements"] += 1

    def visit_checkbox(self, node):
        """
        Visit a checkbox element and generate its description.
        
        Args:
            node: The checkbox node to visit
        """
        self.logging.debug(f"Visiting checkbox: {node.resource_id}")
        widget = self.find_matching_widget(node)
        actions = self.get_possible_actions(node, self.counter)
        
        checked = " that is checked" if node.checked else " that is unchecked"
        text = f"Checkbox{checked} {self.__with_text(node)}{self.__with_description(node)}{self.__has_focus(node)}{self.__with_resource_id(node)}"
        
        item = ScreenItem(node.data, text, actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_checked_text(self, node):
        """
        Visit a checked text view element and generate its description.
        
        Args:
            node: The checked text view node to visit
        """
        self.logging.debug(f"Visiting checked text view: {node.resource_id}")
        actions = self.get_possible_actions(node, self.counter)
        
        checked = " that is checked" if node.checked else " that is unchecked"
        text = f"Checkable text{checked} {self.__with_text(node)}{self.__with_description(node)}{self.__has_focus(node)}{self.__with_resource_id(node)}"
        
        item = ScreenItem(node.data, text, actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_image_button(self, node):
        """
        Visit an image button element and generate its description.
        
        Args:
            node: The image button node to visit
        """
        self.logging.debug(f"Visiting image button: {node.resource_id}")
        widget = self.find_matching_widget(node)
        actions = self.get_possible_actions(node, self.counter)
        
        text = f"Image button {self.__with_text(node)}{self.__with_description(node)}{self.__with_resource_id(node)}"
        
        item = ScreenItem(node.data, text, actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_image(self, node):
        """
        Visit an image element and generate its description.
        
        Args:
            node: The image node to visit
        """
        self.logging.debug(f"Visiting image: {node.resource_id}")
        actions = self.get_possible_actions(node, self.counter)
        
        # Only include interactive images or those with descriptions
        if actions or node.content_description:
            text = f"Image {self.__with_text(node)}{self.__with_description(node)}{self.__with_resource_id(node)}"
            item = ScreenItem(node.data, text, actions)
            self.items.append(item)
            if actions:
                self.window_info["interactive_elements"] += 1

    def visit_toggle_button(self, node):
        """
        Visit a toggle button element and generate its description.
        
        Args:
            node: The toggle button node to visit
        """
        self.logging.debug(f"Visiting toggle button: {node.resource_id}")
        widget = self.find_matching_widget(node)
        actions = self.get_possible_actions(node, self.counter)
        
        state = " that is ON" if node.checked else " that is OFF"
        text = f"Toggle button{state} {self.__with_text(node)}{self.__with_description(node)}{self.__has_focus(node)}{self.__with_resource_id(node)}"
        
        item = ScreenItem(node.data, text, actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_switch(self, node):
        """
        Visit a switch element and generate its description.
        
        Args:
            node: The switch node to visit
        """
        self.logging.debug(f"Visiting switch: {node.resource_id}")
        widget = self.find_matching_widget(node)
        actions = self.get_possible_actions(node, self.counter)
        
        state = " that is ON" if node.checked else " that is OFF"
        text = f"Switch{state} {self.__with_text(node)}{self.__with_description(node)}{self.__has_focus(node)}{self.__with_resource_id(node)}"
        
        item = ScreenItem(node.data, text, actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_radio_button(self, node):
        """
        Visit a radio button element and generate its description.
        
        Args:
            node: The radio button node to visit
        """
        self.logging.debug(f"Visiting radio button: {node.resource_id}")
        widget = self.find_matching_widget(node)
        actions = self.get_possible_actions(node, self.counter)
        
        selected = " that is selected" if node.selected else " that is not selected"
        text = f"Radio button{selected} {self.__with_text(node)}{self.__with_description(node)}{self.__has_focus(node)}{self.__with_resource_id(node)}"
        
        item = ScreenItem(node.data, text, actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_spinner(self, node):
        """
        Visit a spinner element and generate its description.
        
        Args:
            node: The spinner node to visit
        """
        self.logging.debug(f"Visiting spinner: {node.resource_id}")
        widget = self.find_matching_widget(node)
        actions = self.get_possible_actions(node, self.counter)
        
        options = ""
        if widget and widget.entries:
            options_list = ", ".join(widget.entries[:3])
            if len(widget.entries) > 3:
                options_list += f", and {len(widget.entries) - 3} more options"
            options = f" with options: {options_list}"
            
        text = f"Dropdown spinner{options} {self.__with_text(node)}{self.__with_description(node)}{self.__with_resource_id(node)}"
        
        item = ScreenItem(node.data, text, actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_radio_group(self, node):
        """
        Visit a radio group element and generate its description.
        
        Args:
            node: The radio group node to visit
        """
        self.logging.debug(f"Visiting radio group: {node.resource_id}")
        # Process children as radio buttons will be visited individually
        if node.actionable:
            actions = self.get_possible_actions(node, self.counter)
            text = f"Radio button group {self.__with_description(node)}{self.__with_resource_id(node)}"
            item = ScreenItem(node.data, text, actions)
            self.items.append(item)
            
        # Visit all children
        for child in node.children:
            child.accept(self)

    def __default_message(self, node: Node, prefix: str):
        """
        Generate a default message for a UI element.
        
        Args:
            node: The node to describe
            prefix: Prefix to add to the description
            
        Returns:
            Formatted description string
        """
        return f"{prefix}{self.__with_text(node)}{self.__has_focus(node)}{self.__with_description(node)}{self.__with_resource_id(node)}"

    def __with_text(self, node: Node):
        """
        Format node text description.
        
        Args:
            node: The node to describe
            
        Returns:
            Formatted text description
        """
        return f"with text '{node.view_text}'" if node.view_text else "with no text"
    
    def __has_focus(self, node: Node):
        """
        Format node focus description.
        
        Args:
            node: The node to describe
            
        Returns:
            Formatted focus description
        """
        return " that is focused" if node.focused else ""

    def __with_description(self, node: Node):
        """
        Format node content description.
        
        Args:
            node: The node to describe
            
        Returns:
            Formatted content description
        """
        return f" with description '{node.content_description}'" if node.content_description else ""

    def __with_resource_id(self, node: Node):
        """
        Format node resource ID description.
        
        Args:
            node: The node to describe
            
        Returns:
            Formatted resource ID description
        """
        if node.resource_id:
            parts = node.resource_id.split("/")
            if len(parts) > 1:
                return f" with id={parts[1]}"
        return ""
    
    def _check_method_reaches_mop(self, signature: str) -> bool:
        """
        Check if a method reaches MOP (Method of Protection).
        
        Args:
            signature: Method signature to check
            
        Returns:
            True if method reaches MOP, False otherwise
        """
        if self.static_info and self.static_info.classes:
            method = self.static_info.classes.methods.get(signature)
            if method:
                return method.reaches_mop
        return False
    
    def _check_method_directly_reaches_mop(self, signature: str) -> bool:
        """
        Check if a method directly reaches MOP.
        
        Args:
            signature: Method signature to check
            
        Returns:
            True if method directly reaches MOP, False otherwise
        """
        if self.static_info and self.static_info.classes:
            method = self.static_info.classes.methods.get(signature)
            if method:
                return method.directly_reaches_mop
        return False

    def get_screen_description(self) -> ScreenDescription:
        """
        Create and return a complete screen description.
        
        Returns:
            ScreenDescription object containing all parsed items
        """
        self.logging.info(f"Generated screen description with {len(self.items)} items")
        self.logging.info(f"Window info: {self.window_info}")
        return ScreenDescription(self.activity, self.items)


def create_tree_from_json(json_data: dict) -> Node:
    """
    Create a Node tree from JSON representation of an Android UI hierarchy.
    
    Args:
        json_data: JSON dictionary containing UI hierarchy data
        
    Returns:
        Root Node of the UI hierarchy tree
    """
    logger = logging_api.getLogger(__name__)
    logger.debug("Creating UI tree from JSON data")
    
    def create_node(data):
        """Recursive function to create nodes from JSON data"""
        if not isinstance(data, dict):
            logger.warning(f"Invalid node data format: {data}")
            return None
            
        children = []
        if "children" in data and isinstance(data["children"], list):
            for child_data in data["children"]:
                child_node = create_node(child_data)
                if child_node:
                    children.append(child_node)
                    
        return Node(data, children)
        
    return create_node(json_data)


# Enhancements for rvandroid/parser/droidbot/droidbot_state_parser_novo.py

def parse(screen_info: dict, static_data: StaticAnalysisData) -> ScreenDescription:
    """
    Parse screen information to create a structured description.
    
    Args:
        screen_info: Dictionary containing screen information
        static_data: Static analysis data for the application
        
    Returns:
        ScreenDescription object containing parsed UI elements
    """
    logger = logging_api.getLogger(__name__)
    logger.info(f"Parsing screen info for activity: {screen_info.get('activity', 'unknown')}")

    # Clean up activity and stack names
    activity = screen_info.get("activity", "").replace("/", "")
    stack = screen_info.get("stack", [])
    new_stack = [name.replace("/", "") for name in stack]
    
    # Update screen_info with cleaned values
    screen_info["stack"] = new_stack
    screen_info["activity"] = activity

    # Create UI hierarchy tree
    if "view_tree" not in screen_info:
        logger.error("No view_tree found in screen_info")
        return ScreenDescription(activity, [])
        
    tree = create_tree_from_json(screen_info["view_tree"])
    if not tree:
        logger.error("Failed to create UI tree from view_tree data")
        return ScreenDescription(activity, [])

    # Create visitor and traverse tree
    visitor = TextVisitor(static_data, activity)
    tree.accept(visitor)
    
    # Get and return screen description
    description = visitor.get_screen_description()
    logger.info(f"Parsed {len(description.items)} UI elements from screen")
    
    # Enhance description with activity metrics
    if static_data and static_data.classes:
        clazz = static_data.classes.get_clazz(activity)
        if clazz:
            total_reachable = sum(1 for m in clazz.methods if m.reachable)
            total_mop = sum(1 for m in clazz.methods if m.reaches_mop)
            # Add metrics to description if needed
            
    return description


# def execute(view: dict, static_data: StaticAnalysisData) -> ScreenDescription:
#     """
#     Execute parsing on a view dictionary.
    
#     Args:
#         view: View dictionary to parse
#         static_data: Static analysis data
        
#     Returns:
#         ScreenDescription object
#     """
#     logger = logging_api.getLogger(__name__)
#     logger.debug("Executing parse on view data")
    
#     activity = view.get("activity", "").replace("/", "")
#     return parse(view, static_data)


# def www(screen_info: dict, classes: Classes, windows: Windows, wtg: WindowTransitionGraph) -> ScreenDescription:
#     # Criando a árvore a partir do JSON
#     tree = create_tree_from_json(screen_info)

#     # Criando um visitante
#     visitor = TextVisitor()

#     # Percorrendo a árvore
#     tree.accept(visitor)

#     return visitor.get_screen_description()


# TODO refazer esse método
# def is_same_package(view: dict):
#     app_package = "br.unb.cic.cryptoapp"
#     return app_package == __safe_dict_get(view, "package")

def is_view_enabled(view_dict: dict) -> bool:
    # exclude navigation bar if exists
    if __safe_dict_get(view_dict, "visible") and \
            __safe_dict_get(view_dict, "resource_id") not in \
            ["android:id/navigationBarBackground",
             "android:id/statusBarBackground"]:
        return True
    return False


def __safe_dict_get(view_dict, key, default=None):
    return view_dict[key] if (key in view_dict) else default
