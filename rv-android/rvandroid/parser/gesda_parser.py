import rvandroid.utils as utils
from rvandroid.parser.classes import Classes, Widget, Window, WindowType, WidgetType, WidgetListener


def parse_gesda_file(gesda_file: str, classes: Classes | None = None) -> dict[str, Window]:
    windows: dict[str, Window] = {}
    if classes is None:  # TODO rever essa parte
        classes = Classes()
    gesda = utils.read_json(gesda_file)
    for window in gesda["windows"]:
        print(f"\n\n{window}")
        clazz_name = window["name"]
        if clazz_name not in classes.classes:
            classes.add_clazz(window["name"], True, window["isMain"])
            print(f"parse_gesda_file ... criando nova classe: {window["name"]}")
            exit(-1)  # TODO verificar
        # clazz: Clazz = classes.get_clazz(window["name"])

        screen = Window(clazz_name)
        screen.type = WindowType.from_string(window["type"])
        screen.layout_file = window["layoutFileName"]
        screen.widgets = get_widgets(window["widgets"])

        windows[clazz_name] = screen
        print(screen)

    return windows


def get_listeners(param: list[dict]):
    listeners = []
    for listener_dict in param:
        print(f"listener: {listener_dict}")

        listener_type = listener_dict["type"]  # TODO verificar
        listener_class = listener_dict["callbackMethod"]["className"]
        listener_method = listener_dict["callbackMethod"]["name"]
        listener_signature = listener_dict["callbackMethod"]["signature"]

        listeners.append(WidgetListener(listener_type, listener_class, listener_method, listener_signature))
    return listeners


def get_widgets(widgets_list: list[dict]) -> list[Widget]:
    widgets: list[Widget] = []

    for widget_dict in widgets_list:
        print(f"\n\n{widget_dict}")

        widget_id = widget_dict["widgetId"]
        widget_type = WidgetType.from_string(widget_dict["type"])
        widget_name = widget_dict["name"]

        widget = Widget(widget_id, widget_type, widget_name)

        # Using the dict.get() method with default values (None)
        widget.field = widget_dict.get("field")
        widget.text = widget_dict.get("text")
        widget.hint = widget_dict.get("hint")
        widget.entries = widget_dict.get("entries")
        widget.input_type = widget_dict.get("inputType")

        if "listeners" in widget_dict:
            widget.listeners = get_listeners(widget_dict["listeners"])

        widgets.append(widget)

    return widgets
