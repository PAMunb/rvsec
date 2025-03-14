# rvandroid/tools/droidbot_bfs_greedy/tool.py
from rvandroid.app import App
from rvandroid.commands.command import Command
from rvandroid.experiment.task_model import Task  # Updated import
from rvandroid.tools.tool_spec import AbstractTool


class ToolSpec(AbstractTool):
    def __init__(self):
        super(ToolSpec, self).__init__("droidbot_bfs_greedy", """DroidBot is a lightweight test input generator for Android. 
        It can send random or scripted input events to an Android app, achieve higher test coverage more quickly, 
        and generate a UI transition graph (UTG) after testing (https://github.com/honeynet/droidbot).""",
                                       'com.android.commands.droidbot')

    def execute_tool_specific_logic(self, task: Task, app: App):
        with open(task.result.trace_file, 'wb') as trace:
            exec_cmd = Command('droidbot', [
                '-d',
                'emulator-5554',
                '-a',
                app.path,
                '-policy',
                'bfs_greedy',
                "-count",
                "10000000000",
                "-timeout",
                str(task.config.timeout),
                "-ignore_ad",
                '-is_emulator',
            ], task.config.timeout)
            exec_cmd.invoke(stdout=trace)
