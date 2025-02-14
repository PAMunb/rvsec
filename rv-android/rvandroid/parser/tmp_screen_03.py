import json
from droidbot.device_state import DeviceState
from droidbot.input_event import *

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
        
        if node.clickable or node.checkable:
            cont = counter.inc()
            text = "click ({})".format(cont)
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

class TextVisitor(Visitor):
        
    def visit_node(self, node):
        # print(f"\nNode: {node.data}")
        pass

    def visit_leaf_node(self, leaf_node):
        print(f"\n ***** Leaf Node: {leaf_node.data}")
        # Lógica para retornar texto específico para nós folha
        # return self.get_specific_text(leaf_node.data)
        
    def visit_button(self, node: Node):
        print(f"\n ***** BUTTON: {node.data}")
        actions = self.get_possible_actions(node, self.counter)             
        text = "Button {}{}{}".format(self.__with_text(node), self.__with_description(node), self.__with_resource_id(node))
        item = ScreenItem(node.data, text, actions)
        print(item)
        self.items.append(item)
            
    def visit_edit_text(self, node):
        print(f"\n ***** EDIT_TEXT: {node.data}")
        actions = Visitor.get_possible_actions(node, self.counter)
        text = "Editable text view {}{}{}".format(self.__with_text(node), self.__with_description(node), self.__with_resource_id(node))
        item = ScreenItem(node.data, text, actions)
        print(item)
        self.items.append(item)
    
    def visit_text_view(self, node):
        print(f"\n ***** TEXT_VIEW: {node.data}")
        actions = Visitor.get_possible_actions(node, self.counter)
        text = "Text view {}{}{}".format(self.__with_text(node), self.__with_description(node), self.__with_resource_id(node))
        item = ScreenItem(node.data, text, actions)
        print(item)
        self.items.append(item)
        
    def visit_checkbox(self, node):
        print(f"\n ***** CHECKBOX: {node.data}")
    
    def visit_checked_text(self, node):
        print(f"\n ***** CHECKED_TEXT_VIEW: {node.data}")
    
    def visit_image_button(self, node):
        print(f"\n ***** IMAGE_BUTTON: {node.data}")
        actions = self.get_possible_actions(node, self.counter)             
        text = "Image button {}{}{}".format(self.__with_text(node), self.__with_description(node), self.__with_resource_id(node))
        item = ScreenItem(node.data, text, actions)
        print(item)
        self.items.append(item)
    
    def visit_image(self, node):
        print(f"\n ***** IMAGE: {node.data}")
        actions = self.get_possible_actions(node, self.counter)             
        text = "Image {}{}{}".format(self.__with_text(node), self.__with_description(node), self.__with_resource_id(node))
        item = ScreenItem(node.data, text, actions)
        print(item)
        self.items.append(item)
        
    def visit_toggle_button(self, node):
        print(f"\n ***** TOGGLE_BUTTON: {node.data}")
    
    def visit_switch(self, node):
        print(f"\n ***** SWITCH: {node.data}")
        
    def visit_radio_button(self, node):
        print(f"\n ***** RADIO_BUTTON: {node.data}")
        
    def visit_spinner(self, node):
        print(f"\n ***** SPINNER: {node.data}")
        
    def visit_radio_group(self, node):
        print(f"\n ***** RADIO_GROUP: {node.data}")

    def __with_text(self, node: Node):
        return f"with text '{node.view_text}'" if node.view_text else "with no text"
    
    def __with_description(self, node: Node):
        return f" with description '{node.content_description}'" if node.content_description else ""   
    
    def __with_resource_id(self, node: Node):
        result = ""
        if node.resource_id:
            name = node.resource_id
            idx = name.find("/")            
            result = f" with id={name[idx + 1:]}"
        return result
        

def create_tree_from_json(json_data: dict):    
    def create_node(data):
        children = []
        if isinstance(data, dict) and "children" in data:
            for child_data in data["children"]:
                children.append(create_node(child_data))
        return Node(data, children)
    return create_node(json_data)

def execute(view: dict):    
    # xxx(view)
    www(view)


def www(view: dict):
    # Criando a árvore a partir do JSON
    tree = create_tree_from_json(view)

    # Criando um visitante
    visitor = TextVisitor()

    # Percorrendo a árvore
    tree.accept(visitor)
    
    print(visitor.get_screen_description())

def xxx(view: dict):    
    if is_view_enabled(view) and is_same_package(view):
        child_count = __safe_dict_get(view, "child_count")
        if child_count > 0:
            for child in view["children"]:
                xxx(child)
        #else:
        print(f"\nview={view}")
        
        clickable = _get_self_ancestors_property(view, "clickable")
        scrollable = __safe_dict_get(view, "scrollable")
        checkable = _get_self_ancestors_property(view, "checkable")
        long_clickable = _get_self_ancestors_property(view, "long_clickable")
        editable = __safe_dict_get(view, "editable")
        actionable = clickable or scrollable or checkable or long_clickable or editable
        checked = __safe_dict_get(view, "checked")
        selected = __safe_dict_get(view, "selected")
        content_description = __safe_dict_get(view, "content_description", default="")
        view_text = __safe_dict_get(view, "text", default="")
        
        item_type = view["class"]
        match item_type:
            case "android.widget.TextView": pass
            case _: pass


