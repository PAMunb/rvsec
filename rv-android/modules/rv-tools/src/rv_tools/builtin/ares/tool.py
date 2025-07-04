"""
Ares Docker-based testing tool implementation.

This module provides integration with the Ares Android testing framework,
enabling systematic UI exploration through Docker containerization.
"""

import os
from typing import Dict, Any, List

from rv_android_core.app import App
from rv_android_core.commands.command import Command
from rv_android_core.domain.task import Task
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT


class AresTool(AbstractTool):
    """
    Ares Docker-based systematic UI exploration tool for monitored operations testing.

    ### Architectural Decisions:
    - Inherits directly from AbstractTool for simplified architecture
    - Implements Docker-based execution model for isolated testing environment
    - Provides systematic UI exploration with configurable parameters
    - Uses containerized execution for reproducible testing conditions
    - Supports timeout management and execution control
    - Integrates with rv-android-core infrastructure for error handling and logging

    ### Role in the System:
    - Serves as a Docker-based testing tool for systematic Android app exploration
    - Provides isolated execution environment through containerization
    - Enables systematic UI exploration with configurable strategies
    - Supports both JCA cryptography detection and generic monitored operations testing
    - Facilitates reproducible testing through standardized container environments

    ### Key Features:
    - Docker-based execution for environment isolation
    - Systematic UI exploration and interaction
    - Configurable execution timeouts and parameters
    - APK deployment and testing automation
    - Integration with Android emulator through Docker

    ### Tool Variants:
    Ares supports different execution modes as variants:
    - standard: Standard systematic exploration
    - debug: Debug mode with verbose logging
    - fast: Fast exploration with reduced timeouts
    """

    # Simplified tool specification
    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="ares",
        description="Ares Docker-based systematic UI exploration tool for Android applications",
        url="https://github.com/functional-fuzzing-android-apps/ares",
        version="1.0.0",
        process_pattern="ares"
    )

    def __init__(self, name: str = None, description: str = None, process_pattern: str = None):
        """
        Initialize the Ares tool with rv-android-core infrastructure.
        """
        super().__init__(
            name=name or self.TOOL_SPEC.name,
            description=description or self.TOOL_SPEC.description,
            process_pattern=process_pattern or self.TOOL_SPEC.process_pattern
        )

        # Initialize rv-android-core infrastructure components
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_tools.builtin.ares",
            {CONTEXT_COMPONENT: "AresTool"}
        )

        # Default Ares configuration
        self.config = {
            "timeout": 600,                  # Execution timeout in seconds
            "emulator_name": "emulator-5554", # Target emulator name
            "docker_image": "ares:latest",   # Docker image to use
            "container_name": None,          # Container name (auto-generated)
            "debug_mode": False,             # Enable debug mode
            "cleanup_container": True,       # Clean up container after execution
            "volume_mapping": None,          # Volume mapping for results
            "environment_vars": {}           # Environment variables for container
        }

        self.logger.info("Initialized Ares tool for Docker-based exploration")

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure Ares-specific parameters.

        Supported configuration options:
        - timeout: Execution timeout in seconds
        - emulator_name: Target emulator name
        - docker_image: Docker image to use
        - container_name: Container name
        - debug_mode: Enable debug mode
        - cleanup_container: Clean up container after execution
        - volume_mapping: Volume mapping for results
        - environment_vars: Environment variables for container

        Args:
            config: Configuration dictionary with Ares parameters
        """
        if not config:
            return

        # Update timeout
        if 'timeout' in config:
            try:
                timeout = int(config['timeout'])
                if timeout > 0:
                    self.config['timeout'] = timeout
                    self.logger.debug(f"Set Ares timeout to: {timeout}s")
                else:
                    self.logger.warning("Timeout must be positive")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid timeout value: {config['timeout']}")

        # Update emulator name
        if 'emulator_name' in config:
            self.config['emulator_name'] = str(config['emulator_name'])
            self.logger.debug(f"Set Ares emulator name to: {config['emulator_name']}")

        # Update Docker image
        if 'docker_image' in config:
            self.config['docker_image'] = str(config['docker_image'])
            self.logger.debug(f"Set Ares Docker image to: {config['docker_image']}")

        # Update container name
        if 'container_name' in config:
            self.config['container_name'] = str(config['container_name'])
            self.logger.debug(f"Set Ares container name to: {config['container_name']}")

        # Update boolean flags
        boolean_flags = ['debug_mode', 'cleanup_container']
        for flag in boolean_flags:
            if flag in config:
                self.config[flag] = bool(config[flag])
                self.logger.debug(f"Set Ares {flag} to: {self.config[flag]}")

        # Update volume mapping
        if 'volume_mapping' in config:
            self.config['volume_mapping'] = config['volume_mapping']
            self.logger.debug(f"Set Ares volume mapping to: {config['volume_mapping']}")

        # Update environment variables
        if 'environment_vars' in config and isinstance(config['environment_vars'], dict):
            self.config['environment_vars'].update(config['environment_vars'])
            self.logger.debug(f"Updated Ares environment variables: {config['environment_vars']}")

    @ErrorHandler.handle_errors(
        component="AresTool",
        phase="execute_tool_specific_logic"
    )
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """
        Execute Ares testing with configured parameters.

        ### Execution Workflow:
        1. Prepare Docker environment and container configuration
        2. Mount necessary volumes for APK and results
        3. Execute Ares in Docker container with specified parameters
        4. Capture execution output and results
        5. Clean up container resources (if enabled)

        Args:
            task: Task configuration containing timeout and other parameters
            app: Application under test with package name and metadata
        """
        self.logger.info(f"Executing Ares tool for {app.package_name}")
        self.logger.debug(f"Docker image: {self.config['docker_image']}, Timeout: {self.config['timeout']}s")

        # Get timeout from task configuration
        timeout_in_seconds = getattr(task.config, 'timeout', self.config['timeout'])
        
        self.logger.info(f"Ares execution timeout: {timeout_in_seconds} seconds")

        # Create output directory for Ares results
        output_dir = os.path.join(os.path.dirname(task.result.trace_file), "ares_output")
        os.makedirs(output_dir, exist_ok=True)

        # Generate container name if not provided
        if not self.config['container_name']:
            container_name = f"ares_{app.package_name.replace('.', '_')}"
        else:
            container_name = self.config['container_name']

        # Build Ares Docker command
        ares_cmd = self._build_ares_command(app, output_dir, container_name, timeout_in_seconds)
        
        # Build command string for logging
        cmd_str = f"{ares_cmd.command} {' '.join(ares_cmd.args)}"
        self.logger.debug(f"Ares command: {cmd_str}")

        # Execute Ares testing with centralized error handling
        try:
            self.logger.info(f"Starting Ares execution for {app.package_name}")
            
            # Execute command with output redirection (binary mode for command output)
            with open(task.result.trace_file, 'wb') as trace_file:
                # Use centralized command execution with error handling
                # Redirect both stdout and stderr to trace file to prevent console flooding
                result = self._execute_and_check_command(ares_cmd, stdout=trace_file, stderr=trace_file)
            
            # Append success information to trace file (text mode for metadata)
            # with open(task.result.trace_file, 'a', encoding='utf-8') as trace_file:
            #     success_info = f"\n--- Ares Execution Completed ---\n"
            #     success_info += f"Docker image: {self.config['docker_image']}\n"
            #     success_info += f"Container name: {container_name}\n"
            #     success_info += f"Output directory: {output_dir}\n"
            #     success_info += f"Command: {cmd_str}\n"
            #     trace_file.write(success_info)
            
            self.logger.info("Ares execution completed successfully")
            
        except Exception as e:
            self.logger.error(f"Ares execution failed: {str(e)}")
            raise
        finally:
            # Clean up container if enabled
            if self.config['cleanup_container']:
                self._cleanup_container(container_name)

    def _build_ares_command(self, app: App, output_dir: str, container_name: str, timeout_seconds: int) -> Command:
        """
        Build the Ares Docker command with configured parameters.

        Args:
            app: Application under test
            output_dir: Output directory for Ares results
            container_name: Docker container name
            timeout_seconds: Command execution timeout

        Returns:
            Configured Command object for Ares execution
        """
        # Start building Docker command arguments
        cmd_args = [
            "run",
            "--name", container_name,
            "--rm" if self.config['cleanup_container'] else "",
            "-v", f"{app.path}:/app/target.apk:ro",
            "-v", f"{output_dir}:/app/output"
        ]

        # Remove empty strings from args
        cmd_args = [arg for arg in cmd_args if arg]

        # Add environment variables
        for key, value in self.config['environment_vars'].items():
            cmd_args.extend(["-e", f"{key}={value}"])

        # Add volume mapping if specified
        if self.config['volume_mapping']:
            cmd_args.extend(["-v", self.config['volume_mapping']])

        # Add Docker image
        cmd_args.append(self.config['docker_image'])

        # Add Ares-specific arguments
        cmd_args.extend([
            "--apk", "/app/target.apk",
            "--output", "/app/output",
            "--emulator", self.config['emulator_name'],
            "--timeout", str(self.config['timeout'])
        ])

        # Add debug mode if enabled
        if self.config['debug_mode']:
            cmd_args.append("--debug")

        return Command("docker", cmd_args, timeout_seconds)

    def _cleanup_container(self, container_name: str) -> None:
        """
        Clean up Docker container after execution.

        Args:
            container_name: Name of container to clean up
        """
        try:
            cleanup_cmd = Command("docker", ["rm", "-f", container_name], 30)
            cleanup_cmd.invoke()
            self.logger.debug(f"Cleaned up container: {container_name}")
        except Exception as e:
            self.logger.warning(f"Failed to clean up container {container_name}: {e}")

    def get_tool_info(self) -> dict:
        """
        Get comprehensive Ares tool information.

        Returns:
            Dictionary with tool information and current configuration
        """
        info = super().get_tool_info()
        info.update({
            "tool_spec": self.TOOL_SPEC.to_dict(),
            "docker_image": self.config["docker_image"],
            "current_timeout": self.config["timeout"],
            "debug_mode": self.config["debug_mode"],
            "version": self.TOOL_SPEC.version,
            "url": self.TOOL_SPEC.url
        })
        return info


# Function to register Ares variants
def register_ares_variants(registry):
    """
    Register Ares variants in the tool registry.
    
    Args:
        registry: ToolRegistry instance
    """
    # Register execution mode variants
    variants = {
        "standard": {"debug_mode": False, "timeout": 600},
        "debug": {"debug_mode": True, "timeout": 900},
        "fast": {"debug_mode": False, "timeout": 300}
    }
    
    for variant_name, config in variants.items():
        registry.register_variant("ares", variant_name, config)