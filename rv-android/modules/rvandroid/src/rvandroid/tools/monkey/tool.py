# rvandroid/tools/monkey/tool.py
from rv_android_core.app import App
from rv_android_core.commands.command import Command
from rv_android_core.experiment.task.task_model import Task  # Updated import
from ..tool_spec import AbstractTool


class ToolSpec(AbstractTool):
    def __init__(self):
        super(ToolSpec, self).__init__("monkey", """Monkey is a program that runs on your emulator 
        or device and generates pseudo-random streams of user events such as clicks, touches, or gestures, 
        as well as a number of system-level events. (https://developer.android.com/studio/test/other-testing-tools/monkey)""",
                                       "com.android.commands.monkey")

    def execute_tool_specific_logic(self, task: Task, app: App):
        # seed = "123"
        with open(task.result.trace_file, "wb") as trace:
            exec_cmd = Command("adb", [
                "shell",
                "monkey",
                "-v",
                "-v",
                # "--seed",
                # seed,
                "--ignore-security-exceptions",
                "-p",
                app.package_name,  # app package
                str(1_000_000_000)  # events
            ], task.config.timeout)
            exec_cmd.invoke(stdout=trace)