def is_same_package(view: dict):
    app_package = "br.unb.cic.cryptoapp"
    return app_package == __safe_dict_get(view, "package")

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

TELA_INICIAL = {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 3, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 1, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 1, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 2, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 1, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 2, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[42, 101], [316, 172]], "resource_id": None, "checked": False, "text": "Crypto App", "class": "android.widget.TextView", "scrollable": False, "selected": False, "long_clickable": False, "parent": 5, "temp_id": 6, "size": "274*71"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 1, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": False, "clickable": True, "is_password": False, "focusable": True, "enabled": True, "content_description": "More options", "children": [], "focused": False, "bounds": [[975, 73], [1080, 199]], "resource_id": None, "checked": False, "text": None, "class": "android.widget.ImageView", "scrollable": False, "selected": False, "long_clickable": True, "parent": 7, "temp_id": 8, "size": "105*126"}], "focused": False, "bounds": [[975, 63], [1080, 210]], "resource_id": None, "checked": False, "text": None, "class": "androidx.appcompat.widget.LinearLayoutCompat", "scrollable": False, "selected": False, "long_clickable": False, "parent": 5, "temp_id": 7, "size": "105*147"}], "focused": False, "bounds": [[0, 63], [1080, 210]], "resource_id": "br.unb.cic.cryptoapp:id/action_bar", "checked": False, "text": None, "class": "android.view.ViewGroup", "scrollable": False, "selected": False, "long_clickable": False, "parent": 4, "temp_id": 5, "size": "1080*147"}], "focused": False, "bounds": [[0, 63], [1080, 210]], "resource_id": "br.unb.cic.cryptoapp:id/action_bar_container", "checked": False, "text": None, "class": "android.widget.FrameLayout", "scrollable": False, "selected": False, "long_clickable": False, "parent": 3, "temp_id": 4, "size": "1080*147"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 1, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 2, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": False, "clickable": True, "is_password": False, "focusable": True, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 210], [1080, 336]], "resource_id": "br.unb.cic.cryptoapp:id/buttonMessageDigest", "checked": False, "text": "MESSAGE DIGEST", "class": "android.widget.Button", "scrollable": False, "selected": False, "long_clickable": False, "parent": 10, "temp_id": 11, "size": "1080*126"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": False, "clickable": True, "is_password": False, "focusable": True, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 336], [1080, 462]], "resource_id": "br.unb.cic.cryptoapp:id/buttonCipher", "checked": False, "text": "CIPHER", "class": "android.widget.Button", "scrollable": False, "selected": False, "long_clickable": False, "parent": 10, "temp_id": 12, "size": "1080*126"}], "focused": False, "bounds": [[0, 210], [1080, 1794]], "resource_id": None, "checked": False, "text": None, "class": "android.widget.LinearLayout", "scrollable": False, "selected": False, "long_clickable": False, "parent": 9, "temp_id": 10, "size": "1080*1584"}], "focused": False, "bounds": [[0, 210], [1080, 1794]], "resource_id": "android:id/content", "checked": False, "text": None, "class": "android.widget.FrameLayout", "scrollable": False, "selected": False, "long_clickable": False, "parent": 3, "temp_id": 9, "size": "1080*1584"}], "focused": False, "bounds": [[0, 63], [1080, 1794]], "resource_id": "br.unb.cic.cryptoapp:id/decor_content_parent", "checked": False, "text": None, "class": "android.view.ViewGroup", "scrollable": False, "selected": False, "long_clickable": False, "parent": 2, "temp_id": 3, "size": "1080*1731"}], "focused": False, "bounds": [[0, 63], [1080, 1794]], "resource_id": None, "checked": False, "text": None, "class": "android.widget.FrameLayout", "scrollable": False, "selected": False, "long_clickable": False, "parent": 1, "temp_id": 2, "size": "1080*1731"}], "focused": False, "bounds": [[0, 0], [1080, 1794]], "resource_id": None, "checked": False, "text": None, "class": "android.widget.LinearLayout", "scrollable": False, "selected": False, "long_clickable": False, "parent": 0, "temp_id": 1, "size": "1080*1794"}, {"package": "br.unb.cic.cryptoapp", "visible": False, "checkable": False, "child_count": 0, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 0], [1080, 63]], "resource_id": "android:id/statusBarBackground", "checked": False, "text": None, "class": "android.view.View", "scrollable": False, "selected": False, "long_clickable": False, "parent": 0, "temp_id": 13, "size": "1080*63"}, {"package": "br.unb.cic.cryptoapp", "visible": False, "checkable": False, "child_count": 0, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 1794], [1080, 1920]], "resource_id": "android:id/navigationBarBackground", "checked": False, "text": None, "class": "android.view.View", "scrollable": False, "selected": False, "long_clickable": False, "parent": 0, "temp_id": 14, "size": "1080*126"}], "focused": False, "bounds": [[0, 0], [1080, 1920]], "resource_id": None, "checked": False, "text": None, "class": "android.widget.FrameLayout", "scrollable": False, "selected": False, "long_clickable": False, "parent": -1, "temp_id": 0, "size": "1080*1920"}
TELA_MESSAGE_DIGEST = {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 3, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 1, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 1, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 2, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 1, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 2, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[42, 101], [316, 172]], "resource_id": None, "checked": False, "text": "Crypto App", "class": "android.widget.TextView", "scrollable": False, "selected": False, "long_clickable": False, "parent": 5, "temp_id": 6, "size": "274*71"}, {"package": "br.unb.cic.cryptoapp", "visible": False, "checkable": False, "child_count": 0, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[1080, 63], [1080, 210]], "resource_id": None, "checked": False, "text": None, "class": "androidx.appcompat.widget.LinearLayoutCompat", "scrollable": False, "selected": False, "long_clickable": False, "parent": 5, "temp_id": 7, "size": "0*147"}], "focused": False, "bounds": [[0, 63], [1080, 210]], "resource_id": "br.unb.cic.cryptoapp:id/action_bar", "checked": False, "text": None, "class": "android.view.ViewGroup", "scrollable": False, "selected": False, "long_clickable": False, "parent": 4, "temp_id": 5, "size": "1080*147"}], "focused": False, "bounds": [[0, 63], [1080, 210]], "resource_id": "br.unb.cic.cryptoapp:id/action_bar_container", "checked": False, "text": None, "class": "android.widget.FrameLayout", "scrollable": False, "selected": False, "long_clickable": False, "parent": 3, "temp_id": 4, "size": "1080*147"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 1, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 5, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 210], [1080, 261]], "resource_id": "br.unb.cic.cryptoapp:id/textView", "checked": False, "text": "Message Digest", "class": "android.widget.TextView", "scrollable": False, "selected": False, "long_clickable": False, "parent": 9, "temp_id": 10, "size": "1080*51"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 1, "editable": False, "clickable": True, "is_password": False, "focusable": True, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 264], [954, 321]], "resource_id": "android:id/text1", "checked": False, "text": "Select", "class": "android.widget.TextView", "scrollable": False, "selected": False, "long_clickable": False, "parent": 11, "temp_id": 12, "size": "954*57"}], "focused": False, "bounds": [[0, 261], [1080, 324]], "resource_id": "br.unb.cic.cryptoapp:id/spinnerMessageDigest", "checked": False, "text": None, "class": "android.widget.Spinner", "scrollable": True, "selected": False, "long_clickable": True, "parent": 9, "temp_id": 11, "size": "1080*63"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": True, "clickable": True, "is_password": False, "focusable": True, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 324], [1080, 442]], "resource_id": "br.unb.cic.cryptoapp:id/editTextMessageDigest", "checked": False, "text": "Input text ...", "class": "android.widget.EditText", "scrollable": False, "selected": False, "long_clickable": True, "parent": 9, "temp_id": 13, "size": "1080*118"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": False, "clickable": True, "is_password": False, "focusable": True, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 442], [1080, 568]], "resource_id": "br.unb.cic.cryptoapp:id/buttonGenerateHash", "checked": False, "text": "GENERATE HASH", "class": "android.widget.Button", "scrollable": False, "selected": False, "long_clickable": False, "parent": 9, "temp_id": 14, "size": "1080*126"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 1, "editable": False, "clickable": False, "is_password": False, "focusable": True, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 1, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 568], [1080, 619]], "resource_id": "br.unb.cic.cryptoapp:id/textViewMessageDigestResult", "checked": False, "text": None, "class": "android.widget.TextView", "scrollable": False, "selected": False, "long_clickable": False, "parent": 16, "temp_id": 17, "size": "1080*51"}], "focused": False, "bounds": [[0, 568], [1080, 619]], "resource_id": None, "checked": False, "text": None, "class": "android.widget.LinearLayout", "scrollable": False, "selected": False, "long_clickable": False, "parent": 15, "temp_id": 16, "size": "1080*51"}], "focused": False, "bounds": [[0, 568], [1080, 1794]], "resource_id": None, "checked": False, "text": None, "class": "android.widget.ScrollView", "scrollable": False, "selected": False, "long_clickable": False, "parent": 9, "temp_id": 15, "size": "1080*1226"}], "focused": False, "bounds": [[0, 210], [1080, 1794]], "resource_id": None, "checked": False, "text": None, "class": "android.widget.LinearLayout", "scrollable": False, "selected": False, "long_clickable": False, "parent": 8, "temp_id": 9, "size": "1080*1584"}], "focused": False, "bounds": [[0, 210], [1080, 1794]], "resource_id": "android:id/content", "checked": False, "text": None, "class": "android.widget.FrameLayout", "scrollable": False, "selected": False, "long_clickable": False, "parent": 3, "temp_id": 8, "size": "1080*1584"}], "focused": False, "bounds": [[0, 63], [1080, 1794]], "resource_id": "br.unb.cic.cryptoapp:id/decor_content_parent", "checked": False, "text": None, "class": "android.view.ViewGroup", "scrollable": False, "selected": False, "long_clickable": False, "parent": 2, "temp_id": 3, "size": "1080*1731"}], "focused": False, "bounds": [[0, 63], [1080, 1794]], "resource_id": None, "checked": False, "text": None, "class": "android.widget.FrameLayout", "scrollable": False, "selected": False, "long_clickable": False, "parent": 1, "temp_id": 2, "size": "1080*1731"}], "focused": False, "bounds": [[0, 0], [1080, 1794]], "resource_id": None, "checked": False, "text": None, "class": "android.widget.LinearLayout", "scrollable": False, "selected": False, "long_clickable": False, "ptarent": 0, "temp_id": 1, "size": "1080*1794"}, {"package": "br.unb.cic.cryptoapp", "visible": False, "checkable": False, "child_count": 0, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 0], [1080, 63]], "resource_id": "android:id/statusBarBackground", "checked": False, "text": None, "class": "android.view.View", "scrollable": False, "selected": False, "long_clickable": False, "parent": 0, "temp_id": 18, "size": "1080*63"}, {"package": "br.unb.cic.cryptoapp", "visible": False, "checkable": False, "child_count": 0, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 1794], [1080, 1920]], "resource_id": "android:id/navigationBarBackground", "checked": False, "text": None, "class": "android.view.View", "scrollable": False, "selected": False, "long_clickable": False, "parent": 0, "temp_id": 19, "size": "1080*126"}], "focused": False, "bounds": [[0, 0], [1080, 1920]], "resource_id": None, "checked": False, "text": None, "class": "android.widget.FrameLayout", "scrollable": False, "selected": False, "long_clickable": False, "parent": -1, "temp_id": 0, "size": "1080*1920"}
TELA_CIPHER = {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 3, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 1, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 1, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 2, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 1, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 2, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[42, 101], [316, 172]], "resource_id": None, "checked": False, "text": "Crypto App", "class": "android.widget.TextView", "scrollable": False, "selected": False, "long_clickable": False, "parent": 5, "temp_id": 6, "size": "274*71", "signature": "[class]android.widget.TextView[resource_id]None[text]Crypto App[enabled,,]", "view_str": "83abc6f3ec93bf7ecef569dec70269ac", "content_free_signature": "[class]android.widget.TextView[resource_id]None"}, {"package": "br.unb.cic.cryptoapp", "visible": False, "checkable": False, "child_count": 0, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[1080, 63], [1080, 210]], "resource_id": None, "checked": False, "text": None, "class": "androidx.appcompat.widget.LinearLayoutCompat", "scrollable": False, "selected": False, "long_clickable": False, "parent": 5, "temp_id": 7, "size": "0*147", "signature": "[class]androidx.appcompat.widget.LinearLayoutCompat[resource_id]None[text]None[enabled,,]", "view_str": "4dcfaab2414f46250a4d2d72aa9500f8", "content_free_signature": "[class]androidx.appcompat.widget.LinearLayoutCompat[resource_id]None"}], "focused": False, "bounds": [[0, 63], [1080, 210]], "resource_id": "br.unb.cic.cryptoapp:id/action_bar", "checked": False, "text": None, "class": "android.view.ViewGroup", "scrollable": False, "selected": False, "long_clickable": False, "parent": 4, "temp_id": 5, "size": "1080*147", "signature": "[class]android.view.ViewGroup[resource_id]br.unb.cic.cryptoapp:id/action_bar[text]None[enabled,,]", "view_str": "aa204a7957aa3644bfddf43f055b91b7", "content_free_signature": "[class]android.view.ViewGroup[resource_id]br.unb.cic.cryptoapp:id/action_bar"}], "focused": False, "bounds": [[0, 63], [1080, 210]], "resource_id": "br.unb.cic.cryptoapp:id/action_bar_container", "checked": False, "text": None, "class": "android.widget.FrameLayout", "scrollable": False, "selected": False, "long_clickable": False, "parent": 3, "temp_id": 4, "size": "1080*147", "signature": "[class]android.widget.FrameLayout[resource_id]br.unb.cic.cryptoapp:id/action_bar_container[text]None[enabled,,]", "view_str": "1f767acb23a636bce913fc5e9bfb3813", "content_free_signature": "[class]android.widget.FrameLayout[resource_id]br.unb.cic.cryptoapp:id/action_bar_container"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 1, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 18, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": "Descricao do conteudo: cipherTextView", "children": [], "focused": False, "bounds": [[0, 210], [1080, 261]], "resource_id": "br.unb.cic.cryptoapp:id/cipherTextView", "checked": False, "text": "Cipher", "class": "android.widget.TextView", "scrollable": False, "selected": False, "long_clickable": False, "parent": 9, "temp_id": 10, "size": "1080*51", "signature": "[class]android.widget.TextView[resource_id]br.unb.cic.cryptoapp:id/cipherTextView[text]Cipher[enabled,,]", "view_str": "035d2e2d5b30094853f3abc66e2ce728", "content_free_signature": "[class]android.widget.TextView[resource_id]br.unb.cic.cryptoapp:id/cipherTextView"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": True, "clickable": True, "is_password": False, "focusable": True, "enabled": True, "content_description": "Descricao do conteudo: editTextCipherEncrypt", "children": [], "focused": False, "bounds": [[0, 261], [1080, 379]], "resource_id": "br.unb.cic.cryptoapp:id/editTextCipherEncrypt", "checked": False, "text": "Input text ...", "class": "android.widget.EditText", "scrollable": False, "selected": False, "long_clickable": True, "parent": 9, "temp_id": 11, "size": "1080*118", "signature": "[class]android.widget.EditText[resource_id]br.unb.cic.cryptoapp:id/editTextCipherEncrypt[text]Input text ...[enabled,,]", "view_str": "85a319f1fee133873bb621d6ce792f77", "content_free_signature": "[class]android.widget.EditText[resource_id]br.unb.cic.cryptoapp:id/editTextCipherEncrypt"}, {"package": "br.unb.cic.cryptoapp", "visible": False, "checkable": False, "child_count": 0, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": "Descricao do conteudo: textViewCypherEncryptResult", "children": [], "focused": False, "bounds": [[0, 379], [0, 430]], "resource_id": "br.unb.cic.cryptoapp:id/textViewCypherEncryptResult", "checked": False, "text": None, "class": "android.widget.TextView", "scrollable": False, "selected": False, "long_clickable": False, "parent": 9, "temp_id": 12, "size": "0*51", "signature": "[class]android.widget.TextView[resource_id]br.unb.cic.cryptoapp:id/textViewCypherEncryptResult[text]None[enabled,,]", "view_str": "9eda5ff764b814832884dadc09dc0bce", "content_free_signature": "[class]android.widget.TextView[resource_id]br.unb.cic.cryptoapp:id/textViewCypherEncryptResult"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": False, "clickable": True, "is_password": False, "focusable": True, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 430], [1080, 556]], "resource_id": "br.unb.cic.cryptoapp:id/btn_cipher_encrypt", "checked": False, "text": "ENCRYPT", "class": "android.widget.Button", "scrollable": False, "selected": False, "long_clickable": False, "parent": 9, "temp_id": 13, "size": "1080*126", "signature": "[class]android.widget.Button[resource_id]br.unb.cic.cryptoapp:id/btn_cipher_encrypt[text]ENCRYPT[enabled,,]", "view_str": "5555a277adc071642fbd8fe252c2081c", "content_free_signature": "[class]android.widget.Button[resource_id]br.unb.cic.cryptoapp:id/btn_cipher_encrypt"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": True, "clickable": True, "is_password": False, "focusable": True, "enabled": True, "content_description": "Descricao do conteudo: editTextPhone", "children": [], "focused": False, "bounds": [[0, 556], [1080, 674]], "resource_id": "br.unb.cic.cryptoapp:id/editTextPhone", "checked": False, "text": "Hint: editTextPhone", "class": "android.widget.EditText", "scrollable": False, "selected": False, "long_clickable": True, "parent": 9, "temp_id": 14, "size": "1080*118", "signature": "[class]android.widget.EditText[resource_id]br.unb.cic.cryptoapp:id/editTextPhone[text]Hint: editTextPhone[enabled,,]", "view_str": "6144142853994e22e77c90d4b00537f3", "content_free_signature": "[class]android.widget.EditText[resource_id]br.unb.cic.cryptoapp:id/editTextPhone"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": True, "clickable": True, "is_password": False, "focusable": True, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 674], [1080, 792]], "resource_id": "br.unb.cic.cryptoapp:id/editTextTextEmailAddress", "checked": False, "text": None, "class": "android.widget.EditText", "scrollable": False, "selected": False, "long_clickable": True, "parent": 9, "temp_id": 15, "size": "1080*118", "signature": "[class]android.widget.EditText[resource_id]br.unb.cic.cryptoapp:id/editTextTextEmailAddress[text]None[enabled,,]", "view_str": "9c49530a1d59dce161f99614b0517f80", "content_free_signature": "[class]android.widget.EditText[resource_id]br.unb.cic.cryptoapp:id/editTextTextEmailAddress"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": True, "clickable": True, "is_password": False, "focusable": True, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 792], [1080, 910]], "resource_id": "br.unb.cic.cryptoapp:id/editTextDate", "checked": False, "text": None, "class": "android.widget.EditText", "scrollable": False, "selected": False, "long_clickable": True, "parent": 9, "temp_id": 16, "size": "1080*118", "signature": "[class]android.widget.EditText[resource_id]br.unb.cic.cryptoapp:id/editTextDate[text]None[enabled,,]", "view_str": "c02fffac834a5ab6e1497fba88788ede", "content_free_signature": "[class]android.widget.EditText[resource_id]br.unb.cic.cryptoapp:id/editTextDate"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": True, "clickable": True, "is_password": False, "focusable": True, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 910], [1080, 1028]], "resource_id": "br.unb.cic.cryptoapp:id/editTextDate2", "checked": False, "text": None, "class": "android.widget.EditText", "scrollable": False, "selected": False, "long_clickable": True, "parent": 9, "temp_id": 17, "size": "1080*118", "signature": "[class]android.widget.EditText[resource_id]br.unb.cic.cryptoapp:id/editTextDate2[text]None[enabled,,]", "view_str": "2b8729b9f3df5f7588b4f72eab5da726", "content_free_signature": "[class]android.widget.EditText[resource_id]br.unb.cic.cryptoapp:id/editTextDate2"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": True, "clickable": True, "is_password": False, "focusable": True, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 1028], [1080, 1146]], "resource_id": "br.unb.cic.cryptoapp:id/editTextNumber", "checked": False, "text": None, "class": "android.widget.EditText", "scrollable": False, "selected": False, "long_clickable": True, "parent": 9, "temp_id": 18, "size": "1080*118", "signature": "[class]android.widget.EditText[resource_id]br.unb.cic.cryptoapp:id/editTextNumber[text]None[enabled,,]", "view_str": "723409b49f8f7d06586e696f928806f1", "content_free_signature": "[class]android.widget.EditText[resource_id]br.unb.cic.cryptoapp:id/editTextNumber"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": True, "child_count": 0, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 1146], [1080, 1197]], "resource_id": "br.unb.cic.cryptoapp:id/checkedTextView", "checked": False, "text": "CheckedTextView", "class": "android.widget.CheckedTextView", "scrollable": False, "selected": False, "long_clickable": False, "parent": 9, "temp_id": 19, "size": "1080*51", "signature": "[class]android.widget.CheckedTextView[resource_id]br.unb.cic.cryptoapp:id/checkedTextView[text]CheckedTextView[enabled,,]", "view_str": "c0a7c5300b69da70864916f2cdb5a58f", "content_free_signature": "[class]android.widget.CheckedTextView[resource_id]br.unb.cic.cryptoapp:id/checkedTextView"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": False, "clickable": True, "is_password": False, "focusable": True, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 1197], [147, 1344]], "resource_id": "br.unb.cic.cryptoapp:id/floatingActionButton", "checked": False, "text": None, "class": "android.widget.ImageButton", "scrollable": False, "selected": False, "long_clickable": False, "parent": 9, "temp_id": 20, "size": "147*147", "signature": "[class]android.widget.ImageButton[resource_id]br.unb.cic.cryptoapp:id/floatingActionButton[text]None[enabled,,]", "view_str": "0c9abe022f5b6bf9f6fb947de12a80e8", "content_free_signature": "[class]android.widget.ImageButton[resource_id]br.unb.cic.cryptoapp:id/floatingActionButton"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": False, "clickable": True, "is_password": False, "focusable": True, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 1344], [1080, 1394]], "resource_id": "br.unb.cic.cryptoapp:id/imageButton", "checked": False, "text": None, "class": "android.widget.ImageButton", "scrollable": False, "selected": False, "long_clickable": False, "parent": 9, "temp_id": 21, "size": "1080*50", "signature": "[class]android.widget.ImageButton[resource_id]br.unb.cic.cryptoapp:id/imageButton[text]None[enabled,,]", "view_str": "22622f6e54d17e04e4ce93ac87e44cff", "content_free_signature": "[class]android.widget.ImageButton[resource_id]br.unb.cic.cryptoapp:id/imageButton"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": True, "child_count": 0, "editable": False, "clickable": True, "is_password": False, "focusable": True, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 1394], [1080, 1520]], "resource_id": "br.unb.cic.cryptoapp:id/checkBox", "checked": False, "text": "CheckBox", "class": "android.widget.CheckBox", "scrollable": False, "selected": False, "long_clickable": False, "parent": 9, "temp_id": 22, "size": "1080*126", "signature": "[class]android.widget.CheckBox[resource_id]br.unb.cic.cryptoapp:id/checkBox[text]CheckBox[enabled,,]", "view_str": "ab7cb80fe923697115cc545bdeb3735e", "content_free_signature": "[class]android.widget.CheckBox[resource_id]br.unb.cic.cryptoapp:id/checkBox"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": False, "clickable": True, "is_password": False, "focusable": True, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 1520], [1080, 1646]], "resource_id": "br.unb.cic.cryptoapp:id/chip4", "checked": False, "text": None, "class": "android.widget.Button", "scrollable": False, "selected": False, "long_clickable": False, "parent": 9, "temp_id": 23, "size": "1080*126", "signature": "[class]android.widget.Button[resource_id]br.unb.cic.cryptoapp:id/chip4[text]None[enabled,,]", "view_str": "7ec558ee4026b2a737f121da049d7925", "content_free_signature": "[class]android.widget.Button[resource_id]br.unb.cic.cryptoapp:id/chip4"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": True, "child_count": 0, "editable": False, "clickable": True, "is_password": False, "focusable": True, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 1646], [1080, 1772]], "resource_id": "br.unb.cic.cryptoapp:id/toggleButton", "checked": False, "text": "OFF", "class": "android.widget.ToggleButton", "scrollable": False, "selected": False, "long_clickable": False, "parent": 9, "temp_id": 24, "size": "1080*126", "signature": "[class]android.widget.ToggleButton[resource_id]br.unb.cic.cryptoapp:id/toggleButton[text]OFF[enabled,,]", "view_str": "5005a34059030dc55314d16182df3b41", "content_free_signature": "[class]android.widget.ToggleButton[resource_id]br.unb.cic.cryptoapp:id/toggleButton"}, {"package": "br.unb.cic.cryptoapp", "visible": True, "checkable": False, "child_count": 0, "editable": False, "clickable": True, "is_password": False, "focusable": True, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 1772], [1080, 1794]], "resource_id": "br.unb.cic.cryptoapp:id/chip5", "checked": False, "text": None, "class": "android.widget.Button", "scrollable": False, "selected": False, "long_clickable": False, "parent": 9, "temp_id": 25, "size": "1080*22", "signature": "[class]android.widget.Button[resource_id]br.unb.cic.cryptoapp:id/chip5[text]None[enabled,,]", "view_str": "81d7265e49d43013a2f003312bcb1c1d", "content_free_signature": "[class]android.widget.Button[resource_id]br.unb.cic.cryptoapp:id/chip5"}, {"package": "br.unb.cic.cryptoapp", "visible": False, "checkable": True, "child_count": 0, "editable": False, "clickable": True, "is_password": False, "focusable": True, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 1794], [1080, 1794]], "resource_id": "br.unb.cic.cryptoapp:id/switch1", "checked": False, "text": "Switch OFF", "class": "android.widget.Switch", "scrollable": False, "selected": False, "long_clickable": False, "parent": 9, "temp_id": 26, "size": "1080*0", "signature": "[class]android.widget.Switch[resource_id]br.unb.cic.cryptoapp:id/switch1[text]Switch OFF[enabled,,]", "view_str": "45e735048472aa41d6f8bed336cb5a28", "content_free_signature": "[class]android.widget.Switch[resource_id]br.unb.cic.cryptoapp:id/switch1"}, {"package": "br.unb.cic.cryptoapp", "visible": False, "checkable": False, "child_count": 1, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [{"package": "br.unb.cic.cryptoapp", "visible": False, "checkable": True, "child_count": 0, "editable": False, "clickable": True, "is_password": False, "focusable": True, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 1865], [1080, 1794]], "resource_id": "br.unb.cic.cryptoapp:id/radioButton", "checked": False, "text": "RadioButton", "class": "android.widget.RadioButton", "scrollable": False, "selected": False, "long_clickable": False, "parent": 27, "temp_id": 28, "size": "1080*-71", "signature": "[class]android.widget.RadioButton[resource_id]br.unb.cic.cryptoapp:id/radioButton[text]RadioButton[enabled,,]", "view_str": "2401c0a4fde1a17491a70bcb30665477", "content_free_signature": "[class]android.widget.RadioButton[resource_id]br.unb.cic.cryptoapp:id/radioButton"}], "focused": False, "bounds": [[0, 1865], [1080, 1794]], "resource_id": None, "checked": False, "text": None, "class": "android.widget.RadioGroup", "scrollable": False, "selected": False, "long_clickable": False, "parent": 9, "temp_id": 27, "size": "1080*-71", "signature": "[class]android.widget.RadioGroup[resource_id]None[text]None[enabled,,]", "view_str": "79f459539d92cddfc19cb80632b87193", "content_free_signature": "[class]android.widget.RadioGroup[resource_id]None"}], "focused": False, "bounds": [[0, 210], [1080, 1794]], "resource_id": None, "checked": False, "text": None, "class": "android.widget.LinearLayout", "scrollable": False, "selected": False, "long_clickable": False, "parent": 8, "temp_id": 9, "size": "1080*1584", "signature": "[class]android.widget.LinearLayout[resource_id]None[text]None[enabled,,]", "view_str": "a34cda874ff08a7dd4d67aab1f1d0c75", "content_free_signature": "[class]android.widget.LinearLayout[resource_id]None"}], "focused": False, "bounds": [[0, 210], [1080, 1794]], "resource_id": "android:id/content", "checked": False, "text": None, "class": "android.widget.FrameLayout", "scrollable": False, "selected": False, "long_clickable": False, "parent": 3, "temp_id": 8, "size": "1080*1584", "signature": "[class]android.widget.FrameLayout[resource_id]android:id/content[text]None[enabled,,]", "view_str": "59055f8b52b170cda6d83e1fcc4b44eb", "content_free_signature": "[class]android.widget.FrameLayout[resource_id]android:id/content"}], "focused": False, "bounds": [[0, 63], [1080, 1794]], "resource_id": "br.unb.cic.cryptoapp:id/decor_content_parent", "checked": False, "text": None, "class": "android.view.ViewGroup", "scrollable": False, "selected": False, "long_clickable": False, "parent": 2, "temp_id": 3, "size": "1080*1731", "signature": "[class]android.view.ViewGroup[resource_id]br.unb.cic.cryptoapp:id/decor_content_parent[text]None[enabled,,]", "view_str": "c4a2a20ec4942943824384f276bd39ef", "content_free_signature": "[class]android.view.ViewGroup[resource_id]br.unb.cic.cryptoapp:id/decor_content_parent"}], "focused": False, "bounds": [[0, 63], [1080, 1794]], "resource_id": None, "checked": False, "text": None, "class": "android.widget.FrameLayout", "scrollable": False, "selected": False, "long_clickable": False, "parent": 1, "temp_id": 2, "size": "1080*1731", "signature": "[class]android.widget.FrameLayout[resource_id]None[text]None[enabled,,]", "view_str": "d55677649715a359c5b6d9c4371aa95a", "content_free_signature": "[class]android.widget.FrameLayout[resource_id]None"}], "focused": False, "bounds": [[0, 0], [1080, 1794]], "resource_id": None, "checked": False, "text": None, "class": "android.widget.LinearLayout", "scrollable": False, "selected": False, "long_clickable": False, "parent": 0, "temp_id": 1, "size": "1080*1794", "signature": "[class]android.widget.LinearLayout[resource_id]None[text]None[enabled,,]", "view_str": "0a101039f3da2bde4823764034bdd4da", "content_free_signature": "[class]android.widget.LinearLayout[resource_id]None"}, {"package": "br.unb.cic.cryptoapp", "visible": False, "checkable": False, "child_count": 0, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 0], [1080, 63]], "resource_id": "android:id/statusBarBackground", "checked": False, "text": None, "class": "android.view.View", "scrollable": False, "selected": False, "long_clickable": False, "parent": 0, "temp_id": 29, "size": "1080*63", "signature": "[class]android.view.View[resource_id]android:id/statusBarBackground[text]None[enabled,,]", "view_str": "66a0c12e18ccf78c4aaccc487e37d29c", "content_free_signature": "[class]android.view.View[resource_id]android:id/statusBarBackground"}, {"package": "br.unb.cic.cryptoapp", "visible": False, "checkable": False, "child_count": 0, "editable": False, "clickable": False, "is_password": False, "focusable": False, "enabled": True, "content_description": None, "children": [], "focused": False, "bounds": [[0, 1794], [1080, 1920]], "resource_id": "android:id/navigationBarBackground", "checked": False, "text": None, "class": "android.view.View", "scrollable": False, "selected": False, "long_clickable": False, "parent": 0, "temp_id": 30, "size": "1080*126", "signature": "[class]android.view.View[resource_id]android:id/navigationBarBackground[text]None[enabled,,]", "view_str": "a811d8269917e82dccf5432e9316f7f3", "content_free_signature": "[class]android.view.View[resource_id]android:id/navigationBarBackground"}], "focused": False, "bounds": [[0, 0], [1080, 1920]], "resource_id": None, "checked": False, "text": None, "class": "android.widget.FrameLayout", "scrollable": False, "selected": False, "long_clickable": False, "parent": -1, "temp_id": 0, "size": "1080*1920", "signature": "[class]android.widget.FrameLayout[resource_id]None[text]None[enabled,,]", "view_str": "5840fa61c9ce7ee3c2325efceb0ce15f", "content_free_signature": "[class]android.widget.FrameLayout[resource_id]None"}



if __name__ == "__main__":
    # execute(TELA_INICIAL)
    execute(TELA_MESSAGE_DIGEST)
    # execute(TELA_CIPHER)