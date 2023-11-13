from app import App
from commands.command import Command

from ..tool_spec import AbstractTool
import os
from settings import WORKING_DIR, INSTRUMENTED_DIR

class ToolSpec(AbstractTool):
    def __init__(self):
        super(ToolSpec, self).__init__("droidmate", """DroidMate-2 is a platform to easily assist both developers
                and researchers to customize, develop and test new test generators.(https://github.com/uds-se/droidmate).""",
                                       'org.droidmate')

    def execute_tool_specific_logic(self, app: App, timeout: int, log_file: str):
        droidmate_jar = os.path.join(WORKING_DIR, 'tools', 'droidmate', 'droidmate-2-X.X.X-all.jar')
        output_dir = os.path.join(WORKING_DIR, 'tools', 'droidmate', 'temp')

        with open(log_file, 'wb') as droidmate_trace:
            exec_cmd = Command('java', [
                '-jar',
                '{}'.format(droidmate_jar),
                '--Exploration-apkNames={0}'.format(app.name),
                '--Exploration-apksDir={0}'.format(INSTRUMENTED_DIR),
                '--Output-outputDir={0}'.format(output_dir),
                '--Core-logLevel=debug'
            ], timeout=timeout)
            exec_cmd.invoke(stdout=droidmate_trace)
