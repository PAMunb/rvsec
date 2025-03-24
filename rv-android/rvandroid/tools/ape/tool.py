# rvandroid/tools/ape/tool.py
import logging as logging_api
import os

from rvandroid.app import App
from rvandroid.commands.command import Command
from rvandroid.experiment.task.task_model import Task  # Updated import
from settings import TOOLS_DIR
from ..tool_spec import AbstractTool

logging = logging_api.getLogger(__name__)


# TODO mover para android.py
def adb_push(input_file, out_path, std_out):
    logging.info("ADB pushing: {} to {}".format(input_file, out_path))
    push_cmd = Command('adb', ['push', '-a', '-p', input_file, out_path])
    push_cmd.invoke(stdout=std_out)


class ToolSpec(AbstractTool):
    def __init__(self):
        super(ToolSpec, self).__init__("ape", """Ape applies a CEGAR style technique to refine and coarsen the model abstraction.
                                    (http://gutianxiao.com/ape/).""",
                                       'com.android.commands.ape')

    def execute_tool_specific_logic(self, task: Task, app: App):
        ape_base_dir = os.path.join(TOOLS_DIR, 'ape')
        jar_ape = os.path.join(ape_base_dir, 'ape.jar')

        # Update to access timeout from the new Task structure
        timeout_in_seconds = task.config.timeout
        timeout_in_minutes = int(timeout_in_seconds / 60)

        # Update to access log_file from the new Task structure
        with open(task.result.trace_file, 'wb') as trace:
            adb_push(jar_ape, "/data/local/tmp/ape.jar", trace)

            exec_cmd = Command('adb', [
                '-s',
                'emulator-5554',
                'shell',
                'CLASSPATH=/data/local/tmp/ape.jar',
                '/system/bin/app_process',
                '/data/local/tmp/',
                'com.android.commands.monkey.Monkey',
                '-p',
                app.package_name,
                '--running-minutes',
                str(timeout_in_minutes),
                '--ape',
                'sata'
            ], timeout_in_seconds)
            exec_cmd.invoke(stdout=trace)