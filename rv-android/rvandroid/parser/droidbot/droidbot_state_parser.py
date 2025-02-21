from rvandroid.parser.droidbot.visitor import *


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
        text = "Button {}{}{}".format(self.__with_text(node), self.__with_description(node),
                                      self.__with_resource_id(node))
        item = ScreenItem(node.data, text, actions)
        print(item)
        self.items.append(item)

    def visit_edit_text(self, node):
        print(f"\n ***** EDIT_TEXT: {node.data}")
        actions = Visitor.get_possible_actions(node, self.counter)
        text = "Editable text view {}{}{}".format(self.__with_text(node), self.__with_description(node),
                                                  self.__with_resource_id(node))
        item = ScreenItem(node.data, text, actions)
        print(item)
        self.items.append(item)

    def visit_text_view(self, node):
        print(f"\n ***** TEXT_VIEW: {node.data}")
        actions = Visitor.get_possible_actions(node, self.counter)
        text = "Text view {}{}{}".format(self.__with_text(node), self.__with_description(node),
                                         self.__with_resource_id(node))
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
        text = "Image button {}{}{}".format(self.__with_text(node), self.__with_description(node),
                                            self.__with_resource_id(node))
        item = ScreenItem(node.data, text, actions)
        print(item)
        self.items.append(item)

    def visit_image(self, node):
        print(f"\n ***** IMAGE: {node.data}")
        actions = self.get_possible_actions(node, self.counter)
        text = "Image {}{}{}".format(self.__with_text(node), self.__with_description(node),
                                     self.__with_resource_id(node))
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
    return www(view)


def www(view: dict):
    # Criando a árvore a partir do JSON
    tree = create_tree_from_json(view)

    # Criando um visitante
    visitor = TextVisitor()

    # Percorrendo a árvore
    tree.accept(visitor)

    return visitor.get_screen_description()


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
