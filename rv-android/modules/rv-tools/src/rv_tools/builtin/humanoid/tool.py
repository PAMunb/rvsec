"""
Humanoid tool implementation for monitored operations testing.

This module provides integration with DroidBot's humanoid mode, which connects
to an external Humanoid inference HTTP server for human-like input generation
during Android application exploration.
"""

from typing import Any, Dict

from rv_android_core.commands.command import Command
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.error_handler import ErrorHandler


class HumanoidTool(AbstractTool):
    """
    DroidBot with Humanoid inference server for human-like exploration.

    Humanoid is NOT a standalone tool. It runs DroidBot with the `-humanoid <url>`
    flag, which connects to an external HTTP inference server (phtcosta/humanoid:1.0
    on port 50405) for human-like input generation. The Humanoid server provides a
    trained model that predicts human-like touch interactions based on UI screenshots.

    The command format is identical to DroidBot with one addition:
        droidbot -d <serial> -a <apk> -humanoid <url> -policy <policy>
            -count 10000000000 -timeout <t> -ignore_ad -is_emulator

    Configuration follows the canonical ARES/QTesting variant-default pattern
    (gh55 D8): the default `humanoid_url` is declared in `get_variants()` and the
    factory merge `{**variant_defaults, **tool_config.parameters}` guarantees the
    key is present at `configure(config)` time. L5 (`rv-experiment`) overrides the
    default by injecting `parameters["humanoid_url"]` whenever `RV_HUMANOID_URL`
    or `--humanoid-url` is set. No `os.environ` access happens at L2.
    """

    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="humanoid",
        description="DroidBot with Humanoid inference server for human-like exploration",
        url="https://github.com/yzygitzh/Humanoid",
        version="1.0.0",
        process_pattern="droidbot",
    )

    def __init__(self):
        """Initialize the Humanoid tool."""
        tool_spec = self.get_tool_spec()
        super().__init__(
            name=tool_spec.name,
            description=tool_spec.description,
            process_pattern=tool_spec.process_pattern,
        )
        self.config = {}
        self.logger.info("Initialized Humanoid tool (DroidBot + humanoid inference)")

    @classmethod
    def get_tool_spec(cls):
        """Get tool specification for registration."""
        return cls.TOOL_SPEC

    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get available Humanoid variants.

        Only a single 'default' variant is provided, matching the ICST experiment
        configuration (dfs_greedy policy with humanoid inference). The
        `humanoid_url` default carries the canonical localhost endpoint —
        ARES/QTesting precedent (`builtin/ares/tool.py:79` `docker_image`).
        """
        return {
            "default": {
                "policy": "dfs_greedy",
                "count": 10000000000,
                "ignore_ad": True,
                "humanoid_url": "127.0.0.1:50405",
            }
        }

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure Humanoid tool parameters.

        `config` is the merged dict produced by `ToolFactory.create_tool` —
        `{**variant_defaults, **tool_config.parameters}` — so `humanoid_url` is
        always present (variant default `127.0.0.1:50405` carries through when
        L5 does not override).

        Args:
            config: Configuration dictionary with tool parameters
        """
        self.config = {
            "policy": config.get("policy", "dfs_greedy"),
            "count": config.get("count", 10000000000),
            "timeout": config.get("timeout", 3600),
            "device_serial": config.get("device_serial", "emulator-5554"),
            "humanoid_url": config["humanoid_url"],  # always present after merge
            "ignore_ad": config.get("ignore_ad", True),
        }

        self.logger.info(
            f"Configured Humanoid tool - Policy: {self.config['policy']}, "
            f"Humanoid URL: {self.config['humanoid_url']}"
        )

    @ErrorHandler.handle_errors(
        component="HumanoidTool", phase="execute_tool_specific_logic", reraise=True
    )
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """
        Execute DroidBot with humanoid inference for the target application.

        Args:
            task: Task configuration containing timeout and other parameters
            app: Application under test with package name and metadata
        """
        self.logger.info(f"Executing Humanoid tool for {app.package_name}")
        self.logger.debug(
            f"Policy: {self.config['policy']}, Humanoid URL: {self.config['humanoid_url']}"
        )

        timeout_in_seconds = getattr(task.config, "timeout", self.config["timeout"])
        self.logger.info(f"Humanoid execution timeout: {timeout_in_seconds} seconds")

        humanoid_cmd = self._build_humanoid_command(app, timeout_in_seconds)

        cmd_str = f"{humanoid_cmd.command} {' '.join(humanoid_cmd.args)}"
        self.logger.debug(f"Humanoid command: {cmd_str}")

        self.logger.info(f"Starting Humanoid execution for {app.package_name}")

        with open(task.result.trace_file, "wb") as trace_file:
            self._execute_and_check_command(
                humanoid_cmd, stdout=trace_file, stderr=trace_file
            )

        self.logger.info("Humanoid execution completed successfully")

    def _build_humanoid_command(self, app: App, timeout_seconds: int) -> Command:
        """
        Build DroidBot command with the -humanoid flag.

        Command format:
            droidbot -d <serial> -a <apk> -humanoid <url>
                -policy <policy> -count 10000000000 -timeout <t> -ignore_ad -is_emulator

        Args:
            app: Application under test containing APK path
            timeout_seconds: Command execution timeout in seconds

        Returns:
            Configured Command object
        """
        device_serial = self.config.get("device_serial") or "emulator-5554"

        cmd_args = [
            "-d",
            device_serial,
            "-a",
            app.path,
            "-humanoid",
            self.config["humanoid_url"],
            "-policy",
            self.config["policy"],
            "-count",
            "10000000000",
            "-timeout",
            str(timeout_seconds),
            "-ignore_ad",
            "-is_emulator",
        ]

        return Command("droidbot", cmd_args, timeout_seconds)

    def get_tool_info(self) -> dict:
        """Get Humanoid tool information."""
        info = super().get_tool_info()
        info.update(
            {
                "tool_spec": self.TOOL_SPEC.to_dict(),
                "humanoid_url": self.config.get("humanoid_url", "not configured"),
                "current_policy": self.config.get("policy", "not configured"),
                "version": self.TOOL_SPEC.version,
                "url": self.TOOL_SPEC.url,
            }
        )
        return info
