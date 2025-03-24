# rvandroid/tools/qtesting/tool.py
import os

from rvandroid.app import App
from rvandroid.commands.command import Command
from rvandroid.experiment.task.task_model import Task  # Updated import
from settings import TOOLS_DIR
from ..tool_spec import AbstractTool


class ToolSpec(AbstractTool):
    def __init__(self):
        super(ToolSpec, self).__init__("qtesting", """ qtesting """, "main.py")

    def execute_tool_specific_logic(self, task: Task, app: App):
        timeout_in_seconds = task.config.timeout
        qtesting_dir = os.path.join(TOOLS_DIR, "qtesting")
        qtesting_python = os.path.join(qtesting_dir, "venv", "bin", "python")
        qtesting_entrypoint = os.path.join(qtesting_dir, "src", "main.py")
        # qtesting_dir = os.path.join(WORKING_DIR, "tools", "qtesting")
        # qtesting_entrypoint = os.path.join(qtesting_dir, "run.sh")
        config_file = os.path.join(qtesting_dir, "src", "conf.txt")
        # config_file = os.path.join(qtesting_dir, "apks", "conf.txt")
        with open(config_file, "w") as f:
            f.write("""
                    [Path]
                    Benchmark =
                    APK_NAME = {0}
                    [Setting]
                    DEVICE_ID = emulator-5554
                    TIME_LIMIT = {1}
                    TEST_INDEX=1""".format(app.path, timeout_in_seconds))
            # f.write("""
            #         [Path]
            #         Benchmark =
            #         APK_NAME = /qtesting/apks/app.apk
            #         [Setting]
            #         DEVICE_ID = emulator-5554
            #         TIME_LIMIT = {0}
            #         TEST_INDEX=1""".format(timeout_in_seconds))

        with open(task.result.trace_file, "wb") as qtesting_trace:
            # exec_cmd = Command(qtesting_entrypoint, [
            #     "{}".format(qtesting_dir)
            # ], timeout_in_seconds)

            exec_cmd = Command("python", [
                "{}".format(qtesting_entrypoint),
                "-r",
                "{0}".format(config_file)
            ])
            # ], timeout_in_seconds)

            # exec_cmd = Command("{}".format(qtesting_entrypoint), [
            #     app.path,
            #     qtesting_dir
            # ], timeout_in_seconds)

            exec_cmd.invoke(stdout=qtesting_trace)
