import rvandroid.utils as utils
from rvandroid.experiment.task import Task
from rvandroid.parser.classes import Classes, Window


def find_widget(widget_class, windows):
    pass


def parse_gator_file(gator_file: str, classes: Classes | None = None, windows: dict[str, Window] | None = None,
                     package: str | None = None, task: Task | None = None):
    if classes is None:  # TODO rever essa parte
        classes = Classes()
    if windows is None:
        windows = {}
    gator = utils.read_json(gator_file)
    print(f"gator={gator}")

    for window in gator["windows"]:
        print(f"{window}")
        clazz_name = window["name"]

        if package is not None and package not in clazz_name:
            continue

        if clazz_name not in classes.classes:
            classes.add_clazz(window["name"], True, False)

        if clazz_name not in windows:
            screen = Window(clazz_name)
            windows[clazz_name] = screen
        screen = windows[clazz_name]
        screen.id = window["id"]
        print(f"screen={screen}")

    for transition in gator["transitions"]:
        print(f"transition={transition}")
        for event in transition["events"]:
            print(f"\t-event={event}")

            # widget_class = transition["widgetClass"]
            # window = windows[widget_class]
            # if window:
            #     pass
