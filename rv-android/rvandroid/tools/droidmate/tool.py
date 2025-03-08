import os

from rvandroid.app import App
from rvandroid.commands.command import Command
from rvandroid.experiment.task import Task
from settings import TOOLS_DIR, INSTRUMENTED_DIR
from ..tool_spec import AbstractTool


class ToolSpec(AbstractTool):
    def __init__(self):
        super(ToolSpec, self).__init__("droidmate", """DroidMate-2 is a platform to easily assist both developers
                and researchers to customize, develop and test new test generators.(https://github.com/uds-se/droidmate).""",
                                       "org.droidmate")

    def execute_tool_specific_logic(self, task: Task, app: App):
        droidmate_jar = os.path.join(TOOLS_DIR, "droidmate", "droidmate-2-X.X.X-all.jar")
        output_dir = os.path.join(TOOLS_DIR, "droidmate", "temp")

        timeout_in_seconds = task.timeout
        timeout_in_millis = timeout_in_seconds * 1000

        with open(task.log_file, "wb") as droidmate_trace:
            exec_cmd = Command("java", [
                "-jar",
                "{}".format(droidmate_jar),
                "--Exploration-apkNames={0}".format(app.name),
                "--Exploration-apksDir={0}".format(INSTRUMENTED_DIR),
                "--Output-outputDir={0}".format(output_dir),
                "--Selectors-timeLimit={0}".format(timeout_in_millis),
                "--Selectors-actionLimit=100000000",
                "--Core-logLevel=debug"
            ], timeout=timeout_in_seconds)
            exec_cmd.invoke(stdout=droidmate_trace)

# --Exploration-apksDir=EXPLORATION-APKSDIR               Directory containing the apks to be processed by DroidMate.
# --Exploration-apksLimit=EXPLORATION-APKSLIMIT           Limits the number of apks on which DroidMate will run. 0 means no limit.
# --Exploration-apkNames=EXPLORATION-APKNAMES             Filters apps on which DroidMate will be run. Supply full file names, separated by commas, surrounded by square brackets. If the list is empty, it will run on all the apps in the apks dir. Example value: [app1.apk, app2.apk]
# --Output-outputDir=OUTPUT-OUTPUTDIR                     Path to the directory that will contain DroidMate exploration output.
# --Selectors-actionLimit=SELECTORS-ACTIONLIMIT           How many actions the GUI exploration strategy can conduct before terminating.
# --Selectors-timeLimit=SELECTORS-TIMELIMIT               How long the exploration of any given apk should take, in milli seconds. If set to 0, instead actionsLimit will be used.
# --Output-debugMode=OUTPUT-DEBUGMODE                     enable debug output
# --Exploration-deviceSerialNumber=EXPLORATION-DEVICESERIALNUMBER          Serial number of the device to be used. Mutually exclusive to index.
