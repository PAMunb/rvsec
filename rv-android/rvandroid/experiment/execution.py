import json
import logging as logging_api
import os.path
import os.path
import shutil
from datetime import datetime

from rvandroid.app import App
from rvandroid.constants import EXTENSION_METHODS, EXECUTION_MEMORY_FILENAME, EXTENSION_GESDA, EXTENSION_GATOR, EXTENSION_REACH
from rvandroid.experiment.memory import Memory
from rvandroid.experiment.task import Task, TaskStatus, TaskExecutionTracker
from settings import *
from rvandroid.tools.tool_spec import AbstractTool


logging = logging_api.getLogger(__name__)


class ExecutionManager:

    def __init__(self):
        self.memory: Memory
        self.tasks = []
        self.base_results_dir = ""
        self.memory_file = ""
        self.executed_tasks = set()
        self.start_time = datetime.now()
        self.finish_time = None

    def create_memory(self, apks: list[App], repetitions: int, timeouts: list[int], tools: list[AbstractTool],
                      memory_file: str, _sort=lambda x: (x.repetition, x.timeout, x.tool, x.apk)):
        # if the file exists, resume execution
        if os.path.exists(memory_file):
            self.base_results_dir = os.path.dirname(memory_file)
            self.memory_file = memory_file
            self.memory = self.read_memory()
        else:
            # start a new execution
            self.base_results_dir = create_results_dir()
            self.memory_file = os.path.join(self.base_results_dir, EXECUTION_MEMORY_FILENAME)
            self.memory = self.new_memory(repetitions, timeouts, tools, apks)
            self.write_memory()

        self.tasks = self.memory.get_tasks(_sort)
        self.init_executed_tasks()
        logging.info(f"Tasks: {self.statistics()}")
        logging.info(f"Execution memory file: {self.memory_file}")

    def init_executed_tasks(self):
        # self.executed_tasks = {task for task in self.tasks if task.executed}
        self.executed_tasks = set()
        for task in self.tasks:
            if task.executed:
                self.executed_tasks.add(task)

    def statistics(self) -> dict:
        pct = 0.0
        if len(self.tasks) > 0:
            pct = (len(self.executed_tasks) * 100) / len(self.tasks)
        data = {"tasks": len(self.tasks),
                "completed": len(self.executed_tasks),
                "pct": round(pct, 2)}
        return data

    def start_task(self, task: Task):
        task.init(self.base_results_dir)
        utils.create_folder_if_not_exists(task.results_dir)
        copy_methods_file(task.apk, task.results_dir)        

    def finish_task(self, task):
        task.executed = True
        task.finish_time = datetime.now()
        self.executed_tasks.add(task)
        self.write_memory()

    def task_error(self, task, ex):
        task.error = str(ex)
        task.finish_time = datetime.now()
        self.write_memory()

    def read_memory(self) -> Memory:
        logging.info("Reading execution memory file: {}".format(self.memory_file))
        return Memory.read(self.memory_file)

    def write_memory(self):
        logging.info("Writing execution memory file: {}".format(self.memory_file))
        self.memory.write(self.memory_file)

    @staticmethod
    def new_memory(repetitions: int, timeouts: list[int], tools_obj: list[AbstractTool], apks: list[App]) -> Memory:
        tools = [x.name for x in tools_obj]
        logging.info("Creating new execution memory=[apks={}, repetitions={}, timeouts={}, tools={}]"
                     .format(len(apks), repetitions, timeouts, tools))
        memory = Memory()
        memory.init(repetitions, timeouts, tools, apks)
        return memory


def create_results_dir():
    results_dir = os.path.join(RESULTS_DIR, TIMESTAMP)
    utils.create_folder_if_not_exists(results_dir)
    return results_dir


def copy_methods_file(apk: str, app_results_dir: str):
    extensions = [EXTENSION_METHODS, EXTENSION_GESDA, EXTENSION_GATOR, EXTENSION_REACH]
    for extension in extensions:
        file_name = apk + extension
        file_path = os.path.join(INSTRUMENTED_DIR, file_name)
        if os.path.exists(file_path):
            shutil.copy(file_path, app_results_dir)
    # methods_file_name = apk + EXTENSION_METHODS
    # methods_file = os.path.join(INSTRUMENTED_DIR, methods_file_name)
    # if os.path.exists(methods_file):
    #     shutil.copy(methods_file, app_results_dir)


def status(memory_file: str) -> str:
    memory = Memory.read(memory_file)
    pct = 0.0
    total_tasks = len(memory.tasks)
    executed_tasks = 0
    errors = []
    for task in memory.tasks:
        if TaskStatus.EXECUTED == task.status:
        # if task.executed:
            executed_tasks += 1
        if task.error:
            errors.append(f"task={task}, error={task.error}")
    if total_tasks > 0:
        pct = (executed_tasks * 100) / total_tasks
    data = {"tasks": total_tasks,
            "completed": executed_tasks,
            "pct": round(pct, 2),
            "errors": errors}
    return json.dumps(data, indent=2)
