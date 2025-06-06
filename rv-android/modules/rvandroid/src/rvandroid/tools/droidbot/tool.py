# rvandroid/tools/droidbot/tool.py
"""
DroidBot tool implementation with configuration support.
"""
from rv_android_core.app import App
from rv_android_core.commands.command import Command
from rv_android_core.experiment.task.task_model import Task
from rv_android_core.tools.configurable_tool import ConfigurableTool


class ToolSpec(ConfigurableTool):
    """
    DroidBot tool with configurable policies and parameters.

    ### Architectural Decisions:
    - Implements a single configurable tool instead of multiple similar tools
    - Uses configuration to determine specific policy and parameters
    - Extends ConfigurableTool for standardized configuration handling

    ### Role in the System:
    - Provides a unified interface for all DroidBot variants
    - Eliminates code duplication across similar tool implementations
    - Enables dynamic configuration of DroidBot policies through the tool registry
    """

    def __init__(self):
        """Initialize the DroidBot tool with default configuration."""
        super().__init__(
            "droidbot",
            "DroidBot is a lightweight test input generator for Android. "
            "It can send random or scripted input events to an Android app, "
            "achieve higher test coverage more quickly, and generate a UI "
            "transition graph (UTG) after testing.",
            "com.android.commands.droidbot"
        )

        # Default configuration
        self.config = {
            "policy": "dfs_naive",  # Default policy
            "count": "10000000000",  # Default event count (effectively unlimited)
            "ignore_ad": True,  # Ignore ad-related elements
            "is_emulator": True  # Running on an emulator
        }

    def configure_tool_specific(self, config):
        """Configure DroidBot-specific parameters."""
        # Update policy if specified
        if "policy" in config:
            self.config["policy"] = config["policy"]

        # Update other parameters if specified
        for key in ["count", "ignore_ad", "is_emulator"]:
            if key in config:
                self.config[key] = config[key]

        # Set count with default value if not specified
        self.config["count"] = config.get("count", "10000000000")

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

    # def execute_tool_specific_logic(self, task: Task, app: App):
    #     """Execute DroidBot with the configured policy and parameters."""
    #     self.logger.info(f"Running DroidBot with policy: {self.config['policy']}")
    #
    #     # Build command arguments based on configuration
    #     args = [
    #         "-d", "emulator-5554",
    #         "-a", app.path,
    #         "-policy", self.config["policy"],
    #         "-timeout", str(task.config.timeout)
    #     ]
    #
    #     # Add count parameter if it exists in the configuration
    #     if "count" in self.config:
    #         args.extend(["-count", str(self.config["count"])])
    #
    #     # Add optional arguments based on configuration
    #     if self.config.get("ignore_ad", True):
    #         args.append("-ignore_ad")
    #
    #     if self.config.get("is_emulator", True):
    #         args.append("-is_emulator")
    #
    #     # Execute DroidBot command
    #     with open(task.result.trace_file, "wb") as trace:
    #         exec_cmd = Command("droidbot", args, task.config.timeout)
    #         exec_cmd.invoke(stdout=trace)
