from app import App
from commands.command import Command

from ..tool_spec import AbstractTool
import os, re
from settings import WORKING_DIR, INSTRUMENTED_DIR

class ToolSpec(AbstractTool):
    def __init__(self):
        super(ToolSpec, self).__init__("qtesting", """ qtesting """, 'main.py')

    def execute_tool_specific_logic(self, app: App, timeout: int, log_file: str):
        qtesting_entrypoint = os.path.join(WORKING_DIR, 'tools', 'qtesting', 'src', 'main.py')
        config_file = os.path.join(WORKING_DIR, 'tools', 'qtesting', 'src', 'conf.txt')
        with open(config_file, "w") as f:
            f.write("""
            [Path]
            Benchmark = 
            APK_NAME = {0}
            [Setting]
            DEVICE_ID = emulator-5554
            TIME_LIMIT = {1}
            TEST_INDEX=1""".format(app.path,timeout))

        with open(log_file, 'wb') as qtesting_trace:
            exec_cmd = Command('{}'.format(qtesting_entrypoint), [
                '-r',
                '{0}'.format(config_file)
            ], timeout=timeout)
            print(exec_cmd.args)
            exec_cmd.invoke(stdout=qtesting_trace)
