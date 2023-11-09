import os
import re

from app import App
from commands.command import Command

from tools.tool_spec import AbstractTool


class ToolSpec(AbstractTool):
    def __init__(self):
        super(ToolSpec, self).__init__("droidbot_bfs_naive", """DroidBot is a lightweight test input generator for Android. 
        It can send random or scripted input events to an Android app, achieve higher test coverage more quickly, 
        and generate a UI transition graph (UTG) after testing (https://github.com/honeynet/droidbot).""",
                                       'com.android.commands.droidbot')

    def execute_tool_specific_logic(self, app: App, timeout: int, log_file: str):
        with open(log_file, 'wb') as trace:
            exec_cmd = Command('droidbot', [
                '-d',
                'emulator-5554',
                '-a',
                app.path,
                '-policy',
                'bfs_naive',
                '-is_emulator',
            ], timeout)
            exec_cmd.invoke(stdout=trace)
