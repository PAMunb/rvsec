from app import App
from commands.command import Command

from ..tool_spec import AbstractTool
import os, re
from settings import WORKING_DIR, INSTRUMENTED_DIR


class ToolSpec(AbstractTool):
    def __init__(self):
        super(ToolSpec, self).__init__("ares", """ ares """, 'run_ares.sh')

    def execute_tool_specific_logic(self, app: App, timeout: int, log_file: str):
        ares_entrypoint = os.path.join(WORKING_DIR, 'tools', 'ares', 'run_ares.sh')

        timeout_in_minutes = int(timeout/60)

        with open(log_file, 'wb') as ares_trace:
            exec_cmd = Command('{}'.format(ares_entrypoint),  [
                app.path,
                'emulator-5554',
                str(timeout_in_minutes),
                "{}".format(os.path.join(WORKING_DIR, 'tools', 'ares'))
            ], timeout)
            exec_cmd.invoke(stdout=ares_trace)
