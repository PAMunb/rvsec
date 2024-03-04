import os
import re
import subprocess

from app import App
from commands.command import Command
from settings import WORKING_DIR

from ..tool_spec import AbstractTool
import logging as logging_api


logging = logging_api.getLogger(__name__)


#TODO mover para android.py
def adb_push(input_file, out_path, std_out):
    logging.info("ADB pushing: {} to {}".format(input_file, out_path))
    push_cmd = Command('adb', ['push', '-a', '-p', input_file, out_path])
    push_cmd.invoke(stdout=std_out)


class ToolSpec(AbstractTool):
    def __init__(self):
        super(ToolSpec, self).__init__("ape", """Ape applies a CEGAR style technique to refine and coarsen the model abstraction.
                                    (http://gutianxiao.com/ape/).""",
                                       'com.android.commands.ape')

    def execute_tool_specific_logic(self, app: App, timeout: int, log_file: str):
        ape_base_dir = os.path.join(WORKING_DIR, 'tools', 'ape')
        jar_ape = os.path.join(ape_base_dir, 'ape.jar')

        with open(log_file, 'wb') as trace:
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
                '100',
                '--ape',
                'sata'
            ], timeout)
            exec_cmd.invoke(stdout=trace)

