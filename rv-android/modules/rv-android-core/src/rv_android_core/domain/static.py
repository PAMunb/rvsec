from rv_android_core.domain.classes import Classes
from rv_android_core.domain.window import Windows
from rv_android_core.domain.wtg import WindowTransitionGraph


class StaticAnalysisData:

    def __init__(self, classes: Classes, windows: Windows, wtg: WindowTransitionGraph):
        self.classes = classes
        self.windows = windows
        self.wtg = wtg
