import os

from app import App
from commands.command import Command
from settings import WORKING_DIR
from ..tool_spec import AbstractTool


def adb_push(input_file, out_path):
    push_cmd = Command('adb', ['push', input_file, out_path])
    push_cmd.invoke()


class ToolSpec(AbstractTool):
    def __init__(self):
        super(ToolSpec, self).__init__("fastbot", """Fastbot is a model-based testing tool for 
        modeling GUI transitions to discover app stability problems. It combines machine learning and reinforcement 
        learning techniques to assist discovery in a more intelligent way. (https://github.com/bytedance/Fastbot_Android).""",
                                       'com.android.commands.fastbot')

    def execute_tool_specific_logic(self, app: App, timeout: int, log_file: str):
        print(">>>>>>>>>>> {}".format(os.getcwd()))
        fastbot_base_dir = os.path.join(WORKING_DIR, 'tools', 'fastbot')

        jar_monkeyq = os.path.join(fastbot_base_dir, 'monkeyq.jar')
        jar_fastbot = os.path.join(fastbot_base_dir, 'fastbot-thirdpart.jar')
        jar_framework = os.path.join(fastbot_base_dir, 'framework.jar')
        libs = os.path.join(fastbot_base_dir, 'libs')  # , '*')
        apk_string = os.path.join(fastbot_base_dir, 'max.valid.strings')

        adb_push(jar_monkeyq, "/sdcard/monkeyq.jar")
        adb_push(jar_fastbot, "/sdcard/fastbot-thirdpart.jar")
        adb_push(jar_framework, "/sdcard/framework.jar")
        # adb_push(libs, "/data/local/tmp/")
        adb_push(os.path.join(libs, "arm64-v8a", "libfastbot_native.so"), "/data/local/tmp/arm64-v8a/libfastbot_native.so")
        adb_push(os.path.join(libs, "armeabi-v7a", "libfastbot_native.so"), "/data/local/tmp/armeabi-v7a/libfastbot_native.so")
        adb_push(os.path.join(libs, "x86", "libfastbot_native.so"), "/data/local/tmp/x86/libfastbot_native.so")
        adb_push(os.path.join(libs, "x86_64", "libfastbot_native.so"), "/data/local/tmp/x86_64/libfastbot_native.so")

        with open(apk_string, 'wb') as aapt:
            aapt_cmd = Command('aapt2', ['dump', 'strings', app.path])
            aapt_cmd.invoke(stdout=aapt)
        adb_push(apk_string, "/sdcard")
        os.remove(apk_string)

        with open(log_file, 'wb') as trace:
            exec_cmd = Command('adb', [
                '-s',
                'emulator-5554',
                'shell',
                'CLASSPATH=/sdcard/monkeyq.jar:/sdcard/framework.jar:/sdcard/fastbot-thirdpart.jar',
                'exec',
                'app_process',
                '/system/bin',
                'com.android.commands.monkey.Monkey',
                '-p',
                app.package_name,
                '--agent',
                'reuseq',
                '--running-minutes',
                '120',  # TODO
                '--throttle',
                '100',  # TODO
                '-v',
                '-v'
            ], timeout)
            exec_cmd.invoke(stdout=trace)
