"""
QTesting tool — Docker sibling container for Q-learning based UI exploration.

QTesting uses a Q-learning algorithm to explore Android UIs. It runs as a
Docker container (phtcosta/qtesting:latest) that connects to the emulator
via ADB. Configuration is passed through an INI config file (conf.txt)
copied into the container at /qtesting/apks/conf.txt.

The container entry point is: python src/main.py -r apks/conf.txt
"""

import os
import socket
import tempfile
from typing import Any, Dict

from rv_android_core.commands.command import Command
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class QTestingTool(AbstractTool):
    """
    QTesting Q-learning based Android UI exploration tool.

    Runs as a Docker sibling container spawned via docker.sock. The container
    expects an APK at /qtesting/apks/app.apk and a configuration file at
    /qtesting/apks/conf.txt with device serial, timeout, and APK path.
    """

    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="qtesting",
        description="QTesting Q-learning based Android UI exploration tool",
        url="https://github.com/nicetester/QTesting",
        version="1.0.0",
        process_pattern="qtesting",
    )

    def __init__(self):
        tool_spec = self.get_tool_spec()
        super().__init__(
            name=tool_spec.name,
            description=tool_spec.description,
            process_pattern=tool_spec.process_pattern,
        )

        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_tools.builtin.qtesting", {CONTEXT_COMPONENT: "QTestingTool"}
        )

        self.config = {}

    @classmethod
    def get_tool_spec(cls):
        return cls.TOOL_SPEC

    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "default": {
                "docker_image": "phtcosta/qtesting:latest",
            }
        }

    def configure(self, config: Dict[str, Any]) -> None:
        if not config:
            return

        self.config = {
            "docker_image": config.get("docker_image", "phtcosta/qtesting:latest"),
            "device_serial": config.get("device_serial", "emulator-5554"),
            "timeout": config.get("timeout", 3600),
        }

        self.logger.info(
            f"Configured QTesting tool - Image: {self.config['docker_image']}, "
            f"Device: {self.config['device_serial']}"
        )

    @ErrorHandler.handle_errors(
        component="QTestingTool", phase="execute_tool_specific_logic"
    )
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """
        Execute QTesting in a Docker sibling container.

        Three-step pattern (same as ARES):
        1. docker create — container with network config
        2. docker cp — copy APK and conf.txt into /qtesting/apks/
        3. docker start -a — run and capture output as trace file
        """
        timeout_in_seconds = getattr(task.config, "timeout", self.config["timeout"])
        container_name = f"qtesting_{task.id[:8]}"
        device_serial = self.config.get("device_serial") or "emulator-5554"

        self.logger.info(f"Executing QTesting for {app.package_name}")
        self.logger.info(
            f"QTesting timeout: {timeout_in_seconds}s, device: {device_serial}"
        )

        try:
            # Step 1: Create container
            create_cmd = self._build_create_command(container_name)
            self.logger.debug(
                f"Creating QTesting container: docker {' '.join(create_cmd.args)}"
            )
            create_cmd.invoke()
            self.logger.info(f"Created QTesting container: {container_name}")

            # Step 2a: Copy APK into container
            cp_apk_cmd = Command(
                "docker",
                ["cp", app.path, f"{container_name}:/qtesting/apks/app.apk"],
                60,
            )
            cp_apk_cmd.invoke()
            self.logger.debug(f"Copied APK to container: {app.path}")

            # Step 2b: Generate and copy conf.txt into container
            self._copy_config_file(container_name, device_serial, timeout_in_seconds)

            # Step 3: Start container and capture output
            start_cmd = Command(
                "docker", ["start", "-a", container_name], timeout_in_seconds
            )
            self.logger.info(f"Starting QTesting container: {container_name}")
            with open(task.result.trace_file, "wb") as trace_file:
                self._execute_and_check_command(
                    start_cmd, stdout=trace_file, stderr=trace_file
                )

        finally:
            self._cleanup_container(container_name)

    def _build_create_command(self, container_name: str) -> Command:
        """Build the docker create command for QTesting container."""
        cmd_args = [
            "create",
            "--name",
            container_name,
        ]

        # Network: share parent container's network inside Docker,
        # use host network outside Docker
        if os.path.exists("/.dockerenv"):
            cmd_args.extend(["--network", f"container:{socket.gethostname()}"])
        else:
            cmd_args.extend(["--network", "host"])

        cmd_args.append(self.config["docker_image"])

        return Command("docker", cmd_args, 30)

    def _copy_config_file(
        self, container_name: str, device_serial: str, timeout_seconds: int
    ) -> None:
        """Generate conf.txt and copy it into the container."""
        # QTesting reads an INI config file at /qtesting/apks/conf.txt.
        # Benchmark is empty because APK_NAME is an absolute path inside
        # the container. TIME_LIMIT is in seconds (not minutes like ARES).
        conf_content = (
            "[Path]\n"
            "Benchmark = \n"
            "APK_NAME = /qtesting/apks/app.apk\n"
            "\n"
            "[Setting]\n"
            f"DEVICE_ID = {device_serial}\n"
            f"TIME_LIMIT = {timeout_seconds}\n"
            "TEST_INDEX=1\n"
        )

        # Write to a temp file and docker cp into the container
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(conf_content)
            tmp_path = f.name

        try:
            cp_cmd = Command(
                "docker",
                ["cp", tmp_path, f"{container_name}:/qtesting/apks/conf.txt"],
                30,
            )
            cp_cmd.invoke()
            self.logger.debug(
                f"Copied conf.txt to container "
                f"(DEVICE_ID={device_serial}, TIME_LIMIT={timeout_seconds}s)"
            )
        finally:
            os.unlink(tmp_path)

    def _cleanup_container(self, container_name: str) -> None:
        """Remove the Docker container."""
        try:
            Command("docker", ["rm", "-f", container_name], 30).invoke()
            self.logger.debug(f"Cleaned up container: {container_name}")
        except Exception as e:
            self.logger.warning(f"Failed to clean up container {container_name}: {e}")
