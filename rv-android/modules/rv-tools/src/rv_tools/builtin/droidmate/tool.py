"""
DroidMate tool — DroidMate-2 JAR-based Android UI exploration.

DroidMate-2 (https://github.com/uds-se/droidmate) is a platform for automated
Android app exploration. It runs as a local `java -jar` process using a fat JAR
(`droidmate-2-X.X.X-all.jar`, ~46MB) that includes all dependencies.

DroidMate-2 uses a `--Category-settingName=value` CLI flag format:
  --Exploration-apkNames=<filename>    APK filename (not full path)
  --Exploration-apksDir=<directory>    Directory containing the APK
  --Output-outputDir=<directory>       Output directory for results
  --Selectors-timeLimit=<ms>           Time limit in milliseconds
  --Selectors-actionLimit=<count>      Action count limit
  --Core-logLevel=<level>              Log level (debug, info, etc.)
"""

import os
from typing import Any, Dict

from rv_android_core.commands.command import Command
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.jar_resolver import JarResolver
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class DroidMateTool(AbstractTool):

    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="droidmate",
        description="DroidMate-2 JAR-based Android UI exploration tool",
        url="https://github.com/uds-se/droidmate",
        version="1.0.0",
        process_pattern="org.droidmate",
    )

    JAR_NAME = "droidmate-2-X.X.X-all.jar"

    def __init__(self):
        tool_spec = self.get_tool_spec()
        super().__init__(
            name=tool_spec.name,
            description=tool_spec.description,
            process_pattern=tool_spec.process_pattern,
        )
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_tools.builtin.droidmate", {CONTEXT_COMPONENT: "DroidMateTool"}
        )
        self.jar_resolver = JarResolver()
        self.config = {}

    @classmethod
    def get_tool_spec(cls):
        return cls.TOOL_SPEC

    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "default": {
                "action_limit": 100000000,
            }
        }

    def configure(self, config: Dict[str, Any]) -> None:
        if not config:
            return
        self.config = {
            "action_limit": config.get("action_limit", 100000000),
            "device_serial": config.get("device_serial", "emulator-5554"),
            "timeout": config.get("timeout", 3600),
        }
        self.logger.info(
            f"Configured DroidMate tool - Action limit: {self.config['action_limit']}"
        )

    @ErrorHandler.handle_errors(
        component="DroidMateTool", phase="execute_tool_specific_logic"
    )
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        timeout_in_seconds = getattr(
            task.config, "timeout", self.config.get("timeout", 3600)
        )

        self.logger.info(f"Executing DroidMate for {app.package_name}")
        self.logger.info(f"DroidMate timeout: {timeout_in_seconds}s")

        # Resolve JAR path via JarResolver (searches os.path.dirname(__file__) first)
        jar_path = self._resolve_jar()

        # DroidMate output goes to a temp directory alongside the trace file
        output_dir = os.path.join(
            os.path.dirname(task.result.trace_file), "droidmate_output"
        )
        os.makedirs(output_dir, exist_ok=True)

        # Build and execute DroidMate command
        cmd = self._build_droidmate_command(
            app, jar_path, output_dir, timeout_in_seconds
        )

        with open(task.result.trace_file, "wb") as trace_file:
            self._execute_and_check_command(cmd, stdout=trace_file, stderr=trace_file)

    def _resolve_jar(self) -> str:
        """Resolve DroidMate JAR. The module dir (Docker bundling) is the only
        L2-supplied search root; TOOLS_DIR-based paths are added by the resolver
        at L1 (gh55 D10: TOOLS_DIR is an L1 cross-layer infra read)."""
        search_paths = [os.path.dirname(__file__)]
        return self.jar_resolver.resolve_jar_path(self.JAR_NAME, search_paths)

    def _build_droidmate_command(
        self, app: App, jar_path: str, output_dir: str, timeout_seconds: int
    ) -> Command:
        """Build DroidMate-2 command with correct --Category-settingName=value flags."""
        timeout_millis = timeout_seconds * 1000
        action_limit = self.config.get("action_limit", 100000000)

        # DroidMate-2 expects APK filename and directory separately
        apk_name = os.path.basename(app.path)
        apk_dir = os.path.dirname(app.path)

        cmd_args = [
            "-jar",
            jar_path,
            f"--Exploration-apkNames={apk_name}",
            f"--Exploration-apksDir={apk_dir}",
            f"--Output-outputDir={output_dir}",
            f"--Selectors-timeLimit={timeout_millis}",
            f"--Selectors-actionLimit={action_limit}",
            "--Core-logLevel=debug",
        ]

        return Command("java", cmd_args, timeout_seconds)
