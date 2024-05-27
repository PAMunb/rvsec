from app import App
from commands.command import Command

from ..tool_spec import AbstractTool
import os, fileinput, re
from settings import WORKING_DIR, INSTRUMENTED_DIR

class ToolSpec(AbstractTool):
    def __init__(self):
        super(ToolSpec, self).__init__("qlearning", """ qlearning """, 'main.py')

    def execute_tool_specific_logic(self, app: App, timeout: int, log_file: str):
        qlearning_entrypoint = os.path.join(WORKING_DIR, 'tools', 'qlearning', 'src', 'main.py')
        config_file = os.path.join(WORKING_DIR, 'tools', 'qlearning', 'src', 'conf_template.txt')
        with fileinput.input(config_file, inplace=True) as f:
            for line in f:
                print(re.sub(r"(APK_NAME = ).+", r"\1{0}".format(app.path)), end='')

        with open(log_file, 'wb') as qlearning_trace:
            exec_cmd = Command('python3', [
                '{}'.format(qlearning_entrypoint),
                '-r {0}'.format(config_file)
            ], timeout=timeout)
            exec_cmd.invoke(stdout=qlearning_trace)
