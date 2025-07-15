# rvandroid/tools/ares/tool.py
"""
Ares tool implementation with configuration support.
"""
import os

from rvandroid.app import App
from rvandroid.commands.command import Command
from rvandroid.experiment.task.task_model import Task
from rvandroid.tools.configurable_tool import ConfigurableTool
from settings import TOOLS_DIR


class ToolSpec(ConfigurableTool):
    """
    Ares testing tool with configurable parameters.

    ### Architectural Decisions:
    - Extends ConfigurableTool for standardized configuration handling
    - Provides a unified interface to the Ares testing framework
    - Supports customization through configuration parameters

    ### Role in the System:
    - Integrates the Ares Android testing tool into the RV-Android framework
    - Enables automated testing with configurable parameters
    - Provides consistent execution interface aligned with other tools
    """

    def __init__(self):
        """Initialize the Ares tool with default configuration."""
        super().__init__(
            "ares",
            "Ares is an advanced Android testing framework",
            "run_ares.sh"
        )

        # Default configuration
        self.config = {}

    def execute_tool_specific_logic(self, task: Task, app: App):
        """Execute Ares with the configured parameters."""
        self.logger.info(f"Running Ares on {app.name}")

        ares_dir = os.path.join(TOOLS_DIR, 'ares')
        ares_entrypoint = os.path.join(ares_dir, 'run_ares.sh')

        # Calculate timeout
        timeout_in_seconds = task.config.timeout
        timeout_in_minutes = int(timeout_in_seconds / 60)

        with open(task.result.trace_file, 'wb') as ares_trace:
            exec_cmd = Command(f'{ares_entrypoint}', [
                app.path,
                'emulator-5554',
                str(timeout_in_minutes),
                f"{ares_dir}"
            ], timeout_in_seconds)

            exec_cmd.invoke(stdout=ares_trace)
