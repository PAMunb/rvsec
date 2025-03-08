from rvandroid.app import App
from rvandroid.commands.command import Command
from rvandroid.experiment.task import Task
from ..tool_spec import AbstractTool


class ToolSpec(AbstractTool):
    def __init__(self):
        super(ToolSpec, self).__init__("monkey", """Monkey is a program that runs on your emulator 
        or device and generates pseudo-random streams of user events such as clicks, touches, or gestures, 
        as well as a number of system-level events. (https://developer.android.com/studio/test/other-testing-tools/monkey)""",
                                       "com.android.commands.monkey")

    def execute_tool_specific_logic(self, task: Task, app: App):
        # seed = "123"
        with open(task.log_file, "wb") as trace:
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
            ], task.timeout)
            exec_cmd.invoke(stdout=trace)
