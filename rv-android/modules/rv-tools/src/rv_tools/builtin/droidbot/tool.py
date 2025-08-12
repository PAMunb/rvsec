"""
DroidBot tool implementation for monitored operations testing.

This module provides integration with the DroidBot Android testing framework,
enabling lightweight test input generation and UI transition graph construction.
"""

from typing import Dict, Any, List

from rv_android_core.domain.app import App
from rv_android_core.commands.command import Command
from rv_android_core.domain.task import Task
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class DroidBotTool(AbstractTool):
    """
    DroidBot lightweight test input generator for monitored operations testing.

    ### Architectural Decisions:
    - Inherits directly from AbstractTool for simplified architecture
    - Implements policy-based exploration strategies for systematic testing coverage
    - Provides comprehensive event generation and UI transition graph construction
    - Uses direct binary execution model for efficient resource utilization
    - Supports multiple exploration policies with configurable parameters
    - Integrates with rv-android-core infrastructure for error handling and logging

    ### Role in the System:
    - Serves as a lightweight and efficient UI exploration tool for monitored operations
    - Provides policy-based exploration strategies for comprehensive coverage analysis
    - Enables rapid test input generation with configurable event counts and timeouts
    - Supports both JCA cryptography detection and generic monitored operations testing
    - Facilitates UI transition graph construction for structural analysis of applications

    ### Key Features:
    - Multiple exploration policies: dfs_naive, dfs_greedy, bfs_naive, bfs_greedy, random
    - Configurable event generation with count limits and timeout mechanisms
    - Handles both emulator and real device execution environments
    - UI element filtering and ad-blocking for focused testing
    - Integration with Android Debug Bridge (ADB) for device communication

    ### Tool Variants:
    DroidBot supports different exploration strategies as variants:
    - bfs_greedy: Breadth-first search with greedy exploration
    - dfs_greedy: Depth-first search with greedy exploration
    - bfs_naive: Simple breadth-first search
    - dfs_naive: Simple depth-first search
    - random: Random event generation
    """

    # Simplified tool specification
    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="droidbot",
        description="DroidBot lightweight test input generator for Android applications",
        url="https://github.com/honeynet/droidbot",
        version="1.0.0",
        process_pattern="droidbot"
    )

    # Available exploration policies that can be used as variants
    AVAILABLE_POLICIES = [
        'dfs_naive', 'dfs_greedy', 'bfs_naive', 'bfs_greedy',
        'random', 'monkey', 'none', 'manual'
    ]

    def __init__(self):
        """
        Initialize the DroidBot tool with rv-android-core infrastructure.
        """
        # Initialize base class with tool spec parameters
        tool_spec = self.get_tool_spec()
        super().__init__(
            name=tool_spec.name,
            description=tool_spec.description,
            process_pattern=tool_spec.process_pattern
        )

        # Configuration will be set through configure() method
        self.config = {}

        self.logger.info("Initialized DroidBot tool for lightweight test input generation")

    @classmethod
    def get_tool_spec(cls):
        """
        Get tool specification for registration.
        
        Returns:
            ToolSpec instance with tool metadata
        """
        return cls.TOOL_SPEC

    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get available DroidBot variants with exploration policy configurations.
        
        Returns:
            Dictionary mapping variant names to DroidBot configuration parameters
        """
        return {
            "default": {
                "policy": "dfs_naive",
                "count": 1000,
                "interval": 3,
                "ignore_ad": True
            },
            "dfs_greedy": {
                "policy": "dfs_greedy",
                "count": 10000000000,
                "interval": 3,
                "ignore_ad": True
            },
            "bfs_greedy": {
                "policy": "bfs_greedy", 
                "count": 10000000000,
                "interval": 3,
                "ignore_ad": True
            },
            "dfs_naive": {
                "policy": "dfs_naive",
                "count": 1000,
                "interval": 3,
                "ignore_ad": True
            },
            "bfs_naive": {
                "policy": "bfs_naive",
                "count": 1000,
                "interval": 3,
                "ignore_ad": True
            },
            "random": {
                "policy": "random",
                "count": 1000,
                "interval": 3,
                "ignore_ad": True
            }
        }
        
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure DroidBot tool with resolved variant parameters.
        
        Args:
            config: Configuration dictionary with DroidBot-specific parameters
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        from rv_android_core.util.error.exceptions import ConfigurationError
        
        # Validate required policy
        if "policy" not in config:
            raise ConfigurationError("DroidBot tool requires 'policy' parameter")
        
        if config["policy"] not in self.AVAILABLE_POLICIES:
            raise ConfigurationError(
                f"Invalid DroidBot policy '{config['policy']}'. "
                f"Available policies: {self.AVAILABLE_POLICIES}"
            )
        
        # Set configuration with defaults
        self.config = {
            "policy": config["policy"],
            "count": config.get("count", 1000),
            "timeout": config.get("timeout", 3600),
            "interval": config.get("interval", 3),
            "device_serial": config.get("device_serial", None),
            "keep_app": config.get("keep_app", False),
            "keep_env": config.get("keep_env", False),
            "debug_mode": config.get("debug_mode", False),
            "random_input": config.get("random_input", False),
            "script_path": config.get("script_path", None),
            "profiling_method": config.get("profiling_method", "none"),
            "ignore_ad": config.get("ignore_ad", True),
            **config  # Include any additional parameters
        }
        
        self.logger.info(
            f"Configured DroidBot tool - Policy: {self.config['policy']}, "
            f"Count: {self.config['count']}, Interval: {self.config['interval']}s"
        )

    @ErrorHandler.handle_errors(
        component="DroidBotTool",
        phase="execute_tool_specific_logic",
        reraise=True
    )
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """
        Execute DroidBot testing with configured parameters.
        
        ### Execution Workflow:
        1. Build DroidBot command with configured parameters
        2. Set up output directory for trace files
        3. Execute DroidBot command on target device
        4. Capture execution output for analysis
        
        Args:
            task: Task configuration containing timeout and other parameters
            app: Application under test with package name and metadata
        """
        self.logger.info(f"Executing DroidBot tool for {app.package_name}")
        self.logger.debug(f"Policy: {self.config['policy']}, Count: {self.config['count']}")

        # Get timeout from task configuration
        timeout_in_seconds = getattr(task.config, 'timeout', self.config['timeout'])

        self.logger.info(f"DroidBot execution timeout: {timeout_in_seconds} seconds")

        # Build DroidBot command
        droidbot_cmd = self._build_droidbot_command(app, timeout_in_seconds)

        # Build command string for logging
        cmd_str = f"{droidbot_cmd.command} {' '.join(droidbot_cmd.args)}"
        self.logger.debug(f"DroidBot command: {cmd_str}")

        # Execute DroidBot testing with centralized error handling
        self.logger.info(f"Starting DroidBot execution for {app.package_name}")

        # Execute command with output redirection (binary mode for command output)
        with open(task.result.trace_file, 'wb') as trace_file:
            # Use centralized command execution with error handling
            # Redirect both stdout and stderr to trace file to prevent console flooding
            result = self._execute_and_check_command(droidbot_cmd, stdout=trace_file, stderr=trace_file)

        # Append success information to trace file (text mode for metadata)
        # with open(task.result.trace_file, 'a', encoding='utf-8') as trace_file:
        #     success_info = f"\n--- DroidBot Execution Completed ---\n"
        #     success_info += f"Policy: {self.config['policy']}\n"
        #     success_info += f"Event count: 10000000000\n"
        #     success_info += f"Command: {cmd_str}\n"
        #     trace_file.write(success_info)

        self.logger.info("DroidBot execution completed successfully")

    def _build_droidbot_command(self, app: App, timeout_seconds: int) -> Command:
        """
        Build the DroidBot command with validated parameters.
        
        Constructs DroidBot command for UI exploration with policy-based testing,
        device targeting, and emulator-specific configurations.
        
        Command format: poetry run droidbot -d emulator-5554 -a <apk> -policy <policy> -count 10000000000 -timeout <timeout> -ignore_ad -is_emulator
        
        Args:
            app: Application under test containing APK path and metadata
            timeout_seconds: Command execution timeout in seconds
            
        Returns:
            Configured Command object for DroidBot execution
        """
        cmd_args = [
            "run", "droidbot",
            "-d", "emulator-5554",  # Target device specification
            "-a", app.path,
            "-policy", self.config["policy"],  # Exploration policy configuration
            "-count", "10000000000",  # High event count for comprehensive exploration
            "-timeout", str(timeout_seconds),
            "-ignore_ad",  # Ignore advertisement elements
            "-is_emulator"  # Emulator-specific optimizations
        ]

        return Command("poetry", cmd_args, timeout_seconds)

    def get_available_policies(self) -> List[str]:
        """
        Get list of available exploration policies.
        
        Returns:
            List of available policy names
        """
        return self.AVAILABLE_POLICIES.copy()

    def get_tool_info(self) -> dict:
        """
        Get comprehensive DroidBot tool information.
        
        Returns:
            Dictionary with tool information and current configuration
        """
        info = super().get_tool_info()
        info.update({
            "tool_spec": self.TOOL_SPEC.to_dict(),
            "available_policies": self.get_available_policies(),
            "current_policy": self.config["policy"],
            "current_count": self.config["count"],
            "current_timeout": self.config["timeout"],
            "version": self.TOOL_SPEC.version,
            "url": self.TOOL_SPEC.url
        })
        return info


