# rvandroid/tools/ares/tool.py
import os

from rvandroid.app import App
from rvandroid.commands.command import Command
from rvandroid.experiment.task.task_model import Task  # Updated import
from settings import TOOLS_DIR
from ..tool_spec import AbstractTool


class ToolSpec(AbstractTool):
    def __init__(self):
        super(ToolSpec, self).__init__("ares", """ ares """, 'run_ares.sh')

    def execute_tool_specific_logic(self, task: Task, app: App):
        ares_dir = os.path.join(TOOLS_DIR, 'ares')
        ares_entrypoint = os.path.join(ares_dir, 'run_ares.sh')

        timeout_in_seconds = task.config.timeout
        timeout_in_minutes = int(timeout_in_seconds / 60)

        with open(task.result.trace_file, 'wb') as ares_trace:
            exec_cmd = Command('{}'.format(ares_entrypoint), [
                app.path,
                'emulator-5554',
                str(timeout_in_minutes),
                "{}".format(ares_dir)
            ], timeout_in_seconds)
            exec_cmd.invoke(stdout=ares_trace)
