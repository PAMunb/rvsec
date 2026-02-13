"""
ARES Docker-based testing tool implementation.

This module provides integration with ARES (Automated Reinforcement-learning
Exploration System), a systematic UI exploration tool that runs as a Docker
sibling container using reinforcement learning (SAC algorithm) with Appium.
"""

import os
import socket
from typing import Dict, Any

from rv_android_core.domain.app import App
from rv_android_core.commands.command import Command
from rv_android_core.domain.task import Task
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.error_handler import ErrorHandler


class AresTool(AbstractTool):
    """
    ARES Docker-based systematic UI exploration tool.

    ARES runs as a Docker sibling container spawned via docker.sock. The execution
    flow is:
    1. Create an ARES container with env vars (EMUNAME, TIMEOUT_IN_MINUTES)
    2. Copy the APK into /ares/apks/app.apk inside the container via docker cp
    3. Start the container and capture stdout/stderr to the trace file
    4. Clean up the container after execution

    The ARES container runs `run_inside.sh` which executes `parallel_exec.py`
    with the SAC (Soft Actor-Critic) reinforcement learning algorithm, Appium
    for UI automation, and configurable timeout.

    Network configuration:
    - Inside Docker (/.dockerenv exists): --network container:$(hostname)
      shares the parent container's network namespace so ARES can reach
      the emulator at localhost:5554
    - Outside Docker (standalone): --network host for direct emulator access

    The Docker image is phtcosta/ares:latest, built from the Dockerfile in
    this directory (base: jtpastro/docker-adb with ARES from github.com/H2SO4T/ARES).
    """

    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="ares",
        description="ARES Docker-based systematic UI exploration tool",
        url="https://github.com/H2SO4T/ARES",
        version="1.0.0",
        process_pattern="ares"
    )

    def __init__(self):
        """Initialize the ARES tool."""
        tool_spec = self.get_tool_spec()
        super().__init__(
            name=tool_spec.name,
            description=tool_spec.description,
            process_pattern=tool_spec.process_pattern
        )
        self.config = {}
        self.logger.info("Initialized Ares tool for Docker-based exploration")

    @classmethod
    def get_tool_spec(cls):
        """Get tool specification for registration."""
        return cls.TOOL_SPEC

    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get available ARES variants.

        Single 'default' variant matching the ICST experiment configuration.
        """
        return {
            "default": {
                "docker_image": "phtcosta/ares:latest",
            }
        }

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure ARES tool parameters.

        Args:
            config: Configuration dictionary with tool parameters
        """
        self.config = {
            "docker_image": config.get("docker_image", "phtcosta/ares:latest"),
            "device_serial": config.get("device_serial", "emulator-5554"),
            "timeout": config.get("timeout", 600),
        }

        self.logger.info(
            f"Configured Ares tool - Image: {self.config['docker_image']}, "
            f"Device: {self.config['device_serial']}"
        )

    @ErrorHandler.handle_errors(
        component="AresTool",
        phase="execute_tool_specific_logic",
        reraise=True
    )
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """
        Execute ARES testing via Docker sibling container.

        The execution uses docker create + docker cp + docker start pattern
        because the APK file is inside the rvandroid container's filesystem
        and cannot be bind-mounted directly into the sibling container
        (Docker volumes are resolved by the host daemon, not the calling
        container). docker cp works because the Docker CLI reads the file
        locally and streams it to the daemon via the API.

        Args:
            task: Task configuration containing timeout and other parameters
            app: Application under test with package name and metadata
        """
        self.logger.info(f"Executing Ares tool for {app.package_name}")

        timeout_in_seconds = getattr(task.config, 'timeout', self.config['timeout'])
        timeout_in_minutes = max(1, int(timeout_in_seconds / 60))
        container_name = f"ares_{task.id[:8]}"

        self.logger.info(
            f"Ares execution: timeout={timeout_in_minutes}min, "
            f"container={container_name}, image={self.config['docker_image']}"
        )

        try:
            # 1. Create container with env vars and network config
            create_cmd = self._build_create_command(container_name, timeout_in_minutes)
            self.logger.debug(f"Ares create: docker {' '.join(create_cmd.args)}")
            create_cmd.invoke()

            # 2. Copy APK into the container as /ares/apks/app.apk
            cp_cmd = Command("docker", [
                "cp", app.path, f"{container_name}:/ares/apks/app.apk"
            ], 60)
            self.logger.debug(f"Ares cp: {app.path} -> {container_name}:/ares/apks/app.apk")
            cp_cmd.invoke()

            # 3. Start container and capture output
            start_cmd = Command("docker", ["start", "-a", container_name], timeout_in_seconds)
            self.logger.info(f"Starting Ares container {container_name}")

            with open(task.result.trace_file, 'wb') as trace_file:
                self._execute_and_check_command(start_cmd, stdout=trace_file, stderr=trace_file)

            self.logger.info("Ares execution completed successfully")

        finally:
            self._cleanup_container(container_name)

    def _build_create_command(self, container_name: str, timeout_minutes: int) -> Command:
        """
        Build docker create command for the ARES container.

        The ARES container expects:
        - EMUNAME env var: emulator device serial (default: emulator-5554)
        - TIMEOUT_IN_MINUTES env var: exploration timeout in minutes
        - APK at /ares/apks/app.apk (copied via docker cp after creation)

        Args:
            container_name: Name for the Docker container
            timeout_minutes: ARES exploration timeout in minutes

        Returns:
            Configured Command object for docker create
        """
        device_serial = self.config.get("device_serial") or "emulator-5554"

        cmd_args = [
            "create",
            "--name", container_name,
            "-e", f"EMUNAME={device_serial}",
            "-e", f"TIMEOUT_IN_MINUTES={timeout_minutes}",
        ]

        # Network: share parent container's namespace when in Docker (D10/INV-TOOL-15),
        # use host network otherwise for direct emulator access
        if os.path.exists('/.dockerenv'):
            cmd_args.extend(["--network", f"container:{socket.gethostname()}"])
        else:
            cmd_args.extend(["--network", "host"])

        cmd_args.append(self.config["docker_image"])

        return Command("docker", cmd_args, 30)

    def _cleanup_container(self, container_name: str) -> None:
        """Remove the ARES container after execution."""
        try:
            Command("docker", ["rm", "-f", container_name], 30).invoke()
            self.logger.debug(f"Cleaned up container: {container_name}")
        except Exception as e:
            self.logger.warning(f"Failed to clean up container {container_name}: {e}")

    def get_tool_info(self) -> dict:
        """Get ARES tool information."""
        info = super().get_tool_info()
        info.update({
            "tool_spec": self.TOOL_SPEC.to_dict(),
            "docker_image": self.config.get("docker_image", "not configured"),
            "version": self.TOOL_SPEC.version,
            "url": self.TOOL_SPEC.url
        })
        return info
