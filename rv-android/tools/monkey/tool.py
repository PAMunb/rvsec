import os
import re

from commands.command import Command

from settings import INSTRUMENTED_DIR
from app import App

from ..tool_spec import AbstractTool


class ToolSpec(AbstractTool):
    def __init__(self):
        super(ToolSpec, self).__init__("monkey", """Monkey is a program that runs on your emulator 
        or device and generates pseudo-random streams of user events such as clicks, touches, or gestures, 
        as well as a number of system-level events. (https://developer.android.com/studio/test/monkey)""",
                                       'com.android.commands.monkey')
        
    def execute_tool_specific_logic(self, app: App, timeout: int, log_file: str):
        with open(log_file, 'wb') as trace:
            exec_cmd = Command('adb', [
                'shell',
                'monkey',
                '-p',
                app.package_name,
                # '--ignore-crashes',
                # '--ignore-timeouts',
                '--ignore-security-exceptions',
                '10000000'
            ], timeout)
            exec_cmd.invoke(stdout=trace)
