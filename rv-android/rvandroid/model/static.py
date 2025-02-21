
import logging
import os
import sys

from rvandroid.app import App
from rvandroid.model.wtg import WindowTransitionGraph
from rvandroid.parser.static import gator_parser, reach_parser, gesda_parser, static_analysis_parser
from rvandroid.model.classes import Classes
from rvandroid.model.window import Windows


class StaticAnalysisData:

    def __init__(self, classes: Classes, windows: Windows, wtg: WindowTransitionGraph):
        self.classes = classes
        self.windows = windows
        self.wtg = wtg
