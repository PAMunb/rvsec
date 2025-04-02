# rvandroid/tools/fastbot/tool.py
"""
FastBot tool implementation with configuration support.
"""
import os

from rvandroid.app import App
from rvandroid.commands.command import Command
from rvandroid.experiment.task.task_model import Task
from rvandroid.tools.configurable_tool import ConfigurableTool
from settings import TOOLS_DIR


class ToolSpec(ConfigurableTool):
    """
    FastBot testing tool with configurable parameters.

    ### Architectural Decisions:
    - Extends ConfigurableTool for standardized configuration handling
    - Provides a unified interface to the FastBot testing framework
    - Supports customization through configuration parameters

    ### Role in the System:
    - Integrates FastBot Android testing tool into the RV-Android framework
    - Enables model-based testing with configurable parameters
    - Provides consistent execution interface aligned with other tools
    """

    def __init__(self):
        """Initialize the FastBot tool with default configuration."""
        super().__init__(
            "fastbot",
            "Fastbot is a model-based testing tool for modeling GUI transitions "
            "to discover app stability problems.",
            "com.android.commands.fastbot"
        )

        # Default configuration
        self.config = {
            "throttle": 100  # Default throttle value
        }

    def configure_tool_specific(self, config):
        """Configure FastBot-specific parameters."""
        # Update parameters if specified
        if "throttle" in config:
            self.config["throttle"] = int(config["throttle"])

    def execute_tool_specific_logic(self, task: Task, app: App):
        """Execute FastBot with the configured parameters."""
        self.logger.info(f"Running FastBot on {app.name}")

        fastbot_base_dir = os.path.join(TOOLS_DIR, "fastbot")

        jar_monkeyq = os.path.join(fastbot_base_dir, "monkeyq.jar")
        jar_fastbot = os.path.join(fastbot_base_dir, "fastbot-thirdpart.jar")
        jar_framework = os.path.join(fastbot_base_dir, "framework.jar")
        libs = os.path.join(fastbot_base_dir, "libs")
        apk_string = os.path.join(fastbot_base_dir, "max.valid.strings")

        # Push files to device
        self._adb_push(jar_monkeyq, "/sdcard/monkeyq.jar")
        self._adb_push(jar_fastbot, "/sdcard/fastbot-thirdpart.jar")
        self._adb_push(jar_framework, "/sdcard/framework.jar")

        # Push libraries
        self._adb_push(os.path.join(libs, "arm64-v8a", "libfastbot_native.so"),
                       "/data/local/tmp/arm64-v8a/libfastbot_native.so")
        self._adb_push(os.path.join(libs, "armeabi-v7a", "libfastbot_native.so"),
                       "/data/local/tmp/armeabi-v7a/libfastbot_native.so")
        self._adb_push(os.path.join(libs, "x86", "libfastbot_native.so"),
                       "/data/local/tmp/x86/libfastbot_native.so")
        self._adb_push(os.path.join(libs, "x86_64", "libfastbot_native.so"),
                       "/data/local/tmp/x86_64/libfastbot_native.so")

        # Prepare APK strings
        with open(apk_string, "wb") as aapt:
            aapt_cmd = Command("aapt2", ["dump", "strings", app.path])
            aapt_cmd.invoke(stdout=aapt)
        self._adb_push(apk_string, "/sdcard")
        os.remove(apk_string)

        # Calculate timeout
        timeout_in_seconds = task.config.timeout
        timeout_in_minutes = int(timeout_in_seconds / 60)

        # Execute FastBot
        with open(task.result.trace_file, "wb") as trace:
            exec_cmd = Command("adb", [
                "-s",
                "emulator-5554",
                "shell",
                "CLASSPATH=/sdcard/monkeyq.jar:/sdcard/framework.jar:/sdcard/fastbot-thirdpart.jar",
                "exec",
                "app_process",
                "/system/bin",
                "com.android.commands.monkey.Monkey",
                "-p",
                app.package_name,
                "--agent",
                "reuseq",
                "--running-minutes",
                str(timeout_in_minutes),
                "--throttle",
                str(self.config["throttle"]),
                "-v",
                "-v"
            ], timeout_in_seconds)

            exec_cmd.invoke(stdout=trace)

    def _adb_push(self, input_file, out_path):
        """
        Push a file to the Android device.

        Args:
            input_file: File to push
            out_path: Destination path on device
        """
        push_cmd = Command("adb", ["push", input_file, out_path])
        push_cmd.invoke()