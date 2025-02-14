from collections import namedtuple
from droidbot.input_event import *

"""
This module contains the implementation of a visitor pattern to parse Android UI elements and their associated actions.

The `Visitor` class is responsible for visiting each node in the UI hierarchy, collecting information about clickable,
scrollable, checkable, long-clickable, editable, and actionable views. It generates descriptions of these views
and their corresponding actions, which are stored in a `ScreenDescription` object.

The `Node` class represents an individual view in the UI hierarchy and provides methods to accept a visitor for traversal.
It also includes helper methods to safely retrieve dictionary values with default fallbacks.
"""


class ItemAction:
    def __init__(self, id: int, text: str, event: InputEvent):
        self.id = id
        self.text = text
        self.event = event

class ScreenItem:
    def __init__(self, view: dict, base_description: str, actions: list[ItemAction]):
        self.view = view
        self.base_description = base_description
        self.actions = actions

    @property
    def description(self):
        actions_desc = f". Actions: {', '.join([a.text for a in self.actions])}" if self.actions else "."
        return f"{self.base_description}{actions_desc}"

    def __str__(self):
        return self.description
        
class ScreenDescription:
    def __init__(self, activity: str, items: list[ScreenItem]):
        self.activity = activity
        self.items = items
        self.events_by_id = {action.id: action.event for item in items for action in item.actions}

    @property
    def description(self):
        view_descs = [f" - {item.description}" for item in self.items]
        state_desc = (f"The current screen has the following UI views and corresponding actions, "
                       f"with action id in parentheses:\n ")
        return state_desc + "\n ".join(view_descs)

    def __str__(self):
        return self.description
    
class Counter:
    def __init__(self):
        self.value: int = 0
        
    def inc(self) -> int:
        self.value += 1
        return self.value   
    
class Visitor:
    def __init__(self):
        self.counter = Counter()
        self.items: list[ScreenItem] = []
    
    @staticmethod
    def get_possible_actions(node, counter: Counter):
        actions = []
        
        if node.clickable:
            cont = counter.inc()
            text = "click ({})".format(cont)
            actions.append(ItemAction(cont, text, TouchEvent(view=node.data)))        
        if node.long_clickable:
            cont = counter.inc()
            text = "long click ({})".format(cont)
            actions.append(ItemAction(cont, text, LongTouchEvent(view=node.data)))   
        if node.checkable:
            cont = counter.inc()
            text = "check ({})".format(cont)
            actions.append(ItemAction(cont, text, TouchEvent(view=node.data)))
        if node.checked:
            cont = counter.inc()
            text = "uncheck ({})".format(cont)
            actions.append(ItemAction(cont, text, TouchEvent(view=node.data)))  
        if node.scrollable:
            cont = counter.inc()
            actions.append(ItemAction(cont, f"scroll UP ({cont})", ScrollEvent(view=node.data, direction="UP")))  
            cont = counter.inc()
            actions.append(ItemAction(cont, f"scroll DOWN ({cont})", ScrollEvent(view=node.data, direction="DOWN"))) 
            cont = counter.inc()
            actions.append(ItemAction(cont, f"scroll LEFT ({cont})", ScrollEvent(view=node.data, direction="LEFT")))
            cont = counter.inc()
            actions.append(ItemAction(cont, f"scroll RIGHT ({cont})", ScrollEvent(view=node.data, direction="RIGHT")))
        if node.editable:
            cont = counter.inc()
            actions.append(ItemAction(cont, f"set text ({cont})", SetTextEvent(view=node.data, text="")))
            
        return actions
    
    def get_screen_description(self):
        return ScreenDescription("", self.items)
    
    def visit_node(self, node):
        pass

    def visit_leaf_node(self, leaf_node):
        pass
    
    def visit_button(self, node):
        pass
    
    def visit_edit_text(self, node):
        pass
    
    def visit_text_view(self, node):
        pass
    
    def visit_checkbox(self, node):
        pass
    
    def visit_checked_text(self, node):
        pass
    
    def visit_image_button(self, node):
        pass
    
    def visit_image(self, node):
        pass
    
    def visit_spinner(self, node):
        pass
    
    def visit_toggle_button(self, node):
        pass
    
    def visit_switch(self, node):
        pass
    
    def visit_radio_button(self, node):
        pass
    
    def visit_radio_group(self, node):
        pass

class Node:
    def __init__(self, view, children=None):
        self.data = view
        self.clickable = self.__safe_dict_get(view, "clickable", default=False)
        self.scrollable = self.__safe_dict_get(view, "scrollable", default=False)
        self.checkable = self.__safe_dict_get(view, "checkable", default=False)
        self.long_clickable = self.__safe_dict_get(view, "long_clickable", default=False)
        self.editable = self.__safe_dict_get(view, "editable", default=False)
        self.actionable = self.clickable or self.scrollable or self.checkable or self.long_clickable or self.editable
        self.checked = self.__safe_dict_get(view, "checked", default=False)
        self.selected = self.__safe_dict_get(view, "selected", default=False)
        self.content_description = self.__safe_dict_get(view, "content_description", default="")
        self.view_text = self.__safe_dict_get(view, "text", default="")
        self.view_class = self.__safe_dict_get(view, "class", default="")
        self.resource_id = self.__safe_dict_get(view, "resource_id", default="")
        self.children = children or []        

    def accept(self, visitor: Visitor):
        if len(self.children) == 0:
            match self.view_class:
                case "android.widget.Button": visitor.visit_button(self)
                case "android.widget.EditText": visitor.visit_edit_text(self)
                case "android.widget.TextView": visitor.visit_text_view(self)
                case "android.widget.CheckBox": visitor.visit_checkbox(self)
                case "android.widget.CheckedTextView": visitor.visit_checked_text(self)
                case "android.widget.ImageButton": visitor.visit_image_button(self)
                case "android.widget.ImageView": visitor.visit_image(self)
                case "android.widget.ToggleButton": visitor.visit_toggle_button(self)
                case "android.widget.Switch": visitor.visit_switch(self)
                case "android.widget.RadioButton": visitor.visit_radio_button(self) #TODO
                case _: visitor.visit_leaf_node(self)
        else:
            if "android.widget.Spinner" == self.view_class:
                visitor.visit_spinner(self)
            if "android.widget.RadioGroup" == self.view_class: #TODO
                visitor.visit_radio_group(self)
            else:
                visitor.visit_node(self)
                for child in self.children:
                    child.accept(visitor)
            
    def __safe_dict_get(self, view_dict, key, default=None):
        return view_dict[key] if (key in view_dict) else default       
    