# rvandroid/tools/droidmate/tool.py
"""
DroidMate tool implementation with configuration support.
"""
import os

from rvandroid.app import App
from rvandroid.commands.command import Command
from rvandroid.experiment.task.task_model import Task
from rvandroid.tools.configurable_tool import ConfigurableTool
from settings import TOOLS_DIR, INSTRUMENTED_DIR


class ToolSpec(ConfigurableTool):
    """
    DroidMate tool with configurable parameters.

    ### Architectural Decisions:
    - Extends ConfigurableTool for standardized configuration handling
    - Provides a unified interface to the DroidMate testing framework
    - Supports customization through configuration parameters

    ### Role in the System:
    - Integrates DroidMate into the RV-Android framework
    - Enables automated testing with configurable parameters
    - Provides consistent execution interface aligned with other tools
    """

    def __init__(self):
        """Initialize the DroidMate tool with default configuration."""
        super().__init__(
            "droidmate",
            "DroidMate-2 is a platform to easily assist both developers and researchers "
            "to customize, develop and test new test generators.",
            "org.droidmate"
        )

        # Default configuration
        self.config = {
            "action_limit": 100000000  # Effectively unlimited actions
        }

    def configure_tool_specific(self, config):
        """Configure DroidMate-specific parameters."""
        # Update parameters if specified
        if "action_limit" in config:
            self.config["action_limit"] = config["action_limit"]

    def execute_tool_specific_logic(self, task: Task, app: App):
        """Execute DroidMate with the configured parameters."""
        self.logger.info(f"Running DroidMate on {app.name}")

        droidmate_jar = os.path.join(TOOLS_DIR, "droidmate", "droidmate-2-X.X.X-all.jar")
        output_dir = os.path.join(TOOLS_DIR, "droidmate", "temp")

        # Calculate timeout
        timeout_in_seconds = task.config.timeout
        timeout_in_millis = timeout_in_seconds * 1000

        with open(task.result.trace_file, "wb") as droidmate_trace:
            exec_cmd = Command("java", [
                "-jar",
                f"{droidmate_jar}",
                f"--Exploration-apkNames={app.name}",
                f"--Exploration-apksDir={INSTRUMENTED_DIR}",
                f"--Output-outputDir={output_dir}",
                f"--Selectors-timeLimit={timeout_in_millis}",
                f"--Selectors-actionLimit={self.config['action_limit']}",
                "--Core-logLevel=debug"
            ], timeout=timeout_in_seconds)

            exec_cmd.invoke(stdout=droidmate_trace)