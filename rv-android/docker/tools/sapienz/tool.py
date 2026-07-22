import os

from rvandroid.app import App
from rvandroid.commands import Command
from ..tool_spec import AbstractTool


class ToolSpec(AbstractTool):
    def __init__(self):
        super(ToolSpec, self).__init__("sapienz", """Sapienz is a Multi-objective Automated Testing for 
            Android Applications. (https://github.com/Rhapsod/sapienz)""", None)
        
    def execute_tool_specific_logic(self, app: App, timeout: int, log_file: str):
        with open(log_file, 'wb') as trace:
            exec_cmd = Command('python2', [
                os.environ['SAPIENZ_HOME'] + os.sep + 'main.py',
                app.path
            ], timeout)
            exec_cmd.invoke(stdout=trace)
