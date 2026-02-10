# rvandroid/tools/ape/tool.py
"""
APE tool implementation with configuration support.
"""
import os

from rvandroid.app import App
from rvandroid.commands.command import Command
from rvandroid.experiment.task.task_model import Task
from rvandroid.tools.configurable_tool import ConfigurableTool
from settings import TOOLS_DIR


class ToolSpec(ConfigurableTool):
    """
    APE tool with configurable parameters.

    ### Architectural Decisions:
    - Extends ConfigurableTool for standardized configuration handling
    - Provides a clean interface to the APE testing framework
    - Supports customization of APE parameters through configuration

    ### Role in the System:
    - Integrates the APE Android testing tool into the RV-Android framework
    - Enables APE-based testing with configurable parameters
    - Provides a unified interface for APE execution
    """

    def __init__(self):
        """Initialize the APE tool with default configuration."""
        super().__init__(
            "ape",
            "Ape applies a CEGAR style technique to refine and coarsen the model abstraction.",
            "com.android.commands.ape"
        )

        # Default configuration
        self.config = {
            "strategy": "sata"  # Default strategy
        }

    def configure_tool_specific(self, config):
        """Configure APE-specific parameters."""
        # Update parameters if specified
        if "strategy" in config:
            self.config["strategy"] = config["strategy"]

    def execute_tool_specific_logic(self, task: Task, app: App):
        """Execute APE with the configured parameters."""
        self.logger.info(f"Running APE with strategy: {self.config['strategy']}")

        ape_base_dir = os.path.join(TOOLS_DIR, 'ape')
        jar_ape = os.path.join(ape_base_dir, 'ape.jar')

        # Calculate timeout
        timeout_in_seconds = task.config.timeout
        timeout_in_minutes = int(timeout_in_seconds / 60)

        # Push APE jar to device
        with open(task.result.trace_file, 'wb') as trace:
            self._adb_push(jar_ape, "/data/local/tmp/ape.jar", trace)

            # Execute APE with configured parameters
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
                self.config["strategy"]
            ], timeout_in_seconds)

            exec_cmd.invoke(stdout=trace)

    def _adb_push(self, input_file, out_path, std_out):
        """
        Push a file to the Android device.

        Args:
            input_file: File to push
            out_path: Destination path on device
            std_out: Output stream for command output
        """
        self.logger.info(f"ADB pushing: {input_file} to {out_path}")
        push_cmd = Command('adb', ['push', '-a', '-p', input_file, out_path])
        push_cmd.invoke(stdout=std_out)
