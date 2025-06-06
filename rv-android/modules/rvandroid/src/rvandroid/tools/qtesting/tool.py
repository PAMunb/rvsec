# rvandroid/tools/qtesting/tool.py
"""
QTesting tool implementation with configuration support.
"""
import os

from rv_android_core.app import App
from rv_android_core.commands.command import Command
from rv_android_core.experiment.task.task_model import Task
from rv_android_core.tools.configurable_tool import ConfigurableTool
from settings import TOOLS_DIR


class ToolSpec(ConfigurableTool):
    """
    QTesting tool with configurable parameters.

    ### Architectural Decisions:
    - Extends ConfigurableTool for standardized configuration handling
    - Provides a unified interface to the QTesting framework
    - Supports customization through configuration parameters

    ### Role in the System:
    - Integrates QTesting Android testing tool into the RV-Android framework
    - Enables reinforcement learning-based testing with configurable parameters
    - Provides consistent execution interface aligned with other tools
    """

    def __init__(self):
        """Initialize the QTesting tool with default configuration."""
        super().__init__(
            "qtesting",
            "QTesting is a reinforcement learning-based Android testing tool.",
            "main.py"
        )

        # Default configuration
        self.config = {
            "test_index": 1  # Default test index
        }

    def configure_tool_specific(self, config):
        """Configure QTesting-specific parameters."""
        # Update parameters if specified
        if "test_index" in config:
            self.config["test_index"] = int(config["test_index"])

    def execute_tool_specific_logic(self, task: Task, app: App):
        """Execute QTesting with the configured parameters."""
        self.logger.info(f"Running QTesting on {app.name}")

        timeout_in_seconds = task.config.timeout
        qtesting_dir = os.path.join(TOOLS_DIR, "qtesting")
        qtesting_python = os.path.join(qtesting_dir, "venv", "bin", "python")
        qtesting_entrypoint = os.path.join(qtesting_dir, "src", "main.py")

        # Create configuration file
        config_file = os.path.join(qtesting_dir, "src", "conf.txt")
        with open(config_file, "w") as f:
            f.write("""
                    [Path]
                    Benchmark =
                    APK_NAME = {0}
                    [Setting]
                    DEVICE_ID = emulator-5554
                    TIME_LIMIT = {1}
                    TEST_INDEX={2}""".format(
                app.path,
                timeout_in_seconds,
                self.config["test_index"]
            ))

        # Execute QTesting
        with open(task.result.trace_file, "wb") as qtesting_trace:
            exec_cmd = Command("python", [
                f"{qtesting_entrypoint}",
                "-r",
                f"{config_file}"
            ])

            exec_cmd.invoke(stdout=qtesting_trace)
