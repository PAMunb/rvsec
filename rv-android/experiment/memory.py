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


class Memory:

    def __init__(self):
        self.tasks = []
        self.execution_memory = {}

    def init(self, repetitions: int, timeouts: list[int], tools: list[AbstractTool], apks: list[App]):
        memory = {}
        for apk_app in apks:
            apk = apk_app.name
            if apk not in memory:
                memory[apk] = {}
            for rep in range(repetitions):
                repetition = rep + 1
                if repetition not in memory[apk]:
                    memory[apk][repetition] = {}
                for timeout in timeouts:
                    if timeout not in memory[apk][repetition]:
                        memory[apk][repetition][timeout] = {}
                    for tool_obj in tools:
                        tool = tool_obj.name
                        task = Task(apk, repetition, timeout, tool)
                        memory[apk][repetition][timeout][tool] = task
                        self.tasks.append(task)
        self.execution_memory = memory

    def get_tasks(self, _sort=lambda x: (x.repetition, x.timeout, x.tool, x.apk)):
        tasks = sorted(self.tasks, key=_sort)
        return tasks

    def read(self, memory_file: str):
        print("read={}".format(memory_file))
        with open(memory_file, 'r') as file:
            result = json.load(file)
            self.execution_memory, self.tasks = self.__from_result(result)
            print("self.execution_memory={}".format(self.execution_memory))
            print("self.tasks={}".format(self.tasks))

    def write(self, memory_file: str):
        result = self.__to_result()
        with open(memory_file, "w") as outfile:
            json.dump(result, outfile)

    def __to_result(self):
        result = {}
        for apk, rep_data in self.execution_memory.items():
            for rep, timeout_data in rep_data.items():
                for timeout, tool_data in timeout_data.items():
                    for tool, task in tool_data.items():
                        result.setdefault(apk, {}).setdefault(rep, {}).setdefault(timeout, {})[tool] = task.executed
        return result

    def __from_result(self, result):
        tasks = []
        memory = {}
        for apk, rep_data in result.items():
            memory[apk] = {}
            for rep, timeout_data in rep_data.items():
                memory[apk][rep] = {}
                for timeout, tool_data in timeout_data.items():
                    memory[apk][rep][timeout] = {}
                    for tool, executed in tool_data.items():
                        task = Task(apk, rep, timeout, tool, executed)
                        memory[apk][rep][timeout][tool] = task
                        tasks.append(task)
        return memory, tasks

    def __str__(self):
        return "Memory=[tasks={}]".format(len(self.tasks))
