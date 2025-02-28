from rvandroid.model.classes import Classes
from rvandroid.model.window import Windows
from rvandroid.model.wtg import WindowTransitionGraph


class StaticAnalysisData:

    def __init__(self, classes: Classes, windows: Windows, wtg: WindowTransitionGraph):
        self.classes = classes
        self.windows = windows
        self.wtg = wtg

