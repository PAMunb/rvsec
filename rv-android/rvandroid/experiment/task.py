import logging as logging_api
import os
from datetime import datetime

from rvandroid import utils
from rvandroid.app import App
from rvandroid.constants import *
from rvandroid.log.log import RvCoverage
from rvandroid.parser import static_analysis_parser
from rvandroid.parser.classes import *

DEFAULT_DATETIME = utils.milliseconds_to_datetime(0)


class TaskStatus(Enum):
    CREATED = 1
    RUNNING = 2
    EXECUTED = 3


class Task:
    cont = 0

    def __init__(self, apk: str, repetition: int, timeout: int, tool: str, status=TaskStatus.CREATED, executed=False,
                 start_time=DEFAULT_DATETIME, finish_time=DEFAULT_DATETIME):
        Task.cont += 1
        self.id = Task.cont
        self.tracker = TaskExecutionTracker()
        self.logging = logging_api.getLogger(__name__)
        self.tool = tool
        self.timeout = timeout
        self.repetition = repetition
        self.apk = apk
        self.status = status
        self.executed = executed  # TODO deprecated ... fazer alteracoes para usar status
        self.start_time: datetime = start_time  # TODO inicializar com None
        self.finish_time: datetime = finish_time  # TODO inicializar com None
        self.time: int = 0  # time (in seconds) it took to run
        self.result: list[dict] = []  # TODO o q eh e onde esta sendo usado?
        self.coverage = {}  # TODO onde esta sendo usado?
        self.error = ""  # TODO onde esta sendo usado? e o q eh?
        self.results_dir = ""  # TODO onde esta sendo usado?
        self.logcat_file = ""
        self.log_file = ""

    def init(self, base_results_dir: str):
        self.start_time = datetime.now()
        self.status = TaskStatus.CREATED
        results_dir = os.path.join(base_results_dir, self.apk)
        self.results_dir = results_dir
        base_name = "{0}__{1}__{2}__{3}".format(self.apk, self.repetition, self.timeout, self.tool)
        # TODO limpar se ja existir
        self.logcat_file = os.path.join(results_dir, "{}{}".format(base_name, EXTENSION_LOGCAT))
        self.log_file = os.path.join(results_dir, "{}{}".format(base_name, EXTENSION_TRACE))

    def start_tracker(self, app: App):
        self.tracker.start(self, app)

    def __str__(self):
        return "[id={}, apk={}, rep={}, timeout={}, tool={}]".format(self.id, self.apk, self.repetition, self.timeout,
                                                                     self.tool)

    def __repr__(self):
        return "[{},{},{},{},{},{}]".format(self.id, self.apk, self.repetition, self.timeout, self.tool, self.status)


class TaskExecutionTracker:
    def __init__(self):
        self.logging = logging_api.getLogger(__name__)
        self.task: Task | None = None
        self.app: App | None = None
        self.classes: Classes | None = None
        self.windows: dict[str, Window] | None = None
        self.total_classes = 0  # Total number of classes in the app
        self.total_activities = 0  # Total number of activities in the app
        self.total_methods = 0  # Total number of methods in the app
        self.total_reachable_methods = 0  # Total number of reachable methods in the app
        self.total_reaches_mop = 0  # Total number of methods that reaches at least one MOP method
        self.total_directly_reaches_mop = 0  # Total number of methods that directly reaches at least one MOP method
        self.visited_classes: set[str] = set()
        self.visited_activities: set[str] = set()
        self.visited_methods: set[str] = set()
        self.visited_reachable_methods: set[str] = set()
        self.visited_reaches_mop: set[str] = set()
        self.visited_directly_reaches_mop: set[str] = set()

    def start(self, task: Task, app: App):
        print(f"start tracker for task={task}")
        self.task = task
        self.app = app
        self.classes, self.windows = static_analysis_parser.read_static_analysis_files(task.results_dir, task.apk,
                                                                                       app.package_name)
        print(f"classes={self.classes}")
        for clazz_name in self.classes.classes:
            self.total_classes += 1
            clazz = self.classes.classes[clazz_name]
            if clazz.is_activity:
                self.total_activities += 1
            for method in clazz.methods:
                self.total_methods += 1
                if method.reachable:
                    self.total_reachable_methods += 1
                if method.reaches_mop:
                    self.total_reaches_mop += 1
                if method.directly_reaches_mop:
                    self.total_directly_reaches_mop += 1

    def call(self, cov: RvCoverage):
        # if cov.clazz in self.all_methods:
        #     sig = "{}.{}".format(cov.clazz, cov.method)
        #     if cov.clazz not in self.visited_classes:
        #         self.visited_classes.add(cov.clazz)
        #     if self.all_methods[cov.clazz][IS_ACTIVITY] and cov.clazz not in self.visited_activities:
        #         self.visited_activities.add(cov.clazz)
        #     if cov.method in self.all_methods[cov.clazz][METHODS]:
        #         self.visited_methods.add(sig)
        #         if self.all_methods[cov.clazz][METHODS][cov.method][USE_JCA]:
        #             self.visited_mop_methods.add(sig)
        return self.coverage()

    def coverage(self):
        class_coverage = self.__pct(self.visited_classes, self.total_classes)
        activity_coverage = self.__pct(self.visited_activities, self.total_activities)
        method_coverage = self.__pct(self.visited_methods, self.total_methods)
        reachable_methods_coverage = self.__pct(self.visited_reachable_methods, self.total_reachable_methods)
        reaches_mop_coverage = self.__pct(self.visited_reaches_mop, self.total_reaches_mop)
        directly_reaches_mop_coverage = self.__pct(self.visited_directly_reaches_mop, self.total_directly_reaches_mop)
        return class_coverage, activity_coverage, method_coverage, reachable_methods_coverage, reaches_mop_coverage, directly_reaches_mop_coverage

    def __pct(self, collection: set, total: int):
        return 0 if total == 0 else (len(collection) * 100) / total
