# import analysis.methods_extractor as me
import json
import os
from collections import defaultdict
from datetime import datetime

from rvandroid import utils  # TODO usar assim nos outros imports
from rvandroid.app import App
from rvandroid.experiment.task import Task, TaskStatus


class Memory:

    def __init__(self):
        self.__reset()

    def init(self, repetitions: int, timeouts: list[int], tools: list[str], apks: list[App]):
        self.__reset()
        for apk_app in apks:
            apk = apk_app.name
            if apk not in self.tasks_map:
                self.tasks_map[apk] = {}
            for rep in range(repetitions):
                repetition = str(rep + 1)
                if repetition not in self.tasks_map[apk]:
                    self.tasks_map[apk][repetition] = {}
                for timeout in timeouts:
                    timeout = str(timeout)
                    if timeout not in self.tasks_map[apk][repetition]:
                        self.tasks_map[apk][repetition][timeout] = {}
                    for tool in tools:
                        task = Task(apk, int(repetition), int(timeout), tool)
                        self.tasks_map[apk][repetition][timeout][tool] = task
                        self.tasks.add(task)

    def __reset(self):
        self.tasks: set[Task] = set()
        self.tasks_map: dict[str, dict[str, dict[str, dict[str, Task]]]] = {}

    def get_tasks(self, _sort=lambda x: (x.repetition, x.timeout, x.tool, x.apk)) -> list[Task]:
        sorted_tasks: list[Task]
        sorted_tasks = sorted(self.tasks, key=_sort)
        return sorted_tasks

    def get_task(self, apk: str, repetition: str, timeout: str, tool: str) -> Task | None:
        try:
            return self.tasks_map[apk][repetition][timeout][tool]
        except BaseException:
            return None

    @staticmethod
    def read(memory_file: str):
        memory = Memory()
        base_results_dir = os.path.dirname(memory_file)
        with open(memory_file, "r") as file:
            result = json.load(file)
            memory.tasks, memory.tasks_map = memory.__from_result(result, base_results_dir)
        return memory

    def write(self, memory_file: str):
        result = self.__to_result()
        with open(memory_file, "w") as outfile:
            json.dump(result, outfile)

    def __to_result(self):
        result = {}
        for task in self.tasks:
            start_time = utils.datetime_to_milliseconds(task.start_time)
            finish_time = utils.datetime_to_milliseconds(task.finish_time)
            result.setdefault(task.apk, {}).setdefault(task.repetition, {}).setdefault(task.timeout, {})[
                task.tool] = {"executed": task.executed,
                              "start": start_time,
                              "finish": finish_time
                              # "result": task.result,
                              # "coverage": task.coverage,
                              # "error": str(task.error)
                              }
        return result

    @staticmethod
    def __from_result(result, base_results_dir: str):
        tasks = []
        mapa = {}
        for apk, rep_data in result.items():
            if apk not in mapa:
                mapa[apk] = {}
            for rep, timeout_data in rep_data.items():
                if rep not in mapa[apk]:
                    mapa[apk][rep] = {}
                for timeout, tool_data in timeout_data.items():
                    if timeout not in mapa[apk][rep]:
                        mapa[apk][rep][timeout] = {}
                    for tool, data in tool_data.items():
                        task = Task(apk, int(rep), int(timeout), tool)
                        task.initialize(base_results_dir)
                        # TODO
                        task.status = TaskStatus.EXECUTED if data["executed"] else TaskStatus.CREATED
                        task.start_time = datetime.fromtimestamp(data["start"])
                        task.finish_time = datetime.fromtimestamp(data["finish"])
                        # TODO task.error = data["error"]
                        mapa[apk][rep][timeout][tool] = task
                        tasks.append(task)
        return tasks, mapa

    def __str__(self):
        return "Memory=[tasks={}]".format(len(self.tasks))
