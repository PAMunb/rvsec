from rvandroid.domain.classes import Classes
from rvandroid.domain.window import Windows
from rvandroid.domain.wtg import WindowTransitionGraph


class StaticAnalysisData:

    def __init__(self, classes: Classes, windows: Windows, wtg: WindowTransitionGraph):
        self.classes = classes
        self.windows = windows
        self.wtg = wtg
