import importlib
import logging as logging_api
import os.path
import shutil
import sys

#import analysis.methods_extractor as me
import analysis.reachable_methods_mop as reach
import analysis.results_analysis as res
import utils
from android import Android
from app import App
from commands.command import Command
from constants import EXTENSION_APK, EXTENSION_METHODS, EXTENSION_LOGCAT, EXTENSION_TRACE
from rvandroid import RvAndroid
from rvsec import RVSec
from experiment.task import Task
from settings import *
import json
from tools.tool_spec import AbstractTool
from constants import EXTENSION_METHODS, RVSEC_ERRORS, REPETITIONS, TIMEOUTS, TOOLS, SUMMARY, METHOD_COVERAGE, \
    METHODS_JCA_COVERAGE, ACTIVITIES_COVERAGE
from experiment import config as experiment_config


class Memory:

    def __init__(self):
        self.tasks = set()
        # self.execution_memory = {}

    def init(self, apks: list[App]):
        for apk_app in apks:
            apk = apk_app.name
            for rep in range(experiment_config.repetitions):
                repetition = rep + 1
                for timeout in experiment_config.timeouts:
                    for tool_obj in experiment_config.tools:
                        task = Task(apk, repetition, timeout, tool_obj.name)
                        self.tasks.add(task)

    def get_tasks(self, _sort=lambda x: (x.repetition, x.timeout, x.tool, x.apk)) -> list[Task]:
        sorted_tasks: list[Task]
        sorted_tasks = sorted(self.tasks, key=_sort)
        return sorted_tasks

    def read(self, memory_file: str):
        # print("read={}".format(memory_file))
        with open(memory_file, 'r') as file:
            result = json.load(file)
            # self.execution_memory, self.tasks = self.__from_result(result)
            # print("self.execution_memory={}".format(self.execution_memory))
            self.execution_memory, self.tasks = self.__from_result(result)
            # print("self.tasks={}".format(self.tasks))

    def write(self, memory_file: str):
        result = self.__to_result()
        with open(memory_file, "w") as outfile:
            json.dump(result, outfile)

    def __to_result(self):
        result = {}
        for task in self.tasks:
            result.setdefault(task.apk, {}).setdefault(task.repetition, {}).setdefault(task.timeout, {})[task.tool] = task.executed
        return result

    def __from_result(self, result):
        tasks = []
        # memory = {}
        for apk, rep_data in result.items():
            # memory[apk] = {}
            for rep, timeout_data in rep_data.items():
                # memory[apk][rep] = {}
                for timeout, tool_data in timeout_data.items():
                    # memory[apk][rep][timeout] = {}
                    for tool, executed in tool_data.items():
                        task = Task(apk, rep, timeout, tool, executed)
                        # memory[apk][rep][timeout][tool] = task
                        tasks.append(task)
        #return memory, tasks
        return None, tasks

    def __str__(self):
        return "Memory=[tasks={}]".format(len(self.tasks))
